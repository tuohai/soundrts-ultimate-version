"""Regression: perception._refresh_combat_snapshot must not crash when
enemy_players contains objects lacking a ``units`` attribute.

Real-world traceback observed during a Joan of Arc ch2 game tick:

    File "soundrts/worldplayerbase/perception.py", line 1829, in _refresh_combat_snapshot
        for o in p.units:
    AttributeError: 'Human' object has no attribute 'units'. Did you mean: '_units'?
    AttributeError: 'Computer' object has no attribute 'units'. Did you mean: '_units'?

The fix is to use ``getattr(p, "units", None) or ()`` which is the same
defensive pattern already used across ``worldplayercomputer.py`` (see
lines 488, 672, 816, 2363, 2760, 3438, 3484).
"""
from __future__ import annotations

import re
from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


def test_refresh_combat_snapshot_uses_getattr_units():
    """The ``for o in p.units`` loop must be guarded by getattr()."""
    text = _source("soundrts", "worldplayerbase", "perception.py")
    m = re.search(
        r"def _refresh_combat_snapshot\(self\):(.*?)(?=^    def |\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    assert m, "_refresh_combat_snapshot not found"
    body = m.group(1)

    # The unguarded pattern that caused the AttributeError must be gone.
    assert "for o in p.units:" not in body, (
        "Unguarded `for o in p.units:` is back -- regression."
    )

    # The defensive pattern must be present.
    assert re.search(
        r"for o in getattr\(p, ['\"]units['\"], None\) or \(\):",
        body,
    ), "Missing defensive `getattr(p, 'units', None) or ()` in _refresh_combat_snapshot."


def test_computer_module_already_uses_same_defensive_pattern():
    """Sanity-check: ``worldplayercomputer.py`` has been using this pattern
    for years; we are aligning perception with it."""
    text = _source("soundrts", "worldplayercomputer.py")
    assert "getattr(self, \"units\", ()) or ()" in text or "getattr(self, 'units', ()) or ()" in text
