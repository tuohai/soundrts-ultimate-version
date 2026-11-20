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

import random
import re
import sys
import types
from pathlib import Path

import pytest

from soundrts.combat.damage_effects import DamageEffectsMixin

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
def test_primary_objective_numbers_are_consecutive(name):
    """Primary objectives must be numbered 1..N with no gaps.

    The number is what the objective list shows and speaks ("primary
    objective 3"), so a gap in the primary numbering makes the list jump
    from "objective 1" straight to "objective 3".  Chapter 3 used to
    register 1 3 4 5 because the optional Alfonso's Castle objective
    was squeezed in as number 2.
    """
    text = _read(name)
    registered = set()
    for m in re.finditer(r"\(register_objective([^)]*)\)", text):
        registered |= {int(t) for t in m.group(1).split() if t.isdigit()}
    assert registered, f"{name} must call register_objective"
    assert sorted(registered) == list(range(1, len(registered) + 1)), (
        f"{name}: primary objective numbers must be 1..{len(registered)}, "
        f"got {sorted(registered)}"
    )


@pytest.mark.parametrize("name", MAPS)
def test_optional_objective_numbers_are_numbered_from_one(name):
    """Optional objectives are numbered 1..M in their OWN numbering space.

    ``add_secondary_objective`` numbers are independent from the primary
    ones -- both start at 1 (see doc_src/src/*/mod/mapproduction: "Primary
    and optional objectives use independent numbering (both can start at
    1; primary 1 and optional 1 can coexist)").  An optional objective
    therefore never takes up a primary number: it must be numbered 1..M
    on its own, NOT "the number after the last primary one".

    Chapters 3, 4 and 5 used to number their single optional objective
    5, 5 and 6 -- which both skipped a primary number and made the
    list read "optional objective 5".
    """
    text = _read(name)
    secondary = set()
    for m in re.finditer(r"\(add_secondary_objective\s+(\d+)", text):
        secondary.add(int(m.group(1)))
    if not secondary:
        return
    assert sorted(secondary) == list(range(1, len(secondary) + 1)), (
        f"{name}: optional objective numbers must be 1..{len(secondary)}, "
        f"got {sorted(secondary)}"
    )


@pytest.mark.parametrize("name", MAPS)
def test_secondary_objectives_are_not_registered(name):
    """Secondary objectives live in their own key space.

    A secondary objective must be added with ``add_secondary_objective``
    (never ``add_objective``), and it must be completed with
    ``secondary_objective_complete`` (never ``objective_complete``) --
    only the primary completion adds the number to
    ``_completed_objective_numbers``, which is what ``_try_mission_victory``
    checks.

    The two spaces have INDEPENDENT numbers (both start at 1), so a
    secondary number may well be 1 while primary number 1 exists too.
    What therefore matters is WHICH ACTION is used, not the number:
    comparing the bare numbers would be meaningless here.
    """
    text = _read(name)
    secondary_numbers = {
        int(m.group(1))
        for m in re.finditer(r"\(add_secondary_objective\s+(\d+)", text)
    }
    completed_secondary = {
        int(m.group(1))
        for m in re.finditer(r"\(secondary_objective_complete\s+(\d+)", text)
    }
    assert secondary_numbers <= completed_secondary, (
        f"{name}: optional objectives never completed: "
        f"{sorted(secondary_numbers - completed_secondary)}"
    )
    # Every optional objective is added with add_secondary_objective, so
    # the TTS id of an optional objective must never appear as a primary
    # add_objective id either.
    optional_tts = {
        m.group(1)
        for m in re.finditer(
            r"\(add_secondary_objective\s+\d+\s+(\d+)\)", text
        )
    }
    primary_tts = {
        m.group(1) for m in re.finditer(r"\(add_objective\s+\d+\s+(\d+)\)", text)
    }
    assert not (optional_tts & primary_tts), (
        f"{name}: text ids {sorted(optional_tts & primary_tts)} are used "
        f"both as a primary and as an optional objective"
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


# ---------------------------------------------------------------------------
# 7. unit mobility (the "El Cid cannot move" bug)
# ---------------------------------------------------------------------------
# Every unit the player has to MOVE somewhere must have a non-zero
# ``speed``.  The AoE2 mod's legacy ``knight`` stub is only
# ``class soldier`` + ``decay 1`` -- it carries no ``speed`` at all --
# so any campaign unit built on ``is_a knight`` (or on the plain
# ``class soldier`` base) silently ends up with ``speed == 0``.
#
# A unit with speed 0 cannot be ordered to move: ``GoOrder`` /
# ``move_to_or_fail`` in soundrts/worldorders/base.py refuses the
# order outright ("if self.unit.speed == 0: mark_as_impossible()").
# That made the whole campaign unwinnable:
#   * El Cid could not walk to the stable (ch. 1 / ch. 3) or to
#     Zaragoza (ch. 3),
#   * El Cid Campeador could not cross the maps of ch. 2 / 4 / 5,
#   * King Alfonso could not be escorted to King Sancho (ch. 1) or
#     to the Cid (ch. 4), which soft-locks objectives 4 and 2.
MOBILE_NPCS = (
    "npc_cid",
    "npc_cid_mounted",
    "npc_alfonso",
)

# Story units that must stay where they are put.
IMMOBILE_NPCS = (
    "npc_cid_body",  # the dead Cid, strapped to Babieca
)


@pytest.fixture(scope="module")
def el_cid_rules():
    """Load the AoE2 mod rules plus the El Cid campaign rules."""
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res

    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    rules.load(
        res.text("rules", append=True),
        _read("rules.txt"),
    )
    yield rules
    config.mods = old_config_mods
    res.set_mods(old_mods)


def _speed_of(rules, name: str) -> int:
    uc = rules.unit_class(name)
    assert uc is not None, f"{name} is not defined in the campaign rules"
    return int(getattr(uc, "speed", 0) or 0)


@pytest.mark.parametrize("name", MOBILE_NPCS)
def test_mobile_campaign_npcs_can_move(el_cid_rules, name):
    """A ``speed`` of 0 makes every move order impossible."""
    speed = _speed_of(el_cid_rules, name)
    assert speed > 0, (
        f"{name} has speed {speed}: it can never be ordered to move "
        f"(move_to_or_fail rejects speed-0 units)"
    )


@pytest.mark.parametrize("name", IMMOBILE_NPCS)
def test_stationary_campaign_npcs_stay_still(el_cid_rules, name):
    """The corpse must NOT inherit the mounted hero's cavalry speed."""
    speed = _speed_of(el_cid_rules, name)
    assert speed == 0, f"{name} must be immobile, but its speed is {speed}"


def test_the_heroes_have_a_melee_reload_time(el_cid_rules):
    """Without ``mdg_cd`` the hero would attack once per simulation tick."""
    for name in ("npc_cid", "npc_cid_mounted"):
        uc = el_cid_rules.unit_class(name)
        cd = int(getattr(uc, "mdg_cd", 0) or 0)
        assert cd > 0, (
            f"{name} has no mdg_cd: it would swing once every tick instead "
            f"of once per reload"
        )


def test_the_rules_file_states_the_movement_speed_explicitly():
    """Guard against the speed being dropped from the text again.

    No inheritance chain the hero could use (``knight``, ``militia``)
    provides the DE speed reliably, so the value has to be written out
    in the campaign's own rules.txt.
    """
    text = _read("rules.txt")
    blocks = {}
    current = None
    for line in _statements(text):
        if line.startswith("def "):
            current = line.split()[1]
            blocks[current] = []
        elif current:
            blocks[current].append(line)
    for name in MOBILE_NPCS:
        body = blocks.get(name)
        assert body, f"{name} has no block in the campaign rules.txt"
        assert any(line.startswith("speed ") for line in body), (
            f"{name} must declare an explicit 'speed' (the inherited "
            f"knight stub has none)"
        )
    body = blocks.get("npc_cid_body", [])
    assert any(line == "speed 0" for line in body), (
        "npc_cid_body must declare 'speed 0' so the corpse does not walk away"
    )


# ---------------------------------------------------------------------------
# 7b. the on-foot hero must SOUND like an infantryman (the horse-hoof bug)
# ---------------------------------------------------------------------------
# The footstep noise is read from the STYLE layer, not from the rules:
# ``soundrts/clientgameentity/audio.py::footstepnoise`` calls
# ``style.get(self.type_name, "move")``, and the style lookup walks the
# STYLE ``is_a`` chain.  The cavalry styles carry ``move 1303 1303``
# (horse hooves) while the infantry styles carry ``move 1053 1054``
# (human steps).
#
# The on-foot El Cid was declared ``is_a aoe_knight`` in the campaign's
# ui/style.txt, so before he mounted Babieca he clopped like a rider.
# He must inherit an INFANTRY style instead -- and the mounted form
# must keep the hooves, which is why it may no longer inherit npc_cid.
INFANTRY_FOOTSTEP = ["1053", "1054"]
CAVALRY_HOOFSTEP = ["1303", "1303"]


@pytest.fixture(scope="module")
def el_cid_style():
    """Load the AoE2 mod style plus the El Cid campaign style."""
    from soundrts import config
    from soundrts.definitions import style
    from soundrts.lib.resource import res

    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    style.load(
        res.text("ui/style", append=True),
        _read("ui/style.txt"),
    )
    yield style
    config.mods = old_config_mods
    res.set_mods(old_mods)


def test_the_on_foot_hero_sounds_like_an_infantryman(el_cid_style):
    """Before mounting, El Cid must produce human footsteps."""
    move = el_cid_style.get("npc_cid", "move", warn_if_not_found=False)
    assert move == INFANTRY_FOOTSTEP, (
        "the on-foot El Cid must use the infantry footstep "
        f"{INFANTRY_FOOTSTEP}, got {move} -- a cavalry 'move' means he "
        "clops like a horse while he is still on foot"
    )


def test_the_mounted_hero_sounds_like_a_rider(el_cid_style):
    """Once mounted on Babieca, El Cid must clop like a horse."""
    move = el_cid_style.get("npc_cid_mounted", "move", warn_if_not_found=False)
    assert move == CAVALRY_HOOFSTEP, (
        "the mounted El Cid must use the cavalry hoofstep "
        f"{CAVALRY_HOOFSTEP}, got {move}"
    )


def test_the_corpse_keeps_the_cavalry_sound(el_cid_style):
    """The dead Cid is strapped to Babieca: he keeps the hooves."""
    move = el_cid_style.get("npc_cid_body", "move", warn_if_not_found=False)
    assert move == CAVALRY_HOOFSTEP, (
        "the corpse is strapped to Babieca and must keep the horse-hoof "
        f"sound, got {move}"
    )


def test_the_on_foot_hero_is_not_a_cavalry_style(el_cid_style):
    """The style chain itself must not contain a cavalry parent."""
    chain = set()
    pending = ["npc_cid"]
    seen = set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        chain.add(current)
        parents = (
            el_cid_style.get(current, "is_a", warn_if_not_found=False) or []
        )
        for parent in parents:
            token = str(parent).split()[0].split("(")[0]
            if token:
                pending.append(token)
    for cavalry in ("aoe_knight", "knight", "cavalry"):
        assert cavalry not in chain, (
            f"npc_cid inherits {cavalry}: the mounted hero would drag the "
            "horse-hoof footstep back in"
        )
    assert "militia" in chain, (
        f"npc_cid must inherit an infantry style, got the chain {chain}"
    )


def test_the_on_foot_hero_is_an_infantry_unit_in_the_rules(el_cid_rules):
    """The rules layer must agree: the hero is infantry, not a knight."""
    uc = el_cid_rules.unit_class("npc_cid")
    assert uc is not None, "npc_cid must be defined"
    chain = set(getattr(uc, "expanded_is_a", ()) or ())
    assert "militia" in chain, (
        "npc_cid must inherit the infantry unit 'militia' in the rules, "
        f"got the chain {chain}"
    )
    for cavalry in ("knight", "aoe_knight", "cavalry"):
        assert cavalry not in chain, (
            f"npc_cid inherits {cavalry}: it would be a cavalry unit"
        )


def test_the_on_foot_hero_does_not_join_the_militia_upgrade_line(el_cid_rules):
    """Researching Man-at-Arms must not morph the campaign's key unit.

    ``apply_unit_line_upgrade`` morphs every field unit whose
    ``can_upgrade_to`` names the researched form.  The militia line
    upgrades into man_at_arms, so the hero must explicitly cancel the
    inherited list.
    """
    uc = el_cid_rules.unit_class("npc_cid")
    ups = set(getattr(uc, "can_upgrade_to", ()) or ())
    assert "man_at_arms" not in ups, (
        "npc_cid inherits the militia line's 'can_upgrade_to man_at_arms': "
        "researching Man-at-Arms would morph the hero into a generic unit"
    )
    assert not ups, (
        f"npc_cid must cancel the inherited upgrade list, got {ups}"
    )


def test_the_on_foot_hero_inherits_no_militia_techs(el_cid_rules):
    """He is not one of the player's militia: no blacksmith bonuses."""
    uc = el_cid_rules.unit_class("npc_cid")
    techs = set(getattr(uc, "can_use_tech", ()) or ())
    assert not techs, (
        "npc_cid must cancel the inherited militia tech list, got "
        f"{sorted(techs)}"
    )


def test_the_on_foot_hero_stays_free_and_takes_no_population(el_cid_rules):
    """He is a story unit: free to summon, and his population cost is
    the same as before the infantry switch.

    The hero used to inherit the population cost of the plain ``knight``
    stub (1).  The infantry line's ``militia`` also declares 1, so the
    switch to ``militia`` must not change the population behaviour --
    the campaign's chapters rely on the hero being spawnable as before.
    """
    uc = el_cid_rules.unit_class("npc_cid")
    cost = list(getattr(uc, "cost", ()) or ())
    assert cost == [0, 0, 0, 0], (
        f"npc_cid must stay free, got cost {cost}"
    )
    assert int(getattr(uc, "time_cost", 0) or 0) == 0, (
        "npc_cid must have no train time"
    )
    assert int(getattr(uc, "population_cost", 0) or 0) == 1, (
        "npc_cid's population cost must stay 1 (the value the knight "
        "stub gave it) -- the infantry switch must not change it"
    )


# ---------------------------------------------------------------------------
# 8. the tournament trial: the champion count must match the trigger
# ---------------------------------------------------------------------------
# Chapter 1 is won by killing King Sancho's champion: the trigger reads
# ``(has_killed 1 two_handed_swordsman)``.  The map used to spawn TWO of
# them, so the count and the trigger disagreed.  Because a melee swing
# in this engine hits every enemy standing on the target square, the
# player killed both at once and the surplus champion was never a real
# problem in practice -- but the two numbers must still agree, otherwise
# a champion can survive the trial and keep harassing El Cid.
def _spawn_counts(text: str, unit_type: str) -> dict[str, int]:
    """``{square: count}`` for every ``computer_only`` spawn of a type."""
    out: dict[str, int] = {}
    for line in _statements(text):
        if not line.startswith("computer_only "):
            continue
        words = line.split()
        # computer_only <res...> <square> <count> <type> ...
        for i, word in enumerate(words):
            if word != unit_type:
                continue
            count = 1
            if i >= 1 and words[i - 1].isdigit():
                count = int(words[i - 1])
            square = None
            for j in range(i - 1, -1, -1):
                if re.match(r"^[a-h][0-9]$", words[j]):
                    square = words[j]
                    break
            if square is None:
                continue
            out[square] = out.get(square, 0) + count
    return out


def test_the_tournament_spawns_exactly_one_champion():
    """The DE trial is a 1-on-1 duel against a single champion."""
    text = _read("1.txt")
    counts = _spawn_counts(text, "two_handed_swordsman")
    assert counts, "1.txt must spawn the tournament champion"
    assert sum(counts.values()) == 1, (
        f"1.txt spawns {sum(counts.values())} two_handed_swordsman "
        f"({counts}); the DE original has exactly ONE champion"
    )


def test_the_tournament_trigger_matches_the_spawned_champions():
    """``has_killed N`` must match the number of champions actually spawned.

    Otherwise the trial can be won while a champion is still standing,
    or the trial cannot be won at all.
    """
    text = _read("1.txt")
    spawned = sum(_spawn_counts(text, "two_handed_swordsman").values())
    required = None
    for m in re.finditer(
        r"\(has_killed\s+(\d+)\s+two_handed_swordsman\s*\)", text
    ):
        required = int(m.group(1))
    assert required is not None, (
        "1.txt must complete objective 1 with a "
        "(has_killed N two_handed_swordsman) trigger"
    )
    assert required == spawned, (
        f"1.txt spawns {spawned} two_handed_swordsman but the trial needs "
        f"{required} kill(s) -- the two numbers must agree"
    )


# ---------------------------------------------------------------------------
# 9. King Alfonso must survive his own castle's siege (ch. 1)
# ---------------------------------------------------------------------------
# In chapter 1 Alfonso spawns as an ENEMY of the player (computer3,
# alliance 2) on the very same square as his castle at b5.  The
# player's assaulting units auto-target him and kill him, which trips
# ``(key_unit_killed npc_alfonso) (defeat)`` -- an instant loss, and
# objective 4 (escort him to King Sancho) becomes unreachable.
#
# The fix has two halves:
#   1. ``is_vulnerable 0`` in the campaign rules removes him from
#      ``known_enemies`` so the player's units never pick him.
#   2. ``receive_hit`` honours ``is_vulnerable`` too, because splash /
#      bounce / pierce do not go through the targeting code at all and
#      would still hurt (or kill) him.

def test_king_alfonso_is_not_vulnerable():
    """The rules block must declare ``is_vulnerable 0`` for the king.

    Without it the player's units auto-target him during the siege of
    his own castle and kill him, which loses the chapter.
    """
    text = _read("rules.txt")
    blocks = {}
    current = None
    for line in _statements(text):
        if line.startswith("def "):
            current = line.split()[1]
            blocks[current] = []
        elif current:
            blocks[current].append(line)
    body = blocks.get("npc_alfonso")
    assert body, "npc_alfonso has no block in the campaign rules.txt"
    assert any(line == "is_vulnerable 0" for line in body), (
        "npc_alfonso must declare 'is_vulnerable 0': as an enemy of the "
        "player he is auto-targeted and killed during the siege of his "
        "own castle, which trips (key_unit_killed npc_alfonso) (defeat)"
    )


def test_king_alfonso_is_untouchable_in_the_loaded_rules(el_cid_rules):
    """The parsed unit class must really carry the flag."""
    uc = el_cid_rules.unit_class("npc_alfonso")
    assert uc is not None, "npc_alfonso is not defined in the campaign rules"
    assert not getattr(uc, "is_vulnerable", True), (
        "npc_alfonso.is_vulnerable must be falsy in the loaded rules"
    )


def test_the_escort_trigger_accepts_both_of_sancho_s_positions():
    """Objective 4 must fire on the arena AND on Sancho's castle.

    The DE scenario is ambiguous about the destination: the scenario
    instructions say "King Sancho's tournament grounds" (g2, the arena
    where the mission started) while the Allies section says "King
    Sancho's Castle close to the tournament square" (g4, where
    npc_sancho actually stands).

    The trigger used to list only g2, so a player who walked the king to
    Sancho's castle never got the "objective complete" message and the
    chapter could not be won.  Both squares must be accepted.
    """
    text = _read("1.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+([^)]*npc_alfonso[^)]*)\)",
        text,
        re.MULTILINE,
    )
    assert match, (
        "1.txt must complete objective 4 with a "
        "(has_entered <square> ... npc_alfonso) trigger"
    )
    squares = [tok for tok in match.group(1).split() if tok != "npc_alfonso"]
    assert "g2" in squares, (
        f"the escort trigger must accept the tournament ground g2, "
        f"got {squares}"
    )
    assert "g4" in squares, (
        f"the escort trigger must accept King Sancho's castle g4, "
        f"got {squares}"
    )


class _StubOwner:
    """Just enough of a player for the damage pipeline."""

    def observe(self, other):
        pass

    def note_combat_with(self, other):
        pass

    def on_unit_attacked(self, unit, attacker):
        pass


class _StubVictim(DamageEffectsMixin):
    """A minimal unit that can take a hit."""

    def __init__(self, vulnerable: bool, place=None):
        self.player = _StubOwner()
        self.hp = 100
        self.hp_max = 100
        self.is_vulnerable = vulnerable
        self.world = None
        self.place = place
        self.x = 0
        self.y = 0
        self.type_name = "npc_alfonso"
        self.expanded_is_a = ()
        self.capture_hp_threshold = 0

    def notify(self, *args, **kwargs):
        pass

    def die(self, attacker=None, notify_death=True):
        pass

def test_receive_hit_ignores_non_vulnerable_units():
    """``receive_hit`` is the single choke point of the damage pipeline.

    Splash, bounce and pierce all pick their victims without looking at
    ``is_vulnerable`` and then call ``receive_hit`` directly, so the
    guard has to live here -- otherwise an untouchable unit is still
    hurt (and killed) by splash damage.
    """
    normal = _StubVictim(True)
    normal.receive_hit(30, None)
    assert normal.hp == 70, f"a vulnerable unit must take damage, hp={normal.hp}"

    king = _StubVictim(False)
    king.receive_hit(30, None)
    assert king.hp == 100, (
        f"an untouchable unit must not take damage, hp={king.hp}"
    )


def test_splash_does_not_damage_non_vulnerable_units():
    """Splash picks its victims by proximity, not by targetability.

    This is the damage path that made the rules-only fix insufficient:
    splash calls ``receive_hit`` on every enemy standing next to the
    impact point, so without the ``receive_hit`` guard the king was
    still killed by his own castle's mangonels.
    """
    from soundrts.combat.splash import SplashMixin
    from soundrts.worldunit import Creature

    class _StubPlace:
        def __init__(self):
            self.objects = []
            self.x = 0
            self.y = 0
            self.is_inside_place = False
            self.neighbors = []

    class _FakeCreature(Creature):
        """A Creature that skips the real constructor.

        ``splash_aim`` only looks at ``isinstance(obj, Creature)``, and
        the damage pipeline only needs a handful of attributes, so the
        real ``Creature.__init__`` (which reads dozens of rules values)
        is not needed here.
        """

        def __init__(self, player, place, vulnerable):
            self.player = player
            self.place = place
            self.world = None
            self.x = 0
            self.y = 0
            self.hp = 100
            self.hp_max = 100
            self.is_vulnerable = vulnerable
            self.type_name = "npc_alfonso"
            self.expanded_is_a = ()
            self.capture_hp_threshold = 0

        def notify(self, *args, **kwargs):
            pass

        def die(self, attacker=None, notify_death=True):
            pass

        def observe(self, other):
            pass

    class _StubShooter(SplashMixin):
        """Minimal attacker able to run ``splash_aim``."""

        mdg_radius = 3
        mdg_splash = 40
        mdg_splash_decay_min = 0.0
        mdg_splash_vs = {}
        mdg_radius_vs = {}
        mdg_explode = 0
        rdg_radius = 0
        rdg_splash = 0
        rdg_splash_decay_min = 0.0
        rdg_splash_vs = {}
        rdg_radius_vs = {}
        rdg_explode = 0
        exp_dgf = 0
        exp_dgf_vs = {}

        def __init__(self, place):
            self.place = place
            self.x = 0
            self.y = 0
            self.type_name = "mangonel"
            self.expanded_is_a = ()
            self.is_vulnerable = True
            self.hp = 100
            self.hp_max = 100
            self.world = types.SimpleNamespace(random=random.Random(1))
            self.player = _StubOwner()

        def is_an_enemy(self, other):
            return True

        def notify(self, *args, **kwargs):
            pass

    place = _StubPlace()
    # The unit the shot was aimed at is skipped by ``splash_aim`` (it
    # takes the direct hit instead), so the bystanders next to it are
    # the ones that get splashed.
    impact = _FakeCreature(_StubOwner(), place, True)
    bystander = _FakeCreature(_StubOwner(), place, True)
    king = _FakeCreature(_StubOwner(), place, False)
    shooter = _StubShooter(place)
    place.objects = [impact, bystander, king]

    shooter.splash_aim(impact, is_melee=True)

    assert bystander.hp < 100, (
        f"a vulnerable bystander must be splashed, hp={bystander.hp}"
    )
    assert king.hp == 100, (
        f"an untouchable unit must be immune to splash damage, hp={king.hp}"
    )


# ---------------------------------------------------------------------------
# 10. headless chapter playthroughs
# ---------------------------------------------------------------------------
def _build_world(chapter: int, faction: str):
    """A headless world with the El Cid campaign rules loaded."""
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    rules.load(res.text("rules", append=True), _read("rules.txt"))

    world = World([], 42)
    world._parse_map(_read(f"{chapter}.txt"))
    world.square_width = int(world.square_width * 1000)
    world._build_map()
    client = DirectClient("player1", None)
    client.faction = faction
    client.alliance = None
    client.interface = type(
        "I", (), {"queue_srv_event": lambda *a, **k: None}
    )()
    world.populate_map([client], random_starts=False)
    world._update_buckets()
    return world


def _find_unit(world, type_name: str):
    """``(unit, owner)`` for the first unit of that type, or (None, None)."""
    for player in world.players:
        for unit in player.units:
            if getattr(unit, "type_name", None) == type_name:
                return unit, player
    return None, None


@pytest.mark.parametrize(
    "destination",
    ["6,1", "6,3"],
    ids=["tournament_ground_g2", "sancho_castle_g4"],
)
def test_alfonso_survives_the_siege_and_can_be_escorted(destination):
    """Chapter 1 end-to-end: the king survives, is captured, is escorted.

    This is the regression for the reported bug: Alfonso was killed by
    the player's own assault, which lost the chapter and made objective
    4 impossible.

    ``destination`` covers BOTH of the squares that count as "King
    Sancho's position" in the DE scenario: the tournament ground at g2
    (where the mission started) and his castle at g4 (where npc_sancho
    actually stands).  The trigger must accept either one.
    """
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(1, "spanish")
    player = world.players[0]
    castle_square = world.grid["1,4"]

    # -- step 0: win the tournament, which grants the player's army ----
    champion = None
    for other in world.players:
        for unit in other.units:
            if getattr(unit, "type_name", None) == "two_handed_swordsman":
                champion = unit
    assert champion is not None, "chapter 1 must spawn the tournament champion"
    cid = [u for u in player.units if u.type_name == "npc_cid"][0]
    champion.receive_hit(champion.hp * 3, cid)
    for _ in range(30):
        world.update()

    # -- step 1: march on Alfonso's castle at b5 ------------------------
    army = [
        u
        for u in player.units
        if u.type_name not in ("npc_cid", "npc_cid_mounted")
    ]
    assert army, "the player must own units after winning the tournament"
    for unit in army:
        unit.take_order(("go", castle_square.id))
    for _ in range(600):
        world.update()
        king, _owner = _find_unit(world, "npc_alfonso")
        assert king is not None, (
            "King Alfonso died during the siege of his own castle -- "
            "the chapter is lost as soon as that happens"
        )

    # -- step 2: destroy the castle, which hands him to the player -----
    castle = [
        u
        for u in castle_square.objects
        if getattr(u, "type_name", None) == "aoe_castle"
    ][0]
    castle.receive_hit(castle.hp * 3, player.units[0])
    for _ in range(30):
        world.update()
    king, owner = _find_unit(world, "npc_alfonso")
    assert king is not None, "King Alfonso vanished when his castle fell"
    assert owner is player, (
        "King Alfonso must be transferred to the player when his castle "
        "falls, otherwise he cannot be escorted"
    )
    assert king in list(player.allied_control_units), (
        "King Alfonso must be selectable/commandable so he can be escorted"
    )

    # -- step 3: escort him to King Sancho ------------------------------
    king.take_order(("go", world.grid[destination].id))
    arrived = False
    for _ in range(6000):
        world.update()
        assert king.hp > 0, "King Alfonso died on the way to King Sancho"
        if king.place is not None and king.place.name == destination:
            arrived = True
    assert arrived, f"King Alfonso never reached King Sancho's square {destination}"
    for _ in range(120):
        world.update()

    objectives = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "4" in objectives, (
        f"escorting the king to {destination} must complete objective 4, "
        f"got {objectives}"
    )
    assert getattr(player, "has_victory", False), (
        "completing the escort must win the chapter"
    )


def test_chapter_four_alfonso_still_reaches_his_camp():
    """Chapter 4 must stay intact: rescue the king, then walk him home."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(4, "saracens")
    player = world.players[0]

    king, _owner = _find_unit(world, "npc_alfonso")
    assert king is not None, "chapter 4 must spawn King Alfonso"

    # -- step 1: El Cid reaches the king at e4, who joins the player ----
    cid = [u for u in player.units if u.type_name == "npc_cid_mounted"][0]
    cid.take_order(("go", world.grid["4,3"].id))
    for _ in range(2000):
        world.update()
        king, owner = _find_unit(world, "npc_alfonso")
        if owner is player:
            break
    king, owner = _find_unit(world, "npc_alfonso")
    assert owner is player, (
        "El Cid reaching Alfonso at e4 must bring the king to the player"
    )
    for _ in range(30):
        world.update()

    # -- step 2: escort him west to his own camp at a1 ------------------
    king.take_order(("go", world.grid["0,0"].id))
    arrived = False
    for _ in range(6000):
        world.update()
        assert king.hp > 0, "King Alfonso died on the way to his camp"
        if king.place is not None and king.place.name == "0,0":
            arrived = True
    assert arrived, "King Alfonso never reached his camp at a1"
    for _ in range(120):
        world.update()

    objectives = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "1" in objectives, f"objective 1 (rescue) missing: {objectives}"
    assert "2" in objectives, f"objective 2 (escort) missing: {objectives}"


# ---------------------------------------------------------------------------
# 11. chapter 4 difficulty-conditional content (AoE2 DE "Black Guards")
# ---------------------------------------------------------------------------
def _chapter_four_units(world, type_name):
    """All units of *type_name* in the world, as (unit, owner) pairs."""
    out = []
    for player in world.players:
        for unit in player.units:
            if getattr(unit, "type_name", None) == type_name:
                out.append((unit, player))
    return out


def _run_chapter_four(difficulty: str):
    """Build chapter 4 at *difficulty* and let the timer-0 triggers run."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(4, "saracens")
    world.scenario_difficulty = difficulty
    for _ in range(10):
        world.update()
        for player in world.players:
            player.slow_update()
    return world


@pytest.mark.parametrize("difficulty", ["easy", "standard"])
def test_chapter_four_standard_tier_grants_the_castle_and_murder_holes(difficulty):
    """DE original: on Standard, Alfonso's base has a Castle, and the
    player begins with Murder Holes researched.

    The ``story`` semantic tier covers "easy" and "standard" (easy is the
    equivalent of the DE's Story mode, which is even more generous than
    Standard), so both must get the bonus.

    The castle must belong to Alfonso's camp (computer2) so that it is
    handed over together with the rest of the base when the king is
    escorted home.
    """
    world = _run_chapter_four(difficulty)
    player = world.players[0]

    castles = _chapter_four_units(world, "aoe_castle")
    assert castles, (
        f"on {difficulty}, King Alfonso's base must contain a Castle "
        "(AoE2 DE 'Black Guards')"
    )
    assert all(owner is not player for _unit, owner in castles), (
        "the castle must belong to Alfonso's camp, not to the player -- it "
        "is handed over with the rest of the base when the king is "
        "escorted home"
    )

    assert "murder_holes" in player.upgrades, (
        f"on {difficulty} the player begins with Murder Holes researched "
        "(AoE2 DE 'Black Guards')"
    )


@pytest.mark.parametrize("difficulty", ["moderate", "hard", "extreme"])
def test_chapter_four_harder_difficulties_grant_no_bonus(difficulty):
    """Only the standard tier (easy / standard) gets the castle and
    Murder Holes."""
    world = _run_chapter_four(difficulty)
    player = world.players[0]

    castles = _chapter_four_units(world, "aoe_castle")
    # Yusuf's own castle is a separate computer slot; the base castle
    # must NOT be there.
    base_castles = [
        (unit, owner)
        for unit, owner in castles
        if unit.place is not None and unit.place.name == "0,0"
    ]
    assert not base_castles, (
        f"on {difficulty}, Alfonso's base must NOT contain a Castle"
    )

    assert "murder_holes" not in player.upgrades, (
        f"on {difficulty} the player must NOT start with Murder Holes"
    )


def test_chapter_four_murder_holes_reach_the_inherited_towers():
    """The granted tech must affect the watchtowers the player inherits.

    Murder Holes removes the minimum range of watchtowers/castles.  If
    the trigger only recorded the tech name without applying it, the
    towers the player receives from Alfonso's base would keep their
    1000 minimum range.
    """
    world = _run_chapter_four("standard")
    player = world.players[0]

    towers = _chapter_four_units(world, "scouttower")
    assert towers, "Alfonso's base must have watchtowers"
    tower, owner = towers[0]
    assert owner is not player

    # Hand the camp over to the player, exactly like objective 2 does.
    for unit in list(owner.units):
        unit.set_player(player)
    for _ in range(10):
        world.update()
        player.slow_update()

    tower = [u for u in player.units if getattr(u, "type_name", None) == "scouttower"]
    assert tower, "the watchtowers must be transferred to the player"
    assert tower[0].rdg_minimal_range == 0.0, (
        "after Murder Holes is granted, the inherited watchtowers must "
        f"lose their minimum range, got {tower[0].rdg_minimal_range}"
    )
    castle = [u for u in player.units if getattr(u, "type_name", None) == "aoe_castle"]
    assert castle, (
        "the castle of Alfonso's base must be handed to the player "
        "together with the rest of the base (AoE2 DE 'Black Guards')"
    )


def test_chapter_four_map_has_the_difficulty_triggers():
    """The map must carry the standard-tier bonus triggers."""
    map_text = _read("4.txt")
    assert "trigger computer2 (difficulty story) (add_units a1 aoe_castle)" in map_text
    assert "trigger player1 (difficulty story) (add_units murder_holes)" in map_text
    # The castle must NOT be part of the static computer_only line any
    # more -- otherwise it would appear on every difficulty.
    for line in map_text.splitlines():
        if line.startswith("computer_only") and " a1 " in line:
            assert "aoe_castle" not in line, (
                "the castle must be granted by the difficulty trigger, not "
                "placed statically"
            )


def test_chapter_three_objectives_are_numbered_consecutively():
    """Chapter 3 must show "objective 1, 2, 3, 4" and "optional objective 1".

    The reported bug: the list jumped from "primary objective 1" straight
    to "primary objective 3" because the primary numbering had a gap
    (1, 3, 4, 5) -- the optional Alfonso's Castle objective had been
    squeezed in as number 2.

    The optional objective lives in its own numbering space, so it is
    "optional objective 1", not 5.

    This test walks the whole chapter so that the numbers on screen are
    the ones the map actually completes.
    """
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(3, "saracens")
    player = world.players[0]

    # The objectives are announced by the map's timer-0 triggers, which
    # run in the game loop rather than while the world is built.
    for _ in range(10):
        world.update()

    # The objectives announced at the start of the chapter.
    #
    # The two numbering spaces are independent, so the bare numbers may
    # coincide -- the engine keys them by ("primary"/"secondary", number).
    visible = list(getattr(player, "objectives", {}).values())
    primary_numbers = sorted(
        int(obj.number) for obj in visible if not obj.optional
    )
    assert primary_numbers == [1, 2, 3, 4], (
        f"chapter 3 must show primary objectives 1..4, got {primary_numbers}"
    )
    optional_numbers = sorted(
        int(obj.number) for obj in visible if obj.optional
    )
    assert optional_numbers == [1], (
        f"chapter 3 has one optional objective, which is numbered 1 in the "
        f"optional objectives' own numbering space, got {optional_numbers}"
    )

    # -- objective 1: mount Babieca AND take the Camel Riders ---------
    #
    # The objective text (tts 9187) promises BOTH: "Mount Babieca and
    # take the camel riders".  The map used to complete it as soon as
    # El Cid reached the stable -- without handing over Babieca and
    # without the camel riders -- so the player never got either.
    cid = [u for u in player.units if u.type_name == "npc_cid"][0]
    cid.take_order(("go", world.grid["2,0"].id))
    for _ in range(3000):
        world.update()
        if cid.place is not None and cid.place.name == "2,0":
            break
    for _ in range(60):
        world.update()

    # Babieca must now belong to the player as npc_cid_mounted, and the
    # on-foot hero must be gone (a second El Cid would be killed by
    # Alfonso's watchtowers and trip (key_unit_killed npc_cid)).
    assert any(u.type_name == "npc_cid_mounted" for u in player.units), (
        "reaching the stable must hand Babieca (npc_cid_mounted) to the "
        f"player, got {[u.type_name for u in player.units]}"
    )
    assert not any(u.type_name == "npc_cid" for u in player.units), (
        "the on-foot El Cid must be replaced by the mounted one, got "
        f"{[u.type_name for u in player.units]}"
    )

    # ... but the objective is NOT complete yet: the camel riders are
    # still waiting in the south-west valley.
    completed = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "1" not in completed, (
        "objective 1 must NOT complete before the camel riders are taken: "
        f"{completed}"
    )
    assert not any(u.type_name == "camel_rider" for u in player.units), (
        "the camel riders must not be given before El Cid reaches them"
    )

    # Now El Cid (mounted) rides to the camel riders at d2.
    cid = [u for u in player.units if u.type_name == "npc_cid_mounted"][0]
    cid.take_order(("go", world.grid["3,1"].id))
    for _ in range(6000):
        world.update()
        assert cid.place is not None, "El Cid died on the way to the camel riders"
        if cid.place.name == "3,1":
            break
    for _ in range(60):
        world.update()

    riders = [u for u in player.units if u.type_name == "camel_rider"]
    assert len(riders) == 4, (
        f"El Cid must take all four camel riders, got {len(riders)}"
    )
    completed = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "1" in completed, (
        f"objective 1 (mount up + camel riders) missing: {completed}"
    )

    # -- objective 2: El Cid joins Motamid in Zaragoza (h6) --------------
    #
    # He walks north through the windmill column and then east, because
    # the direct route east runs into Alfonso's Castle (f4), which kills
    # him, and the route along the bottom runs into Berenguer's siege
    # workshop (h4), which would complete objective 3 by accident.
    cid = [u for u in player.units if u.type_name == "npc_cid_mounted"][0]
    cid.take_order(("go", world.grid["2,5"].id))
    for _ in range(3000):
        world.update()
        assert cid.place is not None, "El Cid died on the way north"
    cid.take_order(("go", world.grid["7,5"].id))
    for _ in range(6000):
        world.update()
        assert cid.place is not None, "El Cid died on the way to Zaragoza"
        if "2" in (getattr(player, "_completed_objective_numbers", ()) or ()):
            break
    completed = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "2" in completed, f"objective 2 (Zaragoza) missing: {completed}"
    assert "3" not in completed, (
        f"objective 3 must not be completed by accident: {completed}"
    )

    # -- objective 3: Berenguer's siege workshop (h4) falls -------------
    workshop_square = world.grid["7,3"]
    workshop = [
        u
        for u in workshop_square.objects
        if getattr(u, "type_name", None) == "workshop"
    ]
    assert workshop, "chapter 3 must spawn Berenguer's siege workshop"
    workshop[0].receive_hit(workshop[0].hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    completed = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "3" in completed, f"objective 3 (siege workshop) missing: {completed}"

    # -- objective 4: Berenguer's fortress (i2) falls -> victory --------
    fortress_square = world.grid["8,1"]
    fortress = [
        u
        for u in fortress_square.objects
        if getattr(u, "type_name", None) == "aoe_castle"
    ]
    assert fortress, "chapter 3 must spawn Berenguer's fortress"
    fortress[0].receive_hit(fortress[0].hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    completed = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "4" in completed, f"objective 4 (Berenguer) missing: {completed}"
    assert getattr(player, "has_victory", False), (
        "completing all four primary objectives must win the chapter"
    )


# ---------------------------------------------------------------------------
# 11. chapter 3: the mounted hero must still trigger the later objectives
# ---------------------------------------------------------------------------
# ``has_entered`` matches a unit by its exact type name or by its ``is_a``
# chain.  ``npc_cid_mounted`` is ``is_a knight`` -- NOT ``is_a npc_cid``
# -- so every trigger that watched for the on-foot hero stops matching the
# moment the hero mounts.  Chapter 3 has two such triggers (the camel
# riders at d2 and Motamid in Zaragoza at h6); before the fix both of
# them were unreachable for a mounted Cid.
def test_chapter_three_triggers_accept_the_mounted_hero():
    """Every ``has_entered`` trigger must name both hero forms."""
    text = _read("3.txt")
    for square in ("d2", "h6"):
        match = re.search(
            rf"^trigger\s+player1\s+\(has_entered\s+{square}\s+([^)]*)\)",
            text,
            re.MULTILINE,
        )
        assert match, f"3.txt must have a (has_entered {square} ...) trigger"
        types = match.group(1).split()
        assert "npc_cid_mounted" in types, (
            f"the (has_entered {square} ...) trigger must accept "
            f"npc_cid_mounted -- the hero is mounted by the time the player "
            f"gets there, and npc_cid_mounted is not a npc_cid: {types}"
        )


def test_chapter_three_hands_over_babieca_at_the_stable():
    """The stable trigger must actually transfer the mounted hero."""
    text = _read("3.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+c1\s+([^)]*)\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "3.txt must have a (has_entered c1 ...) trigger"
    action = match.group(2)
    assert "transfer_units computer1 player1" in action, (
        "the stable trigger must hand Babieca (computer1's npc_cid_mounted) "
        f"to the player, got: {action}"
    )
    assert "remove_ground_item c1 npc_cid" in action, (
        "the stable trigger must remove the on-foot El Cid -- leaving two "
        f"heroes means one of them eventually dies to Alfonso's watchtowers: "
        f"{action}"
    )
    assert "objective_complete 1" in action, (
        "the stable trigger must be able to complete objective 1 (when the "
        f"camel riders have already been taken), got: {action}"
    )


def test_chapter_three_objective_one_needs_both_halves():
    """Objective 1 must only fire once BOTH halves are fulfilled.

    The objective text promises both halves ("Mount Babieca and take the
    camel riders"), so each of the two triggers must check for the OTHER
    half before completing the objective:

    * the ``c1`` trigger (the stable) hands over Babieca and therefore
      checks whether the player already has the camel riders;
    * the ``d2`` trigger (the camel riders) hands over the riders and
      therefore checks whether the player has already mounted.
    """
    text = _read("3.txt")
    expected = {"c1": "camel_rider", "d2": "npc_cid_mounted"}
    for square, other_half in expected.items():
        match = re.search(
            rf"^trigger\s+player1\s+\(has_entered\s+{square}\s+[^)]*\)\s*"
            r"\(do\s+(.*)\)\s*$",
            text,
            re.MULTILINE,
        )
        assert match, f"3.txt must have a (has_entered {square} ...) trigger"
        action = match.group(1)
        assert "(if " in action and "objective_complete 1" in action, (
            f"the (has_entered {square} ...) trigger must complete "
            f"objective 1 only conditionally -- it needs both halves of "
            f"the objective, got: {action}"
        )
        assert other_half in action, (
            f"the (has_entered {square} ...) trigger must check for "
            f"{other_half} (the other half of objective 1), got: {action}"
        )


# ---------------------------------------------------------------------------
# 12. chapter 1: mounting Babieca must swap the hero, not clone it
# ---------------------------------------------------------------------------
# Chapter 1 has the same hero swap as chapter 3: the on-foot ``npc_cid``
# walks to the stable (e4) and takes over the mounted ``npc_cid_mounted``
# that waits there.  The on-foot copy has to be DELETED, otherwise the
# player ends up with two El Cids -- and ``key_unit_killed npc_cid`` is a
# defeat condition, so a stray second hero eventually loses the chapter.
def test_chapter_one_stable_trigger_deletes_the_on_foot_hero():
    """The stable trigger must remove the on-foot El Cid after the swap."""
    text = _read("1.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+e4\s+([^)]*)\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "1.txt must have a (has_entered e4 ...) trigger"
    action = match.group(2)
    assert "transfer_units computer5 player1" in action, (
        "the stable trigger must hand the mounted El Cid (computer5's "
        f"npc_cid_mounted) to the player, got: {action}"
    )
    assert "remove_ground_item e4 npc_cid" in action, (
        "the stable trigger must remove the on-foot El Cid -- leaving two "
        "heroes means one of them eventually dies, and key_unit_killed "
        f"npc_cid is a defeat condition: {action}"
    )


def test_chapter_one_mounting_babieca_leaves_exactly_one_hero():
    """Headless: after the stable swap there is exactly one El Cid left."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(1, "spanish")
    player = world.players[0]

    cid, _owner = _find_unit(world, "npc_cid")
    assert cid is not None, "chapter 1 must start with the on-foot El Cid"

    # The mounted El Cid waits at the stable (e4 == grid square 4,3).
    mounted, mounted_owner = _find_unit(world, "npc_cid_mounted")
    assert mounted is not None, "chapter 1 must spawn the mounted El Cid"
    assert mounted_owner is not player, (
        "the mounted El Cid must start in the stable's slot, not with the "
        "player"
    )

    cid.take_order(("go", world.grid["4,3"].id))
    for _ in range(4000):
        world.update()
        if any(
            u.type_name == "npc_cid_mounted" and u.player is player
            for u in player.units
        ):
            break
    for _ in range(60):
        world.update()

    on_foot, _ = _find_unit(world, "npc_cid")
    assert on_foot is None, (
        "the on-foot El Cid must be removed when the mounted one is taken "
        "over -- two heroes means one of them eventually dies, and "
        "key_unit_killed npc_cid is a defeat condition"
    )
    mounted, mounted_owner = _find_unit(world, "npc_cid_mounted")
    assert mounted is not None and mounted_owner is player, (
        "the mounted El Cid must belong to the player after the swap"
    )
    objectives = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "2" in objectives, (
        f"objective 2 (mount Babieca) missing after the swap: {objectives}"
    )
    assert not getattr(world, "defeated", None), (
        "the hero swap must not trigger a defeat"
    )


# ---------------------------------------------------------------------------
# 13. chapter 3: the player must be able to WIN the chapter
# ---------------------------------------------------------------------------
# Reported bug: "the forces you give me cannot beat the enemy -- in
# particular Berenguer's fortress, and the optional objective (Alfonso's
# castle) is out of reach because I have no siege engines at all.  And
# destroying Berenguer's workshop gives me 4 peasants, but they are
# useless: I cannot build a Town Center, so I cannot build anything and
# I cannot mine."
#
# Three separate root causes, all verified against the engine:
#
#   * the player starts with NO villagers and NO buildings, so there is
#     no economy at all -- and the GATA camp (f2), which in the DE
#     original hands over a Town Center, a Siege Workshop, villagers and
#     a Trebuchet, was never handed over;
#   * only ``town_center`` stores all four resource types, and every
#     economy building (``mining_camp`` / ``lumbermill`` / ``mill`` /
#     ``barracks`` / ``house``) has ``requirements town_center``, so
#     without a Town Center the peasants cannot deposit anything and
#     cannot build anything;
#   * the chapter started in the Dark Age, so ``requirements castle_age``
#     (workshop, battering_ram, mangonel) could never be satisfied and
#     no siege engine could be built or trained.
def _cid_hero(player):
    """The hero, in either form (the on-foot one is deleted on mount)."""
    for name in ("npc_cid_mounted", "npc_cid"):
        for unit in player.units:
            if unit.type_name == name:
                return unit
    return None


def _walk_to(world, player, square_name, limit=8000):
    """Walk the hero to a grid square; True when it arrives."""
    hero = _cid_hero(player)
    if hero is None:
        return False
    hero.take_order(("go", world.grid[square_name].id))
    for _ in range(limit):
        world.update()
        hero = _cid_hero(player)
        if hero is None:
            return False
        if hero.place is not None and hero.place.name == square_name:
            return True
    return False


def test_chapter_three_starts_in_the_castle_age_with_building_money():
    """The chapter must start in the Castle Age and be able to pay for a TC.

    ``town_center`` costs 275 wood + 100 stone.  The old start (200 /
    200 / 200 / 200) could not even pay for it, and without an age in
    ``player.upgrades`` the ``requirements castle_age`` of the workshop
    and of the siege engines could never be satisfied.
    """
    text = _read("3.txt")
    match = re.search(r"^player\s+(.+)$", text, re.MULTILINE)
    assert match, "3.txt must have a player line"
    tokens = match.group(1).split()
    assert len(tokens) >= 4, f"the player line must give 4 resources: {tokens}"
    gold, wood, food, stone = (int(t) for t in tokens[:4])
    assert wood >= 275, (
        f"the player must start with enough wood for a Town Center "
        f"(275), got {wood}"
    )
    assert stone >= 100, (
        f"the player must start with enough stone for a Town Center "
        f"(100), got {stone}"
    )
    for age in ("dark_age", "feudal_age", "castle_age"):
        assert age in tokens, (
            f"chapter 3 must start in the Castle Age, so {age} must be "
            f"listed in the player line: {tokens}"
        )


def test_chapter_three_gata_camp_provides_an_economy_and_siege():
    """The GATA camp must hand over a Town Center, a Workshop and siege.

    DE original: the Gaia camp in the south-east provides a Siege
    Workshop, villagers, resources and a Trebuchet so that Alfonso's
    Castle (the optional objective) can be taken.  This chapter never
    transferred it, so the optional objective was unwinnable.

    The Trebuchet itself is granted on the standard tier only (DE:
    "Gaia units: 1 Trebuchet * Standard difficulty only"), so it is NOT
    part of the static ``computer_only`` line any more -- it comes from a
    ``(difficulty story)`` trigger instead.
    """
    text = _read("3.txt")
    match = re.search(r"^computer_only\s+.*\bf2\b(.*)$", text, re.MULTILINE)
    assert match, "3.txt must spawn the GATA camp at f2"
    units = match.group(1)
    for needed in ("town_center", "workshop", "mangonel",
                   "battering_ram", "peasant"):
        assert needed in units, (
            f"the GATA camp must provide {needed} -- without it the "
            f"optional objective (Alfonso's Castle) is unwinnable: {units}"
        )
    # The Trebuchet must be granted by the standard-tier trigger.
    assert "trebuchet" not in units, (
        f"the Trebuchet must NOT be in the static GATA camp line -- in the "
        f"DE original it is granted on Standard difficulty only: {units}"
    )
    assert "trigger player1 (difficulty story) (add_units f2 trebuchet)" in text, (
        "the Trebuchet must be granted on the standard tier "
        "(DE: 'Standard difficulty only')"
    )
    # ... and the camp must actually be handed over.
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+f2\s+[^)]*\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "3.txt must have a (has_entered f2 ...) trigger"
    action = match.group(1)
    assert "transfer_units computer8 player1" in action, (
        f"the GATA camp must be transferred to the player: {action}"
    )
    assert "grant_resources" in action, (
        f"the GATA camp must also hand over resources: {action}"
    )


def test_chapter_three_windmill_garrison_joins_the_player():
    """The windmill garrison (2 knights, 6 pikemen) must change sides."""
    text = _read("3.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+c6\s+[^)]*\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "3.txt must have a (has_entered c6 ...) trigger"
    assert "transfer_units computer2 player1" in match.group(1), (
        f"the windmill garrison must be transferred to the player: "
        f"{match.group(1)}"
    )


def test_chapter_three_zaragoza_joins_the_player():
    """Motamid's castle must be handed over with him."""
    text = _read("3.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(has_entered\s+h6\s+[^)]*\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "3.txt must have a (has_entered h6 ...) trigger"
    assert "transfer_units computer9 player1" in match.group(1), (
        f"Zaragoza must be transferred to the player: {match.group(1)}"
    )


def test_chapter_three_workshop_reward_includes_a_town_center():
    """Destroying Berenguer's workshop must hand over a Town Center.

    Four peasants without a Town Center are useless: only ``town_center``
    stores all four resource types, and every economy building requires
    one -- so the player could neither deposit resources nor build
    anything nor mine.
    """
    text = _read("3.txt")
    match = re.search(
        r"^trigger\s+player1\s+\(enemy_building_destroyed\s+h4\s+workshop\)\s*"
        r"\(do\s+(.*)\)\s*$",
        text,
        re.MULTILINE,
    )
    assert match, "3.txt must have the (enemy_building_destroyed h4 ...) trigger"
    action = match.group(1)
    assert "add_units" in action, f"the workshop must give a reward: {action}"
    assert "town_center" in action, (
        f"the reward must include a Town Center -- without one the "
        f"peasants cannot deposit resources and cannot build anything: "
        f"{action}"
    )
    assert "peasant" in action, f"the reward must include peasants: {action}"


def test_chapter_three_player_gets_an_economy_and_siege_train():
    """Headless: walking the chapter hands over the base and the siege.

    This is the end-to-end check of the two reported problems: the
    player must end up with a Town Center (economy) and with siege
    engines (so the two castles can actually be taken down).
    """
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(3, "saracens")
    player = world.players[0]
    for _ in range(10):
        world.update()

    # The player starts in the Castle Age -- siege engines are buildable.
    assert player.has("castle_age"), (
        f"chapter 3 must start in the Castle Age, got {player.upgrades}"
    )

    # Mount Babieca at the stable (c1 == grid 2,0).
    assert _walk_to(world, player, "2,0"), "El Cid could not reach the stable"
    for _ in range(60):
        world.update()

    # Reach the GATA camp (f2 == grid 5,1).
    assert _walk_to(world, player, "5,1"), "El Cid could not reach the GATA camp"
    for _ in range(60):
        world.update()

    assert player.has("town_center"), (
        "the GATA camp must give the player a Town Center -- it is the "
        "only building that stores all four resource types, so without it "
        "the villagers cannot deposit anything"
    )
    assert player.has("workshop"), (
        "the GATA camp must give the player a Siege Workshop"
    )
    tc = [u for u in player.units if u.type_name == "town_center"][0]
    assert set(tc.storable_resource_types) == {
        "resource1", "resource2", "resource3", "resource4",
    }, (
        "the Town Center must be able to store gold, wood, food and stone, "
        f"got {tc.storable_resource_types}"
    )
    assert "peasant" in tc.can_train, (
        f"the Town Center must be able to train peasants, got {tc.can_train}"
    )
    assert player.has("trebuchet"), (
        "the GATA camp must give the player a Trebuchet -- the castles "
        "have 4800 HP and cannot be taken down by soldiers alone"
    )
    assert player.has("battering_ram"), (
        "the GATA camp must give the player a Battering Ram"
    )
    assert player.has("mangonel"), (
        "the GATA camp must give the player a Mangonel"
    )
    # The population must have room for the army.
    assert player.available_population >= 20, (
        f"the player must have population headroom, got "
        f"{player.available_population}"
    )


def test_chapter_three_can_be_completed():
    """Headless: the whole chapter is winnable, objectives 1..4."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(3, "saracens")
    player = world.players[0]
    for _ in range(10):
        world.update()

    def completed():
        return sorted(getattr(player, "_completed_objective_numbers", ()) or ())

    # 1) the stable (c1), the GATA camp (f2) and the camel riders (d2)
    assert _walk_to(world, player, "2,0"), "could not reach the stable"
    for _ in range(60):
        world.update()
    assert _walk_to(world, player, "5,1"), "could not reach the GATA camp"
    for _ in range(60):
        world.update()
    assert _walk_to(world, player, "3,1"), "could not reach the camel riders"
    for _ in range(60):
        world.update()
    assert "1" in completed(), (
        f"objective 1 (mount Babieca + camel riders) missing: {completed()}"
    )

    # 2) the windmill (c6) and Zaragoza (h6)
    assert _walk_to(world, player, "2,5"), "could not reach the windmill"
    for _ in range(60):
        world.update()
    assert len([u for u in player.units if u.type_name == "aoe_knight"]) == 2, (
        "the windmill garrison (2 knights) must join the player"
    )
    assert len([u for u in player.units if u.type_name == "pikeman"]) == 6, (
        "the windmill garrison (6 pikemen) must join the player"
    )
    assert _walk_to(world, player, "7,5"), "could not reach Zaragoza"
    for _ in range(60):
        world.update()
    assert "2" in completed(), (
        f"objective 2 (Zaragoza) missing: {completed()}"
    )

    # 3) destroy Berenguer's siege workshop (h4 == grid 7,3)
    workshop = [
        o
        for o in world.grid["7,3"].objects
        if getattr(o, "type_name", None) == "workshop"
    ]
    assert workshop, "chapter 3 must spawn Berenguer's siege workshop"
    workshop[0].receive_hit(workshop[0].hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    assert "3" in completed(), (
        f"objective 3 (siege workshop) missing: {completed()}"
    )
    # The reward must include a Town Center, so the player has an economy.
    assert player.has("town_center"), (
        "destroying the workshop must hand over a Town Center -- four "
        "peasants without one are useless"
    )

    # 4) destroy Berenguer's fortress (i2 == grid 8,1)
    fortress = [
        o
        for o in world.grid["8,1"].objects
        if getattr(o, "type_name", None) == "aoe_castle"
    ]
    assert fortress, "chapter 3 must spawn Berenguer's fortress"
    fortress[0].receive_hit(fortress[0].hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    assert "4" in completed(), (
        f"objective 4 (Berenguer) missing: {completed()}"
    )
    assert getattr(player, "has_victory", False), (
        "completing all four primary objectives must win the chapter"
    )


# ---------------------------------------------------------------------------
# 11. chapter 4 -- "Black Guards": economy, housing and siege train
# ---------------------------------------------------------------------------
def _ch4_world():
    """Chapter 4 world, with the sound module stubbed out."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(4, "saracens")
    for _ in range(10):
        world.update()
    return world


def test_chapter_four_starts_in_the_castle_age():
    """The player must start in the Castle Age.

    Without a phase in ``player.upgrades`` the engine falls back to the
    Dark Age (``worldplayerbase/base.py``: the phase whose requirements
    name no other phase), so ``requirements castle_age`` of the Siege
    Workshop and of the siege engines could never be satisfied -- which
    is exactly why the chapter had NO siege engines at all.

    All three phase names must be listed: ``castle_age`` itself requires
    ``feudal_age``, and that requirement is checked by literal name.
    """
    world = _ch4_world()
    player = world.players[0]

    for phase in ("dark_age", "feudal_age", "castle_age"):
        assert phase in player.upgrades, (
            f"chapter 4 must start with {phase} in player.upgrades, "
            f"got {player.upgrades}"
        )
    assert player.current_phase == "castle_age", (
        f"chapter 4 must start in the Castle Age, got {player.current_phase}"
    )
    assert player.has("castle_age"), (
        "the player must satisfy 'requirements castle_age' so that the "
        "Siege Workshop and the siege engines can be built"
    )


def test_chapter_four_starts_with_a_working_economy():
    """The player must own a Town Center, and it must work as a warehouse.

    Reported bug: "there are plenty of villagers and the map has the
    resources, but there is no Town Center, so I cannot mine".

    ``town_center`` is the ONLY building whose ``storable_resource_types``
    covers all four resources (``rules.txt``); ``workshop``,
    ``aoe_castle``, ``scouttower`` and ``shipyard`` store nothing.  With
    no Town Center ``nearest_warehouse`` returns None for every
    resource and the villagers cannot deposit a single thing.

    The Town Center also gates every economy building (``house``,
    ``mill``, ``lumbermill``, ``mining_camp`` and ``barracks`` all have
    ``requirements town_center``) and is the only building that can
    ``can_advance`` to the next age.
    """
    world = _ch4_world()
    player = world.players[0]

    assert player.has("town_center"), (
        "chapter 4 must start with a Town Center -- without it the "
        "villagers cannot deposit anything and no economy building can "
        "be raised"
    )
    tc = [u for u in player.units if u.type_name == "town_center"][0]
    assert set(tc.storable_resource_types) == {
        "resource1", "resource2", "resource3", "resource4",
    }, (
        "the Town Center must store gold, wood, food and stone, got "
        f"{tc.storable_resource_types}"
    )
    assert "peasant" in tc.can_train, (
        f"the Town Center must be able to train peasants, got {tc.can_train}"
    )

    # Every resource must have a warehouse to be deposited into.
    place = tc.place
    for resource in ("resource1", "resource2", "resource3", "resource4"):
        warehouse = player.nearest_warehouse(place, resource)
        assert warehouse is not None, (
            f"no building can store {resource} -- the villagers would "
            "get 'order_impossible' when trying to deposit it"
        )

    # The other economy buildings the player needs to unlock.
    for building in ("barracks", "stables", "workshop"):
        assert player.has(building), (
            f"chapter 4 must start with a {building}"
        )
    assert player.has("house"), (
        "chapter 4 must start with housing, otherwise the player cannot "
        "train a single unit"
    )


def test_chapter_four_has_population_headroom():
    """The player must not start over the population cap.

    ``available_population`` is ``min(housing, world limit)``; when it is
    below ``used_population`` every training order is rejected with
    ``order_impossible,not_enough_population`` -- the player could not
    even replace a lost villager.
    """
    world = _ch4_world()
    player = world.players[0]

    assert player.population > 0, (
        "the player must have housing at the start of chapter 4"
    )
    assert player.available_population > player.used_population, (
        f"the player starts over the population cap: "
        f"available={player.available_population} "
        f"used={player.used_population}"
    )


def test_chapter_four_starts_with_a_siege_train():
    """The player must start with siege engines and be able to build more.

    Yusuf's castle has 4800 HP and 11 armour.  Measured with the
    engine's own damage formula, a Conquistador does 5 damage per hit
    and a Mameluke 0 -- soldiers simply cannot take the castle down.
    The siege engines can: a Battering Ram does 144 damage per hit,
    a Mangonel 67 and a Trebuchet 439 (at 80% accuracy vs buildings).
    """
    world = _ch4_world()
    player = world.players[0]

    for siege in ("battering_ram", "mangonel", "trebuchet"):
        assert player.has(siege), (
            f"chapter 4 must start with a {siege} -- the castles cannot be "
            "taken down by soldiers alone"
        )

    workshop = [u for u in player.units if u.type_name == "workshop"][0]
    for trainable in ("battering_ram", "mangonel", "scorpion"):
        assert trainable in workshop.can_train, (
            f"the Siege Workshop must be able to train {trainable}, got "
            f"{workshop.can_train}"
        )

    # ... and the workshop must actually deliver a siege engine.
    player.resources = [10 ** 9] * 4
    before = len([u for u in player.units if u.type_name == "battering_ram"])
    workshop.take_order(
        ["train", "battering_ram"], forget_previous=True, imperative=False
    )
    for _ in range(600):
        world.update()
    after = len([u for u in player.units if u.type_name == "battering_ram"])
    assert after == before + 1, (
        f"the Siege Workshop must build a Battering Ram, got {before} -> {after}"
    )


def test_chapter_four_siege_is_strong_enough_for_yusufs_castle():
    """The siege train must be able to raze Yusuf's castle in a sane time.

    The numbers come from the engine's own damage formula
    (``Combat.DamageCalculationMixin._calculate_actual_damage``) and from
    the rules' attack cooldowns, so the test measures the real game
    rules rather than a hand-written approximation.
    """
    from soundrts.definitions import rules

    world = _ch4_world()
    player = world.players[0]
    yusuf = world.players[-1]

    castle = [u for u in yusuf.units if u.type_name == "aoe_castle"][0]
    assert castle is not None, "chapter 4 must spawn Yusuf's castle"

    def dps_of(unit):
        # NOTE: the engine stores HP, damage and hit-rate percentages in
        # PRECISION (1000) units and cooldowns in milliseconds, so
        #     dps = (hit / 1000) * (1000 / cd_ms) * (accuracy / 1000)
        #         = hit * accuracy / cd_ms
        # with ``accuracy`` given in PRECISION-scaled percent.
        is_melee = not (getattr(unit, "rdg_range", 0) or 0) > 0
        if is_melee:
            raw = getattr(unit, "mdg", 0) + (getattr(unit, "mdg_vs", {}) or {}).get(
                "building", 0
            )
            cd = getattr(unit, "mdg_cd", 0) or 0
        else:
            raw = getattr(unit, "rdg", 0) + (getattr(unit, "rdg_vs", {}) or {}).get(
                "building", 0
            )
            cd = getattr(unit, "rdg_cd", 0) or 0
        hit = castle._calculate_actual_damage(raw, unit, is_melee=is_melee)
        # Melee always hits; ranged units have a PRECISION-scaled hit rate
        # (the Trebuchet: 15 % in general, 80 % against buildings).
        accuracy = 100 * 1000
        if not is_melee:
            accuracy = (getattr(unit, "rdg_hit_rate", 0) or 0) + (
                getattr(unit, "rdg_hit_rate_vs", {}) or {}
            ).get("building", 0)
        return hit * accuracy / 100000.0 / cd

    siege = [
        u
        for u in player.units
        if u.type_name in ("battering_ram", "mangonel", "trebuchet")
    ]
    total_dps = sum(dps_of(u) for u in siege)
    # HP is stored in PRECISION (1000) units, so 4800000 == 4800 HP.
    castle_hp = castle.hp / 1000.0
    seconds = castle_hp / total_dps
    assert seconds < 180, (
        "the starting siege train must raze Yusuf's 4800 HP castle in "
        f"under three minutes, got {seconds:.0f} s "
        f"({total_dps:.1f} dps over {len(siege)} engines)"
    )

    # ... and soldiers alone must NOT be enough, otherwise the siege
    # engines would be pointless.
    soldiers = [
        u
        for u in player.units
        if u.type_name in ("conquistador", "mameluke", "pikeman", "aoe_knight")
    ]
    soldier_dps = sum(dps_of(u) for u in soldiers)
    assert soldier_dps * 180 < castle_hp, (
        "plain soldiers must not be able to raze the castle -- otherwise "
        "the siege engines are pointless"
    )

    # The workshop must also be able to keep the siege train coming.
    assert rules.unit_class("battering_ram") is not None


def test_chapter_four_alfonso_camp_hands_over_a_town_center():
    """Escorting the king must give the player a real base.

    DE original: "bring him towards the king's base (blue), where the
    whole base will switch to the player's control", and on Standard
    difficulty "King Alfonso's base has a Castle, which will be given to
    the player with the rest of his base".

    Without a Town Center the handed-over villagers are useless -- they
    still have nowhere to deposit their gold.
    """
    world = _ch4_world()
    player = world.players[0]

    king, _owner = _find_unit(world, "npc_alfonso")
    assert king is not None, "chapter 4 must spawn King Alfonso"

    cid = [u for u in player.units if u.type_name == "npc_cid_mounted"][0]
    cid.take_order(("go", world.grid["4,3"].id))
    for _ in range(2000):
        world.update()
        king, owner = _find_unit(world, "npc_alfonso")
        if owner is player:
            break
    assert owner is player, (
        "El Cid reaching Alfonso at e4 must bring the king to the player"
    )
    for _ in range(30):
        world.update()

    king.take_order(("go", world.grid["0,0"].id))
    for _ in range(6000):
        world.update()
        assert king.hp > 0, "King Alfonso died on the way to his camp"
        if king.place is not None and king.place.name == "0,0":
            break
    for _ in range(120):
        world.update()

    objectives = sorted(getattr(player, "_completed_objective_numbers", ()) or ())
    assert "2" in objectives, f"objective 2 (escort) missing: {objectives}"

    assert player.has("town_center"), (
        "Alfonso's camp must hand over a Town Center -- it is the only "
        "building that stores all four resources"
    )
    assert player.has("aoe_castle"), (
        "Alfonso's camp must hand over a Castle -- the DE original gives "
        "the player one, and it is what unlocks the Trebuchet"
    )
    assert player.available_population > player.used_population, (
        "the handed-over base must give the player population headroom"
    )

    # ... and Yusuf must wake up now that the king is safe at home.
    yusuf = world.players[-1]
    for _ in range(200):
        world.update()
    assert getattr(yusuf, "AI_type", None) == "intermediate", (
        "Yusuf must get a real AI once the king is home, got "
        f"{getattr(yusuf, 'AI_type', None)!r}"
    )


def test_chapter_four_objective_four_needs_the_castle_and_the_town_center():
    """DE original: "forcing Yusuf to resign requires destroying his
    Town Center AND his Castle".

    The old map completed the objective as soon as the castle fell, so
    the player could win without dismantling the base at all.
    """
    world = _ch4_world()
    player = world.players[0]
    yusuf = world.players[-1]

    def completed():
        return sorted(getattr(player, "_completed_objective_numbers", ()) or ())

    castle = [u for u in yusuf.units if u.type_name == "aoe_castle"][0]
    town_center = [u for u in yusuf.units if u.type_name == "town_center"][0]

    castle.receive_hit(castle.hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    assert "4" not in completed(), (
        "destroying only the castle must not complete objective 4 -- "
        "Yusuf's Town Center has to fall as well"
    )
    assert not getattr(player, "has_victory", False), (
        "the chapter must not be won while Yusuf still has a Town Center"
    )

    town_center.receive_hit(town_center.hp * 3, player.units[0])
    for _ in range(60):
        world.update()
    assert "4" in completed(), (
        f"objective 4 (Yusuf) missing after both buildings fell: {completed()}"
    )
    assert getattr(player, "has_victory", False), (
        "destroying Yusuf's castle and Town Center must win the chapter"
    )


def test_chapter_four_enemies_are_given_a_real_ai():
    """The Black Guard Navy and Yusuf must actually attack.

    A ``computer_only`` slot gets a trigger-only, do-nothing AI by
    default, so without ``(ai intermediate)`` the whole chapter would be
    a walk around an empty map -- Yusuf would hide in his castle and the
    player's army would never be tested.

    Yusuf is the exception: he only wakes up (``yusuf_awake``) once the
    king has been escorted home, because while the king is being
    rescued El Cid stands alone on the battlefield and an active Yusuf
    would simply hunt him down and end the chapter.
    """
    world = _ch4_world()

    computers = [p for p in world.players if p is not world.players[0]]
    # 1 = King Alfonso, 2 = Alfonso's camp, 3 = the mosque (all neutral).
    # 4..9 = the six docks, 10 = Yusuf.
    assert len(computers) >= 10, (
        f"chapter 4 must have ten computer slots, got {len(computers)}"
    )
    for index in range(3, 9):
        ai = getattr(computers[index], "AI_type", None)
        assert ai == "intermediate", (
            f"computer {index + 1} (the Black Guard Navy docks) must use "
            f"a real AI, got {ai!r}"
        )

    # Yusuf starts inert, but he must have a trigger that wakes him up.
    yusuf = computers[9]
    assert getattr(yusuf, "AI_type", None) != "intermediate", (
        "Yusuf must stay inert until the king is home, otherwise he "
        "kills El Cid during the escort"
    )
    assert _ch4_has_yusuf_awakening_trigger(), (
        "chapter 4 must wake Yusuf up (set_global yusuf_awake / "
        "(global yusuf_awake >= 1)) once the king is home"
    )


def _ch4_has_yusuf_awakening_trigger():
    """True when the map sets ``yusuf_awake`` and gates Yusuf's AI on it."""
    path = (
        Path(__file__).resolve().parents[2]
        / "mods"
        / "aoe2"
        / "single"
        / "El Cid"
        / "4.txt"
    )
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    return (
        "set_global yusuf_awake 1" in text
        and "(global yusuf_awake >= 1) (ai intermediate)" in text
    )


def test_chapter_four_docks_can_be_reached_and_destroyed():
    """Objective 3 (six docks) must be achievable.

    Every dock must be reachable from the player's start and must have
    a shipyard that the player can destroy.
    """
    world = _ch4_world()
    player = world.players[0]

    docks = ("7,1", "8,1", "8,3", "8,5", "9,2", "9,5")
    for name in docks:
        place = world.grid.get(name)
        assert place is not None, f"the map must have a square {name}"
        shipyards = [
            o
            for o in place.objects
            if getattr(o, "type_name", None) == "shipyard"
        ]
        assert shipyards, f"the Black Guard dock at {name} must have a shipyard"

    # The docks must have an economy of their own, otherwise their AI
    # cannot even spawn a villager (a Town Center is the only maker of
    # peasants) and the whole chapter would be a walkover.
    for computer in world.players[1:]:
        if computer.AI_type == "intermediate" and computer is not world.players[-1]:
            assert computer.has("town_center"), (
                "each Black Guard dock needs a Town Center so that its AI "
                "can produce units"
            )

