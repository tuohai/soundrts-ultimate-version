# -*- coding: utf-8 -*-
"""AoE2: no castle may offer a technology that does not exist.

Player-visible bug
------------------
``mods/aoe2/rules.txt`` listed a technology named ``mercenaries`` in the
Magyar Castle's ``can_research`` list, but no ``def mercenaries`` exists
anywhere in the ruleset - it was dropped when the invented (AoE1) unique
technologies were replaced with the canonical AoE2 DE ones, and the
castle list was not cleaned up with them.

The consequence is a crash, not just a cosmetic problem:

* ``ComplexOrder.__init__`` resolves the order type with
  ``rules.unit_class("mercenaries")`` -> ``None``;
* ``ResearchOrder.cost`` then reads ``self.type.cost`` ->

      AttributeError: 'NoneType' object has no attribute 'cost'

so focusing that entry in the Magyar Castle's technology menu blows up.
(The AI happens to guard against it with an explicit
``if unit_type is None: continue``, which is why only the human player
path crashed.)

This module locks it down: every technology a building offers must
resolve to a real rules class, and every castle in the mod must survive
building its research menu.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "mods" / "aoe2"


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (MOD / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


def _castle_names(rules):
    out = []
    for name in rules.classnames():
        cls = rules.unit_class(name)
        if cls is None:
            continue
        if not rules.class_rules_attr(cls, "is_a_building", False):
            continue
        if "can_research" in rules.class_rules_attr(cls, "can_research", ()) or True:
            out.append(name)
    return out


def test_every_castle_technology_resolves_to_a_real_class(aoe2_rules):
    """No building may list a technology that has no rules definition."""
    broken = {}
    for name in _castle_names(aoe2_rules):
        cls = aoe2_rules.unit_class(name)
        for tech in aoe2_rules.class_rules_attr(cls, "can_research", ()) or ():
            if aoe2_rules.unit_class(tech) is None:
                broken.setdefault(name, []).append(tech)
    assert not broken, "buildings offering undefined technologies: %r" % broken


def test_the_magyar_castle_no_longer_offers_the_removed_mercenaries_tech(aoe2_rules):
    """The specific regression: "mercenaries" has no rules definition."""
    assert aoe2_rules.unit_class("mercenaries") is None
    castle = aoe2_rules.unit_class("magyar_castle")
    assert "mercenaries" not in set(
        aoe2_rules.class_rules_attr(castle, "can_research", ())
    )


def test_the_magyar_castle_research_menu_builds_without_crashing(aoe2_rules):
    """Building the menu must not raise on a dangling technology name."""
    from soundrts.definitions import rules as global_rules
    from soundrts.worldorders.production import ResearchOrder

    saved_dict = global_rules._dict
    saved_classes = getattr(global_rules, "classes", None)
    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    try:

        class _Player:
            forbidden_techs = []
            upgrades = ["imperial_age"]
            units = []

            def has_all(self, requirements):
                return True

            def check_count_limit(self, type_name):
                return True

        class _Castle:
            type_name = "magyar_castle"
            attached_addons = []
            is_a_building = True
            place = None
            orders = []
            basic_skills = set()
            can_advance = ()

            def __init__(self):
                self.player = _Player()
                self.can_research = list(
                    aoe2_rules.class_rules_attr(
                        aoe2_rules.unit_class("magyar_castle"), "can_research", ()
                    )
                )

        castle = _Castle()
        entries = ResearchOrder.menu(castle)
        assert "research mercenaries" not in entries
        # Every entry must be backed by a real class, so the order can be built.
        for entry in entries:
            tech = entry.split(" ", 1)[1]
            order = ResearchOrder(castle, [tech])
            assert order.type is not None, tech
            # The cost must be computable - this is what used to crash.
            assert order.cost is not None
    finally:
        global_rules._dict = saved_dict
        if saved_classes is not None:
            global_rules.classes = saved_classes
