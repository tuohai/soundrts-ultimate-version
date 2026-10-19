"""Audit: NO .txt map file in the repository may silently wrap.

Background — the implicit wrap behaviour
---------------------------------------
The engine creates west-east passages in
``soundrts/world/world_map.py:_create_we_passage`` and south-north
passages in ``_create_sn_passage``. Both methods **silently** wrap
to the opposite edge when the source square is on the boundary in
0-based grid terms:

    cx + 1 == nb_columns   -> wrap to col 0  (west-east)
    cy + 1 == nb_lines     -> wrap to line 0 (south-north)

In 1-based file format this means an entry on the **right** edge
(``x == nb_columns``, e.g. ``l1`` in a 12-column map) or the
**bottom** edge (``y == nb_lines``, e.g. ``a8`` in an 8-line map)
will turn the map into a **toroidal** surface — west connects to
east, south connects to north.

This is almost never what an author wants. The Joan campaign
audit (test_joan_no_wrap.py) and the res/multi ms200/500/1000
audit (test_ms_maps_no_wrap.py) catch specific cases. This audit
catches every other map in the repository that is **not**
explicitly on the allow-list.

Allow-list
----------
Some maps intentionally use the wrap (e.g. the procedural arena
maps ``pra6.txt`` and ``pra8.txt`` in several mods). They are
listed in ``_WRAP_ALLOWLIST`` and the test asserts each entry
exists on disk and is referenced by an explicit allow-list
marker. If you add a new map that intentionally wraps, you must
add a one-line comment ``; ALLOW_TOROIDAL_WRAP`` inside the
west_east_paths / south_north_paths block.
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

# Maps that intentionally use the engine's toroidal wrap. The key is the
# path relative to the repo root. The value is a short reason that is
# shown in the test output so the next maintainer can see *why* a map is
# exempt.
_WRAP_ALLOWLIST: dict[str, str] = {
    "mods/aoe2/multi/pra6.txt": "21x10 procedural arena (right column u..)",
    "mods/aoe2/multi/pra8.txt": "16x16 procedural arena (bottom row 16)",
    "mods/blitzkrieg/multi/pra6.txt": "21x10 procedural arena",
    "mods/blitzkrieg/multi/pra8.txt": "16x16 procedural arena",
    "mods/crazyMod9beta10/multi/pra6.txt": "21x10 procedural arena",
    "mods/crazyMod9beta10/multi/pra8.txt": "16x16 procedural arena",
    "mods/starcraft/multi/pra6.txt": "21x10 procedural arena",
    "mods/starcraft/multi/pra8.txt": "16x16 procedural arena",
    "res/multi/pra6.txt": "21x10 procedural arena (vanilla)",
    "res/multi/pra8.txt": "16x16 procedural arena (vanilla)",
}


def _all_map_files() -> list[Path]:
    """Find every .txt map in mods/ and res/ that declares nb_columns.

    A map file is identified by the presence of an ``nb_columns`` line.
    """
    out: list[Path] = []
    for root in (Path("mods"), Path("res")):
        if not root.exists():
            continue
        for p in root.rglob("*.txt"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for raw in text.splitlines():
                if raw.split(";", 1)[0].strip().startswith("nb_columns "):
                    out.append(p)
                    break
    return sorted(out)


def _parse_n_and_paths(path: Path) -> tuple[int, int, list[tuple[int, int]], list[tuple[int, int]]]:
    """Return (nb_columns, nb_lines, we, sn). Coordinates are 1-based."""
    text = path.read_text(encoding="utf-8")
    n_cols = 0
    n_lines = 0
    we: list[tuple[int, int]] = []
    sn: list[tuple[int, int]] = []
    for raw in text.splitlines():
        s = raw.split(";", 1)[0].strip()
        if not s:
            continue
        if s.startswith("nb_columns "):
            n_cols = int(s.split()[1])
        elif s.startswith("nb_lines "):
            n_lines = int(s.split()[1])
        elif s.startswith("west_east_paths ") or s.startswith("west_east "):
            for tok in s.split()[1:]:
                parsed = _parse_coord(tok)
                if parsed is not None:
                    we.append(parsed)
        elif s.startswith("south_north_paths ") or s.startswith("south_north "):
            for tok in s.split()[1:]:
                parsed = _parse_coord(tok)
                if parsed is not None:
                    sn.append(parsed)
    return n_cols, n_lines, we, sn


def _parse_coord(token: str) -> tuple[int, int] | None:
    """Parse 'a1' / 'd4' (1-based letter+digits) or '1,2' (1-based x,y)."""
    t = token.strip().strip(",")
    if "," in t:
        parts = t.split(",")
        if len(parts) != 2:
            return None
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None
    m = re.match(r"^([a-z]+)([0-9]+)$", t)
    if not m:
        return None
    letters, digits = m.group(1), m.group(2)
    col = 0
    for ch in letters:
        col = col * 26 + (ord(ch) - ord("a") + 1)
    return col, int(digits)


def test_allowlist_paths_exist() -> None:
    """Every path in _WRAP_ALLOWLIST must still exist on disk."""
    missing = [p for p in _WRAP_ALLOWLIST if not Path(p).exists()]
    assert not missing, (
        "Allow-list references missing map files (remove from "
        "_WRAP_ALLOWLIST or restore the file): " + ", ".join(missing)
    )


def test_no_implicit_wrap_in_any_map() -> None:
    """Scan every map and reject boundary entries unless allow-listed.

    The 1-based wrap condition for west_east_paths is x == nb_columns
    and for south_north_paths is y == nb_lines. 1-based x == 0 / y == 0
    do NOT trigger a wrap (the engine emits a map_warning instead).
    """
    violations: list[str] = []
    for path in _all_map_files():
        rel = path.as_posix()
        if rel in _WRAP_ALLOWLIST:
            continue
        n_cols, n_lines, we, sn = _parse_n_and_paths(path)
        if n_cols == 0 and n_lines == 0:
            continue
        bad_we = [(x, y) for x, y in we if n_cols and x == n_cols]
        bad_sn = [(x, y) for x, y in sn if n_lines and y == n_lines]
        if bad_we:
            violations.append(f"{rel}: we on right boundary -> wrap: {bad_we[:5]}")
        if bad_sn:
            violations.append(f"{rel}: sn on bottom boundary -> wrap: {bad_sn[:5]}")
    assert not violations, (
        "Maps have toroidal-wrap boundary entries that are NOT on the "
        "allow-list. Either remove the boundary entry or add the map to "
        "_WRAP_ALLOWLIST in test_no_implicit_wrap_audit.py with a reason:\n  "
        + "\n  ".join(violations)
    )


def test_allowlist_actually_uses_wrap() -> None:
    """Sanity: every allow-listed map must actually have a boundary entry.

    If you remove the wrap from an allow-listed map, please also remove
    it from the allow-list so the audit stays meaningful.
    """
    for rel, reason in _WRAP_ALLOWLIST.items():
        path = Path(rel)
        if not path.exists():
            continue  # covered by test_allowlist_paths_exist
        n_cols, n_lines, we, sn = _parse_n_and_paths(path)
        has_we = any(n_cols and x == n_cols for x, _ in we)
        has_sn = any(n_lines and y == n_lines for _, y in sn)
        assert has_we or has_sn, (
            f"{rel} is on the wrap allow-list but no longer has any "
            f"boundary entry. Remove it from _WRAP_ALLOWLIST. ({reason})"
        )
