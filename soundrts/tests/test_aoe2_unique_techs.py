# -*- coding: utf-8 -*-
"""AoE2 unique tech effects must be complete (DE mapping + can_use_tech wiring)."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = Path(__file__).resolve().parents[2] / "res" / "rules.txt"
    mod = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    r = Rules()
    r.load(base.read_text(encoding="utf-8"), mod.read_text(encoding="utf-8"))
    return r


def _techs(rules, unit):
    return list(rules.get(unit, "can_use_tech") or [])


def _effect(rules, name):
    return rules.get(name, "effect")


def test_yeomen_effects_and_beneficiaries(aoe2_rules):
    eff = _effect(aoe2_rules, "yeomen")
    flat = str(eff)
    assert "rdg_range" in flat and "archer_unit" in flat and "-cavalry" in flat
    assert "rdg" in flat and "scouttower" in flat
    for u in (
        "aoe_archer",
        "crossbowman",
        "arbalester",
        "skirmisher",
        "elite_skirmisher",
        "longbowman",
        "elite_longbowman",
        "scouttower",
        "guardtower",
        "keeptower",
    ):
        assert "yeomen" in _techs(aoe2_rules, u), u
        # upgrade tiers must still inherit blacksmith/archery techs
        if u in ("crossbowman", "arbalester", "elite_skirmisher", "elite_longbowman"):
            assert "fletching" in _techs(aoe2_rules, u), u


def test_warwolf_trebuchet_blast(aoe2_rules):
    eff = str(_effect(aoe2_rules, "warwolf"))
    assert "rdg_splash" in eff and "rdg_radius" in eff and "trebuchet" in eff
    assert "warwolf" in _techs(aoe2_rules, "trebuchet")


def test_chivalry_cavalry_train_time(aoe2_rules):
    eff = _effect(aoe2_rules, "chivalry")
    assert "time_cost" in str(eff) and "-40%" in str(eff)
    for u in (
        "scout_cavalry",
        "light_cavalry",
        "hussar",
        "aoe_knight",
        "cavalier",
        "paladin",
        "camel_rider",
        "heavy_camel_rider",
        "frankish_knight",
        "frankish_cavalier",
        "frankish_paladin",
    ):
        t = _techs(aoe2_rules, u)
        assert "chivalry" in t, u
        assert "forging" in t or "husbandry" in t, u


def test_bearded_axe_axemen_range(aoe2_rules):
    eff = str(_effect(aoe2_rules, "bearded_axe"))
    assert "mdg_range" in eff and "throwing_axeman" in eff
    assert "bearded_axe" in _techs(aoe2_rules, "throwing_axeman")
    assert "bearded_axe" in _techs(aoe2_rules, "elite_throwing_axeman")


def test_great_wall_hp(aoe2_rules):
    eff = str(_effect(aoe2_rules, "great_wall"))
    assert "hp_max" in eff and "30%" in eff
    for u in ("wall", "gate", "fortified_wall", "scouttower", "guardtower", "keeptower", "cannontower"):
        assert "great_wall" in _techs(aoe2_rules, u), u


def test_rocketry_ckn_scorpion(aoe2_rules):
    eff = str(_effect(aoe2_rules, "rocketry"))
    assert "chu_ko_nu" in eff and "scorpion" in eff
    assert "rocketry" in _techs(aoe2_rules, "chu_ko_nu")
    assert "rocketry" in _techs(aoe2_rules, "elite_chu_ko_nu")
    assert "rocketry" in _techs(aoe2_rules, "scorpion")
    assert "rocketry" in _techs(aoe2_rules, "heavy_scorpion")


def test_drill_siege_speed(aoe2_rules):
    eff = str(_effect(aoe2_rules, "drill"))
    assert "speed" in eff and "50%" in eff
    for u in (
        "battering_ram",
        "capped_ram",
        "mangonel",
        "onager",
        "scorpion",
        "trebuchet",
        "siege_tower",
    ):
        assert "drill" in _techs(aoe2_rules, u), u


def test_greek_fire_ships_and_tower(aoe2_rules):
    eff = str(_effect(aoe2_rules, "greek_fire"))
    assert "fire_galley" in eff and "dromon" in eff and "cannontower" in eff
    for u in ("fire_galley", "fire_ship", "fast_fire_ship", "dromon", "cannontower"):
        assert "greek_fire" in _techs(aoe2_rules, u), u
    assert "shipwright" in _techs(aoe2_rules, "dromon")


def test_logistica_cataphract_trample(aoe2_rules):
    eff = str(_effect(aoe2_rules, "logistica"))
    assert "mdg_splash" in eff and "mdg_radius" in eff and "mdg_vs" in eff
    assert "logistica" in _techs(aoe2_rules, "cataphract")
    assert "logistica" in _techs(aoe2_rules, "elite_cataphract")


def test_nomads_defined_and_engine_hook():
    from soundrts.worldplayerbase import base as player_base

    src = Path(player_base.__file__).read_text(encoding="utf-8")
    assert 'retain_house_pop' in src or '"nomads"' in src
    assert "nomads" in src
    rules_path = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    text = rules_path.read_text(encoding="utf-8")
    assert "def nomads" in text
