"""Cross-faction meta achievement progress (_meta.json)."""

from __future__ import annotations

import pytest

from soundrts import achievements as ach
from soundrts import titles as title_mod
from soundrts.faction_progress import definition_matches_faction
from soundrts.meta_progress import (
    count_factions_unlocked_at_least,
    load_meta_state,
    meta_save_path,
    save_meta_state,
)


@pytest.fixture
def per_faction_rules(monkeypatch):
    monkeypatch.setattr(
        "soundrts.faction_progress.rules.get",
        lambda obj, attr, default=None: (
            1 if obj == "parameters" and attr == "achievements_per_faction" else default
        ),
    )
    monkeypatch.setattr(
        "soundrts.meta_progress.achievements_per_faction_enabled",
        lambda: True,
    )


@pytest.fixture
def meta_env(tmp_path, monkeypatch, per_faction_rules):
    base = tmp_path / "achievements" / "testmod"
    base.mkdir(parents=True)

    def _faction_path(faction=None):
        if faction is None:
            return str(tmp_path / "achievements" / "testmod.json")
        return str(base / f"{faction}.json")

    def _meta_path():
        return str(base / "_meta.json")

    monkeypatch.setattr(ach, "current_mod_key", lambda: "testmod")
    monkeypatch.setattr(ach, "achievements_save_path", _faction_path)
    monkeypatch.setattr("soundrts.meta_progress.CONFIG_DIR_PATH", str(tmp_path))
    monkeypatch.setattr("soundrts.meta_progress.current_mod_key", lambda: "testmod")
    monkeypatch.setattr("soundrts.meta_progress.meta_save_path", _meta_path)
    return base


def _load_defs():
    ach.load_achievements(
        """
        def trad_grade_s
        faction traditionnel
        title 5300
        condition grade S
        once

        def meta_three_branches
        scope meta
        title 79950
        condition factions_unlocked_at_least 3 1
        once
        reward title honor_meta_novice

        def meta_five_sergeant
        scope meta
        title 79951
        condition factions_medals_at_least 5 150
        once
        reward title honor_meta_commander
        """
    )
    title_mod.load_titles(
        """
        def honor_meta_novice
        kind honor
        title 79860

        def honor_meta_commander
        kind honor
        title 79861
        """
    )


def test_definition_without_faction_not_matched_in_per_faction_mode(per_faction_rules):
    assert definition_matches_faction(None, "orc", scope="faction") is False


def test_meta_achievement_skipped_in_faction_evaluate(meta_env):
    _load_defs()
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=0,
        survival=0,
        building_defense=0,
        map_name="",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    for faction in ("traditionnel", "orc", "technique"):
        state = ach._empty_unlock_state()
        state["unlocked"]["trad_grade_s"] = {"count": 1}
        ach.save_unlock_state(state, faction)
    newly, _ = ach.evaluate_new_unlocks(ctx, ach._empty_unlock_state(), "traditionnel")
    assert [d.id for d in newly] == ["trad_grade_s"]


def test_meta_unlocks_after_faction_progress(meta_env):
    _load_defs()
    for faction in ("traditionnel", "orc", "technique"):
        state = ach._empty_unlock_state()
        state["unlocked"]["dummy"] = {"count": 1}
        ach.save_unlock_state(state, faction)
    newly, honors, state, changed = ach.evaluate_meta_unlocks()
    assert changed is True
    assert [d.id for d in newly] == ["meta_three_branches"]
    assert "honor_meta_novice" in honors
    assert "meta_three_branches" in state["unlocked"]


def test_meta_medals_condition(meta_env):
    _load_defs()
    factions = ("traditionnel", "orc", "technique", "robotique", "tenebre")
    for faction in factions:
        state = ach._empty_unlock_state()
        state["medals"] = 150
        ach.save_unlock_state(state, faction)
    newly, honors, _, changed = ach.evaluate_meta_unlocks()
    assert changed is True
    assert [d.id for d in newly] == ["meta_five_sergeant"]
    assert "honor_meta_commander" in honors


def test_meta_save_persists(meta_env):
    _load_defs()
    state = load_meta_state()
    state["unlocked"]["meta_three_branches"] = {"count": 1}
    save_meta_state(state)
    loaded = load_meta_state()
    assert "meta_three_branches" in loaded["unlocked"]
    assert meta_save_path().endswith("_meta.json")


def test_count_factions_unlocked_at_least():
    snapshots = {
        "a": {"unlocked": {"x": {}}},
        "b": {"unlocked": {"x": {}, "y": {}}},
        "c": {"unlocked": {}},
    }
    assert count_factions_unlocked_at_least(snapshots, 1) == 2
    assert count_factions_unlocked_at_least(snapshots, 2) == 1


def test_process_game_end_triggers_meta(meta_env, monkeypatch):
    _load_defs()
    for faction in ("traditionnel", "orc", "technique"):
        state = ach._empty_unlock_state()
        state["unlocked"]["dummy"] = {"count": 1}
        ach.save_unlock_state(state, faction)

    class Stats:
        def score_breakdown(self):
            return {
                "total": 0,
                "utilization_percent": 0,
                "survival": 0,
                "building_defense": 0,
                "ai_defeat_entries": [],
            }

        def score_grade_letter(self, _total):
            return "C"

    player = type(
        "P",
        (),
        {
            "faction": "traditionnel",
            "has_victory": True,
            "is_spectator": False,
            "stats": Stats(),
        },
    )()
    game = type("G", (), {"map": type("M", (), {"name": "pra1"})()})()
    monkeypatch.setattr(ach, "achievements_enabled", lambda: True)
    msgs = ach.process_game_end_achievements(game, player)
    assert any(79950 in line for line in msgs)
    meta = load_meta_state()
    assert "meta_three_branches" in meta["unlocked"]
