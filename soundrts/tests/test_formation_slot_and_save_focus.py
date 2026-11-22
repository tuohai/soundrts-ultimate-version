# -*- coding: utf-8 -*-
"""Regression tests for two bugs reported in the AoE2 Joan of Arc chapter 2.

Bug 1 -- "3 archers stuck in d2":
    The player's army stood in square e2 (``4,1``) and was ordered to a1
    (``0,0``) in a horizontal line formation.  Exactly three archers
    stopped in d2 (``3,1``) and never followed the rest of the army.

    Root cause: the formation slot was turned into a ``ZoomTarget`` and
    ``ZoomTarget.contains()`` folded a point from a *different* square
    onto the edge sub-cell of the target square.  ``is_in_position()``
    therefore returned True while the unit was still four squares away,
    so the ``go`` order completed and the unit stopped for good.

Bug 2 -- "camera focus lost on reload":
    Saving with the view on d1 and loading the save put the camera back
    on the spawn square, because the interface (and with it
    ``interface.place``) was stripped from the pickle.
"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.world_formation import after_group_order
    from soundrts.worldclient import DirectClient

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

import pytest

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)

# A wide map: the army stands in e2 (4,1) and marches to a1 (0,0) along
# the second row (a2..e2) and then up into a1.
#
# Path coordinates are 1-based "x,y" in the map file (the engine converts
# them to 0-based).  ``west_east_paths 1,2 2,2 3,2 4,2`` links
# a2-b2-c2-d2-e2; ``south_north_paths 1,1`` links a1 and a2.
_MAP = """
nb_columns 5
nb_lines 3
nb_players_min 1
nb_players_max 1
starting_squares e2
starting_resources 0 0
terrain plain a1 a2 a3 a4 a5 b1 b2 b3 b4 b5 c1 c2 c3 c4 c5 d1 d2 d3 d4 d5 e1 e2 e3 e4 e5
west_east_paths 1,2 2,2 3,2 4,2 5,2
south_north_paths 1,1
"""


@pytest.fixture
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _sq(world, label):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid["%s,%s" % (col, row)]


def _world(seed=7):
    world = World([], seed)
    world._parse_map(_MAP)
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    world.treaty_until_time = 0
    p1 = DirectClient("p1", None)
    p1.faction = "britons"
    p1.alliance = "1"
    p1.create_player(world)
    p1.player.population = 200
    return world, p1.player


def _spawn(cls, player, place, x, y):
    unit = cls(player, place, x, y)
    unit.collision = 0
    return unit


def _ticks(ms):
    return max(1, int(ms / VIRTUAL_TIME_INTERVAL))


# ---------------------------------------------------------------------------
# Bug 1: units must all reach the destination square, not stop half-way.
# ---------------------------------------------------------------------------


class _FakePlace:
    """A square-like object with just the bounds ZoomTarget needs."""

    title = []
    xmin, ymin, xmax, ymax = 0, 0, 12000, 12000


def test_zoom_target_does_not_contain_a_point_from_another_square():
    """A zoom cell of square a1 must not swallow a point from d2."""
    from soundrts.worldroom import ZoomTarget

    place = _FakePlace()
    # A slot in the top-right sub-cell of a1.
    zt = ZoomTarget(place, 11500, 11500, precision=5)
    # A unit still standing in square d2 (x 36000..48000, y 12000..24000).
    assert zt.contains(47904, 17482) is False
    # A point genuinely inside a1's top-right sub-cell still matches.
    assert zt.contains(11500, 11500) is True


def test_zoom_cell_contains_requires_the_point_inside_the_square():
    from soundrts.worldroom import zoom_cell_contains

    place = _FakePlace()
    assert zoom_cell_contains(place, 5, 11500, 11500, 11500, 11500) is True
    # Far away in another square -> not contained.
    assert zoom_cell_contains(place, 5, 11500, 11500, 47904, 17482) is False
    # Just outside the square's own bounds -> not contained either.
    assert zoom_cell_contains(place, 5, 11500, 11500, 12000, 11500) is False


def test_whole_line_formation_reaches_the_far_square(aoe2_loaded):
    """The reported bug: 3 archers stopped in d2 and never reached a1.

    The army stands in e2 (``4,1``) and is ordered to a1 (``0,0``) with a
    horizontal line formation.  Every unit must end up in a1.
    """
    world, player = _world()
    e2 = _sq(world, "e2")
    a1 = _sq(world, "a1")

    arch_cls = rules.unit_class("aoe_archer")
    knight_cls = rules.unit_class("aoe_knight")
    melee_cls = rules.unit_class("man_at_arms")

    army = []
    # 12 archers, spread over a wide line.
    for i in range(12):
        army.append(_spawn(arch_cls, player, e2, 48000 + (i % 4) * 200,
                           12000 + (i // 4) * 2000))
    for i in range(12):
        army.append(_spawn(knight_cls, player, e2, 48500, 12000 + i * 200))
    army.append(_spawn(melee_cls, player, e2, 47000, 12000))
    army.append(_spawn(melee_cls, player, e2, 47500, 12000))

    for u in army:
        u.formation = "formation_line"

    player.group = list(army)
    for u in army:
        u.group = player.group
        u.take_order(["go", a1.id], forget_previous=True)
    after_group_order(player.group, "go")

    # The formation must really produce slots in the destination square.
    assert any(getattr(u, "_formation_slot", None) for u in army)

    # VIRTUAL_TIME_INTERVAL is 300 ms per world tick, so marching four
    # squares takes a couple of hundred ticks.
    for _ in range(_ticks(400000)):
        world.update()

    stuck = [u for u in army if getattr(u, "place", None) is not a1]
    assert stuck == [], (
        "units stuck short of the destination: %s"
        % [(u.id, u.type_name, getattr(u.place, "name", None))
           for u in stuck]
    )


# ---------------------------------------------------------------------------
# Bug 2: the view focus must survive a save / load round trip.
# ---------------------------------------------------------------------------


class _FakeGridView:
    def __init__(self):
        self._cam_force_center = False
        self._cam_origin = (1, 2)


class _FakeInterface:
    def __init__(self, world):
        self.world = world
        self.place = None
        self.target = "stale"
        self.follow_mode = True
        self.zoom = None
        self.zoom_mode = False
        self.scouted_squares = ()
        self.scouted_before_squares = ()
        self._fog_synced = False
        self.grid_view = _FakeGridView()


class _FakeWorld:
    """Minimal stand-in for a World exposing ``squares``."""

    def __init__(self, squares):
        self.squares = list(squares)


class _FakeSquare:
    id = 42
    name = "3,0"


def test_capture_and_restore_focus_round_trip():
    from soundrts.clientgame.focus_persistence import capture_focus, restore_focus

    square = _FakeSquare()
    world = _FakeWorld([square])
    iface = _FakeInterface(world)
    iface.place = square

    data = capture_focus(iface)
    assert data is not None
    assert data["square_id"] == 42

    # A fresh interface (as after a load) has no focus at all.
    fresh = _FakeInterface(world)
    assert fresh.place is None
    assert restore_focus(fresh, data) is True
    assert fresh.place is square
    assert fresh.target is None
    assert fresh.follow_mode is False
    # The camera is re-centred on the restored square.
    assert fresh.grid_view._cam_force_center is True
    assert fresh.grid_view._cam_origin is None


def test_capture_focus_without_a_square_returns_none():
    from soundrts.clientgame.focus_persistence import capture_focus

    iface = _FakeInterface(_FakeWorld([]))
    assert capture_focus(iface) is None
    assert capture_focus(None) is None


def test_restore_focus_ignores_a_square_that_no_longer_exists():
    from soundrts.clientgame.focus_persistence import restore_focus

    iface = _FakeInterface(_FakeWorld([_FakeSquare()]))
    # The saved square id is not in the loaded world.
    assert restore_focus(iface, {"square_id": 999}) is False
    assert iface.place is None
    assert restore_focus(iface, None) is False
    assert restore_focus(iface, {}) is False


def test_savable_stores_the_focus_and_strips_the_interface():
    """``_Savable.__getstate__`` must keep the focus but drop the interface."""
    from soundrts.game import _Savable

    square = _FakeSquare()

    class _Game(_Savable):
        pass

    g = _Game()
    g.interface = _FakeInterface(_FakeWorld([square]))
    g.interface.place = square
    g._replay_file = object()

    state = g.__getstate__()
    assert "interface" not in state
    assert state["_saved_focus"]["square_id"] == 42


# ---------------------------------------------------------------------------
# Bug 2b: the restored square must not be announced as "unknown".
# ---------------------------------------------------------------------------


def test_fog_state_ready_needs_the_first_voila():
    from soundrts.clientgame.focus_persistence import fog_state_ready

    iface = _FakeInterface(_FakeWorld([_FakeSquare()]))
    # Before the server's first "voila" the fog data is unknown.
    iface._fog_synced = False
    assert fog_state_ready(iface) is False
    # After the voila the square is scouted -> ready.
    iface._fog_synced = True
    assert fog_state_ready(iface) is True
    assert fog_state_ready(None) is False


def test_restored_focus_is_announced_only_once_the_fog_is_known(monkeypatch):
    """The announce must wait for the fog data, otherwise it says 'unknown'."""
    from soundrts.clientgame import game_navigation as nav
    from soundrts.clientgame.focus_persistence import announce_restored_focus

    spoken = []
    monkeypatch.setattr(
        nav, "say_square", lambda iface, p, prefix=[]: spoken.append((p, list(prefix)))
    )

    square = _FakeSquare()
    iface = _FakeInterface(_FakeWorld([square]))
    iface.place = square
    iface.scouted_squares = ()
    iface.scouted_before_squares = ()
    iface._fog_synced = False

    announce_restored_focus(iface, square)

    # Frame 1: no fog data yet -> nothing is spoken, the announcement stays
    # queued.
    nav.flush_pending_square_announce(iface)
    assert spoken == []
    assert iface._pending_square_announce is not None

    # The server's first "voila" arrives.
    iface.scouted_squares = {square}
    iface._fog_synced = True

    # Frame 2: now the square is announced (and only once).
    nav.flush_pending_square_announce(iface)
    assert spoken == [(square, [])]
    assert iface._pending_square_announce is None

    # Frame 3: no repeat.
    nav.flush_pending_square_announce(iface)
    assert spoken == [(square, [])]


def test_restored_focus_announce_is_dropped_when_the_player_moved_on(
    monkeypatch,
):
    from soundrts.clientgame import game_navigation as nav
    from soundrts.clientgame.focus_persistence import announce_restored_focus

    spoken = []
    monkeypatch.setattr(
        nav, "say_square", lambda iface, p, prefix=[]: spoken.append((p, list(prefix)))
    )

    square = _FakeSquare()
    other = _FakeSquare()
    iface = _FakeInterface(_FakeWorld([square, other]))
    iface.place = square
    iface.scouted_squares = {square}
    iface._fog_synced = True

    announce_restored_focus(iface, square)
    # The player moved to another square before the announcement fired.
    iface.place = other
    nav.flush_pending_square_announce(iface)
    assert spoken == []
    assert iface._pending_square_announce is None
