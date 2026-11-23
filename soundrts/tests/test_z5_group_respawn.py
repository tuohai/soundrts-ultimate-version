# -*- coding: utf-8 -*-
"""z5 地图（zombie planet part 5）的 b3 守军会整队回来。

``res/multi/z5.txt`` 的 b3 格里是一大波敌军（20 步兵、20 弓箭手、20 骑士、
20 投石机、20 飞龙、20 法师、20 祭司）。这张图用 ``respawn_group``：
**整个守军被打光之后**，过 60 秒，原地恢复原始阵容。

这里用真实的地图文件跑一遍，确认：
  * 地图能正常加载（``respawn_group`` 被解析掉，不当成单位类型）；
  * b3 上确实有 140 个敌军单位；
  * 全歼之后排一次整队复活的队列，敌人不算输；
  * 60 秒后整队回来，人数与原来一样。
"""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

Z5 = ROOT / "res" / "multi" / "z5.txt"


@pytest.fixture
def z5_world():
    """Load the real z5 map and populate it with one human player."""
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

        world = World([], 11)
        world._parse_map(Z5.read_text(encoding="utf-8"))
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


def _hostile_computer(world):
    """The b3 garrison computer (not the neutral wildlife one)."""
    computers = [p for p in world.players if not getattr(p, "is_human", False)]
    assert len(computers) == 2, "z5 has two computer_only slots"
    # The neutral wildlife slot holds deer / sheep / boar; the garrison
    # slot holds the army.
    garrison = None
    for computer in computers:
        if any(u.type_name == "footman" for u in computer.units):
            garrison = computer
    assert garrison is not None, "the b3 garrison must exist"
    return garrison


def test_z5_declares_a_group_respawn():
    """地图文件里写的是 ``respawn_group 60``。"""
    text = Z5.read_text(encoding="utf-8")
    assert "respawn_group 60" in text


def test_the_b3_garrison_is_armed(z5_world):
    """b3 那一槽配置了 60 秒的整队复活。"""
    garrison = _hostile_computer(z5_world)
    assert garrison._respawn_group_seconds == 60 * 1000
    assert garrison._respawn_group_armed is True


def test_the_b3_garrison_has_140_units(z5_world):
    """b3 上是 20 × 7 = 140 个敌军单位。"""
    garrison = _hostile_computer(z5_world)
    assert len(garrison.units) == 140, len(garrison.units)


def test_the_roster_covers_every_type(z5_world):
    """原始阵容里七种单位各 20 个。"""
    garrison = _hostile_computer(z5_world)
    by_name = {}
    for _place, name, count in garrison._respawn_roster:
        by_name[name] = by_name.get(name, 0) + count
    for type_name in (
        "footman",
        "archer",
        "knight",
        "catapult",
        "dragon",
        "mage",
        "priest",
    ):
        assert by_name.get(type_name) == 20, (type_name, by_name)


def test_wiping_the_garrison_queues_the_whole_faction(z5_world):
    """140 个全杀了 → 排一次整队复活的队列。"""
    garrison = _hostile_computer(z5_world)
    for unit in list(garrison.units):
        unit.hp = 0
        unit.die(None)

    assert not garrison.units
    queue = z5_world._respawn_group_queue
    assert len(queue) == 1
    deadline, owner = queue[0]
    assert owner is garrison
    assert deadline == z5_world.time + 60 * 1000


def test_the_garrison_does_not_lose_while_waiting(z5_world):
    """等着整队回来的时候不算输。"""
    garrison = _hostile_computer(z5_world)
    for unit in list(garrison.units):
        unit.hp = 0
        unit.die(None)

    assert garrison.lang_no_unit_left([]) is False


def test_the_whole_garrison_comes_back(z5_world):
    """60 秒后，140 个单位整队回来。"""
    from soundrts.world_respawn import tick_group_respawns

    garrison = _hostile_computer(z5_world)
    for unit in list(garrison.units):
        unit.hp = 0
        unit.die(None)

    z5_world.time += 61 * 1000
    tick_group_respawns(z5_world)

    assert len(garrison.units) == 140, len(garrison.units)
    assert not z5_world._respawn_group_queue
