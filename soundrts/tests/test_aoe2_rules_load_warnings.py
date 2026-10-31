# -*- coding: utf-8 -*-
"""Regression tests for two rules.txt warnings raised by the AoE2 rules parser.

Both bugs were introduced together by commit ``cabdfdca`` ("define the missing
DE unique units and technologies") and both were silent at load time — the
parser only warned and then dropped the offending data.

Warning 1 — ``citadels`` (Persian unique technology)
    ``WARNING:root:in citadels: effect bonus does not accept unit filters
    (ignored: mdg_vs siege_ram capped_ram battering_ram3); put units on
    effect_bonus_targets``

    Two separate defects in one line:

    * ``effect bonus <stat> <target> <value>`` takes exactly ONE target per
      row.  ``mdg_vs siege_ram capped_ram battering_ram 3`` put three unit
      names on the row, so the parser could not tell where the bonus ended
      and dropped the whole row.
    * the castle attacks *ranged* (``rdg 11``), so a ``mdg`` / ``mdg_vs``
      (melee) row would never have fired even if it had parsed.  DE Citadels
      says "Castles +4 attack, +3 vs. Rams, +3 vs. Infantry".

Warning 2 — ``houfnice`` (Bohemian unique unit)
    ``WARNING:root:in houfnice: <class 'soundrts.worldunit.worldsoldier.Soldier'>
    doesn't have any attribute called 'train_time'``

    ``train_time`` was never registered as a rules property, so the parser
    dropped it — meaning the Houfnice trained at its ``time_cost`` (140s,
    the *research* duration) instead of the DE 56s train time.

Both warnings are asserted to be absent, so a regression re-introduces them
loudly.
"""
from __future__ import annotations

import logging
from pathlib import Path

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
def load_warnings():
    """Load the AoE2 rules and return every warning the loader emitted."""
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")

    records = []

    class _Collector(logging.Handler):
        def emit(self, record):
            records.append(record.getMessage())

    handler = _Collector()
    logger = logging.getLogger()
    old_level = logger.level
    logger.setLevel(logging.WARNING)
    logger.addHandler(handler)
    try:
        r = Rules()
        r.load(base, mod)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
    return records


# ---------------------------------------------------------------------------
# The warnings themselves
# ---------------------------------------------------------------------------


def test_no_rules_load_warnings(load_warnings):
    """The AoE2 rules must load without emitting a single warning.

    Both bugs reported by the user were silent data loss: the parser warned
    and then threw the data away, so the game kept running with the bonus /
    the train time quietly missing.
    """
    assert not load_warnings, "rules load emitted warnings:\n%s" % (
        "\n".join(load_warnings)
    )


def test_citadels_effect_bonus_has_no_unit_filters(load_warnings):
    """No ``effect bonus`` row may smuggle unit names onto the bonus line."""
    offenders = [w for w in load_warnings if "does not accept unit filters" in w]
    assert not offenders, "effect bonus rows still carry unit filters:\n%s" % (
        "\n".join(offenders)
    )


def test_no_unknown_attribute_warnings(load_warnings):
    """No rules property may reference an attribute the base class lacks."""
    offenders = [
        w for w in load_warnings
        if "doesn't have any attribute called" in w
    ]
    assert not offenders, "unknown attributes:\n%s" % "\n".join(offenders)


# ---------------------------------------------------------------------------
# Citadels — Persian unique technology
# ---------------------------------------------------------------------------


def test_citadels_uses_ranged_stats(aoe2_rules):
    """The castle attacks ranged, so Citadels must use ``rdg`` / ``rdg_vs``.

    A ``mdg`` / ``mdg_vs`` row is a no-op on a building whose only weapon is
    a ranged one (``aoe_castle`` has ``rdg 11`` and ``mdg 0``).
    """
    castle = aoe2_rules.unit_class("aoe_castle")
    assert getattr(castle, "mdg", 0) == 0
    assert getattr(castle, "rdg", 0) > 0

    raw = aoe2_rules._dict["citadels"]
    effect = raw.get("effect")
    assert effect, "citadels has no effect rows"
    rows = effect if isinstance(effect[0], list) else [effect]
    for row in rows:
        assert row[0] == "bonus"
        stats = {row[i] for i in range(1, len(row), 2) if isinstance(row[i], str)}
        melee = sorted(s for s in stats if s.startswith("mdg"))
        assert not melee, (
            "citadels declares a melee stat %s, but the castle attacks ranged"
            % melee
        )


def test_citadels_bonus_rows_have_a_single_target(aoe2_rules):
    """Each ``*_vs`` row must carry exactly one ``<target> <value>`` pair."""
    raw = aoe2_rules._dict["citadels"]
    effect = raw.get("effect")
    rows = effect if isinstance(effect[0], list) else [effect]
    for row in rows:
        i = 1
        while i < len(row):
            stat = row[i]
            if stat.endswith("_vs"):
                # stat, target, value -> exactly three tokens
                assert i + 2 < len(row), (
                    "citadels row %r has a truncated %s triple" % (row, stat)
                )
                value = row[i + 2]
                assert isinstance(value, (int, float)), (
                    "citadels row %r: %s value %r is not numeric"
                    % (row, stat, value)
                )
                i += 3
                continue
            i += 2


def test_citadels_applies_attack_bonuses_to_the_castle(installed):
    """Researching Citadels must raise the castle's ranged attack and armor."""
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player = _FakePlayer()
    castle = _FakeUnit("aoe_castle", installed, player=player)
    player.units = [castle]
    player.upgrades.append("citadels")
    castle.can_use_tech = tuple(castle.can_use_tech) + ("citadels",)

    installed.unit_class("citadels").upgrade_player(player)

    base_rdg = installed.unit_class("aoe_castle").rdg
    assert castle.rdg == base_rdg + 4 * P, (
        "Citadels must give the castle +4 ranged attack "
        "(DE: 'Castles +4 attack')"
    )
    # DE: "+3 vs. Rams, +3 vs. Infantry"
    assert castle.rdg_vs.get("battering_ram") == 3 * P
    assert castle.rdg_vs.get("infantry") == 3 * P
    # DE: "receive -25% bonus damage" -> +25% armor
    assert castle.mdf == installed.unit_class("aoe_castle").mdf * 1.25
    assert castle.rdf == installed.unit_class("aoe_castle").rdf * 1.25


def test_citadels_ram_bonus_covers_the_whole_ram_line(installed):
    """The "+3 vs. Rams" bonus must reach every tier of the ram line.

    The vs-lookup walks ``expanded_is_a``, so a single ``battering_ram`` key
    covers ``capped_ram`` and ``siege_ram`` too.
    """
    from soundrts.combat.damage_calculation import _vs_lookup
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player = _FakePlayer()
    castle = _FakeUnit("aoe_castle", installed, player=player)
    player.units = [castle]
    player.upgrades.append("citadels")
    castle.can_use_tech = tuple(castle.can_use_tech) + ("citadels",)

    installed.unit_class("citadels").upgrade_player(player)

    for tier in ("battering_ram", "capped_ram", "siege_ram"):
        cls = installed.unit_class(tier)
        expanded = set(getattr(cls, "expanded_is_a", ()) or ())
        expanded.add(tier)
        assert _vs_lookup(castle.rdg_vs, tier, expanded) == 3 * P, (
            "Citadels' +3 vs. Rams does not reach the %s" % tier
        )


# ---------------------------------------------------------------------------
# Houfnice — Bohemian unique unit
# ---------------------------------------------------------------------------


def test_train_time_is_a_registered_rules_property(aoe2_rules):
    """``train_time`` must exist on the base classes.

    ``world_build_rules.unit_train_time`` reads ``cls.train_time`` before the
    line-root walk, so the attribute has to be declared on the base class —
    otherwise the rules parser rejects the property (and drops the value).
    """
    from soundrts.worldunit import Soldier

    assert hasattr(Soldier, "train_time")


def test_houfnice_declares_its_de_train_time(aoe2_rules):
    """DE: the Houfnice trains in 56s (its research takes 140s)."""
    houfnice = aoe2_rules.unit_class("houfnice")
    assert getattr(houfnice, "train_time", 0) == 56 * P
    # ``time_cost`` stays the *research* duration of the line upgrade.
    assert getattr(houfnice, "time_cost", 0) == 140 * P


def test_houfnice_train_time_is_used_for_the_train_order(aoe2_rules):
    """``unit_train_time`` must return the declared 56s, not the line root."""
    from soundrts.world_build_rules import unit_train_time

    assert unit_train_time("houfnice") == 56 * P


def test_train_time_zero_falls_back_to_the_line_root(aoe2_rules):
    """A ``train_time`` of 0 means "not declared" -> line-root walk.

    Guards the ``if explicit:`` change in ``unit_train_time``: a plain 0
    default must not short-circuit the fallback (which would make every
    unit train instantly).
    """
    from soundrts.world_build_rules import unit_train_time

    # The Bombard Cannon line trains at its own 56s.
    assert unit_train_time("bombard_cannon") == 56 * P
    # The sword line trains at the militia root's 21s.
    assert unit_train_time("militia") == 21 * P
    assert unit_train_time("legionary") == 21 * P
    assert unit_train_time("battering_ram") == 36 * P


def test_houfnice_train_cost_matches_de(aoe2_rules):
    """DE: 225 wood 225 gold to train the Houfnice."""
    from soundrts.world_build_rules import unit_train_cost

    cost = list(unit_train_cost("houfnice"))
    assert cost[0] == 225 * P  # gold
    assert cost[1] == 225 * P  # wood
    assert cost[2] == 0 and cost[3] == 0


# ---------------------------------------------------------------------------
# Local stubs (mirroring test_aoe2_tech_effect_engine.py)
# ---------------------------------------------------------------------------


class _FakeUnit:
    """Unit stand-in for the upgrade/effect engine."""

    def __init__(self, type_name, rules, player=None, **attrs):
        self.type_name = type_name
        self.player = player
        cls = rules.unit_class(type_name)
        self.cls = cls
        self.expanded_is_a = set(getattr(cls, "expanded_is_a", ()) or ())
        self.can_use = tuple(getattr(cls, "can_use", ()) or ())
        self.can_use_tech = tuple(getattr(cls, "can_use_tech", ()) or ())
        self.can_use_skill = tuple(getattr(cls, "can_use_skill", ()) or ())
        for stat in ("mdg", "rdg", "mdf", "rdf"):
            setattr(self, stat, getattr(cls, stat, 0) or 0)
        self.cost_bonus = [0] * 16
        self.cost_percent_bonus = [0.0] * 16
        self.time_cost_bonus = 0
        self.time_cost_percent_bonus = 0.0
        self.population_cost_bonus = 0
        self.population_cost_percent_bonus = 0.0
        self.kill_resource_vs = {}
        self.mdg_vs = {}
        self.rdg_vs = {}
        self._applied_upgrade_effects = set()
        self.__dict__.update(attrs)


class _FakePlayer:
    def __init__(self, faction="persians"):
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


@pytest.fixture(scope="module")
def installed(aoe2_rules):
    """Install the AoE2 rules into the global rules object."""
    import soundrts.worldplayerbase.base  # noqa: F401
    import soundrts.worldupgrade  # noqa: F401
    import soundrts.worldorders.base  # noqa: F401
    import soundrts.world_civ_bonuses  # noqa: F401
    import soundrts.worldphase  # noqa: F401
    from soundrts.definitions import rules as global_rules

    saved_dict = global_rules._dict
    saved_classes = getattr(global_rules, "classes", None)
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
