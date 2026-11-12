"""Tests for the rollback netcode: snapshots, input stream, rollback manager."""

import os
import sys
import warnings

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from soundrts.net.input_stream import (
    InputFrame,
    InputStream,
    decode_frame,
    decode_input,
    encode_input,
)
from soundrts.net.rollback import RollbackManager
from soundrts.net.snapshot import capture_snapshot, restore_snapshot, strong_digest


# --------------------------------------------------------------------------
# A tiny deterministic fake world
# --------------------------------------------------------------------------


class FakeWorld:
    """A minimal deterministic world: a counter plus a list of applied orders.

    It is deliberately trivial — the point of these tests is the rollback
    *machinery*, not the simulation.
    """

    def __init__(self):
        self.counter = 0
        self.log = []

    def apply(self, inputs):
        for player in sorted(inputs):
            order = inputs[player]
            if order:
                self.log.append((player, order))

    def step(self):
        self.counter += 1

    # -- trivial snapshot / restore, standing in for the real ones ------
    def capture(self):
        return (self.counter, list(self.log))

    def restore(self, snapshot):
        self.counter, self.log = snapshot[0], list(snapshot[1])


def make_manager(world, local="p1", players=("p1", "p2")):
    return RollbackManager(
        local_player=local,
        players=list(players),
        world=world,
        step=world.step,
        apply_inputs=world.apply,
        capture=world.capture,
        restore=world.restore,
        history_size=16,
    )


# --------------------------------------------------------------------------
# Input stream
# --------------------------------------------------------------------------


def test_input_stream_confirms_frame_once_every_player_answered():
    stream = InputStream(["p1", "p2"])
    assert stream.submit("p1", 0, "move 1") is None
    frame = stream.submit("p2", 0, "build 2")
    assert frame is not None
    assert frame.confirmed is not None
    assert stream.is_authoritative(0)
    assert frame.order_for("p1") == "move 1"
    assert frame.order_for("p2") == "build 2"
    assert stream.confirmed_frame == 0


def test_input_stream_ignores_duplicate_submissions():
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 0, "move 1")
    stream.submit("p2", 0, "build 2")
    # A retransmission must not change the frame.
    assert stream.submit("p1", 0, "move 999") is None
    frame = stream.frame(0)
    assert frame.order_for("p1") == "move 1"
    assert frame.orders_signature() == (("p1", "move 1"), ("p2", "build 2"))


def test_input_stream_detects_gaps():
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 0, "")
    stream.submit("p2", 0, "")
    assert stream.confirmed_frame == 0
    # p2 never answers frame 1, so frame 1 stays open.
    stream.submit("p1", 1, "")
    assert stream.confirmed_frame == 0
    assert stream.gaps() == []


def test_a_player_that_quits_does_not_stall_the_match():
    """The frames a quitter left open are closed, or the match is over.

    A frame is only complete once *every* player has answered it.  A player
    that quits mid-match will never answer the frames it was supposed to
    answer, so those frames have to be closed when it leaves.
    """
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 0, "")
    stream.submit("p2", 0, "")
    # p2 answers frame 1, p1 does not.
    stream.submit("p2", 1, "")
    assert stream.confirmed_frame == 0

    # p1 quits: frame 1 is closed with p1's empty share.
    opened = stream.remove_player("p1")
    assert 1 in opened
    assert stream.confirmed_frame == 1
    assert stream.is_authoritative(1)
    assert "p1" not in stream.players

    # And the match goes on: the frame 2 only needs p2 now.
    stream.submit("p2", 2, "")
    assert stream.is_authoritative(2)


def test_a_player_that_quits_does_not_change_the_frames_it_answered():
    """The frames the quitter *did* answer stay exactly as they were."""
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 0, "move 1")
    stream.submit("p2", 0, "")
    stream.remove_player("p1")
    frame = stream.frame(0)
    assert frame.order_for("p1") == "move 1"
    assert frame.orders_signature() == (("p1", "move 1"), ("p2", ""))


def test_input_stream_roundtrips_through_the_wire_format():
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 3, "order 0 0 move 4,5")
    stream.submit("p2", 3, "")
    frame = stream.frame(3)
    encoded = stream.encode_frame(frame)
    decoded = decode_frame(encoded)
    assert decoded.frame == 3
    assert decoded.confirmed is not None
    assert decoded.order_for("p1") == "order 0 0 move 4,5"
    assert decoded.order_for("p2") == ""
    assert decoded.orders_signature() == frame.orders_signature()


def test_input_stream_confirms_frames_in_order():
    stream = InputStream(["p1", "p2"])
    stream.submit("p1", 1, "b")
    stream.submit("p2", 1, "c")
    assert stream.confirmed_frame == -1  # frame 0 is still missing
    stream.submit("p1", 0, "a")
    stream.submit("p2", 0, "z")
    assert stream.confirmed_frame == 1


# --------------------------------------------------------------------------
# Input stream: the incremental (lockstep-free) path
# --------------------------------------------------------------------------


def test_incremental_input_is_stamped_and_returned_immediately():
    """The server must not wait for the other player to answer.

    This is the whole point of the incremental path: the input is stamped
    and returned as soon as it arrives, instead of being held back until
    the frame is complete.
    """
    stream = InputStream(["p1", "p2"])

    stamped = stream.submit_incremental("p1", 0, "move 1")
    assert stamped is not None
    frame, seq, orders = stamped
    assert frame == 0
    assert orders == "move 1"
    assert seq is not None

    # The frame is *not* complete yet, so it is not authoritative...
    assert not stream.is_authoritative(0)
    assert stream.confirmed_frame == -1
    # ...but the input was already accepted and stamped.
    assert stream.frame(0).order_for("p1") == "move 1"


def test_incremental_sequence_numbers_are_authoritative_and_increasing():
    """The sequence number fixes the order in which inputs are applied."""
    stream = InputStream(["p1", "p2"])
    first = stream.submit_incremental("p2", 0, "b")
    second = stream.submit_incremental("p1", 0, "a")
    assert first[1] < second[1]

    # A duplicate must not get a new stamp: a retransmission must never
    # change an input that has already been broadcast.
    duplicate = stream.submit_incremental("p2", 0, "different")
    assert duplicate is None
    assert stream.frame(0).order_for("p2") == "b"


def test_incremental_frame_becomes_authoritative_once_everyone_answered():
    stream = InputStream(["p1", "p2"])
    stream.submit_incremental("p1", 0, "a")
    assert not stream.is_authoritative(0)
    stream.submit_incremental("p2", 0, "b")
    assert stream.is_authoritative(0)
    assert stream.confirmed_frame == 0
    frame = stream.frame(0)
    assert frame.order_for("p1") == "a"
    assert frame.order_for("p2") == "b"


def test_incremental_input_roundtrips_through_the_wire_format():
    stream = InputStream(["p1", "p2"])
    frame, seq, orders = stream.submit_incremental("p1", 7, "order 0 0 go 12")
    encoded = stream.encode_input_for(frame, "p1", seq, orders)

    decoded_frame, decoded_player, decoded_seq, decoded_orders = decode_input(
        encoded
    )
    assert decoded_frame == 7
    assert decoded_player == "p1"
    assert decoded_seq == seq
    assert decoded_orders == "order 0 0 go 12"


def test_incremental_input_with_no_orders_roundtrips():
    """An empty order string must survive the wire format."""
    stream = InputStream(["p1", "p2"])
    frame, seq, orders = stream.submit_incremental("p2", 0, "")
    encoded = stream.encode_input_for(frame, "p2", seq, orders)
    decoded_frame, decoded_player, decoded_seq, decoded_orders = decode_input(
        encoded
    )
    assert decoded_frame == 0
    assert decoded_player == "p2"
    assert decoded_orders == ""


def test_inputs_since_replays_only_the_newer_frames():
    """A reconnecting client asks for what it has not seen yet."""
    stream = InputStream(["p1", "p2"])
    stream.submit_incremental("p1", 0, "a")
    stream.submit_incremental("p2", 0, "b")
    stream.submit_incremental("p1", 1, "c")
    stream.submit_incremental("p2", 1, "d")

    last_seen = stream.frame(0).confirmed
    newer = stream.inputs_since(last_seen)
    assert [f.frame for f in newer] == [1]

    everything = stream.inputs_since(-1)
    assert [f.frame for f in everything] == [0, 1]


# --------------------------------------------------------------------------
# Rollback manager
# --------------------------------------------------------------------------


def test_local_orders_are_applied_without_waiting_for_the_server():
    world = FakeWorld()
    manager = make_manager(world)
    manager.submit_local("attack")
    manager.advance()
    # The local order is already in the world.
    assert world.log == [("p1", "attack")]
    assert manager.stats.predicted_frames == 1
    assert manager.stats.rollbacks == 0


def test_confirmed_frame_matching_the_prediction_needs_no_rollback():
    world = FakeWorld()
    manager = make_manager(world)
    manager.submit_local("attack")
    manager.advance()

    confirmed = InputFrame(0, {"p1": (0, "attack"), "p2": (1, "")}, 0)
    assert manager.confirm(confirmed) is None
    manager.advance()
    assert manager.stats.rollbacks == 0
    assert manager.stats.desync_detected == 0
    assert world.counter == 2


def test_conflicting_remote_input_triggers_a_rollback_and_resimulation():
    world = FakeWorld()
    manager = make_manager(world)
    manager.submit_local("attack")
    manager.advance()
    manager.advance()
    manager.advance()
    assert world.counter == 3

    # The server now says p2 did something in frame 0 that we did not know.
    confirmed = InputFrame(0, {"p1": (0, "attack"), "p2": (1, "defend")}, 0)
    assert manager.confirm(confirmed) == 0
    assert manager.needs_rollback()

    manager.advance()
    assert manager.stats.rollbacks == 1
    assert manager.stats.frames_resimulated == 3
    # The remote order is now in the world, in the right place.
    assert world.log == [("p1", "attack"), ("p2", "defend")]
    assert world.counter == 3


# --------------------------------------------------------------------------
# Rollback manager: incremental confirmation (lockstep-free path)
# --------------------------------------------------------------------------


def test_incremental_remote_input_needs_no_rollback_when_it_agrees():
    """The last input of a frame completes it; if it agrees, nothing happens."""
    world = FakeWorld()
    manager = make_manager(world)
    manager.advance()

    # p2 was predicted idle, and p2 really was idle.
    assert manager.confirm_input(0, "p2", "") is None
    assert manager.needs_rollback() is False
    assert manager.stats.desync_detected == 0


def test_incremental_remote_input_triggers_a_rollback_when_it_contradicts():
    """The inputs arrive one by one; the last one contradicts the prediction."""
    world = FakeWorld()
    manager = make_manager(world)
    manager.advance()
    manager.advance()

    # p2's real input for frame 0 turns out to be something else.
    assert manager.confirm_input(0, "p2", "defend") == 0
    assert manager.needs_rollback()

    manager.advance()
    assert manager.stats.rollbacks == 1
    assert world.log == [("p2", "defend")]


def test_incremental_input_for_a_frame_that_is_not_simulated_yet_is_kept():
    """A frame the client has not reached yet is stored, not rejected."""
    world = FakeWorld()
    manager = make_manager(world)

    assert manager.confirm_input(5, "p2", "early") is None
    assert manager.unrecoverable_desync is False

    # When the client reaches that frame, the authoritative input is used.
    for _ in range(6):
        manager.advance()
    assert world.log == [("p2", "early")]


def test_incremental_local_input_is_ignored():
    """The server's echo of the local player's input must not override it."""
    world = FakeWorld()
    manager = make_manager(world)
    manager.submit_local("attack")
    manager.advance()

    # The server echoes something different; the client knows better.
    assert manager.confirm_input(0, "p1", "something else") is None
    assert manager.needs_rollback() is False
    assert world.log == [("p1", "attack")]


def test_incremental_duplicate_input_does_not_change_anything():
    """A retransmission must not trigger a rollback."""
    world = FakeWorld()
    manager = make_manager(world)
    manager.advance()

    assert manager.confirm_input(0, "p2", "defend") == 0
    manager.advance()
    assert manager.stats.rollbacks == 1

    # The same input arriving again changes nothing.
    assert manager.confirm_input(0, "p2", "defend") is None
    assert manager.stats.rollbacks == 1


def test_a_partial_frame_does_not_trigger_a_rollback():
    """A frame is only authoritative once *every* player answered it.

    Until then the missing players are predicted idle, which is the whole
    point: the client does not wait for the slowest player.
    """
    world = FakeWorld()
    manager = make_manager(world, local="p1", players=("p1", "p2", "p3"))
    manager.advance()

    # Only p2 has answered; p3 is still missing.
    assert manager.confirm_input(0, "p2", "defend") is None
    assert manager.needs_rollback() is False
    assert manager.stats.desync_detected == 0

    # Now p3 answers with something different from the prediction.
    assert manager.confirm_input(0, "p3", "attack") == 0
    assert manager.needs_rollback()


def test_rollback_restores_the_world_state_exactly():
    world = FakeWorld()
    manager = make_manager(world)
    manager.submit_local("a")
    manager.advance()
    before = world.counter
    manager.submit_local("b")
    manager.advance()
    manager.submit_local("c")
    manager.advance()
    assert world.counter == before + 2

    manager.confirm(InputFrame(1, {"p1": (0, "b"), "p2": (1, "X")}, 1))
    manager.advance()
    # p2's order was applied to frame 1, so the log has it before "c".
    assert world.log == [("p1", "a"), ("p1", "b"), ("p2", "X"), ("p1", "c")]
    assert world.counter == 3


def test_confirmation_arriving_before_the_frame_is_simulated_is_used():
    world = FakeWorld()
    manager = make_manager(world)
    # The server confirms frame 0 before we get there.
    manager.confirm(InputFrame(0, {"p1": (0, ""), "p2": (1, "early")}, 0))
    manager.advance()
    assert world.log == [("p2", "early")]
    assert manager.stats.predicted_frames == 0
    assert manager.stats.rollbacks == 0


def test_rollback_too_deep_is_refused_rather_than_crashing():
    world = FakeWorld()
    manager = make_manager(world, )
    manager.history_size = 4
    for _ in range(6):
        manager.advance()
    # Frame 0 is no longer in the history, so it cannot be redone.
    manager.confirm(InputFrame(0, {"p1": (0, ""), "p2": (1, "late")}, 0))
    manager.advance()
    assert manager.stats.rollbacks == 0


def test_rollback_too_deep_is_reported_as_an_unrecoverable_desync():
    """A desync that cannot be repaired must be *reported*.

    When the dirty frame is older than the history window there is no
    snapshot to rewind to.  The client then holds a world that the server
    has already contradicted, and it stays wrong.  Silently swallowing that
    would let the client diverge from every other client for the rest of the
    match without anybody noticing, so it is surfaced explicitly.
    """
    world = FakeWorld()
    manager = make_manager(world)
    manager.history_size = 4
    for _ in range(6):
        manager.advance()

    assert manager.unrecoverable_desync is False

    # Frame 0 is gone from the history, so it cannot be redone.
    manager.confirm(InputFrame(0, {"p1": (0, ""), "p2": (1, "late")}, 0))
    manager.advance()

    assert manager.stats.rollbacks == 0
    assert manager.stats.unrecoverable_desyncs == 1
    assert manager.unrecoverable_desync is True

    # The caller can acknowledge it after a full re-sync.
    manager.clear_unrecoverable_desync()
    assert manager.unrecoverable_desync is False


def test_a_confirmation_for_a_frame_that_was_not_simulated_yet_is_not_a_desync():
    """A confirmation that arrives *before* the frame is not a desync.

    The frame simply has not been reached yet, so it will be picked up with
    the authoritative input when it is.
    """
    world = FakeWorld()
    manager = make_manager(world)
    manager.advance()

    # Frame 5 has not been simulated yet.
    manager.confirm(InputFrame(5, {"p1": (0, ""), "p2": (1, "early")}, 5))
    manager.advance()

    assert manager.stats.unrecoverable_desyncs == 0
    assert manager.unrecoverable_desync is False
    assert manager.stats.desync_detected == 0


# --------------------------------------------------------------------------
# Snapshot fidelity against the real simulation
# --------------------------------------------------------------------------


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


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_snapshot_restore_is_bit_exact():
    world = _build_world()
    for _ in range(20):
        world.update()
    snapshot = capture_snapshot(world)
    digest = strong_digest(world)
    for _ in range(10):
        world.update()
    restore_snapshot(world, snapshot)
    assert strong_digest(world) == digest


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rolling_back_and_resimulating_matches_a_straight_run():
    """The core guarantee of the whole redesign.

    A client that rolls back and re-simulates must end up in exactly the
    state a client that never rolled back is in.
    """
    from soundrts.game import TrainingGame
    from soundrts.mapfile import Map
    from soundrts.world import World

    def build():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            m = Map(os.path.join("res", "multi", "cw1.txt"))
            game = TrainingGame(m, ["test", "easy"], ["human", "orc"], ["1", "2"])
            game.record_replay = False
            game.seed = 1234
            game.world = World(game.default_triggers, 1234)
            game.world.load_and_build_map(m)
            game.world.populate_map(game.players, equivalents=True)
        return game.world

    straight = build()
    rolled = build()
    for _ in range(30):
        straight.update()
        rolled.update()

    snapshot = capture_snapshot(rolled)
    # The rolled-back world runs on for a while, then rewinds.
    for _ in range(5):
        rolled.update()
    restore_snapshot(rolled, snapshot)
    for _ in range(5):
        rolled.update()

    for _ in range(5):
        straight.update()

    assert strong_digest(straight) == strong_digest(rolled)


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_restores_fog_memory_objects():
    """Fog-of-war memory copies must survive a rollback.

    A player's ``memory`` holds *copies* of objects that fell out of sight.
    Those copies keep the original object's id, so a naive snapshot that
    keys state by id either overwrites the live object's state or drops the
    copy entirely.  A stale copy has ``place is None``, which makes
    ``Player.updated_target`` resolve the target to ``None`` and silently
    cancel the unit's order.
    """
    world = _build_world()
    for _ in range(30):
        world.update()

    # Find a memory object (a copy of something that left the field of view).
    memory_obj = None
    for player in world.players:
        for remembrance in getattr(player, "memory", ()) or ():
            memory_obj = remembrance
            break
        if memory_obj is not None:
            break
    assert memory_obj is not None, "expected at least one fog memory object"

    original_place = getattr(memory_obj, "place", None)
    snapshot = capture_snapshot(world)

    # Simulate the object leaving the field of view: its memory copy loses
    # its place.
    memory_obj.place = None

    restore_snapshot(world, snapshot)
    assert getattr(memory_obj, "place", None) == original_place


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_restores_unit_actions_and_orders():
    """A unit's ``Action`` and its ``Order`` queue must survive a rollback.

    Actions and orders have no engine id, so they cannot be found in
    ``world.objects``.  They are captured as *children* of their unit; if
    they are captured but not restored, the unit keeps a stale action or a
    stale order (a ``GatherOrder`` whose ``delay`` no longer matches the
    world clock).
    """
    world = _build_world()
    for _ in range(30):
        world.update()

    snapshot = capture_snapshot(world)

    # Mutate a unit's action and order state.
    unit = None
    for player in world.players:
        for u in player.units:
            if getattr(u, "orders", None):
                unit = u
                break
        if unit is not None:
            break
    assert unit is not None

    order = unit.orders[0]
    original_delay = getattr(order, "delay", None)
    original_mode = getattr(order, "mode", None)
    order.delay = 999999
    order.mode = "tampered"

    restore_snapshot(world, snapshot)

    assert getattr(order, "delay", None) == original_delay
    assert getattr(order, "mode", None) == original_mode


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_restores_perception_caches():
    """The world's perception caches must be restored exactly.

    They look like infrastructure, but they decide what a player can see and
    therefore which enemies are picked up.  Restoring them resets the
    world's notion of "already seen", which changes the simulation.
    """
    world = _build_world()
    for _ in range(30):
        world.update()

    snapshot = capture_snapshot(world)

    caches = world._perception_caches
    caches.observed_squares_cache["__tampered__"] = {"x": 1}
    caches.place_visible_bucket = 999999

    restore_snapshot(world, snapshot)

    assert "__tampered__" not in caches.observed_squares_cache
    assert caches.place_visible_bucket != 999999


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_restores_the_order_id_counter():
    """``World._next_order_id`` must be rewound by a rollback.

    The counter is a **class** attribute, so it only appears in the
    instance ``__dict__`` once it has been incremented for the first time.
    A snapshot that reads the instance dictionary alone therefore misses it
    entirely, and the re-simulated orders get *different* ids than the
    original ones — which silently breaks every order that refers to an
    order id.
    """
    world = _build_world()

    # A world that has not issued an order yet has no instance value at all.
    assert "_next_order_id" not in world.__dict__

    snapshot = capture_snapshot(world)

    # Issue a few orders, so the counter moves.
    for _ in range(3):
        world.get_next_order_id()
    assert world.get_next_order_id() == 4

    restore_snapshot(world, snapshot)

    # The counter must be back where it was, not at 5.
    assert world.get_next_order_id() == 1


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_restores_the_next_id_counter():
    """``World._next_id`` must be rewound by a rollback.

    When a unit dies and is rebuilt, the new object gets a fresh id.  If the
    counter is not rewound, the re-simulated world hands out different ids
    than the original one, and the two worlds diverge.
    """
    world = _build_world()
    for _ in range(30):
        world.update()

    snapshot = capture_snapshot(world)
    before = world.get_next_id()
    world.get_next_id()
    world.get_next_id()

    restore_snapshot(world, snapshot)

    assert world.get_next_id() == before


# --------------------------------------------------------------------------
# End-to-end: the real simulation driven through the rollback manager
# --------------------------------------------------------------------------


def _real_manager(world, local_id, remote_id, remote_orders=None):
    """A ``RollbackManager`` wired to the *real* world.

    The manager is given the same three responsibilities the network layer
    would give it:

    * ``apply_inputs`` runs each player's packed orders through the player's
      command dispatcher (the same ``execute_command`` the live client uses);
    * ``step`` advances the simulation by one frame;
    * ``capture`` / ``restore`` use the real snapshot machinery.

    ``remote_orders`` is a ``{frame: orders}`` mapping: it stands for the
    authoritative input the server sends back.  Frames that are *not* in the
    mapping are predicted empty, exactly as a real client would predict a
    remote player who has not answered yet.
    """
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

    def step():
        world.update()

    manager = RollbackManager(
        local_player=local_id,
        players=[local_id, remote_id],
        world=world,
        step=step,
        apply_inputs=apply_inputs,
        capture=lambda: capture_snapshot(world),
        restore=lambda snap: restore_snapshot(world, snap),
        history_size=32,
    )
    return manager


def _order_for(unit_id, target_id):
    """Build the packed order string the live client would send.

    The live protocol sends two commands: ``control`` selects the unit, then
    ``order 0 0 go <target>`` moves it.
    """
    return "control %s\norder 0 0 go %s" % (unit_id, target_id)


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_rollback_manager_replays_real_orders_into_the_real_world():
    """The whole stack, end to end.

    A real world is driven by the real :class:`RollbackManager`.  The local
    player orders a unit to move; the remote player stays idle.  Then the
    server reveals that the remote player *also* moved a unit in an earlier
    frame, which forces a rollback and a re-simulation.

    The result must be identical to a world that received the authoritative
    orders in the right frame the first time.  This is the property the
    entire rollback redesign rests on — and it is only meaningful here
    because the simulation, the snapshot and the orders are all real.
    """
    from soundrts.game import TrainingGame
    from soundrts.mapfile import Map
    from soundrts.world import World

    def build():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            m = Map(os.path.join("res", "multi", "cw1.txt"))
            game = TrainingGame(m, ["test", "easy"], ["human", "orc"], ["1", "2"])
            game.record_replay = False
            game.seed = 1234
            game.world = World(game.default_triggers, 1234)
            game.world.load_and_build_map(m)
            game.world.populate_map(game.players, equivalents=True)
        return game.world

    straight = build()
    rolled = build()

    local_id = straight.players[0].id
    remote_id = straight.players[1].id

    def first_moving_unit(world):
        for player in world.players:
            for unit in player.units:
                if getattr(unit, "type_name", "") in ("peasant", "footman", "archer"):
                    return unit
        raise AssertionError("no movable unit found")

    straight_unit = first_moving_unit(straight)
    rolled_unit = first_moving_unit(rolled)
    assert straight_unit.id == rolled_unit.id

    # The target is a neighbouring square, so the order is actually accepted.
    target_id = None
    for exit_square in getattr(straight_unit.place, "exits", ()) or ():
        target_id = exit_square.id
        break
    assert target_id is not None

    local_order = _order_for(straight_unit.id, target_id)

    # The remote player also moves a unit, but only in frame 3.  The client
    # has to *predict* frame 3 as empty and roll back when the truth arrives.
    remote_unit = None
    for unit in straight.players[1].units:
        if getattr(unit, "type_name", "") in ("peasant", "footman", "archer"):
            remote_unit = unit
            break
    assert remote_unit is not None
    remote_target = None
    for exit_square in getattr(remote_unit.place, "exits", ()) or ():
        remote_target = exit_square.id
        break
    remote_order = _order_for(remote_unit.id, remote_target)

    # -- the straight run: every order applied in the frame it belongs to --
    for frame in range(12):
        if frame == 5:
            straight.players[0].execute_command("control %s" % straight_unit.id)
            straight.players[0].execute_command("order 0 0 go %s" % target_id)
        if frame == 3:
            straight.players[1].execute_command("control %s" % remote_unit.id)
            straight.players[1].execute_command("order 0 0 go %s" % remote_target)
        straight.update()

    # -- the rolled-back run: same orders, but the remote one arrives late --
    manager = _real_manager(rolled, local_id, remote_id)
    for frame in range(12):
        if frame == 5:
            manager.submit_local(local_order)
        manager.advance()

    # The two worlds *must* differ at this point: the straight run already
    # applied the remote order, the rolled-back run predicted it as empty.
    # Without this assertion the test could pass while proving nothing.
    assert strong_digest(straight) != strong_digest(rolled)

    # The server now confirms frame 3, with a remote order we did not know.
    confirmed = InputFrame(
        3,
        {local_id: (0, ""), remote_id: (1, remote_order)},
        4,
    )
    assert manager.confirm(confirmed) == 3
    assert manager.needs_rollback()

    # The rollback happens on the next advance, and re-simulates the frames
    # that were predicted wrongly.
    manager.advance()
    assert manager.stats.rollbacks == 1
    assert manager.stats.frames_resimulated >= 1

    # Run the remaining frames so both worlds end at the same point.
    while manager.current_frame < 12:
        manager.advance()

    assert manager.current_frame == 12
    assert strong_digest(straight) == strong_digest(rolled)


# --------------------------------------------------------------------------
# End-to-end: a server and two clients talking the incremental protocol
# --------------------------------------------------------------------------


def _network_order_for(world, player_index, target_offset=0):
    """Build a ``(player_id, orders)`` pair for a real unit of *player_index*."""
    player = world.players[player_index]
    for unit in player.units:
        if getattr(unit, "type_name", "") in ("peasant", "footman", "archer"):
            exits = list(getattr(unit.place, "exits", ()) or ())
            if not exits:
                continue
            target = exits[target_offset % len(exits)]
            return player.id, _order_for(unit.id, target.id)
    raise AssertionError("no movable unit found")


@pytest.mark.skipif(
    not os.path.isfile(os.path.join("res", "multi", "cw1.txt")),
    reason="cw1 map not present",
)
def test_two_clients_converge_over_the_incremental_protocol():
    """A whole match, over the wire, with latency.

    Two clients run the *real* simulation.  The server is the real
    :class:`InputStream`.  Inputs travel with a delay, so each client
    predicts the other's moves and has to roll back when the truth arrives.

    At the end, both clients must be in exactly the same state — and that
    state must equal the one a client that never had to roll back reaches.

    This is the property the whole redesign rests on: the netcode may
    reorder, delay and re-simulate, and the simulation must still end up in
    the same place.
    """
    from soundrts.game import TrainingGame
    from soundrts.mapfile import Map
    from soundrts.world import World

    def build():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            m = Map(os.path.join("res", "multi", "cw1.txt"))
            game = TrainingGame(m, ["test", "easy"], ["human", "orc"], ["1", "2"])
            game.record_replay = False
            game.seed = 1234
            game.world = World(game.default_triggers, 1234)
            game.world.load_and_build_map(m)
            game.world.populate_map(game.players, equivalents=True)
        return game.world

    reference = build()
    world_a = build()
    world_b = build()

    ids = [reference.players[0].id, reference.players[1].id]
    order_a = _network_order_for(reference, 0)
    order_b = _network_order_for(reference, 1)
    # The same orders are issued in both worlds (the unit ids are the same,
    # because both worlds were built from the same seed).
    order_a2 = (ids[0], order_a[1])
    order_b2 = (ids[1], order_b[1])

    stream = InputStream(ids)

    # The pending messages, as if they were in flight.
    inbox_a = []
    inbox_b = []

    def deliver(target, message, delay):
        target.append((delay, message))

    # -- the reference run: every order applied in the frame it belongs to --
    LOCAL_FRAME_A = 4
    LOCAL_FRAME_B = 7
    NB_FRAMES = 16

    def apply_order(world, player_index, orders):
        """Apply a multi-line order string, one command per line."""
        player = world.players[player_index]
        for line in orders.split("\n"):
            if line:
                player.execute_command(line)

    for frame in range(NB_FRAMES):
        if frame == LOCAL_FRAME_A:
            apply_order(reference, 0, order_a2[1])
        if frame == LOCAL_FRAME_B:
            apply_order(reference, 1, order_b2[1])
        reference.update()

    manager_a = _real_manager(world_a, ids[0], ids[1])
    manager_a.history_size = 64
    manager_b = _real_manager(world_b, ids[1], ids[0])
    manager_b.history_size = 64

    # Each client sends its input for a frame, and the server stamps and
    # forwards it to the *other* client with a delay.
    LATENCY_A = 3   # frames of delay for the messages towards client A
    LATENCY_B = 5   # frames of delay for the messages towards client B

    for frame in range(NB_FRAMES):
        # -- what each client sends to the server --
        sent_a = order_a2[1] if frame == LOCAL_FRAME_A else ""
        sent_b = order_b2[1] if frame == LOCAL_FRAME_B else ""

        # -- the server stamps both inputs and forwards them --
        stamped_a = stream.submit_incremental(ids[0], frame, sent_a)
        stamped_b = stream.submit_incremental(ids[1], frame, sent_b)
        assert stamped_a is not None
        assert stamped_b is not None

        # Client B only needs client A's input, and vice versa.
        deliver(
            inbox_a,
            encode_input(stamped_b[0], ids[1], stamped_b[1], stamped_b[2]),
            LATENCY_A,
        )
        deliver(
            inbox_b,
            encode_input(stamped_a[0], ids[0], stamped_a[1], stamped_a[2]),
            LATENCY_B,
        )

        # -- what each client has received by now --
        for message in list(inbox_b):
            delay, payload = message
            if delay > 0:
                continue
            inbox_b.remove(message)
            frame_no, player_id, seq, orders = decode_input(payload)
            manager_b.confirm_input(frame_no, player_id, orders)
        for message in list(inbox_a):
            delay, payload = message
            if delay > 0:
                continue
            inbox_a.remove(message)
            frame_no, player_id, seq, orders = decode_input(payload)
            manager_a.confirm_input(frame_no, player_id, orders)

        # -- each client runs its own input --
        if frame == LOCAL_FRAME_A:
            manager_a.submit_local(order_a2[1])
        if frame == LOCAL_FRAME_B:
            manager_b.submit_local(order_b2[1])

        # -- and simulates --
        while manager_a.needs_rollback():
            manager_a.advance()
        while manager_b.needs_rollback():
            manager_b.advance()
        manager_a.advance()
        manager_b.advance()

        # Age the in-flight messages.
        inbox_a = [(d - 1, m) for (d, m) in inbox_a]
        inbox_b = [(d - 1, m) for (d, m) in inbox_b]

    # Let the last messages arrive, and let both clients repair their state.
    # This must *not* advance the simulation: the clients have already
    # simulated the frames in question, they only need to re-simulate them
    # with the truth (which is what a rollback does).
    for _ in range(10):
        for message in list(inbox_b):
            delay, payload = message
            if delay > 0:
                continue
            inbox_b.remove(message)
            frame_no, player_id, seq, orders = decode_input(payload)
            manager_b.confirm_input(frame_no, player_id, orders)
        for message in list(inbox_a):
            delay, payload = message
            if delay > 0:
                continue
            inbox_a.remove(message)
            frame_no, player_id, seq, orders = decode_input(payload)
            manager_a.confirm_input(frame_no, player_id, orders)
        # A rollback re-simulates the affected frames, but does not move the
        # clients forward in time.
        while manager_a.needs_rollback():
            manager_a.advance()
        while manager_b.needs_rollback():
            manager_b.advance()

    # Both clients ran the same number of frames.
    assert manager_a.current_frame == manager_b.current_frame
    assert manager_a.current_frame == NB_FRAMES

    # Neither client ended up in an unrecoverable desync.
    assert manager_a.unrecoverable_desync is False
    assert manager_b.unrecoverable_desync is False

    # Both clients really did have to roll back: the latency made them
    # predict the other player's move wrongly.  Without this assertion the
    # test could pass while proving nothing.
    assert manager_a.stats.rollbacks >= 1
    assert manager_b.stats.rollbacks >= 1
    assert manager_a.stats.frames_resimulated >= 1
    assert manager_b.stats.frames_resimulated >= 1

    # And they agree with each other, and with the reference run.
    assert strong_digest(world_a) == strong_digest(world_b)
    assert strong_digest(world_a) == strong_digest(reference)
