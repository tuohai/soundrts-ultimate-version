"""Regression: terrain lookup caches / combat short-circuit."""
from __future__ import annotations

from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.square_terrain_rules import (
    any_terrain_defines,
    clear_terrain_lookup_caches,
    is_terrain_def,
    square_terrain_entries_for_type,
    terrain_property,
    terrain_unit_stat_percent_delta,
    type_affects_square_terrain,
)


def test_any_terrain_defines_false_when_no_combat_vs():
    rules.load(
        """
def plain
class terrain
is_dynamic 1

def footman
class soldier
mdg 6
""",
        base_classes=_get_base_classes(),
    )
    assert is_terrain_def("plain") is True
    assert any_terrain_defines("mdg_vs") is False
    assert any_terrain_defines("rdg_vs") is False
    assert terrain_unit_stat_percent_delta("plain", object(), 1000, "mdg_vs") == 0


def test_any_terrain_defines_true_when_mdg_vs_present():
    rules.load(
        """
def marsh
class terrain
mdg_vs footman -.33

def footman
class soldier
""",
        base_classes=_get_base_classes(),
    )
    assert any_terrain_defines("mdg_vs") is True
    assert any_terrain_defines("rdg_vs") is False


def test_terrain_property_cache_cleared_on_reload():
    rules.load(
        """
def hill
class terrain
is_high_ground 1
""",
        base_classes=_get_base_classes(),
    )
    assert terrain_property("hill", "is_high_ground", 0) == 1
    rules.load(
        """
def hill
class terrain
""",
        base_classes=_get_base_classes(),
    )
    assert terrain_property("hill", "is_high_ground", 0) == 0
    clear_terrain_lookup_caches()
    assert is_terrain_def("hill") is True


def test_square_terrain_entries_cache_hit_and_cleared_on_reload():
    rules.load(
        """
def meadows
class terrain

def tree
class deposit
square_terrain meadows 80 7

def rock
class deposit
""",
        base_classes=_get_base_classes(),
    )
    first = square_terrain_entries_for_type("tree")
    second = square_terrain_entries_for_type("tree")
    assert first is second
    assert list(first) == [{"name": "meadows", "priority": 80, "min_count": 7}]
    assert type_affects_square_terrain("tree") is True
    assert square_terrain_entries_for_type("rock") == ()
    assert type_affects_square_terrain("rock") is False

    rules.load(
        """
def meadows
class terrain

def tree
class deposit
square_terrain meadows 10 1
""",
        base_classes=_get_base_classes(),
    )
    updated = square_terrain_entries_for_type("tree")
    assert list(updated) == [{"name": "meadows", "priority": 10, "min_count": 1}]
    assert updated is not first
