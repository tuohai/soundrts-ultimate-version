"""Regression tests for the four rollback/replay defects.

The defects were found by analysing a real 2-client match
(``user/replays/_base/replay386_1794618056.txt``) in which one player paused
the game (F10) during the final attack on the enemy base:

1. **The frame-0 snapshot poison.**  The snapshot of the very first frame
   captured ``None`` for the lazily-initialised counters
   (``_last_full_terrain_update``, ``_last_perception_cleanup``).  On
   restore, that ``None`` shadowed the class attribute and the simulation
   died with ``TypeError: unsupported operand type(s) for -: 'int' and
   'NoneType'`` — swallowed by the world thread, so the game froze for the
   player with no error shown.

2. **The desync was silent.**  When a client falls further behind than the
   rollback history window (64 frames = 19.2 s), the world it holds is
   provably wrong, and it stays wrong for the rest of the match.  Nothing
   told the player.

3. **The replay writer wrote multi-line orders.**  An order string may
   hold several orders; writing them as one physical line put a raw newline
   in the replay file, and the reader then died with ``ValueError: invalid
   literal for int() with base 10: 'order'``.

4. **The replay timestamps were not monotonic.**  A rollback rewinds the
   world, so ``world.time`` went backwards, and the reader — which waited
   for an exact time match — stalled forever.
"""

import os
import sys
import warnings

import pytest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# --------------------------------------------------------------------------
# Defect 1: the frame-0 snapshot poison
# --------------------------------------------------------------------------


def test_captured_scalars_never_contain_none():
    """A missing attribute must not be captured as ``None``.

    Capturing ``None`` poisons the snapshot: on restore it shadows the
    class attribute and the lazy initialisation never runs again.
    """
    from soundrts.net.snapshot import _capture_scalars

    class Dummy:
        # A counter that has not been initialised yet: it exists neither
        # on the instance nor on the class.
        pass

    world = Dummy()
    world.random = __import__("random").Random(1)
    data = _capture_scalars(world)
    assert None not in data.values(), "a None was captured: %r" % data


def test_the_world_counters_have_class_level_defaults():
    """The lazily-initialised counters must have a class-level default.

    Otherwise the snapshot of the first frame has to skip them, and the
    first frame is exactly the frame a rollback rewinds to.
    """
    from soundrts.world.world_core import World

    assert isinstance(World._last_full_terrain_update, int)
    assert isinstance(World._last_perception_cleanup, int)
    assert World._last_full_terrain_update == 0
    assert World._last_perception_cleanup == 0


def test_restoring_a_none_scalar_does_not_poison_the_world():
    """A snapshot written by an older version must not poison the world."""
    from soundrts.net.snapshot import _restore_scalars

    class Dummy:
        _last_full_terrain_update = 0

    world = Dummy()
    _restore_scalars(world, {"_last_full_terrain_update": None})
    # The class attribute must still be visible.
    assert world._last_full_terrain_update == 0
    assert world._last_full_terrain_update is not None


def test_a_restored_frame_0_world_can_be_updated():
    """The world must survive an update after a frame-0 restore.

    This is the exact crash of the defect: ``self.time - None``.
    """
    from soundrts.net.snapshot import capture_snapshot, restore_snapshot
    from soundrts.world import World

    world = World([], seed=1)
    # The counters must not be in the instance dict yet: that is the state
    # of a world that has not run a single update.
    world.__dict__.pop("_last_full_terrain_update", None)
    world.__dict__.pop("_last_perception_cleanup", None)

    snap = capture_snapshot(world)
    restore_snapshot(world, snap)

    # The restored world must be able to run the update that used to
    # raise ``TypeError: unsupported operand type(s) for -: 'int' and
    # 'NoneType'``.
    world._update_terrain()
    assert world._last_full_terrain_update is not None
    assert world._last_perception_cleanup is not None


# --------------------------------------------------------------------------
# Defect 2: the desync must not be silent
# --------------------------------------------------------------------------


class _FakeStats:
    rollbacks = 3
    max_rollback_depth = 70
    unrecoverable_desyncs = 1


class _FakeSession:
    def __init__(self, desync=True):
        self.unrecoverable_desync = desync
        self.stats = _FakeStats()


class _FakeServer:
    def __init__(self, desync=True):
        self.rollback_session = _FakeSession(desync)
        self.written = []

    def has_unrecoverable_desync(self):
        return self.rollback_session.unrecoverable_desync

    def unrecoverable_desync_stats(self):
        return self.rollback_session.stats

    def write_line(self, s):
        self.written.append(s)


def _make_interface(server):
    from soundrts.clientgame.game_interface_base import GameInterface

    iface = GameInterface.__new__(GameInterface)
    iface.server = server
    iface._desync_announced = False
    iface.end_loop = False
    iface.forced_quit = False
    return iface


def test_the_coordinator_exposes_the_unrecoverable_desync():
    from soundrts.worldclient import Coordinator

    coord = Coordinator.__new__(Coordinator)
    coord.rollback_session = _FakeSession(desync=True)
    assert coord.has_unrecoverable_desync() is True
    coord.rollback_session = _FakeSession(desync=False)
    assert coord.has_unrecoverable_desync() is False


def test_the_interface_announces_the_desync_and_ends_the_match(monkeypatch):
    from soundrts.clientgame import game_interface_base as gib

    spoken = []

    class FakeVoice:
        @staticmethod
        def confirmation(msg):
            spoken.append(msg)

        @staticmethod
        def info(msg):
            spoken.append(msg)

        @staticmethod
        def discard_pending():
            pass

    monkeypatch.setattr(gib, "voice", FakeVoice)
    server = _FakeServer(desync=True)
    iface = _make_interface(server)

    assert iface.check_unrecoverable_desync() is True
    assert iface.end_loop is True
    assert iface.forced_quit is True
    assert "quit" in server.written
    assert spoken, "the player was told nothing"


def test_the_interface_does_nothing_when_there_is_no_desync(monkeypatch):
    from soundrts.clientgame import game_interface_base as gib

    spoken = []

    class FakeVoice:
        @staticmethod
        def confirmation(msg):
            spoken.append(msg)

        @staticmethod
        def info(msg):
            spoken.append(msg)

        @staticmethod
        def discard_pending():
            pass

    monkeypatch.setattr(gib, "voice", FakeVoice)
    server = _FakeServer(desync=False)
    iface = _make_interface(server)

    assert iface.check_unrecoverable_desync() is False
    assert iface.end_loop is False
    assert not spoken


def test_the_desync_is_announced_only_once(monkeypatch):
    from soundrts.clientgame import game_interface_base as gib

    spoken = []

    class FakeVoice:
        @staticmethod
        def confirmation(msg):
            spoken.append(msg)

        @staticmethod
        def info(msg):
            spoken.append(msg)

        @staticmethod
        def discard_pending():
            pass

    monkeypatch.setattr(gib, "voice", FakeVoice)
    iface = _make_interface(_FakeServer(desync=True))
    for _ in range(3):
        iface.check_unrecoverable_desync()
    assert len(spoken) == 1


# --------------------------------------------------------------------------
# Defect 3 and 4: the replay writer and the replay reader
# --------------------------------------------------------------------------


class _ReplaySession:
    """The bits of the game session the replay reader/writer needs."""

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

    def __init__(self, session, world):
        self.game_session = session
        self.player = _FakeReplayPlayer(world)
        self.applied = []

    # The real methods, bound from the real class.
    from soundrts.worldclient import ReplayClient as _Base

    _parse_replay_record = _Base._parse_replay_record
    _parse_continuation = _Base._parse_continuation
    _dispatch_orders = _Base._dispatch_orders
    _read_replay_line = _Base._read_replay_line
    _pending_replay_records = _Base._pending_replay_records

    def queue_command(self, player, s):
        self.applied.append(s)


class _RecordingCoordinator:
    """A stand-in for ``Coordinator`` that only exercises the recorder."""

    from soundrts.worldclient import Coordinator as _Base

    _record_rollback_replay = _Base._record_rollback_replay

    def __init__(self, session, world, frame=0):
        self.game_session = session
        self.world = world
        self.rollback_session = None
        self._replay_written = set()
        self._frame = frame
        self._fake_clients = []

    @property
    def clients(self):
        return self._fake_clients

    def _rollback_current_frame(self):
        return self._frame


def _make_coordinator(session, world):
    coord = _RecordingCoordinator(session, world)
    player = world.players[0]
    coord._fake_clients = [
        type("C", (), {"login": "p0", "player": player})()
    ]
    return coord


def test_the_replay_writer_writes_one_line_per_order():
    """A multi-line order must not put a raw newline in the replay file."""
    session = _ReplaySession()
    session.record_replay = True
    world = _ReplayWorld()
    coord = _make_coordinator(session, world)

    coord._record_rollback_replay(
        "p0", "control 127-226\norder 0 0 default 7"
    )

    assert len(session.written) == 2
    for line in session.written:
        assert "\n" not in line
        assert len(line.split(" ", 2)) == 3


def test_the_replay_timestamps_are_monotonic_across_a_rollback():
    """The timestamps must come from the frame, not from the world.

    A rollback rewinds the world, so ``world.time`` goes backwards; the
    replay's timestamps would then not be monotonic, and the reader would
    stall on the first record that went backwards.
    """
    session = _ReplaySession()
    session.record_replay = True
    world = _ReplayWorld()
    coord = _make_coordinator(session, world)

    for frame in range(10):
        coord._frame = frame
        coord._record_rollback_replay("p0", "order 0 0 default %d" % frame)
    # The rollback re-simulates frames 5..9.  They must not be written
    # twice, and the timestamps must stay monotonic.
    for frame in range(5, 10):
        coord._frame = frame
        coord._record_rollback_replay("p0", "order 0 0 default %d" % frame)

    times = [int(line.split(" ", 1)[0]) for line in session.written]
    assert times == sorted(times)
    assert len(times) == len(set(times))


def test_the_replay_reader_survives_a_continuation_line():
    """The reader must not die on a continuation line.

    The old reader did ``int(time)`` on ``"order 0 0 default 7"`` and
    raised ``ValueError``.
    """
    session = _ReplaySession(
        [
            "89700 0 control 127-226",
            "order 0 0 default 7",
            "",
            "81000 1 order 0 0 default 7",
            "",
        ]
    )
    world = _ReplayWorld()
    world.time = 90000
    client = _RecordingReplayClient(session, world)

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
    session = _ReplaySession(
        [
            "not a record at all",
            "600",
            "",
            "900 0 order 0 0 default 3",
            "",
        ]
    )
    world = _ReplayWorld()
    world.time = 3000
    client = _RecordingReplayClient(session, world)

    client._dispatch_orders()

    assert client.applied == ["order 0 0 default 3"]


def test_the_replay_reader_does_not_stall_on_a_rounded_timestamp():
    """A timestamp that is not a multiple of 300 ms must still be applied.

    The old reader waited for an *exact* match, so such a record blocked
    every record behind it.
    """
    session = _ReplaySession(
        [
            "1234 0 order 0 0 default 1",
            "600 0 order 0 0 default 2",
            "900 0 order 0 0 default 3",
            "",
        ]
    )
    world = _ReplayWorld()
    world.time = 3000
    client = _RecordingReplayClient(session, world)

    client._dispatch_orders()

    assert sorted(client.applied) == [
        "order 0 0 default 1",
        "order 0 0 default 2",
        "order 0 0 default 3",
    ]


def test_the_replay_reader_applies_the_records_in_chronological_order():
    """A record that went backwards must be applied at the right moment.

    The real replay of the user's match has ``89700`` written before
    ``80700`` (a 30-frame rollback).  The reader must apply the ``80700``
    record first.
    """
    session = _ReplaySession(
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
        ]
    )
    world = _ReplayWorld()
    world.time = 90000
    client = _RecordingReplayClient(session, world)

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
    assert not client._pending_records, "some records were never applied"


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
