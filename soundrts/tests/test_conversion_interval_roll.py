"""Rules-driven conversion interval rolls (AoE2 DE-style miss until max)."""
from __future__ import annotations

from soundrts.definitions import Rules, rules
from soundrts.lib.nofloat import PRECISION
from soundrts.world_conversion import (
    ConversionRollParams,
    conversion_roll_after_interval,
    conversion_roll_params,
)
from soundrts.worldskill import Skill


class _AlwaysMiss:
    def randint(self, a, b):
        return b


class _AlwaysHit:
    def randint(self, a, b):
        return a


def test_no_interval_keeps_legacy_channel():
    class SkillType:
        conversion_interval = 0
        time_cost = 6 * PRECISION

    class Target:
        type_name = "militia"
        expanded_is_a = set()
        player = None

    assert conversion_roll_params(None, Target(), SkillType) is None
    assert Skill.conversion_channel_time(None, Target(), SkillType) == 6 * PRECISION


def test_unit_roll_params_and_guaranteed_max():
    class SkillType:
        conversion_interval = 1250
        conversion_min_intervals = 5
        conversion_max_intervals = 9
        conversion_chance = 38
        conversion_fail_at_max = 0

    class Target:
        type_name = "militia"
        expanded_is_a = set()
        player = None

    p = conversion_roll_params(None, Target(), SkillType)
    assert p.interval == 1250
    assert p.min_ci == 5
    assert p.max_ci == 9
    assert p.chance == 38
    assert p.fail_at_max is False
    assert Skill.conversion_channel_time(None, Target(), SkillType) == 1250 * 9
    assert conversion_roll_after_interval(p, 4, _AlwaysMiss()) == "warmup"
    assert conversion_roll_after_interval(p, 5, _AlwaysMiss()) == "miss"
    assert conversion_roll_after_interval(p, 5, _AlwaysHit()) == "success"
    assert conversion_roll_after_interval(p, 9, _AlwaysMiss()) == "success"


def test_fail_at_max_can_abort():
    p = ConversionRollParams(1250, 5, 9, 38, True)
    assert conversion_roll_after_interval(p, 9, _AlwaysMiss()) == "fail"
    assert conversion_roll_after_interval(p, 9, _AlwaysHit()) == "success"


def test_target_chance_and_resist_override_skill():
    rules.load(
        """
def parameters
nb_of_resource_types 4

def building
class building
conversion_min_intervals 15
conversion_max_intervals 25
conversion_chance 8

def scout_cavalry
class soldier
conversion_min_intervals 8
conversion_max_intervals 10
conversion_resist 2
"""
    )

    class SkillType:
        conversion_interval = 1250
        conversion_min_intervals = 5
        conversion_max_intervals = 9
        conversion_chance = 38

    class Building:
        type_name = "barracks"
        expanded_is_a = {"building"}
        player = None

    b = conversion_roll_params(None, Building(), SkillType)
    assert b.min_ci == 15
    assert b.max_ci == 25
    assert b.chance == 8

    class Scout:
        type_name = "scout_cavalry"
        expanded_is_a = {"scout_cavalry"}
        player = None

    s = conversion_roll_params(None, Scout(), SkillType)
    assert s.min_ci == 8
    assert s.max_ci == 10
    assert s.chance == 19  # 38 // 2


def test_faith_interval_bonus_lengthens_max():
    rules.load(
        """
def parameters
nb_of_resource_types 4

def faith
class upgrade
conversion_min_intervals_bonus 4
conversion_max_intervals_bonus 4
"""
    )

    class SkillType:
        conversion_interval = 1250
        conversion_min_intervals = 5
        conversion_max_intervals = 9
        conversion_chance = 38

    class Target:
        type_name = "militia"
        expanded_is_a = set()
        player = type("P", (), {"upgrades": ["faith"]})()

    p = conversion_roll_params(None, Target(), SkillType)
    assert p.min_ci == 9
    assert p.max_ci == 13
    assert Skill.conversion_channel_time(None, Target(), SkillType) == 1250 * 13


def test_aoe2_a_conversion_parses_interval_fields():
    from pathlib import Path

    src = Path(__file__).resolve().parents[2].joinpath("mods", "aoe2", "rules.txt")
    if not src.is_file():
        return
    text = src.read_text(encoding="utf-8")
    r = Rules()
    r.load(text)
    sk = r.unit_class("a_conversion")
    assert int(getattr(sk, "conversion_min_intervals", 0)) == 5
    assert int(getattr(sk, "conversion_max_intervals", 0)) == 9
    assert int(getattr(sk, "conversion_chance", 0)) == 38
    interval = int(getattr(sk, "conversion_interval", 0))
    assert interval == 1250 or interval == int(1.25 * PRECISION)
    faith = r.unit_class("faith")
    assert int(getattr(faith, "conversion_min_intervals_bonus", 0)) == 4
    assert int(getattr(faith, "conversion_max_intervals_bonus", 0)) == 4
    building = r.unit_class("building")
    assert int(getattr(building, "conversion_min_intervals", 0)) == 15
    scout = r.unit_class("scout_cavalry")
    assert int(getattr(scout, "conversion_resist", 0)) == 2
