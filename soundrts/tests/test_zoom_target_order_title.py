"""缩放子格目标（ZoomTarget）在 orders_txt / say_group 中须可播报。"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts import msgparts as mp
from soundrts.clientgameentity.base import _order_title_msg
from soundrts.worldroom import ZoomTarget


class _FakeGoOrder:
    is_deferred = False
    keyword = "go"
    type = None
    unit = None

    def __init__(self, target):
        self.target = target


def _square():
    return SimpleNamespace(
        title=["a3"],
        xmin=0,
        xmax=3000,
        ymin=0,
        ymax=3000,
        world=SimpleNamespace(subcell_precision=3),
    )


def test_zoom_target_title_msg_includes_subcell_coords():
    sq = _square()
    zt = ZoomTarget(sq, 1500, 1500, precision=3)
    msg = zt.title_msg()
    assert "a3" in msg
    assert mp.DOT[0] in msg


def test_order_title_msg_zoom_target_with_subcell_in_zoom_mode():
    sq = _square()
    zt = ZoomTarget(sq, 1500, 1500, precision=3)
    order = _FakeGoOrder(zt)
    interface = SimpleNamespace(zoom_mode=True, place=sq, dobjets={})
    result = _order_title_msg(order, interface)
    assert mp.COMMA[0] in result
    assert "a3" in result
    assert mp.DOT[0] in result


def test_order_title_msg_zoom_target_square_only_outside_zoom_mode():
    """退出缩放模式后，go 目标只报主方格，不含子格坐标。"""
    sq = _square()
    zt = ZoomTarget(sq, 1500, 1500, precision=20)
    order = _FakeGoOrder(zt)
    interface = SimpleNamespace(zoom_mode=False, place=sq, dobjets={})
    result = _order_title_msg(order, interface)
    assert "a3" in result
    assert mp.DOT[0] not in result


def test_order_title_msg_attack_wall_target_uses_short_title(monkeypatch):
    """手动攻击墙时仍走 EntityView.short_title 分支。"""
    sq = _square()
    wall = SimpleNamespace(
        type_name="wall",
        place=sq,
        x=1000,
        y=1000,
        hp=100,
        hp_max=100,
        player=None,
    )

    class _FakeAttackOrder:
        is_deferred = False
        keyword = "attack"
        type = None
        unit = None

        def __init__(self, target):
            self.target = target

    order = _FakeAttackOrder(wall)
    interface = SimpleNamespace(
        zoom_mode=False,
        place=sq,
        dobjets={},
        memory=set(),
        scouted_squares=set(),
        player=SimpleNamespace(),
    )
    result = _order_title_msg(order, interface)
    assert mp.COMMA[0] in result
