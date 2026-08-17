# -*- coding: utf-8 -*-
"""Budgeted entity animation must not block the client loop for a full wave."""

from __future__ import annotations

import time
from types import SimpleNamespace

from soundrts import parameters
from soundrts.clientgame import game_display as gd


class _SlowView:
    def __init__(self, delay_s: float, place=None):
        self.delay_s = delay_s
        self.place = place
        self.is_inside = False
        self.calls = 0

    def animate(self):
        self.calls += 1
        time.sleep(self.delay_s)


def test_animate_objects_yields_within_budget(monkeypatch):
    monkeypatch.setitem(parameters.d, "animation_delay", 0.0)
    monkeypatch.setitem(parameters.d, "animation_budget_ms", 5)
    monkeypatch.setitem(parameters.d, "render_nearby_objects", 0)
    def _noop_obs(iface, update_sounds=True):
        return None

    monkeypatch.setattr(
        "soundrts.clientgame.game_navigation.set_obs_pos",
        _noop_obs,
    )
    monkeypatch.setattr(
        "soundrts.clientgameentity.formation_sound_queue.flush_formation_sound_queue",
        lambda iface: None,
    )
    monkeypatch.setattr(gd, "_animate_terrain", lambda iface: None)
    monkeypatch.setattr(gd, "_check_battle_status", lambda iface: None)
    monkeypatch.setattr(gd, "_check_rpg_unit_place_change", lambda iface: None)
    monkeypatch.setattr(
        "soundrts.clientgame.build_field_voice.animate_build_field_noises",
        lambda iface: None,
    )

    place = object()
    views = [_SlowView(0.01, place=place) for _ in range(20)]
    iface = SimpleNamespace(
        dobjets={i: v for i, v in enumerate(views)},
        place=place,
        previous_animation=0,
        _animate_resume=None,
        group=[],
    )

    # First call is setup_obs-only and must return quickly.
    t0 = time.perf_counter()
    gd._animate_objects(iface)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert elapsed_ms < 40.0
    assert iface._animate_resume is not None
    assert iface._animate_resume.get("phase") == "setup_cand"

    # Drain the wave across further frames (cand + objs + post steps).
    for _ in range(80):
        gd._animate_objects(iface)
        if iface._animate_resume is None:
            break
    assert iface._animate_resume is None
    assert sum(v.calls for v in views) == len(views)
