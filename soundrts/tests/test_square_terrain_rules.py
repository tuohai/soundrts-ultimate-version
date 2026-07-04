import types

from soundrts.lib.square_terrain_rules import (
    parse_square_terrain_entries,
    resolve_square_layers,
    resolve_square_type_name,
    terrain_is_dynamic,
    winning_terrain_entry,
)
from soundrts.worldroom import Square


def test_parse_square_terrain_entries():
    assert parse_square_terrain_entries(["forest", "80", "7"]) == [
        {"name": "forest", "priority": 80, "min_count": 7}
    ]


def test_fixed_hill_terrain_voices_hill_and_high_ground():
    from pathlib import Path

    from soundrts.clientgame.game_navigation import _square_terrain
    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    square = object.__new__(Square)
    square.objects = []
    square.type_name = "hill"
    square.high_ground = True
    square.is_water = False
    square.fixed_terrain = True
    square.world = types.SimpleNamespace()
    msgs = _square_terrain(square)
    assert 5699 in msgs or "5699" in msgs
    assert 5698 in msgs or "5698" in msgs


def test_empty_square_has_no_default_terrain():
    square = object.__new__(Square)
    square.objects = []
    square.high_ground = False
    square.is_water = False
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    assert resolve_square_type_name(square) == ""
    layers = resolve_square_layers(square)
    assert layers["feature_voice"] is None
    assert layers["dynamic_voice"] is None


def test_forest_from_objects_when_no_map_terrain():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    square = object.__new__(Square)
    square.objects = [types.SimpleNamespace(type_name="wood")]
    square.high_ground = False
    square.is_water = False
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    layers = resolve_square_layers(square)
    assert layers["feature_voice"] == "forest"
    assert layers["type_name"] == "forest"


def test_forest_removed_leaves_empty_type_name():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    square = object.__new__(Square)
    square.objects = []
    square.high_ground = False
    square.is_water = False
    square.fixed_terrain = False
    square.world = types.SimpleNamespace()
    assert resolve_square_type_name(square) == ""


def test_terrain_plain_on_map_sets_fixed_terrain():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    square = object.__new__(Square)
    square.objects = []
    square.type_name = "plain"
    square.high_ground = False
    square.is_water = False
    square.fixed_terrain = True
    square.world = types.SimpleNamespace()
    assert resolve_square_type_name(square) == "plain"


def test_mountain_terrain_applies_ground_air_and_blocks_path():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import (
        apply_terrain_map_flags,
        terrain_blocks_path,
        terrain_map_square_flags,
    )

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    flags = terrain_map_square_flags("mountain")
    assert flags == {
        "high_ground": False,
        "is_water": False,
        "is_ground": False,
        "is_air": False,
    }
    assert terrain_blocks_path("mountain") is True
    square = object.__new__(Square)
    square.high_ground = True
    square.is_water = False
    square.is_ground = True
    square.is_air = True
    apply_terrain_map_flags(square, "mountain")
    assert square.high_ground is False
    assert square.is_water is False
    assert square.is_ground is False
    assert square.is_air is False


def test_lake_terrain_applies_water_and_blocks_ground():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import (
        apply_terrain_map_flags,
        terrain_effective_is_ground,
        terrain_is_water,
    )

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    assert terrain_is_water("lake") is True
    assert terrain_effective_is_ground("lake") is False
    square = object.__new__(Square)
    square.high_ground = False
    square.is_water = False
    square.is_ground = True
    square.subcells = None
    apply_terrain_map_flags(square, "lake")
    assert square.is_water is True
    assert square.is_ground is False


def test_all_map_terrains_have_class_terrain():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    expected = [
        "plain",
        "rocky_plain",
        "plateau",
        "hill",
        "high_rocky_plain",
        "mountain_pass",
        "basin",
        "lake",
        "sea",
        "ocean",
        "river",
        "creek",
        "ford",
        "big_bridge",
        "bridge_deck",
        "marsh",
        "mountain",
        "town",
        "meadows",
        "build_sites",
        "forest",
        "dense_forest",
    ]
    for name in expected:
        assert rules.get(name, "class") == ["terrain"], name


def test_terrain_is_dynamic_from_class_terrain():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    assert terrain_is_dynamic("plain") is True
    assert terrain_is_dynamic("lake") is False


def test_terrain_map_object_spawns_from_square_terrain():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import terrain_map_object_spawns

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    assert terrain_map_object_spawns("forest") == {"wood": 1}
    assert terrain_map_object_spawns("dense_forest") == {"wood": 7}
    assert terrain_map_object_spawns("town") == {"townhall": 1}
    assert terrain_map_object_spawns("lake") == {}


def test_passable_units_not_configured_uses_category_flags():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import terrain_has_passable_units

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    assert terrain_has_passable_units("mountain") is False


def test_passable_units_parent_type_allows_child_unit():
    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import (
        terrain_allows_unit,
        unit_matches_passable_units,
    )
    from soundrts.worldroom import Square

    rules.load(
        """
def archers
class soldier

def archer
class soldier
is_a archers

def mountain
class terrain
is_ground 0
is_air 0
passable_units archers
""",
        base_classes=_get_base_classes(),
    )
    assert unit_matches_passable_units(
        types.SimpleNamespace(type_name="archer", expanded_is_a=("archers",)),
        ["archers"],
    )
    assert terrain_allows_unit(
        "mountain",
        types.SimpleNamespace(type_name="archer", expanded_is_a=("archers",)),
    )
    assert terrain_allows_unit(
        "mountain",
        types.SimpleNamespace(type_name="footman", expanded_is_a=()),
    ) is False

    sq = object.__new__(Square)
    sq.subcells = None
    sq.fixed_terrain = True
    sq.type_name = "mountain"
    sq.is_ground = False
    sq.is_air = False
    sq.is_water = False
    sq.type_name_at = lambda x, y: "mountain"

    class _Archer:
        type_name = "archer"
        expanded_is_a = ("archers",)
        airground_type = "ground"

    class _Footman:
        type_name = "footman"
        expanded_is_a = ()
        airground_type = "ground"

    assert sq.is_passable_for(_Archer(), 1, 1) is True
    assert sq.is_passable_for(_Footman(), 1, 1) is False


def test_passable_units_empty_list_denies_everyone():
    from soundrts.definitions import _get_base_classes, rules
    from soundrts.lib.square_terrain_rules import terrain_allows_unit

    rules.load(
        """
def sealed
class terrain
is_ground 1
passable_units
""",
        base_classes=_get_base_classes(),
    )
    unit = types.SimpleNamespace(type_name="footman", expanded_is_a=())
    assert terrain_allows_unit("sealed", unit) is False
