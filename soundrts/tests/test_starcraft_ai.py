# -*- coding: utf-8 -*-
"""StarCraft ai.txt uses mod type names, not Warcraft peasant/footman aliases."""
from __future__ import annotations

import logging
import os
import re
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, get_ai, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit import BuildingSite

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
MOD = "starcraft"
PRA1 = ROOT / "mods" / MOD / "multi" / "pra1.txt"

_VANILLA_GET_NAMES = frozenset(
    {
        "peasant",
        "footman",
        "archer",
        "knight",
        "catapult",
        "priest",
        "mage",
        "dragon",
        "townhall",
        "house",
        "lumbermill",
        "blacksmith",
        "stables",
        "farm",
        "workshop",
        "temple",
        "magestower",
        "flyingmachine",
        "new_flyingmachine",
        "darkarcher",
        "shipyard",
        "boat",
        "destroyer",
        "guardtower",
        "cannontower",
    }
)

_FACTION_SCRIPTS = {
    "terran": {
        "beginner": "sc_terran_easy",
        "easy": "sc_terran_easy",
        "intermediate": "sc_terran_aggressive",
        "aggressive": "sc_terran_aggressive",
        "advanced": "sc_terran_advanced",
        "expert": "sc_terran_expert",
        "nightmare": "sc_terran_nightmare",
    },
    "protoss": {
        "beginner": "sc_protoss_easy",
        "easy": "sc_protoss_easy",
        "intermediate": "sc_protoss_aggressive",
        "aggressive": "sc_protoss_aggressive",
        "advanced": "sc_protoss_advanced",
        "expert": "sc_protoss_expert",
        "nightmare": "sc_protoss_nightmare",
    },
    "zerg": {
        "beginner": "sc_zerg_easy",
        "easy": "sc_zerg_easy",
        "intermediate": "sc_zerg_aggressive",
        "aggressive": "sc_zerg_aggressive",
        "advanced": "sc_zerg_advanced",
        "expert": "sc_zerg_expert",
        "nightmare": "sc_zerg_nightmare",
    },
}


@pytest.fixture
def starcraft_loaded():
    if not (ROOT / "mods" / MOD / "rules.txt").is_file():
        pytest.skip("starcraft mod not present")
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = MOD
    res.set_mods(MOD)
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _get_tokens(script_name):
    names = []
    for line in get_ai(script_name) or ():
        words = line.split()
        if not words or words[0] != "get":
            continue
        for w in words[1:]:
            if not re.match(r"^[0-9]+$", w):
                names.append(w)
    return names


def test_faction_ai_maps_menu_difficulties(starcraft_loaded):
    for faction, mapping in _FACTION_SCRIPTS.items():
        for difficulty, script in mapping.items():
            assert rules.get(faction, difficulty) == [script]
            assert get_ai(script), "missing AI def %s" % script


def test_ai_get_lines_use_starcraft_type_names(starcraft_loaded):
    seen = set()
    for mapping in _FACTION_SCRIPTS.values():
        for script in set(mapping.values()):
            for name in _get_tokens(script):
                seen.add(name)
                assert name not in _VANILLA_GET_NAMES, (
                    "%s still asks for Warcraft type %s" % (script, name)
                )
                assert rules.unit_class(name) is not None, (
                    "%s get-token %s is not a StarCraft type" % (script, name)
                )
    assert {"scv", "marine", "probe", "zealot", "drone", "zergling"} <= seen


def test_clear_drops_warcraft_menu_scripts(starcraft_loaded):
    for name in (
        "beginner",
        "easy",
        "intermediate",
        "aggressive",
        "advanced",
        "expert",
        "nightmare",
    ):
        assert not get_ai(name), "vanilla %s script survived starcraft clear" % name


def test_every_goto_has_a_label(starcraft_loaded):
    for mapping in _FACTION_SCRIPTS.values():
        for script in set(mapping.values()):
            plan = list(get_ai(script) or ())
            labels = {
                line.split()[1]
                for line in plan
                if line.split() and line.split()[0] == "label" and len(line.split()) > 1
            }
            for line in plan:
                words = line.split()
                if len(words) < 2 or words[0] != "goto":
                    continue
                dest = words[1]
                if re.match(r"^[+-]?[0-9]+$", dest):
                    continue
                assert dest in labels, "%s goto %s has no label" % (script, dest)


def test_addon_units_have_host_makers(starcraft_loaded):
    assert "factory" in (rules.get_makers("tank") or ())
    assert "barracks" in (rules.get_makers("marauder") or ())
    assert "starport" in (rules.get_makers("medivac") or ())


def test_long_range_units_have_projectile_speed(starcraft_loaded):
    """Ranged ballistic weapons fly; lasers and flamethrowers stay instant."""
    samples = {
        "marine": 10,
        "marauder": 6,
        "tank": 5,
        "siege_tank": 3.5,
        "ghost": 8,
        "thor": 5,
        "dragoon": 6,
        "photon_cannon": 6,
        "phoenix": 8,
        "carrier": 5,
        "hydralisk": 8,
        "mutalisk": 6,
    }
    for name, tiles_s in samples.items():
        uc = rules.unit_class(name)
        assert uc is not None, name
        assert getattr(uc, "rdg_projectile", 0), name
        assert getattr(uc, "rdg_projectile_speed", 0) == tiles_s * PRECISION, name
    for name in ("battlecruiser", "hellion"):
        uc = rules.unit_class(name)
        assert uc is not None, name
        assert not getattr(uc, "rdg_projectile_speed", 0), name


def test_workers_have_train_time(starcraft_loaded):
    for name in ("scv", "probe", "drone"):
        uc = rules.unit_class(name)
        assert uc is not None, name
        assert getattr(uc, "time_cost", 0) == 12 * PRECISION, name


def test_sc2_faster_train_and_gather(starcraft_loaded):
    """Train/build/research times and trip yields match SC2 Faster."""
    times = {
        "marine": 18,
        "marauder": 21,
        "zealot": 27,
        "dragoon": 27,
        "zergling": 17,
        "hydralisk": 24,
        "command_center": 71,
        "nexus": 71,
        "hatchery": 71,
        "barracks": 46,
        "gateway": 46,
        "spawning_pool": 46,
        "tech_lab": 18,
        "reactor": 36,
        "infantry_weapons": 114,
        "infantry_weapons_2": 136,
        "infantry_weapons_3": 157,
        "u_stim": 100,
        "u_burrow": 71,
    }
    for name, seconds in times.items():
        uc = rules.unit_class(name)
        assert uc is not None, name
        assert getattr(uc, "time_cost", 0) == seconds * PRECISION, name
    hatch = rules.unit_class("hatchery")
    assert getattr(hatch, "larva_spawn_time", 0) == 8 * PRECISION
    mineral = rules.unit_class("mineral_field")
    gas = rules.unit_class("assimilator")
    geyser = rules.unit_class("geyser")
    assert getattr(mineral, "extraction_qty", 0) in (5, 5 * PRECISION)
    assert getattr(gas, "extraction_qty", 0) in (4, 4 * PRECISION)
    assert getattr(gas, "production_qty", 0) in (4, 4 * PRECISION)
    assert getattr(gas, "depleted_production_qty", 0) in (2, 2 * PRECISION)
    assert getattr(geyser, "deposit_volume", 0) == 2250


_MAP_DEPOSIT_CMD = re.compile(
    r"^[ \t]*;?[ \t]*(goldmines|goldmine|woods|wood)[ \t]+"
)


def test_starcraft_maps_use_mineral_field_and_geyser():
    maps = list((ROOT / "mods" / MOD / "multi").glob("*.txt"))
    maps += list((ROOT / "mods" / MOD / "single").rglob("*.txt"))
    assert maps
    leftovers = []
    saw_minerals = False
    saw_gas = False
    for path in maps:
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _MAP_DEPOSIT_CMD.match(line):
                leftovers.append("%s:%s %s" % (path.name, i, line.strip()))
            words = line.split()
            if words and words[0] in ("mineral_field", "mineral_fields"):
                saw_minerals = True
            if words and words[0] in ("geyser", "geysers"):
                saw_gas = True
    assert not leftovers, leftovers[:8]
    assert saw_minerals and saw_gas


@pytest.mark.skipif(not PRA1.is_file(), reason="starcraft pra1 map not present")
def test_pra1_spawns_mineral_fields_and_geysers(starcraft_loaded):
    world = World([], 7)
    world._parse_map(PRA1.read_text(encoding="utf-8"))
    kinds = {cls for _, cls, _ in world.map_objects}
    assert "mineral_field" in kinds
    assert "geyser" in kinds
    assert "goldmine" not in kinds
    assert "wood" not in kinds


@pytest.mark.skipif(not PRA1.is_file(), reason="starcraft pra1 map not present")
def test_pra1_spawns_workers_from_peasant_alias(starcraft_loaded):
    world = World([], 7)
    world._parse_map(PRA1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("human", None)
    human.faction = "terran"
    human.alliance = "1"
    ai_client = DummyClient("aggressive")
    ai_client.faction = "zerg"
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False, equivalents=True)
    human_p = next(p for p in world.players if not isinstance(p, Computer))
    zerg_p = next(p for p in world.players if isinstance(p, Computer))
    assert sum(1 for u in human_p.units if u.type_name == "scv") == 10
    assert sum(1 for u in human_p.units if u.type_name == "command_center") == 1
    assert sum(1 for u in zerg_p.units if u.type_name == "drone") == 10
    assert sum(1 for u in zerg_p.units if u.type_name == "hatchery") == 1


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


@pytest.mark.skipif(not PRA1.is_file(), reason="starcraft pra1 map not present")
@pytest.mark.parametrize(
    "faction,want",
    [
        ("terran", {"marine", "barracks"}),
        ("protoss", {"zealot", "gateway"}),
        ("zerg", {"zergling", "spawning_pool"}),
    ],
)
def test_aggressive_computer_uses_race_units(starcraft_loaded, faction, want):
    world = World([], 7)
    world._parse_map(PRA1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("human", None)
    human.faction = faction
    human.alliance = "1"
    ai_client = DummyClient("aggressive")
    ai_client.faction = faction
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False, equivalents=True)

    comp = next(p for p in world.players if isinstance(p, Computer))
    assert comp.faction == faction
    ticks = int(90 * 1000 / VIRTUAL_TIME_INTERVAL)
    hit = False
    for _ in range(ticks):
        world.update()
        if set(_type_names(comp)) & want:
            hit = True
            break
    assert hit, (
        "%s aggressive AI never made %s; units=%s line=%s"
        % (
            faction,
            want,
            _type_names(comp),
            comp._plan[comp._line_nb] if comp._plan else "",
        )
    )
