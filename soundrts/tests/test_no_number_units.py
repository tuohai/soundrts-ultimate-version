"""no_number 1 — 同类型仅 1 个时不报序号；默认单位始终报序号。"""
from __future__ import annotations

from pathlib import Path

import soundrts.worldunit  # noqa: F401

from soundrts.worldplayerbase.base import Player
from soundrts.worldunit.worldcreature import Creature


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def unit_has_no_number(model):
    return bool(getattr(model, "no_number", 0))


def count_player_units_of_type(player, type_name):
    if not player:
        return 0
    return sum(
        1
        for u in player.units
        if getattr(u, "type_name", None) == type_name and getattr(u, "presence", True)
    )


def unit_should_show_number(model):
    if not getattr(model, "number", 0):
        return False
    if not unit_has_no_number(model):
        return True
    player = getattr(model, "player", None)
    type_name = getattr(model, "type_name", None)
    if not player or not type_name:
        return False
    return count_player_units_of_type(player, type_name) > 1


def summary_omit_single_count(model):
    if not unit_has_no_number(model):
        return False
    return not unit_should_show_number(model)


class _StubWorld:
    time = 0


def _make_player() -> Player:
    p = Player.__new__(Player)
    p.neutral = False
    p.units = []
    p.population = 0
    p.used_population = 0
    p.world = _StubWorld()
    p.allied = []
    p._cached_allied_vision = []
    p._allied_vision_cache_time = 0
    return p


def _make_creature_unit(player: Player, type_name: str = "test_creature", **attrs) -> Creature:
    u = Creature.__new__(Creature)
    u.player = player
    u.type_name = type_name
    u.number = 0
    u.presence = True
    u.ai_mode = "offensive"
    u.counterattack_enabled = False
    u.last_attacker = None
    u.population_provided = 0
    u.population_cost = 0
    u.action_target = None
    for key, value in attrs.items():
        setattr(u, key, value)
    return u


def test_no_number_in_definitions():
    src = _source("soundrts", "definitions.py")
    assert '"no_number"' in src


def test_default_unit_always_shows_number():
    player = _make_player()
    a = _make_creature_unit(player, type_name="peasant", number=1)
    player.units = [a]

    assert unit_should_show_number(a) is True
    assert summary_omit_single_count(a) is False


def test_no_number_single_unit_hides_number():
    player = _make_player()
    a = _make_creature_unit(player, type_name="guan_yu", number=1, no_number=1)
    player.units = [a]

    assert unit_should_show_number(a) is False
    assert summary_omit_single_count(a) is True


def test_no_number_multiple_units_show_number():
    player = _make_player()
    a = _make_creature_unit(player, type_name="guan_yu", number=1, no_number=1)
    b = _make_creature_unit(player, type_name="guan_yu", number=2, no_number=1)
    player.units = [a, b]

    assert unit_should_show_number(a) is True
    assert unit_should_show_number(b) is True
    assert summary_omit_single_count(a) is False


def test_title_gates_on_no_number():
    src = _source("soundrts", "clientgameentity", "properties.py")
    assert "def unit_has_no_number(model):" in src
    assert "if not unit_has_no_number(model):" in src
    assert "if self.number and unit_should_show_number(self.model):" in src


def test_summary_only_omits_for_no_number():
    src = _source("soundrts", "clientgame", "game_unit_control.py")
    assert "summary_omit_single_count" in src
    assert "if omit_single_count and count == 1:" in src


def test_player_add_always_assigns_numbers():
    player = _make_player()
    hero = _make_creature_unit(player, type_name="guan_yu", no_number=1)
    soldier = _make_creature_unit(player, type_name="footman")

    player.add(hero)
    player.add(soldier)

    assert hero.number == 1
    assert soldier.number == 1
