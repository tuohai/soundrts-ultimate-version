# -*- coding: utf-8 -*-
"""The spectator, end to end, under the rollback protocol.

The spectator is the hardest case of the rollback netcode:

* it has no local player, so it cannot predict anything;
* it joins *in the middle* of a match, so it must rebuild everything that
  happened before it arrived;
* it must then keep up with the live match, frame by frame, without ever
  showing a state that does not exist.

The mechanism is simple: the server keeps the whole authoritative input
history, hands it to the spectator when it joins, and the spectator replays
it one frame at a time with :class:`SpectatorSession`.

These tests drive the *real* pieces — the server's input stream, the real
:func:`Coordinator`, the real :class:`SpectatorSession` and the real
simulation — against each other, and check that the spectator ends up
bit-exact with the match it is watching.
"""
from __future__ import annotations

import logging
import os
import sys
import types
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.net.input_stream import (
        InputStream,
        decode_input,
        encode_input,
        pack_orders,
    )
    from soundrts.net.session import RollbackSession, SpectatorSession
    from soundrts.net.snapshot import strong_digest
    from soundrts.world import World
    from soundrts.worldclient import Coordinator, RemoteClient

sys.argv = saved

CW1 = os.path.join("res", "multi", "cw1.txt")


# ---------------------------------------------------------------------------
# The spectator session on its own
# ---------------------------------------------------------------------------


class _FakeWorld:
    """A trivial deterministic world, with just enough state to track."""

    def __init__(self):
        self.counter = 0
        self.log = []
        self.time = 0

    def update(self):
        self.counter += 1
        self.time += 1


def _spectator_session(world=None, players=("p1", "p2")):
    world = world if world is not None else _FakeWorld()

    def apply_inputs(inputs):
        for pid in sorted(inputs):
            orders = inputs.get(pid) or ""
            if orders:
                world.log.append((pid, orders))

    return SpectatorSession(
        world=world,
        players=list(players),
        step=world.update,
        apply_inputs=apply_inputs,
    )


def test_the_spectator_waits_for_every_player():
    """A frame is simulated only when *all* the players answered it.

    The spectator has no prediction: showing a frame that is missing one
    player's orders would show a state that never existed.
    """
    session = _spectator_session()

    session.on_input(0, "p1", "attack")
    assert session.has_ready_frame() is False
    assert session.step() is False
    assert session.frame == 0
    assert session.world.counter == 0

    session.on_input(0, "p2", "")
    assert session.has_ready_frame() is True
    assert session.step() is True
    assert session.frame == 1
    assert session.world.counter == 1


def test_the_spectator_replays_the_frames_in_order():
    session = _spectator_session()

    # The frames arrive out of order: the spectator must not skip ahead.
    session.on_input(1, "p1", "")
    session.on_input(1, "p2", "")
    assert session.has_ready_frame() is False

    session.on_input(0, "p1", "")
    session.on_input(0, "p2", "")
    assert session.has_ready_frame() is True

    assert session.step() is True
    assert session.frame == 1
    assert session.has_ready_frame() is True
    assert session.step() is True
    assert session.frame == 2
    assert session.has_ready_frame() is False


def test_the_spectator_ignores_a_retransmitted_input():
    session = _spectator_session()

    session.on_input(0, "p1", "first")
    session.on_input(0, "p1", "second")
    session.on_input(0, "p2", "")

    session.step()
    assert session.world.log == [("p1", "first")]


def test_the_spectator_counts_the_frames_it_still_has_to_replay():
    session = _spectator_session()

    assert session.pending_frames() == 0
    session.on_input(0, "p1", "")
    session.on_input(1, "p1", "")
    session.on_input(2, "p1", "")
    assert session.pending_frames() == 3

    session.on_input(0, "p2", "")
    session.step()
    assert session.pending_frames() == 2


def test_the_spectator_does_not_wait_for_a_player_that_quit():
    """A player that quits will never answer: the spectator must not wait.

    Otherwise the spectator would freeze at the frame the player left on,
    and would never show the rest of the match.
    """
    session = _spectator_session()

    session.on_input(0, "p1", "")
    assert session.has_ready_frame() is False

    # The second player quits.
    session.remove_player("p2")

    assert session.has_ready_frame() is True
    assert session.step() is True
    assert session.frame == 1


# ---------------------------------------------------------------------------
# The server hands its input history to the spectator
# ---------------------------------------------------------------------------


class _FakeClient:
    """A client that only records what it is notified."""

    def __init__(self, login, alliance="1", faction="human_faction"):
        self.login = login
        self.alliance = alliance
        self.faction = faction
        self.notes = []
        self.protocol = "rollback"

    def notify(self, *args):
        self.notes.append(args)


def _game_with_players(*logins):
    """A minimal server-side game, with an input stream."""
    from soundrts.serverroom import Game, InputStreamGame

    game = Game.__new__(Game)
    game.players = [_FakeClient(login) for login in logins]
    game.spectators = []
    game.protocol = "rollback"
    game._input_stream = InputStreamGame(game)
    game._timeout_reference = None
    game._orders = types.SimpleNamespace(players_without_orders=lambda: [])
    game.scenario = types.SimpleNamespace(name="jl1")
    game.speed = 1
    game.seed = 42
    game.treaty_minutes = 0
    game._coop_enemy_hp = 100
    game._coop_enemy_damage = 100
    game._initial_players_pack = ""
    game._order_history = []
    return game


def test_the_server_sends_the_whole_input_history_to_a_new_spectator():
    """The spectator joins in the middle: it needs everything before it."""
    game = _game_with_players("host", "guest")
    host, guest = game.players

    # The match goes on for a few frames.
    for frame in range(3):
        game.submit_input(host, frame, pack_orders("order 0 0 go %d" % frame))
        game.submit_input(guest, frame, pack_orders(""))

    spectator = _FakeClient("watcher")
    game._send_input_history(spectator)

    inputs = [n for n in spectator.notes if n[0] == "input"]
    assert len(inputs) == 6

    # Every input of every frame was sent, in order.  Within a frame the
    # players are sorted by login, so that every client applies them in the
    # same order.
    decoded = [decode_input(" ".join(n[1:])) for n in inputs]
    assert [(f, p) for f, p, _s, _o in decoded] == [
        (0, "guest"),
        (0, "host"),
        (1, "guest"),
        (1, "host"),
        (2, "guest"),
        (2, "host"),
    ]
    assert decoded[1][3] == "order 0 0 go 0"
    assert decoded[3][3] == "order 0 0 go 1"


def test_the_server_does_not_send_the_input_history_to_a_lockstep_spectator():
    """The lockstep protocol has its own history: the communication turns."""
    game = _game_with_players("host", "guest")
    game.protocol = "lockstep"
    game._order_history = [(1, "host/order,0,0,default,a1 guest/")]

    spectator = _FakeClient("watcher")
    game._send_start_spectating(spectator)

    kinds = [n[0] for n in spectator.notes]
    assert "input" not in kinds
    assert "all_orders" in kinds


def test_the_server_only_sends_the_frames_every_player_answered():
    """A half-answered frame cannot be replayed: the spectator would have
    to guess what the missing player did."""
    game = _game_with_players("host", "guest")
    host, guest = game.players

    game.submit_input(host, 0, pack_orders("a"))
    game.submit_input(guest, 0, pack_orders("b"))
    game.submit_input(host, 1, pack_orders("c"))

    spectator = _FakeClient("watcher")
    game._send_input_history(spectator)

    decoded = [decode_input(" ".join(n[1:])) for n in spectator.notes]
    assert {(f, p) for f, p, _s, _o in decoded} == {(0, "host"), (0, "guest")}


def test_the_live_inputs_reach_the_spectators():
    """A spectator does not only rebuild the past: it keeps up with the match.

    Without the live inputs, the spectator would freeze at the frame it had
    caught up to when it joined.
    """
    game = _game_with_players("host", "guest")
    host, guest = game.players
    spectator = _FakeClient("watcher")
    game.spectators.append(spectator)

    game.submit_input(host, 0, pack_orders("a"))
    game.submit_input(guest, 0, pack_orders("b"))

    decoded = [decode_input(" ".join(n[1:])) for n in spectator.notes]
    assert {(f, p) for f, p, _s, _o in decoded} == {(0, "host"), (0, "guest")}


def test_a_player_that_quits_does_not_stall_the_match():
    """The frames the quitter left open are closed, and everybody is told.

    A frame is only complete once every player has answered it.  A player
    that quits will never answer the frames it was supposed to answer, so
    the server has to close them — and tell the other clients, or they
    would wait for the quitter forever.
    """
    game = _game_with_players("host", "guest")
    host, guest = game.players
    spectator = _FakeClient("watcher")
    game.spectators.append(spectator)

    # Frame 0 is complete, frame 1 is not: the guest never answered it.
    game.submit_input(host, 0, pack_orders("a"))
    game.submit_input(guest, 0, pack_orders("b"))
    game.submit_input(host, 1, pack_orders("c"))

    game._input_stream.remove_player("guest")

    # The other clients are told the guest is gone.
    assert ("player_quit", "guest") in host.notes
    assert ("player_quit", "guest") in spectator.notes

    # And the open frame is closed with the guest's empty share, so that
    # everybody can replay it.
    inputs = [
        decode_input(" ".join(n[1:])) for n in spectator.notes if n[0] == "input"
    ]
    assert (1, "guest") in {(f, p) for f, p, _s, _o in inputs}

    # The frame is now authoritative, and the match can go on.
    assert [f.frame for f in game.confirmed_frames()] == [0, 1]


# ---------------------------------------------------------------------------
# The whole chain, against the real simulation
# ---------------------------------------------------------------------------


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _build_world(seed, logins):
    """A world with one human player per login, like a real multiplayer game."""
    if not os.path.isfile(CW1):
        pytest.skip("cw1 map not present")
    from soundrts.mapfile import Map

    faction = rules.factions[0] if rules.factions else "human_faction"
    clients = []
    for index, login in enumerate(logins):
        client = RemoteClient(login)
        client.alliance = str(index + 1)
        client.faction = faction
        clients.append(client)

    world = World([], seed)
    world.load_and_build_map(Map(CW1))
    world.populate_map(clients, equivalents=True)
    return world, clients


def _apply_orders(players_by_login, inputs):
    """Hand one frame's orders to the players they belong to."""
    for login in sorted(inputs):
        orders = inputs.get(login) or ""
        player = players_by_login.get(login)
        if player is None or not orders:
            continue
        for order in orders.split("\n"):
            if order:
                player.execute_command(order)


def _move_order(player):
    """A simple, deterministic order: move a unit to a neighbouring square."""
    for unit in player.units:
        if getattr(unit, "type_name", "") not in ("peasant", "footman", "archer"):
            continue
        exits = list(getattr(unit.place, "exits", ()) or ())
        if not exits:
            continue
        return "control %s\norder 0 0 go %s" % (unit.id, exits[0].id)
    return ""


def test_the_spectator_rebuilds_the_match_and_stays_in_sync(res_loaded):
    """The whole chain, on the real world.

    Two players play a match under the rollback protocol.  A spectator
    joins in the middle, gets the server's input history, replays it, and
    must end up in exactly the same state as the players.

    This is the test that catches a spectator that shows a world which does
    not exist.
    """
    seed = 4242
    logins = ("host", "guest")
    NB_FRAMES = 14

    live_world, live_clients = _build_world(seed, logins)
    host_world, host_clients = _build_world(seed, logins)
    guest_world, guest_clients = _build_world(seed, logins)
    spec_world, spec_clients = _build_world(seed, logins)

    live_players = {p.login: p.player for p in live_clients}
    host_players = {p.login: p.player for p in host_clients}
    guest_players = {p.login: p.player for p in guest_clients}
    spec_players = {p.login: p.player for p in spec_clients}

    # -- the reference run: the orders are applied in the frame they belong to
    orders_by_frame = {frame: {} for frame in range(NB_FRAMES)}
    for frame in range(NB_FRAMES):
        if frame == 2:
            orders_by_frame[frame]["host"] = _move_order(live_players["host"])
        if frame == 5:
            orders_by_frame[frame]["guest"] = _move_order(live_players["guest"])
        if frame == 9:
            orders_by_frame[frame]["host"] = _move_order(live_players["host"])
        _apply_orders(live_players, orders_by_frame[frame])
        live_world.update()

    # -- the two clients, under the rollback protocol --
    host_session = RollbackSession(
        world=host_world,
        local_player="host",
        players=list(logins),
        step=host_world.update,
        apply_inputs=lambda inputs: _apply_orders(host_players, inputs),
    )
    guest_session = RollbackSession(
        world=guest_world,
        local_player="guest",
        players=list(logins),
        step=guest_world.update,
        apply_inputs=lambda inputs: _apply_orders(guest_players, inputs),
    )

    # The server: it stamps every input and broadcasts it straight away.
    server = _game_with_players(*logins)
    server_clients = {c.login: c for c in server.players}

    # The server never echoes an input back to its author: the author
    # already knows what it did.
    delivered = {"host": [], "guest": []}
    sessions = {"host": host_session, "guest": guest_session}

    for frame in range(NB_FRAMES):
        for login in logins:
            packed = pack_orders(orders_by_frame[frame].get(login, ""))
            assert server.submit_input(server_clients[login], frame, packed) is True

        # Collect what the server broadcast to each player.
        for login in logins:
            for note in server_clients[login].notes:
                if note[0] == "input":
                    delivered[login].append(note[1])

        # Each client receives the other's inputs, with a one frame delay:
        # that is what makes the clients roll back.
        for login in logins:
            for message in delivered[login]:
                number, player_id, _seq, orders = decode_input(message)
                if number == frame - 1:
                    sessions[login].on_input(number, player_id, orders)

        # The local player submits its own orders for this frame.
        for login in logins:
            orders = orders_by_frame[frame].get(login, "")
            if orders:
                sessions[login].submit_local(orders)

        host_session.step()
        guest_session.step()

    # The clients converged on the reference run.
    assert host_session.stats.rollbacks >= 1
    assert strong_digest(host_world) == strong_digest(live_world)

    # -- the spectator joins now, and gets the server's history --
    spectator_client = _FakeClient("watcher")
    server._send_input_history(spectator_client)

    spectator_session = SpectatorSession(
        world=spec_world,
        players=list(logins),
        step=spec_world.update,
        apply_inputs=lambda inputs: _apply_orders(spec_players, inputs),
    )
    for note in spectator_client.notes:
        if note[0] != "input":
            continue
        number, login, _seq, orders = decode_input(" ".join(note[1:]))
        spectator_session.on_input(number, login, orders)

    # The spectator replays the whole history, one frame at a time.
    while spectator_session.frame < NB_FRAMES:
        assert spectator_session.step() is True

    # The spectator is now exactly where the players are.
    assert spectator_session.frame == NB_FRAMES
    assert strong_digest(spec_world) == strong_digest(live_world)


def test_the_spectator_keeps_up_with_a_live_match(res_loaded):
    """A spectator that joined mid-match must follow the rest of the match.

    The spectator does not only rebuild the past: it receives the inputs of
    the frames that come after it joined, and replays them as they arrive.
    """
    if not os.path.isfile(CW1):
        pytest.skip("cw1 map not present")

    seed = 777
    logins = ("host", "guest")
    NB_FRAMES = 8

    live_world, live_clients = _build_world(seed, logins)
    spec_world, spec_clients = _build_world(seed, logins)

    live_players = {p.login: p.player for p in live_clients}
    spec_players = {p.login: p.player for p in spec_clients}

    orders_by_frame = {frame: {} for frame in range(NB_FRAMES)}
    for frame in range(NB_FRAMES):
        if frame == 1:
            orders_by_frame[frame]["host"] = _move_order(live_players["host"])
        if frame == 4:
            orders_by_frame[frame]["guest"] = _move_order(live_players["guest"])
        _apply_orders(live_players, orders_by_frame[frame])
        live_world.update()

    server = _game_with_players(*logins)
    server_clients = {c.login: c for c in server.players}
    spectator_client = _FakeClient("watcher")
    server.spectators.append(spectator_client)

    # The spectator joins after the first three frames.
    JOIN_FRAME = 3
    for frame in range(JOIN_FRAME):
        for login in logins:
            server.submit_input(
                server_clients[login],
                frame,
                pack_orders(orders_by_frame[frame].get(login, "")),
            )

    server._send_input_history(spectator_client)

    spectator_session = SpectatorSession(
        world=spec_world,
        players=list(logins),
        step=spec_world.update,
        apply_inputs=lambda inputs: _apply_orders(spec_players, inputs),
    )
    for note in spectator_client.notes:
        if note[0] != "input":
            continue
        number, login, _seq, orders = decode_input(" ".join(note[1:]))
        spectator_session.on_input(number, login, orders)

    # The spectator catches up with the frames that happened before it
    # joined.
    while spectator_session.frame < JOIN_FRAME:
        assert spectator_session.step() is True

    # And then the live frames arrive: the spectator follows along.
    for frame in range(JOIN_FRAME, NB_FRAMES):
        for login in logins:
            server.submit_input(
                server_clients[login],
                frame,
                pack_orders(orders_by_frame[frame].get(login, "")),
            )
        for note in spectator_client.notes:
            if note[0] != "input":
                continue
            number, login, _seq, orders = decode_input(" ".join(note[1:]))
            spectator_session.on_input(number, login, orders)
        assert spectator_session.step() is True

    assert spectator_session.frame == NB_FRAMES
    assert strong_digest(spec_world) == strong_digest(live_world)


def test_the_spectator_coordinator_replays_the_inputs_it_receives(res_loaded):
    """The wiring, from the "input" message to the simulation.

    The spectator's coordinator receives the authoritative inputs from the
    server and must hand them to its session, which replays them.
    """
    if not os.path.isfile(CW1):
        pytest.skip("cw1 map not present")

    seed = 99
    logins = ("host", "guest")
    spec_world, spec_clients = _build_world(seed, logins)

    session = types.SimpleNamespace(
        humans=spec_clients,
        is_spectator_session=True,
        record_replay=False,
    )
    coordinator = Coordinator(
        "watcher",
        types.SimpleNamespace(write_line=lambda s: None),
        session,
    )
    coordinator.world = spec_world
    coordinator.rollback_enabled = True

    # The coordinator creates the spectator session lazily.
    rollback_session = coordinator._ensure_session()
    assert isinstance(rollback_session, SpectatorSession)

    # The server sends the inputs of the first two frames.
    coordinator.receive_rollback_input(encode_input(0, "host", 1, "order 0 0 go 1"))
    coordinator.receive_rollback_input(encode_input(1, "host", 3, ""))
    coordinator.receive_rollback_input(encode_input(1, "guest", 4, ""))

    # The spectator is not ready until every player answered the frame.
    assert coordinator.orders_are_ready() is False
    coordinator.receive_rollback_input(encode_input(0, "guest", 5, ""))
    assert coordinator.orders_are_ready() is True

    # The spectator replays the frame: the world moved on.
    assert rollback_session.step() is True
    assert rollback_session.frame == 1
    assert spec_world.time > 0


def test_the_coordinator_keeps_the_inputs_that_arrive_before_the_session(res_loaded):
    """The first inputs must not be lost.

    The session needs the world and the players, and they only exist once
    the game has started.  The socket may deliver inputs before that, and
    dropping them would make the client diverge from the server for the
    whole match.
    """
    if not os.path.isfile(CW1):
        pytest.skip("cw1 map not present")

    seed = 123
    logins = ("host", "guest")
    spec_world, spec_clients = _build_world(seed, logins)

    session = types.SimpleNamespace(
        humans=spec_clients,
        is_spectator_session=True,
        record_replay=False,
    )
    coordinator = Coordinator(
        "watcher",
        types.SimpleNamespace(write_line=lambda s: None),
        session,
    )
    coordinator.rollback_enabled = True

    # The world does not exist yet: the inputs are buffered, not dropped.
    coordinator.receive_rollback_input(encode_input(0, "host", 1, "order 0 0 go 1"))
    coordinator.receive_rollback_input(encode_input(0, "guest", 2, ""))
    assert coordinator.rollback_session is None
    assert len(coordinator._pending_rollback_inputs) == 2

    # The world appears: the session is created and the buffered inputs
    # are replayed into it.
    coordinator.world = spec_world
    rollback_session = coordinator._ensure_session()
    assert isinstance(rollback_session, SpectatorSession)
    assert coordinator._pending_rollback_inputs == []

    # The buffered frame 0 is complete: the spectator can replay it.
    assert coordinator.orders_are_ready() is True
    assert rollback_session.step() is True
    assert rollback_session.frame == 1


def test_the_game_starts_the_rollback_session_before_the_first_frame(res_loaded):
    """The session is created eagerly, not on the first input.

    ``Game._start_rollback_session`` is called by the game, right after
    the world is built and the players are created.  This is what makes
    the spectator work at all: without a session, the interface would
    simulate frames nobody has any input for.
    """
    from soundrts.game import _Game

    if not os.path.isfile(CW1):
        pytest.skip("cw1 map not present")

    seed = 321
    logins = ("host", "guest")
    spec_world, spec_clients = _build_world(seed, logins)

    session = types.SimpleNamespace(
        humans=spec_clients,
        is_spectator_session=True,
        record_replay=False,
    )
    coordinator = Coordinator(
        "watcher",
        types.SimpleNamespace(write_line=lambda s: None),
        session,
    )
    coordinator.rollback_enabled = True

    game = _Game.__new__(_Game)
    game.local_client = coordinator
    game.world = spec_world

    game._start_rollback_session()

    assert coordinator.rollback_session is not None
    assert isinstance(coordinator.rollback_session, SpectatorSession)
    assert coordinator.rollback_session.world is spec_world
