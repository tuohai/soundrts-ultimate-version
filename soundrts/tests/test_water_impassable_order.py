"""地面/水上/地面与空中单位前往不可通行地形时应拒绝命令并提示。"""
from __future__ import annotations

import types

from soundrts.worldorders.base import (
    _ground_air_impassable_reason,
    _is_impassable_land_for_water_unit,
    _is_impassable_water_for_ground_unit,
    _order_target_square,
    _terrain_impassable_reason,
)
from soundrts.worldorders.movement import GoOrder, PatrolOrder


def _make_unit(*, airground_type, target, is_imperative=False):
    unit = types.SimpleNamespace(
        airground_type=airground_type,
        orders=[],
        notifications=[],
        is_imperative=is_imperative,
        speed=2,
        is_idle=True,
        place=types.SimpleNamespace(id="start", is_water=(airground_type == "water")),
        player=types.SimpleNamespace(
            get_object_by_id=lambda _id: target,
            updated_target=lambda t: t,
            smart_units=False,
        ),
        world=types.SimpleNamespace(time=0),
    )
    unit.notify = lambda msg, *_a, **_k: unit.notifications.append(msg)
    unit.deploy = lambda: None
    return unit


def test_order_target_square_from_entity():
    square = types.SimpleNamespace(id="sq", is_water=False, is_ground=True)
    entity = types.SimpleNamespace(place=square)
    assert _order_target_square(entity) is square
    assert _order_target_square(square) is square


def test_impassable_water_detects_river_ocean_lake():
    unit = types.SimpleNamespace(airground_type="ground")
    water = types.SimpleNamespace(is_water=True, is_ground=False)
    assert _is_impassable_water_for_ground_unit(unit, water)


def test_ford_and_bridge_are_not_impassable():
    unit = types.SimpleNamespace(airground_type="ground")
    ford = types.SimpleNamespace(is_water=True, is_ground=True)
    bridge = types.SimpleNamespace(is_water=False, is_ground=True)
    assert not _is_impassable_water_for_ground_unit(unit, ford)
    assert not _is_impassable_water_for_ground_unit(unit, bridge)


def test_go_order_to_water_is_impossible_with_message():
    water = types.SimpleNamespace(id="w1", is_water=True, is_ground=False)
    unit = _make_unit(airground_type="ground", target=water)
    order = GoOrder(unit, [water.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,water_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_go_order_to_ford_still_ok():
    ford = types.SimpleNamespace(id="f1", is_water=True, is_ground=True)
    unit = _make_unit(airground_type="ground", target=ford)
    order = GoOrder(unit, [ford.id])
    order.on_queued()
    assert not order.is_impossible
    assert "order_ok" in unit.notifications


def test_patrol_order_to_water_is_impossible():
    water = types.SimpleNamespace(id="w1", is_water=True, is_ground=False)
    unit = _make_unit(airground_type="ground", target=water)
    order = PatrolOrder(unit, [water.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,water_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_impassable_land_detects_ground_square():
    unit = types.SimpleNamespace(airground_type="water")
    land = types.SimpleNamespace(is_water=False, is_ground=True)
    assert _is_impassable_land_for_water_unit(unit, land)


def test_water_unit_can_order_to_water_square():
    unit = types.SimpleNamespace(airground_type="water")
    water = types.SimpleNamespace(is_water=True, is_ground=False)
    assert not _is_impassable_land_for_water_unit(unit, water)


def test_go_order_to_land_is_impossible_for_water_unit():
    land = types.SimpleNamespace(id="l1", is_water=False, is_ground=True)
    unit = _make_unit(airground_type="water", target=land)
    order = GoOrder(unit, [land.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,land_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_patrol_order_to_land_is_impossible_for_water_unit():
    land = types.SimpleNamespace(id="l1", is_water=False, is_ground=True)
    unit = _make_unit(airground_type="water", target=land)
    order = PatrolOrder(unit, [land.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,land_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_ground_air_impassable_reason_mountain_for_ground_unit():
    unit = types.SimpleNamespace(airground_type="ground")
    mountain = types.SimpleNamespace(is_water=False, is_ground=False, is_air=False)
    assert _ground_air_impassable_reason(unit, mountain) == "ground_impassable"
    assert _terrain_impassable_reason(unit, mountain) == "ground_impassable"


def test_ground_air_impassable_reason_mountain_for_air_unit():
    unit = types.SimpleNamespace(airground_type="air")
    mountain = types.SimpleNamespace(is_water=False, is_ground=False, is_air=False)
    assert _ground_air_impassable_reason(unit, mountain) == "air_impassable"
    assert _terrain_impassable_reason(unit, mountain) == "air_impassable"


def test_go_order_to_mountain_is_impossible_for_ground_unit():
    mountain = types.SimpleNamespace(id="m1", is_water=False, is_ground=False, is_air=False)
    unit = _make_unit(airground_type="ground", target=mountain)
    order = GoOrder(unit, [mountain.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,ground_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_go_order_to_mountain_is_impossible_for_air_unit():
    mountain = types.SimpleNamespace(id="m1", is_water=False, is_ground=False, is_air=False)
    unit = _make_unit(airground_type="air", target=mountain)
    order = GoOrder(unit, [mountain.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,air_impassable" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_go_order_to_passable_land_still_ok_for_ground_unit():
    land = types.SimpleNamespace(id="l1", is_water=False, is_ground=True, is_air=True)
    unit = _make_unit(airground_type="ground", target=land)
    order = GoOrder(unit, [land.id])
    order.on_queued()
    assert not order.is_impossible
    assert "order_ok" in unit.notifications


def test_go_order_passable_units_denied_for_non_whitelisted_unit():
    from soundrts.definitions import _get_base_classes, rules
    from soundrts.worldroom import Square

    rules.load(
        """
def archers
class soldier

def archer
class soldier
is_a archers

def footman
class soldier

def knight
class soldier

def mountain
class terrain
is_ground 0
is_air 0
passable_units archers
""",
        base_classes=_get_base_classes(),
    )
    sq = object.__new__(Square)
    sq.id = "m1"
    sq.subcells = None
    sq.fixed_terrain = True
    sq.type_name = "mountain"
    sq.is_ground = False
    sq.is_air = False
    sq.is_water = False
    sq.x = 0
    sq.y = 0
    sq.type_name_at = lambda x, y: "mountain"

    footman = _make_unit(airground_type="ground", target=sq)
    footman.type_name = "footman"
    footman.expanded_is_a = ()
    order = GoOrder(footman, [sq.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,passable_units_denied,footman" in footman.notifications

    knight = _make_unit(airground_type="ground", target=sq)
    knight.type_name = "knight"
    knight.expanded_is_a = ()
    order = GoOrder(knight, [sq.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,passable_units_denied,knight" in knight.notifications


def test_go_order_passable_units_allows_whitelisted_unit():
    from soundrts.definitions import _get_base_classes, rules
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
    sq = object.__new__(Square)
    sq.id = "m1"
    sq.subcells = None
    sq.fixed_terrain = True
    sq.type_name = "mountain"
    sq.is_ground = False
    sq.is_air = False
    sq.is_water = False
    sq.x = 0
    sq.y = 0
    sq.type_name_at = lambda x, y: "mountain"

    archer = _make_unit(airground_type="ground", target=sq)
    archer.type_name = "archer"
    archer.expanded_is_a = ("archers",)
    order = GoOrder(archer, [sq.id])
    order.on_queued()
    assert not order.is_impossible
    assert "order_ok" in archer.notifications
