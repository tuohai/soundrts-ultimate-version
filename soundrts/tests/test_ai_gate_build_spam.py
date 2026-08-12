# -*- coding: utf-8 -*-
"""AI must not spam cannot_build_here when walling after a building is attacked."""
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
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def onj1_beginner():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    world = World([], 42)
    world._parse_map((ROOT / "mods/aoe2/multi/onj1.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("beginner")
    ai.faction = "franks"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)
    comp = next(
        p
        for p in world.players
        if isinstance(p, Computer) and p.units and p.faction == "franks"
    )
    yield world, comp
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()


def test_beginner_does_not_spam_gate_builds_when_attacked(onj1_beginner):
    world, comp = onj1_beginner
    comp._update_perception()
    comp.resources = [10000 * PRECISION] * 4
    if "feudal_age" not in comp.upgrades:
        comp.upgrades.append("feudal_age")

    tc = next(u for u in comp.units if u.type_name == "town_center")
    place = tc.place
    meadow = next(o for o in place.objects if getattr(o, "is_a_building_land", False))
    bcls = rules.unit_class("barracks")
    x, y, land = place.find_and_remove_meadow(bcls)
    x, y = place.find_free_space(bcls.airground_type, x, y)
    barracks = bcls(comp, place, x, y)
    barracks.building_land = land
    # Simulate raid — previously triggered infinite palisade_gate build spam.
    comp._sensible_building = barracks
    comp._enemy_presence = []
    comp._attacked_places = []

    fails = collections.Counter()
    detail = collections.Counter()

    def hook():
        for u in list(comp.units):
            if getattr(u, "_t_hook", False):
                continue
            real = u.notify

            def make(unit, real_notify=real):
                def n(e, *a, **k):
                    if isinstance(e, str) and "cannot_build" in e:
                        fails[e] += 1
                        if unit.orders:
                            o = unit.orders[0]
                            t = getattr(o, "type", None)
                            tn = getattr(t, "__name__", None) or t
                            detail[(o.keyword, tn)] += 1
                    return real_notify(e, *a, **k)

                return n

            u.notify = make(u)
            u._t_hook = True

    for _ in range(40):
        hook()
        comp._should_play_this_turn = lambda: True
        comp._update_perception()
        comp.play()
        for __ in range(5):
            for u in list(comp.units):
                if u.orders:
                    try:
                        u.orders[0].update()
                    except Exception:
                        pass

    gate_fails = sum(v for (kw, tn), v in detail.items() if tn and "gate" in str(tn))
    assert gate_fails == 0, detail
    assert fails.get("order_impossible,cannot_build_here", 0) < 5, dict(fails)
    # Beginner must not keep issuing palisade_gate / gate builds.
    pending_gates = [
        o
        for u in comp.units
        for o in u.orders
        if getattr(o, "keyword", None) == "build"
        and "gate" in str(getattr(getattr(o, "type", None), "__name__", ""))
    ]
    assert not pending_gates


def test_prefer_palisade_gate():
    ai = Computer.__new__(Computer)
    assert (
        Computer._prefer_gate_type_name(ai, ("gate", "palisade_gate", "fortified_gate"))
        == "palisade_gate"
    )
