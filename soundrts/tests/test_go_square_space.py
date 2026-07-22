"""Go to a full square: immediate reject vs exit-then-block."""
from __future__ import annotations

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.worldorders.base import _order_target_square
from soundrts.worldorders.movement import GoOrder, PatrolOrder
from soundrts.worldunit.world_movement import CreatureMovement


def _full_square(width=12, square_id="full"):
    capacity = int(width * PRECISION)
    objects = [
        types.SimpleNamespace(
            space=1 * PRECISION,
            airground_type="ground",
            collision=1,
        )
        for _ in range(width)
    ]

    def have_enough(unit, _objects=objects, _capacity=capacity):
        space = int(getattr(unit, "space", 0) or 0)
        if space <= 0:
            return True
        if space > _capacity:
            return False
        used = sum(
            int(getattr(o, "space", 0) or 0)
            for o in _objects
            if getattr(o, "airground_type", None)
            == getattr(unit, "airground_type", "ground")
            and int(getattr(o, "space", 0) or 0) > 0
        )
        return used + space <= _capacity

    return types.SimpleNamespace(
        id=square_id,
        is_water=False,
        is_ground=True,
        is_air=True,
        x=0,
        y=0,
        objects=objects,
        have_enough_square_space=have_enough,
    )


def _make_unit(*, target, place=None, space=1):
    if place is None:
        place = types.SimpleNamespace(
            id="start",
            is_water=False,
            is_ground=True,
            objects=[],
            have_enough_square_space=lambda u: True,
        )
    unit = types.SimpleNamespace(
        airground_type="ground",
        space=int(space * PRECISION),
        orders=[],
        notifications=[],
        is_imperative=False,
        speed=2,
        is_idle=True,
        place=place,
        player=types.SimpleNamespace(
            get_object_by_id=lambda _id: target,
            updated_target=lambda t: t,
            smart_units=False,
        ),
        world=types.SimpleNamespace(time=0),
    )
    unit.notify = lambda msg, *_a, **_k: unit.notifications.append(msg)
    unit.deploy = lambda: None
    unit.stop = lambda: setattr(unit, "stopped", True)
    return unit


def test_go_direct_to_full_square_impossible_immediately():
    full = _full_square()
    unit = _make_unit(target=full)
    order = GoOrder(unit, [full.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,not_enough_space" in unit.notifications
    assert "order_ok" not in unit.notifications


def test_go_via_exit_to_full_square_allowed_on_queue():
    full = _full_square()
    exit_ = types.SimpleNamespace(
        id="exit1",
        other_side=types.SimpleNamespace(place=full),
    )
    unit = _make_unit(target=exit_)
    order = GoOrder(unit, [exit_.id])
    order.on_queued()
    assert not order.is_impossible
    assert order.target is full
    assert "order_ok" in unit.notifications
    assert "not_enough_space" not in "".join(unit.notifications)


def test_entry_block_notifies_when_destination_is_full():
    full = _full_square()
    unit = _make_unit(target=full)
    order = GoOrder(unit, [full.id])
    # Simulate exit-path: queued without immediate reject
    order.target = full
    order.is_impossible = False
    unit.orders = [order]
    unit._on_square_space_blocked = CreatureMovement._on_square_space_blocked.__get__(
        unit, type(unit)
    )
    unit._order_destination_square = CreatureMovement._order_destination_square.__get__(
        unit, type(unit)
    )

    unit._on_square_space_blocked(full)
    assert order.is_impossible
    assert "order_impossible,not_enough_space" in unit.notifications
    assert getattr(unit, "stopped", False) is True


def test_entry_block_ignores_unrelated_adjacent_full_square():
    other = _full_square(square_id="other")
    dest = types.SimpleNamespace(
        id="dest",
        is_water=False,
        is_ground=True,
        objects=[],
        have_enough_square_space=lambda u: True,
    )
    unit = _make_unit(target=dest)
    order = GoOrder(unit, [dest.id])
    order.target = dest
    order.is_impossible = False
    unit.orders = [order]
    unit._on_square_space_blocked = CreatureMovement._on_square_space_blocked.__get__(
        unit, type(unit)
    )
    unit._order_destination_square = CreatureMovement._order_destination_square.__get__(
        unit, type(unit)
    )

    unit._on_square_space_blocked(other)
    assert not order.is_impossible
    assert "not_enough_space" not in "".join(unit.notifications)


def test_patrol_to_full_square_impossible_immediately():
    full = _full_square()
    unit = _make_unit(target=full)
    order = PatrolOrder(unit, [full.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,not_enough_space" in unit.notifications


def test_order_target_square_from_square():
    full = _full_square()
    assert _order_target_square(full) is full
