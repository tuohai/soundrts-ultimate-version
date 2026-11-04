"""AoE2 DE unique-building auras (the Caravanserai).

Rules knobs (see ``mods/aoe2/rules.txt``)::

    def caravanserai
    aura_radius 8            # radius, in TILES
    aura_heal_level 1        # HP healed per pulse (integer HP)
    aura_heal_cd 5           # SECONDS between pulses
    aura_speed_bonus_pct 20  # % speed bonus applied to the targets
    aura_target_types trade_cart

Everything is data-driven: a building opts in by declaring the ``aura_*``
rows; the engine never hardcodes a building name.

Two effects are implemented:

* a **speed aura** — every unit matching ``aura_target_types`` inside the
  radius moves ``aura_speed_bonus_pct``% faster.  Applied in
  ``ResourcesMixin._update_actual_speed`` (the authoritative per-tick speed
  computation) and re-applied in ``CreatureMovement.move_to`` (which
  recomputes ``_actual_speed`` from scratch when a new order is issued).
* a **heal pulse** — every ``aura_heal_cd`` seconds the building heals the
  matching units by ``aura_heal_level`` HP.  Driven from
  ``CreatureStatusUpdate.slow_update`` (the once-per-second tick).

Units are stored PRECISION-scaled (1 HP == ``PRECISION`` internal units),
so the heal amount is ``aura_heal_level * PRECISION``.
"""
from __future__ import annotations

from .lib.nofloat import PRECISION
from .lib.log import warning

#: Fallback tile size (engine units) when the world has no ``square_width``.
DEFAULT_TILE_UNITS = 12

#: How often the per-unit speed-aura cache is refreshed (ms).
AURA_CACHE_MS = 500


def _tile_units(world) -> int:
    """Engine units per map tile (the world's ``square_width``)."""
    sw = getattr(world, "square_width", 0) or 0
    try:
        sw = int(sw)
    except (TypeError, ValueError):
        sw = 0
    if sw <= 0:
        return DEFAULT_TILE_UNITS
    return sw


def aura_radius_mm(building) -> int:
    """Aura radius of *building* in internal distance units (mm).

    ``aura_radius`` is expressed in TILES (DE units); the engine's tile
    side is the world's ``square_width``.
    """
    tiles = int(getattr(building, "aura_radius", 0) or 0)
    if tiles <= 0:
        return 0
    world = getattr(building, "world", None)
    return tiles * _tile_units(world) * PRECISION


def aura_heal_level(building) -> int:
    return int(getattr(building, "aura_heal_level", 0) or 0)


def aura_heal_cd_ms(building) -> int:
    """Pulse interval in ms (``aura_heal_cd`` is expressed in seconds)."""
    seconds = int(getattr(building, "aura_heal_cd", 0) or 0)
    return seconds * 1000


def aura_speed_pct(building) -> int:
    return int(getattr(building, "aura_speed_bonus_pct", 0) or 0)


def aura_target_types(building):
    raw = getattr(building, "aura_target_types", ()) or ()
    if isinstance(raw, str):
        raw = raw.split()
    return tuple(str(t) for t in raw if t)


def is_aura_building(unit) -> bool:
    """True when *unit* declares an aura (``aura_radius`` > 0)."""
    if unit is None:
        return False
    return int(getattr(unit, "aura_radius", 0) or 0) > 0


def _matches_targets(unit, targets) -> bool:
    if not targets:
        return False
    from .world_build_rules import type_matches

    try:
        return type_matches(unit, targets)
    except Exception:
        return False


def _all_units(world):
    for player in list(getattr(world, "players", ()) or ()):
        for unit in list(getattr(player, "units", ()) or ()):
            yield unit


def _within(unit, cx, cy, radius_mm) -> bool:
    dx = getattr(unit, "x", 0) - cx
    dy = getattr(unit, "y", 0) - cy
    return dx * dx + dy * dy <= radius_mm * radius_mm


def _aura_buildings_near(unit):
    """Aura buildings within *unit*'s own aura radius."""
    world = getattr(unit, "world", None)
    if world is None:
        return []
    out = []
    cx = getattr(unit, "x", 0)
    cy = getattr(unit, "y", 0)
    for other in _all_units(world):
        if not is_aura_building(other):
            continue
        radius = aura_radius_mm(other)
        if radius <= 0:
            continue
        if _within(other, cx, cy, radius):
            out.append(other)
    return out


def aura_speed_bonus_pct(unit) -> int:
    """% speed bonus granted to *unit* by the auras around it.

    Several auras do not stack (DE behaviour): the strongest one wins.
    The result is cached for ``AURA_CACHE_MS`` because the movement code
    asks for it on every tick.
    """
    if unit is None:
        return 0
    world = getattr(unit, "world", None)
    if world is None:
        return 0
    now = int(getattr(world, "time", 0) or 0)
    cache = getattr(unit, "_aura_speed_cache", None)
    if cache is not None and now - cache[0] < AURA_CACHE_MS:
        return cache[1]

    pct = 0
    try:
        for building in _aura_buildings_near(unit):
            if not _matches_targets(unit, aura_target_types(building)):
                continue
            pct = max(pct, aura_speed_pct(building))
    except Exception as exc:  # pragma: no cover - defensive
        warning("aura speed bonus failed: %s", exc)
        pct = 0
    try:
        unit._aura_speed_cache = (now, pct)
    except Exception:
        pass
    return pct


def apply_speed_aura(unit) -> int:
    """Multiply the unit's current speed by the aura bonus.

    Returns the applied percentage (0 when no aura applies).
    """
    pct = aura_speed_bonus_pct(unit)
    if pct <= 0:
        return 0
    speed = int(getattr(unit, "_actual_speed", 0) or 0)
    if speed <= 0:
        return 0
    unit._actual_speed = max(1, speed * (100 + pct) // 100)
    return pct


def apply_building_aura(building) -> int:
    """Run the heal pulse of *building* (called from ``slow_update``).

    Returns the number of units healed.
    """
    if not is_aura_building(building):
        return 0
    level = aura_heal_level(building)
    if level <= 0:
        return 0
    targets = aura_target_types(building)
    if not targets:
        return 0
    radius = aura_radius_mm(building)
    if radius <= 0:
        return 0
    world = getattr(building, "world", None)
    now = int(getattr(world, "time", 0) or 0) if world is not None else 0
    next_time = int(getattr(building, "_aura_heal_next_time", 0) or 0)
    if now < next_time:
        return 0
    building._aura_heal_next_time = now + aura_heal_cd_ms(building)

    hp = level * PRECISION
    healed = 0
    cx = getattr(building, "x", 0)
    cy = getattr(building, "y", 0)
    try:
        for unit in _all_units(world):
            if unit is building:
                continue
            if not _within(unit, cx, cy, radius):
                continue
            if not _matches_targets(unit, targets):
                continue
            hp_max = int(getattr(unit, "hp_max", 0) or 0)
            hp_now = int(getattr(unit, "hp", 0) or 0)
            if hp_now <= 0 or hp_max <= 0 or hp_now >= hp_max:
                continue
            unit.hp = min(hp_max, hp_now + hp)
            healed += 1
    except Exception as exc:  # pragma: no cover - defensive
        warning("aura heal pulse failed: %s", exc)
    return healed
