# -*- coding: utf-8 -*-
"""Gather targeting must not rescan perception via choose(Deposit)."""
from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer
from soundrts.worldresource import Deposit


def _computer(**fields):
    p = Computer.__new__(Computer)
    p.units = []
    p.upgrades = []
    p._play_memo = {}
    p.perception = set()
    p.memory = set()
    for k, v in fields.items():
        setattr(p, k, v)
    return p


def _blocked_origin():
    origin = SimpleNamespace(id="a2", x=0, y=0, is_water=False, is_ground=True)
    origin.shortest_path_distance_to = lambda *_a, **_k: float("inf")
    return origin


def _wood_deposit(place):
    d = Deposit.__new__(Deposit)
    d.place = place
    d.id = "wood1"
    d.qty = 100
    d.resource_type = "resource2"
    d.type_name = "wood"
    return d


def test_choose_gather_target_returns_euclidean_when_path_blocked():
    origin = _blocked_origin()
    dest = SimpleNamespace(id="c5", x=24, y=0, is_water=False, is_ground=True)
    dest.shortest_path_distance_to = origin.shortest_path_distance_to
    deposit = _wood_deposit(dest)
    worker = SimpleNamespace(
        place=origin,
        can_gather_deposit=["all"],
        airground_type="ground",
    )
    p = _computer()
    p.perception = {deposit}
    p._gather_target_ok = lambda o: True
    p._world_place_for_unit = lambda _w: origin
    p._known_ok_deposits = lambda: [deposit]
    p._worker_can_gather_deposit = lambda *_a, **_k: True
    p._gatherable_building_targets = lambda _w: []
    p._resource_need_ratio = lambda _i: 1.0
    p._target_resource_index = lambda _t: 1
    p._need_later_age_production_wood = lambda: False
    p.choose = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("choose(Deposit) must not rescan perception")
    )
    assert p._choose_gather_target(worker) is deposit


def test_choose_gather_target_shares_the_candidate_scan():
    """Two workers on the same square scan the deposits only once.

    The *scan* (which deposits may this worker gather from) is shared;
    only the final *pick* is per-worker, because that is where the
    load balancing happens.  Without the split, spreading the workers
    would cost one full scan per worker.
    """
    origin = _blocked_origin()
    dest = SimpleNamespace(id="c5", x=24, y=0, is_water=False, is_ground=True)
    dest.shortest_path_distance_to = origin.shortest_path_distance_to
    deposit = _wood_deposit(dest)
    worker = SimpleNamespace(
        place=origin,
        id="w1",
        can_gather_deposit=["all"],
        airground_type="ground",
    )
    other = SimpleNamespace(
        place=origin,
        id="w2",
        can_gather_deposit=["all"],
        airground_type="ground",
    )
    scans = []
    p = _computer()
    p._world_place_for_unit = lambda _w: origin
    p._known_ok_deposits = lambda: scans.append(1) or [deposit]
    p._worker_can_gather_deposit = lambda *_a, **_k: True
    p._gatherable_building_targets = lambda _w: []
    p._resource_need_ratio = lambda _i: 1.0
    p._target_resource_index = lambda _t: 1
    p._need_later_age_production_wood = lambda: False
    assert p._choose_gather_target(worker) is deposit
    assert p._choose_gather_target(other) is deposit
    assert scans == [1]


def test_choose_gather_target_does_not_reuse_another_workers_pick():
    """Two workers on the same square must be able to pick *different* targets.

    The pick is memoized per worker, not per square: otherwise every
    villager standing on the same square would be sent to the same
    source and the economy would have a single leg.
    """
    origin = _blocked_origin()
    near = SimpleNamespace(id="near", x=5, y=0, is_water=False, is_ground=True)
    near.shortest_path_distance_to = origin.shortest_path_distance_to
    far = SimpleNamespace(id="far", x=20, y=0, is_water=False, is_ground=True)
    far.shortest_path_distance_to = origin.shortest_path_distance_to
    near_deposit = _wood_deposit(near)
    far_deposit = _wood_deposit(far)
    far_deposit.id = "wood2"

    worker = SimpleNamespace(
        place=origin, id="w1", can_gather_deposit=["all"], airground_type="ground"
    )
    other = SimpleNamespace(
        place=origin, id="w2", can_gather_deposit=["all"], airground_type="ground"
    )

    p = _computer()
    p.AI_type = "expert"
    p.world = SimpleNamespace(players=[p])
    # The workers belong to the player: that is where the load is counted.
    p.units = [worker, other]
    p._world_place_for_unit = lambda _w: origin
    p._known_ok_deposits = lambda: [near_deposit, far_deposit]
    p._worker_can_gather_deposit = lambda *_a, **_k: True
    p._gatherable_building_targets = lambda _w: []
    p._resource_need_ratio = lambda _i: 1.0
    p._target_resource_index = lambda _t: 1
    p._need_later_age_production_wood = lambda: False
    p._keep_lumberjacks = lambda: False
    p._wood_dropoff_place = lambda: None

    first = p._choose_gather_target(worker)
    # The first worker is now busy at that target.
    worker.orders = [SimpleNamespace(keyword="gather", target=first)]
    second = p._choose_gather_target(other)

    assert first is not second
    assert second is far_deposit


def test_choose_gather_target_does_not_rescan_when_no_candidates():
    origin = _blocked_origin()
    worker = SimpleNamespace(
        place=origin,
        can_gather_deposit=["all"],
        airground_type="ground",
    )
    p = _computer()
    p._world_place_for_unit = lambda _w: origin
    p._known_ok_deposits = lambda: []
    p._gatherable_building_targets = lambda _w: []
    p.choose = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("choose(Deposit) must not rescan perception")
    )
    assert p._choose_gather_target(worker) is None


def test_known_huntable_animals_memoized_per_play():
    scans = []

    class _Perc(set):
        def union(self, other):
            scans.append(1)
            return set()

    p = _computer(perception=_Perc(), memory=set())
    assert p._known_huntable_animals() == []
    assert p._known_huntable_animals() == []
    assert len(scans) == 1
