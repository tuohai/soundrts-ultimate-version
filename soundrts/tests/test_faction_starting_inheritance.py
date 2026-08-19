"""Faction/race ``is_a`` inheritance for starting_resources / starting_units."""
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
        from soundrts.definitions import Rules
        from soundrts.lib.nofloat import to_int
        from soundrts.lib.resource import res
        from soundrts.world import World
        from soundrts.worldclient import DirectClient, DummyClient
    finally:
        sys.argv = saved_argv


SAMPLE = """
def parameters
nb_of_resource_types 4

def Civilization
class race
abstract 1
starting_resources 100 200 200 200
starting_units townhall house peasant

def chinese
class race
is_a Civilization
starting_units townhall 3 house 6 peasant

def britons
class race
is_a Civilization
peasant peasant

def Mid
starting_units townhall 2 peasant

def Leaf
class race
is_a Mid
is_a Civilization
"""


def test_is_a_inherits_starting_and_allows_override():
    r = Rules()
    r.load(SAMPLE)
    assert "Civilization" not in r.factions
    assert set(r.factions) >= {"chinese", "britons", "Leaf"}
    assert r.get("britons", "starting_resources") == ["100", "200", "200", "200"]
    assert r.get("britons", "starting_units") == ["townhall", "house", "peasant"]
    assert r.get("chinese", "starting_resources") == ["100", "200", "200", "200"]
    assert r.get("chinese", "starting_units") == [
        "townhall",
        "3",
        "house",
        "6",
        "peasant",
    ]
    # Chain: Mid units override Civilization units; resources still from Civilization.
    assert r.get("Leaf", "starting_units") == ["townhall", "2", "peasant"]
    assert r.get("Leaf", "starting_resources") == ["100", "200", "200", "200"]
    assert r._dict["britons"].get("abstract") is None


@pytest.mark.skipif(not Path("mods/aoe2/rules.txt").is_file(), reason="aoe2 missing")
def test_aoe2_civilization_inheritance_and_jl1_resources(monkeypatch):
    from soundrts import config

    monkeypatch.setattr(config, "mods", "aoe2")
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    from soundrts.definitions import rules

    assert "Civilization" not in rules.factions
    assert "britons" in rules.factions
    assert rules.get("britons", "starting_units") == [
        "town_center",
        "3",
        "peasant",
        "scout_cavalry",
    ]
    assert rules.get("chinese", "starting_units") == [
        "town_center",
        "6",
        "peasant",
        "scout_cavalry",
    ]
    assert rules.get("chinese", "starting_resources") == ["100", "150", "0", "200"]
    assert rules.get("franks", "starting_resources") == ["100", "200", "200", "200"]

    jl1 = Path("mods/aoe2/multi/jl1.txt").read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(jl1)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    ai = DummyClient("beginner")
    ai.faction = "franks"
    ai.alliance = "2"

    parsed = []
    orig = world.parse_start

    def peek(start, faction, eq):
        result = orig(start, faction, eq)
        parsed.append((faction, start[1], result[0], result[3]))
        return result

    world.parse_start = peek
    world.populate_map([human, ai], random_starts=False)

    briton_parse = next(p for p in parsed if p[0] == "britons")
    names = {
        getattr(u[1], "type_name", None): u[2] for u in briton_parse[1]
    }
    assert names.get("peasant") == 3
    assert names.get("scout_cavalry") == 1
    assert "house" not in names
    assert briton_parse[3][0] == to_int("100")
    briton = next(p for p in world.players if getattr(p, "faction", None) == "britons")
    assert [round(x / 1000) for x in briton.resources] == [100, 200, 200, 200]
