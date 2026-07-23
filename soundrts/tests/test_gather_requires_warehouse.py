"""Gathered cargo must not enter inventory without a warehouse."""
from __future__ import annotations

import types

from soundrts.worldorders.gathering import GatherOrder


def _make_gather_order(*, cargo, warehouse=None):
    stored = []
    unit = types.SimpleNamespace(
        cargo=cargo,
        airground_type="ground",
        place=types.SimpleNamespace(id="p1", world=types.SimpleNamespace(time=0)),
        notifications=[],
        is_idle=True,
    )
    unit.notify = lambda msg, *_a, **_k: unit.notifications.append(msg)
    unit.stop = lambda: setattr(unit, "stopped", True)
    unit.start_moving_to = lambda target: setattr(unit, "moving_to", target)
    unit._near_enough = lambda t: False

    player = types.SimpleNamespace(
        nearest_warehouse=lambda place, resource_type, include_building_sites=False: warehouse,
        store=lambda resource_type, qty: stored.append((resource_type, qty)),
    )
    unit.player = player

    order = GatherOrder(unit, ["deposit"])
    order.mode = "bring_back"
    order.storage = None
    order.target = types.SimpleNamespace(id="deposit")
    order.update_target = lambda: None
    return order, unit, stored


def test_bring_back_without_warehouse_does_not_store():
    order, unit, stored = _make_gather_order(cargo=(0, 1000), warehouse=None)
    order.execute()
    assert stored == []
    assert unit.cargo == (0, 1000)
    assert order.mode == "bring_back"
    assert "order_impossible" in unit.notifications
    assert getattr(unit, "stopped", False) is True


def test_bring_back_with_warehouse_starts_moving():
    warehouse = types.SimpleNamespace(id="townhall")
    order, unit, stored = _make_gather_order(cargo=(0, 1000), warehouse=warehouse)
    order.execute()
    assert stored == []
    assert unit.cargo == (0, 1000)
    assert order.storage is warehouse
    assert getattr(unit, "moving_to", None) is warehouse
