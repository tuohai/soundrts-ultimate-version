import types
from pathlib import Path

import pytest

from soundrts.clientgame import load_palette
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.editor_palette import apply_palette_to_square
from soundrts.worldroom import Square


def _load_default_rules():
    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )


def _palette_entry(name):
    for key, entry in load_palette():
        if key == name:
            return entry
    raise KeyError(name)


@pytest.mark.parametrize(
    "name,expected_style",
    [
        ("forest", "forest"),
        ("dense_forest", "dense_forest"),
        ("lake", "lake"),
        ("rocky_plain", "rocky_plain"),
    ],
)
def test_load_palette_uses_new_terrain_names(name, expected_style):
    entry = _palette_entry(name)
    assert entry["style"] == expected_style


def test_apply_palette_lake_sets_fixed_terrain():
    _load_default_rules()
    from soundrts.world import World

    world = World([], 42)
    world._parse_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
"""
    )
    world._create_squares_and_grid()
    sq = world.grid["0,0"]
    apply_palette_to_square(sq, _palette_entry("lake"))
    assert sq.fixed_terrain is True
    assert sq.type_name == "lake"
    assert sq.is_water
    assert not sq.is_ground


def test_apply_palette_forest_spawns_woods_and_dynamic_terrain():
    _load_default_rules()
    from soundrts.world import World

    world = World([], 42)
    world._parse_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
"""
    )
    world._create_squares_and_grid()
    sq = world.grid["0,0"]
    apply_palette_to_square(sq, _palette_entry("forest"))
    assert sq.fixed_terrain is False
    assert len([o for o in sq.objects if o.type_name == "wood"]) == 3
    assert sq.type_name == "forest"


def test_apply_palette_dense_forest_spawns_seven_woods():
    _load_default_rules()
    from soundrts.world import World

    world = World([], 42)
    world._parse_map(
        """
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
"""
    )
    world._create_squares_and_grid()
    sq = world.grid["0,0"]
    apply_palette_to_square(sq, _palette_entry("dense_forest"))
    assert sq.fixed_terrain is False
    assert len([o for o in sq.objects if o.type_name == "wood"]) == 7
    assert sq.type_name == "dense_forest"


def test_apply_palette_rocky_plain_locks_without_objects():
    _load_default_rules()
    sq = object.__new__(Square)
    sq.objects = []
    sq.type_name = ""
    sq.high_ground = False
    sq.is_water = False
    sq.is_ground = True
    sq.is_air = True
    sq.fixed_terrain = False
    sq.strict_neighbors = []
    sq.world = types.SimpleNamespace(nb_columns=2, nb_lines=2)
    sq.x = sq.y = 0
    sq.xmin = sq.ymin = 0
    sq.xmax = sq.ymax = 12000
    sq.col = sq.row = 0
    apply_palette_to_square(sq, _palette_entry("rocky_plain"))
    assert sq.fixed_terrain is True
    assert sq.type_name == "rocky_plain"
