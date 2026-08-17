# -*- coding: utf-8 -*-
"""AoE2 race equivalents must resolve to early-game trainables for AI get()."""
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
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)


@pytest.fixture
def aoe2_rules():
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


def test_ai_semantic_units_have_makers(aoe2_rules):
    """footman/archer/knight must not map to castle-only UUs or maker-less shells."""
    for civ in ("britons", "franks", "chinese", "mongols", "byzantines"):
        for semantic in ("footman", "archer", "knight", "peasant"):
            mapped = rules.get(civ, semantic)
            assert mapped, f"{civ} missing {semantic}"
            name = mapped[0]
            makers = rules.get_makers(name)
            assert makers, f"{civ}.{semantic} -> {name} has no makers"


def test_race_equivalent_sources_are_cached(aoe2_rules):
    sources = rules._race_equivalent_sources("chinese_villager")
    assert "peasant" in sources
    assert sources == rules._race_equivalent_sources("chinese_villager")
    assert getattr(rules, "_race_equiv_index", None)
    first = rules.factions
    assert first is rules.factions
    assert "britons" in first
    assert "chinese" in first


def test_franks_beginner_can_start_barracks_path(aoe2_rules):
    """Franks beginner must build barracks for militia, not stall on throwing_axeman."""
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
    assert comp.equivalent("footman") == "militia"
    assert rules.get_makers("throwing_axeman") == ["frank_castle"]
    assert "barracks" in rules.get_makers("militia")

    # Enough peasants + wood so get(militia) can order barracks immediately.
    comp.resources = [5000 * PRECISION] * 4
    comp._enemy_presence = []
    comp._attacked_places = []
    comp._update_perception()
    tc = next(u for u in comp.units if u.type_name == "town_center")
    pcls = rules.unit_class("peasant")
    for _ in range(7):
        pcls(comp, tc.place, tc.x, tc.y)
    comp._update_effect_users_and_workers()

    comp.get(1, comp.equivalent("footman"))
    assert comp.future_nb("barracks") > 0 or comp.nb("barracks") > 0 or any(
        getattr(o, "keyword", None) == "build"
        and getattr(getattr(o, "type", None), "__name__", None) == "barracks"
        for u in comp.units
        for o in (getattr(u, "orders", None) or ())
    )


def test_portuguese_building_shells_fall_back_for_ai_get(aoe2_rules):
    """Portuguese barracks shells are not on villager can_build; AI uses semantic."""
    world = World([], 7)
    world._parse_map((ROOT / "mods/aoe2/multi/z5.txt").read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("p1", None)
    human.faction = "britons"
    human.alliance = "1"
    ai = DummyClient("intermediate")
    ai.faction = "portuguese"
    ai.alliance = "2"
    world.populate_map([human, ai], random_starts=False)
    comp = next(
        p
        for p in world.players
        if isinstance(p, Computer) and p.units and p.faction == "portuguese"
    )
    assert comp.equivalent("peasant") == "portuguese_villager"
    assert comp.equivalent("barracks") == "barracks"
    assert comp.equivalent("archery_range") == "archery_range"
    assert rules.get("portuguese", "barracks")[0] == "portuguese_barracks"

    comp.resources = [5000 * PRECISION] * 4
    if "feudal_age" not in comp.upgrades:
        comp.upgrades.append("feudal_age")
    comp._enemy_presence = []
    comp._attacked_places = []
    comp._update_perception()
    # Race-remapped train must queue on TC (ask for more than the AI start already has).
    want = max(2, int(comp.nb(comp.equivalent("peasant"))) + 2)
    comp.get(want, comp.equivalent("peasant"))
    assert any(
        getattr(o, "keyword", None) == "train"
        for u in comp.units
        for o in (getattr(u, "orders", None) or ())
    )
    # Semantic barracks build must be orderable (shell would trouble-get).
    tc = next(u for u in comp.units if u.type_name == "town_center")
    pcls = rules.unit_class("portuguese_villager")
    for _ in range(4):
        pcls(comp, tc.place, tc.x, tc.y)
    comp._update_effect_users_and_workers()
    comp.get(1, comp.equivalent("barracks"))
    assert comp.future_nb("barracks") > 0 or comp.nb("barracks") > 0 or any(
        getattr(o, "keyword", None) == "build"
        and getattr(getattr(o, "type", None), "__name__", None)
        in ("barracks", "portuguese_barracks")
        for u in comp.units
        for o in (getattr(u, "orders", None) or ())
    )
