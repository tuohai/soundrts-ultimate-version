"""Unit abstract diameter (rules ``space``) vs square capacity (``square_width``)."""

import types

from soundrts.definitions import Rules, _get_base_classes, rules
from soundrts.lib.nofloat import PRECISION
from soundrts.worldroom import Square


def _make_square(width_map_units=12):
    """Bare Square with capacity = width_map_units * PRECISION."""
    sq = object.__new__(Square)
    w = int(width_map_units * PRECISION)
    sq.xmin = 0
    sq.xmax = w
    sq.ymin = 0
    sq.ymax = w
    sq.x = w // 2
    sq.y = w // 2
    sq.objects = []
    sq.world = types.SimpleNamespace(square_width=w, collision={})
    return sq


def _unit(space, airground_type="ground", collision=1):
    """*space* in map units; stored as precision ints like rules."""
    return types.SimpleNamespace(
        space=int(space * PRECISION) if space else 0,
        airground_type=airground_type,
        collision=collision,
    )


def test_space_registered_as_precision_property():
    assert "space" in Rules.precision_properties
    assert "space" not in Rules.int_properties


def test_square_capacity_from_square_width():
    sq = _make_square(12)
    assert sq.square_capacity == 12 * PRECISION
    sq10 = _make_square(10)
    assert sq10.square_capacity == 10 * PRECISION


def test_space_zero_never_blocks():
    sq = _make_square(12)
    for _ in range(20):
        sq.objects.append(_unit(0))
    assert sq.have_enough_square_space(_unit(0)) is True
    assert sq.have_enough_square_space(_unit(1)) is True


def test_unit_larger_than_square_width_cannot_enter():
    sq = _make_square(12)
    assert sq.have_enough_square_space(_unit(13)) is False
    assert sq.have_enough_square_space(_unit(12)) is True


def test_capacity_fills_and_blocks():
    sq = _make_square(12)
    sq.objects.append(_unit(4))
    sq.objects.append(_unit(4))
    sq.objects.append(_unit(4))
    assert sq.used_square_space("ground") == 12 * PRECISION
    assert sq.have_enough_square_space(_unit(1)) is False
    assert sq.have_enough_square_space(_unit(0)) is True


def test_decimal_space_half_fits_24_on_width_12():
    """space 0.5 on square_width 12 → capacity 24."""
    sq = _make_square(12)
    for _ in range(24):
        assert sq.have_enough_square_space(_unit(0.5)) is True
        sq.objects.append(_unit(0.5))
    assert sq.have_enough_square_space(_unit(0.5)) is False


def test_space_1_fits_12_on_width_12():
    sq = _make_square(12)
    for _ in range(12):
        sq.objects.append(_unit(1))
    assert sq.have_enough_square_space(_unit(1)) is False


def test_exclude_self_when_already_on_square():
    sq = _make_square(12)
    me = _unit(6)
    sq.objects.append(me)
    sq.objects.append(_unit(6))
    assert sq.have_enough_square_space(me) is True


def test_airground_layers_are_separate():
    sq = _make_square(12)
    sq.objects.append(_unit(12, airground_type="ground"))
    assert sq.have_enough_square_space(_unit(12, airground_type="air")) is True
    assert sq.have_enough_square_space(_unit(1, airground_type="ground")) is False


def test_can_receive_respects_unit_space():
    sq = _make_square(12)
    sq.objects.append(_unit(12))
    assert sq.can_receive("ground") is True
    assert sq.can_receive("ground", unit=_unit(1)) is False
    assert sq.can_receive("ground", unit=_unit(0)) is True


def test_rules_parse_decimal_space():
    rules.load(
        """
def peasant
class worker
space 0.5
hp_max 4
speed 1.5
""",
        base_classes=_get_base_classes(),
    )
    cls = rules.unit_class("peasant")
    assert cls.space == 500
