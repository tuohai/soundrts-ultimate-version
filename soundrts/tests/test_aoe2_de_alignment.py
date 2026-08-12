# -*- coding: utf-8 -*-
"""AoE2 DE tech alignment smoke tests."""
from __future__ import annotations

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
    assert "heavy_plow" in (aoe2_rules.get("peasant", "can_use_tech") or [])


def test_chinese_tc_bonus(aoe2_rules):
    assert aoe2_rules.get("chinese", "townhall") == ["chinese_town_center"]
    assert aoe2_rules.get("chinese_town_center", "population_provided")


def test_franks_cavalry_hp_phase(aoe2_rules):
    # on_phase stored in rules dict
    raw = aoe2_rules._dict.get("franks", {})
    assert any("hp_max" in str(v) and "cavalry" in str(v) for v in raw.values()) or "cavalry" in str(
        raw
    )
