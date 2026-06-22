"""Tests for combat stat per-level growth."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.level_up_stats import LEVEL_UP_STAT_ATTRS, apply_level_stat_bonuses
from soundrts.worldunit.world_status_update import CreatureStatusUpdate


def _make_unit(**overrides):
    unit = SimpleNamespace(
        type_name="test_hero",
        id=1,
        level=1,
        max_level=20,
        xp=0,
        xp_thresholds=[100],
        xp_reward=0,
        xp_reward_per_xp=0,
        hp_max=1000,
        hp=1000,
        hp_max_per_level=100,
        mdg=5000,
        mdg_per_level=200,
        mdg_crit_rate=10,
        mdg_crit_rate_per_level=2,
        mdf=3000,
        mdf_per_level=100,
        charge_mdg=1000,
        charge_mdg_per_level=500,
        notifications=[],
    )
    for key, value in overrides.items():
        setattr(unit, key, value)
    unit.notify = lambda msg: unit.notifications.append(msg)
    unit._unlock_level_skills = lambda level, notify=False: None
    return unit


def test_apply_level_stat_bonuses_combat_attrs():
    unit = _make_unit()
    apply_level_stat_bonuses(unit)
    assert unit.hp_max == 1100
    assert unit.hp == 1100
    assert unit.mdg == 5200
    assert unit.mdf == 3100
    assert unit.mdg_crit_rate == 12
    assert unit.charge_mdg == 1500


def test_increase_xp_applies_all_per_level_stats():
    unit = _make_unit(xp=99)
    CreatureStatusUpdate.increase_xp(unit, 1)
    assert unit.level == 2
    assert unit.xp == 100
    assert unit.mdg == 5200
    assert unit.charge_mdg == 1500
    assert any("level_up" in n for n in unit.notifications)


def test_increase_xp_resets_xp_when_level_up_reset_xp():
    unit = _make_unit(xp=99, level_up_reset_xp=1)
    CreatureStatusUpdate.increase_xp(unit, 1)
    assert unit.level == 2
    assert unit.xp == 0


def test_increase_xp_keeps_xp_by_default():
    unit = _make_unit(xp=99, level_up_reset_xp=0)
    CreatureStatusUpdate.increase_xp(unit, 1)
    assert unit.level == 2
    assert unit.xp == 100


def test_level_up_reset_xp_parsed_in_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        """
def hero
class soldier
level_up_reset_xp 1
"""
    )
    assert r.unit_class("hero").level_up_reset_xp == 1


def test_all_combat_stats_have_per_level_rules_support():
    from soundrts.definitions import rules

    for stat in LEVEL_UP_STAT_ATTRS:
        per_level = f"{stat}_per_level"
        assert (
            per_level in rules.precision_properties
            or per_level in rules.int_properties
        ), f"{per_level} not registered in rules"


def test_soldier_has_all_per_level_class_attrs():
    from soundrts.worldunit.worldsoldier import Soldier

    for stat in LEVEL_UP_STAT_ATTRS:
        assert hasattr(Soldier, f"{stat}_per_level")


def test_apply_level_stat_bonuses_mana_and_heal_harm():
    unit = _make_unit(
        mana_max=100,
        mana=100,
        mana_max_per_level=20,
        mana_regen=5,
        mana_regen_per_level=1,
        hp_regen_cd=1000,
        hp_regen_cd_per_level=500,
        heal_level=2,
        heal_level_per_level=1,
        heal_cd=3000,
        heal_cd_per_level=1000,
        heal_radius=6000,
        heal_radius_per_level=1000,
        harm_level=3,
        harm_level_per_level=1,
        harm_cd=2000,
        harm_cd_per_level=500,
    )
    apply_level_stat_bonuses(unit)
    assert unit.mana_max == 120
    assert unit.mana == 120
    assert unit.mana_regen == 6
    assert unit.hp_regen_cd == 1500
    assert unit.heal_level == 3
    assert unit.heal_cd == 4000
    assert unit.heal_radius == 7000
    assert unit.harm_level == 4
    assert unit.harm_cd == 2500


def test_level_up_heal_full_restores_hp_and_mana():
    unit = _make_unit(
        hp=400,
        hp_max=1000,
        hp_max_per_level=100,
        mana_max=200,
        mana=50,
        mana_max_per_level=20,
        level_up_heal_full=1,
    )
    apply_level_stat_bonuses(unit)
    assert unit.hp_max == 1100
    assert unit.hp == 1100
    assert unit.mana_max == 220
    assert unit.mana == 220


def test_level_up_without_heal_full_only_adds_bonus():
    unit = _make_unit(
        hp=400,
        hp_max=1000,
        hp_max_per_level=100,
        mana_max=200,
        mana=50,
        mana_max_per_level=20,
        level_up_heal_full=0,
    )
    apply_level_stat_bonuses(unit)
    assert unit.hp_max == 1100
    assert unit.hp == 500
    assert unit.mana_max == 220
    assert unit.mana == 70


def test_level_up_heal_full_parsed_in_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def soldier
class soldier

def hero
class soldier
level_up_heal_full 1
"""
    )
    assert r.unit_class("hero").level_up_heal_full == 1
