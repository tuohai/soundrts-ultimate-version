"""Parity tests for hybrid C++ ECS Phase 1 (world_ecs_fast)."""

from __future__ import annotations

import importlib.util
import os
from glob import glob

import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_module(basename: str):
    candidates = sorted(
        glob(os.path.join(_HERE, "world", basename + "*.pyd"))
        + glob(os.path.join(_HERE, "world", basename + "*.so"))
    )
    if not candidates:
        return None
    spec = importlib.util.spec_from_file_location(
        "soundrts.world." + basename, candidates[0]
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_ecs = _load_module("world_ecs_fast")
_wbf = _load_module("world_buckets_fast")

if _ecs is None:
    pytest.skip("world_ecs_fast Cython extension not built", allow_module_level=True)


class _UnitMock:
    def __init__(self, x, y, uid=None, player=None):
        self.x = x
        self.y = y
        self.id = uid
        self.player = player


class _PlayerMock:
    def __init__(self, pid):
        self.id = pid
        self.units = []


def _ref_build_buckets(units, A):
    buckets = {}
    for u in units:
        k = (u.x // A, u.y // A)
        try:
            buckets[k].append(u)
        except KeyError:
            buckets[k] = [u]
    return buckets


@pytest.fixture
def store():
    return _ecs.UnitStore()


def test_store_sync_and_buckets(store):
    units = [_UnitMock(x, y, str(i)) for i, (x, y) in enumerate([(10, 20), (-5, 7), (100, 0)])]
    xs = [u.x for u in units]
    ys = [u.y for u in units]
    store.sync_from_scalars(xs, ys)
    assert store.count() == 3
    A = 100
    got = store.build_buckets(A, units)
    assert got == _ref_build_buckets(units, A)


def _bucket_coords(buckets):
    return {
        k: sorted((u.x, u.y) for u in v)
        for k, v in buckets.items()
    }


def test_store_swap_remove(store):
    store.add_slot(1, 2)
    store.add_slot(3, 4)
    store.add_slot(5, 6)
    moved = store.remove_slot(0)
    assert moved == 0
    assert store.count() == 2
    units = [_UnitMock(3, 4), _UnitMock(5, 6)]
    assert _bucket_coords(store.build_buckets(10, units)) == _bucket_coords(
        _ref_build_buckets(units, 10)
    )


def test_ecs_matches_world_buckets_fast():
    if _wbf is None:
        pytest.skip("world_buckets_fast not built")
    A = 12 * 1000  # PRECISION bucket size used in game
    rng = [(i * 137, i * 89 - 50) for i in range(80)]
    units = [_UnitMock(x, y) for x, y in rng]
    xs = [u.x for u in units]
    ys = [u.y for u in units]
    store = _ecs.UnitStore()
    store.sync_from_scalars(xs, ys)
    ecs_buckets = store.build_buckets(A, units)
    wbf_buckets = _wbf.build_buckets(units, A)
    assert ecs_buckets == wbf_buckets


def test_world_ecs_registry_roundtrip(monkeypatch):
    monkeypatch.setenv("SOUNDRTS_ECS", "1")
    from soundrts.world.world_ecs import WorldEcs

    ecs = WorldEcs()
    p = _PlayerMock("p1")
    u1 = _UnitMock(10, 20, "1", p)
    u2 = _UnitMock(30, 40, "2", p)
    p.units = [u1, u2]
    ecs.rebuild_player_from_units(p)
    ecs.sync_all([p])
    A = 100
    assert ecs.build_buckets_for_player(p, A) == _ref_build_buckets(p.units, A)
    ecs.unregister(u1)
    p.units.remove(u1)
    ecs.sync_all([p])
    assert ecs.build_buckets_for_player(p, A) == _ref_build_buckets(p.units, A)
