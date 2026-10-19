"""Audit: Joan of Arc campaign maps must NOT have toroidal wrap passages.

Background:
    The engine creates west-east passages via _create_we_passage
    (soundrts/world/world_map.py):

        col = cx + 1
        if col == self.nb_columns:    # cx == nb_columns - 1 (0-based grid)
            col = 0; is_a_portal = True

    A 1-based ``(N, row)`` or ``a,1`` parses to 0-based
    ``(N-1, row)`` (or ``(0, 0)``), which trips the portal branch
    and creates a wrap passage to col 0. Same for south_north.

    This audit confirms that no 1-based boundary coordinate that
    would create a wrap is present in any Joan of Arc map.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import pytest

_CAMPAIGN = Path("mods") / "aoe2" / "single" / "Joan of Arc"
_MAPS = ("1.txt", "2.txt", "3.txt", "4.txt", "5.txt", "6.txt")


def _map_path(name: str) -> Path:
    return _CAMPAIGN / name


def _parse_n_and_paths(path: Path) -> tuple[int, int, list[tuple[int, int]], list[tuple[int, int]]]:
    """Return (nb_columns, nb_lines, [(x, y) for we, ...] for sn).

    Coordinates are kept as 1-based (file format).
    """
    text = path.read_text(encoding="utf-8")
    n_cols = 0
    n_lines = 0
    we: list[tuple[int, int]] = []
    sn: list[tuple[int, int]] = []
    for raw in text.splitlines():
        # Strip end-of-line comments (anything after ';' on a non-statement line)
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("nb_columns "):
            n_cols = int(line.split()[1])
        elif line.startswith("nb_lines "):
            n_lines = int(line.split()[1])
        elif line.startswith("west_east_paths ") or line.startswith("west_east "):
            for tok in line.split()[1:]:
                parsed = _parse_coord(tok)
                if parsed is not None:
                    we.append(parsed)
        elif line.startswith("south_north_paths ") or line.startswith("south_north "):
            for tok in line.split()[1:]:
                parsed = _parse_coord(tok)
                if parsed is not None:
                    sn.append(parsed)
    return n_cols, n_lines, we, sn


def _parse_coord(token: str) -> tuple[int, int] | None:
    """Parse a coordinate token. Supports 'a1' / 'd4' (1-based letter+digits)
    and '1,2' (1-based x,y) formats. Returns None for non-coordinate tokens.
    """
    t = token.strip().strip(",")
    if "," in t:
        parts = t.split(",")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None
    import re
    m = re.match(r"^([a-z]+)([0-9]+)$", t)
    if not m:
        return None
    letters, digits = m.group(1), m.group(2)
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("a") + 1)
    return col, int(digits)


@pytest.mark.parametrize("name", _MAPS)
def test_no_boundary_entries_in_joan_map(name):
    """Each Joan map must not contain 1-based boundary entries in
    west_east / south_north paths; those would trigger the engine's
    silent portal wrap (soundrts/world/world_map.py:_create_we_passage
    and _create_sn_passage).

    In 0-based grid terms the engine wraps when
        cx + 1 == nb_columns   (west_east)
        cy + 1 == nb_lines     (south_north)
    In 1-based file format, the **right** edge is x == nb_columns
    (e.g. ``l1`` in a 12-column map) and the **bottom** edge is
    y == nb_lines (e.g. ``a8`` in an 8-line map). 1-based x == 0
    and y == 0 (i.e. ``a1``) do NOT trigger a wrap — the engine
    just resolves them to a non-existent neighbour and emits a
    ``map_warning`` (not a wrap).

    So:
      - we entries must avoid x == nb_columns (1-based)
      - sn entries must avoid y == nb_lines   (1-based)
    """
    path = _map_path(name)
    if not path.exists():
        pytest.skip(f"{path} not present")
    n_cols, n_lines, we, sn = _parse_n_and_paths(path)
    assert n_cols > 0, f"{name} did not declare nb_columns"
    assert n_lines > 0, f"{name} did not declare nb_lines"
    bad_we = [(x, y) for x, y in we if x == n_cols]
    bad_sn = [(x, y) for x, y in sn if y == n_lines]
    assert not bad_we, (
        f"{name}: west_east entries on 1-based x boundary "
        f"(x in {{0, nb_columns}}) would wrap: {bad_we[:10]}"
    )
    assert not bad_sn, (
        f"{name}: south_north entries on 1-based y boundary "
        f"(y in {{0, nb_lines}}) would wrap: {bad_sn[:10]}"
    )
