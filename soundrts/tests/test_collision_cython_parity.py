"""验证 ``soundrts.lib.collision_fast``（Cython）与纯 Python 参考实现一致。

CollisionMatrix 在 World pickle 图内，所以本测试也校验：
1. 启用 Cython 加速时数值等价
2. 实例可正确 pickle round-trip（_set 是 Python set，不受影响）
"""
from __future__ import annotations

import pickle
import random

import pytest

from soundrts.lib import collision


cy = pytest.importorskip(
    "soundrts.lib.collision_fast",
    reason="Cython 扩展未编译；运行 `python setup_cython.py --inplace`",
)


SHAPE_REF = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def ref_key(x, y, res, amax):
    return x // res + amax * (y // res)


def ref_shape(x, y, res, amax):
    k = ref_key(x, y, res, amax)
    return {k + a + amax * b for (a, b) in SHAPE_REF}


def test_module_uses_cython():
    assert collision.CYTHON_ACCELERATED is True


def test_compute_key_random_parity():
    """随机 1000 个 (x, y, res, amax) 校验。"""
    rng = random.Random(20260526)
    for _ in range(1000):
        res = rng.choice([1, 2, 4, 8, 16])
        amax = rng.choice([10, 50, 100, 500])
        x = rng.randint(-amax * res, amax * res * 2)
        y = rng.randint(-amax * res, amax * res * 2)
        assert cy.compute_key(x, y, res, amax) == ref_key(x, y, res, amax), (x, y, res, amax)


def test_compute_shape_random_parity():
    rng = random.Random(20260527)
    for _ in range(1000):
        res = rng.choice([1, 2, 4, 8, 16])
        amax = rng.choice([10, 50, 100, 500])
        x = rng.randint(0, amax * res)
        y = rng.randint(0, amax * res)
        assert cy.compute_shape(x, y, res, amax) == ref_shape(x, y, res, amax), (x, y, res, amax)


def test_compute_shape_returns_5_keys():
    s = cy.compute_shape(6, 6, 2, 100)
    assert isinstance(s, set)
    assert len(s) == 5


def test_collision_matrix_full_lifecycle():
    """add/would_collide/remove 完整循环。"""
    m = collision.CollisionMatrix(200, 2)
    assert not m.would_collide(6, 6)
    m.add(6, 6)
    assert m.would_collide(6, 6)
    m.remove(6, 6)
    assert not m.would_collide(6, 6)


def test_collision_matrix_pickle_roundtrip():
    """CollisionMatrix 必须可 pickle —— 它在 World 存档对象图内。"""
    m = collision.CollisionMatrix(200, 2)
    m.add(10, 10)
    m.add(20, 20)
    m.add(50, 50)
    data = pickle.dumps(m)
    m2 = pickle.loads(data)
    assert m2.would_collide(10, 10)
    assert m2.would_collide(20, 20)
    assert m2.would_collide(50, 50)
    assert not m2.would_collide(80, 80)
    assert len(m2._set) == len(m._set)


def test_xy_from_key_inverse_of_key():
    """(0,0)/(50,0)/(0,50)/(20,56) 都应满足 _xy(_key(x, y)) == (x, y)。"""
    m = collision.CollisionMatrix(200, 2)
    for x, y in ((0, 0), (50, 0), (0, 50), (20, 56)):
        k = m._key(x, y)
        assert m._xy(k) == (x, y), f"({x}, {y}) -> key={k} -> xy={m._xy(k)}"


def test_xy_set_round_trip():
    """add(x, y) 后 xy_set 应包含 (x, y) 所在格的代表坐标。"""
    m = collision.CollisionMatrix(200, 2)
    m.add(100, 100)
    coords = set(m.xy_set())
    # 添加 (100, 100) 后 5 格内有该坐标
    assert (100, 100) in coords
