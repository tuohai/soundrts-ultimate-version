"""Tests for xp_threshold_growth (auto-generated xp_thresholds)."""
from __future__ import annotations

import pytest

from soundrts.definitions import Rules
from soundrts.xp_threshold_growth import generate_xp_thresholds


def test_linear_growth():
    assert generate_xp_thresholds(["linear", "100", "50"], 5) == [100, 150, 200, 250]


def test_quadratic_matches_raynor_curve():
    expected = [40, 90, 160, 250, 360, 490, 640, 810, 1000]
    assert generate_xp_thresholds(["quadratic", "40", "40", "10"], 10) == expected


def test_geometric_growth():
    result = generate_xp_thresholds(["geometric", "100", "1.5"], 5)
    assert result == [100, 150, 225, 338]


def test_polynomial_is_general_quadratic():
    assert generate_xp_thresholds(["polynomial", "40", "40", "10"], 5) == [40, 90, 160, 250]


def test_max_level_100_linear():
    thresholds = generate_xp_thresholds(["linear", "100", "50"], 100)
    assert len(thresholds) == 99
    assert thresholds[0] == 100
    assert thresholds[-1] == 100 + 50 * 98


def test_rules_load_expands_growth():
    rules = Rules()
    rules.read(
        """
def hero_template
class soldier
max_level 5
xp_threshold_growth linear 100 50
hp_max_per_level 10
"""
    )
    rules.apply_inheritance()
    rules._expand_xp_thresholds_for_all_units()
    assert rules._dict["hero_template"]["xp_thresholds"] == [100, 150, 200, 250]


def test_rules_load_full_class():
    rules = Rules()
    rules.load(
        """
def growth_hero
class soldier
max_level 4
xp_threshold_growth quadratic 40 40 10
"""
    )
    hero = rules.unit_class("growth_hero")
    assert hero is not None
    assert hero.xp_thresholds == [40, 90, 160]
    assert len(hero.xp_thresholds) + 1 == 4
    assert "max_level" not in hero.__dict__
    assert "xp_threshold_growth" not in hero.__dict__


def test_explicit_xp_thresholds_win():
    rules = Rules()
    rules.read(
        """
def explicit_hero
class soldier
max_level 10
xp_thresholds 200 500
xp_threshold_growth linear 100 50
"""
    )
    rules.apply_inheritance()
    rules._expand_xp_thresholds_for_all_units()
    assert rules._dict["explicit_hero"]["xp_thresholds"] == [200, 500]


def test_inheritance_child_overrides_max_level():
    rules = Rules()
    rules.read(
        """
def base_hero
class soldier
max_level 10
xp_threshold_growth linear 100 50

def child_hero
is_a base_hero
max_level 4
"""
    )
    rules.apply_inheritance()
    rules._expand_xp_thresholds_for_all_units()
    assert rules._dict["child_hero"]["xp_thresholds"] == [100, 150, 200]


def test_unknown_growth_type_raises():
    with pytest.raises(ValueError, match="unknown"):
        generate_xp_thresholds(["weird", "1"], 3)
