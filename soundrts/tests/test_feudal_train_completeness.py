# -*- coding: utf-8 -*-
"""Feudal time_cost -5 must apply once; proportion bar must not skip ticks."""
from __future__ import annotations

import logging
import os
import sys
import types
import warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import to_int
    from soundrts.lib.resource import res
    from soundrts.worldorders.production import (
        ProductionOrder,
        TrainOrder,
        completeness_values_between,
    )

sys.argv = saved


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def test_completeness_values_between_fills_jumps():
    assert completeness_values_between(None, 0) == [0]
    assert completeness_values_between(1, 3) == [2, 3]
    assert completeness_values_between(7, 9) == [8, 9]
    assert completeness_values_between(4, 4) == []
    assert completeness_values_between(10, 10) == []


def test_short_duration_notifies_every_proportion_tick():
    notifies = []
    order = ProductionOrder.__new__(ProductionOrder)
    order.time = 2000
    order._completeness_duration = 2000
    order._previous_completeness = None
    order.unit = types.SimpleNamespace(notify=lambda ev: notifies.append(ev))
    order._notify_completeness()
    while order.time > 0:
        order.time -= VIRTUAL_TIME_INTERVAL
        order._notify_completeness()
    got = [int(e.split(",")[1]) for e in notifies if e.startswith("completeness,")]
    assert got == list(range(0, 11)), got


def test_feudal_footman_train_time_is_seven_seconds(res_loaded):
    """phase_bonus time_cost -5 is player-level; must not also apply from the pool."""
    ft = rules.unit_class("footman")
    feudal = rules.unit_class("feudal_age")
    if ft is None or feudal is None:
        pytest.skip("default res footman/feudal_age not present")
    player = types.SimpleNamespace(
        upgrades=[],
        units=[],
        resources=[to_int("100"), to_int("100")],
        phase_time_cost_bonus=0,
        phase_time_cost_percent_bonus=0.0,
        phase_cost_bonus=[0, 0, 0, 0],
        phase_cost_percent_bonus=[0.0, 0.0, 0.0, 0.0],
        _phase_bonus_pool=[],
        faction="human_faction",
        current_phase=None,
        level=lambda n: 1,
    )
    feudal.upgrade_player(player)
    pool_stats = []
    for entry in player._phase_bonus_pool:
        args = entry[0] if entry else ()
        pool_stats.extend(args[i] for i in range(0, len(args), 2))
    assert "time_cost" not in pool_stats
    assert "cost" not in pool_stats
    assert player.phase_time_cost_bonus == to_int("-5")

    building = types.SimpleNamespace(
        player=player,
        orders=[],
        place=types.SimpleNamespace(),
        rallying_point=None,
        is_a_building=True,
        check_if_enough_resources=lambda cost, food=0: None,
        notify=lambda *a, **k: None,
        can_train={"footman": 1},
    )
    order = TrainOrder(building, ["footman"])
    order.type = ft
    assert order.time_cost == to_int("7"), order.time_cost
    assert order.time_cost == ft.time_cost + to_int("-5")
    assert ft.time_cost == to_int("12")
