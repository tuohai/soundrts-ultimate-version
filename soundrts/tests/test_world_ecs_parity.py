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


def test_ecs_enabled_defaults_on(monkeypatch):
    monkeypatch.delenv("SOUNDRTS_ECS", raising=False)
    from soundrts.world import world_ecs as we

    if we._ecs_fast is None:
        pytest.skip("world_ecs_fast not built")
    assert we.ecs_enabled() is True
    monkeypatch.setenv("SOUNDRTS_ECS", "0")
    assert we.ecs_enabled() is False
    monkeypatch.setenv("SOUNDRTS_ECS", "off")
    assert we.ecs_enabled() is False


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


class _ObsUnit:
    def __init__(self, x, y, sight, uid, inside=False):
        self.x = x
        self.y = y
        self.sight_range = sight
        self.id = uid
        self.is_inside = inside
        self.player = None
        self.blocked_exit = None
        self.is_invisible = False
        self.is_cloaked = False
        self.place = None


def _ref_observers_seeing(units, tx, ty, A):
    """Python reference for halo + Euclidean (matches UnitStore.observers_seeing_point)."""
    gx, gy = tx // A, ty // A
    out = []
    for u in units:
        if getattr(u, "is_inside", False):
            continue
        sr = int(getattr(u, "sight_range", 0) or 0)
        if not sr:
            continue
        if abs(u.x // A - gx) > 1 or abs(u.y // A - gy) > 1:
            continue
        dx = u.x - tx
        dy = u.y - ty
        if dx * dx + dy * dy >= sr * sr:
            continue
        out.append(u)
    return out


def test_observers_seeing_point_parity(store):
    A = 12 * 1000
    sight = 8 * 1000
    units = [
        _ObsUnit(0, 0, sight, "a"),
        _ObsUnit(sight - 1, 0, sight, "b"),  # just inside
        _ObsUnit(sight, 0, sight, "c"),  # boundary: not seeing (strict <)
        _ObsUnit(A * 3, 0, sight, "d"),  # outside halo
        _ObsUnit(100, 100, sight, "e", inside=True),
        _ObsUnit(50, 0, 0, "f"),  # zero sight
    ]
    xs = [u.x for u in units]
    ys = [u.y for u in units]
    sights = [u.sight_range for u in units]
    flags = [1 if u.is_inside else 0 for u in units]
    store.sync_from_scalars(xs, ys, sights, flags)
    tx, ty = 0, 0
    got = store.observers_seeing_point(units, tx, ty, A)
    ref = _ref_observers_seeing(units, tx, ty, A)
    assert [u.id for u in got] == [u.id for u in ref]
    assert {u.id for u in got} == {"a", "b"}


def test_world_ecs_observers_for_target(monkeypatch):
    monkeypatch.setenv("SOUNDRTS_ECS", "1")
    from soundrts.world.world_ecs import WorldEcs
    from soundrts.worldplayerbase.base import A

    ecs = WorldEcs()
    p = _PlayerMock("p1")
    sight = 8 * 1000
    u_near = _ObsUnit(0, 0, sight, "near")
    u_far = _ObsUnit(A * 5, 0, sight, "far")
    u_near.player = p
    u_far.player = p
    p.units = [u_near, u_far]
    ecs.rebuild_player_from_units(p)
    ecs.sync_player(p)
    got = ecs.observers_for_target(p, 100, 0, A)
    assert [u.id for u in got] == ["near"]


def test_sync_slots_from_units_inplace(store):
    units = [_ObsUnit(1, 2, 100, "a"), _ObsUnit(3, 4, 200, "b")]
    store.sync_from_scalars(
        [u.x for u in units],
        [u.y for u in units],
        [u.sight_range for u in units],
        [0, 0],
    )
    units[0].x = 50
    units[0].y = 60
    units[0].sight_range = 999
    units[1].is_inside = True
    store.sync_slots_from_units(units)
    A = 100
    # after move, observers at (50,60) with sight 999 should include a
    got = store.observers_seeing_point(units, 50, 60, A)
    assert [u.id for u in got] == ["a"]


def test_batch_see_enemies_matches_is_seeing(monkeypatch):
    """batch_see_enemies ⊆ same decisions as repeated _is_seeing (no cloak)."""
    monkeypatch.setenv("SOUNDRTS_ECS", "1")
    from soundrts.world.world_ecs import WorldEcs
    from soundrts.worldplayerbase.base import A
    from soundrts.worldplayerbase.perception import PerceptionMixin

    class _Place:
        def __init__(self, name):
            self.name = name

    class _World:
        def __init__(self):
            self.time = 0
            self.players = []

    class _P(PerceptionMixin):
        pass

    _P._global_neighbors_cache = {}
    _P._global_neighbors_timestamp = {}
    _P._last_cleanup_time = 0

    sight = 8 * 1000
    place_here = _Place("here")
    place_far = _Place("far")

    viewer = _P()
    viewer.id = "v"
    viewer.world = _World()
    viewer.detected_units = set()
    viewer.observed_squares = {place_here}
    viewer._buckets = {}
    viewer._bucket_unit_cells = {}

    ally = _P()
    ally.id = "a"
    ally.world = viewer.world
    ally.detected_units = set()

    observer = _ObsUnit(0, 0, sight, "obs")
    observer.player = ally
    observer.place = place_here
    observer.get_observed_squares = lambda: {place_here}
    observer.get_observed_squares_optimized = lambda: {
        "strict": {place_here},
        "all": {place_here},
    }
    ally.units = [observer]
    gx, gy = 0 // A, 0 // A
    ally._buckets = {(gx, gy): [observer]}

    viewer.allied_vision = [ally]
    viewer.units = []

    near = _ObsUnit(100, 0, sight, "near")
    near.place = place_here
    near.is_invisible = False
    near.is_cloaked = False
    far = _ObsUnit(A * 5, 0, sight, "far")
    far.place = place_far
    far.is_invisible = False
    far.is_cloaked = False

    ecs = WorldEcs()
    ecs.rebuild_player_from_units(ally)
    ecs.sync_player(ally)
    viewer.world._ecs = ecs

    # Patch exit blocker
    viewer._exit_blocker_visible = lambda u: False

    batch = ecs.batch_see_enemies(viewer, [near, far], A)
    assert near in batch
    assert far not in batch

    # Parity with single-target path (neighbor-based)
    assert viewer._py_is_seeing(near) is True
    assert viewer._py_is_seeing(far) is False

    # vision_places prefilter: far place excluded → still not seen; near kept
    batch2 = ecs.batch_see_enemies(
        viewer, [near, far], A, vision_places={place_here}
    )
    assert near in batch2
    assert far not in batch2
    # Empty vision: neither Euclidean-visible (exit blockers not in this fixture)
    batch3 = ecs.batch_see_enemies(viewer, [near, far], A, vision_places=set())
    assert near not in batch3
    assert far not in batch3


def test_ecs_update_buckets_uses_incremental(monkeypatch):
    """ECS hot path must keep warm neighbor cache when nothing moves."""
    monkeypatch.setenv("SOUNDRTS_ECS", "1")
    from soundrts.world.world_ecs import WorldEcs
    from soundrts.world.world_game import WorldGameMixin
    from soundrts.worldplayerbase.base import A
    from soundrts.worldplayerbase.perception import PerceptionMixin

    class _P(PerceptionMixin):
        pass

    class _W(WorldGameMixin):
        pass

    _P._global_neighbors_cache = {}
    _P._global_neighbors_timestamp = {}
    _P._global_vision_cache = {}
    _P._observed_squares_cache = {}
    _P._observed_squares_cache_timestamp = {}

    w = _W()
    ecs = WorldEcs()
    w._ecs = ecs
    p = _P()
    p.id = "p1"
    p.units = []
    p._buckets = {}
    p._bucket_unit_cells = None
    p._bucket_ticks_since_heal = 0
    u = _ObsUnit(10, 10, 8000, "u1")
    u.player = p
    p.units = [u]
    w.players = [p]

    # First tick: cold rebuild
    w._update_buckets()
    assert p._buckets
    key = (id(p), 0, 0)
    _P._global_neighbors_cache[key] = ["keep"]
    # Stationary tick: incremental dirty empty → neighbor cache entry survives
    w._update_buckets()
    assert _P._global_neighbors_cache.get(key) == ["keep"]
    # Cross-cell move dirties cells but must not wipe other players' caches
    u.x = u.x + A * 2
    u.y = u.y + A * 2
    w._update_buckets()
    assert any((u.x // A, u.y // A) == k for k in p._buckets)
