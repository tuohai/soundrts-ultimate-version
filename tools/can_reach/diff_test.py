#!/usr/bin/env python3
"""Differential test: ``Square.can_reach`` vs ``shortest_path_to(places=True)``.

Runs a headless cw1 match and compares the two reachability answers at
every opportunity (same origin/dest/player/plane), reporting any
disagreement.

Usage::

    python tools/can_reach/diff_test.py [game-minutes]

Exit code 0 means the two implementations agreed on every call.
"""
from __future__ import annotations

import sys
from collections import Counter

from common import build_world, run_world, silence_logs

silence_logs()

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0


def main() -> int:
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldplayercomputer_water import movement_target_for_unit

    stats = Counter()
    mismatches = []

    orig = Computer._unit_can_reach

    def patched(self, unit, dest, avoid=False):
        # Recompute the old answer for comparison.
        dest2 = self._world_place_for_pathfinding(dest)
        old = None
        if dest2 is not None:
            origin = self._world_place_for_unit(unit)
            if origin is not None:
                from soundrts.worldplayercomputer import path_plane

                plane = path_plane(unit)
                mt = movement_target_for_unit(unit, dest2, self)
                try:
                    path = origin.shortest_path_to(
                        mt, self, plane=plane, places=True, avoid=avoid
                    )
                    old = bool(path)
                except Exception:
                    stats["old_error"] += 1
                    old = None
        res = orig(self, unit, dest, avoid)
        stats["calls"] += 1
        if old is not None:
            if old == res:
                stats["agree"] += 1
            else:
                stats["MISMATCH"] += 1
                if len(mismatches) < 12:
                    mismatches.append((unit, dest2, plane, avoid, old, res))
        return res

    Computer._unit_can_reach = patched

    world = build_world()
    run_world(world, GAME_MINUTES)

    print("=" * 70)
    print("differential: can_reach vs shortest_path_to(places=True)")
    print("=" * 70)
    print(f"game minutes : {GAME_MINUTES}")
    print(f"calls        : {stats['calls']}")
    print(f"agree        : {stats['agree']}")
    print(f"MISMATCH     : {stats['MISMATCH']}")
    print(f"old_error    : {stats['old_error']}")
    for m in mismatches:
        u, d, plane, avoid, old, new = m
        print(
            f"  unit={getattr(u, 'type_name', '?')} id={getattr(u, 'id', None)} "
            f"dest={d} plane={plane} avoid={avoid} old={old} new={new}"
        )
    return 1 if stats["MISMATCH"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
