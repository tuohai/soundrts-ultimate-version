"""并行版 mark_cloaked_parallel 与单线程 mark_cloaked 的等价性测试。

关键：并行版的结果必须与单线程**完全一致**，否则 RTS desync。
单线程版本经过 phase 3 的等价性测试已验证与原 Python 行为相同，
所以这里只需保证 ``mark_cloaked_parallel`` 与 ``mark_cloaked`` 状态等价即可。
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest


# --- 直接加载编译产物 .pyd，绕过 soundrts.options 在导入时解析 sys.argv 的副作用
def _load_world_buckets_fast():
    """直接从 .pyd 加载，避免触发 soundrts/__init__ 的 optparse SystemExit。"""
    root = Path(__file__).resolve().parents[2]
    pyd_glob = list((root / "soundrts" / "world").glob("world_buckets_fast*.pyd"))
    pyd_glob += list((root / "soundrts" / "world").glob("world_buckets_fast*.so"))
    if not pyd_glob:
        pytest.skip("world_buckets_fast 未编译，跳过并行测试")
    spec = importlib.util.spec_from_file_location("world_buckets_fast", pyd_glob[0])
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wbf = _load_world_buckets_fast()


class Unit:
    """最小化模拟 VisibleUnit：只暴露 mark_cloaked 需要的属性。"""

    __slots__ = ("x", "y", "is_cloakable", "is_cloaked")

    def __init__(self, x: int, y: int, is_cloakable: bool, is_cloaked: bool = False):
        self.x = x
        self.y = y
        self.is_cloakable = is_cloakable
        self.is_cloaked = is_cloaked


def _make_units(n: int, seed: int = 0):
    """构造测试用单位列表：约 1/3 可隐身，1/10 已隐身。"""
    import random

    rng = random.Random(seed)
    units = []
    for _ in range(n):
        x = rng.randint(-100_000, 100_000)
        y = rng.randint(-100_000, 100_000)
        is_cloakable = rng.random() < 0.33
        is_cloaked = is_cloakable and rng.random() < 0.1
        units.append(Unit(x, y, is_cloakable, is_cloaked))
    return units


def _snapshot_cloaked(units):
    return [u.is_cloaked for u in units]


def _reset(units, snapshot):
    for u, c in zip(units, snapshot):
        u.is_cloaked = c


@pytest.mark.parametrize("n", [0, 1, 5, 63, 64, 65, 100, 500, 2000])
@pytest.mark.parametrize("seed", [0, 1, 42])
def test_parallel_matches_serial(n, seed):
    """并行版与单线程版必须产出完全相同的 is_cloaked 最终状态。"""
    units = _make_units(n, seed)
    initial = _snapshot_cloaked(units)

    cx, cy = 0, 0
    radius2 = 50_000 * 50_000

    # 单线程版
    serial_count = wbf.mark_cloaked(units, cx, cy, radius2)
    serial_state = _snapshot_cloaked(units)

    # 重置后跑并行版（默认线程数）
    _reset(units, initial)
    parallel_count = wbf.mark_cloaked_parallel(units, cx, cy, radius2, 0)
    parallel_state = _snapshot_cloaked(units)
    assert serial_count == parallel_count, f"count 不一致 n={n} seed={seed}"
    assert serial_state == parallel_state, f"状态不一致 n={n} seed={seed}"

    # 显式 1 / 2 / 4 / 8 线程都要等价
    for nt in (1, 2, 4, 8):
        _reset(units, initial)
        c = wbf.mark_cloaked_parallel(units, cx, cy, radius2, nt)
        s = _snapshot_cloaked(units)
        assert c == serial_count, f"线程数={nt} count 不一致"
        assert s == serial_state, f"线程数={nt} 状态不一致"


def test_parallel_does_not_uncloak():
    """已经 cloaked 的单位即使在范围外也不被 uncloak（不写 False）。"""
    units = [
        Unit(1_000_000, 1_000_000, is_cloakable=True, is_cloaked=True),
        Unit(0, 0, is_cloakable=True, is_cloaked=False),
    ]
    wbf.mark_cloaked_parallel(units, 0, 0, 100 * 100, 4)
    assert units[0].is_cloaked is True
    assert units[1].is_cloaked is True


def test_parallel_skips_non_cloakable():
    units = [
        Unit(0, 0, is_cloakable=False, is_cloaked=False),
        Unit(1, 1, is_cloakable=True, is_cloaked=False),
    ]
    count = wbf.mark_cloaked_parallel(units, 0, 0, 100 * 100, 2)
    assert count == 1
    assert units[0].is_cloaked is False
    assert units[1].is_cloaked is True


def test_threshold_helper_exists():
    """get_parallel_threshold 返回一个正整数。"""
    t = wbf.get_parallel_threshold()
    assert isinstance(t, int)
    assert t > 0
