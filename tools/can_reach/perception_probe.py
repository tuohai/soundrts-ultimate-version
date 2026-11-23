#!/usr/bin/env python3
"""Measure the cost of the old ``perception.union(memory)`` allocations.

``_known_huntable_animals``, ``_reachable_deposits`` and
``_known_ok_deposits_compute`` used to build a fresh set with
``self.perception.union(self.memory)`` on every call.  That copies every
known entity.  The optimisation walks the two sets directly instead.

This probe measures the allocation itself (and, for comparison, the cost
of just iterating the two sets) on a live world, so the saving can be
quoted.

Usage::

    python tools/can_reach/perception_probe.py [game-minutes]
"""
from __future__ import annotations

import sys
import time

from common import build_world, run_world, silence_logs

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0

TARGETS = (
    "_known_huntable_animals",
    "_reachable_deposits",
    "_known_ok_deposits_compute",
)


def main() -> int:
    silence_logs()
    world = build_world()

    from soundrts.worldplayercomputer import Computer

    stats = {"calls": 0, "time": 0.0}
    union_stats = {"calls": 0, "time": 0.0, "copied": 0}

    def wrap(name):
        orig = getattr(Computer, name)

        def patched(self, *a, **kw):
            t0 = time.perf_counter()
            try:
                return orig(self, *a, **kw)
            finally:
                stats["calls"] += 1
                stats["time"] += time.perf_counter() - t0

        setattr(Computer, name, patched)

    for name in TARGETS:
        if hasattr(Computer, name):
            wrap(name)

    # Time the union allocation the old code performed, on the same world.
    players = list(world.players)

    def measure_unions():
        for p in players:
            perception = getattr(p, "perception", None) or set()
            memory = getattr(p, "memory", None) or set()
            t0 = time.perf_counter()
            merged = perception.union(memory)
            union_stats["time"] += time.perf_counter() - t0
            union_stats["calls"] += 1
            union_stats["copied"] += len(merged)

    t0 = time.perf_counter()
    run_world(world, GAME_MINUTES)
    wall = time.perf_counter() - t0
    measure_unions()

    print("=" * 70)
    print("perception/memory set-walk probe")
    print("=" * 70)
    print(f"game minutes : {GAME_MINUTES}")
    print(f"wall seconds : {wall:.1f}")
    print(f"calls        : {stats['calls']}")
    print(f"cpu seconds  : {stats['time']:.2f}")
    if stats["calls"]:
        print(f"us per call  : {1e6 * stats['time'] / stats['calls']:.1f}")
        print(f"cpu share    : {100.0 * stats['time'] / wall:.2f}%")
    print()
    print("  one union() per player, on the final world state:")
    print(f"    unions     : {union_stats['calls']}")
    print(f"    cpu seconds: {union_stats['time']:.4f}")
    print(f"    entities copied: {union_stats['copied']}")
    if union_stats["calls"]:
        print(
            f"    us per union: "
            f"{1e6 * union_stats['time'] / union_stats['calls']:.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
