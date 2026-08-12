# -*- coding: utf-8 -*-
"""effect bonus hp vs hp_max: hp raises current+max; hp_max raises max only."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.lib.nofloat import PRECISION
from soundrts.worldupgrade.base import Upgrade


def test_effect_bonus_hp_raises_current_and_max():
    u = SimpleNamespace(hp=100 * PRECISION, hp_max=100 * PRECISION, type_name="scout")
    Upgrade.effect_bonus(u, 0, "hp", 20 * PRECISION)
    assert u.hp_max == 120 * PRECISION
    assert u.hp == 120 * PRECISION


def test_effect_bonus_hp_on_damaged_unit():
    u = SimpleNamespace(hp=40 * PRECISION, hp_max=100 * PRECISION, type_name="scout")
    Upgrade.effect_bonus(u, 0, "hp", 20 * PRECISION)
    assert u.hp_max == 120 * PRECISION
    assert u.hp == 60 * PRECISION


def test_effect_bonus_hp_max_does_not_heal_current():
    u = SimpleNamespace(hp=40 * PRECISION, hp_max=100 * PRECISION, type_name="scout")
    Upgrade.effect_bonus(u, 0, "hp_max", 20 * PRECISION)
    assert u.hp_max == 120 * PRECISION
    assert u.hp == 40 * PRECISION


def test_effect_bonus_hp_percent_grows_max_and_current_by_delta():
    u = SimpleNamespace(hp=50 * PRECISION, hp_max=100 * PRECISION, type_name="wall")
    Upgrade.effect_bonus(u, 0, "hp", "10%")
    assert u.hp_max == 110 * PRECISION
    assert u.hp == 60 * PRECISION


def test_aoe2_bloodlines_uses_hp_not_hp_max():
    from pathlib import Path

    text = Path("mods/aoe2/rules.txt").read_text(encoding="utf-8")
    block = text[text.find("def bloodlines") : text.find("def husbandry")]
    assert "effect bonus hp 20" in block
    assert "effect bonus hp_max 20" not in block
