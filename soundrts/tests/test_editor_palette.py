import os
import types
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.clientgame import load_palette
from soundrts.clientgame.game_resources import _execute_command
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


_TINY_MAP = """
nb_columns 3
nb_lines 3
nb_players_min 1
nb_players_max 1
starting_squares 2,2
"""


def _tiny_world():
    from soundrts.world import World

    world = World([], 42)
    world._parse_map(_TINY_MAP)
    world._create_squares_and_grid()
    return world


def _editor_interface(square, world):
    return types.SimpleNamespace(
        place=square,
        world=world,
        zoom_mode=False,
        _terrain_noises=[],
    )


@patch("soundrts.clientgame.game_resources.voice.item")
def test_console_st_cycles_every_palette_entry(voice_item):
    _load_default_rules()
    pal = load_palette()
    names = [k for k, _ in pal]
    assert names, "editor_palette.txt must load"
    interface = _editor_interface(_tiny_world().grid["1,1"], None)
    spoken = []
    voice_item.side_effect = lambda msg: spoken.append(msg)
    for _ in names:
        _execute_command(interface, "st 1")
    cycled = [msg[0] for msg in spoken]
    assert cycled == names


@patch("soundrts.clientgame.game_resources.voice.item")
def test_console_st_at_applies_every_palette_entry(voice_item):
    _load_default_rules()
    pal = load_palette()
    world = _tiny_world()
    sq = world.grid["1,1"]
    interface = _editor_interface(sq, world)
    voice_item.side_effect = lambda msg: None
    for name, entry in pal:
        _execute_command(interface, "st %s" % name)
        _execute_command(interface, "at")
        style = entry["style"]
        assert bool(sq.is_water) is bool(entry["water"]), name
        assert bool(sq.is_ground) is bool(entry["ground"]), name
        assert bool(sq.is_air) is bool(entry["air"]), name
        assert bool(sq.high_ground) is bool(entry["high_ground"]), name
        woods = [o for o in sq.objects if getattr(o, "type_name", None) == "wood"]
        gold = [o for o in sq.objects if getattr(o, "type_name", None) == "goldmine"]
        assert len(woods) == entry["woods"][0], name
        assert len(gold) == entry["goldmines"][0], name
        if name in ("goldmine", "high_goldmine"):
            # Brush style is meadows, but one wood makes object-driven forest.
            assert sq.type_name in ("forest", "meadows"), name
        else:
            assert sq.type_name == style, name
        if name == "forest":
            assert sq.fixed_terrain is False
        if name == "lake":
            assert sq.fixed_terrain is True
    _execute_command(interface, "st lake")
    _execute_command(interface, "at")
    assert sq.is_water
    _execute_command(interface, "st forest")
    _execute_command(interface, "at")
    woods = [o for o in sq.objects if getattr(o, "type_name", None) == "wood"]
    assert len(woods) == 3
    assert not sq.is_water
    assert sq.type_name == "forest"


@patch("soundrts.clientgame.game_resources.voice.item")
def test_console_at_without_st_beeps(voice_item):
    from soundrts import msgparts as mp

    _load_default_rules()
    world = _tiny_world()
    interface = _editor_interface(world.grid["1,1"], world)
    _execute_command(interface, "at")
    voice_item.assert_called_with(mp.BEEP)
