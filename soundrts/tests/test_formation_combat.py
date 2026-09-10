# -*- coding: utf-8 -*-
"""Headless: do AoE2 formations change real combat, not just slot math?"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.world_formation import _spec, after_group_order, assign_formation_slots
    from soundrts.worldclient import DirectClient
    from soundrts.worldunit import Creature

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

import pytest

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)

_MAP = """
nb_columns 3
nb_lines 3
nb_players_min 1
nb_players_max 2
starting_squares a1 c3
starting_resources 0 0
terrain plain a1 a2 a3 b1 b2 b3 c1 c2 c3
west_east_paths 1,1 2,1 1,2 2,2 1,3 2,3
south_north_paths 1,1 2,1 3,1 1,2 2,2 3,2
"""

_FORMATIONS = (
    "formation_line",
    "formation_box",
    "formation_staggered",
    "formation_flank",
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
    res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _sq(world, label):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid["%s,%s" % (col, row)]


def _world(seed=7):
    world = World([], seed)
    world._parse_map(_MAP)
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    world.treaty_until_time = 0
    p1 = DirectClient("p1", None)
    p1.faction = "britons"
    p1.alliance = "1"
    p1.create_player(world)
    p2 = DirectClient("p2", None)
    p2.faction = "britons"
    p2.alliance = "2"
    p2.create_player(world)
    p1.player.population = 200
    p2.player.population = 200
    return world, p1.player, p2.player


def _spawn(cls, player, place, x, y):
    unit = cls(player, place, x, y)
    unit.collision = 0
    return unit


def _see_each_other(a_units, b_units, pa, pb):
    for u in a_units:
        pb.perception.add(u)
    for u in b_units:
        pa.perception.add(u)


def _place_layout(units, layout, anchor, facing=90):
    if layout == "blob":
        for u in units:
            u.x = int(anchor.x)
            u.y = int(anchor.y)
        return
    spec = _spec(layout)
    assert spec is not None, layout
    for u in units:
        u.formation = layout
    slots = assign_formation_slots(units, anchor, spec, facing=facing)
    for unit, _place, x, y in slots:
        unit.x = int(x)
        unit.y = int(y)


def _alive(units):
    return [u for u in units if getattr(u, "hp", 0) > 0 and getattr(u, "place", None)]


def _hp_sum(units):
    return sum(int(getattr(u, "hp", 0) or 0) for u in _alive(units))


def _ticks(ms):
    return max(1, int(ms / VIRTUAL_TIME_INTERVAL))


def _group_go(player, units, dest, use_formation):
    player.group = list(units)
    for u in units:
        u.group = player.group
        u.take_order(["go", dest.id], forget_previous=True)
    if use_formation:
        after_group_order(player.group, "go")


def _mangonel_splash(aoe2_loaded, layout):
    world, p1, p2 = _world(11)
    sq = _sq(world, "b2")
    cx, cy = int(sq.x), int(sq.y)
    mang_cls = rules.unit_class("mangonel")
    mil_cls = rules.unit_class("militia")
    mang_cls.collision = 0
    mil_cls.collision = 0
    mang = _spawn(mang_cls, p1, sq, cx - 4500, cy)
    mang.mdg_crit_rate = 0
    mang.ai_mode = "guard"
    militia = [_spawn(mil_cls, p2, sq, cx, cy) for _ in range(8)]
    for m in militia:
        m.hp_max = 400 * PRECISION
        m.hp = 400 * PRECISION
        m.mdg = 0
        m.rdg = 0
        m.mdf = 0
        m.rdf = 0
        m.ai_mode = "guard"
    _place_layout(militia, layout, sq, facing=180)
    primary = min(militia, key=lambda u: (u.x - mang.x) ** 2 + (u.y - mang.y) ** 2)
    _see_each_other([mang], militia, p1, p2)
    world._update_buckets()
    hp0 = {id(u): int(u.hp) for u in militia}
    mang.take_order(["attack", primary.id], imperative=True, forget_previous=True)
    for _ in range(_ticks(8000)):
        world.update()
        lost = sum(hp0[id(u)] - int(u.hp) for u in militia)
        if lost > 0:
            extras = sum(1 for u in militia if u is not primary and int(u.hp) < hp0[id(u)])
            splash_hp = sum(hp0[id(u)] - int(u.hp) for u in militia if u is not primary)
            return {
                "layout": layout,
                "primary_hp": hp0[id(primary)] - int(primary.hp),
                "extras": extras,
                "splash_hp": splash_hp,
                "total_hp": lost,
            }
    return {
        "layout": layout,
        "primary_hp": 0,
        "extras": 0,
        "splash_hp": 0,
        "total_hp": 0,
    }


def test_headless_mangonel_splash_blob_is_worse_than_named_formations(aoe2_loaded):
    """Mangonel blast radius is 1m; line spacing 1.5m so a blob shares splash, a line does not."""
    blob = _mangonel_splash(aoe2_loaded, "blob")
    formed = {name: _mangonel_splash(aoe2_loaded, name) for name in _FORMATIONS}
    print("mangonel splash:", blob, formed)
    assert blob["total_hp"] > 0, blob
    assert blob["extras"] >= 3, blob
    for name, row in formed.items():
        assert row["extras"] < blob["extras"], (name, row, blob)
        assert row["splash_hp"] < blob["splash_hp"], (name, row, blob)


def _scorpion_pierce(aoe2_loaded, layout):
    world, p1, p2 = _world(13)
    sq = _sq(world, "b2")
    cx, cy = int(sq.x), int(sq.y)
    scorp_cls = rules.unit_class("scorpion")
    mil_cls = rules.unit_class("militia")
    scorp_cls.collision = 0
    mil_cls.collision = 0
    scorp = _spawn(scorp_cls, p1, sq, cx - 500, cy)
    scorp.rdg_crit_rate = 0
    scorp.rdg_hit_rate = 100 * PRECISION
    scorp.ai_mode = "guard"
    militia = [_spawn(mil_cls, p2, sq, cx + 1500, cy) for _ in range(6)]
    for m in militia:
        m.hp_max = 200 * PRECISION
        m.hp = 200 * PRECISION
        m.mdg = 0
        m.rdg = 0
        m.mdf = 0
        m.rdf = 0
        m.ai_mode = "guard"
    _place_layout(militia, layout, sq, facing=0)
    primary = max(militia, key=lambda u: u.x)
    _see_each_other([scorp], militia, p1, p2)
    world._update_buckets()
    hits = []
    orig = Creature.receive_hit

    def wrapped(self, damage, attacker, *a, **k):
        before = int(getattr(self, "hp", 0) or 0)
        orig(self, damage, attacker, *a, **k)
        after = int(getattr(self, "hp", 0) or 0)
        if attacker is scorp and after < before:
            hits.append(self.id)

    Creature.receive_hit = wrapped
    try:
        scorp.take_order(["attack", primary.id], imperative=True, forget_previous=True)
        for _ in range(_ticks(5000)):
            world.update()
            if hits:
                break
    finally:
        Creature.receive_hit = orig
    return {"layout": layout, "hit_count": len(hits), "ids": hits}


def test_headless_scorpion_hits_more_units_in_a_line_than_a_box(aoe2_loaded):
    line = _scorpion_pierce(aoe2_loaded, "formation_line")
    box = _scorpion_pierce(aoe2_loaded, "formation_box")
    staggered = _scorpion_pierce(aoe2_loaded, "formation_staggered")
    print("scorpion pierce:", line, box, staggered)
    assert line["hit_count"] >= 2, line
    assert box["hit_count"] <= line["hit_count"], (box, line)
    assert staggered["hit_count"] <= line["hit_count"], (staggered, line)


def _first_arrival(aoe2_loaded, use_formation):
    world, p1, p2 = _world(17)
    start = _sq(world, "a1")
    dest = _sq(world, "a2")
    mil_cls = rules.unit_class("militia")
    knight_cls = rules.unit_class("aoe_knight")
    mil_cls.collision = 0
    knight_cls.collision = 0
    militia = [_spawn(mil_cls, p1, start, start.x - 800 + i * 400, start.y) for i in range(4)]
    knights = [
        _spawn(knight_cls, p1, start, start.x - 800 + i * 400, start.y + 400) for i in range(4)
    ]
    army = militia + knights
    for u in army:
        u.formation = "formation_line"
        u.ai_mode = "defensive"
    _group_go(p1, army, dest, use_formation=use_formation)
    world._update_buckets()
    first_knight = first_militia = None
    spread_when_both = None
    for i in range(_ticks(25000)):
        world.update()
        if first_knight is None and any(u.place is dest for u in knights if u.hp > 0):
            first_knight = world.time
        if first_militia is None and any(u.place is dest for u in militia if u.hp > 0):
            first_militia = world.time
        if first_knight is not None and first_militia is not None:
            spread_when_both = abs(first_knight - first_militia)
            break
    knights_in = sum(1 for u in knights if u.place is dest)
    militia_in = sum(1 for u in militia if u.place is dest)
    return {
        "use_formation": use_formation,
        "first_knight_ms": first_knight,
        "first_militia_ms": first_militia,
        "spread_ms": spread_when_both,
        "knights_in": knights_in,
        "militia_in": militia_in,
        "caps": [int(getattr(u, "_formation_speed_cap", 0) or 0) for u in army],
    }


def test_headless_keep_pace_arrives_as_one_wave(aoe2_loaded):
    blob = _first_arrival(aoe2_loaded, use_formation=False)
    formed = _first_arrival(aoe2_loaded, use_formation=True)
    print("keep_pace arrival:", blob, formed)
    assert any(c > 0 for c in formed["caps"]), formed
    assert all(c == 0 for c in blob["caps"]), blob
    assert formed["spread_ms"] is not None, formed
    assert blob["spread_ms"] is not None, blob
    assert formed["first_knight_ms"] > blob["first_knight_ms"], (formed, blob)
    assert formed["spread_ms"] < blob["spread_ms"], (formed, blob)
    assert formed["spread_ms"] <= 1500, formed


def _mixed_fight(aoe2_loaded, layout, seed=19):
    """Same-square brawl: 6 militia + 6 archers vs 8 militia walking in from the west."""
    world, p1, p2 = _world(seed)
    sq = _sq(world, "b2")
    mil_cls = rules.unit_class("militia")
    archer_cls = rules.unit_class("aoe_archer")
    mil_cls.collision = 0
    archer_cls.collision = 0
    melee = [_spawn(mil_cls, p1, sq, sq.x, sq.y) for _ in range(6)]
    archers = [_spawn(archer_cls, p1, sq, sq.x, sq.y) for _ in range(6)]
    attackers = melee + archers
    for u in attackers:
        u.formation = "formation_line" if layout != "blob" else ""
        u.ai_mode = "offensive"
    if layout != "blob":
        for u in attackers:
            u.group = attackers
    _place_layout(attackers, layout if layout != "blob" else "blob", sq, facing=180)
    defenders = [
        _spawn(mil_cls, p2, sq, sq.x - 3500 + (i % 4) * 200, sq.y - 400 + (i // 4) * 200)
        for i in range(8)
    ]
    for u in defenders:
        u.ai_mode = "offensive"
    _see_each_other(attackers, defenders, p1, p2)
    world._update_buckets()
    for _ in range(_ticks(30000)):
        world.update()
        if not _alive(attackers) or not _alive(defenders):
            break
    archer_hp = _hp_sum(archers)
    return {
        "layout": layout,
        "atk_alive": len(_alive(attackers)),
        "def_alive": len(_alive(defenders)),
        "atk_hp": _hp_sum(attackers),
        "def_hp": _hp_sum(defenders),
        "archers_alive": len(_alive(archers)),
        "archer_hp": archer_hp,
        "melee_alive": len(_alive(melee)),
        "time_ms": world.time,
    }


def test_headless_mixed_fight_line_keeps_archers_alive(aoe2_loaded):
    """Front rank soaks the charge; back-rank archers are still up after melee dies."""
    blob = _mixed_fight(aoe2_loaded, "blob")
    formed = _mixed_fight(aoe2_loaded, "formation_line")
    print("mixed fight blob:", blob)
    print("mixed fight line:", formed)
    start_hp = (6 * 40 + 6 * 30 + 8 * 40) * PRECISION
    assert blob["atk_hp"] + blob["def_hp"] < start_hp
    assert formed["atk_hp"] + formed["def_hp"] < start_hp
    assert formed["archers_alive"] > 0, formed
    assert formed["melee_alive"] == 0, formed
    assert formed["archers_alive"] > formed["melee_alive"]


def test_headless_go_to_enemy_breaks_slots(aoe2_loaded):
    world, p1, p2 = _world(23)
    start = _sq(world, "a1")
    dest = _sq(world, "b2")
    mil_cls = rules.unit_class("militia")
    mil_cls.collision = 0
    army = [_spawn(mil_cls, p1, start, start.x - 800 + i * 400, start.y) for i in range(4)]
    foe = _spawn(mil_cls, p2, dest, dest.x, dest.y)
    foe.ai_mode = "guard"
    for u in army:
        u.formation = "formation_line"
        u.ai_mode = "offensive"
    _see_each_other(army, [foe], p1, p2)
    _group_go(p1, army, dest, use_formation=True)
    assert any(getattr(u, "_formation_slot", None) for u in army)
    p1.group = list(army)
    for u in army:
        u.group = p1.group
        u.take_order(["go", foe.id], forget_previous=True)
    after_group_order(p1.group, "go")
    assert all(u.orders and u.orders[0].keyword == "go" for u in army)
    assert all(getattr(u, "_formation_slot", None) is None for u in army)
    assert all(getattr(u, "_formation_focus_fire", 0) for u in army)


def test_headless_stand_ground_does_not_walk(aoe2_loaded):
    world, p1, p2 = _world(29)
    sq = _sq(world, "b2")
    mil_cls = rules.unit_class("militia")
    mil_cls.collision = 0
    guards = [_spawn(mil_cls, p1, sq, sq.x + 2500, sq.y - 400 + i * 400) for i in range(3)]
    start = [(int(u.x), int(u.y)) for u in guards]
    for u in guards:
        u.formation = "formation_line"
        u.ai_mode = "guard"
        u.group = guards
    foe = _spawn(mil_cls, p2, sq, sq.x - 3500, sq.y)
    foe.ai_mode = "offensive"
    foe.mdg = 0
    foe.rdg = 0
    _see_each_other(guards, [foe], p1, p2)
    world._update_buckets()
    for _ in range(_ticks(4000)):
        world.update()
    for u, (x, y) in zip(guards, start):
        assert abs(int(u.x) - x) < 400, (int(u.x), x, int(u.y), y)
        assert abs(int(u.y) - y) < 400, (int(u.x), x, int(u.y), y)


def test_headless_blocker_soaks_focus_fire_before_back_rank(aoe2_loaded):
    world, p1, p2 = _world(31)
    sq = _sq(world, "b2")
    mil_cls = rules.unit_class("militia")
    archer_cls = rules.unit_class("aoe_archer")
    mil_cls.collision = 0
    archer_cls.collision = 0
    cx, cy = int(sq.x), int(sq.y)
    wall = [_spawn(mil_cls, p2, sq, cx, cy - 600 + i * 400) for i in range(4)]
    archer = _spawn(archer_cls, p2, sq, cx + 2500, cy)
    archer.mdg = 0
    archer.rdg = 0
    archer.ai_mode = "guard"
    for u in wall:
        u.ai_mode = "guard"
        u.mdg = 0
        u.rdg = 0
        u._formation_slot = (sq, int(u.x), int(u.y))
    walker = _spawn(mil_cls, p1, sq, cx - 3500, cy)
    walker.ai_mode = "offensive"
    walker._formation_focus_fire = 1
    _see_each_other([walker], wall + [archer], p1, p2)
    world._update_buckets()
    hits = []
    orig = Creature.receive_hit

    def wrapped(self, damage, attacker, *a, **k):
        before = int(getattr(self, "hp", 0) or 0)
        orig(self, damage, attacker, *a, **k)
        after = int(getattr(self, "hp", 0) or 0)
        if attacker is walker and after < before:
            hits.append(self)

    Creature.receive_hit = wrapped
    try:
        walker.take_order(["attack", archer.id], imperative=True, forget_previous=True)
        for _ in range(_ticks(15000)):
            world.update()
            if hits:
                break
    finally:
        Creature.receive_hit = orig
    assert hits, "walker never landed a hit"
    assert hits[0] in wall, hits[0].id
    assert hits[0] is not archer
