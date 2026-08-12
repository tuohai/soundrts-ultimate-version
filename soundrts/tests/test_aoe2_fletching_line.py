# -*- coding: utf-8 -*-
"""Fletching / Bodkin / Bracer must match AoE2 DE (incl. TC LOS, no TC range)."""
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


@pytest.mark.parametrize("tech", ("fletching", "bodkin_arrow", "bracer"))
def test_fletching_line_has_sight_and_tc_exception(aoe2_rules, tech):
    eff = aoe2_rules.get(tech, "effect")
    flat = []
    for item in eff:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    s = " ".join(str(x) for x in flat)
    assert "sight_range" in s
    assert "town_center" in s
    # TC block must not get range; arrow units do
    assert "rdg_range" in s
    # Parse groups: any bonus that includes town_center must not be rdg_range
    groups = eff if isinstance(eff[0], list) else [eff]
    for g in groups:
        if "town_center" in g or "townhall" in g:
            assert "rdg_range" not in g
            assert "rdg" in g or "sight_range" in g


@pytest.mark.parametrize(
    "unit",
    (
        "aoe_archer",
        "scouttower",
        "aoe_castle",
        "galley",
        "war_galley",
        "galleon",
        "town_center",
        "townhall",
    ),
)
def test_fletching_beneficiaries_can_use_tech(aoe2_rules, unit):
    techs = aoe2_rules.get(unit, "can_use_tech") or []
    for t in ("fletching", "bodkin_arrow", "bracer"):
        assert t in techs, (unit, t, techs)


def test_town_center_has_base_arrow_stats(aoe2_rules):
    assert aoe2_rules.get("town_center", "rdg")
    assert aoe2_rules.get("town_center", "rdg_range")
    assert aoe2_rules.get("town_center", "sight_range")
