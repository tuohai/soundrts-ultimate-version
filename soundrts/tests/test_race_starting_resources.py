"""Race/faction starting_resources apply when the map omits them."""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from soundrts.lib.nofloat import to_int
        from soundrts.lib.resource import res
        from soundrts.world import World
        from soundrts.worldclient import DirectClient, DummyClient
    finally:
        sys.argv = saved_argv


MAP_NO_STARTING_RESOURCES = """
title 1
square_width 12
nb_columns 3
nb_lines 4
west_east_paths 1,1 2,1 1,2 2,2 1,3 2,3 1,4 2,4
south_north_paths 2,2
nb_players_min 2
nb_players_max 2
starting_squares 2,1 2,4
starting_units townhall house peasant
"""

AOE2_JL1 = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "multi" / "jl1.txt"


@pytest.fixture
def aoe2_rules(monkeypatch):
    from soundrts import config

    monkeypatch.setattr(config, "mods", "aoe2")
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    yield
    monkeypatch.setattr(config, "mods", "")
    res.set_mods("")
    res.load_rules_and_ai()


def test_parse_map_leaves_starting_resources_empty_until_defined():
    res.load_rules_and_ai()
    world = World([], 42)
    world._parse_map(MAP_NO_STARTING_RESOURCES)
    assert world.map_defined_starting_resources is False
    assert world.players_starts[0][0] == []


@pytest.mark.skipif(not AOE2_JL1.is_file(), reason="aoe2 mod not present")
def test_aoe2_jl1_uses_race_starting_resources(aoe2_rules):
    from soundrts.definitions import rules

    assert rules.get("britons", "starting_resources") == ["100", "200", "200", "200"]
    jl1 = AOE2_JL1.read_text(encoding="utf-8")
    active = [
        line.split()[0]
        for line in jl1.splitlines()
        if line.strip() and not line.strip().startswith(";")
    ]
    assert "starting_resources" not in active

    world = World([], 42)
    world._parse_map(jl1)
    assert world.map_defined_starting_resources is False
    assert world.players_starts[0][0] == []
    world._build_map()

    human = DirectClient("p1", None)
    human.faction = "britons"
    ai = DummyClient("beginner")
    ai.faction = "franks"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)

    human_player = next(p for p in world.players if getattr(p, "faction", None) == "britons")
    assert [round(x / 1000) for x in human_player.resources] == [100, 200, 200, 200]
    assert human_player.resources[0] == to_int("100")


MAP_SQUARES_ONLY = """
title 1
square_width 12
nb_columns 3
nb_lines 3
west_east_paths 1,1 2,1 1,2 2,2 1,3 2,3
nb_players_min 1
nb_players_max 4
starting_squares a1 c1 a3 c3
"""


def test_starting_squares_kept_when_map_has_no_units():
    res.load_rules_and_ai()
    from soundrts.world.world_core import start_slot_square

    world = World([], 42)
    world._parse_map(MAP_SQUARES_ONLY)
    assert world.starting_squares == ["0,0", "2,0", "0,2", "2,2"]
    assert [start_slot_square(slot) for slot in world.players_starts] == world.starting_squares
    assert all(slot[1] == [] for slot in world.players_starts)


def _briton_start_square(world, human, ai, random_starts=True):
    assigned = []
    orig = world.parse_start

    def peek(start, faction, eq):
        result = orig(start, faction, eq)
        if faction == "britons" and result[0]:
            assigned.append(result[0][0][0].name)
        return result

    world.parse_start = peek
    world.populate_map([human, ai], random_starts=random_starts)
    assert assigned, "britons start was not parsed"
    return assigned[0]


@pytest.mark.skipif(not AOE2_JL1.is_file(), reason="aoe2 mod not present")
def test_aoe2_jl1_faction_defaults_follow_shuffled_starting_squares(aoe2_rules):
    jl1 = AOE2_JL1.read_text(encoding="utf-8")
    parsed = World([], 0)
    parsed._parse_map(jl1)
    allowed = set(parsed.starting_squares)
    seen = set()
    for seed in range(16):
        world = World([], seed)
        world._parse_map(jl1)
        world._build_map()
        human = DirectClient("p1", None)
        human.faction = "britons"
        ai = DummyClient("beginner")
        ai.faction = "franks"
        ai.alliance = "2"
        seen.add(_briton_start_square(world, human, ai))
    assert seen <= allowed
    assert len(seen) > 1


@pytest.mark.skipif(not AOE2_JL1.is_file(), reason="aoe2 mod not present")
def test_aoe2_jl1_sequential_uses_first_starting_square(aoe2_rules):
    jl1 = AOE2_JL1.read_text(encoding="utf-8")
    world = World([], 7)
    world._parse_map(jl1)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    ai = DummyClient("beginner")
    ai.faction = "franks"
    ai.alliance = "2"
    assert _briton_start_square(world, human, ai, random_starts=False) == world.starting_squares[0]
