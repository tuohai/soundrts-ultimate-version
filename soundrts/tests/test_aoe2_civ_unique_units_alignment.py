# -*- coding: utf-8 -*-
"""AoE2 DE alignment tests for the civs fixed in the 2026-10-30 audit.

The audit found that several civ unique units were either never wired into a
building, or defined with stats that did not match AoE2: Definitive Edition:

  * Bulgarians: the mod defined a non-existent unit named ``bulwark`` and a
    *mounted archer* named ``konnik``.  DE's real Bulgarian UU is the Konnik,
    a heavy cavalry (The Last Khans).
  * Italians: the Condottiero existed but no building could train it.
  * Incas: the Kamayuk was never trainable, and the Slinger had invented
    stats (and belonged at the Archery Range, not the Castle).
  * Byzantines / Goths / Huns / Armenians / Romans: the Dromon (Return of Rome
    regional siege ship) existed but was trainable nowhere.
  * Hindustanis: DE's Dynasties of India removed the (Elite) Elephant Archer
    from them and added the Ghulam; the mod still offered the Elephant Archer
    and had no Ghulam.

NOTE: rules values are stored PRECISION-scaled (x1000) by the engine, e.g.
``hp_max 125`` -> 125000, ``speed 1.35`` -> 1350.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
P = 1000  # soundrts.lib.nofloat.PRECISION


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


@pytest.fixture(scope="module")
def installed(aoe2_rules):
    """Install the AoE2 rules as the global rules for engine-level helpers."""
    from soundrts.definitions import rules as global_rules

    saved_dict = global_rules._dict
    saved_classes = global_rules.classes
    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    yield aoe2_rules
    global_rules._dict = saved_dict
    global_rules.classes = saved_classes


def _attr(aoe2_rules, type_name, attr, default=None):
    value = aoe2_rules.get(type_name, attr)
    if value is None:
        return default
    if isinstance(value, list) and not value:
        return default
    return value


def _can_train(aoe2_rules, type_name):
    cls = aoe2_rules.unit_class(type_name)
    assert cls is not None, "unknown type %r" % type_name
    return set(aoe2_rules.class_rules_attr(cls, "can_train", ()) or ())


def _can_research(aoe2_rules, type_name):
    cls = aoe2_rules.unit_class(type_name)
    assert cls is not None, "unknown type %r" % type_name
    return set(aoe2_rules.class_rules_attr(cls, "can_research", ()) or ())


def _race(aoe2_rules, faction):
    race = aoe2_rules._dict.get(faction) or {}
    assert race, "missing race %r" % faction
    return race


# --------------------------------------------------------------------------
# Bulgarians — the Konnik (DE: heavy cavalry, not a mounted archer)
# --------------------------------------------------------------------------


def test_bulwark_no_longer_exists(aoe2_rules):
    """``bulwark`` was never an AoE2 DE unit; it must be gone."""
    assert aoe2_rules.unit_class("bulwark") is None
    assert aoe2_rules.unit_class("elite_bulwark") is None


def test_bulgarian_castle_trains_the_konnik(aoe2_rules):
    assert "konnik" in _can_train(aoe2_rules, "bulgarian_castle")
    assert "trebuchet" in _can_train(aoe2_rules, "bulgarian_castle")


def test_bulgarian_castle_researches_the_elite_konnik(aoe2_rules):
    assert "elite_konnik" in _can_research(aoe2_rules, "bulgarian_castle")


def test_konnik_is_heavy_cavalry_not_a_mounted_archer(aoe2_rules):
    """DE: the Konnik is a heavy cavalry unit (HP 100, Atk 12, Arm 2/2)."""
    assert "archer_unit" not in (_attr(aoe2_rules, "konnik", "is_a", ()) or ())
    assert "cavalry" in (_attr(aoe2_rules, "konnik", "is_a", ()) or ())
    assert _attr(aoe2_rules, "konnik", "hp_max") == 100 * P
    assert _attr(aoe2_rules, "konnik", "mdg") == 12 * P
    assert _attr(aoe2_rules, "konnik", "mdf") == 2 * P
    assert _attr(aoe2_rules, "konnik", "rdf") == 2 * P
    assert _attr(aoe2_rules, "konnik", "speed") == 1.35 * P
    assert _attr(aoe2_rules, "konnik", "population_cost") == 2
    assert "castle_age" in (_attr(aoe2_rules, "konnik", "requirements", ()) or ())


def test_konnik_cost_and_train_time(aoe2_rules):
    cost = list(_attr(aoe2_rules, "konnik", "cost", ()) or ())
    assert cost[0] == 70 * P  # gold
    assert cost[2] == 60 * P  # food


def test_elite_konnik_stats_and_cost(aoe2_rules):
    assert _attr(aoe2_rules, "elite_konnik", "hp_max") == 120 * P
    assert _attr(aoe2_rules, "elite_konnik", "mdg") == 14 * P
    cost = list(_attr(aoe2_rules, "elite_konnik", "cost", ()) or ())
    assert cost[0] == 750 * P  # gold
    assert cost[2] == 1000 * P  # food
    assert _attr(aoe2_rules, "elite_konnik", "time_cost") == 70 * P


def test_konnik_upgrades_to_elite_konnik(aoe2_rules):
    ups = set(_attr(aoe2_rules, "konnik", "can_upgrade_to", ()) or ())
    assert "elite_konnik" in ups


# --------------------------------------------------------------------------
# Italians — the Condottiero is trainable at the Barracks
# --------------------------------------------------------------------------


def test_italian_barracks_trains_the_condottiero(aoe2_rules):
    assert "condottiero" in _can_train(aoe2_rules, "italian_barracks")


def test_condottiero_stats_match_de(aoe2_rules):
    """DE: 35 gold 50 food, 18s, HP 80, Atk 10, Arm 1/0, speed 1.2, LoS 6."""
    cost = list(_attr(aoe2_rules, "condottiero", "cost", ()) or ())
    assert cost[0] == 35 * P  # gold
    assert cost[2] == 50 * P  # food
    assert _attr(aoe2_rules, "condottiero", "time_cost") == 18 * P
    assert _attr(aoe2_rules, "condottiero", "hp_max") == 80 * P
    assert _attr(aoe2_rules, "condottiero", "mdg") == 10 * P
    assert _attr(aoe2_rules, "condottiero", "mdf") == 1 * P
    assert _attr(aoe2_rules, "condottiero", "rdf") == 0
    assert _attr(aoe2_rules, "condottiero", "speed") == 1.2 * P
    assert _attr(aoe2_rules, "condottiero", "sight_range") == 6 * P
    assert "imperial_age" in (
        _attr(aoe2_rules, "condottiero", "requirements", ()) or ()
    )


def test_condottiero_has_no_elite_version(aoe2_rules):
    assert aoe2_rules.unit_class("elite_condottiero") is None


def test_condottiero_bonus_damage_vs_gunpowder_and_buildings(aoe2_rules):
    mdg_vs = _attr(aoe2_rules, "condottiero", "mdg_vs", {}) or {}
    assert mdg_vs.get("hand_cannoneer") == 10 * P
    assert mdg_vs.get("building") == 2 * P


def test_condottiero_is_team_free(aoe2_rules):
    """The Italian team bonus makes the Condottiero free for every ally."""
    assert _attr(aoe2_rules, "condottiero", "team_free_unit")
    grants = _race(aoe2_rules, "italians").get("race_grants_team_free_unit")
    assert grants
    assert "condottiero" in {n for row in grants for n in row}


def test_condottiero_is_shared_with_allies_via_team_share_train(aoe2_rules):
    """AoE2: allies of an Italian can train the Condottiero too."""
    rows = _race(aoe2_rules, "italians").get("team_share_train")
    assert rows
    units = {row[0] for row in rows}
    hosts = {h for row in rows for h in row[1:]}
    assert "condottiero" in units
    assert "barracks" in hosts


def test_team_share_train_rows_reach_allies(installed):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_civ_bonuses import team_share_train_entries

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    italian = SimpleNamespace(faction="italians")
    ally = SimpleNamespace(faction="britons")
    ally.allied_victory = [ally, italian]

    rows = team_share_train_entries(ally)
    assert any(unit == "condottiero" for unit, _hosts in rows)


def test_allied_barracks_offers_the_condottiero(installed):
    """A British player allied with an Italian gets the Condottiero."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    italian = SimpleNamespace(faction="italians")
    player = SimpleNamespace(
        faction="britons",
        upgrades=[],
        allied_victory=[],
        _can_train_overrides_by_type=None,
    )
    player.allied_victory = [player, italian]

    barracks = installed.unit_class("briton_barracks")
    unit = SimpleNamespace(
        player=player, type=barracks, type_name="briton_barracks",
        attached_addons=[],
    )
    assert "condottiero" in effective_can_train(unit)


def test_unallied_barracks_does_not_offer_the_condottiero(installed):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = SimpleNamespace(
        faction="britons",
        upgrades=[],
        allied_victory=[],
        _can_train_overrides_by_type=None,
    )
    player.allied_victory = [player]

    barracks = installed.unit_class("briton_barracks")
    unit = SimpleNamespace(
        player=player, type=barracks, type_name="briton_barracks",
        attached_addons=[],
    )
    assert "condottiero" not in effective_can_train(unit)


# --------------------------------------------------------------------------
# Incas — Kamayuk at the Castle, Slinger at the Archery Range
# --------------------------------------------------------------------------


def test_incan_castle_trains_the_kamayuk(aoe2_rules):
    assert "kamayuk" in _can_train(aoe2_rules, "incan_castle")
    assert "elite_kamayuk" in _can_research(aoe2_rules, "incan_castle")


def test_incan_archery_trains_the_slinger(aoe2_rules):
    """DE: the Slinger is an Archery Range unit, not a Castle unit."""
    assert "slinger" in _can_train(aoe2_rules, "incan_archery")
    assert "slinger" not in _can_train(aoe2_rules, "incan_castle")


def test_kamayuk_stats_match_de(aoe2_rules):
    """DE: 30 gold 70 food, 10s, HP 70, Atk 7, Arm 1/0, speed 1.0."""
    cost = list(_attr(aoe2_rules, "kamayuk", "cost", ()) or ())
    assert cost[0] == 30 * P  # gold
    assert cost[2] == 70 * P  # food
    assert _attr(aoe2_rules, "kamayuk", "time_cost") == 10 * P
    assert _attr(aoe2_rules, "kamayuk", "hp_max") == 70 * P
    assert _attr(aoe2_rules, "kamayuk", "mdg") == 7 * P
    assert _attr(aoe2_rules, "kamayuk", "mdf") == 1 * P
    assert _attr(aoe2_rules, "kamayuk", "speed") == 1.0 * P


def test_kamayuk_bonus_damage(aoe2_rules):
    mdg_vs = _attr(aoe2_rules, "kamayuk", "mdg_vs", {}) or {}
    assert mdg_vs.get("cavalry") == 8 * P
    assert mdg_vs.get("camel_rider") == 6 * P


def test_elite_kamayuk_stats_and_cost(aoe2_rules):
    assert _attr(aoe2_rules, "elite_kamayuk", "hp_max") == 80 * P
    assert _attr(aoe2_rules, "elite_kamayuk", "mdg") == 8 * P
    cost = list(_attr(aoe2_rules, "elite_kamayuk", "cost", ()) or ())
    assert cost[0] == 500 * P  # gold
    assert cost[2] == 900 * P  # food


def test_slinger_stats_match_de(aoe2_rules):
    """DE: 50 food 25 wood, 25s, HP 35, Atk 4, range 5, accuracy 90%."""
    cost = list(_attr(aoe2_rules, "slinger", "cost", ()) or ())
    assert cost[1] == 25 * P  # wood
    assert cost[2] == 50 * P  # food
    assert _attr(aoe2_rules, "slinger", "time_cost") == 25 * P
    assert _attr(aoe2_rules, "slinger", "hp_max") == 35 * P
    assert _attr(aoe2_rules, "slinger", "rdg") == 4 * P
    assert _attr(aoe2_rules, "slinger", "rdg_range") == 5 * P
    assert _attr(aoe2_rules, "slinger", "rdg_hit_rate") == 90 * P
    assert _attr(aoe2_rules, "slinger", "speed") == 0.96 * P


def test_slinger_cannot_attack_at_close_range(aoe2_rules):
    """DE: the Slinger is a skirmisher with a minimum range of 2."""
    assert _attr(aoe2_rules, "slinger", "rdg_minimal_range") == 2 * P


def test_slinger_bonus_damage(aoe2_rules):
    rdg_vs = _attr(aoe2_rules, "slinger", "rdg_vs", {}) or {}
    assert rdg_vs.get("infantry") == 4 * P
    assert rdg_vs.get("spearman") == 1 * P
    assert rdg_vs.get("siege_unit") == 3 * P


# --------------------------------------------------------------------------
# Dromon — the Return of Rome regional siege ship
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "shipyard",
    [
        "armenian_shipyard",
        "byzantine_shipyard",
        "goth_shipyard",
        "hun_shipyard",
        "roman_shipyard",
    ],
)
def test_dromon_is_trainable_at_the_regional_shipyards(aoe2_rules, shipyard):
    assert "dromon" in _can_train(aoe2_rules, shipyard)


def test_dromon_stats_match_de(aoe2_rules):
    """DE: 150 gold 175 wood, 65s, HP 125, Atk 8, Arm 1/6, range 12, LoS 14."""
    cost = list(_attr(aoe2_rules, "dromon", "cost", ()) or ())
    assert cost[0] == 150 * P  # gold
    assert cost[1] == 175 * P  # wood
    assert _attr(aoe2_rules, "dromon", "time_cost") == 65 * P
    assert _attr(aoe2_rules, "dromon", "hp_max") == 125 * P
    assert _attr(aoe2_rules, "dromon", "mdg") == 8 * P
    assert _attr(aoe2_rules, "dromon", "mdf") == 1 * P
    assert _attr(aoe2_rules, "dromon", "rdf") == 6 * P
    assert _attr(aoe2_rules, "dromon", "mdg_range") == 12 * P
    assert _attr(aoe2_rules, "dromon", "sight_range") == 14 * P
    assert _attr(aoe2_rules, "dromon", "speed") == 1.15 * P


def test_dromon_cannot_attack_at_close_range(aoe2_rules):
    assert _attr(aoe2_rules, "dromon", "mdg_minimal_range") == 3 * P


def test_dromon_is_imperial_age_only(aoe2_rules):
    assert "imperial_age" in (_attr(aoe2_rules, "dromon", "requirements", ()) or ())


def test_dromon_bonus_damage(aoe2_rules):
    mdg_vs = _attr(aoe2_rules, "dromon", "mdg_vs", {}) or {}
    assert mdg_vs.get("building") == 34 * P
    assert mdg_vs.get("siege_unit") == 2 * P


def test_dromon_splash_pool_matches_its_attack(aoe2_rules):
    """Engine convention: the blast pool equals the main attack."""
    assert _attr(aoe2_rules, "dromon", "mdg_splash") == 8 * P


# --------------------------------------------------------------------------
# Hindustanis — the Ghulam replaces the removed Elephant Archer
# --------------------------------------------------------------------------


def test_hindustani_castle_trains_the_ghulam(aoe2_rules):
    assert "ghulam" in _can_train(aoe2_rules, "hindustani_castle")
    assert "elite_ghulam" in _can_research(aoe2_rules, "hindustani_castle")


def test_hindustanis_no_longer_offer_the_elephant_archer(aoe2_rules):
    """DE (Dynasties of India) removed the Elephant Archer from the
    Hindustanis -- it is a regional unit for the South Asian civs."""
    for building in (
        "hindustani_stable",
        "hindustani_archery",
        "hindustani_castle",
    ):
        assert "elephant_archer" not in _can_train(aoe2_rules, building)
        assert "elite_elephant_archer" not in _can_research(
            aoe2_rules, building
        )


def test_ghulam_stats_match_de(aoe2_rules):
    """DE: 45 gold 30 food, 12s, HP 60, Atk 9, Arm 0/3, speed 1.15, LoS 6."""
    cost = list(_attr(aoe2_rules, "ghulam", "cost", ()) or ())
    assert cost[0] == 45 * P  # gold
    assert cost[2] == 30 * P  # food
    assert _attr(aoe2_rules, "ghulam", "time_cost") == 12 * P
    assert _attr(aoe2_rules, "ghulam", "hp_max") == 60 * P
    assert _attr(aoe2_rules, "ghulam", "mdg") == 9 * P
    assert _attr(aoe2_rules, "ghulam", "mdf") == 0
    assert _attr(aoe2_rules, "ghulam", "rdf") == 3 * P
    assert _attr(aoe2_rules, "ghulam", "speed") == 1.15 * P
    assert "castle_age" in (_attr(aoe2_rules, "ghulam", "requirements", ()) or ())


def test_ghulam_bonus_damage_vs_archers(aoe2_rules):
    mdg_vs = _attr(aoe2_rules, "ghulam", "mdg_vs", {}) or {}
    assert mdg_vs.get("archer_unit") == 5 * P
    assert mdg_vs.get("building") == 2 * P


def test_elite_ghulam_stats_and_cost(aoe2_rules):
    assert _attr(aoe2_rules, "elite_ghulam", "hp_max") == 70 * P
    assert _attr(aoe2_rules, "elite_ghulam", "mdg") == 11 * P
    assert _attr(aoe2_rules, "elite_ghulam", "rdf") == 6 * P
    cost = list(_attr(aoe2_rules, "elite_ghulam", "cost", ()) or ())
    assert cost[0] == 575 * P  # gold
    assert cost[2] == 950 * P  # food
    assert _attr(aoe2_rules, "elite_ghulam", "time_cost") == 45 * P


# --------------------------------------------------------------------------
# Global invariant: every unique unit is reachable
# --------------------------------------------------------------------------


def test_every_unique_unit_is_trainable_or_a_line_upgrade(aoe2_rules):
    """No unique unit may be defined but unreachable from any civ building.

    A unique unit is legitimate when it is a *line upgrade* research (the
    Roman Legionary is researched at the Barracks, not trained), so those
    are allowed as long as a civ building lists them in ``can_research``.
    """
    raw = aoe2_rules._dict
    uu = [
        name for name, obj in raw.items()
        if "unique_unit" in (obj.get("is_a") or [])
    ]
    assert uu, "no unique units found -- the rules did not load"

    trainable = set()
    researchable = set()
    for name, obj in raw.items():
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
        name for name in uu
        if name not in trainable and name not in researchable
    ]
    assert not unreachable, "unique units unreachable: %s" % unreachable
