"""aoe2 phase: building age tables + race on_phase civ bonuses (no units_auto_upgrade)."""
from __future__ import annotations

from soundrts.definitions import Rules
from soundrts.worldphase import Phase, apply_faction_on_phase_effects, is_a_phase


def test_rules_parse_on_phase_effects():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4

def britons
class race
on_phase castle_age rdg_range 1 aoe_archer longbowman
on_phase imperial_age rdg_range 1 aoe_archer longbowman
"""
    )
    effects = r._dict["britons"]["on_phase_effects"]
    assert len(effects) == 2
    assert effects[0][0] == "castle_age"
    assert "rdg_range" in effects[0]
    assert "longbowman" in effects[0]


def _units_auto_upgrade(d) -> int:
    raw = d.get("units_auto_upgrade", 0)
    if isinstance(raw, list):
        raw = raw[0] if raw else 0
    return int(raw or 0)


def test_aoe2_ages_without_res_combat_bonus():
    from pathlib import Path

    if not Path("mods/aoe2/rules.txt").is_file():
        return
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    saved = sys.argv
    sys.argv = [saved[0] if saved else "pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts import config
        from soundrts.lib.resource import res

        config.mods = "aoe2"
        res.set_mods("aoe2")
        res.load_rules_and_ai()
        from soundrts.definitions import rules

    sys.argv = saved
    # AoE2 uses researched line_upgrade, not age-tied units_auto_upgrade
    assert _units_auto_upgrade(rules._dict["dark_age"]) == 0
    for age in ("feudal_age", "castle_age", "imperial_age"):
        d = rules._dict[age]
        # Building HP/armor age tables — must clear res demo combat buffs first
        pb = d.get("phase_bonus") or []
        assert "mdg" not in pb and "rdg" not in pb
        assert "cost" not in pb
        assert "hp" in pb or "hp_max" in pb or "mdf" in pb
        groups = d.get("phase_bonus_groups") or []
        assert len(groups) >= 1
        # No group should carry res demo mdg/rdg
        for args, _tgts in groups:
            assert "mdg" not in args and "rdg" not in args
        assert _units_auto_upgrade(d) == 0
        assert is_a_phase(rules.unit_class(age))
    assert rules._dict["champion"].get("no_auto_upgrade") in ([1], 1, ["1"])
    brit = rules._dict["britons"].get("on_phase_effects") or []
    assert any(e and e[0] == "castle_age" for e in brit)
    # Dark-age bases for buildings that age-scale (precision-scaled in rules dict)
    def _stat(typename, key):
        raw = rules._dict[typename][key]
        if isinstance(raw, (list, tuple)):
            raw = raw[0]
        return int(raw)

    from soundrts.lib.nofloat import PRECISION

    assert _stat("mill", "hp_max") == 600 * PRECISION
    assert _stat("house", "hp_max") == 550 * PRECISION
    assert _stat("house", "mdf") == -2 * PRECISION
    assert _stat("barracks", "hp_max") == 1200 * PRECISION
    assert _stat("town_center", "mdf") == 3 * PRECISION
    byz = rules._dict["byzantines"].get("on_phase_effects") or []
    assert any(e and e[0] == "dark_age" and "hp" in e for e in byz)


def test_effect_bonus_hp_max_percent_stays_numeric():
    """Byzantine-style ``hp_max 10%`` must multiply, never store the string."""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldupgrade import Upgrade

    u = type("u", (), {})()
    u.type_name = "house"
    u.expanded_is_a = set()
    base = 550 * PRECISION
    u.hp_max = base
    u.hp = base
    Upgrade.effect_bonus(u, 0, "hp_max", "10%")
    assert isinstance(u.hp_max, int)
    assert isinstance(u.hp, int)
    assert u.hp_max == int(base * 1.1)
    # hp_max only raises the ceiling; current HP is unchanged.
    assert u.hp == base


def test_effect_bonus_hp_percent_also_raises_current():
    """``effect bonus hp 10%`` grows max and current by the same absolute delta."""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldupgrade import Upgrade

    u = type("u", (), {})()
    u.type_name = "house"
    u.expanded_is_a = set()
    base = 550 * PRECISION
    u.hp_max = base
    u.hp = base
    Upgrade.effect_bonus(u, 0, "hp", "10%")
    assert u.hp_max == int(base * 1.1)
    assert u.hp == int(base * 1.1)


def test_phase_bonus_hp_raises_current_on_age():
    """Age ``phase bonus hp N`` must raise current HP, not only hp_max."""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldupgrade import Upgrade

    u = type("u", (), {})()
    u.type_name = "house"
    u.expanded_is_a = set()
    base = 550 * PRECISION
    u.hp_max = base
    u.hp = base // 2
    Upgrade.effect_bonus(u, 0, "hp", 150 * PRECISION)
    assert u.hp_max == base + 150 * PRECISION
    assert u.hp == base // 2 + 150 * PRECISION


def test_bridge_terrain_providers_tolerates_string_hp():
    from soundrts.world_build_rules import _bridge_terrain_providers

    class Obj:
        hp = "10%"
        type_name = "house"

    assert list(_bridge_terrain_providers([Obj()])) == []


def test_apply_faction_on_phase_increases_range():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 4

def castle_age
class phase
cost 0 0 0 0

def britons
class race
on_phase castle_age rdg_range 1 longbowman

def longbowman
class soldier
rdg_range 5
"""
    )
    from soundrts.definitions import rules as global_rules

    saved_dict = global_rules._dict
    saved_classes = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    try:
        class U:
            type_name = "longbowman"
            expanded_is_a = set()
            rdg_range = 5 * 1000  # PRECISION-ish; effect_bonus may add to_int

        u = U()
        # Use class from rules for PRECISION attribute
        lb = r.unit_class("longbowman")
        u2 = type("u", (), {})()
        u2.type_name = "longbowman"
        u2.expanded_is_a = set()
        u2.rdg_range = getattr(lb, "rdg_range", 5000)

        class P:
            faction = "britons"
            units = [u2]
            _phase_bonus_pool = []

        apply_faction_on_phase_effects(P(), "castle_age")
        assert u2.rdg_range > getattr(lb, "rdg_range", 5000)
    finally:
        global_rules._dict = saved_dict
        if saved_classes is not None:
            global_rules.classes = saved_classes
