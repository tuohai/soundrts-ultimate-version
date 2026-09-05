"""信号弹语音：谁打了哪一格；规则开关与 style 名称。"""
from types import SimpleNamespace

from soundrts import msgparts as mp
from soundrts.flare_announce import (
    _flag_on,
    flare_title_msgs,
    flare_voice_msg,
    player_by_number,
)
from soundrts.worldplayerbase.commands import CommandsMixin


def test_flag_on():
    assert _flag_on(1) is True
    assert _flag_on(0) is False
    assert _flag_on(["1"]) is True
    assert _flag_on(["0"]) is False
    assert _flag_on(None) is False


def test_own_flare_speaks_square_without_name():
    place = SimpleNamespace(title=["a3"])
    you = SimpleNamespace(name=["Alice"], number=1)
    title = flare_title_msgs()
    assert flare_voice_msg(place, you, you) == title + list(mp.AT) + ["a3"]


def test_ally_flare_speaks_sender_and_square():
    place = SimpleNamespace(title=["b2"])
    ally = SimpleNamespace(name=["Bob"], number=2)
    you = SimpleNamespace(name=["Alice"], number=1)
    title = flare_title_msgs()
    assert flare_voice_msg(place, ally, you) == ["Bob"] + title + list(mp.AT) + ["b2"]


def test_flare_without_square_still_says_title():
    you = SimpleNamespace(name=["Alice"], number=1)
    assert flare_voice_msg(None, you, you) == flare_title_msgs()


def test_flare_title_from_style(monkeypatch):
    class _Style:
        def get(self, obj, attr, warn_if_not_found=True):
            if obj == "parameters" and attr == "signal_flare_title":
                return [9001]
            return []

    monkeypatch.setattr("soundrts.definitions.style", _Style())
    assert flare_title_msgs() == [9001]
    place = SimpleNamespace(title=["c1"])
    assert flare_voice_msg(place) == [9001] + list(mp.AT) + ["c1"]


def test_player_by_number():
    a = SimpleNamespace(number=1)
    b = SimpleNamespace(number=2)
    world = SimpleNamespace(players=(a, b))
    assert player_by_number(world, "2") is b
    assert player_by_number(world, None) is None


def test_cmd_flare_pushes_sender_number_to_allies(monkeypatch):
    monkeypatch.setattr("soundrts.flare_announce.signal_flare_enabled", lambda: True)
    square = SimpleNamespace(id="sq1")

    class _P:
        def __init__(self, number):
            self.number = number
            self.pushed = []
            self.allied = []

        def push(self, *args):
            self.pushed.append(args)

        def get_object_by_id(self, _i):
            return square

    you = _P(4)
    ally = _P(5)
    you.allied = [you, ally]
    CommandsMixin.cmd_flare(you, ["sq1"])
    assert you.pushed == [("flare", "sq1", 4)]
    assert ally.pushed == [("flare", "sq1", 4)]


def test_cmd_flare_noop_when_disabled(monkeypatch):
    monkeypatch.setattr("soundrts.flare_announce.signal_flare_enabled", lambda: False)
    square = SimpleNamespace(id="sq1")

    class _P:
        def __init__(self):
            self.pushed = []
            self.allied = []
            self.number = 1

        def push(self, *args):
            self.pushed.append(args)

        def get_object_by_id(self, _i):
            return square

    you = _P()
    you.allied = [you]
    CommandsMixin.cmd_flare(you, ["sq1"])
    assert you.pushed == []
