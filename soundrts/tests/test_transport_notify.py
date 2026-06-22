"""装载/卸载失败与无效时的专用播报。"""
from __future__ import annotations

import types

from soundrts.worldorders.transport import LoadAllOrder, LoadOrder, UnloadAllOrder


def _land(name, *, neighbors=(), is_water=False, is_ground=True):
    return types.SimpleNamespace(
        id=name,
        is_water=is_water,
        is_ground=is_ground,
        high_ground=False,
        strict_neighbors=list(neighbors),
        neighbors=list(neighbors),
        objects=[],
        x=0,
        y=0,
        contains=lambda x, y: True,
    )


def _water(name, *, neighbors=()):
    return types.SimpleNamespace(
        id=name,
        is_water=True,
        is_ground=False,
        high_ground=False,
        strict_neighbors=list(neighbors),
        neighbors=list(neighbors),
    )


def _player():
    return types.SimpleNamespace(
        updated_target=lambda t: t,
        smart_units=False,
        get_object_by_id=lambda object_id: object_id,
    )


def _make_boat(*, place, inside_objects=(), load_fn=None, load_all_fn=None, unload_all_fn=None):
    inside = types.SimpleNamespace(objects=list(inside_objects))
    boat = types.SimpleNamespace(
        airground_type="water",
        transport_capacity=8,
        speed=2,
        place=place,
        inside=inside,
        orders=[],
        notifications=[],
        is_idle=True,
        x=0,
        y=0,
        player=_player(),
        is_inside=False,
    )
    boat.notify = lambda msg, *_a, **_k: boat.notifications.append(msg)
    boat.stop = lambda: None
    boat.start_moving_to = lambda target: setattr(boat, "is_idle", False)
    boat.have_enough_space = lambda target: True
    if load_fn is None:
        load_fn = lambda target: inside.objects.append(target) or True
    if load_all_fn is None:
        load_all_fn = lambda place: 0
    if unload_all_fn is None:
        unload_all_fn = lambda place=None: len(inside.objects)
    boat.load = load_fn
    boat.load_all = load_all_fn
    boat.unload_all = unload_all_fn
    return boat


def test_load_order_invalid_when_target_missing():
    boat = _make_boat(place=_water("w"))
    boat.player.get_object_by_id = lambda _id: None
    order = LoadOrder(boat, ["missing"])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,load_invalid" in boat.notifications


def test_load_order_failed_when_no_space():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    boat = _make_boat(place=water)
    soldier = types.SimpleNamespace(
        id="u1",
        place=shore,
        player=boat.player,
        is_inside=False,
        airground_type="ground",
    )
    boat.have_enough_space = lambda target: False
    order = LoadOrder(boat, [soldier.id])
    order.target = soldier
    order.execute()
    assert order.is_impossible
    assert "order_impossible,load_failed" in boat.notifications


def test_load_order_waits_when_target_not_at_shore():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    far_land = _land("base")
    soldier = types.SimpleNamespace(
        id="u1",
        place=far_land,
        player=_player(),
        is_inside=False,
        airground_type="ground",
    )
    boat = _make_boat(place=water)
    soldier.player = boat.player
    order = LoadOrder(boat, [soldier.id])
    order.target = soldier
    order.execute()
    assert not order.is_impossible
    assert not order.is_complete


def test_load_all_waits_when_shore_empty():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    boat = _make_boat(place=water, load_all_fn=lambda place: 0)
    order = LoadAllOrder(boat, [shore.id])
    order.target = shore
    order.execute()
    assert not order.is_impossible
    assert not order.is_complete


def test_load_all_waits_when_not_adjacent_to_shore():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    far_water = _water("far")
    boat = _make_boat(place=far_water)
    order = LoadAllOrder(boat, [shore.id])
    order.target = shore
    order.execute()
    assert not order.is_impossible
    assert not order.is_complete


def test_unload_all_invalid_when_empty():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    boat = _make_boat(place=water)
    boat.player.get_object_by_id = lambda _id: shore
    order = UnloadAllOrder(boat, [shore.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,unload_invalid" in boat.notifications


def test_unload_all_failed_when_only_water_units_to_land():
    shore = _land("shore")
    water = _water("w", neighbors=[shore])
    shore.strict_neighbors.append(water)
    water_unit = types.SimpleNamespace(airground_type="water")
    boat = _make_boat(place=water, inside_objects=[water_unit])
    boat.player.get_object_by_id = lambda _id: shore
    order = UnloadAllOrder(boat, [shore.id])
    order.on_queued()
    boat.notifications.clear()
    order.execute()
    assert order.is_impossible
    assert "order_impossible,unload_failed" in boat.notifications
