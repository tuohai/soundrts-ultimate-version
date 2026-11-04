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

The bonus itself is *declarative*: the techs carry a normal effect row

    effect bonus resource_volume_max 75
    effect_bonus_targets farm

and the farm no longer has to list them in ``can_use_tech``: a filtered
``effect bonus`` row's ``effect_bonus_targets farm`` list *is* the
authorisation (the universal target-as-authorisation model).  The engine
therefore has to

* grow the farm's **capacity** (``resource_volume_max``) by the *full*
  bonus — 175 -> 250 for Horse Collar — and
* top up the **stored** food by the DE-proportional amount.
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
    (where it is set in ``Building.__init__``).  ``resource_volume_max`` is
    a *class* attribute, mirroring the engine too: the pristine capacity
    lives on the rules class, and the instance value is what the tech
    bonuses are folded into.
    """

    type_name = "farm"
    expanded_is_a = frozenset({"farm", "building"})
    cls = SimpleNamespace(__name__="building")
    resource_volume_max = 175
    resource_volume_start = 175
    production_qty = 175

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
    """The farm food bonus declared by a tech's effect rows."""
    from soundrts.world_build_rules import _tech_farm_food_bonus

    return _tech_farm_food_bonus(rules.unit_class(tech_name))


def test_mill_techs_declare_farm_food_bonus(aoe2_rules):
    assert _bonus_of(aoe2_rules, "horse_collar") == 75
    assert _bonus_of(aoe2_rules, "heavy_plow") == 125
    assert _bonus_of(aoe2_rules, "crop_rotation") == 175


def test_farm_does_not_need_to_repeat_the_mill_techs(aoe2_rules):
    """The techs authorise themselves through ``effect_bonus_targets``.

    The farm therefore must *not* list 马轭/重犁/轮作 in ``can_use_tech``:
    the tech's own ``effect_bonus_targets farm`` list is the authorisation
    (the universal target-as-authorisation model).
    """
    farm = aoe2_rules.unit_class("farm")
    can_use_tech = tuple(getattr(farm, "can_use_tech", ()))
    for tech_name in ("horse_collar", "heavy_plow", "crop_rotation"):
        assert tech_name not in can_use_tech, tech_name


def test_mill_techs_need_no_opt_in_flag(aoe2_rules):
    """The universal model has no opt-in flag any more.

    The engine used to require ``effect_bonus_targets_are_authorization 1``
    on every tech whose target list was to act as the authorisation.  That
    flag is gone; the target list alone authorises.
    """
    for tech_name in ("horse_collar", "heavy_plow", "crop_rotation"):
        cls = aoe2_rules.unit_class(tech_name)
        assert not hasattr(cls, "effect_bonus_targets_are_authorization"), (
            tech_name
        )


def test_self_authorisation_lets_the_farm_receive_the_bonus(
    installed_rules, aoe2_rules
):
    """Without ``can_use_tech`` the row must still reach the farm.

    This is the regression test for the double-gate problem: the farm does
    not list the tech, yet the tech's ``effect_bonus_targets farm`` grants
    the capacity bonus.
    """
    from soundrts.worldupgrade.effect_bonus_parse import unit_matches_tech_targets

    farm = FakeFarm(FakePlayer())
    tech = aoe2_rules.unit_class("horse_collar")
    # The authorisation comes from the target list alone.
    assert unit_matches_tech_targets(farm, tech)
    assert tech._unit_authorised(farm)


def test_mill_techs_use_the_declarative_effect_row(aoe2_rules):
    """The bonus must be a plain ``effect bonus`` row, not a custom field."""
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    for tech_name, expected in (
        ("horse_collar", 75),
        ("heavy_plow", 125),
        ("crop_rotation", 175),
    ):
        cls = aoe2_rules.unit_class(tech_name)
        effect = getattr(cls, "effect", None)
        assert effect, tech_name
        rows = (
            effect
            if isinstance(effect, list) and effect and isinstance(effect[0], list)
            else [effect]
        )
        found = False
        for row in rows:
            bonus_tokens, targets = split_effect_bonus_args(list(row[1:]))
            if "farm" not in targets:
                continue
            tokens = list(bonus_tokens)
            for i in range(0, len(tokens) - 1, 2):
                if tokens[i] == "resource_volume_max":
                    assert int(float(tokens[i + 1])) == expected
                    found = True
        assert found, "%s declares no farm capacity bonus" % tech_name


def test_existing_full_farm_gains_full_bonus(installed_rules):
    """A farm at full capacity gains the complete bonus."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=175)

    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == 175 + 75
    assert farm.resource_qty == 175 + 75
    assert farm.production_qty == 175 + 75


def test_existing_half_full_farm_keeps_full_capacity(installed_rules):
    """The *limit* must be base + full bonus, never "current + bonus".

    Regression test for the reported bug: a farm holding 105 food showed
    ``105/180`` after Horse Collar instead of ``105/250``.
    """
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    farm = FakeFarm(player, qty=105)

    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == 250
    # DE: the stored food grows by 75 * (105/175) ** 2 == 27
    assert farm.resource_qty == 105 + 27


def test_existing_half_full_farm_gains_quarter_bonus(installed_rules):
    """DE: the granted amount scales with the square of the fill ratio."""
    from soundrts.world_build_rules import _apply_farm_food_tech_bonuses

    player = FakePlayer(upgrades=["horse_collar"])
    # 50% of 175 == 87 (int), fill == 87/175 -> square -> ~24% of 75 == 18
    farm = FakeFarm(player, qty=87)

    _apply_farm_food_tech_bonuses(farm)

    granted = farm.resource_qty - 87
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
    qty_once = farm.resource_qty
    _apply_farm_food_tech_bonuses(farm)

    assert farm.resource_volume_max == once == 250
    assert farm.resource_qty == qty_once == 250


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


def test_upgrade_player_grows_capacity_of_partially_filled_farm(
    installed_rules, aoe2_rules
):
    """The reported scenario: 105/175 must become 105/250 after the tech."""
    from soundrts.worldupgrade import Upgrade

    player = FakePlayer()
    farm = FakeFarm(player, qty=105)
    player.units.append(farm)

    tech_cls = aoe2_rules.unit_class("horse_collar")
    assert issubclass(tech_cls, Upgrade)

    tech_cls.upgrade_player(player)

    assert farm.resource_volume_max == 250
    assert farm.resource_qty == 132  # 105 + 27


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
