"""1.3.8.1 parity: stick only to menacing targets; re-scan when hitting farms etc."""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401 — break import cycles

from soundrts.worldunit import world_ai_decision as wad


class _Square:
    def __init__(self, sid):
        self.id = sid
        self.neighbors = []
        self.strict_neighbors = []
        self.exits = []


class _Target:
    def __init__(self, menace, place, uid=1):
        self.menace = menace
        self.place = place
        self.hp = 100
        self.id = uid
        self.is_creature = True
        self.player = types.SimpleNamespace(neutral=False)
        self.x = self.y = 0


class _DecideStub:
    _last_decide_time = 0
    _decision_cache = {}
    _decision_cache_bucket = -1
    _cached_has_attack = True

    def __init__(self, place):
        self.ai_mode = "offensive"
        self.speed = 10
        self.orders = []
        self.auto_explore = False
        self.world = types.SimpleNamespace(time=100000)
        self.id = 1
        self.last_attacker = None
        self.mdg = 10
        self.rdg = 0
        self.is_inside = False
        self.place = place
        self.attacked = []
        self._previous_square = None
        self.action = None
        self.counterattack_enabled = False
        self.player = types.SimpleNamespace(
            smart_units=False,
            enemy_menace=lambda _p: 0,
            balance=lambda *a, **k: 10,
        )

    def is_an_enemy(self, other):
        return True

    def _is_neutral_target(self, other):
        return False

    def _player_ordered_attack_on(self, other):
        return False

    def _must_hold(self):
        return False

    def _wildlife_wander(self):
        return False

    def can_attack(self, other):
        return True

    def _attack(self, target):
        self.attacked.append(target)
        self.action = types.SimpleNamespace(target=target)

    def take_order(self, *args, **kwargs):
        pass

    def notify(self, *args, **kwargs):
        pass

    def _get_squares_in_sight(self):
        return []

    def _choose_enemy(self, place):
        return False


def test_sticky_engage_skips_rescan_for_menacing_target():
    place = _Square("sq1")
    unit = _DecideStub(place)
    soldier = _Target(menace=100, place=place, uid=2)
    unit.action = types.SimpleNamespace(target=soldier)
    choose_calls = []

    def _choose(place):
        choose_calls.append(place)
        return False

    unit._choose_enemy = _choose
    _DecideStub._decision_cache = {}
    _DecideStub._decision_cache_bucket = -1

    wad.CreatureAIDecision.decide(unit)

    assert choose_calls == []
    assert unit.attacked == []  # sticky path returns without re-_attack


def test_sticky_engage_rescan_when_target_has_zero_menace():
    place = _Square("sq1")
    unit = _DecideStub(place)
    farm = _Target(menace=0, place=place, uid=3)
    soldier = _Target(menace=200, place=place, uid=4)
    unit.action = types.SimpleNamespace(target=farm)

    def _choose(place):
        unit._attack(soldier)
        return True

    unit._choose_enemy = _choose
    _DecideStub._decision_cache = {}
    _DecideStub._decision_cache_bucket = -1

    wad.CreatureAIDecision.decide(unit)

    assert unit.attacked == [soldier]


def test_decision_cache_does_not_lock_zero_menace_target():
    place = _Square("sq1")
    unit = _DecideStub(place)
    farm = _Target(menace=0, place=place, uid=5)
    soldier = _Target(menace=200, place=place, uid=6)
    unit.action = types.SimpleNamespace(target=farm)

    bucket = unit.world.time // 150
    _DecideStub._decision_cache = {(unit.id, bucket): {"action": "attack", "target": farm}}
    _DecideStub._decision_cache_bucket = bucket

    def _choose(place):
        unit._attack(soldier)
        return True

    unit._choose_enemy = _choose

    wad.CreatureAIDecision.decide(unit)

    assert unit.attacked == [soldier]
