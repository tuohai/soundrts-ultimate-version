# -*- coding: utf-8 -*-
"""``conscription`` must reach exactly the units DE's Conscription reaches.

DE's Conscription reads (aoe2db)::

    Military buildings (except Siege Workshops) work +33% faster.

so it speeds up every unit trained at the **Barracks, Archery Range,
Stable, Castle, Krepost and Donjon**, and nothing else.  In particular it
does *not* reach:

* **Dock** units -- the Caravel, the Turtle Ship, the Dragon Ship, the
  Dromon, the Longboat;
* **Siege Workshop** units -- the Houfnice, the Flaming Camel, the
  Armored Elephant;
* **Monastery / Fortified Church** units -- the Missionary, the Warrior
  Priest.

It *does* reach the Castle-trained siege units -- the Trebuchet and the
Petard -- even though they are plain siege weapons with no unique-unit
marker.

The mod models the bonus as a filtered ``time_cost`` row on the tech
(``effect bonus time_cost -33%`` + ``effect_bonus_targets …``), and the
engine matches that row against **unit types**, not against buildings.
The target list therefore has to spell out DE's scope by hand.

This module pins that list to DE's own tech-tree data: every unit node in
``_de_trees/*.json`` records the DE building that trains it, and that
building decides whether the unit is in scope.

Reference data (checked into the repository):

* ``_de_trees/*.json`` -- the 42 per-civilisation DE tech trees.  Each
  unit node carries ``node_type`` and ``building_id``; the building id
  resolves to the building's DE display name.

The mod's *own* wiring (which building lists a unit in ``can_train``) is
used as a second, independent signal in
:func:`test_mod_wiring_agrees_with_de_trees`, so a future re-wiring of
the mod cannot silently disagree with DE again.
"""
from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DE_TREES = ROOT / "_de_trees"

# DE buildings whose work rate Conscription speeds up.
DE_AFFECTED_BUILDINGS = {
    "Barracks",
    "Archery Range",
    "Stable",
    "Castle",
    "Krepost",
    "Donjon",
}

# Units the mod currently wires to a different building than DE does.
#
# ``armored_elephant``: DE trains it at the **Siege Workshop** (the
# Hindustani ram-line replacement).  The mod now wires it there too, so
# this set is empty -- it stays in place as a regression hook: if a
# future change moves the unit back to the Castle, the wiring test fails
# instead of silently widening Conscription's scope.
KNOWN_MOD_WIRING_DIVERGENCE: set[str] = set()

# The DE buildings Conscription explicitly leaves alone.
DE_EXCLUDED_BUILDINGS = {
    "Dock",
    "Siege Workshop",
    "Monastery",
    "Fortified Church",
}

# DE display names whose mechanical counterpart carries a different id in
# the mod (the Viking *Longship* is the mod's ``longboat``).
_DE_NAME_TO_MOD_ID = {
    "longship": "longboat",
    "elite longship": "elite_longboat",
}

# DE names that the mod spells with an AoE2-specific id.
#
# ``Archer`` and ``Knight`` are DE's *generic* Archery Range / Stable
# units, and the mod calls them ``aoe_archer`` / ``aoe_knight`` (the
# plain names ``archer`` / ``knight`` belong to the vanilla base game
# and are not part of the AoE2 mod at all).
_DE_NAME_OVERRIDES = {
    "trebuchet (packed)": "trebuchet",
    "elite trebuchet": "trebuchet",
    "archer": "aoe_archer",
    "knight": "aoe_knight",
}


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    return r


def _mod_id(de_name: str) -> str:
    """The ``rules.txt`` id of a DE display name."""
    key = de_name.lower()
    if key in _DE_NAME_OVERRIDES:
        return _DE_NAME_OVERRIDES[key]
    alias = _DE_NAME_TO_MOD_ID.get(key)
    if alias is not None:
        return alias
    return re.sub(r"[^a-z0-9]+", "_", key).strip("_")


@pytest.fixture(scope="module")
def de_trained_at():
    """Mod unit id -> the set of DE buildings that train it.

    Only units the mod actually implements are included, so the mapping
    can be compared with the mod's own unit list directly.
    """
    out: dict[str, set[str]] = defaultdict(set)
    for path in sorted(glob.glob(str(DE_TREES / "*.json"))):
        tree = json.loads(Path(path).read_text(encoding="utf-8"))
        buildings = {
            b["building_id"]: b["name"]
            for b in (tree.get("buildings") or ())
        }
        for node in tree.get("units_techs") or ():
            if node.get("node_type") not in (
                "Unit",
                "UniqueUnit",
                "RegionalUnit",
            ):
                continue
            building = buildings.get(node.get("building_id"))
            if building is None:
                continue
            out[_mod_id(node["name"])].add(building)
    return dict(out)


@pytest.fixture(scope="module")
def conscription_targets(aoe2_rules):
    """The target list of the Conscription tech's filtered ``time_cost`` row."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(aoe2_rules.unit_class("conscription")))
    assert rows, "conscription declares no targeted effect row"
    return list(rows[0][1])


def _matches(aoe2_rules, type_name, targets):
    """The engine's own target matcher."""
    from soundrts.worldphase import Phase
    from soundrts.world_civ_bonuses import _type_proxy

    cls = aoe2_rules.unit_class(type_name)
    if cls is None:
        return False
    return Phase._unit_matches_targets(_type_proxy(cls), targets)


def _mod_units(aoe2_rules):
    """Every soldier class the mod defines (the AoE2 mod's own units)."""
    out = []
    for name in aoe2_rules.classnames():
        cls = aoe2_rules.unit_class(name)
        if cls is None:
            continue
        base = getattr(getattr(cls, "cls", None), "__name__", "") or ""
        if base.lower() != "soldier":
            continue
        out.append(name)
    return sorted(out)


# ---------------------------------------------------------------------------
# 1. The scope matches DE exactly
# ---------------------------------------------------------------------------


def test_conscription_reaches_every_de_in_scope_unit(
    aoe2_rules, de_trained_at, conscription_targets
):
    """Every DE unit trained at an affected building must be reached."""
    missed = []
    for unit, buildings in sorted(de_trained_at.items()):
        if not (buildings & DE_AFFECTED_BUILDINGS):
            continue
        if aoe2_rules.unit_class(unit) is None:
            continue
        if not _matches(aoe2_rules, unit, conscription_targets):
            missed.append((unit, sorted(buildings)))
    assert not missed, (
        "DE units trained at an affected building but not reached by "
        "Conscription: %s" % missed
    )


def test_conscription_reaches_no_de_out_of_scope_unit(
    aoe2_rules, de_trained_at, conscription_targets
):
    """No unit trained at an excluded building may be reached."""
    wrongly = []
    for unit, buildings in sorted(de_trained_at.items()):
        if buildings & DE_AFFECTED_BUILDINGS:
            continue
        if not (buildings & DE_EXCLUDED_BUILDINGS):
            continue
        if aoe2_rules.unit_class(unit) is None:
            continue
        if _matches(aoe2_rules, unit, conscription_targets):
            wrongly.append((unit, sorted(buildings)))
    assert not wrongly, (
        "DE units trained at an excluded building but reached by "
        "Conscription: %s" % wrongly
    )


def test_the_excluded_buildings_really_are_excluded(
    aoe2_rules, de_trained_at, conscription_targets
):
    """The concrete regression cases, named explicitly.

    Each of these was wrongly reached by the old target list
    (``infantry archer_unit cavalry unique_unit``) because it is a civ
    unique unit or carries the ``cavalry`` root.
    """
    expected_excluded = {
        # Dock
        "caravel": "Dock",
        "elite_caravel": "Dock",
        "turtle_ship": "Dock",
        "elite_turtle_ship": "Dock",
        "dragon_ship": "Dock",
        "dromon": "Dock",
        "longboat": "Dock",
        # Siege Workshop
        "houfnice": "Siege Workshop",
        "flaming_camel": "Siege Workshop",
        "armored_elephant": "Siege Workshop",
        "elite_armored_elephant": "Siege Workshop",
        # Monastery / Fortified Church
        "missionary": "Monastery",
        "warrior_priest": "Fortified Church",
        "monk": "Monastery",
    }
    offenders = []
    for unit, building in sorted(expected_excluded.items()):
        if aoe2_rules.unit_class(unit) is None:
            continue
        if _matches(aoe2_rules, unit, conscription_targets):
            offenders.append((unit, building))
    assert not offenders, (
        "units DE trains at an excluded building but Conscription reaches: %s"
        % offenders
    )


def test_the_castle_trained_siege_units_are_reached(
    aoe2_rules, conscription_targets
):
    """The Trebuchet and the Petard are Castle units, so they *are* sped up.

    DE gives the Trebuchet "Creation speed: Conscription (+33%)".  Neither
    unit carries the ``unique_unit`` marker and neither is infantry,
    archer or cavalry, so the old target list silently dropped them.
    """
    for unit in ("trebuchet", "petard"):
        assert aoe2_rules.unit_class(unit) is not None, unit
        assert _matches(aoe2_rules, unit, conscription_targets), unit


def test_the_castle_trained_units_keep_their_speedup(
    aoe2_rules, conscription_targets
):
    """A sample of DE Castle units must be reached.

    ``organ_gun`` (Portuguese) and ``obuch`` (Polish) are the two cases
    that motivated this fix: both are Castle units whose root chain does
    not include ``infantry``.
    """
    for unit in (
        "organ_gun",
        "elite_organ_gun",
        "obuch",
        "elite_obuch",
        "huskarl",
        "konnik",
        "serjeant",
        "mameluke",
        "jaguar_warrior",
        "longbowman",
    ):
        assert aoe2_rules.unit_class(unit) is not None, unit
        assert _matches(aoe2_rules, unit, conscription_targets), unit


# ---------------------------------------------------------------------------
# 2. The mod's own wiring agrees with DE
# ---------------------------------------------------------------------------


def test_mod_wiring_agrees_with_de_trees(
    aoe2_rules, de_trained_at, conscription_targets
):
    """A unit the mod trains at an affected building must be reached.

    This is the wiring half of the check: DE's tech tree decides the
    scope, but if the mod hands a unit to a *different* building, the
    mod's own behaviour would drift from DE even with a perfect target
    list.  It also catches units DE does not implement at all (the
    ``no DE node`` rows in the mod's tech tree).
    """
    building_to_de = {
        "barracks": "Barracks",
        "archery_range": "Archery Range",
        "stables": "Stable",
        "aoe_castle": "Castle",
        "donjon": "Donjon",
        "krepost": "Krepost",
        "shipyard": "Dock",
        "workshop": "Siege Workshop",
        "monastery": "Monastery",
    }

    def _de_building(building_name):
        cls = aoe2_rules.unit_class(building_name)
        if cls is None:
            return None
        chain = set(getattr(cls, "expanded_is_a", ()) or ())
        for root, de in building_to_de.items():
            if root in chain:
                return de
        return None

    # Which mod building trains which unit.
    trainers: dict[str, set[str]] = defaultdict(set)
    for name in aoe2_rules.classnames():
        cls = aoe2_rules.unit_class(name)
        if cls is None:
            continue
        if "building" not in set(getattr(cls, "expanded_is_a", ()) or ()):
            continue
        for unit in aoe2_rules.class_rules_attr(cls, "can_train", ()) or {}:
            trainers[unit].add(name)

    offenders = []
    for unit, buildings in sorted(trainers.items()):
        de_buildings = {
            d for d in (_de_building(b) for b in buildings) if d
        }
        if not de_buildings:
            continue
        if not (de_buildings & DE_AFFECTED_BUILDINGS):
            continue
        # The mod trains it at an affected building: DE must agree, and
        # the unit must be reached.
        de_node = de_trained_at.get(unit)
        if de_node and not (de_node & DE_AFFECTED_BUILDINGS):
            if unit in KNOWN_MOD_WIRING_DIVERGENCE:
                # The mod trains this unit at a different building than
                # DE does.  That is a separate wiring defect, tracked
                # separately; what matters *here* is that Conscription
                # must not reach it, because DE's building is excluded.
                assert not _matches(
                    aoe2_rules, unit, conscription_targets
                ), unit
                continue
            offenders.append((unit, sorted(de_buildings), sorted(de_node)))
            continue
        if not _matches(aoe2_rules, unit, conscription_targets):
            offenders.append((unit, sorted(de_buildings), "not reached"))
    assert not offenders, offenders


def test_known_wiring_divergence_units_are_not_reached(
    aoe2_rules, conscription_targets
):
    """Units the mod wires to the wrong building must stay out of scope.

    The divergence set is currently empty (the ``armored_elephant``
    wiring was fixed: it now lives at the Hindustani Siege Workshop,
    exactly like DE).  The hook stays so that a future re-wiring which
    moves a DE-excluded unit onto an affected building is caught by the
    scope test rather than silently widening Conscription.
    """
    for unit in sorted(KNOWN_MOD_WIRING_DIVERGENCE):
        if aoe2_rules.unit_class(unit) is None:
            continue
        assert not _matches(aoe2_rules, unit, conscription_targets), unit


def test_armored_elephant_is_a_siege_workshop_unit(aoe2_rules):
    """DE trains the Armored Elephant at the **Siege Workshop**.

    The mod used to train it at the Hindustani Castle, which both
    contradicted DE and (because Conscription speeds up Castle work)
    would have handed the unit the +33% bonus that DE withholds from
    Siege Workshop units.
    """
    workshop = aoe2_rules.unit_class("hindustani_workshop")
    castle = aoe2_rules.unit_class("hindustani_castle")

    workshop_trains = set(
        aoe2_rules.class_rules_attr(workshop, "can_train", ()) or {}
    )
    castle_trains = set(
        aoe2_rules.class_rules_attr(castle, "can_train", ()) or {}
    )
    assert "armored_elephant" in workshop_trains
    assert "armored_elephant" not in castle_trains

    workshop_research = set(
        aoe2_rules.class_rules_attr(workshop, "can_research", ()) or {}
    )
    castle_research = set(
        aoe2_rules.class_rules_attr(castle, "can_research", ()) or {}
    )
    assert "elite_armored_elephant" in workshop_research
    assert "elite_armored_elephant" not in castle_research


def test_armored_elephant_is_not_reached_by_conscription(
    aoe2_rules, conscription_targets
):
    """DE's Conscription excludes Siege Workshop units."""
    assert not _matches(aoe2_rules, "armored_elephant", conscription_targets)


# ---------------------------------------------------------------------------
# 3. The scope is expressed by category, not by unit enumeration
# ---------------------------------------------------------------------------


def test_conscription_does_not_enumerate_units(
    aoe2_rules, conscription_targets
):
    """The target list must stay a category list.

    Enumerating every unit id would be unreadable and would silently
    rot as soon as a new unit is added.  The only concrete unit names
    allowed are the two Castle-trained siege weapons (which have no
    category root of their own) and the five exclusions that encode
    DE's excluded buildings.
    """
    allowed_includes = {
        "infantry",
        "archer_unit",
        "cavalry",
        "unique_unit",
        "trebuchet",
        "petard",
    }
    allowed_excludes = {
        "-ship",
        "-monk",
        "-armored_elephant",
        "-houfnice",
        "-flaming_camel",
    }
    for target in conscription_targets:
        if target.startswith("-"):
            assert target in allowed_excludes, (
                "unexpected exclusion in the Conscription target list: %s"
                % target
            )
        else:
            assert target in allowed_includes, (
                "unexpected target name in the Conscription target list: %s"
                % target
            )


def test_conscription_excludes_the_excluded_buildings(
    conscription_targets,
):
    """The exclusions that encode DE's "except Siege Workshops" clause."""
    for needed in ("-ship", "-monk"):
        assert needed in conscription_targets, conscription_targets
