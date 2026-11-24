# -*- coding: utf-8 -*-
"""Regression: building a building must cost exactly the price that was shown.

The player had 10 gold in the feudal age, ordered a townhall (rules cost
12 gold, feudal ``phase bonus cost -2`` -> 10 gold shown) and ended up with
**-2 gold**.

Two bugs combined:

* ``BuildOrder`` reserved the *discounted* cost (10) and refunded it when
  the worker arrived, but ``BuildingSite.__init__`` then charged the *raw*
  rules cost (12) again -- the resources were taken twice, the second time
  at a different (undiscounted) price.
* the reservation refund used the *current* order cost instead of the
  amount that was actually charged, so a cost change between reservation
  and refund silently created or destroyed resources.
"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient
    from soundrts.worldunit import BuildingSite

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


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


def _res_world():
    text = JL1.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "human_faction"
    human.alliance = "1"
    human.game_session = type("S", (), {"record_replay": False})()
    world.populate_map([human], random_starts=False)
    # A few ticks so the player perceives the squares / building land.
    for _ in range(5):
        world.update()
    return world, human.player


def test_reserve_then_free_is_resource_neutral(res_loaded):
    """Reserving then freeing must give back exactly what was taken."""
    from soundrts.worldplayerbase.resources import ResourcesMixin

    class _Order:
        def __init__(self, cost):
            self.cost = cost

    class _Player(ResourcesMixin):
        def __init__(self):
            self.resources = [10 * PRECISION, 0, 0]
            self.budget = []

    p = _Player()
    order = _Order((10 * PRECISION, 16 * PRECISION))
    p.reserve_resources_if_needed(order)
    assert p.resources[0] == 0, p.resources[0]
    p.free_resources(order)
    assert p.resources[0] == 10 * PRECISION, p.resources[0]


def test_free_refunds_the_reserved_amount_even_if_cost_changed(res_loaded):
    """A cost change between reservation and refund must not leak resources."""
    from soundrts.worldplayerbase.resources import ResourcesMixin

    class _Order:
        def __init__(self, cost):
            self.cost = cost

    class _Player(ResourcesMixin):
        def __init__(self):
            self.resources = [10 * PRECISION, 0, 0]
            self.budget = []

    p = _Player()
    order = _Order((10 * PRECISION, 16 * PRECISION))
    p.reserve_resources_if_needed(order)
    # The age-up / a tech now makes the order more expensive.
    order.cost = (12 * PRECISION, 16 * PRECISION)
    p.free_resources(order)
    assert p.resources[0] == 10 * PRECISION, p.resources[0]


def test_res_feudal_townhall_does_not_drive_gold_negative(res_loaded):
    """End-to-end: 10 gold -> build a townhall in the feudal age -> 0 gold."""
    if not JL1.is_file():
        pytest.skip("res jl1 map not present")
    world, player = _res_world()

    from soundrts.worldphase import Phase

    rules.unit_class("feudal_age").upgrade_player(player)
    assert "feudal_age" in player.upgrades

    # The feudal phase bonus gives a 2 gold discount on every cost.
    assert player.phase_cost_bonus[0] == -2 * PRECISION, player.phase_cost_bonus

    worker = next(u for u in player.units if getattr(u, "can_build", ()))
    meadow = next(
        o for o in worker.place.objects if getattr(o, "is_a_building_land", False)
    )

    # Give the player exactly 10 gold, like the reported save.
    player.resources = [10 * PRECISION, 16 * PRECISION, 0, 0]

    worker.take_order(["build", "townhall", meadow.id])

    # The order must have reserved exactly 10 gold (12 raw - 2 discount).
    build_order = worker.orders[0]
    assert build_order.cost[0] == 10 * PRECISION, build_order.cost
    assert not build_order.is_impossible, build_order.is_impossible
    assert player.resources[0] == 0, player.resources[0]

    # Let the worker walk to the site and place it.
    site = None
    for _ in range(300):
        world.update()
        assert player.resources[0] >= 0, (
            f"gold went negative while building: {player.resources[0]}"
        )
        site = next((u for u in player.units if isinstance(u, BuildingSite)), None)
        if site is not None:
            break

    assert site is not None, "no building site was created"
    assert player.resources[0] == 0, player.resources[0]
    assert site.paid_cost[0] == 10 * PRECISION, site.paid_cost
