# -*- coding: utf-8 -*-
"""AoE2: civ building shells must not double-count any_buildings age gates."""
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
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.world_build_rules import resolve_buildable_type
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldrequirements import (
        buildings_of_group,
        clear_caches,
        count_owned_buildings_of_group,
        requirements_satisfied,
    )

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
    clear_caches()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    clear_caches()
    logging.disable(logging.NOTSET)


def test_feudal_group_excludes_civ_archery_shells(aoe2_loaded):
    names = set(buildings_of_group("feudal_age_buildings"))
    assert "archery_range" in names
    assert "aztec_archery" not in names
    assert "portuguese_archery" not in names
    assert "chinese_archery" not in names


def test_z5_aztec_one_archery_not_enough_for_castle_age(aoe2_loaded):
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
    player.upgrades.append("feudal_age")

    assert count_owned_buildings_of_group(player, "feudal_age_buildings") == 0
    sq = player.units[0].place
    resolved = resolve_buildable_type(player, "archery_range")
    assert resolved == "aztec_archery"
    rules.unit_class(resolved)(player, sq, sq.x, sq.y)

    assert count_owned_buildings_of_group(player, "feudal_age_buildings") == 1
    castle = rules.unit_class("castle_age")
    assert requirements_satisfied(player, castle.requirements) is False

    # Second distinct feudal building unlocks Castle Age
    bs = resolve_buildable_type(player, "blacksmith")
    rules.unit_class(bs)(player, sq, sq.x, sq.y)
    assert count_owned_buildings_of_group(player, "feudal_age_buildings") == 2
    assert requirements_satisfied(player, castle.requirements) is True
