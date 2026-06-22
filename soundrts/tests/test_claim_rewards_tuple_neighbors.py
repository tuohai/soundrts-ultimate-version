"""``CreatureStatusUpdate.claim_rewards`` 必须兼容 tuple 类型的 ``strict_neighbors``。

背景：``worldroom.Square.strict_neighbors`` 在 Round 4 cached_property 优化里
改成返回 **tuple**（immutable，可安全缓存共享）。所有其它 caller 都只用
``for ... in strict_neighbors`` 迭代，对 tuple 兼容；唯一坏掉的点是
``claim_rewards`` 里的 ``[target.place] + target.place.strict_neighbors`` —
``list + tuple`` 在 Python 里非法，每次一个 ``xp_reward > 0`` 的单位在有
邻居（几乎总是）的方格上被击杀时都会抛 ``TypeError``。

本测试在不实例化 World / Square / Player 的前提下，直接驱动 ``claim_rewards``
跑过那一行，验证 tuple 形状不会再回归 ``TypeError``。
"""
from __future__ import annotations

import warnings

# soundrts/lib/resource.py 在 import 时会调用 locale.getdefaultlocale()，
# 该函数在 Python 3.12+ 触发 DeprecationWarning，pytest.ini 设了
# filterwarnings = error 会让收集阶段失败。这里在 import soundrts
# 任何子模块之前先屏蔽。
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=r".*getdefaultlocale.*",
)

import pytest

import soundrts.worldunit  # noqa: F401 解开 combat/worldunit 循环依赖

from soundrts.worldunit.world_status_update import CreatureStatusUpdate


class _FakePlayer:
    """最简玩家：``player_is_an_enemy`` 返回固定值，``allied`` 为空列表。"""

    def __init__(self, is_enemy=True, allied=None):
        self._is_enemy = is_enemy
        self.allied = allied if allied is not None else []

    def player_is_an_enemy(self, other):
        return self._is_enemy


class _FakePlace:
    """模拟 ``Square``：``objects`` 与 tuple 形态的 ``strict_neighbors``。"""

    def __init__(self, objects=None, strict_neighbors=()):
        self.objects = objects if objects is not None else []
        # 注意：必须是 tuple — 这是 Round 4 优化后 Square 的真实形状。
        self.strict_neighbors = strict_neighbors


class _FakeTarget:
    def __init__(self, place, xp_reward=100, player=None):
        self.place = place
        self.xp_reward = xp_reward
        self.player = player if player is not None else _FakePlayer(is_enemy=True)


def _make_attacker(*, player=None, last_player=None):
    """构造一个无 ``__init__`` 的 ``CreatureStatusUpdate``，仅塞入
    ``claim_rewards`` 真正读取的两个字段。"""
    a = CreatureStatusUpdate.__new__(CreatureStatusUpdate)
    a.player = player if player is not None else _FakePlayer(is_enemy=True)
    a.last_player = last_player
    return a


# ---------------------------------------------------------------------------
# 主回归测试
# ---------------------------------------------------------------------------


def test_claim_rewards_accepts_tuple_strict_neighbors():
    """``claim_rewards`` 必须能处理 tuple 类型的 ``strict_neighbors``
    而不抛 ``TypeError: can only concatenate list (not "tuple") to list``。"""
    neighbor = _FakePlace()
    place = _FakePlace(strict_neighbors=(neighbor,))
    target = _FakeTarget(place=place, xp_reward=100)
    attacker = _make_attacker()

    # 修复前这里会抛 TypeError；修复后应静默通过（没有有资格领奖的单位
    # → units 为空 → 直接返回，不调 increase_xp）。
    attacker.claim_rewards(target)


def test_claim_rewards_accepts_empty_tuple_strict_neighbors():
    """边界情况：方格没有任何邻居（地图角落上的孤岛 square），
    ``strict_neighbors`` 是空 tuple；仍然不能抛。"""
    place = _FakePlace(strict_neighbors=())
    target = _FakeTarget(place=place, xp_reward=100)
    attacker = _make_attacker()

    attacker.claim_rewards(target)


def test_claim_rewards_accepts_list_strict_neighbors():
    """forward-compat：若未来有人把 ``strict_neighbors`` 又改回 list，
    新代码（``.extend``）依然兼容。"""
    neighbor = _FakePlace()
    place = _FakePlace(strict_neighbors=[neighbor])
    target = _FakeTarget(place=place, xp_reward=100)
    attacker = _make_attacker()

    attacker.claim_rewards(target)


def test_claim_rewards_skips_when_target_place_has_no_neighbors_attr():
    """``hasattr`` 兜底分支：``target.place`` 不是方格（如 zoom target）时
    只看本格。不应抛 ``AttributeError``。"""

    class _PlaceWithoutNeighbors:
        objects = []
        # 故意不定义 strict_neighbors

    target = _FakeTarget(place=_PlaceWithoutNeighbors(), xp_reward=100)
    attacker = _make_attacker()

    attacker.claim_rewards(target)


# ---------------------------------------------------------------------------
# 行为不变性测试：确认修复没改变 xp 分配语义
# ---------------------------------------------------------------------------


class _FakeAlly:
    """模拟一个有 ``xp_thresholds`` 的盟友单位（够格领奖）。"""

    def __init__(self, player, xp_thresholds=(100, 300, 700)):
        self.player = player
        self.xp_thresholds = xp_thresholds
        self.received_xp = 0

    def increase_xp(self, xp):
        self.received_xp += xp


def test_claim_rewards_distributes_xp_across_self_and_neighbors():
    """端到端：本格 + 邻居各有 1 个盟友单位，xp_reward = 100 应平分 50/50。
    顺便确认 tuple-typed neighbors 在该路径上仍然能被正确迭代。"""
    attacker_player = _FakePlayer(is_enemy=True)
    # claim_rewards 用 self.player.allied（last_player is None 时）筛选
    ally_in_self = _FakeAlly(player=attacker_player)
    ally_in_neighbor = _FakeAlly(player=attacker_player)
    attacker_player.allied = [attacker_player]  # 自己在自己的 allied 里

    self_place = _FakePlace(objects=[ally_in_self])
    neighbor_place = _FakePlace(objects=[ally_in_neighbor])
    self_place.strict_neighbors = (neighbor_place,)  # 关键：tuple

    target = _FakeTarget(place=self_place, xp_reward=100)
    attacker = _make_attacker(player=attacker_player)

    attacker.claim_rewards(target)

    # 100 xp 平分给 2 个盟友
    assert ally_in_self.received_xp == 50
    assert ally_in_neighbor.received_xp == 50


def test_claim_rewards_does_nothing_when_xp_reward_is_zero():
    """``target.xp_reward == 0`` 的快速早返路径不受影响。"""
    place = _FakePlace(strict_neighbors=(_FakePlace(),))
    target = _FakeTarget(place=place, xp_reward=0)
    attacker = _make_attacker()

    attacker.claim_rewards(target)  # 不应抛任何异常


def test_unit_die_does_not_double_claim_rewards():
    """``Unit.die`` 不应在 ``Creature.die`` 之外再发一次经验。

    士兵类单位（含雷诺）走 ``Unit.die`` → ``Creature.die``；若两处都调
    ``claim_rewards``，击杀 ``xp_reward 50`` 的单位会拿到 100 经验并连升两级。
    """
    from unittest.mock import MagicMock, patch

    from soundrts.worldunit.worldbase import Unit
    from soundrts.worldunit.worldcreature import Creature

    attacker = MagicMock()
    victim = MagicMock()
    victim.player = MagicMock()
    victim.corpse = False
    victim.is_inside = False
    victim.drop_loot = False
    victim.inventory = []

    with patch.object(Creature, "die") as mock_creature_die:
        Unit.die(victim, attacker)

    attacker.claim_rewards.assert_not_called()
    mock_creature_die.assert_called_once_with(victim, attacker)
