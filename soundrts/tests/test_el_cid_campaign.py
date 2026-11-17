"""Tests for the AoE2 DE "El Cid" campaign (mods/aoe2/single/El Cid).

Covers:
1. The campaign is discovered and all 7 chapters (0-6) load.
2. Every chapter map parses: grid size, no toroidal wrap in
   ``west_east_paths`` / ``south_north_paths``.
3. Objective bookkeeping is coherent: every registered objective is
   added and completed, secondary objectives live in their own key
   space, and no chapter fires an instant victory.
4. The civilization switching works: Spanish in ch. 1/2/5/6, Saracens
   in ch. 3/4.
5. Every ``npc_*`` unit used by a map has a ``title`` in the
   campaign's ``ui/style.txt`` -- without one, ``EntityView.short_title``
   is empty and the unit can neither be selected nor targeted.
6. TTS coverage: every id referenced by a map or by style.txt exists in
   the English tts.txt AND in all 12 localised ui-* folders.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

CAMP = ROOT / "mods" / "aoe2" / "single" / "El Cid"
MAPS = [f"{n}.txt" for n in range(1, 7)]

LANGS = [
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
]

# The chapter -> faction table the DE original uses.
EXPECTED_FACTION = {
    1: "spanish",
    2: "spanish",
    3: "saracens",
    4: "saracens",
    5: "spanish",
    6: "spanish",
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _read(name: str) -> str:
    return (CAMP / name).read_text(encoding="utf-8")


def _statements(text: str) -> list[str]:
    """Map text with comments stripped, one statement per line."""
    out = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _parse_tts(path: Path) -> dict[int, str]:
    out: dict[int, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        m = re.match(r"^(\d+)\s+(.*)$", line)
        if m:
            out[int(m.group(1))] = m.group(2).strip()
    return out


def _col_index(token: str) -> int:
    """``a`` -> 1, ``b`` -> 2, ... ``l`` -> 12 (1-based column)."""
    idx = 0
    for ch in token.lower():
        idx = idx * 26 + (ord(ch) - ord("a") + 1)
    return idx


def _path_coords(text: str, keyword: str) -> list[tuple[int, int]]:
    """All coordinates listed on ``west_east_paths`` / ``south_north_paths``."""
    out = []
    for line in _statements(text):
        if not line.startswith(keyword + " "):
            continue
        for tok in line.split()[1:]:
            m = re.match(r"^([a-z]+)([0-9]+)$", tok.strip(","))
            if m:
                out.append((_col_index(m.group(1)), int(m.group(2))))
    return out


def _grid_size(text: str) -> tuple[int, int]:
    cols = lines = 0
    for line in _statements(text):
        if line.startswith("nb_columns "):
            cols = int(line.split()[1])
        elif line.startswith("nb_lines "):
            lines = int(line.split()[1])
    return cols, lines


# ---------------------------------------------------------------------------
# 1. campaign discovery
# ---------------------------------------------------------------------------
def test_campaign_is_discovered_with_all_chapters():
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    campaigns = [c for c in res.campaigns() if c.name == "El Cid"]
    assert campaigns, "El Cid campaign must be discovered by the aoe2 mod"
    numbers = sorted(ch.number for ch in campaigns[0].chapters)
    assert numbers == [0, 1, 2, 3, 4, 5, 6], f"Expected chapters 0-6, got {numbers}"


def test_chapter_zero_is_the_intro_cutscene():
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    cid = [c for c in res.campaigns() if c.name == "El Cid"][0]
    ch0 = cid.chapter(0)
    assert type(ch0).__name__ == "CutSceneChapter", (
        f"ch0 must be CutSceneChapter, got {type(ch0).__name__}"
    )
    assert list(ch0.title) == [9140], f"ch0 title must be 9140, got {ch0.title}"
    assert 9142 in ch0.sequence and 9143 in ch0.sequence, (
        f"ch0 sequence must contain 9142 and 9143, got {ch0.sequence}"
    )


def test_campaign_metadata_uses_the_campaign_tts_ids():
    text = _read("campaign.txt")
    assert re.search(r"^title\s+9140\b", text, re.MULTILINE), text
    assert re.search(r"^synopsis\s+9141\b", text, re.MULTILINE), text
    assert re.search(r"^intro\s+9142\s+9143\b", text, re.MULTILINE), text
    assert re.search(r"^default_faction\s+spanish\b", text, re.MULTILINE), text


# ---------------------------------------------------------------------------
# 2. map geometry / wrap safety
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", MAPS)
def test_map_declares_a_grid(name):
    cols, lines = _grid_size(_read(name))
    assert cols > 0 and lines > 0, f"{name} must declare nb_columns/nb_lines"


@pytest.mark.parametrize("name", MAPS)
def test_map_has_no_toroidal_wrap(name):
    """A boundary entry in a path line silently wraps to the far edge.

    ``_create_we_passage`` wraps when the column equals ``nb_columns``
    and ``_create_sn_passage`` wraps when the row equals ``nb_lines``.
    """
    text = _read(name)
    cols, lines = _grid_size(text)
    for col, row in _path_coords(text, "west_east_paths"):
        assert col < cols, (
            f"{name}: west_east_paths entry at column {col} would wrap "
            f"(nb_columns is {cols})"
        )
    for col, row in _path_coords(text, "south_north_paths"):
        assert row < lines, (
            f"{name}: south_north_paths entry at row {row} would wrap "
            f"(nb_lines is {lines})"
        )


@pytest.mark.parametrize("name", MAPS)
def test_map_starting_squares_cover_every_spawn(name):
    """Every ``player`` / ``computer_only`` slot needs a starting square.

    Without them the AI's auto_explore has no target and the enemies
    never look for the player.
    """
    text = _read(name)
    statements = _statements(text)
    starting = None
    slots = 0
    for line in statements:
        if line.startswith("starting_squares "):
            starting = line.split()[1:]
        elif line.startswith("player "):
            slots += 1
        elif line.startswith("computer_only "):
            slots += 1
    assert starting, f"{name} must declare starting_squares"
    assert len(starting) >= slots, (
        f"{name} declares {len(starting)} starting squares for {slots} spawn slots"
    )


# ---------------------------------------------------------------------------
# 3. objective bookkeeping
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", MAPS)
def test_map_registers_and_adds_the_same_objectives(name):
    text = _read(name)
    registered = set()
    added = set()
    for m in re.finditer(r"\(register_objective([^)]*)\)", text):
        registered |= {t for t in m.group(1).split() if t.isdigit()}
    for m in re.finditer(r"\(add_objective\s+(\d+)", text):
        added.add(m.group(1))
    assert registered, f"{name} must call register_objective"
    assert added == registered, (
        f"{name}: add_objective {sorted(added)} != register_objective {sorted(registered)}"
    )


@pytest.mark.parametrize("name", MAPS)
def test_map_completes_every_registered_objective(name):
    text = _read(name)
    registered = set()
    for m in re.finditer(r"\(register_objective([^)]*)\)", text):
        registered |= {t for t in m.group(1).split() if t.isdigit()}
    completed = set()
    for m in re.finditer(r"\(objective_complete\s+(\d+)", text):
        completed.add(m.group(1))
    assert registered <= completed, (
        f"{name}: registered objectives never completed: {sorted(registered - completed)}"
    )


@pytest.mark.parametrize("name", MAPS)
def test_secondary_objectives_are_not_registered(name):
    """Secondary objectives live in their own key space.

    A secondary number must not appear in ``register_objective`` and
    must not be completed with ``objective_complete``.
    """
    text = _read(name)
    registered = set()
    for m in re.finditer(r"\(register_objective([^)]*)\)", text):
        registered |= {t for t in m.group(1).split() if t.isdigit()}
    secondary = set()
    for m in re.finditer(r"\(add_secondary_objective\s+(\d+)", text):
        secondary.add(m.group(1))
    assert not (secondary & registered), (
        f"{name}: secondary objectives {sorted(secondary & registered)} "
        f"must not be registered as primary"
    )
    completed = set()
    for m in re.finditer(r"\(objective_complete\s+(\d+)", text):
        completed.add(m.group(1))
    assert not (secondary & completed), (
        f"{name}: secondary objectives {sorted(secondary & completed)} "
        f"must be completed with secondary_objective_complete"
    )


@pytest.mark.parametrize("name", MAPS)
def test_map_has_no_instant_victory_condition(name):
    """``(no_enemy_player_left)`` is already True on tick 0 for campaign NPCs."""
    text = _read(name)
    assert not re.search(
        r"^trigger\s+\S+\s+\(no_enemy_player_left\)", text, re.MULTILINE
    ), f"{name}: (no_enemy_player_left) fires immediately in a campaign map"


@pytest.mark.parametrize("name", MAPS)
def test_map_has_a_defeat_condition(name):
    text = _read(name)
    assert "(defeat)" in text, f"{name} must have a defeat trigger"


@pytest.mark.parametrize("name", MAPS)
def test_map_uses_only_counting_item_triggers(name):
    """``npc_has_item`` accepts one item; ``npc_has_items`` counts them.

    Objectives that ask for several relics must use the counting form.
    """
    text = _read(name)
    for m in re.finditer(r"\(npc_has_item\s+([^\)]*)\)", text):
        args = m.group(1).split()
        assert len(args) >= 3 and args[2].isdigit(), (
            f"{name}: (npc_has_item {m.group(1)}) must use the counting "
            f"form (npc_has_items) when more than one item is required"
        )


# ---------------------------------------------------------------------------
# 4. civilization switching
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("number,faction", sorted(EXPECTED_FACTION.items()))
def test_chapter_plays_the_expected_civilization(number, faction):
    text = _read(f"{number}.txt")
    m = re.search(r"^player_faction\s+(\S+)", text, re.MULTILINE)
    assert m, f"ch{number}.txt must declare player_faction"
    assert m.group(1) == faction, (
        f"ch{number}.txt must be played as {faction}, got {m.group(1)}"
    )


def test_civilization_switches_at_least_once():
    factions = [
        re.search(r"^player_faction\s+(\S+)", _read(f"{n}.txt"), re.MULTILINE).group(1)
        for n in range(1, 7)
    ]
    assert len(set(factions)) > 1, (
        "El Cid must switch civilization between chapters; "
        f"got {factions}"
    )


# ---------------------------------------------------------------------------
# 5. entity visibility (style.txt titles)
# ---------------------------------------------------------------------------
def _style_titles() -> dict[str, int]:
    """Map of style block name -> tts id of its title."""
    out: dict[str, int] = {}
    current = None
    for line in _statements(_read("ui/style.txt")):
        if line.startswith("def "):
            current = line.split()[1]
        elif line.startswith("title ") and current:
            out[current] = int(line.split()[1])
            current = None
    return out


def test_every_npc_used_by_a_map_has_a_style_title():
    titles = _style_titles()
    used = set()
    for name in MAPS:
        used |= set(re.findall(r"\bnpc_[a-z_]+\b", _read(name)))
    used.discard("npc_has_items")  # a trigger keyword, not a unit type
    missing = sorted(u for u in used if u not in titles)
    assert not missing, (
        f"these npc units have no style.txt title and would be invisible / "
        f"untargetable: {missing}"
    )


def test_every_style_title_has_a_tts_entry():
    english = _parse_tts(CAMP / "ui" / "tts.txt")
    for block, tid in sorted(_style_titles().items()):
        assert tid in english, f"style block {block} points at missing tts id {tid}"


# ---------------------------------------------------------------------------
# 6. TTS coverage
# ---------------------------------------------------------------------------
def _referenced_tts_ids() -> set[int]:
    ids: set[int] = set()
    for name in MAPS + ["0.txt", "campaign.txt"]:
        text = _read(name)
        for keyword in (
            "title",
            "intro",
            "sequence",
            "add_objective",
            "add_secondary_objective",
            "cut_scene",
            "square_name",
        ):
            for m in re.finditer(rf"^{keyword}\s+(.*)$", text, re.MULTILINE):
                for tok in m.group(1).split():
                    if tok.isdigit() and 9000 <= int(tok) <= 9999:
                        ids.add(int(tok))
        for m in re.finditer(r"\(cut_scene\s+(\d+)\)", text):
            ids.add(int(m.group(1)))
    return ids


def test_english_tts_defines_every_referenced_id():
    english = _parse_tts(CAMP / "ui" / "tts.txt")
    assert english, "ui/tts.txt must exist and be non-empty"
    missing = sorted(_referenced_tts_ids() - set(english))
    assert not missing, f"ui/tts.txt is missing referenced ids: {missing}"


def test_english_tts_has_no_empty_text():
    english = _parse_tts(CAMP / "ui" / "tts.txt")
    empty = sorted(i for i, text in english.items() if not text.strip())
    assert not empty, f"ui/tts.txt has empty text for ids: {empty}"


@pytest.mark.parametrize("lang", LANGS)
def test_localised_tts_covers_every_english_id(lang):
    english = _parse_tts(CAMP / "ui" / "tts.txt")
    path = CAMP / lang / "tts.txt"
    assert path.is_file(), f"{lang}/tts.txt is missing"
    localised = _parse_tts(path)
    missing = sorted(set(english) - set(localised))
    assert not missing, f"{lang}/tts.txt is missing ids: {missing}"
    extra = sorted(set(localised) - set(english))
    assert not extra, f"{lang}/tts.txt has ids not in ui/tts.txt: {extra}"
    empty = sorted(i for i, text in localised.items() if not text.strip())
    assert not empty, f"{lang}/tts.txt has empty text for ids: {empty}"


@pytest.mark.parametrize("lang", LANGS)
def test_localised_tts_keeps_the_french_typo_fixed(lang):
    """Regression: the French chapter 1 intro had a stray "pour fighting"."""
    path = CAMP / lang / "tts.txt"
    if not path.is_file():
        pytest.skip(f"{lang}/tts.txt is missing")
    text = path.read_text(encoding="utf-8")
    assert "pour fighting" not in text.lower(), (
        f"{lang}/tts.txt still contains the 'pour fighting' typo"
    )


def test_no_tts_id_collides_with_the_other_campaigns():
    """The campaign's ids must not clash with the other AoE2 campaigns."""
    english = set(_parse_tts(CAMP / "ui" / "tts.txt"))
    for other in ("Joan of Arc", "William Wallace"):
        base = ROOT / "mods" / "aoe2" / "single" / other
        for tts in base.glob("ui*/tts.txt"):
            other_ids = set(_parse_tts(tts))
            clash = sorted(english & other_ids)
            assert not clash, (
                f"tts ids {clash} are used by both El Cid and {other}/{tts.parent.name}"
            )
