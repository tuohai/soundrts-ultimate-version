"""The client side of the rollback protocol: a session that ties the
simulation, the rollback manager and the network together.

Why a separate module
----------------------

The game runs the simulation on its own thread (the world thread), while
the network messages arrive on another one.  Restoring a snapshot *mutates*
the world, so it must not happen on the network thread: the world thread
could be halfway through a frame at the same time, and the two would race.

This module therefore splits the work in two:

* the network thread only *records* what the server said.  It never touches
  the world;
* the world thread performs the rollback and the re-simulation, when it
  next steps the simulation.

That is what :meth:`RollbackSession.on_input` and
:meth:`RollbackSession.step` are for.

The frame loop
--------------

:meth:`RollbackSession.step` advances the simulation by exactly one frame:

1. if a rollback is pending (an authoritative input contradicted the
   prediction), the world is restored to the affected frame and the frames
   from there on are re-simulated with the authoritative inputs;
2. the inputs of the next frame are applied — the local player's own
   orders, plus whatever the server has confirmed for the remote players
   (the rest are predicted as idle);
3. the world is stepped by one frame;
4. the state is snapshotted so the frame can be redone later.

The client therefore never waits for the server: it simulates ahead and
corrects itself when the truth arrives.
"""

from __future__ import annotations

import threading
from typing import Callable, Dict, List, Optional, Sequence

from .input_stream import InputFrame, pack_orders
from .rollback import RollbackManager
from .snapshot import capture_snapshot, restore_snapshot

__all__ = ["RollbackSession", "SpectatorSession"]


class RollbackSession:
    """One client's view of a rollback match.

    Attributes:
        manager: the underlying :class:`~soundrts.net.rollback.RollbackManager`.
        frame: the number of the next frame to simulate.
        unrecoverable_desync: whether the client fell too far behind to be
            able to repair itself.
    """

    def __init__(
        self,
        world,
        local_player: str,
        players: Sequence[str],
        step: Callable[[], None],
        apply_inputs: Callable[[Dict[str, str]], None],
        capture: Optional[Callable[[], object]] = None,
        restore: Optional[Callable[[object], None]] = None,
        history_size: int = 64,
        on_local_input: Optional[Callable[[int, str], None]] = None,
    ):
        """
        Args:
            world: the world object.
            local_player: the id of the player this client controls.
            players: every participating player id.
            step: advances the world by exactly one frame.
            apply_inputs: applies one frame's inputs (player id -> packed
                order string) to the world.
            capture / restore: snapshot hooks; default to the real ones.
            history_size: how many frames can be rolled back.
            on_local_input: called with ``(frame, packed orders)`` when the
                local player's input must be sent to the server.
        """
        self.world = world
        self.local_player = local_player
        self.players: List[str] = list(players)
        self._step = step
        self._apply_inputs = apply_inputs
        self._on_local_input = on_local_input

        self.manager = RollbackManager(
            local_player=local_player,
            players=self.players,
            world=world,
            step=step,
            apply_inputs=apply_inputs,
            capture=capture if capture is not None else (lambda: capture_snapshot(world)),
            restore=restore if restore is not None else (
                lambda snap: restore_snapshot(world, snap)
            ),
            history_size=history_size,
        )

        # The authoritative inputs the server sent, keyed by frame then by
        # player id.  They are kept here (and not only in the manager) so
        # that the world thread can read them without touching the manager's
        # own state from another thread.
        self._lock = threading.Lock()
        self._received: Dict[int, Dict[str, str]] = {}
        # The frames whose authoritative inputs are not known yet.
        self._pending_rollback = False

    # -- state -----------------------------------------------------------

    @property
    def frame(self) -> int:
        """The number of the next frame to simulate."""
        return self.manager.current_frame

    @property
    def stats(self):
        return self.manager.stats

    @property
    def unrecoverable_desync(self) -> bool:
        return self.manager.unrecoverable_desync

    def confirmed_frame(self) -> int:
        """The highest frame the server has confirmed."""
        return self.manager.confirmed_frame

    def remove_player(self, player_id: str) -> None:
        """Drop a player that quit the match.

        The quitter will never send an input again, so the session must stop
        waiting for it: otherwise every frame would stay incomplete and the
        client would never simulate anything again.
        """
        self.manager.remove_player(player_id)

    # -- the network thread ----------------------------------------------

    def on_input(self, frame: int, player_id: str, orders: str) -> None:
        """Record an authoritative input received from the server.

        This is called from the network thread.  It does **not** touch the
        world: it only records what the server said, and remembers that a
        rollback may be needed.  The actual rollback happens in
        :meth:`step`, on the world thread.
        """
        with self._lock:
            bucket = self._received.setdefault(frame, {})
            if player_id in bucket:
                # A retransmission: the first one wins.
                return
            bucket[player_id] = orders
            self._pending_rollback = True

    def on_frame(self, frame_obj: InputFrame) -> None:
        """Record a whole authoritative frame received from the server."""
        for player_id, (_seq, orders) in frame_obj.inputs.items():
            self.on_input(frame_obj.frame, player_id, orders)

    def submit_local(self, orders: str, frame: Optional[int] = None) -> None:
        """Record the local player's orders and send them to the server.

        The local player's input is known immediately — it comes from the
        local player — so it is never predicted and never rolled back.

        The frame the orders belong to is decided here, on the *interface*
        thread, and it must be the frame the world thread is going to
        simulate next.  ``manager.current_frame`` is the next frame to
        simulate, so the orders land on exactly that frame — and the server
        is told about the same frame, which is what keeps the two sides
        talking about the same thing.

        The manager returns the frame it actually recorded the orders for:
        the world thread may have moved on in the meantime, and the server
        has to be told about the frame the orders will really be applied
        on.
        """
        frame = self.manager.submit_local(orders, frame)
        if self._on_local_input is not None:
            self._on_local_input(frame, pack_orders(orders))

    # -- the world thread ------------------------------------------------

    def step(self) -> bool:
        """Advance the simulation by one frame.

        Returns ``True`` when the frame was simulated normally, ``False``
        when a rollback happened first (the frame was then simulated as
        part of the re-simulation).
        """
        repaired = self._repair()
        # Whether or not a rollback happened, the client moves forward by
        # exactly one frame.  A rollback rewinds the world and re-simulates
        # the frames it rewound over, so the frame counter is unchanged by
        # it — the client must not lose a frame because of it.
        self.manager.advance()
        return not repaired

    def repair(self) -> bool:
        """Repair the world if an authoritative input contradicted it.

        Returns ``True`` when a rollback was performed.

        This does **not** advance the client: it only rewinds the world to
        the affected frame and re-simulates the frames from there with the
        authoritative inputs.  The client ends up on the same frame it was
        on, but with the correct state.
        """
        return self._repair()

    def _repair(self) -> bool:
        """Feed the pending inputs to the manager and perform the rollback."""
        with self._lock:
            received = self._received
            self._received = {}
            pending = self._pending_rollback
            self._pending_rollback = False

        if pending:
            # Feed the newly received inputs to the manager.  It decides
            # whether they contradict what was applied, and schedules a
            # rollback if they do.
            for frame in sorted(received):
                for player_id, orders in sorted(received[frame].items()):
                    self.manager.confirm_input(frame, player_id, orders)

        if not self.manager.needs_rollback():
            return False
        # The manager performs the rollback and re-simulates the affected
        # frames as part of its next ``advance``.
        self.manager.advance()
        return True


class SpectatorSession:
    """Replays a match, frame by frame, for a spectator.

    A spectator is not a player: it sends nothing and predicts nothing.  It
    only has to *reproduce* the match, which means replaying the
    authoritative inputs of every frame, in order.

    That is much simpler than a player's session:

    * the inputs arrive from the server in order (the server replays the
      whole history when the spectator joins);
    * a frame is simulated as soon as *every* player has answered it, and
      not before — there is nothing to predict, because the truth is
      already known;
    * no rollback is ever needed: the inputs never contradict each other.

    The session therefore keeps a small buffer of the frames it is still
    waiting for, and steps the world one frame at a time.
    """

    def __init__(self, world, players: Sequence[str], step: Callable[[], None],
                 apply_inputs: Callable[[Dict[str, str]], None]):
        """
        Args:
            world: the world object.
            players: every participating player id.
            step: advances the world by exactly one frame.
            apply_inputs: applies one frame's inputs to the world.
        """
        self.world = world
        self.players: List[str] = list(players)
        self._step = step
        self._apply_inputs = apply_inputs

        self._lock = threading.Lock()
        # frame -> player id -> orders
        self._received: Dict[int, Dict[str, str]] = {}
        # The next frame to simulate.
        self._next_frame = 0

    @property
    def frame(self) -> int:
        """The number of the next frame to simulate."""
        return self._next_frame

    def remove_player(self, player_id: str) -> None:
        """Drop a player that quit the match.

        The quitter will never send an input again, so the session must stop
        waiting for it: otherwise every frame would stay incomplete and the
        spectator would freeze.
        """
        with self._lock:
            if player_id in self.players:
                self.players.remove(player_id)

    def on_input(self, frame: int, player_id: str, orders: str) -> None:
        """Record one authoritative input.  Called from the network thread."""
        with self._lock:
            bucket = self._received.setdefault(frame, {})
            if player_id in bucket:
                # A retransmission: the first one wins.
                return
            bucket[player_id] = orders

    def pending_frames(self) -> int:
        """How many frames are waiting to be simulated."""
        with self._lock:
            return max(0, len(self._received))

    def has_ready_frame(self) -> bool:
        """Is the next frame complete, and can it be simulated?"""
        with self._lock:
            bucket = self._received.get(self._next_frame)
            if bucket is None:
                return False
            return all(pid in bucket for pid in self.players)

    def step(self) -> bool:
        """Simulate the next frame, if it is complete.

        Returns ``True`` when a frame was simulated, ``False`` when the
        session is still waiting for the inputs of the current frame.
        """
        with self._lock:
            bucket = self._received.get(self._next_frame)
            if bucket is None:
                return False
            if not all(pid in bucket for pid in self.players):
                # The frame is not complete yet: the spectator waits.
                return False
            inputs = dict(bucket)
            del self._received[self._next_frame]

        self._apply_inputs(inputs)
        self._step()
        self._next_frame += 1
        return True
