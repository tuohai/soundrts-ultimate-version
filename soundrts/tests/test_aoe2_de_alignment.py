# -*- coding: utf-8 -*-
"""AoE2 DE tech alignment smoke tests."""
from __future__ import annotations

import types
from pathlib import Path

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


def _flat(eff):
    if not eff:
        return ""
    parts = []
    for item in eff if isinstance(eff[0], list) else [eff]:
        parts.extend(str(x) for x in item)
    return " ".join(parts)


def test_bloodlines_plus_20(aoe2_rules):
    assert "20" in _flat(aoe2_rules.get("bloodlines", "effect"))


def test_loom_melee_armor(aoe2_rules):
    s = _flat(aoe2_rules.get("loom", "effect"))
    assert "mdf" in s and "rdf" in s


def test_gambesons_and_supplies_on_militia(aoe2_rules):
    techs = aoe2_rules.get("militia", "can_use_tech") or []
    assert "gambesons" in techs
    assert "supplies" in techs


def test_ballistics_no_range_bonus(aoe2_rules):
    s = _flat(aoe2_rules.get("ballistics", "effect"))
    assert "rdg_range" not in s
    assert "rdg_cover" not in s
    assert "projectile_lead" in s
    assert "town_center" in s
    assert "info" in s


def test_aoe2_archer_uses_projectile_speed(aoe2_rules):
    assert aoe2_rules.get("aoe_archer", "rdg_projectile_speed")
    assert not aoe2_rules.get("aoe_archer", "rdg_delay")
    assert aoe2_rules.get("mangonel", "mdg_projectile_speed")


def test_ballistics_engine_uses_projectile_lead_flag():
    from soundrts.combat import damage_effects as de

    src = Path(de.__file__).read_text(encoding="utf-8")
    assert "projectile_lead" in src
    assert '"ballistics"' not in src
    assert "missed," in src


def test_chemistry_galley_not_hc(aoe2_rules):
    s = _flat(aoe2_rules.get("chemistry", "effect"))
    assert "galley" in s
    assert "-hand_cannoneer" in s


def test_thumb_ring_excludes_cavalry(aoe2_rules):
    s = _flat(aoe2_rules.get("thumb_ring", "effect"))
    assert "-cavalry" in s


def test_town_watch_and_careening_exist(aoe2_rules):
    assert aoe2_rules.get("town_watch", "class")
    assert aoe2_rules.get("town_patrol", "class")
    assert aoe2_rules.get("careening", "class")
    assert aoe2_rules.get("dry_dock", "class")
    assert aoe2_rules.get("supplies", "class")


def test_heavy_plow_on_peasant(aoe2_rules):
    peasant_techs = aoe2_rules.get("peasant", "can_use_tech") or []
    assert "heavy_plow" in peasant_techs
    assert "horse_collar" in peasant_techs
    assert "crop_rotation" in peasant_techs
    assert "frank_horse_collar" not in peasant_techs
    assert "frank_heavy_plow" not in peasant_techs
    assert "frank_crop_rotation" not in peasant_techs
    frank_techs = aoe2_rules.get("frank_villager", "can_use_tech") or []
    assert "frank_heavy_plow" in frank_techs
    assert "heavy_plow" not in frank_techs
    assert aoe2_rules.get("franks", "peasant") == ["frank_villager"]


def test_chinese_tc_bonus(aoe2_rules):
    assert aoe2_rules.get("chinese", "townhall") == ["chinese_town_center"]
    pop = aoe2_rules.get("chinese_town_center", "population_provided")
    assert pop in (["15"], 15, ["15"]) or (pop and str(pop[0]) == "15")
    sight = aoe2_rules.get("chinese_town_center", "sight_range")
    assert sight


def test_franks_cavalry_hp_phase(aoe2_rules):
    # on_phase stored in rules dict
    raw = aoe2_rules._dict.get("franks", {})
    assert any("hp_max" in str(v) and "cavalry" in str(v) for v in raw.values()) or "cavalry" in str(
        raw
    )


def test_trebuchet_de_accuracy_units_15_buildings_80(aoe2_rules):
    from soundrts.combat.hit_miss import HitMissMixin
    from soundrts.lib.nofloat import to_int

    cls = aoe2_rules.unit_class("trebuchet")
    assert cls.rdg_cover == to_int("15")
    assert cls.rdg_cover_vs.get("building") == to_int("65")

    class _Treb(HitMissMixin):
        rdg_cover = cls.rdg_cover
        rdg_cover_vs = dict(cls.rdg_cover_vs)

    treb = _Treb()
    building = types.SimpleNamespace(
        type_name="aoe_castle", expanded_is_a=("building",)
    )
    unit = types.SimpleNamespace(type_name="militia", expanded_is_a=("infantry",))
    assert treb._get_ranged_cover_vs(building) == 80
    assert treb._get_ranged_cover_vs(unit) == 15


def test_aoe2_towers_and_outpost_buildable_anywhere(aoe2_rules):
    for name in (
        "outpost",
        "scouttower",
        "guardtower",
        "keeptower",
        "cannontower",
        "byzantine_scouttower",
        "byzantine_guardtower",
    ):
        cls = aoe2_rules.unit_class(name)
        assert getattr(cls, "is_buildable_anywhere", 0) == 1, name
    barracks = aoe2_rules.unit_class("barracks")
    assert getattr(barracks, "is_buildable_anywhere", 0) in (0, False)


def test_mangonel_line_de_melee_and_splash_pool(aoe2_rules):
    from soundrts.lib.nofloat import PRECISION

    for name, dmg in (("mangonel", 40), ("onager", 50), ("siege_onager", 75)):
        cls = aoe2_rules.unit_class(name)
        assert int(cls.mdg) == dmg * PRECISION, name
        assert int(cls.mdg_splash) == dmg * PRECISION, name


def test_aoe2_auto_scout_on_scout_and_eagle_not_mangudai(aoe2_rules):
    """DE update 111772: Auto Scout on scout/eagle lines, not Mangudai."""
    for name in (
        "scout_cavalry",
        "light_cavalry",
        "hussar",
        "eagle_scout",
        "aztec_eagle_scout",
        "eagle_warrior",
        "elite_eagle_warrior",
    ):
        cls = aoe2_rules.unit_class(name)
        assert getattr(cls, "can_auto_explore", 0), name
    for name in ("mangudai", "elite_mangudai", "camel_rider"):
        cls = aoe2_rules.unit_class(name)
        assert not getattr(cls, "can_auto_explore", 0), name


def test_archery_line_upgrades_live_on_range_not_stable(aoe2_rules):
    """Foot-archer / skirmisher / CA upgrades belong on the range, not the stable."""
    archery_techs = {
        "crossbowman",
        "arbalester",
        "elite_skirmisher",
        "imperial_skirmisher",
        "heavy_cavalry_archer",
        "thumb_ring",
        "parthian_tactics",
    }
    frank_archery = aoe2_rules.get("frank_archery", "can_research") or []
    frank_stable = aoe2_rules.get("frank_stable", "can_research") or []
    assert "crossbowman" in frank_archery
    assert "arbalester" in frank_archery
    assert "elite_skirmisher" in frank_archery
    assert "thumb_ring" not in frank_archery
    assert "heavy_cavalry_archer" not in frank_archery
    assert not archery_techs.intersection(frank_stable)
    assert "husbandry" in frank_stable
    assert "frankish_cavalier" in frank_stable
    assert "frankish_paladin" in frank_stable

    briton_archery = aoe2_rules.get("briton_archery", "can_research") or []
    briton_stable = aoe2_rules.get("briton_stable", "can_research") or []
    assert "crossbowman" in briton_archery
    assert "arbalester" in briton_archery
    assert "elite_skirmisher" in briton_archery
    assert "thumb_ring" not in briton_archery
    assert "heavy_cavalry_archer" not in briton_archery
    assert not archery_techs.intersection(briton_stable)
    assert "husbandry" in briton_stable
    assert "cavalier" in briton_stable
    assert "paladin" in briton_stable

    for name in aoe2_rules.classnames():
        research = set(aoe2_rules.get(name, "can_research") or [])
        if not research:
            continue
        is_a = aoe2_rules.get(name, "is_a") or []
        if name == "stables" or "stables" in is_a or name.endswith("_stable"):
            leaked = research & archery_techs
            assert not leaked, f"{name} has archery techs {leaked}"


def test_aoe2_blast_units_splash_pool_matches_attack(aoe2_rules):
    """Projectile blast / trample: splash pool equals main attack (not leftover flag 1)."""
    from soundrts.lib.nofloat import PRECISION

    melee = (
        ("bombard_cannon", 40),
        ("cannon_galleon", 50),
        ("elite_cannon_galleon", 60),
        ("dromon", 8),
        ("petard", 25),
        ("demolition_raft", 75),
        ("demolition_ship", 95),
        ("heavy_demolition_ship", 120),
        ("battle_elephant", 12),
        ("elite_battle_elephant", 14),
        ("war_elephant", 15),
        ("elite_war_elephant", 20),
        ("elite_armored_elephant", 4),
        ("capped_ram", 3),
        ("siege_ram", 4),
    )
    for name, dmg in melee:
        cls = aoe2_rules.unit_class(name)
        assert int(cls.mdg) == dmg * PRECISION, name
        assert int(cls.mdg_splash) == dmg * PRECISION, name

    pierce = (
        ("turtle_ship", 9),
        ("elite_turtle_ship", 13),
        ("cannontower", 120),
    )
    for name, dmg in pierce:
        cls = aoe2_rules.unit_class(name)
        assert int(cls.rdg) == dmg * PRECISION, name
        assert int(cls.rdg_splash) == dmg * PRECISION, name
