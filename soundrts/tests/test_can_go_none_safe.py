"""Regression: ``_can_go(None)`` and ``can_move_to(None)`` must not crash.

Off-map ``get_place_from_xy`` returns ``None``; ``_can_go`` and
``can_move_to`` must treat ``None`` as "cannot go" without raising
``AttributeError: 'NoneType' object has no attribute 'id'``.
"""
from __future__ import annotations

import types

from soundrts.worldunit.world_movement import CreatureMovement


class _MovementStub:
    """Bare-minimum object that satisfies ``CreatureMovement`` for ``_can_go``."""

    airground_type = "ground"
    world = types.SimpleNamespace(time=0)
    place = None
    _can_go_cache = None
    _can_go_cache_timestamp = 0


def _make_unit():
    # Skip ``__init__``: only the fields read by ``_can_go`` matter.
    u = _MovementStub.__new__(_MovementStub)
    return u


def test_can_go_none_returns_false():
    u = _make_unit()
    assert CreatureMovement._can_go(u, None) is False


def test_can_go_ignores_blockers_none_returns_false():
    u = _make_unit()
    assert (
        CreatureMovement._can_go(u, None, ignore_blockers=True) is False
    )
    assert (
        CreatureMovement._can_go(
            u, None, ignore_blockers=True, ignore_forests=True,
        )
        is False
    )


def test_can_go_air_unit_still_returns_true_for_none():
    """Air units ignore terrain entirely, so None is still 'go'."""
    u = _make_unit()
    u.airground_type = "air"
    assert CreatureMovement._can_go(u, None) is True


def test_can_move_to_none_returns_false():
    u = _make_unit()
    u.speed = 100
    assert CreatureMovement.can_move_to(u, None) is False
