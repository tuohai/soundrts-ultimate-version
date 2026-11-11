# -*- coding: utf-8 -*-
"""The mining-camp / lumber-mill techs must actually speed the villager up.

Two things are checked here:

1. **The techs work.**  Researching AoE2's *Gold Mining* / *Double Bit Axe*
   puts a ``gather_time`` bonus on the player, and the villager's real
   per-second gathering rate goes up accordingly.
2. **The attributes screen follows.**  The unit attribute screen used to
   print the static rules value (0.38 gold/second) no matter which techs
   the player had researched.  It now prints the *effective* rate.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


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


class _FakePlayer:
    def __init__(self):
        self.upgrades = []
        self.forbidden_techs = []
        self.allied_victory = [self]
        self.number = 0
        self.gather_time_bonus = {}
        self.gather_qty_bonus = {}
        self.units = []

    def level(self, name):
        return self.upgrades.count(name)


class _Villager:
    """A villager stand-in carrying the rules values and a player."""

    def __init__(self, rules, player):
        self.player = player
        self.type_name = "peasant"
        cls = rules.unit_class("peasant")
        for key in dir(cls):
            if key.startswith(("gather_rate", "gather_time", "gather_qty")):
                setattr(self, key, getattr(cls, key))
        self.gather_rate = dict(getattr(cls, "gather_rate", {}) or {})
        self.gather_time = dict(getattr(cls, "gather_time", {}) or {})
        self.gather_qty = dict(getattr(cls, "gather_qty", {}) or {})
        self.can_gather_deposit = list(
            getattr(cls, "can_gather_deposit", []) or [])
        self.can_gather_building = list(
            getattr(cls, "can_gather_building", []) or [])
        self.can_use_tech = tuple(getattr(cls, "can_use_tech", ()) or ())
        self.can_use = tuple(getattr(cls, "can_use", ()) or ())
        self.expanded_is_a = set(getattr(cls, "expanded_is_a", ()) or ())
        self._applied_upgrade_effects = set()

    def _single_gather_permission(self):
        perms = (self.can_gather_deposit or []) + (
            self.can_gather_building or [])
        return len(perms) == 1


class _Deposit:
    def __init__(self, type_name, resource_type):
        self.type_name = type_name
        self.resource_type = resource_type
        self.extraction_time = 0


def _research(rules, player, villager, tech):
    from soundrts.worldupgrade import Upgrade

    Upgrade.reset()
    player.upgrades.append(tech)
    rules.unit_class(tech).upgrade_player(player)


# ---------------------------------------------------------------------------
# 1 — the techs really do speed the villager up
# ---------------------------------------------------------------------------


def test_gold_mining_tech_is_defined_with_a_time_bonus(aoe2_rules):
    effect = aoe2_rules.unit_class("gold_mining").effect
    # The mining camp is a *resource*-scoped bonus: it speeds up every
    # gold deposit (resource1 = gold), so the key names the resource slot.
    assert "gather_time_resource1" in effect
    assert "-13%" in effect


def test_double_bit_axe_tech_is_defined_with_a_time_bonus(aoe2_rules):
    effect = aoe2_rules.unit_class("double_bit_axe").effect
    # The lumber mill is a *resource*-scoped bonus: every wood deposit is
    # affected, so the key names the resource slot (resource2 = wood).
    assert "gather_time_resource2" in effect
    assert "-17%" in effect


def test_gold_mining_raises_the_real_gold_rate(installed):
    """0.38 gold/s before the tech, ~0.44 gold/s after it."""
    from soundrts.worldunit.worldworker import Worker

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    gold = _Deposit("goldmine", "resource1")

    before = Worker.get_gather_rate(villager, "resource1", gold)
    assert before == pytest.approx(0.38, abs=1e-6)

    _research(installed, player, villager, "gold_mining")
    assert player.gather_time_bonus["resource1"] == "-13%"

    after = Worker.get_gather_rate(villager, "resource1", gold)
    # -13% gather time → 1 / 0.87 ≈ 1.1494× faster.
    assert after == pytest.approx(before / 0.87, abs=1e-6)
    assert after > before


def test_double_bit_axe_raises_the_real_wood_rate(installed):
    from soundrts.worldunit.worldworker import Worker

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    wood = _Deposit("wood", "resource2")

    before = Worker.get_gather_rate(villager, "resource2", wood)
    assert before == pytest.approx(0.39, abs=1e-6)

    _research(installed, player, villager, "double_bit_axe")
    after = Worker.get_gather_rate(villager, "resource2", wood)
    assert after == pytest.approx(before / 0.83, abs=1e-6)
    assert after > before


def test_mining_tech_does_not_speed_up_other_resources(installed):
    """Gold Mining must not touch wood / stone / food."""
    from soundrts.worldunit.worldworker import Worker

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]

    wood = _Deposit("wood", "resource2")
    stone = _Deposit("stone_mine", "resource4")
    before_wood = Worker.get_gather_rate(villager, "resource2", wood)
    before_stone = Worker.get_gather_rate(villager, "resource4", stone)

    _research(installed, player, villager, "gold_mining")

    assert Worker.get_gather_rate(villager, "resource2", wood) == pytest.approx(
        before_wood, abs=1e-6)
    assert Worker.get_gather_rate(
        villager, "resource4", stone) == pytest.approx(before_stone, abs=1e-6)


# ---------------------------------------------------------------------------
# 2 — the attributes screen shows the effective rate
# ---------------------------------------------------------------------------


def _rate_rows(attrs):
    from soundrts import msgparts as mp

    out = {}
    for _key, name, value in attrs:
        if isinstance(name, list) and name and name[0] == mp.GATHER_RATE[0]:
            out[tuple(name)] = value
    return out


def _num(value):
    """The numeric part of a msg list (the trailing msgpart id is ignored).

    ``nb2msg_float`` renders non-integers as text ("0.38"), so the digits
    have to be parsed out of the string.
    """
    from soundrts import msgparts as mp

    for part in value:
        if isinstance(part, (int, float)) and not isinstance(part, bool):
            if part == mp.PER_SECOND[0]:
                continue
            return float(part)
        if isinstance(part, str):
            try:
                return float(part)
            except ValueError:
                continue
    return None


def _handler():
    from soundrts.attributes.gather_handler import GatherHandler

    parent = SimpleNamespace(
        resource_utils=SimpleNamespace(
            _get_resource_type_name=lambda t: t),
    )
    return GatherHandler(parent)


def test_attribute_screen_rate_follows_gold_mining(installed):
    """The row for the gold mine must show the boosted rate."""
    from soundrts.attributes.gather_rate_display import effective_rate

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    unit_view = SimpleNamespace(model=villager, player=player)

    before = effective_rate(unit_view, "goldmine")
    assert before == pytest.approx(0.38, abs=1e-6)

    _research(installed, player, villager, "gold_mining")

    after = effective_rate(unit_view, "goldmine")
    assert after == pytest.approx(0.38 / 0.87, abs=1e-6)
    assert after > before


def test_attribute_screen_rate_follows_double_bit_axe(installed):
    from soundrts.attributes.gather_rate_display import effective_rate

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    unit_view = SimpleNamespace(model=villager, player=player)

    before = effective_rate(unit_view, "wood")
    assert before == pytest.approx(0.39, abs=1e-6)

    _research(installed, player, villager, "double_bit_axe")

    after = effective_rate(unit_view, "wood")
    assert after == pytest.approx(0.39 / 0.83, abs=1e-6)
    assert after > before


def test_screen_and_simulation_agree_when_both_scopes_are_active(installed):
    """The screen must not disagree with the live worker.

    A civ-wide bonus (``gather_time_resource1``) and a deposit-scoped
    bonus (``gather_time_goldmine``) can be active at the same time.  Both
    code paths have to resolve the *same* bonus, otherwise the attribute
    screen reports a rate the worker never achieves.
    """
    from soundrts.attributes.gather_rate_display import effective_rate
    from soundrts.worldunit.worldworker import Worker

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    unit_view = SimpleNamespace(model=villager, player=player)
    gold = _Deposit("goldmine", "resource1")

    # A civ-wide bonus (like the Romans' -5% on every resource) ...
    player.gather_time_bonus["resource1"] = "-5%"
    # ... plus a deposit-scoped bonus.
    player.gather_time_bonus["goldmine"] = "-13%"

    screen = effective_rate(unit_view, "goldmine")
    simulated = Worker.get_gather_rate(villager, "resource1", gold)
    assert screen == pytest.approx(simulated, abs=1e-9)
    # The deposit-scoped key is the more specific one, so it is the one
    # that wins.
    assert screen == pytest.approx(0.38 / 0.87, abs=1e-6)


def test_tech_and_civ_phase_bonuses_do_not_overwrite_each_other(installed):
    """A tech and a civ bonus may use the *same* key — neither may be lost.

    The mining-camp tech is written ``gather_time_resource1`` and the
    Ethiopians' civ bonus is written ``gather_time_resource1`` too.  Both
    used to land in one flat dict, so whichever was applied last silently
    erased the other.  They are stored apart now and *combined*.
    """
    from soundrts.gather_rate import player_gather_bonus
    from soundrts.worldphase import apply_parsed_on_phase_bonus

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    gold = _Deposit("goldmine", "resource1")

    # The tech (through the normal research path) ...
    _research(installed, player, villager, "gold_mining")
    assert player.gather_time_bonus["resource1"] == "-13%"

    # ... and the civ phase bonus, which uses the very same key.
    apply_parsed_on_phase_bonus(
        player, ["gather_time_resource1", "-50%"], [], "castle_age", "ethiopians"
    )

    # Neither dict may have eaten the other.
    assert player.gather_time_bonus["resource1"] == "-13%"
    assert player.phase_gather_time_bonus["resource1"] == "-50%"

    # Both apply: -13% and -50% of the time.
    merged = player_gather_bonus(player, "time")
    assert merged.lookup(("goldmine", "resource1")) == "-56.500000%"

    from soundrts.worldunit.worldworker import Worker
    rate = Worker.get_gather_rate(villager, "resource1", gold)
    assert rate == pytest.approx(0.38 / (0.87 * 0.50), abs=1e-6)


def test_civ_phase_bonus_does_not_hide_the_tech_for_another_deposit(installed):
    """Each namespace resolves its own most specific key.

    The Mayans' civ bonus is written for the deposit type (``goldmine``)
    while the mining tech is written for the resource slot
    (``resource1``).  Merging the two dicts before the lookup would let
    the narrow key hide the broad one.
    """
    from soundrts.gather_rate import player_gather_bonus
    from soundrts.worldphase import apply_parsed_on_phase_bonus

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]

    _research(installed, player, villager, "gold_mining")
    apply_parsed_on_phase_bonus(
        player, ["gather_time_goldmine", "-7%"], [], "castle_age", "mayans"
    )

    merged = player_gather_bonus(player, "time")
    # The gold mine gets both the tech and the civ bonus ...
    assert merged.lookup(("goldmine", "resource1")) == "-19.090000%"
    # ... while another gold deposit still gets the tech.
    assert merged.lookup(("goldmine_deposit", "resource1")) == "-13%"


def test_attribute_screen_shows_effective_rate_row(installed):
    """The real attribute pipeline must print the boosted number."""
    from soundrts.attributes.utils import get_stat_tts_name

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]
    unit_view = SimpleNamespace(model=villager, player=player)

    handler = _handler()

    attrs = []
    handler._add_dynamic_gather_attributes(attrs, unit_view, "gather_rate")

    rows = _rate_rows(attrs)
    assert rows, "no gather-rate rows were produced"

    gold_label = tuple(get_stat_tts_name("gather_rate_goldmine"))
    wood_label = tuple(get_stat_tts_name("gather_rate_wood"))
    assert gold_label in rows
    assert wood_label in rows

    assert _num(rows[gold_label]) == pytest.approx(0.38, abs=0.005)

    _research(installed, player, villager, "gold_mining")

    attrs = []
    handler._add_dynamic_gather_attributes(attrs, unit_view, "gather_rate")
    rows = _rate_rows(attrs)
    assert _num(rows[gold_label]) == pytest.approx(0.44, abs=0.005)
    # Wood is untouched by Gold Mining.
    assert _num(rows[wood_label]) == pytest.approx(0.39, abs=0.005)


def test_attribute_screen_without_player_keeps_base_rate(installed):
    """No player (unit browser / detail proxy) → the rules value stands."""
    from soundrts.attributes.gather_rate_display import effective_rate

    villager = _Villager(installed, _FakePlayer())
    unit_view = SimpleNamespace(model=villager)

    assert effective_rate(unit_view, "goldmine") == pytest.approx(
        0.38, abs=1e-6)


def test_detail_proxy_uses_its_own_player(installed):
    """``TempUnit``-style proxies carry the player directly."""
    from soundrts.attributes.gather_rate_display import effective_rate

    player = _FakePlayer()
    villager = _Villager(installed, player)
    player.units = [villager]

    proxy = SimpleNamespace(model=villager, player=player)
    _research(installed, player, villager, "gold_mining")

    assert effective_rate(proxy, "goldmine") == pytest.approx(
        0.38 / 0.87, abs=1e-6)


# ---------------------------------------------------------------------------
# 3 — shared helper sanity
# ---------------------------------------------------------------------------


def test_rate_bonus_factor_inverts_the_time_bonus():
    from soundrts.gather_rate import rate_bonus_factor

    assert rate_bonus_factor({"goldmine": "-13%"}, "goldmine", "resource1") \
        == pytest.approx(1 / 0.87)
    assert rate_bonus_factor({"gold": "-50%"}, "goldmine", "resource1") \
        == pytest.approx(2.0)
    # Flat (seconds) bonuses cannot be expressed as a factor.
    assert rate_bonus_factor({"goldmine": -1}, "goldmine", "resource1") is None
    assert rate_bonus_factor(None, "goldmine", "resource1") is None


def test_rate_bonus_factor_prefers_the_deposit_key():
    """The continuous path resolves the deposit type before the resource."""
    from soundrts.gather_rate import rate_bonus_factor

    bonus = {"goldmine": "-13%", "resource1": "-50%"}
    assert rate_bonus_factor(bonus, "goldmine", "resource1") == pytest.approx(
        1 / 0.87)


def test_bonus_keys_use_one_shared_order():
    """Deposit → resource slot → resource name → ``all``.

    The live simulation (``get_gather_time``) and the attribute screen
    (``get_gather_rate``) must resolve the *same* bonus, otherwise the
    screen can claim a rate the worker does not achieve.
    """
    from soundrts.gather_rate import bonus_keys

    assert bonus_keys("goldmine", "resource1") == (
        "goldmine", "resource1", "gold", "all")
    assert bonus_keys("stone_mine", "resource4") == (
        "stone_mine", "resource4", "stone", "all")
    assert bonus_keys("food_livestock", "resource3") == (
        "food_livestock", "resource3", "food", "all")


def test_time_and_rate_resolve_the_same_bonus():
    """A resource-wide bonus must not shadow a deposit-scoped tech.

    The Romans' civ bonus (``gather_time_resource1 -5%``) and Gold Mining
    (``gather_time_goldmine -13%``) can both be active.  The mining tech
    is the more specific key, so it is the one that applies — and it has
    to be the one *both* code paths pick.
    """
    from soundrts.gather_rate import bonus_keys, lookup_bonus

    bonus = {"resource1": "-5%", "goldmine": "-13%"}
    keys = bonus_keys("goldmine", "resource1")
    assert lookup_bonus(bonus, keys) == "-13%"


def test_both_key_spellings_reach_the_same_worker():
    """``gather_time_resource1`` and ``gather_time_goldmine`` are equivalent.
    The user asked for *both* spellings to work: the resource slot
    (``resourceN``) and the deposit type (``goldmine``).  A rules author
    may use either; the worker must gather at the same speed.
    """
    from soundrts.gather_rate import rate_bonus_factor

    by_slot = rate_bonus_factor({"resource1": "-13%"}, "goldmine", "resource1")
    by_deposit = rate_bonus_factor({"goldmine": "-13%"}, "goldmine", "resource1")
    by_name = rate_bonus_factor({"gold": "-13%"}, "goldmine", "resource1")
    assert by_slot == pytest.approx(1 / 0.87)
    assert by_deposit == pytest.approx(by_slot)
    assert by_name == pytest.approx(by_slot)


def test_base_gather_rate_prefers_the_per_deposit_attribute():
    from soundrts.gather_rate import base_gather_rate

    unit = SimpleNamespace(
        gather_rate={"wood": 0.39},
        gather_rate_goldmine=0.38,
    )
    assert base_gather_rate(unit, "goldmine") == pytest.approx(0.38)
    assert base_gather_rate(unit, "wood") == pytest.approx(0.39)
    assert base_gather_rate(unit, "stone_mine") is None


# ---------------------------------------------------------------------------
# 3b — gather_qty supports the resource slot *and* the deposit type
# ---------------------------------------------------------------------------


def _apply_gather_qty_bonus(player, stat, value):
    """Push a ``gather_qty_<key>`` bonus onto the player, as a tech would."""
    from soundrts.worldupgrade import Upgrade

    class _Host:
        def __init__(self, p):
            self.player = p
            self.can_gather_deposit = []
            self.can_gather_building = []

    Upgrade.effect_bonus(_Host(player), 0, stat, value)


def _real_deposit(type_name, resource_type):
    """A real ``Deposit`` instance — the worker checks ``isinstance``."""
    from soundrts.worldresource import Deposit

    dep = Deposit.__new__(Deposit)
    dep.type_name = type_name
    dep.resource_type = resource_type
    dep.extraction_time = None
    dep.extraction_qty = None
    return dep


def test_gather_qty_accepts_the_resource_slot_and_the_deposit_type(installed):
    """``gather_qty`` mirrors ``gather_time``: both spellings work.

    ``gather_qty_resource1`` (the resource slot) and ``gather_qty_goldmine``
    (the deposit type) must both reach the worker and raise the amount
    carried per trip by the same amount.
    """
    from soundrts.worldunit.worldworker import Worker

    for stat in ("gather_qty_resource1", "gather_qty_goldmine"):
        player = _FakePlayer()
        villager = _Villager(installed, player)
        villager.gather_qty = {"goldmine": 10}
        player.units = [villager]
        gold = _real_deposit("goldmine", "resource1")

        base = Worker.get_gather_qty(villager, "resource1", gold)
        assert base == 10

        _apply_gather_qty_bonus(player, stat, "25%")
        boosted = Worker.get_gather_qty(villager, "resource1", gold)

        # The bonus is stored under the key exactly as the rules wrote it.
        assert list(player.gather_qty_bonus) == [stat[len("gather_qty_"):]]
        # ``get_gather_qty`` returns whole units, so the boosted amount is
        # truncated (10 * 1.25 -> 12).
        assert boosted == int(base * 1.25)


def test_gather_qty_bonus_keys_prefer_the_deposit_type():
    """The same lookup order as ``gather_time``: deposit type first.

    A deposit-scoped bonus must not be shadowed by a resource-wide one,
    or the two code paths would disagree about the carried amount.
    """
    from soundrts.gather_rate import bonus_keys, qty_bonus_factor

    assert bonus_keys("goldmine", "resource1") == (
        "goldmine", "resource1", "gold", "all")

    bonus = {"resource1": "10%", "goldmine": "25%"}
    # The gold mine picks the deposit-scoped bonus (25%), not the
    # resource-wide one (10%).
    assert qty_bonus_factor(bonus, "goldmine", "resource1") == pytest.approx(1.25)
    # A deposit with no bonus of its own falls back to the resource slot.
    assert qty_bonus_factor(bonus, "stone_mine", "resource4") is None
    assert qty_bonus_factor({"resource4": "10%"}, "stone_mine", "resource4") \
        == pytest.approx(1.10)


# ---------------------------------------------------------------------------
# 4 — resource names are declared by the rules, not hardcoded in the engine
# ---------------------------------------------------------------------------


def test_resource_names_come_from_the_rules_parameters():
    """``parameters resource_names`` is the only source of the names."""
    from soundrts.worldmarket import parse_resource_index

    # The base rules declare gold / wood / food.
    assert parse_resource_index("gold") == 0
    assert parse_resource_index("wood") == 1
    assert parse_resource_index("food") == 2


def test_resource_names_survive_a_rules_dict_swap():
    """The declaration must survive the rules being swapped out.

    ``Rules.load`` replaces ``_dict`` wholesale, and the test harness
    restores the base rules between modules.  A resource name that was
    resolved once must keep resolving — otherwise the market and the
    gather bonuses silently stop finding "wood" and "gold".
    """
    from soundrts.definitions import Rules, rules as global_rules
    from soundrts.worldmarket import parse_resource_index

    # Make sure the declaration is known.
    assert parse_resource_index("wood") == 1

    saved_dict = global_rules._dict
    try:
        global_rules._dict = {}
        assert parse_resource_index("wood") == 1
        assert parse_resource_index("gold") == 0
    finally:
        global_rules._dict = saved_dict

    # A freshly loaded rules set replaces the remembered declaration.
    fresh = Rules()
    fresh.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    assert fresh.resource_name_pairs() == (
        (0, "gold"), (1, "wood"), (2, "food"), (3, "stone"))
