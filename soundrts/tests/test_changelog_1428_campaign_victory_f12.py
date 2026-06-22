"""审计：1.4.2.8 — 战役胜负判定 + F12 外交在战役里的屏蔽。

背景（雷诺传第五章 5.txt，含 2 个非中立电脑：1 个纯触发器脚本电脑
``ai_timers`` + 1 个被 ``(ai easy)`` 升格的电脑）暴露出两个 bug：

1. ``Player.victory()`` 边遍历 ``self.world.players`` 边删：
   ``p.defeat()`` 对非观察者（含战役里的电脑）会走到 ``quit_game()`` →
   ``self.world.players.remove(self)``。在**原列表**上遍历时删除当前元素，
   会跳过紧随其后的玩家。于是战役里有 2 个电脑时，完成任务目标触发
   ``victory()`` 只打败了第 1 个电脑，第 2 个被跳过仍在游戏中，
   ``true_playing_players`` 非空 → 游戏不结束，必须再手动消灭第 2 个电脑才胜利。
   修复：遍历 ``self.world.players[:]`` 快照。

2. F12（``select_alliance_candidate`` / 动态结盟）在战役里不应能切到任何目标。
   被 ``(ai easy)`` 升格的电脑 AI_type 不再是 ``"timers"``，于是漏过了
   ``_diplo_players`` 的 ``AI_type != 'timers'`` 过滤，F12 能切到它并把内部
   login ``"ai_timers"`` 读出来。修复：``_diplo_players`` 在
   ``world.is_campaign`` 时直接返回 ``[]``。

测试策略：
- 胜负判定：用 ``Player.__new__`` + stub world/players 复刻"defeat 删自己"的
  列表突变场景，直接调真的 ``Player.victory`` 验证所有非盟友玩家都被击败。
- F12：``_diplo_players`` 在 is_campaign 时返回 []（模块级），并做源码契约检查。
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

# 解开 worldunit 循环导入（与其它 worldplayerbase 测试一致）
import soundrts.worldunit  # noqa: F401

# 用组合后的完整 Player（``victory`` 定义在 TriggersMixin 上）。
from soundrts.worldplayerbase import Player


REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(*path_parts):
    return REPO_ROOT.joinpath(*path_parts).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) victory() 不能因列表突变而跳过玩家
# ---------------------------------------------------------------------------


class _Stats:
    def freeze(self):
        pass


class _StubWorld:
    is_campaign = True

    def __init__(self):
        self.players = []


class _StubPlayer:
    """最小玩家：``is_playing`` 真值由 has_victory/has_been_defeated 决定；
    ``defeat()`` 模拟非观察者（战役电脑）的行为——把自己从 world.players 删掉。"""

    def __init__(self, world, allied_to_winner: bool):
        self.world = world
        self.has_victory = False
        self.has_been_defeated = False
        self.stats = _Stats()
        self._allied_to_winner = allied_to_winner

    @property
    def is_playing(self):
        return not (self.has_victory or self.has_been_defeated)

    def defeat(self, force_quit=False):
        self.has_been_defeated = True
        self.stats.freeze()
        # 模拟 quit_game() 里的 world.players.remove(self)（关键：触发列表突变）
        if self in self.world.players:
            self.world.players.remove(self)


def _make_winner(world) -> Player:
    p = Player.__new__(Player)
    p.world = world
    p.has_victory = False
    p.has_been_defeated = False
    p.stats = _Stats()
    return p


def test_victory_defeats_all_enemies_even_when_defeat_mutates_player_list():
    """复刻第五章场景：1 个人 + 2 个敌方电脑，电脑 defeat() 会把自己从
    world.players 删掉。``victory()`` 必须仍然打败**两个**电脑。"""
    world = _StubWorld()
    winner = _make_winner(world)
    enemy1 = _StubPlayer(world, allied_to_winner=False)
    enemy2 = _StubPlayer(world, allied_to_winner=False)
    world.players = [winner, enemy1, enemy2]

    # winner 的 allied_victory 只有自己
    winner.allied = [winner]

    winner.victory()

    assert winner.has_victory is True
    assert enemy1.has_been_defeated is True, "第 1 个电脑应被击败"
    assert enemy2.has_been_defeated is True, (
        "第 2 个电脑被跳过 = 回归 bug（遍历原列表时被 defeat() 删元素跳过）"
    )


def test_victory_keeps_allies_and_defeats_only_enemies():
    """盟友拿 has_victory，敌人被 defeat；多敌人也不能漏。"""
    world = _StubWorld()
    winner = _make_winner(world)
    ally = _StubPlayer(world, allied_to_winner=True)
    enemy1 = _StubPlayer(world, allied_to_winner=False)
    enemy2 = _StubPlayer(world, allied_to_winner=False)
    world.players = [winner, enemy1, ally, enemy2]
    winner.allied = [winner, ally]

    winner.victory()

    assert winner.has_victory is True
    assert ally.has_victory is True and ally.has_been_defeated is False
    assert enemy1.has_been_defeated is True
    assert enemy2.has_been_defeated is True


def test_victory_iterates_over_player_list_snapshot_source():
    """源码契约：``victory()`` 必须遍历 ``self.world.players[:]`` 快照。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    s = src.index("def victory(self):")
    block = src[s:s + 600]
    assert "self.world.players[:]" in block, (
        "victory() 必须遍历 players 快照，否则 defeat() 删元素会跳过玩家"
    )


# ---------------------------------------------------------------------------
# 2) F12 在战役里不返回任何候选
# ---------------------------------------------------------------------------


class _DiploWorld:
    def __init__(self, is_campaign, players):
        self.is_campaign = is_campaign
        self.players = players


class _DiploPlayer:
    def __init__(self, pid, neutral=False, AI_type="easy"):
        self.id = pid
        self.neutral = neutral
        self.AI_type = AI_type
        self.has_been_defeated = False
        self.has_victory = False


class _DiploInterface:
    def __init__(self, world, me):
        self.world = world
        self.player = me


def _load_diplo_players():
    """导入真正的 ``game_audio._diplo_players``。

    直接 import 会拉起整条 clientgame 链，其中 ``soundrts.options`` 在 import
    时用 ``optparse`` 解析 ``sys.argv``，pytest 的 ``-q`` 等参数会让它报错退出。
    所以临时把 ``sys.argv`` 收窄成单元素（对齐 test_player_start 的做法）。"""
    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.clientgame import game_audio
        return game_audio._diplo_players
    except Exception:
        return None
    finally:
        sys.argv = saved_argv


def test_diplo_players_empty_in_campaign():
    """战役里 F12 候选必须为空——即使存在被 (ai easy) 升格的非 timers 电脑。"""
    _diplo_players = _load_diplo_players()
    if _diplo_players is None:
        pytest.skip("game_audio could not be imported (client stack unavailable)")
    me = _DiploPlayer("1", AI_type="")
    # 一个被升格的电脑（AI_type 'easy'，本来会漏过 timers 过滤）
    enemy = _DiploPlayer("2", AI_type="easy")
    world = _DiploWorld(is_campaign=True, players=[me, enemy])
    interface = _DiploInterface(world, me)

    assert _diplo_players(interface) == []


def test_diplo_players_nonempty_outside_campaign():
    """非战役（多人/对战）里同样的电脑仍是合法 F12 候选，行为不变。"""
    _diplo_players = _load_diplo_players()
    if _diplo_players is None:
        pytest.skip("game_audio could not be imported (client stack unavailable)")
    me = _DiploPlayer("1", AI_type="")
    enemy = _DiploPlayer("2", AI_type="easy")
    world = _DiploWorld(is_campaign=False, players=[me, enemy])
    interface = _DiploInterface(world, me)

    result = _diplo_players(interface)
    assert enemy in result


def test_diplo_players_campaign_guard_source():
    """源码契约：``_diplo_players`` 必须在 ``is_campaign`` 时短路返回 []。"""
    src = _source("soundrts", "clientgame", "game_audio.py")
    s = src.index("def _diplo_players(interface):")
    block = src[s:s + 900]
    assert "is_campaign" in block
    assert "return []" in block


# ---------------------------------------------------------------------------
# 3) 战役里所有电脑（含被 (ai easy) 升格的）都算 NPC：
#    - is_campaign_npc 判据
#    - defeat()/quit_game() 不播报 NPC 被击败/退出游戏
# ---------------------------------------------------------------------------


class _NpcWorld:
    def __init__(self, is_campaign):
        self.is_campaign = is_campaign


def _make_player_with_ai(world, ai_type, is_human):
    """构造一个最小 Player：注入 ``is_campaign_npc`` property 实际访问的字段。"""
    p = Player.__new__(Player)
    p.world = world
    p.AI_type = ai_type
    # is_human 是类属性（Player=False / Human=True），这里显式覆盖以模拟两种玩家。
    object.__setattr__(p, "is_human", is_human)
    return p


def test_is_campaign_npc_true_for_upgraded_campaign_computer():
    """战役里被 (ai easy) 升格的电脑（AI_type != 'timers'）仍是 NPC。"""
    world = _NpcWorld(is_campaign=True)
    upgraded = _make_player_with_ai(world, ai_type="easy", is_human=False)
    timers = _make_player_with_ai(world, ai_type="timers", is_human=False)
    assert upgraded.is_campaign_npc is True
    assert timers.is_campaign_npc is True


def test_is_campaign_npc_false_for_human_in_campaign():
    """战役里的人类玩家不是 NPC。"""
    world = _NpcWorld(is_campaign=True)
    human = _make_player_with_ai(world, ai_type="", is_human=True)
    assert human.is_campaign_npc is False


def test_is_campaign_npc_false_outside_campaign():
    """非战役（多人/对战）里的电脑不是 NPC——名字/被击败播报照常。"""
    world = _NpcWorld(is_campaign=False)
    computer = _make_player_with_ai(world, ai_type="easy", is_human=False)
    assert computer.is_campaign_npc is False


# ---------------------------------------------------------------------------
# is_script_npc：用于"显示身份"（实体 title、切换视角），覆盖范围比
# is_campaign_npc 更广——非战役地图（td2）里的 timers 脚本 AI 也算。
# ---------------------------------------------------------------------------


def test_is_script_npc_true_for_timers_outside_campaign():
    """非战役地图（如 td2）里的 timers 脚本 AI 在显示身份时算 NPC。

    这是 “td2 按 Ctrl+Shift+F4 切视角误读 ai_timers / 中立 1” 的回归点。"""
    world = _NpcWorld(is_campaign=False)
    timers = _make_player_with_ai(world, ai_type="timers", is_human=False)
    assert timers.is_script_npc is True
    assert timers.is_campaign_npc is False
    assert timers.broadcasts_defeat_and_quit is False


def test_is_script_npc_true_for_upgraded_campaign_computer():
    """战役里被 (ai easy) 升格的电脑（AI_type != 'timers'）显示身份仍是 NPC。"""
    world = _NpcWorld(is_campaign=True)
    upgraded = _make_player_with_ai(world, ai_type="easy", is_human=False)
    assert upgraded.is_script_npc is True


def test_is_script_npc_false_for_real_opponent_outside_campaign():
    """非战役里被升格的真人对手 AI（AI_type != 'timers'）不算 NPC，照读名字。"""
    world = _NpcWorld(is_campaign=False)
    computer = _make_player_with_ai(world, ai_type="easy", is_human=False)
    assert computer.is_script_npc is False


def test_is_script_npc_false_for_human():
    world = _NpcWorld(is_campaign=False)
    human = _make_player_with_ai(world, ai_type="", is_human=True)
    assert human.is_script_npc is False


class _BroadcastWorld:
    def __init__(self, is_campaign, players):
        self.is_campaign = is_campaign
        self.players = players
        self.ex_players = []

    def true_players(self):
        return [p for p in self.players if not getattr(p, "neutral", False)]

    @property
    def true_playing_players(self):
        return [p for p in self.true_players() if p.is_playing]

    @property
    def match_participating_players(self):
        return [p for p in self.true_playing_players if p.broadcasts_defeat_and_quit]

    @property
    def at_least_two_camps(self):
        return False


class _FakeClient:
    name = ["computer_x"]


def _make_broadcast_player(world, ai_type, is_human, neutral=False):
    p = Player.__new__(Player)
    p.world = world
    p.AI_type = ai_type
    object.__setattr__(p, "is_human", is_human)
    p.neutral = neutral
    p.has_been_defeated = False
    p.units = []
    p.stats = _Stats()
    p.client = _FakeClient()
    p._broadcasts = []

    def _record(msg, exclude=None):
        p._broadcasts.append(msg)

    p.broadcast_to_others_only = _record
    p.push = lambda *a, **k: None
    # 让 defeat() 末尾的胜利检查变成 no-op
    p._check_victory_conditions_after_player_change = lambda: None
    return p


def test_defeat_does_not_broadcast_for_upgraded_campaign_computer():
    """战役里被升格的电脑被击败时不应播报 "ai_timers 被击败"。"""
    upgraded = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=True, players=[upgraded])
    upgraded.world = world
    # 隔离：避免 defeat() 末尾的 quit_game() 二次播报，专测被击败播报分支。
    upgraded.quit_game = lambda *a, **k: None

    upgraded.defeat()

    assert upgraded._broadcasts == [], "战役电脑被击败不应播报"


def test_defeat_still_broadcasts_for_non_campaign_computer():
    """非战役里邀请的电脑对手被击败仍然正常播报（行为不变）。"""
    computer = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[computer])
    computer.world = world
    computer.quit_game = lambda *a, **k: None

    computer.defeat()

    assert len(computer._broadcasts) == 1, "非战役电脑被击败应照常播报"


def test_defeat_does_not_broadcast_for_map_timers_npc():
    """多人地图上的 computer_only（timers）被连带击败时不应播报。"""
    npc = _make_broadcast_player(None, ai_type="timers", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[npc])
    npc.world = world
    npc.quit_game = lambda *a, **k: None

    npc.defeat()

    assert npc._broadcasts == []


def test_campaign_human_defeat_quits_when_other_players_remain():
    """战役人类被 (defeat) 击败时，场上仍有电脑也应 quit_game。

    否则 observer_if_defeated 分支只播音效不退出（第25章首领阵亡后卡住的 bug）。"""
    human = _make_broadcast_player(None, ai_type="", is_human=True)
    human.observer_if_defeated = True
    enemy = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=True, players=[human, enemy])
    human.world = world
    enemy.world = world

    quit_calls = []
    human.quit_game = lambda *a, **k: quit_calls.append(True)
    human.send_voice_important = lambda msg: None

    human.defeat()

    assert quit_calls == [True], "战役人类失败应退出游戏，不能留在旁观态"


def test_skirmish_human_defeat_quits_when_ai_opponent_remains():
    """非战役单机：人类被 AI 击败后应退出并结算，不能旁观 AI 继续打。

    回归：随机地图探索遗迹等模式，建筑全毁触发 (defeat) 后只剩邀请的
    电脑对手仍在 match_participating_players，旧逻辑会进入旁观态、不显示
    战败统计。"""
    human = _make_broadcast_player(None, ai_type="", is_human=True)
    human.observer_if_defeated = True
    enemy = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[human, enemy])
    human.world = world
    enemy.world = world

    quit_calls = []
    human.quit_game = lambda *a, **k: quit_calls.append(True)
    human.send_voice_important = lambda msg: None

    human.defeat()

    assert quit_calls == [True], "单机对 AI 失败应结束对局，不应旁观"


def test_human_defeat_enters_observer_when_other_human_remains():
    """多人局：一名真人被淘汰后，另一名真人仍在场时应进入旁观。"""
    human1 = _make_broadcast_player(None, ai_type="", is_human=True)
    human1.observer_if_defeated = True
    human2 = _make_broadcast_player(None, ai_type="", is_human=True)
    world = _BroadcastWorld(is_campaign=False, players=[human1, human2])
    human1.world = world
    human2.world = world

    quit_calls = []
    voice_msgs = []
    human1.quit_game = lambda *a, **k: quit_calls.append(True)
    human1.send_voice_important = lambda msg: voice_msgs.append(msg)

    human1.defeat()

    assert quit_calls == [], "仍有其他真人时不应退出"
    assert voice_msgs, "应播报战败/旁观提示"


def test_skirmish_personal_victory_quits_when_ai_opponent_remains():
    """生存模式单机：计时胜利后应退出并结算，不能等 AI 打完才结束。"""
    human = _make_broadcast_player(None, ai_type="", is_human=True)
    enemy = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[human, enemy])
    human.world = world
    enemy.world = world

    quit_calls = []
    human.quit_game = lambda *a, **k: quit_calls.append(True)

    human.lang_personal_victory([])

    assert human.has_victory is True
    assert quit_calls == [True], "单机 personal_victory 应结束对局"


def test_human_defeat_quits_when_only_map_npc_remains():
    """非战役：人类被击败后只剩地图脚本 NPC 时，应退出而非旁观。

    回归：td 等地图有 ai_timers 脚本电脑时，true_playing_players 非空
    导致玩家进入观察者模式、对局与统计不结束。"""
    human = _make_broadcast_player(None, ai_type="", is_human=True)
    human.observer_if_defeated = True
    npc = _make_broadcast_player(None, ai_type="timers", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[human, npc])
    human.world = world
    npc.world = world

    quit_calls = []
    human.quit_game = lambda *a, **k: quit_calls.append(True)
    human.send_voice_important = lambda msg: None

    human.defeat()

    assert quit_calls == [True], "只剩 NPC 时不应旁观，应结束对局"


def test_quit_game_does_not_broadcast_for_upgraded_campaign_computer():
    """战役里被升格的电脑退出游戏时不应播报 "ai_timers 退出了游戏"。"""
    upgraded = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=True, players=[upgraded])
    upgraded.world = world

    upgraded.quit_game()

    assert upgraded._broadcasts == [], "战役电脑退出游戏不应播报"


def test_quit_game_still_broadcasts_for_non_campaign_computer():
    """非战役里邀请的电脑对手退出游戏仍然正常播报（行为不变）。"""
    computer = _make_broadcast_player(None, ai_type="easy", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[computer])
    computer.world = world

    computer.quit_game()

    assert len(computer._broadcasts) == 1, "非战役电脑退出游戏应照常播报"


def test_quit_game_does_not_broadcast_for_map_timers_npc():
    npc = _make_broadcast_player(None, ai_type="timers", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[npc])
    npc.world = world

    npc.quit_game()

    assert npc._broadcasts == []


# ---------------------------------------------------------------------------
# 源码契约：四个 NPC 判定点改用 is_campaign_npc / not is_human
# ---------------------------------------------------------------------------


def test_is_campaign_npc_property_defined():
    src = _source("soundrts", "worldplayerbase", "base.py")
    assert "def is_campaign_npc(self):" in src
    s = src.index("def is_campaign_npc(self):")
    block = src[s:s + 800]
    assert "is_campaign" in block
    assert "not self.is_human" in block


def test_is_script_npc_property_defined():
    """is_script_npc 必须同时覆盖 is_campaign_npc 与 AI_type=='timers'。

    这是显示身份的统一判据；少了任何一支都会回归到读出 "ai_timers" 的 bug。"""
    src = _source("soundrts", "worldplayerbase", "base.py")
    assert "def is_script_npc(self):" in src
    s = src.index("def is_script_npc(self):")
    block = src[s:s + 600]
    assert "is_campaign_npc" in block
    assert '"timers"' in block


def test_defeat_and_quit_use_broadcasts_defeat_and_quit():
    base = _source("soundrts", "worldplayerbase", "base.py")
    triggers = _source("soundrts", "worldplayerbase", "triggers.py")
    assert "broadcasts_defeat_and_quit" in base
    assert "self.broadcasts_defeat_and_quit" in base, "quit_game 应改用 broadcasts_defeat_and_quit"
    assert "self.broadcasts_defeat_and_quit" in triggers, "defeat 应改用 broadcasts_defeat_and_quit"
    # 旧的 timers-only 判据不该再出现在这两个播报分支
    assert "_is_campaign_timer" not in base
    assert "_is_campaign_timer" not in triggers


def test_title_and_change_player_use_is_script_npc():
    """实体 title 与切换视角播报必须走统一的 is_script_npc 判据。

    早先这两处只判 is_campaign_npc，导致非战役地图（td2）里的 timers AI 漏判，
    切视角时读出内部 login "ai_timers" / 中立序号。现统一改用 is_script_npc。"""
    props = _source("soundrts", "clientgameentity", "properties.py")
    res = _source("soundrts", "clientgame", "game_resources.py")
    assert 'getattr(self.player, "is_script_npc", False)' in props
    assert 'getattr(p, "is_script_npc", False)' in res
    # 这两个显示分支不应再各自内联拼 is_campaign_npc / AI_type，判据集中到属性里
    assert 'getattr(self.player, "AI_type", "") == "timers"' not in props
    assert 'getattr(p, "AI_type", "") == "timers"' not in res


def test_say_players_excludes_map_timers_npc():
    """F11 播报玩家列表时不应包含地图脚本 NPC。"""
    from soundrts.clientgame import game_audio

    human = _make_broadcast_player(None, ai_type="", is_human=True)
    npc = _make_broadcast_player(None, ai_type="timers", is_human=False)
    world = _BroadcastWorld(is_campaign=False, players=[human, npc])
    human.world = world
    npc.world = world

    class _Iface:
        pass

    iface = _Iface()
    iface.world = world

    voiced = []
    original = game_audio.voice.item
    try:
        game_audio.voice.item = lambda msg: voiced.append(msg)
        game_audio.cmd_say_players(iface)
    finally:
        game_audio.voice.item = original

    assert voiced, "F11 应播报至少一名玩家"
    flat = sum(voiced, [])
    assert ["NPC"] not in flat and not any(part == "NPC" for part in flat if isinstance(part, str))
    assert human.name[0] in flat or human.name == flat[: len(human.name)]
