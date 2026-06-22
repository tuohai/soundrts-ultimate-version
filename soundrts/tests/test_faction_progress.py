"""Per-faction achievement progress tests."""

from __future__ import annotations

import json

import pytest

from soundrts import achievements as ach
from soundrts import cards as card_mod
from soundrts import titles as title_mod
from soundrts.faction_progress import (
    achievements_per_faction_enabled,
    definition_matches_faction,
    normalize_faction_key,
)


@pytest.fixture
def per_faction_rules(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.rules.get",
        lambda obj, attr, default=None: (
            1 if obj == "parameters" and attr == "achievements_per_faction" else default
        ),
    )


@pytest.fixture
def faction_save(tmp_path, monkeypatch, per_faction_rules):
    base = tmp_path / "achievements" / "testmod"
    base.mkdir(parents=True)

    def _path(faction=None):
        if faction is None:
            return str(tmp_path / "achievements" / "testmod.json")
        key = normalize_faction_key(faction) or "_default"
        return str(base / f"{key}.json")

    monkeypatch.setattr(ach, "current_mod_key", lambda: "testmod")
    monkeypatch.setattr(ach, "achievements_save_path", _path)
    return base


def test_normalize_faction_key():
    assert normalize_faction_key("traditionnel") == "traditionnel"
    assert normalize_faction_key("random_faction") is None


def test_definition_matches_faction_only_when_enabled(per_faction_rules):
    assert definition_matches_faction("traditionnel", "traditionnel") is True
    assert definition_matches_faction("traditionnel", "orc") is False
    assert definition_matches_faction(None, "orc", scope="faction") is False
    assert definition_matches_faction(None, "orc", scope=None) is True


def test_definition_matches_faction_ignored_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.rules.get",
        lambda obj, attr, default=None: default,
    )
    assert definition_matches_faction("traditionnel", "orc") is True


def test_per_faction_save_paths(faction_save, monkeypatch):
    monkeypatch.setattr(ach, "achievements_per_faction_enabled", lambda: True)
    assert ach.achievements_save_path("traditionnel").endswith("traditionnel.json")
    assert ach.achievements_save_path("orc").endswith("orc.json")


def test_per_faction_separate_unlock_state(faction_save, monkeypatch):
    monkeypatch.setattr(ach, "achievements_per_faction_enabled", lambda: True)
    trad = ach._empty_unlock_state()
    trad["medals"] = 10
    ach.save_unlock_state(trad, "traditionnel")

    orc = ach._empty_unlock_state()
    orc["medals"] = 25
    ach.save_unlock_state(orc, "orc")

    assert ach.load_unlock_state("traditionnel")["medals"] == 10
    assert ach.load_unlock_state("orc")["medals"] == 25


def test_faction_scoped_achievements(faction_save, per_faction_rules):
    ach.load_achievements("""
        def trad_grade_s
        faction traditionnel
        title 5300
        condition grade S
        once

        def orc_grade_s
        faction orc
        title 5301
        condition grade S
        once
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="m1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    trad_state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, trad_state, "traditionnel")
    assert [d.id for d in newly] == ["trad_grade_s"]

    orc_state = ach._empty_unlock_state()
    newly_orc, _ = ach.evaluate_new_unlocks(ctx, orc_state, "orc")
    assert [d.id for d in newly_orc] == ["orc_grade_s"]


def test_faction_scoped_rank_ladder(per_faction_rules):
    title_mod.load_titles("""
        def rank_trad_recruit
        faction traditionnel
        kind rank
        title 5400
        medals 0
        loadout_slots 0

        def rank_trad_lieutenant
        faction traditionnel
        kind rank
        title 5404
        medals 100
        loadout_slots 2

        def rank_orc_recruit
        faction orc
        kind rank
        title 5500
        medals 0
        loadout_slots 0
    """)
    assert title_mod.get_current_rank(150, "traditionnel").id == "rank_trad_lieutenant"
    assert title_mod.get_current_rank(150, "orc").id == "rank_orc_recruit"
    assert title_mod.get_loadout_slots(150, "traditionnel") == 2
    assert title_mod.get_loadout_slots(150, "orc") == 0


def test_faction_scoped_card_order(per_faction_rules):
    card_mod.load_cards("""
        def card_trad_infantry
        faction traditionnel
        title 5322
        spawn arbaletrier 2

        def card_orc_infantry
        faction orc
        title 5323
        spawn troll_cogneur 2

        def card_gold
        title 5320
        resource resource1 50
    """)
    trad_cards = card_mod.get_card_order("traditionnel")
    assert "card_trad_infantry" in trad_cards
    assert "card_orc_infantry" not in trad_cards
    assert "card_gold" in trad_cards


def test_race_keyword_alias_for_faction(faction_save, per_faction_rules):
    ach.load_achievements("""
        def trad_grade_s
        race traditionnel
        title 5300
        condition grade S
        once
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="m1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    trad_state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, trad_state, "traditionnel")
    assert [d.id for d in newly] == ["trad_grade_s"]
    assert ach.get_achievement_defs()["trad_grade_s"].faction == "traditionnel"

    title_mod.load_titles("""
        def rank_trad_recruit
        race traditionnel
        kind rank
        title 5400
        medals 0
        loadout_slots 0
    """)
    assert title_mod.get_current_rank(0, "traditionnel").id == "rank_trad_recruit"

    card_mod.load_cards("""
        def card_trad_infantry
        race traditionnel
        title 5322
        spawn arbaletrier 2
    """)
    assert "card_trad_infantry" in card_mod.get_card_order("traditionnel")
    assert card_mod.get_card("card_trad_infantry").faction == "traditionnel"


def test_achievements_per_faction_enabled_reads_rules(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.rules.get",
        lambda obj, attr, default=None: 1 if attr == "achievements_per_faction" else default,
    )
    assert achievements_per_faction_enabled() is True
