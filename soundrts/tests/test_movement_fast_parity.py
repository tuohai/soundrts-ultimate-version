"""验证 movement_fast.future_coords 与原 Python ``_future_coords`` 数值等价。"""
from __future__ import annotations

import random

import pytest


mf = pytest.importorskip(
    "soundrts.worldunit.movement_fast",
    exc_type=ImportError,
    reason="Cython 扩展未编译；运行 `python setup_cython.py --inplace`",
)
from soundrts.lib.nofloat import int_cos_1000, int_sin_1000

VIRTUAL_TIME_INTERVAL = 300  # 与 definitions.py 对齐


def ref_future_coords(x, y, o, actual_speed, rotation, target_d):
    """与 world_movement.py::_future_coords 算法完全一致。"""
    d = actual_speed * VIRTUAL_TIME_INTERVAL // 1000
    if rotation == 0:
        d = min(d, target_d)
    a = o + rotation
    new_x = int(x + d * int_cos_1000(a) // 1000)
    new_y = int(y + d * int_sin_1000(a) // 1000)
    return new_x, new_y


def test_no_rotation_clamped_by_target_d():
    """rotation=0 时 d 被 target_d 限制。"""
    # speed * 300 // 1000 = 30, but target_d = 10
    cy = mf.future_coords(100, 100, 0, 100, 0, 10)
    py = ref_future_coords(100, 100, 0, 100, 0, 10)
    assert cy == py
    # 移动距离 = min(30, 10) = 10，方向 0 -> +x
    assert cy == (110, 100)


def test_no_rotation_d_smaller_than_target():
    """rotation=0 时若 d < target_d，使用 d。"""
    cy = mf.future_coords(100, 100, 0, 100, 0, 1000)
    py = ref_future_coords(100, 100, 0, 100, 0, 1000)
    assert cy == py


def test_rotation_no_clamp():
    """rotation != 0 时不受 target_d 影响。"""
    cy = mf.future_coords(100, 100, 0, 100, 45, 5)
    py = ref_future_coords(100, 100, 0, 100, 45, 5)
    assert cy == py


def test_negative_rotation():
    cy = mf.future_coords(100, 100, 0, 100, -45, 1000)
    py = ref_future_coords(100, 100, 0, 100, -45, 1000)
    assert cy == py


def test_wrap_around_orientation():
    """orientation + rotation 可能超出 ±360。"""
    cy = mf.future_coords(100, 100, 350, 100, 20, 1000)  # a = 370
    py = ref_future_coords(100, 100, 350, 100, 20, 1000)
    assert cy == py


def test_random_parity():
    rng = random.Random(20260526)
    for _ in range(5000):
        x = rng.randint(-100_000, 100_000)
        y = rng.randint(-100_000, 100_000)
        o = rng.randint(-720, 720)
        speed = rng.randint(0, 10_000)
        rotation = rng.choice([0, rng.randint(-180, 180)])
        target_d = rng.randint(0, 10_000)
        cy = mf.future_coords(x, y, o, speed, rotation, target_d)
        py = ref_future_coords(x, y, o, speed, rotation, target_d)
        assert cy == py, (
            f"mismatch at x={x},y={y},o={o},speed={speed},rot={rotation},td={target_d}: "
            f"cy={cy} py={py}"
        )


def test_zero_speed():
    cy = mf.future_coords(100, 100, 90, 0, 0, 1000)
    py = ref_future_coords(100, 100, 90, 0, 0, 1000)
    assert cy == py == (100, 100)


# === D-Phase 2 §3.1 parity: near_enough_to_aim ============================

class _FakePlace:
    def __init__(self, high_ground=False):
        self.high_ground = high_ground


class _FakeUnit:
    """模拟攻击者: 提供 _near_enough_to_aim 需要的所有字段."""
    def __init__(self, x=0, y=0, radius=10, place=None,
                 mdg=0, rdg=0, minimal_damage=0,
                 mdg_minimal_range=0, rdg_minimal_range=0,
                 mdg_minimal_range_vs=None, rdg_minimal_range_vs=None,
                 mdg_projectile=0, rdg_projectile=0,
                 eff_mdg_range=0, eff_rdg_range=0,
                 melee_dmg_vs_target=0, ranged_dmg_vs_target=0):
        self.x = x; self.y = y; self.radius = radius
        self.place = place if place is not None else _FakePlace()
        self.mdg = mdg; self.rdg = rdg
        self.minimal_damage = minimal_damage
        self.mdg_minimal_range = mdg_minimal_range
        self.rdg_minimal_range = rdg_minimal_range
        self.mdg_minimal_range_vs = mdg_minimal_range_vs or {}
        self.rdg_minimal_range_vs = rdg_minimal_range_vs or {}
        self.mdg_projectile = mdg_projectile
        self.rdg_projectile = rdg_projectile
        self._eff_mdg_range = eff_mdg_range
        self._eff_rdg_range = eff_rdg_range
        self._melee_dmg = melee_dmg_vs_target
        self._ranged_dmg = ranged_dmg_vs_target

    def get_effective_mdg_range(self, target):
        return self._eff_mdg_range

    def get_effective_rdg_range(self, target):
        return self._eff_rdg_range

    def _get_melee_damage_vs(self, target):
        return self._melee_dmg

    def _get_ranged_damage_vs(self, target):
        return self._ranged_dmg


class _FakeAimTarget:
    def __init__(self, x=0, y=0, radius=10, place=None, airground_type="ground",
                 type_name="orc", expanded_is_a=()):
        self.x = x; self.y = y; self.radius = radius
        self.place = place if place is not None else _FakePlace()
        self.airground_type = airground_type
        self.type_name = type_name
        self.expanded_is_a = expanded_is_a


def ref_near_enough_to_aim(self, target):
    """与 world_movement.py:_py_near_enough_to_aim 等价的 Python 参考."""
    self_place = self.place
    target_place = target.place
    if (self_place is not None and target_place is not None
            and not self_place.high_ground and target_place.high_ground
            and target.airground_type == "ground"
            and self.mdg_projectile != 1 and self.rdg_projectile != 1):
        return False
    dx = self.x - target.x
    dy = self.y - target.y
    dist2 = dx * dx + dy * dy
    collision = self.radius + target.radius
    DEFAULT_ATTACK_RANGE = 175

    melee_damage = self._get_melee_damage_vs(target)
    ranged_damage = self._get_ranged_damage_vs(target)
    minimal_damage = self.minimal_damage

    can_use_mdg = False
    if melee_damage > 0 or minimal_damage > 0:
        eff_range = self.get_effective_mdg_range(target)
        max_range = eff_range if eff_range > 0 else DEFAULT_ATTACK_RANGE
        max_r2 = (max_range + collision) ** 2
        min_range = self.mdg_minimal_range
        if target.type_name in self.mdg_minimal_range_vs:
            min_range += self.mdg_minimal_range_vs[target.type_name]
        else:
            for t in target.expanded_is_a:
                if t in self.mdg_minimal_range_vs:
                    min_range += self.mdg_minimal_range_vs[t]
                    break
        if min_range > 0:
            min_r2 = (min_range + collision) ** 2
            if min_r2 <= dist2 <= max_r2:
                can_use_mdg = True
        else:
            if dist2 <= max_r2:
                can_use_mdg = True

    can_use_rdg = False
    if ranged_damage > 0 or minimal_damage > 0:
        eff_range = self.get_effective_rdg_range(target)
        max_range = eff_range if eff_range > 0 else DEFAULT_ATTACK_RANGE
        max_r2 = (max_range + collision) ** 2
        min_range = self.rdg_minimal_range
        if target.type_name in self.rdg_minimal_range_vs:
            min_range += self.rdg_minimal_range_vs[target.type_name]
        else:
            for t in target.expanded_is_a:
                if t in self.rdg_minimal_range_vs:
                    min_range += self.rdg_minimal_range_vs[t]
                    break
        if min_range > 0:
            min_r2 = (min_range + collision) ** 2
            if min_r2 <= dist2 <= max_r2:
                can_use_rdg = True
        else:
            if dist2 <= max_r2:
                can_use_rdg = True

    return can_use_mdg or can_use_rdg


class TestNearEnoughToAim:
    def test_in_range_melee(self):
        a = _FakeUnit(x=0, y=0, mdg=10, eff_mdg_range=100,
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=50, y=0)
        assert mf.near_enough_to_aim(a, t) is True

    def test_out_of_range(self):
        a = _FakeUnit(x=0, y=0, mdg=10, eff_mdg_range=100,
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=200, y=0)
        assert mf.near_enough_to_aim(a, t) is False

    def test_default_range_when_eff_range_zero(self):
        """eff_range = 0 时使用 DEFAULT_ATTACK_RANGE=175."""
        a = _FakeUnit(x=0, y=0, radius=10, mdg=10, eff_mdg_range=0,
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=150, y=0, radius=10)
        # max_r = 175+10+10=195, dist=150 -> in range
        assert mf.near_enough_to_aim(a, t) is True

    def test_low_to_high_ground_blocked(self):
        sp = _FakePlace(high_ground=False)
        tp = _FakePlace(high_ground=True)
        a = _FakeUnit(x=0, y=0, place=sp, mdg=10, eff_mdg_range=100,
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=50, y=0, place=tp, airground_type="ground")
        assert mf.near_enough_to_aim(a, t) is False
        # 但若攻击者有 mdg_projectile, 可以攻击高地
        a.mdg_projectile = 1
        assert mf.near_enough_to_aim(a, t) is True

    def test_air_target_ignores_high_ground(self):
        sp = _FakePlace(high_ground=False)
        tp = _FakePlace(high_ground=True)
        a = _FakeUnit(x=0, y=0, place=sp, mdg=10, eff_mdg_range=100,
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=50, y=0, place=tp, airground_type="air")
        assert mf.near_enough_to_aim(a, t) is True

    def test_min_range_blocks_close(self):
        """min_range > 0 时, 太近不可攻击."""
        a = _FakeUnit(x=0, y=0, mdg=10, eff_mdg_range=200,
                     mdg_minimal_range=50, melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=10, y=0)
        # min_r2 = (50+20)^2 = 4900, dist2 = 100 < 4900 -> blocked
        assert mf.near_enough_to_aim(a, t) is False
        # 远一点应该可以
        t.x = 80
        # dist2 = 6400, min_r2 = 4900, max_r = (200+20)^2 = 48400
        assert mf.near_enough_to_aim(a, t) is True

    def test_no_damage_returns_false(self):
        a = _FakeUnit(x=0, y=0, mdg=0, rdg=0, minimal_damage=0,
                     melee_dmg_vs_target=0, ranged_dmg_vs_target=0)
        t = _FakeAimTarget(x=10, y=0)
        assert mf.near_enough_to_aim(a, t) is False

    def test_minimal_damage_still_attacks(self):
        a = _FakeUnit(x=0, y=0, mdg=0, minimal_damage=1, eff_mdg_range=100,
                     melee_dmg_vs_target=0)
        t = _FakeAimTarget(x=50, y=0)
        assert mf.near_enough_to_aim(a, t) is True

    def test_ranged_works_when_melee_zero(self):
        a = _FakeUnit(x=0, y=0, mdg=0, rdg=10, eff_rdg_range=200,
                     ranged_dmg_vs_target=10)
        t = _FakeAimTarget(x=100, y=0)
        assert mf.near_enough_to_aim(a, t) is True

    def test_minimal_range_vs_type_name(self):
        """min_range_vs 应增加最小射程."""
        a = _FakeUnit(x=0, y=0, mdg=10, eff_mdg_range=200,
                     mdg_minimal_range=20,
                     mdg_minimal_range_vs={"orc": 50},
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=40, y=0, type_name="orc")
        # min_range = 20+50 = 70, min_r2 = (70+20)^2 = 8100
        # dist2 = 1600 < 8100 -> blocked
        assert mf.near_enough_to_aim(a, t) is False

    def test_minimal_range_vs_expanded_is_a(self):
        a = _FakeUnit(x=0, y=0, mdg=10, eff_mdg_range=200,
                     mdg_minimal_range=20,
                     mdg_minimal_range_vs={"humanoid": 50},
                     melee_dmg_vs_target=10)
        t = _FakeAimTarget(x=40, y=0, type_name="warlord",
                          expanded_is_a=("humanoid",))
        # 同上
        assert mf.near_enough_to_aim(a, t) is False

    def test_random_parity(self):
        rng = random.Random(20260602)
        type_pool = ["orc", "elf", "human"]
        for _ in range(2000):
            sp_hg = rng.choice([False, True, False, False])
            tp_hg = rng.choice([False, True, False, False])
            ag = rng.choice(["ground", "air"])
            a = _FakeUnit(
                x=rng.randint(-1000, 1000),
                y=rng.randint(-1000, 1000),
                radius=rng.randint(0, 30),
                place=_FakePlace(high_ground=sp_hg),
                mdg=rng.randint(0, 50),
                rdg=rng.randint(0, 50),
                minimal_damage=rng.choice([0, 0, 0, rng.randint(0, 5)]),
                mdg_minimal_range=rng.randint(0, 60),
                rdg_minimal_range=rng.randint(0, 60),
                mdg_minimal_range_vs={t: rng.randint(-20, 20)
                                       for t in rng.sample(type_pool, rng.randint(0, 2))},
                rdg_minimal_range_vs={t: rng.randint(-20, 20)
                                       for t in rng.sample(type_pool, rng.randint(0, 2))},
                mdg_projectile=rng.choice([0, 1]),
                rdg_projectile=rng.choice([0, 1]),
                eff_mdg_range=rng.randint(0, 300),
                eff_rdg_range=rng.randint(0, 300),
                melee_dmg_vs_target=rng.randint(0, 30),
                ranged_dmg_vs_target=rng.randint(0, 30),
            )
            t = _FakeAimTarget(
                x=rng.randint(-1000, 1000),
                y=rng.randint(-1000, 1000),
                radius=rng.randint(0, 30),
                place=_FakePlace(high_ground=tp_hg),
                airground_type=ag,
                type_name=rng.choice(type_pool),
                expanded_is_a=tuple(rng.sample(type_pool, rng.randint(0, 2))),
            )
            cy = mf.near_enough_to_aim(a, t)
            py = ref_near_enough_to_aim(a, t)
            assert cy == py, (
                f"mismatch: ax={a.x},ay={a.y},tx={t.x},ty={t.y}, cy={cy} py={py}"
            )
