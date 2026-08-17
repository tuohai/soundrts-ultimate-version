# -*- coding: utf-8 -*-
"""Housing / age-unlock must not spam cannot_build_here via stone walls."""
from __future__ import annotations

import collections
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldentity import Entity
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldrequirements import (
        count_owned_buildings_of_group,
        iter_unmet_building_candidates,
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
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def test_housing_prefers_house_over_castle_and_excludes_walls(aoe2_loaded):
    ai = Computer.__new__(Computer)
    ai._workers = []
    ai.units = []
    ai._type_discovery_cache = None
    ai.world = type("W", (), {"turn": 0})()
    peasant = rules.unit_class("peasant")
    ai._workers = [type("W", (), {"can_build": peasant.can_build})()]
    houses = ai._housing_type_names()
    assert houses
    assert houses[0] == "house"
    assert "aoe_castle" not in houses[:1]
    assert "wall" not in houses
    assert "palisade_wall" not in houses
    assert "gate" not in houses


def test_feudal_age_candidates_defer_exit_only_walls(aoe2_loaded):
    player = type("P", (), {"has": lambda self, n: False})()
    names = list(iter_unmet_building_candidates(player, "feudal_age_buildings"))
    assert names
    assert names[0] != "wall"
    assert "wall" in names  # still available, but not first


def test_castle_age_reqs_skip_fish_trap_on_land(aoe2_loaded):
    """Land AI must unlock castle via blacksmith, not stall on fish_trap."""
    from soundrts.lib.nofloat import to_int

    world = World([], 42)
    world._parse_map((ROOT / "mods/aoe2/multi/m2.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("intermediate")
    ai.faction = "aztecs"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    for p in world.players:
        p.interface = type(
            "I", (), {"queue_srv_event": staticmethod(lambda *a, **k: None)}
        )()
    comp = next(
        p for p in world.players if isinstance(p, Computer) and p.faction == "aztecs"
    )
    for up in ("dark_age", "feudal_age"):
        if up not in comp.upgrades:
            comp.upgrades.append(up)
    tc = next(u for u in comp.units if u.type_name == "town_center")
    if not comp.has("archery_range"):
        rules.unit_class("aztec_archery")(comp, tc.place, tc.x, tc.y)
    assert count_owned_buildings_of_group(comp, "feudal_age_buildings") == 1
    assert not comp.has("blacksmith")
    comp.resources = [to_int("400"), to_int("400"), to_int("100"), to_int("400")]
    comp._play_memo = {}
    comp._type_discovery_cache = None
    asked = []
    real_get = comp._get

    def _spy(nb, types):
        name = types[0] if isinstance(types, (list, tuple)) else types
        asked.append(getattr(name, "__name__", name))
        return real_get(nb, types)

    comp._get = _spy
    comp._get_requirements(rules.unit_class("castle_age"))
    assert "fish_trap" not in asked
    assert "blacksmith" in asked or comp.future_nb("blacksmith") > 0


def test_castle_unlock_wood_blocks_mill_and_warehouse(aoe2_loaded):
    """While missing a feudal unlock building, 150 wood must not go to mill/camp."""
    from soundrts.lib.nofloat import to_int

    world = World([], 42)
    world._parse_map((ROOT / "mods/aoe2/multi/m2.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("intermediate")
    ai.faction = "aztecs"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False, equivalents=True)
    for p in world.players:
        p.interface = type(
            "I", (), {"queue_srv_event": staticmethod(lambda *a, **k: None)}
        )()
    comp = next(
        p for p in world.players if isinstance(p, Computer) and p.faction == "aztecs"
    )
    for up in ("dark_age", "feudal_age"):
        if up not in comp.upgrades:
            comp.upgrades.append(up)
    tc = next(u for u in comp.units if u.type_name == "town_center")
    if not comp.has("archery_range"):
        rules.unit_class("aztec_archery")(comp, tc.place, tc.x, tc.y)
    assert count_owned_buildings_of_group(comp, "feudal_age_buildings") == 1
    assert not comp.has("blacksmith")
    # Castle get-wave (rams / castle units), not the feudal army line.
    for i, line in enumerate(comp._plan):
        if line.startswith("get ") and "battering_ram" in line:
            comp._line_nb = i
            break
    # Enough food/gold for castle click intent; wood just under blacksmith.
    comp.resources = [to_int("650"), to_int("140"), to_int("200"), to_int("400")]
    comp._play_memo = {}
    comp._type_discovery_cache = None
    assert comp._should_click_plan_phase()
    unlock = comp._next_plan_phase_building_wood_need()
    assert unlock == to_int("150")
    mill_cost = (0, to_int("100"), 0, 0)
    assert comp._would_spend_past_plan_building(mill_cost, ignore_age_defer=True)
    assert comp._should_defer_food_building_expansion(mill_cost)
    assert comp._warehouse_spend_blocked_by_wood_reserve(
        (0, to_int("100")), stores=("resource2",)
    )
    # Blacksmith itself may spend the unlock wood.
    assert not comp._would_spend_past_plan_building(
        (0, to_int("150")), ignore_age_defer=True
    )
    # Once wood covers unlock, camps still wait so blacksmith can click first.
    comp.resources = [to_int("650"), to_int("160"), to_int("200"), to_int("400")]
    comp._play_memo = {}
    assert comp._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("150")
    assert comp._warehouse_spend_blocked_by_wood_reserve(
        (0, to_int("100")), stores=("resource1", "resource4")
    )


def test_byzantine_equivalent_scouttower_is_buildable(aoe2_loaded):
    """Civ scouttower shells have no makers; equivalent must fall back."""
    world = World([], 42)
    world._parse_map((ROOT / "mods/aoe2/multi/onj1.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("beginner")
    ai.faction = "byzantines"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)
    comp = next(
        p
        for p in world.players
        if isinstance(p, Computer) and p.faction == "byzantines"
    )
    assert comp.equivalent("scouttower") == "scouttower"
    assert rules.get_makers("scouttower")
    assert comp.equivalent("guardtower") == "guardtower"


def test_onj1_byzantine_beginner_no_cannot_build_spam(aoe2_loaded):
    world = World([], 42)
    world._parse_map((ROOT / "mods/aoe2/multi/onj1.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("beginner")
    ai.faction = "byzantines"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)
    comp = next(
        p
        for p in world.players
        if isinstance(p, Computer) and p.faction == "byzantines"
    )

    fails = collections.Counter()
    detail = collections.Counter()
    orig = Entity.notify

    def notify(self, event, universal=False):
        if (
            isinstance(event, str)
            and event.startswith("order_impossible")
            and getattr(self, "player", None) is comp
        ):
            fails[event] += 1
            if self.orders:
                o = self.orders[0]
                t = getattr(o, "type", None)
                tn = getattr(t, "__name__", None) or getattr(t, "type_name", None)
                detail[(o.keyword, tn)] += 1
        return orig(self, event, universal)

    Entity.notify = notify
    try:
        ticks = int(420 * 1000 / VIRTUAL_TIME_INTERVAL)
        for _ in range(ticks):
            world.update()
    finally:
        Entity.notify = orig

    assert fails.get("order_impossible,cannot_build_here", 0) == 0, dict(detail)
    # 7 minutes: at least some military or a second house; do not require both.
    assert (
        comp.nb("house") >= 2
        or comp.nb("militia") >= 1
        or comp.nb("barracks") >= 1
    )
    assert "wall" not in {tn for (_, tn) in detail}
