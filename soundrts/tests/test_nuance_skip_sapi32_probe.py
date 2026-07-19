"""Nuance voices must not probe the 32-bit SAPI helper on Alt / stop."""
from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SOUNDRTS_UI_BACKEND", "pygame")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def test_needs_sapi32_false_for_nuance_without_helper():
    from soundrts.lib import game_tts, sapi32_tts

    calls = []
    sapi32_tts.list_voices = lambda: calls.append("list_voices") or []  # type: ignore
    sapi32_tts.list_wow6432_token_names = (  # type: ignore
        lambda: calls.append("wow") or []
    )
    sapi32_tts.available = lambda: calls.append("available") or True  # type: ignore

    game_tts._needs_sapi32_cache.clear()
    assert game_tts.needs_sapi32("nuance:Ting-Ting") is False
    assert calls == []


def test_needs_sapi32_nuance_is_fast():
    from soundrts.lib import game_tts

    game_tts._needs_sapi32_cache.clear()
    t0 = time.perf_counter()
    assert game_tts.needs_sapi32("nuance:Ting-Ting") is False
    assert (time.perf_counter() - t0) < 0.05
