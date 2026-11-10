# -*- coding: utf-8 -*-
"""AoE2: only the Burgundian villager may be upgraded to Flemish Militia.

Player-visible bug
------------------
``mods/aoe2/rules.txt`` declared::

    def peasant
    ...
    can_upgrade_to flemish_militia

on the **shared** ``peasant`` base class.  Every civilisation that reuses
that base (the Vietnamese included) therefore inherited a manual
"upgrade to Flemish Militia" action on its villagers, even though Flemish
Revolution is a Burgundian-only technology.  The player saw a button that
did not belong to their civilisation.

The flag now lives on ``burgundian_villager`` only.  This module locks
that down:

* the shared ``peasant`` base must NOT offer the Flemish Militia upgrade;
* ``burgundian_villager`` must offer it (otherwise Flemish Revolution
  would have nothing to morph);
* no other civilisation's villager may offer it.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


def _race_peasant(rules, civ):
    """The villager type a race uses (``peasant <type>`` in the race def)."""
    value = rules.get(civ, "peasant")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else None
    return value


def _can_upgrade_to(rules, type_name):
    cls = rules.unit_class(type_name)
    assert cls is not None, type_name
    return set(getattr(cls, "can_upgrade_to", ()) or ())


def test_shared_peasant_does_not_offer_the_flemish_militia_upgrade(aoe2_rules):
    """``peasant`` is the base of every civ's villager — keep it clean."""
    assert "flemish_militia" not in _can_upgrade_to(aoe2_rules, "peasant")


def test_the_burgundian_villager_keeps_the_flemish_militia_upgrade(aoe2_rules):
    """Flemish Revolution morphs the villagers, so the flag must stay."""
    assert "flemish_militia" in _can_upgrade_to(aoe2_rules, "burgundian_villager")


@pytest.mark.parametrize(
    "civ",
    [
        "vietnamese",
        "britons",
        "franks",
        "chinese",
        "mongols",
        "byzantines",
        "japanese",
        "teutons",
        "vikings",
        "portuguese",
        "celts",
        "malians",
        "aztecs",
        "goths",
        "persians",
        "slavs",
        "cumans",
        "huns",
        "koreans",
        "mayans",
        "hindustanis",
        "spanish",
        "magyars",
        "poles",
        "italians",
        "bohemians",
        "turks",
        "saracens",
        "bulgarians",
        "lithuanians",
        "tatars",
        "berbers",
        "ethiopians",
        "khmer",
        "malays",
        "burmese",
        "sicilians",
        "armenians",
        "georgians",
        "incas",
        "romans",
    ],
)
def test_no_other_civ_villager_offers_the_flemish_militia_upgrade(aoe2_rules, civ):
    """Every non-Burgundian villager must not inherit the upgrade."""
    villager = _race_peasant(aoe2_rules, civ)
    assert villager, civ
    assert villager != "burgundian_villager"
    assert "flemish_militia" not in _can_upgrade_to(aoe2_rules, villager)


def test_flemish_revolution_is_still_a_burgundian_castle_technology(aoe2_rules):
    """The research itself must stay reachable — only the manual upgrade moved."""
    castle = aoe2_rules.unit_class("burgundian_castle")
    assert "flemish_revolution" in set(
        aoe2_rules.class_rules_attr(castle, "can_research", ())
    )
    # And the effect still morphs the villagers into Flemish Militia.
    effect = aoe2_rules.get("flemish_revolution", "effect")
    assert effect == ["unit_line_upgrade", "flemish_militia"]
