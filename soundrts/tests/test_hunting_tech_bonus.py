"""狩猎科技：尸体食物储量加成。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.definitions import rules
from soundrts.worldresource import Deposit
from soundrts.worldunit.worldcreature import Creature


class _Square:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.objects = []
        self.is_inside_place = False
        self.world = types.SimpleNamespace(
            unit_class=lambda name: rules.unit_class(name),
            unregister_entity=lambda _e: None,
        )

    def enter(self, obj):
        self.objects.append(obj)

    def leave(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)

    def add(self, obj):
        if obj not in self.objects:
            self.objects.append(obj)

    def remove(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)


def test_food_deposit_qty_bonus_increases_carcass():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())
    sq = _Square()
    player = types.SimpleNamespace(food_deposit_qty_bonus=10)
    deposit = Creature._create_hunt_food_deposit(
        sq.world, "food_carcass", 35, sq, 100, 200, player=player
    )
    assert deposit is not None
    assert isinstance(deposit, Deposit)
    assert deposit.qty == 45000
