"""ai.txt starting_resources / starting_units for computer AI."""
from __future__ import annotations

import types

import pytest

from soundrts import definitions
from soundrts.definitions import (
    DEFAULT_AI_DEFEAT_SCORE,
    filter_ai_executable_plan,
    get_ai_defeat_score,
    load_ai,
    parse_ai_start_settings,
)
from soundrts.worldplayercomputer import Computer


@pytest.fixture
def isolated_ai(monkeypatch):
    fresh = {}
    monkeypatch.setattr(definitions, "_ai", fresh)
    return fresh


def test_parse_ai_start_settings(isolated_ai):
    load_ai("""
        def expert
        starting_resources 200 150
        starting_units 3 footman 2 archer
        workers 20
        attack
    """)
    bonus, units, population = parse_ai_start_settings("expert")
    assert bonus[:2] == [200 * 1000, 150 * 1000]
    assert units == ["3", "footman", "2", "archer"]
    assert population == 0


def test_parse_ai_start_settings_population(isolated_ai):
    load_ai("""
        def expert
        starting_population 60
        attack
    """)
    bonus, units, population = parse_ai_start_settings("expert")
    assert bonus is None
    assert units == []
    assert population == 60


def test_filter_ai_executable_plan_drops_start_directives():
    lines = [
        "starting_resources 100 100",
        "workers 12",
        "starting_units 2 knight",
        "starting_population 40",
        "defeat_score 25",
        "attack",
    ]
    assert filter_ai_executable_plan(lines) == ["workers 12", "attack"]


def test_get_ai_defeat_score_default_for_builtin_tier(isolated_ai):
    load_ai("""
        def beginner
        attack
    """)
    assert get_ai_defeat_score("beginner") == DEFAULT_AI_DEFEAT_SCORE["beginner"]


def test_get_ai_defeat_score_custom_in_ai_txt(isolated_ai):
    load_ai("""
        def beginner
        defeat_score 15
        attack
    """)
    assert get_ai_defeat_score("beginner") == 15


def test_get_ai_defeat_score_custom_mod_ai(isolated_ai):
    load_ai("""
        def tang_hard
        defeat_score 55
        attack
    """)
    assert get_ai_defeat_score("tang_hard") == 55


def test_get_ai_defeat_score_unknown_mod_ai_without_directive(isolated_ai):
    load_ai("""
        def tang_hard
        attack
    """)
    assert get_ai_defeat_score("tang_hard") == 0


def test_get_ai_defeat_score_zero_disables_bonus(isolated_ai):
    load_ai("""
        def beginner
        defeat_score 0
        attack
    """)
    assert get_ai_defeat_score("beginner") == 0


class _FakeWorld:
    starting_squares = ["a1"]
    squares = []

    def __init__(self):
        self.grid = {"a1": _FakePlace()}
        self.squares = [self.grid["a1"]]


class _FakePlace:
    pass


class _FakeUnit:
    def __init__(self, place):
        self.place = place


class _Footman:
    type_name = "footman"


class _Archer:
    type_name = "archer"


def test_computer_applies_ai_start_bonus(monkeypatch, isolated_ai):
    load_ai("""
        def nightmare
        starting_resources 50 25
        starting_units 2 footman 1 archer
        starting_population 30
        goto -1
    """)
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.rules.unit_class",
        lambda name: {"footman": _Footman, "archer": _Archer}.get(name),
    )
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.is_an_upgrade",
        lambda cls: False,
    )

    c = Computer.__new__(Computer)
    c.AI_type = "nightmare"
    c.neutral = False
    c.faction = "human_faction"
    c.world = _FakeWorld()
    c.number = 1
    c.units = [_FakeUnit(_FakeWorld().grid["a1"])]
    c.resources = [100 * 1000, 100 * 1000, 0]
    c.population = 5
    c.stats = types.SimpleNamespace(add=lambda *a, **k: None)
    c.upgrades = []
    c.forbidden_techs = []
    c.client = types.SimpleNamespace()
    added = []

    def equivalent(name):
        return name

    def add_unit(cls, place, population_cost=None):
        added.append((cls.type_name, place, population_cost))

    c.equivalent = equivalent
    c.add_unit = add_unit
    c.faction_ai_type = lambda ai_type: ai_type

    c._apply_ai_start_settings()

    assert c.resources[0] == 150 * 1000
    assert c.resources[1] == 125 * 1000
    assert c.population == 35
    assert [entry[0] for entry in added] == ["footman", "footman", "archer"]
    assert all(entry[2] == 0 for entry in added)
