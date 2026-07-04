"""attack_inside_chance：外部攻击容器时按几率命中内部乘客。"""
from __future__ import annotations

import types

from soundrts.combat.attack_action import AttackActionMixin
from soundrts.open_container import (
    container_visible_from_place,
    inside_unit_visible_from_place,
    is_open_container,
)
from soundrts.worldroom import Inside


def _square(name, *, neighbors=()):
    sq = types.SimpleNamespace(
        id=name,
        neighbors=list(neighbors),
        high_ground=False,
        type_name="meadow",
        terrain_cover=(0, 0),
        objects=[],
    )
    sq.type_name_at = lambda x, y: sq.type_name
    sq.terrain_cover_at = lambda x, y: sq.terrain_cover
    sq.high_ground_at = lambda x, y: sq.high_ground
    return sq


def _wall(*, place, chance=40, passengers=()):
    inside = Inside(types.SimpleNamespace(place=place, transport_capacity=4))
    inside.container = None  # set after wall is created
    wall = types.SimpleNamespace(
        place=place,
        inside=inside,
        transport_capacity=4,
        attack_inside_chance=chance,
        x=100,
        y=100,
        radius=50,
        blocked_exit=None,
    )
    inside.container = wall
    for p in passengers:
        p.place = inside
        p.is_inside = True
        p.x = 0
        p.y = 0
        p.hp = 100
        inside.objects.append(p)
    return wall


def _attacker(*, place, enemy_checker):
    world = types.SimpleNamespace(
        random=types.SimpleNamespace(
            randint=lambda a, b: 50,
            choice=lambda items: items[0],
        )
    )
    attacker = AttackActionMixin.__new__(AttackActionMixin)
    attacker.world = world
    attacker.place = place
    attacker.x = 0
    attacker.y = 0
    attacker.radius = 10
    attacker.allow_attack_inside = False
    attacker.is_an_enemy = enemy_checker
    attacker._near_enough_to_aim = lambda container: True
    return attacker


def test_get_attack_inside_chance_from_container():
    sq = _square("a1")
    wall = _wall(place=sq, chance=40)
    attacker = _attacker(place=sq, enemy_checker=lambda t: True)
    assert attacker._get_attack_inside_chance(wall) == 40


def test_resolve_damage_target_hits_passenger_on_roll():
    sq = _square("a1")
    enemy = types.SimpleNamespace(hp=100, player=types.SimpleNamespace())
    wall = _wall(place=sq, chance=100, passengers=[enemy])
    attacker = _attacker(place=sq, enemy_checker=lambda t: True)
    victim = attacker._resolve_damage_target(wall)
    assert victim is enemy


def test_resolve_damage_target_misses_container_on_low_roll():
    sq = _square("a1")
    enemy = types.SimpleNamespace(hp=100, player=types.SimpleNamespace())
    wall = _wall(place=sq, chance=0, passengers=[enemy])
    attacker = _attacker(place=sq, enemy_checker=lambda t: True)
    assert attacker._resolve_damage_target(wall) is wall
    assert attacker._resolve_inside_attack_target(enemy) is None


def test_ranged_can_reach_open_container_passengers():
    sq = _square("a1", neighbors=[])
    far = _square("b1")
    sq.neighbors.append(far)
    wall = _wall(place=sq, chance=40)
    attacker = _attacker(place=far, enemy_checker=lambda t: True)
    attacker._attacker_near_container = lambda c: False
    attacker._near_enough_to_aim = lambda c: True
    assert attacker._attacker_can_reach_container_passengers(wall)


def test_inside_terrain_delegates_to_container_square():
    sq = _square("a1")
    sq.type_name = "wall_terrain"
    sq.terrain_cover = (3, 1)
    wall = _wall(place=sq, chance=40)
    inside = wall.inside
    assert inside.type_name == "wall_terrain"
    assert inside.terrain_cover == (3, 1)
    assert inside.terrain_cover_at(0, 0) == (3, 1)


def test_open_container_visibility_from_neighbors():
    a1 = _square("a1")
    b1 = _square("b1")
    a1.neighbors.append(b1)
    b1.neighbors.append(a1)
    archer = types.SimpleNamespace(is_inside=True, hp=100)
    wall = _wall(place=a1, chance=40, passengers=[archer])
    assert is_open_container(wall)
    assert container_visible_from_place(wall, a1)
    assert container_visible_from_place(wall, b1)
    assert inside_unit_visible_from_place(archer, b1)
