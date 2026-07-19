"""Repeated train / Alt+Z must stack in the production queue.

Production orders are class-marked imperative (``ProductionOrder.is_imperative``).
``take_order`` used to allow only one follow-up behind an imperative head, so a
second Alt+Z (``do_again now`` without queue_order) replaced the queued train
instead of appending — queue length stayed at 2.
"""
from __future__ import annotations

import logging
import os
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import sys

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient

sys.argv = saved_argv

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


@pytest.fixture(autouse=True)
def load_rules():
    logging.disable(logging.CRITICAL)
    res.load_rules_and_ai()


def _townhall():
    world = World([], 42)
    world._parse_map(JL1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("human", None)
    human.faction = rules.factions[0]
    human.alliance = "1"
    ai = DummyClient("beginner")
    ai.faction = rules.factions[0]
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)
    player = human.player
    th = next(u for u in player.units if getattr(u, "type_name", None) == "townhall")
    player.resources = [10**9] * len(player.resources)
    player.population_limit = 200
    return th


def test_repeated_train_stacks_behind_active_train():
    th = _townhall()
    # Mimic Alt+Z: client sends queue_order=0 (forget_previous=True), imperative=0.
    th.take_order(["train", "peasant"], forget_previous=True, imperative=False)
    assert len(th.orders) == 1
    assert th.orders[0].keyword == "train"

    th.take_order(["train", "peasant"], forget_previous=True, imperative=False)
    assert len(th.orders) == 2

    th.take_order(["train", "peasant"], forget_previous=True, imperative=False)
    assert len(th.orders) == 3
    assert all(o.keyword == "train" for o in th.orders)
