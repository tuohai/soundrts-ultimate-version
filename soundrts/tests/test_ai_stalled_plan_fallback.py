# -*- coding: utf-8 -*-
"""AI must keep producing (and build its missing requirement chain).

crazyMod's robot build script reaches ``get 28 canon_plasma``, whose
requirement chain is ``canon_plasma -> accelerateur_de_particules ->
supercalculateur -> garage``.  ``supercalculateur`` is an *upgrade* that
takes ~215 s.  While the chain was being built the plan produced nothing
at all: 30 workers stood idle and 2 M gold sat unused, because the only
``get`` token was unreachable and SoundRTS had no fallback production.

Two mechanisms are tested here:

1. ``_fallback_train_army_when_plan_stalled`` — when the plan has been
   stuck on the same ``get`` line for a while, the AI trains an army unit
   from an owned, idle production building (Blizzard's "extra production").

2. ``_ensure_missing_requirement_buildings`` — the AI walks the requirement
   chain of the current plan line and asks for the missing buildings
   instead of waiting until the plan reaches the blocked token.

The tests use the *default* ruleset types (``footman``, ``keep``) so they
do not depend on a particular mod being loaded.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from soundrts.definitions import rules
from soundrts.worldplayercomputer import Computer


def _make_comp(**kwargs):
    comp = Computer.__new__(Computer)
    comp.world = SimpleNamespace(players=[], time=0, turn=0)
    comp.units = []
    comp._plan = []
    comp._line_nb = 0
    comp._previous_linechange = 0
    comp._safe_cnt = 0
    # The stall detector needs to know how much of the current plan line is
    # already satisfied, so it can tell "waiting" from "making progress".
    comp.equivalent = lambda name: name
    comp.nb = lambda name: 0
    comp.future_nb = lambda name: 0
    for k, v in kwargs.items():
        setattr(comp, k, v)
    return comp


class _FakeHost:
    """A building that can train units."""

    def __init__(self, name="barracks", trains=("footman",)):
        self.type_name = name
        self.id = name
        self.is_a_building = True
        self.place = object()
        self.orders = []
        self.trains = tuple(trains)
        self.trained = []

    def take_order(self, order):
        self.trained.append(tuple(order))
        self.orders.append(SimpleNamespace(keyword=order[0]))


# ---------------------------------------------------------------------------
# 1. Fallback production
# ---------------------------------------------------------------------------


def _stalled_comp(plan=None, line_nb=0, seconds=120):
    """A Computer whose current plan line has made no progress for a while.

    The stall detector is progress-based: it needs one call to record the
    starting signature, then a later call (same signature, later clock) to
    report the elapsed time.
    """
    comp = _make_comp(_plan=plan or ["get 30 footman"], _line_nb=line_nb)
    comp.world.time = 0
    comp._plan_progress_stall_seconds()  # records the initial signature
    comp.world.time = seconds * 1000
    return comp


def test_fallback_waits_while_plan_is_moving():
    """A plan line that is still advancing must not trigger the fallback."""
    comp = _make_comp(_plan=["get 4 footman"], _line_nb=0)
    comp._previous_linechange = 0
    comp.world.time = 10 * 1000  # only 10 s on this line

    assert comp._plan_line_is_stalled_get() is False
    assert comp._fallback_train_army_when_plan_stalled() is False


def test_fallback_does_not_fire_on_non_get_line():
    """Only ``get`` lines can stall on an unreachable token."""
    comp = _make_comp(_plan=["goto somewhere"], _line_nb=0)
    comp._previous_linechange = 0
    comp.world.time = 600 * 1000

    assert comp._plan_line_is_stalled_get() is False
    assert comp._fallback_train_army_when_plan_stalled() is False


def test_fallback_fires_even_when_the_watchdog_keeps_refreshing_the_timer():
    """The stall detector must not depend on ``_previous_linechange``.

    ``_watchdog_should_wait`` refreshes ``_previous_linechange`` every tick
    while it considers the line "still completable" (AoE2 jl3: the AI banks
    food for the feudal click on ``get 6 militia`` for minutes).  The
    fallback must still fire, otherwise the AI never produces anything.
    """
    comp = _stalled_comp(seconds=120)
    comp._previous_linechange = comp.world.time  # refreshed right now

    assert comp._plan_line_is_stalled_get() is True


def test_fallback_resets_when_the_plan_line_makes_progress():
    """Progress on the current line must restart the stall clock."""
    comp = _stalled_comp(seconds=120)
    assert comp._plan_line_is_stalled_get() is True

    # One more footman shows up: the line is progressing again.
    comp.nb = lambda name: 1
    assert comp._plan_line_is_stalled_get() is False


def test_fallback_trains_when_plan_is_stalled():
    """A stalled ``get`` line must produce a unit from an idle factory."""
    if rules.unit_class("footman") is None:
        pytest.skip("default ruleset not loaded")

    comp = _stalled_comp(seconds=120)

    assert comp._plan_line_is_stalled_get() is True

    host = _FakeHost()
    comp.units = [host]

    # Patch the candidate lookup so the test does not depend on the real
    # rules of whichever mod is loaded.
    comp._fallback_army_train_candidates = lambda: [("footman", host)]
    comp.missing_resources = lambda cost: []
    comp.gather = lambda cost, pop: True
    comp._invalidate_play_derived_counts = lambda: None
    comp._saving_food_for_age = lambda: False

    assert comp._fallback_train_army_when_plan_stalled() is True
    assert host.trained == [("train", "footman")]


def test_fallback_skips_units_that_cost_more_than_the_treasury():
    """The fallback must not order a unit the AI cannot pay for."""
    if rules.unit_class("footman") is None:
        pytest.skip("default ruleset not loaded")

    comp = _stalled_comp(seconds=120)

    host = _FakeHost()
    comp.units = [host]
    comp._fallback_army_train_candidates = lambda: [("footman", host)]
    comp.missing_resources = lambda cost: [0]  # gold missing
    comp.gather = lambda cost, pop: True
    comp._invalidate_play_derived_counts = lambda: None
    comp._saving_food_for_age = lambda: False

    assert comp._fallback_train_army_when_plan_stalled() is False
    assert host.trained == []


def test_fallback_candidates_skip_busy_buildings():
    """A factory that is already training must not get a second order."""
    if rules.unit_class("footman") is None:
        pytest.skip("default ruleset not loaded")

    comp = _make_comp(_plan=["get 30 footman"], _line_nb=0)
    comp._previous_linechange = 0
    comp.world.time = 120 * 1000

    busy = _FakeHost()
    busy.orders = [SimpleNamespace(keyword="train")]
    comp.units = [busy]
    comp.equivalent = lambda name: name
    comp.has_all = lambda reqs: True
    comp._token_is_army_for_inject = lambda name: True

    assert comp._fallback_army_train_candidates() == []


# ---------------------------------------------------------------------------
# 2. Requirement-chain backfill
# ---------------------------------------------------------------------------


def test_requirement_chain_is_walked_recursively():
    """The chain below the token must be included, not just its first level.

    In the default ruleset ``keep`` requires ``barracks``, which requires
    ``feudal_age``.  A one-level lookup would only ever find ``barracks``
    and would never notice the phase requirement.
    """
    if rules.unit_class("keep") is None:
        pytest.skip("default ruleset not loaded")

    comp = _make_comp(_plan=["get 1 keep"], _line_nb=0)

    wanted = comp._plan_line_requirement_buildings("get 1 keep")
    assert "barracks" in wanted


def test_requirement_backfill_ignores_non_get_lines():
    comp = _make_comp(_plan=["goto somewhere"], _line_nb=0)
    assert comp._ensure_missing_requirement_buildings() is False


def test_requirement_backfill_asks_for_the_missing_building():
    """The backfill must actually request a missing requirement building."""
    if rules.unit_class("keep") is None:
        pytest.skip("default ruleset not loaded")

    comp = _make_comp(_plan=["get 1 keep"], _line_nb=0)
    comp.has = lambda name: False
    comp.future_nb = lambda name: 0
    comp._requirement_building_is_buildable = lambda name: True

    pending = {"count": 0}

    def _pending_count():
        return pending["count"]

    comp._total_pending_order_count = _pending_count

    requested = []

    def _get(nb, name):
        requested.append(name)
        # ``_get`` queues a build order: the pending-order count grows.
        pending["count"] += 1
        return False

    comp._get = _get

    assert comp._ensure_missing_requirement_buildings() is True
    assert "barracks" in requested


def test_requirement_backfill_skips_already_owned_buildings():
    """Nothing must be requested when the chain is already built."""
    if rules.unit_class("keep") is None:
        pytest.skip("default ruleset not loaded")

    comp = _make_comp(_plan=["get 1 keep"], _line_nb=0)
    comp.has = lambda name: True
    comp.future_nb = lambda name: 0
    comp._requirement_building_is_buildable = lambda name: True
    comp._total_pending_order_count = lambda: 0

    requested = []
    comp._get = lambda nb, name: requested.append(name)

    assert comp._ensure_missing_requirement_buildings() is False
    assert requested == []


def test_requirement_backfill_skips_buildings_already_in_progress():
    """A building that is already being built must not be ordered twice."""
    if rules.unit_class("keep") is None:
        pytest.skip("default ruleset not loaded")

    comp = _make_comp(_plan=["get 1 keep"], _line_nb=0)
    comp.has = lambda name: False
    comp.future_nb = lambda name: 1  # already building
    comp._requirement_building_is_buildable = lambda name: True
    comp._total_pending_order_count = lambda: 0

    requested = []
    comp._get = lambda nb, name: requested.append(name)

    assert comp._ensure_missing_requirement_buildings() is False
    assert requested == []
