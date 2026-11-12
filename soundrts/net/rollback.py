"""Client-side rollback: predict, then correct.

How rollback works here
-----------------------

The client runs the simulation *ahead* of the server.  Every simulation frame
is a rectangle of inputs (one per player).  The client:

1. **predicts** the inputs it does not have yet — its own orders are known
    immediately, remote orders are predicted as "nothing" until the server
    confirms them;
2. **applies** the predicted frame and steps the simulation;
3. **stores** the state from before the frame ran, so it can go back;
4. when the server's authoritative frame arrives and *contradicts* the
    prediction, it **rolls back** to the affected frame and **re-simulates**
    from there with the confirmed inputs.

The invariant that makes this correct is that the simulation is
deterministic: given the same starting state and the same ordered inputs,
``World.update()`` produces exactly the same next state.  That is why
:mod:`soundrts.net.snapshot` had to be bit-exact — a snapshot that loses one
bit of state would fork the world on every rollback.

The three pieces
----------------

:class:`RollbackManager`
    Owns the confirmed/predicted frame history and the re-simulation loop.
    This is the class the network layer talks to.

:class:`FrameRecord`
    What the client *did* with one frame: the inputs it applied and the
    snapshot taken before the frame ran.  Kept so a rollback can redo the
    frame with different inputs.

:class:`RollbackStats`
    Counters the client can surface in a debug overlay.

Prediction policy
-----------------

Only the *local* player's input is predicted.  Remote inputs are predicted
as empty ("the remote player did nothing this frame"), which is the
conservative choice: it never invents an order that the remote player did
not issue.  When the real remote input arrives and differs from the
prediction, the affected frame is rolled back and re-simulated.

This is the classic GGPO trade-off, and it is the right one for an RTS: a
mistaken remote order is rare (players act every few seconds), while a
mistaken *local* order would be felt immediately and constantly.
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .input_stream import InputFrame, unpack_orders
from .snapshot import Snapshot, capture_snapshot, restore_snapshot

__all__ = [
    "FrameRecord",
    "RollbackManager",
    "RollbackStats",
]


class RollbackStats:
    """Counters describing how much work the rollback machinery did."""

    __slots__ = (
        "frames_simulated",
        "rollbacks",
        "frames_resimulated",
        "max_rollback_depth",
        "predicted_frames",
        "desync_detected",
        "unrecoverable_desyncs",
    )

    def __init__(self):
        self.frames_simulated = 0
        self.rollbacks = 0
        self.frames_resimulated = 0
        self.max_rollback_depth = 0
        self.predicted_frames = 0
        self.desync_detected = 0
        # How often a desync could *not* be repaired because the dirty frame
        # was older than the history window.
        self.unrecoverable_desyncs = 0

    def as_dict(self):
        return {
            "frames_simulated": self.frames_simulated,
            "rollbacks": self.rollbacks,
            "frames_resimulated": self.frames_resimulated,
            "max_rollback_depth": self.max_rollback_depth,
            "predicted_frames": self.predicted_frames,
            "desync_detected": self.desync_detected,
            "unrecoverable_desyncs": self.unrecoverable_desyncs,
        }

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<RollbackStats %r>" % (self.as_dict(),)


class FrameRecord:
    """What happened during one frame.

    Attributes:
        frame: the frame number.
        inputs: player id -> order string that was *applied*.
        predicted: whether the frame contained a prediction (i.e. it was
            applied before the server confirmed it).
        snapshot: the world state *before* the frame ran.
    """

    __slots__ = ("frame", "inputs", "predicted", "snapshot")

    def __init__(
        self,
        frame: int,
        inputs: Dict[str, str],
        predicted: bool,
        snapshot: Optional[Snapshot],
    ):
        self.frame = frame
        self.inputs = inputs
        self.predicted = predicted
        self.snapshot = snapshot


class RollbackManager:
    """Drives prediction, rollback and re-simulation for one client.

    The manager does not know how to simulate.  It is given a *step*
    callable that advances the world by exactly one frame, and an *apply*
    callable that hands one frame's inputs to the world.  That keeps the
    rollback logic independent of the game's command plumbing, and makes it
    testable with a trivial fake world.

    Attributes:
        local_player: the id of the player this client controls.
        players: every participating player id, in a stable order.
        world: the world object whose state is snapshotted.
        confirmed: the authoritative frames received from the server.
        history: the frames that have been simulated, oldest first.
    """

    def __init__(
        self,
        local_player: str,
        players: Sequence[str],
        world,
        step: Callable[[], None],
        apply_inputs: Callable[[Dict[str, str]], None],
        capture: Optional[Callable[[], Snapshot]] = None,
        restore: Optional[Callable[[Snapshot], None]] = None,
        history_size: int = 64,
    ):
        self.local_player = local_player
        self.players: List[str] = list(players)
        # The players that quit the match.  They are no longer waited for,
        # but their confirmed orders are still part of the authoritative
        # content of the frames they answered, so they stay in the input
        # vector of those frames.
        self._departed: List[str] = []
        self.world = world
        self._step = step
        self._apply_inputs = apply_inputs
        self._capture = capture if capture is not None else (lambda: capture_snapshot(world))
        self._restore = restore if restore is not None else (
            lambda snap: restore_snapshot(world, snap)
        )
        self.history: List[FrameRecord] = []
        self.history_size = max(4, history_size)
        self.confirmed: Dict[int, InputFrame] = {}
        self.local_inputs: Dict[int, str] = {}
        self.stats = RollbackStats()
        self._next_frame = 0
        self._rollback_target: Optional[int] = None
        # Set when a desync could not be repaired (the dirty frame was older
        # than the history window).  The world is then provably wrong and the
        # caller has to decide what to do.
        self._unrecoverable_desync = False
        # The local player's orders are submitted from the *interface* thread
        # (the player presses a key) but consumed and trimmed on the *world*
        # thread (which steps the simulation).  Without a lock, the world
        # thread can iterate ``local_inputs`` while the interface thread adds
        # an entry to it, which raises "dictionary changed size during
        # iteration" and would drop the order.
        #
        # It is a *re-entrant* lock, because the frame a set of orders
        # belongs to is read and the orders are stored under the same lock:
        # the frame must not be able to move between the two, or the orders
        # would land on a frame that has already been simulated — and be
        # silently dropped.
        self._inputs_lock = threading.RLock()

    # -- state -----------------------------------------------------------

    @property
    def current_frame(self) -> int:
        """The number of the next frame to simulate."""
        return self._next_frame

    @property
    def confirmed_frame(self) -> int:
        """The highest frame the server has confirmed for this client."""
        if not self.confirmed:
            return -1
        return max(self.confirmed)

    def _record_for(self, frame: int) -> Optional[FrameRecord]:
        for record in self.history:
            if record.frame == frame:
                return record
        return None

    # -- input -----------------------------------------------------------

    def submit_local(self, orders: str, frame: Optional[int] = None) -> int:
        """Record the local player's orders for a frame.

        The local player's input is never wrong: it comes from the local
        player.  It is therefore applied immediately (that is the whole
        point of prediction — no waiting for the server round trip).

        The orders are stored **per frame** so that a re-simulation can
        replay them: when the client rolls back, the local player's own
        commands must be applied again, exactly as they were the first
        time.

        Args:
            orders: the packed order string.
            frame: the frame the orders belong to.  Defaults to the next
                frame to be simulated.

        Returns:
            The frame the orders were recorded for.  The caller has to tell
            the server about *that* frame: it is the frame the orders will
            be applied on, on every client.
        """
        with self._inputs_lock:
            if frame is None:
                frame = self._next_frame
            self.local_inputs[frame] = orders
            return frame

    def _frame_is_complete(self, frame: int) -> bool:
        """Has every *remote* player answered *frame*?

        The local player's input never has to arrive from the server: the
        client is the one that produced it.
        """
        confirmed = self.confirmed.get(frame)
        if confirmed is None:
            return False
        return all(
            pid in confirmed.inputs for pid in self.players if pid != self.local_player
        )

    def frame_is_complete(self, frame: int) -> bool:
        """Has every *remote* player's authoritative input for *frame* arrived?

        Once this is true, the content of the frame is final: the server
        stamps an input only once, so a confirmed frame can never be
        contradicted afterwards.
        """
        return self._frame_is_complete(frame)

    def remove_player(self, player_id: str) -> None:
        """Drop a player that quit the match.

        The quitter will never answer the frames it was supposed to answer,
        so the client must stop waiting for it.  The frames it left open are
        closed with an empty input — that is what the server does too, so
        the two sides agree on the content of those frames.

        Dropping the player is enough for the *waiting* to stop (the frame
        is complete as soon as the remaining players have answered).  The
        frames that were applied with the quitter still waiting for its
        answer are re-checked, because the authoritative content of those
        frames may now differ from what was applied.

        The quitter is *not* forgotten, though: it is moved to
        :attr:`_departed`.  It still has to be part of the input vector of
        the frames it answered, because the server's authoritative record
        of those frames contains its orders.  Dropping it from the vector
        entirely would make every re-simulation of those frames apply one
        order less than the server did, and the client would silently
        diverge from the server and from every spectator.
        """
        if player_id not in self.players:
            return
        self.players.remove(player_id)
        if player_id not in self._departed:
            self._departed.append(player_id)
        for frame, confirmed in list(self.confirmed.items()):
            if not self._frame_is_complete(frame):
                continue
            record = self._record_for(frame)
            if record is None:
                continue
            if self._matches(record, confirmed):
                continue
            # The frame was applied with a prediction, and the truth is now
            # known: everything from this frame on has to be redone.
            self.stats.desync_detected += 1
            if self._rollback_target is None or frame < self._rollback_target:
                self._rollback_target = frame

    def _inputs_for(self, frame: int) -> Tuple[Dict[str, str], bool]:
        """Build the input vector for *frame*.

        Returns the inputs and whether the frame is (partly) predicted.
        """
        with self._inputs_lock:
            local_orders = self.local_inputs.get(frame, "")
        confirmed = self.confirmed.get(frame)
        if confirmed is not None:
            # The vector contains the players who are still in the match
            # *and* the ones who left: a quitter's orders are part of the
            # authoritative content of the frames it answered, so they must
            # be applied again when the frame is re-simulated.
            vector_players = list(self.players) + [
                pid for pid in self._departed if pid != self.local_player
            ]
            inputs = {pid: confirmed.order_for(pid) for pid in vector_players}
            # A player that did not answer the server keeps its empty
            # prediction, which is what the server confirmed too.
            for pid in confirmed.inputs:
                inputs.setdefault(pid, "")
            # The local player's own input is known locally and wins over
            # the server's copy: it is what the local player actually did.
            inputs[self.local_player] = local_orders
            # A frame is only fully authoritative once every remote player
            # has answered it.  Until then the remaining players are still
            # predicted, and the frame counts as predicted.
            return inputs, not self._frame_is_complete(frame)

        # No confirmation yet: predict.  The local player's orders are known;
        # remote players are predicted to be idle.
        inputs = {pid: "" for pid in self.players}
        if local_orders:
            inputs[self.local_player] = local_orders
        return inputs, True

    # -- simulation ------------------------------------------------------

    def advance(self) -> bool:
        """Simulate one more frame.

        Returns ``True`` when the frame was simulated normally.  Returns
        ``False`` when a rollback had to happen first; the frame is then
        simulated as part of the re-simulation, so the caller should not
        advance again.
        """
        if self._rollback_target is not None:
            self._perform_rollback()
            return False

        # The frame counter moves *before* the inputs are read, and both
        # happen under the same lock as the local inputs.  The interface
        # thread submits the local player's orders concurrently, and it has
        # to know which frame they belong to: if the counter could move
        # between that read and the recording of the orders, the orders
        # would land on a frame that has already been simulated, and would
        # be silently dropped.
        #
        # The lock is released before the simulation itself: it is the
        # expensive part (a whole world frame), and the interface thread
        # must not be blocked by it.
        with self._inputs_lock:
            frame = self._next_frame
            self._next_frame = frame + 1
            inputs, predicted = self._inputs_for(frame)
            if predicted:
                self.stats.predicted_frames += 1

        snapshot = self._capture()
        self._apply_inputs(inputs)
        self._step()

        self.history.append(FrameRecord(frame, inputs, predicted, snapshot))
        self._trim_history()
        self.stats.frames_simulated += 1
        return True

    def _trim_history(self) -> None:
        if len(self.history) > self.history_size:
            del self.history[: len(self.history) - self.history_size]
        # Local inputs older than the history can never be replayed, so they
        # are dropped: the client only needs to remember what it might have
        # to roll back to.
        if self.history:
            oldest = self.history[0].frame
            with self._inputs_lock:
                for frame in [f for f in self.local_inputs if f < oldest]:
                    del self.local_inputs[frame]
            for frame in [f for f in self.confirmed if f < oldest]:
                del self.confirmed[frame]

    # -- confirmation ----------------------------------------------------

    def confirm_input(
        self, frame: int, player_id: str, orders: str, packed: bool = False
    ) -> Optional[int]:
        """Receive **one** player's authoritative input for *frame*.

        This is the client-side counterpart of
        :meth:`soundrts.net.input_stream.InputStream.submit_incremental`:
        the server sends the inputs of a frame one by one, as they arrive,
        so the client is not made to wait for the whole frame.

        A frame only becomes *authoritative* once every player has answered
        it.  Until then the client keeps predicting the missing players as
        idle.  When the last input arrives, the frame is complete and is
        compared against what was applied:

        * if they agree, nothing happens;
        * if they disagree, the frame is scheduled for a rollback.

        Returns the frame number a rollback is needed for, or ``None``.

        The local player's own input is never taken from the server: the
        client knows what the local player did, and the server's copy is
        merely an echo of it.

        Args:
            frame: the frame the input belongs to.
            player_id: who the input is from.
            orders: the order string.
            packed: whether *orders* is still in the packed (wire) form.
                It is unpacked here when it is.
        """
        if player_id == self.local_player:
            # The local player's input is authoritative already; the server
            # only echoes it back.
            return None

        if packed:
            orders = unpack_orders(orders)

        known = self.confirmed.get(frame)
        inputs = dict(known.inputs) if known is not None else {}
        if player_id in inputs:
            # Already known: a retransmission must not change anything.
            #
            # The *first* confirmation wins, even when the orders differ.
            # A differing second copy can only come from a source that
            # disagrees with the authoritative record -- for instance the
            # empty input the server synthesises when a player quits,
            # broadcast for a frame the quitter had already answered.
            # Overwriting the real orders with that empty input would
            # silently corrupt the frame and fork the client from the
            # server and from every spectator.
            return None
        inputs[player_id] = (0, orders)

        frame_obj = InputFrame(frame, inputs, confirmed=frame)
        self.confirmed[frame] = frame_obj

        # The frame is only authoritative once every *remote* player
        # answered it.  The local player's input is known already — the
        # client is the one that produced it — so it never has to arrive
        # from the server.
        if not all(
            pid in inputs for pid in self.players if pid != self.local_player
        ):
            # Still incomplete: the client keeps predicting the missing
            # players as idle, and no rollback is needed yet.
            return None

        record = self._record_for(frame)
        if record is None:
            if frame < self._next_frame:
                # The frame was simulated, but its record has been trimmed
                # from the history, so it cannot be redone.
                self.stats.desync_detected += 1
                self.stats.unrecoverable_desyncs += 1
                self._unrecoverable_desync = True
                return frame
            # Not simulated yet: it will be picked up when it is reached.
            return None

        if self._matches(record, frame_obj):
            return None

        # The authoritative frame differs from what was applied: everything
        # from this frame on has to be redone.
        self.stats.desync_detected += 1
        if self._rollback_target is None or frame < self._rollback_target:
            self._rollback_target = frame
        return frame

    def confirm(self, frame_obj: InputFrame) -> Optional[int]:
        """Receive an authoritative frame from the server.

        Returns the frame number a rollback is needed for, or ``None`` when
        the confirmation agrees with what was applied (or when the frame has
        not been simulated yet).

        The confirmation may arrive *before* the frame was simulated (it is
        then stored for later) or *after* (it is then compared against what
        was applied, and a mismatch schedules a rollback).
        """
        number = frame_obj.frame
        existing = self.confirmed.get(number)
        if existing is not None and (
            existing.orders_signature() == frame_obj.orders_signature()
        ):
            # Duplicate confirmation of the same content: nothing to do.
            return None
        self.confirmed[number] = frame_obj

        record = self._record_for(number)
        if record is None:
            if number < self._next_frame:
                # The frame *was* simulated, but its record has already been
                # trimmed from the history: the snapshot needed to rewind to
                # it no longer exists.  The world therefore holds a
                # prediction that the server has just contradicted, and it
                # cannot be repaired.  This must not be mistaken for
                # "not simulated yet" — that would leave the client silently
                # desynced for the rest of the match.
                self.stats.desync_detected += 1
                self.stats.unrecoverable_desyncs += 1
                self._unrecoverable_desync = True
                return number
            # Not simulated yet: it will be picked up when it is reached.
            return None

        if self._matches(record, frame_obj):
            return None

        # The authoritative frame differs from what was applied: everything
        # from this frame on has to be redone.
        self.stats.desync_detected += 1
        if self._rollback_target is None or number < self._rollback_target:
            self._rollback_target = number
        return number

    def _matches(self, record: FrameRecord, frame_obj: InputFrame) -> bool:
        """Does the confirmed frame agree with what was applied?

        Only the *remote* players are compared.  The local player's input is
        the client's own: the server merely echoes it back, and a
        discrepancy there (a re-packing, a truncated packet) must not
        trigger a rollback — the local player knows best what it ordered.
        """
        for pid in set(record.inputs) | set(frame_obj.inputs):
            if pid == self.local_player:
                continue
            applied = record.inputs.get(pid, "")
            if applied != frame_obj.order_for(pid):
                return False
        return True

    # -- rollback --------------------------------------------------------

    def _perform_rollback(self) -> None:
        """Restore the earliest dirty frame and re-simulate forward."""
        target = self._rollback_target
        self._rollback_target = None
        if target is None:
            return

        record = self._record_for(target)
        if record is None or record.snapshot is None:
            # The frame is too old to redo: we cannot roll back that far.
            #
            # This is *not* a harmless situation: the world we are holding is
            # provably wrong (it contains a prediction the server has just
            # contradicted), and it will stay wrong for the rest of the
            # match.  Silently continuing would let the client diverge from
            # every other client without anybody noticing, so the desync is
            # counted and reported.
            #
            # The caller decides what to do about it (drop the match, ask for
            # a full re-sync, …).  ``unrecoverable_desyncs`` is the signal.
            self.stats.unrecoverable_desyncs += 1
            self._unrecoverable_desync = True
            return

        depth = self._next_frame - target
        self.stats.rollbacks += 1
        self.stats.frames_resimulated += depth
        if depth > self.stats.max_rollback_depth:
            self.stats.max_rollback_depth = depth

        # Restore the state from before the dirty frame ran.
        self._restore(record.snapshot)

        # Drop the dirty frame and everything after it.
        self.history = [r for r in self.history if r.frame < target]
        self._next_frame = target

        # Re-simulate with the authoritative inputs.
        while self._next_frame < target + depth:
            self.advance()

    def needs_rollback(self) -> bool:
        return self._rollback_target is not None

    def rollback_pending_at(self) -> Optional[int]:
        return self._rollback_target

    @property
    def unrecoverable_desync(self) -> bool:
        """Has a desync been detected that could *not* be rolled back?

        This happens when the dirty frame is older than the history window:
        the snapshot needed to rewind to it no longer exists.  The world the
        client is holding is then provably wrong and will stay wrong, so the
        caller has to end the match or re-sync from scratch.
        """
        return self._unrecoverable_desync

    def clear_unrecoverable_desync(self) -> None:
        """Acknowledge an unrecoverable desync (after a full re-sync)."""
        self._unrecoverable_desync = False
