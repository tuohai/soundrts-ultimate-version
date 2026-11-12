"""Authoritative input stream — the replacement for lockstep's "wait for all".

Why this module exists
----------------------

The legacy multiplayer path is *deterministic lockstep*: every client runs the
whole simulation, and the server only ships a batch of orders once **all**
players have sent theirs.  Two consequences:

* the slowest player's ping sets the pace of the whole match;
* one late or lost packet stalls everybody, and a single desync kills the
  match.

The replacement is the *host-authoritative input stream* used by rollback
netcode (GGPO / Overwatch style):

* the server is the **authority on ordering**.  It stamps every input with a
  monotonically increasing sequence number and broadcasts the confirmed
  stream;
* clients **predict** their own input locally (so a local order is felt
  immediately, without waiting for the server round trip);
* when the authoritative stream contradicts the prediction, the client
  **rolls back** to the affected frame and re-simulates.

This module owns the *stream* half of that: sequence numbering, per-player
ordering, deduplication and gap detection.  :mod:`soundrts.net.rollback`
owns the *rollback* half.

The stream is deliberately transport-agnostic: it deals in
:class:`InputFrame` objects and never touches sockets.  The wire format is
produced by :meth:`InputStream.encode_frame` / parsed by
:func:`decode_frame`, so the same logic can be unit-tested without a network.

Frame numbering
---------------

A *frame* is one simulation step (``World.update()``).  Frames are numbered
with a plain integer that increases by one per step.  Each frame carries the
inputs of **every** player, so a frame is self-contained: replaying frame
*N* means "apply these inputs, then simulate one step".

Every player contributes *at most one* input per frame.  A player that has
nothing to do contributes an empty input — that keeps the frame vector
rectangular, which is what makes replay cheap and gap detection meaningful.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

__all__ = [
    "Input",
    "InputFrame",
    "InputStream",
    "decode_frame",
    "decode_input",
    "encode_input",
    "pack_orders",
    "unpack_orders",
]


# The wire is line-based, so an order string (which contains newlines and
# spaces) has to be packed before it can be sent.  The legacy protocol uses
# the same convention (see :func:`soundrts.worldclient._pack`), which keeps
# the two protocols consistent.
NEWLINE_REPLACEMENT = ";"
SPACE_REPLACEMENT = ","


def pack_orders(orders: str) -> str:
    """Pack an order string so it fits on a single wire line.

    Newlines become ``;`` and spaces become ``,``.  Neither character can
    appear in an order otherwise, so no escaping is needed.
    """
    return orders.replace("\n", NEWLINE_REPLACEMENT).replace(
        " ", SPACE_REPLACEMENT
    )


def unpack_orders(orders: str) -> str:
    """Unpack an order string that was packed by :func:`pack_orders`."""
    return orders.replace(NEWLINE_REPLACEMENT, "\n").replace(
        SPACE_REPLACEMENT, " "
    )


# One player's contribution to a frame: the raw order string plus the
# sequence number the server assigned to it.  ``seq`` is ``None`` for a
# prediction (not yet confirmed by the server).
Input = Tuple[int, str]


def encode_input(frame: int, player_id: str, seq: int, orders: str) -> str:
    """Serialise *one* player's contribution to *frame*.

    The wire format is::

        <frame>:<player>=<seq>:<packed orders>

    This is the *incremental* form: the server sends one message per player
    input, the moment the input arrives.  That is what removes the lockstep
    barrier — the server no longer waits for the slowest player before it
    says anything.

    The order string is packed with :func:`pack_orders`, exactly like the
    legacy protocol does, so it fits on a single line and needs no further
    escaping.
    """
    return "%d:%s=%d:%s" % (frame, player_id, seq, pack_orders(orders))


def decode_input(payload: str) -> Tuple[int, str, int, str]:
    """Parse one incremental input message.

    Returns ``(frame, player_id, seq, orders)`` with the orders *unpacked*.

    Raises:
        ValueError: when the payload does not have the expected shape.
    """
    frame_part, sep, rest = payload.partition(":")
    if not sep:
        raise ValueError("malformed input payload: %r" % (payload,))
    frame = int(frame_part)
    player_part, sep2, order_part = rest.partition("=")
    if not sep2:
        raise ValueError("malformed input payload: %r" % (payload,))
    seq_part, sep3, orders = order_part.partition(":")
    if not sep3:
        # No orders for this player.
        return frame, player_part, int(seq_part), ""
    return frame, player_part, int(seq_part), unpack_orders(orders)


class InputFrame:
    """The authoritative inputs of a single simulation frame.

    Attributes:
        frame: the frame number.
        inputs: player id -> (sequence number, order string).  Every player
            that participates in the match has an entry, even if its order
            string is empty.
        confirmed: the sequence number of the whole frame, i.e. the server's
            authoritative stamp.  ``None`` while the frame is still a local
            prediction.
    """

    __slots__ = ("frame", "inputs", "confirmed")

    def __init__(
        self,
        frame: int,
        inputs: Optional[Dict[str, Input]] = None,
        confirmed: Optional[int] = None,
    ):
        self.frame = frame
        self.inputs: Dict[str, Input] = dict(inputs or {})
        self.confirmed = confirmed

    def order_for(self, player_id: str) -> str:
        """The order string of *player_id* (empty string when it has none)."""
        entry = self.inputs.get(player_id)
        return entry[1] if entry else ""

    def seq_for(self, player_id: str) -> Optional[int]:
        entry = self.inputs.get(player_id)
        return entry[0] if entry else None

    def players(self) -> List[str]:
        return list(self.inputs.keys())

    def copy(self) -> "InputFrame":
        return InputFrame(self.frame, dict(self.inputs), self.confirmed)

    def orders_signature(self) -> Tuple[Tuple[str, str], ...]:
        """A comparable signature of the *content* of this frame.

        Two frames with the same signature apply exactly the same orders, so
        a client that predicted one of them needs no rollback when the other
        arrives.
        """
        return tuple(sorted((pid, order) for pid, (_, order) in self.inputs.items()))

    def __eq__(self, other):
        if not isinstance(other, InputFrame):
            return NotImplemented
        return (
            self.frame == other.frame
            and self.orders_signature() == other.orders_signature()
        )

    def __hash__(self):
        return hash((self.frame, self.orders_signature()))

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<InputFrame %d confirmed=%s inputs=%d>" % (
            self.frame,
            self.confirmed,
            len(self.inputs),
        )


def decode_frame(payload: str) -> InputFrame:
    """Parse one wire frame.

    The wire format is::

        <frame>:<confirmed>:<player>=<seq>:<orders>|<player>=<seq>:<orders>

    ``confirmed`` is ``-`` when the frame has not been confirmed yet.  The
    order strings are packed the same way the legacy protocol packs them
    (see :func:`soundrts.worldclient._pack`), so no extra escaping is
    needed beyond packing away ``|`` and ``:``.
    """
    frame_part, _, rest = payload.partition(":")
    confirmed_part, _, inputs_part = rest.partition(":")
    frame = int(frame_part)
    confirmed = None if confirmed_part == "-" else int(confirmed_part)
    inputs: Dict[str, Input] = {}
    if inputs_part:
        for chunk in inputs_part.split("|"):
            if not chunk:
                continue
            player_part, sep, order_part = chunk.partition("=")
            if not sep:
                continue
            seq_part, sep2, orders = order_part.partition(":")
            if not sep2:
                # No orders for this player.
                inputs[player_part] = (int(seq_part), "")
            else:
                inputs[player_part] = (int(seq_part), orders)
    return InputFrame(frame, inputs, confirmed)


class InputStream:
    """The server-side authoritative input stream.

    The server does **not** simulate the world.  It only decides *when* an
    input becomes authoritative and *in which order* the inputs are applied.
    That is enough to remove the lockstep barrier: a client can send its
    input for frame *N* as soon as it has it, and the server confirms it
    immediately instead of waiting for the slowest player.

    How the server decides a frame is complete
    -------------------------------------------

    A frame is *complete* once every participating player has contributed an
    input for it.  The server then stamps the frame with the next sequence
    number and broadcasts it.  Players that are late for frame *N* are
    handled by the client-side prediction/rollback machinery, not by the
    server blocking: the server simply keeps the frame open until every
    player has answered, and the *client* keeps simulating ahead by
    predicting.

    Attributes:
        players: the participating player ids, in a stable order.
    """

    def __init__(self, players: Sequence[str]):
        self.players: List[str] = list(players)
        # frame -> player id -> (seq, orders)
        self._frames: Dict[int, Dict[str, Input]] = {}
        # player id -> the highest frame that player has contributed
        self._last_frame: Dict[str, int] = {}
        self._next_seq = 0
        # the frames that every player has answered, and are therefore
        # authoritative
        self._complete: Dict[int, int] = {}
        # the highest frame such that every frame up to it is complete
        self._confirmed_frame = -1

    # -- introspection ---------------------------------------------------

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def confirmed_frame(self) -> int:
        """The highest frame such that every frame up to it is complete.

        Frames *above* this one may still be complete (a player can run
        ahead); they are authoritative too, they are just not contiguous
        yet.
        """
        return self._confirmed_frame

    def is_authoritative(self, number: int) -> bool:
        """Has every player answered frame *number*?"""
        return number in self._complete

    def frame(self, number: int) -> Optional[InputFrame]:
        """Return the (possibly unconfirmed) frame *number*."""
        raw = self._frames.get(number)
        if raw is None:
            return None
        return InputFrame(number, raw, self._complete.get(number))

    def is_complete(self, number: int) -> bool:
        raw = self._frames.get(number)
        if raw is None:
            return False
        return all(pid in raw for pid in self.players)

    def gaps(self) -> List[int]:
        """Frame numbers below the confirmed frame that are not complete."""
        missing = []
        for number in range(0, self._confirmed_frame + 1):
            if not self.is_complete(number):
                missing.append(number)
        return missing

    # -- server side -----------------------------------------------------

    def submit(self, player_id: str, number: int, orders: str) -> Optional[InputFrame]:
        """Record *player_id*'s input for frame *number*.

        Returns the frame once it becomes authoritative (every player has
        answered it), otherwise ``None``.

        The server is tolerant of duplicates: a repeated submission is
        ignored, because a retransmission must never change a frame that
        has already been broadcast.
        """
        bucket = self._frames.setdefault(number, {})
        if player_id in bucket:
            # Duplicate submission.  The first one wins.
            return None
        bucket[player_id] = (self._next_seq, orders)
        self._next_seq += 1
        last = self._last_frame.get(player_id)
        if last is None or number > last:
            self._last_frame[player_id] = number

        if number not in self._complete and self.is_complete(number):
            self._complete[number] = self._next_seq
            self._next_seq += 1
            self._advance_confirmed()
            return self.frame(number)
        return None

    # -- incremental (lockstep-free) path --------------------------------

    def submit_incremental(
        self, player_id: str, number: int, orders: str
    ) -> Optional[Tuple[int, int, str]]:
        """Record *player_id*'s input and stamp it immediately.

        This is the **lockstep-free** path.  The legacy path
        (:meth:`submit`) holds a frame back until every player has answered
        it, which means the slowest player's ping sets the pace of the whole
        match.  Here the server instead:

        * assigns the input the next sequence number **at once**, so the
          order in which inputs are applied is authoritative and globally
          consistent;
        * returns it so the caller can broadcast it *immediately*.

        The client receives the inputs of a frame one by one and knows the
        frame is complete once every player has answered it.  It does not
        have to wait for the server to say so.

        Returns:
            ``(frame, seq, orders)`` — the stamped input, ready to be sent —
            or ``None`` when the submission is a duplicate (a retransmission
            must never change an input that has already been broadcast).

        The *frame* is still tracked as complete once every player has
        answered it, so :meth:`confirmed_frame` and :meth:`gaps` keep
        working for the desync check.
        """
        bucket = self._frames.setdefault(number, {})
        if player_id in bucket:
            # Duplicate submission: the first one wins.  A retransmission
            # must not produce a second authoritative stamp.
            return None
        seq = self._next_seq
        self._next_seq += 1
        bucket[player_id] = (seq, orders)
        last = self._last_frame.get(player_id)
        if last is None or number > last:
            self._last_frame[player_id] = number

        if number not in self._complete and self.is_complete(number):
            self._complete[number] = self._next_seq
            self._next_seq += 1
            self._advance_confirmed()

        return number, seq, orders

    def _advance_confirmed(self) -> None:
        """Track the highest contiguous complete frame."""
        number = self._confirmed_frame + 1
        while number in self._complete:
            self._confirmed_frame = number
            number += 1

    def confirmed_frames(self) -> List[InputFrame]:
        """Every authoritative frame, oldest first."""
        result = []
        for number in sorted(self._complete):
            frame = self.frame(number)
            if frame is not None:
                result.append(frame)
        return result

    def frame_numbers(self) -> List[int]:
        """Every frame that has at least one input, oldest first.

        This is *not* the same as :meth:`confirmed_frames`: a frame that
        only one player has answered is not authoritative yet, but its
        input exists and must not be lost -- a spectator joining now needs
        it, and it will be completed by the inputs that arrive later.
        """
        return sorted(self._frames)

    def remove_player(self, player_id: str) -> List[int]:
        """Drop *player_id* from the stream, and close the frames it left open.

        A player that quits mid-match will never answer the frames it was
        supposed to answer.  Leaving those frames open would stall the
        whole match: no later frame could ever be complete, because a frame
        is only complete once *every* player has answered it.

        So the frames the quitter left open are closed (the quitter's share
        of them is empty — it did nothing), and the player is dropped from
        the list of participants.

        Returns the frames that were open, so that the caller can tell the
        other clients about the quitter's empty contribution.
        """
        if player_id not in self.players:
            return []
        self.players.remove(player_id)
        open_frames = self.incomplete_frames()
        for number in open_frames:
            if number in self._complete:
                continue
            if self.is_complete(number):
                self._complete[number] = self._next_seq
                self._next_seq += 1
        self._advance_confirmed()
        return open_frames

    def incomplete_frames(self) -> List[int]:
        """Every frame that is not complete yet, oldest first."""
        return [
            number
            for number in sorted(self._frames)
            if number not in self._complete
        ]

    def encode_frame(self, frame: InputFrame) -> str:
        """Serialise *frame* for the wire."""
        parts = []
        for player_id in sorted(frame.inputs):
            seq, orders = frame.inputs[player_id]
            parts.append("%s=%d:%s" % (player_id, seq, orders))
        return "%d:%s:%s" % (
            frame.frame,
            "-" if frame.confirmed is None else str(frame.confirmed),
            "|".join(parts),
        )

    def encode_frames(self, frames: Iterable[InputFrame]) -> List[str]:
        return [self.encode_frame(frame) for frame in frames]

    def encode_input_for(self, frame: int, player_id: str, seq: int,
                         orders: str) -> str:
        """Serialise one incremental input for the wire."""
        return encode_input(frame, player_id, seq, orders)

    def inputs_since(self, seq: int) -> List[InputFrame]:
        """Every *complete* frame whose stamp is newer than *seq*.

        This is what a client asks for when it reconnects or falls behind:
        the server replays the frames it has already stamped.  The client
        gets them in order, so it can roll back and re-simulate.
        """
        result = []
        for number in sorted(self._complete):
            if self._complete[number] <= seq:
                continue
            frame = self.frame(number)
            if frame is not None:
                result.append(frame)
        return result
