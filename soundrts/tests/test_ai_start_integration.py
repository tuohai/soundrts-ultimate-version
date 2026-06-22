"""Integration: Computer applies ai.txt starting_resources on populate_map."""
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
        from soundrts.lib.nofloat import to_int
        from soundrts.world import World
        from soundrts.worldclient import DirectClient, DummyClient
        from soundrts.worldplayercomputer import Computer
    finally:
        sys.argv = saved_argv


JL1 = """
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
starting_resources 10 10
"""


@pytest.fixture(autouse=True)
def load_rules():
    res.load_rules_and_ai()


def test_nightmare_computer_gets_resource_bonus():
    world = World([], 42)
    world._parse_map(JL1)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = rules_faction()
    ai = DummyClient("nightmare")
    ai.faction = rules_faction()
    ai.alliance = "2"

    world.populate_map([human, ai], random_starts=False)

    computer = next(p for p in world.players if isinstance(p, Computer))
    assert computer.resources[0] == to_int("10") + to_int("400")
    assert computer.resources[1] == to_int("10") + to_int("400")
    assert computer.population >= 60


def rules_faction():
    from soundrts.definitions import rules

    return rules.factions[0] if rules.factions else "human_faction"
