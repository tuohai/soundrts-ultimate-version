# -*- coding: utf-8 -*-
"""Smoke tests for dock fish trap / trade cog / shipwright wiring."""
from __future__ import annotations

from pathlib import Path


def test_trade_hub_helpers():
    from soundrts.worldmarket import is_dock_building, is_trade_hub_for

    class O:
        pass

    dock = O()
    dock.is_dock = 1
    dock.type_name = "shipyard"
    market = O()
    market.is_market = 1
    market.type_name = "market"
    cog = O()
    cog.type_name = "trade_cog"
    cog.is_trade_unit = 1
    cog.airground_type = "water"
    cog.trade_hubs = ("is_dock", "shipyard")
    cart = O()
    cart.type_name = "trade_cart"
    cart.is_trade_unit = 1
    cart.trade_hubs = ("market",)

    assert is_dock_building(dock)
    assert is_trade_hub_for(cog, dock)
    assert not is_trade_hub_for(cog, market)
    assert is_trade_hub_for(cart, market)
    assert not is_trade_hub_for(cart, dock)


def test_aoe2_dock_economy_rules():
    text = (
        Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    ).read_text(encoding="utf-8")
    for s in (
        "def fish_trap",
        "def gillnets",
        "def trade_cog",
        "def shipwright",
        "is_dock 1",
        "can_train fishing_ship trade_cog",
        "can_research gillnets shipwright",
        "can_build fish_trap",
        "gather_time_fish_trap -20%",
        "resource_volume_max 715",
    ):
        assert s in text, s


def test_creature_has_is_dock():
    from soundrts.worldunit.worldcreature import Creature

    assert hasattr(Creature, "is_dock")


def test_aoe2_fish_trap_keeps_sight_range_1():
    """Legacy tower shorthand must not rewrite intentional LOS 1."""
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    saved = sys.argv
    sys.argv = [saved[0] if saved else "pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts import config
        from soundrts.definitions import PRECISION, rules
        from soundrts.lib.resource import res

    sys.argv = saved
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    try:
        ft = rules.unit_class("fish_trap")
        assert ft is not None
        assert ft.sight_range == 1 * PRECISION
        assert not getattr(ft, "bonus_height", 0)
    finally:
        config.mods = old
        res.set_mods(old or "")
        if old:
            res.load_rules_and_ai()
