"""Ground exit-only A* sanity checks on a real multi map."""
from __future__ import annotations

import os
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_ground_astar_exits_only_basic():
    from soundrts.mapfile import Map
    from soundrts.world import World

    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(here, "res", "multi", "jl1.txt")
    if not os.path.isfile(path):
        import pytest

        pytest.skip("jl1.txt not found")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ResourceWarning)
        world = World([], 1)
        world.load_and_build_map(Map(path))

    squares = [s for s in world.squares if getattr(s, "exits", None)]
    assert len(squares) >= 4
    a, b = squares[0], squares[3]
    nxt, dist = a._shortest_path_to(b, "ground", None, places=False, avoid=False)
    if nxt is not None:
        assert nxt in a.exits
        assert dist >= 0
        # Cached identically
        assert a._shortest_path_to(b, "ground", None, places=False, avoid=False) == (
            nxt,
            dist,
        )
    # Adjacent / self
    assert a._shortest_path_to(a, "ground", None, places=False, avoid=False) == (
        None,
        0,
    )
