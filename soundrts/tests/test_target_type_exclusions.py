"""目标类型排除语法（-tag）测试。"""
from __future__ import annotations

import types

from soundrts.worldunit.world_public_method import (
    has_target_type,
    matches_attack_targets,
    matches_heal_targets,
    passes_harm_diplomacy_filter,
    skill_can_harm,
    split_target_tags,
)


def _unit(**kw):
    defaults = dict(
        type_name="footman",
        is_a_unit=True,
        is_a_building=False,
        airground_type="ground",
        is_healable=True,
        is_undead=False,
        is_vulnerable=True,
        hp=100,
    )
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


class _StubPlayer:
    def __init__(self, pid, neutral=False):
        self.id = pid
        self.neutral = neutral

    def player_is_an_enemy(self, other):
        return other is not None and other.id != self.id

    def player_is_a_hostile_enemy(self, other):
        if other is None or getattr(other, "neutral", False):
            return False
        return self.player_is_an_enemy(other)


def test_split_target_tags():
    assert split_target_tags(["enemy", "-building", "ground"]) == (
        ["enemy", "ground"],
        ["building"],
    )


def test_has_target_type_excludes_building():
    soldier = _unit()
    building = _unit(type_name="house", is_a_building=True, is_a_unit=False)
    assert has_target_type(soldier, ["-building"]) is True
    assert has_target_type(building, ["-building"]) is False


def test_has_target_type_ground_but_not_building():
    soldier = _unit()
    building = _unit(type_name="house", is_a_building=True, is_a_unit=False)
    tags = ["ground", "-building"]
    assert has_target_type(soldier, tags) is True
    assert has_target_type(building, tags) is False


def test_has_target_type_buff_target_type():
    undead = _unit(is_undead=True)
    living = _unit(is_undead=False)
    assert has_target_type(undead, ["unit", "-undead"]) is False
    assert has_target_type(living, ["unit", "-undead"]) is True


def test_matches_attack_targets_excludes_building():
    soldier = _unit()
    building = _unit(type_name="house", is_a_building=True, is_a_unit=False)
    assert matches_attack_targets(soldier, ["-building"], "ground") is True
    assert matches_attack_targets(building, ["-building"], "ground") is False


def test_matches_attack_targets_ground_or_air_excluding_building():
    air = _unit(airground_type="air")
    building = _unit(type_name="house", is_a_building=True, is_a_unit=False)
    tags = ["ground", "air", "-building"]
    assert matches_attack_targets(air, tags, "air") is True
    assert matches_attack_targets(building, tags, "ground") is False


def test_harm_diplomacy_excludes_enemy():
    hero = _StubPlayer("hero")
    enemy = _StubPlayer("enemy")
    neutral = _StubPlayer("neutral", neutral=True)
    assert passes_harm_diplomacy_filter(["-enemy"], hero, neutral) is True
    assert passes_harm_diplomacy_filter(["-enemy"], hero, enemy) is False


def test_skill_can_harm_excludes_building_for_push_like_skill():
    class _Skill:
        harm_target_type = ["enemy", "-building"]

    hero = _StubPlayer("hero")
    enemy = _StubPlayer("enemy")
    caster = types.SimpleNamespace(
        player=hero,
        is_an_enemy=lambda u: u.player is enemy,
    )
    soldier = _unit(player=enemy)
    building = _unit(
        player=enemy, type_name="house", is_a_building=True, is_a_unit=False
    )
    assert skill_can_harm(caster, _Skill, soldier) is True
    assert skill_can_harm(caster, _Skill, building) is False


def test_matches_heal_targets_excludes_undead():
    living = _unit(is_undead=False)
    undead = _unit(is_undead=True)
    assert matches_heal_targets(living, ["unit", "-undead"]) is True
    assert matches_heal_targets(undead, ["unit", "-undead"]) is False


def test_matches_heal_targets_ground_only():
    ground = _unit(airground_type="ground")
    air = _unit(airground_type="air")
    water = _unit(airground_type="water")
    assert matches_heal_targets(ground, ["ground"]) is True
    assert matches_heal_targets(air, ["ground"]) is False
    assert matches_heal_targets(water, ["ground"]) is False
    assert matches_heal_targets(water, ["water"]) is True


def test_can_heal_uses_heal_target_type_exclusions():
    from soundrts.tests.test_wuxia_skills import _StubPlayer
    from soundrts.worldunit.world_status_update import CreatureStatusUpdate

    class _Healer:
        heal_target_type = ["unit", "-undead"]

        def __init__(self, player):
            self.player = player

    hero = _StubPlayer("hero")
    healer = _Healer(hero)
    living = _unit(player=hero, is_undead=False)
    undead = _unit(player=hero, is_undead=True)

    assert CreatureStatusUpdate._can_heal(healer, living) is True
    assert CreatureStatusUpdate._can_heal(healer, undead) is False
