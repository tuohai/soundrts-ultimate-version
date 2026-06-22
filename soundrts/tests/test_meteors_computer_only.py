"""res/rules.txt 流星（meteors）应能伤害 computer_only 地图单位。

回归：多条 computer_only 行会创建多个 Computer 玩家；若邻居缓存键
不含玩家 id，先被查询的空电脑会污染缓存，导致 get_objects2 / harm
找不到其它电脑格上的单位。
"""
from __future__ import annotations

import os
import sys
import warnings

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import soundrts.worldunit  # noqa: F401

from soundrts import config

config.debug_mode = 0
config.mods = ""

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.definitions import rules
        from soundrts.mapfile import Map
        from soundrts.world import World
        from soundrts.worldclient import DirectClient
finally:
    sys.argv = _saved_argv


def _load_rules():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())


def _map_two_computer_only_lines():
    return """
square_width 12
nb_columns 15
nb_lines 1
west_east_paths a1 b1 c1 d1 e1 f1 g1 h1 i1 j1 k1 l1 m1 n1 o1
nb_players_min 1
nb_players_max 1
starting_squares a1
player 1000 1000 a1 1 mage
computer_only 0 0 c1 5 footman
computer_only 0 0 o1 10 footman
"""


def test_meteors_harm_computer_only_with_multiple_computer_players():
    _load_rules()
    m = Map.loads(_map_two_computer_only_lines().encode("utf-8"), "two_co.txt")
    world = World(seed=1)
    world.load_and_build_map(m)
    world.populate_map([DirectClient("p1", None)], random_starts=False)
    world._update_buckets()

    human = world.players[0]
    o1_computer = world.players[2]
    footmen = [u for u in o1_computer.units if u.type_name == "footman"]
    assert len(footmen) == 10

    sq = footmen[0].place
    Meteors = rules.unit_class("meteors")
    effect = Meteors(human, sq, sq.x, sq.y)

    hp_before = sum(u.hp for u in footmen)
    for _ in range(50):
        effect.harm_nearby_units()
        world._update_buckets()
    hp_after = sum(u.hp for u in footmen)

    assert hp_after < hp_before, "meteors should damage computer_only units at o1"


def test_can_harm_repairable_matches_mechanical_not_healable_units():
    from soundrts.world.world_objects import WorldObjectsMixin

    class _HarmWorld(WorldObjectsMixin):
        harm_target_types = {}

    world = _HarmWorld()
    meteors = rules.unit_class("meteors")
    old_tags = meteors.harm_target_type
    try:
        meteors.harm_target_type = ["repairable"]
        world.harm_target_types.clear()
        assert world.can_harm("meteors", "townhall") is True
        assert world.can_harm("meteors", "footman") is False
    finally:
        meteors.harm_target_type = old_tags
        world.harm_target_types.clear()
