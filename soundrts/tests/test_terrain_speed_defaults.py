"""Terrain speed: rules default, map override, editor palette inheritance."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.clientgame import load_palette
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.editor_palette import apply_palette_to_square
from soundrts.lib.square_terrain_rules import (
    DEFAULT_TERRAIN_SPEED,
    parse_terrain_speed_pair,
    resolve_terrain_speed,
    terrain_default_speed,
)
from soundrts.world import World


@pytest.fixture(autouse=True)
def _load_rules():
    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )


def test_parse_terrain_speed_pair():
    assert parse_terrain_speed_pair([".5", "1"]) == (50, 100)
    assert parse_terrain_speed_pair(["0", ".25"]) == (0, 25)


def test_ford_default_speed_from_rules():
    assert terrain_default_speed("ford") == (50, 100)
    assert terrain_default_speed("plain") is None


def test_resolve_terrain_speed_priority():
    assert resolve_terrain_speed("ford", (100, 100)) == (100, 100)
    assert resolve_terrain_speed("ford", None) == (50, 100)
    assert resolve_terrain_speed(None, None) == DEFAULT_TERRAIN_SPEED


def _build_map(text: str):
    world = World([], 42)
    world._parse_map(text)
    world._build_map()
    return world


def test_map_terrain_ford_uses_rules_speed_without_speed_line():
    world = _build_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain ford 1,1
"""
    )
    assert world.grid["0,0"].terrain_speed == (50, 100)


def test_map_speed_line_overrides_rules_default():
    world = _build_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain ford 1,1
speed 1 1 1,1
"""
    )
    assert world.grid["0,0"].terrain_speed == (100, 100)


def test_load_palette_inherits_ford_speed_from_rules():
    entry = next(e for name, e in load_palette() if name == "ford")
    assert entry["speed"] == (50, 100)


def test_apply_palette_ford_matches_rules_speed():
    world = _build_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
"""
    )
    sq = world.grid["0,0"]
    entry = next(e for name, e in load_palette() if name == "ford")
    apply_palette_to_square(sq, entry)
    assert sq.terrain_speed == (50, 100)
