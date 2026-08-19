"""Faction age cost discounts are rules-driven (no civ-name hardcoding)."""
from __future__ import annotations

from soundrts.definitions import Rules, MAX_NB_OF_RESOURCE_TYPES
from soundrts.worldorders.base import ComplexOrder
from soundrts.worldphase import (
    advance_cost_percent_for_age,
    refresh_faction_research_cost_discount,
)


def _load_discount_rules():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4

def feudal_age
class phase
cost 0 0 500 0

def castle_age
class phase
cost 200 0 800 0

def imperial_age
class phase
cost 800 0 1000 0

def sample_tech
class upgrade
cost 100 0 50 0

def any_named_civ
class race
research_cost_discount feudal_age -10% castle_age -15% imperial_age -20%

def another_civ
class race
advance_cost_discount imperial_age -33%
"""
    )
    return r


def test_research_discount_follows_rules_not_civ_name():
    r = _load_discount_rules()
    from soundrts.definitions import rules as global_rules

    saved = global_rules._dict
    global_rules._dict = r._dict
    try:
        class P:
            faction = "any_named_civ"
            upgrades = ["feudal_age"]
            research_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            research_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES

        p = P()
        refresh_faction_research_cost_discount(p)
        assert abs(p.research_cost_percent_bonus[0] - (-0.10)) < 1e-9

        p.upgrades = ["feudal_age", "castle_age"]
        refresh_faction_research_cost_discount(p)
        assert abs(p.research_cost_percent_bonus[0] - (-0.15)) < 1e-9

        p.upgrades = ["feudal_age", "castle_age", "imperial_age"]
        refresh_faction_research_cost_discount(p)
        assert abs(p.research_cost_percent_bonus[0] - (-0.20)) < 1e-9

        cost = [100, 0, 50, 0]
        ComplexOrder._merge_research_resource_cost(p, cost)
        assert cost == [80, 0, 40, 0]
    finally:
        global_rules._dict = saved


def test_advance_discount_is_per_purchased_age():
    r = _load_discount_rules()
    from soundrts.definitions import rules as global_rules

    saved = global_rules._dict
    global_rules._dict = r._dict
    try:
        class P:
            faction = "another_civ"
            upgrades = ["castle_age"]

        p = P()
        assert abs(advance_cost_percent_for_age(p, "imperial_age") - (-0.33)) < 1e-9
        assert advance_cost_percent_for_age(p, "feudal_age") == 0.0

        cost = [800, 0, 1000, 0]
        ComplexOrder._merge_advance_resource_cost(p, cost, "imperial_age")
        assert cost == [536, 0, 670, 0]  # -33%
    finally:
        global_rules._dict = saved


def test_aoe2_chinese_and_byzantine_tables():
    from pathlib import Path

    if not Path("mods/aoe2/rules.txt").is_file():
        return
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
        from soundrts.lib.resource import res

        config.mods = "aoe2"
        res.set_mods("aoe2")
        res.load_rules_and_ai()
        from soundrts.definitions import rules

    sys.argv = saved
    cn = rules.get("chinese", "research_cost_discount")
    assert cn and "feudal_age" in cn and "-5%" in cn
    assert "imperial_age" in cn and "-15%" in cn
    byz = rules.get("byzantines", "advance_cost_discount")
    assert byz and "imperial_age" in byz and "-33%" in byz
