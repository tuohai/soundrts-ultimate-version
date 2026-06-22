"""F9 任务目标逐条播报。"""
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

from unittest.mock import patch

_saved_argv = sys.argv
sys.argv = [_saved_argv[0]] if _saved_argv else ["test"]

from soundrts import msgparts as mp
from soundrts.clientgame.game_resources import cmd_objectives
from soundrts.lib.msgs import nb2msg
from soundrts.worldplayerbase.base import Objective


class _StubWorld:
    objective = None


class _StubPlayer:
    def __init__(self, objectives, required=None):
        self.objectives = objectives
        self._required_objective_numbers = set(required or [])


class _StubInterface:
    def __init__(self, objectives, required=None, world_objective=None):
        self.world = _StubWorld()
        self.world.objective = world_objective
        self.player = _StubPlayer(objectives, required)


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_shows_one_primary_at_a_time(voice_item):
    objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
    }
    interface = _StubInterface(objectives, required={"1"})
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == mp.PRIMARY_OBJECTIVE + mp.COLON + ["7510"]


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_cycles_forward(voice_item):
    objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
        Objective.storage_key("2", optional=False): Objective("2", ["7511"]),
    }
    interface = _StubInterface(objectives, required={"1", "2"})
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == (
        mp.PRIMARY_OBJECTIVE + nb2msg(1) + mp.COLON + ["7510"]
    )
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == (
        mp.PRIMARY_OBJECTIVE + nb2msg(2) + mp.COLON + ["7511"]
    )
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == (
        mp.PRIMARY_OBJECTIVE + nb2msg(1) + mp.COLON + ["7510"]
    )


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_cycles_backward(voice_item):
    objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
        Objective.storage_key("2", optional=False): Objective("2", ["7511"]),
    }
    interface = _StubInterface(objectives, required={"1", "2"})
    cmd_objectives(interface, -1)
    assert voice_item.call_args[0][0] == (
        mp.PRIMARY_OBJECTIVE + nb2msg(2) + mp.COLON + ["7511"]
    )
    cmd_objectives(interface, -1)
    assert voice_item.call_args[0][0] == (
        mp.PRIMARY_OBJECTIVE + nb2msg(1) + mp.COLON + ["7510"]
    )


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_includes_world_objective_first(voice_item):
    objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
    }
    interface = _StubInterface(objectives, required={"1"}, world_objective=["9999"])
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == mp.OBJECTIVE + ["9999"] + mp.PERIOD
    cmd_objectives(interface, 1)
    assert voice_item.call_args[0][0] == mp.PRIMARY_OBJECTIVE + mp.COLON + ["7510"]


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_beep_when_empty(voice_item):
    cmd_objectives(_StubInterface({}), 1)
    assert voice_item.call_args[0][0] == mp.BEEP


@patch("soundrts.clientgame.game_resources.voice.item")
def test_cmd_objectives_resets_index_when_list_changes(voice_item):
    objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
        Objective.storage_key("2", optional=False): Objective("2", ["7511"]),
    }
    interface = _StubInterface(objectives, required={"1", "2"})
    cmd_objectives(interface, 1)
    cmd_objectives(interface, 1)
    assert interface._objective_view_index == 1
    interface.player.objectives = {
        Objective.storage_key("1", optional=False): Objective("1", ["7510"]),
    }
    interface.player._required_objective_numbers = {"1"}
    cmd_objectives(interface, 1)
    assert interface._objective_view_index == 0
    assert voice_item.call_args[0][0] == mp.PRIMARY_OBJECTIVE + mp.COLON + ["7510"]
