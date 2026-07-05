"""地形攻击/冷却/冲锋修正回归测试。"""
from __future__ import annotations

import soundrts.worldunit  # noqa: F401

from soundrts.combat.attack_action import AttackActionMixin
from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.lib.nofloat import PRECISION


class _MarshPlace:
    type_name = "marsh"

    def type_name_at(self, x, y):
        return "marsh"


class _PlainPlace:
    type_name = "meadow"


class _MockTarget:
    _armor_instance = None
    armor = None
    type_name = "footman"
    expanded_is_a = ()


class _Attacker(DamageCalculationMixin, AttackActionMixin):
    def __init__(self, *, on_marsh=False):
        self.mdg = 6 * PRECISION
        self.rdg = 0
        self.mdg_vs = {}
        self.rdg_vs = {}
        self.mdg_cd = int(1.5 * PRECISION)
        self.rdg_cd = 0
        self.mdg_cd_vs = {}
        self.rdg_cd_vs = {}
        self.charge_mdg = 2 * PRECISION
        self.charge_rdg = 0
        self.charge_mdg_vs = {}
        self.charge_rdg_vs = {}
        self.charge_mdg_cd = 10 * PRECISION
        self.charge_rdg_cd = 0
        self.charge_mdg_dist = 0
        self.charge_rdg_dist = 0
        self.mdg_on_terrain = ("marsh", "-2")
        self.rdg_on_terrain = ()
        self.mdg_cd_on_terrain = ("marsh", "0.5")
        self.rdg_cd_on_terrain = ()
        self.charge_mdg_terrain = ("marsh", "-1")
        self.charge_rdg_terrain = ()
        self.charge_mdg_cd_on_terrain = ("marsh", "2")
        self.charge_rdg_cd_on_terrain = ()
        self.place = _MarshPlace() if on_marsh else _PlainPlace()
        self.x = 0
        self.y = 0
        self.world = type("W", (), {"time": 1000})()


def test_mdg_on_terrain_reduces_damage_on_marsh():
    attacker = _Attacker(on_marsh=True)
    target = _MockTarget()
    assert attacker._get_melee_damage_vs(target) == 4 * PRECISION


def test_mdg_on_terrain_ignored_off_marsh():
    attacker = _Attacker(on_marsh=False)
    target = _MockTarget()
    assert attacker._get_melee_damage_vs(target) == 6 * PRECISION


def test_mdg_cd_on_terrain_increases_cooldown_on_marsh():
    attacker = _Attacker(on_marsh=True)
    target = _MockTarget()
    assert attacker._get_melee_cd_vs(target) == int(2.0 * PRECISION)


def test_charge_mdg_terrain_reduces_charge_damage_on_marsh():
    attacker = _Attacker(on_marsh=True)
    target = _MockTarget()
    # mdg 4 (terrain) + charge 1 (terrain) = 5
    assert attacker._get_charge_damage(target, is_melee=True) == 5 * PRECISION


def test_charge_mdg_cd_on_terrain_increases_charge_cooldown():
    attacker = _Attacker(on_marsh=True)
    attacker._set_charge_cooldown(is_melee=True)
    assert attacker.charge_mdg_next_time == 1000 + 12 * PRECISION


def test_mdg_on_terrain_inherits_parent_terrain_type():
    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        """
def forests
class terrain

def forest
class terrain
is_a forests

def archer
class soldier
mdg 6
mdg_on_terrain forests -2
""",
        base_classes=_get_base_classes(),
    )

    class _ForestPlace:
        type_name = "forest"

        def type_name_at(self, x, y):
            return "forest"

    attacker_cls = rules.unit_class("archer")
    attacker = attacker_cls.__new__(attacker_cls)
    DamageCalculationMixin.__init__(attacker)
    attacker.mdg = 6 * PRECISION
    attacker.mdg_vs = {}
    attacker.mdg_on_terrain = attacker_cls.mdg_on_terrain
    attacker.place = _ForestPlace()
    attacker.x = 0
    attacker.y = 0
    target = _MockTarget()
    assert attacker._get_melee_damage_vs(target) == 4 * PRECISION
