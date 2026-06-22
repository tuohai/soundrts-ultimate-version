"""验证 Phase 2.2 的 Mixin 改造：用 combat_fast 重新接线后，
``DamageCalculationMixin._calculate_actual_damage`` 等关键方法仍与"原算法"等价。

通过构造最小化的 mock attacker / target 对象，直接调用 Mixin 方法。
不实例化完整 Creature 类（避免触发 World/Player 的复杂依赖）。
"""
from __future__ import annotations

import pytest

# 解开 combat 包的循环导入（见 test_combat_fast_parity.py 注释）
import soundrts.worldunit  # noqa: F401

from soundrts.combat.damage_calculation import DamageCalculationMixin


class _MockTarget:
    """最小化的目标对象，提供 Mixin 需要的属性。"""

    # Round 4: 真实 Creature 的 _armor_instance 在 worldbase.__init__ 中初始化,
    # _get_melee_damage_vs 直接读 target._armor_instance (无 hasattr fallback).
    # Mock 也对齐这个默认值.
    _armor_instance = None
    # D-Phase 2: armor 已上提到 Entity class default (None); damage_calculation
    # 直接读 target.armor, mock 必须也对齐.
    armor = None

    def __init__(self, type_name: str, expanded_is_a=(), armor_name=None):
        self.type_name = type_name
        self.expanded_is_a = expanded_is_a
        self._armor_name = armor_name
        self.armor = armor_name

    def get_current_armor_name(self):
        return self._armor_name


class _MockAttackerWithDamage(DamageCalculationMixin):
    """注入 Mixin 所需的 mdg / mdg_vs / rdg / rdg_vs 等字段。"""

    def __init__(self):
        self.mdg = 100
        self.mdg_vs = {"orc": 20, "humanoid": 10}
        self.rdg = 80
        self.rdg_vs = {"elf": 15}
        # 防御相关
        self.mdf = 30
        self.mdf_vs = {"dragon": 5}
        self.rdf = 25
        self.rdf_vs = {}


class TestGetDamageVs:
    def test_melee_hit_type_name(self):
        a = _MockAttackerWithDamage()
        t = _MockTarget("orc", expanded_is_a=())
        assert a._get_melee_damage_vs(t) == 100 + 20

    def test_melee_hit_expanded_is_a(self):
        a = _MockAttackerWithDamage()
        t = _MockTarget("warlord", expanded_is_a=("humanoid",))
        assert a._get_melee_damage_vs(t) == 100 + 10

    def test_melee_no_vs(self):
        a = _MockAttackerWithDamage()
        t = _MockTarget("dwarf", expanded_is_a=("beast",))
        assert a._get_melee_damage_vs(t) == 100

    def test_ranged_hit(self):
        a = _MockAttackerWithDamage()
        t = _MockTarget("elf", expanded_is_a=())
        assert a._get_ranged_damage_vs(t) == 80 + 15

    def test_ranged_no_vs(self):
        a = _MockAttackerWithDamage()
        t = _MockTarget("orc", expanded_is_a=())
        assert a._get_ranged_damage_vs(t) == 80


class _MockAttackerForDefense:
    """模拟攻击者，供防守端 _get_*_defense_vs 测试用。"""

    def __init__(self, type_name="orc", expanded_is_a=()):
        self.type_name = type_name
        self.expanded_is_a = expanded_is_a


class TestGetDefenseVs:
    def test_melee_defense_dragon_hit(self):
        defender = _MockAttackerWithDamage()
        attacker = _MockAttackerForDefense("dragon", ())
        assert defender._get_melee_defense_vs(attacker) == 30 + 5

    def test_melee_defense_no_vs(self):
        defender = _MockAttackerWithDamage()
        attacker = _MockAttackerForDefense("orc", ())
        assert defender._get_melee_defense_vs(attacker) == 30


class _MockTargetForDamage(DamageCalculationMixin):
    """供 _calculate_actual_damage 测试用——既是 target 又是 Mixin host。"""

    def __init__(self, mdf=20, rdf=15):
        self.mdg_vs = {}
        self.rdg_vs = {}
        self.mdf = mdf
        self.mdf_vs = {}
        self.rdf = rdf
        self.rdf_vs = {}
        self.mdg = 0
        self.rdg = 0


class _SimpleAttacker:
    type_name = "swordsman"
    expanded_is_a = ()
    minimal_damage = 0
    forced_damage = 0
    # 默认无远程
    # rdg_range 未设置 -> is_melee=True


class TestCalculateActualDamage:
    def test_basic_melee_damage(self):
        target = _MockTargetForDamage(mdf=20, rdf=15)
        attacker = _SimpleAttacker()
        # damage=50, defense=20 (melee) -> 30
        assert target._calculate_actual_damage(50, attacker) == 30

    def test_damage_floor_at_1(self):
        target = _MockTargetForDamage(mdf=100, rdf=15)
        attacker = _SimpleAttacker()
        # damage=10 - 100 < 0 -> floor 1
        assert target._calculate_actual_damage(10, attacker) == 1

    def test_minimal_damage(self):
        target = _MockTargetForDamage(mdf=20, rdf=15)
        attacker = _SimpleAttacker()
        attacker.minimal_damage = 25
        # would be 30; floor stays 30
        assert target._calculate_actual_damage(50, attacker) == 30
        # would be 10; min 25
        assert target._calculate_actual_damage(30, attacker) == 25

    def test_forced_damage_overrides(self):
        target = _MockTargetForDamage(mdf=20, rdf=15)
        attacker = _SimpleAttacker()
        attacker.forced_damage = 99
        assert target._calculate_actual_damage(50, attacker) == 99

    def test_none_attacker_returns_raw_damage(self):
        target = _MockTargetForDamage(mdf=20)
        assert target._calculate_actual_damage(50, None) == 50


class TestPiercing:
    def test_no_piercing(self):
        target = _MockTargetForDamage(mdf=30)
        attacker = _SimpleAttacker()
        assert target._get_total_melee_defense_vs(attacker) == 30

    def test_with_piercing(self):
        target = _MockTargetForDamage(mdf=30)
        attacker = _SimpleAttacker()
        attacker.mdg_piercing = 10
        # base_defense=30; net pierce = 10 - 0 = 10; reduced = 30 - 10 = 20
        assert target._get_total_melee_defense_vs(attacker) == 20

    def test_piercing_with_resist(self):
        target = _MockTargetForDamage(mdf=30)
        target.mdf_piercing_vs = {"swordsman": 5}
        attacker = _SimpleAttacker()
        attacker.mdg_piercing = 10
        # net pierce = 10 - 5 = 5; reduced = 30 - 5 = 25
        assert target._get_total_melee_defense_vs(attacker) == 25
