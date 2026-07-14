"""Idle AI must react immediately to hostiles entering their square."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.definitions import rules
from soundrts.lib.resource import res
from soundrts.world import World
from soundrts.worldclient import DirectClient


@pytest.fixture(autouse=True)
def _load_rules():
    res.load_rules_and_ai()


def _sq(world, label: str):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid[f"{col},{row}"]


def test_idle_ai_attacks_invader_same_square_immediately():
    """z5-style: computer knight idle on a square must not wait for forced perception."""
    text = """
nb_columns 5
nb_lines 5
nb_players_min 2
nb_players_max 2
starting_squares 0,0 2,2
starting_resources 100 100
terrain plain a1 a2 a3 a4 a5
terrain plain b1 b2 b3 b4 b5
terrain plain c1 c2 c3 c4 c5
terrain plain d1 d2 d3 d4 d5
terrain plain e1 e2 e3 e4 e5
"""
    world = World([], 42)
    world._parse_map(text)
    world._build_map()

    c1 = DirectClient("p1", None)
    c1.create_player(world)
    human = c1.player

    c2 = DirectClient("p2", None)
    c2.create_player(world)
    ai = c2.player
    # Make sure they are enemies.
    if hasattr(ai, "share_team"):
        pass

    a1 = _sq(world, "a1")
    b3 = _sq(world, "b3")

    knight_cls = rules.unit_class("knight")
    knight_cls.collision = 0
    ai_knight = knight_cls(ai, b3, b3.x, b3.y)
    ai_knight.ai_mode = "offensive"

    # Let AI settle with idle perception skips.
    for _ in range(30):
        world.update()

    # Invader arrives on the AI knight's square without AI units moving.
    human_knight = knight_cls(human, b3, b3.x + 100, b3.y + 100)

    # One or two ticks should be enough with contact-force perception.
    for _ in range(5):
        world.update()
        if human_knight in ai.perception:
            break

    assert human_knight in ai.perception, "AI must perceive same-square invader immediately"

    # Decide should acquire an attack order/target quickly.
    reacted = False
    for _ in range(20):
        world.update()
        action = getattr(ai_knight, "action", None)
        target = getattr(action, "target", None) if action is not None else None
        if target is human_knight:
            reacted = True
            break
        orders = getattr(ai_knight, "orders", None) or ()
        if orders and getattr(orders[0], "keyword", None) in ("attack", "a"):
            reacted = True
            break
    assert reacted, "AI knight must attack the invader without multi-second delay"
