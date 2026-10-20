"""测试 lang_campaign_defeat：剧情失败后能进入下一关。"""
from __future__ import annotations

import types
import pytest


class _StubClient:
    alliance = None


class _StubPlayer:
    is_human = True
    is_playing = True
    broadcasts_defeat_and_quit = False

    def __init__(self, player_id="p1", name="Player 1"):
        self.id = player_id
        self.name = name
        self.neutral = False
        self.units = []
        self.allied = [self]
        self.allied_control = (self,)
        self.allied_control_units_set = set()
        self.client = _StubClient()
        self._ally_requests_from = set()
        self._alliance_declined_from = set()
        self.objectives = {}
        self._required_objective_numbers = set()
        self._completed_objective_numbers = set()
        self.upgrades = []
        self.has_victory = False
        self.has_been_defeated = False
        self.voice = []
        self._pending = []
        self._stats = types.SimpleNamespace(freeze=lambda: None)

    @property
    def stats(self):
        return self._stats

    def push(self, what, payload=None):
        self._pending.append((what, payload))

    def pop(self):
        if self._pending:
            return self._pending.pop(0)
        return None


class _StubWorld:
    def __init__(self, players):
        self.players = players
        self.time = 0

    def add_to_queue(self, *args, **kwargs):
        pass


def _make_triggers(player, world):
    from soundrts.worldplayerbase.triggers import TriggersMixin
    t = TriggersMixin.__new__(TriggersMixin)
    t.world = world
    t.allied = [player]
    t.allied_victory = [player]
    t.allied_control = (player,)
    t.push = player.push
    t.has_victory = False
    t.has_been_defeated = False
    return t


def test_lang_campaign_defeat_marks_victory_and_pending_quit():
    human = _StubPlayer(player_id="h1", name="Joan")
    enemy1 = _StubPlayer(player_id="c1", name="English1")
    enemy1.is_playing = True
    world = _StubWorld([human, enemy1])
    human.world = world
    enemy1.world = world
    t = _make_triggers(human, world)
    t.lang_campaign_defeat([])
    assert t.has_victory is True
    assert world.campaign_defeat_pending is True
    # Check that quit was pushed
    quit_pushed = any(p[0] == "quit" for p in human._pending)
    assert quit_pushed, f"expected quit in pending, got {human._pending}"
    assert enemy1.has_been_defeated is True


def test_lang_campaign_defeat_with_cutscene_pushes_sequence():
    human = _StubPlayer(player_id="h1", name="Joan")
    world = _StubWorld([human])
    human.world = world
    t = _make_triggers(human, world)
    t.lang_campaign_defeat(["cutscene_joan_captured"])
    # Check sequence was pushed
    seq_pushed = any(p[0] == "sequence" and p[1] == ["cutscene_joan_captured"]
                     for p in human._pending)
    assert seq_pushed, f"expected sequence in pending, got {human._pending}"
    assert t.has_victory is True


def test_lang_campaign_defeat_handles_no_args():
    """Regression: 当 args 为空时不应报错。"""
    human = _StubPlayer(player_id="h1", name="Joan")
    world = _StubWorld([human])
    human.world = world
    t = _make_triggers(human, world)
    t.lang_campaign_defeat([])
    assert t.has_victory is True
    assert world.campaign_defeat_pending is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
