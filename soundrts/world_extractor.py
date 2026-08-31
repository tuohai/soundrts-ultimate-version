"""Extractor buildings that deplete a deposit reserve (StarCraft-style gas).

Keywords (rules.txt):
  is_an_extractor 1          — building consumes a transferred deposit reserve
  depleted_production_qty N  — per-trip yield after the reserve hits 0 (0 = stop)
  deposit_volume N           — default reserve on the deposit type (map qty ``1`` = use this)

StarCraft gas extractors: workers gather from the building (qty from rules;
SC2 uses extraction_qty 4 / depleted 2). Geyser reserve is on ``source_qty``.
Prefer ``auto_production 0`` so trips debit the reserve directly via
Building.extract_resource. ``gather_slots 3`` caps concurrent extractors
(4th waits) like SC gas saturation.

Related: requires_deposit, resource_type, extraction_qty, is_gather, gather_slots.
"""

from .lib.nofloat import PRECISION


def resolve_deposit_source_qty(deposit):
    """Return the display-unit reserve to transfer onto an extractor building."""
    qty = getattr(deposit, "qty", 0) or 0
    display = qty // PRECISION if qty else 0
    default_vol = int(getattr(deposit, "deposit_volume", 0) or 0)
    # Map convention: ``geyser 1`` is a build-site marker; use deposit_volume.
    if display <= 1 and default_vol > 0:
        return default_vol
    if display > 0:
        return display
    return default_vol


def transfer_extractor_source(building, deposit):
    """Copy deposit reserves onto the building, then caller deletes the deposit."""
    if not getattr(building, "is_an_extractor", 0):
        return
    source = resolve_deposit_source_qty(deposit)
    building.source_qty = source
    building.source_qty_max = source
    # Mirror reserve onto resource_qty so trip gather / UI see remaining gas.
    building.resource_qty = source
    building._resource_qty_frac = 0
    if source > 0:
        building.notify(f"source_qty_update,{source}")
        building.notify(f"qty_update,{source}")


def extractor_source_ready(building):
    """True once the deposit reserve has been transferred onto the building."""
    return getattr(building, "is_an_extractor", 0) and hasattr(
        building, "source_qty_max"
    )


def is_extractor_source_depleted(building):
    return extractor_source_ready(building) and getattr(building, "source_qty", 0) <= 0


def extractor_can_still_yield(building):
    """True while workers can still take trips (full or depleted rate)."""
    if not getattr(building, "is_an_extractor", 0):
        return False
    if not extractor_source_ready(building):
        return False
    if int(getattr(building, "source_qty", 0) or 0) > 0:
        return True
    return depleted_production_qty_of(building) > 0


def depleted_production_qty_of(building):
    return int(getattr(type(building), "depleted_production_qty", 0) or 0)


def gather_slots_of(target):
    """Max concurrent workers extracting from target; 0 = unlimited."""
    n = getattr(target, "gather_slots", None)
    if n is None:
        n = getattr(type(target), "gather_slots", 0)
    try:
        return int(n or 0)
    except (TypeError, ValueError):
        return 0


def worker_holds_gather_slot(unit, target):
    """True while the worker is actively extracting (occupies a gather slot)."""
    if unit is None or target is None:
        return False
    orders = getattr(unit, "orders", None) or []
    if not orders:
        return False
    order = orders[0]
    if getattr(order, "keyword", None) != "gather":
        return False
    if getattr(order, "target", None) is not target:
        return False
    return getattr(order, "mode", None) == "gather"


def count_gather_slot_holders(target, exclude=None):
    """How many workers currently occupy gather slots on ``target``."""
    if target is None:
        return 0
    place = getattr(target, "place", None)
    world = getattr(place, "world", None) if place is not None else None
    if world is None:
        world = getattr(target, "world", None)
    if world is None:
        return 0
    n = 0
    for player in getattr(world, "players", ()) or ():
        for unit in getattr(player, "units", ()) or ():
            if unit is exclude:
                continue
            if worker_holds_gather_slot(unit, target):
                n += 1
    return n


def gather_slot_available(target, unit=None):
    """True if ``unit`` may start extracting now (unlimited or free slot)."""
    slots = gather_slots_of(target)
    if slots <= 0:
        return True
    return count_gather_slot_holders(target, exclude=unit) < slots


def count_workers_assigned_to_gather_target(target, exclude=None):
    """Workers with an active gather order aimed at ``target`` (any mode)."""
    if target is None:
        return 0
    place = getattr(target, "place", None)
    world = getattr(place, "world", None) if place is not None else None
    if world is None:
        world = getattr(target, "world", None)
    if world is None:
        return 0
    n = 0
    for player in getattr(world, "players", ()) or ():
        for unit in getattr(player, "units", ()) or ():
            if unit is exclude:
                continue
            orders = getattr(unit, "orders", None) or []
            if not orders:
                continue
            order = orders[0]
            if getattr(order, "keyword", None) != "gather":
                continue
            if getattr(order, "target", None) is target:
                n += 1
    return n


def gather_target_wants_more_workers(target, unit=None):
    """AI helper: respect gather_slots when assigning workers to a target."""
    slots = gather_slots_of(target)
    if slots <= 0:
        return True
    return count_workers_assigned_to_gather_target(target, exclude=unit) < slots


def effective_resource_volume_max(building):
    """Buffer cap; when the source is depleted, shrink to one depleted trip."""
    base = int(getattr(building, "resource_volume_max", 0) or 0)
    if not is_extractor_source_depleted(building):
        return base
    depleted = depleted_production_qty_of(building)
    if depleted > 0:
        return depleted
    return base


def base_production_qty_for(building):
    """Class production_qty, or depleted rate when the source is empty."""
    unit_class = type(building)
    if is_extractor_source_depleted(building):
        return depleted_production_qty_of(building)
    return int(getattr(unit_class, "production_qty", 0) or 0)


def apply_extractor_production(building, requested_qty):
    """Debit the source reserve and return the actual display qty to produce.

    When the reserve is empty, returns ``depleted_production_qty`` (may be 0).
    """
    if not extractor_source_ready(building):
        return requested_qty

    source = int(getattr(building, "source_qty", 0) or 0)
    if source > 0:
        actual = min(max(0, int(requested_qty)), source)
        building.source_qty = source - actual
        building.notify(f"source_qty_update,{building.source_qty}")
        if building.source_qty <= 0:
            building.source_qty = 0
            building.notify("source_depleted")
            depleted = depleted_production_qty_of(building)
            building.production_qty = depleted
            vol = effective_resource_volume_max(building)
            if vol > 0 and getattr(building, "resource_qty", 0) > vol:
                building.resource_qty = vol
                building.notify(f"qty_update,{building.resource_qty}")
        return actual

    return depleted_production_qty_of(building)
