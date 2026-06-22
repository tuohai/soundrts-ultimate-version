"""Achievement system phase 1 tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from soundrts import msgparts as mp
from soundrts import achievements as ach
from soundrts import achievements_menu as ach_menu
from soundrts import cards as card_mod
from soundrts import titles as title_mod


@pytest.fixture
def isolated_achievements(monkeypatch, tmp_path):
    monkeypatch.setattr(ach, "_achievements", {})
    monkeypatch.setattr(ach, "_achievements_order", [])
    save = tmp_path / "ach.json"
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(save))
    return save


def _load_sample():
    ach.load_achievements("""
        def grade_s
        title 5300
        condition grade S
        once_per map_ai

        def frugal
        title 5304
        condition victory
        condition utilization_below 30
        once_per map
    """)


def test_load_achievements_parses_conditions(isolated_achievements):
    _load_sample()
    assert "grade_s" in ach.get_achievement_defs()
    defn = ach.get_achievement_defs()["grade_s"]
    assert defn.title == [5300]
    assert defn.conditions == [("grade", "S")]
    assert defn.once_mode == "map_ai"


def test_grade_s_unlock_once_per_map_ai(isolated_achievements):
    _load_sample()
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="jl1",
        defeated_ai_types=["beginner"],
        primary_enemy_ai="beginner",
    )
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["grade_s"]
    assert state["once_keys"]["grade_s|map:jl1|ai:beginner"] is True

    newly2, _ = ach.evaluate_new_unlocks(ctx, state)
    assert newly2 == []


def test_repeat_medal_on_recompletion(isolated_achievements):
    card_mod.load_cards("""
        def card_mixed_army
        title 5332
        grant_charges 1
    """)
    ach.load_achievements("""
        def grade_s
        title 5300
        condition grade S
        once_per map_ai
        reward medal 40
        repeat_medal 8
        reward card card_mixed_army
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="jl1",
        defeated_ai_types=["beginner"],
        primary_enemy_ai="beginner",
    )
    state = ach._empty_unlock_state()
    ach.evaluate_new_unlocks(ctx, state)
    assert state["medals"] == 40
    assert state["cards"]["card_mixed_army"]["charges"] == 1

    repeats = ach.evaluate_repeat_completions(ctx, state)
    assert [d.id for d in repeats] == ["grade_s"]
    added = ach.apply_repeat_medals(repeats, state)
    assert added == 8
    assert state["medals"] == 48
    assert "cards" not in state or state["cards"]["card_mixed_army"]["charges"] == 1

    msgs = ach.repeat_medal_msgs(repeats)
    assert mp.REPEAT_ACHIEVEMENT[0] in msgs[0]
    assert 1000008 in msgs[0]


def test_repeat_medal_zero_means_no_repeat_reward(isolated_achievements):
    ach.load_achievements("""
        def grade_c
        title 5303
        condition grade C
        once_per map
        reward medal 8
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="C",
        utilization_percent=50,
        survival=50,
        building_defense=50,
        map_name="jl1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    state = ach._empty_unlock_state()
    ach.evaluate_new_unlocks(ctx, state)
    assert ach.evaluate_repeat_completions(ctx, state) == []


def test_frugal_victory_requires_low_utilization(isolated_achievements):
    _load_sample()
    ctx = ach.AchievementContext(
        victory=True,
        grade="A",
        utilization_percent=10,
        survival=80,
        building_defense=90,
        map_name="m1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["frugal"]

    ctx_high = ach.AchievementContext(
        victory=True,
        grade="A",
        utilization_percent=80,
        survival=80,
        building_defense=90,
        map_name="m1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    newly, _ = ach.evaluate_new_unlocks(ctx_high, state)
    assert newly == []


def test_process_game_end_persists_save(isolated_achievements):
    _load_sample()
    player = SimpleNamespace(
        has_victory=True,
        is_spectator=False,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 750,
                "utilization_percent": 5,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [{"ai_type": "beginner", "count": 1, "points": 10}],
            },
            score_grade_letter=lambda total=None: "S",
        ),
    )
    game = SimpleNamespace(map=SimpleNamespace(name="testmap"))
    msgs = ach.process_game_end_achievements(game, player)
    assert msgs
    assert mp.ACHIEVEMENT_UNLOCKED[0] in msgs[0]
    data = json.loads(isolated_achievements.read_text(encoding="utf-8"))
    assert "grade_s" in data["unlocked"]


def test_spectator_skipped(isolated_achievements):
    _load_sample()
    player = SimpleNamespace(is_spectator=True, stats=None)
    assert ach.process_game_end_achievements(SimpleNamespace(), player) == []


def test_defeated_ai_accepts_legacy_easy_alias(isolated_achievements):
    ach.load_achievements("""
        def beat_beginner
        title 5308
        condition defeated_ai beginner easy
        once
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="B",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="m1",
        defeated_ai_types=["easy"],
        primary_enemy_ai="easy",
    )
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["beat_beginner"]


def test_build_achievement_menu_entries(isolated_achievements):
    _load_sample()
    entries = ach_menu.build_achievement_menu_entries()
    assert len(entries) == 2
    assert entries[0][1] is False
    assert entries[0][2]
    assert entries[1][1] is False
    assert entries[1][2]


def test_defeated_ai_total_at_least_unlocks_on_nth_win(isolated_achievements):
    ach.load_achievements("""
        def win_beginner_3
        title 5308
        condition victory
        condition defeated_ai beginner
        condition defeated_ai_total_at_least 3 beginner
        once
        reward medal 10
    """)
    state = ach._empty_unlock_state()
    for _ in range(2):
        ctx = ach.AchievementContext(
            victory=True,
            grade="C",
            utilization_percent=50,
            survival=0,
            building_defense=0,
            map_name="jl1",
            defeated_ai_types=["beginner"],
            primary_enemy_ai="beginner",
        )
        ach.record_defeat_progress(ctx, state)
        newly, _ = ach.evaluate_new_unlocks(ctx, state)
        assert newly == []
    ctx = ach.AchievementContext(
        victory=True,
        grade="C",
        utilization_percent=50,
        survival=0,
        building_defense=0,
        map_name="jl1",
        defeated_ai_types=["beginner"],
        primary_enemy_ai="beginner",
    )
    ach.record_defeat_progress(ctx, state)
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["win_beginner_3"]
    assert state["ai_defeats"]["beginner"] == 3


def test_defeated_ai_map_at_least_requires_specific_map(isolated_achievements):
    ach.load_achievements("""
        def pra1_beginner_3
        title 5308
        condition victory
        condition map pra1
        condition defeated_ai beginner
        condition defeated_ai_map_at_least pra1 3 beginner
        once
        reward medal 12
    """)
    state = ach._empty_unlock_state()
    for map_name in ("pra1", "pra1", "jl1"):
        ctx = ach.AchievementContext(
            victory=True,
            grade="C",
            utilization_percent=50,
            survival=0,
            building_defense=0,
            map_name=map_name,
            defeated_ai_types=["beginner"],
            primary_enemy_ai="beginner",
        )
        ach.record_defeat_progress(ctx, state)
    assert state["map_ai_defeats"]["pra1"]["beginner"] == 2
    ctx_final = ach.AchievementContext(
        victory=True,
        grade="C",
        utilization_percent=50,
        survival=0,
        building_defense=0,
        map_name="pra1",
        defeated_ai_types=["beginner"],
        primary_enemy_ai="beginner",
    )
    ach.record_defeat_progress(ctx_final, state)
    newly, _ = ach.evaluate_new_unlocks(ctx_final, state)
    assert [d.id for d in newly] == ["pra1_beginner_3"]


def test_map_condition_requires_specific_map(isolated_achievements):
    ach.load_achievements("""
        def jl9_nightmare
        title 5306
        condition victory
        condition map jl9
        condition defeated_ai nightmare
        once
        reward medal 50
    """)
    ctx_ok = ach.AchievementContext(
        victory=True,
        grade="B",
        utilization_percent=50,
        survival=50,
        building_defense=50,
        map_name="jl9",
        defeated_ai_types=["nightmare"],
        primary_enemy_ai="nightmare",
    )
    ctx_wrong_map = ach.AchievementContext(
        victory=True,
        grade="B",
        utilization_percent=50,
        survival=50,
        building_defense=50,
        map_name="jl1",
        defeated_ai_types=["nightmare"],
        primary_enemy_ai="nightmare",
    )
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx_ok, state)
    assert [d.id for d in newly] == ["jl9_nightmare"]
    newly2, _ = ach.evaluate_new_unlocks(ctx_wrong_map, state)
    assert newly2 == []


def test_map_condition_accepts_any_listed_map(isolated_achievements):
    ach.load_achievements("""
        def multi_map_win
        title 5308
        condition victory
        condition map jl9 z5 pra11
        once
        reward medal 10
    """)
    for map_name in ("jl9", "z5", "pra11"):
        state = ach._empty_unlock_state()
        ctx = ach.AchievementContext(
            victory=True,
            grade="C",
            utilization_percent=50,
            survival=0,
            building_defense=0,
            map_name=map_name,
            defeated_ai_types=[],
            primary_enemy_ai=None,
        )
        newly, _ = ach.evaluate_new_unlocks(ctx, state)
        assert [d.id for d in newly] == ["multi_map_win"]


def test_achievement_requirement_msgs_includes_map(isolated_achievements):
    ach.load_achievements("""
        def map_challenge
        title 5300
        condition victory
        condition map jl9
        condition defeated_ai expert
    """)
    defn = ach.get_achievement_defs()["map_challenge"]
    msgs = ach.achievement_requirement_msgs(defn)
    assert mp.ACHIEVEMENT_ON_MAP[0] in msgs


def test_achievement_requirement_msgs_grade_and_defeated_ai():
    ach.load_achievements("""
        def grade_s
        title 5300
        condition grade S
        def defeat_expert
        title 5307
        condition defeated_ai expert
        def frugal_victory
        title 5304
        condition victory
        condition utilization_below 30
    """)
    grade_s = ach.get_achievement_defs()["grade_s"]
    expert = ach.get_achievement_defs()["defeat_expert"]
    frugal = ach.get_achievement_defs()["frugal_victory"]

    grade_msgs = ach.achievement_requirement_msgs(grade_s)
    assert mp.ACHIEVEMENT_REQUIRES[0] in grade_msgs
    assert mp.SCORE_GRADE_S[0] in grade_msgs

    expert_msgs = ach.achievement_requirement_msgs(expert)
    assert mp.SCORE_DEFEATED[0] in expert_msgs
    assert mp.EXPERT_COMPUTER[0] in expert_msgs

    frugal_msgs = ach.achievement_requirement_msgs(frugal)
    assert mp.ACHIEVEMENT_REQ_VICTORY[0] in frugal_msgs
    assert mp.SCORE_EFFICIENCY[0] in frugal_msgs
    assert mp.ACHIEVEMENT_BELOW[0] in frugal_msgs
    assert mp.AND[0] in frugal_msgs


def test_achievement_requirement_msgs_empty_when_unlocked_in_menu(isolated_achievements):
    _load_sample()
    state = ach._empty_unlock_state()
    state["unlocked"]["grade_s"] = {"count": 1}
    ach.save_unlock_state(state)
    entries = ach_menu.build_achievement_menu_entries()
    grade_entry = next(e for e in entries if e[0][0] == 5300)
    assert grade_entry[1] is True
    assert grade_entry[2] == []


def test_no_duplicate_beginner_easy_achievements_in_base_file():
    from soundrts.lib.resource import res

    res.load_rules_and_ai()
    order = ach.get_achievement_order()
    titles = []
    for aid in order:
        defn = ach.get_achievement_defs()[aid]
        if defn.title:
            titles.append(tuple(defn.title))
    assert titles.count((5308,)) <= 1


def test_load_achievement_rewards(isolated_achievements):
    ach.load_achievements("""
        def with_rewards
        title 5300
        condition grade S
        reward medal 50
        reward card card_infantry 2
    """)
    defn = ach.get_achievement_defs()["with_rewards"]
    assert defn.rewards == [("medal", 50), ("card", "card_infantry", 2)]


def test_unlock_grants_medals_and_cards(isolated_achievements):
    card_mod.load_cards("""
        def card_infantry
        title 5322
        spawn footman 3
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition grade S
        reward medal 10
        reward card card_infantry
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
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["rewarded"]
    assert state["medals"] == 10
    assert state["cards"]["card_infantry"]["charges"] == 1


def test_process_game_end_announces_rewards(isolated_achievements):
    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition grade S
        reward medal 5
        reward card card_infantry
    """)
    player = SimpleNamespace(
        has_victory=True,
        is_spectator=False,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 750,
                "utilization_percent": 50,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [],
            },
            score_grade_letter=lambda total=None: "S",
        ),
    )
    game = SimpleNamespace(map=SimpleNamespace(name="testmap"))
    msgs = ach.process_game_end_achievements(game, player)
    assert any(mp.REWARD_MEDAL_GAINED[0] in m for m in msgs)
    assert any(mp.REWARD_CARD_GAINED[0] in m for m in msgs)
    data = json.loads(isolated_achievements.read_text(encoding="utf-8"))
    assert data["medals"] == 5
    assert data["cards"]["card_infantry"]["charges"] == 1


def test_build_armory_menu_entries(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        def rank_private
        kind rank
        title 5401
        medals 15
    """)
    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    state = ach._empty_unlock_state()
    ach.grant_card(state, "card_infantry")
    ach.save_unlock_state(state)
    entries = ach_menu.build_armory_menu_entries()
    assert mp.ARMORY_RANK[0] in entries[0][0]
    assert any(e[1] == "card_infantry" for e in entries)


def test_rank_promotion_announced(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        loadout_slots 0
        def rank_private
        kind rank
        title 5401
        medals 35
        loadout_slots 0
        def rank_lieutenant
        kind rank
        title 5404
        medals 200
        loadout_slots 1
    """)
    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition grade S
        reward medal 240
    """)
    player = SimpleNamespace(
        has_victory=True,
        is_spectator=False,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 750,
                "utilization_percent": 50,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [],
            },
            score_grade_letter=lambda total=None: "S",
        ),
    )
    game = SimpleNamespace(map=SimpleNamespace(name="testmap"))
    msgs = ach.process_game_end_achievements(game, player)
    assert any(mp.RANK_PROMOTED[0] in m for m in msgs)
    slot_msgs = [m for m in msgs if mp.LOADOUT_SLOTS_INCREASED[0] in m]
    assert len(slot_msgs) == 1
    assert mp.LOADOUT_SLOT_SUFFIX[0] in slot_msgs[0]


def test_rank_promotion_without_slot_increase_is_silent(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        loadout_slots 0
        def rank_private
        kind rank
        title 5401
        medals 35
        loadout_slots 0
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition grade S
        reward medal 40
    """)
    player = SimpleNamespace(
        has_victory=True,
        is_spectator=False,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 750,
                "utilization_percent": 50,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [],
            },
            score_grade_letter=lambda total=None: "S",
        ),
    )
    msgs = ach.process_game_end_achievements(
        SimpleNamespace(map=SimpleNamespace(name="m1")), player
    )
    assert any(mp.RANK_PROMOTED[0] in m for m in msgs)
    assert not any(mp.LOADOUT_SLOTS_INCREASED[0] in m for m in msgs)


def test_honor_title_granted_once(isolated_achievements):
    title_mod.load_titles("""
        def honor_test
        kind honor
        title 5420
    """)
    ach.load_achievements("""
        def with_honor
        title 5300
        condition grade S
        reward title honor_test
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
    state = ach._empty_unlock_state()
    _, honors = ach.evaluate_new_unlocks(ctx, state)
    assert honors == ["honor_test"]
    assert state["honors"] == ["honor_test"]
    _, honors2 = ach.evaluate_new_unlocks(ctx, state)
    assert honors2 == []


def test_duplicate_honor_skipped_when_same_as_achievement_title(isolated_achievements):
    title_mod.load_titles("""
        def honor_same
        kind honor
        title 5304
    """)
    ach.load_achievements("""
        def frugal
        title 5304
        condition victory
        condition utilization_below 30
        reward title honor_same
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="B",
        utilization_percent=10,
        survival=80,
        building_defense=80,
        map_name="m1",
        defeated_ai_types=[],
        primary_enemy_ai=None,
    )
    state = ach._empty_unlock_state()
    newly, honors = ach.evaluate_new_unlocks(ctx, state)
    assert [d.id for d in newly] == ["frugal"]
    assert honors == []
    assert state.get("honors", []) == []
    msgs = ach.achievement_reward_msgs(newly, state, honors)
    assert not any(mp.REWARD_HONOR_GAINED[0] in m for m in msgs)


def test_distinct_honor_announced_for_nightmare(isolated_achievements):
    title_mod.load_titles("""
        def honor_nightmare_slayer
        kind honor
        title 5422
    """)
    ach.load_achievements("""
        def defeat_nightmare
        title 5306
        condition defeated_ai nightmare
        reward title honor_nightmare_slayer
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="S",
        utilization_percent=50,
        survival=100,
        building_defense=100,
        map_name="m1",
        defeated_ai_types=["nightmare"],
        primary_enemy_ai="nightmare",
    )
    state = ach._empty_unlock_state()
    newly, honors = ach.evaluate_new_unlocks(ctx, state)
    assert honors == ["honor_nightmare_slayer"]
    msgs = ach.achievement_unlock_msgs(newly) + ach.achievement_reward_msgs(newly, state, honors)
    assert any(mp.ACHIEVEMENT_UNLOCKED[0] in m and 5306 in m for m in msgs)
    assert any(mp.REWARD_HONOR_GAINED[0] in m and 5422 in m for m in msgs)


def test_armory_next_rank_progress_phrasing(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        def rank_private
        kind rank
        title 5401
        medals 35
    """)
    state = ach._empty_unlock_state()
    state["medals"] = 5
    ach.save_unlock_state(state)
    line = next(e for e in ach_menu.build_armory_menu_entries() if e[1] == "next_rank")[0]
    from soundrts.lib.msgs import nb2msg

    assert line == (
        mp.ARMORY_RANK_PROGRESS
        + [5401]
        + mp.ARMORY_RANK_PROGRESS_NEED
        + nb2msg(30)
        + mp.ARMORY_MEDAL_UNIT
    )


def test_armory_shows_min_rank_on_locked_card(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
        loadout_slots 0
        def rank_lieutenant
        kind rank
        title 5404
        medals 200
        loadout_slots 1
    """)
    card_mod.load_cards("""
        def card_siege
        title 5327
        min_rank rank_lieutenant
        grant_charges 1
    """)
    state = ach._empty_unlock_state()
    ach.grant_card(state, "card_siege")
    ach.save_unlock_state(state)
    entries = ach_menu.build_armory_menu_entries()
    siege_line = next(e for e in entries if e[1] == "card_siege")
    assert mp.ARMORY_REQUIRES_RANK[0] in siege_line[0]
    assert 5404 in siege_line[0]


def test_build_current_rank_msgs(isolated_achievements):
    title_mod.load_titles("""
        def rank_recruit
        kind rank
        title 5400
        medals 0
    """)
    state = ach._empty_unlock_state()
    ach.save_unlock_state(state)
    msgs = ach.build_current_rank_msgs()
    assert msgs == [mp.ARMORY_RANK + [5400]]


def test_normalize_unlock_state_adds_inventory_keys(isolated_achievements):
    isolated_achievements.write_text(
        '{"unlocked": {}, "once_keys": {}}', encoding="utf-8"
    )
    state = ach.load_unlock_state()
    assert "medals" in state
    assert "cards" in state
    assert "honors" in state


def test_achievements_enabled_default():
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def parameters
nb_of_resource_types 2
""")
    assert r.get("parameters", "achievements_enabled", 1) == 1


def test_achievements_enabled_mod_disable(monkeypatch):
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def parameters
achievements_enabled 0
""")
    monkeypatch.setattr(ach, "rules", r)
    assert ach.achievements_enabled() is False


def test_process_game_end_skipped_when_disabled(isolated_achievements, monkeypatch):
    monkeypatch.setattr(ach, "achievements_enabled", lambda: False)
    player = SimpleNamespace(
        is_spectator=False,
        stats=SimpleNamespace(score_breakdown=lambda: {}),
    )
    assert ach.process_game_end_achievements(SimpleNamespace(), player) == []


def test_main_menu_hides_achievements_when_disabled(monkeypatch):
    from soundrts import clientmain
    from soundrts import msgparts as mp

    monkeypatch.setattr(ach, "achievements_enabled", lambda: False)
    labels = [choice[0] for choice in clientmain._build_main_menu_choices()]
    assert mp.ACHIEVEMENTS not in labels


def test_faction_ai_script_counts_toward_standard_tier(isolated_achievements, monkeypatch):
    from soundrts.lib.resource import res

    monkeypatch.setattr(
        "soundrts.faction_progress.rules.get",
        lambda obj, attr, default=None: (
            1 if obj == "parameters" and attr == "achievements_per_faction" else default
        ),
    )
    res.set_mods("crazyMod9beta10")
    res.load_rules_and_ai()
    ach.load_achievements("""
        def ver_map_z5
        faction vermine
        title 79928
        condition victory
        condition defeated_ai expert
        condition defeated_ai_map_at_least z5 1 expert
        once
        reward medal 50
    """)
    ctx = ach.AchievementContext(
        victory=True,
        grade="B",
        utilization_percent=50,
        survival=50,
        building_defense=50,
        map_name="z5",
        defeated_ai_types=["traditionnel_exp"],
        primary_enemy_ai="traditionnel_exp",
    )
    state = ach._empty_unlock_state()
    ach.record_defeat_progress(ctx, state)
    newly, _ = ach.evaluate_new_unlocks(ctx, state, "vermine")
    assert [d.id for d in newly] == ["ver_map_z5"]
    assert state["map_ai_defeats"]["z5"]["expert"] == 1


def test_achievement_requirement_msgs_includes_map_and_cumulative(isolated_achievements):
    ach.load_achievements("""
        def pra9_expert_1
        title 79921
        condition victory
        condition map pra9
        condition defeated_ai expert
        condition defeated_ai_map_at_least pra9 1 expert
    """)
    defn = ach.get_achievement_defs()["pra9_expert_1"]
    msgs = ach.achievement_requirement_msgs(defn)
    assert mp.ACHIEVEMENT_REQ_VICTORY[0] in msgs
    assert msgs.count(mp.ACHIEVEMENT_ON_MAP[0]) == 2
    assert msgs.count(mp.SCORE_DEFEATED[0]) == 2


def test_process_game_end_skipped_for_campaign(isolated_achievements):
    ach.load_achievements("""
        def grade_s
        title 5300
        condition grade S
        once
        reward medal 10
    """)
    player = SimpleNamespace(
        has_victory=True,
        is_spectator=False,
        faction="traditionnel",
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 750,
                "utilization_percent": 50,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [{"ai_type": "expert", "count": 1, "points": 80}],
            },
            score_grade_letter=lambda total=None: "S",
        ),
    )
    game = SimpleNamespace(
        game_type_name="mission",
        is_coop_campaign=False,
        world=SimpleNamespace(is_campaign=True, map=SimpleNamespace(name="chapter1")),
        map=SimpleNamespace(name="chapter1"),
    )
    msgs = ach.process_game_end_achievements(game, player)
    assert msgs == []
    assert not isolated_achievements.exists() or json.loads(
        isolated_achievements.read_text(encoding="utf-8")
    ).get("medals", 0) == 0


def _rmg_ctx(mode: str, *, victory: bool = True) -> ach.AchievementContext:
    return ach.AchievementContext(
        victory=victory,
        grade="B",
        utilization_percent=50,
        survival=80,
        building_defense=80,
        map_name="random_42.txt",
        defeated_ai_types=["beginner"],
        primary_enemy_ai="beginner",
        is_random_map=True,
        victory_mode=mode,
    )


def test_rmg_victory_mode_achievement_unlocks(isolated_achievements):
    ach.load_achievements("""
        def rmg_conquest
        title 5445
        condition victory_mode conquest
        condition victory
        once
        reward medal 20
    """)
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(_rmg_ctx("conquest"), state)
    assert [d.id for d in newly] == ["rmg_conquest"]
    assert state["medals"] == 20

    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(_rmg_ctx("economic"), state)
    assert newly == []


def test_rmg_victory_mode_requires_random_map_flag(isolated_achievements):
    ach.load_achievements("""
        def rmg_survival
        title 5448
        condition victory_mode survival
        condition victory
        once
    """)
    ctx = _rmg_ctx("survival")
    ctx.is_random_map = False
    state = ach._empty_unlock_state()
    newly, _ = ach.evaluate_new_unlocks(ctx, state)
    assert newly == []


def test_rmg_mode_master_unlocks_after_four_modes(isolated_achievements):
    ach.load_achievements("""
        def rmg_conquest
        title 5445
        condition victory_mode conquest
        condition victory
        once

        def rmg_economic
        title 5446
        condition victory_mode economic
        condition victory
        once

        def rmg_exploration
        title 5447
        condition victory_mode exploration
        condition victory
        once

        def rmg_survival
        title 5448
        condition victory_mode survival
        condition victory
        once

        def rmg_mode_master
        title 5449
        condition achievement rmg_conquest
        condition achievement rmg_economic
        condition achievement rmg_exploration
        condition achievement rmg_survival
        once
        reward medal 40
    """)
    state = ach._empty_unlock_state()
    for mode in ("conquest", "economic", "exploration"):
        newly, _ = ach.evaluate_new_unlocks(_rmg_ctx(mode), state)
        assert [d.id for d in newly] == [f"rmg_{mode}"]

    newly, _ = ach.evaluate_new_unlocks(_rmg_ctx("survival"), state)
    assert [d.id for d in newly] == ["rmg_survival", "rmg_mode_master"]
    assert state["medals"] == 40


def test_rmg_requirement_msgs(isolated_achievements):
    ach.load_achievements("""
        def rmg_exploration
        title 5447
        condition victory_mode exploration
        condition victory
        once
    """)
    defn = ach.get_achievement_defs()["rmg_exploration"]
    msgs = ach.achievement_requirement_msgs(defn)
    flat = list(msgs)
    assert mp.ACHIEVEMENT_ON_RANDOM_MAP[0] in flat
    assert mp.RMG_VICTORY_EXPLORATION[0] in flat
    assert mp.ACHIEVEMENT_REQ_VICTORY[0] in flat


def test_build_context_reads_random_map_meta(isolated_achievements):
    definition = (
        "title random_map standard seed_9\n"
        "random_map 1\n"
        "victory_mode economic\n"
        "objective 5435 5437\n"
    )
    player = SimpleNamespace(
        has_victory=True,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 500,
                "utilization_percent": 40,
                "survival": 70,
                "building_defense": 70,
                "ai_defeat_entries": [],
            },
            score_grade_letter=lambda total: "B",
        ),
    )
    game = SimpleNamespace(
        map=SimpleNamespace(name="random_9.txt", definition=definition),
    )
    ctx = ach.build_context(player, game)
    assert ctx.is_random_map is True
    assert ctx.victory_mode == "economic"
