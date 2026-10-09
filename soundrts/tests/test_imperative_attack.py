"""强制攻击（imperative go/attack）回归测试。"""
from __future__ import annotations

import types

import pytest

import soundrts.worldunit  # noqa: F401

from soundrts.worldunit.world_ai_decision import CreatureAIDecision
from soundrts.worldunit.world_order import CreatureOrders


class _Sq:
    def __init__(self, sid="sq1"):
        self.id = sid
        self.objects = []
        self.neighbors = []
        self.exits = []
        self.is_inside_place = False


class _Player:
    def __init__(self, neutral=False):
        self.neutral = neutral
        self.id = "p1"
        self.allied = [self]

    def player_is_an_enemy(self, other):
        return other is not None and other is not self and other not in self.allied


class _Stub(CreatureAIDecision):
    def __init__(self, orders=None):
        self.orders = orders or []
        self.player = _Player()
        self.mdg_range = 1
        self.rdg_range = 0
        self.speed = 10
        self.place = _Sq()
        self.world = types.SimpleNamespace(time=0, treaty_until_time=0)

    def is_an_enemy(self, other):
        if self._player_ordered_attack_on(other):
            return True
        p = getattr(other, "player", None)
        return self.player.player_is_an_enemy(p)

    def can_attack_if_in_range(self, other):
        return True

    def _get_melee_damage_vs(self, other):
        return 10

    def _get_ranged_damage_vs(self, other):
        return 0

    def _near_enough_to_aim(self, other):
        return True

    def _is_neutral_target(self, other):
        p = getattr(other, "player", None)
        return p is not None and getattr(p, "neutral", False)


class _Target:
    def __init__(self, uid, neutral=True, huntable=0):
        self.id = uid
        self.player = _Player(neutral=neutral)
        self.hp = 100
        self.is_vulnerable = True
        self.place = _Sq()
        self.x = self.y = 0
        self.is_huntable = huntable


def test_player_ordered_attack_matches_by_id_not_identity():
    target = _Target("deer1", huntable=1)
    proxy = _Target("deer1", huntable=1)
    order = types.SimpleNamespace(
        is_imperative=True,
        target=target,
        keyword="attack",
    )
    unit = _Stub(orders=[order])

    assert unit._player_ordered_attack_on(proxy) is True
    assert unit.is_an_enemy(proxy) is True
    assert unit.can_attack(proxy) is True


def test_imperative_attack_on_neutral_non_huntable():
    target = _Target("shrine1", huntable=0)
    order = types.SimpleNamespace(
        is_imperative=True,
        target=target,
        keyword="attack",
    )
    unit = _Stub(orders=[order])

    assert unit.is_an_enemy(target) is True
    assert unit.can_attack(target) is True


def test_imperative_attack_on_own_unit():
    own_player = _Player(neutral=False)
    target = _Target("pylon1", neutral=False)
    target.player = own_player
    order = types.SimpleNamespace(
        is_imperative=True,
        target=target,
        keyword="attack",
    )
    unit = _Stub(orders=[order])
    unit.player = own_player

    assert unit.is_an_enemy(target) is True
    assert unit.can_attack(target) is True


def test_imperative_default_prefers_repair_then_attack():
    from soundrts.worldunit.world_order import CreatureOrders

    class _Orders(CreatureOrders):
        basic_skills = {"go", "attack", "repair", "enter", "herd"}
        can_build = ("townhall",)

        def __init__(self):
            self.player = types.SimpleNamespace(
                get_object_by_id=lambda _id: None,
                id="human",
            )
            self.orders_taken = []
            self.can_repair = 1

        def is_an_enemy(self, _target):
            return False

        def take_order(self, o, forget_previous=True, imperative=False, order_id=None):
            self.orders_taken.append((list(o), imperative))

        def get_default_order(self, target_id):
            return "go"

    unit = _Orders()
    damaged = types.SimpleNamespace(
        id="b1",
        player=unit.player,
        hp=50,
        hp_max=100,
        is_repairable=True,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    intact = types.SimpleNamespace(
        id="u1",
        player=unit.player,
        hp=100,
        hp_max=100,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    container = types.SimpleNamespace(
        id="t1",
        player=unit.player,
        hp=100,
        hp_max=100,
        is_vulnerable=True,
        have_enough_space=lambda _u: True,
    )
    unit.player.get_object_by_id = lambda i: {
        "b1": damaged,
        "u1": intact,
        "t1": container,
    }[i]

    unit.take_default_order("t1", imperative=True)
    assert unit.orders_taken[-1] == (["enter", "t1"], True)

    unit.take_default_order("b1", imperative=True)
    assert unit.orders_taken[-1] == (["repair", "b1"], True)

    sheep = types.SimpleNamespace(
        id="s1",
        player=unit.player,
        hp=100,
        hp_max=100,
        herdable=1,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    unit.player.get_object_by_id = lambda i: {
        "b1": damaged,
        "u1": intact,
        "t1": container,
        "s1": sheep,
    }[i]
    unit.take_default_order("s1", imperative=True)
    assert unit.orders_taken[-1] == (["herd", "s1"], True)

    unit.take_default_order("u1", imperative=True)
    assert unit.orders_taken[-1] == (["attack", "u1"], True)


def test_get_resolved_default_order_imperative_attack_on_wall():
    """敌方墙：普通默认 go，强制默认 attack（与 take_default_order 一致）。"""
    class _Orders(CreatureOrders):
        basic_skills = ["go", "attack"]

        def __init__(self):
            self.player = _Player()
            self.basic_skills = ["go", "attack"]

        def get_default_order(self, target_id):
            return "go"

        def is_an_enemy(self, _target):
            return True

    unit = _Orders()
    wall = types.SimpleNamespace(
        id="wall1",
        player=_Player(),
        hp=100,
        is_vulnerable=True,
        is_huntable=0,
        have_enough_space=lambda _u: False,
    )
    unit.player.get_object_by_id = lambda i: {"wall1": wall}[i]

    assert unit.get_default_order("wall1") == "go"
    assert unit.get_resolved_default_order("wall1", imperative=False) == "go"
    assert unit.get_resolved_default_order("wall1", imperative=True) == "attack"


def test_resolve_imperative_go_order_on_wall():
    class _Orders(CreatureOrders):
        def __init__(self):
            self.player = _Player()
            self.basic_skills = ["go", "attack"]

    unit = _Orders()
    wall = types.SimpleNamespace(
        id="wall1",
        player=_Player(),
        hp=100,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    unit.player.get_object_by_id = lambda i: {"wall1": wall}[i]

    assert unit.resolve_imperative_go_order("wall1") == "attack"


def test_resolve_imperative_go_order_without_attack_skill():
    class _Orders(CreatureOrders):
        def __init__(self):
            self.player = _Player()
            self.basic_skills = ["go"]

    unit = _Orders()
    wall = types.SimpleNamespace(
        id="wall1",
        player=_Player(),
        hp=100,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    unit.player.get_object_by_id = lambda i: {"wall1": wall}[i]

    assert unit.resolve_imperative_go_order("wall1") == "go"


def test_resolve_imperative_go_order_on_square():
    class _Orders(CreatureOrders):
        def __init__(self):
            self.player = _Player()
            self.basic_skills = ["go", "attack"]

    unit = _Orders()
    square = types.SimpleNamespace(id="sq1", player=None)
    unit.player.get_object_by_id = lambda i: {"sq1": square}[i]

    assert unit.resolve_imperative_go_order("sq1") == "go"


def test_normal_go_queues_behind_imperative_attack():
    """强制攻击中：普通 go 自动排队，先摧毁目标再执行移动。"""
    from soundrts.worldunit.world_order import CreatureOrders

    class _Orders(CreatureOrders):
        basic_skills = ["go", "attack"]

        def __init__(self):
            self.player = _Player()
            self.orders = []
            self.notifications = []
            self.place = _Sq()
            self.is_idle = True
            self.world = types.SimpleNamespace(time=0)

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def stop(self):
            pass

    unit = _Orders()
    townhall = _Target("th1", neutral=True, huntable=0)
    unit.player.get_object_by_id = lambda i: {"th1": townhall, "a1": _Sq("a1")}[i]

    unit.take_order(["attack", "th1"], imperative=True)
    assert len(unit.orders) == 1
    assert unit.orders[0].is_imperative
    assert unit.orders[0].keyword == "attack"

    unit.take_order(["go", "a1"])
    assert "order_impossible" not in unit.notifications
    assert len(unit.orders) == 2
    assert unit.orders[0].keyword == "attack"
    assert unit.orders[0].is_imperative
    assert unit.orders[1].keyword == "go"
    assert not unit.orders[1].is_imperative
    assert "order_ok" in unit.notifications


def test_normal_go_explicit_queue_behind_imperative_attack():
    """强制攻击中：显式排队 go 同样接在队尾。"""
    from soundrts.worldunit.world_order import CreatureOrders

    class _Orders(CreatureOrders):
        basic_skills = ["go", "attack"]

        def __init__(self):
            self.player = _Player()
            self.orders = []
            self.notifications = []
            self.place = _Sq()
            self.is_idle = True
            self.world = types.SimpleNamespace(time=0)

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def stop(self):
            pass

    unit = _Orders()
    townhall = _Target("th1", neutral=True, huntable=0)
    unit.player.get_object_by_id = lambda i: {"th1": townhall, "a1": _Sq("a1")}[i]

    unit.take_order(["attack", "th1"], imperative=True)
    unit.take_order(["go", "a1"], forget_previous=False)
    assert "order_impossible" not in unit.notifications
    assert len(unit.orders) == 2
    assert unit.orders[0].keyword == "attack"
    assert unit.orders[1].keyword == "go"


def test_only_one_queued_order_behind_imperative_attack():
    """强制命令后只能排队一个命令；再下普通命令时替换排队项。"""
    from soundrts.worldunit.world_order import CreatureOrders

    class _Orders(CreatureOrders):
        basic_skills = ["go", "attack"]

        def __init__(self):
            self.player = _Player()
            self.orders = []
            self.notifications = []
            self.place = _Sq()
            self.is_idle = True
            self.world = types.SimpleNamespace(time=0)

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def stop(self):
            pass

    unit = _Orders()
    townhall = _Target("th1", neutral=True, huntable=0)
    a1 = _Sq("a1")
    b1 = _Sq("b1")
    unit.player.get_object_by_id = lambda i: {"th1": townhall, "a1": a1, "b1": b1}[i]

    unit.take_order(["attack", "th1"], imperative=True)
    unit.take_order(["go", "a1"])
    assert len(unit.orders) == 2
    assert unit.orders[1].args == ["a1"]

    unit.take_order(["go", "b1"])
    assert "order_impossible" not in unit.notifications
    assert len(unit.orders) == 2
    assert unit.orders[0].keyword == "attack"
    assert unit.orders[1].keyword == "go"
    assert unit.orders[1].args == ["b1"]


def test_stop_can_interrupt_imperative_attack():
    """stop 命令仍可取消强制攻击。"""
    from soundrts.worldunit.world_order import CreatureOrders

    class _Orders(CreatureOrders):
        basic_skills = ["go", "attack", "stop"]

        def __init__(self):
            self.player = _Player()
            self.orders = []
            self.notifications = []
            self.place = _Sq()
            self.is_idle = True
            self.world = types.SimpleNamespace(time=0)
            # Siege-pack rules: defaults match Creature (unpackable), so
            # cancel_siege_transition's is_packable() early-returns False.
            self.unpack_time = 0
            self.pack_time = 0
            self.packable = 0

        def notify(self, msg, *_args, **_kwargs):
            self.notifications.append(msg)

        def stop(self):
            pass

    unit = _Orders()
    townhall = _Target("th1", neutral=True, huntable=0)
    unit.player.get_object_by_id = lambda i: {"th1": townhall}[i]

    unit.take_order(["attack", "th1"], imperative=True)
    unit.take_order(["stop"])
    assert len(unit.orders) == 0
    assert "order_ok" in unit.notifications


def test_get_resolved_default_order_imperative_go_without_attack_skill():
    """无攻击力单位：强制默认仍为 go。"""
    class _Orders(CreatureOrders):
        def __init__(self):
            self.player = _Player()
            self.basic_skills = ["go"]

        def get_default_order(self, target_id):
            return "go"

    unit = _Orders()
    wall = types.SimpleNamespace(
        id="wall1",
        player=_Player(),
        hp=100,
        is_vulnerable=True,
        have_enough_space=lambda _u: False,
    )
    unit.player.get_object_by_id = lambda i: {"wall1": wall}[i]

    assert unit.get_resolved_default_order("wall1", imperative=True) == "go"
