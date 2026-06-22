"""牧羊与狩猎科技。"""
from __future__ import annotations

import types
from pathlib import Path

import soundrts.worldunit  # noqa: F401

from soundrts.worldunit import world_ai_decision as wad
from soundrts.worldunit.worldworker import Worker
from soundrts.worldorders import ORDERS_DICT
from soundrts.worldorders.movement import HerdOrder


class _Sheep:
    herdable = 1
    hp = 4
    x = 0
    y = 0
    place = object()
    last_attacker = object()

    def __init__(self):
        self._herd_leader = None
        self._herd_player = None


def test_herd_order_is_registered():
    assert ORDERS_DICT["herd"] is HerdOrder


def test_worker_default_order_on_herdable_is_herd():
    worker = Worker.__new__(Worker)
    worker._basic_skills = {"go", "attack", "herd", "gather"}
    worker.can_herd = 1
    worker.orders = []
    worker.player = types.SimpleNamespace(get_object_by_id=lambda _id: _Sheep())
    assert worker.get_default_order(1) == "herd"


def test_worker_with_can_herd_has_herd_skill():
    worker = Worker.__new__(Worker)
    worker.can_herd = 1
    worker.orders = []
    assert "herd" in worker.basic_skills


def test_worker_without_can_herd_no_herd_skill():
    worker = Worker.__new__(Worker)
    worker.can_herd = 0
    worker.orders = []
    assert "herd" not in worker.basic_skills
    worker.player = types.SimpleNamespace(get_object_by_id=lambda _id: _Sheep())
    assert worker.get_default_order(1) != "herd"


def test_worker_default_can_herd_is_disabled():
    worker = Worker.__new__(Worker)
    worker.orders = []
    assert getattr(Worker, "can_herd", None) == 0
    assert "herd" not in worker.basic_skills


def test_herd_order_attaches_leader():
    sheep = _Sheep()
    player = types.SimpleNamespace(
        get_object_by_id=lambda _id: sheep,
        updated_target=lambda t: t,
    )
    worker = types.SimpleNamespace(
        id=1,
        player=player,
        place=sheep.place,
        basic_skills={"herd"},
        notify=lambda *_a, **_k: None,
        _near_enough=lambda _t: True,
        is_idle=True,
        action_target=object(),
        stopped=False,
    )

    def _stop():
        worker.stopped = True
        worker.action_target = None

    worker.stop = _stop
    order = HerdOrder(worker, [99])
    order.on_queued()
    order.execute()
    assert order.is_complete
    assert sheep._herd_leader is worker
    assert sheep.last_attacker is None
    assert worker.stopped


def test_herd_order_moves_first_then_attaches_in_same_square():
    place = object()
    other_place = object()
    sheep = _Sheep()
    sheep.place = place
    sheep.id = 99
    player = types.SimpleNamespace(
        get_object_by_id=lambda _id: sheep,
        updated_target=lambda t: t,
        smart_units=False,
    )
    worker = types.SimpleNamespace(
        id=1,
        player=player,
        place=other_place,
        basic_skills={"herd"},
        notify=lambda *_a, **_k: None,
        action_target=types.SimpleNamespace(id=7),
        orders=[],
        started=[],
        _near_enough=lambda _t: False,
        is_idle=False,
        speed=1.5,
    )
    worker.start_moving_to = lambda target, avoid=False: worker.started.append(
        (target, avoid)
    )

    order = HerdOrder(worker, [99])
    order.on_queued()
    order.execute()
    assert not order.is_complete
    assert sheep._herd_leader is None
    assert worker.started == []

    worker.place = place
    worker.is_idle = True
    worker.stop = lambda: None
    order.execute()
    assert order.is_complete
    assert sheep._herd_leader is worker


def test_herd_order_does_not_reset_path_while_moving():
    sheep_place = object()
    sheep = _Sheep()
    sheep.place = sheep_place
    sheep.id = 99
    player = types.SimpleNamespace(
        get_object_by_id=lambda _id: sheep,
        updated_target=lambda t: t,
        smart_units=False,
    )
    worker = types.SimpleNamespace(
        id=1,
        player=player,
        place=object(),
        basic_skills={"herd"},
        notify=lambda *_a, **_k: None,
        action_target=types.SimpleNamespace(id=7),
        orders=[],
        started=[],
        _near_enough=lambda _t: False,
        is_idle=False,
        speed=1.5,
    )
    worker.start_moving_to = lambda target, avoid=False: worker.started.append(
        (target, avoid)
    )

    order = HerdOrder(worker, [99])
    order.on_queued()
    order.execute()
    assert worker.started == []


def test_herd_follow_stops_when_near_idle_leader_in_same_square():
    shared_place = object()
    leader = types.SimpleNamespace(
        place=shared_place,
        player=types.SimpleNamespace(allied=[]),
        x=0,
        y=0,
        hp=10,
        id=99,
        action_target=None,
    )

    class _Animal:
        herdable = 1
        herd_leash_range = 12000
        speed = 2

        def __init__(self):
            self.x = 1000
            self.y = 0
            self.place = shared_place
            self._herd_leader = leader
            self._herd_player = leader.player
            self._herd_follow_place = None
            self.orders = []
            self.action_target = object()
            self.started = []
            self.stopped = False

        def _near_enough(self, _other):
            return True

        @property
        def is_idle(self):
            return self.action_target is None

        def cancel_all_orders(self):
            self.orders = []

        def stop(self):
            self.stopped = True
            self.action_target = None

        def start_moving_to(self, target, avoid=False):
            self.started.append((target, avoid))

    animal = _Animal()
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal.started == []
    assert animal.stopped
    assert animal._herd_follow_place is shared_place


def test_herd_follow_trails_leader_within_same_square():
    shared_place = object()
    leader = types.SimpleNamespace(
        place=shared_place,
        player=types.SimpleNamespace(allied=[]),
        x=5000,
        y=0,
        hp=10,
        id=99,
        action_target=object(),
    )

    class _Animal:
        herdable = 1
        herd_leash_range = 12000
        speed = 2

        def __init__(self):
            self.x = 0
            self.y = 0
            self.place = shared_place
            self._herd_leader = leader
            self._herd_player = leader.player
            self.orders = []
            self.action_target = None
            self.started = []

        def _near_enough(self, _other):
            return False

        @property
        def is_idle(self):
            return self.action_target is None

        def cancel_all_orders(self):
            self.orders = []

        def stop(self):
            self.action_target = None

        def start_moving_to(self, target, avoid=False):
            self.started.append((target, avoid))

    animal = _Animal()
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal.started == [(leader, False)]


def test_herd_follow_retargets_when_leader_changes_square():
    place_a = object()
    place_b = object()
    place_c = object()
    leader = types.SimpleNamespace(
        place=place_c,
        player=types.SimpleNamespace(allied=[]),
        x=0,
        y=0,
        hp=10,
        id=99,
    )

    class _Animal:
        herdable = 1
        herd_leash_range = 12000
        speed = 2
        x = 0
        y = 0
        place = place_a
        _herd_leader = leader
        _herd_player = leader.player
        _herd_follow_place = place_b
        orders = []
        action_target = types.SimpleNamespace(id=7)
        started = []

        def _near_enough(self, _other):
            return False

        @property
        def is_idle(self):
            return self.action_target is None

        def cancel_all_orders(self):
            self.orders = []

        def start_moving_to(self, target, avoid=False):
            self.started.append((target, avoid))

    animal = _Animal()
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal.started == [(leader, False)]
    assert animal._herd_follow_place is place_c


def test_herd_follow_moves_without_player_target_lookup():
    place_a = object()
    place_b = object()
    leader = types.SimpleNamespace(
        place=place_b,
        player=types.SimpleNamespace(allied=[]),
        x=0,
        y=0,
        hp=10,
        id=99,
    )

    class _Animal:
        herdable = 1
        herd_leash_range = 12000
        speed = 2
        x = 0
        y = 0
        place = place_a
        _herd_leader = leader
        _herd_player = leader.player
        _herd_follow_place = place_a
        orders = []
        action_target = None
        started = []

        def _near_enough(self, _other):
            return False

        @property
        def is_idle(self):
            return self.action_target is None

        def cancel_all_orders(self):
            self.orders = []

        def start_moving_to(self, target, avoid=False):
            self.started.append((target, avoid))

    animal = _Animal()
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal.started == [(leader, False)]
    assert animal._herd_follow_place is place_b

    animal.started.clear()
    animal.action_target = types.SimpleNamespace(id=7)
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal.started == []


def test_herd_follow_clears_on_long_leash():
    leader = types.SimpleNamespace(
        place=types.SimpleNamespace(),
        player=types.SimpleNamespace(allied=[]),
        x=0,
        y=0,
        hp=10,
        id=1,
    )

    class _Animal:
        herdable = 1
        herd_leash_range = 1000
        speed = 2
        x = 5000
        y = 0
        place = types.SimpleNamespace()
        _herd_leader = leader
        _herd_player = leader.player
        orders = []
        is_idle = True

        def _near_enough(self, _other):
            return False

        def take_order(self, *_a, **_k):
            pass

    animal = _Animal()
    wad.CreatureAIDecision._maintain_herd_follow(animal)
    assert animal._herd_leader is None


def test_rules_define_herding_and_hunting_tech():
    text = Path("res/rules.txt").read_text(encoding="utf-8")
    assert "herdable 1" in text
    peasant_block = text.split("def peasant", 1)[1].split("def footman", 1)[0]
    assert "can_herd 1" in peasant_block
    boat_block = text.split("def boat", 1)[1].split("def destroyer", 1)[0]
    assert "can_herd 0" in boat_block
    assert "def hunting_techniques" in text
    assert "can_research hunting_techniques" in text
    assert "effect bonus food_deposit_qty 10" in text


def test_computer_ai_maintain_herding_leads_and_slaughters():
    import sys
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        old_argv = sys.argv
        sys.argv = ["pytest"]
        try:
            from soundrts.worldplayercomputer import Computer
        finally:
            sys.argv = old_argv

    base = types.SimpleNamespace(id="base")
    sheep = types.SimpleNamespace(
        id="sheep1",
        hp=4,
        place=base,
        _herd_leader=None,
    )
    worker = types.SimpleNamespace(
        id="w1",
        place=base,
        can_herd=1,
        can_gather_deposit=["food_carcass"],
        _basic_skills={"go", "attack", "herd", "gather"},
        orders=[],
    )
    worker.take_order = lambda cmd, imperative=False: worker.orders.append(
        (cmd, imperative)
    )
    wildlife = types.SimpleNamespace(neutral=True, units=[sheep])
    townhall = types.SimpleNamespace(
        is_a_building=True,
        place=base,
        storable_resource_types=["resource1", "resource2", "resource3"],
    )

    ai = Computer.__new__(Computer)
    ai.world = types.SimpleNamespace(players=[wildlife])
    ai.units = [townhall]
    ai.nearest_warehouse = lambda place, resource_type, include_building_sites=False: townhall
    sheep._herd_leader = worker

    assert ai._herded_animals(worker) == [sheep]
    assert ai._maintain_worker_herding(worker) is True
    assert worker.orders[0][0] == ["attack", "sheep1"]
    assert worker.orders[0][1] is True

    worker.orders = []
    worker.place = types.SimpleNamespace(id="field")
    sheep.place = types.SimpleNamespace(id="field")
    assert ai._maintain_worker_herding(worker) is True
    assert worker.orders[0][0] == ["go", "base"]
