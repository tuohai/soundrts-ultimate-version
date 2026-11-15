# -*- coding: utf-8 -*-
"""Regression coverage for the replay *format*.

The rollback netcode was removed in 1.5.2.1, but the replay-format fixes
that shipped with it are protocol-independent and were kept:

  * one physical line per order (a multi-line order used to leave a raw
    newline in the file);
  * a reader that tells a blank line from the end of the file
    (``replay_read_line()``);
  * a reader that applies the records whose time the world has reached,
    instead of waiting for an exact match, and that applies them in
    chronological order.

These tests cover that behaviour, plus the two shapes of damaged file the
reader must survive: a *continuation* line (a multi-line order written by
an older recorder) and a corrupted line.
"""

from __future__ import annotations

import os

import pytest


class _ReplaySession:
    """The bits of the game session the replay reader needs."""

    def __init__(self, lines=None):
        self._lines = list(lines or [])
        self.record_replay = False
        self.written = []

    def replay_read(self):
        if not self._lines:
            return ""
        return self._lines.pop(0)

    def replay_read_line(self):
        if not self._lines:
            return None
        return self._lines.pop(0)

    def replay_write(self, s):
        self.written.append(s)


class _ReplayWorld:
    def __init__(self):
        self.time = 0
        self.players = [object(), object()]


class _FakeReplayPlayer:
    def __init__(self, world):
        self.world = world


class _RecordingReplayClient:
    """A stand-in for ``ReplayClient`` that records what it applies."""

    from soundrts.worldclient import ReplayClient as _Base

    _parse_replay_record = _Base._parse_replay_record
    _parse_continuation = _Base._parse_continuation
    _dispatch_orders = _Base._dispatch_orders
    _read_replay_line = _Base._read_replay_line
    _pending_replay_records = _Base._pending_replay_records

    def __init__(self, session, world):
        self.game_session = session
        self.player = _FakeReplayPlayer(world)
        self.applied = []

    def queue_command(self, player, s):
        self.applied.append(s)


def _client(lines, world_time):
    session = _ReplaySession(lines)
    world = _ReplayWorld()
    world.time = world_time
    return _RecordingReplayClient(session, world)


def test_the_replay_reader_survives_a_continuation_line():
    """The reader must not die on a continuation line.

    The old reader did ``int(time)`` on ``"order 0 0 default 7"`` and
    raised ``ValueError``.
    """
    client = _client(
        [
            "89700 0 control 127-226",
            "order 0 0 default 7",
            "",
            "81000 1 order 0 0 default 7",
            "",
        ],
        90000,
    )

    client._dispatch_orders()

    # The 81000 record comes first (it is earlier in the match), then the
    # 89700 record and its continuation.
    assert client.applied == [
        "order 0 0 default 7",
        "control 127-226",
        "order 0 0 default 7",
    ]


def test_the_replay_reader_survives_a_malformed_line():
    """A corrupted line is skipped, not fatal."""
    client = _client(
        [
            "not a record at all",
            "600",
            "",
            "900 0 order 0 0 default 3",
            "",
        ],
        3000,
    )

    client._dispatch_orders()

    assert client.applied == ["order 0 0 default 3"]


def test_the_replay_reader_does_not_stall_on_a_rounded_timestamp():
    """A timestamp that is not a multiple of 300 ms must still be applied.

    The old reader waited for an *exact* match, so such a record blocked
    every record behind it.
    """
    client = _client(
        [
            "1234 0 order 0 0 default 1",
            "600 0 order 0 0 default 2",
            "900 0 order 0 0 default 3",
            "",
        ],
        3000,
    )

    client._dispatch_orders()

    assert sorted(client.applied) == [
        "order 0 0 default 1",
        "order 0 0 default 2",
        "order 0 0 default 3",
    ]


def test_the_replay_reader_applies_the_records_in_chronological_order():
    """A record that went backwards must be applied at the right moment."""
    client = _client(
        [
            "89700 0 control 127-226",
            "order 0 0 default 7",
            "",
            "80700 1 control 260-359",
            "order 0 0 default 7",
            "order 0 0 default 7",
            "",
            "81000 1 order 0 0 default 7",
            "",
        ],
        90000,
    )

    client._dispatch_orders()

    # The 80700 records come first, then the 81000 one, then the 89700
    # ones.
    assert client.applied == [
        "control 260-359",
        "order 0 0 default 7",
        "order 0 0 default 7",
        "order 0 0 default 7",
        "control 127-226",
        "order 0 0 default 7",
    ]


def test_the_replay_reader_keeps_the_records_that_are_not_due_yet():
    """A record whose time has not been reached must be buffered.

    The old reader consumed the record and threw it away when it did not
    match, so the order was lost for good.
    """
    client = _client(
        [
            "900 0 order 0 0 default 3",
            "",
        ],
        300,
    )

    client._dispatch_orders()
    assert client.applied == []
    assert len(client._pending_replay_records()) == 1

    # The world catches up: the record is applied now.
    client.player.world.time = 900
    client._dispatch_orders()
    assert client.applied == ["order 0 0 default 3"]
    assert client._pending_replay_records() == []


def test_the_replay_reader_applies_every_record_of_the_real_replay():
    """The user's real replay must play to the end.

    ``user/replays/_base/replay386_1794618056.txt`` is a 2-client match in
    which one player paused the game during the final attack on the enemy
    base.  It has 6 records and 5 continuation lines.
    """
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "user",
        "replays",
        "_base",
        "replay386_1794618056.txt",
    )
    if not os.path.isfile(path):
        pytest.skip("the replay is not in the tree")

    with open(path, encoding="utf-8") as f:
        lines = f.read().replace("\r\n", "\n").split("\n")
    # Skip the 10 header lines.
    body = lines[10:]

    session = _ReplaySession(body)
    world = _ReplayWorld()
    client = _RecordingReplayClient(session, world)

    for t in range(0, 240000, 300):
        world.time = t
        client._dispatch_orders()

    # 6 records + 5 continuation lines = 11 orders.
    assert len(client.applied) == 11
    assert not client._pending_replay_records(), "some records were never applied"


def test_the_replay_read_line_tells_a_blank_line_from_the_end():
    """``replay_read`` returns "" for both; ``replay_read_line`` does not."""
    from soundrts.game import ReplayGame

    class FakeFile:
        def __init__(self, lines):
            self.lines = list(lines)

        def readline(self):
            if not self.lines:
                return ""
            return self.lines.pop(0)

    game = ReplayGame.__new__(ReplayGame)
    game._file = FakeFile(["a\n", "\n", "b\n"])

    assert game.replay_read_line() == "a"
    assert game.replay_read_line() == ""       # a blank line
    assert game.replay_read_line() == "b"
    assert game.replay_read_line() is None     # the end of the file
