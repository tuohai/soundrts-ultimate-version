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


def test_choose_gather_target_memoized_for_same_origin():
    origin = _blocked_origin()
    dest = SimpleNamespace(id="c5", x=24, y=0, is_water=False, is_ground=True)
    dest.shortest_path_distance_to = origin.shortest_path_distance_to
    deposit = _wood_deposit(dest)
    worker = SimpleNamespace(
        place=origin,
        can_gather_deposit=["all"],
        airground_type="ground",
    )
    other = SimpleNamespace(
        place=origin,
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
