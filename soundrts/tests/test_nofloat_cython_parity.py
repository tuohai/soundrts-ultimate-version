"""验证 ``soundrts.lib.nofloat_fast``（Cython）与纯 Python 参考实现
对所有热点函数的数值结果完全一致。

RTS 必须 deterministic：任何 byte 级偏差都可能触发 multiplayer desync，
所以这里用大批量随机输入做枚举式比对。
"""
from __future__ import annotations

import math
import random

import pytest

from soundrts.lib import nofloat


fast = pytest.importorskip(
    "soundrts.lib.nofloat_fast",
    reason="Cython 扩展未编译；运行 `python setup_cython.py --inplace`",
)


# --- 纯 Python 参考实现（与原 nofloat.py 算法一致，独立复制以防被覆盖） ----

_PRECISION = 1000
_REF_COS = tuple(int(math.cos(math.radians(a)) * _PRECISION) for a in range(360))
_REF_SIN = tuple(int(math.sin(math.radians(a)) * _PRECISION) for a in range(360))
_REF_ACOS = {
    c: int(math.degrees(math.acos(c / 100.0))) for c in range(-100, 101)
}


def ref_int_cos_1000(angle):
    return _REF_COS[angle % 360]


def ref_int_sin_1000(angle):
    return _REF_SIN[angle % 360]


def ref_square_of_distance(x1, y1, x2, y2):
    dx = x2 - x1
    dy = y2 - y1
    return dx * dx + dy * dy


def ref_int_sqrt(x):
    if x < 0:
        return 0
    r = int(math.sqrt(x))
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) < x:
        r += 1
    return r


def ref_int_distance(x1, y1, x2, y2):
    return ref_int_sqrt(ref_square_of_distance(x1, y1, x2, y2))


def ref_int_angle(x1, y1, x2, y2):
    d = ref_int_distance(x1, y1, x2, y2)
    if d == 0:
        return 0
    c = (x2 - x1) * 100 // d
    if c < -100:
        c = -100
    elif c > 100:
        c = 100
    ac = _REF_ACOS[c]
    if y2 - y1 > 0:
        return ac
    return -ac


def ref_to_int(s):
    assert isinstance(s, str)
    return int(float(s) * _PRECISION)


# --- 测试 -----------------------------------------------------------------


@pytest.mark.parametrize("a", list(range(-720, 721, 1)))
def test_int_cos_1000_parity(a):
    """覆盖 ±2 圈的所有整数角度。"""
    assert fast.int_cos_1000(a) == ref_int_cos_1000(a)


@pytest.mark.parametrize("a", list(range(-720, 721, 1)))
def test_int_sin_1000_parity(a):
    assert fast.int_sin_1000(a) == ref_int_sin_1000(a)


def test_int_sqrt_parity_dense():
    """对密集小值与稀疏大值都校验。"""
    for x in list(range(0, 2000)) + [10_000, 1_000_000, 999_999_999, 10**12]:
        assert fast.int_sqrt(x) == ref_int_sqrt(x), f"int_sqrt({x})"


def test_int_sqrt_negative_returns_zero():
    """纯 Python 版本 ``int(math.sqrt(-1))`` 会 ValueError；Cython 版本
    定义为返回 0（调用方从未传入负值，仅做防御）。"""
    assert fast.int_sqrt(-1) == 0


def test_square_of_distance_int64_range():
    """1000x1000 地图 ×1000 PRECISION 下最坏 dx²+dy² ≈ 2e12，必须用 int64。"""
    cases = [
        (0, 0, 1_000_000, 1_000_000),
        (-500_000, -500_000, 500_000, 500_000),
        (0, 0, 0, 0),
        (1, 1, 1, 1),
    ]
    for x1, y1, x2, y2 in cases:
        assert (
            fast.square_of_distance(x1, y1, x2, y2)
            == ref_square_of_distance(x1, y1, x2, y2)
        ), f"square_of_distance{(x1, y1, x2, y2)}"


def test_int_distance_int64_range():
    cases = [
        (0, 0, 3, 4),
        (0, 0, 1_000_000, 1_000_000),
        (-500_000, -500_000, 500_000, 500_000),
        (0, 0, 0, 0),
    ]
    for x1, y1, x2, y2 in cases:
        assert (
            fast.int_distance(x1, y1, x2, y2)
            == ref_int_distance(x1, y1, x2, y2)
        ), f"int_distance{(x1, y1, x2, y2)}"


def test_int_angle_axis_cases():
    """各轴向典型角度。"""
    cases = [
        ((0, 0, 1, 0), 0),
        ((0, 0, 0, 1), 90),
        ((0, 0, -1, 0), -180),  # 历史行为：y2-y1 = 0 走 else 分支返回 -ac
        ((0, 0, 0, -1), -90),
        ((10, 10, 10, 10), 0),
    ]
    for args, expected in cases:
        assert fast.int_angle(*args) == expected, f"int_angle{args}"
        assert ref_int_angle(*args) == expected, f"ref_int_angle{args}"


def test_int_angle_random_parity():
    """随机 5000 个 (x1, y1, x2, y2) 组合，覆盖正负、零距离。"""
    rng = random.Random(20260526)
    for _ in range(5000):
        x1 = rng.randint(-10_000, 10_000)
        y1 = rng.randint(-10_000, 10_000)
        x2 = rng.randint(-10_000, 10_000)
        y2 = rng.randint(-10_000, 10_000)
        a_fast = fast.int_angle(x1, y1, x2, y2)
        a_ref = ref_int_angle(x1, y1, x2, y2)
        assert a_fast == a_ref, f"int_angle{(x1, y1, x2, y2)}: fast={a_fast} ref={a_ref}"


def test_to_int_parity():
    cases = ["0", "1", ".1", ".01", ".001", "10", "100", "1.5", "-1", "-.5"]
    for s in cases:
        assert fast.to_int(s) == ref_to_int(s), f"to_int({s!r})"


def test_to_int_rejects_non_string():
    with pytest.raises(AssertionError):
        fast.to_int(1)  # type: ignore[arg-type]


def test_module_binding_uses_cython():
    """``soundrts.lib.nofloat`` 默认应导入 Cython 加速。"""
    assert nofloat.CYTHON_ACCELERATED is True
    # 顶层 nofloat 重导出后，函数应等价
    assert nofloat.int_cos_1000(45) == fast.int_cos_1000(45)
    assert nofloat.int_distance(0, 0, 7, 24) == 25 == fast.int_distance(0, 0, 7, 24)
