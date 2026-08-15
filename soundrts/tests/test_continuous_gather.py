"""Continuous (AoE2-style) gather: fill carry_capacity at gather_rate, then drop off."""
from __future__ import annotations

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.worldorders.gathering import GatherOrder
from soundrts.worldunit.worldworker import Worker


def _deposit(*, qty=100 * PRECISION, type_name="wood", resource_type=0):
    state = {"qty": qty}

    def extract_resource(want):
        take = min(want, state["qty"])
        state["qty"] -= take
        return take

    return types.SimpleNamespace(
        type_name=type_name,
        resource_type=resource_type,
        resource_qty=qty,
        extract_resource=extract_resource,
    )


def _worker(*, gather_mode="continuous", carry_capacity=10, rate=0.4):
    unit = types.SimpleNamespace(
        gather_mode=gather_mode,
        carry_capacity=carry_capacity,
        cargo=None,
        place=types.SimpleNamespace(world=types.SimpleNamespace(time=0)),
        notifications=[],
        is_idle=True,
        player=types.SimpleNamespace(
            gather_time_bonus=None,
            carry_capacity_bonus=None,
            ai_gather_time_percent=100,
        ),
    )
    unit.notify = lambda msg, *_a, **_k: unit.notifications.append(msg)
    unit.stop = lambda: setattr(unit, "stopped", True)
    unit.deploy = lambda: setattr(unit, "deployed", True)
    unit._near_enough = lambda t: True
    unit.uses_continuous_gather = lambda: gather_mode in ("continuous", "aoe", "aoe2")
    unit.get_gather_rate = lambda resource_type, target=None: rate
    unit.get_carry_capacity = lambda resource_type=None, target=None: carry_capacity
    unit.get_gather_time = lambda resource_type, target=None: 5
    unit.get_gather_qty = lambda resource_type, target=None: 2
    return unit


def _order(unit, deposit, mode="gather"):
    order = GatherOrder(unit, ["d"])
    order.mode = mode
    order.target = deposit
    order.storage = None
    order.update_target = lambda: None
    return order


def test_continuous_fills_carry_then_brings_back():
    unit = _worker(carry_capacity=10, rate=1.0)
    deposit = _deposit()
    order = _order(unit, deposit)
    order._cont_last_t = 0
    order._cont_accum = 0.0

    unit.place.world.time = 5000
    order.execute()
    assert order.mode == "gather"
    assert unit.cargo[1] == 5 * PRECISION

    unit.place.world.time = 10000
    order.execute()
    assert order.mode == "bring_back"
    assert unit.cargo[1] == 10 * PRECISION


def test_trip_mode_still_one_shot():
    unit = _worker(gather_mode="trip", carry_capacity=10, rate=1.0)
    deposit = _deposit()
    order = _order(unit, deposit)
    order.delay = 0
    unit.place.world.time = 1000
    order.execute()
    assert order.mode == "bring_back"
    assert unit.cargo[1] == 2 * PRECISION


def test_worker_helpers_default_trip():
    w = types.SimpleNamespace(
        gather_mode=None,
        carry_capacity=0,
        player=None,
        gather_rate={},
    )
    w.get_gather_qty = lambda *a, **k: 2
    w.get_gather_time = lambda *a, **k: 5
    assert Worker.get_gather_mode(w) == "trip"
    assert Worker.get_gather_mode(w) not in ("continuous", "aoe", "aoe2")
    assert abs(Worker.get_gather_rate(w, "resource2", None) - 0.4) < 1e-6


def test_gather_byproduct_matches_wood_deposit_type_name():
    stored = []
    unit = _worker()
    unit.gather_byproduct = {"wood": (0.5, "resource1")}
    unit.player = types.SimpleNamespace(store=lambda res, amt: stored.append((res, amt)))
    deposit = _deposit(type_name="wood", resource_type="resource2")
    order = _order(unit, deposit)
    order._apply_gather_byproduct(2.0)
    assert stored == [("resource1", 1 * PRECISION)]
    assert abs(order._byproduct_accum - 0.0) < 1e-9
