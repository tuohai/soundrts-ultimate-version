# -*- coding: utf-8 -*-
"""Headless z5 repro: Japanese mill style + farm food qty while gathering."""
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

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules, style
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldorders.gathering import GatherOrder
    from soundrts.worldunit.worldcreature import Building

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

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
    res.load_style()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
        res.load_style()
    logging.disable(logging.NOTSET)


def test_japanese_mill_style_title(aoe2_loaded):
    """Built Japanese mill must resolve to mill title (not silent)."""
    mapped = rules.get("japanese", "mill")
    assert mapped and mapped[0] == "japanese_mill"
    title = style.get("japanese_mill", "title")
    assert title, "japanese_mill missing style title (check is_a mill shell)"
    mill_title = style.get("mill", "title")
    assert title == mill_title


def test_farm_extract_decrements_on_sub_unit_ticks():
    """Continuous gather often takes <1 display unit; farm qty must still fall."""
    events = []
    farm = Building.__new__(Building)
    farm.resource_type = "resource3"
    farm.resource_qty = 175
    farm.resource_volume_max = 175
    farm._resource_qty_frac = 0
    farm.notify = lambda msg, *a, **k: events.append(msg)

    # 0.32 food/s for 1s → 320 internal; previously //1000 == 0 lost food forever
    got = farm.extract_resource(320)
    assert got == 320
    assert farm.resource_qty == 175
    assert farm._resource_qty_frac == 320

    got = farm.extract_resource(700)
    assert got == 700
    assert farm.resource_qty == 174  # 1020 internal → 1 display unit consumed
    assert farm._resource_qty_frac == 20


def test_z5_japanese_farm_gather_qty_falls(aoe2_loaded):
    """100x-speed style: continuous gather on z5 Japanese start depletes farm."""
    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "japanese"
    human.alliance = "1"
    human.game_session = types.SimpleNamespace(record_replay=False, allow_cheatmode=True)
    ai = DummyClient("beginner")
    ai.faction = "britons"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    player = human.player

    # Place mill shell + farm like a completed build
    sq = player.units[0].place
    mill_cls = rules.unit_class("japanese_mill")
    farm_cls = rules.unit_class("farm")
    assert mill_cls is not None and farm_cls is not None
    mill = mill_cls(player, sq, sq.x, sq.y)
    farm = farm_cls(player, sq, sq.x, sq.y)
    assert style.get(mill.type_name, "title"), mill.type_name
    assert farm.resource_qty == 175

    # Prefer any worker
    workers = [u for u in player.units if hasattr(u, "get_gather_rate")]
    assert workers, "no worker on z5 japanese start"
    worker = workers[0]

    order = GatherOrder(worker, [farm.id])
    order.mode = "gather"
    order.target = farm
    order.storage = None
    order.update_target = lambda: None
    order._cont_last_t = 0
    order._cont_accum = 0.0
    worker._near_enough = lambda t: True
    worker.place.world.time = 0

    start_qty = farm.resource_qty
    # Simulate ~60s at 100x (many 100ms ticks) of continuous gather
    for t in range(100, 60100, 100):
        worker.place.world.time = t
        if order.mode == "bring_back":
            # Instant drop-off for the test
            if worker.cargo:
                rt, qty = worker.cargo
                player.store(rt, qty)
                worker.cargo = None
            order.mode = "gather"
            order._cont_last_t = t
            order._cont_accum = 0.0
            continue
        if order.mode != "gather":
            break
        order._continuous_gather_tick()

    assert farm.resource_qty < start_qty, (
        f"farm stayed at {farm.resource_qty} after continuous gather "
        f"(frac={getattr(farm, '_resource_qty_frac', None)})"
    )
