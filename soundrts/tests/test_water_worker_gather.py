"""水上/陆地工人只能采集对应地形上的资源。

地图里普通矿床即可，例如 ``goldmines 10000 a3``：若 a3 是水路方格，
则 boat 可采、农民不可；若 a3 是陆地，则相反。不依赖专用「水上矿床」类型。
"""
from __future__ import annotations

import types

from soundrts.worldorders.gathering import GatherOrder
from soundrts.worldresource import Deposit
from soundrts.worldunit.worldworker import Worker


def _make_worker(*, airground_type="ground", can_gather_deposit=None):
    worker = types.SimpleNamespace(
        airground_type=airground_type,
        can_gather_deposit=can_gather_deposit or ["all"],
        can_gather_building=[],
        notifications=[],
    )
    worker.notify = lambda msg, *_a, **_k: worker.notifications.append(msg)
    return worker


def _make_deposit(*, is_water=False, is_ground=True, type_name="goldmine"):
    place = types.SimpleNamespace(is_water=is_water, is_ground=is_ground)
    deposit = Deposit.__new__(Deposit)
    deposit.type_name = type_name
    deposit.place = place
    deposit.resource_type = "gold"
    deposit.resource_qty = 1000
    deposit.id = "deposit"
    return deposit


def test_goldmine_on_water_square_map_syntax():
    """goldmines <qty> <square> — 方格为水路时仅水上工人可采。"""
    worker = _make_worker(airground_type="water")
    deposit = _make_deposit(is_water=True, is_ground=False, type_name="goldmine")
    assert Worker._can_gather_target(worker, deposit)

    peasant = _make_worker(airground_type="ground")
    assert not Worker._can_gather_target(peasant, deposit)


def test_goldmine_on_land_square_map_syntax():
    deposit = _make_deposit(is_water=False, is_ground=True, type_name="goldmine")
    peasant = _make_worker(airground_type="ground")
    assert Worker._can_gather_target(peasant, deposit)

    boat = _make_worker(airground_type="water")
    assert not Worker._can_gather_target(boat, deposit)


def test_water_worker_cannot_gather_land_deposit():
    worker = _make_worker(airground_type="water")
    deposit = _make_deposit(is_water=False, is_ground=True)
    assert not Worker._gather_terrain_ok_for_unit(worker, deposit)
    assert not Worker._can_gather_target(worker, deposit)


def test_ground_worker_cannot_gather_water_deposit():
    worker = _make_worker(airground_type="ground")
    deposit = _make_deposit(is_water=True, is_ground=False)
    assert not Worker._gather_terrain_ok_for_unit(worker, deposit)
    assert not Worker._can_gather_target(worker, deposit)


def test_water_worker_can_gather_water_deposit():
    worker = _make_worker(airground_type="water")
    deposit = _make_deposit(is_water=True, is_ground=False)
    assert Worker._gather_terrain_ok_for_unit(worker, deposit)
    assert Worker._can_gather_target(worker, deposit)


def test_ground_worker_can_gather_land_deposit():
    worker = _make_worker(airground_type="ground")
    deposit = _make_deposit(is_water=False, is_ground=True)
    assert Worker._gather_terrain_ok_for_unit(worker, deposit)
    assert Worker._can_gather_target(worker, deposit)


def test_ford_deposit_ok_for_ground_worker():
    worker = _make_worker(airground_type="ground")
    deposit = _make_deposit(is_water=True, is_ground=True)
    assert Worker._gather_terrain_ok_for_unit(worker, deposit)
    assert Worker._can_gather_target(worker, deposit)


def test_gather_order_to_land_deposit_impossible_for_boat():
    deposit = _make_deposit(is_water=False, is_ground=True)
    deposit.id = "d1"
    worker = _make_worker(airground_type="water")
    unit = types.SimpleNamespace(
        airground_type=worker.airground_type,
        can_gather_deposit=worker.can_gather_deposit,
        can_gather_building=worker.can_gather_building,
        orders=[],
        notifications=[],
        cargo=None,
        player=types.SimpleNamespace(
            get_object_by_id=lambda _id: deposit,
        ),
    )
    unit.notify = lambda msg, *_a, **_k: unit.notifications.append(msg)
    unit._can_gather_target = Worker._can_gather_target.__get__(unit, Worker)

    order = GatherOrder(unit, [deposit.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,land_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications
