import os.path
import random
import time
from typing import List, Tuple, Union

import cloudpickle
import pygame
from pygame.locals import KEYDOWN

from . import clientgame, config, definitions
from . import msgparts as mp
from . import stats
from .clientgameorder import update_orders_list
from .clientmedia import play_sequence, voice
from .definitions import rules, style
from .lib.log import warning
from .lib.msgs import nb2msg, encode_msg
from .lib.resource import res
from .paths import (
    MAX_SAVE_SLOTS,
    current_replays_dir,
    current_resume_save_path,
    current_saves_dir,
)
from .version import VERSION, compatibility_version
from .world import World, MapError
from .worldclient import (
    Coordinator,
    DirectClient,
    DummyClient,
    RemoteClient,
    ReplayClient,
    _Controller,
    send_platform_version_to_metaserver,
)
from .worldupgrade import Upgrade


SAVE_RECURSION_LIMIT_BASE = 20000
SAVE_RECURSION_LIMIT_MAX = 100000


def pickle_recursion_limit_for_squares(n):
    if n <= 0:
        return SAVE_RECURSION_LIMIT_BASE
    return min(SAVE_RECURSION_LIMIT_MAX, max(SAVE_RECURSION_LIMIT_BASE, n * 5))


def pickle_recursion_limit_for_file_size(size_bytes):
    if size_bytes > 5 * 1024 * 1024:
        return 50000
    if size_bytes > 1024 * 1024:
        return 30000
    return SAVE_RECURSION_LIMIT_BASE


def cloudpickle_dump_game(obj, f, *, square_count=0):
    import sys as _sys

    limit = pickle_recursion_limit_for_squares(square_count)
    saved = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(saved, limit))
    try:
        cloudpickle.dump(obj, f)
    finally:
        _sys.setrecursionlimit(saved)


class SaveTooLargeError(Exception):
    """pickle 在拉高 recursion limit 后仍失败."""

    def __init__(self, square_count):
        self.square_count = square_count
        super().__init__(square_count)


class _Game:

    default_triggers: List[Tuple[str, List[str], List[str]]] = []
    game_type_name: str
    record_replay = True
    allow_cheatmode = True
    must_apply_equivalent_type = False
    players: List[_Controller]
    local_client: Union[DirectClient, Coordinator]
    interface: clientgame.GameInterface
    auto = None

    @staticmethod
    def _next_replay_number():
        """Return the next sequential replay number by scanning existing replays."""
        replays_dir = current_replays_dir()
        max_n = 0
        import re as _re
        try:
            for name in os.listdir(replays_dir):
                m = _re.match(r'^replay(\d+)_\d+\.txt$', name)
                if m:
                    n = int(m.group(1))
                    if n > max_n:
                        max_n = n
        except OSError:
            pass
        return max_n + 1

    def create_replay(self):
        # 写入当前 mod 专属的回放目录，使得不同 mod 之间的录像互不混淆
        n = self._next_replay_number()
        self._replay_file = open(
            os.path.join(current_replays_dir(), "replay%d_%s.txt" % (n, int(time.time()))),
            "w",
            encoding="utf-8",
        )
        self.replay_write(self.game_type_name)
        players = " ".join([p.login for p in self.players])
        self.replay_write(self.map.name + " " + players)
        self.replay_write(VERSION)
        self.replay_write(str(res.mods))
        self.replay_write(compatibility_version())
        self._replay_write_map()
        self.replay_write(players)
        alliances = [p.alliance for p in self.players]
        self.replay_write(" ".join(map(str, alliances)))
        factions = [p.faction for p in self.players]
        self.replay_write(" ".join(factions))
        # seed 行向后兼容地追加合作战役敌人强度百分比：旧回放只有 seed，
        # 新回放为 "<seed> <enemy_hp%> <enemy_damage%>"。这样回放重建世界时
        # 能套用与对局完全一致的难度，避免敌方 hp/伤害缩放不一致导致不同步。
        ehp = int(getattr(self, "enemy_hp_factor", 100) or 100)
        edmg = int(getattr(self, "enemy_damage_factor", 100) or 100)
        if ehp != 100 or edmg != 100:
            self.replay_write(f"{self.seed} {ehp} {edmg}")
        else:
            self.replay_write(str(self.seed))

    def _replay_write_map(self):
        self.replay_write(self.map.digest())

    def replay_write(self, s):
        self._replay_file.write(s + "\n")

    def _game_type(self):
        return "{}/{}/{}".format(
            VERSION,
            self.game_type_name + "-" + self.map.name,
            self.nb_human_players,
        )

    def is_campaign_session(self) -> bool:
        """True for single-player missions and coop campaign chapters."""
        if getattr(self, "is_coop_campaign", False):
            return True
        if self.game_type_name == "mission":
            return True
        world = getattr(self, "world", None)
        return bool(getattr(world, "is_campaign", False))

    def _pin_scoring_player(self):
        """Remember the local human for end-of-game score and achievements.

        Ctrl+Shift+F4 (change_player) rebinds local_client.player for observation,
        but must not let AI victory grant the human medals, cards, or achievements.
        """
        if getattr(self, "_scoring_player", None) is not None:
            return
        local = getattr(self, "local_client", None)
        player = getattr(local, "player", None) if local is not None else None
        if (
            player is not None
            and getattr(player, "is_human", False)
            and not getattr(player, "is_spectator", False)
        ):
            self._scoring_player = player
            return
        world = getattr(self, "world", None)
        if world is None:
            return
        for p in self._all_human_players(world):
            self._scoring_player = p
            return

    @staticmethod
    def _all_human_players(world):
        for p in world.players:
            if getattr(p, "is_human", False) and not getattr(p, "is_spectator", False):
                yield p
        for p in getattr(world, "ex_players", []):
            if getattr(p, "is_human", False) and not getattr(p, "is_spectator", False):
                yield p

    def scoring_player(self):
        """Local human whose match outcome drives score and achievements."""
        if getattr(self, "_scoring_player", None) is None:
            self._pin_scoring_player()
        pinned = getattr(self, "_scoring_player", None)
        world = getattr(self, "world", None)
        if pinned is None or world is None:
            return None
        if pinned in world.players or pinned in getattr(world, "ex_players", []):
            return pinned
        return None

    def _defeated_scoring_enemy_ids(self, player):
        stats = player.stats
        return {
            p.id
            for p in stats._all_world_players()
            if stats._is_scoring_computer(p)
        }

    def _record_change_player_baseline(self):
        if hasattr(self, "_enemies_defeated_at_first_change"):
            return
        player = self.scoring_player()
        if player is None or not hasattr(player, "stats"):
            self._enemies_defeated_at_first_change = set()
            return
        self._enemies_defeated_at_first_change = self._defeated_scoring_enemy_ids(player)

    def scored_enemy_ids(self):
        """Scoring opponents that may contribute AI-defeat points after change_player."""
        player = self.scoring_player()
        if player is None:
            return set()
        all_ids = self._defeated_scoring_enemy_ids(player)
        if not getattr(self, "_change_player_used", False):
            return all_ids
        baseline = getattr(self, "_enemies_defeated_at_first_change", set())
        return all_ids & baseline

    def scoring_victory(self):
        """Whether the pinned human earned a valid win for score and achievements."""
        player = self.scoring_player()
        if player is None or not player.has_victory:
            return False
        if not getattr(self, "_change_player_used", False):
            return True
        baseline = getattr(self, "_enemies_defeated_at_first_change", None)
        if baseline is None:
            return False
        current = self._defeated_scoring_enemy_ids(player)
        # After Ctrl+Shift+F4, no scoring opponent may fall for the first time.
        return current <= baseline

    def _record_stats(self, world):
        if self.is_campaign_session():
            return
        stats.add(self._game_type(), int(world.time / 1000))

    def _world_default_triggers(self):
        """RMG maps embed their own victory/defeat triggers; skip melee defaults."""
        map_obj = getattr(self, "map", None)
        definition = getattr(map_obj, "definition", "") or ""
        if definition:
            from .randommap import parse_random_map_meta

            if parse_random_map_meta(definition)[0]:
                return []
        return self.default_triggers

    def run(self, speed=config.speed):
        if self.record_replay:
            self.create_replay()

        self.world = World(self._world_default_triggers(), self.seed)
        # 标记本局是否为战役（mission）：战役里的电脑只是触发器脚本（ai_timers），
        # 没有具体身份，完成战役时不应播报它"被击败/退出了游戏"。
        # 合作战役（多人玩同一张战役关）也按战役处理：使用战役音乐、抑制对
        # 触发器 NPC 的"被击败/退出"播报、并让过场/目标按战役语义共享。
        # 注意：world.campaign 对合作战役保持 None（不设置），因此跨章节的
        # campaign_flag 触发器会自动成为确定性 no-op（读到 None 返回 False、
        # 不写本地配置），避免各客户端读各自本地存档导致的多人不同步；
        # 关卡内 set_map_flag/map_flag 用的是世界内状态，仍可正常工作。
        self.world.is_campaign = (
            (self.game_type_name == "mission")
            or bool(getattr(self, "is_coop_campaign", False))
        )
        # 合作战役难度：把已算定的敌人强度百分比写入世界，世界据此在敌方单位生成时
        # 缩放 hp、在结算敌方输出伤害时缩放 damage（整数运算，确定性安全）。
        # 非合作/未设难度时默认为 100（不改变原版平衡）。
        self.world.enemy_hp_factor = int(getattr(self, "enemy_hp_factor", 100) or 100)
        self.world.enemy_damage_factor = int(getattr(self, "enemy_damage_factor", 100) or 100)
        self.world.coop_difficulty = getattr(self, "coop_difficulty", "") or ""
        # 条约时间配置（分钟转毫秒），仅多人局使用
        treaty_minutes = int(getattr(self, "treaty_minutes", 0) or 0)
        if treaty_minutes > 0:
            # 记录条约结束时间（世界时间从0开始，单位毫秒）
            self.world.treaty_until_time = treaty_minutes * 60 * 1000
        else:
            self.world.treaty_until_time = 0

        chapter = getattr(self, "chapter", None)
        if chapter is not None and getattr(chapter, "campaign", None) is not None:
            self.world.campaign = chapter.campaign

        try:
            self.world.load_and_build_map(self.map)
        except MapError as msg:
            msg = "map error: %s" % msg
            warning(msg)
            voice.alert(mp.BEEP + [msg])
        else:
            use_equivalents = self.must_apply_equivalent_type
            if getattr(self, "is_coop_campaign", False):
                # 合作战役地图按战役单位表生成（与单人战役一致），
                # 不做多人局阵营等价替换，否则 footman 等可能与 style 键盘槽位脱节。
                use_equivalents = False
            self.world.populate_map(self.players, equivalents=use_equivalents)
            self._pin_scoring_player()
            if chapter is not None and getattr(chapter, "campaign", None) is not None:
                from .campaign_hero import restore_hero_on_world

                restore_hero_on_world(
                    self.world, chapter.campaign, chapter.number
                )
            from .card_loadout import apply_training_loadout, loadout_applied_msgs

            applied_cards = apply_training_loadout(
                self,
                getattr(self, "card_loadout", None) or [],
                getattr(self, "card_loadout_faction", None),
            )
            if applied_cards:
                for msg in loadout_applied_msgs(applied_cards):
                    voice.alert(msg)
            self.nb_human_players = self.world.current_nb_human_players()
            self.interface = clientgame.GameInterface(self.local_client, speed=speed)
            self.interface.auto = self.auto
            # 推导本局是否锁定联盟：如果开局前已设置非空且存在共享的联盟编号，则锁定
            try:
                alliances = [getattr(c, 'alliance', None) for c in self.players]
                non_null = [a for a in alliances if a not in [None, 'None']]
                self.world.alliances_locked = bool(non_null and (len(set(non_null)) < len(non_null)))
            except Exception:
                self.world.alliances_locked = False
            # 在进入界面前给出条约提示
            try:
                if getattr(self.world, "treaty_until_time", 0) > 0:
                    minutes = self.world.treaty_until_time // 60000
                    for p in self.world.players:
                        if p.is_local_human():
                            # 使用消息常量 + 数字编码 + MINUTES，避免读出tts里其它词条
                            p.push("msg", encode_msg(mp.TREATY + nb2msg(minutes) + mp.MINUTES + mp.TREATY_ACTIVE))
                    # 安排条约结束提示
                    def _treaty_end_announce():
                        from . import msgparts as mp
                        for p in self.world.players:
                            if p.is_local_human():
                                p.push("msg", encode_msg(mp.TREATY_END))
                    self.world.schedule_after(self.world.treaty_until_time, _treaty_end_announce)

                    # 安排条约剩余时间提示（30s/20s/10s），以及最后5秒倒计时
                    def _announce_remaining(seconds):
                        from . import msgparts as mp
                        for p in self.world.players:
                            if p.is_local_human():
                                # 非阻塞：通过msg发送，不用sequence
                                p.push("msg", encode_msg(mp.TREATY + nb2msg(seconds) + mp.SECONDS))

                    # 30/20/10秒提示
                    for _s in (30, 20, 10):
                        _delay = self.world.treaty_until_time - _s * 1000
                        if _delay > 0:
                            self.world.schedule_after(
                                _delay,
                                (lambda s=_s: (lambda: _announce_remaining(s)))()
                            )

                    # 最后5秒倒计时（5,4,3,2,1）
                    for _s in (5, 4, 3, 2, 1):
                        _delay = self.world.treaty_until_time - _s * 1000
                        if _delay > 0:
                            def _countdown_fn(val=_s):
                                for p in self.world.players:
                                    if p.is_local_human():
                                        p.push("msg", encode_msg(nb2msg(val)))
                            self.world.schedule_after(_delay, _countdown_fn)
            except Exception:
                pass
            self.interface.run_game(self)

        if self.record_replay:
            self._replay_file.close()

    def pre_run(self):
        if self.world.intro:
            # 导入sound模块以便停止音乐
            from soundrts.lib import sound
            
            # 完全停止背景音乐（菜单音乐）
            sound.stop_music()
            
            # 播放介绍序列
            play_sequence(self.world.intro)
            
            # intro结束后不恢复音乐，让后续的游戏音乐系统来处理

    def post_run(self):
        # 首先检查胜利或失败状态并播放相应音乐
        from soundrts.lib import sound
        
        player = self.scoring_player()
        if player is not None:
            if self.scoring_victory():
                # 玩家胜利，播放胜利音乐
                sound.play_victory_sound(self.world.map_victory_sound)
            else:
                # 玩家失败，播放失败音乐
                sound.play_defeat_sound(self.world.map_defeat_sound)
        
        # 显示统计信息
        self.say_score()
        self._say_achievements()
        Upgrade.reset()

    def _say_achievements(self):
        if self.is_campaign_session():
            return
        try:
            from .achievements import process_game_end_achievements
            from .lib import game_tts

            player = self.scoring_player()
            if player is None:
                return
            for msg in process_game_end_achievements(self, player):
                # End-of-game summary → primary / screen reader, not secondary.
                voice.important(msg, tts_channel=game_tts.PRIMARY)
            voice.flush()
        except Exception:
            pass

    def say_score(self):
        if self.is_campaign_session():
            voice.flush()
            return
        from .lib import game_tts

        player = self.scoring_player()
        if player is not None and hasattr(player, "stats"):
            for msg in player.stats.score_msgs(
                effective_victory=self.scoring_victory(),
                scored_enemy_ids=self.scored_enemy_ids(),
            ):
                # Post-match stats must use primary (SR owns primary when active).
                voice.important(msg, tts_channel=game_tts.PRIMARY)
        elif (
            hasattr(self.local_client, "player")
            and self.local_client.player
            and getattr(self.local_client.player, "is_spectator", False)
        ):
            voice.important(mp.SPECTATING_FINISHED, tts_channel=game_tts.PRIMARY)
        voice.flush()


class _MultiplayerGame(_Game):

    default_triggers = [
        ("players", ["no_enemy_player_left"], ["victory"]),
        ("players", ["no_building_left"], ["defeat"]),
        ("computers", ["no_unit_left"], ["defeat"]),
    ]
    must_apply_equivalent_type = True


class MultiplayerGame(_MultiplayerGame):

    game_type_name = "multiplayer"

    def _clients(self, players, local_login, main_server):
        clients = []
        for login, a, f in players:
            if login.startswith("ai_"):
                level = login[3:]
                if level == "coop":
                    level = "aggressive"
                c = DummyClient(level)
            else:
                if login != local_login:
                    c = RemoteClient(login)
                else:
                    c = Coordinator(local_login, main_server, self)
                    self.local_client = c
            c.alliance = a
            c.faction = f
            clients.append(c)
        return clients

    @property
    def humans(self):
        return [c for c in self.players if c.__class__ != DummyClient]

    def __init__(self, map, players, local_login, main_server, seed, speed):
        self.map = map
        self.players = self._clients(players, local_login, main_server)
        self.seed = seed
        self.speed = speed
        self.main_server = main_server
        if len(self.humans) > 1:
            self.allow_cheatmode = False

    def run(self):
        _MultiplayerGame.run(self, speed=self.speed)

    def _countdown(self):
        voice.important(mp.THE_GAME_WILL_START)
        for n in [5, 4, 3, 2, 1, 0]:
            voice.item(nb2msg(n))
            time.sleep(1)
        pygame.event.clear(KEYDOWN)

    def pre_run(self):
        # 合作战役：像单人战役那样先播放关卡开场过场（world.intro），让所有玩家
        # 一起进入剧情。pre_run 在 lockstep 主循环之前执行、是各客户端本地阻塞调用，
        # 不影响同步（开打后靠回合 orders 自动对齐）。
        if getattr(self, "is_coop_campaign", False) and getattr(self.world, "intro", None):
            from soundrts.lib import sound
            sound.stop_music()
            play_sequence(self.world.intro)
        if len(self.humans) > 1:
            send_platform_version_to_metaserver(self.map.name, len(self.humans))
            self._countdown()

    def post_run(self):
        # 首先播放胜利/失败音效并显示统计信息
        _Game.post_run(self)
        
        self.main_server.write_line("quit_game")
        # say score only after quit_game to avoid blocking the main server
        # 注意：由于_Game.post_run()已经调用了say_score()，这里不需要再次调用
        voice.menu(mp.MENU + mp.MAKE_A_SELECTION)
        # (long enough to allow history navigation)

        # 如果是合作战役并且胜利，更新合作战役进度书签（与单人 chapter 独立）
        try:
            scoring = self.scoring_player()
            if (
                getattr(self, "is_coop_campaign", False)
                and scoring is not None
                and self.scoring_victory()
            ):
                campaign_name = getattr(self, "coop_campaign_name", None)
                chapter_num = getattr(self, "coop_chapter", None)
                if campaign_name is not None and chapter_num is not None:
                    campaign = res.find_campaign(campaign_name)
                    if campaign:
                        try:
                            campaign.unlock_next_coop(campaign.chapter(int(chapter_num)))
                        except Exception:
                            pass
        except Exception:
            pass


def _list_save_slot_paths(saves_dir=None):
    """返回指定（默认：当前 mod 专属）存档目录中所有存档文件的绝对路径，按修改时间从新到旧排序。"""
    if saves_dir is None:
        saves_dir = current_saves_dir()
    try:
        names = os.listdir(saves_dir)
    except OSError:
        return []
    paths = [os.path.join(saves_dir, n) for n in names if n.startswith("save_")]
    paths = [p for p in paths if os.path.isfile(p)]
    paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return paths


def _prune_save_slots(saves_dir=None):
    """如果当前 mod 的存档数量超过 MAX_SAVE_SLOTS，删除最旧的存档。"""
    paths = _list_save_slot_paths(saves_dir)
    if len(paths) > MAX_SAVE_SLOTS:
        for p in paths[MAX_SAVE_SLOTS:]:
            try:
                os.remove(p)
            except OSError:
                warning("无法删除旧存档：%s", p)


def _new_save_slot_path():
    """在当前 mod 的存档目录中生成一个新的存档槽路径。"""
    saves_dir = current_saves_dir()
    ts = int(time.time())
    base = os.path.join(saves_dir, "save_%d" % ts)
    path = base
    counter = 1
    while os.path.exists(path):
        path = "%s_%d" % (base, counter)
        counter += 1
    return path


class _Savable:
    def __getstate__(self):
        odict = self.__dict__.copy()
        odict.pop("_replay_file", None)
        odict.pop("interface", None)
        return odict

    def __setstate__(self, state):
        from .save_pickle import link_game_clients_after_load

        self.__dict__.update(state)
        link_game_clients_after_load(self)

    def _save_world_square_count(self):
        world = getattr(self, "world", None)
        squares = getattr(world, "squares", None) if world is not None else None
        return len(squares) if squares is not None else 0

    def _check_save_size(self):
        """保留钩子供测试/日志; 大地图改由 cloudpickle_dump_game 处理."""
        return self._save_world_square_count()

    def _write_save_to(self, path):
        """将当前游戏序列化写入指定路径 (原子写入: tmp -> rename).

        Note: cloudpickle 在大乱斗 (14+ AI, 500+ units) 下走 game world 时,
        某些对象引用链 (例: ``creature.last_attacker -> other.last_attacker -> ...``,
        ``action.target -> action.target -> ...``, Square 邻居链 etc.) 可能
        超过 CPython 默认 1000 深度递归限制. 这里临时把限制拉高到 20000,
        save 完恢复. cloudpickle 的 memoization 处理实际循环引用, 高 limit
        只是给合法长链留余量, 不会引入无限递归风险.

        原子写入策略: 先写到 ``path + ".tmp"``, 全部成功后 rename 到目标路径.
        若中途异常 (RecursionError / IOError / KeyboardInterrupt), 立刻删除
        tmp 文件并把异常抛出. 这样目标 path 要么完全不存在, 要么是个合法
        save, 不会产生只有 header / 截断 pickle 的孤儿文件 (历史 bug:
        ``EOFError: Ran out of input`` 来自这类孤儿).

        极大世界: ``save_pickle`` 在 ``__getstate__`` 里去掉 ``World.g`` / 邻居缓存等
        可重建结构, 避免 cloudpickle 递归过深.
        """
        square_count = self._save_world_square_count()
        tmp_path = path + ".tmp"
        # 确保目录存在 (新装机第一次存档场景)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError:
            pass
        try:
            f = open(tmp_path, "wb")
            try:
                i = stats.Stats(None, None)._get_weak_user_id()
                f.write(("%s\n" % i).encode(encoding="ascii"))
                self._rules = rules
                self._ai = definitions._ai
                self._style = style
                # 持久化全局升级成本效果，避免读档后丢失（如 dsc 的 cost/time/population 修正）
                self._global_cost_effects = Upgrade._global_cost_effects
                if self.record_replay:
                    self._replay_file.flush()
                    os.fsync(self._replay_file.fileno())  # just to be sure
                    self._replay_file_content = open(
                        self._replay_file.name, encoding="utf-8"
                    ).read()
                try:
                    cloudpickle_dump_game(self, f, square_count=square_count)
                except Exception as exc:
                    raise SaveTooLargeError(square_count) from exc
                f.flush()
                try:
                    os.fsync(f.fileno())
                except (OSError, AttributeError):
                    pass
            finally:
                f.close()
            # 写入成功 → 原子替换. Windows 下 os.replace 可覆盖已有文件.
            os.replace(tmp_path, path)
        except BaseException:
            # 任何失败 (RecursionError, IOError, KeyboardInterrupt etc.):
            # 清理 tmp, 让 path 保持原状 (不存在或上次正常的版本).
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

    def save(self):
        """玩家手动保存：新建一个存档槽（超过上限则覆盖最旧的）。"""
        path = _new_save_slot_path()
        self._write_save_to(path)
        _prune_save_slots()

    def save_resume(self):
        """玩家中途退出时自动保存，用于"继续未完成的游戏"。

        会写入当前 mod 专属的续玩存档路径，从而做到 mod 之间互不影响。
        """
        self._write_save_to(current_resume_save_path())

    def _ensure_interface_for_restore(self):
        """续玩/读档：interface 不写入 pickle，此处重建。"""
        if getattr(self, "interface", None) is not None:
            return
        self._pin_scoring_player()
        speed = getattr(config, "speed", None)
        self.interface = clientgame.GameInterface(self.local_client, speed=speed)
        self.interface.auto = getattr(self, "auto", None)

    def run_on(self):
        if self.record_replay:
            # 同样写入当前 mod 专属的回放目录
            n = _Game._next_replay_number()
            self._replay_file = open(
                os.path.join(current_replays_dir(), "replay%d_%s.txt" % (n, int(time.time()))),
                "w",
                encoding="utf-8",
            )
            self._replay_file.write(self._replay_file_content)
        rules.copy(self._rules)
        definitions._ai = self._ai
        style.copy(self._style)
        # 恢复全局升级成本效果（如果存档中存在），确保读档后各单位仍按科技生效
        try:
            from .worldupgrade import Upgrade as _Upg
            _Upg._global_cost_effects = getattr(self, "_global_cost_effects", {})
        except Exception:
            pass
        update_orders_list()  # when style has changed
        self._ensure_interface_for_restore()
        self.interface.run_game(self, new=False)
        if self.record_replay:
            self._replay_file.close()


class TrainingGame(_MultiplayerGame, _Savable):

    game_type_name = "training"

    def __init__(self, map, players, factions, alliances):
        self.map = map
        self.seed = random.randint(0, 10000)
        self.local_client = DirectClient(config.login, self)
        self.players = [self.local_client] + [DummyClient(x) for x in players[1:]]
        for p, f, a in zip(self.players, factions, alliances):
            p.faction = f
            p.alliance = a


class MissionGame(_Game, _Savable):

    game_type_name = "mission"
    _has_victory = False

    def __init__(self, chapter):
        self.chapter = chapter
        self.map = chapter.map
        self.seed = random.randint(0, 10000)
        self.local_client = DirectClient(config.login, self)
        self.players = [self.local_client]

    def _replay_write_map(self):
        self.replay_write(self.chapter.campaign.name)
        self.replay_write(str(self.chapter.number))

    def pre_run(self):
        if self.world.intro:
            # 导入sound模块以便停止音乐
            from soundrts.lib import sound
            
            # 完全停止背景音乐（菜单音乐）
            sound.stop_music()
            
            # 播放介绍序列
            play_sequence(self.world.intro)
            
            # intro结束后不恢复音乐，让后续的游戏音乐系统来处理

    def post_run(self):
        _Game.post_run(self)
        scoring = self.scoring_player()
        self._has_victory = bool(scoring is not None and self.scoring_victory())
        from .campaign_hero import save_hero_after_victory

        save_hero_after_victory(self)

    def has_victory(self):
        return self._has_victory

    def run_on(self):
        try:
            res.set_campaign(self.chapter.campaign)
            res.set_map(self.map)
            _Savable.run_on(self)
            self.chapter.run_next_step(self)
        finally:
            res.set_map()
            res.set_campaign()


class ReplayGame(_Game):

    game_type_name = "replay"  # probably useless (or maybe for stats)
    record_replay = False

    def __init__(self, replay: str) -> None:
        self._file = open(replay, encoding="utf-8")
        game_type_name = self.replay_read()
        if game_type_name in ("multiplayer", "training"):
            self.default_triggers = _MultiplayerGame.default_triggers
            self.must_apply_equivalent_type = True
        game_name = self.replay_read()
        voice.alert([game_name])
        version = self.replay_read()
        mods = self.replay_read()
        res.set_mods(mods)
        _compatibility_version = self.replay_read()
        if _compatibility_version != compatibility_version():
            voice.alert(mp.BEEP + mp.VERSION_ERROR)
            warning(
                "Version mismatch. Version should be: %s. Mods should be: %s.",
                version,
                mods,
            )
        self._load_chapter_or_unpack_map(game_type_name)
        players = self.replay_read().split()
        alliances = self.replay_read().split()
        factions = self.replay_read().split()
        # seed 行可能为 "<seed>" 或 "<seed> <enemy_hp%> <enemy_damage%>"（合作战役难度）
        seed_parts = self.replay_read().split()
        self.seed = int(seed_parts[0])
        if len(seed_parts) >= 3:
            self.enemy_hp_factor = int(seed_parts[1])
            self.enemy_damage_factor = int(seed_parts[2])
        self.local_client = ReplayClient(players[0], self)
        self.players = [self.local_client]
        _replay_ai_types = {
            "beginner",
            "intermediate",
            "advanced",
            "expert",
            "nightmare",
            "easy",
            "aggressive",
            "ai2",
            "timers",
        }
        for x in players[1:]:
            if x.startswith("ai_"):
                x = x[3:]
            if x in _replay_ai_types:
                self.players += [DummyClient(x)]
            else:
                self.players += [RemoteClient(x)]
        for p, a, f in zip(self.players, alliances, factions):
            p.alliance = a
            p.faction = f

    def _load_chapter_or_unpack_map(self, game_type_name):
        campaign_name_or_map_digest = self.replay_read()
        if game_type_name == "mission" and "***" not in campaign_name_or_map_digest:
            campaign = res.find_campaign(campaign_name_or_map_digest)
            res.set_campaign(campaign)
            chapter = campaign.chapter(int(self.replay_read()))
            self.map = chapter.map
        else:
            self.map = res.find_multiplayer_map(campaign_name_or_map_digest)

    def replay_read(self):
        s = self._file.readline()
        if s and s.endswith("\n"):
            s = s[:-1]
        return s

    def pre_run(self):
        voice.info(mp.OBSERVE_ANOTHER_PLAYER_EXPLANATION)
        voice.flush()

    def post_run(self):
        super().post_run()
        res.set_map()
        res.set_campaign()


class SpectatorGame(_MultiplayerGame):
    """旁观者游戏类 - 用于旁观正在进行的多人游戏
    
    观战者完全独立于游戏玩家系统，不占用玩家槽位
    """
    
    game_type_name = "spectator"
    record_replay = False
    allow_cheatmode = True  # 旁观者可以看到全部内容
    # 标记本会话为旁观会话：Coordinator 据此不向服务器发送 orders/timeout，
    # 界面据此启用追帧快进与快进静音。
    is_spectator_session = True

    def __init__(self, map_name, players, main_server, speed, seed=0, treaty_minutes=0):
        # 根据地图名称查找地图
        self.map = None
        for m in res.multiplayer_maps():
            if map_name in m.name:
                self.map = m
                break
        
        if not self.map:
            # 如果找不到地图，使用第一个可用地图作为默认
            self.map = res.multiplayer_maps()[0]
        
        # 必须使用与真实对局相同的种子，否则世界生成（随机阵营/起始位置/地形等）
        # 就会与对局分叉，导致看到的根本不是同一局游戏。
        self.seed = int(seed)
        self.treaty_minutes = int(treaty_minutes) if treaty_minutes else 0
        self.speed = speed
        self.main_server = main_server
        
        # 创建旁观者客户端（使用Coordinator作为基础）
        self.local_client = Coordinator(main_server.login, main_server, self)
        
        # 创建实际游戏玩家列表（观战者不包含在内）
        self.players = []  # 只包含实际游戏玩家，不包含观战者
        for login, alliance, faction in players:
            if login.startswith("ai_"):
                c = DummyClient(login[3:])
            else:
                c = RemoteClient(login)
            c.alliance = alliance
            c.faction = faction
            self.players.append(c)
        
        # 观战者单独存储，不占用游戏槽位
        self.spectator_client = self.local_client

    @property
    def humans(self):
        """返回需要路由网络 orders 的真实人类客户端。

        历史 bug：这里曾返回 []，导致 Coordinator 的 get_client_by_login 永远
        找不到玩家、把所有人类指令都丢弃，旁观者只能看到一动不动的开局。
        正确做法与 MultiplayerGame 一致：返回 self.players 里的非 AI 客户端
        （AI 由本地世界确定性模拟，不在网络 orders 中）。旁观者自己的
        local_client 不在 self.players 内，天然被排除。"""
        return [c for c in self.players if c.__class__ != DummyClient]

    def run(self, speed=config.speed):
        if self.record_replay:
            self.create_replay()

        self.world = World(self._world_default_triggers(), self.seed)

        # 与真实对局保持一致的世界级设置，否则重放历史 orders 会分叉：
        # treaty_until_time 会门控条约期内的战斗/移动，alliances_locked 会
        # 门控结盟类指令的处理。两者都直接影响 world.random 的消耗路径。
        treaty_minutes = int(getattr(self, "treaty_minutes", 0) or 0)
        if treaty_minutes > 0:
            self.world.treaty_until_time = treaty_minutes * 60 * 1000
        else:
            self.world.treaty_until_time = 0

        # 合作战役难度：旁观世界必须与对局用相同的敌人强度百分比，否则不同步。
        self.world.enemy_hp_factor = int(getattr(self, "enemy_hp_factor", 100) or 100)
        self.world.enemy_damage_factor = int(getattr(self, "enemy_damage_factor", 100) or 100)

        try:
            self.world.load_and_build_map(self.map)
        except MapError as msg:
            msg = "map error: %s" % msg
            warning(msg)
            voice.alert(mp.BEEP + [msg])
        else:
            # 为实际游戏玩家分配地图位置和创建玩家对象
            self.world.populate_map(self.players, equivalents=self.must_apply_equivalent_type)
            self.nb_human_players = self.world.current_nb_human_players()

            # 与 _Game.run 一致地推导联盟锁定状态
            try:
                alliances = [getattr(c, 'alliance', None) for c in self.players]
                non_null = [a for a in alliances if a not in [None, 'None']]
                self.world.alliances_locked = bool(
                    non_null and (len(set(non_null)) < len(non_null))
                )
            except Exception:
                self.world.alliances_locked = False
            
            # 为观战者创建独立的玩家对象（在 populate_map 之后，确保不扰乱
            # 真实玩家创建期间的随机数消耗）
            self._create_spectator_player()
            
            self.interface = clientgame.GameInterface(self.local_client, speed=speed)
            self.interface.auto = self.auto
            self.interface.run_game(self)

        if self.record_replay:
            self._replay_file.close()

    def _create_spectator_player(self):
        """为观战者创建玩家对象，添加到世界中但不计入游戏玩家。

        确定性要点：旁观玩家是真实对局里不存在的"额外玩家"，创建与更新它都
        绝不能消耗 world.random，否则随机数流就会相对真实对局错位、导致全程
        不同步。为此：
          - 创建前把客户端 faction 设成一个具体阵营（非 "random_faction"），
            避免 Player.__init__ 里的 world.random.choice；
          - 创建前把 neutral 置 True，避免占用 player number；
          - 配合 Player.update/slow_update 对 _is_pure_spectator 的特判
            （只跑感知、不跑 AI/触发器），保证模拟期间零随机消耗。
        """
        # 选一个确定的阵营，避免 random_faction 触发的随机抽取
        try:
            fixed_faction = rules.factions[0] if rules.factions else "human_faction"
        except Exception:
            fixed_faction = "human_faction"
        self.spectator_client.faction = fixed_faction
        self.spectator_client.neutral = True

        # 使用标准的 create_player 方法，让观战者成为世界中的玩家（能浏览地图）
        self.spectator_client.create_player(self.world)
        
        # 设置观战者的特殊属性
        player = self.spectator_client.player
        player.is_spectator = True
        player.neutral = True
        player.cheatmode = True  # 观战者可以看到整个地图
        player._is_pure_spectator = True  # 确保观战者不会获得任何单位
        player.observer_if_defeated = True
        
        # 观战者是世界中的玩家（能浏览地图），但标记为观战者以排除在游戏逻辑外
        warning(f"Created spectator player. Total world players: {len(self.world.players)}")
        warning(f"Game players only: {len([p for p in self.world.players if not getattr(p, '_is_pure_spectator', False)])}")

    def pre_run(self):
        voice.info(mp.YOU_ARE_SPECTATING)
        voice.flush()

    def post_run(self):
        # 旁观结束，发送停止旁观命令
        self.main_server.write_line("quit_spectating")
        voice.menu(mp.MENU + mp.MAKE_A_SELECTION)
