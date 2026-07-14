"""Leaving a square must keep meadows/exits Tab-selectable via fog memory."""
from __future__ import annotations

import os
import types

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.definitions import rules
from soundrts.lib.resource import res
from soundrts.world import World
from soundrts.worldclient import DirectClient
from soundrts.clientgame.game_unit_control import _object_choices
from soundrts.clientgame.game_navigation import update_fog_of_war


@pytest.fixture(autouse=True)
def _load_rules():
    res.load_rules_and_ai()


def _world_from_map(text: str):
    world = World([], 42)
    world._parse_map(text)
    world._build_map()
    client = DirectClient("p1", None)
    client.create_player(world)
    return world, client.player


def _sq(world, label: str):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid[f"{col},{row}"]


def _map_5x5():
    return """
nb_columns 5
nb_lines 5
nb_players_min 1
nb_players_max 1
starting_squares 0,0
starting_resources 100 100
nb_meadows_by_square 4
terrain plain a1 a2 a3 a4 a5
terrain plain b1 b2 b3 b4 b5
terrain plain c1 c2 c3 c4 c5
terrain plain d1 d2 d3 d4 d5
terrain plain e1 e2 e3 e4 e5
"""


def _tab_choices(player, world, square):
    iface = types.SimpleNamespace(
        world=world,
        player=player,
        place=square,
        zoom_mode=False,
        zoom=None,
        immersion=False,
        group=[],
        x=square.x / 1000,
        y=square.y / 1000,
        o=90,
        dobjets={},
        memory=set(),
        perception=set(),
        scouted_squares=set(),
        scouted_before_squares=set(),
        scout_info=set(),
        target=None,
        collision_debug=None,
        _side_filter="all",
        _type_filter="all",
        an_order_requiring_a_target_is_selected=False,
    )
    iface.distance = lambda o: 0
    iface.memory = set(player.memory_for_display())
    iface.perception = set(player.perception)
    iface.scouted_squares = set(player.observed_squares)
    iface.scouted_before_squares = set(player.observed_before_squares)
    update_fog_of_war(iface)
    return _object_choices(iface, 1, [])


def test_tab_finds_meadows_after_unit_leaves_square():
    world, player = _world_from_map(_map_5x5())
    a1 = _sq(world, "a1")
    a2 = _sq(world, "a2")
    a2.ensure_meadows(4)

    th_cls = rules.unit_class("townhall")
    th_cls.collision = 0
    th_cls(player, a1, a1.x, a1.y)
    peasant_cls = rules.unit_class("peasant")
    peasant_cls.collision = 0
    peasant = peasant_cls(player, a2, a2.x, a2.y)

    for _ in range(40):
        world.update()

    assert a2 in player.observed_squares
    before = _tab_choices(player, world, a2)
    assert any(c.type_name == "meadow" for c in before)

    peasant.move_to(a1, a1.x, a1.y)
    for _ in range(80):
        world.update()

    assert a2 not in player.observed_squares
    after = _tab_choices(player, world, a2)
    meadows = [c for c in after if c.type_name == "meadow"]
    assert len(meadows) >= 4
    assert all(c.is_memory for c in meadows)


def test_exit_pair_both_sides_tab_after_crossing():
    """Seeing a2's south exit must also fog-remember a1's north exit."""
    from pathlib import Path

    text = (
        Path(__file__).resolve().parents[2] / "res" / "multi" / "b1.txt"
    ).read_text(encoding="utf-8")
    world, player = _world_from_map(text)
    # Pick adjacent squares linked by a path exit pair.
    a_side = None
    b_side = None
    for s in world.grid.values():
        for e in getattr(s, "exits", ()) or ():
            other = getattr(e, "other_side", None)
            if other is None or other.place is None:
                continue
            if getattr(e, "type_name", None) != "path":
                continue
            a_side, b_side = s, other.place
            break
        if a_side is not None:
            break
    assert a_side is not None and b_side is not None

    # Base on a third square if possible; else on a_side then walk.
    spawn = a_side
    for s in world.grid.values():
        if s is not a_side and s is not b_side:
            spawn = s
            break

    th_cls = rules.unit_class("townhall")
    th_cls.collision = 0
    th_cls(player, spawn, spawn.x, spawn.y)
    peasant_cls = rules.unit_class("peasant")
    peasant_cls.collision = 0
    peasant = peasant_cls(player, a_side, a_side.x, a_side.y)

    for _ in range(40):
        world.update()
    # Cross to the other side so one exit is live and the far side may be fog.
    peasant.move_to(b_side, b_side.x, b_side.y)
    for _ in range(80):
        world.update()

    # Move away so both sides are fog (not currently observed).
    peasant.move_to(spawn, spawn.x, spawn.y)
    for _ in range(100):
        world.update()

    assert a_side not in player.observed_squares
    assert b_side not in player.observed_squares

    tab_a = _tab_choices(player, world, a_side)
    tab_b = _tab_choices(player, world, b_side)
    exits_a = [c for c in tab_a if getattr(c, "is_an_exit", False)]
    exits_b = [c for c in tab_b if getattr(c, "is_an_exit", False)]
    assert exits_a, "a-side must still Tab-find its exit under fog"
    assert exits_b, "b-side must still Tab-find its exit under fog"
