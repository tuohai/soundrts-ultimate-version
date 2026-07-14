"""Neutral go/follow must not look like attacking; huntables must take attack damage."""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.worldaction import AttackAction, MoveAction
from soundrts.worldunit.world_ai_decision import CreatureAIDecision
from soundrts.worldunit.worldcreature import Creature


class _Player:
    def __init__(self, neutral=False):
        self.neutral = neutral
        self.id = "p1" if not neutral else "n1"
        self.allied = [self]

    def player_is_an_enemy(self, other):
        return other is not None and other is not self and other not in self.allied


class _Stub(CreatureAIDecision):
    def __init__(self, orders=None):
        self.orders = orders or []
        self.player = _Player()
        self.world = types.SimpleNamespace(
            time=0,
            treaty_until_time=0,
            _allied_control_scanned=True,
            _allied_control_active=False,
        )
        self.mdg_range = 0
        self.rdg_range = 0
        self.speed = 10
        self.place = types.SimpleNamespace(id="sq", objects=[], neighbors=[])
        self.action = None
        self.is_creature = True

    def can_attack_if_in_range(self, other):
        return True

    def _get_melee_damage_vs(self, other):
        return 10

    def _get_ranged_damage_vs(self, other):
        return 0

    def _near_enough_to_aim(self, other):
        return True


# Bind Creature.is_an_enemy / set_action_target helpers onto stub via mixin methods
_Stub._is_neutral_target = CreatureAIDecision._is_neutral_target
_Stub._player_ordered_attack_on = CreatureAIDecision._player_ordered_attack_on
_Stub.can_attack = CreatureAIDecision.can_attack
_Stub.is_an_enemy = Creature.is_an_enemy
_Stub.set_action_target = Creature.set_action_target


class _NeutralUnit:
    is_creature = True
    hp = 100
    is_vulnerable = True
    id = "n1"
    is_huntable = 0

    def __init__(self, huntable=0):
        self.player = _Player(neutral=True)
        self.is_huntable = huntable
        self.place = types.SimpleNamespace(id="sq", objects=[], neighbors=[])
        self.x = self.y = 0


def test_go_to_neutral_sets_move_action_not_attack():
    unit = _Stub()
    neutral = _NeutralUnit()
    # Diplomacy: neutrals are "enemies" but go must not AttackAction
    assert unit.player.player_is_an_enemy(neutral.player) is True
    unit.set_action_target(neutral)
    assert isinstance(unit.action, MoveAction)
    assert not isinstance(unit.action, AttackAction)


def test_normal_attack_order_on_huntable_can_deal_damage():
    animal = _NeutralUnit(huntable=1)
    order = types.SimpleNamespace(
        is_imperative=False,
        target=animal,
        keyword="attack",
    )
    unit = _Stub(orders=[order])
    assert unit._player_ordered_attack_on(animal) is True
    assert unit.can_attack(animal) is True
    unit.set_action_target(animal)
    assert isinstance(unit.action, AttackAction)


def test_imperative_go_on_neutral_still_attacks():
    neutral = _NeutralUnit()
    order = types.SimpleNamespace(
        is_imperative=True,
        target=neutral,
        keyword="go",
    )
    unit = _Stub(orders=[order])
    assert unit._player_ordered_attack_on(neutral) is True
    assert unit.can_attack(neutral) is True
    unit.set_action_target(neutral)
    assert isinstance(unit.action, AttackAction)
