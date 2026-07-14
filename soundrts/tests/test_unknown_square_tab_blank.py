"""Unknown (never scouted) squares must stay blank for Tab / place summary.

Reproduce with z5: start on a1/c1, peer-path exit pairing can fog-remember the
far side of a path on a2/c2/a3/c3 before those squares are ever visited.
Arrow-navigating the camera onto such an unknown square must not Tab-find
「向南小径」等出口。
"""
from __future__ import annotations

import os
import types
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.clientgame.game_navigation import update_fog_of_war
from soundrts.clientgame.game_unit_control import _object_choices, place_summary
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
    return world.grid[(col, row)]


def _world_z5():
    text = (Path(__file__).resolve().parents[2] / "res" / "multi" / "z5.txt").read_text(
        encoding="utf-8"
    )
    world = World([], 42)
    world._parse_map(text)
    world._build_map()
    client = DirectClient("p1", None)
    client.create_player(world)
    return world, client.player


def _iface(player, world, square):
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
        _known_resource_places=set(),
        _known_item_ids=set(),
        new_enemy_units=[],
    )
    iface.distance = lambda o: 0
    iface.memory = set(player.memory_for_display())
    iface.perception = set(player.perception)
    iface.scouted_squares = set(player.observed_squares)
    iface.scouted_before_squares = set(player.observed_before_squares)
    update_fog_of_war(iface)
    return iface


def _tab_exits(iface):
    return [
        c
        for c in _object_choices(iface, 1, [])
        if getattr(c, "is_an_exit", False)
    ]


def test_z5_unknown_a3_blank_after_seeing_a1_paths():
    """Start near a1: peer-path memory must not make unknown a3 Tab-able."""
    world, player = _world_z5()
    a1 = _sq(world, "a1")
    a2 = _sq(world, "a2")
    a3 = _sq(world, "a3")

    th_cls = rules.unit_class("townhall")
    th_cls.collision = 0
    th_cls.sight_range = 1  # keep vision local so a2 can leave fog
    th_cls(player, a1, a1.x, a1.y)
    knight_cls = rules.unit_class("knight")
    knight_cls.collision = 0
    knight_cls.sight_range = 1
    knight = knight_cls(player, a1, a1.x, a1.y)

    for _ in range(60):
        world.update()

    assert a1 in player.observed_squares or a1 in player.observed_before_squares
    assert a3 not in player.observed_squares
    assert a3 not in player.observed_before_squares

    # Even if far-side exits were peer-memorized onto a2/a3...
    iface_a3 = _iface(player, world, a3)
    assert _tab_exits(iface_a3) == []
    assert place_summary(iface_a3, a3) == []

    # ...while a1 (known) still has Tab targets.
    iface_a1 = _iface(player, world, a1)
    assert _tab_exits(iface_a1) or any(
        getattr(c, "type_name", None) for c in _object_choices(iface_a1, 1, [])
    )

    # Visit a2 then leave: a2 becomes fog (scouted_before) — Tab exits OK.
    knight.move_to(a2, a2.x, a2.y)
    for _ in range(80):
        world.update()
    knight.move_to(a1, a1.x, a1.y)
    for _ in range(80):
        world.update()

    assert a2 in player.observed_before_squares
    # With limited sight, a2 may still linger in observed via TH; force camera fog case
    # by checking Tab when treating a2 as scouted_before-only in the iface.
    iface_a2_fog = _iface(player, world, a2)
    iface_a2_fog.scouted_squares = set()
    iface_a2_fog.scouted_before_squares = {a2}
    assert _tab_exits(iface_a2_fog) or _object_choices(iface_a2_fog, 1, []), (
        "previously visited a2 under fog may still Tab static objects"
    )


def test_z5_unknown_c3_blank_from_c1_start():
    world, player = _world_z5()
    c1 = _sq(world, "c1")
    c3 = _sq(world, "c3")

    th_cls = rules.unit_class("townhall")
    th_cls.collision = 0
    th_cls(player, c1, c1.x, c1.y)
    peasant_cls = rules.unit_class("peasant")
    peasant_cls.collision = 0
    peasant_cls(player, c1, c1.x, c1.y)

    for _ in range(60):
        world.update()

    assert c3 not in player.observed_before_squares
    iface = _iface(player, world, c3)
    assert _tab_exits(iface) == []
    assert place_summary(iface, c3) == []
