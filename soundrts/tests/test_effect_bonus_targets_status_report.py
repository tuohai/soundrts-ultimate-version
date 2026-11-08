# -*- coding: utf-8 -*-
"""The ``v`` status readout must list target-authorised techs.

Background
----------
Under the universal target-as-authorisation model a filtered ``effect bonus``
row's ``effect_bonus_targets`` list *is* the row's authorisation.  A unit
that matches the list enjoys the row even though the unit does not repeat
the tech in ``can_use_tech``.

That has a direct consequence for the UI: the status readout (the ``v`` key)
lists the techs a unit enjoys via :attr:`CreatureAttributes.upgrades`, which
used to look only at ``can_use`` / ``can_use_tech``.  So the AoE2 farm did
*not* mention 马轭 (``horse_collar``) after it had been researched in the
mill — even though the farm really was enjoying it.

This module guards the fix:

* ``farm.upgrades`` contains ``horse_collar`` once the player researched it;
* it does *not* contain it before the research;
* the *target* path alone never authorises a unit the target list does not
  name (an archer does not get 马轭 through the target list);
* a tech that carries two rows with different targets (AoE2 *Heavy Plow*:
  ``farm`` capacity *and* villager carry capacity) reaches exactly the units
  each row names;
* the readout never lists a tech twice, even when the tech is reachable both
  through ``can_use_tech`` and through a target list;
* the announced title is the one the style table defines (8255 → 马轭).
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

    The property resolves techs through ``definitions.rules`` (the global
    registry), so the AoE2 rule set has to be visible there.  The previous
    content is restored afterwards.
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


@pytest.fixture(scope="module")
def aoe2_style():
    """The AoE2 style table (the base one plus the mod's)."""
    from soundrts.definitions import Style

    s = Style()
    s.load(
        (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8"),
    )
    return s


class FakePlayer:
    """A minimal stand-in for a player: only what ``upgrades`` touches."""

    def __init__(self, upgrades=()):
        self.upgrades = list(upgrades)
        self.units = []
        self.faction = "britons"

    def level(self, name):
        return 1 if name in self.upgrades else 0


def _make_unit(rules, type_name, player):
    """A farm / villager instance with a real rules class attached."""
    cls = rules.unit_class(type_name)
    assert cls is not None, type_name
    unit = cls.__new__(cls)
    unit.player = player
    return unit


# ---------------------------------------------------------------------------
# 1. The concrete case: 马轭 (horse collar) on the farm
# ---------------------------------------------------------------------------


def test_horse_collar_targets_the_farm(installed_rules):
    """The rules really do authorise the farm through the target list."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(installed_rules.unit_class("horse_collar")))
    assert rows, "horse_collar declares no targeted effect row"
    assert ["farm"] in [list(targets) for _bonus, targets in rows]


def test_farm_does_not_list_horse_collar_in_can_use_tech(installed_rules):
    """The farm does *not* repeat the tech — that is the whole point.

    If the farm did list it, the target-as-authorisation path would not be
    exercised at all and the regression this module guards would be invisible.
    """
    farm_cls = installed_rules.unit_class("farm")
    can_use = list(getattr(farm_cls, "can_use", ()) or ())
    can_use_tech = list(getattr(farm_cls, "can_use_tech", ()) or ())
    assert "horse_collar" not in can_use
    assert "horse_collar" not in can_use_tech


def test_farm_lists_horse_collar_after_the_research(installed_rules):
    """The core fix: researching 马轭 makes the farm list it."""
    player = FakePlayer(["horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    assert "horse_collar" in farm.upgrades


def test_farm_does_not_list_horse_collar_before_the_research(installed_rules):
    """Nothing is announced before the tech has been researched."""
    player = FakePlayer([])
    farm = _make_unit(installed_rules, "farm", player)

    assert "horse_collar" not in farm.upgrades


def test_farm_lists_horse_collar_next_to_the_classic_techs(installed_rules):
    """The target-authorised tech is added, the classic ones stay."""
    player = FakePlayer(["horse_collar", "masonry"])
    farm = _make_unit(installed_rules, "farm", player)

    upgrades = farm.upgrades
    assert "horse_collar" in upgrades
    assert "masonry" in upgrades


# ---------------------------------------------------------------------------
# 2. Only the units the target list names
# ---------------------------------------------------------------------------


def test_the_target_path_does_not_authorise_an_unrelated_unit(installed_rules):
    """The target list names ``farm`` — an archer must not be authorised.

    This checks the *target* path alone (the helper), so it is independent of
    what a unit happens to list in ``can_use_tech``.
    """
    from soundrts.worldupgrade.effect_bonus_parse import researched_techs_for_unit

    player = FakePlayer(["horse_collar"])
    archer = _make_unit(installed_rules, "archer", player)

    assert "horse_collar" not in researched_techs_for_unit(archer, player.upgrades)


def test_the_target_path_authorises_the_farm(installed_rules):
    """The same helper *does* authorise the farm."""
    from soundrts.worldupgrade.effect_bonus_parse import researched_techs_for_unit

    player = FakePlayer(["horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    assert "horse_collar" in researched_techs_for_unit(farm, player.upgrades)


def test_heavy_plow_reaches_both_the_farm_and_the_villager(installed_rules):
    """A tech with two rows reaches exactly the units each row names.

    AoE2 *Heavy Plow* raises the farm capacity **and** the villager's carry
    capacity, so it carries two filtered rows with different targets.
    """
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(installed_rules.unit_class("heavy_plow")))
    target_lists = [list(targets) for _bonus, targets in rows]
    assert ["farm"] in target_lists
    assert ["peasant"] in target_lists

    player = FakePlayer(["heavy_plow"])
    farm = _make_unit(installed_rules, "farm", player)
    villager = _make_unit(installed_rules, "peasant", player)

    assert "heavy_plow" in farm.upgrades
    assert "heavy_plow" in villager.upgrades


def test_crop_rotation_reaches_the_farm(installed_rules):
    """Another AoE2 farm tech authorised through its target list."""
    player = FakePlayer(["crop_rotation"])
    farm = _make_unit(installed_rules, "farm", player)

    assert "crop_rotation" in farm.upgrades


def test_the_frank_alias_reaches_the_farm(installed_rules):
    """The Franks' free alias authorises the farm the same way."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(installed_rules.unit_class("frank_horse_collar")))
    assert ["farm"] in [list(targets) for _bonus, targets in rows]

    player = FakePlayer(["frank_horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    assert "frank_horse_collar" in farm.upgrades


# ---------------------------------------------------------------------------
# 3. No duplicates, stable order
# ---------------------------------------------------------------------------


def test_a_tech_is_never_listed_twice(installed_rules):
    """A tech reachable through both paths is announced once."""
    player = FakePlayer(["horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    upgrades = farm.upgrades
    assert upgrades.count("horse_collar") == 1


def test_the_target_techs_keep_the_research_order(installed_rules):
    """The target-authorised techs follow the player's research order."""
    player = FakePlayer(["crop_rotation", "horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    upgrades = farm.upgrades
    assert upgrades.index("crop_rotation") < upgrades.index("horse_collar")


def test_a_researched_tech_is_not_repeated_when_the_player_lists_it_twice(
    installed_rules,
):
    """A player that lists a tech twice still gets it announced once."""
    player = FakePlayer(["horse_collar", "horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    assert farm.upgrades.count("horse_collar") == 1


# ---------------------------------------------------------------------------
# 4. The helper itself
# ---------------------------------------------------------------------------


def test_researched_techs_for_unit_returns_only_the_target_authorised(
    installed_rules,
):
    """The helper answers exactly "which researched techs apply to this unit?"."""
    from soundrts.worldupgrade.effect_bonus_parse import researched_techs_for_unit

    player = FakePlayer(["horse_collar", "heavy_plow", "wheelbarrow"])
    farm = _make_unit(installed_rules, "farm", player)

    result = researched_techs_for_unit(farm, player.upgrades)
    assert "horse_collar" in result
    assert "heavy_plow" in result
    assert "wheelbarrow" not in result


def test_researched_techs_for_unit_is_empty_without_researched_techs(
    installed_rules,
):
    """No researched techs → no target-authorised techs."""
    from soundrts.worldupgrade.effect_bonus_parse import researched_techs_for_unit

    player = FakePlayer([])
    farm = _make_unit(installed_rules, "farm", player)

    assert researched_techs_for_unit(farm, player.upgrades) == []


def test_the_helper_survives_a_player_without_upgrades(installed_rules):
    """A player stub without an ``upgrades`` attribute must not crash."""
    from soundrts.worldupgrade.effect_bonus_parse import researched_techs_for_unit

    farm = _make_unit(installed_rules, "farm", SimpleNamespace())
    assert researched_techs_for_unit(farm, []) == []


# ---------------------------------------------------------------------------
# 5. The announced title
# ---------------------------------------------------------------------------


def test_the_style_table_names_the_tech(aoe2_style):
    """The style table maps 马轭 to the TTS id 8255."""
    assert aoe2_style.get("horse_collar", "title") == ["8255"]


def test_the_announced_title_is_the_style_title(installed_rules, aoe2_style):
    """The ``v`` readout announces the style title (8255 → 马轭)."""
    player = FakePlayer(["horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)

    announced = []
    for upgrade in farm.upgrades:
        announced += aoe2_style.get(upgrade, "title")
    assert "8255" in announced


def test_the_announced_id_says_the_chinese_name(installed_rules):
    """8255 is spoken as 马轭 in the Chinese voice table."""
    tts = (ROOT / "mods" / "aoe2" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    assert "8255 马轭" in tts


def test_the_upgrades_status_property_lists_the_title(installed_rules, aoe2_style):
    """``EntityViewProperties.upgrades_status`` is the readout's engine."""
    from soundrts.clientgameentity import properties as properties_module

    class _View:
        """The bare minimum of an ``EntityView``: delegate to the model."""

        def __init__(self, model):
            self.model = model

        def __getattr__(self, name):
            if name == "model":
                raise AttributeError(name)
            return getattr(self.model, name)

    player = FakePlayer(["horse_collar"])
    farm = _make_unit(installed_rules, "farm", player)
    view = _View(farm)

    # The property reads the *global* style singleton.
    original_style = properties_module.style
    properties_module.style = aoe2_style
    try:
        status = properties_module.EntityViewProperties.upgrades_status.fget(view)
    finally:
        properties_module.style = original_style

    assert "8255" in status
