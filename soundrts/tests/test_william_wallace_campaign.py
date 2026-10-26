"""Smoke tests for the William Wallace campaign.

Verifies:
1. All 8 chapters (0–7) load from the AoE2 mod.
2. Intro cutscene (0.txt) has correct title and sequence.
3. Each mission chapter has progressive objectives (register + add).
4. Each mission chapter has alliance triggers.
5. Each mission chapter has at least one victory and one defeat trigger.
6. Chapter 6 (relic mission) places relics on the map.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_all_8_chapters_load():
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    ww = [c for c in res.campaigns() if c.name == "William Wallace"][0]
    numbers = [ch.number for ch in ww.chapters]
    assert numbers == [0, 1, 2, 3, 4, 5, 6, 7], f"Expected 0-7, got {numbers}"


def test_chapter0_is_intro_cutscene():
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    ww = [c for c in res.campaigns() if c.name == "William Wallace"][0]
    ch0 = ww.chapter(0)
    assert type(ch0).__name__ == "CutSceneChapter", f"ch0 must be CutSceneChapter, got {type(ch0).__name__}"
    assert ch0.title == [8600]
    assert 8601 in ch0.sequence, f"intro sequence must contain 8601, got {ch0.sequence}"
    assert 8710 in ch0.sequence, f"intro sequence must contain 8710, got {ch0.sequence}"


def test_chapter0_title_is_campaign_title():
    """0.txt title must be the campaign title (8600), matching campaign.txt."""
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    ww = [c for c in res.campaigns() if c.name == "William Wallace"][0]
    title_val = ww.title[0]
    # The parser may return int or str for the title; accept either
    assert str(title_val) == "8600", f"campaign.txt title must be 8600, got {ww.title}"


def _chapters_have_trigger(text: str, trigger: str) -> bool:
    """Return True if any trigger line in text contains the given string."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("trigger ") and trigger in stripped:
            return True
    return False


def test_each_chapter_has_register_objective():
    """Each mission chapter must use register_objective (progressive reveal)."""
    base = Path("mods/aoe2/single/William Wallace")
    for n in range(1, 8):
        text = (base / f"{n}.txt").read_text(encoding="utf-8")
        assert _chapters_have_trigger(text, "register_objective"), (
            f"ch{n} must have a register_objective trigger"
        )


def test_each_chapter_has_alliance_triggers():
    """Each mission chapter with enemies must set up alliances (alliance 1 / alliance 2).

    Solo tutorial chapters (ch2 resource, ch3 training) have no enemies
    and don't need alliance triggers.
    """
    base = Path("mods/aoe2/single/William Wallace")
    # Chapters with enemies: 1 (optional raid), 4 (raid), 5, 6, 7
    solo_chapters = {2, 3}  # no enemy players
    for n in range(1, 8):
        text = (base / f"{n}.txt").read_text(encoding="utf-8")
        if n in solo_chapters:
            continue  # skip solo tutorials
        assert _chapters_have_trigger(text, "(alliance 1)"), (
            f"ch{n} must set alliance 1 (player team)"
        )


def test_each_chapter_has_victory_trigger():
    """Each mission chapter must have at least one victory trigger."""
    base = Path("mods/aoe2/single/William Wallace")
    for n in range(1, 8):
        text = (base / f"{n}.txt").read_text(encoding="utf-8")
        assert _chapters_have_trigger(text, "victory"), (
            f"ch{n} must have a victory trigger"
        )


def test_each_chapter_has_defeat_trigger():
    """Each mission chapter must have at least one defeat trigger."""
    base = Path("mods/aoe2/single/William Wallace")
    for n in range(1, 8):
        text = (base / f"{n}.txt").read_text(encoding="utf-8")
        assert _chapters_have_trigger(text, "defeat"), (
            f"ch{n} must have a defeat trigger"
        )


def test_chapter6_places_relics_on_map():
    """Ch6 (Forge an Alliance) must place relics via the relic directive."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "6.txt").read_text(encoding="utf-8")
    assert "relic" in text, "ch6 must use the relic directive to place relics on the map"


def test_chapter6_has_relic_objective():
    """Ch6 must use has_brought_item to check for 3 relics at monastery."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "6.txt").read_text(encoding="utf-8")
    assert _chapters_have_trigger(text, "has_brought_item"), (
        "ch6 must use has_brought_item to detect relic delivery"
    )
    assert _chapters_have_trigger(text, "relic"), (
        "ch6 objective must reference the relic item type"
    )


def test_chapter7_has_secondary_objective():
    """Ch7 (Falkirk) must have two objectives: build castle + destroy enemy castle."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "7.txt").read_text(encoding="utf-8")
    # register_objective with 2 IDs
    assert "register_objective 1 2" in text, "ch7 must register 2 objectives"
    # no_enemy_left victory (secondary objective)
    assert _chapters_have_trigger(text, "no_enemy_left"), (
        "ch7 must use no_enemy_left for secondary victory condition"
    )


def test_chapter1_movement_tutorial():
    """Ch1 (Marching) must use has_entered for movement-based victory."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "1.txt").read_text(encoding="utf-8")
    assert _chapters_have_trigger(text, "has_entered"), (
        "ch1 must use has_entered for the movement tutorial"
    )


def test_chapter2_resource_objective():
    """Ch2 (Feeding) must use has_resources for resource gathering victory."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "2.txt").read_text(encoding="utf-8")
    assert _chapters_have_trigger(text, "has_resources"), (
        "ch2 must use has_resources for resource gathering victory"
    )


def test_chapter5_enemy_building_destroyed():
    """Ch5 (Stirling) must use enemy_building_destroyed for tower objective."""
    base = Path("mods/aoe2/single/William Wallace")
    text = (base / "5.txt").read_text(encoding="utf-8")
    assert _chapters_have_trigger(text, "enemy_building_destroyed"), (
        "ch5 must use enemy_building_destroyed to check the English watch tower"
    )


def test_campaign_tts_has_intro_cutscene_text():
    """English TTS must contain the intro cutscene text IDs."""
    tts = Path("mods/aoe2/single/William Wallace/ui/tts.txt").read_text(encoding="utf-8")
    assert "8710" in tts, "English TTS must contain intro cutscene text 8710"
    assert "8711" in tts, "English TTS must contain intro cutscene text 8711"


def test_campaign_tts_has_chapter_titles():
    """English TTS must contain all 7 mission titles."""
    tts = Path("mods/aoe2/single/William Wallace/ui/tts.txt").read_text(encoding="utf-8")
    for n in range(2, 9):
        assert f"86{n:02d}" in tts, f"English TTS must contain title 86{n:02d}"


def test_chinese_tts_has_intro_cutscene_text():
    """Chinese TTS must contain the intro cutscene text."""
    tts = Path("mods/aoe2/single/William Wallace/ui-zh/tts.txt").read_text(encoding="utf-8")
    assert "8710" in tts, "Chinese TTS must contain intro cutscene text 8710"
    assert "8711" in tts, "Chinese TTS must contain intro cutscene text 8711"


def test_chapter0_and_campaign_intro_consistent():
    """0.txt sequence must include the intro cutscene text IDs."""
    from soundrts.lib.resource import res

    res.set_mods("aoe2")
    ww = [c for c in res.campaigns() if c.name == "William Wallace"][0]
    assert ww.chapters[0].number == 0, "ch0 should be the first chapter"
    ch0 = ww.chapter(0)
    # campaign.txt: intro 8602 8710 8711  → play before ch0
    # 0.txt: sequence 8601 8710             → play after intro (adds campaign title + first cutscene)
    assert 8601 in ch0.sequence, "ch0 must play 8601 (campaign title)"
    assert 8710 in ch0.sequence, "ch0 must play 8710 (intro cutscene part 1)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
