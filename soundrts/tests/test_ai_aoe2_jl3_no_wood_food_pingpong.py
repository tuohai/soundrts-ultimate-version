# -*- coding: utf-8 -*-
"""AoE2 jl3 regression: the dark-age food/wood ping-pong must stop.

On jl3 the intermediate AoE2 AI never attacked: the 500-food feudal click
slipped past 24 minutes.  The cause was *not* a missing farm or a missing
wood reserve -- it was the AI re-assigning the same villagers between wood and
food roughly 60 times per minute.

The dark-age get line asks for **both** resources in the same turn:

* ``gather(feudal_age)`` -> 500 food  (the age-up click)
* ``gather(barracks)``   -> 175 wood  (the next wave's barracks)

``Computer.gather()`` sends one ``_send_workers_toward_resources`` request per
missing resource, and every request re-assigns workers *from the front of the
worker list*.  The "this worker already collects X" guard only knew about the
resource the current pass was asking for, so:

1. the wood pass took villagers 0 and 1 onto wood;
2. the food pass (same turn) walked the same list, found them on wood, and
   took them back onto the farms;
3. the next AI turn repeated the whole dance.

Every re-issue re-created the ``GatherOrder``, which resets the continuous
gather progress (``_cont_accum`` / ``_cont_last_t``).  Neither wood nor food
therefore ever accumulated.

These tests pin the fix: the guard must know the worker cap of *every*
resource, not only the one the current pass asks for.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import (
        VIRTUAL_TIME_INTERVAL,
        filter_ai_executable_plan,
        get_ai,
    )
    from soundrts.lib.nofloat import PRECISION, to_int
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldresource import Deposit

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL3 = ROOT / "mods" / "aoe2" / "multi" / "jl3.txt"

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)


@pytest.fixture
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


class _HashableFarm(SimpleNamespace):
    """A farm stub that can live in the AI's ``perception`` set."""

    __hash__ = object.__hash__


def _wood_deposit(place, ident="wood1"):
    wood = Deposit.__new__(Deposit)
    wood.place = place
    wood.id = ident
    wood.qty = 1000
    wood.resource_type = "resource2"
    wood.type_name = "wood"
    return wood


def _farm_building(place, ident="farm1"):
    return _HashableFarm(
        place=place,
        id=ident,
        resource_qty=to_int("175"),
        resource_type="resource3",
        type_name="farm",
        is_a_building=True,
        is_an_extractor=0,
        expanded_is_a=("farm", "building"),
        auto_cultivate=1,
        is_producing=False,
        orders=[],
        resource_volume_max=175,
    )


def _villager(place, orders, issued, ident, targets=None):
    """A villager stub whose ``take_order`` really replaces its order list.

    The real engine's ``Creature.take_order`` cancels the previous orders and
    installs a fresh ``GatherOrder``; the stub has to do the same, otherwise
    the test cannot see that the worker was re-assigned.
    """
    known = targets if targets is not None else {}

    def _take_order(order, *a, **k):
        issued.append(list(order))
        if order and str(order[0]) == "gather":
            target = known.get(order[1])
            orders.clear()
            orders.append(
                SimpleNamespace(
                    keyword="gather",
                    target=target,
                    mode=None,
                    storage=None,
                )
            )
        else:
            orders.clear()
            orders.append(SimpleNamespace(keyword=str(order[0]), target=None))

    return SimpleNamespace(
        id=ident,
        place=place,
        is_inside=False,
        orders=orders,
        can_gather_deposit=["goldmine", "wood"],
        can_gather_building=["farm"],
        airground_type="ground",
        speed=1.0,
        hp=25,
        type_name="frank_villager",
        expanded_is_a=("frank_villager", "peasant"),
        take_order=_take_order,
    )


def _dark_age_ai():
    """A bare intermediate AoE2 AI on the dark-age villager wave."""
    ai = Computer.__new__(Computer)
    ai.world = type("W", (), {"turn": 0, "time": 0})()
    ai.faction = "franks"
    ai.upgrades = ["dark_age"]
    ai.units = []
    ai._workers = []
    ai._plan = filter_ai_executable_plan(get_ai("franks_intermediate"))
    ai._line_nb = 0
    ai._type_discovery_cache = None
    ai.perception = set()
    ai.memory = set()
    ai._gathered_deposits = {}
    ai.square_is_dangerous = lambda *_a, **_k: False
    ai.resources = [to_int("150"), to_int("40"), to_int("100"), 0]
    return ai


def test_dark_age_food_request_does_not_steal_a_working_lumberjack(aoe2_loaded):
    """A food request must not yank a lumberjack that already has cargo moving.

    The lumberjack is walking home with 10 wood (mode ``bring_back``).  Before
    the fix the food pass replaced its order with a fresh farm-gather order,
    which threw the cargo away *and* reset the continuous-gather progress.
    """
    ai = _dark_age_ai()
    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = _wood_deposit(place)
    issued = []
    order = SimpleNamespace(keyword="gather", target=wood, mode="bring_back")
    villager = _villager(place, [order], issued, 1)
    ai._workers = [villager]
    ai.perception = {wood}
    ai.units = []

    Computer._send_workers_toward_resources(ai, [2], max_workers=2)

    assert not issued, "food request stole a lumberjack that was already working"
    assert villager.orders[0].target is wood
    assert villager.orders[0].mode == "bring_back"


def test_dark_age_food_request_keeps_lumberjack_cap_respected(aoe2_loaded):
    """The wood cap must hold while the food request runs.

    Two villagers are already chopping wood (the dark-age cap) and one is
    free.  The food request may take the free one, but it must not take a
    second one from the wood crew.
    """
    ai = _dark_age_ai()
    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = _wood_deposit(place)
    farm = _farm_building(place)
    issued = []

    on_wood_a = [SimpleNamespace(keyword="gather", target=wood, mode="gather")]
    on_wood_b = [SimpleNamespace(keyword="gather", target=wood, mode="go_gather")]
    targets = {"wood1": wood, "farm1": farm}
    v1 = _villager(place, on_wood_a, issued, 1, targets)
    v2 = _villager(place, on_wood_b, issued, 2, targets)
    v3 = _villager(place, [], issued, 3, targets)
    ai._workers = [v1, v2, v3]
    ai.perception = {wood, farm}
    ai.units = [farm]
    ai._choose_gather_target = lambda worker, resource_indices=None: (
        farm if resource_indices and 2 in resource_indices else wood
    )

    Computer._send_workers_toward_resources(ai, [2], max_workers=2)

    # v1 / v2 must still be on wood.
    assert v1.orders[0].target is wood
    assert v2.orders[0].target is wood


def test_dark_age_wood_and_food_requests_do_not_ping_pong(aoe2_loaded):
    """The regression itself: alternating requests must not thrash workers.

    The dark-age get line asks for food *and* wood in the same turn.  Running
    both requests repeatedly (as the AI does every turn) must not produce a
    stream of fresh gather orders for the same worker.
    """
    ai = _dark_age_ai()
    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = _wood_deposit(place)
    farm = _farm_building(place)
    issued = []

    v1 = _villager(place, [], issued, 1, {"wood1": wood, "farm1": farm})
    v2 = _villager(place, [], issued, 2, {"wood1": wood, "farm1": farm})
    v3 = _villager(place, [], issued, 3, {"wood1": wood, "farm1": farm})
    ai._workers = [v1, v2, v3]
    ai.perception = {wood, farm}
    ai.units = [farm]
    ai._choose_gather_target = lambda worker, resource_indices=None: (
        farm if resource_indices and 2 in resource_indices else wood
    )

    # 60 AI turns, each asking for food then for wood (the real order on
    # jl3 was: food from the age click, wood from the barracks).
    for _ in range(60):
        Computer._send_workers_toward_resources(ai, [2], max_workers=2)
        Computer._send_workers_toward_resources(ai, [1], max_workers=2)

    # Each villager may be re-ordered at most once per resource switch, not
    # once per turn.  The bug produced hundreds of re-issues.
    assert len(issued) <= 12, (
        "food/wood requests are still ping-ponging: "
        f"{len(issued)} order re-issues in 60 turns"
    )


def test_jl3_intermediate_reaches_feudal_without_ping_pong(aoe2_loaded):
    """Headless jl3: the intermediate AI must bank 500 food and click feudal.

    Before the fix the food/wood ping-pong reset every continuous gather, so
    the food rate stayed at ~0 and the 500-food click never happened.
    """
    if not JL3.is_file():
        pytest.skip("aoe2 jl3 map not present")

    world = World([], 42)
    world._parse_map(JL3.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    p1 = DummyClient("intermediate")
    p1.faction = "britons"
    p1.alliance = "1"
    p2 = DummyClient("intermediate")
    p2.faction = "franks"
    p2.alliance = "2"
    world.populate_map([p1, p2], random_starts=False, equivalents=True)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "intermediate"
    ]
    assert len(comps) == 2

    feudal_at = None
    game_limit_ms = 26 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    for _ in range(ticks):
        world.update()
        for c in comps:
            if "feudal_age" in (getattr(c, "upgrades", None) or []):
                feudal_at = world.time
                break
        if feudal_at is not None:
            break

    assert feudal_at is not None, (
        "no intermediate AI reached feudal_age on jl3 within 26 minutes; "
        f"resources={[list(getattr(c, 'resources', []) or []) for c in comps]}"
    )
    assert feudal_at <= 26 * 60 * 1000, feudal_at
