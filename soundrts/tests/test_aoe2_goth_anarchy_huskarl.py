# -*- coding: utf-8 -*-
"""AoE2 DE alignment: the Goths' Anarchy must unlock the Huskarl at the
Barracks, and the Chinese menu labels must match the civ description.

Two separate player-visible bugs are covered here.

Bug 1 — ``anarchy`` had no effect at all
    ``def anarchy`` in ``mods/aoe2/rules.txt`` carried only comments, so the
    technology could be researched but never did anything.  In AoE2 DE,
    Anarchy says "Huskarls can be trained at Barracks."  A Goth player who
    read the civ description ("独特单位：侍从战士。") therefore never found
    the unit in the Barracks at all - it only ever appeared in the Castle.

    The fix gives the technology a real effect::

        effect bonus can_train huskarl 1
        effect_bonus_targets goth_barracks barracks

    and lists ``anarchy`` in the Barracks' ``can_use_tech`` so the filtered
    effect actually reaches the building.

Bug 2 — the Chinese menu labels drifted away from the civ description
    The mod shipped two parallel Chinese label sets: the civilization
    description used the official AoE2 DE names ("侍从战士") while the unit
    menu used a second, hand-invented transliteration set ("赫斯卡尔").  A
    player therefore read "侍从战士" in the civ intro and then found
    "赫斯卡尔" in the Castle menu, and could not find "侍从战士" at all.

Bug 3 — a filtered ``can_train`` effect leaked its filter targets
    ``split_effect_bonus_args`` returned the whole remainder of a
    ``can_train`` row as bonus tokens, so the ``effect_bonus_targets`` names
    were treated as further trainable units.  The AoE2 *Anarchy* effect
    therefore offered "goth_barracks" and "barracks" as trainable units at
    every building that listed the technology.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "mods" / "aoe2"
P = 1000  # soundrts.lib.nofloat.PRECISION


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (MOD / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


@pytest.fixture(scope="module")
def installed(aoe2_rules):
    """Install the AoE2 rules into the global rules object.

    The engine modules must be imported **before** the AoE2 rules are
    installed, otherwise the AoE2 rule set is silently replaced by the base
    one.
    """
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


def _attr(aoe2_rules, type_name, attr, default=None):
    value = aoe2_rules.get(type_name, attr)
    if value is None:
        return default
    if isinstance(value, str):
        return value.split()
    return value


class _FakePlayer:
    def __init__(self, faction="goths"):
        self.faction = faction
        self.units = []
        self.upgrades = []
        self.forbidden_techs = []
        self.allied_victory = [self]
        self.number = 0
        self.gather_time_bonus = {}
        self.gather_qty_bonus = {}
        # The train order scales its duration with the AI time percentages.
        self.ai_train_time_percent = 100
        self.ai_research_time_percent = 100
        self.ai_build_time_percent = 100

    def level(self, name):
        return self.upgrades.count(name)


def _make_building(aoe2_rules, player, type_name):
    cls = aoe2_rules.unit_class(type_name)
    return SimpleNamespace(
        player=player,
        type_name=type_name,
        type=cls,
        attached_addons=[],
        can_use_tech=tuple(getattr(cls, "can_use_tech", ()) or ()),
        can_use=tuple(getattr(cls, "can_use", ()) or ()),
        can_use_skill=tuple(getattr(cls, "can_use_skill", ()) or ()),
        _applied_upgrade_effects=set(),
    )


def _train_time_with(aoe2_rules, unit_name, upgrades):
    """Return ``(base_time, time_after_researching)`` for a train order.

    The base value is the order duration without any technology; the second
    value is the duration once *upgrades* have been researched.  The real
    ``TrainOrder`` is used so the whole chain (per-unit ``time_cost``,
    filtered ``effect_bonus_targets`` rows, phase bonuses) is exercised.
    """
    from soundrts.worldorders.production import TrainOrder
    from soundrts.worldupgrade import Upgrade

    def order_time(researched):
        Upgrade.reset()
        player = _FakePlayer()
        for tech in researched:
            player.upgrades.append(tech)
            aoe2_rules.unit_class(tech).upgrade_player(player)
        order = TrainOrder.__new__(TrainOrder)
        order.type = aoe2_rules.unit_class(unit_name)
        order.unit = SimpleNamespace(
            player=player,
            type_name="goth_barracks",
            type=aoe2_rules.unit_class("goth_barracks"),
            _buff_time_cost_percent=0,
            time_cost=0,
            population_cost=0,
        )
        return order.time_cost

    return order_time([]), order_time(list(upgrades))


# ---------------------------------------------------------------------------
# Bug 1 — Anarchy unlocks the Huskarl at the Barracks
# ---------------------------------------------------------------------------


def test_anarchy_declares_a_real_effect(aoe2_rules):
    """``anarchy`` must declare a ``can_train`` effect, not just comments."""
    effect = _attr(aoe2_rules, "anarchy", "effect")
    assert effect, "anarchy has no effect - researching it does nothing"
    flat = " ".join(effect) if isinstance(effect, list) else str(effect)
    assert "can_train" in flat
    assert "huskarl" in flat


def test_anarchy_targets_the_barracks(aoe2_rules):
    """The effect must be scoped to the Barracks, not to every building."""
    effect = _attr(aoe2_rules, "anarchy", "effect")
    flat = " ".join(effect) if isinstance(effect, list) else str(effect)
    assert "barracks" in flat


def test_goth_barracks_can_use_anarchy(aoe2_rules):
    """The effect only reaches a building that lists ``anarchy``.

    ``effect_bonus_targets`` filters by unit type; the effect itself is
    applied to the buildings whose ``can_use_tech`` contains the technology.
    Only the Goths' own Barracks may list it - the generic ``barracks`` class
    is the base of *every* civ's Barracks, so listing ``anarchy`` there
    would let every other civ's Barracks train Huskarls.
    """
    can_use = _attr(aoe2_rules, "goth_barracks", "can_use_tech", ())
    assert "anarchy" in can_use, (
        "goth_barracks does not list 'anarchy' in can_use_tech, so the "
        "Huskarl unlock never reaches it"
    )

    generic = _attr(aoe2_rules, "barracks", "can_use_tech", ())
    assert "anarchy" not in generic, (
        "the generic 'barracks' class must not list 'anarchy': it is the "
        "base of every civ's Barracks"
    )


def test_goth_barracks_trains_huskarl_after_anarchy(installed):
    """Researching Anarchy must add the Huskarl to the Barracks."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train
    from soundrts.worldupgrade import Upgrade

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = _FakePlayer()
    barracks = _make_building(installed, player, "goth_barracks")
    player.units = [barracks]

    before = effective_can_train(barracks)
    assert "huskarl" not in before, "the Huskarl is trainable before Anarchy"

    Upgrade.reset()
    player.upgrades.append("anarchy")
    installed.unit_class("anarchy").upgrade_player(player)

    after = effective_can_train(barracks)
    assert "huskarl" in after, (
        "researching Anarchy did not unlock the Huskarl at the Barracks"
    )


def test_anarchy_does_not_offer_the_filter_targets_as_units(installed):
    """The effect's filter names must not become trainable units.

    ``effect_bonus_targets goth_barracks barracks`` is a *filter*, not a
    list of units; before the parser fix they showed up in the production
    menu as "goth_barracks" and "barracks".
    """
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train
    from soundrts.worldupgrade import Upgrade

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = _FakePlayer()
    barracks = _make_building(installed, player, "goth_barracks")
    player.units = [barracks]

    Upgrade.reset()
    player.upgrades.append("anarchy")
    installed.unit_class("anarchy").upgrade_player(player)

    trained = effective_can_train(barracks)
    assert "barracks" not in trained
    assert "goth_barracks" not in trained


def test_filtered_can_train_effect_keeps_its_targets_apart():
    """The parser must peel the filter targets off a ``can_train`` row."""
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    bonus, targets = split_effect_bonus_args(
        ["can_train", "huskarl", "1", "goth_barracks", "barracks"]
    )
    assert bonus == ["can_train", "huskarl", "1"], bonus
    assert targets == ["goth_barracks", "barracks"], targets

    # The existing AoE2 First Crusade row must keep working.
    bonus, targets = split_effect_bonus_args(
        ["can_train", "serjeant", "5", "town_center", "townhall"]
    )
    assert bonus == ["can_train", "serjeant", "5"], bonus
    assert targets == ["town_center", "townhall"], targets

    # A row without a filter keeps all of its units.
    bonus, targets = split_effect_bonus_args(
        ["can_train", "footman", "5", "archer", "3", "knight", "2"]
    )
    assert bonus == ["can_train", "footman", "5", "archer", "3", "knight", "2"]
    assert targets == []


def test_can_train_bonus_survives_a_none_override_container(installed):
    """A player whose override container is ``None`` must not crash.

    ``Player`` creates ``_can_train_overrides_by_type`` as ``None``; using
    ``dict.setdefault`` handed that ``None`` back and the assignment raised
    ``TypeError: 'NoneType' object does not support item assignment``.
    """
    from soundrts.definitions import rules as global_rules
    from soundrts.worldupgrade import Upgrade

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = _FakePlayer()
    player._can_train_overrides_by_type = None
    barracks = _make_building(installed, player, "goth_barracks")
    player.units = [barracks]

    Upgrade.reset()
    player.upgrades.append("anarchy")
    installed.unit_class("anarchy").upgrade_player(player)

    assert isinstance(player._can_train_overrides_by_type, dict)
    assert "huskarl" in player._can_train_overrides_by_type["goth_barracks"]


def test_huskarl_is_a_unique_unit_and_at_the_castle(installed):
    """The Huskarl stays a Castle unit until Anarchy is researched."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = _FakePlayer()
    castle = _make_building(installed, player, "goth_castle")
    assert "huskarl" in effective_can_train(castle)

    is_a = _attr(installed, "huskarl", "is_a", ())
    assert "unique_unit" in is_a


# ---------------------------------------------------------------------------
# Bug 4 — Perfusion matches the AoE2 DE specification
# ---------------------------------------------------------------------------


def test_perfusion_matches_the_de_specification(aoe2_rules):
    """AoE2 DE Perfusion: 400 wood + 600 gold, 40s, Imperial Age, Castle.

    Verified against the official DE data
    (``_aoe2db_cache/https_aoe2db_com_civilizations_goths.html``):
    ``Perfusion … cost:{wood:400, gold:600}, research_time:40`` and
    ``"Research Perfusion (Barracks work +100% faster)"``.
    """
    cost = list(aoe2_rules.get("perfusion", "cost"))
    # Resource slots are ordered [gold, wood, food, stone]; the values are
    # PRECISION-scaled (x1000).
    assert cost[0] == 600 * P, cost   # gold
    assert cost[1] == 400 * P, cost   # wood
    assert cost[2] == 0, cost         # food
    assert cost[3] == 0, cost         # stone

    assert aoe2_rules.get("perfusion", "time_cost") == 40 * P

    reqs = _attr(aoe2_rules, "perfusion", "requirements", ())
    assert "aoe_castle" in reqs, reqs
    assert "imperial_age" in reqs, reqs


def test_perfusion_grants_no_resource_discount(aoe2_rules):
    """DE Perfusion is a *speed* bonus only - it grants no cost discount.

    The rule used to carry a second effect row
    (``effect bonus cost 0 0 -20% 0`` — a -20% food discount on the
    infantry).  That discount is not in AoE2 DE: Perfusion only says
    "Barracks work +100% faster".
    """
    effect = _attr(aoe2_rules, "perfusion", "effect")
    flat = " ".join(effect) if isinstance(effect, list) else str(effect)
    assert "time_cost" in flat
    assert "cost" not in flat.replace("time_cost", ""), (
        "perfusion must not grant a resource discount: %r" % flat
    )


def test_perfusion_halves_the_train_time_of_every_barracks_unit(installed):
    """DE: "Barracks work +100% faster" -> every Barracks unit trains in
    half the time (Militia, Spearman *and* the Huskarl unlocked by Anarchy)."""
    from soundrts.definitions import rules as global_rules

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    for unit_name in ("militia", "spearman", "huskarl", "elite_huskarl"):
        base, after = _train_time_with(installed, unit_name, ["perfusion"])
        assert after * 2 == base, (
            "%s: perfusion must halve the train time (%r -> %r)"
            % (unit_name, base, after)
        )


def test_perfusion_does_not_speed_up_non_barracks_units(installed):
    """Perfusion is a *Barracks* bonus - archers and cavalry are unaffected."""
    from soundrts.definitions import rules as global_rules

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    for unit_name in ("aoe_archer", "aoe_knight"):
        base, after = _train_time_with(installed, unit_name, ["perfusion"])
        assert after == base, (
            "%s: perfusion must not change the train time (%r -> %r)"
            % (unit_name, base, after)
        )


def test_perfusion_is_wired_into_the_barracks_units(installed):
    """Every unit the Barracks can train must list ``perfusion``.

    A filtered effect only reaches a unit that lists the technology in
    ``can_use_tech``; without this the Huskarl never gets the bonus.
    """
    for name in (
        "militia",
        "man_at_arms",
        "long_swordsman",
        "two_handed_swordsman",
        "champion",
        "spearman",
        "pikeman",
        "halberdier",
        "huskarl",
        "elite_huskarl",
    ):
        cls = installed.unit_class(name)
        assert "perfusion" in (getattr(cls, "can_use_tech", ()) or ()), name


def test_goth_barracks_keeps_the_generic_barracks_techs(installed):
    """Declaring ``can_use_tech`` blocks attribute inheritance.

    ``goth_barracks`` lists ``anarchy`` (needed for the Huskarl unlock), but
    it must not lose the generic Barracks techs it used to inherit from
    ``barracks`` — Masonry, Architecture, Town Watch and Town Patrol.
    """
    generic = set(_attr(installed, "barracks", "can_use_tech", ()))
    goth = set(_attr(installed, "goth_barracks", "can_use_tech", ()))

    missing = generic - goth
    assert not missing, (
        "goth_barracks lost the inherited Barracks techs: %s" % sorted(missing)
    )
    assert "anarchy" in goth


# ---------------------------------------------------------------------------
# Bug 2 — the Chinese menu labels match the civ description
# ---------------------------------------------------------------------------


def _read_blocks(path):
    """tts id -> the id's text plus every following unnumbered line."""
    blocks = {}
    cur = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith(";"):
                continue
            p = s.split(None, 1)
            if len(p) == 2 and p[0].isdigit():
                cur = int(p[0])
                blocks[cur] = p[1]
            elif cur is not None:
                blocks[cur] += " " + s
    return blocks


def _read_tts(path):
    out = {}
    with open(path, encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith(";"):
                continue
            p = s.split(None, 1)
            if len(p) == 2 and p[0].isdigit():
                out[int(p[0])] = p[1]
    return out


EN_UNIT = re.compile(r"Unique units?\s+(.+?)\.", re.S)
EN_TECH = re.compile(r"Unique techs?\s+(.+?)\.", re.S)
ZH_UNIT = re.compile(r"独特单位：(.+?)。")
ZH_TECH = re.compile(r"独特科技：(.+?)。")
ZH_SPLIT = re.compile(r"[、,，/]")


def _menu_labels():
    """english menu label -> tts title id."""
    en = _read_tts(MOD / "ui" / "tts.txt")
    out = {}
    for tid, label in en.items():
        out.setdefault(label.strip().lower(), tid)
    return out


def test_chinese_menu_labels_match_the_civ_description():
    """Every advertised unique unit / technology must use the same Chinese
    name in the unit menu as in the civilization description."""
    en_blocks = _read_blocks(MOD / "ui" / "tts.txt")
    zh_blocks = _read_blocks(MOD / "ui-zh" / "tts.txt")
    zh_tts = _read_tts(MOD / "ui-zh" / "tts.txt")
    name_to_tid = _menu_labels()

    mismatches = []
    for cid in sorted(en_blocks):
        if not 8520 <= cid <= 8567:
            continue
        for en_rx, zh_rx in ((EN_UNIT, ZH_UNIT), (EN_TECH, ZH_TECH)):
            me = en_rx.search(en_blocks[cid])
            mz = zh_rx.search(zh_blocks.get(cid, ""))
            if not me or not mz:
                continue
            en_names = [n.strip() for n in re.split(r",| and ", me.group(1)) if n.strip()]
            zh_names = [n.strip() for n in ZH_SPLIT.split(mz.group(1)) if n.strip()]
            if len(en_names) != len(zh_names):
                continue
            for en, zh in zip(en_names, zh_names):
                tid = name_to_tid.get(en.lower())
                if tid is None:
                    continue
                menu = zh_tts.get(tid, "")
                if menu != zh:
                    mismatches.append(
                        "tts %d: description says %r, menu says %r" % (tid, zh, menu)
                    )
    assert not mismatches, "\n".join(mismatches)


def test_goth_huskarl_is_called_the_same_everywhere():
    """The specific case the player reported."""
    zh_tts = _read_tts(MOD / "ui-zh" / "tts.txt")
    zh_blocks = _read_blocks(MOD / "ui-zh" / "tts.txt")

    # 9014 = huskarl, 8334 = elite huskarl
    assert zh_tts.get(9014) == "侍从战士"
    assert zh_tts.get(8334) == "精锐侍从战士"
    # 9042 = anarchy, 9043 = perfusion
    assert zh_tts.get(9042) == "无政府"
    assert zh_tts.get(9043) == "井喷"

    # The Goths' civ description (tts 8540) must use the same names.
    desc = zh_blocks.get(8540, "")
    assert "侍从战士" in desc
    assert "无政府" in desc
    assert "井喷" in desc
