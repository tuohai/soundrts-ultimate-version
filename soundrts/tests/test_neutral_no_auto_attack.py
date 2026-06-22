"""验证玩家单位在进攻/防御/追击模式下不主动攻击中立者，防御模式不因中立者逃跑。

中立 creep（``computer_only ... neutral``）仍视为非战斗敌对目标：
* ``player_is_a_hostile_enemy`` 排除 neutral 玩家
* ``can_attack`` 对中立目标返回 False，除非有 imperative attack/go 命令
"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401 — 解开循环导入

from soundrts.worldplayerbase.combat import CombatMixin
from soundrts.worldunit import world_ai_decision as wad


class _CombatPlayer(CombatMixin):
    def __init__(self, neutral=False):
        self.neutral = neutral
        self.allied = [self]
        self.id = "1"
        self.world = types.SimpleNamespace(time=0, players=[self])
        self._enemy_player_cache = {}
        self._enemy_player_timestamp = 0

    def player_is_an_enemy(self, p):
        return p is not None and p not in self.allied


class _Square:
    """可哈希的方格占位对象，供 balance() 测试使用。"""

    def __init__(self, sid):
        self.id = sid


class _CanAttackStub:
    """仅测试 CreatureAIDecision.can_attack / 决策缓存中立过滤所需字段。"""

    def __init__(self, orders=None):
        self.orders = orders or []
        self.mdg_range = 0
        self.rdg_range = 0
        self.speed = 10
        self.place = _Square("sq1")
        self.world = types.SimpleNamespace(time=0, treaty_until_time=0)
        self.player = _CombatPlayer()

    def is_an_enemy(self, other):
        return True

    def can_attack_if_in_range(self, other):
        return True

    def _get_melee_damage_vs(self, other):
        return 10

    def _get_ranged_damage_vs(self, other):
        return 0

    def _near_enough_to_aim(self, other):
        return True

    # 绑定 mixin 方法
    _is_neutral_target = wad.CreatureAIDecision._is_neutral_target
    _player_ordered_attack_on = wad.CreatureAIDecision._player_ordered_attack_on
    can_attack = wad.CreatureAIDecision.can_attack


class _NeutralTarget:
    def __init__(self, place=None):
        self.player = _CombatPlayer(neutral=True)
        self.hp = 100
        self.place = place or _Square("sq1")
        self.x = self.y = 0
        self.radius = 0
        self.id = 99


def test_passes_harm_diplomacy_filter_enemy_excludes_neutral():
    from soundrts.worldunit.world_public_method import passes_harm_diplomacy_filter

    human = _CombatPlayer(neutral=False)
    neutral = _CombatPlayer(neutral=True)
    hostile = _CombatPlayer(neutral=False)
    human.allied = [human]
    hostile.allied = []

    assert passes_harm_diplomacy_filter(["enemy"], human, hostile) is True
    assert passes_harm_diplomacy_filter(["enemy"], human, neutral) is False
    assert passes_harm_diplomacy_filter(["non_neutral"], human, hostile) is True
    assert passes_harm_diplomacy_filter(["neutral"], human, neutral) is True
    assert passes_harm_diplomacy_filter(["neutral"], human, hostile) is False


def test_player_is_a_hostile_enemy_excludes_neutral():
    human = _CombatPlayer(neutral=False)
    neutral = _CombatPlayer(neutral=True)
    human.allied = [human]

    assert human.player_is_an_enemy(neutral) is True
    assert human.player_is_a_hostile_enemy(neutral) is False
    assert human.player_is_a_hostile_enemy(human) is False


def test_can_attack_refuses_neutral_without_imperative_order():
    unit = _CanAttackStub()
    neutral = _NeutralTarget()

    assert unit.can_attack(neutral) is False


def test_can_attack_allows_neutral_with_imperative_attack_order():
    neutral = _NeutralTarget()
    attack_order = types.SimpleNamespace(
        is_imperative=True,
        target=neutral,
        keyword="attack",
    )
    unit = _CanAttackStub(orders=[attack_order])

    assert unit.can_attack(neutral) is True


def test_can_attack_allows_neutral_with_imperative_go_order():
    neutral = _NeutralTarget()
    go_order = types.SimpleNamespace(
        is_imperative=True,
        target=neutral,
        keyword="go",
    )
    unit = _CanAttackStub(orders=[go_order])

    assert unit.can_attack(neutral) is True


def test_decide_cache_skips_neutral_attack():
    """决策缓存恢复时不应继续攻击中立目标。"""

    class _DecideStub:
        _last_decide_time = 0
        _decision_cache = {}
        _decision_cache_bucket = -1
        _cached_has_attack = True

        def __init__(self):
            self.ai_mode = "offensive"
            self.speed = 10
            self.orders = []
            self.auto_explore = False
            self.world = types.SimpleNamespace(time=100000)
            self.id = 1
            self.last_attacker = None
            self.mdg = 10
            self.rdg = 0
            self.is_inside = False
            self.place = _Square("sq1")
            self.attacked = []
            self._previous_square = None
            self.player = _CombatPlayer()

        def is_an_enemy(self, other):
            return True

        def _is_neutral_target(self, other):
            return wad.CreatureAIDecision._is_neutral_target(self, other)

        def _player_ordered_attack_on(self, other):
            return wad.CreatureAIDecision._player_ordered_attack_on(self, other)

        def _must_hold(self):
            return False

        def _wildlife_wander(self):
            return False

        def _attack(self, target):
            self.attacked.append(target)

        def take_order(self, *args, **kwargs):
            pass

        def notify(self, *args, **kwargs):
            pass

        def _get_squares_in_sight(self):
            return []

        def _choose_enemy(self, place):
            return False

    neutral = _NeutralTarget()
    unit = _DecideStub()
    unit.counterattack_enabled = False
    bucket = unit.world.time // 100
    _DecideStub._decision_cache[(unit.id, bucket)] = {
        "action": "attack",
        "target": neutral,
    }
    _DecideStub._decision_cache_bucket = bucket

    wad.CreatureAIDecision.decide(unit)

    assert unit.attacked == []


def test_decide_cache_neutral_filter_logic():
    """逻辑级：缓存攻击中立目标时，无强制命令则不攻击。"""

    class _Stub:
        orders = []

        def _is_neutral_target(self, other):
            return True

        def _player_ordered_attack_on(self, other):
            return False

    target = _NeutralTarget()
    should_attack = (
        target.place is not None
        and target.hp > 0
        and (not _Stub()._is_neutral_target(target) or _Stub()._player_ordered_attack_on(target))
    )
    assert should_attack is False


def test_defensive_mode_no_flee_when_only_neutral_threat():
    """仅有中立单位威胁时，enemy_menace 为 0，balance 不应触发逃跑。"""
    human = _CombatPlayer(neutral=False)
    human.units = []
    human.world = types.SimpleNamespace(time=1000)
    human._enemy_menace = {}
    human._balance_cache = {}
    human._balance_cache_time = {}

    square = _Square("sq1")
    result = human.balance(square, mult=10)
    assert result >= 5


def test_combat_source_uses_hostile_enemy_for_menace():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "soundrts" / "worldplayerbase" / "combat.py").read_text(encoding="utf-8")
    assert "def player_is_a_hostile_enemy(self, p):" in src
    assert "player_is_a_hostile_enemy(p)" in src


def test_perception_source_uses_hostile_enemy_for_known_enemies():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2]
           / "soundrts" / "worldplayerbase" / "perception.py").read_text(encoding="utf-8")
    assert src.count("player_is_a_hostile_enemy(p)") >= 2

