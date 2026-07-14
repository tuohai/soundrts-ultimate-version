"""Tests for Computer._pick_nearest_reachable (Euclidean prefilter + A* top_k)."""

from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer


class _Place:
    def __init__(self, pid, x, y, distances):
        self.id = pid
        self.x = x
        self.y = y
        self._distances = distances

    def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
        return self._distances.get(dest.id, float("inf"))


def _candidate(cid, place):
    return SimpleNamespace(id=cid, place=place)


def test_pick_nearest_reachable_uses_top_k_path_not_all():
    """Far Euclidean candidates must not be pathfinded when a nearer one is reachable."""
    calls = []

    class TrackingPlace(_Place):
        def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
            calls.append(dest.id)
            return super().shortest_path_distance_to(dest, player, plane, avoid)

    origin = TrackingPlace(
        0,
        0,
        0,
        {1: 100, 2: 50, 3: 10, 4: float("inf")},
    )
    # Euclidean nearest: 1 (10), 4 (15). First reachable among them is 1.
    p1 = _Place(1, 10, 0, {})
    p2 = _Place(2, 20, 0, {})
    p3 = _Place(3, 1000, 0, {})
    p4 = _Place(4, 15, 0, {})
    cands = [_candidate(1, p1), _candidate(2, p2), _candidate(3, p3), _candidate(4, p4)]

    ai = Computer.__new__(Computer)
    picked = Computer._pick_nearest_reachable(
        ai, origin, cands, top_k=2
    )
    assert picked.id == 1
    assert calls == [1]  # stop at first reachable; never touch 2/3/4


def test_pick_nearest_reachable_falls_back_past_top_k():
    origin = _Place(0, 0, 0, {1: float("inf"), 2: float("inf"), 3: 5})
    p1 = _Place(1, 10, 0, {})
    p2 = _Place(2, 20, 0, {})
    p3 = _Place(3, 1000, 0, {})
    cands = [_candidate(1, p1), _candidate(2, p2), _candidate(3, p3)]
    ai = Computer.__new__(Computer)
    picked = Computer._pick_nearest_reachable(ai, origin, cands, top_k=2)
    assert picked.id == 3


def test_pick_nearest_reachable_empty():
    ai = Computer.__new__(Computer)
    assert Computer._pick_nearest_reachable(ai, None, []) is None
    origin = _Place(0, 0, 0, {})
    assert Computer._pick_nearest_reachable(ai, origin, []) is None


def test_pick_nearest_reachable_sorts_when_ids_are_none():
    """Regression: equal euclid + id=None must not compare entity instances."""

    class _Mine:
        def __init__(self, place):
            self.id = None
            self.place = place

    origin = _Place(0, 0, 0, {10: 1, 11: 2})
    # Same coordinates → same euclid; both ids None.
    p_a = _Place(10, 5, 0, {})
    p_b = _Place(11, 5, 0, {})
    cands = [_Mine(p_a), _Mine(p_b)]
    ai = Computer.__new__(Computer)
    picked = Computer._pick_nearest_reachable(ai, origin, cands, top_k=2)
    assert picked is not None
    assert picked.place.id in (10, 11)
