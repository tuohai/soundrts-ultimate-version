#!/usr/bin/env python3
"""Measure the *per-call* cost of the two reachability implementations.

Why per-call and not total CPU
------------------------------
The engine is inherently nondeterministic (some code iterates over
``id()``-keyed dictionaries, so ASLR changes the order).  Two separate
runs therefore play different games: they issue different numbers of
reachability queries against different worlds, so their *total*
pathfinding CPU is not comparable, and a total-CPU A/B number swings
between runs.

The per-query cost, however, is a property of the algorithm and is
comparable across runs: the same call on the same squares does the same
work.  This probe therefore reports microseconds per query.

Usage::

    python tools/can_reach/cost_probe.py [game-minutes]
"""
from __future__ import annotations

import statistics
import sys
import time

from common import build_world, run_world, silence_logs, use_legacy_can_reach

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0


def measure(legacy: bool):
    """Return (median us per call, call count) for one arm."""
    use_legacy_can_reach(legacy)
    silence_logs()

    # Build the world *before* importing the engine modules we patch, so
    # that we instrument the very same module objects the world uses.
    world = build_world()

    from soundrts import worldroom

    samples = []
    counts = {"shortest": 0, "can_reach": 0}

    orig_shortest = worldroom.Square._shortest_path_to
    orig_can_reach = worldroom.Square.can_reach

    def shortest(self, dest, player, plane, places=False, avoid=False):
        counts["shortest"] += 1
        t0 = time.perf_counter()
        try:
            return orig_shortest(self, dest, player, plane, places, avoid)
        finally:
            samples.append(time.perf_counter() - t0)

    def can_reach(self, dest, player=None, plane="ground", avoid=False):
        counts["can_reach"] += 1
        t0 = time.perf_counter()
        try:
            return orig_can_reach(self, dest, player, plane=plane, avoid=avoid)
        finally:
            samples.append(time.perf_counter() - t0)

    worldroom.Square._shortest_path_to = shortest
    worldroom.Square.can_reach = can_reach

    run_world(world, GAME_MINUTES)

    worldroom.Square._shortest_path_to = orig_shortest
    worldroom.Square.can_reach = orig_can_reach

    total = counts["shortest"] + counts["can_reach"]
    if not samples:
        return 0.0, counts
    return 1e6 * statistics.median(samples), counts


def main() -> int:
    print("=" * 70)
    print("reachability per-query cost probe")
    print("=" * 70)
    print(f"game minutes: {GAME_MINUTES}")

    results = {}
    for label, legacy in (("legacy", True), ("can_reach", False)):
        us, counts = measure(legacy)
        results[label] = us
        print()
        print(f"--- {label} ---")
        print(f"  shortest_path calls: {counts['shortest']}")
        print(f"  can_reach calls    : {counts['can_reach']}")
        print(f"  us per query       : {us:.1f}")

    legacy_us, new_us = results["legacy"], results["can_reach"]
    print()
    print("=" * 70)
    print("summary")
    print("=" * 70)
    if legacy_us:
        print(
            f"  legacy={legacy_us:.1f} us   can_reach={new_us:.1f} us   "
            f"delta={100.0 * (new_us - legacy_us) / legacy_us:+.1f}%"
        )
    print(
        "  NOTE: the per-query cost is comparable across runs; the *total*"
    )
    print(
        "        pathfinding CPU is not, because the two arms play different"
    )
    print("        games (the engine is inherently nondeterministic).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
