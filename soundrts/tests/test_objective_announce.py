"""任务目标序号播报（共用逻辑）。"""
from soundrts import msgparts as mp
from soundrts.lib.msgs import nb2msg
from soundrts.objective_announce import (
    collect_objective_entries,
    collect_planned_objective_numbers,
    navigate_objective_index,
    objective_prefix_msg,
    should_announce_objective_number,
)
from soundrts.worldplayerbase.base import Objective


class _StubPlayer:
    def __init__(self, objectives, required=None, triggers=None):
        self.objectives = objectives
        self._required_objective_numbers = set(required or [])
        planned_primary, planned_secondary = collect_planned_objective_numbers(
            triggers or ()
        )
        self._planned_primary_objective_numbers = planned_primary
        self._planned_secondary_objective_numbers = planned_secondary


def test_collect_planned_objectives_from_separate_timer_triggers():
    triggers = [
        (["timer", "0"], ["add_objective", "1", "7583"]),
        (["timer", "0"], ["add_objective", "2", "7584"]),
    ]
    primary, secondary = collect_planned_objective_numbers(triggers)
    assert primary == {"1", "2"}
    assert secondary == set()


def test_should_announce_number_when_map_plans_multiple_objectives():
    triggers = [
        (["timer", "0"], ["add_objective", "1", "7583"]),
        (["timer", "0"], ["add_objective", "2", "7584"]),
    ]
    player = _StubPlayer({}, triggers=triggers)
    assert should_announce_objective_number(player, optional=False) is True


def test_should_announce_number_for_multiple_primary():
    player = _StubPlayer({}, required={"1", "2", "3"})
    assert should_announce_objective_number(player, optional=False) is True


def test_should_not_announce_number_for_single_primary():
    player = _StubPlayer(
        {Objective.storage_key("1", optional=False): Objective("1", ["7510"])},
        required={"1"},
    )
    assert should_announce_objective_number(player, optional=False) is False


def test_objective_prefix_msg_with_number():
    assert objective_prefix_msg(mp.PRIMARY_OBJECTIVE, "2", True) == (
        mp.PRIMARY_OBJECTIVE + nb2msg(2) + mp.COLON
    )


def test_objective_prefix_msg_without_number():
    assert objective_prefix_msg(mp.PRIMARY_OBJECTIVE, "1", False) == (
        mp.PRIMARY_OBJECTIVE + mp.COLON
    )


def test_navigate_objective_index_from_uninitialized():
    assert navigate_objective_index(-1, 1, 3) == 0
    assert navigate_objective_index(-1, -1, 3) == 2


def test_navigate_objective_index_wraps():
    assert navigate_objective_index(2, 1, 3) == 0
    assert navigate_objective_index(0, -1, 3) == 2


def test_collect_objective_entries_orders_primary_before_secondary():
    world = type("W", (), {"objective": None})()
    player = _StubPlayer(
        {
            Objective.storage_key("1", optional=True): Objective("1", ["7599"], optional=True),
            Objective.storage_key("1", optional=False): Objective("1", ["7583"]),
        }
    )
    entries = collect_objective_entries(world, player)
    assert len(entries) == 2
    assert entries[0] == mp.PRIMARY_OBJECTIVE + mp.COLON + ["7583"]
    assert entries[1] == mp.SECONDARY_OBJECTIVE + mp.COLON + ["7599"]
