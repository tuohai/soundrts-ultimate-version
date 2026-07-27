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


def test_transfer_skips_non_extractor():
    building = types.SimpleNamespace(is_an_extractor=0)
    transfer_extractor_source(building, _deposit(5000))
    assert not hasattr(building, "source_qty")


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
