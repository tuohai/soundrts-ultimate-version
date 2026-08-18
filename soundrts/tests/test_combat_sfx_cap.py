# -*- coding: utf-8 -*-
"""Combat / order / move / noise SFX caps."""

from __future__ import annotations

import time
from types import SimpleNamespace

from soundrts import parameters
from soundrts.clientgame.game_interface_base import GameInterface
from soundrts.clientgameentity.combat_sfx_cap import (
    combat_sfx_consume,
    combat_sfx_would_allow,
    event_kind,
    is_capped_combat_event,
    is_local_player_model,
    reset_combat_sfx_cap,
)


def _iface():
    iface = SimpleNamespace(
        player=object(),
        next_update=time.time() + 60,
        processed=[],
        skipped=0,
    )
    reset_combat_sfx_cap(iface)
    return iface


def test_event_kind_and_cap_set():
    assert event_kind("launch_mdg,footman,1") == "launch_mdg"
    assert is_capped_combat_event("launch_rdg")
    assert is_capped_combat_event("wounded")
    assert not is_capped_combat_event("death")


def test_global_and_place_caps(monkeypatch):
    monkeypatch.setitem(parameters.d, "combat_sfx_per_tick", 3)
    monkeypatch.setitem(parameters.d, "combat_sfx_per_place_tick", 2)
    iface = _iface()
    a = SimpleNamespace(place=object(), player=object())
    b_place = object()
    b = SimpleNamespace(place=b_place, player=object())
    c = SimpleNamespace(place=a.place, player=object())
    assert combat_sfx_consume(iface, a)
    assert combat_sfx_consume(iface, c)  # same place, place cap 2
    assert not combat_sfx_consume(iface, SimpleNamespace(place=a.place))
    assert combat_sfx_consume(iface, b)  # other place, global 3
    assert not combat_sfx_consume(iface, SimpleNamespace(place=object()))


def test_reset_allows_next_tick(monkeypatch):
    monkeypatch.setitem(parameters.d, "combat_sfx_per_tick", 1)
    monkeypatch.setitem(parameters.d, "combat_sfx_per_place_tick", 8)
    iface = _iface()
    m = SimpleNamespace(place=object())
    assert combat_sfx_consume(iface, m)
    assert not combat_sfx_would_allow(iface, m)
    reset_combat_sfx_cap(iface)
    assert combat_sfx_consume(iface, m)


def test_srv_event_drops_excess_launches(monkeypatch):
    monkeypatch.setitem(parameters.d, "combat_sfx_per_tick", 2)
    monkeypatch.setitem(parameters.d, "combat_sfx_per_place_tick", 8)
    iface = _iface()
    place = object()
    models = [SimpleNamespace(place=place, player=object()) for _ in range(5)]
    notified = []

    class _View:
        def __init__(self, interface, model):
            self.interface = interface
            self.model = model

        def notify(self, e):
            notified.append(e)

    monkeypatch.setattr(
        "soundrts.clientgame.game_interface_base.EntityView", _View
    )
    iface.srv_event = GameInterface.srv_event.__get__(iface, GameInterface)
    for i, m in enumerate(models):
        iface.srv_event(m, f"launch_mdg,footman,{i}")
    assert len(notified) == 2


def test_local_wounded_still_delivered_when_capped(monkeypatch):
    monkeypatch.setitem(parameters.d, "combat_sfx_per_tick", 1)
    monkeypatch.setitem(parameters.d, "combat_sfx_per_place_tick", 1)
    iface = _iface()
    local = SimpleNamespace(place=object(), player=iface.player)
    enemy = SimpleNamespace(place=local.place, player=object())
    notified = []

    class _View:
        def __init__(self, interface, model):
            self.model = model

        def notify(self, e):
            notified.append((self.model, e))

    monkeypatch.setattr(
        "soundrts.clientgame.game_interface_base.EntityView", _View
    )
    iface.srv_event = GameInterface.srv_event.__get__(iface, GameInterface)
    iface.srv_event(enemy, "launch_mdg,footman,1")
    iface.srv_event(local, "wounded,footman,1,0,0,0")
    assert len(notified) == 2
    assert notified[1][0] is local
    assert is_local_player_model(iface, local)


def test_order_ok_capped_per_tick(monkeypatch):
    monkeypatch.setitem(parameters.d, "order_sfx_per_tick", 2)
    iface = _iface()
    notified = []

    class _View:
        def __init__(self, interface, model):
            self.model = model

        def notify(self, e):
            notified.append(e)

    monkeypatch.setattr(
        "soundrts.clientgame.game_interface_base.EntityView", _View
    )
    iface.srv_event = GameInterface.srv_event.__get__(iface, GameInterface)
    local = iface.player
    for _ in range(8):
        iface.srv_event(
            SimpleNamespace(place=object(), player=local),
            "order_ok",
        )
    assert notified == ["order_ok", "order_ok"]
    iface.srv_event(
        SimpleNamespace(place=object(), player=object()),
        "order_ok",
    )
    assert notified == ["order_ok", "order_ok"]


def test_move_wave_caps(monkeypatch):
    from soundrts.clientgameentity.combat_sfx_cap import (
        move_sfx_consume,
        reset_animate_sfx_cap,
    )

    monkeypatch.setitem(parameters.d, "move_sfx_per_wave", 2)
    monkeypatch.setitem(parameters.d, "move_sfx_per_place_wave", 2)
    iface = _iface()
    reset_animate_sfx_cap(iface)
    a = SimpleNamespace(place=object())
    b = SimpleNamespace(place=a.place)
    c = SimpleNamespace(place=object())
    assert move_sfx_consume(iface, a)
    assert move_sfx_consume(iface, b)
    assert not move_sfx_consume(iface, c)
    reset_animate_sfx_cap(iface)
    assert move_sfx_consume(iface, c)


def test_noise_capped_per_type_not_globally(monkeypatch):
    from soundrts.clientgameentity.combat_sfx_cap import (
        noise_sfx_consume,
        reset_animate_sfx_cap,
    )

    monkeypatch.setitem(parameters.d, "noise_sfx_per_type", 3)
    iface = _iface()
    reset_animate_sfx_cap(iface)
    peasants = [SimpleNamespace(type_name="peasant") for _ in range(8)]
    halls = [SimpleNamespace(type_name="townhall") for _ in range(3)]
    assert sum(noise_sfx_consume(iface, u) for u in peasants) == 3
    assert all(noise_sfx_consume(iface, u) for u in halls)
    site = SimpleNamespace(
        type_name="buildingsite",
        type=SimpleNamespace(type_name="barracks"),
    )
    assert noise_sfx_consume(iface, site)
    reset_animate_sfx_cap(iface)
    assert noise_sfx_consume(iface, peasants[0])
    reset_animate_sfx_cap(iface)
    kinds = [SimpleNamespace(type_name=f"u{i}") for i in range(20)]
    assert sum(noise_sfx_consume(iface, u) for u in kinds) == 20
