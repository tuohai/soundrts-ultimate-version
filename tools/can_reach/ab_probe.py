#!/usr/bin/env python3
"""Deterministic A/B probe for the ``can_reach`` optimisation.

The full 40-minute headless benchmark cannot be used for an A/B
comparison: the engine is *inherently* nondeterministic (two identical
runs diverge at tick 42 because some code iterates over ``id()``-keyed
dictionaries, so ASLR changes the order).  The two arms therefore end up
playing different games and their wall-clock numbers are not comparable.

This probe sidesteps that by measuring the *algorithmic* cost directly:

* run a fixed number of ticks with the legacy path enabled,
* run the same number of ticks with ``can_reach`` enabled,
* count how many A* expansions each arm performs and how much CPU the
  reachability helpers consume.

Usage::

    python tools/can_reach/ab_probe.py [game-minutes]

The release notes for 1.5.2.5 quote the result of the 20-minute run.
"""
from __future__ import annotations

import collections
import sys
import time

from common import build_world, run_world, silence_logs, use_legacy_can_reach

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0


def instrument():
    """Count A* expansions and reachability work."""
    from soundrts import worldroom

    stats = collections.Counter()

    orig_can_reach = worldroom.Square.can_reach
    orig_shortest = worldroom.Square._shortest_path_to

    def can_reach(self, dest, player=None, plane="ground", avoid=False):
        stats["can_reach_calls"] += 1
        t0 = time.perf_counter()
        try:
            return orig_can_reach(self, dest, player, plane=plane, avoid=avoid)
        finally:
            stats["can_reach_time"] += time.perf_counter() - t0

    def shortest(self, dest, player, plane, places=False, avoid=False):
        stats["shortest_calls"] += 1
        t0 = time.perf_counter()
        try:
            return orig_shortest(self, dest, player, plane, places, avoid)
        finally:
            stats["shortest_time"] += time.perf_counter() - t0

    worldroom.Square.can_reach = can_reach
    worldroom.Square._shortest_path_to = shortest
    return stats


def run(legacy: bool):
    use_legacy_can_reach(legacy)
    silence_logs()
    world = build_world()
    stats = instrument()
    t0 = time.perf_counter()
    ticks = run_world(world, GAME_MINUTES)
    elapsed = time.perf_counter() - t0
    units = sum(len(p.units) for p in world.players)
    return stats, elapsed, ticks, units


def main() -> int:
    print("=" * 70)
    print("can_reach A/B (deterministic algorithmic cost probe)")
    print("=" * 70)
    print(f"game minutes: {GAME_MINUTES}")

    results = {}
    for label, legacy in (("legacy", True), ("can_reach", False)):
        stats, elapsed, ticks, units = run(legacy)
        results[label] = (stats, elapsed, ticks, units)
        print()
        print(f"--- {label} ---")
        print(f"  ticks              : {ticks}")
        print(f"  wall seconds       : {elapsed:.1f}")
        print(f"  units              : {units}")
        print(f"  can_reach calls    : {stats['can_reach_calls']}")
        print(f"  can_reach cpu sec  : {stats['can_reach_time']:.1f}")
        print(f"  shortest_path calls: {stats['shortest_calls']}")
        print(f"  shortest_path cpu  : {stats['shortest_time']:.1f}")
        total = stats["can_reach_time"] + stats["shortest_time"]
        print(f"  pathfinding cpu    : {total:.1f}  ({100.0 * total / elapsed:.1f}% of wall)")

    leg = results["legacy"][0]
    new = results["can_reach"][0]
    print()
    print("=" * 70)
    print("summary")
    print("=" * 70)
    l_calls = leg["shortest_calls"] + leg["can_reach_calls"]
    n_calls = new["shortest_calls"] + new["can_reach_calls"]
    l_cpu = leg["shortest_time"] + leg["can_reach_time"]
    n_cpu = new["can_reach_time"] + new["shortest_time"]
    print(f"  pathfinding calls  : legacy={l_calls}  can_reach={n_calls}")
    print(f"  pathfinding cpu    : legacy={l_cpu:.1f}s  can_reach={n_cpu:.1f}s")
    if l_cpu:
        print(f"  cpu delta          : {100.0 * (n_cpu - l_cpu) / l_cpu:+.1f}%")
    print(
        "  NOTE: unit counts may differ between arms because the engine is "
        "inherently"
    )
    print(
        "        nondeterministic (id()-ordered iteration); the wall-clock "
        "numbers are"
    )
    print("        therefore only loosely comparable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
