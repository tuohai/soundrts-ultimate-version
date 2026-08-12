"""Mod can clear res demo ``phase bonus`` with bare ``phase bonus``."""
from __future__ import annotations

from soundrts.definitions import Rules


def test_bare_phase_bonus_clears_merged_res_style_bonus():
    r = Rules()
    r.load(
        """
def feudal_age
class phase
cost 10 15
phase_targets -building
phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
units_auto_upgrade 0

def feudal_age
class phase
cost 0 0 500 0
time_cost 130
phase bonus
phase_targets
units_auto_upgrade 0
""",
    )
    assert r.get("feudal_age", "phase_bonus") == []
    assert r.get("feudal_age", "phase_bonus_targets") == []
    assert r.get("feudal_age", "phase_targets") == []


def test_phase_bonus_clear_keyword():
    r = Rules()
    r.load(
        """
def castle_age
class phase
phase bonus mdg 2 rdg 2
phase bonus clear
""",
    )
    assert r.get("castle_age", "phase_bonus") == []
