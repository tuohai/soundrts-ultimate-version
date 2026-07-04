"""Ground region flood-fill must connect ford/bridge tiles to adjacent land."""
from __future__ import annotations

import os
import types
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.lib.resource import res
from soundrts.lib.square_terrain_rules import squares_same_ground_region
from soundrts.world import World
from soundrts.worldclient import DummyClient


ROOT = Path(__file__).resolve().parents[2]
CH2 = ROOT / "res" / "single" / "The Legend of Raynor" / "2.txt"


@pytest.fixture(autouse=True)
def _load_rules():
    res.load_rules_and_ai()


def _sq(world, label: str):
    col = ord(label[0]) - ord("a")
    row = int(label[1:]) - 1
    return world.grid[f"{col},{row}"]


def _build_ch2_world():
    world = World([], 42)
    world._parse_map(CH2.read_text(encoding="utf-8"))
    world._build_map()
    client = DummyClient(alliance=1)
    client.create_player(world)
    return world


def test_squares_same_ground_region_ford_and_land():
    ford = types.SimpleNamespace(is_water=True, is_ground=True)
    land = types.SimpleNamespace(is_water=False, is_ground=True)
    river = types.SimpleNamespace(is_water=True, is_ground=False)
    assert squares_same_ground_region(ford, land)
    assert not squares_same_ground_region(ford, river)
    assert not squares_same_ground_region(land, river)


def test_ch2_ford_shares_ground_region_with_a3():
    world = _build_ch2_world()
    a2 = _sq(world, "a2")
    a3 = _sq(world, "a3")
    assert a2.is_water and a2.is_ground
    assert not a3.is_water and a3.is_ground
    assert getattr(a2, "region", None) is getattr(a3, "region", None)


def test_ch2_shortest_path_from_ford_to_a3():
    world = _build_ch2_world()
    a2 = _sq(world, "a2")
    a3 = _sq(world, "a3")
    nxt = a2.shortest_path_to(a3)
    assert nxt is not None
    assert nxt.other_side.place is a3
