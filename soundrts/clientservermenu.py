import time
from typing import List

from . import msgparts as mp
from .clientmedia import play_sequence, voice
from .clientmenu import Menu
from .definitions import ai_invite_label, ai_player_label, get_menu_ai_difficulties, rules, style
from .game import MultiplayerGame
from .lib.log import info, warning
from .lib.msgs import (
    coerce_voice_msg_parts,
    eval_msg_and_volume,
    nb2msg,
    normalize_map_title_for_voice,
)
from .lib.resource import res


def insert_silences(msg):
    result = msg[:1]
    for sound in msg[1:]:
        result += mp.PERIOD + [sound]
    return result


def game_short_status(map_title, clients, minutes):
    clients = clients.split(",")
    players = insert_silences(sum([name(c) for c in clients], []))
    if isinstance(map_title, str):
        title_parts = [map_title]
    else:
        title_parts = list(map_title)
    msg = (
        mp.MULTIPLAYER
        + title_parts
        + mp.PERIOD
        + players
        + mp.PERIOD
        + nb2msg(minutes)
        + mp.MINUTES
    )
    return msg


class _ServerMenu(Menu):
    def __init__(self, server, auto=False, menu_type="main"):
        self.server = server
        self.auto = auto
        Menu.__init__(self, menu_type=menu_type)
        # 初始化返回主菜单的标志
        self.return_to_main_menu = False

    def _process_server_event(self, s):
        e = s.strip().split(" ")
        try:
            cmd = getattr(self, "srv_" + e[0])
        except AttributeError:
            if e[0] in ("all_orders", "pong"):
                info("ignored by ServerMenu: %s", s)
            elif e[0]:
                warning("not recognized by ServerMenu: %s", s)
        else:
            cmd(e[1:])

    def _process_available_server_lines(self):
        while True:
            s = self.server.read_line()
            if s is None:
                return
            self._process_server_event(s)
            if self.end_loop:  # received "quit"
                # stop reading
                return

    def loop(self):
        self.end_loop = False
        while not self.end_loop:
            self._process_available_server_lines()  # to avoid empty menus
            self.step()
            if self.auto:
                if self.auto[0].run(self):
                    del self.auto[0]
            voice.update()  # for voice.info()
            time.sleep(0.01)

    def push(self, line):
        self.server.write_line(line)

    login = None

    def srv_update_menu(self, unused_args):
        self.update_menu(self.make_menu())

    def srv_quit(self, unused_args):
        voice.flush()
        # 重置战斗状态，停止服务器大厅音乐并播放主菜单音乐
        from soundrts.lib import sound
        sound.in_battle = False
        sound.play_menu_music()
        self.end_loop = True
        # 设置一个标志，表明我们应该直接返回主菜单而不是继续循环
        self.return_to_main_menu = True

    def srv_say(self, args):
        login, msg = args[0], args[1:]
        # 确保消息内容被处理为文本，而不是被解释为声音ID
        # 将每个单词包装为字符串，避免被解释为声音文件名
        text_msg = []
        for word in msg:
            # 如果是纯数字或可能与声音文件名匹配的字符串，确保它被处理为文本
            # 通过添加前缀"文本: "来确保它不会被解释为声音ID
            text_msg.append("文本: " + word)
        
        voice.info([login] + mp.SAYS + text_msg)

    def srv_sequence(self, args):
        play_sequence(args)

    def srv_logged_in(self, args):
        (login,) = args
        if login != self.server.login:
            voice.info([login] + mp.HAS_JUST_LOGGED_IN)

    def srv_logged_out(self, args):
        (login,) = args
        voice.info([login] + mp.HAS_JUST_LOGGED_OUT)

    def srv_msg(self, args):
        voice.info(*eval_msg_and_volume(" ".join(args)))

    def srv_invite_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_invite_computer_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_register_error(self, unused_args):
        voice.info(mp.BEEP)

    def srv_too_many_games(self, unused_args):
        voice.info(mp.TOO_MANY_GAMES)

    def srv_clients(self, args):
        msg = insert_silences(sum([name(c) for c in args], []))
        voice.info(msg)

    def srv_game(self, args):
        minutes = args[-1]
        clients = args[-2]
        map_title = coerce_voice_msg_parts(args[:-2])
        voice.info(game_short_status(map_title, clients, minutes))

    def srv_invitation(self, args):
        admin_login = args[0]
        map_title = coerce_voice_msg_parts(args[1:])
        voice.info([admin_login] + mp.INVITES_YOU + map_title)

    def _players_names(self, players):
        return insert_silences(sum([name(p) for p in players], []))

    def srv_registered(self, args):
        player_login, players = args
        players = players.split(",")
        voice.info(name(player_login) + mp.HAS_JUST_JOINED + self._players_names(players))

    def srv_alliance(self, args):
        player_login, alliance = args
        voice.info(mp.MOVE + name(player_login) + mp.TO_ALLIANCE + nb2msg(alliance))

    def srv_faction(self, args):
        player_login, faction = args
        faction_name = style.get(faction, "title")
        voice.info(name(player_login) + faction_name)


class ServerMenu(_ServerMenu):

    invitations = ()

    def loop(self):
        # 调用父类的loop方法
        super().loop()
        # 不再直接调用main_menu，而是设置返回标志
        # 递归调用main_menu会导致栈溢出问题

    def _get_speed_submenu(self, args):
        n, title, is_public = args

        def go_treaty_menu(speed):
            return (self._get_treaty_submenu, (n, title, is_public, speed))

        def go_random_map_menu(speed):
            return (self._open_random_map_server_menu, (is_public, speed))

        # 定义取消时的操作
        def cancel_and_play_lobby_music():
            # 重置战斗状态，并播放服务器大厅音乐
            from soundrts.lib import sound
            sound.in_battle = False
            sound.play_server_lobby_music()
            return None

        if n == "random":
            Menu(
                title,
                [
                    (mp.SET_SPEED_TO_SLOW, go_random_map_menu("0.5")),
                    (mp.SET_SPEED_TO_NORMAL, go_random_map_menu("1.0")),
                    (mp.SET_SPEED_TO_FAST + nb2msg(2), go_random_map_menu("2.0")),
                    (mp.SET_SPEED_TO_FAST + nb2msg(4), go_random_map_menu("4.0")),
                    (mp.CANCEL, cancel_and_play_lobby_music),
                ],
                default_choice_index=1,
                menu_type="submenu",
            ).run()
            return

        Menu(
            title,
            [
                (mp.SET_SPEED_TO_SLOW, go_treaty_menu("0.5")),
                (mp.SET_SPEED_TO_NORMAL, go_treaty_menu("1.0")),
                (mp.SET_SPEED_TO_FAST + nb2msg(2), go_treaty_menu("2.0")),
                (mp.SET_SPEED_TO_FAST + nb2msg(4), go_treaty_menu("4.0")),
                (mp.CANCEL, cancel_and_play_lobby_music),
            ],
            default_choice_index=1,
            menu_type="submenu",
        ).run()

    def _get_treaty_submenu(self, args):
        n, title, is_public, speed = args

        def create_with_treaty(treaty_min):
            s = f"create {n} {speed} {is_public} {treaty_min}"
            return (self.server.write_line, s)

        def back_to_speed_menu():
            return self._get_speed_submenu((n, title, is_public))

        entries = [
            (mp.TREATY + [":"] + mp.NO_TREATY, create_with_treaty("0")),
            (mp.TREATY + nb2msg(5) + mp.MINUTES, create_with_treaty("5")),
            (mp.TREATY + nb2msg(10) + mp.MINUTES, create_with_treaty("10")),
            (mp.TREATY + nb2msg(15) + mp.MINUTES, create_with_treaty("15")),
            (mp.TREATY + nb2msg(20) + mp.MINUTES, create_with_treaty("20")),
            (mp.CANCEL, back_to_speed_menu),
        ]

        Menu(title, entries, default_choice_index=0, menu_type="submenu").run()

    def _open_random_map_server_menu(self, args):
        is_public, speed = args
        from .randommap_menu import RandomMapMenu

        RandomMapMenu(
            on_ready=None,
            server_mode={
                "write_line": self.server.write_line,
                "speed": speed,
                "is_public": is_public,
            },
        ).run()

    def _get_creation_submenu(self, is_public=""):
        # 设置菜单标题
        if is_public == "public":
            title = mp.START_A_PUBLIC_GAME_ON
        else:
            title = mp.START_A_GAME_ON
            
        # 定义取消时的操作
        def cancel_and_play_lobby_music():
            # 重置战斗状态，并播放服务器大厅音乐
            from soundrts.lib import sound
            sound.in_battle = False
            sound.play_server_lobby_music()
            return None
            
        menu = Menu(title, remember="mapmenu", menu_type="submenu")
        menu.append(mp.RMG_RANDOM_MAP, (self._get_speed_submenu, ("random", title + mp.RMG_RANDOM_MAP, is_public)))
        for n, m in enumerate(self.maps):
            menu.append(m, (self._get_speed_submenu, (n, title + m, is_public)))
        menu.append(mp.CANCEL, cancel_and_play_lobby_music)
        return menu
        
    # 添加新方法，在用户选择菜单项后才播放音乐
    def _on_creation_menu_selected(self, is_public=""):
        # 重置战斗状态，并播放创建游戏菜单音乐
        from soundrts.lib import sound
        sound.in_battle = False
        sound.play_game_creation_music()
        
        # 获取并运行菜单
        menu = self._get_creation_submenu(is_public)
        return menu.run()

    def make_menu(self):
        menu = Menu(menu_type="main")
        for g in self.invitations:
            login = g[1]
            title = normalize_map_title_for_voice(g[2:])
            menu.append(
                mp.ACCEPT_INVITATION_FROM + [login] + title,
                (self.server.write_line, "register %s" % g[0]),
            )
        # 修改这里，使用_on_creation_menu_selected方法替代直接调用_get_creation_submenu
        menu.append(mp.START_A_GAME_ON, (self._on_creation_menu_selected, ()))
        menu.append(mp.START_A_PUBLIC_GAME_ON, (self._on_creation_menu_selected, "public"))
        # 新增：合作战役菜单（使用消息常量以支持多语言）
        menu.append(mp.COOP_CAMPAIGN, self._coop_campaign_menu)
        menu.append(mp.SPECTATE_GAME, self._spectate_games_menu)  # 添加旁观游戏选项
        menu.append(mp.QUIT2, (self.server.write_line, "quit"))
        return menu

    def srv_welcome(self, args):
        self.server.login, server_login = args
        voice.important(
            mp.WELCOME + [self.server.login] + mp.ON_THE_SERVER_OF + [server_login]
        )

    def srv_invitations(self, args):
        self.invitations = [x.split(",") for x in args]

    def srv_maps(self, args):
        self.maps = [x.split(",") for x in args]

    def srv_game_admin_menu(self, args):
        menu = GameAdminMenu(self.server, auto=self.auto, menu_type="submenu")
        try:
            menu._is_coop_campaign = bool(int(args[0])) if args else False
        except (IndexError, ValueError):
            menu._is_coop_campaign = False
        menu.loop()

    def srv_game_guest_menu(self, unused_args):
        GameGuestMenu(self.server, auto=self.auto, menu_type="submenu").loop()

    def _coop_campaign_menu(self):
        """合作战役：选择战役、章节、速度、公开性、条约分钟数，然后发送 create_campaign 命令"""
        # 播放创建游戏菜单音乐
        from soundrts.lib import sound
        sound.in_battle = False
        sound.play_game_creation_music()

        # 只列出 campaign.txt 声明 ``coop_campaign 1`` 的战役。
        campaigns = res.coop_campaigns()
        if not campaigns:
            voice.info(["没有可用合作战役"])
            return None

        # 选择战役
        def _select_campaign():
            m = Menu(mp.SELECT_COOP_CAMPAIGN, menu_type="submenu")
            for c in campaigns:
                m.append(c.title, (lambda _c=c: _select_chapter(_c)))
            m.append(mp.CANCEL, None)
            m.run()

        # 选择章节（按合作战役独立进度：coop_chapter，与单人 chapter 无关）
        def _select_chapter(campaign):
            bookmark = campaign._get_coop_bookmark()
            m = Menu(mp.SELECT_COOP_CHAPTER, menu_type="submenu")
            for ch in campaign.coop_menu_chapters():
                prefix = nb2msg(ch.number) if ch.number > 0 else []
                if ch.number < bookmark:
                    action = (lambda _c=campaign, _ch=ch: _on_coop_chapter_selected(_c, _ch))
                    m.append(prefix + ch.title + mp.MISSION_COMPLETED, action)
                elif ch.number == bookmark:
                    m.append(
                        prefix + ch.title,
                        (lambda _c=campaign, _ch=ch: _on_coop_chapter_selected(_c, _ch)),
                    )
                else:
                    m.append(prefix + mp.MISSION_LOCKED, None)
            m.append(mp.CANCEL, _select_campaign)
            m.run()

        def _on_coop_chapter_selected(campaign, chapter):
            from .campaign import CutSceneChapter

            if isinstance(chapter, CutSceneChapter):
                _run_coop_cutscene(campaign, chapter)
                return
            _select_difficulty(campaign, chapter)

        def _run_coop_cutscene(campaign, chapter):
            prev_mods = res.mods
            coop_campaign_obj = res.apply_campaign_resources(campaign.name)
            try:
                chapter.run_for_coop()
            finally:
                if coop_campaign_obj is not None:
                    res.set_campaign()
                    if coop_campaign_obj.mods is not None and res.mods != prev_mods:
                        res.set_mods(prev_mods)
            _select_chapter(campaign)

        # 选择难度（帝国时代决定版风格：越难敌人越强，且随玩家人数提升）
        def _select_difficulty(campaign, chapter):
            from .coop_difficulty import LEVELS, label

            current = campaign.get_coop_difficulty()
            default_idx = 1
            entries = []
            for i, lvl in enumerate(LEVELS):
                if lvl == current:
                    default_idx = i
                entries.append(
                    (label(lvl), (lambda _l=lvl: _choose_coop_difficulty(campaign, chapter, _l)))
                )
            entries.append((mp.CANCEL, lambda: _select_chapter(campaign)))
            Menu(
                mp.DIFFICULTY,
                entries,
                default_choice_index=default_idx,
                menu_type="submenu",
            ).run()

        def _choose_coop_difficulty(campaign, chapter, difficulty):
            campaign.set_coop_difficulty(difficulty)
            _select_speed(campaign, chapter, difficulty)

        # 选择速度，然后选择私人/公开房间（公开房会出现在大厅邀请列表）
        def _select_speed(campaign, chapter, difficulty):
            title = mp.SPEED

            def _go_visibility(speed):
                return (lambda: _select_visibility(campaign, chapter, speed, difficulty))

            Menu(
                title,
                [
                    (mp.SET_SPEED_TO_SLOW, _go_visibility("0.5")),
                    (mp.SET_SPEED_TO_NORMAL, _go_visibility("1.0")),
                    (mp.SET_SPEED_TO_FAST + nb2msg(2), _go_visibility("2.0")),
                    (mp.SET_SPEED_TO_FAST + nb2msg(4), _go_visibility("4.0")),
                    (mp.CANCEL, lambda: _select_difficulty(campaign, chapter)),
                ],
                default_choice_index=1,
                menu_type="submenu",
            ).run()

        def _select_visibility(campaign, chapter, speed, difficulty):
            Menu(
                mp.SELECT_COOP_ROOM,
                [
                    (
                        mp.COOP_PRIVATE_ROOM,
                        (lambda: _send_create_campaign(
                            (campaign, chapter, speed, "", "0", difficulty)
                        )),
                    ),
                    (
                        mp.COOP_PUBLIC_ROOM,
                        (lambda: _send_create_campaign(
                            (campaign, chapter, speed, "public", "0", difficulty)
                        )),
                    ),
                    (mp.CANCEL, lambda: _select_speed(campaign, chapter, difficulty)),
                ],
                menu_type="submenu",
            ).run()

        # 发送命令
        def _send_create_campaign(args):
            from .coop_difficulty import normalize_level

            # 兼容不同签名
            difficulty = None
            if len(args) == 4:
                campaign, chapter, speed, is_public = args
                treaty = "0"
            elif len(args) == 5:
                campaign, chapter, speed, is_public, treaty = args
            elif len(args) == 6:
                campaign, chapter, speed, is_public, treaty, difficulty = args
            else:
                return None
            name = campaign.name
            n = chapter.number
            is_public = is_public or ""
            cmd = f"create_campaign {name} {n} {speed} {is_public} {treaty}"
            # 难度作为带标记的 token 追加，避免与"战役名可含空格"的宽松解析冲突
            if difficulty:
                cmd += f" difficulty={normalize_level(difficulty)}"
            self.server.write_line(cmd)

        _select_campaign()
        return None

    def _spectate_games_menu(self):
        """显示旁观游戏菜单"""
        # 重置战斗状态，并播放服务器大厅音乐
        from soundrts.lib import sound
        sound.in_battle = False
        sound.play_server_lobby_music()
        
        # 请求服务器发送游戏列表
        self.server.write_line("list_games")
        
        # 创建并显示旁观菜单
        SpectateMenu(self.server, auto=self.auto, menu_type="submenu").loop()

    running_games = []

    def srv_running_games(self, args):
        """接收服务器发送的正在进行的游戏列表"""
        self.running_games = []
        for game_info in args:
            # 解析游戏信息：游戏ID,地图名称,玩家列表,进行时间(分钟)
            parts = game_info.split(",")
            if len(parts) >= 4:
                game_id = parts[0]
                map_name = parts[1]
                players = parts[2] if parts[2] else "无玩家"
                minutes = parts[3]
                self.running_games.append((game_id, map_name, players, minutes))

    def srv_no_running_games(self, unused_args):
        """接收服务器通知：没有正在进行的游戏"""
        self.running_games = []
        voice.info(mp.NO_GAMES_AVAILABLE)

    def srv_spectate_success(self, unused_args):
        """成功开始旁观游戏"""
        voice.info(mp.YOU_ARE_SPECTATING)

    def srv_spectate_error(self, args):
        """旁观游戏失败"""
        voice.info(mp.BEEP)

    def srv_spectator_joined(self, args):
        """旁观者加入通知"""
        login = args[0]
        voice.info([login] + mp.SPECTATOR_JOINED)

    def srv_spectator_left(self, args):
        """旁观者离开通知"""
        login = args[0]
        voice.info([login] + mp.SPECTATOR_LEFT)


_AI_LOGIN_LABELS = {
    "ai_beginner": mp.BEGINNER_COMPUTER,
    "ai_intermediate": mp.INTERMEDIATE_COMPUTER,
    "ai_advanced": mp.ADVANCED_COMPUTER,
    "ai_expert": mp.EXPERT_COMPUTER,
    "ai_nightmare": mp.NIGHTMARE_COMPUTER,
}


def name(login):
    if login == "ai_coop":
        return mp.COOP_AI_PARTNER
    if login.startswith("ai_"):
        return ai_player_label(login[3:])
    return [login]


class _BeforeGameMenu(_ServerMenu):

    registered_players = ()
    _is_coop_campaign = False
    # 合作战役难度：服务器在 start_game 之前用 coop_difficulty 行下发已算定的
    # 敌人强度百分比（含玩家人数缩放）。默认 100 = 标准强度。
    _coop_enemy_hp = 100
    _coop_enemy_damage = 100
    _coop_difficulty = ""

    def srv_coop_difficulty(self, args):
        """接收服务器下发的合作战役难度（敌人 hp% / 伤害% / 等级名）。

        该行总在 start_game 之前到达，由 srv_start_game 读取并配置世界。
        """
        try:
            self._coop_enemy_hp = int(args[0])
            self._coop_enemy_damage = int(args[1])
        except (IndexError, ValueError):
            self._coop_enemy_hp = 100
            self._coop_enemy_damage = 100
        self._coop_difficulty = args[2] if len(args) >= 3 else ""

    def srv_map(self, args: List[str]) -> None:
        # warning: args is split from a stripped string
        self.map = res.unpack_map(" ".join(args).encode(), save=True)
        res.set_map(self.map)
        # 合作战役：地图名形如「战役/章节」时尽早加载战役 tts，避免只播 loc_ch02_* 原文
        res.apply_campaign_from_map_name(getattr(self.map, "name", ""))
        # 强制重新加载规则以确保地图特定规则被应用
        res.load_rules_and_ai()
        # 规范化地图标题：章节号用数值读法，避免命中 tts.txt 的 "1" 等条目
        try:
            self.map.title = normalize_map_title_for_voice(
                getattr(self.map, "title", []),
                getattr(self.map, "name", ""),
            )
        except Exception:
            pass

    def srv_registered_players(self, args):
        self.registered_players = [p.split(",") for p in args]

    def _game_status(self, players):
        msg = nb2msg(len(players)) + mp.PLAYERS_ON + nb2msg(self.map.nb_players_max)
        if len(players) >= self.map.nb_players_min:
            msg += mp.THE_GAME_WILL_START_WHEN_ORGANIZER_IS_READY
        else:
            msg += mp.NOT_ENOUGH_PLAYERS + nb2msg(self.map.nb_players_min)
        msg += mp.PERIOD + self._players_names(players)
        return msg

    def srv_registered(self, args):
        player_login, players = args
        players = players.split(",")
        voice.info(name(player_login) + mp.HAS_JUST_JOINED + self._game_status(players))

    def _add_faction_menu(self, menu, pn, p, pr):
        if len(rules.factions) > 1:
            for r in ["random_faction"] + rules.factions:
                if r != pr:
                    menu.append(
                        name(p) + style.get(r, "title"),
                        (self.server.write_line, f"faction {pn} {r}"),
                    )

    def srv_start_game(self, args):
        # 兼容老参数顺序: players, local_login, seed, speed
        # 新增可选第5-8个参数: 条约分钟数、是否合作、战役名、章节号
        # 注意：servereroom.py 的 notify 一共发 8 个位置参数（不含命令名），
        # 所以判断阈值用 8 而不是 9——历史上写 ``>= 9`` 会让 8 参数的合作战役
        # 走到 ``>= 5`` 分支，导致 ``is_coop`` / ``coop_campaign_name`` /
        # ``coop_chapter`` 在客户端被默默丢弃，再也无法走"通关后解锁下一章"。
        treaty_minutes = 0
        is_coop = 0
        coop_campaign_name = ""
        coop_chapter = ""
        if len(args) >= 8:
            players, local_login, seed, speed, treaty_minutes, is_coop, coop_campaign_name, coop_chapter = args[:8]
        elif len(args) >= 5:
            players, local_login, seed, speed, treaty_minutes = args[:5]
        else:
            players, local_login, seed, speed = args[:4]
        players = [p.split(",") for p in players.split(";")]
        seed = int(seed)
        speed = float(speed)
        game = MultiplayerGame(self.map, players, local_login, self.server, seed, speed)
        # 将条约分钟数传递给游戏会话（由游戏会话配置世界）
        try:
            game.treaty_minutes = int(treaty_minutes)
        except Exception:
            game.treaty_minutes = 0
        # 传递合作战役上下文
        try:
            game.is_coop_campaign = bool(int(is_coop)) if is_coop != "" else False
            game.coop_campaign_name = coop_campaign_name
            game.coop_chapter = int(coop_chapter) if str(coop_chapter).isdigit() else None
        except Exception:
            pass
        # 传递合作战役难度（敌人强度），由 game.run 写入世界，确定性应用到敌方单位
        game.enemy_hp_factor = int(getattr(self, "_coop_enemy_hp", 100) or 100)
        game.enemy_damage_factor = int(getattr(self, "_coop_enemy_damage", 100) or 100)
        game.coop_difficulty = getattr(self, "_coop_difficulty", "") or ""
        game.auto = self.auto

        # 合作战役：像单人战役 Campaign.run 那样加载该战役的资源层
        # （mods + 战役 rules.txt + 战役 ui/tts.txt）。否则：
        #  1) 战役专属单位无法创建 -> "couldn't create an initial unit"；
        #  2) square_name 地名别名（如 loc_ch01_south）不会被翻译（语音读出原始 key）。
        # 确定性：所有客户端加载同一战役的同一份 rules，世界构建一致；
        # tts 仅影响本地语音，不参与模拟，不会引起不同步。
        coop_campaign_obj = None
        prev_mods = res.mods
        if getattr(game, "is_coop_campaign", False) and coop_campaign_name:
            coop_campaign_obj = res.apply_campaign_resources(coop_campaign_name)
        if coop_campaign_obj is None:
            coop_campaign_obj = res.apply_campaign_from_map_name(
                getattr(self.map, "name", "")
            )
        try:
            game.run()
        finally:
            # 游戏结束后还原资源层，避免污染服务器大厅与后续对局
            if coop_campaign_obj is not None:
                res.set_campaign()
                if coop_campaign_obj.mods is not None and res.mods != prev_mods:
                    res.set_mods(prev_mods)
        self.end_loop = True


class GameAdminMenu(_BeforeGameMenu):

    available_players = ()

    def _player_at_alliance(self, alliance):
        for login, pa, pr in self.registered_players:
            if int(pa) == alliance:
                return login, pa, pr
        return None

    def _coop_slot_status_label(self, slot):
        prefix = mp.COOP_PLAYER + nb2msg(slot)
        occupant = self._player_at_alliance(slot)
        if occupant is None:
            return prefix + mp.COOP_SLOT_OPEN
        return prefix + name(occupant[0])

    def _open_coop_slot_menu(self, slot):
        occupant = self._player_at_alliance(slot)

        def _set_ai():
            self.server.write_line(f"set_coop_slot {slot} ai")

        def _set_open():
            self.server.write_line(f"set_coop_slot {slot} open")

        entries = []
        if occupant is None:
            entries.append((mp.COOP_SET_AI_PARTNER, _set_ai))
        elif occupant[0] == "ai_coop":
            entries.append((mp.COOP_SET_OPEN, _set_open))
        entries.append((mp.BACK, None))
        Menu(
            self._coop_slot_status_label(slot),
            entries,
            menu_type="submenu",
        ).run()

    def _add_coop_slot_entries(self, menu):
        """帝国时代决定版式合作槽位：逐位显示空缺/人类/合作 AI 队友。"""
        try:
            max_slots = int(self.map.nb_players_max)
        except Exception:
            max_slots = 1
        for slot in range(2, max_slots + 1):
            menu.append(
                self._coop_slot_status_label(slot),
                (lambda _s=slot: self._open_coop_slot_menu(_s)),
            )

    def _coop_slot_has_ai_partner(self, slot):
        occupant = self._player_at_alliance(slot)
        return occupant is not None and occupant[0] == "ai_coop"

    def _can_invite_coop_partner(self):
        try:
            max_slots = int(self.map.nb_players_max)
        except Exception:
            return False
        for slot in range(2, max_slots + 1):
            occupant = self._player_at_alliance(slot)
            if occupant is None:
                return True
            if self._coop_slot_has_ai_partner(slot):
                return True
        return False

    def _has_open_coop_slot(self):
        try:
            max_slots = int(self.map.nb_players_max)
        except Exception:
            return False
        for slot in range(2, max_slots + 1):
            if self._player_at_alliance(slot) is None:
                return True
        return False

    def make_menu(self):
        menu = Menu(self.map.title, menu_type="submenu")
        if getattr(self, "_is_coop_campaign", False):
            self._add_coop_slot_entries(menu)
            if self._can_invite_coop_partner():
                for p in self.available_players:
                    menu.append(
                        mp.INVITE + [p], (self.server.write_line, "invite %s" % p)
                    )
        elif len(self.registered_players) < self.map.nb_players_max:
            for p in self.available_players:
                menu.append(mp.INVITE + [p], (self.server.write_line, "invite %s" % p))
            for ai_type in get_menu_ai_difficulties():
                menu.append(
                    ai_invite_label(ai_type),
                    (self.server.write_line, "invite_ai %s" % ai_type),
                )
        if len(self.registered_players) >= self.map.nb_players_min:
            menu.append(mp.START, (self.server.write_line, "start"))
        if not getattr(self, "_is_coop_campaign", False):
            for pn, (login, pa, pr) in enumerate(self.registered_players):
                pa = int(pa)
                for a in range(1, len(self.registered_players) + 1):
                    if a != pa:
                        menu.append(
                            mp.MOVE + name(login) + mp.TO_ALLIANCE + nb2msg(a),
                            (self.server.write_line, f"move_to_alliance {pn} {a}"),
                        )
                if login == self.server.login or login.startswith("ai_"):
                    self._add_faction_menu(menu, pn, login, pr)
        else:
            for pn, (login, pa, pr) in enumerate(self.registered_players):
                if login == self.server.login:
                    self._add_faction_menu(menu, pn, login, pr)
        menu.append(
            mp.CANCEL + mp.CANCEL_THIS_GAME, (self.server.write_line, "cancel_game")
        )
        return menu

    def srv_available_players(self, args):
        self.available_players = args


class GameGuestMenu(_BeforeGameMenu):
    def _get_player(self):
        for pn, (login, pa, pr) in enumerate(self.registered_players):
            if login == self.server.login:
                return pn, login, pr

    def make_menu(self):
        menu = Menu(self.map.title, menu_type="submenu")
        self._add_faction_menu(menu, *self._get_player())
        menu.append(
            mp.QUIT2 + mp.LEAVE_THIS_GAME, (self.server.write_line, "unregister")
        )
        return menu


class SpectateMenu(_ServerMenu):
    """旁观游戏菜单"""
    
    def __init__(self, server, auto=False, menu_type="main"):
        super().__init__(server, auto, menu_type)
        self.running_games = []
    
    def make_menu(self):
        menu = Menu(mp.SELECT_GAME_TO_SPECTATE, menu_type="submenu")
        
        # 添加正在进行的游戏到菜单
        if self.running_games:
            for game_id, map_name, players, minutes in self.running_games:
                game_title = f"{map_name} - {players} - {minutes}分钟"
                menu.append(
                    [game_title], 
                    (self.server.write_line, f"spectate {game_id}")
                )
        else:
            # 如果没有游戏，显示"没有可旁观的游戏"
            menu.append(mp.NO_GAMES_AVAILABLE, None)
        
        # 添加刷新选项
        menu.append(["刷新游戏列表"], (self.server.write_line, "list_games"))
        
        # 定义取消时的操作，用于正确退出旁观菜单
        def cancel_spectate_menu():
            self.end_loop = True
            return None
            
        menu.append(mp.CANCEL, cancel_spectate_menu)
        return menu

    def srv_running_games(self, args):
        """接收服务器发送的正在进行的游戏列表"""
        self.running_games = []
        for game_info in args:
            # 解析游戏信息：游戏ID,地图名称,玩家列表,进行时间(分钟)
            parts = game_info.split(",")
            if len(parts) >= 4:
                game_id = parts[0]
                map_name = parts[1]
                players = parts[2] if parts[2] else "无玩家"
                minutes = parts[3]
                self.running_games.append((game_id, map_name, players, minutes))
        # 收到游戏列表后更新菜单
        self.update_menu(self.make_menu())

    def srv_no_running_games(self, unused_args):
        """接收服务器通知：没有正在进行的游戏"""
        self.running_games = []
        voice.info(mp.NO_GAMES_AVAILABLE)
        # 更新菜单显示
        self.update_menu(self.make_menu())

    def srv_start_spectating(self, args):
        """开始旁观游戏

        服务器格式（新）: <packed_players> <scenario...> <speed> <seed> <treaty_minutes> <enemy_hp%> <enemy_damage%>
        旧格式: <packed_players> <scenario...> <speed> <seed> <treaty_minutes>
        更旧: <packed_players> <scenario...> <speed>
        从两端定位字段，使中间的地图名即使含空格也能正确解析。
        """
        players_str = args[0]
        enemy_hp = 100
        enemy_damage = 100
        if len(args) >= 7:
            # 含合作战役难度的新格式
            speed = float(args[-5])
            seed = int(args[-4])
            treaty = int(args[-3])
            enemy_hp = int(args[-2])
            enemy_damage = int(args[-1])
            map_name = " ".join(args[1:-5])
        elif len(args) >= 5:
            speed = float(args[-3])
            seed = int(args[-2])
            treaty = int(args[-1])
            map_name = " ".join(args[1:-3])
        else:
            speed = float(args[-1])
            seed = 0
            treaty = 0
            map_name = " ".join(args[1:-1])
        players = [p.split(",") for p in players_str.split(";")]
        
        # 创建旁观游戏（seed/treaty 用于确定性重建并重放追帧）
        from .game import SpectatorGame
        game = SpectatorGame(map_name, players, self.server, speed, seed, treaty)
        # 套用与对局一致的合作战役敌人强度，保证确定性
        game.enemy_hp_factor = enemy_hp
        game.enemy_damage_factor = enemy_damage
        game.auto = self.auto
        game.run()
        self.end_loop = True
