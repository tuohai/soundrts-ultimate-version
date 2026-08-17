"""_has_reachable_deposit must stop A* at the first reachable deposit."""

from soundrts.worldplayercomputer import Computer
from soundrts.worldresource import Deposit


class _Place:
    def __init__(self, pid, x, y, distances):
        self.id = pid
        self.x = x
        self.y = y
        self._distances = distances

    def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
        return self._distances.get(dest.id, float("inf"))


class _Wood(Deposit):
    type_name = "wood"
    resource_type = "resource2"
    collision = 0

    def __init__(self, oid, place):
        self.id = oid
        self.place = place
        self.qty = 1000


def test_has_reachable_deposit_stops_at_first_path():
    calls = []

    class TrackingPlace(_Place):
        def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
            calls.append(dest.id)
            return super().shortest_path_distance_to(dest, player, plane, avoid)

    origin = TrackingPlace(0, 0, 0, {1: 10, 2: 20, 3: 30})
    near = _Place(1, 10, 0, {})
    mid = _Place(2, 20, 0, {})
    far = _Place(3, 1000, 0, {})
    trees = [_Wood(11, near), _Wood(12, mid), _Wood(13, far)]

    ai = Computer.__new__(Computer)
    ai.perception = set(trees)
    ai.memory = set()
    ai._play_memo = {}
    ai._gather_target_ok = lambda o: True
    ai._deposit_resource_index = lambda o: 1
    ai._worker_origin_for_gather = lambda: origin
    ai._reachable_deposits = Computer._reachable_deposits.__get__(ai, Computer)
    ai._has_reachable_deposit = Computer._has_reachable_deposit.__get__(ai, Computer)

    assert ai._has_reachable_deposit(1) is True
    assert calls == [1]
    # same play() memo: no second A* pass
    assert ai._has_reachable_deposit(1) is True
    assert calls == [1]


def test_reachable_deposits_full_list_still_scans(monkeypatch):
    calls = []

    class TrackingPlace(_Place):
        def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
            calls.append(dest.id)
            return super().shortest_path_distance_to(dest, player, plane, avoid)

    origin = TrackingPlace(0, 0, 0, {1: 10, 2: 20})
    p1 = _Place(1, 10, 0, {})
    p2 = _Place(2, 20, 0, {})
    trees = [_Wood(11, p1), _Wood(12, p2)]
    ai = Computer.__new__(Computer)
    ai.perception = set(trees)
    ai.memory = set()
    ai._gather_target_ok = lambda o: True
    ai._deposit_resource_index = lambda o: 1
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.find_amphibious_crossing",
        lambda *a, **k: None,
    )
    found = Computer._reachable_deposits(ai, origin, 1)
    assert [o.place.id for o, _mode in found] == [1, 2]
    assert calls == [1, 2]


def test_has_reachable_deposit_same_square_skips_astar():
    calls = []

    class TrackingPlace(_Place):
        def shortest_path_distance_to(self, dest, player, plane="ground", avoid=False):
            calls.append(dest.id)
            return super().shortest_path_distance_to(dest, player, plane, avoid)

    origin = TrackingPlace(0, 0, 0, {})
    tree = _Wood(11, origin)
    ai = Computer.__new__(Computer)
    ai.perception = {tree}
    ai.memory = set()
    ai._play_memo = None
    ai._gather_target_ok = lambda o: True
    ai._deposit_resource_index = lambda o: 1
    ai._worker_origin_for_gather = lambda: origin
    ai._reachable_deposits = Computer._reachable_deposits.__get__(ai, Computer)
    ai._has_reachable_deposit = Computer._has_reachable_deposit.__get__(ai, Computer)
    assert ai._has_reachable_deposit(1) is True
    assert calls == []
