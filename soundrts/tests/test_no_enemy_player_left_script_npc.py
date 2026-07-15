"""回归：no_enemy_player_left 不应被地图 computer_only 脚本 NPC 挡住。

sg4 等多人图：玩家位是真人/邀请电脑，computer_only 是地图 creep。
邀请的初级电脑被 creep 消灭后，应对局胜利；残留的非中立 timers NPC
不得继续让 (no_enemy_player_left)(victory) 为假。
"""
from __future__ import annotations

from soundrts.worldplayerbase import Player


class _World:
    def __init__(self, players):
        self.is_campaign = False
        self.players = players
        self.ex_players = []

    def true_players(self):
        return [p for p in self.players if not getattr(p, "neutral", False)]

    @property
    def true_playing_players(self):
        return [p for p in self.true_players() if p.is_playing]

    @property
    def match_participating_players(self):
        return [p for p in self.true_playing_players if p.broadcasts_defeat_and_quit]


class _Client:
    def __init__(self, login="human"):
        self.login = login
        self.name = [login]


def _make_player(world, *, ai_type="", is_human=False, login="p", enemy_of=None):
    p = Player.__new__(Player)
    p.world = world
    p.AI_type = ai_type
    object.__setattr__(p, "is_human", is_human)
    p.neutral = False
    p.has_victory = False
    p.has_been_defeated = False
    p.units = []
    p.client = _Client(login)
    p._enemy = enemy_of
    p.player_is_an_enemy = lambda other, _self=p: other is not None and other is _self._enemy
    return p


def test_no_enemy_player_left_ignores_hostile_script_npc():
    """初级电脑已败、仅剩敌对 computer_only 时，应对局胜利条件成立。"""
    human = _make_player(None, is_human=True, login="human")
    beginner = _make_player(None, ai_type="beginner", login="ai_beginner")
    npc = _make_player(None, ai_type="timers", login="ai_timers")
    world = _World([human, beginner, npc])
    for p in (human, beginner, npc):
        p.world = world

    # 人类视角：beginner 与 timers NPC 都是敌人
    human._enemy = None
    human.player_is_an_enemy = lambda other: other in (beginner, npc)

    assert human.lang_no_enemy_player_left([]) is False

    beginner.has_been_defeated = True
    assert beginner.is_playing is False
    assert npc.is_playing is True
    assert npc.broadcasts_defeat_and_quit is False

    assert human.lang_no_enemy_player_left([]) is True


def test_no_enemy_player_left_still_requires_invited_ai():
    """邀请的电脑对手仍存活时，胜利条件不得成立。"""
    human = _make_player(None, is_human=True, login="human")
    beginner = _make_player(None, ai_type="beginner", login="ai_beginner")
    world = _World([human, beginner])
    human.world = world
    beginner.world = world
    human.player_is_an_enemy = lambda other: other is beginner

    assert human.lang_no_enemy_player_left([]) is False


def test_no_enemy_left_still_counts_script_npc():
    """需要清空全部敌对势力时仍用 no_enemy_left（含 timers NPC）。"""
    human = _make_player(None, is_human=True, login="human")
    npc = _make_player(None, ai_type="timers", login="ai_timers")
    world = _World([human, npc])
    human.world = world
    npc.world = world
    human.player_is_an_enemy = lambda other: other is npc

    assert human.lang_no_enemy_player_left([]) is True
    assert human.lang_no_enemy_left([]) is False
