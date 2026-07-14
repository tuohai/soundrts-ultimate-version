"""Attribute-screen helpers: apply current-square terrain modifiers to displayed stats."""

from __future__ import annotations

from ..lib.nofloat import to_int
from ..lib.square_terrain_rules import (
    terrain_list_stat_percent_delta,
    terrain_list_value,
    terrain_unit_speed_percent,
    terrain_unit_stat_percent_delta,
)

# Terrain class ``*_vs`` → unit stat shown on the attributes screen.
ATTR_TERRAIN_VS = {
    "mdg": "mdg_vs",
    "rdg": "rdg_vs",
    "mdg_cd": "mdg_cd_vs",
    "rdg_cd": "rdg_cd_vs",
}

# Unit ``*_on_terrain`` / ``charge_*_terrain`` lists.
ATTR_ON_TERRAIN = {
    "mdg": "mdg_on_terrain",
    "rdg": "rdg_on_terrain",
    "mdg_cd": "mdg_cd_on_terrain",
    "rdg_cd": "rdg_cd_on_terrain",
    "charge_mdg": "charge_mdg_terrain",
    "charge_rdg": "charge_rdg_terrain",
    "charge_mdg_cd": "charge_mdg_cd_on_terrain",
    "charge_rdg_cd": "charge_rdg_cd_on_terrain",
}


def world_unit(u):
    """Prefer the world creature behind an EntityView; otherwise *u* itself."""
    model = getattr(u, "model", None)
    if model is not None and not isinstance(model, type):
        # EntityView.model is the live world unit; class-detail screens use types.
        if hasattr(model, "place") or hasattr(model, "type_name"):
            return model
    return u


def current_terrain_type(u):
    """Terrain type name under *u*, or None if unknown / no place."""
    unit = world_unit(u)
    place = getattr(unit, "place", None) or getattr(u, "place", None)
    if not place:
        return None
    x = getattr(unit, "x", None)
    if x is None:
        x = getattr(u, "x", None)
    y = getattr(unit, "y", None)
    if y is None:
        y = getattr(u, "y", None)
    if hasattr(place, "type_name_at") and x is not None and y is not None:
        return place.type_name_at(x, y)
    return getattr(place, "type_name", None)


def _unit_attr_list(u, unit, attr_name):
    terrain_list = getattr(unit, attr_name, None)
    if not terrain_list and unit is not u:
        terrain_list = getattr(u, attr_name, None)
    if not terrain_list:
        model = getattr(u, "model", None)
        if model is not None:
            terrain_list = getattr(model, attr_name, None)
    return terrain_list or ()


def terrain_delta_for_attr(u, base_attr, base_value):
    """Percent-of-base delta from terrain ``*_vs`` and unit ``*_on_terrain``."""
    if not base_value:
        return 0
    terrain = current_terrain_type(u)
    if not terrain:
        return 0
    unit = world_unit(u)
    delta = 0
    prop = ATTR_TERRAIN_VS.get(base_attr)
    if prop:
        delta += terrain_unit_stat_percent_delta(terrain, unit, base_value, prop)
    on_name = ATTR_ON_TERRAIN.get(base_attr)
    if on_name:
        delta += terrain_list_stat_percent_delta(
            terrain, _unit_attr_list(u, unit, on_name), base_value
        )
    return delta


def effective_stat_value(u, base_attr, base_value):
    """Base combat/stat value plus current-square terrain modifiers (floored at 0)."""
    if not base_value:
        return base_value
    return max(0, base_value + terrain_delta_for_attr(u, base_attr, base_value))


def _square_speed_for_unit(u, unit):
    place = getattr(unit, "place", None) or getattr(u, "place", None)
    if place is None:
        return None
    x = getattr(unit, "x", None)
    if x is None:
        x = getattr(u, "x", None)
    y = getattr(unit, "y", None)
    if y is None:
        y = getattr(u, "y", None)
    if hasattr(place, "terrain_speed_at") and x is not None and y is not None:
        return place.terrain_speed_at(x, y)
    return getattr(place, "terrain_speed", None)


def effective_speed_value(u, base_speed):
    """Speed shown on attributes: matches ``move_to`` terrain rules.

    Priority:
    1. Unit ``speed_on_terrain`` absolute override for the current square
    2. Else ``base * terrain_unit_speed_percent`` (terrain ``speed_vs`` /
       square ``speed`` / terrain default)
    """
    if not base_speed:
        return base_speed
    terrain = current_terrain_type(u)
    if not terrain:
        return base_speed
    unit = world_unit(u)
    override = terrain_list_value(terrain, _unit_attr_list(u, unit, "speed_on_terrain"))
    if override is not None:
        try:
            if isinstance(override, str):
                return to_int(override)
            return int(override)
        except (TypeError, ValueError, AssertionError):
            return base_speed
    pcts = terrain_unit_speed_percent(terrain, unit, _square_speed_for_unit(u, unit))
    terrain_type = 0 if getattr(unit, "airground_type", None) == "ground" else 1
    if terrain_type < len(pcts):
        return base_speed * pcts[terrain_type] // 100
    return base_speed
