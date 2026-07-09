"""攻击中选中单位：orders_txt 应播报攻击目标，途中移动时附带去往目标。"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts import msgparts as mp
from soundrts.clientgameentity.base import _attack_action_title_msg
from soundrts.clientgameentity.properties import EntityViewProperties
from soundrts.worldaction import AttackAction
from soundrts.worldorders.movement import GoOrder


class _FakeGoOrder:
    is_deferred = False
    keyword = "go"
    type = None
    unit = None

    def __init__(self, target):
        self.target = target


class _OrdersView(EntityViewProperties):
    def __init__(self, interface, model):
        self.interface = interface
        self.model = model

    @property
    def orders(self):
        return getattr(self.model, "orders", [])


def _square():
    return SimpleNamespace(
        title=["a3"],
        xmin=0,
        xmax=3000,
        ymin=0,
        ymax=3000,
        world=SimpleNamespace(subcell_precision=3),
    )


def test_attack_action_title_msg_wall():
    sq = _square()
    wall = SimpleNamespace(type_name="wall", place=sq, x=1000, y=1000)
    archer = SimpleNamespace(action=AttackAction(archer := SimpleNamespace(), wall))
    interface = SimpleNamespace(zoom_mode=False, place=sq, dobjets={}, memory=set(), scouted_squares=set(), player=SimpleNamespace())
    msg = _attack_action_title_msg(interface, archer)
    assert msg is not None
    assert mp.COMMA[0] in msg
    assert 114 in msg or "114" in msg  # 攻击


def test_orders_txt_go_while_attacking_wall_shows_attack_and_go():
    sq = _square()
    wall = SimpleNamespace(type_name="wall", place=sq, x=1000, y=1000)

    from soundrts.worldroom import ZoomTarget

    zt = ZoomTarget(sq, 1500, 1500, precision=3)
    archer = SimpleNamespace(
        type_name="archer",
        place=sq,
        x=500,
        y=500,
        orders=[_FakeGoOrder(zt)],
        action=AttackAction(SimpleNamespace(), wall),
    )
    interface = SimpleNamespace(
        zoom_mode=False,
        place=sq,
        dobjets={},
        memory=set(),
        scouted_squares=set(),
        player=SimpleNamespace(),
    )
    view = _OrdersView(interface, archer)
    txt = view.orders_txt
    assert "114" in txt  # 攻击
    assert "100" in txt and "115" in txt  # 去到
    assert "a3" in txt
    assert mp.DOT[0] not in txt  # 非缩放模式不播子格


def test_orders_txt_go_while_attacking_in_zoom_mode_shows_subcell_destination():
    sq = _square()
    wall = SimpleNamespace(type_name="wall", place=sq, x=1000, y=1000)
    from soundrts.worldroom import ZoomTarget

    zt = ZoomTarget(sq, 1500, 1500, precision=8)
    archer = SimpleNamespace(
        type_name="archer",
        place=sq,
        orders=[_FakeGoOrder(zt)],
        action=AttackAction(SimpleNamespace(), wall),
    )
    interface = SimpleNamespace(
        zoom_mode=True,
        place=sq,
        dobjets={},
        memory=set(),
        scouted_squares=set(),
        player=SimpleNamespace(),
    )
    view = _OrdersView(interface, archer)
    txt = view.orders_txt
    assert "114" in txt
    assert "100" in txt and "115" in txt
    assert mp.DOT[0] in txt  # 缩放模式下 go 目标含子格


def test_orders_txt_explicit_attack_order_unchanged():
    sq = _square()
    wall = SimpleNamespace(type_name="wall", place=sq, x=1000, y=1000)

    class _AttackOrder:
        is_deferred = False
        keyword = "attack"
        type = None
        unit = None
        target = wall

    archer = SimpleNamespace(
        type_name="archer",
        place=sq,
        orders=[_AttackOrder()],
        action=AttackAction(SimpleNamespace(), wall),
    )
    interface = SimpleNamespace(
        zoom_mode=False,
        place=sq,
        dobjets={},
        memory=set(),
        scouted_squares=set(),
        player=SimpleNamespace(),
    )
    view = _OrdersView(interface, archer)
    txt = view.orders_txt
    assert "114" in txt
    # 显式 attack 命令时不重复前置 AttackAction 播报
    assert txt.count("114") == 1
