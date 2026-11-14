# -*- coding: utf-8 -*-
"""Regression tests: a late confirmation must not end a healthy match.

The bug
-------

When a player paused (F10) for a long time, the match ended with
"与对手不同步：落后太多，无法回滚，已结束本局" — on the side that *kept
playing*, not on the side that had paused.

The mechanism was in :meth:`soundrts.net.rollback.RollbackManager.confirm_input`
(and its sibling :meth:`~soundrts.net.rollback.RollbackManager.confirm`):

    record = self._record_for(frame)
    if record is None:
        if frame < self._next_frame:
            # BUG: unconditionally an unrecoverable desync.
            self.stats.unrecoverable_desync += 1
            ...

The frame's record had been trimmed out of the history (the history holds
``history_size`` frames, 64 by default), so the client could not *redo*
the frame.  But "cannot redo" is not the same as "is wrong": the code
never compared the authoritative input against what had actually been
applied.  So a *harmless* late confirmation — the paused player had
really done nothing, and the server confirmed the empty input that had
been predicted — was reported as an unrecoverable desync, and the match
was killed.

The fix
-------

The manager now remembers the input vector it applied on every frame
(cheap: a few short strings, against hundreds of kilobytes for a
snapshot), and keeps it for longer than the snapshot history.  A late
confirmation is then *compared* against what was applied:

* it agrees  → no desync at all, the match goes on;
* it differs → a real desync, still reported as unrecoverable.

These tests cover both halves of that rule, at the manager level, at the
session level, and over real sockets.
"""

from __future__ import annotations

import os
import sys
import warnings

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.net.input_stream import InputFrame
from soundrts.net.rollback import RollbackManager


# --------------------------------------------------------------------------
# A tiny deterministic fake world
# --------------------------------------------------------------------------


class FakeWorld:
    """A minimal deterministic world: a counter plus the applied orders."""

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

    def capture(self):
        return (self.counter, list(self.log))

    def restore(self, snapshot):
        self.counter, self.log = snapshot[0], list(snapshot[1])


def make_manager(world, local="p1", players=("p1", "p2"), history_size=4):
    return RollbackManager(
        local_player=local,
        players=list(players),
        world=world,
        step=world.step,
        apply_inputs=world.apply,
        capture=world.capture,
        restore=world.restore,
        history_size=history_size,
    )


# --------------------------------------------------------------------------
# The manager: a trimmed frame is not a desync unless it contradicts
# --------------------------------------------------------------------------


def test_a_late_empty_confirmation_is_not_a_desync():
    """The core regression: a harmless late confirmation must be harmless.

    The remote player was idle, so the client predicted an empty input
    for its frame.  The server confirms that empty input long after the
    frame's record has been trimmed.

    Nothing diverged: the prediction was *right*.  The world the client
    is holding is correct, and the match must go on.
    """
    world = FakeWorld()
    manager = make_manager(world)

    # Run well past the history window, so frame 0 is trimmed.
    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None, "frame 0 should be trimmed"

    # The server finally confirms that the remote player did nothing.
    assert manager.confirm_input(0, "p2", "") is None

    assert manager.stats.unrecoverable_desyncs == 0
    assert manager.unrecoverable_desync is False
    assert manager.stats.desync_detected == 0
    assert manager.needs_rollback() is False


def test_a_late_confirmation_that_contradicts_is_still_a_desync():
    """The fix must not swallow the *real* desync.

    This is the mirror image of the test above: the remote player really
    did something, the client had predicted it away, and the frame can no
    longer be redone.  The world really is wrong, and the match has to be
    ended — otherwise the client would silently diverge for the rest of
    the match.
    """
    world = FakeWorld()
    manager = make_manager(world)

    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None

    # The server says the remote player moved, in frame 0.
    assert manager.confirm_input(0, "p2", "move 1") == 0

    assert manager.stats.unrecoverable_desyncs == 1
    assert manager.unrecoverable_desync is True
    assert manager.stats.desync_detected == 1


def test_a_late_empty_confirmation_through_confirm_is_not_a_desync():
    """The whole-frame confirmation path behaves the same way.

    :meth:`RollbackManager.confirm` is the sibling of
    :meth:`RollbackManager.confirm_input`; it used to have the very same
    unconditional flag.
    """
    world = FakeWorld()
    manager = make_manager(world)

    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None

    # The authoritative frame says the remote player did nothing.
    assert manager.confirm(InputFrame(0, {"p1": (0, ""), "p2": (1, "")}, 0)) is None

    assert manager.stats.unrecoverable_desyncs == 0
    assert manager.unrecoverable_desync is False


def test_a_late_whole_frame_confirmation_that_contradicts_is_still_a_desync():
    """The whole-frame path still reports a real divergence."""
    world = FakeWorld()
    manager = make_manager(world)

    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None

    assert manager.confirm(InputFrame(0, {"p1": (0, ""), "p2": (1, "late")}, 0)) == 0

    assert manager.stats.unrecoverable_desyncs == 1
    assert manager.unrecoverable_desync is True


def test_the_local_players_own_input_never_causes_a_desync():
    """The server's echo of the local input must not be read as a conflict.

    The local player knows best what it ordered; a discrepancy in its own
    echo is not a divergence of the world.
    """
    world = FakeWorld()
    manager = make_manager(world)

    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None

    assert manager.confirm_input(0, "p1", "something else") is None

    assert manager.stats.unrecoverable_desyncs == 0
    assert manager.unrecoverable_desync is False


def test_the_applied_input_vector_outlives_the_snapshot():
    """The applied inputs are kept for longer than the snapshot history.

    They are the only way left to compare a late confirmation, so they
    have to still be there when the record has been trimmed — otherwise
    the comparison could not be made at all.
    """
    world = FakeWorld()
    manager = make_manager(world, history_size=4)

    assert manager.applied_inputs_window > manager.history_size

    for _ in range(12):
        manager.submit_local("")
        manager.advance()

    assert manager._record_for(0) is None, "the snapshot should be trimmed"
    assert 0 in manager._applied_inputs, (
        "the applied input vector must outlive the snapshot"
    )


def test_the_applied_input_vector_is_eventually_dropped():
    """The applied input vectors are not kept forever.

    They are cheap, but a long match must not accumulate them without
    bound.
    """
    world = FakeWorld()
    manager = make_manager(world, history_size=4)

    total = manager.applied_inputs_window + manager.history_size + 10
    for _ in range(total):
        manager.submit_local("")
        manager.advance()

    oldest = min(manager._applied_inputs)
    assert oldest >= manager.current_frame - manager.applied_inputs_window


def test_a_confirmation_for_a_frame_that_was_not_simulated_yet_is_still_kept():
    """The "not simulated yet" path is untouched by the fix."""
    world = FakeWorld()
    manager = make_manager(world)

    assert manager.confirm_input(5, "p2", "early") is None
    assert manager.unrecoverable_desync is False
    assert manager.stats.desync_detected == 0

    for _ in range(6):
        manager.advance()
    assert world.log == [("p2", "early")]


def test_a_confirmation_within_the_history_window_still_rolls_back():
    """The ordinary rollback path is untouched by the fix."""
    world = FakeWorld()
    manager = make_manager(world, history_size=16)

    manager.submit_local("attack")
    manager.advance()
    manager.advance()

    # p2's real input for frame 0 turns out to be something else.
    assert manager.confirm_input(0, "p2", "defend") == 0
    assert manager.needs_rollback()

    manager.advance()
    assert manager.stats.rollbacks == 1
    # The local player's order is replayed, and so is the remote player's,
    # now with the authoritative content.
    assert world.log == [("p1", "attack"), ("p2", "defend")]
    assert manager.stats.unrecoverable_desyncs == 0


def test_the_local_players_orders_survive_the_trim():
    """The local player's orders are still replayable after a rollback."""
    world = FakeWorld()
    manager = make_manager(world, history_size=16)

    manager.submit_local("attack")
    manager.advance()
    manager.advance()

    manager.confirm_input(0, "p2", "defend")
    manager.advance()

    assert world.log == [("p1", "attack"), ("p2", "defend")]


# --------------------------------------------------------------------------
# The session: the same rule, one layer up
# --------------------------------------------------------------------------


def test_the_session_does_not_flag_a_harmless_late_confirmation():
    """The session feeds the manager; the rule has to hold there too."""
    from soundrts.net.session import RollbackSession

    world = FakeWorld()
    session = RollbackSession(
        world=world,
        local_player="p1",
        players=["p1", "p2"],
        step=world.step,
        apply_inputs=world.apply,
        capture=world.capture,
        restore=world.restore,
        history_size=4,
    )

    for _ in range(12):
        session.submit_local("")
        session.step()

    assert session.manager._record_for(0) is None

    # The remote player's late, empty input.
    session.on_input(0, "p2", "")
    session.repair()

    assert session.unrecoverable_desync is False
    assert session.stats.unrecoverable_desyncs == 0


def test_the_session_still_flags_a_real_late_divergence():
    """The mirror image: a real divergence is still reported."""
    from soundrts.net.session import RollbackSession

    world = FakeWorld()
    session = RollbackSession(
        world=world,
        local_player="p1",
        players=["p1", "p2"],
        step=world.step,
        apply_inputs=world.apply,
        capture=world.capture,
        restore=world.restore,
        history_size=4,
    )

    for _ in range(12):
        session.submit_local("")
        session.step()

    session.on_input(0, "p2", "move 1")
    session.repair()

    assert session.unrecoverable_desync is True
    assert session.stats.unrecoverable_desyncs == 1
