# -*- coding: utf-8 -*-
"""Default res AI: intermediate computers still build barracks on jl1."""
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit import BuildingSite

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
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
    ai.faction = kwargs.get("faction", None)
    ai.upgrades = list(kwargs.get("upgrades", ()))
    ai.units = list(kwargs.get("units", ()))
    ai._plan = list(kwargs.get("plan", ()))
    ai._workers = []
    ai._type_discovery_cache = None
    ai._line_nb = kwargs.get("line_nb", 0)
    return ai


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


def test_res_feudal_does_not_block_footman_get(res_loaded):
    from soundrts.lib.nofloat import to_int

    ai = _bare_ai(plan=["get 3 peasant 1 footman"], faction="human_faction")
    assert not ai._feudal_age_saves_food()
    assert not ai._defer_plan_get_token("footman", saving_for_feudal=False)
    assert not ai._defer_plan_get_token(
        "footman", saving_for_feudal=ai._feudal_age_saves_food()
    )
    assert ai._resource_low_threshold(2) == to_int("40")
    ai.nb = lambda n: 0
    ai.future_nb = lambda n: 0
    ai.resources = [to_int("6"), to_int("8"), 0]
    gold, wood = ai._plan_next_production_building_cost()
    assert gold == to_int("7")
    assert wood == to_int("9")
    assert ai._would_spend_past_plan_building((to_int("5"), to_int("5")))
    assert not ai._saving_food_for_age()
    assert not ai._ruleset_has_expensive_food_age()
    assert ai._plan_expensive_wood_reserve() == 0
    assert ai._has_dedicated_dropoff_types()
    assert ai._auto_warehouse_expansion_enabled()
    hall = ai._preferred_warehouse_class()
    assert hall is not None
    assert hall.type_name == "townhall"


def test_owned_townhall_is_not_held_for_later_barracks(res_loaded):
    """Peasants must not count as an owned barracks when the opener is the hall."""
    ai = _bare_ai(
        plan=["get townhall 10 peasant", "get 5 footman"],
        faction="human_faction",
    )

    def _nb(n):
        if n == "townhall":
            return 1
        if n == "peasant":
            return 10
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert not ai._defer_plan_get_token("townhall", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("peasant", saving_for_feudal=False)


def test_res_barracks_army_not_held_for_darkarcher_or_shipyard(res_loaded):
    """Owned barracks must train; unit→unit makers and land-map docks must not bank."""
    from soundrts.lib.nofloat import to_int

    ai = _bare_ai(
        plan=[
            "get 8 peasant 5 footman 15 archer",
            "get 9 peasant 10 knight 1 darkarcher",
            "get 9 peasant 1 lumbermill 1 shipyard 2 destroyer",
        ],
        upgrades=["dark_age", "feudal_age"],
        faction="human_faction",
    )
    ai.resources = [to_int("200"), to_int("200"), to_int("200"), 0]

    def _nb(n):
        if n in ("barracks", "townhall", "lumbermill"):
            return 1
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert ai._first_startable_unpaid_maker_cost() == (0, 0)
    assert not ai._defer_plan_get_token("footman", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("archer", saving_for_feudal=False)


def test_res_jl1_intermediate_builds_barracks(res_loaded):
    if not JL1.is_file():
        pytest.skip("res jl1 map not present")
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION as P

    faction = rules.factions[0] if rules.factions else "human_faction"
    text = JL1.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * P)
    world._build_map()
    p1 = DummyClient("intermediate")
    p1.faction = faction
    p1.alliance = "1"
    p2 = DummyClient("intermediate")
    p2.faction = faction
    p2.alliance = "2"
    world.populate_map([p1, p2], random_starts=False)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "intermediate"
    ]
    assert len(comps) == 2

    mil_at = None
    game_limit_ms = 8 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    wanted = ("barracks", "footman")
    for _ in range(ticks):
        world.update()
        for c in comps:
            names = _type_names(c)
            if any(n in wanted for n in names):
                mil_at = world.time
                break
        if mil_at is not None:
            break

    assert mil_at is not None, (
        "expected barracks/footman on default res jl1; "
        f"types={[(_type_names(c), list(getattr(c, 'upgrades', []) or [])) for c in comps]}"
    )
    assert mil_at <= 8 * 60 * 1000, mil_at


def test_res_jl1_beginner_reaches_feudal_or_barracks(res_loaded):
    """Beginner opener is peasants+footmen: must not ping-pong gold/wood forever."""
    if not JL1.is_file():
        pytest.skip("res jl1 map not present")
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION as P

    faction = rules.factions[0] if rules.factions else "human_faction"
    text = JL1.read_text(encoding="utf-8")
    world = World([], 42)
    world._parse_map(text)
    world.square_width = int(world.square_width * P)
    world._build_map()
    human = DummyClient("timers")
    human.faction = faction
    human.alliance = "1"
    cpu = DummyClient("beginner")
    cpu.faction = faction
    cpu.alliance = "2"
    world.populate_map([human, cpu], random_starts=False)

    comps = [
        p
        for p in world.players
        if isinstance(p, Computer) and getattr(p, "AI_type", None) == "beginner"
    ]
    assert len(comps) == 1
    c = comps[0]

    done_at = None
    game_limit_ms = 8 * 60 * 1000
    ticks = int(game_limit_ms / VIRTUAL_TIME_INTERVAL)
    wanted = ("barracks", "footman")
    for _ in range(ticks):
        world.update()
        names = _type_names(c)
        upg = list(getattr(c, "upgrades", []) or [])
        if any(n in wanted for n in names) or "feudal_age" in upg:
            done_at = world.time
            break

    assert done_at is not None, (
        "beginner on jl1 stayed idle (no feudal/barracks); "
        f"types={_type_names(c)} upgrades={list(getattr(c, 'upgrades', []) or [])} "
        f"res={list(getattr(c, 'resources', []) or [])} line={getattr(c, '_line_nb', None)}"
    )
    assert done_at <= 8 * 60 * 1000, done_at


@pytest.mark.skipif(
    not (ROOT / "mods" / "starcraft" / "rules.txt").is_file(),
    reason="starcraft mod not present",
)
def test_starcraft_does_not_enable_expensive_food_age_gates():
    """StarCraft has no food age-up; AoE2 farm/feudal gates must stay off."""
    from soundrts.lib.nofloat import to_int

    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    try:
        config.mods = "starcraft"
        res.set_mods("starcraft")
        res.load_rules_and_ai()
        ai = _bare_ai(plan=["get 8 scv 1 barracks"])
        ai.nb = lambda n: 1
        ai.future_nb = lambda n: 1
        assert not ai._ruleset_has_expensive_food_age()
        assert ai._resource_low_threshold(2) == to_int("40")
        assert not ai._saving_food_for_age()
        # Empty workers see every race's can_build (including leftover res mill).
        # A real SC computer only has SCVs; they have no single-resource drop-off.
        ai._workers = [
            type(
                "W",
                (),
                {
                    "type_name": "scv",
                    "can_build": (
                        "command_center",
                        "barracks",
                        "factory",
                        "starport",
                        "refinery",
                        "engineering_bay",
                        "armory",
                        "bunker",
                        "supply_depot",
                        "tech_lab",
                        "reactor",
                        "ghost_academy",
                    ),
                },
            )()
        ]
        ai._type_discovery_cache = None
        assert not ai._has_dedicated_dropoff_types()
        assert not ai._auto_warehouse_expansion_enabled()
    finally:
        config.mods = old
        res.set_mods(old or "")
        if old:
            res.load_rules_and_ai()
        logging.disable(logging.NOTSET)
