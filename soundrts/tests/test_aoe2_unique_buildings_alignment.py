# -*- coding: utf-8 -*-
"""AoE2 DE: the 9 missing unique / regional building instances.

DE has 6 unique / regional building *types* that cover 9 civ slots::

    Krepost          Bulgarians          (Castle Age)
    Caravanserai     Persians + Hindustanis (Imperial Age)
    Folwark          Poles               (replaces the Mill)
    Mule Cart        Armenians + Georgians (replaces the Lumber/Mining Camp)
    Fortified Church Armenians + Georgians (replaces the Monastery)
    Settlement       Incas               (replaces the Mill/Lumber/Mining Camp)

Each civ gets its own *shell* (``polish_folwark``, ``armenian_mule_cart``, …)
so the race table can map a semantic slot to it.  The tests below pin:

* the base DE building definitions (costs, HP, garrison, techs, aura knobs),
* the per-civ shells and the race-block slot mappings,
* the ``is_a`` chain that makes the replacement satisfy the requirements of
  the building it replaces (``Player.has`` walks ``expanded_is_a``),
* the villager build menus,
* the Caravanserai aura engine wiring,
* and the ``armored_elephant`` upgrade line (base → elite).
"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules, style
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)


@pytest.fixture(scope="module")
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old_mods = res.mods or ""
    old_config_mods = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    res.load_style()
    yield rules, style
    config.mods = old_config_mods
    res.set_mods(old_mods)
    res.load_rules_and_ai()
    res.load_style()
    logging.disable(logging.NOTSET)


# ---------------------------------------------------------------------------
# helpers — the raw rules dict (the class objects expose ``can_train`` /
# ``can_research`` as properties and scale the numbers by PRECISION).
# ---------------------------------------------------------------------------


def _raw(name):
    d = rules._dict.get(name)
    assert d is not None, "unknown rules type: %s" % name
    return d


def _hp(name):
    """HP in whole HP (the rules store PRECISION-scaled values)."""
    return int(_raw(name)["hp_max"]) // PRECISION


def _can_train(name):
    return dict(_raw(name).get("_rules_can_train") or {})


def _can_build(name):
    return list(_raw(name).get("_rules_can_build") or ())


def _can_research(name):
    return list(_raw(name).get("can_research") or ())


def _expanded(name):
    d = _raw(name)
    out = set(d.get("expanded_is_a") or ())
    out.update(d.get("is_a") or ())
    out.add(name)
    return out


def _attr(name, attr, default=None):
    return getattr(rules.unit_class(name), attr, default)


# ---------------------------------------------------------------------------
# 1. The 6 base DE building definitions
# ---------------------------------------------------------------------------


def test_krepost_is_the_bulgarian_castle_age_fortification(aoe2_loaded):
    """DE: 2600 HP, 20 pop, garrison 20, trains the Konnik line."""
    assert _raw("krepost")["requirements"] == ["castle_age"]
    assert _hp("krepost") == 2600
    assert _raw("krepost")["population_provided"] == 20
    assert _raw("krepost")["transport_capacity"] == 20
    assert _raw("krepost")["conversion_immune"] == 1
    # DE: the Krepost shoots arrows like the Castle (10 pierce, range 7).
    assert _raw("krepost")["rdg"] == 10 * PRECISION
    assert _raw("krepost")["rdg_range"] == 7 * PRECISION
    # DE: the Krepost trains the Bulgarian unique unit and the Petard.
    assert {"konnik", "elite_konnik", "petard"} <= set(_can_train("krepost"))
    # DE: Stirrups / Bagains are researched at the CASTLE, not at the Krepost.
    researched = set(_can_research("krepost"))
    assert "stirrups" not in researched
    assert "bagains" not in researched
    assert {"stirrups", "bagains"} <= set(_can_research("bulgarian_castle"))


def test_caravanserai_has_the_de_aura_knobs(aoe2_loaded):
    """DE: heals and speeds up the Trade Carts in an 8-tile radius."""
    assert _raw("caravanserai")["requirements"] == ["imperial_age"]
    assert _hp("caravanserai") == 2700
    assert _attr("caravanserai", "aura_radius") == 8
    assert _attr("caravanserai", "aura_heal_level") == 1
    assert _attr("caravanserai", "aura_heal_cd") == 5
    assert _attr("caravanserai", "aura_speed_bonus_pct") == 20
    assert list(_attr("caravanserai", "aura_target_types", ()) or ()) == ["trade_cart"]


def test_folwark_is_the_poles_mill_replacement(aoe2_loaded):
    """DE: 1000 HP, 5 pop, stores food, researches the farming techs."""
    assert _hp("folwark") == 1000
    assert _raw("folwark")["population_provided"] == 5
    assert "mill" in _expanded("folwark")
    assert list(_raw("folwark")["storable_resource_types"]) == ["resource3"]
    researched = set(_can_research("folwark"))
    assert {"horse_collar", "heavy_plow", "crop_rotation"} <= researched


def test_mule_cart_replaces_the_lumber_and_mining_camps(aoe2_loaded):
    """DE: 300 HP, stores every resource, hosts the 7 eco technologies."""
    assert _hp("mule_cart") == 300
    assert "lumbermill" in _expanded("mule_cart")
    assert "mining_camp" in _expanded("mule_cart")
    stored = set(_raw("mule_cart")["storable_resource_types"])
    assert stored == {"resource1", "resource2", "resource3", "resource4"}
    researched = set(_can_research("mule_cart"))
    assert {
        "double_bit_axe",
        "bow_saw",
        "two_man_saw",
        "gold_mining",
        "gold_shaft_mining",
        "stone_mining",
        "stone_shaft_mining",
    } <= researched


def test_fortified_church_replaces_the_monastery(aoe2_loaded):
    """DE: 2400 HP, garrison 10 (relic gold), arrow attack, trains the Monk."""
    assert "monastery" in _expanded("fortified_church")
    assert _hp("fortified_church") == 2400
    assert _raw("fortified_church")["transport_capacity"] == 10
    assert _raw("fortified_church")["rdg"] == 5 * PRECISION
    assert _raw("fortified_church")["rdg_range"] == 4 * PRECISION
    assert "monk" in set(_can_train("fortified_church"))
    # DE: the Fortified Church keeps the relic-inventory (gold) behaviour.
    assert _raw("fortified_church")["inventory_capacity"] == 10


def test_settlement_replaces_the_mill_lumber_and_mining_camps(aoe2_loaded):
    """DE: 1000 HP, 5 pop, stores everything, hosts the 10 eco technologies."""
    assert _hp("settlement") == 1000
    assert _raw("settlement")["population_provided"] == 5
    for parent in ("mill", "lumbermill", "mining_camp"):
        assert parent in _expanded("settlement"), parent
    stored = set(_raw("settlement")["storable_resource_types"])
    assert stored == {"resource1", "resource2", "resource3", "resource4"}
    researched = set(_can_research("settlement"))
    assert {
        "horse_collar",
        "heavy_plow",
        "crop_rotation",
        "double_bit_axe",
        "bow_saw",
        "two_man_saw",
        "gold_mining",
        "gold_shaft_mining",
        "stone_mining",
        "stone_shaft_mining",
    } <= researched


# ---------------------------------------------------------------------------
# 2. The per-civ shells and the race-block slot mappings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "civ,slot,shell",
    [
        ("poles", "mill", "polish_folwark"),
        ("armenians", "lumbermill", "armenian_mule_cart"),
        ("armenians", "mining_camp", "armenian_mule_cart"),
        ("armenians", "monastery", "armenian_fortified_church"),
        ("georgians", "lumbermill", "georgian_mule_cart"),
        ("georgians", "mining_camp", "georgian_mule_cart"),
        ("georgians", "monastery", "georgian_fortified_church"),
        ("incas", "mill", "incan_settlement"),
        ("incas", "lumbermill", "incan_settlement"),
        ("incas", "mining_camp", "incan_settlement"),
        ("persians", "caravanserai", "persian_caravanserai"),
        ("hindustanis", "caravanserai", "hindustani_caravanserai"),
    ],
)
def test_race_block_maps_the_slot_to_the_civ_shell(aoe2_loaded, civ, slot, shell):
    assert rules.get(civ, slot)[0] == shell


@pytest.mark.parametrize(
    "shell,base",
    [
        ("polish_folwark", "folwark"),
        ("armenian_mule_cart", "mule_cart"),
        ("georgian_mule_cart", "mule_cart"),
        ("armenian_fortified_church", "fortified_church"),
        ("georgian_fortified_church", "fortified_church"),
        ("incan_settlement", "settlement"),
        ("persian_caravanserai", "caravanserai"),
        ("hindustani_caravanserai", "caravanserai"),
    ],
)
def test_civ_shell_inherits_its_base_building(aoe2_loaded, shell, base):
    assert base in _expanded(shell)


@pytest.mark.parametrize(
    "shell,title_id",
    [
        ("polish_folwark", 9118),
        ("armenian_mule_cart", 9119),
        ("georgian_mule_cart", 9119),
        ("armenian_fortified_church", 9120),
        ("georgian_fortified_church", 9120),
        ("incan_settlement", 9121),
        ("persian_caravanserai", 9117),
        ("hindustani_caravanserai", 9117),
    ],
)
def test_civ_shell_has_a_spoken_title_and_hotkey(aoe2_loaded, shell, title_id):
    """Every shell must be speakable and reachable (see the shell-title test)."""
    _rules, style = aoe2_loaded
    assert list(style.get(shell, "title", warn_if_not_found=False) or []) == [
        str(title_id)
    ]
    assert style.get(shell, "keyboard", warn_if_not_found=False)


def test_base_unique_buildings_have_a_spoken_title_and_hotkey(aoe2_loaded):
    _rules, style = aoe2_loaded
    for base in (
        "krepost",
        "caravanserai",
        "folwark",
        "mule_cart",
        "fortified_church",
        "settlement",
    ):
        assert style.get(base, "title", warn_if_not_found=False), base
        assert style.get(base, "keyboard", warn_if_not_found=False), base


# ---------------------------------------------------------------------------
# 3. Villager build menus
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "civ,villager,unique",
    [
        ("bulgarians", "bulgarian_villager", "krepost"),
        ("poles", "polish_villager", "polish_folwark"),
        ("armenians", "armenian_villager", "armenian_mule_cart"),
        ("armenians", "armenian_villager", "armenian_fortified_church"),
        ("georgians", "georgian_villager", "georgian_mule_cart"),
        ("georgians", "georgian_villager", "georgian_fortified_church"),
        ("incas", "incan_villager", "incan_settlement"),
        ("persians", "persian_villager", "caravanserai"),
        ("hindustanis", "hindustani_villager", "caravanserai"),
    ],
)
def test_villager_can_build_the_unique_building(aoe2_loaded, civ, villager, unique):
    assert unique in _can_build(villager), "%s cannot build %s" % (civ, unique)


@pytest.mark.parametrize(
    "villager,forbidden",
    [
        # The Folwark replaces the Mill for the Poles.
        ("polish_villager", "mill"),
        # The Mule Cart replaces the Lumber Camp / Mining Camp.
        ("armenian_villager", "lumbermill"),
        ("armenian_villager", "mining_camp"),
        ("georgian_villager", "lumbermill"),
        ("georgian_villager", "mining_camp"),
        # The Settlement replaces the Mill / Lumber Camp / Mining Camp.
        ("incan_villager", "mill"),
        ("incan_villager", "lumbermill"),
        ("incan_villager", "mining_camp"),
    ],
)
def test_replaced_buildings_are_not_on_the_villager_menu(aoe2_loaded, villager, forbidden):
    assert forbidden not in _can_build(villager)


@pytest.mark.parametrize("villager", ["armenian_villager", "georgian_villager"])
def test_armenians_and_georgians_keep_the_mill_but_not_the_monastery(
    aoe2_loaded, villager
):
    """DE: they keep a Mill; the Fortified Church replaces the Monastery."""
    menu = _can_build(villager)
    assert "mill" in menu
    assert "monastery" not in menu


def test_incas_keep_the_monastery(aoe2_loaded):
    """DE: the Incas keep a Monastery; only the economy buildings are replaced."""
    assert "monastery" in _can_build("incan_villager")


# ---------------------------------------------------------------------------
# 4. The Caravanserai aura engine
# ---------------------------------------------------------------------------


def test_aura_engine_module_is_data_driven():
    """The engine must not hardcode a building name."""
    from soundrts import world_aura

    source = (ROOT / "soundrts" / "world_aura.py").read_text(encoding="utf-8")
    # The building name may appear in the docstring, but never in the code:
    # strip the module docstring before checking.
    body = source.split('"""', 2)[-1]
    assert "caravanserai" not in body.lower()
    assert hasattr(world_aura, "apply_speed_aura")
    assert hasattr(world_aura, "apply_building_aura")
    assert hasattr(world_aura, "aura_radius_mm")


def test_aura_is_hooked_into_the_movement_and_status_update():
    """The speed aura must be applied where the speed is computed."""
    movement = (ROOT / "soundrts/worldunit/world_movement.py").read_text(encoding="utf-8")
    resources = (ROOT / "soundrts/worldplayerbase/resources.py").read_text(encoding="utf-8")
    status = (ROOT / "soundrts/worldunit/world_status_update.py").read_text(encoding="utf-8")
    assert "apply_speed_aura" in movement
    assert "apply_speed_aura" in resources
    assert "apply_building_aura" in status


def test_aura_radius_is_expressed_in_tiles():
    from soundrts import world_aura

    class _Building:
        aura_radius = 8
        world = None

    # 8 tiles * 12 engine units per tile * PRECISION.
    expected = 8 * world_aura.DEFAULT_TILE_UNITS * PRECISION
    assert world_aura.aura_radius_mm(_Building()) == expected


def test_aura_speed_bonus_is_a_noop_without_an_aura_building():
    from soundrts import world_aura

    class _Unit:
        _actual_speed = 100
        world = None

    unit = _Unit()
    assert world_aura.apply_speed_aura(unit) == 0
    assert unit._actual_speed == 100


# ---------------------------------------------------------------------------
# 5. The armored_elephant upgrade line
# ---------------------------------------------------------------------------


def test_armored_elephant_line_is_wired(aoe2_loaded):
    """The base unit must point at the elite form, which must be a line upgrade."""
    base = _raw("armored_elephant")
    elite = _raw("elite_armored_elephant")
    assert "elite_armored_elephant" in set(base["can_upgrade_to"])
    # The base unit must NOT be marked as a researched-only form.
    assert int(base.get("no_auto_upgrade", 0) or 0) == 0
    # The elite form is unlocked by research (workshop), not automatically.
    assert int(elite.get("line_upgrade", 0) or 0) == 1
    assert int(elite.get("no_auto_upgrade", 0) or 0) == 1


def test_armored_elephant_line_is_siege_workshop_tech(aoe2_loaded):
    """DE: the Hindustani Armored Elephant line lives in the Siege Workshop."""
    assert "armored_elephant" in set(_can_train("hindustani_workshop"))
    assert "elite_armored_elephant" in set(_can_research("hindustani_workshop"))


def test_line_upgrade_resolves_the_elite_form_once_researched(aoe2_loaded):
    """``resolve_trainable_unit_type`` must pick the elite form after research."""
    from soundrts.world_build_rules import resolve_trainable_unit_type

    class _Player:
        faction = "hindustanis"
        upgrades = ["elite_armored_elephant", "imperial_age"]

        def has_all(self, tokens):
            return True

    assert (
        resolve_trainable_unit_type(_Player(), "armored_elephant")
        == "elite_armored_elephant"
    )
