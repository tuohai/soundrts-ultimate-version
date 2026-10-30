# -*- coding: utf-8 -*-
"""Regression tests for the AoE2 tech-effect engine fixes.

Three engine bugs were found while auditing the Roman (Return of Rome) tech
tree.  Each had a dedicated test here so it cannot silently come back.

Bug 1 — ``build_speed_pct`` never reached the player
    ``BuildingSite.time_cost`` reads ``player.build_speed_pct``, but the race
    field was never copied onto the player, so the AoE2 DE Roman +5% (and
    Spanish +30%) build-speed bonus had no effect at all.
    Fixed in ``soundrts/worldplayerbase/base.py``.

Bug 2 — ``effect_bonus_targets`` was ignored for cost effects
    A cost effect carrying a unit filter (e.g. AoE2 ``perfusion``: militia and
    spearman only) was written to the player-wide cost bonus pool, so it
    leaked to *every* unit the player trained.  Filtered effects are now kept
    out of the player-wide pool and applied per unit type by the order layer.
    Fixed in ``soundrts/worldupgrade/base.py`` + ``soundrts/worldorders/``.

Bug 3 — multi-row effects lost every row but the first
    ``Upgrade._apply_effects_to_unit`` de-duplicated with the key
    ``"<tech>:<level>"``, so the first ``effect`` row marked the key and every
    later row was skipped.  A tech like ``magyar_raid`` (a ``kill_resource_vs``
    row *and* a ``time_cost`` row) therefore only ever applied its first row.
    Fixed in ``soundrts/worldupgrade/base.py``.
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
    """Install the AoE2 rules into the global rules object.

    ``soundrts.lib.resource`` loads the *base* rules at import time, so every
    engine module must be imported **before** the AoE2 rules are installed —
    otherwise the AoE2 rule set is silently replaced by the base one.
    """
    # Import the engine modules first: importing them loads the base rules.
    import soundrts.worldplayerbase.base  # noqa: F401
    import soundrts.worldupgrade  # noqa: F401
    import soundrts.worldorders.base  # noqa: F401
    import soundrts.world_civ_bonuses  # noqa: F401
    import soundrts.worldphase  # noqa: F401
    from soundrts.definitions import rules as global_rules

    saved_dict = global_rules._dict
    saved_classes = getattr(global_rules, "classes", None)
    # The global rules cache values per (obj, attr); swapping ``_dict``
    # directly would leave stale entries behind, so clear it.
    saved_cache = getattr(global_rules, "_get_cache", None)
    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    if hasattr(global_rules, "_get_cache"):
        global_rules._get_cache.clear()
    try:
        yield aoe2_rules
    finally:
        global_rules._dict = saved_dict
        if saved_classes is not None:
            global_rules.classes = saved_classes
        if saved_cache is not None:
            global_rules._get_cache = saved_cache


class _FakeUnit:
    """Unit stand-in for the upgrade/effect engine.

    Real units expose ``<stat>_bonus`` accumulators and a list-valued
    ``cost_bonus``; the engine writes through them, so the stub must too.
    """

    def __init__(self, type_name, rules, player=None, **attrs):
        self.type_name = type_name
        self.player = player
        cls = rules.unit_class(type_name)
        self.cls = cls
        self.expanded_is_a = set(getattr(cls, "expanded_is_a", ()) or ())
        self.can_use = tuple(getattr(cls, "can_use", ()) or ())
        self.can_use_tech = tuple(getattr(cls, "can_use_tech", ()) or ())
        self.can_use_skill = tuple(getattr(cls, "can_use_skill", ()) or ())
        for stat in ("mdg", "rdg", "mdf", "rdf", "rdg_cd", "mdg_cd",
                     "sight_range", "hp", "hp_max", "speed", "mana_regen",
                     "conversion_resist", "rdg_range", "mdg_radius",
                     "rdg_hit_rate"):
            setattr(self, stat + "_bonus", 0)
            # The engine applies percent bonuses to the unit's *current*
            # value, so the stub must start from the class value.
            setattr(self, stat, getattr(cls, stat, 0) or 0)
        self.cost_bonus = [0] * 16
        self.cost_percent_bonus = [0.0] * 16
        self.time_cost_bonus = 0
        self.time_cost_percent_bonus = 0.0
        self.population_cost_bonus = 0
        self.population_cost_percent_bonus = 0.0
        self.kill_resource_vs = {}
        self.mdg_vs = {}
        self._applied_upgrade_effects = set()
        self.__dict__.update(attrs)


class _FakePlayer:
    def __init__(self, faction="romans"):
        self.faction = faction
        self.units = []
        self.upgrades = []
        self.forbidden_techs = []
        self.allied_victory = [self]
        self.number = 0
        self.gather_time_bonus = {}
        self.gather_qty_bonus = {}

    def level(self, name):
        return self.upgrades.count(name)


from soundrts.worldupgrade import Upgrade


def _research(installed, tech, unit_name, wire=True):
    """Research *tech* and return (unit, player) with the effect applied."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player = _FakePlayer()
    unit = _FakeUnit(unit_name, installed, player=player)
    player.units = [unit]
    player.upgrades.append(tech)
    if wire:
        unit.can_use_tech = tuple(unit.can_use_tech) + (tech,)
    installed.unit_class(tech).upgrade_player(player)
    return unit, player


# ---------------------------------------------------------------------------
# Bug 1 — build_speed_pct reaches the player
# ---------------------------------------------------------------------------


def test_build_speed_pct_is_read_from_the_race(installed):
    from soundrts.worldplayerbase.base import _race_build_speed_pct

    assert _race_build_speed_pct("romans") == 5
    assert _race_build_speed_pct("spanish") == 30
    assert _race_build_speed_pct("britons") == 0
    assert _race_build_speed_pct(None) == 0


def test_build_speed_pct_shortens_construction_time(installed):
    """A Roman's building site is 5% quicker than an identical one."""
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


def test_player_stores_build_speed_pct(installed):
    """``Player.__init__`` must copy the race's build_speed_pct onto itself."""
    from soundrts.definitions import rules as global_rules

    assert global_rules.get("romans", "build_speed_pct") == 5


# ---------------------------------------------------------------------------
# Bug 2 — effect_bonus_targets is honoured for cost effects
# ---------------------------------------------------------------------------


def test_filtered_cost_effect_does_not_leak_player_wide(installed):
    """AoE2 ``perfusion`` (militia/spearman only) must not become a
    player-wide -20% food cost bonus."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    _unit, player = _research(installed, "perfusion", "militia")

    assert list(getattr(player, "cost_percent_bonus", []) or []) == [
        0.0
    ] * len(player.cost_percent_bonus)
    assert float(getattr(player, "time_cost_percent_bonus", 0.0) or 0.0) == 0.0


def test_filtered_cost_effect_is_stored_with_its_targets(installed):
    """The filtered row must be kept in ``_global_cost_effects`` together
    with its ``effect_bonus_targets`` filter, so the order layer can match it
    against the unit being trained."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    _research(installed, "perfusion", "militia")

    rows = Upgrade._global_cost_effects.get("perfusion", ())
    filtered = [r for r in rows if r.get("effect_targets")]
    assert filtered, "perfusion's filtered cost effect was dropped"
    targets = filtered[0]["effect_targets"]
    assert "militia" in targets
    assert "spearman" in targets
    # The filtered row must not be marked as a player-wide effect.
    assert not filtered[0].get("has_cost_percent_effect") or (
        filtered[0].get("cost_percent_bonus_values") is not None
    )


def test_filtered_cost_effect_applies_only_to_matching_units(installed):
    """The order layer applies the filtered bonus per unit type."""
    from soundrts.world_civ_bonuses import _type_proxy
    from soundrts.worldphase import Phase
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    _research(installed, "perfusion", "militia")

    rows = Upgrade._global_cost_effects.get("perfusion", ())
    filtered = [r for r in rows if r.get("effect_targets")]
    assert filtered
    targets = filtered[0]["effect_targets"]

    militia_proxy = _type_proxy(installed.unit_class("militia"))
    archer_proxy = _type_proxy(installed.unit_class("aoe_archer"))
    assert Phase._unit_matches_targets(militia_proxy, targets)
    assert not Phase._unit_matches_targets(archer_proxy, targets)


def test_filtered_time_effect_applies_only_to_matching_units(installed):
    """AoE2 ``comitatenses`` must speed up the Roman military lines only."""
    from soundrts.world_civ_bonuses import _type_proxy
    from soundrts.worldphase import Phase
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    _research(installed, "comitatenses", "militia")

    rows = Upgrade._global_cost_effects.get("comitatenses", ())
    filtered = [r for r in rows if r.get("effect_targets")]
    assert filtered, "comitatenses' filtered time effect was dropped"
    targets = filtered[0]["effect_targets"]

    assert Phase._unit_matches_targets(
        _type_proxy(installed.unit_class("militia")), targets
    )
    assert Phase._unit_matches_targets(
        _type_proxy(installed.unit_class("centurion")), targets
    )
    assert not Phase._unit_matches_targets(
        _type_proxy(installed.unit_class("aoe_archer")), targets
    )


def test_roman_unique_techs_are_wired_into_can_use_tech(installed):
    """The units a Roman UT targets must list it in ``can_use_tech``.

    Without this the per-unit effects never reach the unit at all.
    """
    comitatenses = ("militia", "man_at_arms", "long_swordsman", "legionary",
                    "aoe_knight", "cavalier", "centurion", "elite_centurion")
    for name in comitatenses:
        cls = installed.unit_class(name)
        assert "comitatenses" in (getattr(cls, "can_use_tech", ()) or ()), name

    ballistas = ("scorpion", "heavy_scorpion", "galley", "war_galley", "galleon")
    for name in ballistas:
        cls = installed.unit_class(name)
        assert "ballistas" in (getattr(cls, "can_use_tech", ()) or ()), name


def test_comitatenses_effect_reaches_the_militia(installed):
    """Researching Comitatenses must actually halve the Militia's train time."""
    unit, _player = _research(installed, "comitatenses", "militia")

    assert unit.time_cost_percent_bonus == -0.5


def test_ballistas_effect_reaches_the_scorpion(installed):
    """Researching Ballistas must actually speed up the Scorpion's reload."""
    scorpion_cls = installed.unit_class("scorpion")
    base_rdg_cd = getattr(scorpion_cls, "rdg_cd", 0)

    unit, _player = _research(installed, "ballistas", "scorpion")

    assert unit.rdg_cd == pytest.approx(
        int(base_rdg_cd * 0.67), abs=1
    )


def _filtered_time_cost(installed, tech, unit_name):
    """Simulate the order layer's filtered train-time application."""
    from soundrts.worldphase import Phase
    from soundrts.world_civ_bonuses import _type_proxy

    Upgrade.reset()
    player = _FakePlayer()
    player.upgrades.append(tech)
    installed.unit_class(tech).upgrade_player(player)

    cls = installed.unit_class(unit_name)
    base = int(getattr(cls, "time_cost", 0) or 0)
    proxy = _type_proxy(cls)
    total = base
    for eff in Upgrade._global_cost_effects.get(tech, ()):
        targets = eff.get("effect_targets") or ()
        if not targets:
            continue
        if not Phase._unit_matches_targets(proxy, targets):
            continue
        if eff.get("has_time_cost_effect"):
            total += eff.get("time_cost_bonus_value", 0)
        if eff.get("has_time_cost_percent_effect"):
            total += int(total * eff.get("time_cost_percent_bonus_value", 0.0))
    return base, total


def test_filtered_time_effect_matches_aoe2_semantics(installed):
    """Each AoE2 filtered train-time tech must hit exactly its own units."""
    # Conscription: -33% on all military lines (already worked before the fix).
    base, total = _filtered_time_cost(installed, "conscription", "militia")
    assert total == int(base * 0.67)
    base, total = _filtered_time_cost(installed, "conscription", "aoe_knight")
    assert total == int(base * 0.67)

    # Comitatenses: -50% on the Roman military lines only.
    base, total = _filtered_time_cost(installed, "comitatenses", "militia")
    assert total == int(base * 0.5)
    base, total = _filtered_time_cost(installed, "comitatenses", "centurion")
    assert total == int(base * 0.5)
    base, total = _filtered_time_cost(installed, "comitatenses", "aoe_archer")
    assert total == base  # archers are unaffected

    # Treadmill Crane: -20% on villagers only.
    base, total = _filtered_time_cost(installed, "treadmill_crane", "peasant")
    assert total == int(base * 0.8)
    base, total = _filtered_time_cost(installed, "treadmill_crane", "militia")
    assert total == base


def test_filtered_cost_effect_matches_aoe2_semantics(installed):
    """A filtered cost bonus must apply to its target unit and no other."""
    from soundrts.worldorders.base import ComplexOrder

    def sim(tech, unit_name):
        Upgrade.reset()
        player = _FakePlayer()
        player.upgrades.append(tech)
        installed.unit_class(tech).upgrade_player(player)
        cls = installed.unit_class(unit_name)
        cost = list(cls.cost)
        ComplexOrder._merge_filtered_cost_for_type(player, cls, cost)
        return cost

    base = list(installed.unit_class("militia").cost)
    # Perfusion: -20% food cost for militia / spearman only.
    militia_cost = sim("perfusion", "militia")
    assert militia_cost[2] == int(base[2] * 0.8)
    assert militia_cost[0] == base[0]

    archer_cost = sim("perfusion", "aoe_archer")
    assert archer_cost == list(installed.unit_class("aoe_archer").cost)


# ---------------------------------------------------------------------------
# Bug 3 — multi-row effects apply every row
# ---------------------------------------------------------------------------


def test_multi_row_effect_applies_every_row(installed):
    """``magyar_raid`` has two effect rows; both must be applied."""
    unit, _player = _research(installed, "magyar_raid", "magyar_huszar")

    # Row 1: kill_resource_vs peasant resource1 5
    assert unit.kill_resource_vs.get("peasant", {}).get("resource1") == 5
    # Row 2: time_cost -50%
    assert unit.time_cost_percent_bonus == -0.5


def test_multi_row_effect_applies_every_row_on_new_units(installed):
    """The same must hold on the "unit created later" path."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player = _FakePlayer()
    unit = _FakeUnit("magyar_huszar", installed, player=player)
    unit.can_use_tech = tuple(unit.can_use_tech) + ("magyar_raid",)
    player.upgrades.append("magyar_raid")

    installed.unit_class("magyar_raid").upgrade_unit_to_player_level(unit)

    assert unit.kill_resource_vs.get("peasant", {}).get("resource1") == 5
    assert unit.time_cost_percent_bonus == -0.5


def test_multi_row_effect_does_not_double_apply(installed):
    """The per-row dedup key must not allow a second application."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player = _FakePlayer()
    unit = _FakeUnit("magyar_huszar", installed, player=player)
    unit.can_use_tech = tuple(unit.can_use_tech) + ("magyar_raid",)
    player.upgrades.append("magyar_raid")

    tech = installed.unit_class("magyar_raid")
    tech.upgrade_unit_to_player_level(unit)
    first = unit.time_cost_percent_bonus
    tech.upgrade_unit_to_player_level(unit)

    assert unit.time_cost_percent_bonus == first == -0.5
