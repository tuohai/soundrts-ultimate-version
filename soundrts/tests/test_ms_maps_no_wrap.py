"""Audit: ms200/500/1000 maps must NOT have toroidal wrap passages.

Background:
    The engine creates west-east passages via _create_we_passage:
        col = cx + 1
        if col == self.nb_columns:    # cx == nb_columns - 1 (0-based grid)
            col = 0; is_a_portal = True
    A 1-based ``(N, row)`` parses to 0-based ``(N-1, row)``, which trips
    the portal branch and creates a wrap passage to col 0. Same for sn.

    This audit confirms that no boundary 1-based coordinate that would
    create a wrap is present in any of the three multi maps.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest


_MAPS = ("ms200.txt", "ms500.txt", "ms1000.txt")


def _map_path(name: str) -> Path:
    return Path("res") / "multi" / name


def _parse_n_and_paths(path: Path) -> tuple[int, list[tuple[int, int]], list[tuple[int, int]]]:
    """Return (nb_columns, [(x, y), ...] for west_east, [... for south_north]).

    Coordinates are kept as 1-based (file format).
    """
    text = path.read_text(encoding="utf-8")
    n = 0
    we: list[tuple[int, int]] = []
    sn: list[tuple[int, int]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("nb_columns "):
            n = int(line.split()[1])
        elif line.startswith("west_east_paths ") or line.startswith("west_east "):
            for tok in line.split()[1:]:
                x, y = (int(p) for p in tok.split(","))
                we.append((x, y))
        elif line.startswith("south_north_paths ") or line.startswith("south_north "):
            for tok in line.split()[1:]:
                x, y = (int(p) for p in tok.split(","))
                sn.append((x, y))
    return n, we, sn


@pytest.mark.parametrize("name", _MAPS)
def test_boundary_entries_dropped_to_prevent_toroidal_wrap(name):
    """Each multi map must not contain ``(N, row)`` / ``(col, N)`` 1-based
    boundary entries; those would trigger the engine's portal wrap.

    Engine parses 1-based -> 0-based via ``_normalize_square_token``.
    ``_create_we_passage`` wraps when ``cx+1 == nb_columns`` (0-based),
    i.e. for 0-based ``(N-1, row)`` which is 1-based ``(N, row)``.
    """
    path = _map_path(name)
    assert path.exists(), f"{path} must exist"
    n, we, sn = _parse_n_and_paths(path)
    assert n > 0, f"{name} did not declare nb_columns"
    bad_we = [(x, y) for x, y in we if x == n or x == 0]
    bad_sn = [(x, y) for x, y in sn if y == n or y == 0]
    assert not bad_we, (
        f"{name}: west_east entries on boundary would wrap "
        f"(1-based x == n or x == 0): {bad_we[:10]}"
    )
    assert not bad_sn, (
        f"{name}: south_north entries on boundary would wrap "
        f"(1-based y == n or y == 0): {bad_sn[:10]}"
    )


@pytest.mark.parametrize("name", _MAPS)
def test_engine_does_not_create_toroidal_wrap_for_ms_map(name):
    """Load the map via the engine and assert no boundary<->opposite exits."""
    path = _map_path(name)
    assert path.exists(), f"{path} must exist"

    import os
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.lib.resource import res
        res.load_rules_and_ai()
        from soundrts.world import World

        text = path.read_text(encoding="utf-8")
        w = World([], 42)
        w._parse_map(text)
        w.square_width = int(w.square_width * 1000)
        w._build_map()

    n = w.nb_columns
    # Check every boundary square for an exit that jumps to the opposite edge.
    for x in range(n):
        for y in range(n):
            on_left = x == 0
            on_right = x == n - 1
            on_top = y == 0
            on_bottom = y == n - 1
            if not (on_left or on_right or on_top or on_bottom):
                continue
            sq = w.grid.get(f"{x},{y}")
            assert sq is not None, f"missing square {x},{y}"
            for exit_ in sq.exits:
                other = exit_.other_side.place
                wraps = False
                if on_right and other.col == 0 and other.row == y:
                    wraps = True
                if on_left and other.col == n - 1 and other.row == y:
                    wraps = True
                if on_bottom and other.row == 0 and other.col == x:
                    wraps = True
                if on_top and other.row == n - 1 and other.col == x:
                    wraps = True
                assert not wraps, (
                    f"{name}: toroidal wrap from ({x},{y}) -> "
                    f"({other.col},{other.row}) via {exit_.type_name}"
                )


def test_generator_avoids_boundary_entries():
    """tools/gen_ms500.py must avoid emitting boundary ``(N, row)``/``(col, N)``.

    If the generator is rerun with the same seed it must not reintroduce the
    wrap-causing entries.
    """
    src = Path("tools") / "gen_ms500.py"
    assert src.exists(), "tools/gen_ms500.py must exist"
    text = src.read_text(encoding="utf-8")
    # The fix: range(1, n) instead of range(1, n + 1) for the main corridors.
    assert "range(1, n)" in text, (
        "gen_ms500.py must clamp corridor range to (1, n) to avoid "
        "emitting wrap-triggering boundary entries"
    )
    # Secondary branches must also drop boundary picks.
    assert "x == n or x == 0 or y == n or y == 0" in text, (
        "gen_ms500.py must filter secondary branches that land on boundary"
    )
