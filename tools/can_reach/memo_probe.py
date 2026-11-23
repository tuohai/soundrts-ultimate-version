#!/usr/bin/env python3
"""Measure the 1500 ms reachability memo's hit rate in a live match.

The memo is the other half of the optimisation: ``Square.can_reach``
caches its answer in a 1500 ms bucket, so the same question asked again
in the next tick is answered from the cache instead of re-running the
search.

This probe counts, per live call:

* how many were answered from the memo (a hit),
* how many had to run the search (a miss),
* the CPU time spent on each.

Usage::

    python tools/can_reach/memo_probe.py [game-minutes]
"""
from __future__ import annotations

import sys
import time

from common import build_world, run_world, silence_logs

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0


def main() -> int:
    silence_logs()
    world = build_world()

    from soundrts import worldroom

    stats = {"calls": 0, "hit": 0, "miss": 0}
    times = {"hit": 0.0, "miss": 0.0}

    orig = worldroom.Square.can_reach

    def can_reach(self, dest, player=None, plane="ground", avoid=False):
        # A memo hit returns before the search runs, so we detect it by
        # looking at whether the cache already holds the key.
        bucket = self.world.time // 1500
        cache = worldroom._reach_cache
        key = (
            id(self.world),
            self.id,
            None if dest is None else dest.id,
            None if player is None else player.id,
            avoid,
        )
        is_hit = worldroom._reach_cache_time == bucket and key in cache
        t0 = time.perf_counter()
        try:
            return orig(self, dest, player, plane=plane, avoid=avoid)
        finally:
            dt = time.perf_counter() - t0
            stats["calls"] += 1
            if is_hit:
                stats["hit"] += 1
                times["hit"] += dt
            else:
                stats["miss"] += 1
                times["miss"] += dt

    worldroom.Square.can_reach = can_reach

    t0 = time.perf_counter()
    run_world(world, GAME_MINUTES)
    wall = time.perf_counter() - t0

    calls = stats["calls"] or 1
    print("=" * 70)
    print("reachability memo probe")
    print("=" * 70)
    print(f"game minutes : {GAME_MINUTES}")
    print(f"wall seconds : {wall:.1f}")
    print(f"can_reach calls: {stats['calls']}")
    print(f"  memo hits   : {stats['hit']}  ({100.0 * stats['hit'] / calls:.1f}%)")
    print(f"  searches    : {stats['miss']}  ({100.0 * stats['miss'] / calls:.1f}%)")
    if stats["hit"]:
        print(f"  us per hit  : {1e6 * times['hit'] / stats['hit']:.1f}")
    if stats["miss"]:
        print(f"  us per miss : {1e6 * times['miss'] / stats['miss']:.1f}")
    if stats["calls"]:
        print(f"  us per call : {1e6 * (times['hit'] + times['miss']) / calls:.1f}")
        print(f"  cpu share   : {100.0 * (times['hit'] + times['miss']) / wall:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
