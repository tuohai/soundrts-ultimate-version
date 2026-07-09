"""强制攻击（imperative go/attack）回归测试。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.worldunit.world_ai_decision import CreatureAIDecision
from soundrts.worldunit.world_order import CreatureOrders


class _Sq:
    def __init__(self, sid="sq1"):
        self.id = sid
        self.objects = []
        self.neighbors = []
        self.exits = []


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
