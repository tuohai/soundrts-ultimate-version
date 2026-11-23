# -*- coding: utf-8 -*-
"""敌军刷新（respawn）—— RPG 式的「怪物重生」。

背景：
  地图 ``res/multi/z5.txt`` 的 b3 格里有一大波敌军（20 步兵、20 弓箭手、
  20 骑士、20 投石机……）。玩家把这批守军全杀了，对局就结束了 ——
  但这类地图（zombie planet）本来的玩法是**像 RPG 一样无限刷怪**。

新增两个东西：
  * 规则关键字 ``respawn_time <秒>`` —— 写在单位/建筑定义上，
    被摧毁后多久在原地刷新（0 = 永不刷新，默认）。
  * 地图语法 ``respawn <类型> <秒>`` —— 写在 ``computer_only`` 行里，
    逐类型覆盖规则里的 ``respawn_time``。

规则：
  * 刷新出来的单位是**全新**的（满血、无 buff、属于原主人）。
  * 可刷新的单位**不参与失败判定**：把它们全杀了，敌人也不宣布失败。
"""
from __future__ import annotations

from pathlib import Path

from soundrts.lib.nofloat import PRECISION

ROOT = Path(__file__).resolve().parents[2]


def _source(*path_parts):
    return ROOT.joinpath(*path_parts).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 规则关键字
# ---------------------------------------------------------------------------
def test_respawn_time_registered_in_definitions():
    src = _source("soundrts", "definitions.py")
    assert '"respawn_time"' in src


def test_respawn_time_parsed_as_seconds():
    """``respawn_time`` 在规则里写秒，加载后是毫秒。"""
    from soundrts.worldunit.world_attributes import CreatureAttributes

    d = {"respawn_time": 60}
    CreatureAttributes.interpret(d)
    assert d["respawn_time"] == 60 * PRECISION


def test_respawn_time_defaults_to_never_respawn():
    """没写就是 0 = 永不刷新（保持旧行为）。"""
    from soundrts.worldunit.worldcreature import Creature

    assert Creature.respawn_time == 0


def test_respawn_time_lands_on_the_unit_class():
    """规则里写了 ``respawn_time`` 的类型，类上确实有这个属性。"""
    from soundrts.definitions import Rules

    rules = Rules()
    rules.load(_source("res", "rules.txt"))
    # res/rules.txt 里的类型默认不带 respawn_time。
    footman = rules.unit_class("footman")
    assert footman is not None
    assert footman.respawn_time == 0


# ---------------------------------------------------------------------------
# 地图语法
# ---------------------------------------------------------------------------
def test_respawn_token_parsed_out_of_a_computer_only_line():
    """``respawn <类型> <秒>`` 从单位列表里摘出来，剩下的还是单位列表。"""
    from soundrts.world.world_map import WorldMapMixin

    items = [
        "20",
        "footman",
        "20",
        "archer",
        "respawn",
        "footman",
        "10",
        "respawn",
        "archer",
        "60",
    ]
    filtered, overrides = WorldMapMixin._strip_respawn_from_items(
        WorldMapMixin, items
    )
    assert filtered == ["20", "footman", "20", "archer"]
    assert overrides == {"footman": 10, "archer": 60}


def test_respawn_zero_means_never():
    """``respawn <类型> 0`` 表示这个类型不刷新。"""
    from soundrts.world.world_map import WorldMapMixin

    filtered, overrides = WorldMapMixin._strip_respawn_from_items(
        WorldMapMixin, ["footman", "respawn", "footman", "0"]
    )
    assert filtered == ["footman"]
    assert overrides == {"footman": 0}


def test_respawn_overrides_survive_on_the_start_slot():
    """覆盖值要挂在 start slot 上（``computers_starts``）。"""
    from soundrts.world.world_core import (
        set_start_slot_respawn_overrides,
        start_slot_respawn_overrides,
    )

    slot = [["res"], [], []]
    set_start_slot_respawn_overrides(slot, {"footman": 10})
    assert start_slot_respawn_overrides(slot) == {"footman": 10}
    assert start_slot_respawn_overrides([["res"], [], []]) == {}


# ---------------------------------------------------------------------------
# 刷新队列
# ---------------------------------------------------------------------------
class _FakeWorld:
    def __init__(self, now=0):
        self.time = now
        self.players = []


class _FakeUnit:
    """足够跑 ``schedule_respawn`` / ``respawn_time_for`` 的假单位。"""

    def __init__(self, world, place, player, respawn_time=0, override=None):
        self.world = world
        self.place = place
        self.player = player
        self.type_name = "footman"
        self.respawn_time = respawn_time
        if override is not None:
            self._respawn_time_override = override


class _FakePlace:
    def __init__(self, world):
        self.world = world
        self.objects = []
        self.x = 0
        self.y = 0
        self.is_inside_place = False


class _FakePlayer:
    def __init__(self, world):
        self.world = world
        self.units = []
        self.has_been_defeated = False
        self.is_playing = True

    def add_unit(self, unit_cls, place, population_cost=None, respawn_time_override=None):
        unit = unit_cls(self, place, 0, 0)
        if respawn_time_override is not None:
            unit._respawn_time_override = respawn_time_override
        self.units.append(unit)
        return unit


def test_schedule_respawn_queues_the_dead_unit():
    """死亡后排进队列，到期时间 = 现在 + 刷新时限。"""
    from soundrts.world_respawn import schedule_respawn

    world = _FakeWorld(now=1000)
    place = _FakePlace(world)
    player = _FakePlayer(world)
    unit = _FakeUnit(world, place, player, respawn_time=30 * PRECISION)

    deadline = schedule_respawn(unit)
    assert deadline == 1000 + 30 * PRECISION
    assert len(world._respawn_queue) == 1


def test_schedule_respawn_does_nothing_without_a_respawn_time():
    """没写 ``respawn_time`` 的单位不会排队。"""
    from soundrts.world_respawn import schedule_respawn

    world = _FakeWorld(now=1000)
    place = _FakePlace(world)
    player = _FakePlayer(world)
    unit = _FakeUnit(world, place, player, respawn_time=0)

    assert schedule_respawn(unit) is None
    assert not getattr(world, "_respawn_queue", None)


def test_map_override_beats_the_rules_value():
    """地图的 ``respawn`` 覆盖优先于规则里的 ``respawn_time``。"""
    from soundrts.world_respawn import respawn_time_for

    world = _FakeWorld()
    place = _FakePlace(world)
    player = _FakePlayer(world)
    unit = _FakeUnit(
        world, place, player, respawn_time=30 * PRECISION, override=5 * PRECISION
    )
    assert respawn_time_for(unit) == 5 * PRECISION


def test_player_has_respawnable_units_while_waiting():
    """排队等刷新期间，玩家算「还有可刷新单位」。"""
    from soundrts.world_respawn import player_has_respawnable_units, schedule_respawn

    world = _FakeWorld(now=1000)
    place = _FakePlace(world)
    player = _FakePlayer(world)
    unit = _FakeUnit(world, place, player, respawn_time=30 * PRECISION)

    assert player_has_respawnable_units(player) is False
    schedule_respawn(unit)
    assert player_has_respawnable_units(player) is True


def test_player_has_respawnable_units_with_a_living_one():
    """手上还有一个活着的可刷新单位时也算。"""
    from soundrts.world_respawn import player_has_respawnable_units

    world = _FakeWorld()
    place = _FakePlace(world)
    player = _FakePlayer(world)
    player.units.append(_FakeUnit(world, place, player, respawn_time=30 * PRECISION))
    assert player_has_respawnable_units(player) is True


def test_player_without_respawnable_units_is_not_immune():
    """普通玩家（没有可刷新单位）不受影响。"""
    from soundrts.world_respawn import player_has_respawnable_units

    world = _FakeWorld()
    place = _FakePlace(world)
    player = _FakePlayer(world)
    player.units.append(_FakeUnit(world, place, player, respawn_time=0))
    assert player_has_respawnable_units(player) is False


# ---------------------------------------------------------------------------
# 失败判定
# ---------------------------------------------------------------------------
def test_no_unit_left_is_false_while_a_respawn_is_queued():
    """可刷新的单位全死了，也不算「全军覆没」。"""
    from soundrts.world_respawn import schedule_respawn
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Player(TriggersMixin):
        def __init__(self):
            self.units = []
            self.has_been_defeated = False
            self.is_playing = True
            self.world = _FakeWorld()

    player = _Player()
    place = _FakePlace(player.world)
    unit = _FakeUnit(player.world, place, player, respawn_time=30 * PRECISION)
    schedule_respawn(unit)

    assert player.lang_no_unit_left([]) is False


def test_no_unit_left_is_true_for_a_normal_player():
    """普通玩家没单位了照样算输（老行为不变）。"""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Player(TriggersMixin):
        def __init__(self):
            self.units = []
            self.has_been_defeated = False
            self.is_playing = True
            self.world = _FakeWorld()

    assert _Player().lang_no_unit_left([]) is True


# ---------------------------------------------------------------------------
# z5 地图
# ---------------------------------------------------------------------------
def test_z5_uses_the_respawn_syntax():
    """z5 的 b3 守军现在会刷新。"""
    text = _source("res", "multi", "z5.txt")
    assert "respawn" in text
