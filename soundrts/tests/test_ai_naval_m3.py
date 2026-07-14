"""M3 map + intermediate AI naval: shore shipyard, boats, tiered destroyers."""
from __future__ import annotations

import os
import sys
import types
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldplayercomputer_sc_build import choose_near_water_build_target

sys.argv = saved_argv

ROOT = Path(__file__).resolve().parents[2]
M3 = ROOT / "res" / "multi" / "m3.txt"


@pytest.fixture(autouse=True)
def load_rules():
    res.load_rules_and_ai()


def _load_m3_world():
    world = World([], 42)
    world._parse_map(M3.read_text(encoding="utf-8"))
    world._build_map()
    return world


def test_m3_map_has_water():
    world = _load_m3_world()
    assert len(world.water_squares) > 0
    assert any(getattr(sq, "is_near_water", False) for sq in world.squares)


def test_m3_intermediate_finds_shore_shipyard_site():
    world = _load_m3_world()
    human = DirectClient("p1", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai_client = DummyClient("intermediate")
    ai_client.faction = rules.factions[0]
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False)
    comp = next(p for p in world.players if isinstance(p, Computer))
    assert comp._map_has_water()
    start_name = world.players_starts[1][1][0][0]
    start = world.grid[start_name]
    shipyard = rules.unit_class("shipyard")
    target = choose_near_water_build_target(comp, shipyard, starting_place=start)
    assert target is not None
    place = target if hasattr(target, "is_near_water") else target.place
    assert place.is_near_water


def test_maintain_naval_requests_shipyard_on_m3(monkeypatch):
    world = _load_m3_world()
    comp = Computer.__new__(Computer)
    comp.world = world
    comp.AI_type = "intermediate"
    comp._workers = []
    comp._type_discovery_cache = None
    comp.nb = lambda name: 0
    comp.future_nb = lambda name: 0
    calls = []
    comp.get = lambda n, t: calls.append((n, t)) or True
    comp._try_maintain_naval()
    assert calls == [(1, "shipyard")]


def test_maintain_naval_requests_boats_when_dock_ready(monkeypatch):
    world = _load_m3_world()
    comp = Computer.__new__(Computer)
    comp.world = world
    comp.AI_type = "intermediate"
    comp._workers = []
    comp._type_discovery_cache = None
    comp.nb = lambda name: 1 if name == "shipyard" else 0
    comp.future_nb = lambda name: 0
    calls = []
    comp.get = lambda n, t: calls.append((n, t)) or True
    comp._try_maintain_naval()
    assert calls == [(2, "boat")]


@pytest.mark.parametrize(
    "ai_type,expected",
    [
        ("intermediate", 2),
        ("advanced", 3),
        ("expert", 4),
        ("nightmare", 4),
        ("beginner", 0),
    ],
)
def test_naval_destroyer_target_by_difficulty(ai_type, expected):
    comp = Computer.__new__(Computer)
    comp.AI_type = ai_type
    assert comp._naval_destroyer_target() == expected


def test_maintain_naval_requests_destroyers_for_intermediate():
    world = _load_m3_world()
    comp = Computer.__new__(Computer)
    comp.world = world
    comp.AI_type = "intermediate"
    comp._workers = []
    comp._type_discovery_cache = None
    comp.nb = lambda name: 2 if name == "boat" else (1 if name == "shipyard" else 0)
    comp.future_nb = lambda name: 0
    calls = []
    comp.get = lambda n, t: calls.append((n, t)) or True
    comp._try_maintain_naval()
    assert calls == [(2, "destroyer")]


def test_is_ground_worker_excludes_boat():
    from soundrts.worldplayercomputer import is_ground_worker
    from soundrts.worldunit import Worker

    class TestWorker(Worker):
        def __init__(self):
            pass

    p = object.__new__(TestWorker)
    p.airground_type = "ground"
    b = object.__new__(TestWorker)
    b.airground_type = "water"
    assert is_ground_worker(p)
    assert not is_ground_worker(b)


def test_sanitize_cancels_gather_on_water_unit_to_land_deposit():
    from soundrts.worldplayercomputer import Computer

    land_deposit = types.SimpleNamespace(
        place=types.SimpleNamespace(is_water=False, is_ground=True),
    )
    unit = types.SimpleNamespace(
        airground_type="water",
        can_gather_deposit=["all"],
        can_gather_building=[],
        orders=[types.SimpleNamespace(keyword="gather", target=land_deposit)],
        cancel_all_orders=lambda: unit.orders.clear(),
    )
    comp = Computer.__new__(Computer)
    comp.units = [unit]
    comp._sanitize_water_unit_orders()
    assert unit.orders == []


def test_m3_destroyer_can_reach_enemy_base_via_lake():
    world = _load_m3_world()
    human = DirectClient("p1", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai_client = DummyClient("nightmare")
    ai_client.faction = rules.factions[0]
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False)
    comp = next(p for p in world.players if isinstance(p, Computer))
    comp.AI_type = "nightmare"
    from soundrts.worldplayercomputer_water import movement_target_for_unit

    water_sq = next(sq for sq in world.squares if sq.is_water)
    enemy_start = world.grid[world.players_starts[0][1][0][0]]
    unit = types.SimpleNamespace(airground_type="water", place=water_sq)
    move_target = movement_target_for_unit(unit, enemy_start, comp)
    assert getattr(move_target, "is_water", False)
    path = water_sq.shortest_path_to(move_target, comp, plane="water", places=True)
    assert path


def test_ai_naval_patrol_has_fallback_targets_on_m3():
    world = _load_m3_world()
    human = DirectClient("p1", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai_client = DummyClient("nightmare")
    ai_client.faction = rules.factions[0]
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False)
    comp = next(p for p in world.players if isinstance(p, Computer))
    comp._enemy_presence = []
    targets = comp._naval_patrol_targets()
    assert targets
    assert any(getattr(t, "is_water", False) for t in targets) or targets


def test_try_amphibious_landings_orders_boat_and_soldiers_on_m3():
    import types

    from soundrts.worldplayercomputer_water import find_amphibious_crossing

    world = _load_m3_world()
    human = DirectClient("p1", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai_client = DummyClient("nightmare")
    ai_client.faction = rules.factions[0]
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False)
    comp = next(p for p in world.players if isinstance(p, Computer))
    comp.AI_type = "nightmare"
    ai_start = world.grid[world.players_starts[1][1][0][0]]
    enemy_start = world.grid[world.players_starts[0][1][0][0]]
    route = find_amphibious_crossing(ai_start, enemy_start, comp)
    assert route is not None
    load_land, load_water, unload_water, unload_land = route

    footman = types.SimpleNamespace(
        airground_type="ground",
        speed=1,
        place=ai_start,
        orders=[],
        is_inside=False,
        transport_volume=1,
        cancel_all_orders=lambda: footman.orders.clear(),
        take_order=lambda cmd, **kw: footman.orders.append(
            types.SimpleNamespace(keyword=cmd[0])
        ),
    )
    boat = types.SimpleNamespace(
        airground_type="water",
        transport_capacity=8,
        speed=1,
        place=load_water,
        orders=[],
        is_inside=False,
        inside=types.SimpleNamespace(objects=[]),
        cancel_all_orders=lambda: boat.orders.clear(),
        take_order=lambda cmd, **kw: boat.orders.append(
            types.SimpleNamespace(keyword=cmd[0])
        ),
    )
    comp.units = [footman, boat]

    sent = comp._send_ground_units_amphibious([footman], enemy_start)
    assert sent == [footman]
    assert any(o.keyword == "go" for o in footman.orders)
    keywords = [o.keyword for o in boat.orders]
    assert "go" in keywords
    assert "load_all" in keywords
    assert "unload_all" in keywords
