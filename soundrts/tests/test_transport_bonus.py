"""运输容器 load_bonus / passenger_bonus 属性加成。"""
from __future__ import annotations

import types

from soundrts.worldunit.world_transport import (
    _apply_transport_bonus,
    _remove_transport_bonus,
)


def test_load_bonus_scales_speed_and_applies_mdg():
    unit = types.SimpleNamespace(speed=1500, mdg=5)
    stats = {}
    _apply_transport_bonus(unit, {"speed": 0.5, "mdg": 2}, stats)
    assert unit.speed == 2000
    assert unit.mdg == 2005
    assert stats == {"speed": 500, "mdg": 2000}


def test_remove_transport_bonus_restores_values():
    unit = types.SimpleNamespace(speed=2000, mdg=2005)
    stats = {"speed": 500, "mdg": 2000}
    _remove_transport_bonus(unit, stats)
    assert unit.speed == 1500
    assert unit.mdg == 5
    assert stats == {}


def test_passenger_bonus_tracked_separately_from_container():
    container = types.SimpleNamespace(speed=1000)
    passenger = types.SimpleNamespace(rdg_range=4)
    container_stats = {}
    passenger_stats = {}
    _apply_transport_bonus(container, {"speed": 0.5}, container_stats)
    _apply_transport_bonus(passenger, {"rdg_range": 1}, passenger_stats)
    assert container.speed == 1500
    assert passenger.rdg_range == 1004
    _remove_transport_bonus(container, container_stats)
    _remove_transport_bonus(passenger, passenger_stats)
    assert container.speed == 1000
    assert passenger.rdg_range == 4


def test_load_bonus_dotted_vs_updates_dict():
    unit = types.SimpleNamespace(speed=600, mdg_vs={"building": 150000})
    stats = {}
    _apply_transport_bonus(
        unit, {"speed": 0.05, "mdg_vs.building": 10}, stats
    )
    assert unit.speed == 650
    assert unit.mdg_vs["building"] == 160000
    assert stats == {"speed": 50, "mdg_vs.building": 10000}
    _remove_transport_bonus(unit, stats)
    assert unit.speed == 600
    assert unit.mdg_vs["building"] == 150000
    assert stats == {}


def test_passenger_bonus_dotted_vs_updates_dict():
    """passenger_bonus uses the same dotted vs path as load_bonus."""
    passenger = types.SimpleNamespace(mdg_vs={"building": 5000, "siege_unit": 0})
    stats = {}
    _apply_transport_bonus(passenger, {"mdg_vs.building": 10}, stats)
    assert passenger.mdg_vs["building"] == 15000
    assert passenger.mdg_vs["siege_unit"] == 0
    assert stats == {"mdg_vs.building": 10000}
    _remove_transport_bonus(passenger, stats)
    assert passenger.mdg_vs["building"] == 5000
    assert stats == {}


def test_load_bonus_dotted_cover_vs_is_scaled():
    unit = types.SimpleNamespace(mdg_cover_vs={"footman": 0})
    stats = {}
    _apply_transport_bonus(unit, {"mdg_cover_vs.footman": 10}, stats)
    assert unit.mdg_cover_vs["footman"] == 10000
    assert stats == {"mdg_cover_vs.footman": 10000}
    _remove_transport_bonus(unit, stats)
    assert unit.mdg_cover_vs["footman"] == 0
