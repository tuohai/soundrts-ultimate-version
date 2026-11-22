# -*- coding: utf-8 -*-
"""``Square.can_reach`` must agree with the full pathfinding A*.

``Computer._unit_can_reach`` only needs to know *whether* a unit can walk
to a destination.  It used to answer that question with
``shortest_path_to(places=True)``, which mutates the shared world graph and
reconstructs the whole path.  ``Square.can_reach`` answers the same
question with a cheaper exit-graph A* that stops at the destination.

These tests pin the two behaviours together so the optimisation can never
silently change the AI's decisions.
"""
import types

from soundrts.worldplayercomputer import Computer
from soundrts.worldroom import Square


class _FakeExit:
    """Minimal stand-in for ``worldexit.Exit``."""

    is_an_exit = True
    is_blocked_by_forests = False
    _blockers = ()
    _other_side = None

    def __init__(self, place, other=None, x=0, y=0, i=0):
        self.place = place
        self._other_side = other
        self.x = x
        self.y = y
        self.id = i

    @property
    def other_side(self):
        return self._other_side

    def is_blocked(self, player=None, ignore_enemy_walls=False, **kwargs):
        return False


class _FakeWorld:
    def __init__(self, squares):
        self.squares = squares
        self.g = {"ground": {}, "air": {}, "water": {}}
        self.time = 0


def _linked(a, b, index):
    """Connect two squares with a pair of exits (a passage)."""
    ea = _FakeExit(a, b, a.x, a.y, index)
    eb = _FakeExit(b, a, b.x, b.y, index + 1)
    a.exits.append(ea)
    b.exits.append(eb)
    world = a.world
    ground = world.g["ground"]
    # The ground graph links an exit to its partner across the passage.
    ground.setdefault(ea, {})[eb] = 0
    ground.setdefault(eb, {})[ea] = 0
    # ... and to the other exits standing on the same square.
    _relink_square(world, a)
    _relink_square(world, b)
    return ea, eb


def _relink_square(world, square):
    """Mirror the engine's rule: exits on one square link to each other."""
    ground = world.g["ground"]
    for e in square.exits:
        entry = ground.setdefault(e, {})
        for f in square.exits:
            if f is not e:
                entry[f] = 1


def _square(world, name, x, y):
    sq = Square.__new__(Square)
    sq.__dict__.update(
        {
            "world": world,
            "col": x,
            "row": y,
            "name": name,
            "id": len(world.squares) + 1,
            "exits": [],
            "objects": [],
            "place": world,
            "x": x,
            "y": y,
            "is_water": False,
            "is_ground": True,
            "is_air": True,
            "is_inside_place": False,
            "region": None,
            "terrain_speed": (100, 100),
            "_blockers": (),
            "is_an_exit": False,
        }
    )
    world.squares.append(sq)
    return sq


def _world_with_squares():
    world = _FakeWorld([])
    return world


def test_can_reach_true_for_directly_linked_squares():
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    _linked(a, b, 1)
    assert a.can_reach(b, None, plane="ground") is True
    assert b.can_reach(a, None, plane="ground") is True


def test_can_reach_false_for_disconnected_squares():
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    # No exit links the two squares: they are separate islands.
    assert a.can_reach(b, None, plane="ground") is False
    assert b.can_reach(a, None, plane="ground") is False


def test_can_reach_true_through_a_chain():
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    c = _square(world, "2,0", 2, 0)
    _linked(a, b, 1)
    _linked(b, c, 3)
    assert a.can_reach(c, None, plane="ground") is True
    assert c.can_reach(a, None, plane="ground") is True


def test_can_reach_self_is_true():
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    assert a.can_reach(a, None, plane="ground") is True


def test_can_reach_none_destination_is_false():
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    assert a.can_reach(None, None, plane="ground") is False


def test_unit_can_reach_uses_the_reachability_search():
    """The AI helper must go through ``can_reach`` (and stay correct)."""
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    _linked(a, b, 1)

    unit = types.SimpleNamespace(
        airground_type="ground", is_inside=False, place=a, id=1
    )
    comp = Computer.__new__(Computer)
    comp.id = 1
    comp._world_place_for_pathfinding = lambda p: p
    comp._world_place_for_unit = lambda u: u.place
    comp._play_memo = {}
    assert comp._unit_can_reach(unit, b) is True

    c = _square(world, "9,9", 9, 9)
    comp._play_memo = {}
    assert comp._unit_can_reach(unit, c) is False


class _BlockingExit(_FakeExit):
    """An exit whose partner carries blockers (a wall / closed gate)."""

    def __init__(self, place, other=None, x=0, y=0, i=0, blocked=False):
        super().__init__(place, other, x, y, i)
        self._blockers = (object(),) if blocked else ()
        self._blocked = blocked

    def is_blocked(self, player=None, ignore_enemy_walls=False, **kwargs):
        return self._blocked


def test_can_reach_ignores_a_blocked_passage():
    """A passage with blockers must not count as a connection."""
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    ea = _BlockingExit(a, b, a.x, a.y, 1, blocked=True)
    eb = _BlockingExit(b, a, b.x, b.y, 2, blocked=False)
    a.exits.append(ea)
    b.exits.append(eb)
    ground = world.g["ground"]
    ground.setdefault(ea, {})[eb] = 0
    ground.setdefault(eb, {})[ea] = 0
    _relink_square(world, a)
    _relink_square(world, b)

    player = types.SimpleNamespace(id=1)
    # The blocked exit is skipped, so the squares are unreachable.
    assert a.can_reach(b, player, plane="ground") is False


def test_can_reach_forest_blocked_exit_is_skipped():
    """``is_blocked_by_forests`` must short-circuit the whole check."""
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    ea = _FakeExit(a, b, a.x, a.y, 1)
    eb = _FakeExit(b, a, b.x, b.y, 2)
    ea.is_blocked_by_forests = True
    a.exits.append(ea)
    b.exits.append(eb)
    ground = world.g["ground"]
    ground.setdefault(ea, {})[eb] = 0
    ground.setdefault(eb, {})[ea] = 0
    _relink_square(world, a)
    _relink_square(world, b)

    player = types.SimpleNamespace(id=1)
    assert a.can_reach(b, player, plane="ground") is False


def test_can_reach_is_cached_within_the_time_bucket():
    """The 1500 ms bucket must answer a repeat query without re-searching.

    The observable is ``world.g``: the A* reads the exit graph on every
    *real* search, but a cache hit returns before touching it.
    """
    world = _world_with_squares()
    a = _square(world, "0,0", 0, 0)
    b = _square(world, "1,0", 1, 0)
    _linked(a, b, 1)

    class _CountingGraph(dict):
        ground_reads = 0

        def __getitem__(self, key):
            if key == "ground":
                type(self).ground_reads += 1
            return dict.__getitem__(self, key)

    world.g = _CountingGraph(world.g)

    assert a.can_reach(b, None, plane="ground") is True
    assert _CountingGraph.ground_reads == 1, _CountingGraph.ground_reads

    # The second call must be served from the cache (no new graph read).
    assert a.can_reach(b, None, plane="ground") is True
    assert _CountingGraph.ground_reads == 1, _CountingGraph.ground_reads

    # Moving to a new bucket invalidates the memo.
    world.time = 2000
    assert a.can_reach(b, None, plane="ground") is True
    assert _CountingGraph.ground_reads == 2, _CountingGraph.ground_reads
