"""夺取阈值 100 目标的默认占领命令回归测试。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401 — 解开循环导入

from soundrts.worldunit.worldsoldier import Soldier
from soundrts.worldunit.worldworker import Worker


class _EnemyPlayer:
    def __init__(self):
        self.allied = [self]

    def player_is_an_enemy(self, other):
        return other is not None and other not in self.allied

    def updated_target(self, target):
        return target


class _CaptureTarget:
    hp = 500
    hp_max = 500
    is_vulnerable = True
    is_a_building = True
    capture_hp_threshold = 100

    def __init__(self, owner):
        self.player = owner


def _make_unit(cls):
    unit = cls.__new__(cls)
    unit._basic_skills = {"go", "attack", "gather", "repair", "block", "join_group", "pickup", "drop"}
    unit.orders = []
    owner = _EnemyPlayer()
    enemy = _EnemyPlayer()
    unit.player = owner
    target = _CaptureTarget(enemy)

    def is_an_enemy(other):
        return getattr(other, "player", None) is enemy

    unit.is_an_enemy = is_an_enemy
    unit.player.get_object_by_id = lambda _id: target
    return unit, target


def test_soldier_default_order_on_capture_target_is_capture():
    unit, _target = _make_unit(Soldier)
    assert unit.get_default_order(1) == "capture"


def test_worker_default_order_on_capture_target_is_capture():
    unit, _target = _make_unit(Worker)
    assert unit.get_default_order(1) == "capture"


def test_default_order_not_capture_when_can_capture_disabled():
    unit, _target = _make_unit(Soldier)
    unit.can_capture = 0
    assert unit.get_default_order(1) == "go"


def test_capture_order_not_allowed_when_can_capture_disabled():
    from soundrts.worldorders.movement import CaptureOrder

    unit, target = _make_unit(Soldier)
    unit.can_capture = 0
    target.id = 1
    assert not CaptureOrder.is_allowed(unit, 1)


def test_default_order_not_capture_for_non_capture_threshold():
    unit, target = _make_unit(Soldier)
    target.capture_hp_threshold = 30
    assert unit.get_default_order(1) == "go"


def test_default_order_not_capture_for_allied_target():
    unit, target = _make_unit(Soldier)
    target.player = unit.player
    target.have_enough_space = lambda _u: False
    assert unit.get_default_order(1) != "capture"


def test_capture_order_completes_silently_after_target_captured():
    from soundrts.worldorders.movement import CaptureOrder

    owner = _EnemyPlayer()
    captor = _EnemyPlayer()
    building = _CaptureTarget(owner)
    building.id = "b1"

    class _Unit:
        player = owner
        orders = []
        notifications = []
        is_idle = True
        action = None
        speed = 2
        place = types.SimpleNamespace(objects=[building])

        def is_an_enemy(self, other):
            return getattr(other, "player", None) is captor

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def _near_enough_to_aim(self, _target):
            return True

    unit = _Unit()
    order = CaptureOrder(unit, ["b1"])
    order.target = building
    order.on_queued = lambda: None
    unit.orders.append(order)

    # 占领成功：建筑已归己方
    building.player = owner
    order.execute()

    assert order.is_complete
    assert not order.is_impossible
    assert "order_impossible" not in unit.notifications


def test_capture_order_still_impossible_for_non_capture_friendly_target():
    from soundrts.worldorders.movement import AttackOrder

    owner = _EnemyPlayer()
    ally = _EnemyPlayer()
    owner.allied = [owner, ally]
    ally.allied = [owner, ally]

    class _Friendly:
        id = "u2"
        player = ally
        hp = 100
        is_vulnerable = True
        capture_hp_threshold = 0

    class _Unit:
        player = owner
        orders = []
        notifications = []
        is_idle = True
        action = None
        speed = 2

        def is_an_enemy(self, other):
            return False

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def _near_enough_to_aim(self, _target):
            return True

    unit = _Unit()
    target = _Friendly()
    order = AttackOrder(unit, ["u2"])
    order.target = target
    order.on_queued = lambda: None
    unit.orders.append(order)

    order.execute()

    assert order.is_impossible
    assert "order_impossible" in unit.notifications

def test_imperative_attack_on_captured_barracks_deals_damage_not_capture():
    """已占领的夺取阈值 100 建筑：强制攻击应造成伤害，而非再次占领。"""
    from soundrts.worldaction import AttackAction

    owner = _EnemyPlayer()
    building = _CaptureTarget(owner)
    building.id = "b1"

    class _Unit:
        player = owner
        orders = []
        notifications = []
        can_capture = 1
        speed = 0
        place = types.SimpleNamespace(objects=[building])
        aim_calls = []
        capture_calls = []

        def is_an_enemy(self, other):
            if self._player_ordered_attack_on(other):
                return True
            return getattr(other, "player", None) is not self.player

        def _player_ordered_attack_on(self, other):
            return getattr(other, "id", None) == "b1"

        def _near_enough_to_aim(self, _target):
            return True

        def can_attack(self, _target):
            return True

        def aim(self, target):
            self.aim_calls.append(target)

        def _perform_capture(self, target):
            self.capture_calls.append(target)

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

    unit = _Unit()
    action = AttackAction(unit, building)
    action.update()

    assert unit.aim_calls == [building]
    assert unit.capture_calls == []
    assert "captured_success" not in unit.notifications

