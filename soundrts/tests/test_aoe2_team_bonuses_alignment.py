# -*- coding: utf-8 -*-
"""AoE2 DE team-bonus alignment tests (42 civilizations).

The AoE2 DE "team bonus" of a civilisation applies to *the player and all of
their allies*.  These tests check two things:

1. **Declarative** team bonuses (``team_on_phase <phase> <stat> <value>``)
   exist for every civilisation, with the canonical DE targets.
2. **Special** team bonuses that need dedicated engine support are wired up:

   ==========================================  ================================
   AoE2 DE team bonus                           engine support
   ==========================================  ================================
   Building repairs cost -25% (Georgians)       ``team_repair_cost_pct``
   Military buildings provide +5 population      ``team_military_building_pop``
   Outposts cost no stone (Ethiopians)          ``team_free_stone_buildings``
   Start with a free Llama (Incas)              ``team_start_free_llama``
   Relics generate food too (Burgundians)       ``team_relic_food``
   Relics visible at game start (Burmese)       ``team_relic_visible``
   Mounted Archers / Gunpowder train +25%       ``team_train_speed_pct``
   ==========================================  ================================

NOTE: rules values are stored PRECISION-scaled (x1000) by the engine, e.g.
``hp_max 75`` -> 75000.  Percentages (``-50%``) stay as strings.
"""
from __future__ import annotations

import json
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

    saved_dict = getattr(global_rules, "_dict", None)
    saved_classes = getattr(global_rules, "classes", None)
    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    yield aoe2_rules
    global_rules._dict = saved_dict
    if saved_classes is not None:
        global_rules.classes = saved_classes


@pytest.fixture(scope="module")
def de_truth():
    return json.loads((ROOT / "_de_truth.json").read_text(encoding="utf-8"))


def _race(aoe2_rules, faction):
    return aoe2_rules._dict.get(faction, {})


def _team_rows(aoe2_rules, faction):
    rows = _race(aoe2_rules, faction).get("team_on_phase_effects") or []
    return [list(r) for r in rows]


def _team_flat(aoe2_rules, faction):
    """All team bonus tokens as a single flat list of strings."""
    out = []
    for row in _team_rows(aoe2_rules, faction):
        out.extend(str(x) for x in row)
    return out


# --------------------------------------------------------------------------
# (1) Every civilisation has a team bonus
# --------------------------------------------------------------------------

# truth key -> rules faction name
FACTION_ALIASES = {
    "inca": "incas",
    "maya": "mayans",
    "malay": "malays",
}


def test_de_truth_covers_all_civilisations(de_truth):
    assert len(de_truth) == 42
    for key, value in de_truth.items():
        assert value.get("team"), f"{key} has no team bonus in _de_truth.json"


def test_every_civilisation_defines_a_team_bonus(aoe2_rules, de_truth):
    """Each of the 42 civs has at least one team bonus in rules.txt."""
    missing = []
    for key in de_truth:
        faction = FACTION_ALIASES.get(key, key)
        rows = _team_rows(aoe2_rules, faction)
        special = any(
            _race(aoe2_rules, faction).get(attr)
            for attr in (
                "team_repair_cost_pct",
                "team_military_building_pop",
                "team_free_stone_buildings",
                "team_start_free_llama",
                "team_relic_food",
                "team_relic_visible",
                "team_train_speed_pct",
                "team_farm_food_pct",
                "team_supplies_pct",
                "team_trade_capacity_pct",
                "team_share_research",
                "team_share_train",
                "team_share_steppe_lancer",
                "team_inventory_production_bonus_pct",
                "team_conversion_channel_bonus_pct",
            )
        )
        if not rows and not special:
            missing.append(faction)
    assert not missing, f"civilisations without a team bonus: {missing}"


# --------------------------------------------------------------------------
# (2) Declarative team bonuses: stat + value + canonical targets
# --------------------------------------------------------------------------

# faction -> (stat, value, [required targets])
# NOTE: precision stats (sight_range, rdg_range, hp, …) are PRECISION-scaled
# by the loader, so their stored value is the DE number x 1000.
DECLARATIVE_TEAM_BONUSES = {
    "armenians": ("sight_range", 2 * P, ["militia"]),
    "bohemians": ("time_cost", "-44%", ["trade_cart"]),
    "britons": ("time_cost", "-9%", ["aoe_archer"]),
    "bulgarians": ("time_cost", "-44%", ["forging"]),
    "byzantines": ("heal_cd", "-50%", ["monk"]),
    "celts": ("time_cost", "-17%", ["battering_ram"]),
    "cumans": ("hp", "33%", ["palisade_wall"]),
    "ethiopians": ("sight_range", 3 * P, ["outpost"]),
    "franks": ("sight_range", 2 * P, ["aoe_knight"]),
    "hindustanis": ("mdg_vs", ("building", "2"), ["scout_cavalry"]),
    "huns": ("time_cost", "-17%", ["scout_cavalry"]),
    "japanese": ("sight_range", 4 * P, ["galley"]),
    "khmer": ("rdg_range", 1 * P, ["scorpion"]),
    "koreans": ("sight_range", 3 * P, ["peasant"]),
    "lithuanians": ("time_cost", "-17%", ["monk"]),
    "malians": ("time_cost", "-44%", ["ballistics"]),
    "mongols": ("sight_range", 2 * P, ["scout_cavalry"]),
    "persians": ("mdg_vs", ("archer_unit", "2"), ["aoe_knight"]),
    "poles": ("mdg_vs", ("archer_unit", "1"), ["scout_cavalry"]),
    "portuguese": ("research_time", "-20%", []),
    "romans": ("rdg_minimal_range", -1 * P, ["scorpion"]),
    "saracens": ("mdg_vs", ("building", "2"), ["aoe_archer"]),
    "sicilians": ("sight_range", 5 * P, ["transport_ship"]),
    "spanish": ("trade_reward_bonus_pct", 25, []),
    "tatars": ("sight_range", 2 * P, ["cavalry_archer"]),
    "vikings": ("cost", None, ["shipyard"]),
}


@pytest.mark.parametrize("faction", sorted(DECLARATIVE_TEAM_BONUSES))
def test_declarative_team_bonus_stat_and_targets(aoe2_rules, faction):
    stat, value, targets = DECLARATIVE_TEAM_BONUSES[faction]
    rows = _team_rows(aoe2_rules, faction)
    matching = [r for r in rows if stat in [str(x) for x in r]]
    assert matching, f"{faction}: no team_on_phase row with stat {stat!r} (rows={rows})"
    row = matching[0]
    flat = [str(x) for x in row]
    assert stat in flat
    if value is not None:
        idx = flat.index(stat)
        got = flat[idx + 1]
        if stat == "mdg_vs":
            # mdg_vs <target> <value>  — the value is the third token.
            assert flat[idx + 1] == value[0], (
                f"{faction}: team bonus {stat} target is {flat[idx + 1]!r}, "
                f"expected {value[0]!r}"
            )
            got = flat[idx + 2]
            assert got == str(value[1]), (
                f"{faction}: team bonus {stat} value is {got!r}, "
                f"expected {value[1]!r}"
            )
        else:
            assert got == str(value) or got == value, (
                f"{faction}: team bonus {stat} value is {got!r}, expected {value!r}"
            )
    for target in targets:
        assert target in flat, f"{faction}: team bonus {stat} missing target {target!r}"


def test_sicilian_transport_ship_cost_discount_is_on_wood(aoe2_rules):
    """DE: Transport Ships cost -50%.

    ``transport_ship`` costs ``0 125 0 0`` (gold / wood / food / stone), so
    the discount must sit in slot 1 (wood), not slot 0.
    """
    rows = _team_rows(aoe2_rules, "sicilians")
    cost_rows = [r for r in rows if "cost" in [str(x) for x in r]]
    assert cost_rows
    flat = [str(x) for x in cost_rows[0]]
    idx = flat.index("cost")
    values = flat[idx + 1: idx + 5]
    assert values == ["0", "-50%", "0", "0"], values
    assert "transport_ship" in flat


def test_viking_dock_cost_discount_is_on_wood(aoe2_rules):
    """DE: Docks cost -15% (shipyard costs ``10 15 0 0`` -> wood is slot 1)."""
    rows = _team_rows(aoe2_rules, "vikings")
    cost_rows = [r for r in rows if "cost" in [str(x) for x in r]]
    assert cost_rows
    flat = [str(x) for x in cost_rows[0]]
    idx = flat.index("cost")
    values = flat[idx + 1: idx + 5]
    assert values == ["0", "-15%", "0", "0"], values


def test_mayan_wall_cost_discount_is_on_stone(aoe2_rules):
    """DE: Walls cost -50% (stone is slot 3)."""
    rows = _team_rows(aoe2_rules, "mayans")
    cost_rows = [r for r in rows if "cost" in [str(x) for x in r]]
    assert cost_rows
    flat = [str(x) for x in cost_rows[0]]
    idx = flat.index("cost")
    values = flat[idx + 1: idx + 5]
    assert values == ["0", "0", "0", "-50%"], values


# --------------------------------------------------------------------------
# (3) Special team bonuses: rules data
# --------------------------------------------------------------------------


def test_georgian_team_repair_cost_pct(aoe2_rules):
    assert _race(aoe2_rules, "georgians").get("team_repair_cost_pct") == -25


def test_slav_team_military_building_pop(aoe2_rules):
    rows = _race(aoe2_rules, "slavs").get("team_military_building_pop")
    assert rows
    flat = [str(x) for x in rows[0]]
    assert flat[0] == "5"
    assert "barracks" in flat
    # Castles are excluded by the DE wording.
    assert "aoe_castle" not in flat


def test_ethiopian_team_free_stone_buildings(aoe2_rules):
    rows = _race(aoe2_rules, "ethiopians").get("team_free_stone_buildings")
    assert rows
    flat = [str(x) for x in rows[0]]
    assert "outpost" in flat


def test_inca_team_start_free_llama(aoe2_rules):
    assert _race(aoe2_rules, "incas").get("team_start_free_llama") == 1


def test_burgundian_team_relic_food(aoe2_rules):
    assert _race(aoe2_rules, "burgundians").get("team_relic_food") == 1


def test_burmese_team_relic_visible(aoe2_rules):
    assert _race(aoe2_rules, "burmese").get("team_relic_visible") == 1


def test_magyar_team_train_speed_pct(aoe2_rules):
    rows = _race(aoe2_rules, "magyars").get("team_train_speed_pct")
    assert rows
    flat = [str(x) for x in rows[0]]
    assert flat[0] == "25"
    assert "cavalry_archer" in flat


def test_turk_team_train_speed_pct(aoe2_rules):
    rows = _race(aoe2_rules, "turks").get("team_train_speed_pct")
    assert rows
    flat = [str(x) for x in rows[0]]
    assert flat[0] == "25"
    assert "janissary" in flat


def test_spanish_trade_reward_bonus_is_raw_percent(aoe2_rules):
    """``trade_reward_bonus_pct`` is a raw percentage, not PRECISION-scaled.

    The market math computes ``amount * (1 + bonus / 100)``; a rules value
    of 25 must therefore stay 25 and not become 25000.
    """
    rows = _team_rows(aoe2_rules, "spanish")
    rows = [r for r in rows if "trade_reward_bonus_pct" in [str(x) for x in r]]
    assert rows
    flat = [str(x) for x in rows[0]]
    idx = flat.index("trade_reward_bonus_pct")
    assert flat[idx + 1] == "25"


# --------------------------------------------------------------------------
# (4) Special team bonuses: engine helpers
# --------------------------------------------------------------------------


def _player(faction, allies=()):
    p = SimpleNamespace(faction=faction, allied_victory=list(allies) or None)
    if not allies:
        p.allied_victory = (p,)
    return p


def test_team_repair_cost_pct_helper(installed):
    from soundrts.world_civ_bonuses import team_repair_cost_pct

    georgian = _player("georgians")
    plain = _player("britons")
    assert team_repair_cost_pct(georgian) == -25
    assert team_repair_cost_pct(plain) == 0
    # An ally with the bonus grants it to the whole team.
    assert team_repair_cost_pct(_player("britons", [georgian])) == -25


def test_team_military_building_pop_helper(installed):
    from soundrts.world_civ_bonuses import team_military_building_pop

    slav = _player("slavs")
    assert team_military_building_pop(slav) == 5
    assert team_military_building_pop(_player("britons")) == 0
    assert team_military_building_pop(_player("britons", [slav])) == 5


def test_team_free_stone_buildings_helper(installed):
    from soundrts.world_civ_bonuses import team_free_stone_buildings

    ethiopian = _player("ethiopians")
    assert "outpost" in team_free_stone_buildings(ethiopian)
    assert team_free_stone_buildings(_player("britons")) == ()
    assert "outpost" in team_free_stone_buildings(
        _player("britons", [ethiopian])
    )


def test_team_relic_food_helper(installed):
    from soundrts.world_civ_bonuses import team_relic_food

    assert team_relic_food(_player("burgundians")) == 1
    assert team_relic_food(_player("britons")) == 0


def test_team_relic_visible_helper(installed):
    from soundrts.world_civ_bonuses import team_relic_visible

    assert team_relic_visible(_player("burmese")) == 1
    assert team_relic_visible(_player("britons")) == 0


def test_team_start_free_llama_helper(installed):
    from soundrts.world_civ_bonuses import team_start_free_llama

    assert team_start_free_llama(_player("incas")) == 1
    assert team_start_free_llama(_player("britons")) == 0


def test_team_train_speed_pct_helper(installed):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_civ_bonuses import team_train_speed_pct

    magyar = _player("magyars")
    ca = global_rules.unit_class("cavalry_archer")
    scout = global_rules.unit_class("scout_cavalry")
    assert ca is not None and scout is not None
    assert team_train_speed_pct(magyar, ca) == 25
    assert team_train_speed_pct(magyar, scout) == 0
    # An ally with the bonus grants it to the whole team.
    assert team_train_speed_pct(_player("britons", [magyar]), ca) == 25


def test_team_train_speed_pct_applies_to_derived_units(installed):
    """``mangudai`` is a Magyar unique that ``is_a`` the cavalry archer line."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_civ_bonuses import team_train_speed_pct

    magyar = _player("magyars")
    for name in ("mangudai", "elite_mangudai", "heavy_cavalry_archer"):
        cls = global_rules.unit_class(name)
        assert cls is not None, name
        assert team_train_speed_pct(magyar, cls) == 25, name


# --------------------------------------------------------------------------
# (5) Engine integration
# --------------------------------------------------------------------------


def test_georgian_repair_cost_is_reduced(installed):
    """A Georgian building repairs 25% cheaper than the same building owned
    by a non-Georgian player."""
    from soundrts.worldunit.world_attributes import CreatureAttributes

    plain = CreatureAttributes.__new__(CreatureAttributes)
    plain.cost = (1000 * P, 0, 0, 0)
    plain.time_cost = 100 * P
    plain.player = _player("britons")

    georgian = CreatureAttributes.__new__(CreatureAttributes)
    georgian.cost = (1000 * P, 0, 0, 0)
    georgian.time_cost = 100 * P
    georgian.player = _player("georgians")

    plain_cost = list(plain.repair_cost)[0]
    geo_cost = list(georgian.repair_cost)[0]
    assert plain_cost > 0
    assert geo_cost == int(plain_cost * 0.75)


def test_ethiopian_outpost_stone_cost_is_zero(installed):
    """The Ethiopian team bonus zeroes the stone cost of Outposts."""
    from soundrts.definitions import rules as global_rules
    from soundrts.worldorders.base import ComplexOrder

    outpost = global_rules.unit_class("outpost")
    assert outpost is not None
    base = list(outpost.cost)
    assert base[3] > 0, "the outpost must normally cost stone"

    modified = list(base)
    ComplexOrder._merge_team_free_stone_cost(
        _player("ethiopians"), outpost, modified
    )
    assert modified[3] == 0
    assert modified[1] == base[1]

    # A non-Ethiopian player pays the normal price.
    other = list(base)
    ComplexOrder._merge_team_free_stone_cost(_player("britons"), outpost, other)
    assert other[3] == base[3]


def test_magyar_train_order_is_faster(installed):
    """A Magyar mounted archer trains 25% faster than a plain one."""
    from soundrts.definitions import rules as global_rules
    from soundrts.worldorders.production import TrainOrder
    from soundrts.world_build_rules import unit_train_time

    ca = global_rules.unit_class("cavalry_archer")
    assert ca is not None

    class _Host:
        player = None

    host = _Host()

    def _time_for(player):
        host.player = player
        order = TrainOrder.__new__(TrainOrder)
        order.unit = host
        order.type = ca
        return order._train_type_time()

    plain = _time_for(_player("britons"))
    magyar = _time_for(_player("magyars"))
    base = int(unit_train_time(ca))
    assert base > 0
    assert plain == base
    assert magyar == max(1, base * 100 // 125)


def test_slav_military_building_gives_extra_population(installed):
    """The Slavs team bonus adds +5 population for military buildings."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_civ_bonuses import is_military_building

    barracks = global_rules.unit_class("barracks")
    castle = global_rules.unit_class("aoe_castle")
    market = global_rules.unit_class("market")
    assert barracks is not None and castle is not None and market is not None
    names = (
        "barracks",
        "archery_range",
        "stables",
        "blacksmith",
        "workshop",
        "university",
        "monastery",
        "scouttower",
        "guardtower",
        "keeptower",
        "cannontower",
    )
    assert is_military_building(barracks, names)
    assert not is_military_building(castle, names)
    assert not is_military_building(market, names)


def test_team_bonus_helpers_are_importable(installed):
    """Every helper documented in ``world_civ_bonuses`` must exist."""
    from soundrts import world_civ_bonuses

    for name in (
        "team_repair_cost_pct",
        "team_military_building_pop",
        "team_free_stone_buildings",
        "team_start_free_llama",
        "team_relic_food",
        "team_relic_visible",
        "team_train_speed_pct",
    ):
        assert callable(getattr(world_civ_bonuses, name)), name
