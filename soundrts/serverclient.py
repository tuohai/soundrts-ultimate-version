import re
import sys
import time
from typing import TYPE_CHECKING

from . import config
from .batteries import asynchat
from .lib.log import exception, info, warning
from .lib.msgs import encode_msg, normalize_map_title_for_voice
from .lib.resource import res
from .pack import pack_buffer

if TYPE_CHECKING:
    from .servermain import Server

from .serverroom import (
    Anonymous,
    Game,
    InTheLobby,
    OrganizingAGame,
    Playing,
    Spectating,
    WaitingForTheGameToStart,
    _State,
)


def _map(map_index_or_name):
    maps = res.multiplayer_maps()
    try:
        return maps[int(map_index_or_name)]
    except ValueError:
        for scenario in maps:
            if map_index_or_name in scenario.name:
                return scenario


class ConnectionToClient(asynchat.async_chat):

    is_disconnected = False
    login = None
    version = None
    game = None

    def __init__(self, server: "Server", connection_and_address) -> None:
        (connection, address) = connection_and_address
        asynchat.async_chat.__init__(self, connection)
        self.id = server.get_next_id()
        self.set_terminator(b"\n")
        self.server = server
        self.inbuffer = b""
        self.address = address
        self.state: _State = Anonymous()
        self.push(":")
        self.t1 = time.time()

    def push(self, s):
        return asynchat.async_chat.push(self, s.encode("utf-8"))

    @property
    def name(self):
        return [self.login]

    def collect_incoming_data(self, data):
        self.inbuffer += data

    def _execute_command(self, data):
        args = data.decode("utf-8").split(" ")
        if args[0] not in self.state.allowed_commands:
            warning("action not allowed: %s" % args[0])
            return
        cmd = "cmd_" + args[0]
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning("action unknown: %s" % args[0])

    def found_terminator(self):
        data = self.inbuffer.replace(b"\r", b"")
        self.inbuffer = b""
        try:
            self._execute_command(data)
        except SystemExit:
            raise
        except:
            exception("error executing command: %s" % data)

    def handle_close(self):
        try:
            self.server.remove_client(self)
        except SystemExit:
            raise
        except:
            try:
                exception("error")
            except:
                pass
        self.close()

    def handle_error(self):
        if sys.exc_info()[0] in [SystemExit, KeyboardInterrupt]:
            sys.exit()
        else:
            self.handle_close()

    def send_invitations(self):
        self.push(
            "invitations %s\n"
            % " ".join(
                [
                    ",".join(
                        [
                            str(x)
                            for x in [g.id, g.admin.login]
                            + normalize_map_title_for_voice(
                                g.scenario.title, g.scenario.name
                            )
                        ]
                    )
                    for g in self.server.games
                    if self in g.guests
                ]
            )
        )

    def notify(self, *args):
        if not self.is_disconnected:
            self.push(" ".join(map(str, args)) + "\n")

    def send_maps(self):
        if self.server.can_create(self):
            self.push(
                "maps %s\n"
                % " ".join(
                    [",".join([str(y) for y in x.title]) for x in res.multiplayer_maps()]
                )
            )
        else:
            self.push("maps \n")

    def is_compatible(self, client):
        return self.version == client.version

    # "anonymous" commands

    def _unique_login(self, client_login):
        if client_login.startswith("ai_"):
            client_login = "player"
        login = client_login
        n = 2
        while login in [x.login for x in self.server.clients]:
            login = client_login + str(n)
            n += 1
        return login

    def _get_version_and_login_from_data(self, data):
        try:
            version, login = data.split(" ", 1)
        except:
            warning("can't extract version and login: %s" % data)
            return None, None
        if not config.login_is_valid(login):
            warning("bad login: %s" % login)
            return version, None
        if len(self.server.clients) >= self.server.nb_clients_max:
            warning("refused client %s: too many clients." % login)
            return version, None
        return version, self._unique_login(login)

    @property
    def compatible_clients(self):
        return [c.login for c in self.server.clients if c.is_compatible(self)]

    def _send_server_status(self):
        self.notify("clients", *self.compatible_clients)
        for game in self.server.games:
            if game.started:
                self.notify("game", *game.short_status)

    def _accept_client_after_login(self):
        self.delay = time.time() - self.t1
        info(
            "new player: IP=%s login=%s version=%s delay=%s"
            % (self.address[0], self.login, self.version, self.delay)
        )
        # welcome client to server
        self.push("ok!\n")
        self.push(f"welcome {self.login} {self.server.login}\n")
        self.server.clients.append(self)
        # move client to lobby
        self.state = InTheLobby()
        # alert lobby and game admins
        for c in self.server.available_players() + self.server.game_admins():
            if c.is_compatible(self):
                c.notify("logged_in", self.login)
        self._send_server_status()
        for g in self.server.games:
            g.notify_connection_of(self)
        self.server.log_status()

    def cmd_login(self, args):
        self.version, self.login = self._get_version_and_login_from_data(" ".join(args))
        if self.login is not None:
            self._accept_client_after_login()
            self.server.update_menus()
        else:
            info("incorrect login")
            self.handle_close()  # disconnect client

    # "in the lobby" commands

    def cmd_create(self, args: str) -> None:
        map_index_or_name = args[0]
        speed = float(args[1])
        is_public = len(args) >= 3 and args[2] == "public"
        # 可选：条约分钟数
        try:
            treaty_minutes = int(args[3]) if len(args) >= 4 else 0
        except Exception:
            treaty_minutes = 0
        if self.server.can_create(self):
            map_ = _map(map_index_or_name)
            if map_:
                self._create_game(map_, speed, is_public, treaty_minutes)
        else:
            warning("game not created (max number reached)")
            self.notify("too_many_games")

    def cmd_create_random(self, args: str) -> None:
        """create_random <size> <nb_players> <monster> <layout> <template> <terrain>
        <team> <water> <treasure> <victory_mode> <seed> <speed> [public] [treaty]"""
        from .randommap import make_map, parse_server_create_args

        if not self.server.can_create(self):
            warning("game not created (max number reached)")
            self.notify("too_many_games")
            return
        try:
            cfg, speed, is_public, treaty_minutes = parse_server_create_args(args)
            map_, seed = make_map(cfg)
        except Exception:
            warning("create_random: bad args")
            self.notify("too_many_games")
            return
        self._create_game(map_, speed, is_public, treaty_minutes)
        self.game.rmg_seed = seed

    def _create_game(
        self,
        map_,
        speed,
        is_public,
        treaty_minutes=0,
        is_coop_campaign=False,
        coop_campaign_name=None,
        coop_chapter=None,
        coop_difficulty=None,
    ):
        self.state = OrganizingAGame()
        if is_coop_campaign:
            self.push("game_admin_menu 1\n")
        else:
            self.push("game_admin_menu\n")
        self.push("map %s\n" % pack_buffer(map_.buffer, map_.buffer_name).decode())
        game = Game(map_, speed, self.server, self, is_public, treaty_minutes)
        # 标记为合作战役（用于强制同盟等逻辑）
        try:
            game.is_coop_campaign = bool(is_coop_campaign)
        except Exception:
            game.is_coop_campaign = False
        # 记录合作战役元信息
        try:
            game.coop_campaign_name = coop_campaign_name
            game.coop_chapter = coop_chapter
        except Exception:
            pass
        # 记录合作战役难度等级（敌人强度由 Game._start 在开局时算定百分比并下发）
        try:
            from .coop_difficulty import normalize_level

            game.coop_difficulty = (
                normalize_level(coop_difficulty)
                if coop_difficulty is not None
                else None
            )
        except Exception:
            game.coop_difficulty = None
        self.server.games.append(game)
        self.server.update_menus()

    def cmd_register(self, args: str) -> None:
        game = self.server.get_game_by_id(args[0])
        if game is not None and game.can_register():
            self.state = WaitingForTheGameToStart()
            # Send guest menu and map before register(): register() broadcasts
            # "registered" to all players, and the client needs self.map set first.
            self.push("game_guest_menu\n")
            self.push("map %s\n" % pack_buffer(game.scenario.buffer, game.scenario.buffer_name).decode())
            if not game.register(self):
                self.notify("register_error")
                return
            self.server.update_menus()
        else:
            self.notify("register_error")

    def cmd_create_campaign(self, args: str) -> None:
        """创建合作战役：create_campaign <campaign_name> <chapter_number> <speed> [public] [treaty_minutes]

        说明：客户端直接指定战役名与章节号，服务器在本地资源中加载对应地图。
        """
        # 宽松解析：支持战役名包含空格，忽略多余空格，识别 public 与可选条约分钟数
        try:
            tokens = [t for t in args if t != ""]
            if len(tokens) < 3:
                raise ValueError("too_few_args")

            # 先摘除带标记的难度 token（difficulty=<level>），避免与"战役名可含空格"
            # 的宽松解析冲突。缺省为标准难度。
            coop_difficulty = None
            for i, t in enumerate(tokens):
                if t.startswith("difficulty="):
                    coop_difficulty = t.split("=", 1)[1]
                    tokens.pop(i)
                    break

            # 尝试解析末尾的条约分钟数（可选）
            treaty_minutes = 0
            if len(tokens) >= 4:
                try:
                    treaty_minutes = int(tokens[-1])
                    tokens = tokens[:-1]
                except Exception:
                    pass

            # 解析可选 public 标记
            is_public = False
            if tokens and tokens[-1] == "public":
                is_public = True
                tokens = tokens[:-1]

            # 解析速度和章节号
            speed = float(tokens[-1])
            tokens = tokens[:-1]
            chapter_number = int(tokens[-1])
            tokens = tokens[:-1]

            # 余下为战役名称（可能包含空格）
            campaign_name = " ".join(tokens).strip()
            if not campaign_name:
                raise ValueError("empty_campaign_name")
        except Exception:
            warning("create_campaign: bad args")
            self.notify("invite_error")
            return

        if not self.server.can_create(self):
            warning("game not created (max number reached)")
            self.notify("too_many_games")
            return

        # 从服务器资源中查找战役并加载章节地图
        try:
            from .lib.resource import res
            from .campaign import Campaign
        except Exception:
            pass
        campaign = None
        for c in res.campaigns():
            if c.name == campaign_name:
                campaign = c
                break
        if campaign is None:
            warning(f"campaign not found: {campaign_name}")
            self.notify("invite_error")
            return
        chapter = campaign.chapter(chapter_number)
        if chapter is None:
            warning(f"campaign chapter not found: {campaign_name}/{chapter_number}")
            self.notify("invite_error")
            return

        # 跳过过场章节（没有 map 的章节），寻找下一个可玩的任务章节
        effective_chapter = chapter
        while effective_chapter is not None and not hasattr(effective_chapter, "map"):
            effective_chapter = campaign.next(effective_chapter)

        if effective_chapter is None:
            warning(f"no playable mission chapter after: {campaign_name}/{chapter_number}")
            self.notify("invite_error")
            return

        # 合作战役与单人共用 ``N.txt`` 任务地图（campaign.txt 声明 coop_missions）
        from .campaign import ensure_chapter_map

        map_ = ensure_chapter_map(effective_chapter)
        try:
            logical = f"{campaign.name}/{effective_chapter.number}"
            map_.name = logical
            # 网络打包名须含战役前缀，否则 Windows 客户端 basename 会丢掉战役名，
            # 无法从地图名推断战役并加载 ui/tts.txt 地名翻译。
            map_.buffer_name = f"{logical}.txt"
        except Exception:
            pass

        self._create_game(
            map_,
            speed,
            is_public,
            treaty_minutes,
            is_coop_campaign=True,
            coop_campaign_name=campaign.name,
            coop_chapter=effective_chapter.number,
            coop_difficulty=coop_difficulty,
        )

    def cmd_quit(self, unused_args):
        # When the client wants to quit, he first sends "quit" to the server.
        # Then the server knows he mustn't send commands anymore. He warns the
        # client: "ok, you can quit". Then the client closes the connection
        # and then, and only then, the server forgets the client.
        self.push("quit\n")
        # self.is_quitting = True

    def cmd_list_games(self, unused_args):
        """发送正在进行的游戏列表给客户端"""
        running_games = []
        for game in self.server.games:
            if game.started:
                # 格式：游戏ID,地图名称,玩家列表,进行时间(分钟)
                game_info = f"{game.id},{game.scenario.name},{','.join([p.login for p in game.human_players])},{game.nb_minutes}"
                running_games.append(game_info)
        
        if running_games:
            self.notify("running_games", *running_games)
        else:
            self.notify("no_running_games")

    def cmd_spectate(self, args):
        """开始旁观指定的游戏"""
        if not args:
            self.notify("spectate_error", "missing_game_id")
            return
            
        try:
            game_id = int(args[0])
            game = self.server.get_game_by_id(game_id)
            if game and game.started:
                if game.start_spectating(self):
                    self.notify("spectate_success")
                else:
                    self.notify("spectate_error", "game_not_started")
            else:
                self.notify("spectate_error", "game_not_found")
        except (ValueError, AssertionError):
            self.notify("spectate_error", "invalid_game_id")

    # "organizing a game" commands

    def cmd_cancel_game(self, unused_args):
        self.game.cancel()
        self.server.update_menus()

    def cmd_invite(self, args):
        guest = self.server.get_client_by_login(args[0])
        if (
            guest
            and guest in self.server.available_players()
            and guest.is_compatible(self)
        ):
            if getattr(self.game, "is_coop_campaign", False):
                for slot in self.game._coop_partner_slots():
                    self.game.prepare_coop_slot_for_human(slot)
            self.game.invite(guest)
            self.server.update_menus()
        else:
            self.notify("invite_error")

    def cmd_invite_ai(self, args):
        from .definitions import get_menu_ai_difficulties

        if getattr(self.game, "is_coop_campaign", False):
            self.notify("invite_computer_error")
            return
        if not args or args[0] not in get_menu_ai_difficulties():
            self.notify("invite_error")
            return
        self.game.invite_computer(args[0])
        self.send_menu()

    def cmd_set_coop_slot(self, args):
        """合作战役槽位：set_coop_slot <alliance> open|ai"""
        if not getattr(self.game, "is_coop_campaign", False):
            self.notify("invite_error")
            return
        try:
            alliance = int(args[0])
            mode = args[1]
        except (IndexError, ValueError):
            self.notify("invite_error")
            return
        if alliance < 2 or alliance > self.game.scenario.nb_players_max:
            self.notify("invite_error")
            return
        if mode == "ai":
            ok = self.game.set_coop_slot_ai(alliance)
        elif mode == "open":
            ok = self.game.clear_coop_slot(alliance)
        else:
            self.notify("invite_error")
            return
        if not ok:
            self.notify("invite_error")
            return
        self.server.update_menus()

    def cmd_invite_beginner(self, unused_args):
        self.game.invite_computer("beginner")
        self.send_menu()

    def cmd_invite_intermediate(self, unused_args):
        self.game.invite_computer("intermediate")
        self.send_menu()

    def cmd_invite_advanced(self, unused_args):
        self.game.invite_computer("advanced")
        self.send_menu()

    def cmd_invite_expert(self, unused_args):
        self.game.invite_computer("expert")
        self.send_menu()

    def cmd_invite_nightmare(self, unused_args):
        self.game.invite_computer("nightmare")
        self.send_menu()

    # legacy invite commands (kept for backward compatibility)
    def cmd_invite_easy(self, unused_args):
        self.game.invite_computer("beginner")
        self.send_menu()

    def cmd_invite_aggressive(self, unused_args):
        self.game.invite_computer("intermediate")
        self.send_menu()

    def cmd_invite_ai2(self, unused_args):
        self.game.invite_computer("ai2")
        self.send_menu()

    def cmd_move_to_alliance(self, args):
        self.game.move_to_alliance(args[0], args[1])
        self.send_menu()  # only the admin

    def cmd_start(self, unused_args):
        self.game.start()  # create chosen world
        self.server.update_menus()

    def cmd_faction(self, args):
        self.game.set_faction(args[0], args[1])
        self.server.update_menus()

    # "waiting for the game to start" commands

    def cmd_unregister(self, unused_args):
        self.game.unregister(self)
        self.server.update_menus()

    # "playing" commands

    def cmd_orders(self, args):
        self.push("pong\n")
        self.game.orders(self, *args)

    def cmd_quit_game(self, unused_args):
        self.game.orders(self, "quit")
        self.game.remove(self)
        self.state = InTheLobby()
        self.server.update_menus()

    def cmd_timeout(self, unused_args):
        self.game.check_timeout()

    # "spectating" commands

    def cmd_quit_spectating(self, unused_args):
        """停止旁观游戏"""
        if self.game:
            self.game.remove_spectator(self)
        self.server.update_menus()

    # wrapper

    def send_menu(self):
        self.state.send_menu(self)

    # misc

    def send_msg(self, msg):
        self.push("msg %s\n" % encode_msg(msg))

    def cmd_debug_info(self, args):
        info(" ".join(args))

    def cmd_say(self, args):
        if self.game:
            clients = self.game.human_players
        else:
            clients = self.server.available_players()
        for client in clients:
            client.notify("say", self.login, *args)
