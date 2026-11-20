# -*- coding: utf-8 -*-
"""三个 AoE2 战役共 19 章的难度差异断言（1.5.2.3）。

本测试逐章检查《帝国时代 2 决定版》原版的难度差异是否真的在地图脚本里
落地：

  * El Cid 6 章（mods/aoe2/single/El Cid/1-6.txt）
  * Joan of Arc 6 章（mods/aoe2/single/Joan of Arc/1-6.txt）
  * William Wallace 7 章（mods/aoe2/single/William Wallace/1-7.txt）

难度共 5 档：easy / standard / moderate / hard / extreme。
其中 ``story`` 是**语义档**，覆盖 easy + standard（决定版的「标准档礼物」
两档都发，easy 相当于决定版的 Story mode，比标准更宽松）。

每个章节都做两件事：

  1. **静态检查** —— 地图脚本里必须出现对应的难度触发器写法；
  2. **行为检查** —— 真正把章节载入引擎、按不同难度跑一遍触发器，
     检查方格上的单位/建筑确实随难度变化。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

EL_CID = ROOT / "mods" / "aoe2" / "single" / "El Cid"
JOAN = ROOT / "mods" / "aoe2" / "single" / "Joan of Arc"
WALLACE = ROOT / "mods" / "aoe2" / "single" / "William Wallace"

ALL_TIERS = ("easy", "standard", "moderate", "hard", "extreme")
STORY_TIERS = ("easy", "standard")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _statements(text: str) -> list[str]:
    """Map text with comments stripped, one statement per line."""
    out = []
    for raw in text.splitlines():
        line = raw.split(";", 1)[0].strip()
        if line:
            out.append(line)
    return out


def _read(folder: Path, name: str) -> str:
    return (folder / name).read_text(encoding="utf-8")


def _col_index(token: str) -> int:
    """``a`` -> 1, ``b`` -> 2, ... (1-based column)."""
    idx = 0
    for ch in token.lower():
        idx = idx * 26 + (ord(ch) - ord("a") + 1)
    return idx


def _square_key(token: str) -> str:
    """``c4`` -> ``"2,3"`` (the grid keys used by ``world.grid``)."""
    m = re.match(r"^([a-z]+)([0-9]+)$", token)
    if not m:
        raise AssertionError(f"not a square token: {token!r}")
    return f"{_col_index(m.group(1)) - 1},{int(m.group(2)) - 1}"


def _build_world(folder: Path, chapter: str, difficulty: str, time_ms: int = 0):
    """Load a campaign chapter into a headless world at *difficulty*."""
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    rules.load(
        res.text("rules", append=True),
        _read(folder, "rules.txt"),
    )

    world = World([], 42)
    world.scenario_difficulty = difficulty
    world._parse_map(_read(folder, chapter))
    world.square_width = int(world.square_width * 1000)
    world._build_map()
    client = DirectClient("player1", None)
    client.faction = "franks"
    client.alliance = None
    client.interface = type(
        "I", (), {"queue_srv_event": lambda *a, **k: None}
    )()
    world.populate_map([client], random_starts=False)
    world._update_buckets()
    world.time = time_ms
    return world


def _run(folder: Path, chapter: str, difficulty: str, time_ms: int = 0):
    """Build the chapter and let every trigger fire once."""
    from soundrts.lib import sound

    sound.pause_music = lambda *a, **k: None
    world = _build_world(folder, chapter, difficulty, time_ms)
    for player in world.players:
        try:
            player.run_triggers()
        except Exception:  # pragma: no cover - surfaces map bugs
            raise
    return world


def _types_on(world, square: str) -> list[str]:
    """Type names of every object standing on *square*."""
    place = world.grid.get(_square_key(square))
    if place is None:
        return []
    return [getattr(o, "type_name", "") for o in place.objects]


def _count(world, square: str, type_name: str) -> int:
    return _types_on(world, square).count(type_name)


def _count_all(world, type_name: str) -> int:
    total = 0
    for player in world.players:
        for unit in player.units:
            if getattr(unit, "type_name", None) == type_name:
                total += 1
    return total


# ---------------------------------------------------------------------------
# 1. the engine side: the story tier and the remove_unit action
# ---------------------------------------------------------------------------
def test_the_story_semantic_tier_covers_easy_and_standard():
    from soundrts.coop_difficulty import STORY_TIERS, is_story_tier

    assert STORY_TIERS == ("easy", "standard")
    for tier in STORY_TIERS:
        assert is_story_tier(tier) is True
    for tier in ("moderate", "hard", "extreme"):
        assert is_story_tier(tier) is False


def test_remove_unit_is_a_real_trigger_action():
    from soundrts.worldplayerbase.triggers import TriggersMixin

    assert hasattr(TriggersMixin, "lang_remove_unit"), (
        "the (remove_unit <square> <type> [count]) trigger action must exist"
    )
    src = Path(TriggersMixin.lang_remove_unit.__code__.co_filename)
    text = src.read_text(encoding="utf-8")
    assert "o.delete()" in text, (
        "remove_unit must actually delete the object (o.delete()), not "
        "just drop it from a list"
    )


def test_no_campaign_map_uses_an_unknown_difficulty_level():
    """Every ``(difficulty <level>)`` must name a real level or ``story``."""
    known = set(ALL_TIERS) | {"story"}
    for folder in (EL_CID, JOAN, WALLACE):
        for path in sorted(folder.glob("[1-7].txt")):
            for line in _statements(path.read_text(encoding="utf-8")):
                for m in re.finditer(r"\(difficulty([^)]*)\)", line):
                    args = m.group(1).split()
                    if not args:
                        continue
                    if args[0] in (">=", "<=", ">", "<", "==", "=", "!="):
                        assert len(args) == 2, (path.name, m.group(0))
                        level = args[1]
                    else:
                        level = args[0]
                    assert level in known, (
                        f"{path.parent.name}/{path.name}: unknown difficulty "
                        f"level {level!r}"
                    )


# ---------------------------------------------------------------------------
# 2. El Cid -- 6 chapters
# ---------------------------------------------------------------------------
def test_el_cid_chapter_one_gives_murder_holes_on_the_story_tier():
    text = _read(EL_CID, "1.txt")
    assert "trigger player1 (difficulty story) (add_units murder_holes)" in text


def test_el_cid_chapter_three_gives_a_trebuchet_on_the_story_tier():
    text = _read(EL_CID, "3.txt")
    assert "trigger player1 (difficulty story) (add_units f2 trebuchet)" in text


def test_el_cid_chapter_four_grants_the_castle_and_murder_holes():
    text = _read(EL_CID, "4.txt")
    assert "trigger computer2 (difficulty story) (add_units a1 aoe_castle)" in text
    assert "trigger player1 (difficulty story) (add_units murder_holes)" in text


def test_el_cid_chapter_six_has_one_fleet_trigger_per_tier():
    text = _read(EL_CID, "6.txt")
    # The story tier covers easy + standard, so the baseline fleet is
    # granted with (difficulty story); moderate, hard and extreme each
    # have their own trigger.
    for tier in ("story", "moderate", "hard", "extreme"):
        assert f"(difficulty {tier})" in text, tier
    # The DE fleet tiers: standard / moderate / hard.
    assert "war_galley" in text and "fire_ship" in text
    assert "siege_ram" in text and "capped_ram" in text
    assert "battering_ram" in text


@pytest.mark.parametrize("tier", STORY_TIERS)
def test_el_cid_chapter_six_story_tier_gets_the_standard_fleet(tier):
    world = _run(EL_CID, "6.txt", tier)
    player = world.players[0]
    assert player.has("war_galley"), tier
    assert player.has("fast_fire_ship"), tier


@pytest.mark.parametrize("tier", ("moderate",))
def test_el_cid_chapter_six_moderate_tier_gets_the_moderate_fleet(tier):
    world = _run(EL_CID, "6.txt", tier)
    player = world.players[0]
    assert player.has("war_galley"), tier
    assert player.has("fire_ship"), tier
    assert player.has("capped_ram"), tier


@pytest.mark.parametrize("tier", ("hard", "extreme"))
def test_el_cid_chapter_six_hard_tiers_get_the_hard_fleet(tier):
    world = _run(EL_CID, "6.txt", tier)
    player = world.players[0]
    assert player.has("battering_ram"), tier


# ---------------------------------------------------------------------------
# 3. Joan of Arc -- 6 chapters
# ---------------------------------------------------------------------------
def test_joan_chapter_one_removes_the_guard_towers_on_the_story_tier():
    """DE "An Unlikely Messiah": on Standard there are no Guard Towers."""
    text = _read(JOAN, "1.txt")
    assert "trigger computer1 (difficulty story) (remove_unit c2 scouttower)" in text
    assert "trigger computer3 (difficulty story) (remove_unit e3 scouttower)" in text


@pytest.mark.parametrize("tier", STORY_TIERS)
def test_joan_chapter_one_story_tier_has_no_guard_towers(tier):
    world = _run(JOAN, "1.txt", tier)
    assert _count(world, "c2", "scouttower") == 0, tier
    assert _count(world, "e3", "scouttower") == 0, tier


@pytest.mark.parametrize("tier", ("moderate", "hard", "extreme"))
def test_joan_chapter_one_harder_tiers_keep_the_guard_towers(tier):
    world = _run(JOAN, "1.txt", tier)
    assert _count(world, "c2", "scouttower") == 1, tier
    assert _count(world, "e3", "scouttower") == 1, tier


def test_joan_chapter_two_grants_murder_holes_from_hard_upwards():
    """DE "The Maid of Orleans": Murder Holes from the hard tier up."""
    text = _read(JOAN, "2.txt")
    assert text.count("(difficulty >= hard)") >= 1
    assert "(difficulty hard)" not in text, (
        "the hard tier must be written as (difficulty >= hard) so that the "
        "extreme tier is covered too"
    )


def test_joan_chapter_three_scales_the_scorpion_and_the_rams():
    text = _read(JOAN, "3.txt")
    assert "trigger computer1 (difficulty story) (remove_unit a1 scorpion)" in text
    assert "trigger computer2 (difficulty story) (remove_unit f5 scorpion)" in text
    assert "trigger computer1 (difficulty moderate) (add_units a1 1 capped_ram)" in text
    assert "trigger computer2 (difficulty moderate) (add_units f5 1 capped_ram)" in text
    assert "(difficulty >= hard)" in text


@pytest.mark.parametrize("tier", STORY_TIERS)
def test_joan_chapter_three_story_tier_has_no_scorpion_and_no_ram(tier):
    world = _run(JOAN, "3.txt", tier)
    assert _count(world, "a1", "scorpion") == 0, tier
    assert _count(world, "f5", "scorpion") == 0, tier
    assert _count(world, "a1", "capped_ram") == 0, tier
    assert _count(world, "f5", "capped_ram") == 0, tier


def test_joan_chapter_three_moderate_tier_gets_one_capped_ram():
    world = _run(JOAN, "3.txt", "moderate")
    assert _count(world, "a1", "scorpion") == 1
    assert _count(world, "a1", "capped_ram") == 1
    assert _count(world, "a1", "battering_ram") == 0


@pytest.mark.parametrize("tier", ("hard", "extreme"))
def test_joan_chapter_three_hard_tiers_get_the_extra_ram(tier):
    world = _run(JOAN, "3.txt", tier)
    assert _count(world, "a1", "capped_ram") == 1, tier
    assert _count(world, "a1", "battering_ram") == 1, tier
    assert _count(world, "f5", "battering_ram") == 1, tier


def test_joan_chapter_four_has_no_difficulty_difference():
    """DE "The Rising": the official difference list says nothing."""
    text = _read(JOAN, "4.txt")
    assert "(difficulty " not in text, (
        "chapter 4 has no difficulty differences in the DE original -- "
        "it must not branch on the difficulty"
    )


def test_joan_chapter_five_strips_and_fortifies_the_fortresses():
    text = _read(JOAN, "5.txt")
    assert "trigger computer2 (difficulty story) (remove_unit d3 onager)" in text
    assert "trigger computer2 (difficulty story) (remove_unit d3 trebuchet)" in text
    assert "trigger computer3 (difficulty story) (remove_unit f5 onager)" in text
    assert "trigger computer2 (difficulty >= hard) (add_units d3 1 keep" in text
    assert "cannontower" in text
    assert "monk" in text


@pytest.mark.parametrize("tier", STORY_TIERS)
def test_joan_chapter_five_story_tier_has_no_siege_engines(tier):
    world = _run(JOAN, "5.txt", tier)
    assert _count(world, "d3", "onager") == 0, tier
    assert _count(world, "d3", "trebuchet") == 0, tier
    assert _count(world, "f5", "onager") == 0, tier


@pytest.mark.parametrize("tier", ("moderate",))
def test_joan_chapter_five_moderate_tier_keeps_the_siege_engines(tier):
    world = _run(JOAN, "5.txt", tier)
    assert _count(world, "d3", "onager") == 1, tier
    assert _count(world, "d3", "trebuchet") == 1, tier


@pytest.mark.parametrize("tier", ("hard", "extreme"))
def test_joan_chapter_five_hard_tiers_fortify_the_fortress(tier):
    world = _run(JOAN, "5.txt", tier)
    assert _count(world, "d3", "keep") == 1, tier
    assert _count(world, "d3", "cannontower") == 1, tier
    assert _count(world, "d3", "monk") == 2, tier
    # The ambush is twice as large.
    assert _count(world, "f5", "militia") >= 10, tier


def test_joan_chapter_six_scales_the_artillery_and_the_siege():
    text = _read(JOAN, "6.txt")
    assert "(add_units e6 2 trebuchet 6 bombard_cannon)" in text
    assert "(add_units e6 1 trebuchet 3 bombard_cannon)" in text
    assert "trigger computer1 (difficulty >= hard) (add_units c2 3 bombard_cannon" in text
    assert "guardtower" in text
    assert "trigger computer1 (and (difficulty >= hard) (timer 30))" in text


@pytest.mark.parametrize("tier", STORY_TIERS + ("moderate",))
def test_joan_chapter_six_baseline_tiers_get_the_full_artillery(tier):
    world = _run(JOAN, "6.txt", tier)
    assert _count(world, "e6", "trebuchet") == 2, tier
    assert _count(world, "e6", "bombard_cannon") == 6, tier


@pytest.mark.parametrize("tier", ("hard", "extreme"))
def test_joan_chapter_six_hard_tiers_get_the_reduced_artillery(tier):
    world = _run(JOAN, "6.txt", tier)
    assert _count(world, "e6", "trebuchet") == 1, tier
    assert _count(world, "e6", "bombard_cannon") == 3, tier
    assert _count(world, "c2", "bombard_cannon") == 3, tier
    assert _count(world, "c2", "guardtower") == 1, tier


def test_joan_chapter_six_extra_town_center_comes_after_fifteen_minutes():
    """The English build a second Town Center after 15 minutes on hard."""
    before = _run(JOAN, "6.txt", "hard")
    assert _count(before, "c2", "town_center") == 1

    after = _run(JOAN, "6.txt", "hard", time_ms=30 * 30 * 1000)
    assert _count(after, "c2", "town_center") == 2


def test_joan_chapter_six_extra_town_center_is_never_built_on_easy():
    after = _run(JOAN, "6.txt", "easy", time_ms=30 * 30 * 1000)
    assert _count(after, "c2", "town_center") == 1


# ---------------------------------------------------------------------------
# 4. William Wallace -- 7 chapters
# ---------------------------------------------------------------------------
def test_william_wallace_chapter_four_upgrades_the_raid_from_moderate_up():
    """DE "Research and Technology": above Standard the militia become
    Men-at-Arms."""
    text = _read(WALLACE, "4.txt")
    assert "trigger computer1 (difficulty >= moderate) (remove_unit c3 militia" in text
    assert "trigger computer1 (difficulty >= moderate) (add_units c3 3 man_at_arms)" in text


@pytest.mark.parametrize("tier", STORY_TIERS)
def test_william_wallace_chapter_four_story_tier_keeps_the_militia(tier):
    world = _run(WALLACE, "4.txt", tier)
    assert _count(world, "c3", "militia") == 3, tier
    assert _count(world, "c3", "man_at_arms") == 0, tier


@pytest.mark.parametrize("tier", ("moderate", "hard", "extreme"))
def test_william_wallace_chapter_four_harder_tiers_get_the_men_at_arms(tier):
    world = _run(WALLACE, "4.txt", tier)
    assert _count(world, "c3", "militia") == 0, tier
    assert _count(world, "c3", "man_at_arms") == 3, tier


@pytest.mark.parametrize("chapter", ["1.txt", "2.txt", "3.txt", "5.txt", "6.txt", "7.txt"])
def test_the_other_william_wallace_chapters_have_no_difficulty_difference(chapter):
    """DE lists no difficulty differences for the other six chapters."""
    text = _read(WALLACE, chapter)
    assert "(difficulty " not in text, (
        f"William Wallace {chapter} has no difficulty differences in the "
        "DE original -- it must not branch on the difficulty"
    )


# ---------------------------------------------------------------------------
# 5. every chapter of the three campaigns still parses
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "folder,chapters",
    [
        (EL_CID, [f"{n}.txt" for n in range(1, 7)]),
        (JOAN, [f"{n}.txt" for n in range(1, 7)]),
        (WALLACE, [f"{n}.txt" for n in range(1, 8)]),
    ],
    ids=["el-cid", "joan-of-arc", "william-wallace"],
)
def test_every_chapter_loads_on_every_difficulty(folder, chapters):
    """All 19 chapters must load on all 5 difficulty levels."""
    for chapter in chapters:
        for tier in ALL_TIERS:
            world = _run(folder, chapter, tier)
            assert world.players, (folder.name, chapter, tier)
