"""强制移动命令（Ctrl+退格）order_ok 音效回归测试。

背景：
- ``GoOrder.on_queued`` 曾经用 ``if not self.is_imperative`` 把强制移动命令的
  ``order_ok`` 通知完全屏蔽掉，导致玩家用 Ctrl+退格 强制命令单位移动时听不到
  确认音（而普通移动命令能听到）。
- 第一人称 RPG 模式（``interface.immersion``）下方向键会重复发送强制 go
  命令，若不屏蔽会在走路时持续蜂鸣，因此屏蔽点改到客户端
  ``EntityViewEvents.on_order_ok``。
"""
from __future__ import annotations

import types

from soundrts.clientgameentity.events import EntityViewEvents
from soundrts.worldunit.world_order import CreatureOrders


class _Square:
    """最小化的地面方格替身。"""

    id = "sq1"
    objects = []
    neighbors = []
    exits = []
    is_inside_place = False
    is_ground = True
    is_water = False
    is_air = True


class _Player:
    def __init__(self):
        self.id = "p1"
        self.allied = [self]
        self.available_population = 99
        self.used_population = 0

    def player_is_an_enemy(self, other):
        return other is not None and other is not self and other not in self.allied

    def get_object_by_id(self, obj_id):
        return {"sq1": _Square()}.get(obj_id)


class _Orders(CreatureOrders):
    """支持 go 命令的最小单位。"""

    basic_skills = ["go", "attack"]

    def __init__(self):
        self.player = _Player()
        self.orders = []
        self.notifications = []
        self.place = _Square()
        self.is_idle = True
        self.world = types.SimpleNamespace(time=0)
        self.airground_type = "ground"
        self.distance_to_goal = 0

    def notify(self, msg, *_args, **_kwargs):
        self.notifications.append(msg)

    def stop(self):
        pass


def test_imperative_go_order_notifies_order_ok():
    """强制移动命令（Ctrl+退格）必须播放 order_ok 音效。"""
    unit = _Orders()
    unit.take_order(["go", "sq1"], imperative=True)

    assert "order_ok" in unit.notifications
    assert "order_impossible" not in unit.notifications
    assert unit.orders[0].keyword == "go"
    assert unit.orders[0].is_imperative is True


def test_normal_go_order_still_notifies_order_ok():
    """普通移动命令依然播放 order_ok（行为不变）。"""
    unit = _Orders()
    unit.take_order(["go", "sq1"])

    assert "order_ok" in unit.notifications
    assert unit.orders[0].is_imperative is False


def test_imperative_default_order_to_ground_notifies_order_ok():
    """Ctrl+退格 指向地面方格时，解析为 go 强制命令，同样播放 order_ok。"""
    unit = _Orders()
    unit.get_default_order = lambda target_id: "go"
    unit.take_default_order("sq1", imperative=True)

    assert "order_ok" in unit.notifications
    assert unit.orders[0].keyword == "go"
    assert unit.orders[0].is_imperative is True


class _EventsStub(EntityViewEvents):
    """EntityViewEvents 的最小可测替身。"""

    def __init__(self, player, interface):
        self.player = player
        self.interface = interface
        self.launched = []

    def launch_event_style(self, attr, alert=False, priority=0):
        self.launched.append((attr, alert))


def _make_view(immersion):
    human = object()
    interface = types.SimpleNamespace(player=human, immersion=immersion)
    return _EventsStub(human, interface)


def test_on_order_ok_plays_sound_in_normal_mode():
    """普通视角下本地玩家的 order_ok 事件播放音效。"""
    view = _make_view(immersion=False)
    view.on_order_ok()

    assert view.launched == [("order_ok", True)]


def test_on_order_ok_is_silent_in_immersion_mode():
    """第一人称 RPG 模式屏蔽 order_ok，避免走路时持续蜂鸣。"""
    view = _make_view(immersion=True)
    view.on_order_ok()

    assert view.launched == []


def test_on_order_ok_ignores_other_players_units():
    """非本地玩家的单位不播放 order_ok。"""
    human = object()
    interface = types.SimpleNamespace(player=human, immersion=False)
    view = _EventsStub(object(), interface)
    view.on_order_ok()

    assert view.launched == []
