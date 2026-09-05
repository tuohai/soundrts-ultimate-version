"""Town Bell: Euclidean meter range, garrison/restore, style hooks."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from soundrts.lib.nofloat import PRECISION
from soundrts.world_town_bell import (
    is_town_bell_target,
    nearest_shelter,
    restore_orders,
    ring_town_bell,
    snapshot_orders,
    stop_town_bell,
    worker_in_bell_range,
    workers_already_inside,
    workers_to_garrison,
)


ROOT = Path(__file__).resolve().parents[2]


def test_range_is_euclidean_meters_not_squares():
    # Live units store PRECISION mm. 3 m = 3000.
    bell = SimpleNamespace(town_bell_range=3 * PRECISION, x=0, y=0)
    assert worker_in_bell_range(SimpleNamespace(x=2 * PRECISION, y=0), bell)
    assert not worker_in_bell_range(SimpleNamespace(x=4 * PRECISION, y=0), bell)
    # Same-square offset of 8 m is outside a 3 m bell.
    assert not worker_in_bell_range(SimpleNamespace(x=8 * PRECISION, y=0), bell)


def test_range_zero_is_unlimited():
    bell = SimpleNamespace(town_bell_range=0, x=0, y=0)
    assert worker_in_bell_range(SimpleNamespace(x=10**9, y=10**9), bell)


def test_type_filter_uses_is_a():
    peasant = SimpleNamespace(
        is_inside=False,
        hp=25,
        type_name="peasant",
        expanded_is_a=("peasant", "worker"),
        airground_type="ground",
    )
    boat = SimpleNamespace(
        is_inside=False,
        hp=25,
        type_name="fishing_ship",
        expanded_is_a=("fishing_ship", "ship"),
        airground_type="water",
    )
    assert is_town_bell_target(peasant, ("peasant",))
    assert not is_town_bell_target(boat, ("peasant",))
    inside = SimpleNamespace(
        is_inside=True, hp=25, type_name="peasant", expanded_is_a=("peasant",)
    )
    assert not is_town_bell_target(inside, ("peasant",))


def test_workers_to_garrison_only_in_range():
    bell = SimpleNamespace(
        town_bell=1,
        town_bell_range=3 * PRECISION,
        town_bell_units=("peasant",),
        hp=2400,
        x=0,
        y=0,
        id="tc",
    )
    near = SimpleNamespace(
        id="v1",
        is_inside=False,
        hp=25,
        type_name="peasant",
        expanded_is_a=("peasant",),
        x=2 * PRECISION,
        y=0,
        airground_type="ground",
    )
    far = SimpleNamespace(
        id="v2",
        is_inside=False,
        hp=25,
        type_name="peasant",
        expanded_is_a=("peasant",),
        x=20 * PRECISION,
        y=0,
        airground_type="ground",
    )
    player = SimpleNamespace(units=[bell, near, far])
    got = workers_to_garrison(player)
    assert near in got
    assert far not in got


def test_nearest_shelter_picks_closer_with_space():
    worker = SimpleNamespace(x=0, y=0, id="v")
    close = SimpleNamespace(
        x=1 * PRECISION,
        y=0,
        hp=100,
        transport_capacity=15,
        have_enough_space=lambda _w: True,
        id="a",
    )
    far = SimpleNamespace(
        x=9 * PRECISION,
        y=0,
        hp=100,
        transport_capacity=15,
        have_enough_space=lambda _w: True,
        id="b",
    )
    full = SimpleNamespace(
        x=0,
        y=0,
        hp=100,
        transport_capacity=15,
        have_enough_space=lambda _w: False,
        id="c",
    )
    player = SimpleNamespace(units=[full, far, close])
    assert nearest_shelter(player, worker) is close


def test_ring_and_stop_restore_orders():
    shelter = SimpleNamespace(
        id="tc",
        x=0,
        y=0,
        hp=2400,
        town_bell=1,
        town_bell_range=12 * PRECISION,
        town_bell_units=("peasant",),
        transport_capacity=15,
        have_enough_space=lambda _w: True,
        unload_matching=Mock(return_value=1),
    )
    order = SimpleNamespace(keyword="gather", args=["gold1"])
    worker = SimpleNamespace(
        id="v1",
        is_inside=False,
        hp=25,
        type_name="peasant",
        expanded_is_a=("peasant",),
        x=1 * PRECISION,
        y=0,
        airground_type="ground",
        orders=[order],
        take_order=Mock(),
        cancel_all_orders=Mock(),
    )
    player = SimpleNamespace(units=[shelter, worker], _town_bell_active=False)
    ring_town_bell(player)
    assert player._town_bell_active is True
    assert worker._town_bell_garrisoned is True
    assert worker._town_bell_resume == [["gather", "gold1"]]
    worker.take_order.assert_called_once_with(["enter", "tc"])

    worker.is_inside = False
    stop_town_bell(player)
    assert player._town_bell_active is False
    assert worker._town_bell_garrisoned is False
    worker.cancel_all_orders.assert_called()
    worker.take_order.assert_called_with(["gather", "gold1"], forget_previous=True)


def test_ring_tags_already_garrisoned_villagers_then_stop_unloads():
    """AoE2: after manual garrison, Town Bell still works; Return to Work lets vils out."""
    shelter = SimpleNamespace(
        id="tc",
        x=0,
        y=0,
        hp=2400,
        town_bell=1,
        town_bell_range=12 * PRECISION,
        town_bell_units=("peasant",),
        transport_capacity=15,
        have_enough_space=lambda _w: True,
        unload_matching=Mock(return_value=1),
    )
    inside_place = SimpleNamespace(container=shelter)
    vil = SimpleNamespace(
        id="v1",
        is_inside=True,
        hp=25,
        type_name="peasant",
        expanded_is_a=("peasant",),
        x=0,
        y=0,
        airground_type="ground",
        orders=[],
        place=inside_place,
        take_order=Mock(),
        cancel_all_orders=Mock(),
    )
    soldier = SimpleNamespace(
        id="s1",
        is_inside=True,
        hp=40,
        type_name="militia",
        expanded_is_a=("militia", "infantry"),
        x=0,
        y=0,
        airground_type="ground",
        orders=[],
        place=inside_place,
        take_order=Mock(),
    )
    player = SimpleNamespace(units=[shelter, vil, soldier], _town_bell_active=False)
    assert vil in workers_already_inside(player)
    assert soldier not in workers_already_inside(player)

    ring_town_bell(player)
    assert player._town_bell_active is True
    assert vil._town_bell_garrisoned is True
    vil.take_order.assert_not_called()
    assert not getattr(soldier, "_town_bell_garrisoned", False)

    stop_town_bell(player)
    assert player._town_bell_active is False
    assert vil._town_bell_garrisoned is False
    shelter.unload_matching.assert_called()
    soldier.take_order.assert_not_called()


def test_snapshot_and_restore_roundtrip():
    unit = SimpleNamespace(
        orders=[
            SimpleNamespace(keyword="gather", args=["n1"]),
            SimpleNamespace(keyword="go", args=["n2"]),
        ],
        take_order=Mock(),
    )
    snaps = snapshot_orders(unit)
    assert snaps == [["gather", "n1"], ["go", "n2"]]
    restore_orders(unit, snaps)
    assert unit.take_order.call_count == 2
    unit.take_order.assert_any_call(["gather", "n1"], forget_previous=True)
    unit.take_order.assert_any_call(["go", "n2"], forget_previous=False)


def test_building_has_town_bell_class_attrs():
    from soundrts.worldunit.worldcreature import Building

    assert hasattr(Building, "town_bell")
    assert hasattr(Building, "town_bell_range")
    assert hasattr(Building, "town_bell_units")
    assert Building.town_bell == 0
    assert Building.town_bell_range == 0
    assert Building.town_bell_units == ()


def test_aoe2_rules_and_style_wire_town_bell():
    rules = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    style = (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8")
    assert "town_bell 1" in rules
    assert "town_bell_range 24" in rules
    assert "town_bell town_bell1" in style
    assert "town_bell_stop town_bell2" in style
    defs = (ROOT / "soundrts" / "definitions.py").read_text(encoding="utf-8")
    assert '"town_bell"' in defs
    assert '"town_bell_range"' in defs
    assert '"town_bell_units"' in defs
    creature = (ROOT / "soundrts" / "worldunit" / "worldcreature.py").read_text(
        encoding="utf-8"
    )
    assert "town_bell_range = 0" in creature


def test_aoe2_teuton_town_center_keeps_town_bell_range():
    """interpret() used to drop town_bell_range because Building lacked the attr."""
    from soundrts.definitions import Rules
    from soundrts.lib.nofloat import PRECISION as P

    aoe2 = ROOT / "mods" / "aoe2" / "rules.txt"
    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        aoe2.read_text(encoding="utf-8"),
    )
    for name in ("town_center", "townhall", "teuton_town_center"):
        assert r.get(name, "town_bell") == 1, name
        assert r.get(name, "town_bell_range") == 24 * P, name
