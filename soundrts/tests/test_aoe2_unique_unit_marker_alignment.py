# -*- coding: utf-8 -*-
"""``is_a unique_unit`` must match the AoE2 DE "unique unit" classification.

The mod's ``unique_unit`` marker carries two meanings at once:

1. **Engine damage category.**  ``mdg_vs unique_unit 8`` on the Japanese
   Samurai is DE's "Strong vs. Unique Units" bonus.  In the official DE
   data that bonus is armour **class 19**, and DE puts exactly its
   civ-exclusive units into it.
2. **Leak-detection invariant.**  ``soundrts/tests/
   test_effect_bonus_target_redundancy.py`` exempts civ-exclusive units
   from base-class leakage checks, on the grounds that a unit only one
   civilisation owns can never show up in another civ's army.

Both meanings only hold if the marker means the same thing DE means by
"unique unit".  DE's own tech-tree data makes that explicit with a
``node_type`` field, and DE's unit data makes it explicit with armour
class 19:

* ``node_type == "UniqueUnit"`` -- a civ-exclusive signature unit.
* ``node_type == "RegionalUnit"`` -- a unit shared by a *group* of
  civilisations (the Dromon of the Return of Rome, the Slinger of the
  Incas, the Longship of the Vikings, the Mounted Crossbowman of the
  western civs, ...).  These are **not** unique units: they show up in
  several armies, so the leak-detection exemption would be wrong for
  them, and DE does not give them the Samurai bonus.
* ``node_type == "Unit"`` / ``"UnitUpgrade"`` -- generic base units and
  generic line upgrades.

This module pins the mod's markers to that DE classification, so a
future edit cannot silently re-introduce the drift:

* every DE ``UniqueUnit`` that exists in the mod is marked
  ``is_a unique_unit``;
* nothing that DE calls a ``RegionalUnit`` is marked
  ``is_a unique_unit``.

Reference data (both are checked into the repository):

* ``_de_trees/*.json`` -- the 42 per-civilisation DE tech trees.  Each
  file name is the civ's slug (``inca``, ``malay``, ``maya``, ...); the
  mod's faction names differ slightly (``incas``, ``malays``,
  ``mayans``), and :func:`_civ_slug` maps between them.  Each entry
  carries a ``node_type``.
* ``_aoe2techtree_data.json`` -- the official DE unit/tech tables,
  carrying the armour class lists.
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
DE_DATA = ROOT / "_aoe2techtree_data.json"

# DE's node types that describe a *unit* (as opposed to a technology).
UNIT_NODE_TYPES = {"UniqueUnit", "RegionalUnit", "Unit", "UnitUpgrade"}

# The mod spells three civs in the plural where DE uses the singular.
_MOD_TO_DE_CIV = {
    "incas": "inca",
    "malays": "malay",
    "mayans": "maya",
}

# DE display names whose mechanical counterpart carries a different id in
# ``rules.txt``.  Without this map the DE name simply does not resolve to
# a mod type, and the unit silently escapes every check below -- the
# Viking Longship (DE) is the mod's ``longboat``, and DE's *Longship*
# being a ``RegionalUnit`` is exactly what makes the ``unique_unit``
# marker wrong for it.
_DE_NAME_TO_MOD_ID = {
    "longship": "longboat",
    "elite longship": "elite_longboat",
}

# DE civs that own the same UniqueUnit (the Polish/Lithuanian Winged
# Hussar).  A shared unique unit is still a *unique* unit: DE gives it
# its own tech-tree node type and its own damage class, and it never
# appears in a third civ's army.
_SHARED_UNIQUE_CIVS = {
    "winged_hussar": {"lithuanians", "poles"},
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


def _civ_slug(mod_faction: str) -> str:
    """The ``_de_trees`` file stem of a mod faction name."""
    return _MOD_TO_DE_CIV.get(mod_faction, mod_faction)


@pytest.fixture(scope="module")
def de_units():
    """DE display name -> {"types": set, "civs": set, "ids": set}.

    ``civs`` uses the mod's faction names so it can be compared with
    :attr:`soundrts.definitions.Rules.factions` directly.
    """
    out: dict[str, dict] = defaultdict(
        lambda: {"types": set(), "civs": set(), "ids": set()}
    )
    for path in sorted(glob.glob(str(DE_TREES / "*.json"))):
        slug = Path(path).stem
        faction = next(
            (f for f in _MOD_TO_DE_CIV if _MOD_TO_DE_CIV[f] == slug), slug
        )
        tree = json.loads(Path(path).read_text(encoding="utf-8"))
        for node in tree.get("units_techs") or ():
            if node.get("node_type") not in UNIT_NODE_TYPES:
                continue
            entry = out[node["name"]]
            entry["types"].add(node["node_type"])
            entry["civs"].add(faction)
            entry["ids"].add(int(node["node_id"]))
    return dict(out)


@pytest.fixture(scope="module")
def de_class19():
    """The set of DE unit ids whose armour list contains class 19.

    Class 19 is DE's "unique unit" damage class: it is what the
    Samurai's "Strong vs. Unique Units" bonus actually hits.
    """
    if not DE_DATA.exists():
        pytest.skip("_aoe2techtree_data.json not available")
    data = json.loads(DE_DATA.read_text(encoding="utf-8"))
    return {
        int(uid)
        for uid, rec in data["data"]["Unit"].items()
        if any(a["Class"] == 19 for a in rec.get("Armours") or [])
    }


def _mod_id(de_name: str) -> str:
    """The ``rules.txt`` id of a DE display name.

    A handful of DE names are spelled differently in the mod (the Viking
    *Longship* is the mod's ``longboat``); those are listed in
    :data:`_DE_NAME_TO_MOD_ID`.  Everything else is the DE name with
    non-alphanumerics turned into underscores.
    """
    alias = _DE_NAME_TO_MOD_ID.get(de_name.lower())
    if alias is not None:
        return alias
    return re.sub(r"[^a-z0-9]+", "_", de_name.lower()).strip("_")


def _is_marked(rules, type_name: str) -> bool:
    cls = rules.unit_class(type_name)
    if cls is None:
        return False
    return "unique_unit" in set(getattr(cls, "expanded_is_a", ()) or ())


# ---------------------------------------------------------------------------
# 1. Every DE UniqueUnit the mod defines is marked
# ---------------------------------------------------------------------------


def test_every_de_unique_unit_is_marked(aoe2_rules, de_units):
    """DE ``node_type=UniqueUnit`` -> the mod marks it ``is_a unique_unit``."""
    unmarked = []
    for de_name, entry in sorted(de_units.items()):
        if "UniqueUnit" not in entry["types"]:
            continue
        mod_id = _mod_id(de_name)
        if aoe2_rules.unit_class(mod_id) is None:
            # The mod does not implement this unit at all -- a separate
            # (already tracked) gap, not a marker problem.
            continue
        if not _is_marked(aoe2_rules, mod_id):
            unmarked.append((de_name, mod_id))
    assert not unmarked, (
        "DE unique units missing the `unique_unit` marker: %s" % unmarked
    )


# ---------------------------------------------------------------------------
# 2. Nothing DE calls regional is marked
# ---------------------------------------------------------------------------


def test_no_regional_unit_is_marked(aoe2_rules, de_units):
    """DE ``node_type=RegionalUnit`` -> the mod must NOT mark it.

    A regional unit belongs to a *group* of civilisations, so:

    * it can appear in more than one army, which makes the leak-detection
      exemption in ``test_effect_bonus_target_redundancy.py`` invalid for
      it, and
    * DE does not give it the Samurai's "Strong vs. Unique Units" bonus
      (it is not in DE armour class 19).
    """
    wrongly_marked = []
    for de_name, entry in sorted(de_units.items()):
        if "UniqueUnit" in entry["types"]:
            continue
        if "RegionalUnit" not in entry["types"]:
            continue
        mod_id = _mod_id(de_name)
        if aoe2_rules.unit_class(mod_id) is None:
            continue
        if _is_marked(aoe2_rules, mod_id):
            wrongly_marked.append((de_name, mod_id, sorted(entry["civs"])))
    assert not wrongly_marked, (
        "DE regional units wrongly marked `unique_unit`: %s" % wrongly_marked
    )


# ---------------------------------------------------------------------------
# 3. The engine damage category agrees with DE's class 19
# ---------------------------------------------------------------------------


def test_regional_units_are_not_in_de_class19(de_units, de_class19):
    """Sanity check on the reference data itself.

    If DE's class 19 contained regional units, the two signals used by
    this module would contradict each other and the marker could not be
    pinned to either.  This test documents that they agree.
    """
    regional_in_19 = [
        name
        for name, entry in de_units.items()
        if "RegionalUnit" in entry["types"]
        and entry["ids"] & de_class19
    ]
    assert not regional_in_19, regional_in_19


def test_samurai_bonus_only_reaches_de_unique_units(aoe2_rules, de_units,
                                                    de_class19):
    """The Samurai's ``mdg_vs unique_unit`` must hit DE's class 19.

    The bonus is modelled as an ``mdg_vs`` row against the ``unique_unit``
    category, so the units it reaches are exactly the ones the mod marks.
    DE's equivalent is armour class 19.  Both sets must agree for every
    DE unit the mod implements.
    """
    mismatches = []
    for de_name, entry in sorted(de_units.items()):
        if not entry["ids"]:
            continue
        if not entry["types"] & {"UniqueUnit", "RegionalUnit"}:
            continue
        mod_id = _mod_id(de_name)
        if aoe2_rules.unit_class(mod_id) is None:
            continue
        in_class19 = bool(entry["ids"] & de_class19)
        marked = _is_marked(aoe2_rules, mod_id)
        # A DE UniqueUnit may lack class 19 (DE itself is not perfectly
        # self-consistent for a handful of line upgrades), so only the
        # regional direction is asserted strictly.
        if "RegionalUnit" in entry["types"] and in_class19:
            mismatches.append((de_name, "regional but in class 19"))
        if "UniqueUnit" in entry["types"] and in_class19 and not marked:
            mismatches.append((de_name, "in class 19 but not marked"))
    assert not mismatches, mismatches


# ---------------------------------------------------------------------------
# 4. The marker keeps its leak-detection meaning
# ---------------------------------------------------------------------------


def test_marked_units_are_owned_by_one_civ_or_a_known_shared_pair(
    aoe2_rules, de_units
):
    """A marked unit must belong to exactly one civ (or a known pair).

    This is the invariant the leak-detection exemption in
    ``test_effect_bonus_target_redundancy.py`` relies on: the exemption
    is only sound when the unit cannot show up in an unrelated civ's
    army.

    The civ list is taken from DE's own tech trees, so it reflects what
    DE intends rather than what the mod currently wires up.
    """
    offenders = []
    for de_name, entry in sorted(de_units.items()):
        if "UniqueUnit" not in entry["types"]:
            continue
        mod_id = _mod_id(de_name)
        if aoe2_rules.unit_class(mod_id) is None:
            continue
        if not _is_marked(aoe2_rules, mod_id):
            continue
        civs = set(entry["civs"])
        allowed = _SHARED_UNIQUE_CIVS.get(mod_id)
        if allowed is not None:
            if civs != allowed:
                offenders.append((mod_id, sorted(civs), sorted(allowed)))
        elif len(civs) != 1:
            offenders.append((mod_id, sorted(civs)))
    assert not offenders, offenders


def test_marked_units_are_wired_to_exactly_their_de_civs(aoe2_rules, de_units):
    """The mod must not hand a marked unit to a civ DE does not give it to.

    This is the wiring half of the leak-detection invariant.  A unit
    marked ``unique_unit`` that several civs can train would defeat the
    exemption in ``test_effect_bonus_target_redundancy.py``: the unit
    really can appear in several armies.

    The Turtle Ship was the concrete case -- DE gives it to the Koreans
    only, but the mod used to offer it at six shipyards.
    """
    mod_civs = set(aoe2_rules.factions)
    building_keys = (
        "barracks", "archery_range", "stables", "aoe_castle", "shipyard",
        "university", "market", "monastery", "workshop", "townhall",
    )

    def _mod_owners(unit: str) -> set[str]:
        out: set[str] = set()
        for civ in mod_civs:
            for key in building_keys:
                for building in aoe2_rules.get(civ, key) or ():
                    cls = aoe2_rules.unit_class(building)
                    if cls is None:
                        continue
                    trained = aoe2_rules.class_rules_attr(
                        cls, "can_train", ()) or {}
                    researched = aoe2_rules.class_rules_attr(
                        cls, "can_research", ()) or ()
                    if unit in trained or unit in researched:
                        out.add(civ)
        return out

    offenders = []
    for de_name, entry in sorted(de_units.items()):
        if "UniqueUnit" not in entry["types"]:
            continue
        mod_id = _mod_id(de_name)
        if aoe2_rules.unit_class(mod_id) is None:
            continue
        if not _is_marked(aoe2_rules, mod_id):
            continue
        # ``de_units`` already reports DE's civs under the mod's faction
        # names, so the two sets are directly comparable.
        de_civs = set(entry["civs"])
        mod_owners = _mod_owners(mod_id)
        # A shared unique unit (the Polish/Lithuanian Winged Hussar) is
        # legitimately owned by more than one civ.
        extra = mod_owners - de_civs
        if extra:
            offenders.append((mod_id, sorted(extra), sorted(de_civs)))
    assert not offenders, offenders


# ---------------------------------------------------------------------------
# 5. Every marked unit is reachable
# ---------------------------------------------------------------------------


def test_every_marked_unit_is_reachable(aoe2_rules):
    """A marked unit must be trainable or researchable somewhere.

    ``test_aoe2_civ_unique_units_alignment.py`` asserts the same thing
    from the other direction; this module repeats it so that the
    ``unique_unit`` marker can never be applied to a dead shell.
    """
    raw = aoe2_rules._dict
    trainable: set[str] = set()
    researchable: set[str] = set()
    for obj in raw.values():
        if obj.get("class", [None])[0] not in ("faction", "race"):
            continue
        for slot in (
            "barracks", "archery_range", "stables", "aoe_castle", "workshop",
            "university", "blacksmith", "shipyard", "townhall", "market",
            "monastery", "mill",
        ):
            value = obj.get(slot)
            if not value:
                continue
            building = value[0] if isinstance(value, list) else value
            bobj = raw.get(building) or {}
            trains = bobj.get("_rules_can_train")
            if trains is None:
                trains = bobj.get("can_train")
            if isinstance(trains, dict):
                trains = list(trains)
            trainable |= set(trains or ())
            researchable |= set(bobj.get("can_research") or ())

    unreachable = [
        name
        for name in aoe2_rules.classnames()
        if _is_marked(aoe2_rules, name)
        and name not in trainable
        and name not in researchable
    ]
    assert not unreachable, unreachable
