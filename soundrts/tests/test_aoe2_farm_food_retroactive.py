# -*- coding: utf-8 -*-
"""AoE2 DE: farm mill techs must also boost farms that already exist.

DE wording (Horse Collar / Heavy Plow / Crop Rotation):
    "New Farms provide +75 food.  Existing Farms provide a smaller food
    amount."

and the Wiki formula for the existing-farm part:

    added = bonus * (remaining_food / capacity) ** 2

So a farm that is still full gains the *full* bonus, an almost empty farm
gains almost nothing, and a farm built after the research gets the full
bonus as well.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    return r


@pytest.fixture
def installed_rules(aoe2_rules):
    """Install the AoE2 rules into the global registry.

    The farm code resolves techs through ``definitions.rules`` (the global
    registry), so the AoE2 rule set has to be visible there for the lookup
    to succeed.  The previous content is restored afterwards.
    """
    from soundrts.definitions import rules as global_rules

    original_dict = global_rules._dict
    original_classes = getattr(global_rules, "classes", {})
    try:
        global_rules._dict.update(aoe2_rules._dict)
        global_rules.classes.update(aoe2_rules.classes)
        global_rules.apply_inheritance(expanded_is_a=True)
        yield global_rules
    finally:
        global_rules._dict.clear()
        global_rules._dict.update(original_dict)
        global_rules.classes.clear()
        global_rules.classes.update(original_classes)
        global_rules.apply_inheritance(expanded_is_a=True)


class FakePlayer:
    """Minimal stand-in for a player: only what the farm code touches."""

    def __init__(self, upgrades=()):
        self.upgrades = list(upgrades)
        self.units = []
        self.faction = "britons"
        self.allied_victory = (self,)

    def level(self, tech_name):
        return 1 if tech_name in self.upgrades else 0


class FakeFarm:
    """Stand-in for a farm building instance.

    ``resource_qty`` is an *instance* attribute here, mirroring the engine
    (where it is set in ``Building.__init__``).
    """

    type_name = "farm"
    expanded_is_a = frozenset({"farm", "building"})
    cls = SimpleNamespace(__name__="building")

    def __init__(self, player, qty=175, capacity=175, production=175):
        self.player = player
        self.resource_qty = qty
        self.resource_volume_max = capacity
        self.resource_volume_start = capacity
        self.production_qty = production
        self.auto_cultivate = 1
        self.is_gather = 1
        self.notifications = []

    def notify(self, msg):
        self.notifications.append(msg)


def _bonus_of(rules, tech_name):
    cls = rules.unit_class(tech_name)
    return int(getattr(cls, "farm_food_bonus", 0) or 0)


def test_mill_techs_declare_farm_food_bonus(aoe2_rules):
    assert _bonus_of(aoe2_rules, "horse_collar") == 75
    assert _bonus_of(aoe2_rules, "heavy_plow") == 125
    assert _bonus_of(aoe2_rules, "crop_rotation") == 175


def test_existing_full_farm_gains_full_bonus(installed_rules):
    """A farm at full capacity gains the complete bonus."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=175)

    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == 175 + 75
    assert farm.resource_qty == 175 + 75
    assert farm.production_qty == 175 + 75


def test_existing_half_full_farm_gains_quarter_bonus(installed_rules):
    """DE: the granted amount scales with the square of the fill ratio."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    # 50% of 175 == 87 (int), fill == 87/175 -> square -> ~24% of 75 == 18
    farm = FakeFarm(player, qty=87)

    _apply_farm_food_tech_bonuses(farm)

    granted = farm.resource_volume_max - 175
    assert 15 <= granted <= 20, granted


def test_existing_empty_farm_gets_no_bonus_now_but_larger_capacity(installed_rules):
    """An empty farm gains no food now, but its capacity still grows."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=0)

    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_qty == 0
    assert farm.resource_volume_max == 175 + 75


def test_applying_twice_does_not_double_count(installed_rules):
    """The refresh must be idempotent."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=175)

    _apply_farm_food_tech_bonuses(farm)
    once = farm.resource_volume_max
    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == once == 250


def test_second_tech_adds_only_the_difference(installed_rules):
    """Heavy Plow on a farm that already got Horse Collar adds 125, not 200."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=175)
    _apply_farm_food_tech_bonuses(farm)
    assert farm.resource_volume_max == 250

    player.upgrades.append("heavy_plow")
    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == 375
    assert farm.production_qty == 375


def test_upgrade_player_refreshes_existing_farms(installed_rules, aoe2_rules):
    """Researching Horse Collar must reach the farms that already stand."""
    from soundrts.worldupgrade import Upgrade

    player = FakePlayer()
    farm = FakeFarm(player, qty=175)
    player.units.append(farm)

    tech_cls = aoe2_rules.unit_class("horse_collar")
    assert issubclass(tech_cls, Upgrade)

    tech_cls.upgrade_player(player)

    assert "horse_collar" in player.upgrades
    assert farm.resource_volume_max == 250
    assert farm.resource_qty == 250
    assert farm.production_qty == 250


def test_new_farm_after_research_gets_full_bonus(installed_rules):
    """A farm built after the research starts out with the bigger capacity."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    # ``finalize_new_building`` runs before the initial fill, so the
    # instance has no own ``resource_qty`` yet.
    farm = FakeFarm.__new__(FakeFarm)
    farm.player = player
    farm.resource_volume_max = 175
    farm.resource_volume_start = 175
    farm.production_qty = 175
    farm.auto_cultivate = 1
    farm.is_gather = 1

    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == 250
    assert farm.production_qty == 250
    assert farm.resource_volume_start == 250


def test_farm_yield_survives_production_cycle(installed_rules):
    """The bonus must not be wiped when the farm restarts production.

    ``production_qty`` is recomputed from the class value at every production
    cycle; the farm bonus has to be added back there (see
    ``world_extractor.base_production_qty_for``).
    """
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses
    from soundrts.world_extractor import base_production_qty_for

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=175)

    _apply_farm_food_tech_bonuses(farm)
    assert farm.production_qty == 250

    # Simulate the production cycle resetting the instance value.
    farm.production_qty = 175
    assert base_production_qty_for(farm) == 250
