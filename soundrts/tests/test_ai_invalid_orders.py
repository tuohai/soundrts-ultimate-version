"""Detect and prevent invalid orders issued by computer players.

Runs headless world simulation with multiple AI types, collects
``order_impossible`` notifications from computer-controlled units,
and asserts no order-menu TypeErrors (e.g. CaptureOrder.is_allowed).
"""
from __future__ import annotations

import os
import sys
import types
import warnings
from collections import Counter
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldentity import Entity
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldplayercomputer2 import Computer2
    from soundrts.worldorders import ORDERS_DICT
    from soundrts.worldorders.movement import CaptureOrder

sys.argv = saved_argv

ROOT = Path(__file__).resolve().parents[2]
M3 = ROOT / "res" / "multi" / "m3.txt"
JL6 = ROOT / "res" / "multi" / "jl6.txt"


@pytest.fixture(autouse=True)
def load_rules():
    res.load_rules_and_ai()


def _faction():
    return rules.factions[0] if rules.factions else "human_faction"


def _load_map(path: Path):
    world = World([], 42)
    world._parse_map(path.read_text(encoding="utf-8"))
    world._build_map()
    return world


def _populate(world, ai_specs):
    """ai_specs: list of (ai_type, alliance) tuples."""
    clients = []
    for i, (ai_type, alliance) in enumerate(ai_specs):
        if ai_type == "human":
            c = DirectClient(f"p{i}", None)
        else:
            c = DummyClient(ai_type)
        c.faction = _faction()
        c.alliance = alliance
        clients.append(c)
    world.populate_map(clients, random_starts=False)
    world._update_buckets()
    return world


def _hook_order_impossible(world):
    """Return a Counter of order_impossible reasons from computer units."""
    counts: Counter[str] = Counter()
    orig_notify = Entity.notify

    def patched_notify(self, event, universal=False):
        if (
            event.startswith("order_impossible")
            and getattr(self, "player", None) is not None
            and getattr(self.player, "is_computer_player", False)
        ):
            counts[event] += 1
        return orig_notify(self, event, universal)

    Entity.notify = patched_notify
    return counts, orig_notify


def _run_ticks(world, n: int):
    for _ in range(n):
        world.update()


def test_capture_order_menu_without_target_does_not_crash():
    """CaptureOrder.is_allowed requires target_id; menu() must not TypeError."""
    unit = types.SimpleNamespace(
        basic_skills={"attack", "go"},
        can_capture=1,
        player=types.SimpleNamespace(
            get_object_by_id=lambda _id: None,
            forbidden_techs=[],
        ),
    )
    unit.is_an_enemy = lambda _t: False
    # Regression: BasicOrder.menu calls is_allowed(unit) with no target.
    menu = CaptureOrder.menu(unit, strict=True)
    assert isinstance(menu, list)


def test_all_order_menus_callable_on_minimal_unit():
    """Every order class menu() must accept a minimal stub unit."""
    unit = types.SimpleNamespace(
        basic_skills=set(ORDERS_DICT.keys()),
        can_capture=1,
        can_switch_ai_mode=True,
        ai_mode="offensive",
        counterattack_enabled=False,
        inventory=[],
        can_use=[],
        can_use_skill=[],
        can_build=[],
        can_train=[],
        can_research=[],
        can_advance=[],
        can_upgrade_to=[],
        can_change_to=[],
        player=types.SimpleNamespace(
            get_object_by_id=lambda _id: None,
            forbidden_techs=[],
            has_all=lambda _r: True,
            check_count_limit=lambda _t: True,
            perception=set(),
            memory=set(),
        ),
        orders=[],
    )
    unit.is_an_enemy = lambda _t: False
    for name, cls in ORDERS_DICT.items():
        try:
            cls.menu(unit, strict=True)
        except TypeError as exc:
            pytest.fail(f"{name}.menu() raised TypeError: {exc}")
        except AttributeError:
            # Some menus need richer unit stubs; TypeError is what we guard against.
            pass


def test_choose_gather_target_skips_wrong_terrain_deposit():
    from soundrts.worldresource import Deposit

    deposit = Deposit.__new__(Deposit)
    deposit.place = types.SimpleNamespace(is_water=False, is_ground=True)
    deposit.resource_qty = 100
    comp = Computer.__new__(Computer)
    comp.perception = set()
    comp.memory = set()
    comp.units = []
    comp.square_is_dangerous = lambda _p: False
    comp.choose = lambda *a, **k: deposit
    comp._gather_target_ok = Computer._gather_target_ok.__get__(comp, Computer)
    comp._world_place_for_unit = lambda _w: types.SimpleNamespace(
        shortest_path_distance_to=lambda *a, **k: 1,
    )

    water_worker = types.SimpleNamespace(airground_type="water")
    assert comp._choose_water_gather_target(water_worker) is None

    ground_worker = types.SimpleNamespace(airground_type="ground")
    water_deposit = Deposit.__new__(Deposit)
    water_deposit.place = types.SimpleNamespace(is_water=True, is_ground=False)
    water_deposit.resource_qty = 100
    comp.choose = lambda *a, **k: water_deposit
    assert comp._choose_gather_target(ground_worker) is None



@pytest.mark.parametrize(
    "map_path,ai_specs,ticks",
    [
        (M3, [("intermediate", "1"), ("aggressive", "2")], 800),
        (JL6, [("advanced", "1"), ("easy", "2")], 800),
        (M3, [("ai2", "1"), ("ai2", "2")], 400),
    ],
)
def test_computer_players_issue_no_invalid_orders(map_path, ai_specs, ticks):
    if not map_path.is_file():
        pytest.skip(f"missing map {map_path}")
    world = _populate(_load_map(map_path), ai_specs)
    counts, orig_notify = _hook_order_impossible(world)
    try:
        _run_ticks(world, ticks)
    finally:
        Entity.notify = orig_notify

    computers = [
        p
        for p in world.players
        if isinstance(p, (Computer, Computer2))
    ]
    assert computers, "expected at least one computer player"

    # Report for debugging when test fails.
    if counts:
        summary = ", ".join(f"{k}={v}" for k, v in counts.most_common(10))
        pytest.fail(
            f"Computer units got order_impossible ({sum(counts)} total): {summary}"
        )
