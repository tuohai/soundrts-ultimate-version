"""_meadow_candidates should BFS nearby squares instead of scanning all fog memory."""

import types

from soundrts.worldplayercomputer_sc_build import _meadow_candidates


class _Square:
    def __init__(self, sid, x=0, y=0):
        self.id = sid
        self.x = x
        self.y = y
        self.objects = []
        self.exits = []
        self.neighbors = []

    def shortest_path_distance_to(self, other, player=None, avoid=False):
        if other is self:
            return 0
        return abs(self.id - getattr(other, "id", 0))


class _Exit:
    def __init__(self, dest):
        self.other_side = types.SimpleNamespace(place=dest)


class _Meadow:
    is_a_building_land = True
    is_an_exit = False

    def __init__(self, mid, place):
        self.id = mid
        self.place = place
        self.x = place.x
        self.y = place.y
        self.type_name = "meadow"


class _Tree:
    is_a_building_land = False
    is_an_exit = False

    def __init__(self, tid, place):
        self.id = tid
        self.place = place


def _link(a, b):
    a.exits.append(_Exit(b))
    b.exits.append(_Exit(a))


def _ai(squares, meadows, junk=()):
    class AI:
        units = [types.SimpleNamespace(place=squares[0])]
        perception = set(meadows) | set(junk)
        memory = set(junk)

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            raise AssertionError("BFS path must not fall back to full-map prune")

    return AI()


def test_meadow_candidates_bfs_stops_at_ten():
    squares = [_Square(i, i * 10, 0) for i in range(15)]
    for a, b in zip(squares, squares[1:]):
        _link(a, b)
    meadows = []
    for i, sq in enumerate(squares):
        m = _Meadow(100 + i, sq)
        sq.objects.append(m)
        meadows.append(m)
    junk = [_Tree(1000 + i, squares[0]) for i in range(200)]
    squares[0].objects.extend(junk)
    ai = _ai(squares, meadows, junk)
    found = _meadow_candidates(ai, squares[0])
    assert [m.place.id for m in found] == list(range(10))
    assert meadows[-1] not in found


def test_meadow_candidates_requires_known_object():
    a = _Square(1)
    b = _Square(2)
    _link(a, b)
    seen = _Meadow(10, a)
    hidden = _Meadow(11, b)
    a.objects.append(seen)
    b.objects.append(hidden)
    ai = _ai([a, b], [seen])
    found = _meadow_candidates(ai, a)
    assert found == [seen]


def test_meadow_candidates_stub_square_still_scans_perception():
    """Existing fixtures have no exits/objects; keep the old scan."""
    place = types.SimpleNamespace(id=1, x=0, y=0, neighbors=[])
    meadow = _Meadow(10, place)

    def _dist(other, player=None, avoid=False):
        return 0

    place.shortest_path_distance_to = _dist

    class AI:
        units = [types.SimpleNamespace(place=place)]
        perception = {meadow}
        memory = set()

        def square_is_dangerous(self, z):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

    found = _meadow_candidates(AI(), place)
    assert found == [meadow]
