"""Incremental spatial buckets must match full rebuild; idle combat unchanged."""
from __future__ import annotations

import os
import types

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.worldplayerbase import A


def _unit(x, y, uid):
    u = types.SimpleNamespace(x=x, y=y, id=uid)
    return u


def test_incremental_buckets_match_full_rebuild_on_move_and_remove():
    from soundrts.world.world_game import WorldGameMixin

    class _W(WorldGameMixin):
        pass

    w = _W()
    p = types.SimpleNamespace(
        units=[],
        _buckets={},
        _bucket_unit_cells=None,
        _bucket_ticks_since_heal=0,
    )
    u1 = _unit(10, 10, "a")
    u2 = _unit(250, 10, "b")  # different cell if A is large enough
    p.units = [u1, u2]

    w._rebuild_player_buckets(p, A)
    full = {k: list(v) for k, v in p._buckets.items()}

    # Second sync with no move → dirty empty, buckets unchanged content
    dirty = w._incremental_player_buckets(p, A)
    assert dirty == set()
    assert {k: list(v) for k, v in p._buckets.items()} == full

    # Move u1 across a cell boundary
    u1.x = u1.x + A * 3
    dirty = w._incremental_player_buckets(p, A)
    assert dirty
    w2 = _W()
    p2 = types.SimpleNamespace(
        units=[u1, u2],
        _buckets={},
        _bucket_unit_cells=None,
        _bucket_ticks_since_heal=0,
    )
    w2._rebuild_player_buckets(p2, A)
    assert set(map(id, sum(p._buckets.values(), []))) == set(
        map(id, sum(p2._buckets.values(), []))
    )
    assert {k: set(map(id, v)) for k, v in p._buckets.items()} == {
        k: set(map(id, v)) for k, v in p2._buckets.items()
    }

    # Remove a unit
    p.units = [u2]
    dirty = w._incremental_player_buckets(p, A)
    assert u1 not in sum(p._buckets.values(), [])
    assert set(map(id, sum(p._buckets.values(), []))) == {id(u2)}


def test_neighbor_invalidate_keeps_other_players_cache():
    from soundrts.worldplayerbase.perception import PerceptionMixin

    class P(PerceptionMixin):
        pass

    P._global_neighbors_cache = {}
    P._global_neighbors_timestamp = {}

    a = P()
    b = P()
    key_a = (id(a), 1, 1)
    key_b = (id(b), 1, 1)
    P._global_neighbors_cache[key_a] = ["A"]
    P._global_neighbors_cache[key_b] = ["B"]

    a._invalidate_neighbors_near({(1, 1)})
    assert key_a not in P._global_neighbors_cache
    assert P._global_neighbors_cache.get(key_b) == ["B"]
