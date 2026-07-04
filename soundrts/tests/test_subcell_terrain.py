"""Tests for sub-cell terrain within a map square."""

import types

import pytest

from soundrts.lib.subcell_terrain import (
    format_subcell_suffix,
    parse_location_token,
    subcell_index,
)
from soundrts.worldroom import Square


class _MiniWorld:
    def __init__(self):
        self.squares = []
        self.objects = {}
        self._next_id = 1
        self.grid = {}
        self.square_cities = {}
        self.square_districts = {}
        self.square_names = {}

    def get_next_id(self):
        self._next_id += 1
        return self._next_id


def _make_square(col=0, row=0, width=12):
    world = _MiniWorld()
    sq = Square(world, col, row, width)
    return sq


def test_parse_location_token_square_only():
    assert parse_location_token("0,0") == ("0,0", None)
    assert parse_location_token("a1/2,3") == ("a1", (1, 2))


def test_parse_location_token_invalid_subcell():
    with pytest.raises(ValueError):
        parse_location_token("a1/0,1")
    with pytest.raises(ValueError):
        parse_location_token("a1/21,1")


def test_subcell_precision_20_token():
    square_key, cell = parse_location_token("a1/20,20")
    assert square_key == "a1"
    assert cell == (19, 19)


def test_subcell_index_corners():
    sq = _make_square()
    assert subcell_index(sq, sq.xmin, sq.ymin) == (0, 0)
    assert subcell_index(sq, sq.xmax - 1, sq.ymax - 1) == (2, 2)


def test_subcell_high_ground_override():
    sq = _make_square()
    sq.high_ground = False
    sq.subcells.set_high_ground(1, 1, True)
    cx = sq.xmin + (sq.xmax - sq.xmin) // 6 * 3 + 1
    cy = sq.ymin + (sq.ymax - sq.ymin) // 6 * 3 + 1
    assert sq.high_ground_at(cx, cy) is True
    assert sq.high_ground_at(sq.xmin + 1, sq.ymin + 1) is False


def test_square_terrain_uses_subcell_high_ground_for_voice():
    from soundrts.clientgame.game_navigation import _square_terrain

    sq = _make_square()
    sq.high_ground = False
    sq.fixed_terrain = False
    sq.world = types.SimpleNamespace()
    sq.subcells.set_high_ground(0, 0, True)

    high_msgs = _square_terrain(sq, sq.xmin + 1, sq.ymin + 1)
    low_msgs = _square_terrain(sq, sq.xmax - 2, sq.ymax - 2)
    assert 5698 in high_msgs or "5698" in high_msgs
    assert 5698 not in low_msgs and "5698" not in low_msgs
    assert 4314 not in high_msgs and "4314" not in high_msgs
    assert 5696 not in low_msgs and "5696" not in low_msgs


def test_subcell_mountain_blocks_ground():
    sq = _make_square()
    sq.subcells.set_type_name(0, 0, "mountain")
    sq.subcells.set_is_ground(0, 0, False)
    sq.subcells.set_is_air(0, 0, False)

    class _Unit:
        airground_type = "ground"

    x = sq.xmin + 1
    y = sq.ymin + 1
    assert sq.is_passable_for(_Unit(), x, y) is False
    assert sq.is_passable_for(_Unit(), sq.xmax - 2, sq.ymax - 2) is True


def test_map_subcell_terrain_parsing():
    from soundrts.tests.test_player_start import _make_parse_stub

    m = _make_parse_stub()
    if m is None:
        pytest.skip("world_map not importable")
    m.name_to_square = {}
    line = "terrain mountain a1/1,1 a1/2,1"
    locations = m._parse_terrain_location_tokens(["a1/1,1", "a1/2,1"], line, "terrain")
    assert locations == [("0,0", (0, 0)), ("0,0", (1, 0))]


def test_format_subcell_suffix():
    assert format_subcell_suffix(0, 2) == "/1,3"


def test_subcell_overlay_apply_palette():
    sq = _make_square()
    sq.subcells.apply_palette(
        {
            "style": "mountain",
            "water": False,
            "ground": False,
            "air": False,
            "high_ground": True,
            "speed": (50, 100),
            "cover": (10, 0),
        },
        2,
        0,
    )
    x = sq.xmax - 2
    y = sq.ymin + 1
    assert sq.type_name_at(x, y) == "mountain"
    assert sq.high_ground_at(x, y) is True
    assert sq.is_ground_at(x, y) is False
    assert sq.terrain_speed_at(x, y) == (50, 100)
    assert sq.terrain_cover_at(x, y) == (10, 0)
