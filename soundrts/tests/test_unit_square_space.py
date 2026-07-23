"""Unit abstract ``space`` vs square capacity (``square_width``), per alliance."""

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


def _player(name="p"):
    p = types.SimpleNamespace(id=name)
    p.allied = [p]
    return p


def _allied_pair():
    a = _player("a")
    b = _player("b")
    a.allied = [a, b]
    b.allied = [b, a]
    return a, b


def _unit(space, airground_type="ground", collision=1, player=None):
    """*space* in map units; stored as precision ints like rules."""
    return types.SimpleNamespace(
        space=int(space * PRECISION) if space else 0,
        airground_type=airground_type,
        collision=collision,
        player=player,
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
    p = _player()
    for _ in range(20):
        sq.objects.append(_unit(0, player=p))
    assert sq.have_enough_square_space(_unit(0, player=p)) is True
    assert sq.have_enough_square_space(_unit(1, player=p)) is True


def test_unit_larger_than_square_width_cannot_enter():
    sq = _make_square(12)
    p = _player()
    assert sq.have_enough_square_space(_unit(13, player=p)) is False
    assert sq.have_enough_square_space(_unit(12, player=p)) is True


def test_capacity_fills_and_blocks_own_side():
    sq = _make_square(12)
    p = _player()
    sq.objects.append(_unit(4, player=p))
    sq.objects.append(_unit(4, player=p))
    sq.objects.append(_unit(4, player=p))
    assert sq.used_square_space("ground", for_player=p) == 12 * PRECISION
    assert sq.have_enough_square_space(_unit(1, player=p)) is False
    assert sq.have_enough_square_space(_unit(0, player=p)) is True


def test_decimal_space_half_fits_24_on_width_12():
    """space 0.5 on square_width 12 → 24 per side."""
    sq = _make_square(12)
    p = _player()
    for _ in range(24):
        assert sq.have_enough_square_space(_unit(0.5, player=p)) is True
        sq.objects.append(_unit(0.5, player=p))
    assert sq.have_enough_square_space(_unit(0.5, player=p)) is False


def test_space_1_fits_12_on_width_12():
    sq = _make_square(12)
    p = _player()
    for _ in range(12):
        sq.objects.append(_unit(1, player=p))
    assert sq.have_enough_square_space(_unit(1, player=p)) is False


def test_exclude_self_when_already_on_square():
    sq = _make_square(12)
    p = _player()
    me = _unit(6, player=p)
    sq.objects.append(me)
    sq.objects.append(_unit(6, player=p))
    assert sq.have_enough_square_space(me) is True


def test_airground_layers_are_separate():
    sq = _make_square(12)
    p = _player()
    sq.objects.append(_unit(12, airground_type="ground", player=p))
    assert sq.have_enough_square_space(_unit(12, airground_type="air", player=p)) is True
    assert sq.have_enough_square_space(_unit(1, airground_type="ground", player=p)) is False


def test_enemy_full_square_does_not_block_entry():
    """Enemy catapults filling the square must not stop cavalry from entering."""
    sq = _make_square(12)
    enemy = _player("enemy")
    me = _player("me")
    for _ in range(12):
        sq.objects.append(_unit(1, player=enemy))
    assert sq.used_square_space("ground", for_player=me) == 0
    assert sq.have_enough_square_space(_unit(1, player=me)) is True
    for _ in range(12):
        assert sq.have_enough_square_space(_unit(1, player=me)) is True
        sq.objects.append(_unit(1, player=me))
    assert sq.have_enough_square_space(_unit(1, player=me)) is False


def test_allies_share_one_budget():
    sq = _make_square(12)
    a, b = _allied_pair()
    for _ in range(12):
        sq.objects.append(_unit(1, player=a))
    assert sq.have_enough_square_space(_unit(1, player=b)) is False
    assert sq.have_enough_square_space(_unit(1, player=a)) is False


def test_no_player_context_skips_abstract_check_during_construct():
    """Entity.__init__ calls move_to before set_player; must not raise."""
    sq = _make_square(12)
    enemy = _player("enemy")
    for _ in range(12):
        sq.objects.append(_unit(1, player=enemy))
    # Unowned constructing unit: abstract check skipped (caller pre-checked).
    assert sq.have_enough_square_space(_unit(1, player=None)) is True
    assert sq.have_enough_square_space(_unit(1), player=None) is True
    sq = _make_square(12)
    p = _player()
    sq.objects.append(_unit(12, player=p))
    assert sq.can_receive("ground") is True
    assert sq.can_receive("ground", unit=_unit(1, player=p)) is False
    assert sq.can_receive("ground", unit=_unit(0, player=p)) is True


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
