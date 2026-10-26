"""Regression tests for the Joan of Arc objective / cut_scene tts ids.

Background (user-reported bug, 2026-10-25):
  In ``mods/aoe2/single/Joan of Arc/5.txt`` (chapter 5, "The Cleansing
  of the Loire") the second primary objective was declared as::

      trigger player1 (timer 0) (add_objective 2 8830)

  but tts id 8830 is the **chapter 1 cut_scene** line ("The Dauphin
  reads the letter and falls to his knees. France shall rise again.
  ...").  The F9 objective list therefore showed a piece of narration
  instead of a mission goal.

  The root cause was an id collision.  8830 originally held the ch5
  objective text and was later repurposed as a cut_scene line by
  ``_tools/update_ch1_tts.py``, while ``5.txt`` kept referencing it.

Two related latent problems are guarded here as well:

  * ch5 objectives 1 and 3 used the generic 8829 / 8831 strings, which
    describe a *different* set of goals (8829 = "the English outpost on
    the lower Loire", 8831 = "every English tower and castle") than what
    ch5 actually asks for (the three English bridge towns).
  * ids 8839 / 8853 / 8854 / 8855 (the ch2 objectives) were defined only
    in ``ui-zh/tts.txt``.  Every other language therefore fell back to
    the English text through the global tts lookup, so a French or
    German player read the ch2 objectives in English.

The fix gives every language its own objective strings:

    8839  ch2 obj 1   Escort Joan to Blois
    8853  ch2 obj 2   Deliver six supply carts to the Orleans town center
    8854  ch2 obj 3   Advance to the Castle Age
    8855  ch2 obj 4   Destroy one English castle
    8856  ch5 obj 1   Capture Meung-sur-Loire
    8857  ch5 obj 2   Capture Beaugency
    8858  ch5 obj 3   Capture Jallains

and points ``5.txt`` at 8856-8858.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
JOAN = REPO_ROOT / "mods/aoe2/single/Joan of Arc"

CAMPAIGN_LANGS = (
    "ui",
    "ui-be",
    "ui-cs",
    "ui-de",
    "ui-es",
    "ui-fr",
    "ui-it",
    "ui-pl",
    "ui-pt-BR",
    "ui-ru",
    "ui-sk",
    "ui-vi",
    "ui-zh",
)

# tts ids that are *cut_scene narration* and must never be used as an
# objective description.
CUTSCENE_ONLY_IDS = (
    8826,  # Baudricourt grants the holy letter (ch1)
    8830,  # The Dauphin reads the letter (ch1)  <-- the bug
    8834,  # La Hire lets Joan pass (legacy ch2)
    8835,  # Joan reaches Blois (ch2)
    8836,  # The supply wagons have crossed (ch2)
    8837,  # Orleans must reach the Castle Age (ch2)
    8838,  # The English castle crumbles (ch2)
)

# The dedicated objective ids, per chapter.
CH2_OBJECTIVE_IDS = (8839, 8853, 8854, 8855)
CH5_OBJECTIVE_IDS = (8856, 8857, 8858)
ALL_OBJECTIVE_IDS = CH2_OBJECTIVE_IDS + CH5_OBJECTIVE_IDS


def _read_map(name: str) -> str:
    return (JOAN / name).read_text(encoding="utf-8")


def _tts_table(lang: str) -> dict[int, str]:
    """Parse ``ui<lang>/tts.txt`` into ``{id: text}``."""
    table: dict[int, str] = {}
    path = JOAN / lang / "tts.txt"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(";")[0].strip()
        if not line:
            continue
        parts = line.split()
        if parts and parts[0].isdigit():
            table[int(parts[0])] = " ".join(parts[1:])
    return table


def _add_objective_ids(name: str) -> list[tuple[int, int]]:
    """Return ``[(objective number, tts id)]`` declared by a map file."""
    found = []
    pattern = re.compile(
        r"^\s*trigger\b.*\(add_objective\s+(\d+)\s+(\d+)\)", re.MULTILINE
    )
    for m in pattern.finditer(_read_map(name)):
        found.append((int(m.group(1)), int(m.group(2))))
    return found


# ---------------------------------------------------------------------------
# 1) The reported bug: no objective may point at a cut_scene narration id.
# ---------------------------------------------------------------------------


def test_ch5_objectives_do_not_use_cut_scene_ids():
    """ch5 objective 2 used to be tts id 8830 (the ch1 cut_scene line).

    Regression: the F9 objective list showed
    "The Dauphin reads the letter and falls to his knees..." instead of
    a mission goal.
    """
    ids = [tid for _num, tid in _add_objective_ids("5.txt")]
    assert ids, "5.txt declares no add_objective at all"
    for tid in ids:
        assert tid not in CUTSCENE_ONLY_IDS, (
            "5.txt uses cut_scene narration id %d as an objective" % tid
        )
    assert 8830 not in ids, (
        "5.txt objective 2 must not reference the ch1 cut_scene id 8830"
    )


def test_ch5_objectives_use_dedicated_ids():
    """ch5 must use its own objective strings 8856-8858."""
    ids = [tid for _num, tid in _add_objective_ids("5.txt")]
    assert ids == list(CH5_OBJECTIVE_IDS), (
        "5.txt objectives must be %s, got %s"
        % (list(CH5_OBJECTIVE_IDS), ids)
    )


def test_no_chapter_uses_a_cut_scene_id_as_an_objective():
    """Guard every chapter of the campaign, not just ch5."""
    for chapter in ("1.txt", "2.txt", "3.txt", "4.txt", "5.txt", "6.txt"):
        for num, tid in _add_objective_ids(chapter):
            assert tid not in CUTSCENE_ONLY_IDS, (
                "%s objective %d uses cut_scene narration id %d"
                % (chapter, num, tid)
            )


# ---------------------------------------------------------------------------
# 2) Every language must define every objective id.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lang", CAMPAIGN_LANGS)
def test_every_language_defines_all_objective_ids(lang):
    """Each language must ship its own objective text.

    Regression: 8839 / 8853-8855 existed only in ui-zh, so all other
    languages silently fell back to the English strings.
    """
    table = _tts_table(lang)
    missing = [i for i in ALL_OBJECTIVE_IDS if i not in table]
    assert not missing, (
        "%s/tts.txt is missing objective id(s): %s" % (lang, missing)
    )
    for i in ALL_OBJECTIVE_IDS:
        assert table[i].strip(), (
            "%s/tts.txt objective id %d has empty text" % (lang, i)
        )


@pytest.mark.parametrize("lang", CAMPAIGN_LANGS)
def test_objective_texts_are_translated_not_english_fallback(lang):
    """Only the English file may use the English objective strings.

    A non-English file whose objective text is byte-identical to the
    English one means the translation was never added.
    """
    if lang == "ui":
        return
    en = _tts_table("ui")
    table = _tts_table(lang)
    identical = [
        i for i in ALL_OBJECTIVE_IDS
        if table.get(i, "").strip() == en.get(i, "").strip()
    ]
    assert not identical, (
        "%s/tts.txt has untranslated objective id(s): %s"
        % (lang, identical)
    )


# ---------------------------------------------------------------------------
# 3) The objective strings must describe the goals the map actually has.
# ---------------------------------------------------------------------------


def test_ch5_objective_texts_name_the_three_bridge_towns():
    """ch5 asks for Meung-sur-Loire, Beaugency and Jallains.

    The old 8829 / 8831 strings talked about "the lower Loire outpost"
    and "every English tower and castle" instead.
    """
    en = _tts_table("ui")
    assert "Meung" in en[8856]
    assert "Beaugency" in en[8857]
    assert "Jallains" in en[8858]
    # The goal triggers destroy one town center each.
    text = _read_map("5.txt")
    assert "enemy_building_destroyed a1 town_center" in text
    assert "enemy_building_destroyed d3 town_center" in text
    assert "enemy_building_destroyed f5 town_center" in text


def test_cut_scene_ids_still_hold_their_narration():
    """The cut_scene lines must keep their original narration text."""
    en = _tts_table("ui")
    assert "Dauphin reads the letter" in en[8830]
    assert "Baudricourt studies the girl" in en[8826]


def test_zh_objective_texts_are_chinese():
    """The Chinese file must have Chinese objective text, not English."""
    zh = _tts_table("ui-zh")
    for i in ALL_OBJECTIVE_IDS:
        assert not re.match(r"^[A-Za-z]", zh[i]), (
            "ui-zh/tts.txt objective id %d is not Chinese: %r" % (i, zh[i])
        )
    assert "默恩" in zh[8856]
    assert "博让西" in zh[8857]
    assert "雅兰" in zh[8858]
