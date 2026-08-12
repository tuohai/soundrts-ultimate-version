"""Rules-driven conversion tech flags (no upgrade type-name hardcoding).

Upgrade attributes (on ``class upgrade``)::

    conversion_allows_monk 1
    conversion_allows_siege 1
    conversion_allows_building 1
    conversion_victim_dies 1
    conversion_rest_only_success 1
    conversion_channel_scale_num 5
    conversion_channel_scale_den 3
    conversion_channel_bonus_pct 67
    conversion_channel_bonus_time 2

Unit / skill attributes::

    conversion_tech_gated 1   — apply allow-/rest-/channel rules from researched upgrades
    conversion_cleric 1       — target needs ``conversion_allows_monk`` when caster is gated
    conversion_immune 1       — building never convertible (even with allows_building)
"""

from __future__ import annotations

from .definitions import rules
from .lib.nofloat import PRECISION


def _as_int(val, default=0):
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def player_upgrade_attr_max(player, attr, default=0):
    """Largest integer ``attr`` among the player's researched upgrade classes."""
    best = _as_int(default, 0)
    if player is None:
        return best
    for name in getattr(player, "upgrades", ()) or ():
        cls = rules.unit_class(name)
        if cls is None:
            continue
        val = getattr(cls, attr, None)
        if val is None:
            continue
        v = _as_int(val, None)
        if v is None:
            continue
        if v > best:
            best = v
    return best


def player_has_upgrade_flag(player, attr):
    return player_upgrade_attr_max(player, attr, 0) > 0


def unit_or_type_flag(unit, attr):
    """True if the unit instance or its type / ``expanded_is_a`` parents set ``attr``."""
    if unit is None:
        return False
    if _as_int(getattr(unit, attr, 0), 0) > 0:
        return True
    tn = getattr(unit, "type_name", None)
    names = []
    if tn:
        names.append(tn)
    names.extend(getattr(unit, "expanded_is_a", ()) or ())
    for name in names:
        cls = rules.unit_class(name)
        if cls is not None and _as_int(getattr(cls, attr, 0), 0) > 0:
            return True
    return False


def is_conversion_tech_gated(unit):
    """Caster uses researched conversion allow/rest rules (AoE2 monk style)."""
    return unit_or_type_flag(unit, "conversion_tech_gated")


def is_conversion_cleric(unit):
    return unit_or_type_flag(unit, "conversion_cleric")


def is_conversion_immune(unit):
    return unit_or_type_flag(unit, "conversion_immune")


def apply_conversion_channel_resist(base, player):
    """Lengthen channel from the target owner's researched resist upgrades."""
    base = int(base or 0)
    if player is None:
        return max(base, PRECISION)
    num = player_upgrade_attr_max(player, "conversion_channel_scale_num", 0)
    den = player_upgrade_attr_max(player, "conversion_channel_scale_den", 0)
    if num > 0 and den > 0:
        base = base * num // den
    pct = player_upgrade_attr_max(player, "conversion_channel_bonus_pct", 0)
    if pct:
        base = base * (100 + pct) // 100
    add = player_upgrade_attr_max(player, "conversion_channel_bonus_time", 0)
    if add:
        base = base + add
    return max(int(base), PRECISION)
