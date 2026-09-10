"""Terrain ``*_vs`` unit-specific modifiers from rules.txt class terrain."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import soundrts.worldunit  # noqa: F401

from soundrts.combat.attack_action import AttackActionMixin
from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.combat.hit_miss import HitMissMixin
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.nofloat import PRECISION
from soundrts.lib.square_terrain_rules import (
    terrain_unit_cover_percent,
    terrain_unit_speed_percent,
    unit_list_value,
)

_RULES = """
def cavalry
class soldier

def knight
class soldier
is_a cavalry
speed 4

def archer
class soldier
speed 2
rdg 5
rdg_range 5
rdg_cd 1.5

def footman
class soldier
speed 3

def marsh
class terrain
speed_vs knight .25
cover_vs archer .25
dodge_vs archer .1
mdg_vs knight -.33
rdg_vs archer -.2
mdg_cd_vs knight .5
rdg_cd_vs archer .25

def forest
class terrain
speed .5 1
cover .5 0
"""


@pytest.fixture(autouse=True)
def _load_rules():
    rules.load(_RULES, base_classes=_get_base_classes())


class _MarshPlace:
    type_name = "marsh"

    def type_name_at(self, x, y):
        return "marsh"

    @property
    def terrain_speed(self):
        return (100, 100)

    @property
    def terrain_cover(self):
        return (0, 0)

    def terrain_speed_at(self, x, y):
        return self.terrain_speed

    def terrain_cover_at(self, x, y):
        return self.terrain_cover


class _Knight:
    type_name = "knight"
    expanded_is_a = ("cavalry", "soldier")
    airground_type = "ground"
    speed = 4 * PRECISION
    mdg = 6 * PRECISION
    mdg_cd = int(1.5 * PRECISION)
    mdg_vs = {}
    mdg_on_terrain = ()
    place = None
    x = 0
    y = 0


class _Archer:
    type_name = "archer"
    expanded_is_a = ("soldier",)
    airground_type = "ground"
    speed = 2 * PRECISION
    rdg = 5 * PRECISION
    rdg_cd = int(1.5 * PRECISION)
    rdg_vs = {}
    rdg_on_terrain = ()
    rdg_hit_rate = 100 * PRECISION
    rdg_dodge_rate = 0
    mdg_dodge_rate = 0
    mdg_dodge_rate_on_terrain = ()
    rdg_dodge_rate_on_terrain = ()
    mdg_dodge_rate_vs = {}
    rdg_dodge_rate_vs = {}
    place = None
    x = 0
    y = 0
    world = type("W", (), {"random": type("R", (), {"randint": staticmethod(lambda a, b: 50)})()})()


class _Footman:
    type_name = "footman"
    expanded_is_a = ("soldier",)
    airground_type = "ground"
    speed = 3 * PRECISION


def test_unit_list_value_exact_and_is_a():
    knight = _Knight()
    assert unit_list_value(knight, ["knight", ".25", "cavalry", ".5"]) == ".25"
    footman = _Footman()
    assert unit_list_value(footman, ["knight", ".25", "soldier", ".75"]) == ".75"
    assert unit_list_value(footman, ["knight", ".25"], default=None) is None


def test_speed_vs_only_matching_unit():
    knight = _Knight()
    footman = _Footman()
    assert terrain_unit_speed_percent("marsh", knight, (100, 100)) == (25, 25)
    assert terrain_unit_speed_percent("marsh", footman, (100, 100)) == (100, 100)


def test_cover_vs_overrides_default_cover():
    archer = _Archer()
    archer.place = _MarshPlace()
    assert terrain_unit_cover_percent("marsh", archer, (50, 0)) == 25


class _Attacker(DamageCalculationMixin, AttackActionMixin):
    def __init__(self, *, unit, place):
        self.type_name = unit.type_name
        self.expanded_is_a = unit.expanded_is_a
        self.place = place
        self.x = 0
        self.y = 0
        self.mdg = getattr(unit, "mdg", 0)
        self.mdg_vs = {}
        self.mdg_on_terrain = ()
        self.rdg_cd = getattr(unit, "rdg_cd", 0)
        self.rdg_cd_on_terrain = ()


def test_mdg_vs_reduces_damage_on_marsh():
    attacker = _Attacker(unit=_Knight(), place=_MarshPlace())
    target = type(
        "T",
        (),
        {"type_name": "footman", "expanded_is_a": (), "_armor_instance": None, "armor": None},
    )()
    # mdg 6, -33% -> 6 + 6*(-33)//100 = 4.02
    assert attacker._get_melee_damage_vs(target) == 6 * PRECISION + 6 * PRECISION * (-33) // 100


def test_rdg_cd_vs_increases_cooldown():
    attacker = _Attacker(unit=_Archer(), place=_MarshPlace())
    # rdg_cd 1.5, +25% -> +0.375s
    assert attacker._get_ranged_cd_on_terrain() == int(1.5 * PRECISION) * 25 // 100


def test_dodge_vs_adds_terrain_dodge():
    target = type("T", (HitMissMixin,), {})()
    target.type_name = "archer"
    target.expanded_is_a = ("soldier",)
    target.place = _MarshPlace()
    target.x = 0
    target.y = 0
    target.mdg_dodge_rate_on_terrain = ()
    target.rdg_dodge_rate_on_terrain = ()
    assert target._get_dodge_on_terrain(is_melee=False) == 10


def test_chance_to_hit_uses_cover_vs_for_archer():
    archer = _Archer()
    archer.place = _MarshPlace()
    attacker = type(
        "R",
        (HitMissMixin,),
        {
            "rdg_range": 5 * PRECISION,
            "rdg_hit_rate": 100 * PRECISION,
            "rdg_hit_rate_vs": {},
            "rdg_hit_rate_on_terrain": (),
            "expanded_is_a": (),
            "type_name": "archer",
            "height": 0,
            "mdg_projectile": 0,
            "rdg_projectile": 0,
            "place": _MarshPlace(),
            "x": 0,
            "y": 0,
        },
    )()

    def in_ranged_range(_self, _target):
        return True

    attacker.in_ranged_range = in_ranged_range.__get__(attacker, type(attacker))
    attacker.in_melee_range = lambda _t: False
    # 100% hit * (100 - 25 cover) / 100 = 75
    assert attacker.chance_to_hit(archer) == 75


def test_movement_speed_vs_integration():
    knight = _Knight()
    base_speed = 4 * PRECISION
    square_speed = (100, 100)
    terrain_speed = terrain_unit_speed_percent("marsh", knight, square_speed)
    actual_speed = (base_speed * terrain_speed[0]) // 100
    assert actual_speed == 1 * PRECISION
