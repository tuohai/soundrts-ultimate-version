# -*- coding: utf-8 -*-
"""AoE2 dark-age AI: mill/farms before starve, feudal when get-line needs it."""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import (
        VIRTUAL_TIME_INTERVAL,
        filter_ai_executable_plan,
        get_ai,
        rules,
    )
    from soundrts.lib.nofloat import PRECISION, to_int
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit import BuildingSite

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "mods" / "aoe2" / "multi" / "jl1.txt"
JL3 = ROOT / "mods" / "aoe2" / "multi" / "jl3.txt"

_MIL_BUILDINGS = (
    "barracks",
    "briton_barracks",
    "frank_barracks",
    "archery_range",
    "briton_archery",
    "frank_archery",
    "stables",
    "briton_stable",
    "frank_stable",
)

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


def _bare_ai(**kwargs):
    ai = Computer.__new__(Computer)
    ai.world = type("W", (), {"turn": 0, "time": 0})()
    ai.faction = kwargs.get("faction", "britons")
    ai.upgrades = list(kwargs.get("upgrades", ("dark_age",)))
    ai.units = list(kwargs.get("units", ()))
    ai._plan = list(kwargs.get("plan", ()))
    ai._workers = []
    ai._type_discovery_cache = None
    ai._line_nb = kwargs.get("line_nb", 0)
    return ai


def test_food_low_threshold_is_precision_scaled(aoe2_loaded):
    ai = _bare_ai()
    assert ai._ruleset_has_expensive_food_age()
    assert ai._resource_low_threshold(2) == to_int("150")
    assert ai._resource_low_threshold(0) == to_int("40")
    assert ai._resource_low_threshold(2) >= 150 * PRECISION


def test_get_line_detects_feudal_from_archers(aoe2_loaded):
    ai = _bare_ai(plan=["get 6 peasant 2 militia 6 aoe_archer"])
    assert "feudal_age" in ai._plan_unmet_phase_names()
    assert ai._saving_food_for_age()
    ai.upgrades = ["dark_age", "feudal_age"]
    assert "feudal_age" not in ai._plan_unmet_phase_names()
    assert not ai._saving_food_for_age()


def test_get_line_detects_feudal_before_castle_for_knights(aoe2_loaded):
    ai = _bare_ai(
        faction="franks",
        plan=["get 6 peasant 4 militia 2 aoe_knight"],
    )
    phases = ai._plan_unmet_phase_names()
    assert "feudal_age" in phases
    assert phases[0] == "feudal_age"


def test_defer_military_only_while_saving_for_feudal(aoe2_loaded):
    ai = _bare_ai(plan=["get 6 peasant 2 militia 6 aoe_archer"])
    assert ai._defer_plan_get_token("militia", saving_for_feudal=True)
    assert ai._defer_plan_get_token("aoe_archer", saving_for_feudal=True)
    assert not ai._defer_plan_get_token("peasant", saving_for_feudal=True)
    ai.upgrades = ["dark_age", "feudal_age"]
    ai.resources = [to_int("200"), to_int("200"), to_int("900"), 0]
    assert not ai._defer_plan_get_token("militia", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)


def test_defer_knights_until_castle_but_still_get_militia(aoe2_loaded):
    ai = _bare_ai(
        faction="franks",
        plan=["get 6 peasant 4 militia 2 aoe_knight"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.resources = [to_int("200"), to_int("200"), to_int("900"), 0]
    assert "castle_age" in ai._plan_unmet_phase_names()
    assert not ai._saving_food_for_age()
    assert not ai._defer_plan_get_token(
        "militia", saving_for_feudal=ai._saving_food_for_age()
    )
    assert ai._defer_plan_get_token("aoe_knight", saving_for_feudal=False)


def test_food_only_villager_not_held_for_wood_barracks(aoe2_loaded):
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("80"), to_int("400"), 0]
    assert ai._plan_expensive_wood_reserve() >= to_int("100")
    assert not ai._should_hold_extra_workers(6, "peasant")
    assert ai._wood_gather_worker_cap(6) >= 4


def test_hold_villagers_while_saving_food_for_first_age(aoe2_loaded):
    ai = _bare_ai(plan=["get 6 peasant 2 militia 6 aoe_archer"])
    ai.resources = [0, to_int("200"), to_int("80"), 0]
    assert ai._saving_food_for_age()
    assert ai._should_hold_extra_workers(6, "peasant")
    assert ai._wood_gather_worker_cap(6) == 2


def test_plan_wants_wood_building_for_archers_after_feudal(aoe2_loaded):
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    assert not ai._plan_wants_unbuilt_wood_building()
    ai.upgrades = ["dark_age", "feudal_age"]
    assert ai._plan_wants_unbuilt_wood_building()
    ai.upgrades = ["dark_age"]
    assert ai._plan_wants_unbuilt_wood_building(ignore_age_defer=True)
    ai.upgrades = ["dark_age", "feudal_age"]
    assert ai._plan_expensive_wood_reserve() >= to_int("100")


def test_no_later_building_wood_reserve_while_militia_unmet(aoe2_loaded):
    """Barracks owned: still stash wood for archery, even with 0 militia alive."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert ai._plan_expensive_wood_reserve() >= to_int("100")

    def _nb_militia_done(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        if n == "militia":
            return 2
        return 0

    ai.nb = _nb_militia_done
    ai.future_nb = lambda n: _nb_militia_done(n)
    assert ai._plan_expensive_wood_reserve() >= to_int("100")


def test_stables_reserved_after_barracks_before_castle(aoe2_loaded):
    """Franks: stables are a feudal building; do not wait for castle knights."""
    ai = _bare_ai(
        faction="franks",
        plan=["get 6 peasant 4 militia 2 aoe_knight"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "frank_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert "castle_age" in ai._plan_unmet_phase_names()
    assert not ai._saving_food_for_age()
    assert ai._plan_expensive_wood_reserve() >= to_int("100")


def _has_or_researching_feudal(player):
    if "feudal_age" in (getattr(player, "upgrades", None) or []):
        return True
    for u in list(getattr(player, "units", []) or []):
        orders = getattr(u, "orders", None) or ()
        if not orders:
            continue
        o = orders[0]
        if getattr(o, "keyword", None) != "advance":
            continue
        t = getattr(o, "type", None)
        tn = getattr(t, "__name__", None) or getattr(t, "type_name", None)
        if tn == "feudal_age":
            return True
    return False


def _type_names(player):
    names = []
    for u in list(getattr(player, "units", []) or []):
        if isinstance(u, BuildingSite):
            t = getattr(u, "type", None)
            names.append(
                getattr(t, "__name__", None) or getattr(t, "type_name", None) or "site"
            )
        else:
            names.append(getattr(u, "type_name", "?"))
    return names


def test_jl1_intermediate_builds_mill_and_clicks_feudal(aoe2_loaded):
    """Headless jl1: mill/farm in dark age, feudal before the old 14-minute stall."""
    from soundrts.lib.nofloat import PRECISION as P

    if not JL1.is_file():
        pytest.skip("aoe2 jl1 map not present")
    text = JL1.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * P)
    world._build_map()
    p1 = DummyClient("intermediate")
    p1.faction = "britons"
    p1.alliance = "1"
    p2 = DummyClient("intermediate")
    p2.faction = "franks"
    p2.alliance = "2"
    world.populate_map([p1, p2], random_starts=False, equivalents=True)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "intermediate"
    ]
    assert len(comps) == 2

    mill_at = None
    feudal_at = None
    game_limit_ms = 12 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    millish = ("mill", "frank_mill")
    for _ in range(ticks):
        world.update()
        for c in comps:
            names = _type_names(c)
            if mill_at is None and any(n in millish or n == "farm" for n in names):
                mill_at = world.time
        if feudal_at is None and any(_has_or_researching_feudal(c) for c in comps):
            feudal_at = world.time
        if mill_at is not None and feudal_at is not None:
            break

    assert mill_at is not None, "expected mill/farm well before 12 minutes"
    assert mill_at <= 8 * 60 * 1000, mill_at
    assert feudal_at is not None, "expected feudal_age research"
    assert feudal_at <= 12 * 60 * 1000, feudal_at


def test_jl1_intermediate_builds_feudal_military_buildings(aoe2_loaded):
    """Headless jl1: after feudal, barracks / range / stables actually start.

    Spawn has no trees (woods sit on adjacent squares), same pinch as jl3.
    """
    from soundrts.lib.nofloat import PRECISION as P

    if not JL1.is_file():
        pytest.skip("aoe2 jl1 map not present")
    text = JL1.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * P)
    world._build_map()
    p1 = DummyClient("intermediate")
    p1.faction = "britons"
    p1.alliance = "1"
    p2 = DummyClient("intermediate")
    p2.faction = "franks"
    p2.alliance = "2"
    world.populate_map([p1, p2], random_starts=False, equivalents=True)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "intermediate"
    ]
    assert len(comps) == 2

    mil_at = None
    game_limit_ms = 20 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    for _ in range(ticks):
        world.update()
        for c in comps:
            names = _type_names(c)
            if any(n in _MIL_BUILDINGS for n in names):
                mil_at = world.time
                break
        if mil_at is not None:
            break

    assert mil_at is not None, (
        "expected barracks/archery/stables by 20 minutes; "
        f"types={[(_type_names(c), getattr(c, 'faction', None)) for c in comps]}"
    )
    assert mil_at <= 20 * 60 * 1000, mil_at


def test_jl3_intermediate_builds_feudal_military_buildings(aoe2_loaded):
    """Headless jl3: after feudal, barracks / range / stables actually start."""
    from soundrts.lib.nofloat import PRECISION as P

    if not JL3.is_file():
        pytest.skip("aoe2 jl3 map not present")
    text = JL3.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * P)
    world._build_map()
    p1 = DummyClient("intermediate")
    p1.faction = "britons"
    p1.alliance = "1"
    p2 = DummyClient("intermediate")
    p2.faction = "franks"
    p2.alliance = "2"
    world.populate_map([p1, p2], random_starts=False, equivalents=True)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "intermediate"
    ]
    assert len(comps) == 2

    mil_at = None
    game_limit_ms = 20 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    for _ in range(ticks):
        world.update()
        for c in comps:
            names = _type_names(c)
            if any(n in _MIL_BUILDINGS for n in names):
                mil_at = world.time
                break
        if mil_at is not None:
            break

    assert mil_at is not None, (
        "expected barracks/archery/stables by 20 minutes; "
        f"types={[(_type_names(c), getattr(c, 'faction', None)) for c in comps]}"
    )
    assert mil_at <= 20 * 60 * 1000, mil_at


def test_dedicated_dropoff_enables_warehouse_expansion(aoe2_loaded):
    """Town center stores wood, but a dedicated lumber mill must still expand."""
    ai = _bare_ai()
    assert ai._has_dedicated_dropoff_types()
    assert ai._auto_warehouse_expansion_enabled()
    wood_wh = ai._preferred_warehouse_class(resource_type="resource2")
    assert wood_wh is not None
    assert wood_wh.type_name not in ai._main_base_type_names()


def test_warehouse_spend_blocked_when_wood_covers_range(aoe2_loaded):
    """Do not spend a mill if wood already covers (or nearly covers) archery."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    mill = to_int("100")
    ai.resources = [0, to_int("175"), 0]
    assert ai._warehouse_spend_blocked_by_wood_reserve((0, mill))
    ai.resources = [0, to_int("161"), 0]
    assert ai._warehouse_spend_blocked_by_wood_reserve((0, mill))
    ai.resources = [0, to_int("110"), 0]
    assert not ai._warehouse_spend_blocked_by_wood_reserve((0, mill))


def test_warehouse_spend_blocked_before_first_barracks(aoe2_loaded):
    """Dark-age mill must not steal the first barracks wood stash."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("110"), 0]
    assert ai._warehouse_spend_blocked_by_wood_reserve((0, to_int("100")))


def test_feudal_army_line_does_not_click_castle_after_barracks(aoe2_loaded):
    """Later knights must not start castle until the feudal get wave is done."""
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 aoe_knight 4 longbowman",
            "get 12 peasant 4 mangonel",
        ],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    assert "castle_age" in ai._plan_unmet_phase_names(lookahead=True)
    assert "castle_age" not in ai._plan_unmet_phase_names(lookahead=False)
    assert not ai._should_click_plan_phase()

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert ai._owns_get_line_production_building()
    assert not ai._should_click_plan_phase()


def test_castle_get_line_clicks_castle(aoe2_loaded):
    ai = _bare_ai(
        plan=["get 12 peasant 8 aoe_knight 6 longbowman"],
        upgrades=["dark_age", "feudal_age"],
    )
    assert "castle_age" in ai._plan_unmet_phase_names(lookahead=False)
    assert ai._should_click_plan_phase()


def test_dark_villager_line_still_clicks_feudal(aoe2_loaded):
    ai = _bare_ai(
        plan=["get 8 peasant", "get 10 peasant 4 militia 8 aoe_archer"],
        upgrades=["dark_age"],
    )
    assert not ai._plan_unmet_phase_names(lookahead=False)
    assert "feudal_age" in ai._plan_unmet_phase_names(lookahead=True)
    assert ai._before_first_expensive_food_age()
    assert ai._should_click_plan_phase()


def test_current_line_feudal_army_not_held_for_later_castle(aoe2_loaded):
    """Militia/archers on this wave must train even if the next wave wants castle."""
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 aoe_knight 2 mangonel",
        ],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.resources = [to_int("200"), to_int("200"), to_int("200"), 0]
    assert not ai._defer_plan_get_token("militia", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)
    assert ai._defer_plan_get_token("aoe_knight", saving_for_feudal=False)


def test_defer_wood_soldiers_until_workshop_started(aoe2_loaded):
    """After castle, do not dump archery wood into archers before the workshop."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("50"), to_int("250"), to_int("100"), 0]
    assert ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("mangonel", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("peasant", saving_for_feudal=False)

    def _nb_workshop(n):
        if n in ("workshop",) or n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb_workshop
    ai.future_nb = lambda n: _nb_workshop(n)
    assert not ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)


def test_workshop_wood_reserved_on_later_get_line(aoe2_loaded):
    """After castle, a watchdog line without mangonel must still bank workshop wood."""
    from soundrts.definitions import rules

    ai = _bare_ai(
        plan=[
            "get 10 peasant 4 militia 16 aoe_archer 4 aoe_knight 4 longbowman",
            "get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel",
        ],
        upgrades=["dark_age", "feudal_age", "castle_age"],
        line_nb=0,
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("50"), to_int("32"), to_int("70"), 0]
    assert ai._has_startable_plan_production_building()
    assert ai._wood_below_pending_building()
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    house = rules.unit_class("house")
    assert house is not None
    assert ai._would_spend_past_plan_building(house.cost, ignore_age_defer=True)
    assert ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)


def test_workshop_wood_reserved_while_castle_researching(aoe2_loaded):
    """The 160s castle click must bank workshop wood, not wait until it finishes."""
    ai = _after_feudal_military_ai()
    ai._workers = [object()] * 10
    ai.resources = [to_int("50"), to_int("40"), to_int("10"), 0]
    ai.future_nb = lambda n: 1 if n in ("castle_age", ["castle_age"]) else 0
    assert ai._phase_advance_in_progress("castle_age")
    assert ai._age_click_in_progress()
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    assert ai._wood_below_pending_building()
    assert ai._would_spend_past_plan_building(
        (0, to_int("60")), ignore_age_defer=True
    )
    assert not ai._should_keep_farms_producing()
    assert ai._wood_scout_worker_cap() == 2
    ai.future_nb = lambda n: 0
    assert not ai._phase_advance_in_progress("castle_age")
    assert not ai._plan_expensive_wood_reserve(ignore_age_defer=True)
    assert not ai._wood_below_pending_building()


def _ram_workshop_ai(wood="80"):
    """Castle-age siege get line with an owned workshop and short wood."""
    from soundrts.definitions import rules

    ai = _bare_ai(
        plan=["get 4 battering_ram 2 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    workshop_cls = rules.unit_class("workshop")
    workshop = SimpleNamespace(
        is_a_building=True,
        type_name="workshop",
        type=workshop_cls,
        player=ai,
        expanded_is_a=(),
    )
    ai.units = [workshop]
    ai.nb = lambda n: 1 if n in ("workshop",) else 0
    ai.future_nb = lambda n: 1 if n in ("workshop",) else 0
    ai.resources = [to_int("200"), to_int(wood), to_int("200"), 0]
    return ai


def test_ram_wood_reserved_after_workshop(aoe2_loaded):
    """Houses and farms must not spend the 160 wood a ram still needs."""
    from soundrts.definitions import rules

    ai = _ram_workshop_ai("80")
    assert ai._owned_trainer_wood_need() >= to_int("160")
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("160")
    assert ai._wood_below_pending_building()
    assert not ai._should_keep_farms_producing()
    house = rules.unit_class("house")
    assert house is not None
    assert ai._would_spend_past_plan_building(house.cost, ignore_age_defer=True)
    assert ai._would_spend_past_plan_building(
        (0, to_int("60")), ignore_age_defer=True
    )


def test_watchdog_pauses_on_ram_line_while_workshop_waits_wood(aoe2_loaded):
    """Do not skip the siege get just because 160 wood takes longer than watchdog."""
    ai = _ram_workshop_ai("80")
    ai.watchdog = 2
    ai._previous_linechange = 0
    ai.world.time = 5000
    ai.get = lambda *_a, **_k: False
    assert ai._watchdog_should_wait()
    ai._follow_plan()
    assert ai._previous_linechange == 5000
    assert ai._line_nb == 0


def test_watchdog_skips_feudal_army_when_castle_is_later(aoe2_loaded):
    """Dying feudal troops must not freeze watchdog forever before the castle wave."""
    ai = _bare_ai(
        plan=[
            "get 4 militia 4 aoe_archer",
            "attack",
            "get 3 battering_ram",
        ],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "archery_range", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("20"), to_int("20"), to_int("20"), 0]
    # Later-wave workshop wood / trainer food must not keep the timer paused.
    ai._wood_below_pending_building = lambda: True
    ai._owned_trainer_food_need = lambda: to_int("60")
    assert not ai._should_click_plan_phase()
    assert "castle_age" in ai._plan_unmet_phase_names(lookahead=True)
    assert not ai._watchdog_should_wait()
    ai.watchdog = 2
    ai._previous_linechange = 0
    ai.world.time = 5000
    ai.get = lambda *_a, **_k: False
    ai._follow_plan()
    # Watchdog skips feudal get; same turn ``attack`` advances onto the ram wave.
    assert ai._line_nb == 2
    assert "battering_ram" in ai._plan[ai._line_nb]


def test_age_up_needs_food_after_barracks(aoe2_loaded):
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 aoe_knight 2 mangonel",
        ],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("50"), to_int("50"), to_int("100"), 0]
    assert not ai._should_click_plan_phase()
    assert not ai._age_up_needs_food()


def test_one_lumber_dropoff_while_saving_for_range(aoe2_loaded):
    """Do not spam lumber mills while the get line still needs 175 wood."""
    from soundrts.definitions import rules

    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        if n == "lumbermill":
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    mill = rules.unit_class("lumbermill")
    assert mill is not None
    assert ai._dedicated_dropoff_at_cap(mill)
    ai.future_nb = lambda n: 1 if n in ("barracks", "briton_barracks") else 0
    ai.nb = lambda n: 1 if n in ("barracks", "briton_barracks") else 0
    assert not ai._dedicated_dropoff_at_cap(mill)


def test_after_barracks_farm_would_steal_archery_wood(aoe2_loaded):
    """Recultivate/farm must see archery wood even while militia is unfinished."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    gold, wood = ai._plan_next_production_building_cost(ignore_age_defer=True)
    assert wood >= to_int("100")
    ai.resources = [0, to_int("161"), to_int("50")]
    assert ai._would_spend_past_plan_building(
        (0, to_int("60")), ignore_age_defer=True
    )


def _after_barracks_ai():
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 aoe_knight 2 mangonel",
        ],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in ("barracks", "briton_barracks"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    return ai


def _on_castle_wave_ai():
    """Current get line needs castle (knights), feudal already complete."""
    ai = _bare_ai(
        plan=["get 12 peasant 8 aoe_knight"],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in (
            "barracks",
            "briton_barracks",
            "archery_range",
            "briton_archery",
            "stables",
            "briton_stable",
        ):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    # has()/any_buildings read units; nb stubs alone are not enough.
    sq = SimpleNamespace(x=0, y=0)
    ai.units = [
        SimpleNamespace(
            type_name="archery_range",
            expanded_is_a=("archery_range", "building"),
            place=sq,
        ),
        SimpleNamespace(
            type_name="stables",
            expanded_is_a=("stables", "building"),
            place=sq,
        ),
    ]
    return ai


def _castle_wave_units(ai, *extra):
    """Keep feudal unlock buildings when a test swaps in farms."""
    keep = ("archery_range", "stables", "blacksmith", "barracks")
    base = [
        u
        for u in (getattr(ai, "units", None) or ())
        if getattr(u, "type_name", None) in keep
    ]
    ai.units = base + list(extra)
    return ai.units


def _after_feudal_military_ai():
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 aoe_knight 2 mangonel",
        ],
        upgrades=["dark_age", "feudal_age"],
    )

    def _nb(n):
        if n in (
            "barracks",
            "briton_barracks",
            "archery_range",
            "briton_archery",
            "stables",
            "briton_stable",
        ):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    return ai


def test_resource_need_ratio_ranks_wood_above_castle_food(aoe2_loaded):
    """Idle gather must prefer unpaid archery wood over nearby farms."""
    ai = _after_barracks_ai()
    ai.resources = [to_int("50"), to_int("40"), to_int("100"), 0]
    assert ai._wood_below_pending_building()
    assert ai._resource_need_ratio(1) < ai._resource_need_ratio(0)
    assert not ai._should_keep_farms_producing()
    ai.resources = [to_int("50"), to_int("200"), to_int("100"), 0]
    assert not ai._wood_below_pending_building()
    # Feudal army line is not clicking castle; farms resume only once trainers
    # need food (stub AIs have no real barracks in ``units``).
    ai = _on_castle_wave_ai()
    ai.resources = [to_int("50"), to_int("200"), to_int("100"), 0]
    assert ai._should_keep_farms_producing()


def test_gold_camp_blocked_while_range_wood_short(aoe2_loaded):
    """Mining camps must not spend the 175 wood stash; lumber mills still may."""
    ai = _after_barracks_ai()
    mill = to_int("100")
    ai.resources = [0, to_int("110"), 0]
    assert not ai._warehouse_spend_blocked_by_wood_reserve((0, mill))
    assert ai._warehouse_spend_blocked_by_wood_reserve(
        (0, mill), stores=("resource1", "resource4")
    )


def test_mining_camp_blocked_while_workshop_wood_short(aoe2_loaded):
    """After castle, a 100-wood gold camp must not spend the workshop stash."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("70"), to_int("142"), to_int("22"), to_int("500")]
    camp = to_int("100")
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    assert ai._wood_below_pending_building()
    assert ai._warehouse_spend_blocked_by_wood_reserve(
        (0, camp), stores=("resource1", "resource4")
    )


def test_mining_camp_blocked_on_watchdog_line_after_castle(aoe2_loaded):
    """Watchdog feudal line after castle must still bank workshop wood."""
    ai = _bare_ai(
        plan=[
            "get 6 peasant 2 militia 6 aoe_archer",
            "get 10 peasant 4 militia 16 aoe_archer 4 aoe_knight 4 longbowman",
            "get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel",
        ],
        upgrades=["dark_age", "feudal_age", "castle_age"],
        line_nb=0,
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("70"), to_int("142"), to_int("22"), to_int("500")]
    camp = to_int("100")
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    assert ai._wood_below_pending_building()
    assert ai._warehouse_spend_blocked_by_wood_reserve(
        (0, camp), stores=("resource1", "resource4")
    )


def _chinese_watchdog_after_castle_ai(wood="167"):
    plan = filter_ai_executable_plan(get_ai("chinese_intermediate"))
    line_nb = next(
        i
        for i, line in enumerate(plan)
        if line.startswith("get ") and "militia" in line and "aoe_archer" in line
    )
    ai = _bare_ai(
        faction="chinese",
        plan=plan,
        upgrades=["dark_age", "loom", "feudal_age", "castle_age"],
        line_nb=line_nb,
    )

    def _nb(n):
        names = n if isinstance(n, (list, tuple)) else (n,)
        owned = {
            "chinese_barracks": 1,
            "barracks": 1,
            "chinese_archery": 1,
            "archery_range": 1,
            "chinese_stable": 1,
            "stables": 1,
        }
        return sum(owned.get(name, 0) for name in names)

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("120"), to_int(wood), to_int("22"), to_int("401")]
    return ai


def test_chinese_watchdog_line_keeps_workshop_wood_after_castle(aoe2_loaded):
    """Full chinese_intermediate plan on the feudal watchdog line still banks 200 wood."""
    ai = _chinese_watchdog_after_castle_ai()
    assert ai._later_age_startable_production_wood() >= to_int("200")
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("200")
    assert ai._wood_below_pending_building()
    assert ai._need_later_age_production_wood()
    assert ai._warehouse_spend_blocked_by_wood_reserve(
        (0, to_int("100")), stores=("resource1", "resource4")
    )


def test_monastery_does_not_spend_workshop_wood(aoe2_loaded):
    """get(monk) must not place monastery before the 200-wood workshop stash is paid."""
    ai = _chinese_watchdog_after_castle_ai(wood="175")
    assert ai._later_age_startable_production_wood() >= to_int("200")
    assert ai._trainer_blocked_by_later_age_wood("monastery")
    assert not ai._trainer_blocked_by_later_age_wood("workshop")


def test_send_workers_keeps_lumberjacks_while_range_unpaid(aoe2_loaded):
    """get(castle) missing food must not pull lumberjacks off unpaid archery wood."""
    from soundrts.worldresource import Deposit

    ai = _after_barracks_ai()
    ai.resources = [to_int("50"), to_int("40"), to_int("100"), 0]
    ai.perception = set()
    ai.memory = set()
    ai._gathered_deposits = {}
    ai.square_is_dangerous = lambda *_a, **_k: False

    place = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = Deposit.__new__(Deposit)
    wood.place = place
    wood.id = "wood1"
    wood.qty = 1000
    wood.resource_type = "resource2"
    wood.type_name = "wood"

    orders = [SimpleNamespace(keyword="gather", target=wood)]
    issued = []

    def take_order(order, *args, **kwargs):
        issued.append(list(order))

    peasant = SimpleNamespace(
        place=place,
        is_inside=False,
        orders=orders,
        can_gather_deposit=["goldmine", "wood"],
        can_gather_building=["farm"],
        airground_type="ground",
        take_order=take_order,
    )
    ai.units = []
    ai._workers = [peasant]
    ai.perception = {wood}
    assert ai._wood_below_pending_building()
    Computer._send_workers_toward_resources(ai, [2], max_workers=2)
    assert not issued
    assert peasant.orders[0].target is wood


def test_keeps_farms_while_saving_food_for_feudal(aoe2_loaded):
    """Dark-age mill/farms must keep running while banking 500 food."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("50"), to_int("100"), 0]
    assert ai._saving_food_for_age()
    assert ai._should_keep_farms_producing()


def test_clears_auto_farm_mode_while_range_wood_short(aoe2_loaded):
    """Engine auto-restart would spend 60 wood; turn it off until archery is paid."""
    ai = _after_barracks_ai()
    ai.resources = [to_int("50"), to_int("40"), to_int("100"), 0]
    farm = SimpleNamespace(
        is_a_building=True,
        is_producing=False,
        orders=[],
        auto_cultivate=1,
        current_production_mode="auto",
        auto_production=0,
        type_name="farm",
        expanded_is_a=(),
        take_order=lambda *_a, **_k: None,
    )
    ai.units = [farm]
    Computer._idle_resource_buildings_produce(ai)
    assert farm.current_production_mode is None


def test_dark_age_does_not_recultivate_past_barracks_wood(aoe2_loaded):
    """Keep enough wood for barracks even while farming for feudal."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("180"), to_int("200"), 0]
    farm = SimpleNamespace(
        is_a_building=True,
        is_producing=False,
        orders=[],
        auto_cultivate=1,
        current_production_mode="auto",
        auto_production=0,
        type_name="farm",
        expanded_is_a=(),
        production_cost=(0, to_int("60"), 0, 0),
        take_order=lambda *_a, **_k: None,
    )
    ai.units = [farm]
    assert ai._before_first_expensive_food_age()
    Computer._idle_resource_buildings_produce(ai)
    assert farm.current_production_mode is None


def test_castle_get_line_raises_farm_target(aoe2_loaded):
    """800-food castle on the current wave keeps planting farms above the 150 floor."""
    ai = _bare_ai(
        plan=["get 12 peasant 8 aoe_knight"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai._workers = [object()] * 12
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [to_int("200"), to_int("200"), to_int("200"), 0]
    assert ai._should_click_plan_phase()
    assert ai._age_up_needs_food()
    assert ai._target_resource_building_count(2) >= 6
    assert ai._resource_low_threshold(2) >= to_int("500")


def test_castle_wave_still_trains_feudal_units_while_food_short(aoe2_loaded):
    """Low food must not freeze archers/militia just because knights share the line."""
    ai = _bare_ai(
        plan=["get 12 peasant 16 aoe_archer 4 aoe_knight 8 longbowman"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.resources = [to_int("200"), to_int("200"), to_int("50"), 0]
    assert "castle_age" in ai._plan_unmet_phase_names()
    assert not ai._saving_food_for_age()
    assert not ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("militia", saving_for_feudal=False)
    assert ai._defer_plan_get_token("aoe_knight", saving_for_feudal=False)
    assert ai._defer_plan_get_token("longbowman", saving_for_feudal=False)


def test_feudal_army_line_does_not_hold_for_castle(aoe2_loaded):
    """After feudal, current-line archers/villagers train even if castle is next."""
    ai = _after_barracks_ai()
    ai._workers = [object()] * 12
    ai.resources = [to_int("50"), to_int("40"), to_int("100"), 0]
    assert ai._wood_below_pending_building()
    assert ai._target_resource_building_count(2) == max(2, 12 // 4)

    def _nb(n):
        if n in (
            "barracks",
            "briton_barracks",
            "archery_range",
            "briton_archery",
        ):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("200"), to_int("200"), to_int("200"), 0]
    assert not ai._wood_below_pending_building()
    assert not ai._age_up_needs_food()
    assert not ai._defer_plan_get_token("aoe_archer", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("peasant", saving_for_feudal=False)


def test_castle_food_blocks_line_upgrade_on_castle_get_line(aoe2_loaded):
    """Town watch / man-at-arms must not dump castle food on a castle get line."""
    from soundrts.definitions import rules

    ai = _bare_ai(
        plan=["get 12 peasant 8 aoe_knight"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.resources = [to_int("300"), to_int("200"), to_int("600"), 0]
    maa = rules.unit_class("man_at_arms")
    watch = rules.unit_class("town_watch")
    assert maa is not None and watch is not None
    assert ai._should_click_plan_phase()
    assert ai._spend_would_block_age_up(maa.cost)
    assert ai._spend_would_block_age_up(watch.cost)
    ai.resources = [to_int("300"), to_int("200"), to_int("900"), 0]
    assert not ai._spend_would_block_age_up(maa.cost)
    assert not ai._spend_would_block_age_up(watch.cost)


def test_feudal_get_line_allows_line_upgrade_food(aoe2_loaded):
    """Feudal army wave may spend food on man-at-arms; castle is the next wave."""
    from soundrts.definitions import rules

    ai = _after_barracks_ai()
    ai.resources = [to_int("300"), to_int("200"), to_int("600"), 0]
    maa = rules.unit_class("man_at_arms")
    assert maa is not None
    assert not ai._should_click_plan_phase()
    assert not ai._spend_would_block_age_up(maa.cost)


def test_castle_food_blocks_line_upgrade_and_banks_farm_wood(aoe2_loaded):
    """Do not spend castle food on man-at-arms, and keep 60 wood for recultivate."""
    from soundrts.definitions import rules

    ai = _on_castle_wave_ai()
    ai.resources = [to_int("300"), to_int("40"), to_int("600"), 0]
    maa = rules.unit_class("man_at_arms")
    assert maa is not None
    assert ai._spend_would_block_age_up(maa.cost)
    farm = SimpleNamespace(
        auto_cultivate=1,
        production_cost=(0, to_int("60"), 0, 0),
        is_producing=True,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
    )
    _castle_wave_units(ai, farm)
    assert ai._age_up_farm_wood_reserve() >= to_int("60")
    assert ai._need_wood_for_age_up_farms()
    assert ai._wood_gather_worker_cap(10) >= 5
    ai.resources = [to_int("300"), to_int("200"), to_int("900"), 0]
    assert not ai._spend_would_block_age_up(maa.cost)
    assert not ai._need_wood_for_age_up_farms()


def test_recultivate_not_blocked_by_unbuilt_workshop(aoe2_loaded):
    """Castle-age workshop must not freeze farms while castle itself is unpaid."""
    ai = _on_castle_wave_ai()
    ai._workers = [object()] * 10
    ai.resources = [to_int("200"), to_int("40"), to_int("600"), 0]
    assert not ai._wood_below_pending_building()
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) == 0
    assert ai._should_keep_farms_producing()
    assert not ai._would_spend_past_plan_building(
        (0, to_int("60")), ignore_age_defer=True
    )
    farm = SimpleNamespace(
        auto_cultivate=1,
        production_cost=(0, to_int("60"), 0, 0),
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
    )
    _castle_wave_units(ai, farm)
    assert ai._age_up_farm_wood_reserve() >= to_int("60")
    assert ai._need_wood_for_age_up_farms()


def test_do_not_expand_farms_while_recultivate_unpaid(aoe2_loaded):
    """Castle food must recultivate idle farms before planting more of them."""
    ai = _on_castle_wave_ai()
    ai._workers = [object()] * 10
    farm_cost = (0, to_int("60"), 0, 0)
    idle = SimpleNamespace(
        auto_cultivate=1,
        production_cost=farm_cost,
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
    )
    producing = SimpleNamespace(
        auto_cultivate=1,
        production_cost=farm_cost,
        is_producing=True,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
    )
    _castle_wave_units(ai, idle)
    ai.resources = [to_int("200"), to_int("80"), to_int("600"), 0]
    assert ai._should_defer_food_building_expansion(farm_cost)
    grown = SimpleNamespace(
        auto_cultivate=1,
        production_cost=farm_cost,
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
        resource_qty=to_int("175"),
    )
    _castle_wave_units(ai, grown)
    # 80 wood pays the new farm but leaves less than one recultivate.
    assert ai._should_defer_food_building_expansion(farm_cost)
    _castle_wave_units(ai, producing)
    assert ai._should_defer_food_building_expansion(farm_cost)
    ai.resources = [to_int("200"), to_int("200"), to_int("600"), 0]
    assert not ai._should_defer_food_building_expansion(farm_cost)
    dark = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age"],
    )
    dark.nb = lambda n: 0
    dark.future_nb = lambda n: 0
    dark.resources = [0, to_int("80"), to_int("200"), 0]
    dark.units = [idle]
    assert not dark._should_defer_food_building_expansion(farm_cost)


def test_harvest_grown_farms_before_more_wood(aoe2_loaded):
    """Grown farms feed the stockpile, but recultivate wood still outranks them."""
    ai = _on_castle_wave_ai()
    ai._workers = [object()] * 10
    grown = SimpleNamespace(
        auto_cultivate=1,
        production_cost=(0, to_int("60"), 0, 0),
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
        resource_qty=to_int("175"),
        resource_type="resource3",
        is_a_building=True,
    )
    empty = SimpleNamespace(
        auto_cultivate=1,
        production_cost=(0, to_int("60"), 0, 0),
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
        resource_qty=0,
        resource_type="resource3",
        is_a_building=True,
    )
    _castle_wave_units(ai, grown)
    ai.resources = [to_int("200"), to_int("40"), to_int("600"), 0]
    assert ai._has_harvestable_food_buildings()
    assert ai._cultivate_missing_wood() == 0
    assert ai._need_wood_for_age_up_farms()
    assert ai._wood_gather_worker_cap(10) >= 5
    assert ai._resource_need_ratio(1) < ai._resource_need_ratio(2)
    ai.resources = [to_int("200"), to_int("200"), to_int("600"), 0]
    assert not ai._need_wood_for_age_up_farms()
    assert ai._resource_need_ratio(2) < ai._resource_need_ratio(1)
    ai.resources = [to_int("200"), to_int("40"), to_int("600"), 0]
    _castle_wave_units(ai, empty)
    assert not ai._has_harvestable_food_buildings()
    assert ai._cultivate_missing_wood() >= to_int("60")
    assert ai._wood_gather_worker_cap(10) >= 5


def test_scouts_for_wood_when_farm_piles_are_gone(aoe2_loaded):
    """Don't bounce on one neighbor; explore when remembered trees are empty."""
    ai = _after_feudal_military_ai()
    ai.resources = [to_int("200"), to_int("40"), to_int("600"), 0]
    ai.perception = set()
    ai.memory = set()
    farm = SimpleNamespace(
        auto_cultivate=1,
        production_cost=(0, to_int("60"), 0, 0),
        is_producing=False,
        orders=[],
        type_name="farm",
        expanded_is_a=(),
    )
    ai.units = [farm]
    issued = []
    peasant = SimpleNamespace(
        orders=[],
        place=None,
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1][0] == "auto_explore"
    peasant3 = SimpleNamespace(
        orders=[],
        place=None,
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai._workers = [
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        peasant3,
    ]
    issued.clear()
    # Castle food still missing: keep harvesting, only two wood scouts.
    assert ai._wood_scout_worker_cap() == 2
    assert not Computer._send_worker_to_scout_for_wood(ai, peasant3)
    assert not issued


def test_walks_adjacent_square_when_spawn_has_no_trees(aoe2_loaded):
    """jl3-style off-spawn woods: leave the TC square so trees enter LOS."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("40"), to_int("200"), 0]
    ai.perception = set()
    ai.memory = set()
    neighbor = SimpleNamespace(id="a1", neighbors=())
    home = SimpleNamespace(
        id="a2",
        neighbors=(neighbor,),
        shortest_path_distance_to=lambda *a, **k: 0,
    )
    neighbor.neighbors = (home,)
    neighbor.shortest_path_distance_to = lambda *a, **k: 0
    issued = []
    peasant = SimpleNamespace(
        orders=[],
        place=home,
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai._workers = [peasant]
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["go", "a1"]


def test_drops_carried_wood_when_it_would_pay_barracks(aoe2_loaded):
    """Do not walk to a new forest with the last barracks wood still in cargo."""
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("160"), to_int("200"), 0]
    order = SimpleNamespace(keyword="gather", mode="go_gather", storage="keep")
    peasant = SimpleNamespace(
        cargo=("resource2", to_int("20")),
        orders=[order],
        take_order=lambda *_a, **_k: None,
    )
    ai._workers = [peasant]
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    Computer._force_wood_dropoff_if_plan_building_ready(ai)
    assert order.mode == "bring_back"
    assert order.storage is None


def test_wood_almost_covers_plan_building_within_one_carry(aoe2_loaded):
    ai = _bare_ai(
        plan=["get 6 peasant 2 militia 6 aoe_archer"],
        upgrades=["dark_age", "feudal_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("160"), to_int("200"), 0]
    assert ai._wood_almost_covers_plan_building()
    ai.resources = [0, to_int("100"), to_int("200"), 0]
    assert not ai._wood_almost_covers_plan_building()


def test_dark_age_keeps_lumberjacks_while_feudal_food_missing(aoe2_loaded):
    """gather(feudal) must not yank the barracks-wood pair onto berries."""
    ai = _bare_ai(
        plan=["get 4 militia 8 aoe_archer"],
        upgrades=["dark_age"],
    )
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [0, to_int("40"), to_int("80"), 0]
    assert ai._before_first_expensive_food_age()
    assert ai._plan_expensive_wood_reserve(ignore_age_defer=True) >= to_int("100")
    assert ai._keep_lumberjacks()
    assert ai._wood_gather_worker_cap(8) == 2


def test_wood_scout_cap_stays_two_before_first_age(aoe2_loaded):
    """Dark-age food save must not send the whole town exploring for trees."""
    ai = _bare_ai(plan=["get 6 peasant 2 militia 6 aoe_archer"])
    ai.resources = [0, to_int("40"), to_int("80"), 0]
    peasant3 = SimpleNamespace(
        orders=[],
        place=None,
        take_order=lambda *_a, **_k: None,
    )
    ai._workers = [
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        peasant3,
    ]
    # Two scouts is the dark-age cap even if lumberjacks are protected.
    assert ai._wood_scout_worker_cap() == 2
    assert not Computer._send_worker_to_scout_for_wood(ai, peasant3)


def test_workshop_wood_scouts_after_castle(aoe2_loaded):
    """After castle, empty local trees must not leave miners on gold/stone."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("200"), to_int("48"), to_int("3"), to_int("90")]
    ai._workers = [object()] * 10
    assert ai._wood_below_pending_building()
    assert ai._keep_lumberjacks()
    assert ai._wood_scout_worker_cap() >= 5
    peasant = SimpleNamespace(orders=[], place=None, take_order=lambda *_a, **_k: None)
    ai._workers = [
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        peasant,
    ] + [object()] * 7
    assert Computer._send_worker_to_scout_for_wood(ai, peasant)


def test_wood_scout_does_not_pull_gatherers_after_castle(aoe2_loaded):
    """Workshop wood scouts must not convert farm/wood gatherers into explorers."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("70"), to_int("142"), to_int("22"), to_int("500")]
    gatherer = SimpleNamespace(
        orders=[
            SimpleNamespace(
                keyword="gather",
                target=SimpleNamespace(resource_type="resource2"),
            )
        ],
        place=None,
        take_order=lambda *_a, **_k: None,
    )
    ai._workers = [
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        SimpleNamespace(orders=[SimpleNamespace(keyword="auto_explore")]),
        gatherer,
    ] + [object()] * 7
    assert ai._wood_below_pending_building()
    assert ai._has_startable_plan_production_building()
    assert not Computer._send_worker_to_scout_for_wood(ai, gatherer)


def test_farm_gatherers_do_not_scout_before_castle(aoe2_loaded):
    """Feudal farm hands must stay home; archery being startable is not enough."""
    ai = _after_feudal_military_ai()
    ai.resources = [to_int("70"), to_int("24"), to_int("400"), to_int("400")]
    farm_hand = SimpleNamespace(
        orders=[
            SimpleNamespace(
                keyword="gather",
                target=SimpleNamespace(resource_type="resource3"),
            )
        ],
        place=None,
        take_order=lambda *_a, **_k: None,
    )
    ai._workers = [farm_hand] + [object()] * 7
    assert not ai._later_age_startable_production_wood()
    assert not Computer._send_worker_to_scout_for_wood(ai, farm_hand)


def test_farm_gatherers_may_scout_for_workshop_wood(aoe2_loaded):
    """After castle, villagers on farms may explore when local trees are gone."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )

    def _nb(n):
        if n in _MIL_BUILDINGS:
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.resources = [to_int("70"), to_int("24"), to_int("22"), to_int("500")]
    farm_hand = SimpleNamespace(
        orders=[
            SimpleNamespace(
                keyword="gather",
                target=SimpleNamespace(resource_type="resource3"),
            )
        ],
        place=None,
        take_order=lambda *_a, **_k: None,
    )
    ai._workers = [farm_hand] + [object()] * 9
    assert ai._wood_below_pending_building()
    assert ai._later_age_startable_production_wood()
    assert Computer._send_worker_to_scout_for_wood(ai, farm_hand)


def test_explorer_gathers_wood_in_same_square(aoe2_loaded):
    """Scouts standing on remaining trees must chop, not keep walking."""
    from soundrts.worldresource import Deposit

    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    ai.nb = lambda n: 1 if n in _MIL_BUILDINGS else 0
    ai.future_nb = ai.nb
    square = SimpleNamespace(
        x=0,
        y=0,
        id="p1",
        shortest_path_distance_to=lambda *_a, **_k: 0,
    )
    wood = Deposit.__new__(Deposit)
    wood.place = square
    wood.id = "wood1"
    wood.qty = 1000
    wood.resource_type = "resource2"
    issued = []
    peasant = SimpleNamespace(
        place=square,
        is_inside=False,
        orders=[SimpleNamespace(keyword="auto_explore")],
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai.perception = {wood}
    ai.memory = set()
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["gather", "wood1"]


def test_walks_back_to_empty_remembered_forest_after_castle(aoe2_loaded):
    """Chopped regen forests must still pull workshop-wood scouts off random explore."""
    from soundrts.worldresource import Deposit

    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    ai.nb = lambda n: 1 if n in _MIL_BUILDINGS else 0
    ai.future_nb = ai.nb
    ai.resources = [to_int("70"), to_int("58"), to_int("22"), to_int("500")]
    home = SimpleNamespace(
        x=0,
        y=0,
        id="home",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    forest = SimpleNamespace(
        x=100,
        y=0,
        id="forest",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = Deposit.__new__(Deposit)
    wood.place = forest
    wood.id = "wood1"
    wood.qty = 0
    wood.qty_max = 75000
    wood.resource_regen = 1
    wood.resource_type = "resource2"
    issued = []
    peasant = SimpleNamespace(
        place=home,
        is_inside=False,
        orders=[SimpleNamespace(keyword="auto_explore")],
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai.perception = set()
    ai.memory = {wood}
    ai.square_is_dangerous = lambda *_a, **_k: False
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["go", "forest"]


def test_watchdog_after_castle_walks_into_dangerous_wood(aoe2_loaded):
    """Workshop wood must still pull scouts into combat forests after the feudal watchdog."""
    from soundrts.worldresource import Deposit

    ai = _chinese_watchdog_after_castle_ai(wood="25")
    home = SimpleNamespace(
        x=0,
        y=0,
        id="home",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    forest = SimpleNamespace(
        x=100,
        y=0,
        id="d4",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    wood = Deposit.__new__(Deposit)
    wood.place = forest
    wood.id = "wood1"
    wood.qty = 150
    wood.resource_type = "resource2"
    issued = []
    peasant = SimpleNamespace(
        place=home,
        is_inside=False,
        orders=[SimpleNamespace(keyword="auto_explore")],
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai.perception = {wood}
    ai.memory = set()
    ai.square_is_dangerous = lambda *_a, **_k: True
    assert ai._need_later_age_production_wood()
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["go", "d4"]


def test_watchdog_after_castle_wood_scout_cap_uses_lumberjacks(aoe2_loaded):
    """Do not freeze the scout cap at 2 when workshop is only visible via later-age scan."""
    ai = _chinese_watchdog_after_castle_ai(wood="25")
    ai._workers = [object()] * 10
    assert ai._need_later_age_production_wood()
    assert ai._wood_scout_worker_cap() > 2


def test_explorer_gathers_empty_regen_forest_after_castle(aoe2_loaded):
    """Standing on a chopped regen forest must chop, not keep auto_explore."""
    from soundrts.worldresource import Deposit

    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    ai.nb = lambda n: 1 if n in _MIL_BUILDINGS else 0
    ai.future_nb = ai.nb
    ai.resources = [to_int("70"), to_int("25"), to_int("22"), to_int("500")]
    square = SimpleNamespace(
        x=0,
        y=0,
        id="d4",
        shortest_path_distance_to=lambda *_a, **_k: 0,
    )
    wood = Deposit.__new__(Deposit)
    wood.place = square
    wood.id = "wood1"
    wood.qty = 0
    wood.qty_max = 75000
    wood.resource_regen = 1
    wood.resource_type = "resource2"
    issued = []
    peasant = SimpleNamespace(
        place=square,
        is_inside=False,
        orders=[SimpleNamespace(keyword="auto_explore")],
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai.perception = {wood}
    ai.memory = set()
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["gather", "wood1"]


def test_explorer_chops_same_square_instead_of_walking_away(aoe2_loaded):
    """A scout on remaining trees must gather them, not walk to another forest."""
    from soundrts.worldresource import Deposit

    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    ai.nb = lambda n: 1 if n in _MIL_BUILDINGS else 0
    ai.future_nb = ai.nb
    ai.resources = [to_int("70"), to_int("25"), to_int("22"), to_int("500")]
    here = SimpleNamespace(
        x=0,
        y=0,
        id="d4",
        shortest_path_distance_to=lambda *_a, **_k: 0,
    )
    other = SimpleNamespace(
        x=100,
        y=0,
        id="far",
        shortest_path_distance_to=lambda *_a, **_k: 1,
    )
    local = Deposit.__new__(Deposit)
    local.place = here
    local.id = "wood1"
    local.qty = 150
    local.resource_type = "resource2"
    far = Deposit.__new__(Deposit)
    far.place = other
    far.id = "wood2"
    far.qty = 150
    far.resource_type = "resource2"
    issued = []
    peasant = SimpleNamespace(
        place=here,
        is_inside=False,
        orders=[SimpleNamespace(keyword="auto_explore")],
        take_order=lambda order, *a, **k: issued.append(list(order)),
    )
    ai.perception = {local, far}
    ai.memory = set()
    assert Computer._send_worker_toward_known_wood(ai, peasant)
    assert issued and issued[-1] == ["gather", "wood1"]


def test_send_explorer_does_not_recall_workshop_wood_scouts(aoe2_loaded):
    """After castle, extra peasant wood scouts must not be walked back to the TC."""
    ai = _bare_ai(
        plan=["get 12 peasant 30 aoe_archer 8 aoe_knight 4 mangonel"],
        upgrades=["dark_age", "feudal_age", "castle_age"],
    )
    ai.nb = lambda n: 1 if n in _MIL_BUILDINGS else 0
    ai.future_nb = ai.nb
    ai.resources = [to_int("70"), to_int("24"), to_int("22"), to_int("500")]
    issued = []
    home = SimpleNamespace(id="tc")

    def _villager(i):
        return SimpleNamespace(
            id=i,
            type_name="peasant",
            expanded_is_a=(),
            speed=1,
            hp=25,
            airground_type="ground",
            orders=[SimpleNamespace(keyword="auto_explore")],
            place=home,
            take_order=lambda order, *a, **k: issued.append((i, list(order))),
        )

    v1, v2 = _villager(1), _villager(2)
    ai.units = [v1, v2]
    ai._workers = [v1, v2]
    assert ai._later_age_startable_production_wood()
    Computer._send_explorer(ai)
    assert not issued
