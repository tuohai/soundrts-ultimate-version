# -*- coding: utf-8 -*-
"""AoE2 DE Town Center: empty TC does not fire; garrison adds building shots."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from soundrts.definitions import Rules
from soundrts.worldunit.world_transport import (
    GARRISON_SHOT_DEFAULT_CAP,
    CreatureTransport,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    aoe2 = ROOT / "mods" / "aoe2" / "rules.txt"
    if not aoe2.is_file():
        pytest.skip("aoe2 mod not present")
    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        aoe2.read_text(encoding="utf-8"),
    )
    return r


class _TC(CreatureTransport):
    garrison_shots = 1
    base_shots = 0
    max_garrison_shots = 10
    passenger_attack_types = ["archer_unit", "peasant"]


def _passenger(type_name, *parents, hp=1):
    return SimpleNamespace(
        type_name=type_name,
        expanded_is_a=parents,
        hp=hp,
    )


def _tc(*inside):
    tc = _TC.__new__(_TC)
    tc.inside = SimpleNamespace(objects=list(inside))
    return tc


def test_rules_register_garrison_shot_ints():
    assert "garrison_shots" in Rules.int_properties
    assert "base_shots" in Rules.int_properties
    assert "max_garrison_shots" in Rules.int_properties


def test_generic_tc_rules_empty_does_not_fire(aoe2_rules):
    for name in ("town_center", "townhall"):
        assert aoe2_rules.get(name, "garrison_shots") == 1
        assert aoe2_rules.get(name, "base_shots") == 0
        assert aoe2_rules.get(name, "max_garrison_shots") == 10
        assert aoe2_rules.get(name, "rdg")  # still 5 damage per shot


def test_teuton_tc_fires_when_empty(aoe2_rules):
    assert aoe2_rules.get("teuton_town_center", "garrison_shots") == 1
    assert aoe2_rules.get("teuton_town_center", "base_shots") == 5
    assert aoe2_rules.get("teuton_town_center", "transport_capacity") == 25


def test_towers_and_castles_still_fire_empty(aoe2_rules):
    for name in ("scouttower", "guardtower", "keeptower", "aoe_castle"):
        assert not aoe2_rules.get(name, "garrison_shots")
        assert aoe2_rules.get(name, "rdg")


def test_empty_tc_zero_shots():
    tc = _tc()
    assert tc.garrison_shot_count() == 0
    assert tc._garrison_shots_prevent_attack()
    assert tc.garrison_shot_volley() is None


def test_one_villager_one_shot():
    tc = _tc(_passenger("peasant", "worker"))
    assert tc.garrison_shot_count() == 1
    assert not tc._garrison_shots_prevent_attack()
    times, interval = tc.garrison_shot_volley()
    assert times == 1
    assert interval == 0


def test_archers_add_shots_infantry_do_not():
    tc = _tc(
        _passenger("aoe_archer", "archer_unit"),
        _passenger("militia", "infantry"),
        _passenger("monk", "cleric"),
    )
    assert tc.garrison_shot_count() == 1


def test_garrison_shot_cap():
    vils = [_passenger("peasant") for _ in range(15)]
    tc = _tc(*vils)
    assert tc.garrison_shot_count() == GARRISON_SHOT_DEFAULT_CAP
    times, _interval = tc.garrison_shot_volley()
    assert times == 10


def test_teuton_empty_five_shots():
    tc = _tc()
    tc.base_shots = 5
    assert tc.garrison_shot_count() == 5
    assert not tc._garrison_shots_prevent_attack()
    times, interval = tc.garrison_shot_volley()
    assert times == 5
    assert interval == 0.05


def test_flag_off_is_unused():
    class Tower(CreatureTransport):
        garrison_shots = 0
        base_shots = 0
        rdg = 5

    t = Tower.__new__(Tower)
    t.inside = SimpleNamespace(objects=[])
    assert t.garrison_shot_count() is None
    assert not t._garrison_shots_prevent_attack()


def test_passengers_do_not_fire_themselves_from_garrison_shot_building():
    from soundrts.combat.attack_action import AttackActionMixin

    class U(AttackActionMixin):
        is_inside = True
        type_name = "peasant"
        expanded_is_a = ["peasant"]
        place = SimpleNamespace(
            container=SimpleNamespace(
                garrison_shots=1,
                passenger_attack_types=["archer_unit", "peasant"],
            )
        )

    assert U.__new__(U)._can_attack_from_inside() is False
