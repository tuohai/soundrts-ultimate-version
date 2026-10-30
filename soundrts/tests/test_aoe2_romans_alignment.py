# -*- coding: utf-8 -*-
"""Roman (Return of Rome / AoE2 DE) alignment tests for the AoE2 mod.

Covers:
  * Roman barracks tech tree (no Two-Handed Swordsman / Champion, Halberdier
    present, Legionary replaces 2HS/Champion).
  * Roman archery range / stable / workshop / blacksmith tech trees.
  * Roman Castle: Centurion + Elite Centurion (line upgrade), Ballistas /
    Comitatenses unique techs.
  * Unit stats (DE values) for Legionary / Centurion / Elite Centurion.
  * Civ bonuses: build speed, gather time, infantry armor, Scorpion -50%
    gold, galley armor, team scorpion min range.

NOTE: rules values are stored PRECISION-scaled (x1000) by the engine, e.g.
``hp_max 75`` -> 75000, ``speed 0.96`` -> 960.
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
    """Raw rules value (PRECISION-scaled where applicable)."""
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


def _race(aoe2_rules, faction="romans"):
    race = aoe2_rules._dict.get(faction) or {}
    assert race, "missing race %r" % faction
    return race


# --------------------------------------------------------------------------
# Roman race table
# --------------------------------------------------------------------------


def test_roman_race_points_at_roman_buildings(aoe2_rules):
    race = _race(aoe2_rules)
    assert race["peasant"] == ["roman_villager"]
    assert race["barracks"] == ["roman_barracks"]
    assert race["archery_range"] == ["roman_archery"]
    assert race["stables"] == ["roman_stable"]
    assert race["aoe_castle"] == ["roman_castle"]
    assert race["workshop"] == ["roman_workshop"]
    assert race["blacksmith"] == ["roman_blacksmith"]
    assert race["university"] == ["roman_university"]
    assert race["shipyard"] == ["roman_shipyard"]


# --------------------------------------------------------------------------
# Barracks: the Legionary replaces Two-Handed Swordsman / Champion
# --------------------------------------------------------------------------


def test_roman_barracks_trains_militia_and_spearman(aoe2_rules):
    trains = _can_train(aoe2_rules, "roman_barracks")
    assert "militia" in trains
    assert "spearman" in trains


def test_roman_barracks_has_no_two_handed_swordsman_or_champion(aoe2_rules):
    """DE: the Legionary replaces 2HS/Champion for the Romans."""
    researches = _can_research(aoe2_rules, "roman_barracks")
    assert "two_handed_swordsman" not in researches
    assert "champion" not in researches
    assert "legionary" in researches


def test_roman_barracks_has_halberdier_and_pikeman(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_barracks")
    assert "pikeman" in researches
    assert "halberdier" in researches


def test_roman_barracks_lost_arson_gambesons_and_supplies(aoe2_rules):
    """DE update 83607: Romans lost Arson; no Gambesons / Supplies either."""
    researches = _can_research(aoe2_rules, "roman_barracks")
    for tech in ("arson", "gambesons", "supplies"):
        assert tech not in researches, tech


def test_roman_barracks_has_no_battle_axe_or_masonry_upgrades(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_barracks")
    assert "battle_axe" not in researches
    assert "masonry" not in researches
    assert "architecture" not in researches


def test_sword_line_upgrades_to_legionary(aoe2_rules):
    """Long Swordsman upgrades into the Legionary."""
    ups = set(_attr(aoe2_rules, "long_swordsman", "can_upgrade_to", ()) or ())
    assert "legionary" in ups


# --------------------------------------------------------------------------
# Legionary definition (DE values)
# --------------------------------------------------------------------------


def test_legionary_stats(aoe2_rules):
    assert _attr(aoe2_rules, "legionary", "hp_max") == 75 * P
    assert _attr(aoe2_rules, "legionary", "mdg") == 12 * P
    assert _attr(aoe2_rules, "legionary", "mdf") == 2 * P
    assert _attr(aoe2_rules, "legionary", "rdf") == 2 * P
    assert _attr(aoe2_rules, "legionary", "sight_range") == 5 * P
    assert _attr(aoe2_rules, "legionary", "speed") == 0.96 * P
    assert _attr(aoe2_rules, "legionary", "population_cost") == 1


def test_legionary_is_an_imperial_line_upgrade(aoe2_rules):
    assert _attr(aoe2_rules, "legionary", "line_upgrade") == 1
    assert _attr(aoe2_rules, "legionary", "no_auto_upgrade") == 1
    assert "imperial_age" in (_attr(aoe2_rules, "legionary", "requirements", ()) or ())


def test_legionary_research_cost_is_400_gold_800_food(aoe2_rules):
    cost = list(_attr(aoe2_rules, "legionary", "cost", ()) or ())
    assert cost[0] == 400 * P  # gold
    assert cost[2] == 800 * P  # food
    assert cost[1] == 0 and cost[3] == 0
    assert _attr(aoe2_rules, "legionary", "time_cost") == 100 * P


def test_legionary_bonus_damage(aoe2_rules):
    mdg_vs = _attr(aoe2_rules, "legionary", "mdg_vs", {}) or {}
    assert mdg_vs.get("infantry") == 4 * P
    assert mdg_vs.get("building") == 4 * P


def test_legionary_trains_at_the_sword_line_price(installed):
    from soundrts.world_build_rules import unit_train_cost, unit_train_time

    cost = list(unit_train_cost("legionary"))
    assert cost[0] == 20 * P  # gold
    assert cost[2] == 50 * P  # food
    # train time follows the sword-line root (militia = 21s)
    assert unit_train_time("legionary") == 21 * P


def test_legionary_has_no_elite_version(aoe2_rules):
    """DE: the Legionary has no Elite upgrade."""
    assert aoe2_rules.unit_class("elite_legionary") is None
    assert not (_attr(aoe2_rules, "legionary", "can_upgrade_to", ()) or ())


# --------------------------------------------------------------------------
# Castle: Centurion line + Ballistas / Comitatenses
# --------------------------------------------------------------------------


def test_roman_castle_trains_centurion_and_trebuchet(aoe2_rules):
    trains = _can_train(aoe2_rules, "roman_castle")
    assert "centurion" in trains
    assert "trebuchet" in trains
    assert "legionary" not in trains


def test_roman_castle_researches_elite_centurion_and_unique_techs(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_castle")
    assert "elite_centurion" in researches
    assert "ballistas" in researches
    assert "comitatenses" in researches
    assert "conscription" in researches
    assert "sappers" in researches
    assert "spies" in researches


def test_roman_castle_has_no_hoardings(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_castle")
    assert "hoardings" not in researches


def test_centurion_stats(aoe2_rules):
    assert _attr(aoe2_rules, "centurion", "hp_max") == 110 * P
    assert _attr(aoe2_rules, "centurion", "mdg") == 13 * P
    assert _attr(aoe2_rules, "centurion", "mdf") == 2 * P
    assert _attr(aoe2_rules, "centurion", "rdf") == 3 * P
    assert _attr(aoe2_rules, "centurion", "speed") == 1.35 * P
    assert _attr(aoe2_rules, "centurion", "sight_range") == 4 * P
    assert _attr(aoe2_rules, "centurion", "population_cost") == 2
    assert "castle_age" in (_attr(aoe2_rules, "centurion", "requirements", ()) or ())


def test_elite_centurion_stats(aoe2_rules):
    assert _attr(aoe2_rules, "elite_centurion", "hp_max") == 155 * P
    assert _attr(aoe2_rules, "elite_centurion", "mdg") == 15 * P
    assert _attr(aoe2_rules, "elite_centurion", "mdf") == 3 * P
    assert _attr(aoe2_rules, "elite_centurion", "rdf") == 3 * P
    assert _attr(aoe2_rules, "elite_centurion", "sight_range") == 5 * P
    assert _attr(aoe2_rules, "elite_centurion", "line_upgrade") == 1
    assert _attr(aoe2_rules, "elite_centurion", "no_auto_upgrade") == 1
    assert "imperial_age" in (
        _attr(aoe2_rules, "elite_centurion", "requirements", ()) or ()
    )


def test_centurion_upgrades_to_elite_centurion(aoe2_rules):
    ups = set(_attr(aoe2_rules, "centurion", "can_upgrade_to", ()) or ())
    assert "elite_centurion" in ups


def test_elite_centurion_research_cost(aoe2_rules):
    cost = list(_attr(aoe2_rules, "elite_centurion", "cost", ()) or ())
    assert cost[0] == 900 * P  # gold
    assert cost[2] == 1100 * P  # food
    assert _attr(aoe2_rules, "elite_centurion", "time_cost") == 60 * P


def test_centurion_trains_at_85_gold_75_food(installed):
    from soundrts.world_build_rules import unit_train_cost, unit_train_time

    cost = list(unit_train_cost("centurion"))
    assert cost[0] == 85 * P
    assert cost[2] == 75 * P
    assert unit_train_time("centurion") == 24 * P


# --------------------------------------------------------------------------
# Unique techs
# --------------------------------------------------------------------------


def test_ballistas_is_a_castle_unique_tech(aoe2_rules):
    assert _attr(aoe2_rules, "ballistas", "time_cost") == 45 * P
    reqs = _attr(aoe2_rules, "ballistas", "requirements", ()) or ()
    assert "aoe_castle" in reqs
    assert "castle_age" in reqs
    cost = list(_attr(aoe2_rules, "ballistas", "cost", ()) or ())
    assert cost[0] == 300 * P
    assert cost[1] == 400 * P


def test_comitatenses_is_a_castle_unique_tech(aoe2_rules):
    assert _attr(aoe2_rules, "comitatenses", "time_cost") == 60 * P
    reqs = _attr(aoe2_rules, "comitatenses", "requirements", ()) or ()
    assert "aoe_castle" in reqs
    assert "imperial_age" in reqs
    cost = list(_attr(aoe2_rules, "comitatenses", "cost", ()) or ())
    assert cost[0] == 800 * P
    assert cost[2] == 700 * P


def test_comitatenses_covers_the_roman_military_lines(aoe2_rules):
    effect = str(_attr(aoe2_rules, "comitatenses", "effect", "") or "")
    for target in ("militia", "man_at_arms", "long_swordsman", "legionary",
                   "aoe_knight", "cavalier", "centurion", "elite_centurion"):
        assert target in effect, target


# --------------------------------------------------------------------------
# Other Roman buildings (DE tech tree)
# --------------------------------------------------------------------------


def test_roman_archery_range_tech_tree(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_archery")
    assert "crossbowman" in researches
    assert "arbalester" not in researches
    assert "elite_skirmisher" in researches
    assert "heavy_cavalry_archer" in researches
    trains = _can_train(aoe2_rules, "roman_archery")
    assert "aoe_archer" in trains
    assert "skirmisher" in trains
    assert "hand_cannoneer" not in trains


def test_roman_stable_has_no_hussar_or_paladin(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_stable")
    assert "hussar" not in researches
    assert "paladin" not in researches
    assert "light_cavalry" in researches
    assert "cavalier" in researches


def test_roman_workshop_has_no_onager_or_bombard(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_workshop")
    for tech in ("onager", "siege_onager", "bombard", "bombard_cannon"):
        assert tech not in researches, tech
    trains = _can_train(aoe2_rules, "roman_workshop")
    assert "scorpion" in trains
    assert "mangonel" in trains
    assert "battering_ram" in trains


def test_roman_blacksmith_has_no_plate_mail_or_plate_barding(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_blacksmith")
    assert "plate_mail_armor" not in researches
    assert "plate_barding_armor" not in researches
    assert "scale_mail_armor" in researches
    assert "chain_mail_armor" in researches
    assert "iron_casting" in researches
    assert "blast_furnace" in researches


def test_roman_university_has_no_bombard_tower(aoe2_rules):
    researches = _can_research(aoe2_rules, "roman_university")
    assert "cannontower" not in researches
    assert "ballistics" in researches
    assert "chemistry" in researches


# --------------------------------------------------------------------------
# Civ bonuses
# --------------------------------------------------------------------------


def _on_phase(aoe2_rules, faction="romans", key="on_phase_effects"):
    raw = _race(aoe2_rules, faction).get(key) or []
    return [list(e) for e in raw]


def test_roman_build_speed_bonus(aoe2_rules):
    assert _race(aoe2_rules).get("build_speed_pct") == 5


def test_roman_build_speed_bonus_reaches_the_player(installed):
    """Regression: ``build_speed_pct`` must be copied onto the player.

    ``Building.time_cost`` reads ``player.build_speed_pct``; the race field was
    never transferred, so the Roman +5% (and Spanish +30%) had no effect.
    """
    from soundrts.worldplayerbase.base import _race_build_speed_pct

    assert _race_build_speed_pct("romans") == 5
    assert _race_build_speed_pct("spanish") == 30
    assert _race_build_speed_pct("britons") == 0
    assert _race_build_speed_pct(None) == 0


def test_roman_build_speed_pct_shortens_construction_time(installed):
    """A Roman's building is 5% cheaper in time than an identical one.

    ``BuildingSite.time_cost`` is what drives the construction timer, so that
    is the property the race bonus has to reach.
    """
    from soundrts.worldunit.worldcreature import BuildingSite

    roman = SimpleNamespace(build_speed_pct=5, ai_build_time_percent=100)
    plain = SimpleNamespace(build_speed_pct=0, ai_build_time_percent=100)

    site_roman = BuildingSite.__new__(BuildingSite)
    site_plain = BuildingSite.__new__(BuildingSite)
    site_roman.player = roman
    site_plain.player = plain
    site_roman.type = SimpleNamespace(time_cost=100 * P)
    site_plain.type = SimpleNamespace(time_cost=100 * P)

    assert site_plain.time_cost == 100 * P
    assert site_roman.time_cost == int(100 * P * 95 // 100)
    assert site_roman.time_cost < site_plain.time_cost


def test_roman_gather_time_bonus_is_faster(aoe2_rules):
    rows = _on_phase(aoe2_rules)
    found = False
    for row in rows:
        if "gather_time" in row and "-5%" in row:
            for target in ("food", "wood", "gold", "stone"):
                assert target in row
            found = True
    assert found, rows


def test_roman_infantry_gets_double_blacksmith_armor(aoe2_rules):
    """DE: Roman infantry receives double effect from Blacksmith armor upgrades."""
    rows = _on_phase(aoe2_rules)
    mdf_rows = [r for r in rows if "mdf" in r and "infantry" in r]
    rdf_rows = [r for r in rows if "rdf" in r and "infantry" in r]
    assert mdf_rows and rdf_rows
    assert mdf_rows[0][mdf_rows[0].index("mdf") + 1] == 1 * P
    assert rdf_rows[0][rdf_rows[0].index("rdf") + 1] == 1 * P


def test_roman_scorpion_costs_50_percent_less_gold(aoe2_rules):
    """DE: Scorpions cost -50% gold (resource slot 0)."""
    rows = _on_phase(aoe2_rules)
    scorpion_rows = [r for r in rows if "scorpion" in r and "cost" in r]
    assert scorpion_rows
    row = scorpion_rows[0]
    values = row[row.index("cost") + 1:]
    # A percent slot must be first (gold) and the rest must be 0.
    assert values[0] == "-50%"
    assert all(v == "0" for v in values[1:4])


def test_roman_galley_line_gets_extra_armor(aoe2_rules):
    rows = _on_phase(aoe2_rules)
    galley_rows = [
        r for r in rows
        if "galley" in r and ("mdf" in r or "rdf" in r)
    ]
    assert galley_rows
    for row in galley_rows:
        for target in ("galley", "war_galley", "galleon"):
            assert target in row


def test_roman_team_bonus_reduces_scorpion_min_range(aoe2_rules):
    rows = _on_phase(aoe2_rules, key="team_on_phase_effects")
    found = [
        r for r in rows
        if "scorpion" in r and "rdg_minimal_range" in r
    ]
    assert found
    value = found[0][found[0].index("rdg_minimal_range") + 1]
    assert value == -1 * P


# --------------------------------------------------------------------------
# Engine-level: the Roman castle train menu
# --------------------------------------------------------------------------


def test_roman_castle_train_menu_exposes_centurion(installed):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train
    from soundrts.worldplayerbase.base import Player

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = SimpleNamespace(
        faction="romans",
        upgrades=[],
        _can_train_overrides_by_type=None,
    )
    player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)

    castle_cls = installed.unit_class("roman_castle")
    unit = SimpleNamespace(
        player=player, type=castle_cls, type_name="roman_castle",
        attached_addons=[],
    )
    trains = effective_can_train(unit)
    assert "centurion" in trains
    assert "trebuchet" in trains


# --------------------------------------------------------------------------
# Runtime behaviour (engine paths, not just rules text)
# --------------------------------------------------------------------------


class _FakeUnit:
    """Minimal unit stand-in that the effect/upgrade engine can operate on.

    Real game units expose ``<stat>_bonus`` attributes; the engine's
    ``_apply_attribute_bonus`` only writes through them, so the stub must
    declare them too.  ``expanded_is_a`` is taken from the real rules class so
    category targets such as ``infantry`` match exactly as they do in game.
    """

    def __init__(self, type_name, player=None, rules=None, **attrs):
        self.type_name = type_name
        self.player = player
        expanded = set()
        if rules is not None:
            cls = rules.unit_class(type_name)
            if cls is not None:
                expanded = set(getattr(cls, "expanded_is_a", ()) or ())
        self.expanded_is_a = expanded
        self.can_upgrade_to = ()
        # Engine-side bonus accumulators (real units have these).
        for stat in ("mdf", "rdf", "mdg", "rdg", "rdg_cd", "mdg_cd",
                     "sight_range", "hp", "hp_max", "speed"):
            setattr(self, stat + "_bonus", 0)
        self.mdf_bonus = 0
        self.rdf_bonus = 0
        self.time_cost_bonus = 0
        self.time_cost_percent_bonus = 0.0
        self.__dict__.update(attrs)


def _roman_player(installed, units=()):
    from soundrts.definitions import rules as global_rules

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = SimpleNamespace(
        faction="romans",
        units=list(units),
        upgrades=[],
        _phase_bonus_pool=[],
        allied_victory=[],
        forbidden_techs=[],
        research_time_percent_bonus=0.0,
    )
    player.allied_victory = [player]
    return player


def test_roman_infantry_armor_bonus_applies_at_runtime(installed):
    """``on_phase dark_age mdf 1 infantry`` must actually raise infantry armor."""
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _roman_player(installed)
    infantry = _FakeUnit(
        "legionary", player=player, rules=installed,
        mdf=2 * P, rdf=2 * P, hp_max=75 * P, hp=75 * P,
    )
    player.units = [infantry]
    apply_faction_on_phase_effects(player, "dark_age")
    assert infantry.mdf == 3 * P
    assert infantry.rdf == 3 * P


def test_roman_infantry_armor_bonus_skips_non_infantry(installed):
    """A cavalry unit must not receive the infantry armor bonus."""
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _roman_player(installed)
    cavalry = _FakeUnit(
        "centurion", player=player, rules=installed, mdf=2 * P, rdf=3 * P,
    )
    player.units = [cavalry]
    apply_faction_on_phase_effects(player, "dark_age")
    assert cavalry.mdf == 2 * P
    assert cavalry.rdf == 3 * P


def test_roman_galley_armor_bonus_only_hits_galley_line(installed):
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _roman_player(installed)
    galley = _FakeUnit("galley", player=player, rules=installed, mdf=0, rdf=0)
    other = _FakeUnit(
        "fishing_ship", player=player, rules=installed, mdf=0, rdf=0
    )
    player.units = [galley, other]
    apply_faction_on_phase_effects(player, "dark_age")
    assert galley.mdf == 1 * P
    assert galley.rdf == 1 * P
    assert other.mdf == 0
    assert other.rdf == 0


def test_roman_scorpion_cost_bonus_applies_to_scorpion_only(installed):
    """Scorpions cost -50% gold; other siege keeps its price."""
    from soundrts.world_civ_bonuses import merge_pool_cost_for_type
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _roman_player(installed)
    apply_faction_on_phase_effects(player, "dark_age")

    scorpion_cls = installed.unit_class("scorpion")
    base_scorpion_cost = list(installed.get("scorpion", "cost"))
    scorpion_cost = list(base_scorpion_cost)
    merge_pool_cost_for_type(player, scorpion_cls, scorpion_cost)
    # -50% on the gold slot only; the other slots stay untouched.
    assert scorpion_cost[0] == int(base_scorpion_cost[0] * 0.5)
    assert scorpion_cost[1:] == base_scorpion_cost[1:]

    mangonel_cls = installed.unit_class("mangonel")
    base_mangonel_cost = list(installed.get("mangonel", "cost"))
    mangonel_cost = list(base_mangonel_cost)
    merge_pool_cost_for_type(player, mangonel_cls, mangonel_cost)
    assert mangonel_cost == base_mangonel_cost


def test_roman_team_bonus_reduces_scorpion_min_range_at_runtime(installed):
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _roman_player(installed)
    scorpion = _FakeUnit(
        "scorpion", player=player, rules=installed, rdg_minimal_range=5 * P,
    )
    player.units = [scorpion]
    apply_faction_on_phase_effects(player, "dark_age")
    assert scorpion.rdg_minimal_range == 4 * P


def test_roman_line_upgrade_research_unlocks_and_morphs(installed):
    """Researching the Centurion upgrade morphs Centurions into Elites."""
    from soundrts.world_build_rules import apply_unit_line_upgrade

    player = _roman_player(installed)
    assert "elite_centurion" not in player.upgrades

    class _Morphable(_FakeUnit):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.morphed_to = None

    import soundrts.worldphase as worldphase

    original = worldphase.Phase._instant_morph

    def _fake_morph(unit, cls):
        unit.morphed_to = cls

    worldphase.Phase._instant_morph = staticmethod(_fake_morph)
    try:
        elite_cls = installed.unit_class("elite_centurion")
        cavalry = _Morphable(
            type_name="centurion", player=player, rules=installed
        )
        cavalry.can_upgrade_to = ("elite_centurion",)
        player.units = [cavalry]
        apply_unit_line_upgrade(player, "elite_centurion")
    finally:
        worldphase.Phase._instant_morph = original

    assert "elite_centurion" in player.upgrades
    assert cavalry.morphed_to is elite_cls


def test_legionary_line_upgrade_unlocks_only_for_roman(installed):
    """``legionary`` is a research, not a castle-trained unit."""
    from soundrts.world_build_rules import resolve_trainable_unit_type

    player = _roman_player(installed)
    player.has_all = lambda reqs: True
    player.upgrades = ["legionary"]

    # The barracks lists only militia / spearman; the Legionary appears via the
    # researched line upgrade on the sword line, not on the castle menu.
    assert resolve_trainable_unit_type(player, "long_swordsman") == "legionary"
    assert resolve_trainable_unit_type(player, "militia") == "militia"


def test_comitatenses_effect_bonus_applies_train_time(installed):
    """``effect bonus time_cost -50%`` on the Roman military lines.

    The engine stores percent train-time bonuses in
    ``unit.time_cost_percent_bonus`` (the order math applies it later).
    """
    from soundrts.worldupgrade import Upgrade

    militia = _FakeUnit(
        "militia", player=None, rules=installed, time_cost=21 * P,
    )
    Upgrade.effect_bonus(militia, 0, "time_cost", "-50%")
    assert militia.time_cost_percent_bonus == -0.5
    assert militia.time_cost == 21 * P


def test_ballistas_effect_targets_only_scorpion(installed):
    from soundrts.worldupgrade import Upgrade

    scorpion = _FakeUnit("scorpion", player=None, rules=installed, rdg_cd=2 * P)
    Upgrade.effect_bonus(scorpion, 0, "rdg_cd", "-33%")
    # 2.0s * (1 - 0.33) = 1.34s
    assert scorpion.rdg_cd == pytest.approx(int(2 * P * 0.67), abs=1)

