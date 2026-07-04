import types

import pytest

from soundrts.worldresource import (
    BuildingLand,
    building_land_class,
    building_land_types,
    create_building_land,
)
from soundrts.worldroom import Square

try:
    from soundrts.world import world_map as _WM
except Exception:
    _WM = None


def _make_parse_stub():
    if _WM is None:
        return None
    m = _WM.WorldMapMixin.__new__(_WM.WorldMapMixin)
    m.computers_starts = []
    m.players_starts = []
    m.starting_units = []
    m.starting_resources = []
    m.specific_starts = []
    m.player_start_overrides = {}
    m.starting_squares = []
    m.additional_meadows = []
    m.additional_build_sites = []
    m.additional_building_land = []
    m.remove_meadows = []
    m.building_land = "meadow"
    m._map_building_land_explicit = False
    m.high_grounds = []
    m.nb_players_min = 1
    m.nb_players_max = 1
    m.nb_columns = 2
    m.nb_lines = 2
    m.nb_rows = 0
    m.square_width = 12
    m.nb_meadows_by_square = 0
    m.nb_building_land_by_square = {}
    m.random_starts = 1
    m.west_east = []
    m.south_north = []
    m.terrain = {}
    m.terrain_speed = {}
    m.terrain_cover = {}
    m.sub_terrain = {}
    m.sub_high_grounds = {}
    m.sub_terrain_speed = {}
    m.sub_terrain_cover = {}
    m.sub_water = {}
    m.sub_ground = {}
    m.sub_no_air = {}
    m.subcell_precision = 3
    m.water_squares = set()
    m.no_air_squares = set()
    m.ground_squares = set()
    m.name_to_square = {}
    m.square_names = {}
    m.square_cities = {}
    m.square_provinces = {}
    m.square_districts = {}
    m.map_objects = []
    m.map_music = None
    m.map_battle_music = None
    m.map_victory_sound = None
    m.map_defeat_sound = None
    m.map_defined_starting_units = False
    m.map_defined_starting_resources = False
    m.map_defined_specific_starts = False
    m.map_defined_starting_population = False
    m.starting_population = 0
    m.nb_res = 2
    m.default_triggers = []

    class _R:
        def choice(self, xs):
            return xs[0]

    m.random = _R()
    return m


def test_build_site_is_building_land():
    _load_default_rules()
    from soundrts.definitions import rules

    cls = rules.unit_class("build_site")
    assert cls.is_a_building_land
    assert cls.type_name == "build_site"
    assert issubclass(cls, BuildingLand)


def test_building_land_class_lookup():
    _load_default_rules()
    from soundrts.definitions import rules

    assert building_land_class("meadow") is rules.unit_class("meadow")
    assert building_land_class("build_site") is rules.unit_class("build_site")


def test_create_building_land_uses_world_default():
    _load_default_rules()
    from soundrts.definitions import rules

    place = types.SimpleNamespace(
        world=types.SimpleNamespace(building_land="build_site")
    )
    assert building_land_class(getattr(place.world, "building_land")) is rules.unit_class(
        "build_site"
    )


def _make_square_stub(**attrs):
    square = object.__new__(Square)
    square.objects = attrs.get("objects", [])
    square.type_name = attrs.get("type_name", "")
    square.high_ground = attrs.get("high_ground", False)
    square.is_water = attrs.get("is_water", False)
    square.fixed_terrain = attrs.get("fixed_terrain", False)
    square.strict_neighbors = attrs.get("strict_neighbors", [])
    square.world = types.SimpleNamespace()
    return square


def test_update_terrain_meadows_with_meadow_only():
    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="meadow",
            )
        ]
    )
    Square.update_terrain(square)
    assert square.type_name == "meadows"


def test_update_terrain_build_sites_with_build_site():
    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="build_site",
            )
        ]
    )
    Square.update_terrain(square)
    assert square.type_name == "build_sites"


def test_update_terrain_build_sites_when_mixed_with_meadow():
    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="meadow",
            ),
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="build_site",
            ),
        ]
    )
    Square.update_terrain(square)
    assert square.type_name == "build_sites"


def _load_default_rules():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )


def test_square_terrain_voice_build_sites_not_meadows():
    from soundrts.clientgame.game_navigation import _square_terrain

    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="build_site",
            )
        ]
    )
    msgs = _square_terrain(square)
    assert 5696 not in msgs and "5696" not in msgs
    assert 5694 in msgs or "5694" in msgs
    assert 4362 not in msgs and "4362" not in msgs


def test_square_terrain_forest_and_build_sites():
    from soundrts.clientgame.game_navigation import _square_terrain

    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(type_name="wood"),
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="build_site",
            ),
        ]
    )
    msgs = _square_terrain(square)
    assert 5696 not in msgs and "5696" not in msgs
    assert 4363 in msgs or "4363" in msgs
    assert 5694 in msgs or "5694" in msgs


def test_square_terrain_plain_layer_with_meadows():
    from soundrts.clientgame.game_navigation import _square_terrain

    _load_default_rules()
    square = _make_square_stub(
        objects=[
            types.SimpleNamespace(
                is_a_building_land=True,
                is_an_exit=False,
                type_name="meadow",
            )
        ]
    )
    msgs = _square_terrain(square)
    assert 5696 not in msgs and "5696" not in msgs
    assert 4362 in msgs or "4362" in msgs


def test_square_terrain_plain_persists_on_high_ground_square():
    from soundrts.clientgame.game_navigation import _square_terrain

    _load_default_rules()
    square = _make_square_stub(
        high_ground=True,
        objects=[types.SimpleNamespace(type_name="wood")],
    )
    msgs = _square_terrain(square)
    assert 5696 not in msgs and "5696" not in msgs
    assert 4363 in msgs or "4363" in msgs
    assert 5698 in msgs or "5698" in msgs
    assert 4314 not in msgs and "4314" not in msgs


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_parses_building_land_and_additional_build_sites():
    m = _make_parse_stub()
    m._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares a1
building_land build_site
nb_meadows_by_square 1
additional_build_sites a1
""")
    assert m.building_land == "build_site"
    assert m.additional_build_sites == ["0,0"]
    assert m.nb_meadows_by_square == 1

def test_custom_building_land_from_rules():
    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        """
def parameters
default_building_land landing_pad

def landing_pad
class building_land
square_terrain build_sites 45

def build_sites
class terrain
is_dynamic 0
""",
        base_classes=_get_base_classes(),
    )
    from soundrts.worldresource import building_land_types

    assert "landing_pad" in building_land_types()
    cls = rules.unit_class("landing_pad")
    assert cls.is_a_building_land
    assert cls.type_name == "landing_pad"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_parses_nb_build_site_by_square():
    m = _make_parse_stub()
    _load_default_rules()
    m._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares a1
nb_build_site_by_square 2
""")
    assert m.nb_building_land_by_square == {"build_site": 2}
    assert m.nb_meadows_by_square == 0


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_nb_build_site_by_square_spawns_build_site():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
nb_build_site_by_square 1
""")
    world._build_map()
    for sq in world.grid.values():
        if not hasattr(sq, "objects"):
            continue
        lands = [o for o in sq.objects if o.type_name in ("meadow", "build_site")]
        assert lands == [] or all(o.type_name == "build_site" for o in lands)
    sq = world.grid["0,0"]
    assert len([o for o in sq.objects if o.type_name == "build_site"]) == 1
    assert len([o for o in sq.objects if o.type_name == "meadow"]) == 0


def test_nb_by_square_land_type_parsing():
    from soundrts.lib.building_land import nb_by_square_land_type

    assert nb_by_square_land_type("nb_build_site_by_square") == "build_site"
    assert nb_by_square_land_type("nb_volcanic_rock_by_square") == "volcanic_rock"
    assert nb_by_square_land_type("nb_火山岩石_by_square") == "火山岩石"
    assert nb_by_square_land_type("nb_meadows_by_square") is None
    assert nb_by_square_land_type("nb_meadow_by_square") == "meadow"
    assert nb_by_square_land_type("building_land") is None


def test_nb_custom_building_land_by_square():
    from soundrts.definitions import _get_base_classes, rules
    from soundrts.world import World

    rules.load(
        """
def parameters
default_building_land meadow

def landing_pad
class building_land
square_terrain build_sites 45

def build_sites
class terrain
is_dynamic 0
""",
        base_classes=_get_base_classes(),
    )
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
nb_landing_pad_by_square 3
""")
    world._build_map()
    sq = world.grid["0,0"]
    assert len([o for o in sq.objects if o.type_name == "landing_pad"]) == 3


def test_map_infers_building_land_from_nb_by_square():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    assert world.building_land == "meadow"
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares a1
nb_build_site_by_square 1
""")
    assert world.building_land == "build_site"


def test_recreate_building_land_prefers_consumed_over_world_default():
    from soundrts.world import World
    from soundrts.worldresource import recreate_building_land

    _load_default_rules()
    world = World([], 42)
    world.building_land = "meadow"
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
""")
    world._build_map()
    sq = world.grid["0,0"]
    consumed = types.SimpleNamespace(type_name="build_site")
    land = recreate_building_land(sq, sq.x, sq.y, consumed=consumed)
    assert land.type_name == "build_site"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_additional_building_land():
    m = _make_parse_stub()
    _load_default_rules()
    m._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares a1
additional_building_land build_site a1
""")
    assert m.additional_building_land == [("0,0", "build_site")]


def test_building_land_types():
    _load_default_rules()
    assert building_land_types() >= {"meadow", "build_site"}


    _load_default_rules()
    assert building_land_types() >= {"meadow", "build_site"}


def test_update_terrain_empty_when_no_map_or_objects():
    square = object.__new__(Square)
    square.objects = []
    square.type_name = ""
    square.high_ground = False
    square.is_water = False
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    square.strict_neighbors = []
    Square.update_terrain(square)
    assert square.type_name == ""


def test_update_terrain_empty_on_high_ground_without_map_terrain():
    square = object.__new__(Square)
    square.objects = []
    square.type_name = ""
    square.high_ground = True
    square.is_water = False
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    square.strict_neighbors = []
    Square.update_terrain(square)
    assert square.type_name == ""


def test_update_terrain_empty_on_water_without_map_terrain():
    square = object.__new__(Square)
    square.objects = []
    square.type_name = ""
    square.high_ground = False
    square.is_water = True
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    square.strict_neighbors = []
    Square.update_terrain(square)
    assert square.type_name == ""


def test_square_terrain_voice_none_without_map_terrain():
    from soundrts.clientgame.game_navigation import _square_terrain

    _load_default_rules()
    square = _make_square_stub()
    msgs = _square_terrain(square)
    assert 5696 not in msgs and "5696" not in msgs
    assert msgs == []


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_terrain_forest_spawns_wood_from_square_terrain_link():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain forest 1,1
""")
    world._build_map()
    sq = world.grid["0,0"]
    assert sq.fixed_terrain is False
    assert len([o for o in sq.objects if o.type_name == "wood"]) == 1
    sq.update_terrain()
    assert sq.type_name == "forest"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_terrain_dense_forest_spawns_seven_woods():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain dense_forest 1,1
""")
    world._build_map()
    sq = world.grid["0,0"]
    assert len([o for o in sq.objects if o.type_name == "wood"]) == 7
    sq.update_terrain()
    assert sq.type_name == "dense_forest"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_terrain_town_spawns_townhall():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain town 1,1
""")
    world._build_map()
    sq = world.grid["0,0"]
    assert len([o for o in sq.objects if o.type_name == "townhall"]) == 1
    sq.update_terrain()
    assert sq.type_name == "town"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_map_terrain_lake_stays_fixed_without_spawning_objects():
    from soundrts.world import World

    _load_default_rules()
    world = World([], 42)
    world._parse_map("""
nb_columns 2
nb_lines 2
nb_players_min 1
nb_players_max 1
starting_squares 2,2
terrain lake 1,1
""")
    world._build_map()
    sq = world.grid["0,0"]
    assert sq.fixed_terrain is True
    assert sq.type_name == "lake"
    assert [o for o in sq.objects if o.type_name == "wood"] == []
