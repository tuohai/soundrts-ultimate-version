"""any_buildings <n> <group>_buildings requirement syntax."""
from __future__ import annotations

import types

from soundrts.definitions import _get_base_classes, rules
from soundrts.worldrequirements import (
    ANY_BUILDINGS,
    buildings_of_group,
    has_phase_as_simple_requirement,
    parse_requirement_clauses,
    requirements_satisfied,
    resolve_building_group,
    simple_requirement_names,
)


_MINI_RULES = """
def parameters
nb_of_resource_types 2

def feudal_age
class phase

def castle_age
class phase
requirements feudal_age

def imperial_age
class phase
requirements castle_age any_buildings 2 castle_age_buildings

def farm
class building
requirements feudal_age

def barracks
class building
requirements feudal_age

def blacksmith
class building
requirements feudal_age

def stables
class building
requirements castle_age

def workshop
class building
requirements castle_age

def temple
class building
requirements castle_age

def keep
class building
requirements barracks

def castle
class building
requirements any_buildings 2 castle_age_buildings
is_a keep

def knight
class soldier
requirements stables

def catapult
class soldier
requirements castle_age
"""


def _load():
    rules.load(_MINI_RULES, base_classes=_get_base_classes())


def _player(owned=(), upgrades=()):
    owned = set(owned)
    upgrades = set(upgrades)

    def has(name):
        if name in upgrades:
            return True
        return name in owned

    return types.SimpleNamespace(has=has, upgrades=list(upgrades), units=[])


def test_resolve_building_group_strips_suffix():
    assert resolve_building_group("castle_age_buildings") == "castle_age"
    assert resolve_building_group("keep_buildings") == "keep"
    assert resolve_building_group("castle_age") == "castle_age"


def test_parse_any_buildings_mixed_with_simple():
    clauses = parse_requirement_clauses(
        ["castle_age", "any_buildings", "2", "castle_age_buildings"]
    )
    assert clauses == [
        ("has", "castle_age"),
        (ANY_BUILDINGS, 2, "castle_age_buildings"),
    ]


def test_simple_requirement_names_exclude_any_buildings_args():
    tokens = ["castle_age", "any_buildings", "2", "castle_age_buildings"]
    assert simple_requirement_names(tokens) == ["castle_age"]
    assert has_phase_as_simple_requirement(tokens, "castle_age")
    assert not has_phase_as_simple_requirement(
        ["any_buildings", "2", "castle_age_buildings"], "castle_age"
    )


def test_group_membership_from_simple_requirements_only():
    _load()
    assert buildings_of_group("castle_age_buildings") == [
        "stables",
        "temple",
        "workshop",
    ]
    assert "catapult" not in buildings_of_group("castle_age_buildings")
    assert "farm" not in buildings_of_group("castle_age_buildings")
    # without requirements keep, keep_buildings is empty
    assert buildings_of_group("keep_buildings") == []


def test_imperial_age_needs_phase_and_any_two_castle_buildings():
    _load()
    imperial = rules.unit_class("imperial_age")
    assert requirements_satisfied(
        _player(owned=["stables"], upgrades=["castle_age"]),
        imperial.requirements,
    ) is False
    assert requirements_satisfied(
        _player(owned=["stables", "temple"], upgrades=["castle_age"]),
        imperial.requirements,
    ) is True


def test_castle_upgrade_uses_castle_age_buildings_group():
    _load()
    castle = rules.unit_class("castle")
    assert requirements_satisfied(
        _player(owned=["barracks", "farm"]), castle.requirements
    ) is False
    assert requirements_satisfied(
        _player(owned=["stables", "workshop"]), castle.requirements
    ) is True


def test_vanilla_imperial_and_castle_groups():
    from soundrts.lib.resource import res

    res.load_rules_and_ai()
    assert list(rules.unit_class("imperial_age").requirements) == [
        "castle_age",
        "any_buildings",
        "2",
        "castle_age_buildings",
    ]
    assert list(rules.unit_class("castle").requirements) == [
        "any_buildings",
        "2",
        "castle_age_buildings",
    ]
    names = set(buildings_of_group("castle_age_buildings"))
    assert {"stables", "workshop", "temple"}.issubset(names)
    assert "barracks" not in names
