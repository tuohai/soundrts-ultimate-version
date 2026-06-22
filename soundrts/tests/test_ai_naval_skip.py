"""Tests for AI skipping naval units on land-only maps."""
from __future__ import annotations

import types

from soundrts.definitions import rules
from soundrts.worldplayercomputer import Computer


def _make_computer(*, water_squares=frozenset()):
    world = types.SimpleNamespace(
        water_squares=set(water_squares),
        squares=[],
        players=[],
        turn=0,
        time=0,
        population_limit=80,
        random=types.SimpleNamespace(choice=lambda x: x[0], shuffle=lambda x: None),
    )
    client = types.SimpleNamespace(
        neutral=False,
        AI_type="intermediate",
        faction=rules.factions[0] if rules.factions else "human_faction",
    )
    player = Computer.__new__(Computer)
    player.world = world
    player.client = client
    player.units = []
    player._orders = {}
    player._attacked_places = []
    player._previous_choose = {}
    player.neutral = False
    player.allied = []
    player.number = 2
    player._plan = []
    player._line_nb = 0
    player._safe_cnt = 0
    player.equivalent = lambda name: name
    player.nb = lambda *args, **kwargs: 0
    player.future_nb = lambda *args, **kwargs: 0
    return player


def test_map_has_water_detects_water_squares():
    ai = _make_computer(water_squares={("1", "2")})
    assert ai._map_has_water()
    ai = _make_computer()
    assert not ai._map_has_water()


def test_type_needs_water_for_naval_types():
    ai = _make_computer()
    assert ai._type_needs_water("boat")
    assert ai._type_needs_water("shipyard")
    assert not ai._type_needs_water("footman")


def test_get_skips_naval_on_land_only_map():
    ai = _make_computer()
    called = []

    def fake_get(nb, types):
        called.append(types)
        return False

    ai._get = fake_get
    assert ai.get(2, "boat") is True
    assert called == []


def test_get_boat_on_water_map_calls_internal_get():
    ai = _make_computer(water_squares={("3", "3")})
    called = []

    def fake_get(nb, types):
        called.append(types)
        return False

    ai._get = fake_get
    assert ai.get(2, "boat") is False
    assert len(called) == 1
