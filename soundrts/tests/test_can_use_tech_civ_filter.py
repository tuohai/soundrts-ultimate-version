# -*- coding: utf-8 -*-
"""Attribute can_use_tech list is filtered to civ-researchable techs."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_loaded():
    from soundrts.definitions import rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    rules.load(base, mod)
    return rules


def _player(faction, upgrades=(), forbidden=()):
    return SimpleNamespace(
        faction=faction,
        upgrades=list(upgrades),
        forbidden_techs=list(forbidden),
        allied_victory=None,
    )


def test_briton_scorpion_hides_foreign_unique_techs(aoe2_loaded):
    from soundrts.attributes.utils import filter_can_use_tech_names

    raw = list(aoe2_loaded.get("scorpion", "can_use_tech") or [])
    assert "rocketry" in raw
    assert "siege_engineers" in raw

    shown = filter_can_use_tech_names(raw, _player("britons"))
    assert "siege_engineers" in shown
    assert "rocketry" not in shown
    assert "drill" not in shown
    assert "ironclad" not in shown
    assert "furor_celtica" not in shown


def test_chinese_scorpion_shows_rocketry(aoe2_loaded):
    from soundrts.attributes.utils import filter_can_use_tech_names

    raw = list(aoe2_loaded.get("scorpion", "can_use_tech") or [])
    shown = filter_can_use_tech_names(raw, _player("chinese"))
    assert "rocketry" in shown
    assert "drill" not in shown
    assert "furor_celtica" not in shown


def test_already_researched_foreign_tech_still_listed(aoe2_loaded):
    from soundrts.attributes.utils import filter_can_use_tech_names

    raw = ["rocketry", "siege_engineers"]
    shown = filter_can_use_tech_names(
        raw, _player("britons", upgrades=("rocketry",))
    )
    assert "rocketry" in shown
    assert "siege_engineers" in shown


def test_ui_attrs_match_filtered_list(aoe2_loaded):
    from soundrts.attributes.equipment_abilities import EquipmentAbilities
    from soundrts.attributes.utils import filter_can_use_tech_names

    unit = SimpleNamespace(
        can_use_tech=list(aoe2_loaded.get("scorpion", "can_use_tech") or []),
        player=_player("britons"),
        can_use_skill=(),
    )
    attrs = []
    EquipmentAbilities(None).add_tech_skill_attributes(unit, attrs)
    filtered = filter_can_use_tech_names(unit.can_use_tech, unit.player)
    for _prefix, _label, value in attrs:
        if isinstance(value, tuple) and value[0] == "CAN_USE_TECH_ITEMS":
            assert len(value[1]) == len(filtered)
            return
    assert not filtered
