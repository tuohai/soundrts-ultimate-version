"""Regression: AI build must displace imperative auto_explore.

AutoExploreOrder is imperative, so a normal take_order(['build', ...]) only
queues behind it and never runs. Counting those stuck builds in future_nb made
the AI believe barracks were already in production — deadlock, no barracks.
"""
from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL as VTI
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit.worldcreature import BuildingSite

sys.argv = saved_argv

ROOT = Path(__file__).resolve().parents[2]
M2 = ROOT / "res" / "multi" / "m2.txt"


@pytest.fixture(autouse=True)
def load_rules():
    logging.disable(logging.CRITICAL)
    res.load_rules_and_ai()


def test_nb_in_production_ignores_build_queued_behind_auto_explore():
    ai = Computer.__new__(Computer)
    barracks = rules.unit_class("barracks")
    assert barracks is not None

    stuck = SimpleNamespace(
        orders=[
            SimpleNamespace(keyword="auto_explore", is_deferred=False, type=None),
            SimpleNamespace(keyword="build", is_deferred=False, type=barracks),
        ],
    )
    active = SimpleNamespace(
        orders=[
            SimpleNamespace(keyword="build", is_deferred=False, type=barracks),
        ],
    )
    site = BuildingSite.__new__(BuildingSite)
    site.type = barracks

    ai.units = [stuck, active, site]
    assert Computer._nb_in_production(ai, "barracks") == 2
    assert Computer._nb_in_production(ai, ["barracks"]) == 2


def test_order_requisition_stops_auto_explore_before_build():
    ai = Computer.__new__(Computer)
    ai._orders = {}
    ai._gathered_deposits = {}
    meadow = SimpleNamespace(id="m1")
    peasant = SimpleNamespace(
        orders=[
            SimpleNamespace(keyword="auto_explore", is_deferred=False, type=None),
        ],
        place=SimpleNamespace(id="p1"),
        type_name="peasant",
        can_build=("barracks",),
        player=ai,
    )
    stops = []

    def take_order(order, *args, **kwargs):
        stops.append(list(order))
        if order[0] == "stop":
            peasant.orders = []
        elif order[0] == "build":
            peasant.orders = [
                SimpleNamespace(
                    keyword="build",
                    is_deferred=False,
                    type=rules.unit_class("barracks"),
                    is_complete=False,
                    unit=peasant,
                )
            ]

    peasant.take_order = take_order
    ai.units = [peasant]
    ai.check_type = lambda u, types: True
    ai.get_object_by_id = lambda _id: meadow
    ai.has_all = lambda *_a, **_k: True

    # Bypass BuildOrder.is_allowed (needs full unit/player graph).
    import soundrts.worldorders.production as prod

    orig_allowed = prod.BuildOrder.is_allowed
    prod.BuildOrder.is_allowed = staticmethod(lambda *_a, **_k: True)
    try:
        Computer.order(
            ai,
            1,
            "peasant",
            ["build", "barracks", meadow.id],
            near=meadow,
            requisition=True,
        )
    finally:
        prod.BuildOrder.is_allowed = orig_allowed

    assert stops[0] == ["stop"]
    assert stops[1][0] == "build"
    assert peasant.orders[0].keyword == "build"


def _load_m2_with_beginners(n_ai=8):
    world = World([], 42)
    world._parse_map(M2.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    clients = []
    human = DirectClient("human", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    clients.append(human)
    for i in range(n_ai):
        c = DummyClient("beginner")
        c.faction = rules.factions[0]
        c.alliance = str(i + 2)
        clients.append(c)
    world.populate_map(clients, random_starts=False)
    return world


def test_m2_beginner_ais_build_barracks():
    """m2 + 8 beginner: after feudal age, at least one AI must finish a barracks."""
    world = _load_m2_with_beginners(8)
    computers = [p for p in world.players if isinstance(p, Computer)]
    assert len(computers) == 8
    assert all(len(p.units) > 0 for p in computers)

    deadline = 400_000  # ~6.7 min game time; feudal ~130s then build
    while world.time < deadline:
        world.update()
        if any(
            sum(1 for u in p.units if u.type_name == "barracks") > 0
            for p in computers
        ):
            break

    barracks_total = sum(
        1 for p in computers for u in p.units if u.type_name == "barracks"
    )
    sites = [
        getattr(u.type, "type_name", None)
        for p in computers
        for u in p.units
        if isinstance(u, BuildingSite)
    ]
    assert barracks_total >= 1 or "barracks" in sites, (
        f"no barracks after {world.time}ms; sites={sites}; "
        f"samples={[ {u.type_name: sum(1 for x in p.units if x.type_name==u.type_name) for u in p.units} for p in computers[:2]]}"
    )


def test_get_exception_handler_does_not_shadow_builtin_type():
    """_get used to do type(e) while looping 'for type in types', calling Unit.__init__."""
    ai = Computer.__new__(Computer)
    ai._safe_cnt = 0
    ai.resources = [999999, 999999, 999999]
    ai.units = []
    ai._orders = {}
    ai._gathered_deposits = {}
    ai._workers = []

    knight = rules.unit_class("knight")
    assert knight is not None
    makers = rules.get_makers(knight)
    assert makers

    def nb(types_arg, *_a, **_k):
        # Not yet owned: requesting knight itself must be 0.
        names = types_arg if isinstance(types_arg, (list, tuple)) else [types_arg]
        for n in names:
            name = n if isinstance(n, str) else getattr(n, "__name__", None)
            if name == "knight" or n is knight:
                return 0
        return 1  # pretend makers exist

    ai.nb = nb
    ai.future_nb = lambda *_a, **_k: 0

    def boom(*_a, **_k):
        raise RuntimeError("inject")

    ai.build_or_train_or_upgradeto_or_summon = boom

    # Must not raise TypeError from type(e) shadowing; returns False after warning.
    assert Computer._get(ai, 1, [knight]) is False


def test_get_blocks_lumbermill_wood_reentrancy():
    """get(lumbermill) must not recurse via gather→ensure wood storage→get(lumbermill)."""
    ai = Computer.__new__(Computer)
    ai._getting = set()
    ai._map_has_water = lambda: False
    ai._type_needs_water = lambda *_a, **_k: False

    def fake_get_body(nb, types):
        # Re-enter get for the same type (what _ensure_deposit_supply used to do).
        assert Computer.get(ai, 1, "lumbermill") is False
        return False

    ai._get = fake_get_body
    assert Computer.get(ai, 1, "lumbermill") is False
    assert ai._getting == set()


def test_ensure_deposit_supply_skips_lumbermill_when_townhall_stores_wood():
    ai = Computer.__new__(Computer)
    ai.units = [
        SimpleNamespace(storable_resource_types=("resource1", "resource2", "resource3")),
    ]
    ai.nb = lambda *_a, **_k: 0
    ai.future_nb = lambda *_a, **_k: 0
    ai.equivalent = lambda name: name
    got = []
    ai.get = lambda nb, name: got.append((nb, name)) or False
    ai._try_remote_deposit_expansion = lambda *_a, **_k: False

    Computer._ensure_deposit_supply(ai, 1)  # wood
    assert got == []


def test_choose_gather_target_prefers_farm_when_food_low():
    """When food is scarce, pick a stocked farm over gold/wood deposits."""
    from soundrts.worldresource import Deposit

    ai = Computer.__new__(Computer)
    ai.resources = [100, 100, 0]  # gold/wood ok, food empty
    ai.units = []
    ai.perception = set()
    ai.memory = set()
    ai.square_is_dangerous = lambda *_a, **_k: False

    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    gold = Deposit.__new__(Deposit)
    gold.place = place
    gold.id = "gold1"
    gold.qty = 1000
    gold.resource_type = "resource1"
    gold.type_name = "goldmine"

    farm = SimpleNamespace(
        is_a_building=True,
        resource_qty=50,
        resource_type="resource3",
        type_name="farm",
        place=place,
        id="farm1",
    )
    peasant = SimpleNamespace(
        place=place,
        is_inside=False,
        can_gather_deposit=["goldmine", "wood"],
        can_gather_building=["farm"],
        airground_type="ground",
    )
    ai.units = [farm]
    ai.perception = {gold}
    ai.memory = set()

    # Avoid Deposit isinstance checks failing on gold path needing _gather_target_ok
    # — gold is a real Deposit subclass instance.
    picked = Computer._choose_gather_target(ai, peasant)
    assert picked is farm


def test_send_workers_toward_food_reassigns_from_gold():
    """gather() missing food should reassign a gold gatherer onto a farm."""
    from soundrts.worldresource import Deposit

    ai = Computer.__new__(Computer)
    ai.resources = [80, 80, 0]
    ai.perception = set()
    ai.memory = set()
    ai._gathered_deposits = {}
    ai.square_is_dangerous = lambda *_a, **_k: False

    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    gold = Deposit.__new__(Deposit)
    gold.place = place
    gold.id = "gold1"
    gold.qty = 1000
    gold.resource_type = "resource1"
    gold.type_name = "goldmine"

    class _Farm:
        is_a_building = True
        resource_qty = 40
        resource_type = "resource3"
        type_name = "farm"
        id = "farm1"

        def __init__(self, place):
            self.place = place

        def __hash__(self):
            return hash(self.id)

        def __eq__(self, other):
            return getattr(other, "id", None) == self.id

    farm = _Farm(place)
    orders = [SimpleNamespace(keyword="gather", target=gold)]
    issued = []

    def take_order(order, *args, **kwargs):
        issued.append(list(order))
        if order[0] == "gather":
            orders[:] = [
                SimpleNamespace(keyword="gather", target=farm if order[1] == farm.id else gold)
            ]

    peasant = SimpleNamespace(
        place=place,
        is_inside=False,
        orders=orders,
        can_gather_deposit=["goldmine", "wood"],
        can_gather_building=["farm"],
        airground_type="ground",
        take_order=take_order,
    )
    ai.units = [farm]
    ai._workers = [peasant]
    ai.perception = {gold}

    Computer._send_workers_toward_resources(ai, [2], max_workers=2)
    assert any(o[0] == "gather" and o[1] == farm.id for o in issued)
    assert peasant.orders[0].target is farm


def test_choose_pickup_target_finds_gold_coin_at_mint():
    """gold_mint drops gold_coin on the ground; AI must see it as a pickup target."""
    ai = Computer.__new__(Computer)
    ai.resources = [0, 100, 100]
    ai.perception = set()
    ai.memory = set()
    ai.square_is_dangerous = lambda *_a, **_k: False

    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        objects=[],
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    coin = SimpleNamespace(
        id="coin1",
        place=place,
        default_order="pickup",
        resource_rewards=(50,),
        type_name="gold_coin",
    )
    place.objects = [coin]
    mint = SimpleNamespace(
        production_item="gold_coin",
        place=place,
        type_name="gold_mint",
    )
    peasant = SimpleNamespace(
        place=place,
        is_inside=False,
        have_inventory_space=True,
        _basic_skills={"pickup", "gather"},
        airground_type="ground",
    )
    ai.units = [mint]

    picked = Computer._choose_pickup_target(ai, peasant)
    assert picked is coin


def test_maintain_resource_pickups_reassigns_gatherer():
    ai = Computer.__new__(Computer)
    ai.resources = [0, 50, 50]
    ai.perception = set()
    ai.memory = set()
    ai.square_is_dangerous = lambda *_a, **_k: False

    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        objects=[],
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    coin = SimpleNamespace(
        id="coin1",
        place=place,
        default_order="pickup",
        resource_rewards=(50,),
        type_name="gold_coin",
    )
    place.objects = [coin]
    mint = SimpleNamespace(production_item="gold_coin", place=place)
    orders = [SimpleNamespace(keyword="gather", target=SimpleNamespace())]
    issued = []

    def take_order(order, *args, **kwargs):
        issued.append(list(order))
        if order[0] == "stop":
            orders.clear()
        elif order[0] == "pickup":
            orders[:] = [SimpleNamespace(keyword="pickup", target=coin)]

    peasant = SimpleNamespace(
        place=place,
        is_inside=False,
        orders=orders,
        have_inventory_space=True,
        _basic_skills={"pickup", "gather"},
        airground_type="ground",
        take_order=take_order,
    )
    ai.units = [mint]
    ai._workers = [peasant]

    Computer._maintain_resource_pickups(ai, max_workers=2)
    assert ["stop"] in issued
    assert any(o[0] == "pickup" and o[1] == coin.id for o in issued)
    assert peasant.orders[0].keyword == "pickup"
