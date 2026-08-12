"""StarCraft-style extractor: deposit reserve depletes, then low yield."""

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.world_extractor import (
    apply_extractor_production,
    base_production_qty_for,
    effective_resource_volume_max,
    resolve_deposit_source_qty,
    transfer_extractor_source,
)


class _GasBuilding:
    is_an_extractor = 1
    production_qty = 8
    depleted_production_qty = 2
    resource_volume_max = 8


class _GasBuildingNoDepleted(_GasBuilding):
    depleted_production_qty = 0


def _deposit(qty_display, deposit_volume=0):
    return types.SimpleNamespace(
        qty=qty_display * PRECISION,
        deposit_volume=deposit_volume,
    )


def test_resolve_uses_deposit_volume_when_map_qty_is_marker():
    assert resolve_deposit_source_qty(_deposit(1, deposit_volume=5000)) == 5000


def test_resolve_keeps_explicit_map_qty():
    assert resolve_deposit_source_qty(_deposit(1200, deposit_volume=5000)) == 1200


def test_transfer_sets_source_on_extractor():
    building = _GasBuilding()
    building.notify = lambda *_: None
    transfer_extractor_source(building, _deposit(1, deposit_volume=5000))
    assert building.source_qty == 5000
    assert building.source_qty_max == 5000
    assert building.resource_qty == 5000


def test_transfer_skips_non_extractor():
    building = types.SimpleNamespace(is_an_extractor=0)
    transfer_extractor_source(building, _deposit(5000))
    assert not hasattr(building, "source_qty")


def test_extractor_can_still_yield_full_and_depleted():
    from soundrts.world_extractor import extractor_can_still_yield

    building = _GasBuilding()
    building.source_qty = 10
    building.source_qty_max = 10
    assert extractor_can_still_yield(building) is True
    building.source_qty = 0
    assert extractor_can_still_yield(building) is True
    building2 = _GasBuildingNoDepleted()
    building2.source_qty = 0
    building2.source_qty_max = 100
    assert extractor_can_still_yield(building2) is False


def test_gather_slots_cap_and_assignment():
    from soundrts.world_extractor import (
        count_gather_slot_holders,
        count_workers_assigned_to_gather_target,
        gather_slot_available,
        gather_slots_of,
        gather_target_wants_more_workers,
        worker_holds_gather_slot,
    )

    class _B:
        gather_slots = 3
        place = None
        world = None

    class _Order:
        keyword = "gather"
        mode = "gather"
        target = None

    class _Unit:
        def __init__(self, order):
            self.orders = [order]

    class _Player:
        def __init__(self, units):
            self.units = units

    class _World:
        def __init__(self, players):
            self.players = players

    building = _B()
    assert gather_slots_of(building) == 3

    o1 = _Order()
    o1.target = building
    o2 = _Order()
    o2.target = building
    o3 = _Order()
    o3.target = building
    o4 = _Order()
    o4.target = building
    o4.mode = "go_gather"  # waiting — does not hold extract slot

    u1, u2, u3, u4 = _Unit(o1), _Unit(o2), _Unit(o3), _Unit(o4)
    world = _World([_Player([u1, u2, u3, u4])])
    building.world = world

    assert worker_holds_gather_slot(u1, building) is True
    assert worker_holds_gather_slot(u4, building) is False
    assert count_gather_slot_holders(building) == 3
    assert gather_slot_available(building, u4) is False
    assert count_workers_assigned_to_gather_target(building) == 4
    assert gather_target_wants_more_workers(building) is False

    o3.mode = "bring_back"
    assert count_gather_slot_holders(building) == 2
    assert gather_slot_available(building, u4) is True


def test_apply_debits_source_and_switches_to_depleted_rate():
    building = _GasBuilding()
    building.source_qty = 10
    building.source_qty_max = 10
    building.production_qty = 8
    building.resource_qty = 0
    building.notify = lambda *_: None
    assert apply_extractor_production(building, 8) == 8
    assert building.source_qty == 2
    assert apply_extractor_production(building, 8) == 2
    assert building.source_qty == 0
    assert building.production_qty == 2
    assert apply_extractor_production(building, 8) == 2
    assert effective_resource_volume_max(building) == 2
    assert base_production_qty_for(building) == 2


def test_depleted_production_qty_zero_stops():
    building = _GasBuildingNoDepleted()
    building.source_qty = 0
    building.source_qty_max = 100
    building.notify = lambda *_: None
    assert apply_extractor_production(building, 8) == 0
