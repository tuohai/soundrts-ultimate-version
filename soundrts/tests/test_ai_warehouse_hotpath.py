# -*- coding: utf-8 -*-
"""Warehouse A* hot path: same-square drop-off and far Euclidean skip."""
from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer
from soundrts.worldunit import BuildingSite


def _computer(**fields):
    p = Computer.__new__(Computer)
    p.units = []
    p.upgrades = []
    p._play_memo = {}
    p._workers = []
    p._nearest_wh_cache = {}
    p._nearest_wh_bucket = -1
    for k, v in fields.items():
        setattr(p, k, v)
    return p


def test_square_has_finished_dropoff_ignores_building_site():
    hall = SimpleNamespace(storable_resource_types=("resource1", "resource2"))
    site = BuildingSite.__new__(BuildingSite)
    place = SimpleNamespace(objects=[hall])
    p = _computer()
    assert p._square_has_finished_dropoff(place, "resource1")
    place.objects = [site]
    assert not p._square_has_finished_dropoff(place, "resource1")


def test_warehouse_is_too_far_skips_astar_when_euclidean_exceeds_square():
    place = SimpleNamespace(id=1, x=0, y=0)
    far = SimpleNamespace(id=2, x=100, y=0)
    wh = SimpleNamespace(place=far)
    p = _computer(world=SimpleNamespace(square_width=10))

    def _boom(*_a, **_k):
        raise AssertionError("A* should not run for far warehouses")

    place.shortest_path_distance_to = _boom
    assert p._warehouse_is_too_far(place, wh) is True
    assert p._warehouse_is_too_far(place, None) is True
    same = SimpleNamespace(place=place)
    assert p._warehouse_is_too_far(place, same) is False


def test_warehouse_is_too_far_uses_path_for_orthogonal_neighbor():
    place = SimpleNamespace(id=1, x=0, y=0)
    near = SimpleNamespace(id=2, x=10, y=0)
    wh = SimpleNamespace(place=near)
    p = _computer(world=SimpleNamespace(square_width=10))
    place.shortest_path_distance_to = lambda *_a, **_k: 10
    assert p._warehouse_is_too_far(place, wh) is False
    place.shortest_path_distance_to = lambda *_a, **_k: 40
    assert p._warehouse_is_too_far(place, wh) is True


def test_build_a_warehouse_for_skips_nearest_when_townhall_on_square():
    hall = SimpleNamespace(storable_resource_types=("resource1",))
    place = SimpleNamespace(id="a2", objects=[hall], x=0, y=0)
    deposit = SimpleNamespace(place=place, resource_type="resource1", id="gold")
    worker = SimpleNamespace(
        place=place,
        orders=[SimpleNamespace(keyword="gather", target=deposit)],
    )
    p = _computer(_workers=[worker])
    p.nearest_warehouse = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("nearest_warehouse should not run")
    )
    p._build_a_warehouse_for(deposit)


def test_build_a_warehouse_for_skips_nearest_when_adjacent_dropoff():
    hall = SimpleNamespace(storable_resource_types=("resource2",))
    dest = SimpleNamespace(id="b2", objects=[hall], x=12, y=0)
    other = SimpleNamespace(place=dest, is_blocked=lambda *_a, **_k: False)
    exit_ = SimpleNamespace(
        other_side=other,
        is_blocked=lambda *_a, **_k: False,
    )
    place = SimpleNamespace(id="a2", objects=[], exits=[exit_], x=0, y=0)
    deposit = SimpleNamespace(place=place, resource_type="resource2", id="wood")
    worker = SimpleNamespace(
        place=place,
        orders=[SimpleNamespace(keyword="gather", target=deposit)],
    )
    p = _computer(_workers=[worker])
    p.square_is_dangerous = lambda *_a, **_k: False
    p.nearest_warehouse = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("nearest_warehouse should not run")
    )
    p._best_warehouse = lambda **_k: (_ for _ in ()).throw(
        AssertionError("should not build mill when adjacent hall exists")
    )
    p._build_a_warehouse_for(deposit)


def test_build_a_warehouse_for_does_not_astar_when_no_nearby_dropoff():
    place = SimpleNamespace(id="c5", objects=[], exits=[], x=0, y=0)
    deposit = SimpleNamespace(place=place, resource_type="resource2", id="wood")
    worker = SimpleNamespace(
        place=place,
        orders=[SimpleNamespace(keyword="gather", target=deposit)],
    )
    p = _computer(_workers=[worker])
    p.nearest_warehouse = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("nearest_warehouse should not run")
    )
    called = []
    p._best_warehouse = lambda **_k: called.append("best") or None
    p._build_a_warehouse_for(deposit)
    assert called == ["best"]


def test_build_a_warehouse_if_useful_dedups_same_deposit():
    hall = SimpleNamespace(storable_resource_types=("resource1",))
    place = SimpleNamespace(id="a2", objects=[hall], x=0, y=0)
    deposit = SimpleNamespace(place=place, resource_type="resource1", id="gold")
    order = SimpleNamespace(keyword="gather", target=deposit)
    workers = [
        SimpleNamespace(place=place, orders=[order]),
        SimpleNamespace(place=place, orders=[order]),
        SimpleNamespace(place=place, orders=[order]),
    ]
    p = _computer(_workers=workers)
    calls = []
    p._warehouse_economy_enabled = lambda: True
    p._auto_warehouse_expansion_enabled = lambda: True
    p._best_warehouse = lambda: SimpleNamespace(cost=(0, 0))
    p.missing_resources = lambda _cost: False
    p._build_a_warehouse_for = lambda d: calls.append(d)
    p._build_a_warehouse_if_useful()
    assert calls == [deposit]


def test_pick_nearest_reachable_returns_same_square_without_path():
    origin = SimpleNamespace(id="sq", x=0, y=0)
    local = SimpleNamespace(id=1, place=origin)
    far = SimpleNamespace(id=2, place=SimpleNamespace(id="far", x=99, y=99))
    origin.shortest_path_distance_to = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("same-square pick must not A*")
    )
    p = _computer()
    assert p._pick_nearest_reachable(origin, [far, local]) is local


def test_nearest_warehouse_same_square_skips_astar():
    place = SimpleNamespace(id="a2", x=0, y=0)
    place.shortest_path_distance_to = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("same-square warehouse must not A*")
    )
    hall = SimpleNamespace(
        id="th",
        place=place,
        storable_resource_types=("resource1", "resource2"),
        _cached_is_building_site=False,
    )
    p = Computer.__new__(Computer)
    p.world = SimpleNamespace(time=0)
    p._warehouse_cache = {}
    p._warehouse_candidates_cache = {}
    p._warehouse_candidates_bucket = -1
    p._place_distance_cache = {}
    p._place_distance_cache_bucket = -1
    p.allied = [p]
    p.units = [hall]
    assert p.nearest_warehouse(place, "resource1") is hall


def test_nearest_warehouse_adjacent_skips_astar():
    origin = SimpleNamespace(id="a2", x=0, y=0)
    dest = SimpleNamespace(id="b2", x=12, y=0)
    origin.shortest_path_distance_to = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("adjacent warehouse must not A*")
    )
    dest.shortest_path_distance_to = origin.shortest_path_distance_to
    other = SimpleNamespace(place=dest, is_blocked=lambda *_a, **_k: False)
    origin.exits = [
        SimpleNamespace(other_side=other, is_blocked=lambda *_a, **_k: False)
    ]
    mill = SimpleNamespace(
        id="mill",
        place=dest,
        storable_resource_types=("resource2",),
        _cached_is_building_site=False,
    )
    p = Computer.__new__(Computer)
    p.world = SimpleNamespace(time=0, square_width=12)
    p._warehouse_cache = {}
    p._warehouse_candidates_cache = {}
    p._warehouse_candidates_bucket = -1
    p._place_distance_cache = {}
    p._place_distance_cache_bucket = -1
    p.allied = [p]
    p.units = [mill]
    assert p.nearest_warehouse(origin, "resource2") is mill


def _wh_player(units, time=0, square_width=12):
    p = Computer.__new__(Computer)
    p.world = SimpleNamespace(time=time, square_width=square_width)
    p._warehouse_cache = {}
    p._warehouse_candidates_cache = {}
    p._warehouse_candidates_bucket = -1
    p._place_distance_cache = {}
    p._place_distance_cache_bucket = -1
    p.allied = [p]
    p.units = units
    return p


def test_nearest_warehouse_two_hops_skips_astar():
    origin = SimpleNamespace(id="a2", x=0, y=0)
    mid = SimpleNamespace(id="b2", x=12, y=0)
    dest = SimpleNamespace(id="c2", x=24, y=0)
    origin.shortest_path_distance_to = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("two-hop warehouse must not A*")
    )
    unblock = lambda *_a, **_k: False
    dest_side = SimpleNamespace(place=dest, is_blocked=unblock)
    origin_side = SimpleNamespace(place=origin, is_blocked=unblock)
    mid_to_dest = SimpleNamespace(other_side=dest_side, is_blocked=unblock)
    mid_to_origin = SimpleNamespace(other_side=origin_side, is_blocked=unblock)
    origin.exits = [
        SimpleNamespace(
            other_side=SimpleNamespace(place=mid, is_blocked=unblock),
            is_blocked=unblock,
        )
    ]
    mid.exits = [mid_to_dest, mid_to_origin]
    dest.exits = [
        SimpleNamespace(
            other_side=SimpleNamespace(place=mid, is_blocked=unblock),
            is_blocked=unblock,
        )
    ]
    mill = SimpleNamespace(
        id="mill",
        place=dest,
        storable_resource_types=("resource2",),
        _cached_is_building_site=False,
    )
    p = _wh_player([mill])
    assert p.nearest_warehouse(origin, "resource2") is mill


def test_nearest_warehouse_stops_at_first_reachable():
    calls = []
    origin = SimpleNamespace(id="a2", x=0, y=0)

    def _dist(dest, *_a, **_k):
        calls.append(dest.id)
        return 20 if dest.id == "near" else 40

    origin.shortest_path_distance_to = _dist
    origin.exits = []
    near = SimpleNamespace(id="near", x=36, y=0, exits=[])
    far = SimpleNamespace(id="far", x=48, y=0, exits=[])
    mill_a = SimpleNamespace(
        id="ma",
        place=near,
        storable_resource_types=("resource2",),
        _cached_is_building_site=False,
    )
    mill_b = SimpleNamespace(
        id="mb",
        place=far,
        storable_resource_types=("resource2",),
        _cached_is_building_site=False,
    )
    p = _wh_player([mill_a, mill_b])
    assert p.nearest_warehouse(origin, "resource2") is mill_a
    assert calls == ["near"]
