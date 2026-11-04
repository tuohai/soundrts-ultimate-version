# -*- coding: utf-8 -*-
"""AoE2 DE: the Mounted Crossbowman line, Cranequins and Ordonnance Companies.

DE facts (verified against the official DE data — ``_aoe2techtree_data.json``
and the per-civ tech trees in ``_de_trees/*.json``):

  * **Mounted Crossbowman** (DE unit 2700): 65 gold / 40 wood, 40 s,
    HP 45, attack 7 pierce, armor 2 melee / 0 pierce, range 4, reload 2.5 s,
    attack delay 0.91 s, line of sight 6, speed 1.25.  Trained at the
    **Archery Range** from the **Castle Age**.
  * **Heavy Mounted Crossbowman** (DE unit 2701): an *upgrade* of the Mounted
    Crossbowman (DE ``unit_upgrades`` entry 1451) costing 650 gold / 1000
    food, 50 s.  HP 55, attack 8 pierce, armor 2/0, range 4, reload 2.5 s,
    attack delay 0.996667 s (rounded to 1.0), line of sight 6, speed 1.25.
    Researched at the Archery Range from the **Imperial Age**.
  * **Cranequins** (DE tech 1452): 200 gold / 300 food, 70 s, researched at
    the Archery Range in the Imperial Age.  "Mounted Crossbowmen +1 range;
    +2 attack vs. Infantry."  Available to the Britons, Franks and Sicilians.
  * **Ordonnance Companies** (DE tech 1496, Frank unique): 250 gold /
    400 food, 40 s, researched at the Castle.  "Mounted Crossbowmen cost
    -40% gold."

Which civs get which part of the line is a per-civ tech-tree fact; the
exact matrix is asserted below against the DE building-87 data.

NOTE: rules values are stored PRECISION-scaled (x1000) by the engine, e.g.
``hp_max 45`` -> 45000, ``cost 65 40 0 0`` -> (65000, 40000, 0, 0).
The resource slot order is **[gold, wood, food, stone]**.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
P = 1000  # soundrts.lib.nofloat.PRECISION


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    return r


def _attr(rules, name, attr, default=()):
    cls = rules.unit_class(name)
    assert cls is not None, f"missing unit class: {name}"
    value = rules.class_rules_attr(cls, attr, default)
    return value if value else default


def _cost(rules, name):
    return tuple(_attr(rules, name, "cost"))


# ---------------------------------------------------------------------------
# 1. The Mounted Crossbowman
# ---------------------------------------------------------------------------


def test_mounted_crossbowman_exists(aoe2_rules):
    assert aoe2_rules.unit_class("mounted_crossbowman") is not None


def test_mounted_crossbowman_cost_matches_de(aoe2_rules):
    """DE: 65 gold / 40 wood.  Slot order: gold, wood, food, stone."""
    assert _cost(aoe2_rules, "mounted_crossbowman") == (65 * P, 40 * P, 0, 0)


def test_mounted_crossbowman_train_time_matches_de(aoe2_rules):
    """DE: 40 s."""
    assert _attr(aoe2_rules, "mounted_crossbowman", "time_cost") == 40 * P


def test_mounted_crossbowman_stats_match_de(aoe2_rules):
    """DE: HP 45, attack 7 pierce, armor 2 melee / 0 pierce."""
    assert _attr(aoe2_rules, "mounted_crossbowman", "hp_max") == 45 * P
    assert _attr(aoe2_rules, "mounted_crossbowman", "rdg") == 7 * P
    assert _attr(aoe2_rules, "mounted_crossbowman", "mdf") == 2 * P
    # ``rdf 0`` is falsy — read the raw rules dict.
    assert aoe2_rules._dict["mounted_crossbowman"]["rdf"] == 0


def test_mounted_crossbowman_range_and_reload_match_de(aoe2_rules):
    """DE: range 4, reload 2.5 s, attack delay 0.91 s, line of sight 6."""
    assert _attr(aoe2_rules, "mounted_crossbowman", "rdg_range") == 4 * P
    assert _attr(aoe2_rules, "mounted_crossbowman", "rdg_cd") == 2.5 * P
    assert _attr(aoe2_rules, "mounted_crossbowman", "rdg_ready") == 0.91 * P
    assert _attr(aoe2_rules, "mounted_crossbowman", "sight_range") == 6 * P


def test_mounted_crossbowman_is_a_cavalry_archer(aoe2_rules):
    """It is a mounted archer: ``is_a archer_unit`` + ``is_a cavalry``."""
    cls = aoe2_rules.unit_class("mounted_crossbowman")
    expanded = set(getattr(cls, "expanded_is_a", ()) or ())
    assert "archer_unit" in expanded
    assert "cavalry" in expanded


def test_mounted_crossbowman_is_castle_age(aoe2_rules):
    """DE: trained at the Archery Range from the Castle Age."""
    reqs = list(_attr(aoe2_rules, "mounted_crossbowman", "requirements"))
    assert "castle_age" in reqs


def test_mounted_crossbowman_upgrades_into_the_heavy_one(aoe2_rules):
    """The Heavy Mounted Crossbowman is a *line upgrade* of it."""
    can_upgrade = _attr(aoe2_rules, "mounted_crossbowman", "can_upgrade_to")
    assert "heavy_mounted_crossbowman" in can_upgrade


# ---------------------------------------------------------------------------
# 2. The Heavy Mounted Crossbowman
# ---------------------------------------------------------------------------


def test_heavy_mounted_crossbowman_upgrade_cost_matches_de(aoe2_rules):
    """DE ``unit_upgrades`` 1451: 650 gold / 1000 food, 50 s."""
    assert _cost(aoe2_rules, "heavy_mounted_crossbowman") == (650 * P, 0, 1000 * P, 0)
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "time_cost") == 50 * P


def test_heavy_mounted_crossbowman_is_a_line_upgrade(aoe2_rules):
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "line_upgrade") == 1
    cls = aoe2_rules.unit_class("heavy_mounted_crossbowman")
    expanded = set(getattr(cls, "expanded_is_a", ()) or ())
    assert "mounted_crossbowman" in expanded


def test_heavy_mounted_crossbowman_stats_match_de(aoe2_rules):
    """DE: HP 55, attack 8 pierce, armor 2 melee / 0 pierce, speed 1.25."""
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "hp_max") == 55 * P
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "rdg") == 8 * P
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "mdf") == 2 * P
    assert aoe2_rules._dict["heavy_mounted_crossbowman"]["rdf"] == 0
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "speed") == 1.25 * P


def test_heavy_mounted_crossbowman_range_and_reload_match_de(aoe2_rules):
    """DE: range 4, reload 2.5 s, attack delay 0.996667 s (-> 1.0), LoS 6."""
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "rdg_range") == 4 * P
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "rdg_cd") == 2.5 * P
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "rdg_ready") == 1.0 * P
    assert _attr(aoe2_rules, "heavy_mounted_crossbowman", "sight_range") == 6 * P


def test_heavy_mounted_crossbowman_is_imperial_age(aoe2_rules):
    """DE: researched at the Archery Range from the Imperial Age."""
    reqs = list(_attr(aoe2_rules, "heavy_mounted_crossbowman", "requirements"))
    assert "imperial_age" in reqs


# ---------------------------------------------------------------------------
# 3. Cranequins (DE tech 1452)
# ---------------------------------------------------------------------------


def test_cranequins_cost_and_time_match_de(aoe2_rules):
    """DE: 200 gold / 300 food, 70 s."""
    assert _cost(aoe2_rules, "cranequins") == (200 * P, 0, 300 * P, 0)
    assert _attr(aoe2_rules, "cranequins", "time_cost") == 70 * P


def test_cranequins_is_researched_at_the_archery_range(aoe2_rules):
    """DE: researched at the Archery Range in the Imperial Age."""
    reqs = list(_attr(aoe2_rules, "cranequins", "requirements"))
    assert "archery_range" in reqs
    assert "imperial_age" in reqs


def test_cranequins_grants_range_and_infantry_damage(aoe2_rules):
    """DE: "Mounted Crossbowmen +1 range; +2 attack vs. Infantry"."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(aoe2_rules.unit_class("cranequins")))
    assert rows, "cranequins declares no targeted effect row"

    # ``effect bonus`` values are PRECISION-scaled (x1000) by the engine.
    # A ``*_vs`` stat is a triple: ``<stat> <target type> <amount>``.
    flat = []
    for bonus, targets in rows:
        assert list(targets) == ["mounted_crossbowman"], targets
        flat.extend(bonus)
    stats = {}
    i = 0
    while i < len(flat):
        stat = str(flat[i])
        if stat.endswith("_vs"):
            stats[stat] = (str(flat[i + 1]), flat[i + 2])
            i += 3
        else:
            stats[stat] = flat[i + 1]
            i += 2

    assert stats.get("rdg_range") == 1 * P, stats
    # The "+2 attack vs. Infantry" part of the DE description.
    assert stats.get("rdg_vs") == ("infantry", 2 * P), stats


def test_cranequins_is_renamed_from_the_old_spelling(aoe2_rules):
    """The old id was ``cranequin`` (singular); DE spells it ``Cranequins``."""
    assert aoe2_rules.unit_class("cranequin") is None
    assert aoe2_rules.unit_class("cranequins") is not None


# ---------------------------------------------------------------------------
# 4. Ordonnance Companies (DE tech 1496, Frank unique)
# ---------------------------------------------------------------------------


def test_ordonnance_companies_cost_and_time_match_de(aoe2_rules):
    """DE: 250 gold / 400 food, 40 s."""
    assert _cost(aoe2_rules, "ordonnance_companies") == (250 * P, 0, 400 * P, 0)
    assert _attr(aoe2_rules, "ordonnance_companies", "time_cost") == 40 * P


def test_ordonnance_companies_is_researched_at_the_castle(aoe2_rules):
    """DE: researched at the Castle from the Castle Age."""
    reqs = list(_attr(aoe2_rules, "ordonnance_companies", "requirements"))
    assert "aoe_castle" in reqs
    assert "castle_age" in reqs


def test_ordonnance_companies_gives_mounted_crossbowmen_40_percent_less_gold(aoe2_rules):
    """DE: "Mounted Crossbowmen cost -40% gold"."""
    from soundrts.worldupgrade.effect_bonus_parse import tech_target_rows

    rows = list(tech_target_rows(aoe2_rules.unit_class("ordonnance_companies")))
    assert rows, "ordonnance_companies declares no targeted effect row"

    found = False
    for bonus, targets in rows:
        # The Heavy Mounted Crossbowman is ``is_a mounted_crossbowman``, so
        # naming the base type alone already reaches both.
        assert list(targets) == ["mounted_crossbowman"], targets
        for i in range(0, len(bonus) - 1, 2):
            if str(bonus[i]) == "cost":
                assert list(bonus[i + 1:]) == ["0", "-40%", "0", "0"], bonus
                found = True
    assert found, "no cost discount row"


def test_ordonnance_companies_is_a_frank_unique_tech(aoe2_rules):
    """Only the Franks research it, and only at their Castle."""
    assert "ordonnance_companies" in _attr(
        aoe2_rules, "frank_castle", "can_research"
    )
    for civ in ("briton_castle", "teuton_castle", "bohemian_castle"):
        assert "ordonnance_companies" not in _attr(
            aoe2_rules, civ, "can_research"
        ), civ


# ---------------------------------------------------------------------------
# 5. The per-civ Archery Range wiring (DE building 87)
# ---------------------------------------------------------------------------

# The exact DE matrix for the twelve European civs, read off the DE tech
# trees:  "Y" = available, "N" = NotAvailable.
#
#   civ            MCB  HMCB  Cranequins  Crossbow  Arbalester  ElSkirm  ThumbRing  HandCann
#   britons        Y    Y     Y           Y         Y           Y        N           N
#   franks         Y    Y     Y           Y         N           Y        N           Y
#   teutons        Y    Y     N           Y         N           Y        N           Y
#   vikings        Y    N     N           Y         Y           Y        N           N
#   portuguese     Y    N     N           Y         Y           Y        Y           Y
#   celts          Y    Y     N           Y         N           Y        N           N
#   spanish        Y    Y     N           N         N           Y        Y           Y
#   poles          Y    Y     N           Y         Y           Y        Y           N
#   italians       Y    N     N           Y         Y           Y        Y           Y
#   bohemians      Y    N     N           Y         Y           Y        N           Y
#   burgundians    Y    N     N           Y         N           Y        N           Y
#   sicilians      Y    Y     Y           Y         Y           Y        N           N
DE_ARCHERY_MATRIX = {
    "briton": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "Y",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "N",
    },
    "frank": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "Y",
        "crossbowman": "Y",
        "arbalester": "N",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "Y",
    },
    "teuton": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "N",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "Y",
    },
    "viking": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "N",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "N",
    },
    "portuguese": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "N",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "Y",
        "hand_cannoneer": "Y",
    },
    "celtic": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "N",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "N",
    },
    "spanish": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "N",
        "crossbowman": "N",
        "arbalester": "N",
        "elite_skirmisher": "Y",
        "thumb_ring": "Y",
        "hand_cannoneer": "Y",
    },
    "polish": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "Y",
        "hand_cannoneer": "N",
    },
    "italian": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "N",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "Y",
        "hand_cannoneer": "Y",
    },
    "bohemian": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "N",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "Y",
    },
    "burgundian": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "N",
        "cranequins": "N",
        "crossbowman": "Y",
        "arbalester": "N",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "Y",
    },
    "sicilian": {
        "mounted_crossbowman": "Y",
        "heavy_mounted_crossbowman": "Y",
        "cranequins": "Y",
        "crossbowman": "Y",
        "arbalester": "Y",
        "elite_skirmisher": "Y",
        "thumb_ring": "N",
        "hand_cannoneer": "N",
    },
}

# Techs that are *researched* (not trained) and units that are *trained*.
_TRAINED = {"mounted_crossbowman", "hand_cannoneer"}
_RESEARCHED = {
    "heavy_mounted_crossbowman",
    "cranequins",
    "crossbowman",
    "arbalester",
    "elite_skirmisher",
    "thumb_ring",
}


def test_the_de_matrix_covers_the_twelve_european_civs():
    assert len(DE_ARCHERY_MATRIX) == 12


@pytest.mark.parametrize("civ_prefix", sorted(DE_ARCHERY_MATRIX))
def test_archery_range_matches_the_de_matrix(aoe2_rules, civ_prefix):
    """Every European civ's Archery Range must match the DE building-87 data."""
    matrix = DE_ARCHERY_MATRIX[civ_prefix]
    archery = "%s_archery" % civ_prefix
    assert aoe2_rules.unit_class(archery) is not None, archery

    can_train = set(_attr(aoe2_rules, archery, "can_train"))
    can_research = set(_attr(aoe2_rules, archery, "can_research"))

    for name, status in matrix.items():
        if name in _TRAINED:
            listed = name in can_train
        else:
            listed = name in can_research
        assert listed == (status == "Y"), (
            "%s: %s should be %s (can_train=%s, can_research=%s)"
            % (archery, name, status, sorted(can_train), sorted(can_research))
        )


@pytest.mark.parametrize("civ_prefix", sorted(DE_ARCHERY_MATRIX))
def test_no_european_civ_trains_the_cavalry_archer(aoe2_rules, civ_prefix):
    """DE: the Cavalry Archer line is not available at the European ranges."""
    archery = "%s_archery" % civ_prefix
    can_train = set(_attr(aoe2_rules, archery, "can_train"))
    assert "cavalry_archer" not in can_train, archery
    can_research = set(_attr(aoe2_rules, archery, "can_research"))
    assert "heavy_cavalry_archer" not in can_research, archery


def test_every_european_civ_trains_the_mounted_crossbowman(aoe2_rules):
    """DE: all twelve European civs get the Mounted Crossbowman (Castle Age)."""
    missing = []
    for civ_prefix in sorted(DE_ARCHERY_MATRIX):
        archery = "%s_archery" % civ_prefix
        can_train = set(_attr(aoe2_rules, archery, "can_train"))
        if "mounted_crossbowman" not in can_train:
            missing.append(archery)
    assert not missing, missing


def test_the_heavy_mounted_crossbowman_is_for_seven_civs(aoe2_rules):
    """DE: Britons, Celts, Franks, Poles, Sicilians, Spanish, Teutons."""
    expected = {
        "briton_archery",
        "celtic_archery",
        "frank_archery",
        "polish_archery",
        "sicilian_archery",
        "spanish_archery",
        "teuton_archery",
    }
    actual = set()
    for civ_prefix in sorted(DE_ARCHERY_MATRIX):
        archery = "%s_archery" % civ_prefix
        if "heavy_mounted_crossbowman" in set(_attr(aoe2_rules, archery, "can_research")):
            actual.add(archery)
    assert actual == expected, sorted(actual ^ expected)


def test_cranequins_is_for_three_civs(aoe2_rules):
    """DE: Britons, Franks, Sicilians."""
    expected = {"briton_archery", "frank_archery", "sicilian_archery"}
    actual = set()
    for civ_prefix in sorted(DE_ARCHERY_MATRIX):
        archery = "%s_archery" % civ_prefix
        if "cranequins" in set(_attr(aoe2_rules, archery, "can_research")):
            actual.add(archery)
    assert actual == expected, sorted(actual ^ expected)


def test_the_mounted_crossbowman_line_is_not_offered_outside_the_european_civs(aoe2_rules):
    """The Mounted Crossbowman is a European civ unit (DE "RegionalUnit")."""
    offenders = []
    for civ in aoe2_rules.factions:
        prefix = civ
        for key in ("archery_range",):
            for building in aoe2_rules.get(civ, key) or ():
                can_train = set(_attr(aoe2_rules, building, "can_train"))
                if "mounted_crossbowman" in can_train:
                    offenders.append((civ, building))
    # The twelve European civs are expected; anything else is a bug.
    european = {
        "%s_archery" % p for p in DE_ARCHERY_MATRIX
    }
    unexpected = [o for o in offenders if o[1] not in european]
    assert not unexpected, unexpected
    assert {o[1] for o in offenders} == european, sorted(
        european ^ {o[1] for o in offenders}
    )
