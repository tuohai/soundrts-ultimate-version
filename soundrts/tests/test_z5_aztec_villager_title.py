# -*- coding: utf-8 -*-
"""Headless z5 repro: Aztec TC train villager must announce a unit title."""
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
    from soundrts.clientgameorder import OrderTypeView, substitute_args
    from soundrts.definitions import rules, style
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.world_build_rules import effective_can_train
    from soundrts.worldclient import DirectClient, DummyClient

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


def test_aztec_villager_style_title(aoe2_loaded):
    title = style.get("aztec_villager", "title")
    assert title, "aztec_villager missing style title"
    assert title == style.get("peasant", "title")
    eagle_title = style.get("aztec_eagle_scout", "title")
    assert eagle_title, "aztec_eagle_scout missing style title"
    assert eagle_title == style.get("eagle_scout", "title")


@pytest.mark.parametrize(
    "skin,base",
    [
        ("aztec_barracks", "barracks"),
        ("aztec_archery", "archery_range"),
        ("aztec_blacksmith", "blacksmith"),
        ("aztec_university", "university"),
        ("aztec_workshop", "workshop"),
        ("aztec_shipyard", "shipyard"),
        ("aztec_castle", "aoe_castle"),
        ("aztec_monastery", "monastery"),
    ],
)
def test_aztec_building_style_titles(aoe2_loaded, skin, base):
    title = style.get(skin, "title")
    assert title, f"{skin} missing style title"
    assert title == style.get(base, "title")


def test_z5_aztec_tc_train_announces_villager(aoe2_loaded):
    """100x-style headless: Aztec on z5 → TC train order title includes villager."""
    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "aztecs"
    human.alliance = "1"
    human.game_session = types.SimpleNamespace(record_replay=False, allow_cheatmode=True)
    ai = DummyClient("beginner")
    ai.faction = "britons"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    player = human.player

    # Fast-forward a few ticks (100x-style: no realtime sleep)
    for _ in range(10):
        world.update()

    tcs = [u for u in player.units if u.type_name in ("town_center", "townhall")]
    assert tcs, "no town center on z5 aztec start"
    tc = tcs[0]
    trainables = effective_can_train(tc)
    names = list(trainables.keys()) if isinstance(trainables, dict) else list(trainables)
    assert names == ["aztec_villager"], names

    view = OrderTypeView(f"train {names[0]}", tc)
    villager_title = style.get("aztec_villager", "title")
    assert villager_title
    assert view.title == substitute_args(style.get("train", "title"), [villager_title])
    # Must not be bare "train" with empty unit slot
    assert any(tok == villager_title[0] for tok in view.title), view.title
    assert view.population_cost == 1
    food = int(view.cost[2] / PRECISION) if len(view.cost) > 2 else 0
    assert food == 50, view.cost


def test_z5_aztec_built_archery_has_title(aoe2_loaded):
    """Built Aztec archery resolves to aztec_archery shell with archery title."""
    from soundrts.world_build_rules import resolve_buildable_type

    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "aztecs"
    human.alliance = "1"
    human.game_session = types.SimpleNamespace(record_replay=False, allow_cheatmode=True)
    ai = DummyClient("beginner")
    ai.faction = "britons"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    player = human.player
    for _ in range(10):
        world.update()

    resolved = resolve_buildable_type(player, "archery_range")
    assert resolved == "aztec_archery"
    title = style.get(resolved, "title")
    assert title and title == style.get("archery_range", "title")
    sq = player.units[0].place
    b = rules.unit_class(resolved)(player, sq, sq.x, sq.y)
    assert b.type_name == "aztec_archery"
    assert style.get(b.type_name, "title") == title
