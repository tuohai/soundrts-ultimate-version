# -*- coding: utf-8 -*-
"""敌军刷新的端到端测试：真的建一个世界，真的打死单位，真的等它刷新。

前面的 ``test_respawn.py`` 用假对象验证各个零件；这里把整条链跑通：
  地图 ``computer_only`` 行 → 出生时带上刷新时限 → 被打死 → 排队 →
  时间到 → 原地冒出一个新单位 → 敌人不会因此宣布失败。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# 一张只有两格的小地图：a1 给玩家，b1 放一群会刷新的敌军。
MAP = """
title 1 1
square_width 12
nb_columns 2
nb_lines 1
starting_squares a1
starting_units peasant
starting_resources 500 500
computer_only 0 0 b1 3 footman respawn footman 5
"""


@pytest.fixture
def respawn_world():
    """Build a real world with one human and one respawning computer.

    Function-scoped on purpose: every test gets a fresh world, so the
    tests don't see each other's dead units.
    """
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    saved_mods = getattr(config, "mods", "")
    saved_res_mods = res.mods
    try:
        config.mods = ""
        res.set_mods("")
        res.load_rules_and_ai()

        world = World([], 42)
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
    computers = [
        p for p in world.players if not getattr(p, "is_human", False)
    ]
    assert computers, "the map must create one computer_only player"
    return computers[0]


def test_the_computer_army_is_spawned(respawn_world):
    """b1 上确实有 3 个步兵。"""
    computer = _computer(respawn_world)
    footmen = [u for u in computer.units if u.type_name == "footman"]
    assert len(footmen) == 3, [u.type_name for u in computer.units]


def test_the_spawned_units_carry_the_map_respawn_override(respawn_world):
    """地图写的 ``respawn footman 5`` 落到单位上（毫秒）。"""
    from soundrts.world_respawn import respawn_time_for

    computer = _computer(respawn_world)
    for unit in computer.units:
        if unit.type_name != "footman":
            continue
        assert respawn_time_for(unit) == 5 * 1000


def test_a_killed_unit_is_queued_for_respawn(respawn_world):
    """打死一个步兵 → 排进刷新队列。"""
    from soundrts.world_respawn import schedule_respawn

    computer = _computer(respawn_world)
    footman = [u for u in computer.units if u.type_name == "footman"][0]
    place = footman.place
    footman.hp = 0
    footman.die(None)
    assert len(respawn_world._respawn_queue) == 1
    deadline, owner, type_name, queued_place = respawn_world._respawn_queue[0][:4]
    assert owner is computer
    # 队列里存的是**类型名**（不是类对象）—— 动态建的类不适合进存档。
    assert type_name == "footman"
    assert queued_place is place


def test_the_unit_comes_back_after_the_delay(respawn_world):
    """时间到了 → 原地冒出一个新的步兵。"""
    from soundrts.world_respawn import tick_respawns

    computer = _computer(respawn_world)
    before = len([u for u in computer.units if u.type_name == "footman"])
    assert before == 3

    footman = [u for u in computer.units if u.type_name == "footman"][0]
    place = footman.place
    footman.hp = 0
    footman.die(None)
    assert len(computer.units) == before - 1

    # 还没到期 —— 不刷新。
    tick_respawns(respawn_world)
    assert len(computer.units) == before - 1

    # 时间到了 —— 刷新。
    respawn_world.time += 6000
    tick_respawns(respawn_world)
    footmen = [u for u in computer.units if u.type_name == "footman"]
    assert len(footmen) == before, "the footman must come back"
    assert not respawn_world._respawn_queue, "the queue must be drained"


def test_the_respawn_queue_survives_a_save_and_load(respawn_world):
    """存档 / 读档后，待刷新的队列必须还在 —— 而且能继续刷出来。

    队列里存的是**类型名**而不是类对象：规则里的单位类型是运行时动态
    建出来的（``type(name, (base,), d)``），把类塞进存档会让 cloudpickle
    把它整个按值序列化。
    """
    import cloudpickle

    from soundrts.world_respawn import tick_respawns

    computer = _computer(respawn_world)
    for unit in [u for u in computer.units if u.type_name == "footman"][:2]:
        unit.hp = 0
        unit.die(None)
    assert len(respawn_world._respawn_queue) == 2

    data = cloudpickle.dumps(respawn_world)
    restored = cloudpickle.loads(data)
    assert len(getattr(restored, "_respawn_queue", []) or []) == 2

    restored.time += 6000
    tick_respawns(restored)
    computer2 = _computer(restored)
    footmen = [u for u in computer2.units if u.type_name == "footman"]
    assert len(footmen) == 3, "the two queued footmen must come back after a load"


def test_the_respawned_unit_is_brand_new_and_alive(respawn_world):
    """刷新出来的是全新单位：满血、在原格子、属于原主人。"""
    from soundrts.world_respawn import tick_respawns

    computer = _computer(respawn_world)
    ids_before = {u.id for u in computer.units}
    footman = [u for u in computer.units if u.type_name == "footman"][0]
    old_id = footman.id
    place = footman.place
    footman.hp = 0
    footman.die(None)
    assert old_id not in {u.id for u in computer.units}

    respawn_world.time += 6000
    tick_respawns(respawn_world)

    footmen = [u for u in computer.units if u.type_name == "footman"]
    assert len(footmen) == 3
    fresh = [u for u in footmen if u.id not in ids_before]
    assert len(fresh) == 1, "exactly one new footman"
    new = fresh[0]
    assert new.hp == new.hp_max, "the respawned unit must be at full health"
    assert new.place is place, "the respawned unit must be on the old square"
    assert new.player is computer


def test_the_enemy_does_not_lose_when_its_army_is_wiped(respawn_world):
    """把 b1 的守军全杀了，敌人也不宣布失败。"""
    computer = _computer(respawn_world)
    for unit in list(computer.units):
        if unit.type_name == "footman":
            unit.hp = 0
            unit.die(None)

    assert not [u for u in computer.units if u.type_name == "footman"]
    assert computer.lang_no_unit_left([]) is False, (
        "a respawning army must not count as 'no unit left'"
    )


def test_a_normal_player_still_loses_when_wiped(respawn_world):
    """普通玩家没单位了照样算输 —— 老行为不变。"""
    human = [p for p in respawn_world.players if getattr(p, "is_human", False)][0]
    for unit in list(human.units):
        unit.hp = 0
        unit.die(None)
    assert human.lang_no_unit_left([]) is True


def test_a_pending_hero_revival_also_blocks_the_defeat(respawn_world):
    """现有英雄系统（``is_revivable``）的待复活尸体也不能让敌人被判负。

    这是之前的一个漏洞：唯一的一个可复活单位被打死，地上留着等着复活的
    尸体，但 ``no_unit_left`` 返回 True —— 电脑被判负，而它的单位马上就要
    复活了。
    """
    computer = _computer(respawn_world)
    for unit in list(computer.units):
        if unit.type_name == "footman":
            unit.hp = 0
            unit.die(None)
    assert not [u for u in computer.units if u.type_name == "footman"]

    # 现在给剩下的那个单位打开英雄复活开关（模拟 is_revivable 1 的规则）。
    for unit in list(computer.units):
        if unit.type_name == "footman":
            unit.is_revivable = 1
            unit.revival_time = 5000
            unit.hp = 0
            unit.die(None)

    assert not [u for u in computer.units if u.type_name == "footman"]
    assert computer.lang_no_unit_left([]) is False, (
        "a pending hero revival must not count as 'no unit left'"
    )
