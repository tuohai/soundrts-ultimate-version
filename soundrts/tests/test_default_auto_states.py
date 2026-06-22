"""验证 rules.txt 可为不同单位配置开局默认的自动状态：
auto_gather（自动采集）、auto_repair（自动修理）、auto_explore（自动探索）。

需求示例：
* 农民：开局默认启用 auto_gather、禁用 auto_repair；
* 骑士：开局默认启用 auto_explore。

实现要点：
* ``soundrts/definitions.py``：三者均为 int_properties（0/1）。
* ``auto_gather`` / ``auto_repair`` 已是 Worker 类属性，rules 值经生成类覆盖，
  Worker.__init__ 不重置，故 rules 配置直接生效。
* ``auto_explore``：新增 Creature 类属性（默认 False），并在
  ``world_ai_decision.decide`` 中：空闲 + 可移动 + auto_explore 为真时下达
  ``auto_explore`` 标准命令；``AutoExploreOrder.is_allowed`` 放开人类玩家
  （需 auto_explore 标记）；新增 enable/disable_auto_explore 命令供手动开关。
"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401  解开 worldunit 包循环导入

from soundrts.definitions import Rules
from soundrts.worldorders.computer import AutoExploreOrder
from soundrts.worldorders.immediate import EnableAutoExplore, DisableAutoExplore
from soundrts.worldorders import ORDERS_DICT
import soundrts.worldunit.world_ai_decision as wad


# ---------------------------------------------------------------------------
# 1. 属性注册
# ---------------------------------------------------------------------------


def test_auto_states_registered_as_int_properties():
    for k in ("auto_gather", "auto_repair", "auto_explore"):
        assert k in Rules.int_properties


def _load(extra):
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def soldier
class soldier

def worker
class worker
"""
        + extra
    )
    return r


# ---------------------------------------------------------------------------
# 2. rules.txt 配置经生成类生效
# ---------------------------------------------------------------------------


def test_worker_auto_gather_repair_from_rules():
    """农民：auto_gather 1 + auto_repair 0 应体现在生成类上。"""
    r = _load(
        """
def peasant
class worker
auto_gather 1
auto_repair 0
"""
    )
    peasant = r.unit_class("peasant")
    assert peasant is not None
    assert peasant.auto_gather == 1
    assert peasant.auto_repair == 0


def test_knight_auto_explore_from_rules():
    """骑士：auto_explore 1 应体现在生成类上。"""
    r = _load(
        """
def knight
class soldier
auto_explore 1
"""
    )
    knight = r.unit_class("knight")
    assert knight is not None
    assert knight.auto_explore == 1


def test_auto_explore_default_off():
    """未配置时 auto_explore 默认关闭（继承自 Creature 类属性）。"""
    r = _load(
        """
def footman
class soldier
"""
    )
    footman = r.unit_class("footman")
    assert not footman.auto_explore


def test_can_auto_explore_registered_and_per_unit():
    """can_auto_explore 是 int 属性；只给配置了的单位（knight）开放选项。"""
    assert "can_auto_explore" in Rules.int_properties
    r = _load(
        """
def knight
class soldier
can_auto_explore 1

def footman
class soldier
"""
    )
    knight = r.unit_class("knight")
    footman = r.unit_class("footman")
    assert knight.can_auto_explore == 1
    # footman 未配置 → 继承默认 False
    assert not footman.can_auto_explore


# ---------------------------------------------------------------------------
# 3. 命令注册 / is_allowed
# ---------------------------------------------------------------------------


def test_explore_orders_registered():
    assert ORDERS_DICT.get("enable_auto_explore") is EnableAutoExplore
    assert ORDERS_DICT.get("disable_auto_explore") is DisableAutoExplore
    assert ORDERS_DICT.get("auto_explore") is AutoExploreOrder


class _StubPlayer:
    def __init__(self, is_human):
        self.is_human = is_human


class _StubUnit:
    def __init__(self, is_human, auto_explore=False, speed=10, can_auto_explore=True):
        self.player = _StubPlayer(is_human)
        self.auto_explore = auto_explore
        self.can_auto_explore = can_auto_explore
        self.speed = speed
        self.orders = []
        self.notified = []

    def notify(self, msg):
        self.notified.append(msg)

    def cancel_all_orders(self):
        self.orders = []


def test_auto_explore_order_is_allowed_rules():
    # 计算机单位始终允许
    assert AutoExploreOrder.is_allowed(_StubUnit(is_human=False)) is True
    # 人类单位：未开启 → 不允许；开启 → 允许
    assert AutoExploreOrder.is_allowed(_StubUnit(is_human=True, auto_explore=False)) is False
    assert AutoExploreOrder.is_allowed(_StubUnit(is_human=True, auto_explore=True)) is True


def test_enable_auto_explore_is_allowed():
    # 人类、开放了选项(can_auto_explore)、可移动、未开启 → 允许
    assert EnableAutoExplore.is_allowed(
        _StubUnit(True, auto_explore=False, speed=10, can_auto_explore=True)) is True
    # 未开放选项(can_auto_explore=0) → 不允许（命令不出现）
    assert EnableAutoExplore.is_allowed(
        _StubUnit(True, auto_explore=False, speed=10, can_auto_explore=False)) is False
    # 已开启 → 不允许
    assert EnableAutoExplore.is_allowed(_StubUnit(True, auto_explore=True, speed=10)) is False
    # 不可移动（建筑）→ 不允许
    assert EnableAutoExplore.is_allowed(_StubUnit(True, auto_explore=False, speed=0)) is False
    # 非人类 → 不允许（计算机由 AI 自行管理探索）
    assert EnableAutoExplore.is_allowed(_StubUnit(False, auto_explore=False, speed=10)) is False


def test_disable_auto_explore_allowed_even_without_capability():
    """即使未开放 can_auto_explore，只要当前正在自动探索（如开局默认开启），
    也允许禁用，避免"开着却关不掉"。"""
    on = _StubUnit(True, auto_explore=True, speed=10, can_auto_explore=False)
    assert DisableAutoExplore.is_allowed(on) is True


def test_disable_auto_explore_is_allowed_and_action():
    on = _StubUnit(True, auto_explore=True, speed=10)
    assert DisableAutoExplore.is_allowed(on) is True

    off = _StubUnit(True, auto_explore=False, speed=10)
    assert DisableAutoExplore.is_allowed(off) is False

    # immediate_action：关闭标记并取消正在进行的 auto_explore 命令
    o = DisableAutoExplore.__new__(DisableAutoExplore)
    o.unit = on
    on.orders = [types.SimpleNamespace(keyword="auto_explore")]
    o.immediate_action()
    assert on.auto_explore is False
    assert on.orders == []
    assert "order_ok" in on.notified


def test_enable_auto_explore_action_sets_flag():
    u = _StubUnit(True, auto_explore=False, speed=10)
    o = EnableAutoExplore.__new__(EnableAutoExplore)
    o.unit = u
    o.immediate_action()
    assert u.auto_explore is True
    assert "order_ok" in u.notified


# ---------------------------------------------------------------------------
# 4. decide() 在空闲 + 可移动 + auto_explore 时下达 auto_explore 命令
# ---------------------------------------------------------------------------


class _DecideStub:
    """构造满足 CreatureAIDecision.decide 直到 auto_explore 钩子所需的最小单位。

    若 auto_explore 钩子未触发，decide 会继续往下走；为让其能干净返回，
    提供决策缓存所需的类属性，并令 _cached_has_attack 计算为 False
    （mdg/rdg 均为 0），从而在攻击能力检查处提前 return。
    """

    # CreatureAIDecision 的类级默认
    _last_decide_time = 0
    last_attacker = None
    _decision_cache = {}
    _decision_cache_bucket = -1
    _cached_has_attack = None

    def __init__(self, auto_explore, speed, orders):
        self.world = types.SimpleNamespace(time=100000)
        self.ai_mode = "offensive"
        self.speed = speed
        self.orders = orders
        self.is_inside = False
        self.place = object()  # 非 None 即可
        self.auto_explore = auto_explore
        self.id = 1
        self.mdg = 0
        self.rdg = 0
        self.taken = []

    def take_order(self, o, *a, **kw):
        self.taken.append(o)
        # 模拟命令进入队列，避免后续逻辑重复下达
        self.orders = [types.SimpleNamespace(keyword=o[0])]

    def _wildlife_wander(self):
        # 非野生动物：不进行漫游，让 decide 继续走到 auto_explore 钩子
        return False


def _decide(stub):
    return wad.CreatureAIDecision.decide(stub)


def test_decide_issues_auto_explore_when_idle():
    stub = _DecideStub(auto_explore=True, speed=10, orders=[])
    _decide(stub)
    assert stub.taken == [["auto_explore"]]


def test_decide_no_auto_explore_when_disabled():
    stub = _DecideStub(auto_explore=False, speed=10, orders=[])
    _decide(stub)
    assert stub.taken == []


def test_decide_no_auto_explore_when_immobile():
    stub = _DecideStub(auto_explore=True, speed=0, orders=[])
    _decide(stub)
    assert stub.taken == []


def test_decide_no_auto_explore_when_busy():
    busy = [types.SimpleNamespace(keyword="go")]
    stub = _DecideStub(auto_explore=True, speed=10, orders=busy)
    _decide(stub)
    assert stub.taken == []
