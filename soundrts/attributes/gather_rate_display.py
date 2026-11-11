# -*- coding: utf-8 -*-
"""Effective (tech-adjusted) gathering rates for the attributes screen.

The attributes screen used to show the *raw* rules value of
``gather_rate_<deposit>`` (e.g. 0.38 gold/second), so it kept claiming
0.38 even after the player had researched Gold Mining, which actually
makes the villager ~15% faster.  This module computes the rate the unit
really achieves, using the very same bonus resolution as the live
simulation (``soundrts.gather_rate``).

The player is taken from the unit view: a live unit carries
``u.model.player`` (the real player object), while a *type detail* proxy
(``soundrts.attributes.unit_detail.TempUnit``) carries ``u.player``.  When no
player can be found the unmodified rules value is returned, so the screen
still works outside a running game (unit browser, tests).
"""

from __future__ import annotations

from .. import gather_rate as gather_rate_mod


def _player_for(unit_view):
    """Best-effort player lookup for a unit view / detail proxy."""
    model = getattr(unit_view, "model", None)
    for candidate in (model, unit_view):
        player = getattr(candidate, "player", None)
        if player is not None:
            return player
    return None


def _resource_type_for(deposit_type):
    """The ``resourceN`` a deposit type yields (e.g. ``goldmine``→resource1)."""
    from ..definitions import rules

    cls = rules.unit_class(deposit_type)
    if cls is None:
        return None
    resource_type = getattr(cls, "resource_type", None)
    if isinstance(resource_type, (list, tuple)):
        resource_type = resource_type[0] if resource_type else None
    if not resource_type:
        return None
    return str(resource_type)


def effective_rate(unit_view, deposit_type):
    """Return the unit's effective per-second rate for *deposit_type*.

    ``None`` is returned when the unit has no explicit rate for that
    deposit (the caller then falls back to the plain rules value).
    """
    model = getattr(unit_view, "model", unit_view)
    base = gather_rate_mod.base_gather_rate(model, deposit_type)
    if base is None:
        return None

    player = _player_for(unit_view)
    if player is None:
        return base

    bonus = gather_rate_mod.player_gather_bonus(player, "time")
    resource_type = _resource_type_for(deposit_type)
    factor = gather_rate_mod.rate_bonus_factor(
        bonus, deposit_type, resource_type
    )
    if factor is None:
        return base
    return max(0.01, base * factor)


def effective_rates(unit_view):
    """Map every ``gather_rate_<deposit>`` of the unit to its effective rate.

    Only deposits whose rate actually changed are included, so callers can
    tell "unchanged" (no entry) from "changed" (entry present).
    """
    model = getattr(unit_view, "model", unit_view)
    player = _player_for(unit_view)
    if player is None:
        return {}

    bonus = gather_rate_mod.player_gather_bonus(player, "time")
    if not bonus:
        return {}

    result = {}
    for attr_name in dir(model):
        if not attr_name.startswith("gather_rate_"):
            continue
        deposit_type = attr_name[len("gather_rate_"):]
        base = gather_rate_mod.base_gather_rate(model, deposit_type)
        if base is None:
            continue
        resource_type = _resource_type_for(deposit_type)
        factor = gather_rate_mod.rate_bonus_factor(
            bonus, deposit_type, resource_type
        )
        if factor is None:
            continue
        rate = max(0.01, base * factor)
        if abs(rate - base) > 1e-9:
            result[deposit_type] = rate
    return result
