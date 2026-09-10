"""Runtime tests: unit-level *_vs params must change combat/movement outcomes."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import soundrts.worldunit  # noqa: F401

from soundrts.combat.attack_action import AttackActionMixin
from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.combat.hit_miss import HitMissMixin
from soundrts.combat.targeting import TargetingMixin
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.nofloat import PRECISION, to_int

_RULES = """
def building
class building

def footman
class soldier

def test_striker
class soldier
mdg 5
rdg 5
mdg_ready 1
rdg_ready 2
mdg_cd 1.5
rdg_cd 1.5
mdg_hit_rate 80
rdg_hit_rate 90
mdg_range 3
rdg_range 5
mdg_minimal_range 1
rdg_minimal_range 2
speed 4
mdg_ready_vs building 0.5
rdg_ready_vs building 0.6
mdg_cd_vs building 0.7
rdg_cd_vs building 0.8
mdg_hit_rate_vs building 10
rdg_hit_rate_vs building 20
mdg_range_vs building 1
rdg_range_vs building 1.5
mdg_minimal_range_vs building 0.5
rdg_minimal_range_vs building 0.6
speed_vs building 1
mdg_dodge_rate_vs footman 15
rdg_dodge_rate_vs footman 25
"""


@pytest.fixture(autouse=True)
def _load_rules():
    rules.load(_RULES, base_classes=_get_base_classes())


class _BuildingTarget:
    type_name = "building"
    expanded_is_a = ("building",)
    _armor_instance = None
    armor = None
    mdg_dodge_rate = 0
    rdg_dodge_rate = 0
    mdg_dodge_rate_vs = {}
    rdg_dodge_rate_vs = {}
    place = None
    x = 0
    y = 0
    airground_type = "ground"
    height = 0
    radius = 0


class _FootmanTarget(_BuildingTarget):
    type_name = "footman"
    expanded_is_a = ("soldier",)


class _Attacker(AttackActionMixin, HitMissMixin, TargetingMixin, DamageCalculationMixin):
    """Minimal combat mixin host with unit-level *_vs dicts."""

    def __init__(self):
        self.type_name = "test_striker"
        self.expanded_is_a = ()
        self.place = None
        self.x = 0
        self.y = 0
        self.mdg_ready = to_int("1")
        self.rdg_ready = to_int("2")
        self.mdg_cd = to_int("1.5")
        self.rdg_cd = to_int("1.5")
        self.mdg_hit_rate = to_int("80")
        self.rdg_hit_rate = to_int("90")
        self.mdg_range = to_int("3")
        self.rdg_range = to_int("5")
        self.mdg_minimal_range = to_int("1")
        self.rdg_minimal_range = to_int("2")
        self.speed = to_int("4")
        self.mdg_ready_vs = {"building": to_int("0.5")}
        self.rdg_ready_vs = {"building": to_int("0.6")}
        self.mdg_cd_vs = {"building": to_int("0.7")}
        self.rdg_cd_vs = {"building": to_int("0.8")}
        self.mdg_hit_rate_vs = {"building": to_int("10")}
        self.rdg_hit_rate_vs = {"building": to_int("20")}
        self.mdg_range_vs = {"building": to_int("1")}
        self.rdg_range_vs = {"building": to_int("1.5")}
        self.mdg_minimal_range_vs = {"building": to_int("0.5")}
        self.rdg_minimal_range_vs = {"building": to_int("0.6")}
        self.speed_vs = {"building": to_int("1")}
        self.mdg_cd_on_terrain = ()
        self.rdg_cd_on_terrain = ()
        self.mdg_hit_rate_on_terrain = ()
        self.rdg_hit_rate_on_terrain = ()
        self.speed_on_terrain = ()
        self.height = 0
        self.mdg_projectile = 0
        self.rdg_projectile = 0

    def in_melee_range(self, target):
        return True

    def in_ranged_range(self, target):
        return False


def _minimal_range_with_vs(base, vs_dict, target):
    min_range = base
    if target.type_name in vs_dict:
        min_range += vs_dict[target.type_name]
    else:
        for t in target.expanded_is_a:
            if t in vs_dict:
                min_range += vs_dict[t]
                break
    return min_range


def test_rules_txt_parses_all_unit_vs_params():
    cls = rules.unit_class("test_striker")
    assert cls.mdg_ready_vs["building"] == to_int("0.5")
    assert cls.rdg_ready_vs["building"] == to_int("0.6")
    assert cls.mdg_cd_vs["building"] == to_int("0.7")
    assert cls.rdg_cd_vs["building"] == to_int("0.8")
    assert cls.mdg_hit_rate_vs["building"] == to_int("10")
    assert cls.rdg_hit_rate_vs["building"] == to_int("20")
    assert cls.mdg_range_vs["building"] == to_int("1")
    assert cls.rdg_range_vs["building"] == to_int("1.5")
    assert cls.mdg_minimal_range_vs["building"] == to_int("0.5")
    assert cls.rdg_minimal_range_vs["building"] == to_int("0.6")
    assert cls.speed_vs["building"] == to_int("1")
    assert cls.mdg_dodge_rate_vs["footman"] == to_int("15")
    assert cls.rdg_dodge_rate_vs["footman"] == to_int("25")


def test_mdg_ready_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_melee_ready_vs(t) == a.mdg_ready + to_int("0.5")
    assert a._get_melee_ready_vs(_FootmanTarget()) == a.mdg_ready


def test_rdg_ready_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_range_ready_vs(t) == a.rdg_ready + to_int("0.6")
    assert a._get_range_ready_vs(_FootmanTarget()) == a.rdg_ready


def test_mdg_cd_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_melee_cd_vs(t) == a.mdg_cd + to_int("0.7")
    assert a._get_melee_cd_vs(_FootmanTarget()) == a.mdg_cd


def test_rdg_cd_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_ranged_cd_vs(t) == a.rdg_cd + to_int("0.8")
    assert a._get_ranged_cd_vs(_FootmanTarget()) == a.rdg_cd


def test_mdg_hit_rate_vs_adds_hit_chance():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_melee_hit_rate_vs(t) == 80 + 10
    assert a._get_melee_hit_rate_vs(_FootmanTarget()) == 80


def test_rdg_hit_rate_vs_adds_hit_chance():
    a = _Attacker()
    t = _BuildingTarget()
    # +20 vs building, clamped to 100
    assert a._get_ranged_hit_rate_vs(t) == 100
    assert a._get_ranged_hit_rate_vs(_FootmanTarget()) == 90


def test_mdg_dodge_rate_vs_on_defender():
    defender = type(
        "D",
        (HitMissMixin,),
        {
            "type_name": "test_striker",
            "expanded_is_a": (),
            "mdg_dodge_rate": 0,
            "mdg_dodge_rate_vs": {"footman": to_int("15")},
            "rdg_dodge_rate_vs": {},
        },
    )()
    attacker = type("A", (), {"type_name": "footman", "expanded_is_a": ("soldier",)})()
    assert defender._get_dodge_vs(attacker, is_melee=True) == 15
    other = type("A2", (), {"type_name": "building", "expanded_is_a": ("building",)})()
    assert defender._get_dodge_vs(other, is_melee=True) == 0


def test_rdg_dodge_rate_vs_on_defender():
    defender = type(
        "D",
        (HitMissMixin,),
        {
            "type_name": "test_striker",
            "expanded_is_a": (),
            "rdg_dodge_rate": 0,
            "mdg_dodge_rate_vs": {},
            "rdg_dodge_rate_vs": {"footman": to_int("25")},
        },
    )()
    attacker = type("A", (), {"type_name": "footman", "expanded_is_a": ("soldier",)})()
    assert defender._get_dodge_vs(attacker, is_melee=False) == 25


def test_mdg_range_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a.get_effective_mdg_range(t) == a.mdg_range + to_int("1")
    assert a.get_effective_mdg_range(_FootmanTarget()) == a.mdg_range


def test_rdg_range_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    assert a.get_effective_rdg_range(t) == a.rdg_range + to_int("1.5")
    assert a.get_effective_rdg_range(_FootmanTarget()) == a.rdg_range


def test_mdg_minimal_range_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    got = _minimal_range_with_vs(a.mdg_minimal_range, a.mdg_minimal_range_vs, t)
    assert got == a.mdg_minimal_range + to_int("0.5")


def test_rdg_minimal_range_vs_adds_to_base():
    a = _Attacker()
    t = _BuildingTarget()
    got = _minimal_range_with_vs(a.rdg_minimal_range, a.rdg_minimal_range_vs, t)
    assert got == a.rdg_minimal_range + to_int("0.6")


def test_speed_vs_adds_when_chasing_target_type():
    a = _Attacker()
    t = _BuildingTarget()
    assert a._get_speed_vs(t) == a.speed + to_int("1")
    assert a._get_speed_vs(_FootmanTarget()) == a.speed
    assert a._get_speed_vs(None) == a.speed


def test_hit_or_miss_uses_target_dodge_vs():
    """Defender mdg_dodge_rate_vs must reduce attacker hit chance in _hit_or_miss."""
    attacker = _Attacker()
    attacker.world = type(
        "W",
        (),
        {"random": type("R", (), {"randint": staticmethod(lambda a, b: 50)})()},
    )()
    attacker.type_name = "footman"
    attacker.expanded_is_a = ("soldier",)
    attacker.mdg_hit_rate = to_int("100")
    attacker.mdg_hit_rate_vs = {}

    defender = type(
        "D",
        (HitMissMixin, _BuildingTarget),
        {
            "mdg_dodge_rate": 0,
            "rdg_dodge_rate": 0,
            "mdg_dodge_rate_vs": {"footman": 30},
            "rdg_dodge_rate_vs": {},
            "mdg_dodge_rate_on_terrain": (),
            "rdg_dodge_rate_on_terrain": (),
        },
    )()
    defender.notify = lambda *args, **kwargs: None

    # cover 100 - dodge_vs 30 => 70% hit; roll 50 => hit
    assert attacker._hit_or_miss(defender) is True

    defender.mdg_dodge_rate_vs = {"footman": 80}
    # cover 100 - dodge_vs 80 => 20% hit; roll 50 => miss
    assert attacker._hit_or_miss(defender) is False
