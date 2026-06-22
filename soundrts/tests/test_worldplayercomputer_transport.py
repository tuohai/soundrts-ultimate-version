"""Computer AI transport mode: amphibious landing vs airborne assault."""
from __future__ import annotations

import types

from soundrts.worldplayercomputer import Computer


def test_choose_transport_mode_none_when_walking_works():
    comp = Computer.__new__(Computer)
    comp._unit_can_reach = lambda u, p: True
    assert comp._choose_transport_mode([object()], object()) is None


def test_choose_transport_mode_prefers_air_when_only_airlift():
    comp = Computer.__new__(Computer)
    comp._unit_can_reach = lambda u, p: False
    comp._amphibious_transport_cost = lambda u, p: float("inf")
    comp._airborne_transport_cost = lambda u, p: 100
    assert comp._choose_transport_mode([object()], object()) == "airborne"


def test_choose_transport_mode_prefers_amphibious_when_cheaper():
    comp = Computer.__new__(Computer)
    comp._unit_can_reach = lambda u, p: False
    comp._amphibious_transport_cost = lambda u, p: 50
    comp._airborne_transport_cost = lambda u, p: 200
    assert comp._choose_transport_mode([object()], object()) == "amphibious"


def test_choose_transport_mode_prefers_air_on_tie():
    comp = Computer.__new__(Computer)
    comp._unit_can_reach = lambda u, p: False
    comp._amphibious_transport_cost = lambda u, p: 100
    comp._airborne_transport_cost = lambda u, p: 100
    assert comp._choose_transport_mode([object()], object()) == "airborne"


def test_unit_can_reach_unwraps_inside_destination():
    outside = types.SimpleNamespace(id=2, shortest_path_distance_to=lambda *a, **k: 0)
    inside = types.SimpleNamespace(is_inside_place=True, outside=outside)

    class Origin:
        id = 1

        def shortest_path_distance_to(self, *args, **kwargs):
            return 0

        def shortest_path_to(self, dest, *args, **kwargs):
            assert dest is outside
            return [self, dest]

    unit = types.SimpleNamespace(
        airground_type="ground",
        is_inside=False,
        place=Origin(),
    )
    comp = Computer.__new__(Computer)

    assert comp._unit_can_reach(unit, inside)


def test_send_unit_to_place_uses_transport_when_ground_path_blocked(monkeypatch):
    footman = types.SimpleNamespace(
        airground_type="ground",
        speed=1,
        place=types.SimpleNamespace(id=1),
        orders=[],
        cancel_all_orders=lambda: footman.orders.clear(),
        take_order=lambda cmd, **kw: footman.orders.append(cmd),
    )
    dest = types.SimpleNamespace(
        id=2, is_water=False, shortest_path_distance_to=lambda *a, **k: 0
    )
    comp = Computer.__new__(Computer)
    comp._world_place_for_unit = lambda u: u.place
    comp._unit_path = lambda *a, **k: []
    comp._choose_transport_mode = lambda units, place: "airborne"
    comp._send_ground_units_amphibious = lambda units, place: []
    sent = []

    def _airborne(units, place):
        sent.extend(units)
        return units

    comp._send_ground_units_airborne = _airborne
    comp._friendly_presence = lambda place: False
    comp._cataclysm_users = []
    comp._summon_users = []
    comp._detector_users = []
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.movement_target_for_unit",
        lambda unit, place, player: place,
    )
    comp._send_unit_to_place(footman, dest, False, [])
    assert footman in sent


def test_send_ground_units_airborne_orders_load_and_unload(monkeypatch):
    load_land = types.SimpleNamespace(id=1)
    unload_land = types.SimpleNamespace(id=2, is_water=False)
    dest = types.SimpleNamespace(
        id=3, is_water=False, shortest_path_distance_to=lambda *a, **k: 0
    )
    footman = types.SimpleNamespace(
        airground_type="ground",
        speed=1,
        place=load_land,
        orders=[],
        is_inside=False,
        transport_volume=1,
        cancel_all_orders=lambda: footman.orders.clear(),
        take_order=lambda cmd, **kw: footman.orders.append(cmd),
    )
    flyer = types.SimpleNamespace(
        airground_type="air",
        transport_capacity=8,
        speed=1,
        place=load_land,
        orders=[],
        is_inside=False,
        inside=types.SimpleNamespace(objects=[]),
        cancel_all_orders=lambda: flyer.orders.clear(),
        take_order=lambda cmd, **kw: flyer.orders.append(cmd),
    )
    comp = Computer.__new__(Computer)
    comp._world_place_for_unit = lambda u: load_land
    comp._available_air_transports = lambda: [flyer]
    comp._air_path_distance = lambda a, b: 0
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.movement_target_for_unit",
        lambda unit, place, player: unload_land,
    )
    sent = comp._send_ground_units_airborne([footman], dest)
    assert sent == [footman]
    assert ["load_all", load_land.id] in flyer.orders
    assert ["unload_all", unload_land.id] in flyer.orders
    assert footman.orders[-1] == ["go", dest.id]
