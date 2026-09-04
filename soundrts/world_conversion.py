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
    conversion_min_intervals_bonus 4
    conversion_max_intervals_bonus 4
    conversion_resist 2

Unit / skill attributes::

    conversion_tech_gated 1   — apply allow-/rest-/channel rules from researched upgrades
    conversion_cleric 1       — target needs ``conversion_allows_monk`` when caster is gated
    conversion_immune 1       — building never convertible (even with allows_building)
    conversion_interval 1.25  — seconds per conversion interval (0 = old always-succeed channel)
    conversion_min_intervals 5
    conversion_max_intervals 9
    conversion_chance 38      — percent per interval after min (0 = only succeed at max)
    conversion_resist 2       — chance // max(1, resist)
    conversion_fail_at_max 1  — last interval can fail the whole attempt (default 0 = guaranteed)

Race team::

    team_conversion_min_intervals_bonus 3
    team_conversion_max_intervals_bonus 1
"""

from __future__ import annotations

from typing import NamedTuple, Optional

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


class ConversionRollParams(NamedTuple):
    interval: int
    min_ci: int
    max_ci: int
    chance: int
    fail_at_max: bool


def unit_or_type_int(unit, attr, default=0):
    """Largest integer ``attr`` on the instance, its type, or ``expanded_is_a`` parents."""
    best = _as_int(default, 0)
    if unit is None:
        return best
    v = _as_int(getattr(unit, attr, None), None)
    if v is not None and v > best:
        best = v
    tn = getattr(unit, "type_name", None)
    names = []
    if tn:
        names.append(tn)
    names.extend(getattr(unit, "expanded_is_a", ()) or ())
    for name in names:
        cls = rules.unit_class(name)
        if cls is None:
            continue
        cv = _as_int(getattr(cls, attr, None), None)
        if cv is not None and cv > best:
            best = cv
    return best


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
    try:
        from .world_civ_bonuses import team_conversion_channel_bonus_pct

        pct = max(pct, team_conversion_channel_bonus_pct(player))
    except Exception:
        pass
    if pct:
        base = base * (100 + pct) // 100
    add = player_upgrade_attr_max(player, "conversion_channel_bonus_time", 0)
    if add:
        base = base + add
    return max(int(base), PRECISION)


def _positive_or(value, fallback):
    v = _as_int(value, 0)
    return v if v > 0 else fallback


def conversion_roll_params(caster, target, skill_cls) -> Optional[ConversionRollParams]:
    """Interval-roll conversion (AoE2 DE style), or None for the old fixed channel."""
    interval = 0
    if skill_cls is not None:
        interval = _as_int(getattr(skill_cls, "conversion_interval", 0), 0)
    if interval <= 0:
        interval = unit_or_type_int(caster, "conversion_interval", 0)
    if interval <= 0:
        return None

    skill_min = _as_int(getattr(skill_cls, "conversion_min_intervals", 0), 0) if skill_cls else 0
    skill_max = _as_int(getattr(skill_cls, "conversion_max_intervals", 0), 0) if skill_cls else 0
    skill_chance = _as_int(getattr(skill_cls, "conversion_chance", 0), 0) if skill_cls else 0
    fail_at_max = False
    if skill_cls is not None:
        fail_at_max = _as_int(getattr(skill_cls, "conversion_fail_at_max", 0), 0) > 0
    if not fail_at_max:
        fail_at_max = unit_or_type_flag(caster, "conversion_fail_at_max")

    min_ci = _positive_or(unit_or_type_int(target, "conversion_min_intervals", 0), skill_min)
    max_ci = _positive_or(unit_or_type_int(target, "conversion_max_intervals", 0), skill_max)
    chance = _positive_or(unit_or_type_int(target, "conversion_chance", 0), skill_chance)
    if min_ci <= 0:
        min_ci = 1
    if max_ci < min_ci:
        max_ci = min_ci

    enemy = getattr(target, "player", None)
    min_ci += player_upgrade_attr_max(enemy, "conversion_min_intervals_bonus", 0)
    max_ci += player_upgrade_attr_max(enemy, "conversion_max_intervals_bonus", 0)
    try:
        from .world_civ_bonuses import (
            team_conversion_max_intervals_bonus,
            team_conversion_min_intervals_bonus,
        )

        min_ci += team_conversion_min_intervals_bonus(enemy)
        max_ci += team_conversion_max_intervals_bonus(enemy)
    except Exception:
        pass
    if max_ci < min_ci:
        max_ci = min_ci

    resist = unit_or_type_int(target, "conversion_resist", 0)
    resist = max(resist, player_upgrade_attr_max(enemy, "conversion_resist", 0))
    if resist > 1:
        chance = chance // resist
    chance = max(0, min(100, chance))
    return ConversionRollParams(interval, min_ci, max_ci, chance, fail_at_max)


def conversion_roll_after_interval(params: ConversionRollParams, ci, rng):
    """Result after finishing 1-based interval *ci*: warmup, success, miss, or fail."""
    if params is None or ci < int(params.min_ci):
        return "warmup"
    if (not params.fail_at_max) and ci >= int(params.max_ci):
        return "success"
    chance = max(0, min(100, int(params.chance)))
    if chance >= 100:
        return "success"
    if chance <= 0:
        if params.fail_at_max and ci >= int(params.max_ci):
            return "fail"
        return "miss"
    roll = 100
    if rng is not None and hasattr(rng, "randint"):
        roll = rng.randint(1, 100)
    if roll <= chance:
        return "success"
    if params.fail_at_max and ci >= int(params.max_ci):
        return "fail"
    return "miss"
