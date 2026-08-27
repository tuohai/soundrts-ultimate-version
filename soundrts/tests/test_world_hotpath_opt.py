"""World hot-path opts: decide skip gate, last_attacker wake, square-space cache."""
from __future__ import annotations

import types

from soundrts.worldunit.world_status_update import CreatureStatusUpdate
from soundrts.worldunit import world_ai_decision as wad


class _UpdateStub:
    player = object()
    inventory = ()
    _buffs = ()
    packable = 0
    unpack_time = 0
    pack_time = 0
    heal_level = 0
    harm_level = 0
    inside = None
    claimable = 0
    herdable = 0
    _herd_leader = None
    action = None
    orders = []
    last_attacker = None
    is_moving = False

    def __init__(self, time, next_decide=1000):
        self.world = types.SimpleNamespace(time=time)
        self._cooldowns = {}
        self._next_decide_time = next_decide
        self.decide_calls = 0
        self.order_calls = 0

    def has_imperative_orders(self):
        return False

    def decide(self):
        self.decide_calls += 1

    def _is_attacking(self):
        return False

    def _execute_orders(self):
        self.order_calls += 1


def test_update_skips_decide_until_next_time():
    s = _UpdateStub(time=500, next_decide=1000)
    CreatureStatusUpdate.update(s)
    assert s.decide_calls == 0
    s.world.time = 1000
    CreatureStatusUpdate.update(s)
    assert s.decide_calls == 1


def test_update_still_executes_orders_when_decide_skipped():
    s = _UpdateStub(time=0, next_decide=10_000)
    s.orders = [object()]
    CreatureStatusUpdate.update(s)
    assert s.decide_calls == 0
    assert s.order_calls == 1


def test_last_attacker_wakes_decide_before_next_time():
    s = _UpdateStub(time=0, next_decide=10_000)
    s.last_attacker = object()
    CreatureStatusUpdate.update(s)
    assert s.decide_calls == 1


class _DecideStub:
    _last_decide_time = 0
    _next_decide_time = 0
    _decision_cache = {}
    _decision_cache_bucket = -1
    _cached_has_attack = True
    _has_yielded = False
    herdable = 0
    last_attacker = None
    orders = []
    ai_mode = "offensive"
    speed = 0  # building: interval 150+300 = 450 (or 700 if not offensive)

    def __init__(self):
        self.world = types.SimpleNamespace(time=10_000)
        self.id = 1
        self.auto_explore = False
        self.place = types.SimpleNamespace(objects=[], neighbors=[], strict_neighbors=[], exits=[])
        self.action = None
        self.is_inside = False
        self.player = types.SimpleNamespace(
            smart_units=False,
            enemy_menace=lambda _p: 0,
            balance=lambda *a, **k: 10,
        )

    def _flee_on_hit_enabled(self):
        return False

    def _has_pursue_attacker(self):
        return False

    def _wildlife_wander(self):
        return False

    def _must_hold(self):
        return False


def test_decide_sets_next_decide_time_after_work():
    u = _DecideStub()
    u.speed = 10
    u.ai_mode = "offensive"
    # Bind real decide; stub missing later methods should not be reached
    # if we only assert the interval bookkeeping at the top.
    # First call at t=10000, last=0 → dt huge → does work until a missing method.
    # Drive only the interval bookkeeping by calling, catching, then checking times.
    try:
        wad.CreatureAIDecision.decide(u)
    except Exception:
        pass
    assert u._last_decide_time == 10_000
    assert u._next_decide_time > 10_000


def test_decide_interval_skip_sets_next_without_work():
    u = _DecideStub()
    u.speed = 10
    u.ai_mode = "offensive"
    u._last_decide_time = 10_000
    u.world.time = 10_050  # dt=50 < 80 floor
    wad.CreatureAIDecision.decide(u)
    assert u._next_decide_time == 10_080
    assert u._last_decide_time == 10_000
