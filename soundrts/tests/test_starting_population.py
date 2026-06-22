"""Map and per-slot starting_population bonus."""
from __future__ import annotations

import os
import sys
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    try:
        from soundrts.lib.resource import res
        from soundrts.world import World
        from soundrts.worldclient import DirectClient
        from soundrts.world.world_core import start_population_bonus
    finally:
        sys.argv = saved_argv


MAP = """
title 1
square_width 12
nb_columns 3
nb_lines 3
west_east_paths 1,1 2,1 1,2 2,2 1,3 2,3
nb_players_min 1
nb_players_max 1
starting_squares 2,2
starting_units townhall
starting_resources 0 0
starting_population 25
"""


@pytest.fixture(autouse=True)
def load_rules():
    res.load_rules_and_ai()


def test_map_parses_starting_population():
    world = World([], 42)
    world._parse_map(MAP)
    assert world.starting_population == 25
    assert world.map_defined_starting_population is True
    assert len(world.players_starts) == 1
    assert start_population_bonus(world.players_starts[0]) == 25


def test_player_gets_map_starting_population():
    world = World([], 42)
    world._parse_map(MAP)
    world._build_map()
    client = DirectClient("p1", None)
    client.faction = rules_faction()
    world.populate_map([client], random_starts=False)
    player = world.players[0]
    assert player.population >= 25


def rules_faction():
    from soundrts.definitions import rules

    return rules.factions[0] if rules.factions else "human_faction"
