# -*- coding: utf-8 -*-
"""Headless z5: Byzantine barracks must finish at bonus HP, not be repaired up to it."""
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
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldunit.worldcreature import BuildingSite

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
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _z5_byzantines():
    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "byzantines"
    human.alliance = "1"
    human.game_session = types.SimpleNamespace(record_replay=False, allow_cheatmode=True)
    ai = DummyClient("beginner")
    ai.faction = "britons"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    return world, human.player


def test_z5_byzantine_barracks_completes_at_bonus_hp(aoe2_loaded):
    """Dark Age Byzantines: barracks +10% HP (1200→1320) must be full on complete."""
    world, player = _z5_byzantines()
    for _ in range(5):
        world.update()

    worker = next(u for u in player.units if getattr(u, "can_build", ()))
    meadow = next(
        o for o in worker.place.objects if getattr(o, "is_a_building_land", False)
    )
    worker.take_order(["build", "barracks", meadow.id])

    barracks = None
    for _ in range(2500):
        world.update()
        done = [
            u
            for u in player.units
            if "barracks" in (getattr(u, "type_name", "") or "")
            and not isinstance(u, BuildingSite)
        ]
        if done:
            barracks = done[0]
            break
    assert barracks is not None, "barracks never finished on z5"

    hp = barracks.hp / PRECISION
    hp_max = barracks.hp_max / PRECISION
    assert hp_max == 1320, hp_max
    assert hp == hp_max, (hp, hp_max)

    for _ in range(30):
        world.update()
    assert barracks.hp == barracks.hp_max
    assert not any(getattr(o, "keyword", None) == "repair" for o in worker.orders)
