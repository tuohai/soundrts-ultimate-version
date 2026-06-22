"""盟友不可互相占领可夺取建筑的回归测试。"""
from __future__ import annotations

import random
import types


class _Player:
    def __init__(self, pid):
        self.id = pid
        self.allied = [self]

    def player_is_an_enemy(self, other):
        return other is not None and other not in self.allied

    def observe(self, _attacker):
        pass

    def on_unit_attacked(self, _unit, _attacker):
        pass


def _make_building(owner):
    from soundrts.combat.damage_effects import DamageEffectsMixin

    class _Building(DamageEffectsMixin):
        pass

    building = _Building()
    building.player = owner
    building.hp = 50
    building.hp_max = 100
    building.capture_hp_threshold = 100
    building.place = None
    building.world = types.SimpleNamespace(
        time=0,
        treaty_until_time=0,
        random=random.Random(0),
        unit_class=lambda _name: None,
    )

    def set_player(player):
        building.player = player

    building.set_player = set_player
    building.notify = lambda *_args, **_kwargs: None
    return building


def _make_attacker(player):
    from soundrts.combat.damage_effects import DamageEffectsMixin

    class _Attacker(DamageEffectsMixin):
        pass

    attacker = _Attacker()
    attacker.player = player
    attacker._bypass_damage_calc_for_harm = True
    return attacker


def test_allied_attack_does_not_capture_building():
    owner = _Player("owner")
    ally = _Player("ally")
    owner.allied = [owner, ally]
    ally.allied = [owner, ally]

    building = _make_building(owner)
    attacker = _make_attacker(ally)

    building.receive_hit(0, attacker, notify=False)

    assert building.player is owner


def test_enemy_attack_can_capture_building():
    owner = _Player("owner")
    enemy = _Player("enemy")

    building = _make_building(owner)
    attacker = _make_attacker(enemy)

    building.receive_hit(0, attacker, notify=False)

    assert building.player is enemy
