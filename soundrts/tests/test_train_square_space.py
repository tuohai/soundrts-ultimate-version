"""TrainOrder should refuse when the spawn square is full (per-alliance space)."""

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.worldorders.production import TrainOrder
from soundrts.worldroom import Square


def _player(name="p"):
    p = types.SimpleNamespace(id=name)
    p.allied = [p]
    return p


def _square(width=12, unit_space=1, count=12, player=None):
    sq = object.__new__(Square)
    w = int(width * PRECISION)
    sq.xmin = 0
    sq.xmax = w
    sq.ymin = 0
    sq.ymax = w
    sq.x = w // 2
    sq.y = w // 2
    sq.objects = [
        types.SimpleNamespace(
            space=int(unit_space * PRECISION),
            airground_type="ground",
            player=player,
        )
        for _ in range(count)
    ]
    return sq


def test_max_train_count_for_square_space_blocks_when_full():
    p = _player()
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(
        space=1 * PRECISION,
        airground_type="ground",
    )
    order.unit = types.SimpleNamespace(place=_square(player=p), player=p)
    assert order._max_train_count_for_square_space(1) == 0
    assert order._max_train_count_for_square_space(3) == 0


def test_max_train_count_for_square_space_limits_batch():
    p = _player()
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(
        space=1 * PRECISION,
        airground_type="ground",
    )
    # 10 peasants already → room for 2 more at space 1
    order.unit = types.SimpleNamespace(place=_square(count=10, player=p), player=p)
    assert order._max_train_count_for_square_space(5) == 2


def test_max_train_count_space_zero_unlimited():
    p = _player()
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(space=0, airground_type="ground")
    order.unit = types.SimpleNamespace(place=_square(player=p), player=p)
    assert order._max_train_count_for_square_space(4) == 4


def test_max_train_count_ignores_enemy_occupancy():
    enemy = _player("e")
    me = _player("m")
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(
        space=1 * PRECISION,
        airground_type="ground",
    )
    # Enemy filled the square; our side still has full room.
    order.unit = types.SimpleNamespace(place=_square(player=enemy), player=me)
    assert order._max_train_count_for_square_space(5) == 5
