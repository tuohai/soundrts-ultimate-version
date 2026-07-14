"""Partial-square vision (sight < square_width) and script-NPC fog isolation."""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION
from soundrts.lib.resource import res
from soundrts.world import World
from soundrts.worldclient import DirectClient, DummyClient


@pytest.fixture(autouse=True)
def _load_rules():
    res.load_rules_and_ai()


def _sq(world, label: str):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid[f"{col},{row}"]


def test_catapult_sees_zoomed_knight_on_adjacent_wide_square():
    """sg4-style: square_width 15, catapult sight 14 — edge approach must reveal.

    When sight_range < square_width, neighbors are only partially observed.
    Zooming units toward the shared edge must still enter perception via
    Euclidean sight, otherwise range-12 weapons never fire across the edge.
    """
    text = """
square_width 15
nb_columns 3
nb_lines 1
nb_players_min 2
nb_players_max 2
starting_squares 0,0 2,0
starting_resources 100 100
west_east_paths a1 b1
terrain plain a1 b1 c1
"""
    world = World([], 42)
    world._parse_map(text)
    world._build_map()
    # Engine stores square_width in PRECISION units after full load; mirror that.
    if world.square_width < 1000:
        world.square_width = int(world.square_width * PRECISION)

    c1 = DirectClient("p1", None)
    c1.create_player(world)
    human = c1.player

    c2 = DirectClient("p2", None)
    c2.create_player(world)
    ai = c2.player

    a1 = _sq(world, "a1")
    b1 = _sq(world, "b1")
    mid_x = (a1.x + b1.x) // 2

    cat_cls = rules.unit_class("catapult")
    cat_cls.collision = 0
    cat = cat_cls(ai, a1, mid_x - PRECISION // 2, a1.y)
    assert cat.sight_range < world.square_width

    knight_cls = rules.unit_class("knight")
    knight_cls.collision = 0
    knight = knight_cls(human, b1, mid_x + PRECISION // 2, b1.y)

    for _ in range(15):
        world.update()
        if knight in ai.perception:
            break

    assert knight in ai.perception, (
        "catapult must perceive edge-zoomed knight on adjacent wide square"
    )
    assert cat.can_attack(knight) or getattr(cat, "can_attack_if_in_range", lambda t: False)(
        knight
    )


def test_script_npc_allied_vision_is_self_only():
    """computer_only timers NPCs must not share fog with other ``ai`` litter."""
    text = """
nb_columns 3
nb_lines 1
nb_players_min 1
nb_players_max 1
starting_squares 0,0
starting_resources 100 100
terrain plain a1 b1 c1
computer_only 0 0 b1 1 knight
computer_only 0 0 c1 1 knight
"""
    world = World([], 7)
    world._parse_map(text)
    world._build_map()
    DirectClient("p1", None).create_player(world)
    # computer_only slots from the map:
    for computer_start in world.computers_starts:
        DummyClient(neutral=computer_start[3] if len(computer_start) >= 4 else False).create_player(
            world
        )
    for p in world.players:
        p.init_alliance()

    npcs = [p for p in world.players if p.is_script_npc]
    assert len(npcs) >= 2
    a, b = npcs[0], npcs[1]
    # Still diplomatically allied under "ai" (no fratricide), …
    assert b in a.allied or a.client.alliance == b.client.alliance == "ai"
    # …but fog is isolated.
    assert a.allied_vision == [a]
    assert b.allied_vision == [b]


def test_sg4_style_same_square_enemies_visible_without_moving():
    """Start-square co-spawn (sg4 b1 etc.) must enter perception while idle."""
    from pathlib import Path

    from soundrts.mapfile import Map

    raw = Path("res/multi/sg4.txt").read_bytes()
    m = Map.loads(raw, "sg4.txt")
    world = World(seed=1)
    world.load_and_build_map(m)
    client = DirectClient("p1", None)
    world.populate_map([client], random_starts=False)
    human = world.players[0]

    same_square_enemies = []
    for p in world.players:
        if p is human:
            continue
        for u in p.units:
            if u.place and any(hu.place is u.place for hu in human.units):
                same_square_enemies.append(u)
    assert same_square_enemies, "sg4 should co-spawn enemies on human start"

    for _ in range(10):
        world.update()

    seen = [e for e in same_square_enemies if e in human.perception]
    assert seen, (
        "idle human must perceive same-square start enemies "
        f"(0/{len(same_square_enemies)} in perception)"
    )
    assert not human._unseen_hostile_on_owned_squares()
