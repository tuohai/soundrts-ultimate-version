#!/usr/bin/env python3
"""Deterministic per-query A/B, sampled at several points of one match.

Same idea as ``deterministic_ab.py`` -- both implementations are replayed
over the *same* frozen world and the *same* query list, so the numbers
measure the algorithms rather than two different games -- but instead of
one snapshot this samples the world at several points in the match and
reports the spread.

Usage::

    python tools/can_reach/deterministic_ab.py [game-minutes] [query-count]
"""
from __future__ import annotations

import statistics
import sys
import time

from common import build_world, run_world, silence_logs

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
N_QUERIES = int(sys.argv[2]) if len(sys.argv) > 2 else 3000

# Sample the world at these fractions of the run.
CHECKPOINTS = (0.25, 0.5, 0.75, 1.0)


def collect_queries(world, count):
    """Pick *count* (origin, dest, player) queries from the live world."""
    squares = [s for s in world.squares if not getattr(s, "is_water", False)]
    players = list(world.players)
    queries = []
    if not squares or not players:
        return queries
    # Stride through the square list so the sample spreads over the map,
    # and vary the player so the blocked-exit checks differ too.
    stride = max(1, len(squares) // max(1, count // (3 * len(players))))
    for i in range(0, len(squares), stride):
        origin = squares[i]
        dest = squares[(i * 7 + 13) % len(squares)]
        if origin is dest:
            continue
        for player in players:
            queries.append((origin, dest, player))
            if len(queries) >= count:
                return queries
    return queries


def time_queries(queries, legacy: bool):
    """Time *queries* against one implementation; return (samples, results)."""
    if legacy:
        def run_one(origin, dest, player):
            try:
                return bool(
                    origin.shortest_path_to(
                        dest, player, plane="ground", places=True
                    )
                )
            except Exception:
                return None
    else:
        def run_one(origin, dest, player):
            try:
                return bool(origin.can_reach(dest, player, plane="ground"))
            except Exception:
                return None

    # Warm up (imports, page faults, first-touch allocations).
    for origin, dest, player in queries[:50]:
        run_one(origin, dest, player)

    samples = []
    results = []
    for origin, dest, player in queries:
        t0 = time.perf_counter()
        res = run_one(origin, dest, player)
        samples.append(time.perf_counter() - t0)
        results.append(res)
    return samples, results


def main() -> int:
    silence_logs()
    world = build_world()

    limit = int(GAME_MINUTES * 60 * 1000)
    checkpoints = [int(limit * f) for f in CHECKPOINTS]

    deltas = []
    mismatches = 0
    print("=" * 74)
    print("deterministic per-query A/B (same world, same queries, per checkpoint)")
    print("=" * 74)

    for cp in checkpoints:
        while world.time < cp:
            world.update()
        queries = collect_queries(world, N_QUERIES)
        if not queries:
            continue
        legacy_samples, legacy_res = time_queries(queries, legacy=True)
        new_samples, new_res = time_queries(queries, legacy=False)

        l_mean = 1e6 * sum(legacy_samples) / len(legacy_samples)
        n_mean = 1e6 * sum(new_samples) / len(new_samples)
        delta = 100.0 * (n_mean - l_mean) / l_mean
        deltas.append(delta)
        mismatches += sum(
            1
            for a, b in zip(legacy_res, new_res)
            if a is not None and b is not None and a != b
        )
        print(
            f"  world.time={world.time // 1000:5d}s  queries={len(queries):5d}  "
            f"legacy={l_mean:7.1f} us  new={n_mean:7.1f} us  delta={delta:+6.1f}%"
        )

    print()
    if deltas:
        print(
            f"  per-query delta: mean={statistics.mean(deltas):+.1f}%  "
            f"median={statistics.median(deltas):+.1f}%  "
            f"range={min(deltas):+.1f}%..{max(deltas):+.1f}%"
        )
    print(f"  answer mismatches over the shared query sets: {mismatches}")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
