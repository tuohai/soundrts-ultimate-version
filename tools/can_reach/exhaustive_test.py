#!/usr/bin/env python3
"""Exhaustive differential test: ``Square.can_reach`` vs ``shortest_path_to``.

Instead of only the pairs the AI happens to ask about, this walks a grid
of square pairs on the live world and compares the two answers.  Any
mismatch is printed with enough context to reproduce it.

Usage::

    python tools/can_reach/exhaustive_test.py [game-minutes] [step]

``step`` subsamples the square grid (every n-th pair) to keep the runtime
reasonable; the release notes quote the run with the default step.
"""
from __future__ import annotations

import sys
from collections import Counter

from common import build_world, run_world, silence_logs

silence_logs()

GAME_MINUTES = float(sys.argv[1]) if len(sys.argv) > 1 else 4.0
STEP = int(sys.argv[2]) if len(sys.argv) > 2 else 7


def main() -> int:
    world = build_world()
    run_world(world, GAME_MINUTES)

    squares = [s for s in world.squares if not getattr(s, "is_water", False)]
    print("=" * 70)
    print(f"exhaustive can_reach differential: {len(squares)} land squares")
    print("=" * 70)

    stats = Counter()
    mismatches = []
    # Use each player as the 'player' argument (blocked checks depend on it).
    players = list(world.players)

    for pi, player in enumerate(players[:3]):
        for i, origin in enumerate(squares):
            for j, dest in enumerate(squares):
                if (i + j) % STEP:
                    continue
                try:
                    old = bool(
                        origin.shortest_path_to(
                            dest, player, plane="ground", places=True
                        )
                    )
                except Exception:
                    stats["old_error"] += 1
                    continue
                try:
                    new = bool(origin.can_reach(dest, player, plane="ground"))
                except Exception as exc:
                    stats["new_error"] += 1
                    if len(mismatches) < 10:
                        mismatches.append(
                            (origin.name, dest.name, f"new raised {exc!r}")
                        )
                    continue
                stats["compared"] += 1
                if old != new:
                    stats["MISMATCH"] += 1
                    if len(mismatches) < 20:
                        mismatches.append(
                            (
                                origin.name,
                                dest.name,
                                f"old={old} new={new}",
                                player.number if hasattr(player, "number") else "?",
                            )
                        )

    print(f"compared  : {stats['compared']}")
    print(f"agree     : {stats['compared'] - stats['MISMATCH']}")
    print(f"MISMATCH  : {stats['MISMATCH']}")
    print(f"old_error : {stats['old_error']}")
    print(f"new_error : {stats['new_error']}")
    for m in mismatches[:20]:
        print("  ", m)
    return 1 if stats["MISMATCH"] or stats["new_error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
