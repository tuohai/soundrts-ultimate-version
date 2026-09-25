"""击杀动物落下的食物尸体（food_carcass / food_livestock）在 Tab 候选里
应该排在其他矿床之前，方便玩家立即定位采集。

回归：之前尸体和其他矿床共享 ``p = 1 + resource_id / 100`` 优先级，
金矿（p=1.00）/ 石矿（p=1.01）排在尸体（p=1.02）之前，
导致击杀落点在金矿/石矿附近的尸体 Tab 一次定位不到。
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]

from soundrts.clientgame import game_unit_control as guc

sys.argv = saved


def _player_no_enemy():
    p = types.SimpleNamespace()
    p.is_an_enemy = lambda o: False
    return p


def _interface_no_order(player):
    """Interface stub mimicking ``an_order_requiring_a_target_is_selected = False``."""
    return types.SimpleNamespace(
        an_order_requiring_a_target_is_selected=False,
        player=player,
        distance=lambda o: 0,
    )


def _make_deposit(type_name, qty, resource_type):
    """Minimal Deposit stub for _priority() tests."""
    return types.SimpleNamespace(
        type_name=type_name,
        qty=qty,
        resource_type=resource_type,
        title=type_name,
        is_repairable=False,
        is_a_building_land=False,
    )


def _priority(o, interface):
    return guc._priority(interface, o, prioritize_items=False)[0]


def test_food_carcass_outranks_other_deposits():
    """food_carcass / food_livestock should outrank gold_mine / stone_mine / orchard."""
    player = _player_no_enemy()
    interface = _interface_no_order(player)

    carcass = _make_deposit("food_carcass", 80, "resource3")
    livestock = _make_deposit("food_livestock", 40, "resource3")
    gold = _make_deposit("gold_mine", 200, "resource1")
    stone = _make_deposit("stone_mine", 300, "resource2")
    orchard = _make_deposit("orchard", 250, "resource3")

    p_carcass = _priority(carcass, interface)
    p_livestock = _priority(livestock, interface)
    p_gold = _priority(gold, interface)
    p_stone = _priority(stone, interface)
    p_orchard = _priority(orchard, interface)

    assert p_carcass < p_gold, (
        f"food_carcass priority {p_carcass} should outrank gold_mine {p_gold}"
    )
    assert p_carcass < p_stone, (
        f"food_carcass priority {p_carcass} should outrank stone_mine {p_stone}"
    )
    assert p_livestock < p_gold, (
        f"food_livestock priority {p_livestock} should outrank gold_mine {p_gold}"
    )
    assert p_livestock < p_stone, (
        f"food_livestock priority {p_livestock} should outrank stone_mine {p_stone}"
    )
    # also outrank orchard (same resource_type) — the whole point is the
    # "carcass" wins over any plain food deposit sharing the same square.
    assert p_carcass < p_orchard


def test_food_carcass_still_behind_pickup_and_enemy():
    """Threats and pickup items must still outrank the carcass."""
    player = types.SimpleNamespace()
    player.is_an_enemy = lambda o: True  # mark all as enemy
    interface = _interface_no_order(player)
    # Without prioritize_items, the enemy branch (p=0.5) should fire.
    carcass = _make_deposit("food_carcass", 80, "resource3")
    p_enemy_carcass = _priority(carcass, interface)
    assert p_enemy_carcass == 0.5, (
        f"carcass flagged as enemy should keep enemy priority {p_enemy_carcass}"
    )

    # Switch player to no-enemy, but force prioritize_items=True with a
    # pickup item so the ground-item branch fires.
    player.is_an_enemy = lambda o: False

    pickup = types.SimpleNamespace(
        type_name="item",
        qty=0,
        resource_type=None,
        title="potion",
        default_order="pickup",
        player=None,
        is_repairable=False,
        is_a_building_land=False,
    )
    p_pickup = guc._priority(interface, pickup, prioritize_items=True)[0]
    assert p_pickup == 0.25

    p_carcass = _priority(carcass, interface)
    assert p_carcass > p_pickup, (
        f"carcass {p_carcass} should still trail pickup {p_pickup}"
    )


def test_priority_source_has_carcass_branch():
    """Source-level guard: the carcass branch must be in the priority code."""
    src = Path(__file__).resolve().parents[1].joinpath(
        "clientgame", "game_unit_control.py"
    ).read_text(encoding="utf-8")
    assert '"food_carcass", "food_livestock"' in src, (
        "missing food_carcass/food_livestock priority branch in _priority()"
    )
    assert "p = 0.75" in src
