"""验证 ``soundrts.combat.combat_fast``（Cython）与纯 Python 参考实现一致。

战斗算术热点的等价性测试。RTS desync 容忍度 = 0，必须 byte-exact。
"""
from __future__ import annotations

import math
import random

import pytest


# 预加载 worldunit 以解开 combat 包的循环导入：
# combat/__init__.py 在 import 时会触发 worldunit 链，而 worldunit/worldcreature.py
# 又会 import combat.CreatureAttack，所以必须先让 worldunit 完成 import。
# 这是项目既有的导入循环，非本 Phase 引入。
import soundrts.worldunit  # noqa: F401


cf = pytest.importorskip(
    "soundrts.combat.combat_fast",
    exc_type=ImportError,
    reason="Cython 扩展未编译；运行 `python setup_cython.py --inplace`",
)


# --- 纯 Python 参考实现（与 combat_fast.pyx 数学等价） --------------------

def ref_resolve_vs(vs_dict, type_name, expanded_is_a):
    if vs_dict is None:
        return None
    if type_name is not None:
        v = vs_dict.get(type_name)
        if v is not None:
            return v
    if expanded_is_a is None:
        return None
    for t in expanded_is_a:
        v = vs_dict.get(t)
        if v is not None:
            return v
    return None


def ref_range_check(dist2, eff_range, min_range, collision):
    max_range2 = (eff_range + collision) ** 2
    if min_range > 0:
        min_range2 = (min_range + collision) ** 2
        if dist2 < min_range2:
            return False
    return dist2 <= max_range2


def ref_apply_piercing(base_defense, piercing, piercing_resistance):
    return max(0, base_defense - max(0, piercing - piercing_resistance))


def ref_calc_actual_damage(damage, defense, minimal_damage, forced_damage):
    actual = max(1, damage - defense)
    if minimal_damage > 0:
        actual = max(actual, minimal_damage)
    if forced_damage > 0:
        actual = forced_damage
    return actual


def ref_calc_splash_factor(dist2, splash_range, decay_min):
    if splash_range <= 0:
        return 0.0
    decay_range = 1.0 - decay_min
    return 1.0 - (math.sqrt(dist2) / splash_range * decay_range)


def ref_calc_hit_chance(base_cover, specific_cover_bonus, terrain_cover_mod,
                        base_dodge, specific_dodge_bonus, terrain_dodge_mod):
    cover = base_cover + specific_cover_bonus + terrain_cover_mod
    dodge = base_dodge + specific_dodge_bonus + terrain_dodge_mod
    hit = cover - dodge
    return max(0, min(100, hit))


# --- 测试 -----------------------------------------------------------------


class TestResolveVsLookup:
    def test_hit_type_name(self):
        d = {"orc": 10, "elf": 20}
        assert cf.resolve_vs_lookup(d, "orc", []) == 10

    def test_hit_expanded_is_a(self):
        d = {"orc": 10, "elf": 20}
        assert cf.resolve_vs_lookup(d, "warlord", ["humanoid", "elf"]) == 20

    def test_no_match(self):
        d = {"orc": 10}
        assert cf.resolve_vs_lookup(d, "human", ["beast"]) is None

    def test_empty_dict(self):
        assert cf.resolve_vs_lookup({}, "orc", ["humanoid"]) is None

    def test_none_type_name(self):
        d = {"orc": 10}
        assert cf.resolve_vs_lookup(d, None, ["orc"]) == 10

    def test_none_expanded_is_a(self):
        d = {"orc": 10}
        assert cf.resolve_vs_lookup(d, "orc", None) == 10
        assert cf.resolve_vs_lookup(d, "human", None) is None

    def test_zero_value_returns_zero_not_none(self):
        """vs_dict 中 0 是合法值，不应被当作 None 跳过。"""
        d = {"orc": 0, "elf": 5}
        assert cf.resolve_vs_lookup(d, "orc", []) == 0

    def test_random_parity(self):
        rng = random.Random(20260526)
        type_pool = ["orc", "elf", "human", "dwarf", "beast", "demon", "fae"]
        for _ in range(1000):
            d = {t: rng.randint(-50, 50) for t in rng.sample(type_pool, rng.randint(0, 5))}
            tn = rng.choice(type_pool + [None])
            ex = rng.sample(type_pool, rng.randint(0, 4))
            assert cf.resolve_vs_lookup(d, tn, ex) == ref_resolve_vs(d, tn, ex)


class TestRangeCheck:
    def test_in_range_simple(self):
        # max_range2 = (10+5)^2 = 225; dist2 = 100 <= 225
        assert cf.range_check(100, 10, 0, 5) is True

    def test_out_of_range(self):
        assert cf.range_check(300, 10, 0, 5) is False

    def test_at_boundary(self):
        assert cf.range_check(225, 10, 0, 5) is True  # equals max
        assert cf.range_check(226, 10, 0, 5) is False

    def test_min_range_blocks(self):
        # min_range2 = (5+1)^2 = 36; dist2 = 35 < 36 -> False
        assert cf.range_check(35, 10, 5, 1) is False
        assert cf.range_check(36, 10, 5, 1) is True

    def test_min_range_zero_ignored(self):
        assert cf.range_check(0, 10, 0, 5) is True

    def test_random_parity(self):
        rng = random.Random(20260527)
        for _ in range(2000):
            d2 = rng.randint(0, 1_000_000)
            er = rng.randint(0, 100)
            mr = rng.randint(0, 50)
            col = rng.randint(0, 20)
            assert cf.range_check(d2, er, mr, col) == ref_range_check(d2, er, mr, col)


class TestApplyPiercing:
    def test_no_pierce_no_change(self):
        assert cf.apply_piercing(50, 0, 0) == 50
        assert cf.apply_piercing(50, 10, 20) == 50  # resist > pierce

    def test_partial_pierce(self):
        # net_pierce = 20 - 5 = 15; 50 - 15 = 35
        assert cf.apply_piercing(50, 20, 5) == 35

    def test_pierce_overwhelms(self):
        # net_pierce = 100; 10 - 100 < 0 -> 0
        assert cf.apply_piercing(10, 100, 0) == 0

    def test_random_parity(self):
        rng = random.Random(20260528)
        for _ in range(2000):
            d = rng.randint(0, 1000)
            p = rng.randint(0, 1000)
            r = rng.randint(0, 1000)
            assert cf.apply_piercing(d, p, r) == ref_apply_piercing(d, p, r)


class TestCalcActualDamage:
    def test_normal_case(self):
        assert cf.calc_actual_damage(50, 30, 0, 0) == 20

    def test_floor_at_1(self):
        assert cf.calc_actual_damage(20, 30, 0, 0) == 1

    def test_minimal_damage_floor(self):
        assert cf.calc_actual_damage(50, 30, 25, 0) == 25  # would be 20, but min is 25

    def test_minimal_damage_no_effect_if_larger(self):
        assert cf.calc_actual_damage(50, 30, 10, 0) == 20  # 20 > min 10

    def test_forced_damage_overrides(self):
        assert cf.calc_actual_damage(50, 30, 25, 99) == 99

    def test_random_parity(self):
        rng = random.Random(20260529)
        for _ in range(2000):
            damage = rng.randint(0, 1000)
            defense = rng.randint(0, 500)
            minimal = rng.randint(0, 100)
            forced = rng.choice([0, 0, 0, rng.randint(1, 500)])
            assert (
                cf.calc_actual_damage(damage, defense, minimal, forced)
                == ref_calc_actual_damage(damage, defense, minimal, forced)
            )


class TestCalcHitChance:
    def test_basic(self):
        assert cf.calc_hit_chance(80, 0, 0, 20, 0, 0) == 60

    def test_clamp_low(self):
        assert cf.calc_hit_chance(0, 0, 0, 200, 0, 0) == 0

    def test_clamp_high(self):
        assert cf.calc_hit_chance(200, 50, 0, 0, 0, 0) == 100

    def test_random_parity(self):
        rng = random.Random(20260530)
        for _ in range(2000):
            bc = rng.randint(0, 200)
            sc = rng.randint(-50, 50)
            tc = rng.randint(-50, 50)
            bd = rng.randint(0, 100)
            sd = rng.randint(-50, 50)
            td = rng.randint(-50, 50)
            assert (
                cf.calc_hit_chance(bc, sc, tc, bd, sd, td)
                == ref_calc_hit_chance(bc, sc, tc, bd, sd, td)
            )


class TestCalcSplashFactor:
    def test_at_epicenter(self):
        assert cf.calc_splash_factor(0, 100, 0.5) == 1.0

    def test_at_radius(self):
        # dist=100, range=100, decay_range=0.5 -> 1 - 1*0.5 = 0.5
        assert cf.calc_splash_factor(10000, 100, 0.5) == 0.5

    def test_zero_range_guard(self):
        assert cf.calc_splash_factor(100, 0, 0.5) == 0.0

    def test_random_parity(self):
        rng = random.Random(20260531)
        for _ in range(2000):
            dist2 = rng.randint(0, 1_000_000)
            sr = rng.randint(1, 1000)
            dm = rng.random()
            cy = cf.calc_splash_factor(dist2, sr, dm)
            py = ref_calc_splash_factor(dist2, sr, dm)
            assert cy == pytest.approx(py, rel=1e-12, abs=1e-12)


class TestClampAndDescale:
    @pytest.mark.parametrize("inp,expected", [
        (-5, 0), (0, 0), (50, 50), (100, 100), (200, 100),
    ])
    def test_clamp_0_100(self, inp, expected):
        assert cf.clamp_0_100(inp) == expected

    def test_descale_below_threshold(self):
        # value <= threshold 不缩放
        assert cf.descale_if_internal(50, 100, 1000) == 50
        assert cf.descale_if_internal(100, 100, 1000) == 100

    def test_descale_above_threshold(self):
        # value > threshold 走 // divisor
        assert cf.descale_if_internal(50000, 100, 1000) == 50


class TestDotProduct:
    def test_basic(self):
        assert cf.dot_product_2d(3, 4, 5, 6) == 39  # 15+24

    def test_negative(self):
        assert cf.dot_product_2d(-1, -2, 3, 4) == -11


class TestSquareOfDistance:
    def test_basic(self):
        assert cf.square_of_distance(0, 0, 3, 4) == 25

    def test_matches_nofloat(self):
        from soundrts.lib import nofloat
        for x1, y1, x2, y2 in [(0, 0, 7, 24), (-5, -5, 5, 5), (100, 200, 100, 200)]:
            assert (
                cf.square_of_distance(x1, y1, x2, y2)
                == nofloat.square_of_distance(x1, y1, x2, y2)
            )


# === D-Phase 2 §3.2 parity: compute_damage_vs =============================

class _FakeArmor:
    """模拟 Armor 实例: 含 expanded_is_a / is_a."""
    def __init__(self, expanded_is_a=(), is_a=()):
        self.expanded_is_a = expanded_is_a
        self.is_a = is_a


class _FakeTarget:
    """模拟 target 实体: 含 type_name / expanded_is_a / armor (str name) /
    _armor_instance (Armor 对象 or None).
    """
    def __init__(self, type_name=None, expanded_is_a=(), armor=None,
                 _armor_instance=None):
        self.type_name = type_name
        self.expanded_is_a = expanded_is_a
        self.armor = armor
        self._armor_instance = _armor_instance


def ref_compute_damage_vs(base_dg, dg_vs, target):
    """纯 Python 参考实现: 与 damage_calculation._py_get_melee_damage_vs 一致."""
    # 第一层 + 第二层 (resolve_vs_lookup)
    v = ref_resolve_vs(dg_vs, target.type_name, target.expanded_is_a)
    if v is not None:
        return base_dg + v
    # 第三层: armor name
    armor_name = target.armor
    if armor_name and armor_name in dg_vs:
        return base_dg + dg_vs[armor_name]
    # 第四层: armor instance
    armor = target._armor_instance
    if armor is not None:
        for armor_type in armor.expanded_is_a:
            if armor_type in dg_vs:
                return base_dg + dg_vs[armor_type]
        for armor_type in armor.is_a:
            if armor_type in dg_vs:
                return base_dg + dg_vs[armor_type]
    return base_dg


class TestComputeDamageVs:
    def test_hit_type_name(self):
        t = _FakeTarget(type_name="orc", expanded_is_a=())
        assert cf.compute_damage_vs(10, {"orc": 5}, t) == 15

    def test_hit_expanded_is_a(self):
        t = _FakeTarget(type_name="warlord", expanded_is_a=("humanoid", "orc"))
        assert cf.compute_damage_vs(10, {"orc": 7}, t) == 17

    def test_hit_armor_name(self):
        t = _FakeTarget(type_name="x", expanded_is_a=(), armor="plate")
        assert cf.compute_damage_vs(10, {"plate": 3}, t) == 13

    def test_hit_armor_expanded_is_a(self):
        armor = _FakeArmor(expanded_is_a=("heavy",), is_a=("armor",))
        t = _FakeTarget(type_name="x", expanded_is_a=(), armor="plate",
                       _armor_instance=armor)
        assert cf.compute_damage_vs(10, {"heavy": 2}, t) == 12

    def test_hit_armor_is_a_fallback(self):
        armor = _FakeArmor(expanded_is_a=("heavy",), is_a=("armor",))
        t = _FakeTarget(type_name="x", expanded_is_a=(), armor="plate",
                       _armor_instance=armor)
        assert cf.compute_damage_vs(10, {"armor": 1}, t) == 11

    def test_no_match_returns_base(self):
        t = _FakeTarget(type_name="x", expanded_is_a=("y",), armor=None)
        assert cf.compute_damage_vs(10, {"z": 99}, t) == 10

    def test_empty_dict(self):
        t = _FakeTarget(type_name="orc", expanded_is_a=("humanoid",))
        assert cf.compute_damage_vs(50, {}, t) == 50

    def test_zero_vs_returns_base_plus_zero(self):
        """vs adjustment 为 0 仍命中且返回 base + 0 = base."""
        t = _FakeTarget(type_name="orc")
        assert cf.compute_damage_vs(10, {"orc": 0}, t) == 10

    def test_negative_vs(self):
        """vs adjustment 可以是负数 (减伤)."""
        t = _FakeTarget(type_name="orc")
        assert cf.compute_damage_vs(20, {"orc": -5}, t) == 15

    def test_random_parity(self):
        rng = random.Random(20260601)
        type_pool = ["orc", "elf", "human", "dwarf", "beast"]
        armor_pool = ["plate", "leather", "robe", None]
        for _ in range(1000):
            d = {t: rng.randint(-30, 30)
                 for t in rng.sample(type_pool, rng.randint(0, 4))}
            tn = rng.choice(type_pool + [None])
            ex = tuple(rng.sample(type_pool, rng.randint(0, 3)))
            armor_name = rng.choice(armor_pool)
            if rng.random() < 0.3:
                armor = _FakeArmor(
                    expanded_is_a=tuple(rng.sample(type_pool, rng.randint(0, 2))),
                    is_a=tuple(rng.sample(type_pool, rng.randint(0, 2))),
                )
            else:
                armor = None
            t = _FakeTarget(type_name=tn, expanded_is_a=ex,
                           armor=armor_name, _armor_instance=armor)
            base = rng.randint(0, 100)
            assert (
                cf.compute_damage_vs(base, d, t)
                == ref_compute_damage_vs(base, d, t)
            )
