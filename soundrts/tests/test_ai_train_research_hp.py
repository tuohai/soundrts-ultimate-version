"""ai.txt train_time / research_time / unit_hp multipliers."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.worldorders.base import ComplexOrder
from soundrts.worldunit.worldcreature import Creature


class _TrainOrder(ComplexOrder):
    keyword = "train"


class _ResearchOrder(ComplexOrder):
    keyword = "research"


def test_ai_train_time_percent_scales_order_time():
    order = _TrainOrder.__new__(_TrainOrder)
    order.type = SimpleNamespace(time_cost=1000)
    order.unit = SimpleNamespace(
        player=SimpleNamespace(ai_train_time_percent=50, upgrades=[]),
        _buff_time_cost_percent=0,
    )
    assert order.time_cost == 500


def test_ai_research_time_percent_scales_order_time():
    order = _ResearchOrder.__new__(_ResearchOrder)
    order.type = SimpleNamespace(time_cost=1000)
    order.unit = SimpleNamespace(
        player=SimpleNamespace(ai_research_time_percent=80, upgrades=[]),
        _buff_time_cost_percent=0,
    )
    assert order.time_cost == 800


def test_ai_unit_hp_percent_scales_creature_hp():
    creature = Creature.__new__(Creature)
    creature.player = SimpleNamespace(
        is_computer_player=True,
        neutral=False,
        ai_unit_hp_percent=120,
    )
    creature.world = SimpleNamespace(enemy_hp_factor=100)
    creature.hp_max = 1000
    creature.hp = 1000
    creature.hp_soldier_max = 0
    creature._apply_ai_unit_hp()
    assert creature.hp_max == 1200
    assert creature.hp == 1200
