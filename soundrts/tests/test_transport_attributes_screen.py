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
        transport_capacity=1,
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


def test_load_bonus_dotted_vs_uses_tts_not_raw_key():
    """load_bonus mdg_vs.building 应读成「近战伤害加成 建筑 +10」，不是原文键名。"""
    from soundrts.attributes.utils import get_stat_tts_name

    name = get_stat_tts_name("mdg_vs.building")
    assert mp.MDG_VS[0] in name
    assert "mdg_vs.building" not in name

    model = types.SimpleNamespace(
        transport_capacity=1,
        passenger_attack_types=None,
        load_bonus={"speed": 0.05, "mdg_vs.building": 10},
        passenger_bonus=None,
        attack_inside_chance=0,
    )
    di = DisplayInterface(None, None, None, None, None)
    attrs = []
    di._add_transport_container_attributes(_U(model), attrs)
    assert len(attrs) == 1 and attrs[0][1] == mp.LOAD_BONUS
    load_text = attrs[0][2]
    assert "mdg_vs.building" not in load_text
    assert mp.MDG_VS[0] in load_text
    display = Message(mp.LOAD_BONUS + mp.COLON + load_text).translate_and_collapse(
        remove_sounds=True
    )[0]
    assert "mdg_vs.building" not in display
    assert "10" in display


def test_transport_bonus_list_format_from_rules_read():
    """rules 中 load_bonus / passenger_bonus 读入后，属性界面应显示数值而非 tts 方向词。"""
    snippet = """
def parameters
nb_of_resource_types 2

def bonus_flyer
class soldier
transport_capacity 2
load_bonus rdg 3
passenger_bonus rdg 4
"""
    saved_argv = __import__("sys").argv
    try:
        __import__("sys").argv = ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = Rules()
            r.load(snippet, base_classes=_get_base_classes())
            cls = r.unit_class("bonus_flyer")
            assert cls.load_bonus == {"rdg": 3.0}
            assert cls.passenger_bonus == {"rdg": 4.0}
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


def _load_aoe2_class(name):
    saved_argv = __import__("sys").argv
    try:
        __import__("sys").argv = ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = Rules()
            r.load(
                Path("mods/aoe2/rules.txt").read_text(encoding="utf-8"),
                base_classes=_get_base_classes(),
            )
            return r.unit_class(name)
    finally:
        __import__("sys").argv = saved_argv


def test_non_transport_building_hides_transport_attrs():
    """非运输建筑（如采矿场）的属性界面不应显示「容器内可攻击单位」等。

    历史背景：world_attributes.py 的 interpret() 把
    ``passenger_attack_types`` 设到共享基类 Building 上，导致 mining_camp
    等通过 MRO 继承到 archer_unit/peasant。

    根本修复：CreatureAttributes.interpret 现在把 ``passenger_attack_types``
    写回 ``d`` dict（而非 ``cls=Building`` 类对象），由后续的
    ``type(name, (base,), v)`` 把 ``[]`` 拷进新类自己的命名空间。
    配合显示层的 ``transport_capacity > 0`` 守卫形成双保险。
    """
    for name in ("mining_camp", "lumbermill", "mill", "market", "house"):
        cls = _load_aoe2_class(name)
        # 1. 根因：class 自己不持有 town_center 的 passenger_attack_types
        pat = getattr(cls, "passenger_attack_types", None)
        assert pat in (None, []), (
            f"{name}.passenger_attack_types should be [] (or absent), got {pat!r}"
        )
        # 2. 显式：transport_capacity = 0（非运输）
        assert getattr(cls, "transport_capacity", 0) == 0, name
        # 3. 显示层：UI 上一个运输属性都不该出现
        di = DisplayInterface(None, None, None, None, None)
        attrs = []
        di._add_transport_container_attributes(_U(cls), attrs)
        labels = [a[1] for a in attrs]
        assert mp.PASSENGER_ATTACK_TYPES not in labels, name
        assert mp.LOAD_BONUS not in labels, name
        assert mp.PASSENGER_BONUS not in labels, name
        assert labels == [], name


def test_transport_building_still_shows_transport_attrs():
    """真正的运输容器（town_center / aoe_castle / scouttower）仍应显示。"""
    for name in ("town_center", "aoe_castle", "scouttower"):
        cls = _load_aoe2_class(name)
        # 根因未误伤：运输容器的 passenger_attack_types 仍是正确值
        pat = getattr(cls, "passenger_attack_types", [])
        assert pat and pat != [], (
            f"{name}.passenger_attack_types should be non-empty, got {pat!r}"
        )
        assert getattr(cls, "transport_capacity", 0) > 0, name
        di = DisplayInterface(None, None, None, None, None)
        attrs = []
        di._add_transport_container_attributes(_U(cls), attrs)
        labels = [a[1] for a in attrs]
        assert mp.PASSENGER_ATTACK_TYPES in labels, name
