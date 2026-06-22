"""AI 克制目标选择：smart_units 下优先攻击 mdg_vs/rdg_vs 加成目标，并识别 is_a 继承。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401 — 解开循环导入

from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.combat.targeting import TargetingMixin


class _MockTarget:
    def __init__(self, type_name, expanded_is_a=(), menace=100, x=0, y=0, uid=1):
        self.type_name = type_name
        self.expanded_is_a = expanded_is_a
        self.menace = menace
        self.x = x
        self.y = y
        self.id = uid
        self.hp = 100
        self.place = object()


class _Attacker(DamageCalculationMixin):
    def __init__(self, mdg_vs=None, rdg_vs=None):
        self.mdg = 6
        self.rdg = 0
        self.mdg_vs = mdg_vs or {}
        self.rdg_vs = rdg_vs or {}


class _Chooser(TargetingMixin, DamageCalculationMixin):
    def __init__(self, smart_units, counter_skill=100, mdg_vs=None, rdg_vs=None):
        self.mdg = 6
        self.rdg = 4
        self.mdg_vs = mdg_vs or {}
        self.rdg_vs = rdg_vs or {}
        self.x = 0
        self.y = 0
        self.player = types.SimpleNamespace(
            smart_units=smart_units, counter_skill=counter_skill
        )
        self.attacked = []

    def can_attack(self, other):
        return True

    def _attack(self, target):
        self.attacked.append(target)


def test_vs_bonus_matches_expanded_is_a():
    """footman mdg_vs cavalry 应克制 is_a 骑兵 的骆驼兵。"""
    footman = _Attacker(mdg_vs={"cavalry": 13})
    camel = _MockTarget("camel", expanded_is_a=("cavalry",))
    assert footman._get_vs_damage_bonus(camel) == 13


def test_vs_bonus_prefers_best_of_mdg_and_rdg():
    archer = _Attacker(mdg_vs={}, rdg_vs={"footman": 7})
    footman = _MockTarget("footman")
    assert archer._get_vs_damage_bonus(footman) == 7


def test_choose_enemy_prefers_counter_when_smart():
    knight = _Chooser(smart_units=True, counter_skill=100, mdg_vs={"archer": 12})
    archer = _MockTarget("archer", menace=50, uid=1)
    footman = _MockTarget("footman", menace=200, uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        smart_units = True
        counter_skill = 100

        @staticmethod
        def known_enemies(place):
            return [archer, footman]

    knight.player = _Player()
    knight._choose_enemy(_Place())

    assert knight.attacked == [archer]


def test_choose_enemy_low_counter_skill_favors_menace():
    archer_unit = _Chooser(
        smart_units=True, counter_skill=25, mdg_vs={"spearmen": 9, "footman": 7}
    )
    spearmen = _MockTarget("spearmen", menace=50, uid=1)
    footman = _MockTarget("footman", menace=200, uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        smart_units = True
        counter_skill = 25

        @staticmethod
        def known_enemies(place):
            return [spearmen, footman]

    archer_unit.player = _Player()
    archer_unit._choose_enemy(_Place())

    assert archer_unit.attacked == [footman]


def test_choose_enemy_uses_menace_when_not_smart():
    knight = _Chooser(smart_units=False, counter_skill=100, mdg_vs={"archer": 12})
    archer = _MockTarget("archer", menace=50, uid=1)
    footman = _MockTarget("footman", menace=200, uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        @staticmethod
        def known_enemies(place):
            return [archer, footman]

    knight.player = _Player()
    knight.player.smart_units = False
    knight._choose_enemy(_Place())

    assert knight.attacked == [footman]
