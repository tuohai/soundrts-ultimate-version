# -*- coding: utf-8 -*-
"""强制攻击（ctrl+退格）时，攻城单位自动拆包也要显示 / 播报「正在拆包」。

背景：手动点命令菜单的「拆包」会排一条 ``unpack`` 命令，所以界面能看到
「拆包 / 正在拆包」；而强制攻击时拆包发生在 ``attack_action.py`` 的
``ensure_unpacked`` 里，命令列表里只有 attack，界面就完全不提示。
"""
from __future__ import annotations

import os
import types
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts import msgparts as mp
from soundrts.clientgameentity.base import _siege_transition_title_msg
from soundrts.clientgameentity.events import EntityViewEvents
from soundrts.clientgameentity.properties import EntityViewProperties
from soundrts.world_siege_pack import (
    MODE_PACKED,
    MODE_UNPACKED,
    ensure_unpacked,
    init_siege_pack,
    siege_mode,
)


def _siege_unit(mode=MODE_PACKED, world_time=0):
    """一个最小可用的攻城单位（属性与 Creature 默认一致即可）。"""
    world = types.SimpleNamespace(time=world_time)
    player = types.SimpleNamespace(world=world)
    u = types.SimpleNamespace(
        unpack_time=11000,
        pack_time=0,
        packable=1,
        spawn_packed=1,
        packed_mdf=2000,
        packed_rdf=8000,
        mdf=1000,
        rdf=150000,
        player=player,
        world=world,
        rdg_prep_end_time=0,
        mdg_prep_end_time=0,
        notifies=[],
        type_name="trebuchet",
        orders=[],
        action=None,
    )
    u.stop = lambda: None
    u.notify = lambda ev: u.notifies.append(ev)
    init_siege_pack(u)
    return u


class _OrdersView(EntityViewProperties):
    def __init__(self, interface, model):
        self.interface = interface
        self.model = model

    @property
    def orders(self):
        return getattr(self.model, "orders", [])


def _interface():
    return SimpleNamespace(
        zoom_mode=False,
        place=SimpleNamespace(title=["a3"]),
        dobjets={},
        memory=set(),
        scouted_squares=set(),
        player=SimpleNamespace(),
    )


def test_siege_transition_title_msg_reports_unpacking():
    """自动拆包中 → 状态标题为「正在拆包」(4944)。"""
    u = _siege_unit()
    ensure_unpacked(u)
    assert siege_mode(u) == "unpacking"
    msg = _siege_transition_title_msg(u)
    assert msg == ["4944"]


def test_siege_transition_title_msg_reports_packing():
    u = _siege_unit()
    ensure_unpacked(u)
    from soundrts.world_siege_pack import ensure_packed, tick_siege_pack

    u.world.time = 11000  # 拆包完成
    tick_siege_pack(u)
    assert siege_mode(u) == MODE_UNPACKED
    ensure_packed(u)
    assert siege_mode(u) == "packing"
    assert _siege_transition_title_msg(u) == ["4943"]


def test_siege_transition_title_msg_empty_when_stable():
    u = _siege_unit()
    assert _siege_transition_title_msg(u) == []


def test_non_siege_unit_has_no_siege_transition_msg():
    """普通单位没有 _siege_mode，不能因此报错。"""
    u = SimpleNamespace(unpack_time=0, pack_time=0, packable=0)
    assert _siege_transition_title_msg(u) == []


def test_orders_txt_shows_unpacking_during_forced_attack():
    """强制攻击：命令列表里只有 attack，但 orders_txt 必须带「正在拆包」。"""
    u = _siege_unit()

    class _AttackOrder:
        is_deferred = False
        keyword = "attack"
        type = None
        unit = None
        target = None

    u.orders = [_AttackOrder()]
    # 模拟 attack_action.py 里的自动拆包
    ensure_unpacked(u)
    assert siege_mode(u) == "unpacking"

    view = _OrdersView(_interface(), u)
    txt = view.orders_txt
    assert "4944" in txt  # 正在拆包


def test_orders_txt_no_siege_msg_when_not_transitioning():
    u = _siege_unit()
    view = _OrdersView(_interface(), u)
    assert "4944" not in view.orders_txt
    assert "4943" not in view.orders_txt


class _UnpackOrder:
    is_deferred = False
    keyword = "unpack"
    type = None
    unit = None
    target = None


class _PackOrder:
    is_deferred = False
    keyword = "pack"
    type = None
    unit = None
    target = None


def test_orders_txt_does_not_repeat_unpack_after_unpacking():
    """命令菜单点的「拆包」：只说「正在拆包」，不再追加「拆包」。"""
    u = _siege_unit()
    u.orders = [_UnpackOrder()]
    ensure_unpacked(u)
    assert siege_mode(u) == "unpacking"

    txt = _OrdersView(_interface(), u).orders_txt
    assert "4944" in txt  # 正在拆包
    assert "4939" not in txt  # 不再重复「拆包」


def test_orders_txt_does_not_repeat_pack_after_packing():
    """命令菜单点的「打包」：只说「正在打包」，不再追加「打包」。"""
    from soundrts.world_siege_pack import ensure_packed, tick_siege_pack

    u = _siege_unit()
    u.orders = [_PackOrder()]
    ensure_unpacked(u)
    u.world.time = 11000
    tick_siege_pack(u)
    assert siege_mode(u) == MODE_UNPACKED
    ensure_packed(u)
    assert siege_mode(u) == "packing"

    txt = _OrdersView(_interface(), u).orders_txt
    assert "4943" in txt  # 正在打包
    assert "4938" not in txt  # 不再重复「打包」


def test_orders_txt_keeps_other_orders_when_deduping_siege_title():
    """去重只影响 pack / unpack 订单，其他订单照常播报。"""
    u = _siege_unit()

    class _GoOrder:
        is_deferred = False
        keyword = "go"
        type = None
        unit = None
        target = None

    u.orders = [_UnpackOrder(), _GoOrder()]
    ensure_unpacked(u)

    txt = _OrdersView(_interface(), u).orders_txt
    assert "4944" in txt  # 正在拆包
    assert "4939" not in txt  # 「拆包」被去掉
    assert "100" in txt  # 「去到」保留


def test_orders_txt_keeps_pack_order_when_not_transitioning():
    """没有进行中的过渡时，「打包 / 拆包」订单标题照常播报。"""
    u = _siege_unit()
    u.orders = [_UnpackOrder()]
    # 未开始拆包（仍是 packed 稳定态）
    txt = _OrdersView(_interface(), u).orders_txt
    assert "4939" in txt  # 「拆包」
    assert "4944" not in txt


class _EventView(EntityViewEvents):
    type_name = "trebuchet"

    def __init__(self, player, local):
        self.player = player
        self.interface = SimpleNamespace(player=local)

    def launch_event_style(self, attr, alert=False, priority=0):
        pass


def test_client_does_not_announce_siege_transitions(monkeypatch):
    """打包 / 拆包开始或结束时都不主动语音提醒。

    状态只在玩家主动查询单位时播报（见 ``orders_txt``）。
    """
    import soundrts.clientgameentity.events as ev

    spoken = []
    monkeypatch.setattr(ev.voice, "info", lambda msg, **k: spoken.append(list(msg)))
    local = SimpleNamespace()
    v = _EventView(local, local)
    v.on_siege_unpacking()
    v.on_siege_packing()
    v.on_siege_unpacked()
    v.on_siege_packed()
    assert spoken == []


def test_client_does_not_announce_for_enemy_units(monkeypatch):
    """敌方攻城单位拆包不播报（只在己方界面提示）。"""
    import soundrts.clientgameentity.events as ev

    spoken = []
    monkeypatch.setattr(ev.voice, "info", lambda msg, **k: spoken.append(list(msg)))
    local = SimpleNamespace()
    enemy = SimpleNamespace()
    v = _EventView(enemy, local)
    v.on_siege_unpacking()
    assert spoken == []


def test_forced_attack_auto_unpack_notifies_and_shows_status():
    """端到端：强制攻击 → attack_action 自动拆包 → 通知 + 界面显示「正在拆包」。

    复刻 ``combat/attack_action.py`` 里的自动拆包分支：
    ``if is_packable(self) and not ensure_unpacked(self): return``
    """
    from soundrts.world_siege_pack import is_packable

    u = _siege_unit()

    class _AttackOrder:
        is_deferred = False
        keyword = "attack"
        type = None
        unit = None
        target = None

    u.orders = [_AttackOrder()]
    u.notifies.clear()

    # attack_action.py 的自动拆包分支
    if is_packable(u) and not ensure_unpacked(u):
        pass  # 自动拆包，攻击被推迟

    # 1) 世界端发出 siege_unpacking 通知
    assert "siege_unpacking" in u.notifies
    # 2) 界面端播报 / 显示「正在拆包」
    assert _siege_transition_title_msg(u) == ["4944"]
    view = _OrdersView(_interface(), u)
    assert "4944" in view.orders_txt
