"""effect bonus + effect_bonus_targets (no inline unit lists; -exclude supported)."""
from __future__ import annotations

from soundrts.definitions import Rules
from soundrts.worldupgrade import Upgrade
from soundrts.worldupgrade.effect_bonus_parse import (
    split_effect_bonus_args,
    unit_matches_effect_types,
)


def test_split_effect_bonus_vs_only():
    bonus, units = split_effect_bonus_args(["mdg_vs", "building", "2"])
    assert bonus == ["mdg_vs", "building", 2000]
    assert units == []


def test_split_idempotent_on_stored_ints():
    bonus, units = split_effect_bonus_args(["rdg", 1000, "aoe_archer", "-building"])
    assert bonus == ["rdg", 1000]
    assert units == ["aoe_archer", "-building"]


def test_rules_rejects_inline_unit_list_keeps_bonus():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def arson
class upgrade
effect bonus mdg_vs building 2 militia spearman
"""
    )
    effect = r._dict["arson"]["effect"]
    # trailing units discarded at parse; only bonus kept
    assert effect[0] == "bonus"
    assert effect[1:4] == ["mdg_vs", "building", 2000]
    assert len(effect) == 4


def test_effect_bonus_targets_with_exclude():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def bracer
class upgrade
effect bonus rdg 1
effect_bonus_targets aoe_archer scouttower -town_center
"""
    )
    effect = r._dict["bracer"]["effect"]
    bonus, units = split_effect_bonus_args(effect[1:])
    assert bonus[:2] == ["rdg", 1000]
    assert units == ["aoe_archer", "scouttower", "-town_center"]


def test_effect_bonus_exclude_matching():
    class U:
        def __init__(self, type_name, expanded_is_a=(), cls_name=""):
            self.type_name = type_name
            self.expanded_is_a = expanded_is_a
            self.cls = type(cls_name, (), {}) if cls_name else None
            self.rdg = 4000

    archer = U("aoe_archer", ("soldier",), "soldier")
    building = U("scouttower", ("building",), "building")
    targets = ["soldier", "-building"]
    assert unit_matches_effect_types(archer, targets)
    assert not unit_matches_effect_types(building, targets)

    Upgrade.effect_bonus(archer, 0, "rdg", 1000, "soldier", "-building")
    Upgrade.effect_bonus(building, 0, "rdg", 1000, "soldier", "-building")
    assert archer.rdg == 5000
    assert building.rdg == 4000


def test_unit_matches_is_a():
    class U:
        type_name = "crossbowman"
        expanded_is_a = ("aoe_archer", "soldier")
        cls = type("soldier", (), {})

    assert unit_matches_effect_types(U(), ["aoe_archer"])
    assert not unit_matches_effect_types(U(), ["skirmisher"])
    assert unit_matches_effect_types(U(), [])
