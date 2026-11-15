# -*- coding: utf-8 -*-
"""End-to-end test of the lockstep multiplayer path.

The rollback netcode was removed in 1.5.2.1, so the multiplayer protocol
is the classic deterministic lockstep one.  The unit tests in
``test_net_protocol.py`` cover the pieces (the login line, the ``Orders``
barrier).  This test covers the **whole chain** over **real loopback
sockets**, because that is the only way to know the surgery did not break
the wire format:

  * two clients log in with the plain ``<version> <login>`` line;
  * the host creates the room, the guest registers for it, the host
    starts the game;
  * both clients receive ``map`` and ``start_game`` and build their world
    from the bytes the server sent;
  * both clients answer every communication turn with their orders, the
    server broadcasts ``all_orders`` (the lockstep turn), and the worlds
    advance;
  * at the end the two worlds have the **same** digest.

The digest covers every player's resources and every unit's id and
position, so "the same digest" means "the two simulations agree".
"""

from __future__ import annotations

import hashlib
import logging
import os
import socket
import sys
import threading
import time
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.batteries import asyncore
    from soundrts.lib.resource import res
    from soundrts.servermain import Server
    from soundrts.version import compatibility_version
    from soundrts.world import World
    from soundrts.worldclient import Coordinator, RemoteClient

sys.argv = saved

logging.disable(logging.WARNING)


class _StubInterface:
    """The stub the coordinator needs instead of the Pygame interface.

    ``Player.is_local_human()`` is ``hasattr(self.client, "interface")``,
    so the stub has to exist for the local player -- that is what keeps the
    local-human behaviour identical to a real match.
    """

    real_speed = 1.0
    next_update = 0.0

    def __init__(self):
        self.events = []

    def queue_srv_event(self, *args):
        self.events.append(args)

    def get_digest(self):
        return ""


class _Session:
    """The bits of the game session the coordinator reads."""

    def __init__(self, humans):
        self.humans = list(humans)
        self.world = None
        self.local_client = None
        self.record_replay = False
        self.is_spectator_session = False

    def replay_read(self):
        return ""

    def replay_write(self, s):
        pass

    def allow_cheatmode(self):
        return False


class _Connection:
    """A real TCP connection that speaks the real line protocol.

    The API mirrors :class:`soundrts.clientserver.ConnectionToServer`, so
    the coordinator can be pointed at it directly.
    """

    def __init__(self, host, port, login, server_pump=None):
        self.login = login
        self.server_pump = server_pump
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(5.0)
        self.sock.connect((host, port))
        self.sock.setblocking(False)
        self.buffer = b""
        self.data = b""
        self.lines = []

    # -- the wire --------------------------------------------------------

    def _pump_in(self):
        try:
            data = self.sock.recv(65536)
        except BlockingIOError:
            return
        except OSError:
            return
        if data:
            self.buffer += data

    def _split(self):
        out = []
        while b"\n" in self.buffer:
            data, self.buffer = self.buffer.split(b"\n", 1)
            for line in data.decode("utf-8", "replace").split("\r"):
                if line:
                    out.append(line)
                    self.lines.append(line)
        return out

    def poll(self):
        """Move the bytes and return whatever is ready."""
        if self.server_pump is not None:
            self.server_pump()
        self._pump_in()
        return self._split()

    def read_line(self):
        """The API the coordinator uses: one line, or ``None``."""
        if self.server_pump is not None:
            self.server_pump()
        self._pump_in()
        while b"\n" in self.buffer:
            data, self.buffer = self.buffer.split(b"\n", 1)
            line = data.decode("utf-8", "replace").rstrip("\r")
            if line:
                self.lines.append(line)
                return line
        return None

    def write_line(self, line):
        self.sock.sendall((line + "\n").encode("utf-8"))

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    # -- the handshake ---------------------------------------------------

    def _read_until(self, marker, timeout=5.0):
        deadline = time.time() + timeout
        while marker not in self.buffer:
            if time.time() > deadline:
                raise TimeoutError(
                    "handshake timed out waiting for %r (got %r)"
                    % (marker, self.buffer[:200])
                )
            if self.server_pump is not None:
                self.server_pump()
            self._pump_in()
            time.sleep(0.002)
        index = self.buffer.find(marker)
        head = self.buffer[: index + len(marker)]
        self.buffer = self.buffer[index + len(marker):]
        return head

    def do_login(self):
        self._read_until(b":")
        self.write_line("login %s %s" % (compatibility_version(), self.login))
        self._read_until(b"ok!")


def _digest(world):
    """A stable digest of the world, like the engine's own sync check."""
    h = hashlib.md5()
    for player in sorted(world.players, key=lambda p: str(p.id)):
        h.update(("P%s" % player.id).encode())
        h.update(repr(sorted(player.resources)).encode())
        for unit in sorted(player.units, key=lambda u: str(u.id)):
            h.update(("U%s,%s,%s" % (unit.id, unit.x, unit.y)).encode())
    return h.hexdigest()


@pytest.fixture
def headless_server():
    """The real server, on an ephemeral loopback port, pumped by the test."""
    server = Server(["no_metaserver"], is_standalone=True, host="127.0.0.1", port=0)
    server.login = "testserver"

    def pump():
        # The server is pumped twice on purpose: the first pass reads the
        # clients' orders and queues the broadcast, the second one puts
        # it on the wire.
        asyncore.poll(0.0)
        asyncore.poll(0.0)

    try:
        yield server, pump
    finally:
        try:
            for client in list(server.clients):
                client.close()
        except Exception:
            pass
        try:
            server.close()
        except Exception:
            pass


def _find_map(name="jl1"):
    for candidate in res.multiplayer_maps():
        if candidate.name == name:
            return candidate
    for candidate in res.multiplayer_maps():
        if name in candidate.name:
            return candidate
    raise LookupError("no multiplayer map named %r" % name)


def test_two_clients_play_a_lockstep_match_and_the_worlds_agree(headless_server):
    """The whole lockstep path works over real sockets."""
    server, pump = headless_server
    host_addr = server.socket.getsockname()[:2]

    host = _Connection(host_addr[0], host_addr[1], "host", pump)
    guest = _Connection(host_addr[0], host_addr[1], "guest", pump)
    threads = []
    try:
        host.do_login()
        guest.do_login()

        # The host creates the room.
        host.write_line("create %s 1" % _find_map().name)

        def state_of(connection):
            for client in server.clients:
                if client.login == connection.login:
                    return client.state.__class__.__name__
            return ""

        def wait_for(predicate, timeout=5.0):
            deadline = time.time() + timeout
            while time.time() < deadline:
                if predicate():
                    return True
                pump()
                time.sleep(0.001)
            return False

        assert wait_for(lambda: state_of(host) == "OrganizingAGame"), (
            "the host could not create the room"
        )

        game = None
        for client in server.clients:
            if client.login == "host":
                game = client.game
        assert game is not None
        game_id = game.id
        game.rmg_seed = 1234

        # The guest registers for the room.
        guest.write_line("register %d" % game_id)
        assert wait_for(
            lambda: state_of(guest) == "WaitingForTheGameToStart"
        ), "the guest could not register"

        # The host starts the game.
        host.write_line("start")
        assert wait_for(lambda: state_of(host) == "Playing"), "the game did not start"

        # Both clients receive the map and the match description.
        payloads = {}
        starts = {}
        deadline = time.time() + 5.0
        while time.time() < deadline:
            for connection in (host, guest):
                for line in connection.poll():
                    if line.startswith("map "):
                        payloads[connection.login] = line[4:].encode("utf-8")
                    elif line.startswith("start_game "):
                        starts[connection.login] = line.split(" ")[1:]
            if len(payloads) == 2 and len(starts) == 2:
                break
            time.sleep(0.002)
        assert len(payloads) == 2, payloads
        assert len(starts) == 2, starts

        # Every client builds its world from the bytes the server sent.
        worlds = {}
        coordinators = {}
        connections = {"host": host, "guest": guest}
        for login in ("host", "guest"):
            map_obj = res.unpack_map(payloads[login], save=False)
            args = starts[login]
            roster = []
            for entry in args[0].split(";"):
                if not entry:
                    continue
                parts = entry.split(",")
                if len(parts) >= 3:
                    roster.append((parts[0], parts[1], parts[2]))
            seed = int(args[2])

            connection = connections[login]
            session = _Session([])
            coordinator = Coordinator(login, connection, session)
            coordinator.interface = _StubInterface()
            clients = []
            for other_login, alliance, faction in roster:
                client = (
                    coordinator
                    if other_login == login
                    else RemoteClient(other_login)
                )
                client.alliance = alliance
                client.faction = faction
                clients.append(client)
            world = World([], seed)
            world.load_and_build_map(map_obj)
            world.populate_map(clients, equivalents=True)
            coordinator.world = world
            session.humans = list(clients)
            session.world = world
            session.local_client = coordinator
            worlds[login] = world
            coordinators[login] = coordinator

            # The world runs in its own thread, exactly like in the game.
            thread = threading.Thread(target=world.loop, daemon=True)
            thread.start()
            threads.append(thread)

        # The two worlds start out identical.
        assert _digest(worlds["host"]) == _digest(worlds["guest"])

        # Now play.  This mirrors the real client loop:
        #   server.update()  -> read the server's lines
        #   server.get_orders() -> send our orders, receive the turn
        #   world.queue_command(...) -> apply the turn and simulate
        frames = 0
        deadline = time.time() + 30.0
        while frames < 30 and time.time() < deadline:
            for login in ("host", "guest"):
                coordinator = coordinators[login]
                coordinator.update()
            for login in ("host", "guest"):
                coordinator = coordinators[login]
                if not coordinator.orders_are_ready():
                    continue
                for player, order in coordinator.get_orders():
                    coordinator.world.queue_command(player, order)
                coordinator.world.queue_command(None, coordinator.world.update)
            frames += 1
            time.sleep(0.005)

        assert frames >= 10, "the match did not advance (%d frames)" % frames

        # Wait for the world threads to catch up with the queued frames.
        deadline = time.time() + 10.0
        while time.time() < deadline:
            if worlds["host"].time == worlds["guest"].time and worlds["host"].time > 0:
                break
            time.sleep(0.01)

        # After the match has advanced, the two worlds still agree.
        assert worlds["host"].time > 0, "the world did not advance"
        assert worlds["host"].time == worlds["guest"].time, (
            "the two worlds are at different times: %s vs %s"
            % (worlds["host"].time, worlds["guest"].time)
        )
        assert _digest(worlds["host"]) == _digest(worlds["guest"])
    finally:
        host.close()
        guest.close()
        for thread in threads:
            thread.join(timeout=1.0)
