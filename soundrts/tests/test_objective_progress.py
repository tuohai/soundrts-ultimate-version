"""目标动态进度：F9 / HUD 显示 "0/3" → "1/3" → "3/3"。

背景（用户反馈，2026-10-24）：
  圣女贞德德战役第四章目标 1 "将三件圣物送至兰斯大教堂" 的完成条件是
  ``(npc_has_items npc_reims_cathedral relic 3 c5)``，但按 F9 只能看到静态
  文字，看不到已交了几件。现在引擎会从触发器树里自动解析出计数型完成
  条件，并在目标文字后面追加 ``(0/3)`` 形式的进度。

本测试文件覆盖：
1. ``TriggersMixin.objective_progress`` 能从 ``(npc_has_items ...)`` 解析进度；
2. ``collect_objective_entries`` 把进度拼到目标条目末尾；
3. 圣女贞德第四章的地图文件确实用的是计数型条件。
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

import soundrts.worldunit  # noqa: F401  -- 解开循环导入

from soundrts.lib.msgs import LITERAL_TEXT_PREFIX
from soundrts.objective_announce import collect_objective_entries
from soundrts.worldplayerbase.base import Objective
from soundrts.worldplayerbase.triggers import TriggersMixin

REPO_ROOT = Path(__file__).resolve().parents[2]
JOAN = REPO_ROOT / "mods/aoe2/single/Joan of Arc"


# ---------------------------------------------------------------------------
# 桩对象
# ---------------------------------------------------------------------------


class _StubItem:
    def __init__(self, type_name, item_id=1):
        self.type_name = type_name
        self.id = item_id


class _StubPlayer:
    def __init__(self, neutral=False):
        self.neutral = neutral
        self.units = []
        self.allied = [self]
        self.objectives = {}
        self._required_objective_numbers = set()


class _StubUnit:
    def __init__(self, player, type_name="unit", unit_id="u1", place="0,0"):
        self.player = player
        self.type_name = type_name
        self.id = unit_id
        self.place = place
        self.inventory = []
        self.received_items = set()
        self.received_item_counts = {}
        player.units.append(self)


class _StubWorld:
    def __init__(self, players):
        self.players = players
        self.ex_players = []
        self.grid = {"2,4": object()}
        self.name_to_square = {}
        self.squares = []


class _TriggerOwner(TriggersMixin, _StubPlayer):
    pass


def _make_owner(world):
    owner = _TriggerOwner()
    owner.world = world
    owner.triggers = []
    owner.units = []
    return owner


def _make_owner_for(world, player):
    """owner 与 player 共用同一个 units 列表（真实引擎里是同一个对象）。"""
    owner = _make_owner(world)
    owner.units = player.units
    return owner


# ---------------------------------------------------------------------------
# 1. objective_progress：从触发器树解析计数进度
# ---------------------------------------------------------------------------


def test_objective_progress_reads_npc_has_items_condition():
    """``(npc_has_items NPC 物品 3)`` + ``(objective_complete 1)`` → (0, 3)。"""
    npc_player = _StubPlayer(neutral=True)
    human_player = _StubPlayer()
    world = _StubWorld([npc_player, human_player])
    owner = _make_owner(world)

    npc = _StubUnit(
        npc_player, type_name="npc_reims_cathedral", unit_id="n1", place="2,4"
    )
    owner.triggers.append(
        (
            ["npc_has_items", "npc_reims_cathedral", "relic", "3", "c5"],
            ["do", ["objective_complete", "1"], ["cut_scene", "8837"]],
        )
    )

    assert owner.objective_progress("1") == (0, 3)
    npc.received_item_counts["relic"] = 1
    npc.inventory.append(_StubItem("relic", 1))
    assert owner.objective_progress("1") == (1, 3)

    npc.received_item_counts["relic"] = 2
    npc.inventory.append(_StubItem("relic", 2))
    assert owner.objective_progress("1") == (2, 3)

    npc.received_item_counts["relic"] = 3
    npc.inventory.append(_StubItem("relic", 3))
    assert owner.objective_progress("1") == (3, 3)


def test_objective_progress_ignores_unrelated_objective_numbers():
    """进度只属于写明完成的那个目标编号。"""
    npc_player = _StubPlayer(neutral=True)
    human_player = _StubPlayer()
    world = _StubWorld([npc_player, human_player])
    owner = _make_owner(world)

    _StubUnit(npc_player, type_name="npc_reims_cathedral", unit_id="n1")
    owner.triggers.append(
        (
            ["npc_has_items", "npc_reims_cathedral", "relic", "3", "c5"],
            ["do", ["objective_complete", "1"], ["cut_scene", "8837"]],
        )
    )

    assert owner.objective_progress("2") is None


def test_objective_progress_none_without_counting_condition():
    """没有计数型条件时返回 None（不显示进度）。"""
    human_player = _StubPlayer()
    world = _StubWorld([human_player])
    owner = _make_owner(world)

    owner.triggers.append(
        (["has_entered", "c5", "npc_dauphin"], ["objective_complete", "2"])
    )

    assert owner.objective_progress("2") is None


def test_objective_progress_supports_has_item_condition():
    """``(has_item relic 3)`` 也能算出进度。"""
    human_player = _StubPlayer()
    world = _StubWorld([human_player])
    owner = _make_owner_for(world, human_player)

    owner.triggers.append(
        (["has_item", "relic", "3"], ["objective_complete", "1"])
    )

    assert owner.objective_progress("1") == (0, 3)

    unit = _StubUnit(human_player, type_name="monk", unit_id="g")
    unit.inventory.append(_StubItem("relic", 1))
    assert owner.objective_progress("1") == (1, 3)


def test_objective_progress_supports_has_brought_item_condition():
    """``(has_brought_item a1 relic 3)`` 也能算出进度（威廉·华莱士第六章）。"""
    human_player = _StubPlayer()
    world = _StubWorld([human_player])
    owner = _make_owner_for(world, human_player)

    square = types.SimpleNamespace(objects=[])
    world.grid["0,0"] = square

    owner.triggers.append(
        (["has_brought_item", "a1", "relic", "3"], ["objective_complete", "1"])
    )

    assert owner.objective_progress("1") == (0, 3)

    unit = _StubUnit(human_player, type_name="monk", unit_id="g")
    square.objects.append(unit)
    unit.inventory.append(_StubItem("relic", 1))
    assert owner.objective_progress("1") == (1, 3)


# ---------------------------------------------------------------------------
# 2. collect_objective_entries：进度拼到条目末尾
# ---------------------------------------------------------------------------


class _AnnounceWorld:
    objective = None


def test_collect_objective_entries_appends_progress():
    """F9 条目形如 前缀 + 描述 + "(0/3)"。"""
    npc_player = _StubPlayer(neutral=True)
    human_player = _StubPlayer()
    world = _StubWorld([npc_player, human_player])
    owner = _make_owner(world)

    npc = _StubUnit(
        npc_player, type_name="npc_reims_cathedral", unit_id="n1", place="2,4"
    )
    owner.triggers.append(
        (
            ["npc_has_items", "npc_reims_cathedral", "relic", "3", "c5"],
            ["do", ["objective_complete", "1"], ["cut_scene", "8837"]],
        )
    )

    objective = Objective("1", ["8827"])
    owner.objectives[Objective.storage_key("1", optional=False)] = objective
    owner._required_objective_numbers = {"1"}

    entries = collect_objective_entries(_AnnounceWorld(), owner)
    assert len(entries) == 1
    assert entries[0][-1] == LITERAL_TEXT_PREFIX + "0/3"

    # 交一件之后进度变成 1/3
    npc.received_item_counts["relic"] = 1
    npc.inventory.append(_StubItem("relic", 1))
    entries = collect_objective_entries(_AnnounceWorld(), owner)
    assert entries[0][-1] == LITERAL_TEXT_PREFIX + "1/3"


def test_collect_objective_entries_without_progress_has_no_suffix():
    """没有进度信息时，条目保持原样（不追加空片段）。"""
    human_player = _StubPlayer()
    world = _StubWorld([human_player])
    owner = _make_owner(world)

    objective = Objective("1", ["8827"])
    owner.objectives[Objective.storage_key("1", optional=False)] = objective
    owner._required_objective_numbers = {"1"}

    entries = collect_objective_entries(_AnnounceWorld(), owner)
    assert entries[0][-1] == "8827"


def test_explicit_objective_progress_is_used():
    """``Objective.progress`` 显式设置时优先使用。"""
    human_player = _StubPlayer()
    world = _StubWorld([human_player])
    owner = _make_owner(world)

    objective = Objective("1", ["8827"])
    objective.progress = (2, 5)
    owner.objectives[Objective.storage_key("1", optional=False)] = objective
    owner._required_objective_numbers = {"1"}

    entries = collect_objective_entries(_AnnounceWorld(), owner)
    assert entries[0][-1] == LITERAL_TEXT_PREFIX + "2/5"


# ---------------------------------------------------------------------------
# 3. 地图文件契约
# ---------------------------------------------------------------------------


def test_joan_ch4_goal_uses_counting_trigger():
    """第四章目标 1 必须用计数型条件，才能显示 0/3 进度。"""
    text = (JOAN / "4.txt").read_text(encoding="utf-8")
    assert "(npc_has_items npc_reims_cathedral relic 3 c5)" in text
    assert "(npc_has_item npc_reims_cathedral relic c5)" not in text


def test_joan_ch4_registers_only_existing_objectives():
    """``register_objective`` 不应登记不存在的目标 3 / 4。"""
    text = (JOAN / "4.txt").read_text(encoding="utf-8")
    assert "(register_objective 1 2)" in text
    assert "(register_objective 1 2 3 4)" not in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
