"""jl6 map + advanced AI: goldmine deposits and build-target validation."""
from __future__ import annotations

import logging
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
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldplayercomputer_sc_build import (
        choose_build_target,
        resolve_build_target,
    )

sys.argv = saved_argv

ROOT = Path(__file__).resolve().parents[2]
JL6 = ROOT / "res" / "multi" / "jl6.txt"


@pytest.fixture(autouse=True)
def load_rules():
    res.load_rules_and_ai()


def _load_jl6_world():
    world = World([], 42)
    world._parse_map(JL6.read_text(encoding="utf-8"))
    world._build_map()
    return world


def _populate_jl6(ai_type="advanced"):
    world = _load_jl6_world()
    human = DirectClient("p1", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai_client = DummyClient(ai_type)
    ai_client.faction = rules.factions[0]
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False)
    world._update_buckets()
    return world


def _goldmines_on_map(world):
    found = []
    for sq in world.squares:
        for obj in sq.objects:
            if getattr(obj, "type_name", None) == "goldmine":
                found.append(obj)
    return found


def test_jl6_map_loads_goldmines_with_positive_qty():
    world = _load_jl6_world()
    goldmines = _goldmines_on_map(world)
    assert len(goldmines) >= 1
    assert all(getattr(g, "qty", 0) > 0 for g in goldmines)


def test_deposit_init_accepts_integer_qty():
    from soundrts.worldresource import Deposit

    world = types.SimpleNamespace(map_deposit_capacity=[0, 0, 0, 0])
    sq = types.SimpleNamespace(
        id=1,
        x=0,
        y=0,
        world=world,
        is_inside_place=False,
        objects=[],
        neighbors=[],
    )
    sq.enter = lambda _o: None
    sq.leave = lambda _o: None
    sq.add = lambda _o: None
    sq.find_free_space_for = lambda _o, x, y: (x or 0, y or 0)

    class TestDeposit(Deposit):
        collision = 0
        resource_type = "resource1"

    deposit = TestDeposit(sq, 75)
    assert deposit.qty == 75 * PRECISION


def test_resolve_build_target_rejects_goldmine_for_barracks():
    barracks = rules.unit_class("barracks")
    base = types.SimpleNamespace(id=1, x=0, y=0, neighbors=[], objects=[])

    class _Deposit:
        id = 99
        type_name = "goldmine"
        place = base
        x = 0
        y = 0

    deposit = _Deposit()
    _world = types.SimpleNamespace()

    class AI:
        world = _world
        units = []
        perception = {deposit}
        memory = set()

        def check_type(self, o, c):
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

        def _builders_place(self):
            return base

    assert resolve_build_target(AI(), barracks, deposit) is None


def test_get_requirements_skips_unbuildable_deposit(monkeypatch):
    rules.load(
        """
def parameters
nb_of_resource_types 2

def peasant
class worker
can_build townhall needs_mine

def townhall
class building

def needs_mine
class building
requirements goldmine

def goldmine
class deposit
resource_type resource1
"""
    )
    calls = []

    comp = Computer.__new__(Computer)
    comp.has = lambda name: False
    comp._get = lambda nb, types: calls.append(types) or False

    needs_mine = rules.unit_class("needs_mine")
    assert comp._get_requirements(needs_mine) is False
    assert calls == []


def test_choose_build_target_returns_meadow_not_square_for_barracks(monkeypatch):
    from soundrts.tests.test_worldplayercomputer_sc_build import _Meadow, _Square

    world = types.SimpleNamespace()
    b1 = _Square(1, 100, 100)
    b1.world = world
    meadow = _Meadow(10, b1, 100, 100)
    barracks = rules.unit_class("barracks")
    _world = world

    class AI:
        id = 1
        world = _world
        units = [meadow]
        perception = {meadow}
        memory = set()

        def check_type(self, o, c):
            from soundrts.worldresource import Meadow

            if c is Meadow:
                return isinstance(o, _Meadow)
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

        def _builders_place(self):
            return b1

    monkeypatch.setattr(
        "soundrts.worldplayercomputer_sc_build.build_site_valid",
        lambda ai, bt, place, x, y: True,
    )
    chosen = choose_build_target(AI(), barracks, starting_place=b1)
    assert chosen is meadow


def test_jl6_advanced_ai_no_goldmine_build_warnings(caplog):
    caplog.set_level(logging.WARNING)
    world = _populate_jl6("advanced")
    comp = next(p for p in world.players if isinstance(p, Computer))
    assert comp.AI_type == "advanced"

    for _ in range(1000):
        world.update()

    bad = [
        r.message
        for r in caplog.records
        if "创建单位时出错" in r.message and "goldmine()" in r.message
    ]
    assert bad == []


def test_idle_resource_buildings_skip_farm_cultivate_without_wood():
    comp = Computer.__new__(Computer)
    comp.resources = [1000, 0, 1000]
    farm_cls = rules.unit_class("farm")
    farm = types.SimpleNamespace(
        is_a_building=True,
        is_producing=False,
        orders=[],
        auto_cultivate=1,
        auto_production=0,
        type=farm_cls,
    )
    farm.take_order = lambda *a, **k: orders.append(a)
    orders = []
    comp.units = [farm]
    comp.missing_resources = Computer.missing_resources.__get__(comp, Computer)
    comp._can_afford_production_cost = Computer._can_afford_production_cost.__get__(
        comp, Computer
    )
    comp._idle_resource_buildings_produce()
    assert orders == []


def test_maintain_resource_buildings_skips_farm_when_wood_gone():
    comp = Computer.__new__(Computer)
    comp.resources = [1000, 0, 0]
    comp._workers = [object()]
    comp._can_afford_production_cost = lambda cls: False
    comp._has_reachable_deposit = lambda idx: False
    calls = []
    comp._ensure_resource_buildings = lambda low: calls.append(low)
    comp._maintain_resource_buildings()
    assert 2 not in calls[0]


def test_try_remote_deposit_expansion_sends_workers_by_boat(monkeypatch):
    from soundrts.worldresource import Deposit

    base = types.SimpleNamespace(id=1)
    wood_place = types.SimpleNamespace(id=2)
    base.shortest_path_distance_to = lambda dest, player, avoid=False: float("inf")

    class _Wood(Deposit):
        type_name = "wood"
        resource_type = "resource2"
        collision = 0

    wood = _Wood.__new__(_Wood)
    wood.id = 50
    wood.place = wood_place
    wood.qty = 1000
    worker = types.SimpleNamespace(
        orders=[],
        place=base,
        airground_type="ground",
        transport_volume=1,
        can_gather_deposit=["wood", "goldmine"],
        cancel_all_orders=lambda: worker.orders.clear(),
        take_order=lambda cmd, **kw: worker.orders.append(cmd),
    )
    boat = types.SimpleNamespace(
        place=types.SimpleNamespace(id=3),
        transport_capacity=8,
        inside=types.SimpleNamespace(objects=[]),
        orders=[],
        cancel_all_orders=lambda: boat.orders.clear(),
        take_order=lambda cmd, **kw: boat.orders.append(cmd),
    )

    comp = Computer.__new__(Computer)
    comp.resources = [1000, 0, 1000]
    comp.world = types.SimpleNamespace(squares=[])
    comp._workers = [worker]
    comp.units = [worker, boat]
    comp.perception = {wood}
    comp.memory = set()
    comp._builders_place = lambda: base
    comp._map_has_water = lambda: True
    comp._gather_target_ok = Computer._gather_target_ok.__get__(comp, Computer)
    comp._deposit_resource_index = Computer._deposit_resource_index.__get__(comp, Computer)
    comp._worker_can_gather_deposit = Computer._worker_can_gather_deposit.__get__(
        comp, Computer
    )
    comp._reachable_deposits = Computer._reachable_deposits.__get__(comp, Computer)
    comp._available_water_transports = lambda: [boat]
    comp.nb = lambda name: 0
    comp.future_nb = lambda name: 0
    comp.equivalent = lambda name: name
    comp.get = lambda *a, **k: None
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.find_amphibious_crossing",
        lambda start, dest, player: (base, boat.place, boat.place, wood_place),
    )
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.is_ground_worker",
        lambda u: u is worker,
    )
    sent = []
    comp._send_ground_units_amphibious = lambda units, dest: sent.extend(units) or units
    comp._send_workers_to_gather_amphibious = (
        Computer._send_workers_to_gather_amphibious.__get__(comp, Computer)
    )
    assert comp._try_remote_deposit_expansion(1)
    assert worker in sent
    assert worker.orders[-1][0] == "gather"


def test_try_remote_deposit_expansion_requests_townhall_for_gold(monkeypatch):
    from soundrts.worldresource import Deposit

    base = types.SimpleNamespace(id=1)
    gold_place = types.SimpleNamespace(id=2)
    base.shortest_path_distance_to = lambda dest, player, avoid=False: float("inf")

    class _Goldmine(Deposit):
        type_name = "goldmine"
        resource_type = "resource1"
        collision = 0

    gold = _Goldmine.__new__(_Goldmine)
    gold.id = 60
    gold.place = gold_place
    gold.qty = 1000
    worker = types.SimpleNamespace(
        orders=[],
        place=base,
        airground_type="ground",
        transport_volume=1,
        can_gather_deposit=["goldmine", "wood"],
        take_order=lambda cmd, **kw: worker.orders.append(cmd),
    )
    boat = types.SimpleNamespace(
        place=types.SimpleNamespace(id=3),
        transport_capacity=8,
        inside=types.SimpleNamespace(objects=[]),
        orders=[],
    )
    get_calls = []

    comp = Computer.__new__(Computer)
    comp.resources = [0, 1000, 1000]
    comp.world = types.SimpleNamespace(squares=[])
    comp._workers = [worker]
    comp.units = [worker, boat]
    comp.perception = {gold}
    comp.memory = set()
    comp._builders_place = lambda: base
    comp._map_has_water = lambda: True
    comp._gather_target_ok = Computer._gather_target_ok.__get__(comp, Computer)
    comp._deposit_resource_index = Computer._deposit_resource_index.__get__(comp, Computer)
    comp._worker_can_gather_deposit = Computer._worker_can_gather_deposit.__get__(
        comp, Computer
    )
    comp._reachable_deposits = Computer._reachable_deposits.__get__(comp, Computer)
    comp._available_water_transports = lambda: [boat]
    comp.nb = lambda name: 0
    comp.future_nb = lambda name: 0
    comp.equivalent = lambda name: name
    comp.get = lambda n, t: get_calls.append(t)
    comp._send_ground_units_amphibious = lambda units, dest: units
    comp._send_workers_to_gather_amphibious = (
        Computer._send_workers_to_gather_amphibious.__get__(comp, Computer)
    )
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.find_amphibious_crossing",
        lambda start, dest, player: (base, boat.place, boat.place, gold_place),
    )
    monkeypatch.setattr(
        "soundrts.worldplayercomputer.is_ground_worker",
        lambda u: u is worker,
    )
    assert comp._try_remote_deposit_expansion(0)
    assert "townhall" in get_calls
