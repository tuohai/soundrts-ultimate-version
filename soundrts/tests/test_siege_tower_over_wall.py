"""Siege tower: train wiring, infantry-only load, unload over blocked exits."""
from __future__ import annotations

import logging
import os
import sys
import types
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.lib.resource import res
    from soundrts.worldorders.transport import UnloadAllOrder
    from soundrts.worldunit.world_transport import CreatureTransport

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)


@pytest.fixture
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def test_siege_tower_rules_transport_and_workshop(aoe2_loaded):
    from soundrts.definitions import rules

    assert rules.get("siege_tower", "transport_capacity") == 10
    assert rules.get("siege_tower", "can_unload_over_walls") == 1
    assert "infantry" in (rules.get("siege_tower", "transport_passenger_types") or [])
    assert "workshop" in (rules.get_makers("siege_tower") or [])
    raw = (rules._dict.get("workshop") or {}).get("_rules_can_train") or []
    assert "siege_tower" in raw


def test_battering_ram_garrison_load_bonus(aoe2_loaded):
    from soundrts.definitions import rules

    assert rules.get("battering_ram", "transport_capacity") == 6
    assert "infantry" in (rules.get("battering_ram", "transport_passenger_types") or [])
    cls = rules.unit_class("battering_ram")
    assert cls.load_bonus.get("speed") == 0.05
    assert cls.load_bonus.get("mdg_vs.building") == 10
    # Upgrades inherit capacity / bonus via is_a
    for name in ("capped_ram", "siege_ram"):
        u = rules.unit_class(name)
        assert u.transport_capacity == 6
        assert u.load_bonus.get("speed") == 0.05


def test_transport_passenger_minus_excludes_even_if_type_allowed():
    class Tower(CreatureTransport):
        transport_passenger_types = ("infantry", "archer_unit", "-cavalry")
        inside = None

    tower = Tower.__new__(Tower)
    foot_archer = types.SimpleNamespace(
        type_name="aoe_archer", expanded_is_a=("archer_unit", "soldier")
    )
    cav_archer = types.SimpleNamespace(
        type_name="cavalry_archer",
        expanded_is_a=("archer_unit", "cavalry", "soldier"),
    )
    assert tower._can_accept_passenger(foot_archer)
    assert not tower._can_accept_passenger(cav_archer)


def test_transport_passenger_types_filters_non_infantry():
    class Tower(CreatureTransport):
        transport_passenger_types = ("infantry",)
        inside = None

    tower = Tower.__new__(Tower)
    infantry = types.SimpleNamespace(
        type_name="militia", expanded_is_a=("infantry", "soldier")
    )
    cavalry = types.SimpleNamespace(
        type_name="aoe_knight", expanded_is_a=("cavalry", "soldier")
    )
    assert tower._can_accept_passenger(infantry)
    assert not tower._can_accept_passenger(cavalry)
    assert tower.have_enough_space(cavalry) is False


def test_aoe2_defensive_building_garrison(aoe2_loaded):
    from soundrts.definitions import rules

    tc = rules.unit_class("town_center")
    assert tc.transport_capacity == 15
    types = list(tc.transport_passenger_types or [])
    assert "peasant" in types
    assert "-cavalry" in types
    assert "archer_unit" in (tc.passenger_attack_types or [])

    tower = rules.unit_class("scouttower")
    assert tower.transport_capacity == 5
    keep = rules.unit_class("keeptower")
    assert keep.transport_capacity == 5  # inherited

    castle = rules.unit_class("aoe_castle")
    assert castle.transport_capacity == 20
    assert "cavalry" in (castle.transport_passenger_types or [])

    assert rules.unit_class("cannontower").transport_capacity == 0


def test_unload_over_walls_when_adjacent_exit_blocked():
    far = types.SimpleNamespace(id="far", is_ground=True, high_ground=False)
    exit_to_far = types.SimpleNamespace(
        other_side=types.SimpleNamespace(place=far),
        is_blocked=lambda: True,
    )
    near = types.SimpleNamespace(id="near", exits=[exit_to_far])

    calls = []

    unit = types.SimpleNamespace(
        airground_type="ground",
        can_unload_over_walls=1,
        blocked_exit=None,
        place=near,
        inside=types.SimpleNamespace(objects=[object()]),
        unload_all=lambda place=None: calls.append(place) or 1,
        speed=1,
    )
    unit.player = types.SimpleNamespace(
        get_object_by_id=lambda _id: far,
        updated_target=lambda t: t,
    )
    unit.notify = lambda *_a, **_k: None
    unit.move_to = lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must not path"))

    order = UnloadAllOrder(unit, [far.id])
    order.on_queued()
    assert not order.is_impossible
    order.move_to_or_fail = lambda *_a, **_k: (_ for _ in ()).throw(
        AssertionError("must unload over wall, not path")
    )
    order.execute()
    assert calls == [far]
    assert order.is_complete


def test_unload_over_walls_requires_flag():
    far = types.SimpleNamespace(id="far")
    exit_to_far = types.SimpleNamespace(
        other_side=types.SimpleNamespace(place=far),
        is_blocked=lambda: True,
    )
    near = types.SimpleNamespace(id="near", exits=[exit_to_far])
    moved = []

    unit = types.SimpleNamespace(
        airground_type="ground",
        can_unload_over_walls=0,
        blocked_exit=None,
        place=near,
        inside=types.SimpleNamespace(objects=[object()]),
        unload_all=lambda place=None: 0,
        speed=1,
    )
    unit.player = types.SimpleNamespace(
        get_object_by_id=lambda _id: far,
        updated_target=lambda t: t,
    )
    unit.notify = lambda *_a, **_k: None

    order = UnloadAllOrder(unit, [far.id])
    order.on_queued()
    order.move_to_or_fail = lambda place: moved.append(place)
    order.execute()
    assert moved == [far]


def test_unload_over_walls_skips_unblocked_exit():
    far = types.SimpleNamespace(id="far")
    exit_to_far = types.SimpleNamespace(
        other_side=types.SimpleNamespace(place=far),
        is_blocked=lambda: False,
    )
    near = types.SimpleNamespace(id="near", exits=[exit_to_far])
    moved = []

    unit = types.SimpleNamespace(
        airground_type="ground",
        can_unload_over_walls=1,
        blocked_exit=None,
        place=near,
        inside=types.SimpleNamespace(objects=[object()]),
        unload_all=lambda place=None: 0,
        speed=1,
    )
    unit.player = types.SimpleNamespace(
        get_object_by_id=lambda _id: far,
        updated_target=lambda t: t,
    )
    unit.notify = lambda *_a, **_k: None

    order = UnloadAllOrder(unit, [far.id])
    order.on_queued()
    order.move_to_or_fail = lambda place: moved.append(place)
    order.execute()
    assert moved == [far]
