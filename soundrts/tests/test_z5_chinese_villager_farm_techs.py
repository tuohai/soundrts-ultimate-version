# -*- coding: utf-8 -*-
"""Headless z5: Chinese villager usable-tech list must not repeat mill farm techs."""
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
    from soundrts.attributes.equipment_abilities import EquipmentAbilities
    from soundrts.definitions import rules, style
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)

_GENERIC_FARM = ("horse_collar", "heavy_plow", "crop_rotation")
_FRANK_FARM = ("frank_horse_collar", "frank_heavy_plow", "frank_crop_rotation")


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


def _z5_world(human_faction):
    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = human_faction
    human.alliance = "1"
    human.game_session = types.SimpleNamespace(record_replay=False, allow_cheatmode=True)
    ai = DummyClient("beginner")
    ai.faction = "britons" if human_faction != "britons" else "franks"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    for _ in range(10):
        world.update()
    return human.player


def _ui_tech_titles(unit):
    attrs = []
    EquipmentAbilities(None).add_tech_skill_attributes(unit, attrs)
    for _prefix, _label, value in attrs:
        if isinstance(value, tuple) and value[0] == "CAN_USE_TECH_ITEMS":
            return [tuple(item) if isinstance(item, list) else item for item in value[1]]
    return []


def test_z5_chinese_villager_farm_techs_not_duplicated(aoe2_loaded):
    player = _z5_world("chinese")
    vills = [u for u in player.units if u.type_name == "chinese_villager"]
    assert vills, "no chinese_villager on z5"
    unit = vills[0]
    techs = list(unit.can_use_tech)
    assert "horse_collar" in techs
    assert "heavy_plow" in techs
    assert "crop_rotation" in techs
    for alias in _FRANK_FARM:
        assert alias not in techs, alias

    titles = _ui_tech_titles(unit)
    assert titles
    assert len(titles) == len(set(titles)), titles

    farm_titles = tuple(style.get(name, "title") for name in _GENERIC_FARM)
    frank_titles = tuple(style.get(name, "title") for name in _FRANK_FARM)
    assert farm_titles == frank_titles
    for title in farm_titles:
        key = tuple(title) if isinstance(title, list) else title
        assert titles.count(key) == 1, (key, titles)


def test_z5_frank_villager_uses_free_farm_aliases(aoe2_loaded):
    player = _z5_world("franks")
    vills = [u for u in player.units if u.type_name == "frank_villager"]
    assert vills, "no frank_villager on z5"
    unit = vills[0]
    techs = list(unit.can_use_tech)
    for name in _FRANK_FARM:
        assert name in techs, name
    for name in _GENERIC_FARM:
        assert name not in techs, name
    titles = _ui_tech_titles(unit)
    assert titles
    assert len(titles) == len(set(titles)), titles
    assert style.get("frank_villager", "title") == style.get("peasant", "title")
