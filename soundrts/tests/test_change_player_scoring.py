"""change_player (Ctrl+Shift+F4) must not steal score/achievement credit from the human."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from soundrts import achievements as ach
from soundrts import game as game_mod
from soundrts import msgparts as mp
from soundrts.clientgame import game_resources


class _TrainingGameStub(game_mod._Game):
    game_type_name = "training"

    def __init__(self, human, ai, defeated_enemy_ids=None):
        self.world = SimpleNamespace(players=[human, ai], ex_players=[])
        self.map = SimpleNamespace(name="testmap", definition="")
        self.local_client = SimpleNamespace(
            player=human,
            allow_cheatmode=True,
            login="player1",
            game_session=self,
        )
        human.client = self.local_client
        self.is_coop_campaign = False
        self._defeated_ids = set(defeated_enemy_ids or [])
        self._pin_scoring_player()

    def _defeated_scoring_enemy_ids(self, player):
        return set(self._defeated_ids)


def _stats_for(player):
    def score_breakdown(effective_victory=None, scored_enemy_ids=None):
        victory = player.has_victory if effective_victory is None else effective_victory
        return {
            "total": 750 if victory else 100,
            "utilization_percent": 50,
            "survival": 100,
            "building_defense": 100,
            "ai_defeat_entries": [],
        }

    def score_msgs(effective_victory=None, scored_enemy_ids=None):
        victory = player.has_victory if effective_victory is None else effective_victory
        return [["score", "victory" if victory else "defeat"]]

    def score_grade_letter(total=None):
        if total is None:
            total = 750 if player.has_victory else 100
        return "S" if total >= 720 else "E"

    return SimpleNamespace(
        score_msgs=score_msgs,
        score_breakdown=score_breakdown,
        score_grade_letter=score_grade_letter,
    )


def _make_players():
    human = SimpleNamespace(
        id=1,
        is_human=True,
        is_spectator=False,
        has_victory=False,
        faction="human_faction",
        stats=None,
        client=None,
    )
    ai = SimpleNamespace(
        id=2,
        is_human=False,
        is_spectator=False,
        has_victory=False,
        has_been_defeated=False,
        faction="human_faction",
        stats=None,
        client=SimpleNamespace(login="ai_easy"),
    )
    human.stats = _stats_for(human)
    ai.stats = _stats_for(ai)
    return human, ai


def test_scoring_player_pinned_before_change_player():
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    assert game.scoring_player() is human


def _apply_change_player(game, ai, monkeypatch):
    monkeypatch.setattr(
        "soundrts.clientgame.game_navigation.update_fog_of_war",
        lambda _interface: None,
    )
    interface = SimpleNamespace(
        server=game.local_client,
        world=game.world,
        player=game.scoring_player(),
        memory={},
    )
    game_resources._change_player(interface, ai)
    return interface


def test_change_player_rebinds_local_client_but_not_scoring_player(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)

    assert game.local_client.player is ai
    assert game.scoring_player() is human
    assert ai.client is game.local_client
    assert game._enemies_defeated_at_first_change == set()


def test_scoring_victory_blocks_passive_win_after_switch():
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    game._change_player_used = True
    game._enemies_defeated_at_first_change = set()
    human.has_victory = True
    game._defeated_ids = {ai.id}
    assert game.scoring_victory() is False


def test_scoring_victory_allows_win_before_switch_then_observe_ai():
    human, ai = _make_players()
    ai.has_been_defeated = True
    game = _TrainingGameStub(human, ai, defeated_enemy_ids={ai.id})
    game._change_player_used = True
    game._enemies_defeated_at_first_change = {ai.id}
    human.has_victory = True
    assert game.scoring_victory() is True


def test_say_score_uses_scoring_player_after_change_player(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)

    spoken = []
    monkeypatch.setattr(game_mod.voice, "info", spoken.append)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game.say_score()
    assert spoken == [["score", "defeat"]]


def test_say_score_after_human_win_while_on_ai_view(monkeypatch):
    human, ai = _make_players()
    human.has_victory = True
    ai.has_been_defeated = True
    game = _TrainingGameStub(human, ai, defeated_enemy_ids={ai.id})
    _apply_change_player(game, ai, monkeypatch)

    spoken = []
    monkeypatch.setattr(game_mod.voice, "info", spoken.append)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game.say_score()
    assert spoken == [["score", "victory"]]


def test_say_score_blocks_passive_win_when_npc_kills_ai_after_switch(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)
    ai.has_been_defeated = True
    human.has_victory = True
    game._defeated_ids = {ai.id}

    spoken = []
    monkeypatch.setattr(game_mod.voice, "info", spoken.append)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game.say_score()
    assert spoken == [["score", "defeat"]]


def test_say_score_after_defeat_in_ex_players(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)
    game.world.players.remove(human)
    game.world.ex_players = [human]

    spoken = []
    monkeypatch.setattr(game_mod.voice, "info", spoken.append)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game.say_score()
    assert spoken == [["score", "defeat"]]


def test_post_run_plays_defeat_not_victory_after_change_player(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    game.world.map_victory_sound = "v"
    game.world.map_defeat_sound = "d"
    _apply_change_player(game, ai, monkeypatch)

    played = {"sound": None}

    def _play_victory(_s):
        played["sound"] = "victory"

    def _play_defeat(_s):
        played["sound"] = "defeat"

    monkeypatch.setattr("soundrts.lib.sound.play_victory_sound", _play_victory)
    monkeypatch.setattr("soundrts.lib.sound.play_defeat_sound", _play_defeat)
    monkeypatch.setattr(game_mod.voice, "info", lambda *_a, **_k: None)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)
    monkeypatch.setattr(game_mod.Upgrade, "reset", lambda: None)

    game.post_run()
    assert played["sound"] == "defeat"


def test_post_run_blocks_passive_win_music(monkeypatch):
    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    game.world.map_victory_sound = "v"
    game.world.map_defeat_sound = "d"
    _apply_change_player(game, ai, monkeypatch)
    ai.has_been_defeated = True
    human.has_victory = True
    game._defeated_ids = {ai.id}

    played = {"sound": None}
    monkeypatch.setattr(
        "soundrts.lib.sound.play_victory_sound",
        lambda _s: played.__setitem__("sound", "victory"),
    )
    monkeypatch.setattr(
        "soundrts.lib.sound.play_defeat_sound",
        lambda _s: played.__setitem__("sound", "defeat"),
    )
    monkeypatch.setattr(game_mod.voice, "info", lambda *_a, **_k: None)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)
    monkeypatch.setattr(game_mod.Upgrade, "reset", lambda: None)

    game.post_run()
    assert played["sound"] == "defeat"


@pytest.fixture
def isolated_achievements(monkeypatch, tmp_path):
    monkeypatch.setattr(ach, "_achievements", {})
    monkeypatch.setattr(ach, "_achievements_order", [])
    save = tmp_path / "ach.json"
    monkeypatch.setattr(ach, "achievements_enabled", lambda: True)
    monkeypatch.setattr(ach, "achievements_per_faction_enabled", lambda: False)
    monkeypatch.setattr(ach, "achievements_save_path", lambda faction=None: str(save))
    return save


def test_achievements_use_scoring_player_after_change_player(isolated_achievements, monkeypatch):
    from soundrts import cards as card_mod

    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition victory
        condition grade S
        reward medal 5
        reward card card_infantry
    """)

    human, ai = _make_players()
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)

    monkeypatch.setattr(game_mod.voice, "info", lambda *_a, **_k: None)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game._say_achievements()

    assert not isolated_achievements.exists() or isolated_achievements.read_text(encoding="utf-8").strip() in ("", "{}")


def test_achievements_after_human_win_while_on_ai_view(isolated_achievements, monkeypatch):
    from soundrts import cards as card_mod

    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition victory
        condition grade S
        reward medal 5
        reward card card_infantry
    """)

    human, ai = _make_players()
    human.has_victory = True
    ai.has_been_defeated = True
    game = _TrainingGameStub(human, ai, defeated_enemy_ids={ai.id})
    _apply_change_player(game, ai, monkeypatch)

    spoken = []
    monkeypatch.setattr(game_mod.voice, "info", spoken.append)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game._say_achievements()

    data = isolated_achievements.read_text(encoding="utf-8")
    assert '"medals": 5' in data.replace(" ", "") or '"medals":5' in data.replace(" ", "")
    assert any(mp.REWARD_MEDAL_GAINED[0] in m for m in spoken)


def test_achievements_blocked_when_npc_kills_ai_after_switch(isolated_achievements, monkeypatch):
    from soundrts import cards as card_mod

    card_mod.load_cards("""
        def card_infantry
        title 5322
        grant_charges 1
    """)
    ach.load_achievements("""
        def rewarded
        title 5300
        condition victory
        condition grade S
        reward medal 5
        reward card card_infantry
    """)

    human, ai = _make_players()
    human.has_victory = True
    game = _TrainingGameStub(human, ai)
    _apply_change_player(game, ai, monkeypatch)
    ai.has_been_defeated = True
    game._defeated_ids = {ai.id}

    monkeypatch.setattr(game_mod.voice, "info", lambda *_a, **_k: None)
    monkeypatch.setattr(game_mod.voice, "flush", lambda: None)

    game._say_achievements()

    assert not isolated_achievements.exists() or isolated_achievements.read_text(encoding="utf-8").strip() in ("", "{}")
