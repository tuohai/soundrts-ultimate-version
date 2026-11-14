import platform
import sys
import threading
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from hashlib import md5
from typing import Optional

from .definitions import VIRTUAL_TIME_INTERVAL
from .lib import chronometer as chrono
from .lib.log import exception, info, warning
from .metaserver import METASERVER_URL
from .version import IS_DEV_VERSION, VERSION
from .worldplayerbase import Player
from .worldplayercomputer import Computer
from .worldplayercomputer2 import Computer2
from .worldplayerhuman import Human

FIRST_FPCT = 1

# used for packing the orders
NEWLINE_REPLACEMENT = ";"
SPACE_REPLACEMENT = ","

# The orders a replay line may start with.  A line that starts with one of
# these but has no time is a *continuation*: it is the second (or third,
# ...) order of a multi-line order, written by the old rollback recorder
# (which put a raw newline in the replay file).
REPLAY_ORDER_KEYWORDS = (
    "control",
    "order",
    "quit",
    "say",
    "flare",
    "speed",
    "set_formation",
    "stop",
)


def _pack(player_orders):
    return player_orders.replace("\n", NEWLINE_REPLACEMENT).replace(
        " ", SPACE_REPLACEMENT
    )


def _unpack(player_orders):
    return player_orders.replace(NEWLINE_REPLACEMENT, "\n").replace(
        SPACE_REPLACEMENT, " "
    )


def send_error_to_metaserver(error_msg):
    try:
        params = urllib.parse.urlencode({"method": "add", "msg": error_msg})
        urllib.request.urlopen(METASERVER_URL + "errors.php?%s" % params).read()
    except:
        exception("could not send error message to web server")


def send_platform_version_to_metaserver(game, nb):
    error_msg = "not_an_error time={} soundrts={} map={} players={} platform={} python={}".format(
        time.time(),
        VERSION,
        game,
        nb,
        platform.platform(),
        sys.version.replace("\n", " "),
    )
    send_error_to_metaserver(error_msg)


class _Controller:
    @property
    def name(self):
        from .clientservermenu import name

        return name(self.login)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.login!r})"

    player_class = Human
    player: Player
    alliance: Optional[str] = None
    faction = "random_faction"
    neutral = False

    def create_player(self, world):
        player = self.player_class(world, self)
        self.player = player
        world.players.append(player)

    def __getstate__(self):
        state = self.__dict__.copy()
        player = state.pop("player", None)
        if player is not None and getattr(player, "id", None):
            state["_pickle_player_id"] = player.id
        # UI is rebuilt by Game._ensure_interface_for_restore; pickling it
        # pulls pygame Fonts / locks and breaks mid-game resume on big maps.
        state.pop("interface", None)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.player = None
        self.interface = None



class _Client(_Controller):
    @property
    def allow_cheatmode(self):
        return self.game_session.allow_cheatmode

    def push(self, *args):
        self.interface.queue_srv_event(*args)

    def get_orders(self):
        if not hasattr(self, "_orders"):
            self._orders = []
        self._dispatch_orders()
        result = self._orders
        self._orders = []
        return result

    def queue_command(self, player, s):
        if player not in self.player.world.players:
            info("didn't send the order for player %s: %s", player, s)
            return
        if self.game_session.record_replay:
            player_index = self.player.world.players.index(player)
            self.game_session.replay_write(
                " ".join(map(str, (self.player.world.time, player_index, s)))
            )
        if not hasattr(self, "_orders"):
            self._orders = []
        self._orders.append((player, s))

    def _dispatch_orders(self):
        pass


class DummyClient(_Controller):  # AI

    alliance = "ai"  # computer players are allied by default

    def __init__(self, AI_type="timers", neutral=False, alliance="ai"):
        self.AI_type = AI_type
        self.neutral = neutral
        self.alliance = alliance
        self.login = "ai_" + self.AI_type

    def push(self, *args):
        pass

    @property
    def player_class(self):
        # Computer2 is the legacy random-cheat AI; only "ai2" uses it.
        # Every other AI string (incl. all difficulty levels and legacy
        # "easy"/"aggressive") uses the script-driven Computer class.
        if self.login == "ai_ai2":
            return Computer2
        else:
            return Computer


class RemoteClient(_Controller):
    def __init__(self, login):
        self.login = login

    def push(self, *args):
        pass


class DirectClient(_Client):  # client for single player games

    data = ""

    def __init__(self, login, game_session):
        self.login = login
        self.game_session = game_session

    def update(self):
        pass

    def orders_are_ready(self):
        return True

    def write_line(self, s):
        if self.player:
            self.queue_command(self.player, s)
        else:
            warning("couldn't send client command (no player): %s", s)

    def has_victory(self):
        return self.player.has_victory

    def save_game(self):
        self.game_session.save()

    def save_resume(self):
        """玩家中途退出时自动保留进度。"""
        self.game_session.save_resume()


class ReplayClient(DirectClient):

    def write_line(self, s):
        if s == "quit":
            self.queue_command(self.player, "neutral_quit")
        elif not s.startswith(("control", "order")):
            self.queue_command(self.player, s)

    # -- reading the replay ----------------------------------------------

    def _parse_replay_record(self, line):
        """Parse one replay line into ``(time, player index, command)``.

        Returns ``None`` when the line is not a record (a malformed line, or
        a continuation of a multi-line order written by an old version of
        the rollback recorder).

        The old reader did ``self._cmd.split(" ", 2)`` and then
        ``int(time)``, and both could raise:
        * a continuation line (``order 0 0 default 7``) has no time, so
          ``int("order")`` raises ``ValueError`` and the replay dies;
        * a line with fewer than three fields raises ``ValueError`` on the
          unpacking.

        Both are handled here, so a damaged (or old) replay line is skipped
        instead of taking the whole playback down.
        """
        if not line:
            return None
        parts = line.split(" ", 2)
        if len(parts) < 3:
            return None
        time_part, player_part, command = parts
        try:
            record_time = int(time_part)
            player_index = int(player_part)
        except ValueError:
            # Not a record: a continuation line, or a corrupted line.
            return None
        if not command:
            return None
        return record_time, player_index, command

    def _parse_continuation(self, line, previous):
        """Parse a continuation line of a multi-line order.

        The old rollback recorder wrote a multi-line order string as one
        physical line, which put a raw newline in the replay file.  The
        lines after the first therefore have no time and no player index:
        they are the remaining orders of the *same* player's order string,
        applied at the *same* time.

        So a continuation line is turned back into a record that belongs to
        the previous record: same time, same player, and the continuation
        as the command.

        Returns ``None`` when the line is not a continuation (a corrupted
        line, or a line that does not start with an order keyword).
        """
        if not line or previous is None:
            return None
        stripped = line.strip()
        if not stripped.startswith(REPLAY_ORDER_KEYWORDS):
            return None
        previous_time, previous_player, _previous_command = previous
        return previous_time, previous_player, stripped

    def _dispatch_orders(self):
        """Apply the replay records whose time the world has reached.

        The replay is a list of ``<time> <player> <order>`` records, and
        the world advances 300 ms per frame.  A record is applied when the
        world's time has reached the record's time.

        The old reader waited for an *exact* match
        (``int(time) == self.player.world.time``) and stopped at the first
        record that did not match.  That is fragile in three ways:

        * a record whose time is not a multiple of 300 ms can never match
          exactly, so the reader stalls on it forever and the rest of the
          replay is never played;
        * a rollback rewinds the world, so the timestamps of a rollback
          replay are not monotonic, and a record that goes backwards is
          never matched either;
        * the reader stopped at the first record it could not apply, so a
          single unmatchable record blocked *every* record behind it.

        So the reader now:

        * applies every record whose time is **at or before** the world's
          time, instead of waiting for an exact match;
        * keeps the records it cannot apply yet in a buffer, so they are
          applied as soon as the world catches up with them;
        * reads the *whole* file up front and applies the records in
          chronological order, so a record that went backwards (a rollback)
          is not lost.

        The last point matters: a rollback rewinds the world, so the
        records of the rewound frames are written *after* the records of
        the frames that came after them.  Applying them in file order would
        apply them at the wrong moment; sorting by time puts them back in
        the order the match actually happened in.
        """
        world = self.player.world
        pending = self._pending_replay_records()
        # Fill the buffer with every record of the file (if it is not
        # already in it).
        if not getattr(self, "_replay_loaded", False):
            self._replay_loaded = True
            previous = None
            while True:
                line = self._read_replay_line()
                if line is None:
                    break
                record = self._parse_replay_record(line)
                if record is None:
                    # Not a record.  It may be the continuation of a
                    # multi-line order written by the old recorder, which
                    # put a raw newline in the file.
                    record = self._parse_continuation(line, previous)
                    if record is None:
                        # A corrupted line: skip it rather than dying on it.
                        continue
                    pending.append(record)
                    # A continuation belongs to the same order string, so
                    # the *previous* record stays the same one.
                    continue
                pending.append(record)
                previous = record
            # Sort by time, keeping the file order for the records that
            # share a time (they must be applied in that order).
            pending.sort(key=lambda r: r[0])
        # Apply the records that are due.
        applied = 0
        while pending and pending[0][0] <= world.time:
            record_time, player_index, command = pending.pop(0)
            try:
                player = world.players[player_index]
            except IndexError:
                continue
            self.queue_command(player, command)
            applied += 1
        self._pending_records = pending

    def _read_replay_line(self):
        """Read one line of the replay, or ``None`` at the end of the file.

        The session may provide :meth:`replay_read_line`, which tells an
        empty line from the end of the file.  When it does not (an older
        session, or a test double), :meth:`replay_read` is used, and an
        empty string is then the end of the file.
        """
        session = self.game_session
        read_line = getattr(session, "replay_read_line", None)
        if read_line is not None:
            return read_line()
        line = session.replay_read()
        if not line:
            return None
        return line

    def _pending_replay_records(self):
        """The records that were read but not applied yet."""
        pending = getattr(self, "_pending_records", None)
        if pending is None:
            pending = []
            self._pending_records = pending
        return pending


class Coordinator(_Client):  # client coordinator for multiplayer games

    data = ""
    world = None

    def __init__(self, login, main_server, game_session):
        self.login = login
        self.main_server = main_server
        self.orders = ""
        self._all_orders = ""
        self._previous_update = time.time()
        self.game_session = game_session
        self.all_orders = [[FIRST_FPCT]]
        self.turn = 0  # com turn
        self.sub_turn = 0  # simulation frame
        # The number of simulation frames per communication turn.  In the
        # lockstep protocol it is set by the server, in every "all_orders"
        # message.  The rollback protocol has no communication turn at all:
        # the server sends inputs frame by frame, so there is exactly one
        # simulation frame per turn.  The value must exist from the start,
        # because ``_dispatch_orders`` uses it (``self.sub_turn %= self.fpct``)
        # and in rollback mode ``_give_all_orders`` — which is where the
        # lockstep protocol sets it — is never called.
        self.fpct = FIRST_FPCT
        # -- the rollback protocol ---------------------------------------
        # The session drives the simulation: it predicts, it snapshots, and
        # it repairs the world when the server contradicts a prediction.
        # It is created once the world exists (see ``_ensure_session``).
        self.rollback_session = None
        # Whether the server and this client speak the rollback protocol.
        self.rollback_enabled = False
        # The (frame, player index) pairs already written to the replay file.
        # A frame can be simulated more than once (a rollback re-simulates
        # the frames it rewound over), and the orders must not be written
        # twice.
        self._replay_written = set()
        # The authoritative inputs that arrived *before* the session could be
        # created.  The session needs the world (to snapshot it) and the
        # players (to know whose input to wait for), and neither exists when
        # the socket starts delivering messages.  Dropping those inputs would
        # make the client diverge from the server for the whole match, so
        # they are buffered here and replayed into the session as soon as it
        # exists.
        self._pending_rollback_inputs = []
        # The buffer is written by the network thread and read by the world
        # thread, so it needs a lock.
        self._pending_inputs_lock = threading.Lock()

    @property
    def clients(self):
        return self.game_session.humans

    def get_client_by_login(self, login):
        for c in self.clients:
            if c.login == login:
                return c

    # -- the rollback protocol -------------------------------------------

    def _ensure_session(self):
        """Create the rollback session, once the world is available.

        The session needs the world (to snapshot it) and the list of the
        players (to know whose input to wait for).  Both are only known
        once the game has started, so the session is created lazily.
        """
        if self.rollback_session is not None:
            return self.rollback_session
        world = self.world
        if world is None:
            return None

        players_by_login = {}
        for client in self.clients:
            player = getattr(client, "player", None)
            if player is not None:
                players_by_login[client.login] = player
        if not players_by_login:
            return None

        from .net.session import RollbackSession, SpectatorSession

        if self._is_spectator:
            # A spectator does not predict and does not roll back: it only
            # replays the authoritative inputs the server sends it.
            session = SpectatorSession(
                world=world,
                players=list(players_by_login),
                step=world.update,
                apply_inputs=self._apply_rollback_inputs,
            )
        else:
            session = RollbackSession(
                world=world,
                local_player=self.login,
                players=list(players_by_login),
                step=world.update,
                apply_inputs=self._apply_rollback_inputs,
                on_local_input=self._send_rollback_input,
            )
        self.rollback_session = session
        # The inputs that arrived before the session existed are replayed
        # into it now, in the order they were received.
        with self._pending_inputs_lock:
            pending = self._pending_rollback_inputs
            self._pending_rollback_inputs = []
        for frame, player_id, orders in pending:
            session.on_input(frame, player_id, orders)
        return session

    def _apply_rollback_inputs(self, inputs):
        """Apply one frame's inputs to the world.

        This runs on the *world* thread (it is called by the session while
        it steps the simulation), so it is the only place where orders are
        handed to the players.
        """
        for login in sorted(inputs):
            orders = inputs.get(login) or ""
            if not orders:
                continue
            player = None
            for client in self.clients:
                if client.login == login:
                    player = getattr(client, "player", None)
                    break
            if player is None:
                continue
            for order in orders.split("\n"):
                if order:
                    player.execute_command(order)
            # The replay is written here, and not in ``queue_command``:
            # the rollback protocol applies the orders itself.
            self._record_rollback_replay(login, orders)

    # -- the replay, in rollback mode -------------------------------------

    def _record_rollback_replay(self, login, orders) -> None:
        """Write one player's orders to the replay file.

        In the lockstep protocol the replay is written by
        :meth:`_Client.queue_command`, which the rollback protocol does not
        go through (its orders are applied directly, because they are
        applied per *frame* rather than per communication turn).

        The replay format is ``<world time> <player index> <order>``, and
        :class:`~soundrts.game.ReplayGame` applies a line when the world's
        time matches.

        Two things need care here.

        **One physical line per order.**  The order string may hold several
        orders, separated by newlines (a *control* order plus the *order*
        it triggers, for instance).  Writing them as one physical line
        would put a raw newline in the file, and the reader — which reads
        *lines* — would then see a continuation line without a time and a
        player index.  Parsing that line raises ``ValueError: invalid
        literal for int() with base 10: 'order'`` and the replay dies.  So
        every order gets its own line, each with its own time and player
        index.

        **The time of the frame, not the time of the world.**  A rollback
        rewinds the world and re-simulates the frames it rewound over, so
        the world's time goes *backwards* for a moment and then catches up.
        Writing ``world.time`` would therefore produce a replay whose
        timestamps are not monotonic, and the reader — which waits for the
        timestamp to match the world's time — would stall forever on the
        first record that went backwards.

        The frame number is monotonic by construction (a rollback re-uses
        the frame numbers it rewinds over, and each (frame, player) pair is
        written only once), and the frame's time is ``frame * 300`` ms.
        The time is therefore *derived from the frame* instead of read from
        the world, which makes the replay monotonic by construction.

        The tricky part is that a frame can be simulated more than once: a
        rollback rewinds the world and re-simulates the frames it rewound
        over.  Writing the replay line again would duplicate the orders, so
        every (frame, player) pair is written at most once.
        """
        if not getattr(self.game_session, "record_replay", False):
            return
        player = None
        for client in self.clients:
            if client.login == login:
                player = getattr(client, "player", None)
                break
        if player is None:
            return
        world = self.world
        if world is None:
            return
        try:
            player_index = world.players.index(player)
        except ValueError:
            return
        frame = self._rollback_current_frame()
        key = (frame, player_index)
        if key in self._replay_written:
            return
        self._replay_written.add(key)
        # The time of the frame, derived from the frame number: it is
        # monotonic by construction, even when a rollback rewinds the world.
        frame_time = frame * VIRTUAL_TIME_INTERVAL
        for order in orders.split("\n"):
            if not order:
                continue
            try:
                self.game_session.replay_write(
                    " ".join(map(str, (frame_time, player_index, order)))
                )
            except Exception:
                exception("couldn't write the replay")
                return

    def _rollback_current_frame(self) -> int:
        """The frame the world thread is currently simulating."""
        session = self.rollback_session
        if session is not None:
            return session.frame
        return 0

    # -- the unrecoverable desync ----------------------------------------

    def has_unrecoverable_desync(self) -> bool:
        """Has the client fallen too far behind to repair itself?

        This happens when the dirty frame is older than the rollback
        history window (64 frames, i.e. 19.2 s of virtual time).  The world
        the client is holding then contains a prediction the server has
        just contradicted, and it will stay wrong for the rest of the
        match.

        The client must not silently continue: it would diverge from every
        other client (and from the server) without anybody noticing.  The
        caller (the game interface) announces the desync and ends the
        match.
        """
        session = self.rollback_session
        if session is None:
            return False
        try:
            return bool(session.unrecoverable_desync)
        except Exception:
            return False

    def unrecoverable_desync_stats(self):
        """The rollback statistics, for the desync report."""
        session = self.rollback_session
        if session is None:
            return None
        try:
            return session.stats
        except Exception:
            return None

    def _send_rollback_input(self, frame: int, orders: str) -> None:
        """Send the local player's input for *frame* to the server."""
        try:
            self.main_server.write_line("input %d %s" % (frame, orders))
        except Exception:
            warning("couldn't send input for frame %s", frame)

    def submit_rollback_input(self, frame: int, orders: str) -> None:
        """Send the local player's orders for *frame* to the server.

        The orders are sent *packed* (no spaces, no newlines), because the
        protocol is line-based.
        """
        from .net.input_stream import pack_orders

        self._send_rollback_input(frame, pack_orders(orders))

    def receive_rollback_input(self, message: str) -> None:
        """Handle one authoritative input received from the server.

        This runs on the network thread.  It only *records* what the server
        said: the world is not touched here, because it lives on the world
        thread.  The session repairs the world on its next step.
        """
        from .net.input_stream import decode_input

        try:
            frame, player_id, seq, orders = decode_input(message)
        except ValueError:
            warning("malformed input from server: %r", message)
            return

        session = self.rollback_session
        if session is None:
            # The session does not exist yet (the world is not built, or the
            # players are not attached).  The input is not lost: it is
            # buffered and replayed into the session as soon as it exists.
            #
            # The session is *not* created here: it snapshots the world, and
            # that must happen on the world thread, not on the network one.
            with self._pending_inputs_lock:
                self._pending_rollback_inputs.append((frame, player_id, orders))
            return
        session.on_input(frame, player_id, orders)

    def receive_player_quit(self, login: str) -> None:
        """Handle the notification that a player left the match.

        This runs on the network thread.  The player will never send an
        input again, so the session must stop waiting for it — otherwise
        every frame would stay incomplete and the client would freeze.
        """
        session = self.rollback_session
        if session is None:
            return
        remove = getattr(session, "remove_player", None)
        if remove is None:
            return
        try:
            remove(login)
        except Exception:
            warning("couldn't drop the player %s: %s", login, traceback.format_exc())

    # communications with the client game interface

    def com_turn(self):
        return self.sub_turn == 0

    delay = 0

    def orders_are_ready(self):
        if self.rollback_enabled:
            # The rollback protocol has no barrier: the client is always
            # ready to simulate the next frame, because it predicts the
            # inputs it does not have yet.
            #
            # A spectator is the exception: it does not predict, it waits
            # for the authoritative inputs of the frame it is about to
            # replay.  It must not run ahead of them, or it would show a
            # world that does not exist.
            session = self.rollback_session
            if session is not None and hasattr(session, "has_ready_frame"):
                return session.has_ready_frame()
            return True
        return not self.com_turn() or self.all_orders

    def write_line(self, s):
        self.orders += s + "\n"

    @property
    def _is_spectator(self):
        return bool(getattr(self.game_session, "is_spectator_session", False))

    # 追帧快进阈值：旁观者积压的待处理回合数超过此值时，界面会跳过实时节流、
    # 尽快消化积压把世界追到最新；降到阈值内则恢复正常游戏速度播放。
    catch_up_buffer = 3

    def has_catch_up_backlog(self):
        """旁观者是否还有大量未处理的历史回合需要快进追帧。"""
        if not self._is_spectator:
            return False
        session = self.rollback_session
        if session is not None and hasattr(session, "pending_frames"):
            # The rollback protocol: the backlog is the number of frames
            # whose inputs have arrived but have not been replayed yet.
            return session.pending_frames() > self.catch_up_buffer
        return len(self.all_orders) > self.catch_up_buffer

    def _dispatch_orders(self):
        if self.world is None:
            # 尝试从第一个有 player 的客户端获取世界对象
            for client in self.clients:
                if hasattr(client, 'player') and client.player:
                    self.world = client.player.world
                    break
            # 如果仍然没有找到世界对象，可能是观战游戏，尝试从游戏会话获取
            if self.world is None and hasattr(self.game_session, 'world'):
                self.world = self.game_session.world
        if self.com_turn():
            # 旁观者只接收、不上报：服务器把旁观者状态设为 Spectating，
            # 不接受 orders/timeout，硬发只会被拒绝并刷服务器日志。
            if not self._is_spectator:
                if self.rollback_enabled:
                    # The rollback protocol: the local player's orders are
                    # sent as an *input* for the frame they belong to, and
                    # the client does not wait for the server.
                    session = self._ensure_session()
                    if session is not None:
                        session.submit_local(self.orders)
                else:
                    self.main_server.write_line(
                        " ".join(
                            map(
                                str,
                                (
                                    "orders",
                                    _pack(self.orders),
                                    self.get_digest(),
                                    chrono.value("ping"),
                                    chrono.value("update"),
                                    self.delay,
                                    self.interface.real_speed,
                                ),
                            )
                        )
                    )
                chrono.start("ping")
            self.orders = ""
            if not self.rollback_enabled:
                # The lockstep protocol: the server sends back the whole
                # turn ("all_orders"), which is then applied to the players.
                #
                # The rollback protocol has no such message: the server
                # sends the *inputs* one by one, and the session applies
                # them to the players itself (see ``_apply_rollback_inputs``).
                # Popping the order queue here would therefore raise an
                # IndexError, because nothing ever refills it.
                self._give_all_orders()
            self.turn += 1
        self.sub_turn += 1
        self.sub_turn %= self.fpct

    # communications with the world

    def get_digest(self):
        return "{}-{}.{}-{}".format(
            self.world.time,
            self.turn,
            self.sub_turn,
            md5(self.world.previous_state[1]).hexdigest(),
        )

    def get_sync_debug_msg_1(self):
        return "out_of_sync_error: map={} version={} platform={} python={} md5={} time={} players={} active_objects={}".format(
            self.game_session.map.name,
            VERSION,
            platform.platform(),
            sys.version.replace("\n", " "),
            self.get_digest(),
            self.world.previous_state[0],
            len(self.world.players),
            len(self.world.active_objects),
        )

    def get_sync_debug_msg_2(self):
        # 收集更详细的状态信息
        players_info = []
        for p in sorted(self.world.players, key=lambda x: x.id):
            players_info.append(f"player_{p.id}:units_{len(p.units)}:res_{':'.join(map(str, p.resources))}")
        
        return "out_of_sync_error:debug_info orders={} objects={} players_detail={}".format(
            self._all_orders, 
            self.world.previous_state[1][-150:],
            ";".join(players_info)
        )

    def get_sync_debug_msg_3(self):
        """新增第三个调试消息，包含随机数状态"""
        return "out_of_sync_error:random_state={}".format(
            str(self.world.random.getstate())[:200]  # 截断防止过长
        )

    def _give_all_orders(self):
        self._previous_update = time.time()
        all_orders = self.all_orders.pop(0)
        self.fpct = int(all_orders[0])
        players_orders = all_orders[1:]
        for player_orders in players_orders:
            player, orders = player_orders.split("/")
            client = self.get_client_by_login(player)
            if client:
                direct_player = client.player
                if direct_player:
                    orders = _unpack(orders)
                    for order in orders.split("\n"):
                        if order:
                            self.queue_command(direct_player, order)
                    if not order.startswith("control"):
                        self._all_orders += order.replace("order 0 0 ", "") + ";"
                        self._all_orders = self._all_orders[-100:]

    def update(self):
        s = self.main_server.read_line()
        if s is not None:
            args = s.split()
            if args[0] == "pong":
                chrono.stop("ping")
            elif args[0] == "all_orders":
                self.all_orders.append(args[1:])
                self.delay = time.time() - self.interface.next_update
            elif args[0] == "input":
                # An authoritative input from the server (rollback protocol).
                # The whole rest of the line is the payload.
                self.receive_rollback_input(" ".join(args[1:]))
            elif args[0] == "player_quit":
                # A player left the match (rollback protocol).  The client
                # has to stop waiting for its inputs, or it would never
                # simulate another frame.
                if len(args) >= 2:
                    self.receive_player_quit(args[1])
            elif args[0] == "spectate_success":
                # 大厅在 start_spectating 之后才发这条；旁观主循环已经接管套接字，
                # 菜单回调到不了。不是错误，静默丢掉即可。
                pass
            elif args[0] in ("spectator_joined", "spectator_left"):
                if len(args) >= 2:
                    self.push(args[0], args[1])
            elif args[0] == "synchronization_error":
                if IS_DEV_VERSION:
                    # 在开发版本中，保存更详细的调试信息
                    debug_filename_1 = "user/tmp/{}-{}.txt".format(
                        self.world.previous_state[0],
                        md5(self.world.previous_state[1]).hexdigest(),
                    )
                    debug_filename_2 = "user/tmp/{}-{}.txt".format(
                        self.world.previous_previous_state[0],
                        md5(self.world.previous_previous_state[1]).hexdigest(),
                    )
                    
                    open(debug_filename_1, "bw").write(self.world.previous_state[1])
                    open(debug_filename_2, "bw").write(self.world.previous_previous_state[1])
                    
                    # 保存详细调试信息到文本文件
                    debug_info_file = f"user/tmp/sync_debug_{self.world.previous_state[0]}.txt"
                    with open(debug_info_file, "w", encoding="utf-8") as f:
                        f.write(self.get_sync_debug_msg_1() + "\n")
                        f.write(self.get_sync_debug_msg_2() + "\n")
                        f.write(self.get_sync_debug_msg_3() + "\n")
                else:
                    try:
                        send_error_to_metaserver(self.get_sync_debug_msg_1())
                        send_error_to_metaserver(self.get_sync_debug_msg_2())
                        send_error_to_metaserver(self.get_sync_debug_msg_3())
                    except:
                        exception("error sending sync debug data")
            else:
                warning("ignored data from server: %s", s)
        # check for timeout and alert server
        # 旁观者不参与回合同步，也不应触发服务器的超时检查（且 Spectating 状态
        # 根本不接受 timeout 命令），因此跳过。
        if time.time() > self._previous_update + 5.0:
            if not self._is_spectator:
                self.main_server.write_line("timeout")
            self._previous_update += 5.0
