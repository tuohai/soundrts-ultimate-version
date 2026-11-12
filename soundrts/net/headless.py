"""Headless multiplayer harness: two (or three) clients over real TCP.

Why this module exists
----------------------

The rollback netcode is the riskiest part of the multiplayer stack: it
predicts remote inputs, rewinds the world when the server contradicts the
prediction, and re-simulates the frames it rewound over.  The existing unit
tests drive the pieces in-process, one at a time.  They are fast and
precise, but they never exercise the *whole* chain: a real socket, the real
server, the real wire format, and two clients simulating at the same time.

This module provides that chain, without a UI:

* :class:`HeadlessServer` — the real
  :class:`soundrts.servermain.Server`, bound to an ephemeral port on the
  loopback interface, and pumped by the test instead of by
  ``asyncore.loop()``.  It registers with no metaserver and never opens a
  UDP discovery socket.
* :class:`HeadlessConnection` — a real TCP socket that speaks the real
  line protocol (the ``:`` prompt, the ``login`` line, the ``ok!``
  acknowledgement).  It can hold the lines back, which is how the "high
  latency" scenario is built.
* :class:`HeadlessClient` — a real client: a real
  :class:`soundrts.worldclient.Coordinator`, a real
  :class:`soundrts.net.session.RollbackSession` (or
  :class:`~soundrts.net.session.SpectatorSession`), and a real
  :class:`soundrts.world.World`.

What is *not* simulated
-----------------------

Nothing that matters for the netcode.  The only thing replaced is the
Pygame interface: the coordinator normally gets an ``interface`` object
from ``clientgame.GameInterface``, and the harness gives it a stub whose
``queue_srv_event`` does nothing.  The stub still exists, so
``Player.is_local_human()`` keeps its real meaning — it is ``True`` for the
local player only — exactly like in a real match.

The stub does not touch the simulation: ``World.update()`` only *pushes* the
"voila" event to the local human, and pushing is a display concern.  It
does not consume the world RNG, so the two clients' simulations stay
bit-identical even though only one of them has a local human.

The client setup mirrors :meth:`soundrts.game.MultiplayerGame._clients`:
the local player *is* the coordinator, and every other player is a
:class:`soundrts.worldclient.RemoteClient`.  That matters for
determinism: ``populate_map`` assigns the starting positions to the
clients in list order, so the list must be in the same order on every side.

The frame loop
--------------

One frame of the match is three phases, and the order matters:

1. **act** — every player stages its orders, and the coordinator dispatches
   them: the local input goes on the wire, for the frame that is about to
   be simulated;
2. **travel** — the inputs are flushed, the server stamps them and
   broadcasts them, and the clients read what arrived;
3. **simulate** — every client simulates the frame.

With no latency, phase 2 delivers the remote input *before* phase 3, so the
client does not have to predict and never rolls back.  With latency, the
remote input arrives late: the client predicted it as idle, and when the
truth arrives the session rewinds and re-simulates.  That is the rollback.

Determinism rules the harness obeys
-----------------------------------

* every client builds its world from the *same* seed and the *same* map
  bytes, and the players are created in the *same* order;
* the local player's client is the coordinator itself, and the players list
  is the same on both sides;
* orders are applied in the frame they belong to, on every client.

Under those rules the two worlds must produce the same
:func:`soundrts.net.snapshot.strong_digest`.
"""

from __future__ import annotations

import os
import socket
import sys
import time
import warnings
from typing import Callable, Dict, List, Optional, Sequence

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [_saved_argv[0] if _saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.batteries import asyncore
    from soundrts.lib.resource import res
    from soundrts.mapfile import Map
    from soundrts.net.snapshot import strong_digest
    from soundrts.servermain import Server
    from soundrts.version import (
        ROLLBACK_PROTOCOL,
        compatibility_version,
        protocol_token,
    )
    from soundrts.world import World
    from soundrts.worldclient import Coordinator, RemoteClient

sys.argv = _saved_argv

__all__ = [
    "HeadlessServer",
    "HeadlessConnection",
    "HeadlessClient",
    "HeadlessMatch",
    "StubInterface",
    "MatchClock",
    "load_resources",
    "default_triggers",
    "match_digest",
]


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

_loaded = False


def load_resources() -> None:
    """Load the rules and the AI, once, in a reproducible way.

    The tests must not depend on whatever the developer's configuration
    file says, so the mods layer is cleared before the rules are loaded.
    """
    global _loaded
    if _loaded:
        return
    try:
        config.mods = ""
    except Exception:
        pass
    res.set_mods("")
    res.load_rules_and_ai()
    _loaded = True


def default_triggers():
    """The triggers a real multiplayer game starts with.

    This is :attr:`soundrts.game._MultiplayerGame.default_triggers`, copied
    here so the harness does not have to import the whole game module (which
    pulls in Pygame).
    """
    return [
        ("players", ["no_enemy_player_left"], ["victory"]),
        ("players", ["no_building_left"], ["defeat"]),
        ("computers", ["no_unit_left"], ["defeat"]),
    ]


# ---------------------------------------------------------------------------
# The match digest
# ---------------------------------------------------------------------------


class _WithoutPureSpectators:
    """A view of a world whose pure spectator player is hidden.

    A spectator's world holds one extra player — the "pure spectator",
    which exists only so the spectator can browse the map.  It is not part
    of the match, so it must not be part of the comparison.  This proxy
    hides it and lets :func:`soundrts.net.snapshot.strong_digest` compute
    the digest of the *match* state.
    """

    def __init__(self, world):
        self._world = world

    @property
    def players(self):
        return [
            p
            for p in self._world.players
            if not getattr(p, "_is_pure_spectator", False)
        ]

    def __getattr__(self, name):
        return getattr(self._world, name)


def match_digest(world) -> str:
    """The digest of the *match* state of *world*.

    Same as :func:`soundrts.net.snapshot.strong_digest`, but the pure
    spectator player (which only a spectator's world has) is left out, so
    that a spectator's world and the players' worlds can be compared
    directly.
    """
    return strong_digest(_WithoutPureSpectators(world))


# ---------------------------------------------------------------------------
# The clock
# ---------------------------------------------------------------------------


class MatchClock:
    """The frame counter of the match, shared by every connection.

    The latency injection is expressed in *frames*, not in seconds: a
    connection holds a line back until the clock has advanced far enough.
    That makes the "high latency" scenario exactly reproducible — the same
    test always produces the same rollback depth.
    """

    def __init__(self):
        self.frame = 0


# ---------------------------------------------------------------------------
# The server
# ---------------------------------------------------------------------------


class HeadlessServer:
    """The real server, on an ephemeral loopback port, pumped by the test.

    The server is the real :class:`soundrts.servermain.Server`: the same
    login handshake, the same room logic, the same input stream.  Only the
    two things that would reach outside the machine are left out:

    * the metaserver registration (``no_metaserver``), and
    * the UDP discovery thread.

    The socket is bound to ``127.0.0.1`` on port ``0``, so the OS picks a
    free port.  That makes the harness immune to port collisions, and it
    avoids the wildcard bind that makes Windows ask for a firewall rule.

    The server is *not* started in a thread: :meth:`pump` drives it, so the
    test decides exactly when the server runs, and the test can never race
    with it.
    """

    def __init__(self, login: str = "testserver"):
        load_resources()
        self.parameters = ["no_metaserver"]
        # The real server, bound to an ephemeral loopback port.
        self.server = Server(
            self.parameters, is_standalone=True, host="127.0.0.1", port=0
        )
        self.server.login = login
        self.host, self.port = self.server.socket.getsockname()[:2]

    def pump(self, timeout: float = 0.0) -> None:
        """Let the server process whatever is waiting on its sockets."""
        asyncore.poll(timeout)

    def close(self) -> None:
        try:
            for client in list(self.server.clients):
                try:
                    client.close()
                except Exception:
                    pass
            self.server.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# The client connection
# ---------------------------------------------------------------------------


class HeadlessConnection:
    """A real TCP connection to the server, speaking the real protocol.

    The handshake is the one the game uses: the server sends ``:``, the
    client answers with ``login <compatibility> <login> <protocol>``, and
    the server answers ``ok!``.

    Latency injection
    -----------------

    ``incoming_delay_frames`` and ``outgoing_delay_frames`` hold the lines
    back instead of sending them right away.  A line held back by *N*
    frames is delivered when the match clock has advanced *N* frames.  That
    is what makes the remote inputs arrive late — and therefore what makes
    the client predict, and then roll back.

    ``incoming_delay`` and ``outgoing_delay`` add a wall-clock delay on
    top, for the tests that want a realistic, jittery link.
    """

    def __init__(
        self,
        host: str,
        port: int,
        login: str,
        clock: MatchClock,
        protocol: str = ROLLBACK_PROTOCOL,
        incoming_delay_frames: int = 0,
        outgoing_delay_frames: int = 0,
        incoming_delay: float = 0.0,
        outgoing_delay: float = 0.0,
        server_pump: Optional[Callable[[], None]] = None,
    ):
        self.login = login
        self.protocol = protocol
        self.clock = clock
        self.incoming_delay_frames = incoming_delay_frames
        self.outgoing_delay_frames = outgoing_delay_frames
        self.incoming_delay = incoming_delay
        self.outgoing_delay = outgoing_delay
        # The server is not started in a thread: the test drives it.  The
        # connection therefore has to be able to ask the server to poll,
        # or the handshake would wait forever for a server that is not
        # running yet.
        self._server_pump = server_pump
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(5.0)
        self._sock.connect((host, port))
        self._sock.setblocking(False)
        self._in_buffer = b""
        self._ready: List[str] = []
        self._pending_in: List[tuple] = []  # (release_frame, release_at, line)
        self._out_buffer: List[tuple] = []  # (release_frame, release_at, bytes)
        self._closed = False
        self.received: List[str] = []
        self.server_client = None
        self._do_handshake()

    # -- the handshake ---------------------------------------------------

    def _read_until(self, marker: bytes, timeout: float = 5.0) -> bytes:
        deadline = time.time() + timeout
        while marker not in self._in_buffer:
            if time.time() > deadline:
                raise TimeoutError(
                    "handshake timed out waiting for %r (got %r)"
                    % (marker, self._in_buffer[:200])
                )
            if self._server_pump is not None:
                self._server_pump()
            self._pump_in()
            time.sleep(0.002)
        index = self._in_buffer.find(marker)
        head = self._in_buffer[: index + len(marker)]
        self._in_buffer = self._in_buffer[index + len(marker):]
        return head

    def _do_handshake(self) -> None:
        # The server greets with ":".
        self._read_until(b":")
        token = protocol_token(self.protocol)
        self._sock.sendall(
            (
                "login %s %s %s\n"
                % (compatibility_version(), self.login, token)
            ).encode("utf-8")
        )
        self._read_until(b"ok!")

    # -- the wire --------------------------------------------------------

    def _pump_in(self) -> None:
        try:
            data = self._sock.recv(65536)
        except BlockingIOError:
            return
        except OSError:
            self._closed = True
            return
        if not data:
            self._closed = True
            return
        self._in_buffer += data

    def write_line(self, line: str) -> None:
        """Queue one line for the server.

        The latency injection only applies to the *match* traffic (the
        ``input`` lines).  The lobby commands (create, register, start)
        must not be delayed: the handshake of the room would then depend
        on the frame clock, which does not move before the match starts.
        """
        delayed = self.incoming_delay_frames or self.incoming_delay
        if line.startswith("input ") and delayed:
            self._out_buffer.append(self._stamp(line.encode("utf-8") + b"\n"))
            return
        self._out_buffer.append(
            (self.clock.frame, time.time(), line.encode("utf-8") + b"\n")
        )

    def _stamp(self, payload: bytes) -> tuple:
        """When does *payload* become deliverable?"""
        release_frame = self.clock.frame + self.outgoing_delay_frames
        release_at = time.time() + self.outgoing_delay
        return (release_frame, release_at, payload)

    def flush(self) -> None:
        """Put the pending outgoing lines on the wire.

        A line waits until both its frame deadline and its wall-clock
        deadline have passed.
        """
        now = time.time()
        ready = []
        still_pending = []
        for release_frame, release_at, payload in self._out_buffer:
            if release_frame <= self.clock.frame and release_at <= now:
                ready.append(payload)
            else:
                still_pending.append((release_frame, release_at, payload))
        self._out_buffer = still_pending
        for payload in ready:
            try:
                self._sock.sendall(payload)
            except OSError:
                self._closed = True
                return

    def _split_buffer(self) -> List[str]:
        """Take the complete lines out of the socket buffer."""
        lines = []
        while b"\n" in self._in_buffer:
            data, self._in_buffer = self._in_buffer.split(b"\n", 1)
            for line in data.decode("utf-8", errors="replace").split("\r"):
                if line:
                    lines.append(line)
        return lines

    def read_lines(self) -> List[str]:
        """Return the lines that are ready to be read right now."""
        now = time.time()
        lines = list(self._ready)
        self._ready = []
        due = []
        still_pending = []
        for release_frame, release_at, line in self._pending_in:
            if release_frame <= self.clock.frame and release_at <= now:
                due.append(line)
            else:
                still_pending.append((release_frame, release_at, line))
        self._pending_in = still_pending
        lines.extend(due)
        self.received.extend(lines)
        return lines

    def poll(self) -> List[str]:
        """Move the bytes around and return whatever is ready."""
        if self._server_pump is not None:
            self._server_pump()
        self._pump_in()
        for line in self._split_buffer():
            delayed = self.incoming_delay_frames or self.incoming_delay
            if delayed and line.startswith("input "):
                release_frame = self.clock.frame + self.incoming_delay_frames
                release_at = time.time() + self.incoming_delay
                self._pending_in.append((release_frame, release_at, line))
            else:
                self._ready.append(line)
        return self.read_lines()

    def has_pending(self) -> bool:
        """Is anything still in flight (in either direction)?"""
        return bool(self._pending_in or self._out_buffer or self._in_buffer)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------


class StubInterface:
    """A stand-in for the Pygame interface.

    ``Player.is_local_human()`` is ``hasattr(self.client, "interface")``, so
    the stub has to exist for the local player — that is what keeps the
    local-human behaviour identical to a real match.  The stub itself does
    nothing: it only swallows the display events the world pushes.
    """

    real_speed = 1.0
    next_update = 0.0

    def __init__(self):
        self.events: List[tuple] = []

    def queue_srv_event(self, *args) -> None:
        self.events.append(args)

    def get_digest(self):
        return ""


class _GameSession:
    """The game session the coordinator expects.

    It is the little the coordinator reads from: the list of the players of
    the match, whether this is a spectator session, and whether the replay
    has to be recorded.
    """

    def __init__(self, clients, is_spectator: bool):
        self.humans = list(clients)
        self.is_spectator_session = is_spectator
        self.record_replay = False
        self.allow_cheatmode = False
        self.world = None
        self.local_client = None


class HeadlessClient:
    """One real client, playing over a real socket.

    The client owns:

    * a :class:`HeadlessConnection` (the socket);
    * a :class:`soundrts.worldclient.Coordinator` (the real client logic);
    * a real :class:`soundrts.world.World`, built from the map the server
      sent;
    * the real rollback session, created by the coordinator itself.

    The coordinator is passed in, because the client *is* the coordinator
    in a real match: the local player's client object is the coordinator
    itself, and it is the one that owns the player (and therefore the
    ``interface`` that makes it a local human).
    """

    def __init__(
        self,
        connection: HeadlessConnection,
        world: World,
        clients: Sequence,
        local_login: str,
        is_spectator: bool = False,
        coordinator: Optional[Coordinator] = None,
        session: Optional[_GameSession] = None,
    ):
        self.connection = connection
        self.login = local_login
        self.is_spectator = is_spectator
        self.world = world
        self.clients = list(clients)

        if coordinator is None:
            session = _GameSession(self.clients, is_spectator)
            coordinator = Coordinator(local_login, connection, session)
        if session is None:
            session = coordinator.game_session
        self.session = session
        self.coordinator = coordinator
        self.coordinator.rollback_enabled = True
        self.coordinator.world = world
        # The local player gets the (stub) interface, so that
        # ``is_local_human()`` is true for it and false for the others.
        if getattr(self.coordinator, "interface", None) is None:
            self.coordinator.interface = StubInterface()
        self.stub = self.coordinator.interface
        self.session.world = world
        self.session.local_client = self.coordinator
        # Create the session now, before the first frame: it takes the
        # initial snapshot of the world.
        self.rollback_session = self.coordinator._ensure_session()

    # -- the frame loop --------------------------------------------------

    def submit(self, orders: str) -> None:
        """Stage the local player's orders for the next frame."""
        if orders:
            self.coordinator.write_line(orders)

    def dispatch(self) -> None:
        """Dispatch the staged orders: the local input goes on the wire.

        This is what the real interface does when it asks for an update:
        ``get_orders()`` dispatches the staged commands, and in rollback
        mode the coordinator submits the local player's input for the frame
        that is about to be simulated.
        """
        self.coordinator.get_orders()

    def drain_network(self) -> List[str]:
        """Read whatever the server sent, and feed it to the coordinator."""
        lines = self.connection.poll()
        for line in lines:
            args = line.split()
            if not args:
                continue
            if args[0] == "input":
                self.coordinator.receive_rollback_input(" ".join(args[1:]))
            elif args[0] == "player_quit":
                if len(args) >= 2:
                    self.coordinator.receive_player_quit(args[1])
        return lines

    def simulate(self) -> bool:
        """Simulate one frame.

        Returns ``True`` when the frame was simulated normally, ``False``
        when a rollback happened first.
        """
        session = self.rollback_session
        if session is None:
            return False
        return session.step()

    def repair(self) -> bool:
        """Repair the world if the server contradicted the prediction.

        A spectator never predicts, so it never has to repair: its
        :class:`~soundrts.net.session.SpectatorSession` has no such
        method.  The method exists here so that the match can treat every
        client the same way.
        """
        session = self.rollback_session
        if session is None:
            return False
        repair = getattr(session, "repair", None)
        if repair is None:
            return False
        return repair()

    # -- introspection ---------------------------------------------------

    @property
    def frame(self) -> int:
        session = self.rollback_session
        return session.frame if session is not None else -1

    @property
    def stats(self):
        session = self.rollback_session
        return session.stats if session is not None else None

    def digest(self) -> str:
        return match_digest(self.world)


# ---------------------------------------------------------------------------
# The match
# ---------------------------------------------------------------------------


class HeadlessMatch:
    """A whole match: a server, and the clients that play on it.

    The flow is the one the game uses:

    1. the host creates the room;
    2. the guest registers for it;
    3. the host starts the game;
    4. both clients receive ``start_game``, build their world from the map
       the server sent, and create their rollback session.

    The map travels over the wire exactly like in a real game: the server
    packs it (:func:`soundrts.pack.pack_buffer`) and the client unpacks it
    (:meth:`soundrts.lib.resource.res.unpack_map`).
    """

    def __init__(
        self,
        map_name: str = "jl1",
        logins: Sequence[str] = ("host", "guest"),
        seed: int = 1234,
        incoming_delay_frames: int = 0,
        outgoing_delay_frames: int = 0,
        incoming_delay: float = 0.0,
        outgoing_delay: float = 0.0,
    ):
        load_resources()
        self.map = self._find_map(map_name)
        self.logins = list(logins)
        self.seed = seed
        self.clock = MatchClock()
        self.server = HeadlessServer()
        self.connections: Dict[str, HeadlessConnection] = {}
        self.clients: Dict[str, HeadlessClient] = {}
        self.worlds: Dict[str, World] = {}
        self.spectators: Dict[str, HeadlessClient] = {}
        self.rooms: List[int] = []
        self._incoming_delay_frames = incoming_delay_frames
        self._outgoing_delay_frames = outgoing_delay_frames
        self._incoming_delay = incoming_delay
        self._outgoing_delay = outgoing_delay

    @staticmethod
    def _find_map(map_name: str) -> Map:
        for candidate in res.multiplayer_maps():
            if candidate.name == map_name:
                return candidate
        for candidate in res.multiplayer_maps():
            if map_name in candidate.name:
                return candidate
        raise LookupError("no multiplayer map named %r" % map_name)

    # -- the setup -------------------------------------------------------

    def connect(self, login: str) -> HeadlessConnection:
        """Connect one client and log it in."""
        connection = HeadlessConnection(
            self.server.host,
            self.server.port,
            login,
            clock=self.clock,
            protocol=ROLLBACK_PROTOCOL,
            incoming_delay_frames=self._incoming_delay_frames,
            outgoing_delay_frames=self._outgoing_delay_frames,
            incoming_delay=self._incoming_delay,
            outgoing_delay=self._outgoing_delay,
            server_pump=self.pump,
        )
        self.connections[login] = connection
        return connection

    def pump(self) -> None:
        """Move every byte in the system.

        The server is not running in a thread, so the test drives it.  The
        pump flushes the clients' outgoing buffers first (a client that
        wrote a line must actually put it on the wire), then lets the
        server process what arrived.

        The server is pumped *twice* on purpose.  The first pass reads the
        clients' inputs and broadcasts them, but the broadcast is only
        *queued* in the server's socket at that point: ``asyncore`` writes
        the pending buffer during the next poll.  The second pass is the
        one that actually puts the broadcast on the wire, so that the
        client can read it before it simulates the frame.  Without it, the
        client would sometimes miss the remote input and predict it —
        which is a rollback in the making, and would make the "no latency,
        no rollback" scenario flaky.
        """
        for connection in list(self.connections.values()):
            connection.flush()
        self.server.pump(0.0)
        self.server.pump(0.0)

    def _state_name(self, connection: HeadlessConnection) -> str:
        for client in self.server.server.clients:
            if client.login == connection.login:
                return client.state.__class__.__name__
        return ""

    def setup_room(self) -> int:
        """Create the room, register the guests, and start the game.

        The seed is *pinned* before the game starts.  The server picks a
        random seed when it starts a match, which would make every run
        different — and a test that compares two runs would then be
        comparing two different worlds.  Pinning it makes the match
        reproducible, which is what the tests need.

        The pin uses the same attribute the random-map generator uses
        (``rmg_seed``), so nothing else about the room changes.
        """
        host = self.connections[self.logins[0]]
        guest = self.connections[self.logins[1]]

        # The host creates the room.  The server sends the map, so the
        # client knows what it is about to play.
        host.write_line("create %s 1" % self.map.name)
        if not self._wait_for(lambda: self._state_name(host) == "OrganizingAGame"):
            raise TimeoutError("the host could not create the room")
        game = self._game_of(host)
        game_id = game.id
        game.rmg_seed = self.seed

        # The guest registers for the room.
        guest.write_line("register %d" % game_id)
        if not self._wait_for(
            lambda: self._state_name(guest) == "WaitingForTheGameToStart"
        ):
            raise TimeoutError("the guest could not register")

        # The host starts the game.
        host.write_line("start")
        if not self._wait_for(lambda: self._state_name(host) == "Playing"):
            raise TimeoutError("the game did not start")
        self.rooms.append(game_id)
        return game_id

    def _wait_for(self, predicate: Callable[[], bool], timeout: float = 5.0) -> bool:
        """Pump the whole system until *predicate* is true."""
        deadline = time.time() + timeout
        while True:
            if predicate():
                return True
            if time.time() > deadline:
                return False
            self.pump()
            time.sleep(0.001)

    def _game_of(self, connection: HeadlessConnection):
        """The room *connection* is in (or ``None``)."""
        for client in self.server.server.clients:
            if client.login == connection.login:
                return getattr(client, "game", None)
        return None

    # -- building the worlds ---------------------------------------------

    def build_worlds(self) -> None:
        """Build the world of every client, from the map the server sent.

        The map is unpacked from the wire payload, exactly like the real
        client does, so the world is built from the same bytes on every
        side.  The *seed* and the *player roster* come from the server's
        ``start_game`` line, exactly like the real client reads them: the
        server is the only authority on what the match is.

        The local player is the coordinator itself, exactly like in a real
        match, so that it is the only local human of its world.
        """
        payloads = {}
        starts = {}
        for login in self.logins:
            connection = self.connections[login]
            payloads[login], starts[login] = self._wait_for_start(connection)

        for login in self.logins:
            connection = self.connections[login]
            map_obj = res.unpack_map(payloads[login], save=False)
            players_pack, seed = starts[login]
            session = _GameSession([], is_spectator=False)
            coordinator = Coordinator(login, connection, session)
            coordinator.interface = StubInterface()
            # The roster is the server's, in the server's order.  The local
            # player is the coordinator; the others are remote clients.
            clients = []
            for other_login, alliance, faction in players_pack:
                if other_login == login:
                    client = coordinator
                else:
                    client = RemoteClient(other_login)
                client.alliance = alliance
                client.faction = faction
                clients.append(client)
            world = World(default_triggers(), seed)
            world.load_and_build_map(map_obj)
            world.populate_map(clients, equivalents=True)
            coordinator.world = world
            session.humans = list(clients)
            session.world = world
            session.local_client = coordinator
            coordinator.rollback_enabled = True
            self.worlds[login] = world
            self.clients[login] = HeadlessClient(
                connection,
                world,
                clients,
                login,
                coordinator=coordinator,
                session=session,
            )

    def _wait_for_start(self, connection: HeadlessConnection):
        """Wait for the ``map`` and ``start_game`` lines, and return them.

        The ``start_game`` line is ``<players> <local login> <seed>
        <speed> <treaty> <is coop> ...``; the roster and the seed are what
        the client needs to rebuild the match.
        """
        map_payload = None
        start_args = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            for line in connection.poll():
                if line.startswith("map "):
                    map_payload = line[4:].encode("utf-8")
                elif line.startswith("start_game "):
                    start_args = line.split(" ")[1:]
            if map_payload is not None and start_args is not None:
                break
            time.sleep(0.002)
        if map_payload is None or start_args is None:
            raise TimeoutError(
                "no start_game received by %s (map=%s)"
                % (connection.login, map_payload is not None)
            )
        # The players come first; the seed is the fourth field.
        players = []
        for entry in start_args[0].split(";"):
            if not entry:
                continue
            parts = entry.split(",")
            if len(parts) >= 3:
                players.append((parts[0], parts[1], parts[2]))
        seed = int(start_args[2])
        return map_payload, (players, seed)

    # -- the spectator ---------------------------------------------------

    def add_spectator(self, login: str = "watcher") -> HeadlessClient:
        """A spectator joins the running match, and catches up.

        The spectator goes through the real path: it logs in, sends
        ``spectate <game id>``, and the server sends it the protocol, the
        player list, the seed and the whole input history.  The spectator
        then replays the history, one frame at a time, with the real
        :class:`soundrts.net.session.SpectatorSession`.
        """
        connection = self.connect(login)
        game_id = self.rooms[-1] if self.rooms else self._first_game_id()
        connection.write_line("spectate %d" % game_id)

        # The server sends "protocol", "start_spectating" and then the
        # whole input history.
        start_args = None
        history: List[str] = []
        deadline = time.time() + 5.0
        while time.time() < deadline:
            for line in connection.poll():
                if line.startswith("start_spectating "):
                    start_args = line.split(" ")[1:]
                elif line.startswith("input "):
                    history.append(line[len("input "):])
            if start_args is not None and history:
                break
            time.sleep(0.002)
        if start_args is None:
            raise TimeoutError("the spectator did not get the match description")

        seed, players = self._parse_spectator_args(start_args)
        world, clients = self._build_spectator_world(players, seed)
        spectator = HeadlessClient(
            connection, world, clients, login, is_spectator=True
        )
        self.spectators[login] = spectator
        # The pure spectator player: exactly what the real spectator has.
        self._create_pure_spectator(spectator)
        # Replay the history the server sent.
        for payload in history:
            spectator.coordinator.receive_rollback_input(payload)
        return spectator

    def _first_game_id(self) -> int:
        for game in self.server.server.games:
            return game.id
        raise LookupError("no game on the server")

    def _parse_spectator_args(self, args: List[str]):
        """Parse the ``start_spectating`` line.

        The format is ``<packed players> <map name...> <speed> <seed>
        <treaty> <enemy hp %> <enemy damage %>``.  The map name may contain
        spaces, so the trailing numbers are located from the end — exactly
        like :meth:`soundrts.clientservermenu.RoomListMenu.srv_start_spectating`
        does.
        """
        if len(args) >= 7:
            seed = int(args[-4])
        elif len(args) >= 5:
            seed = int(args[-2])
        else:
            seed = 0
        packed = args[0]
        players = []
        for entry in packed.split(";"):
            if not entry:
                continue
            parts = entry.split(",")
            if len(parts) >= 3:
                players.append((parts[0], parts[1], parts[2]))
        return seed, players

    def _build_spectator_world(self, players, seed: int):
        """The spectator's world: the same players, the same seed."""
        map_obj = self._find_map(self.map.name)
        clients = []
        for login, alliance, faction in players:
            client = RemoteClient(login)
            client.alliance = alliance
            client.faction = faction
            clients.append(client)
        world = World(default_triggers(), seed)
        world.load_and_build_map(map_obj)
        world.populate_map(clients, equivalents=True)
        return world, clients

    def _create_pure_spectator(self, spectator: HeadlessClient) -> None:
        """Add the "pure spectator" player, exactly like the real game does.

        The real code lives in
        :meth:`soundrts.game.SpectatorGame._create_spectator_player`; it is
        reused here so that the spectator's world is built the same way.
        """
        from soundrts.game import SpectatorGame

        class _Shim:
            world = spectator.world
            spectator_client = spectator.coordinator

        SpectatorGame._create_spectator_player(_Shim())

    def catch_up_spectator(self, login: str = "watcher", max_frames: int = 5000) -> int:
        """Replay the frames the spectator has, until it catches up.

        The spectator can only replay a frame once *every* player has
        answered it, so the loop keeps reading from the socket until the
        next frame is complete.
        """
        spectator = self.spectators[login]
        session = spectator.rollback_session
        replayed = 0
        while replayed < max_frames:
            spectator.drain_network()
            if not session.has_ready_frame():
                # The next frame is not complete yet: read more.
                self.pump()
                if not spectator.connection.has_pending():
                    break
                time.sleep(0.002)
                continue
            session.step()
            replayed += 1
        return replayed

    # -- running ---------------------------------------------------------

    def run_frames(
        self,
        nb_frames: int,
        orders: Optional[Dict[int, Dict[str, str]]] = None,
    ) -> None:
        """Run *nb_frames* frames on every client.

        ``orders`` maps a frame number to a ``{login: orders}`` dict.  The
        orders are staged on the right client before the frame is
        simulated, exactly like a real player pressing a key.

        The spectators are stepped too: they replay the authoritative
        inputs as they arrive, which is how they keep up with the match.
        """
        orders = orders or {}
        for frame in range(nb_frames):
            frame_orders = orders.get(frame, {})
            # Phase 1: the players act.
            for login in self.logins:
                client = self.clients.get(login)
                if client is None:
                    continue
                client.submit(frame_orders.get(login, ""))
            for login in self.logins:
                client = self.clients.get(login)
                if client is None:
                    continue
                client.dispatch()
            # Phase 2: the inputs travel.
            self.pump()
            for login in self.logins:
                client = self.clients.get(login)
                if client is None:
                    continue
                client.drain_network()
            # Phase 3: the clients simulate.
            for login in self.logins:
                client = self.clients.get(login)
                if client is None:
                    continue
                client.simulate()
            # The spectators replay what arrived, one frame at a time.
            for spectator in self.spectators.values():
                self._step_spectator(spectator)
            self.clock.frame += 1

    @staticmethod
    def _step_spectator(spectator: HeadlessClient) -> int:
        """Read the spectator's inputs and replay the frames it can.

        A spectator never predicts: it replays the authoritative inputs as
        they arrive, and only a frame every player has answered can be
        replayed.
        """
        session = spectator.rollback_session
        replayed = 0
        while replayed < 1000:
            spectator.drain_network()
            if not session.has_ready_frame():
                break
            session.step()
            replayed += 1
        return replayed

    def drain(self, max_rounds: int = 500) -> None:
        """Let every client consume everything the server has sent.

        After the last frame, the authoritative inputs are still in flight.
        The clients have to receive them and repair their worlds, so that
        they end up on the same, authoritative state.

        The clock is pushed forward first, so that the lines held back by
        the latency injection are released.
        """
        # Release everything that is still held back.
        self.clock.frame += max(
            1,
            self._incoming_delay_frames + self._outgoing_delay_frames + 2,
        )
        for _ in range(max_rounds):
            self.pump()
            progressed = False
            for client in list(self.clients.values()) + list(self.spectators.values()):
                if client.drain_network():
                    progressed = True
            for client in list(self.clients.values()) + list(self.spectators.values()):
                if client.repair():
                    progressed = True
            pending = any(
                connection.has_pending()
                for connection in self.connections.values()
            )
            if not pending and not progressed:
                break
            time.sleep(0.002)
        # A final repair pass, so the last inputs are applied.
        for client in list(self.clients.values()) + list(self.spectators.values()):
            for _ in range(4):
                client.repair()

    def disconnect(self, login: str) -> None:
        """Drop a player: the socket is closed, like a network failure."""
        connection = self.connections.get(login)
        if connection is None:
            return
        connection.close()
        # Let the server notice.
        self._wait_for(
            lambda: self._state_name(connection) != "Playing", timeout=5.0
        )

    def digests(self) -> Dict[str, str]:
        result = {login: client.digest() for login, client in self.clients.items()}
        for login, spectator in self.spectators.items():
            result[login] = spectator.digest()
        return result

    def close(self) -> None:
        for connection in self.connections.values():
            connection.close()
        self.server.close()
