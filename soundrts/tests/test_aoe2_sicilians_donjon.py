# -*- coding: utf-8 -*-
"""AoE2 DE: the Sicilian Donjon (城楼) must exist and behave like DE.

DE facts (Lords of the West / The Three Kingdoms, confirmed against the
official wiki, AoE2DB and seicing.com):

  * The Donjon is the Sicilian unique fortification.  It is buildable from the
    Dark Age and *replaces* the Watch Tower line (Watch/Guard/Keep towers are
    "NotAvailable" in the Sicilian tech tree).
  * Cost 50 wood / 175 stone, 2x2 footprint, 125 s build time.
  * HP by age: 625 / 1250 / 1500 / 2250 (Dark / Feudal / Castle / Imperial).
  * Armor by age: melee 0/1/2/3, pierce 6/7/8/9.
  * Attack: none in the Dark Age; 5 pierce in the Feudal Age, firing 1 / 2 /
    3 arrows in Feudal / Castle / Imperial.  Range 8, min range 1, reload 2 s.
  * Garrison 10, heals the garrisoned units.
  * Trains the Serjeant (Sicilian UU) and the Spearman line.
  * Unlocks (is the prerequisite for) the Archery Range and the Stable.

Sicilian civilization bonuses (DE): start with +100 stone; farm upgrades give
+125% extra food; soldiers take -40% bonus damage; can build the Donjon in
the Dark Age; fortifications built 50% faster and Town Centers 100% faster.

NOTE: rules values are stored PRECISION-scaled (x1000) by the engine, e.g.
``hp_max 625`` -> 625000, ``cost 0 50 0 175`` -> (0, 50000, 0, 175000).
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


@pytest.fixture
def installed(aoe2_rules):
    """Install the AoE2 rules into the global registry."""
    from soundrts.definitions import rules as global_rules

    original_dict = global_rules._dict
    original_classes = getattr(global_rules, "classes", {})
    try:
        global_rules._dict.update(aoe2_rules._dict)
        global_rules.classes.update(aoe2_rules.classes)
        global_rules.apply_inheritance(expanded_is_a=True)
        yield global_rules
    finally:
        global_rules._dict.clear()
        global_rules._dict.update(original_dict)
        global_rules.classes.clear()
        global_rules.classes.update(original_classes)
        global_rules.apply_inheritance(expanded_is_a=True)


def _attr(rules, name, attr, default=()):
    cls = rules.unit_class(name)
    assert cls is not None, f"missing unit class: {name}"
    # ``can_build`` / ``can_train`` are shadowed by @property on the base
    # classes, so the rules-provided values live in ``_rules_can_build`` /
    # ``_rules_can_train`` and are only reachable through class_rules_attr.
    value = rules.class_rules_attr(cls, attr, default)
    return value if value else default


# ---------------------------------------------------------------------------
# 1. The building exists and is wired to the Sicilian build menu
# ---------------------------------------------------------------------------


def test_donjon_is_defined(aoe2_rules):
    assert aoe2_rules.unit_class("donjon") is not None


def test_sicilians_start_with_100_extra_stone(aoe2_rules):
    """DE Sicilian bonus: start with +100 stone (200 -> 300 stone)."""
    res = list(aoe2_rules.get("sicilians", "starting_resources") or [])
    assert res == ["100", "200", "200", "300"], res


def test_sicilian_villager_can_build_donjon(aoe2_rules):
    """The Sicilian villager must offer the Donjon instead of the tower line."""
    can_build = list(_attr(aoe2_rules, "sicilian_villager", "can_build"))
    assert "donjon" in can_build
    for tower in ("scouttower", "guardtower", "keeptower"):
        assert tower not in can_build, f"{tower} must be replaced by the Donjon"


def test_other_civs_keep_the_watch_tower_line(aoe2_rules):
    """The Donjon is Sicilian-only — the generic civ keeps the towers."""
    for civ, villager in (
        ("britons", "peasant"),
        ("franks", "frank_villager"),
        ("chinese", "chinese_villager"),
    ):
        can_build = list(_attr(aoe2_rules, villager, "can_build"))
        assert "scouttower" in can_build, civ
        assert "donjon" not in can_build, civ


def test_donjon_is_dark_age_buildable(aoe2_rules):
    """DE: the Donjon replaces the tower line *and* is available in the Dark Age.

    The tower line is unlocked by ``feudal_age``; the Donjon must not be.
    """
    reqs = list(_attr(aoe2_rules, "donjon", "requirements"))
    assert "feudal_age" not in reqs
    assert "dark_age" not in reqs
    assert reqs == ["town_center"], reqs


# ---------------------------------------------------------------------------
# 2. Cost / footprint / garrison
# ---------------------------------------------------------------------------


def test_donjon_cost_and_garrison(aoe2_rules):
    # DE: 50 wood / 175 stone.  Slot order: gold, wood, food, stone.
    assert tuple(_attr(aoe2_rules, "donjon", "cost")) == (0, 50 * P, 0, 175 * P)
    assert tuple(_attr(aoe2_rules, "donjon", "train_cost")) == (0, 50 * P, 0, 175 * P)
    assert _attr(aoe2_rules, "donjon", "transport_capacity") == 10
    assert _attr(aoe2_rules, "donjon", "sight_range") == 10 * P


def test_donjon_build_time(aoe2_rules):
    """DE: 125 s base (83 s with the Sicilian fortification bonus)."""
    assert _attr(aoe2_rules, "donjon", "time_cost") == 125 * P


def test_donjon_base_stats(aoe2_rules):
    assert _attr(aoe2_rules, "donjon", "hp_max") == 625 * P
    # ``mdf 0`` is falsy, so the class-attr helper cannot see it — read the
    # raw rules dict instead.
    assert aoe2_rules._dict["donjon"]["mdf"] == 0
    assert _attr(aoe2_rules, "donjon", "rdf") == 6 * P
    # DE: the Donjon cannot attack in the Dark Age — the attack rows are only
    # granted by the feudal_age phase, not by the building definition.
    assert not _attr(aoe2_rules, "donjon", "rdg")


# ---------------------------------------------------------------------------
# 3. Age scaling
# ---------------------------------------------------------------------------


def _on_phase_rows(rules, faction, phase, target=None):
    """All ``on_phase <phase> …`` rows of a race, as ``(stat, value, targets)``.

    A row may carry several stats (``mdf 1 rdf 1 donjon``), so the bonus
    tokens have to be split with the engine's own
    ``split_effect_bonus_args`` instead of a hand-rolled parser.
    """
    from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args

    rows = []
    for entry in rules.get(faction, "on_phase_effects") or ():
        tokens = list(entry) if not isinstance(entry[0], list) else list(entry[0])
        if not tokens:
            continue
        if str(tokens[0]) != phase:
            continue
        rest = tokens[1:]
        if not rest:
            continue
        bonus, targets = split_effect_bonus_args(rest)
        # ``bonus`` is a flat list of stat/value pairs.
        for i in range(0, len(bonus) - 1, 2):
            stat = str(bonus[i])
            value = bonus[i + 1]
            row_targets = [str(t) for t in targets]
            if target is not None and target not in row_targets:
                continue
            rows.append((stat, value, row_targets))
    return rows


def test_donjon_hp_scales_by_age(aoe2_rules):
    """DE HP: 625 (Dark) / 1250 (Feudal) / 1500 (Castle) / 2250 (Imperial).

    DE applies these as *flat* HP gains on top of the Dark Age base
    (625): +625 in the Feudal Age, +250 in the Castle Age and +750 in the
    Imperial Age.  A percentage row would compound across ages, so the
    rules rows must be flat deltas.
    """
    for phase, delta in (
        ("feudal_age", 625 * P),
        ("castle_age", 250 * P),
        ("imperial_age", 750 * P),
    ):
        found = [
            r
            for r in _on_phase_rows(aoe2_rules, "sicilians", phase, target="donjon")
            if r[0] == "hp"
        ]
        assert found, f"missing hp row for {phase}"
        assert any(r[1] == delta for r in found), (phase, found)

    # No Dark Age HP row: the Dark Age Donjon has its base 625 HP only.
    dark = [
        r
        for r in _on_phase_rows(aoe2_rules, "sicilians", "dark_age", target="donjon")
        if r[0] == "hp"
    ]
    assert not dark, dark


def test_donjon_armor_scales_by_age(aoe2_rules):
    """DE armor: melee 0/1/2/3, pierce 6/7/8/9 — +1/+1 per age.

    The Dark Age Donjon has the base 0/6 armor, so there is no Dark Age
    armor row.
    """
    for phase in ("feudal_age", "castle_age", "imperial_age"):
        rows = _on_phase_rows(aoe2_rules, "sicilians", phase, target="donjon")
        assert any(r[0] == "mdf" and r[1] == 1 * P for r in rows), phase
        assert any(r[0] == "rdf" and r[1] == 1 * P for r in rows), phase

    dark = _on_phase_rows(aoe2_rules, "sicilians", "dark_age", target="donjon")
    assert not [r for r in dark if r[0] in ("mdf", "rdf")], dark


def test_donjon_attack_scales_by_age(aoe2_rules):
    """DE attack: 5 pierce from the Feudal Age, 1/2/3 arrows per age."""
    feudal = _on_phase_rows(aoe2_rules, "sicilians", "feudal_age", target="donjon")
    assert any(r[0] == "rdg" and r[1] == 5 * P for r in feudal)
    # The base ``rdg_range 8`` on the definition is enough — a second
    # feudal_age range row would double the range to 16.
    assert not [r for r in feudal if r[0] == "rdg_range"], feudal
    assert any(r[0] == "rdg_seq_times" and r[1] == "1" for r in feudal)

    castle = _on_phase_rows(aoe2_rules, "sicilians", "castle_age", target="donjon")
    assert any(r[0] == "rdg_seq_times" and r[1] == "2" for r in castle)

    imperial = _on_phase_rows(aoe2_rules, "sicilians", "imperial_age", target="donjon")
    assert any(r[0] == "rdg_seq_times" and r[1] == "3" for r in imperial)


def test_donjon_secondary_sequence_flags_are_set(aoe2_rules):
    """A bare ``rdg_seq_times`` is a no-op in this engine.

    The multi-shot sequence only runs when the secondary mode is on and the
    extra shots carry the live main damage.
    """
    for phase, times in (
        ("feudal_age", "1"),
        ("castle_age", "2"),
        ("imperial_age", "3"),
    ):
        rows = _on_phase_rows(aoe2_rules, "sicilians", phase, target="donjon")
        assert any(
            r[0] == "rdg_seq_times" and r[1] == times for r in rows
        ), phase
        assert any(r[0] == "rdg_seq_secondary" and r[1] == "1" for r in rows), phase
        assert any(
            r[0] == "rdg_seq_secondary_live" and r[1] == "1" for r in rows
        ), phase


# ---------------------------------------------------------------------------
# 4. Sicilian civilization bonuses (DE)
# ---------------------------------------------------------------------------


def test_sicilians_have_no_building_or_town_center_hp_bonus(aoe2_rules):
    """DE gives the Sicilians no building HP bonus and no Town Center HP bonus.

    Both of those belong to the Byzantines ("buildings +10/20/30/40% HP").
    Having them here inflated the Donjon's HP by 10% in every age.
    """
    for phase in ("dark_age", "feudal_age", "castle_age", "imperial_age"):
        rows = _on_phase_rows(aoe2_rules, "sicilians", phase)
        for row in rows:
            assert not (
                row[0] == "hp" and "building" in row[2]
            ), f"unexpected building HP bonus in {phase}: {row}"
            assert not (
                row[0] == "hp" and "town_center" in row[2]
            ), f"unexpected town center HP bonus in {phase}: {row}"


def test_sicilians_build_speed_bonuses(aoe2_rules):
    """DE: fortifications built 50% faster, Town Centers built 100% faster.

    DE expresses those as a time reduction (Donjon 125 s -> 83 s, Town Center
    100 s -> 50 s), so the rules rows use -33% and -50% respectively.
    """
    rows = _on_phase_rows(aoe2_rules, "sicilians", "dark_age")
    fortifications = [
        r for r in rows if r[0] == "time_cost" and "donjon" in r[2]
    ]
    assert fortifications, "missing fortification build-speed row"
    assert fortifications[0][1] == "-33%", fortifications

    town_centers = [
        r for r in rows if r[0] == "time_cost" and "town_center" in r[2]
    ]
    assert town_centers, "missing town center build-speed row"
    assert town_centers[0][1] == "-50%", town_centers


# ---------------------------------------------------------------------------
# 5. Training
# ---------------------------------------------------------------------------


def test_donjon_trains_serjeant_and_spearman_line(aoe2_rules):
    can_train = list(_attr(aoe2_rules, "donjon", "can_train"))
    assert "serjeant" in can_train
    assert "spearman" in can_train
    assert "pikeman" in can_train
    assert "halberdier" in can_train


def test_serjeant_can_build_donjon(aoe2_rules):
    """DE Sicilian bonus: Serjeants (and Elite Serjeants) can build Donjons."""
    for unit in ("serjeant", "elite_serjeant"):
        can_build = list(_attr(aoe2_rules, unit, "can_build"))
        assert "donjon" in can_build, unit


def test_serjeant_is_feudal_age_trained(aoe2_rules):
    """DE: the Serjeant is trained from the Feudal Age, at the Donjon."""
    reqs = list(_attr(aoe2_rules, "serjeant", "requirements"))
    assert "feudal_age" in reqs
    assert "castle_age" not in reqs


def test_serjeant_matches_de_stats(aoe2_rules):
    """DE: 55 food / 25 gold, 16 s, HP 50, attack 5, armor 2/1, speed 0.95."""
    cost = list(_attr(aoe2_rules, "serjeant", "cost"))
    assert cost[0] == 25 * P  # gold
    assert cost[2] == 55 * P  # food
    assert _attr(aoe2_rules, "serjeant", "time_cost") == 16 * P
    assert _attr(aoe2_rules, "serjeant", "hp_max") == 50 * P
    assert _attr(aoe2_rules, "serjeant", "mdg") == 5 * P
    assert _attr(aoe2_rules, "serjeant", "mdf") == 2 * P
    assert _attr(aoe2_rules, "serjeant", "rdf") == 1 * P


def test_elite_serjeant_upgrade_cost_matches_de(aoe2_rules):
    """DE: the Elite Serjeant upgrade costs 800 food / 675 gold, 45 s."""
    cost = list(_attr(aoe2_rules, "elite_serjeant", "cost"))
    assert cost[0] == 675 * P  # gold
    assert cost[2] == 800 * P  # food
    assert _attr(aoe2_rules, "elite_serjeant", "time_cost") == 45 * P
    assert _attr(aoe2_rules, "elite_serjeant", "hp_max") == 85 * P
    assert _attr(aoe2_rules, "elite_serjeant", "mdg") == 11 * P


def test_sicilian_castle_still_trains_serjeant(aoe2_rules):
    can_train = list(_attr(aoe2_rules, "sicilian_castle", "can_train"))
    assert "serjeant" in can_train


def test_donjon_is_the_prerequisite_for_archery_range_and_stable(aoe2_rules):
    """DE: the Donjon is "required for" the Archery Range and the Stable."""
    for civ_building in ("sicilian_archery", "sicilian_stable"):
        reqs = list(_attr(aoe2_rules, civ_building, "requirements"))
        assert "donjon" in reqs, civ_building


def test_hoardings_affects_the_donjon(aoe2_rules):
    """DE: Hoardings gives +1000 HP to Castles *and* to Donjons."""
    effect = aoe2_rules.get("hoardings", "effect")
    rows = (
        effect
        if isinstance(effect, list) and effect and isinstance(effect[0], list)
        else [effect]
    )
    targets = []
    for row in rows:
        tokens = [str(t) for t in (row or [])]
        if "hp" not in tokens:
            continue
        idx = tokens.index("hp")
        if idx + 1 >= len(tokens):
            continue
        assert tokens[idx + 1] == str(1000 * P), tokens
        targets.extend(tokens[idx + 2:])
    assert "donjon" in targets, targets
    assert "aoe_castle" in targets, targets


# ---------------------------------------------------------------------------
# 7. Runtime behaviour (engine paths, not just rules text)
# ---------------------------------------------------------------------------


class _FakeDonjon:
    """Minimal stand-in for the Donjon unit.

    Real units expose ``<stat>_bonus`` accumulators and the weapon/armor
    instance slots; the engine's bonus handlers need both.
    """

    def __init__(self, player, rules):
        cls = rules.unit_class("donjon")
        self.type_name = "donjon"
        self.player = player
        self.expanded_is_a = set(getattr(cls, "expanded_is_a", ()) or ())
        self.expanded_is_a.add("donjon")
        self.can_upgrade_to = ()
        for stat in ("mdf", "rdf", "mdg", "rdg", "rdg_cd", "mdg_cd",
                     "sight_range", "hp", "hp_max", "speed"):
            setattr(self, stat + "_bonus", 0)
        self.mdf_bonus = 0
        self.rdf_bonus = 0
        self.time_cost_bonus = 0
        self.time_cost_percent_bonus = 0.0
        # Base stats of the Dark Age Donjon.
        self.hp_max = 625 * P
        self.hp = 625 * P
        self.mdf = 0
        self.rdf = 6 * P
        self.mdg = 0
        self.rdg = 0
        self.rdg_cd = 2 * P
        self.rdg_range = 8 * P
        self.rdg_minimal_range = 1 * P
        # No weapon / armor instance -> the building branch of
        # ``Phase.apply_pool_to_unit``.
        self._weapon_instances = {}
        self._armor_instance = None

    def notify(self, *_a, **_k):
        pass


def _sicilian_player(installed, units=()):
    from soundrts.definitions import rules as global_rules

    global_rules._dict = installed._dict
    global_rules.classes = installed.classes

    player = type(
        "Player",
        (),
        {
            "faction": "sicilians",
            "units": list(units),
            "upgrades": [],
            "_phase_bonus_pool": [],
            "allied_victory": [],
            "forbidden_techs": [],
            "research_time_percent_bonus": 0.0,
        },
    )()
    player.allied_victory = [player]
    return player


def test_donjon_hp_grows_flat_per_age(installed):
    """DE: 625 (Dark) -> 1250 (Feudal) -> 1500 (Castle) -> 2250 (Imperial).

    The age rows are flat deltas, so the runtime HP after each age change
    must match DE exactly.
    """
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _sicilian_player(installed)
    donjon = _FakeDonjon(player, installed)
    player.units = [donjon]

    assert donjon.hp_max == 625 * P
    apply_faction_on_phase_effects(player, "feudal_age")
    assert donjon.hp_max == 1250 * P, donjon.hp_max
    apply_faction_on_phase_effects(player, "castle_age")
    assert donjon.hp_max == 1500 * P, donjon.hp_max
    apply_faction_on_phase_effects(player, "imperial_age")
    assert donjon.hp_max == 2250 * P, donjon.hp_max


def test_donjon_armor_grows_one_per_age(installed):
    """DE armor: melee 0/1/2/3, pierce 6/7/8/9."""
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _sicilian_player(installed)
    donjon = _FakeDonjon(player, installed)
    player.units = [donjon]

    assert (donjon.mdf, donjon.rdf) == (0, 6 * P)
    for phase, expected in (
        ("feudal_age", (1 * P, 7 * P)),
        ("castle_age", (2 * P, 8 * P)),
        ("imperial_age", (3 * P, 9 * P)),
    ):
        apply_faction_on_phase_effects(player, phase)
        assert (donjon.mdf, donjon.rdf) == expected, phase


def test_donjon_gets_its_attack_in_the_feudal_age(installed):
    """The Dark Age Donjon is unarmed; the Feudal Age Donjon shoots 5 pierce."""
    from soundrts.worldphase import apply_faction_on_phase_effects

    player = _sicilian_player(installed)
    donjon = _FakeDonjon(player, installed)
    player.units = [donjon]

    assert not donjon.rdg
    apply_faction_on_phase_effects(player, "feudal_age")
    assert donjon.rdg == 5 * P, donjon.rdg
    assert donjon.rdg_range == 8 * P, donjon.rdg_range
    assert donjon.rdg_seq_times == 1
    assert donjon.rdg_seq_secondary == 1
    assert donjon.rdg_seq_secondary_live == 1

    apply_faction_on_phase_effects(player, "castle_age")
    assert donjon.rdg_seq_times == 2
    apply_faction_on_phase_effects(player, "imperial_age")
    assert donjon.rdg_seq_times == 3


def test_donjon_built_after_the_age_change_gets_the_pooled_bonus(installed):
    """A Donjon built in the Castle Age must already be 1500 HP / 2+8 armor.

    Buildings never run ``update_weapons`` / ``update_armors``, so the
    phase pool has to be applied to them at creation.
    """
    from soundrts.worldphase import (
        Phase,
        apply_faction_on_phase_effects,
    )

    player = _sicilian_player(installed)
    apply_faction_on_phase_effects(player, "feudal_age")
    apply_faction_on_phase_effects(player, "castle_age")

    donjon = _FakeDonjon(player, installed)
    player.units = [donjon]
    Phase.apply_pool_to_unit(donjon)

    assert donjon.hp_max == 1500 * P, donjon.hp_max
    assert donjon.mdf == 2 * P, donjon.mdf
    assert donjon.rdf == 8 * P, donjon.rdf
    assert donjon.rdg == 5 * P, donjon.rdg
    assert donjon.rdg_seq_times == 2, donjon.rdg_seq_times


# ---------------------------------------------------------------------------
# 6. Localisation
# ---------------------------------------------------------------------------


def test_donjon_title_exists_in_style(aoe2_rules):
    from soundrts.definitions import Style

    style = Style()
    style.load(
        (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8"),
    )
    assert style.get("donjon", "title", warn_if_not_found=False)


def test_donjon_name_is_localised_in_every_language(aoe2_rules):
    """Every language pack must carry a name for the Donjon (id 5544)."""
    from soundrts.definitions import Style

    style = Style()
    style.load(
        (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8"),
    )
    missing = []
    for ui_dir in sorted((ROOT / "mods" / "aoe2").glob("ui-*")):
        tts = ui_dir / "tts.txt"
        if not tts.exists():
            continue
        ids = set()
        for line in tts.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or " " not in line:
                continue
            head = line.split(" ", 1)[0]
            if head.isdigit():
                ids.add(head)
        if "5544" not in ids:
            missing.append(ui_dir.name)
    assert not missing, f"languages without a Donjon name: {missing}"
