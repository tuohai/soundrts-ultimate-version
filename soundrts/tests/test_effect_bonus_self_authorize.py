# -*- coding: utf-8 -*-
"""Universal target-as-authorisation for filtered ``effect bonus`` rows.

Background
----------
A filtered ``effect bonus`` row reaches a unit through *two* gates:

* **Gate 1 (authorisation)** — the tech is listed in the unit's
  ``can_use`` / ``can_use_tech`` / ``can_use_skill``.
* **Gate 2 (row filter)** — ``effect_bonus_targets`` restricts the row to
  matching unit types.

Historically the two gates were *not* interchangeable, so Gate 1 could not
be dropped globally: measured over the AoE2 ruleset, 75 of the 137 filtered
techs would have leaked their bonus to units that never opted in (the worst
case being the Goths' *Anarchy*, whose target ``barracks`` is the base class
of every civ's Barracks).

The universal model removes that distinction: **a filtered row's target list
*is* its authorisation.**  There is no opt-in flag any more — a unit that
matches the row's target list enjoys the row, whether or not it repeats the
tech in ``can_use_tech``.

The base-class hazard does not come back, because the *target lists* were
fixed at the same time: naming a base class next to one of its own
descendants (the Goths' ``goth_barracks barracks``) is forbidden — see
``test_effect_bonus_target_redundancy.py``.

This module tests the universal model: that there is no flag left, that a
matching unit is authorised by its target list alone, that a non-matching
unit is not, and that the classic ``can_use_tech`` path still works.
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
    """Install the AoE2 rules into the global registry."""
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


def _unit(type_name, is_a=(), cls_name="creature"):
    """A minimal unit stand-in for the target matching."""
    return SimpleNamespace(
        type_name=type_name,
        expanded_is_a=set(is_a),
        cls=SimpleNamespace(__name__=cls_name),
    )


# ---------------------------------------------------------------------------
# 1. The flag is gone
# ---------------------------------------------------------------------------


def test_the_opt_in_flag_no_longer_exists():
    """The opt-in flag was removed from the engine's property list."""
    from soundrts.definitions import rules

    assert "effect_bonus_targets_are_authorization" not in rules.int_properties


def test_no_ruleset_uses_the_flag():
    """No ruleset may still declare the retired flag."""
    for path in (
        ROOT / "res" / "rules.txt",
        ROOT / "mods" / "aoe2" / "rules.txt",
    ):
        text = path.read_text(encoding="utf-8")
        assert "effect_bonus_targets_are_authorization" not in text, path


# ---------------------------------------------------------------------------
# 2. What the target list grants
# ---------------------------------------------------------------------------


def test_targeted_unit_is_authorised_without_can_use_tech(aoe2_rules):
    """The point of the model: the farm need not list the tech."""
    farm = _unit("farm", is_a=("farm", "building"), cls_name="building")
    tech = aoe2_rules.unit_class("horse_collar")

    # The farm does NOT list the tech.
    assert "horse_collar" not in tuple(getattr(farm, "can_use_tech", ()))
    # …but it is authorised anyway.
    assert tech._unit_authorised(farm)


def test_unrelated_unit_is_not_authorised(aoe2_rules):
    """A unit that matches no target row is still not authorised."""
    peasant = _unit("peasant", is_a=("peasant", "creature"))
    tech = aoe2_rules.unit_class("horse_collar")

    assert not tech._unit_authorised(peasant)


def test_the_anarchy_target_is_the_only_authorisation(aoe2_rules):
    """The Goths' Anarchy reaches the Goth Barracks and nothing else.

    Its target list names the *derived* type ``goth_barracks``, so the row
    does not drag in the base class of all 41 civ Barracks.
    """
    anarchy = aoe2_rules.unit_class("anarchy")

    goth_barracks = _unit(
        "goth_barracks", is_a=("goth_barracks", "barracks", "building"),
        cls_name="building",
    )
    generic_barracks = _unit(
        "barracks", is_a=("barracks", "building"), cls_name="building"
    )

    assert anarchy._unit_authorised(goth_barracks)
    assert not anarchy._unit_authorised(generic_barracks)


def test_can_use_tech_still_authorises(aoe2_rules):
    """The classic path keeps working unchanged."""
    farm = aoe2_rules.unit_class("farm")
    tech = aoe2_rules.unit_class("masonry")

    # ``masonry`` has no filtered row, so the farm's explicit listing is
    # what authorises it.
    assert "masonry" in tuple(getattr(farm, "can_use_tech", ()))
    assert tech._unit_authorised(farm)


def test_explicit_can_use_tech_still_authorises(aoe2_rules):
    """Gate 1 still opens the tech for units it names explicitly."""
    peasant = _unit("peasant", is_a=("peasant", "creature"))
    peasant.can_use_tech = ("horse_collar",)
    tech = aoe2_rules.unit_class("horse_collar")

    # Matches the explicit list, even though it matches no target row.
    assert tech._unit_authorised(peasant)


# ---------------------------------------------------------------------------
# 3. The target rows themselves
# ---------------------------------------------------------------------------


def test_target_rows_are_only_the_filtered_ones(aoe2_rules):
    """Rows without a target list are governed by Gate 1 alone."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    # Heavy Plow carries two rows: the farm capacity bonus (targeted) and
    # the peasant carry capacity (targeted too) — both filtered.
    rows = list(tech_target_rows(aoe2_rules.unit_class("heavy_plow")))
    assert len(rows) >= 2
    for _bonus, targets in rows:
        assert targets


def test_unit_matches_tech_targets_uses_the_row_filter(aoe2_rules):
    """The matching goes through the engine's own target matcher."""
    from soundrts.worldupgrade.effect_bonus_parse import unit_matches_tech_targets

    tech = aoe2_rules.unit_class("horse_collar")
    assert unit_matches_tech_targets(
        _unit("farm", is_a=("farm", "building"), cls_name="building"), tech
    )
    assert not unit_matches_tech_targets(
        _unit("peasant", is_a=("peasant", "creature")), tech
    )


def test_type_matches_tech_targets_for_the_order_layer(aoe2_rules):
    """The class-level counterpart used by the cost/time aggregation."""
    from soundrts.worldupgrade.effect_bonus_parse import type_matches_tech_targets

    tech = aoe2_rules.unit_class("horse_collar")
    farm_cls = aoe2_rules.unit_class("farm")
    peasant_cls = aoe2_rules.unit_class("peasant")

    assert type_matches_tech_targets(farm_cls, tech)
    assert not type_matches_tech_targets(peasant_cls, tech)


# ---------------------------------------------------------------------------
# 4. The AoE2 rules use the model
# ---------------------------------------------------------------------------


def test_farm_does_not_repeat_the_mill_techs(aoe2_rules):
    """The whole point: the duplication is gone from the farm."""
    farm = aoe2_rules.unit_class("farm")
    can_use_tech = tuple(getattr(farm, "can_use_tech", ()))
    for tech_name in ("horse_collar", "heavy_plow", "crop_rotation"):
        assert tech_name not in can_use_tech


def test_farm_still_lists_the_strict_gate_techs(aoe2_rules):
    """The other farm techs keep the classic path."""
    farm = aoe2_rules.unit_class("farm")
    can_use_tech = tuple(getattr(farm, "can_use_tech", ()))
    for tech_name in ("masonry", "architecture", "town_watch", "town_patrol"):
        assert tech_name in can_use_tech


def test_the_mill_techs_still_declare_their_farm_rows(aoe2_rules):
    """Universal authorisation does not replace the target declaration."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    for tech_name in ("horse_collar", "heavy_plow", "crop_rotation"):
        rows = list(tech_target_rows(aoe2_rules.unit_class(tech_name)))
        assert any("farm" in targets for _bonus, targets in rows), tech_name


def test_every_targeted_row_reaches_at_least_one_type(aoe2_rules):
    """No tech may carry a filtered row that reaches nobody.

    This is the payoff of the universal model: the row's target list *is*
    its reach, so a row that names types nothing matches is a dead effect
    and must not exist.
    """
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows
    from soundrts.worldphase import Phase

    def _proxy(name):
        cls = aoe2_rules.unit_class(name)
        return SimpleNamespace(
            type_name=name,
            expanded_is_a=set(getattr(cls, "expanded_is_a", ()) or ()),
            cls=cls,
        )

    dead = []
    for name in aoe2_rules.classnames():
        cls = aoe2_rules.unit_class(name)
        rows = list(tech_target_rows(cls))
        if not rows:
            continue
        if not any(
            Phase._unit_matches_targets(_proxy(other), targets)
            for _bonus, targets in rows
            for other in aoe2_rules.classnames()
        ):
            dead.append(name)

    assert dead == [], sorted(dead)
