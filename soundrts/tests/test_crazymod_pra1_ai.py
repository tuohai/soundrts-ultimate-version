# -*- coding: utf-8 -*-
"""CrazyMod pra1 computers must leave the hall opener and start producing."""
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit import BuildingSite

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
MOD = "crazyMod9beta10"
PRA1 = ROOT / "mods" / MOD / "multi" / "pra1.txt"

_MIL_HINTS = (
    "barracks",
    "arbaletrier",
    "knight",
    "bivouac_d_entrainement",
    "chasseresse",
    "archer",
    "termitiere",
    "larve",
    "termite_gardien",
    "camp_militaire",
    "mousquetaire",
    "usine_robotique",
    "caveau",
    "goule",
    "arene_boisee",
    "archerot",
    "fosse",
    "troll_cogneur",
    "tour_de_la_terre",
    "elemental_de_terre",
    "coutellerie",
    "rodeur",
)


@pytest.fixture
def crazymod_loaded():
    if not (ROOT / "mods" / MOD / "rules.txt").is_file():
        pytest.skip("crazyMod9beta10 not present")
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = MOD
    res.set_mods(MOD)
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
    ai.faction = kwargs.get("faction", "traditionnel")
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


def test_long_range_units_have_projectile_speed(crazymod_loaded):
    """Ranged shooters use rdg_projectile_speed (tiles/s); lasers stay instant."""
    samples = {
        "arbaletrier": 7,
        "mousquetaire": 10,
        "tour_a_baliste": 3.5,
        "cannontower": 4,
        "ogre_lanceur_de_roche": 3,
        "sam": 3.5,
        "elephant_a_tourelle": None,
    }
    for name, tiles_s in samples.items():
        uc = rules.unit_class(name)
        assert uc is not None, name
        if name == "elephant_a_tourelle":
            assert getattr(uc, "mdg_projectile", 0)
            assert getattr(uc, "mdg_projectile_speed", 0) == 5 * PRECISION
            continue
        assert getattr(uc, "rdg_projectile", 0), name
        assert getattr(uc, "rdg_projectile_speed", 0) == tiles_s * PRECISION, name
    laser = rules.unit_class("tour_laser")
    assert laser is not None
    assert not getattr(laser, "rdg_projectile_speed", 0)


def test_owned_hall_is_not_held_for_later_barracks(crazymod_loaded):
    """Workers must not count as an 'owned production building' for the hall."""
    ai = _bare_ai(
        faction="traditionnel",
        plan=[
            "get chatelet 10 serf",
            "get 12 arbaletrier 6 knight",
        ],
    )

    def _nb(n):
        if n == "chatelet":
            return 1
        if n == "serf":
            return 10
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    assert not ai._defer_plan_get_token("chatelet", saving_for_feudal=False)
    assert not ai._defer_plan_get_token("serf", saving_for_feudal=False)


def test_follow_plan_completes_owned_hall_opener(crazymod_loaded):
    ai = _bare_ai(
        faction="traditionnel",
        plan=["get chatelet 10 serf", "get 12 arbaletrier 6 knight"],
    )

    def _nb(n):
        if n == "chatelet":
            return 1
        if n == "serf":
            return 10
        return 0

    ai.nb = _nb
    ai.future_nb = lambda n: _nb(n)
    ai.watchdog = 0
    ai._previous_linechange = 0
    ai._play_memo = {}
    ai._follow_plan()
    assert ai._plan[ai._line_nb] == "get 12 arbaletrier 6 knight"


@pytest.mark.skipif(not PRA1.is_file(), reason="crazyMod pra1 map not present")
def test_pra1_nightmare_computers_start_producing(crazymod_loaded):
    world = World([], 42)
    world._parse_map(PRA1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("human", None)
    human.faction = "traditionnel"
    human.alliance = "1"
    clients = [human]
    for _ in range(3):
        c = DummyClient("nightmare")
        c.faction = "random_faction"
        c.alliance = "2"
        clients.append(c)
    world.populate_map(clients, random_starts=False, equivalents=True)

    comps = [p for p in world.players if isinstance(p, Computer)]
    assert len(comps) == 3
    for c in comps:
        assert c.units, f"{c.faction} spawned no units"

    produced_at = None
    ticks = int(3 * 60 * 1000 / VIRTUAL_TIME_INTERVAL)
    for _ in range(ticks):
        world.update()
        for c in comps:
            names = _type_names(c)
            if any(n in _MIL_HINTS for n in names):
                produced_at = world.time
                break
            line = c._plan[c._line_nb] if c._plan else ""
            if line.startswith("get ") and "chatelet" not in line and "serf" not in line:
                # Left the opener; any later get counts as playing.
                if "planque" not in line and "couveuse" not in line:
                    if not any(
                        hall in line
                        for hall in (
                            "mairie",
                            "garage",
                            "cimetiere",
                            "clairiere",
                            "campement",
                            "cercle_des_elements",
                            "cabane",
                        )
                    ):
                        produced_at = world.time
                        break
        if produced_at is not None:
            break

    assert produced_at is not None, (
        "crazyMod pra1 nightmare AIs stayed idle; "
        f"state={[(_type_names(c), c.faction, c._plan[c._line_nb] if c._plan else '') for c in comps]}"
    )


def test_vermine_skill_summon_is_a_maker(crazymod_loaded):
    """Hatchery `can_use_skill` summons must count as makers, not only `can_use`."""
    assert "couveuse" in rules.get_makers("larve")
    assert "couveuse" in rules.get_makers("souche")
    assert "souche" in rules.get_makers("termitiere")
    assert "larve" in rules.get_makers("termite_gardien")


@pytest.mark.skipif(not PRA1.is_file(), reason="crazyMod pra1 map not present")
def test_vermine_computer_uses_insect_units(crazymod_loaded):
    world = World([], 42)
    world._parse_map(PRA1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    human = DirectClient("human", None)
    human.faction = "traditionnel"
    human.alliance = "1"
    ai_client = DummyClient("nightmare")
    ai_client.faction = "vermine"
    ai_client.alliance = "2"
    world.populate_map([human, ai_client], random_starts=False, equivalents=True)

    comp = next(p for p in world.players if isinstance(p, Computer))
    assert comp.faction == "vermine"

    ticks = int(3 * 60 * 1000 / VIRTUAL_TIME_INTERVAL)
    saw_termitiere = False
    saw_insect_army = False
    for _ in range(ticks):
        world.update()
        names = set(_type_names(comp))
        if "termitiere" in names:
            saw_termitiere = True
        if names & {"termite_gardien", "termite_conquerant", "guepe_colerique", "larve"}:
            saw_insect_army = True
        if saw_termitiere and saw_insect_army:
            break

    assert saw_termitiere, (
        "vermine AI never made a termite nest; "
        f"units={_type_names(comp)} line={comp._plan[comp._line_nb] if comp._plan else ''}"
    )
    assert saw_insect_army, (
        "vermine AI never produced insect units; "
        f"units={_type_names(comp)} line={comp._plan[comp._line_nb] if comp._plan else ''}"
    )
