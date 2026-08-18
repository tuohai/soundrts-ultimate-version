# -*- coding: utf-8 -*-
"""Combat SFX stay off the decode hot path; misses retry after background load."""

from __future__ import annotations

import time
from types import SimpleNamespace

from soundrts.clientgameentity import sfx_deferred as sd


def test_prefetch_queues_allow_load_false(monkeypatch):
    calls = []

    monkeypatch.setattr(
        sd.style,
        "get",
        lambda type_name, attr, warn_if_not_found=True: ["knight_death"]
        if attr == "death"
        else [],
    )
    monkeypatch.setattr(
        sd.sounds,
        "get_sound",
        lambda name, allow_load=True, warn=True: calls.append((name, allow_load)) or None,
    )
    iface = SimpleNamespace()
    sd.prefetch_type_combat_sfx(iface, "knight")
    sd.prefetch_type_combat_sfx(iface, "knight")
    assert ("knight_death", False) in calls
    assert calls.count(("knight_death", False)) == 1


def test_pending_sfx_plays_once_loaded(monkeypatch):
    loaded = {}
    played = []

    monkeypatch.setattr(
        sd.sounds,
        "get_sound",
        lambda name, allow_load=True, warn=True: loaded.get(name),
    )
    monkeypatch.setattr(
        sd.psounds,
        "play",
        lambda s, volume, x, y, priority, limit, ambient: played.append(s),
    )
    iface = SimpleNamespace()
    sd.queue_pending_sfx(iface, "hit_a", volume=1, x=1, y=2, priority=0)
    assert sd.flush_pending_sfx(iface) == 0
    loaded["hit_a"] = object()
    assert sd.flush_pending_sfx(iface) == 1
    assert played
    assert sd.flush_pending_sfx(iface) == 0


def test_pending_sfx_expires(monkeypatch):
    monkeypatch.setattr(
        sd.sounds,
        "get_sound",
        lambda name, allow_load=True, warn=True: None,
    )
    iface = SimpleNamespace()
    sd.queue_pending_sfx(iface, "hit_a")
    iface._pending_sfx[0]["deadline"] = time.time() - 1
    assert sd.flush_pending_sfx(iface) == 0
    assert iface._pending_sfx == []
