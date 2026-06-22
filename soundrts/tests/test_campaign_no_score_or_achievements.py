"""Campaign sessions must not report score breakdowns or record play-time stats."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from soundrts import achievements as ach
from soundrts import game as game_mod


class _MissionGame(game_mod._Game):
    game_type_name = "mission"

    def __init__(self):
        self.map = SimpleNamespace(name="chapter1")
        self.local_client = SimpleNamespace(player=None)
        self.is_coop_campaign = False
        self.world = SimpleNamespace(is_campaign=True)


class _MultiplayerGame(game_mod._Game):
    game_type_name = "multiplayer"

    def __init__(self, is_campaign=False):
        self.map = SimpleNamespace(name="jl1")
        self.local_client = SimpleNamespace(
            player=SimpleNamespace(
                is_spectator=False,
                stats=SimpleNamespace(score_msgs=lambda: [["score"]]),
            )
        )
        self.is_coop_campaign = is_campaign
        self.world = SimpleNamespace(is_campaign=is_campaign)


def test_is_campaign_session_detects_mission_and_coop():
    mission = _MissionGame()
    assert mission.is_campaign_session() is True

    coop = _MultiplayerGame(is_campaign=True)
    coop.is_coop_campaign = True
    assert coop.is_campaign_session() is True

    multi = _MultiplayerGame(is_campaign=False)
    assert multi.is_campaign_session() is False


def test_say_score_skipped_for_campaign(monkeypatch):
    mission = _MissionGame()
    mission.local_client.player = SimpleNamespace(
        is_spectator=False,
        stats=SimpleNamespace(score_msgs=lambda: (_ for _ in ()).throw(AssertionError("no score"))),
    )
    flushed = {"called": False}

    def _flush():
        flushed["called"] = True

    monkeypatch.setattr(game_mod.voice, "flush", _flush)
    mission.say_score()
    assert flushed["called"] is True


def test_record_stats_skipped_for_campaign(monkeypatch):
    mission = _MissionGame()

    def _fail(*_args, **_kwargs):
        raise AssertionError("stats.add must not run for campaign")

    monkeypatch.setattr(game_mod.stats, "add", _fail)
    mission._record_stats(mission.world)


def test_record_stats_runs_for_multiplayer(monkeypatch):
    multi = _MultiplayerGame(is_campaign=False)
    multi.nb_human_players = 1
    recorded = []

    monkeypatch.setattr(multi, "_game_type", lambda: "test/multi/jl1/1")
    monkeypatch.setattr(
        game_mod.stats,
        "add",
        lambda game_type, seconds: recorded.append((game_type, seconds)),
    )
    multi.world.time = 125000
    multi._record_stats(multi.world)
    assert recorded == [("test/multi/jl1/1", 125)]


def test_process_game_end_achievements_skipped_for_multiplayer(monkeypatch, tmp_path):
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: tmp_path / "ach.json")
    game = SimpleNamespace(
        game_type_name="multiplayer",
        map=SimpleNamespace(name="jl1", definition=""),
        is_coop_campaign=False,
        world=SimpleNamespace(is_campaign=False),
    )
    player = SimpleNamespace(
        is_spectator=False,
        has_victory=True,
        faction=None,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 720,
                "utilization_percent": 20,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [{"ai_type": "nightmare", "count": 1, "points": 100}],
            },
            score_grade_letter=lambda total: "S",
        ),
    )
    assert ach.process_game_end_achievements(game, player) == []
    assert not (tmp_path / "ach.json").exists()


def test_process_game_end_achievements_runs_for_multiplayer_random_map(monkeypatch, tmp_path):
    monkeypatch.setattr(ach, "_achievements", {})
    monkeypatch.setattr(ach, "_achievements_order", [])
    save = tmp_path / "ach.json"
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(save))
    ach.load_achievements("""
        def rmg_conquest
        title 5445
        condition victory_mode conquest
        condition victory
        once
    """)
    game = SimpleNamespace(
        game_type_name="multiplayer",
        map=SimpleNamespace(
            name="random_42.txt",
            definition="random_map 1\nvictory_mode conquest\n",
        ),
        is_coop_campaign=False,
        world=SimpleNamespace(is_campaign=False),
    )
    player = SimpleNamespace(
        is_spectator=False,
        has_victory=True,
        faction=None,
        stats=SimpleNamespace(
            score_breakdown=lambda: {
                "total": 720,
                "utilization_percent": 20,
                "survival": 100,
                "building_defense": 100,
                "ai_defeat_entries": [],
            },
            score_grade_letter=lambda total: "S",
        ),
    )
    msgs = ach.process_game_end_achievements(game, player)
    assert msgs
    assert save.exists()
