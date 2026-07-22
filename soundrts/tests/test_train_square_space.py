"""TrainOrder should refuse when the spawn square is full (abstract space)."""

import types

from soundrts.lib.nofloat import PRECISION
from soundrts.worldorders.production import TrainOrder
from soundrts.worldroom import Square


def _full_square(width=12, unit_space=1, count=12):
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
        )
        for _ in range(count)
    ]
    return sq


def test_max_train_count_for_square_space_blocks_when_full():
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(
        space=1 * PRECISION,
        airground_type="ground",
    )
    order.unit = types.SimpleNamespace(place=_full_square())
    assert order._max_train_count_for_square_space(1) == 0
    assert order._max_train_count_for_square_space(3) == 0


def test_max_train_count_for_square_space_limits_batch():
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(
        space=1 * PRECISION,
        airground_type="ground",
    )
    # 10 peasants already → room for 2 more at space 1
    order.unit = types.SimpleNamespace(place=_full_square(count=10))
    assert order._max_train_count_for_square_space(5) == 2


def test_max_train_count_space_zero_unlimited():
    order = object.__new__(TrainOrder)
    order.type = types.SimpleNamespace(space=0, airground_type="ground")
    order.unit = types.SimpleNamespace(place=_full_square())
    assert order._max_train_count_for_square_space(4) == 4
