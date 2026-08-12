"""Paired phase_bonus/phase_bonus_targets groups and effect_bonus_targets."""
from __future__ import annotations

from soundrts.definitions import Rules
from soundrts.worldupgrade import Upgrade
from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args


def test_phase_bonus_groups_pair_with_targets():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def castle_age
class phase
phase bonus mdg 1 mdf 2
phase_bonus_targets footman knight
phase bonus rdg 2 rdf 2
phase_bonus_targets archer
"""
    )
    groups = r.get("castle_age", "phase_bonus_groups")
    assert len(groups) == 2
    assert groups[0][1] == ["footman", "knight"]
    assert "mdg" in groups[0][0]
    assert groups[1][1] == ["archer"]
    assert "rdg" in groups[1][0]
    # flat compat fields still present
    assert "mdg" in r.get("castle_age", "phase_bonus")
    assert "rdg" in r.get("castle_age", "phase_bonus")
    assert r.get("castle_age", "phase_bonus_targets") == ["archer"]
    assert r.get("castle_age", "phase_targets") == ["archer"]


def test_legacy_phase_targets_then_bonus():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def feudal_age
class phase
phase_targets -building
phase bonus mdg 1 hp_max 5 cost -2 0
"""
    )
    groups = r.get("feudal_age", "phase_bonus_groups")
    assert len(groups) == 1
    assert groups[0][1] == ["-building"]
    assert r.get("feudal_age", "phase_bonus_targets") == ["-building"]
    assert r.get("feudal_age", "phase_targets") == ["-building"]


def test_effect_bonus_targets_pairs_with_effect_bonus():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def siege_engineers
class upgrade
effect bonus mdg_range 1
effect_bonus_targets mangonel onager
effect bonus rdg_range 1
effect_bonus_targets scorpion trebuchet
"""
    )
    eff = r._dict["siege_engineers"]["effect"]
    assert isinstance(eff[0], list)
    b0, u0 = split_effect_bonus_args(eff[0][1:])
    b1, u1 = split_effect_bonus_args(eff[1][1:])
    assert u0 == ["mangonel", "onager"]
    assert u1 == ["scorpion", "trebuchet"]
    assert "mdg_range" in b0
    assert "rdg_range" in b1


def test_tech_effect_targets_alias_still_works():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4
def bracer
class upgrade
effect bonus rdg 1
tech_effect_targets aoe_archer
"""
    )
    _, units = split_effect_bonus_args(r._dict["bracer"]["effect"][1:])
    assert units == ["aoe_archer"]


def test_effect_bonus_targets_applied_via_filter():
    class U:
        def __init__(self, type_name, expanded_is_a=()):
            self.type_name = type_name
            self.expanded_is_a = expanded_is_a
            self.cls = type("soldier", (), {})
            self.mdg_range = 4000

    mang = U("mangonel", ("siege_unit",))
    scor = U("scorpion", ("siege_unit",))
    Upgrade.effect_bonus(mang, 0, "mdg_range", 1000, "mangonel")
    Upgrade.effect_bonus(scor, 0, "mdg_range", 1000, "mangonel")
    assert mang.mdg_range == 5000
    assert scor.mdg_range == 4000


def test_effect_bonus_cost_keeps_multi_resource_values():
    """``effect bonus cost -50% 0`` must not treat ``0`` as a unit filter."""
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2
def dsc
class upgrade
effect bonus cost -50% 0
effect bonus time_cost -5
"""
    )
    eff = r._dict["dsc"]["effect"]
    # may be nested list of groups or a flat bonus list
    if isinstance(eff[0], list):
        cost_group = eff[0]
    else:
        cost_group = eff
    assert cost_group[0] == "bonus"
    bonus, stray = split_effect_bonus_args(cost_group[1:])
    assert stray == []
    assert bonus[:3] == ["cost", "-50%", "0"]
