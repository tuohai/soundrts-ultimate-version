# -*- coding: utf-8 -*-
"""The client side of the rollback protocol.

These tests drive the real :class:`~soundrts.net.session.RollbackSession`
against the real simulation, and check the two properties that matter:

* the client never waits for the server (it simulates ahead);
* when the truth contradicts the prediction, the client repairs itself and
  ends up in exactly the same state as a client that never had to roll back.
"""
from __future__ import annotations

import os
import warnings

import pytest

from soundrts.net.input_stream import InputFrame, InputStream, encode_input
from soundrts.net.session import RollbackSession
from soundrts.net.snapshot import strong_digest


class FakeWorld:
    """A trivial deterministic world, with just enough state to snapshot."""

    def __init__(self):
        self.counter = 0
        self.log = []
        self.time = 0

    def update(self):
        self.counter += 1
        self.time += 1


class FakeSnapshot:
    """The state of a :class:`FakeWorld`."""

    __slots__ = ("counter", "log", "time")

    def __init__(self, world):
        self.counter = world.counter
        self.log = list(world.log)
        self.time = world.time


def fake_capture(world):
    return FakeSnapshot(world)


def fake_restore(world, snapshot):
    world.counter = snapshot.counter
    world.log = list(snapshot.log)
    world.time = snapshot.time


def make_session(world=None, local="p1", players=("p1", "p2")):
    world = world if world is not None else FakeWorld()

    def apply_inputs(inputs):
        for pid in sorted(inputs):
            orders = inputs.get(pid) or ""
            if orders:
                world.log.append((pid, orders))

    return RollbackSession(
        world=world,
        local_player=local,
        players=list(players),
        step=world.update,
        apply_inputs=apply_inputs,
        capture=lambda: fake_capture(world),
        restore=lambda snap: fake_restore(world, snap),
    )


# ---------------------------------------------------------------------------
# The client simulates ahead, without waiting for the server
# ---------------------------------------------------------------------------


def test_the_client_simulates_a_frame_before_the_server_answers():
    session = make_session()
    session.step()
    assert session.frame == 1
    assert session.stats.frames_simulated == 1
    # The remote player was predicted to be idle.
    assert session.stats.predicted_frames == 1


def test_the_local_players_orders_are_applied_immediately():
    session = make_session()
    session.submit_local("attack")
    session.step()
    assert session.world.log == [("p1", "attack")]


def test_the_local_players_orders_are_sent_to_the_server():
    sent = []
    session = make_session()
    session._on_local_input = lambda frame, orders: sent.append((frame, orders))
    session.submit_local("order 0 0 go 42")
    assert sent == [(0, "order,0,0,go,42")]


def test_a_player_that_quits_does_not_stall_the_client():
    """The client must stop waiting for a player that left the match.

    Otherwise every frame would stay incomplete on the client side, and
    the client would never simulate anything again.
    """
    session = make_session()
    session.step()
    assert session.frame == 1

    # The remote player quits.
    session.remove_player("p2")

    # The client keeps going: it no longer waits for p2's input.
    session.step()
    session.step()
    assert session.frame == 3
    assert session.stats.frames_simulated == 3


def test_the_local_orders_are_not_lost_when_they_arrive_during_a_step():
    """The orders of the local player must never be dropped.

    The orders are submitted by the *interface* thread, and the frame they
    belong to is the one the *world* thread is about to simulate.  The two
    threads run at the same time, so the frame number has to be decided
    atomically with the recording of the orders.

    Otherwise the orders land on a frame that has already been simulated:
    they would be applied one frame late — or not at all — and the client
    would drift away from the server.
    """
    import threading

    world = FakeWorld()
    started = threading.Event()
    release = threading.Event()

    def slow_update():
        started.set()
        release.wait(5)
        world.counter += 1
        world.time += 1

    session = RollbackSession(
        world=world,
        local_player="p1",
        players=["p1", "p2"],
        step=slow_update,
        apply_inputs=lambda inputs: world.log.extend(
            (pid, orders) for pid, orders in sorted(inputs.items()) if orders
        ),
        capture=lambda: fake_capture(world),
        restore=lambda snap: fake_restore(world, snap),
    )

    thread = threading.Thread(target=session.step)
    thread.start()
    assert started.wait(5)

    # The interface thread submits the orders while the frame is running.
    session.submit_local("attack")

    release.set()
    thread.join(5)

    # The order was not applied by the frame that was already running (its
    # inputs were fixed), but it was not lost either: it is waiting for the
    # next frame.
    assert world.log == []

    session.step()
    assert world.log == [("p1", "attack")]

    # And the order did not cost a frame.
    assert session.frame == 2


# ---------------------------------------------------------------------------
# A contradicted prediction is repaired
# ---------------------------------------------------------------------------


def test_a_contradicted_prediction_rolls_back_and_repairs_the_world():
    session = make_session()
    session.step()
    session.step()
    session.step()
    assert session.world.log == []

    # The server says the remote player did something in frame 0.
    session.on_input(0, "p2", "defend")
    session.step()

    assert session.stats.rollbacks == 1
    assert session.world.log == [("p2", "defend")]


def test_an_agreeing_input_does_not_roll_back():
    session = make_session()
    session.step()
    session.on_input(0, "p2", "")
    session.step()
    assert session.stats.rollbacks == 0
    assert session.stats.desync_detected == 0


def test_a_retransmitted_input_changes_nothing():
    session = make_session()
    session.step()
    session.on_input(0, "p2", "defend")
    session.step()
    assert session.stats.rollbacks == 1

    session.on_input(0, "p2", "defend")
    session.step()
    assert session.stats.rollbacks == 1


def test_the_network_thread_never_touches_the_world():
    """Recording an input must not mutate the world.

    The world lives on its own thread; restoring a snapshot from the
    network thread would race with it.
    """
    session = make_session()
    session.step()
    before = session.world.counter
    log_before = list(session.world.log)

    session.on_input(0, "p2", "defend")

    assert session.world.counter == before
    assert session.world.log == log_before


def test_the_rollback_happens_on_the_next_step():
    """The rollback is deferred to the world thread, not done on arrival."""
    session = make_session()
    session.step()
    session.step()

    session.on_input(0, "p2", "defend")
    # The input arrived, but nothing happened yet: the world thread has not
    # stepped since.
    assert session.stats.rollbacks == 0
    assert session.world.log == []

    session.step()
    assert session.stats.rollbacks == 1
    assert session.world.log == [("p2", "defend")]


def test_the_frame_number_does_not_move_during_a_rollback():
    """A rollback repairs the past; it does not advance the client."""
    session = make_session()
    session.step()
    session.step()
    session.step()
    frame_before = session.frame

    session.on_input(0, "p2", "defend")
    session.repair()

    # The repair rewound the world and re-simulated the frames it rewound
    # over: the client is on the same frame, but with the right state.
    assert session.frame == frame_before
    assert session.stats.rollbacks == 1
    assert session.world.log == [("p2", "defend")]


def test_a_step_always_advances_by_exactly_one_frame():
    """A rollback must not cost the client a frame."""
    session = make_session()
    session.step()
    session.step()
    assert session.frame == 2

    session.on_input(0, "p2", "defend")
    session.step()
    assert session.frame == 3
    assert session.stats.rollbacks == 1


# ---------------------------------------------------------------------------
# End to end, against the real simulation
# ---------------------------------------------------------------------------


def _build_world(map_path="cw1.txt"):
    from soundrts.game import TrainingGame
    from soundrts.mapfile import Map
    from soundrts.world import World

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        m = Map(os.path.join("res", "multi", map_path))
        game = TrainingGame(m, ["test", "easy"], ["human", "orc"], ["1", "2"])
        game.record_replay = False
        game.seed = 1234
        game.world = World(game.default_triggers, 1234)
        game.world.load_and_build_map(m)
        game.world.populate_map(game.players, equivalents=True)
    return game.world


def _order_for(unit_id, target_id):
    return "control %s\norder 0 0 go %s" % (unit_id, target_id)


def _session_for(world, local_id, remote_id, sent=None):
    players_by_id = {p.id: p for p in world.players}

    def apply_inputs(inputs):
        for pid in sorted(inputs):
            orders = inputs.get(pid) or ""
            if not orders:
                continue
            player = players_by_id.get(pid)
            if player is None:
                continue
            for order in orders.split("\n"):
                if order:
                    player.execute_command(order)

    return RollbackSession(
        world=world,
        local_player=local_id,
        players=[local_id, remote_id],
        step=world.update,
        apply_inputs=apply_inputs,
        on_local_input=(lambda f, o: sent.append((f, o))) if sent is not None else None,
    )


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_the_session_repairs_the_real_simulation():
    """The whole chain, on the real world.

    The client predicts the remote player is idle, the server says
    otherwise, and the client repairs itself.  It must end up exactly where
    a client that never rolled back is.
    """
    straight = _build_world()
    rolled = _build_world()

    ids = [p.id for p in straight.players]

    def first_unit(world, index):
        for unit in world.players[index].units:
            if getattr(unit, "type_name", "") in ("peasant", "footman", "archer"):
                return unit
        raise AssertionError("no movable unit found")

    straight_unit = first_unit(straight, 0)
    target = list(getattr(straight_unit.place, "exits", ()) or ())[0].id
    local_order = _order_for(straight_unit.id, target)

    remote_unit = first_unit(straight, 1)
    remote_target = list(getattr(remote_unit.place, "exits", ()) or ())[0].id
    remote_order = _order_for(remote_unit.id, remote_target)

    # -- the straight run: every order applied in the frame it belongs to --
    def apply_order(world, index, orders):
        player = world.players[index]
        for line in orders.split("\n"):
            if line:
                player.execute_command(line)

    for frame in range(12):
        if frame == 5:
            apply_order(straight, 0, local_order)
        if frame == 3:
            apply_order(straight, 1, remote_order)
        straight.update()

    # -- the rolled-back run: the remote order arrives late --
    session = _session_for(rolled, ids[0], ids[1])
    for frame in range(12):
        if frame == 5:
            session.submit_local(local_order)
        session.step()

    # The two worlds must differ: the straight run already applied the
    # remote order, the other one predicted it as empty.
    assert strong_digest(straight) != strong_digest(rolled)

    # The server now confirms frame 3 with the remote order.
    session.on_input(3, ids[1], remote_order)
    session.repair()

    assert session.stats.rollbacks == 1

    # Run the remaining frames so both worlds end at the same point.
    while session.frame < 12:
        session.step()

    assert strong_digest(straight) == strong_digest(rolled)
    assert session.unrecoverable_desync is False


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_two_sessions_converge_over_the_stream_with_latency():
    """Two real clients, a real server, and real latency."""
    reference = _build_world()
    world_a = _build_world()
    world_b = _build_world()

    ids = [p.id for p in reference.players]

    def first_unit(world, index):
        for unit in world.players[index].units:
            if getattr(unit, "type_name", "") in ("peasant", "footman", "archer"):
                return unit
        raise AssertionError("no movable unit found")

    unit_a = first_unit(reference, 0)
    target_a = list(getattr(unit_a.place, "exits", ()) or ())[0].id
    order_a = _order_for(unit_a.id, target_a)

    unit_b = first_unit(reference, 1)
    target_b = list(getattr(unit_b.place, "exits", ()) or ())[0].id
    order_b = _order_for(unit_b.id, target_b)

    def apply_order(world, index, orders):
        player = world.players[index]
        for line in orders.split("\n"):
            if line:
                player.execute_command(line)

    NB_FRAMES = 16
    LOCAL_FRAME_A = 4
    LOCAL_FRAME_B = 7

    for frame in range(NB_FRAMES):
        if frame == LOCAL_FRAME_A:
            apply_order(reference, 0, order_a)
        if frame == LOCAL_FRAME_B:
            apply_order(reference, 1, order_b)
        reference.update()

    stream = InputStream(ids)
    session_a = _session_for(world_a, ids[0], ids[1])
    session_b = _session_for(world_b, ids[1], ids[0])

    inbox_a = []
    inbox_b = []
    LATENCY_A = 3
    LATENCY_B = 5

    for frame in range(NB_FRAMES):
        sent_a = order_a if frame == LOCAL_FRAME_A else ""
        sent_b = order_b if frame == LOCAL_FRAME_B else ""

        stamped_a = stream.submit_incremental(ids[0], frame, sent_a)
        stamped_b = stream.submit_incremental(ids[1], frame, sent_b)

        inbox_a.append(
            (LATENCY_A, encode_input(stamped_b[0], ids[1], stamped_b[1], stamped_b[2]))
        )
        inbox_b.append(
            (LATENCY_B, encode_input(stamped_a[0], ids[0], stamped_a[1], stamped_a[2]))
        )

        for delay, payload in list(inbox_b):
            if delay == 0:
                inbox_b.remove((delay, payload))
                from soundrts.net.input_stream import decode_input

                f, pl, _s, orders = decode_input(payload)
                session_b.on_input(f, pl, orders)
        for delay, payload in list(inbox_a):
            if delay == 0:
                inbox_a.remove((delay, payload))
                from soundrts.net.input_stream import decode_input

                f, pl, _s, orders = decode_input(payload)
                session_a.on_input(f, pl, orders)

        if frame == LOCAL_FRAME_A:
            session_a.submit_local(order_a)
        if frame == LOCAL_FRAME_B:
            session_b.submit_local(order_b)

        session_a.step()
        session_b.step()

        inbox_a = [(d - 1, m) for (d, m) in inbox_a]
        inbox_b = [(d - 1, m) for (d, m) in inbox_b]

    # Let the last messages arrive.  The clients must not advance: they
    # have already simulated those frames, they only need to repair them.
    from soundrts.net.input_stream import decode_input

    for _ in range(10):
        for delay, payload in list(inbox_b):
            if delay == 0:
                inbox_b.remove((delay, payload))
                f, pl, _s, orders = decode_input(payload)
                session_b.on_input(f, pl, orders)
        for delay, payload in list(inbox_a):
            if delay == 0:
                inbox_a.remove((delay, payload))
                f, pl, _s, orders = decode_input(payload)
                session_a.on_input(f, pl, orders)
        # A step that repairs a rollback does not move the client forward.
        # The sessions that need to advance do so explicitly below.
        session_a.repair()
        session_b.repair()

    assert session_a.frame == session_b.frame == NB_FRAMES
    assert session_a.unrecoverable_desync is False
    assert session_b.unrecoverable_desync is False
    # Both clients really did have to roll back.
    assert session_a.stats.rollbacks >= 1
    assert session_b.stats.rollbacks >= 1

    assert strong_digest(world_a) == strong_digest(world_b)
    assert strong_digest(world_a) == strong_digest(reference)
