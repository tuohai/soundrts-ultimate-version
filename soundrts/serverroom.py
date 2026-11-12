import random
import time
from typing import TYPE_CHECKING, List, Union

from . import config
from .treaty import clamp_treaty_minutes
from .definitions import VIRTUAL_TIME_INTERVAL
from .lib.log import info, warning
from .mapfile import Map

if TYPE_CHECKING:
    from .serverclient import ConnectionToClient

from .version import IS_DEV_VERSION
from .version import DEFAULT_PROTOCOL, ROLLBACK_PROTOCOL, negotiate_protocol
from .version import protocol_revision, protocol_token


def same(strings):
    return len(set(strings)) == 1


def time_string(check_string):
    if check_string is not None:
        return check_string.split("-", 1)[0]


def pack(p):
    return ",".join((p.login, str(p.alliance), p.faction))


class _State:
    allowed_commands: tuple

    def send_menu(self, client):
        pass


class Anonymous(_State):

    allowed_commands = ("login",)


class InTheLobby(_State):

    allowed_commands = ("create", "create_random", "create_campaign", "register", "quit", "say", "list_games", "list_rooms", "spectate", "quit_game")

    def send_menu(self, client):
        client.send_maps()
        client.send_invitations()
        client.notify("update_menu")


class OrganizingAGame(_State):

    allowed_commands = (
        "invite",
        "invite_ai",
        "invite_beginner",
        "invite_intermediate",
        "invite_advanced",
        "invite_expert",
        "invite_nightmare",
        "invite_easy",
        "invite_aggressive",
        "invite_ai2",
        "move_to_alliance",
        "set_coop_slot",
        "start",
        "cancel_game",
        "say",
        "faction",
        "create_campaign",
    )

    def send_menu(self, client):
        client.notify(
            "available_players",
            *[
                p.login
                for p in client.server.available_players(client)
                if p not in client.game.guests
            ],
        )
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class WaitingForTheGameToStart(_State):

    allowed_commands = ("unregister", "say", "faction")

    def send_menu(self, client):
        client.notify("registered_players", *[pack(p) for p in client.game.players])
        client.notify("update_menu")


class Playing(_State):

    allowed_commands = ("orders", "quit_game", "timeout", "debug_info", "say", "input")


class Spectating(_State):

    allowed_commands = ("quit_spectating", "say")


class _Computer:
    def __init__(self, level, coop_partner=False):
        self.level = level
        self.coop_partner = coop_partner
        self.alliance = 0
        self.faction = "random_faction"

    @property
    def login(self):
        if self.coop_partner:
            return "ai_coop"
        return "ai_" + self.level


class Orders:
    def __init__(self, game):
        self.all_orders = {}
        for client in game.human_players:
            self.all_orders[client] = []

    def __repr__(self):
        return "<Orders '%s'>" % repr(self.all_orders)

    def add(self, client, args):
        self.all_orders[client].append(args)

    def pop_and_pack(self):
        _all_orders = []
        for player, queue in list(self.all_orders.items()):
            orders = queue.pop(0)[0]
            _all_orders.append(f"{player.login}/{orders}")
        return " ".join(_all_orders)

    def are_ready(self):
        return [] not in list(self.all_orders.values())

    def remove(self, client):
        del self.all_orders[client]

    def players_without_orders(self):
        return [player for player, queue in list(self.all_orders.items()) if not queue]

    def get_next_check_strings(self):
        return [queue[0][1] for queue in list(self.all_orders.values())]


class InputStreamGame:
    """Server side of the rollback protocol.

    This is the replacement for the lockstep :class:`Orders` barrier.  The
    legacy protocol waits until *every* player has sent their orders for a
    communication turn, and only then broadcasts the whole turn.  The
    slowest player's ping therefore sets the pace of the entire match.

    Here the server instead:

    * stamps every input with a monotonically increasing sequence number the
      moment it arrives — that number is what makes the *order* in which the
      inputs are applied authoritative and identical on every client;
    * broadcasts each input immediately, without waiting for the others.

    A client therefore learns about the other player's move as soon as the
    server receives it, and simulates it immediately.  When the truth
    contradicts what the client predicted, the client rolls back and
    re-simulates — see :mod:`soundrts.net.rollback`.

    The *frame* number is chosen by the client, not by the server: in a
    rollback netcode every client runs its own simulation ahead of the
    server, so only the client knows which frame its orders belong to.  The
    server checks that the frame is not absurdly far ahead, and that is
    that.
    """

    def __init__(self, game, max_ahead: int = 240):
        from .net.input_stream import InputStream

        self.game = game
        self.stream = InputStream([p.login for p in game.human_players])
        # How far a client may run ahead of the server before the server
        # considers it cheating (or broken).
        self.max_ahead = max_ahead
        # The highest frame the server has seen an input for.
        self.highest_frame = -1
        # Frames the server has already broadcast as complete.
        self.confirmed = set()
        # When each player last sent an input.  The timeout check uses it to
        # find a player that stopped playing (the lockstep protocol uses the
        # order queue for the same purpose).
        self.last_input_time = {}

    @property
    def players(self):
        return self.stream.players

    def submit(self, player_login: str, frame: int, orders: str):
        """Record *player_login*'s input for *frame*.

        *orders* must already be packed (see
        :func:`soundrts.net.input_stream.pack_orders`).

        Returns the stamped input, ready to be broadcast, or ``None`` when
        the submission was rejected (a duplicate, or a frame that is too far
        ahead).
        """
        from .net.input_stream import encode_input

        if frame < 0:
            return None
        if self.highest_frame >= 0 and frame > self.highest_frame + self.max_ahead:
            warning(
                "player %s sent input for frame %d, too far ahead of %d",
                player_login,
                frame,
                self.highest_frame,
            )
            return None

        stamped = self.stream.submit_incremental(player_login, frame, orders)
        if stamped is None:
            # A duplicate submission.  The first one wins: a retransmission
            # must never change an input that has already been broadcast.
            return None
        self.last_input_time[player_login] = time.time()
        if frame > self.highest_frame:
            self.highest_frame = frame
        if self.stream.is_authoritative(frame):
            self.confirmed.add(frame)
        number, seq, packed = stamped
        return encode_input(number, player_login, seq, packed)

    def remove_player(self, player_login: str) -> None:
        """Drop a player that quit the match from the stream.

        The frames the quitter left open are closed: they are stamped and
        broadcast, so that the other players and the spectators can keep
        replaying the match instead of stalling on a frame nobody will
        ever answer.
        """
        from .net.input_stream import encode_input

        if player_login not in self.stream.players:
            return
        open_frames = self.stream.remove_player(player_login)
        for number in open_frames:
            # The quitter's share of the frame is empty: it did nothing.
            #
            # But only for the frames it had *not* answered.  A frame the
            # quitter did answer holds its real orders, and broadcasting an
            # empty input for it would contradict — and therefore silently
            # corrupt — the authoritative record of that frame.
            existing = self.stream.frame(number)
            if existing is not None and player_login in existing.inputs:
                continue
            self.game._broadcast_input(
                encode_input(number, player_login, 0, ""), exclude=None
            )
            if self.stream.is_authoritative(number):
                self.confirmed.add(number)
        # The clients must stop waiting for the quitter too: they have to
        # know it is gone, or every frame would stay incomplete on their
        # side as well.
        for client in self.game.human_players:
            client.notify("player_quit", player_login)
        for spectator in self.game.spectators:
            spectator.notify("player_quit", player_login)

    def confirmed_frames(self):
        """Every frame that every player has answered, oldest first."""
        return self.stream.confirmed_frames()

    def frames(self):
        """Every frame that has at least one input, oldest first.

        Unlike :meth:`confirmed_frames`, this includes the frames that are
        not complete yet: their partial inputs exist and must not be lost.
        """
        result = []
        for number in self.stream.frame_numbers():
            frame = self.stream.frame(number)
            if frame is not None:
                result.append(frame)
        return result

    def frame_numbers(self):
        """Every frame that has at least one input, oldest first."""
        return self.stream.frame_numbers()

    def gaps(self):
        """Frames below the confirmed one that are still incomplete."""
        return self.stream.gaps()


class Game:

    started = False
    speed = 1

    def __init__(self, scenario: Map, speed, server, admin, is_public=False, treaty_minutes: int = 0, password: str = "") -> None:
        from .room_password import sanitize_room_password

        self.id = server.get_next_id()
        self.scenario = scenario
        self.speed = speed
        self.real_speed = speed
        self.server = server
        self.admin = admin
        self.password = sanitize_room_password(password)
        self.is_public = not bool(self.password)
        self.treaty_minutes = clamp_treaty_minutes(treaty_minutes)
        self.players: List[Union["ConnectionToClient", _Computer]] = []
        self.guests: List[Union["ConnectionToClient", _Computer]] = []
        self.spectators: List["ConnectionToClient"] = []  # 旁观者列表
        # 旁观同步所需：开局随机种子 + 已下发的全部 all_orders 历史。
        # 服务器本身不模拟世界，旁观者要靠"相同 seed + 重放历史 orders"
        # 才能确定性地重建当前对局状态，因此必须把这两样记录下来。
        self.seed = 0
        self._order_history: List[tuple] = []  # [(fpct, all_orders_string), ...]
        self._initial_players_pack = ""  # 开局原始玩家名册，旁观重建用
        self.register(admin)
        # All rooms appear in the lobby room list. A password, not public/private,
        # controls who may join or spectate. Invited guests skip the password.

    def notify_connection_of(self, unused_client):
        # Login still calls this; the room list is refreshed via update_menus.
        pass

    def _open_room_title_parts(self):
        from .lib.msgs import normalize_map_title_for_voice
        from .randommap import map_voice_title

        voice_title = map_voice_title(self.scenario)
        if voice_title:
            return list(voice_title)
        title = getattr(self.scenario, "title", None)
        if title:
            if isinstance(title, str):
                title = [title]
            return list(normalize_map_title_for_voice(title, self.scenario.name))
        return [self.scenario.name]

    def open_room_pack(self):
        return self.room_pack()

    def room_pack(self):
        """One notify token listing a room (password never included)."""
        from urllib.parse import quote

        players = "+".join(
            p.login.replace("+", "_").replace(",", "_") for p in self.human_players
        ) or self.admin.login.replace("+", "_").replace(",", "_")
        started = 1 if self.started else 0
        locked = 1 if getattr(self, "password", "") else 0
        try:
            minutes = self.nb_minutes if self.started else 0
        except Exception:
            minutes = 0
        joinable = 1 if (not self.started and self.can_register()) else 0
        spectatable = 1
        parts = [
            self.id,
            self.admin.login.replace(",", "_"),
            len(self.human_players),
            self.scenario.nb_players_max,
            players,
            started,
            locked,
            minutes,
            joinable,
            spectatable,
            *self._open_room_title_parts(),
        ]
        return quote(",".join(str(x) for x in parts), safe=",+")

    def is_listed_room(self, client):
        if not client.is_compatible(self.admin):
            return False
        if client in self.human_players or client in self.spectators:
            return False
        return True

    def is_listed_open_room(self, client):
        return self.is_listed_room(client) and (not self.started) and self.can_register()

    def password_accepted(self, client, offered=""):
        from .room_password import sanitize_room_password

        secret = getattr(self, "password", "") or ""
        if not secret:
            return True
        if client in self.guests:
            return True
        return sanitize_room_password(offered) == secret

    def can_join_from_lobby(self, client, offered=""):
        if not self.can_register():
            return False
        if not client.is_compatible(self.admin):
            return False
        return self.password_accepted(client, offered)

    def can_spectate_from_lobby(self, client, offered=""):
        if not client.is_compatible(self.admin):
            return False
        if client in self.human_players:
            return False
        return self.password_accepted(client, offered)

    @property
    def human_players(self) -> List["ConnectionToClient"]:
        return [p for p in self.players if not isinstance(p, _Computer)]

    def _start(self):
        info(
            "start game %s on map %s with players %s",
            self.id,
            self.scenario.name,
            " ".join(p.login for p in self.players),
        )
        self.guests = []
        self.started = True
        self.time = 0
        random.seed()
        seed = getattr(self, "rmg_seed", None)
        if seed is None:
            seed = random.randint(0, 10000)
        # 记录种子，供旁观者用相同种子确定性重建世界。
        self.seed = seed
        self._order_history = []
        self._orders = Orders(self)
        # The authoritative input stream, used by the rollback protocol.
        # It is created here so that the server has a single place that
        # stamps and broadcasts the inputs, no matter which client sent them.
        self._input_stream = InputStreamGame(self)
        # The protocol this game is played with.  It is negotiated from the
        # protocols the clients speak: the rollback protocol only works if
        # *every* player understands it, and agrees on its revision.
        self.protocol = negotiate_protocol(
            [getattr(c, "protocol", DEFAULT_PROTOCOL) for c in self.human_players],
            [int(getattr(c, "protocol_revision", 1) or 1) for c in self.human_players],
        )
        # The revision of the protocol the game is played with.  It is the
        # revision every client announced for that protocol (the negotiation
        # guarantees they all agree on it).
        self.protocol_revision = protocol_revision(self.protocol)
        info(
            "game %s uses the %s protocol (revision %s)",
            self.id,
            self.protocol,
            self.protocol_revision,
        )
        ##        # guess first ping from the connection delays
        ##        self.ping = max([p.delay for p in self.human_players])
        # 帝国时代式合作战役：人类玩家与 AI 队友同属 1 队。
        # 敌人来自地图的 computer_only（在 populate_map 里以 "ai" 同盟自成一队），
        # 不在 game.players 里，因此这里把 game.players 全部归为 1 队即可；
        # 并先用同盟 AI 队友补满地图声明但无人占用的玩家位（空位由 AI 接管，
        # 这样单人也能开合作关，符合帝国时代"线上单人"的做法）。
        try:
            is_coop = bool(getattr(self, "is_coop_campaign", False))
        except Exception:
            is_coop = False
        if is_coop:
            self._fill_coop_ai_partners()
            for p in self.players:
                p.alliance = 1

        # 固化开局玩家名册（含此刻的 alliance/faction）。旁观者必须用这份原始名册
        # 重建世界，而不是 self.players（玩家中途退出会从中移除），否则重放的历史
        # orders 会引用世界里不存在的玩家而分叉。退出动作本身已在 orders 历史里。
        self._initial_players_pack = ";".join(pack(p) for p in self.players)

        # 合作战役难度：在开局时一次性算定敌人强度百分比（含玩家人数缩放），
        # 作为唯一数据源下发给所有客户端，并缓存供旁观者使用。确定性要求各端一致，
        # 故必须由服务器算定后分发，而不是各端自行根据等级名重算。
        self._coop_enemy_hp = 100
        self._coop_enemy_damage = 100
        coop_difficulty = getattr(self, "coop_difficulty", None)
        if is_coop and coop_difficulty:
            try:
                from .coop_difficulty import factors

                self._coop_enemy_hp, self._coop_enemy_damage = factors(
                    coop_difficulty, len(self.human_players)
                )
            except Exception:
                self._coop_enemy_hp = 100
                self._coop_enemy_damage = 100

        for client in self.human_players:
            # 难度行必须在 start_game 之前发送：客户端 menu 顺序处理事件，
            # srv_coop_difficulty 先把百分比存好，srv_start_game 再读取并配置世界。
            if is_coop and coop_difficulty:
                client.notify(
                    "coop_difficulty",
                    self._coop_enemy_hp,
                    self._coop_enemy_damage,
                    coop_difficulty,
                )
            # The protocol is negotiated for the whole game, and sent
            # before start_game: the client has to know which protocol the
            # game uses before it starts simulating.  The token carries
            # the revision too, so a client can check that it understands
            # the exact wire format the server will use.
            client.notify("protocol", protocol_token(self.protocol))
            client.notify(
                "start_game",
                self._initial_players_pack,
                client.login,
                seed,
                self.speed,
                self.treaty_minutes,
                # 附加合作战役元信息：标记、战役名、章节号
                int(is_coop),
                getattr(self, "coop_campaign_name", ""),
                getattr(self, "coop_chapter", ""),
            )
            client.state = Playing()
        for spec in list(self.spectators):
            self._send_start_spectating(spec)
        self.server.log_status()
        self._start_time = time.time()

    def start(self):
        if (
            self.scenario.nb_players_min
            <= len(self.players)
            <= self.scenario.nb_players_max
        ):
            self._start()
        else:
            warning("couldn't start game: bad number of players")

    def remove(self, client):
        info("%s has quit game %s after %s turns", client.login, self.id, self.time)
        if client in self.players:
            self.players.remove(client)
        if getattr(client, "game", None) is self:
            client.game = None
        if getattr(self, "protocol", None) == ROLLBACK_PROTOCOL:
            # The quitter will never answer the frames it was supposed to
            # answer.  Those frames have to be closed, or the whole match
            # would stall: a frame is only complete once every player has
            # answered it.
            stream = getattr(self, "_input_stream", None)
            if stream is not None:
                stream.remove_player(client.login)
        if self.human_players:
            try:
                self._orders.remove(client)
            except KeyError:
                pass
            self._dispatch_orders_if_needed()
        else:
            self.close()

    @property
    def nb_minutes(self):
        return int((time.time() - self._start_time) / 60)

    def close(self):
        info(
            "closed game %s after %s turns (played for %s minutes)",
            self.id,
            self.time,
            self.nb_minutes,
        )
        self.cancel()
        self.server.log_status()

    _nb_allowed_alerts = 1

    def _check_synchronization(self, check_strings):
        if not same(check_strings) and self._nb_allowed_alerts > 0:
            if not same(time_string(cs) for cs in check_strings):
                if IS_DEV_VERSION and None not in check_strings:
                    info(
                        "time mismatch in game %s at turn %s: %s",
                        self.id,
                        self.time,
                        check_strings,
                    )
                return
            warning(
                "mismatch in game %s at turn %s: %s", self.id, self.time, check_strings
            )
            self._nb_allowed_alerts -= 1
            self.notify("synchronization_error")

    ping = 0
    delay = 0

    def orders(
        self, client, orders, check=None, ping=0, update=0, delay=0, real_speed=0
    ):
        self.ping = max(self.ping, float(ping))
        self.delay = max(self.delay, float(delay))
        self.real_speed = min(self.real_speed, float(real_speed))
        self._orders.add(client, [orders, check])
        self._dispatch_orders_if_needed()

    # -- the rollback protocol -------------------------------------------

    def submit_input(self, client, frame: int, orders: str) -> bool:
        """Accept one player's input for *frame* and broadcast it.

        The input is stamped with an authoritative sequence number and sent
        to every other player *immediately* — the server does not wait for
        the other players, which is what removes the lockstep barrier.

        Returns ``True`` when the input was accepted.
        """
        stream = getattr(self, "_input_stream", None)
        if stream is None:
            return False
        login = getattr(client, "login", None)
        if login is None or login not in stream.players:
            return False
        message = stream.submit(login, frame, orders)
        if message is None:
            # A duplicate or a rejected frame: nothing to broadcast.
            return False
        self._broadcast_input(message, exclude=client)
        return True

    def _broadcast_input(self, message: str, exclude=None) -> None:
        """Send an authoritative input to every player but *exclude*.

        The spectators get the inputs too: under the rollback protocol a
        spectator does not merely rebuild the past, it *keeps up* with the
        match by replaying the frames as they arrive.  Without this, a
        spectator would freeze at the frame it had caught up to.
        """
        for client in self.human_players:
            if exclude is not None and client is exclude:
                continue
            client.notify("input", message)
        for spectator in self.spectators:
            spectator.notify("input", message)

    def confirmed_frames(self):
        """Every frame that every player has answered, oldest first."""
        stream = getattr(self, "_input_stream", None)
        if stream is None:
            return []
        return stream.confirmed_frames()

    def input_gaps(self):
        """Frames below the confirmed one that are still incomplete."""
        stream = getattr(self, "_input_stream", None)
        if stream is None:
            return []
        return stream.gaps()

    def input_history(self):
        """Every authoritative input of the match, in order.

        This is what a spectator needs to rebuild the match from the start:
        in the rollback protocol the match is a sequence of frames, and each
        frame is a set of per-player inputs.  Unlike the lockstep protocol
        (which replays the communication turns), the spectator has to
        replay every single frame.

        *Every* frame that has at least one input is included, not only the
        ones every player has answered.  A frame that is still missing a
        player's input is replayed by the spectator as soon as that input
        arrives (live), and dropping the partial inputs here would lose
        them for good.

        Each entry is ``(frame, player_login, seq, packed orders)``.
        """
        stream = getattr(self, "_input_stream", None)
        if stream is None:
            return []
        result = []
        for frame in stream.frames():
            for player_login in sorted(frame.inputs):
                seq, orders = frame.inputs[player_login]
                result.append((frame.frame, player_login, seq, orders))
        return result

    def _send_input_history(self, client) -> None:
        """Send the whole input history to a spectator (rollback mode).

        The spectator rebuilds the match by replaying those inputs, one
        frame at a time, exactly like the players do.
        """
        for frame, player_login, seq, orders in self.input_history():
            client.notify("input", "%d:%s=%d:%s" % (frame, player_login, seq, orders))

    max_ping = 0.5  # seconds

    def fpct(self):
        """number of simulation frames per communication turn"""
        # 1 is probably the best number in most cases because the game is often CPU-bound.
        # the following number could be chosen instead someday
        tps = self.real_speed * 1000 / VIRTUAL_TIME_INTERVAL
        # Avoid unrealistic ping values.
        ping = min(self.max_ping, self.ping)
        result = int(tps * ping * config.fpct_coef) + 1
        return min(config.fpct_max, result)

    def _dispatch_orders_if_needed(self):
        while self._orders.are_ready():
            self._check_synchronization(self._orders.get_next_check_strings())
            all_orders = self._orders.pop_and_pack()
            fpct = self.fpct()
            # 记录这一通信回合下发的 orders，供后来加入的旁观者重放追帧。
            self._order_history.append((fpct, all_orders))
            self.notify("all_orders", fpct, all_orders)
            self.time += 1
            self._timeout_reference = None
            self.ping = 0
            self.delay = 0
            self.real_speed = self.speed

    def invite(self, client):
        self.guests.append(client)
        from .randommap import map_voice_title

        voice_title = map_voice_title(self.scenario)
        if voice_title:
            client.notify("invitation", self.admin.login, *voice_title)
        else:
            client.notify("invitation", self.admin.login, self.scenario.name)

    # 合作战役 AI 队友默认等级（积极型 AI：会主动用该位的起始部队作战）
    coop_partner_level = "aggressive"

    def _player_at_alliance(self, alliance):
        for p in self.players:
            if p.alliance == alliance:
                return p
        return None

    def _add_coop_ai_at_alliance(self, alliance):
        partner = _Computer(self.coop_partner_level, coop_partner=True)
        partner.alliance = alliance
        self.players.append(partner)

    def _notify_registered_players(self):
        self.notify("registered_players", *[pack(p) for p in self.players])

    def set_coop_slot_ai(self, alliance):
        """将指定合作槽位设为 AI 队友（帝国时代决定版式，非遭遇战难度 AI）。"""
        occupant = self._player_at_alliance(alliance)
        if occupant is not None and not isinstance(occupant, _Computer):
            return False
        self.players = [
            p
            for p in self.players
            if not (isinstance(p, _Computer) and p.alliance == alliance)
        ]
        self._add_coop_ai_at_alliance(alliance)
        self._notify_registered_players()
        return True

    def clear_coop_slot(self, alliance):
        """将指定合作槽位设为空缺（移除该位的合作 AI 队友）。"""
        before = len(self.players)
        self.players = [
            p
            for p in self.players
            if not (
                isinstance(p, _Computer)
                and getattr(p, "coop_partner", False)
                and p.alliance == alliance
            )
        ]
        if len(self.players) != before:
            self._notify_registered_players()
        return True

    def _fill_coop_ai_partners(self):
        """合作战役：用同盟 AI 队友补满地图声明但无人占用的玩家位。

        帝国时代决定版的合作战役允许空的玩家位由 AI 队友接管（"线上单人"也能
        开战役）。仅当地图的 ``nb_players_max`` 大于当前已注册玩家数时才补；
        补出的 AI 与人类同队（其 alliance 由调用方在合作分支里统一设为 1）。

        敌人来自地图的 ``computer_only``（不在 ``self.players`` 内），不受影响。
        每个补出的 AI 会在 ``populate_map`` 里分到一个独立的玩家出生点，
        从而像帝国时代那样各自拥有一份起始部队/基地。
        """
        try:
            max_slots = int(self.scenario.nb_players_max)
        except Exception:
            return
        used = {p.alliance for p in self.players}
        for alliance in range(1, max_slots + 1):
            if alliance not in used:
                self._add_coop_ai_at_alliance(alliance)

    def invite_computer(self, level):
        if getattr(self, "is_coop_campaign", False):
            self.admin.notify("invite_computer_error")
            return
        if (
            not config.require_humans
            or "admin_only" in self.server.parameters
            or len(self.players) > 1
        ):
            self.register(_Computer(level))
        else:
            self.admin.notify("invite_computer_error")

    def uninvite(self, client):
        self.guests.remove(client)

    def add_spectator(self, client):
        """添加旁观者"""
        if client not in self.spectators:
            self.spectators.append(client)
            client.game = self
            client.state = Spectating()
            # 通知所有玩家和旁观者有新的旁观者加入
            for player in self.human_players:
                player.notify("spectator_joined", client.login)
            for spectator in self.spectators:
                if spectator != client:
                    spectator.notify("spectator_joined", client.login)
            info(f"旁观者 {client.login} 加入游戏 {self.id}")

    def remove_spectator(self, client):
        """移除旁观者"""
        waiting = not self.started
        if client in self.spectators:
            self.spectators.remove(client)
            client.game = None
            client.state = InTheLobby()
            # 通知所有玩家和旁观者有旁观者离开
            for player in self.human_players:
                player.notify("spectator_left", client.login)
            for spectator in self.spectators:
                spectator.notify("spectator_left", client.login)
            if waiting:
                client.notify("quit")
            info(f"旁观者 {client.login} 离开游戏 {self.id}")

    def _send_start_spectating(self, client):
        initial_players = getattr(self, "_initial_players_pack", None)
        if not initial_players:
            initial_players = ";".join(pack(p) for p in self.players)
        # The protocol comes first: the spectator has to know how to
        # rebuild the match before it starts.  The token carries the
        # revision, so the spectator knows the exact wire format.
        client.notify("protocol", protocol_token(getattr(self, "protocol", DEFAULT_PROTOCOL)))
        client.notify(
            "start_spectating",
            initial_players,
            self.scenario.name,
            self.speed,
            self.seed,
            self.treaty_minutes,
            getattr(self, "_coop_enemy_hp", 100),
            getattr(self, "_coop_enemy_damage", 100),
        )
        if getattr(self, "protocol", None) == ROLLBACK_PROTOCOL:
            # The rollback protocol has no communication turns: the match is
            # a sequence of frames, and the spectator rebuilds it by
            # replaying the inputs of every frame.
            self._send_input_history(client)
            return
        for fpct, all_orders in getattr(self, "_order_history", []) or []:
            client.notify("all_orders", fpct, all_orders)

    def start_spectating(self, client):
        """旁观：已开打则立刻重放追帧；未开打则先进入等待，开局后再下发 start_spectating。"""
        if client in self.human_players:
            return False
        if self.started:
            if client not in self.spectators:
                self.add_spectator(client)
            self._send_start_spectating(client)
            return True
        if client not in self.spectators:
            self.add_spectator(client)
        client.notify("waiting_to_spectate")
        return True

    def move_to_alliance(self, player_index, alliance):
        player = self.players[int(player_index)]
        player.alliance = int(alliance)
        self.notify("alliance", player.login, player.alliance)

    def set_faction(self, player_index, faction):
        player = self.players[int(player_index)]
        player.faction = faction
        self.notify("faction", player.login, faction)

    def notify(self, *args):
        for client in self.human_players:
            client.notify(*args)
        # 旁观者也接收游戏消息
        for spectator in self.spectators:
            spectator.notify(*args)

    def can_register(self):
        if self.started:
            return False
        if getattr(self, "is_coop_campaign", False):
            return self._coop_has_joinable_slot()
        return len(self.players) < self.scenario.nb_players_max

    def _coop_partner_slots(self):
        try:
            max_slots = int(self.scenario.nb_players_max)
        except Exception:
            return []
        return list(range(2, max_slots + 1))

    def _coop_has_joinable_slot(self):
        for alliance in self._coop_partner_slots():
            occupant = self._player_at_alliance(alliance)
            if occupant is None:
                return True
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                return True
        return False

    def prepare_coop_slot_for_human(self, alliance=None):
        """Remove coop AI from partner slot(s) before a human is invited or joins."""
        slots = [alliance] if alliance is not None else self._coop_partner_slots()
        changed = False
        for slot in slots:
            occupant = self._player_at_alliance(slot)
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                if self.clear_coop_slot(slot):
                    changed = True
        return changed

    def register(self, client):
        if getattr(self, "is_coop_campaign", False):
            return self._register_coop(client)
        if not self.can_register():
            return False
        for n in range(len(self.players) + 1):
            n += 1
            if n not in [p.alliance for p in self.players]:
                break
        self._add_registered_client(client, n)
        return True

    def _register_coop(self, client):
        if not self._coop_has_joinable_slot():
            return False
        for alliance in self._coop_partner_slots():
            occupant = self._player_at_alliance(alliance)
            if occupant is None:
                self._add_registered_client(client, alliance)
                return True
            if isinstance(occupant, _Computer) and getattr(occupant, "coop_partner", False):
                self.clear_coop_slot(alliance)
                self._add_registered_client(client, alliance)
                return True
        return False

    def _add_registered_client(self, client, alliance):
        self.players.append(client)
        client.game = self
        client.alliance = alliance
        client.faction = "random_faction"
        self.notify(
            "registered", client.login, ",".join([c.login for c in self.players])
        )
        self._notify_registered_players()

    @property
    def short_status(self):
        from .randommap import map_voice_title

        voice_title = map_voice_title(self.scenario)
        if voice_title is None:
            voice_title = [self.scenario.name]
        return (
            *voice_title,
            ",".join([c.login for c in self.players]),
            self.nb_minutes,
        )

    def unregister(self, client):
        if client in self.players:
            self.players.remove(client)
        prev = getattr(client, "state", None)
        if getattr(client, "game", None) is self:
            client.game = None
        client.state = InTheLobby()
        # Only kick pre-start room menus. A Playing/InTheLobby client is already
        # in (or returning to) the server lobby; "quit" would drop them to the
        # main menu and can arrive after the match UI has already exited.
        if isinstance(prev, (WaitingForTheGameToStart, OrganizingAGame)):
            client.notify("quit")

    def cancel(self):
        for c in list(self.human_players):
            self.unregister(c)
        for c in self.guests[:]:
            self.uninvite(c)
        # 清理旁观者
        for c in self.spectators[:]:
            self.remove_spectator(c)
        if self in self.server.games:
            self.server.games.remove(self)

    _timeout_reference = None

    def check_timeout(self):
        # The rollback protocol: the clients send "input" messages, not
        # "orders", so the lockstep order queue is never filled and every
        # player would look idle.  The timeout is therefore measured on the
        # *input stream* instead: a player that has not sent any input for
        # a while is the one that is stuck.
        if getattr(self, "protocol", None) == ROLLBACK_PROTOCOL:
            self._check_input_timeout()
            return
        if self._timeout_reference is None:
            self._timeout_reference = time.time()
        elif time.time() > self._timeout_reference + config.timeout:
            for player in self._orders.players_without_orders():
                warning("timeout %s", player.login)
                player.handle_close()  # disconnect player
                break  # don't continue! (might disconnect more players)

    def _check_input_timeout(self):
        """Disconnect a player that stopped sending inputs (rollback mode).

        In the rollback protocol every client sends an input for *every*
        frame — even an empty one — so a player that has been silent for
        longer than the timeout is stuck, and is disconnected.

        This mirrors the lockstep behaviour, where the server waits for
        everybody's orders: a player that stops answering stalls the match.
        """
        stream = getattr(self, "_input_stream", None)
        if stream is None:
            return
        now = time.time()
        last = getattr(stream, "last_input_time", None) or {}
        players = self.human_players
        if not players:
            return
        if not all(p.login in last for p in players):
            # Somebody has not spoken yet: give everybody a grace period.
            self._timeout_reference = now
            return
        self._timeout_reference = now
        for player in players:
            if now - last[player.login] > config.timeout:
                warning("timeout %s", player.login)
                player.handle_close()  # disconnect player
                break
