# -*- coding: utf-8 -*-
"""The AI spreads its workers over the sources instead of piling them up.

Two rules are covered here:

* the *load balancing* of the gather targets (difficulty-graded);
* the *base expansion* policy (difficulty-graded, rules-driven).

Everything is tested through the generic interfaces, so the same tests
hold for a mod that calls its worker ``serf`` and its base ``mairie``
and for a mod that calls them ``peasant`` and ``town_center``.
"""
from __future__ import annotations

import os
import sys
import types
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import world_ai_economy as eco
    from soundrts.definitions import rules
    from soundrts.worldplayercomputer import Computer

sys.argv = saved


# ---------------------------------------------------------------------------
# The policy module on its own
# ---------------------------------------------------------------------------


def test_beginner_piles_up_on_one_source():
    """A beginner AI keeps its villagers together -- that is the point."""
    assert eco.balances_workers("beginner") is False
    assert eco.balances_workers("timers") is False
    assert eco.balancing_tier("beginner") == "none"


def test_the_higher_tiers_balance():
    assert eco.balances_workers("intermediate") is True
    assert eco.balances_workers("advanced") is True
    assert eco.balances_workers("expert") is True
    assert eco.balances_workers("nightmare") is True


def test_only_the_top_tiers_balance_strictly():
    """Strict balancing also considers the less-needed sources."""
    assert eco.balances_strictly("intermediate") is False
    assert eco.balances_strictly("advanced") is True
    assert eco.balances_strictly("nightmare") is True


def test_an_unknown_difficulty_balances_but_does_not_assume_the_best():
    """A mod's own difficulty name still gets the balancing."""
    assert eco.balancing_tier("tang_empire_easy") == "needed"
    assert eco.balances_strictly("tang_empire_easy") is False


def test_the_legacy_tier_names_keep_their_meaning():
    """``easy`` was the old beginner tier, ``aggressive`` the old intermediate."""
    assert eco.balancing_tier("easy") == "none"
    assert eco.balancing_tier("aggressive") == "needed"


def test_the_order_key_puts_the_load_before_the_distance():
    """Two candidates that are equally needed: the emptier one wins."""
    key = eco.balanced_order_key("expert", 1.0, 0, load=0, distance=100.0)
    other = eco.balanced_order_key("expert", 1.0, 0, load=1, distance=1.0)
    assert key < other


def test_the_order_key_puts_the_need_before_the_load():
    """A source the AI does not need stays empty, however empty it is."""
    needed = eco.balanced_order_key("expert", 1.0, 0, load=5, distance=1.0)
    not_needed = eco.balanced_order_key("expert", 9.0, 0, load=0, distance=1.0)
    assert needed < not_needed


def test_a_beginner_ignores_the_load_entirely():
    key = eco.balanced_order_key("beginner", 1.0, 0, load=0, distance=100.0)
    other = eco.balanced_order_key("beginner", 1.0, 0, load=1, distance=1.0)
    assert key > other  # the nearer one still wins


# ---------------------------------------------------------------------------
# Base expansion policy
# ---------------------------------------------------------------------------


def test_a_beginner_never_expands_on_its_own():
    assert eco.expansion_headroom("beginner") == 0
    assert eco.expansion_headroom("timers") == 0


def test_the_higher_tiers_get_a_budget():
    assert eco.expansion_headroom("intermediate") == 1
    assert eco.expansion_headroom("advanced") == 2
    assert eco.expansion_headroom("nightmare") == 3


def test_no_housing_capacity_means_no_pressure():
    """A rules set without any housing cannot press the AI."""
    assert eco.population_is_pressured(0, 10) is False


def test_a_full_housing_means_pressure():
    """The AI's own housing is nearly full -> it needs another base."""
    # 20 housing, 16 used -> 80 % full -> pressure.
    assert eco.population_is_pressured(20, 16) is True
    # 20 housing, 4 used -> plenty of room -> no pressure.
    assert eco.population_is_pressured(20, 4) is False


def test_the_global_population_limit_is_not_the_housing():
    """The world's population limit is shared by every player.

    AoE2's cw1 map uses 1999; comparing the AI's housing against it
    would never report any pressure, so the housing capacity is what
    counts.
    """
    # 140 housing, 135 used -> pressure, whatever the global limit is.
    assert eco.population_is_pressured(140, 135) is True
    assert eco.population_is_pressured(140, 20) is False


def test_a_fully_used_housing_is_pressure():
    assert eco.population_is_pressured(20, 20) is True
    assert eco.population_is_pressured(20, 25) is True


def test_expansion_needs_everything():
    """One missing condition is enough to refuse the expansion."""
    common = dict(
        owned_base_count=1,
        target_base_count=2,
        population_pressured=True,
        resources_ready=True,
        has_room_to_build=True,
        housing_needed=True,
    )
    assert eco.expansion_is_worthwhile(**common) is True
    assert eco.expansion_is_worthwhile(**{**common, "resources_ready": False}) is False
    assert eco.expansion_is_worthwhile(**{**common, "has_room_to_build": False}) is False
    assert (
        eco.expansion_is_worthwhile(
            **{**common, "population_pressured": False, "housing_needed": False}
        )
        is False
    )


def test_expansion_stops_at_the_target():
    assert (
        eco.expansion_is_worthwhile(
            owned_base_count=2,
            target_base_count=2,
            population_pressured=True,
            resources_ready=True,
            has_room_to_build=True,
            housing_needed=True,
        )
        is False
    )


# ---------------------------------------------------------------------------
# The rules attributes
# ---------------------------------------------------------------------------


def test_a_base_without_the_attribute_is_worth_expanding():
    """A mod does not have to declare anything to get the behaviour."""
    assert eco.base_is_worth_expanding(rules, "no_such_class_at_all") is True


def test_the_attribute_is_read_when_present():
    fake = types.SimpleNamespace(
        unit_class=lambda name: (
            types.SimpleNamespace() if name == "keep" else None
        ),
        get=lambda cls, attr: ["0"] if attr == "ai_base_worth_expanding" else None,
    )
    assert eco.base_is_worth_expanding(fake, "keep") is False
    assert eco.base_is_worth_expanding(fake, "other") is True


def test_the_supplies_attribute_is_a_list():
    fake = types.SimpleNamespace(
        unit_class=lambda name: types.SimpleNamespace(),
        get=lambda cls, attr: ["resource3", "resource1"],
    )
    assert eco.base_supplies(fake, "anything") == ("resource3", "resource1")


def test_a_class_without_the_attribute_supplies_nothing():
    fake = types.SimpleNamespace(
        unit_class=lambda name: types.SimpleNamespace(),
        get=lambda cls, attr: None,
    )
    assert eco.base_supplies(fake, "anything") == ()


# ---------------------------------------------------------------------------
# The AI itself: the workers really do spread out
# ---------------------------------------------------------------------------


class _Place:
    def __init__(self, pid, x, y, world=None):
        self.id = pid
        self.x = x
        self.y = y
        self.world = world
        self.exits = ()

    def shortest_path_distance_to(self, dest, player=None, plane="ground", avoid=False):
        return abs(self.x - dest.x) + abs(self.y - dest.y)


class _Target:
    """A gather target: a deposit or a farm."""

    def __init__(self, tid, place, resource_index=2, renewable=False):
        self.id = tid
        self.place = place
        self.resource_type = "resource%d" % (resource_index + 1)
        self.type_name = "deposit%d" % resource_index
        self.resource_qty = 100
        self.auto_cultivate = 1 if renewable else 0


class _Worker:
    def __init__(self, wid, place, world):
        self.id = wid
        self.place = place
        self.orders = []
        self.can_gather_deposit = ["all"]
        self.airground_type = "ground"
        self.world = world


class _Order:
    keyword = "gather"

    def __init__(self, target):
        self.target = target


class _World:
    def __init__(self, players):
        self.players = players


def _make_ai(ai_type, targets, workers):
    """A Computer with just enough state to choose gather targets."""
    p = Computer.__new__(Computer)
    p.AI_type = ai_type
    p.units = list(workers)
    p._play_memo = {}
    p.perception = set()
    p.memory = set()
    p.world = _World([p])
    p.resources = [0, 0, 100]
    p._workers = workers
    p._resource_need_ratio = lambda _i: 1.0
    p._target_resource_index = lambda t: int(t.resource_type[8:]) - 1
    p._worker_can_gather_deposit = lambda *_a, **_k: True
    p._gatherable_building_targets = lambda _w: list(targets)
    p._known_ok_deposits = lambda: []
    p._keep_lumberjacks = lambda: False
    p._need_later_age_production_wood = lambda: False
    p._wood_dropoff_place = lambda: None
    p._worker_gather_order = lambda w: None
    return p


def test_the_workers_spread_over_the_sources():
    """Four farms, four workers: one worker per farm, not four on one."""
    world_holder = {}
    origin = _Place("home", 0, 0)
    farms = [
        _Target("f%d" % i, _Place("p%d" % i, i * 10, 0), renewable=True)
        for i in range(4)
    ]
    workers = [_Worker(i, origin, world_holder) for i in range(4)]
    ai = _make_ai("expert", farms, workers)
    ai.world = _World([ai])

    chosen = []
    for w in workers:
        target = ai._choose_gather_target(w)
        chosen.append(target.id)
        # The worker is now busy there: record it so the next worker sees
        # the load (this is what the engine does when the order starts).
        w.orders = [_Order(target)]

    assert len(set(chosen)) == 4, chosen


def test_a_beginner_keeps_the_workers_together():
    """The beginner tier piles them on the nearest source."""
    origin = _Place("home", 0, 0)
    farms = [
        _Target("f%d" % i, _Place("p%d" % i, i * 10, 0), renewable=True)
        for i in range(4)
    ]
    workers = [_Worker(i, origin, None) for i in range(4)]
    ai = _make_ai("beginner", farms, workers)
    ai.world = _World([ai])

    chosen = []
    for w in workers:
        target = ai._choose_gather_target(w)
        chosen.append(target.id)
        w.orders = [_Order(target)]

    assert len(set(chosen)) == 1, chosen


def test_the_ai_does_not_send_a_worker_to_a_source_it_does_not_need():
    """Balancing never overrides the need: an unneeded resource stays idle."""
    origin = _Place("home", 0, 0)
    food = _Target("food", _Place("pf", 5, 0), resource_index=2)
    gold = _Target("gold", _Place("pg", 1, 0), resource_index=0)
    workers = [_Worker(0, origin, None)]
    ai = _make_ai("expert", [food, gold], workers)
    ai.world = _World([ai])
    # The AI is desperate for gold and does not need food.
    ai._resource_need_ratio = lambda i: 0.1 if i == 0 else 9.0

    target = ai._choose_gather_target(workers[0])

    assert target is gold


def test_the_base_expansion_waits_for_the_population():
    """A base is not opened while the housing is still empty."""
    ai = Computer.__new__(Computer)
    ai.AI_type = "expert"
    ai._target_townhalls = 0
    ai.world = types.SimpleNamespace(population_limit=1999)
    ai.population = 20          # housing the AI's own buildings provide
    ai.used_population = 4      # population the AI's units consume
    ai.units = []
    ai._main_base_type_names = lambda: ("town_center",)
    ai.future_nb = lambda _names: 1

    assert ai._automatic_base_target() == 0


def test_the_base_expansion_opens_a_base_when_the_housing_is_full():
    ai = Computer.__new__(Computer)
    ai.AI_type = "expert"
    ai._target_townhalls = 0
    ai.world = types.SimpleNamespace(population_limit=1999)
    ai.population = 20
    ai.used_population = 18
    ai.units = []
    ai._main_base_type_names = lambda: ("town_center",)
    ai.future_nb = lambda _names: 1

    assert ai._automatic_base_target() == 1 + 3


def test_the_global_population_limit_does_not_trigger_the_expansion():
    """The world's population limit is shared by every player.

    AoE2's cw1 map uses 1999.  An AI with 140 housing and 135 units is
    under pressure even though 135 is far below 1999.
    """
    ai = Computer.__new__(Computer)
    ai.AI_type = "expert"
    ai._target_townhalls = 0
    ai.world = types.SimpleNamespace(population_limit=1999)
    ai.population = 140
    ai.used_population = 135
    ai.units = []
    ai._main_base_type_names = lambda: ("town_center",)
    ai.future_nb = lambda _names: 1

    assert ai._automatic_base_target() == 1 + 3


def test_a_beginner_never_opens_a_base_on_its_own():
    ai = Computer.__new__(Computer)
    ai.AI_type = "beginner"
    ai._target_townhalls = 0
    ai.world = types.SimpleNamespace(population_limit=1999)
    ai.population = 20
    ai.used_population = 18
    ai.units = []
    ai._main_base_type_names = lambda: ("town_center",)
    ai.future_nb = lambda _names: 1

    assert ai._automatic_base_target() == 0


def test_the_base_expansion_uses_the_base_type_of_the_mod():
    """The base is found by its rules, not by its name."""
    ai = Computer.__new__(Computer)
    ai.AI_type = "expert"
    ai._target_townhalls = 0
    ai.world = types.SimpleNamespace(population_limit=1999)
    ai.population = 20
    ai.used_population = 18
    ai.units = []
    ai._main_base_type_names = lambda: ("mairie",)
    ai.future_nb = lambda _names: 1

    assert ai._automatic_base_target() == 1 + 3


# ---------------------------------------------------------------------------
# Multi-queue reinforcement (多线补兵)
# ---------------------------------------------------------------------------


def test_a_beginner_keeps_a_single_production_queue():
    """One queue is enough for a beginner opponent."""
    assert eco.should_open_extra_queue("beginner") is False
    assert eco.should_open_extra_queue("timers") is False
    assert eco.multi_queue_limit("beginner") == 0


def test_the_higher_tiers_open_more_queues():
    assert eco.should_open_extra_queue("intermediate") is True
    assert eco.multi_queue_limit("advanced") == 2
    assert eco.multi_queue_limit("expert") == 3
    assert eco.multi_queue_limit("nightmare") == 4


def test_an_unknown_difficulty_opens_one_extra_queue():
    """A mod's own difficulty name still gets a second queue."""
    assert eco.multi_queue_limit("tang_empire_easy") == 1


def test_the_queue_budget_is_capped_by_what_the_ai_owns():
    """A tier never invents buildings to fill its quota."""
    assert eco.extra_queue_budget("expert", 1) == 0
    assert eco.extra_queue_budget("expert", 2) == 1
    assert eco.extra_queue_budget("expert", 5) == 2
    assert eco.extra_queue_budget("beginner", 9) == 0


def test_a_busy_building_has_no_room_for_another_order():
    host = types.SimpleNamespace(
        is_a_building=True,
        orders=[types.SimpleNamespace(keyword="train")],
    )
    assert eco.production_queue_depth(host) == 1
    assert eco.can_queue_on_host(host) is False


def test_an_idle_building_has_room_for_an_order():
    host = types.SimpleNamespace(is_a_building=True, orders=[])
    assert eco.production_queue_depth(host) == 0
    assert eco.can_queue_on_host(host) is True


def test_a_building_doing_something_else_is_still_a_valid_host():
    """A worker building inside the barracks does not block the queue."""
    host = types.SimpleNamespace(
        is_a_building=True,
        orders=[types.SimpleNamespace(keyword="build")],
    )
    assert eco.production_queue_depth(host) == 0
    assert eco.can_queue_on_host(host) is True


def test_the_production_key_prefers_the_least_loaded_building():
    key = eco.balanced_production_key("expert", load=0, queue_depth=0, threat=1, name="a")
    other = eco.balanced_production_key(
        "expert", load=3, queue_depth=0, threat=9, name="b"
    )
    assert key < other


def test_a_beginner_ignores_the_production_load():
    key = eco.balanced_production_key("beginner", load=0, queue_depth=0, threat=1, name="a")
    other = eco.balanced_production_key(
        "beginner", load=3, queue_depth=0, threat=9, name="b"
    )
    assert key > other


# ---------------------------------------------------------------------------
# The AI itself: the extra queues are really opened
# ---------------------------------------------------------------------------


class _TrainOrder:
    keyword = "train"

    def __init__(self, type_name):
        self.type_name = type_name


class _Host:
    """A production building that records the orders it receives."""

    def __init__(self, hid, type_name="barracks"):
        self.id = hid
        self.type_name = type_name
        self.is_a_building = True
        self.place = object()
        self.orders = []
        self.trained = []
        # The rules class is what the engine reads to know what the
        # building can train.
        self.type = rules.unit_class(type_name)

    def take_order(self, order):
        self.trained.append(tuple(order))
        self.orders.append(_TrainOrder(order[1]))


def _make_production_ai(ai_type, hosts, units=(), plan=None, line_nb=0):
    ai = Computer.__new__(Computer)
    ai.AI_type = ai_type
    ai.units = list(hosts) + list(units)
    ai.world = types.SimpleNamespace(players=[])
    ai.equivalent = lambda name: name
    ai.has_all = lambda _reqs: True
    ai.missing_resources = lambda _cost: []
    ai._token_is_army_for_inject = lambda name: True
    ai._invalidate_play_derived_counts = lambda: None
    ai._plan = list(plan or ["get 10 footman"])
    ai._line_nb = line_nb
    ai.future_nb = lambda _name: 0
    return ai


def test_the_expert_ai_uses_two_barracks_at_once():
    """Two barracks, two queues: the second one must not stay idle."""
    if rules.unit_class("footman") is None:
        return
    first = _Host("b1")
    second = _Host("b2")
    ai = _make_production_ai("expert", [first, second])

    assert ai._maintain_multi_queue_production() is True
    assert len(first.trained) == 1
    assert len(second.trained) == 1


def test_a_beginner_ai_keeps_one_barracks_busy():
    """The beginner tier is not allowed a second queue."""
    first = _Host("b1")
    second = _Host("b2")
    ai = _make_production_ai("beginner", [first, second])

    assert ai._maintain_multi_queue_production() is False
    assert first.trained == []
    assert second.trained == []


def test_one_barracks_is_not_a_multi_queue():
    """A single production building behaves exactly like before."""
    first = _Host("b1")
    ai = _make_production_ai("expert", [first])

    assert ai._maintain_multi_queue_production() is False
    assert first.trained == []


def test_a_busy_barracks_is_left_alone():
    """A building that is already training is not given a second order."""
    first = _Host("b1")
    second = _Host("b2")
    second.orders = [_TrainOrder("footman")]
    ai = _make_production_ai("expert", [first, second])

    assert ai._maintain_multi_queue_production() is True
    assert len(first.trained) == 1
    assert second.trained == []


def test_the_extra_queue_does_not_spend_what_the_ai_cannot_pay_for():
    """No order when the treasury is short."""
    if rules.unit_class("footman") is None:
        return
    first = _Host("b1")
    second = _Host("b2")
    ai = _make_production_ai("expert", [first, second])
    ai.missing_resources = lambda _cost: [0]  # gold missing

    assert ai._maintain_multi_queue_production() is False
    assert first.trained == []
    assert second.trained == []


def test_the_extra_queue_spreads_over_the_least_loaded_building():
    """When there are more factories than the tier allows, the busiest is left out."""
    if rules.unit_class("footman") is None:
        return
    busy = _Host("b1")
    idle_a = _Host("b2")
    idle_b = _Host("b3")
    idle_c = _Host("b4")
    # The first barracks already made ten footmen.
    ai = _make_production_ai("expert", [busy, idle_a, idle_b, idle_c])
    ai._ai_trained_by_host = {"b1": 10}

    # The expert tier runs three queues at a time: three of the four
    # factories get an order, and the busiest one is the one left out.
    assert ai._maintain_multi_queue_production() is True
    assert busy.trained == []
    assert len(idle_a.trained) == 1
    assert len(idle_b.trained) == 1
    assert len(idle_c.trained) == 1


def test_the_extra_queue_keeps_the_number_of_queues_bounded():
    """The tier's limit caps how many factories run at the same time."""
    if rules.unit_class("footman") is None:
        return
    hosts = [_Host("b%d" % i) for i in range(5)]
    ai = _make_production_ai("advanced", hosts)  # advanced: two queues

    assert ai._maintain_multi_queue_production() is True
    busy = [h for h in hosts if h.trained]
    assert len(busy) == 2


def test_the_production_hosts_are_found_by_their_rules_not_by_their_name():
    """A building that trains nothing is not a production building."""
    empty = _Host("b1", type_name="house")
    ai = _make_production_ai("expert", [empty])

    assert ai._owned_production_hosts() == []


def test_the_extra_queue_respects_the_plan_quota():
    """The AI never builds more than the build order asked for."""
    if rules.unit_class("footman") is None:
        return
    first = _Host("b1")
    second = _Host("b2")
    ai = _make_production_ai(
        "expert", [first, second], plan=["get 1 footman"]
    )

    assert ai._maintain_multi_queue_production() is True
    # One footman wanted: exactly one order in total.
    assert len(first.trained) + len(second.trained) == 1


def test_the_extra_queue_does_nothing_when_the_plan_is_satisfied():
    """No soldier is missing: the extra queues stay quiet."""
    if rules.unit_class("footman") is None:
        return
    first = _Host("b1")
    second = _Host("b2")
    ai = _make_production_ai("expert", [first, second], plan=["get 4 footman"])
    ai.future_nb = lambda _name: 4  # the plan is already satisfied

    assert ai._maintain_multi_queue_production() is False
    assert first.trained == []
    assert second.trained == []


