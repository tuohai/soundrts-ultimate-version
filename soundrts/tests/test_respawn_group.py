# -*- coding: utf-8 -*-
"""势力整体刷新（``respawn_group``）—— 整支守军被打光后整队回来。

背景：
  逐单位刷新（``respawn <类型> <秒>``）让敌军永远死不绝：杀一个来一个。
  但有些地图想要的是另一层意思 ——「这个势力被打败了（被打光了），
  过一段时间整支部队重新出现」，像是 RPG 里的「BOSS 刷新点」。

地图语法：``computer_only`` 行里写 ``respawn_group <秒>``。

规则：
  * ``respawn_group`` 与逐类型的 ``respawn <类型> <秒>`` **互斥**：
    写了 ``respawn_group`` 的槽位，逐类型刷新被忽略（并在加载时警告）。
  * 势力被全歼的那一刻排一次队列；到期后按**原始阵容**（单位 + 建筑，
    含原来的数量与格子）原样重建。
  * 等待期间势力**不算输** —— 它马上就会回来。
  * 逐单位刷新在这类槽位里**不生效**（否则永远死不绝）。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# 一张两格的小地图：a1 给玩家，b1 放一队会整队复活的敌军。
MAP = """
title 1 1
square_width 12
nb_columns 2
nb_lines 1
starting_squares a1
starting_units peasant
starting_resources 500 500
computer_only 0 0 b1 2 footman 1 archer respawn_group 30
"""


def _source(*path_parts):
    return ROOT.joinpath(*path_parts).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 地图解析
# ---------------------------------------------------------------------------
def test_respawn_group_token_parsed_out_of_a_computer_only_line():
    """``respawn_group <秒>`` 从单位列表里摘出来。"""
    from soundrts.world.world_map import WorldMapMixin

    items = ["20", "footman", "20", "archer", "respawn_group", "45"]
    filtered, seconds = WorldMapMixin._strip_respawn_group_from_items(
        WorldMapMixin, items
    )
    assert filtered == ["20", "footman", "20", "archer"]
    assert seconds == 45


def test_respawn_group_without_a_value_is_ignored():
    """``respawn_group`` 后面没数字时不当成有效配置。"""
    from soundrts.world.world_map import WorldMapMixin

    filtered, seconds = WorldMapMixin._strip_respawn_group_from_items(
        WorldMapMixin, ["footman", "respawn_group"]
    )
    assert filtered == ["footman"]
    assert seconds is None


def test_respawn_group_slot_marker_round_trips():
    """槽位上的标记能读回来。"""
    from soundrts.world.world_core import (
        set_start_slot_respawn_group,
        start_slot_respawn_group,
    )

    slot = ["resources", [], [], True]
    assert start_slot_respawn_group(slot) is None
    set_start_slot_respawn_group(slot, 60)
    assert start_slot_respawn_group(slot) == 60


def test_respawn_group_and_per_type_respawn_are_mutually_exclusive():
    """两种写法同时出现 → 保留 ``respawn_group``，丢掉逐类型设置，并警告。"""
    from soundrts.world.world_map import WorldMapMixin

    mixin = WorldMapMixin()
    mixin.computers_starts = []
    mixin.computers_factions = []
    mixin.computers_names = {}
    mixin.nb_res = 4
    # 直接调用 _add_start，绕开地图解析的其它前置条件。
    mixin._add_start(
        "computer_only",
        [
            "computer_only",
            "0",
            "0",
            "b3",
            "20",
            "footman",
            "respawn",
            "footman",
            "10",
            "respawn_group",
            "60",
        ],
    )
    from soundrts.world.world_core import (
        start_slot_respawn_group,
        start_slot_respawn_overrides,
    )

    slot = mixin.computers_starts[0]
    assert start_slot_respawn_group(slot) == 60
    assert start_slot_respawn_overrides(slot) == {}, (
        "per-type respawn must be dropped when respawn_group is present"
    )


# ---------------------------------------------------------------------------
# 端到端
# ---------------------------------------------------------------------------
@pytest.fixture
def group_world():
    """A real world whose computer garrison comes back as a whole."""
    from soundrts import config
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    saved_mods = getattr(config, "mods", "")
    saved_res_mods = res.mods
    try:
        config.mods = ""
        res.set_mods("")
        res.load_rules_and_ai()

        world = World([], 7)
        world._parse_map(MAP)
        world.square_width = int(world.square_width * 1000)
        world._build_map()

        client = DirectClient("player1", None)
        client.faction = None
        client.alliance = None
        client.interface = type(
            "I", (), {"queue_srv_event": lambda *a, **k: None}
        )()
        world.populate_map([client], random_starts=False)
        world._update_buckets()
        yield world
    finally:
        config.mods = saved_mods
        if res.mods != saved_res_mods:
            res.set_mods(saved_res_mods)


def _computer(world):
    computers = [p for p in world.players if not getattr(p, "is_human", False)]
    assert computers, "the map must create one computer_only player"
    return computers[0]


def test_the_garrison_is_armed_with_the_group_delay(group_world):
    """电脑那一槽配了 ``respawn_group 30``。"""
    computer = _computer(group_world)
    assert computer._respawn_group_seconds == 30 * 1000
    assert computer._respawn_group_armed is True


def test_the_original_roster_is_recorded(group_world):
    """原始阵容被记下来了（含数量）。"""
    computer = _computer(group_world)
    roster = computer._respawn_roster
    assert roster, "the roster must be recorded"
    by_name = {}
    for place, name, count in roster:
        by_name[name] = by_name.get(name, 0) + count
    assert by_name.get("footman") == 2
    assert by_name.get("archer") == 1


def test_per_unit_respawn_is_disabled_for_a_group_slot(group_world):
    """整体刷新的槽位里，逐单位刷新不生效。"""
    from soundrts.world_respawn import schedule_respawn

    computer = _computer(group_world)
    footman = [u for u in computer.units if u.type_name == "footman"][0]
    assert schedule_respawn(footman) is None
    assert not getattr(group_world, "_respawn_queue", None)


def test_wiping_the_garrison_queues_a_group_respawn(group_world):
    """把守军全杀了 → 排一次整队复活的队列。"""
    computer = _computer(group_world)
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)

    assert not [u for u in computer.units if u.type_name in ("footman", "archer")]
    queue = group_world._respawn_group_queue
    assert len(queue) == 1
    deadline, owner = queue[0]
    assert owner is computer
    assert deadline == group_world.time + 30 * 1000


def test_the_enemy_does_not_lose_while_waiting_for_the_garrison(group_world):
    """等着整队回来的时候，敌人不算输。"""
    computer = _computer(group_world)
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)

    assert computer.lang_no_unit_left([]) is False, (
        "a faction waiting for its group respawn must not be 'no unit left'"
    )


def test_the_whole_garrison_comes_back_after_the_delay(group_world):
    """时间到了 → 整队回来（人数与原来一样）。"""
    from soundrts.world_respawn import tick_group_respawns

    computer = _computer(group_world)
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)
    assert not computer.units

    # 还没到期 —— 不回来。
    tick_group_respawns(group_world)
    assert not computer.units

    # 时间到了 —— 整队回来。
    group_world.time += 31 * 1000
    tick_group_respawns(group_world)

    footmen = [u for u in computer.units if u.type_name == "footman"]
    archers = [u for u in computer.units if u.type_name == "archer"]
    assert len(footmen) == 2, [u.type_name for u in computer.units]
    assert len(archers) == 1
    assert not group_world._respawn_group_queue, "the queue must be drained"


def test_the_restored_garrison_is_brand_new_and_alive(group_world):
    """回来的是全新的单位：满血、在原格子、属于原主人。"""
    from soundrts.world_respawn import tick_group_respawns

    computer = _computer(group_world)
    old_places = {
        u.type_name: u.place for u in computer.units if u.type_name == "footman"
    }
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)

    group_world.time += 31 * 1000
    tick_group_respawns(group_world)

    for unit in computer.units:
        assert unit.hp == unit.hp_max, "the restored unit must be at full health"
        assert unit.player is computer
        if unit.type_name == "footman":
            assert unit.place is old_places["footman"], (
                "the garrison must come back on its original square"
            )


def test_the_garrison_can_be_wiped_again(group_world):
    """回来的守军再次被打光 → 再排一次队列（可以反复刷）。"""
    from soundrts.world_respawn import tick_group_respawns

    computer = _computer(group_world)
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)
    assert len(group_world._respawn_group_queue) == 1

    group_world.time += 31 * 1000
    tick_group_respawns(group_world)
    assert len(computer.units) == 3

    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)
    assert len(group_world._respawn_group_queue) == 1, (
        "the garrison must be able to come back again"
    )


def test_a_normal_player_still_loses_when_wiped(group_world):
    """普通玩家没单位了照样算输 —— 老行为不变。"""
    human = [p for p in group_world.players if getattr(p, "is_human", False)][0]
    for unit in list(human.units):
        unit.hp = 0
        unit.die(None)
    assert human.lang_no_unit_left([]) is True


def test_an_ownership_transfer_does_not_queue_a_group_respawn(group_world):
    """**归属转移**不算「势力被打光」。

    ``Player.remove()`` 也会在认领 / 夺回时被调用 —— 那一刻单位的数量会
    短暂变少，但势力并没有被消灭。触发点因此放在 ``Creature.die()`` 里，
    而不是 ``Player.remove()`` 里。
    """
    computer = _computer(group_world)
    other = [p for p in group_world.players if p is not computer][0]

    # 把电脑上**所有**单位都转走 —— 电脑手上一个不剩了。
    for unit in list(computer.units):
        unit.set_player(other)

    assert not computer.units
    assert not getattr(group_world, "_respawn_group_queue", None), (
        "an ownership transfer must not queue a group respawn"
    )


def test_the_group_respawn_queue_survives_a_save_and_load(group_world):
    """存档 / 读档后，待整队复活的队列必须还在 —— 而且能继续刷出来。

    队列里存的是**玩家对象**（不是类），玩家本身就是世界的一部分，
    cloudpickle 会把它按引用处理。
    """
    import cloudpickle

    from soundrts.world_respawn import tick_group_respawns

    computer = _computer(group_world)
    for unit in list(computer.units):
        unit.hp = 0
        unit.die(None)
    assert len(group_world._respawn_group_queue) == 1

    data = cloudpickle.dumps(group_world)
    restored = cloudpickle.loads(data)
    assert len(getattr(restored, "_respawn_group_queue", []) or []) == 1

    restored.time += 31 * 1000
    tick_group_respawns(restored)
    computer2 = _computer(restored)
    assert len(computer2.units) == 3, (
        "the garrison must come back after a load"
    )


def test_only_the_last_death_queues_the_group_respawn(group_world):
    """只有最后一个单位死掉的那一刻才排队列。"""
    computer = _computer(group_world)
    units = list(computer.units)
    assert len(units) == 3, len(units)

    units[0].hp = 0
    units[0].die(None)
    assert not group_world._respawn_group_queue, (
        "the faction is not wiped out yet, nothing must be queued"
    )

    units[1].hp = 0
    units[1].die(None)
    assert not group_world._respawn_group_queue, (
        "the faction is not wiped out yet, nothing must be queued"
    )

    units[2].hp = 0
    units[2].die(None)
    assert len(group_world._respawn_group_queue) == 1
