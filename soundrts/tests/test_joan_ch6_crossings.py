"""Regression tests for the ch6 (Compiègne defence) multi-crossing design.

User-reported bug (2026-10-25):
    "敌人的进攻方向太固定了，必定从 e4 e5 进攻到 e6 ... 否则只需要我把军队
     放在 e5 就能一夫当关万夫莫开了，太容易了。"
    ("The enemy's attack direction is far too fixed -- it always attacks
     from e4 through e5 to e6.  Otherwise I only need to put my army on
     e5 and it is a one-man hold; far too easy.")

Root cause (measured with _tools/probe_ch6_routes.py BEFORE the fix):
    * The Oise (river row 4) had exactly ONE crossing: the bridge at e4.
      Every besieger's ``crossings(row4)`` was ``['e4']``.
    * The citadel at e6 has a single land approach, e5 -> e6.
    * Therefore one stack parked on e5 sealed the map completely:
      with the garrison at e5 the besiegers reached e5 and NEVER e6.

Fix:
    * The Oise now has FOUR crossings: the stone bridge at e4 and three
      fords at b4, g4 and i4 (``terrain ford`` = is_water + is_ground,
      walkable at half speed).
    * The ford columns appear in the ``south_north_paths`` lists, so the
      river row no longer has to be skipped for those columns.
    * computer3 (the a1 outpost, right beside the b4 ford) was upgraded
      from a passive forward position to a real attacker, so the western
      crossing is actually pressured.

These tests lock the design in so a later map edit cannot silently
collapse the chapter back to a single-crossing chokepoint.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

JOAN = Path("mods/aoe2/single/Joan of Arc")
MAP = JOAN / "6.txt"

RIVER_ROW = 4  # 1-based file row of the Oise
COLS = "abcdefghij"

# The four crossings of the Oise, in 1-based file coordinates.
EXPECTED_CROSSINGS = {
    "b4": "ford",
    "e4": "big_bridge",
    "g4": "ford",
    "i4": "ford",
}


def _read() -> str:
    return MAP.read_text(encoding="utf-8")


def _statements() -> list[str]:
    """Every non-comment, non-blank line of the map."""
    out = []
    for raw in _read().splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _terrain_of(square: str) -> str | None:
    """The terrain name the map assigns to ``square`` (e.g. 'ford')."""
    for line in _statements():
        if not line.startswith("terrain "):
            continue
        toks = line.split()
        for tok in toks[2:]:
            if tok == square:
                return toks[1]
    return None


def _south_north_tokens() -> set[str]:
    """Every square token that appears in some ``south_north_paths`` line."""
    toks: set[str] = set()
    for line in _statements():
        if not line.startswith("south_north_paths "):
            continue
        toks.update(line.split()[1:])
    return toks


def _south_north_columns() -> set[str]:
    """Columns that appear in some ``south_north_paths`` line."""
    cols: set[str] = set()
    for line in _statements():
        if not line.startswith("south_north_paths "):
            continue
        for tok in line.split()[1:]:
            cols.add(tok[:-1])  # 'a5' -> 'a'
    return cols


# ---------------------------------------------------------------------------
# 1. The map must declare the four crossings.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("square,terrain", sorted(EXPECTED_CROSSINGS.items()))
def test_ch6_has_four_oise_crossings(square, terrain):
    """The Oise must be crossable at b4, e4, g4 and i4.

    A single crossing is what made the chapter trivially easy: the
    besiegers all funnelled through the bridge and the garrison could
    plug e5.
    """
    assert _terrain_of(square) == terrain, (
        f"ch6 must declare 'terrain {terrain}' on {square}; got "
        f"{_terrain_of(square)!r}.  The Oise needs multiple crossings so "
        f"the enemy cannot be stopped by a single stack on e5."
    )


def test_ch6_river_row_has_no_unintended_crossings():
    """Only the four intended squares of the river row may be walkable.

    Every other river square must stay pure water (``terrain river``),
    otherwise the map would silently become an open lake.
    """
    for col in COLS:
        square = f"{col}{RIVER_ROW}"
        terrain = _terrain_of(square)
        if square in EXPECTED_CROSSINGS:
            assert terrain == EXPECTED_CROSSINGS[square], (
                f"{square} must be {EXPECTED_CROSSINGS[square]!r}, got {terrain!r}"
            )
        else:
            assert terrain == "river", (
                f"{square} must stay 'river' (impassable), got {terrain!r}"
            )


# ---------------------------------------------------------------------------
# 2. The ford columns must actually be wired into the passage graph.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("col", ["b", "g", "i"])
def test_ch6_ford_columns_have_vertical_passages(col):
    """A ford square only works if the row-4 square of its column
    appears in a ``south_north_paths`` line: that is what creates the
    passage from the south bank (row 3) to the north bank (row 5).

    The check is on the row-4 TOKEN (``b4``), not on the column: the
    non-ford columns list their other rows (``a1 a2 a3 a5 a6 a7``) and
    skip row 4, so a column-level check would pass for every column and
    would not detect a missing ford.
    """
    assert f"{col}4" in _south_north_tokens(), (
        f"ch6: ford square {col}4 must appear in a south_north_paths line so "
        f"the ford is actually connected across the river."
    )


def test_ch6_non_ford_columns_skip_the_river_row():
    """Every column that is NOT a ford must skip row 4 in its
    south_north list -- otherwise the water squares become vertical
    passages and the besiegers can wade across anywhere."""
    tokens = _south_north_tokens()
    for col in COLS:
        square = f"{col}{RIVER_ROW}"
        if square in EXPECTED_CROSSINGS:
            continue
        assert square not in tokens, (
            f"ch6: {square} is plain river but appears in a south_north_paths "
            f"line -- that would create an unintended water crossing."
        )


def test_ch6_every_river_column_is_in_the_south_north_list():
    """All ten columns must be listed, each either as a ford column or
    with the river row skipped.

    A column that is missing entirely would be walled off, and a column
    that includes row 4 without a ford terrain would become an
    unintended water crossing.
    """
    cols = _south_north_columns()
    assert cols == set(COLS), (
        f"ch6: south_north_paths must cover every column {COLS!r}, got {cols!r}"
    )


# ---------------------------------------------------------------------------
# 3. The enemy must actually use the fords (not just the bridge).
# ---------------------------------------------------------------------------

def test_ch6_third_besieger_is_an_attacker():
    """computer3 (the a1 outpost beside the b4 ford) must have a real AI.

    It used to be a passive forward position on the default timer AI,
    which left the western crossing unpressured.
    """
    text = _read()
    assert "trigger computer3 (timer 0) (ai intermediate)" in text, (
        "ch6: computer3 (a1, next to the b4 ford) must get a real attacking "
        "AI, otherwise the western crossing is never pressed."
    )


def test_ch6_besiegers_all_have_economies():
    """Every besieger needs gold / food / production buildings.

    Without them the AI cannot train units and never attacks, which
    would silently undo the multi-front design.
    """
    comp_lines = [
        line.split(";", 1)[0].strip()
        for line in _read().splitlines()
        if line.split(";", 1)[0].strip().startswith("computer_only ")
    ]
    assert len(comp_lines) == 3, (
        f"ch6 must have three besieger bases, got {comp_lines!r}"
    )
    for line in comp_lines:
        for needed in ("farm", "barracks", "archery_range", "peasant"):
            assert needed in line, (
                f"ch6 besieger must have {needed!r} to keep attacking, "
                f"got: {line!r}"
            )


# ---------------------------------------------------------------------------
# 4. The intro text must not lie about the number of crossings.
# ---------------------------------------------------------------------------

def test_ch6_intro_text_mentions_the_fords():
    """The ch6 intro (tts 8815) used to say the bridge was "the only
    crossing".  That is now false and would mislead the player, so every
    language must mention the extra crossings."""
    base = Path("mods") / "aoe2" / "single" / "Joan of Arc"
    for lang_dir in sorted(base.glob("ui*")):
        tts = lang_dir / "tts.txt"
        if not tts.exists():
            continue
        intro = ""
        for line in tts.read_text(encoding="utf-8").splitlines():
            if line.startswith("8815 "):
                intro = line
                break
        assert intro, f"{tts} is missing the ch6 intro line (8815)"
        assert "e4" in intro, (
            f"{tts}: ch6 intro must still mention the bridge square e4"
        )
        # At least two of the three ford squares must be named, so the
        # player knows where the other attacks come from.
        mentioned = sum(1 for sq in ("b4", "g4", "i4") if sq in intro)
        assert mentioned >= 2, (
            f"{tts}: ch6 intro must name at least two of the ford squares "
            f"(b4/g4/i4), found {mentioned}.  The intro must not claim the "
            f"bridge is the only crossing any more."
        )


def test_ch6_ford_place_names_exist_in_every_language():
    """The ford squares are labelled with tts ids 8900-8902, so the
    player can see what the enemy is crossing at."""
    base = Path("mods") / "aoe2" / "single" / "Joan of Arc"
    for lang_dir in sorted(base.glob("ui*")):
        tts = lang_dir / "tts.txt"
        if not tts.exists():
            continue
        ids = {
            int(line.split()[0])
            for line in tts.read_text(encoding="utf-8").splitlines()
            if line[:1].isdigit() and len(line.split()[0]) >= 4
        }
        for tts_id in (8900, 8901, 8902):
            assert tts_id in ids, (
                f"{tts} is missing tts id {tts_id} (ch6 ford place name)"
            )


def test_ch6_ford_squares_are_labelled():
    """b4 / g4 / i4 must carry the ford place names."""
    text = _read()
    for square, tts_id in (("2,4", "8900"), ("7,4", "8901"), ("9,4", "8902")):
        assert re.search(
            rf"square_name\s+{tts_id}\s+{re.escape(square)}\b", text
        ), (
            f"ch6 must label {square} with tts id {tts_id} (the ford name)"
        )
