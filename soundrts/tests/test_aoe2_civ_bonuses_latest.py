# -*- coding: utf-8 -*-
"""AoE2 DE latest civilization / team bonus wiring."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    return r


def _effects(rules, civ):
    return rules._dict.get(civ, {}).get("on_phase_effects") or []


def _team(rules, civ):
    return rules._dict.get(civ, {}).get("team_on_phase_effects") or []


def _flat(entries):
    parts = []
    for e in entries:
        parts.extend(str(x) for x in e)
    return " ".join(parts)


def test_chinese_latest_bonuses(aoe2_rules):
    d = aoe2_rules._dict["chinese"]
    assert d.get("starting_resources") == ["100", "150", "0", "200"]
    assert d.get("starting_units") == ["town_center", "6", "peasant", "scout_cavalry"]
    disc = d.get("research_cost_discount") or []
    assert "-5%" in disc and "-10%" in disc and "-15%" in disc
    assert d.get("team_farm_food_pct") in (10, ["10"], 10)
    pop = aoe2_rules.get("chinese_town_center", "population_provided")
    assert str(pop[0] if isinstance(pop, list) else pop) == "15"
    assert "fire_galley" in _flat(_effects(aoe2_rules, "chinese"))


_DE_START_3_SCOUT = ["town_center", "3", "peasant", "scout_cavalry"]
_AOE2_CIVS = (
    "britons",
    "franks",
    "chinese",
    "mongols",
    "byzantines",
    "japanese",
    "teutons",
    "vikings",
    "vietnamese",
    "portuguese",
    "aztecs",
    "celts",
)


def test_de_dark_age_start_matches_aoe2(aoe2_rules):
    """TC + 3 vils + scout; China 6 vils + scout; Aztecs 3 vils + eagle. No house."""
    for civ in _AOE2_CIVS:
        units = list(aoe2_rules.get(civ, "starting_units") or [])
        assert "house" not in units, civ
        assert units[0] == "town_center", civ
        if civ == "chinese":
            assert units == ["town_center", "6", "peasant", "scout_cavalry"]
            assert aoe2_rules.get(civ, "starting_resources") == ["100", "150", "0", "200"]
        elif civ == "aztecs":
            assert units == ["town_center", "3", "peasant", "aztec_eagle_scout"]
            assert aoe2_rules.get(civ, "starting_resources") == ["150", "200", "200", "200"]
        else:
            assert units == _DE_START_3_SCOUT, civ
            assert aoe2_rules.get(civ, "starting_resources") == ["100", "200", "200", "200"]


def test_britons_exclude_skirmisher_range(aoe2_rules):
    text = _flat(_effects(aoe2_rules, "britons"))
    assert "longbowman" in text
    assert "skirmisher" not in text or "time_cost" in _flat(_team(aoe2_rules, "britons"))
    castle = [e for e in _effects(aoe2_rules, "britons") if e and e[0] == "castle_age"]
    assert any("rdg_range" in e for e in castle)
    assert not any("skirmisher" in e and "rdg_range" in e for e in castle)
    assert any("cost" in e and "town_center" in e for e in castle)


def test_franks_cavalry_from_feudal(aoe2_rules):
    text = _flat(_effects(aoe2_rules, "franks"))
    assert "feudal_age" in text and "hp_max" in text
    assert "dark_age hp_max" not in " ".join(
        " ".join(str(x) for x in e) for e in _effects(aoe2_rules, "franks")
        if e and e[0] == "dark_age" and "hp_max" in e
    )
    assert _team(aoe2_rules, "franks")


def test_vikings_flat_feudal_hp(aoe2_rules):
    entries = _effects(aoe2_rules, "vikings")
    feudal = [e for e in entries if e and e[0] == "feudal_age" and "hp_max" in e]
    assert feudal
    assert not any(e and e[0] == "castle_age" and "hp_max" in e for e in entries)


def test_celts_speed_scales_from_dark(aoe2_rules):
    entries = _effects(aoe2_rules, "celts")
    assert any(e and e[0] == "dark_age" and "speed" in e for e in entries)
    team = _flat(_team(aoe2_rules, "celts"))
    assert "time_cost" in team


def test_grant_tech_tables(aoe2_rules):
    byz = aoe2_rules._dict["byzantines"].get("grant_tech_on_phase") or []
    flat = " ".join(" ".join(str(x) for x in e) for e in byz)
    assert "town_watch" in flat and "town_patrol" in flat
    viet = aoe2_rules._dict["vietnamese"].get("grant_tech_on_phase") or []
    assert any("conscription" in e for e in viet)


def test_team_farm_pct_helper():
    from soundrts.world_civ_bonuses import apply_farm_food_team_pct

    class P:
        allied_victory = None
        faction = "chinese"

    class B:
        player = P()

    P.allied_victory = [B.player]
    from soundrts.definitions import Rules
    from soundrts import definitions as defs

    r = Rules()
    r.load("def chinese\nteam_farm_food_pct 10\n")
    saved = defs.rules._dict
    defs.rules._dict = r._dict
    try:
        assert apply_farm_food_team_pct(B(), 175) == 192
    finally:
        defs.rules._dict = saved


def test_vietnamese_team_share_and_celt_steal_flags(aoe2_rules):
    rows = aoe2_rules._dict["vietnamese"].get("team_share_research") or []
    flat = []
    for e in rows:
        if isinstance(e, (list, tuple)):
            flat.extend(str(x) for x in e)
        else:
            flat.append(str(e))
    assert "imperial_skirmisher" in flat
    assert "archery_range" in flat
    celts = aoe2_rules._dict["celts"]
    assert celts.get("herdable_steal_ignore_guards") in (1, ["1"])
    assert celts.get("herdable_steal_protected") in (1, ["1"])
    req = aoe2_rules.get("imperial_skirmisher", "requirements") or []
    rflat = [str(x) for x in req]
    assert "elite_skirmisher" in rflat
    assert "imperial_age" in rflat


def test_team_share_research_names_from_vietnamese_ally(aoe2_rules, monkeypatch):
    from soundrts.world_civ_bonuses import team_share_research_names
    import soundrts.world_civ_bonuses as wcb

    monkeypatch.setattr(wcb, "rules", aoe2_rules)
    viet = SimpleNamespace(faction="vietnamese")
    brit = SimpleNamespace(faction="britons", allied_victory=None)
    brit.allied_victory = [brit, viet]
    assert "imperial_skirmisher" in team_share_research_names(brit)


def test_team_share_research_host_filter():
    from soundrts.world_build_rules import _host_accepts_shared_research

    archery = SimpleNamespace(
        type_name="briton_archery",
        expanded_is_a=("archery_range", "building"),
    )
    barracks = SimpleNamespace(
        type_name="barracks",
        expanded_is_a=("barracks", "building"),
    )
    assert _host_accepts_shared_research(
        archery, (), "imperial_skirmisher", ("archery_range",)
    )
    assert not _host_accepts_shared_research(
        barracks, (), "imperial_skirmisher", ("archery_range",)
    )
    assert _host_accepts_shared_research(
        barracks, ("imperial_skirmisher",), "imperial_skirmisher", ()
    )


def test_reveal_enemy_types_listed_on_vietnamese_rules(aoe2_rules):
    from soundrts.definitions import Rules

    types = aoe2_rules.get("vietnamese", "reveal_enemy_town_centers") or []
    flat = [str(x) for x in (types if isinstance(types, (list, tuple)) else [types])]
    assert "town_center" in flat
    assert "1" not in flat
    brit = aoe2_rules.get("britons", "reveal_enemy_town_centers") or []
    assert not brit
    assert "reveal_enemy_town_centers" in Rules.string_list_properties
    assert "reveal_enemy_town_centers" not in Rules.int_properties


def test_reveal_enemy_types_are_rules_not_hardcoded(monkeypatch):
    import inspect
    from soundrts import world_civ_bonuses as wcb
    from soundrts.definitions import Rules

    src = inspect.getsource(wcb.reveal_enemy_town_centers) + inspect.getsource(
        wcb._unit_matches_reveal_types
    )
    assert "vietnamese" not in src.lower()
    assert "'town_center'" not in src and '"town_center"' not in src
    assert "townhall" not in src

    r = Rules()
    r.load("def spy\nclass race\nreveal_enemy_town_centers castle\n")
    monkeypatch.setattr(wcb, "rules", r)

    class P:
        def __init__(self, **kw):
            self.__dict__.update(kw)

        def __hash__(self):
            return id(self)

        def __eq__(self, other):
            return self is other

    place_castle = object()
    place_tc = object()
    castle = SimpleNamespace(
        type_name="keep",
        expanded_is_a=("castle", "building"),
        place=place_castle,
    )
    tc = SimpleNamespace(
        type_name="town_center",
        expanded_is_a=("town_center", "building"),
        place=place_tc,
    )
    enemy = P(neutral=False, units=[castle, tc])
    spy = P(
        faction="spy",
        allied_victory=None,
        observed_before_squares=set(),
        strictly_observed_before_squares=set(),
    )
    spy.allied_victory = [spy]
    world = SimpleNamespace(players=[spy, enemy])
    spy.world = world
    wcb.reveal_enemy_town_centers(spy)
    assert place_castle in spy.observed_before_squares
    assert place_tc not in spy.observed_before_squares
