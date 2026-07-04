"""运输容器属性在 ALT+V 属性界面中的显示。"""
from __future__ import annotations

import types
import warnings
from pathlib import Path

from soundrts import msgparts as mp
from soundrts.attributes.display_interface import DisplayInterface
from soundrts.definitions import Rules, _get_base_classes
from soundrts.lib.message import Message
from soundrts.lib.msgs import NB_ENCODE_SHIFT

class _U:
    def __init__(self, model):
        self.model = model


def _load_wall_class():
    saved_argv = __import__("sys").argv
    try:
        __import__("sys").argv = ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = Rules()
            r.load(
                Path("res/rules.txt").read_text(encoding="utf-8"),
                base_classes=_get_base_classes(),
            )
            return r.unit_class("wall")
    finally:
        __import__("sys").argv = saved_argv


def test_transport_container_attrs_in_attributes_screen():
    wall = _load_wall_class()
    di = DisplayInterface(None, None, None, None, None)
    attrs = []
    di._add_transport_container_attributes(_U(wall), attrs)
    labels = [a[1] for a in attrs]
    assert mp.PASSENGER_ATTACK_TYPES in labels


def test_transport_bonus_attrs_formatted():
    model = types.SimpleNamespace(
        passenger_attack_types=["archer"],
        load_bonus={"speed": 0.5, "mdg": 2},
        passenger_bonus={"rdg_range": 1},
    )
    di = DisplayInterface(None, None, None, None, None)
    attrs = []
    di._add_transport_container_attributes(_U(model), attrs)
    assert len(attrs) == 3
    assert attrs[0][1] == mp.PASSENGER_ATTACK_TYPES
    assert attrs[1][1] == mp.LOAD_BONUS
    assert attrs[2][1] == mp.PASSENGER_BONUS
    load_text = attrs[1][2]
    passenger_text = attrs[2][2]
    assert "+" in load_text
    assert any(isinstance(x, int) and x >= NB_ENCODE_SHIFT for x in load_text)
    assert any(isinstance(x, int) and x >= NB_ENCODE_SHIFT for x in passenger_text)
    load_display = Message(mp.LOAD_BONUS + mp.COLON + load_text).translate_and_collapse(
        remove_sounds=True
    )[0]
    passenger_display = Message(
        mp.PASSENGER_BONUS + mp.COLON + passenger_text
    ).translate_and_collapse(remove_sounds=True)[0]
    assert "在你前面" not in load_display
    assert "在你后面" not in passenger_display
    assert "+0.5" in load_display or "0.5" in load_display
    assert "+2" in load_display or "2" in load_display


def test_transport_bonus_list_format_from_rules_read():
    """rules.txt 中 load_bonus rdg 3 读入为列表时，属性界面应显示 +3 而非 tts 方向词。"""
    saved_argv = __import__("sys").argv
    try:
        __import__("sys").argv = ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = Rules()
            r.load(
                Path("res/rules.txt").read_text(encoding="utf-8"),
                base_classes=_get_base_classes(),
            )
            cls = r.unit_class("new_flyingmachine")
            assert cls.load_bonus == {"rdg": 3}
            assert cls.passenger_bonus == {"rdg": 4}
    finally:
        __import__("sys").argv = saved_argv

    di = DisplayInterface(None, None, None, None, None)
    attrs = []
    di._add_transport_container_attributes(_U(cls), attrs)
    load_text = next(a[2] for a in attrs if a[1] == mp.LOAD_BONUS)
    passenger_text = next(a[2] for a in attrs if a[1] == mp.PASSENGER_BONUS)
    load_display = Message(mp.LOAD_BONUS + mp.COLON + load_text).translate_and_collapse(
        remove_sounds=True
    )[0]
    passenger_display = Message(
        mp.PASSENGER_BONUS + mp.COLON + passenger_text
    ).translate_and_collapse(remove_sounds=True)[0]
    assert "在你前面" not in load_display
    assert "在你后面" not in passenger_display
    assert "+ 3" in load_display or "+3" in load_display
    assert "+ 4" in passenger_display or "+4" in passenger_display