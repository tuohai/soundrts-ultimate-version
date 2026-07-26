"""模拟「选项 → 语音库设置」↑↓，分段计时找真实卡顿根因。

必须真实走到 Menu._say_choice / draw_menu / translate / TTS 预备路径，
禁止先验下结论。跑 ``pytest -s`` 看打印。
"""
from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SOUNDRTS_UI_BACKEND", "pygame")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def _boot_display_and_mixer():
    import pygame

    from soundrts.lib import screen as screen_mod

    if not pygame.get_init():
        pygame.init()
    if not pygame.mixer.get_init():
        try:
            pygame.mixer.init()
        except Exception:
            pass
    screen_mod._screen = pygame.display.set_mode((960, 640))
    return screen_mod._screen


def _voice_libs_choices():
    from soundrts import msgparts as mp

    return [
        (mp.VOICE_LIB_HELP, None),
        (mp.VOICE_LIB_SECONDARY_TOGGLE, None, mp.VOICE_LIB_SECONDARY_ON),
        (mp.VOICE_LIB_PRIMARY, None),
        (mp.VOICE_LIB_SECONDARY, None),
        (mp.OPEN_VOICES_FOLDER, None),
        (mp.BACK, None),
    ]


def test_simulate_voice_libs_menu_arrows_find_bottleneck(monkeypatch, capsys):
    """连按↓/↑扫完整菜单，统计各分段与昂贵 API 次数。"""
    import pygame

    from soundrts import clientmenu as cm
    from soundrts import msgparts as mp
    from soundrts.lib import game_tts, pygame_ui, voice_packs
    from soundrts.lib.message import Message, clear_collapse_cache
    from soundrts.lib.sound_cache import sounds
    from soundrts.lib.voice import voice

    surf = _boot_display_and_mixer()
    assert surf is not None
    assert pygame_ui.get_screen() is not None

    # Count expensive calls; keep speak from blocking on real COM if possible,
    # but still run resolve_sapi path used by speak().
    counters = {
        "global_lookup": 0,
        "scan_packs": 0,
        "font_size": 0,
        "list_sapi": 0,
        "speak": 0,
    }

    real_global = sounds._global_lookup_text
    real_scan = voice_packs.scan_packs
    real_list_sapi = game_tts.list_sapi_voices
    real_speak = game_tts.speak

    def _g(key):
        counters["global_lookup"] += 1
        return real_global(key)

    def _s():
        counters["scan_packs"] += 1
        return real_scan()

    def _ls():
        counters["list_sapi"] += 1
        return real_list_sapi()

    def _spk(*a, **k):
        counters["speak"] += 1
        # Reproduce prep cost that speak pays before audio (resolve_sapi).
        voice_packs.resolve_sapi(voice_libs_voice())
        return None

    def voice_libs_voice():
        from soundrts.lib import voice_libs

        return voice_libs.get_voice(voice_libs.PRIMARY)

    monkeypatch.setattr(sounds, "_global_lookup_text", _g)
    monkeypatch.setattr(voice_packs, "scan_packs", _s)
    monkeypatch.setattr(game_tts, "list_sapi_voices", _ls)
    monkeypatch.setattr(game_tts, "speak", _spk)
    monkeypatch.setattr(game_tts, "is_speaking", lambda *_a, **_k: False)
    monkeypatch.setattr(game_tts, "stop", lambda *a, **k: None)

    # Patch font.size used inside draw_menu truncate loop.
    real_pick = pygame_ui._pick_font

    def counting_pick(size, bold=False):
        font = real_pick(size, bold)

        class _FontProxy:
            def __init__(self, f):
                self._f = f

            def size(self, text):
                counters["font_size"] += 1
                return self._f.size(text)

            def render(self, *a, **k):
                return self._f.render(*a, **k)

            def get_height(self):
                return self._f.get_height()

            def __getattr__(self, name):
                return getattr(self._f, name)

        return _FontProxy(font)

    monkeypatch.setattr(pygame_ui, "_pick_font", counting_pick)

    # Real channel.play would try TTS; route voice.item through Message+speak stub.
    def _item(msg, *a, **k):
        Message(list(msg)).translate_and_collapse()
        game_tts.speak("x", interrupt=True, channel="primary")

    monkeypatch.setattr(voice, "item", _item)

    menu = cm.Menu(
        title=["语音库设置"],
        choices=_voice_libs_choices(),
        menu_type="submenu",
    )
    # Use the REAL Menu._say_choice (not a reimplementation).
    timings = []  # (label_prefix, total_ms, breakdown)

    def _one(label: str):
        clear_collapse_cache()
        # reset per-arrow counters snapshot
        before = dict(counters)
        t0 = time.perf_counter()
        # select_sfx may load ogg; tolerate mixer quirks
        try:
            menu._say_choice()
        except pygame.error:
            # fallback without SFX
            choice = menu.choices[menu.choice_index]
            msg = list(choice[0])
            if len(choice) > 2:
                msg += list(mp.COMMA) + list(choice[2])
            voice.item(msg)
            menu._draw_menu()
        total_ms = (time.perf_counter() - t0) * 1000
        delta = {k: counters[k] - before[k] for k in counters}
        timings.append((label, total_ms, delta))

    menu.choice_index = 0
    _one("land#0-help")
    for i in range(1, len(menu.choices)):
        menu.choice_index = i
        prefix = pygame_ui.msgparts_to_display_text(menu.choices[i][0])[:16]
        _one(f"down#{i}:{prefix}")
    for i in range(len(menu.choices) - 2, -1, -1):
        menu.choice_index = i
        prefix = pygame_ui.msgparts_to_display_text(menu.choices[i][0])[:16]
        _one(f"up#{i}:{prefix}")

    lines = ["=== simulate voice_libs_menu arrows ==="]
    for label, ms, d in timings:
        lines.append(
            f"{label}: {ms:.1f}ms  "
            f"font_size+{d['font_size']} global+{d['global_lookup']} "
            f"scan_packs+{d['scan_packs']} speak+{d['speak']} list_sapi+{d['list_sapi']}"
        )
    totals = {k: counters[k] for k in counters}
    lines.append(f"TOTALS: {totals}")
    worst = max(timings, key=lambda x: x[1])
    lines.append(f"WORST_ARROW: {worst[0]} {worst[1]:.1f}ms delta={worst[2]}")

    # Attribute: which counter correlates with worst arrows?
    attr = []
    for key in ("font_size", "global_lookup", "scan_packs", "speak", "list_sapi"):
        # average counter delta on arrows slower than 50ms vs faster
        slow = [d[key] for _, ms, d in timings if ms >= 50]
        fast = [d[key] for _, ms, d in timings if ms < 50]
        if slow:
            attr.append(
                f"{key}: slow_avg={sum(slow)/len(slow):.1f} "
                f"fast_avg={(sum(fast)/len(fast) if fast else 0):.1f}"
            )
    lines.append("CORR: " + (" | ".join(attr) if attr else "no arrow >=50ms"))

    report = "\n".join(lines)
    print(report)
    with capsys.disabled():
        print(report)

    # Persist for humans; also assert we actually exercised draw/speak paths.
    assert any(d["font_size"] > 0 or d["speak"] > 0 for _, _, d in timings)
    assert worst[1] >= 0


def test_draw_menu_font_size_calls_per_redraw(monkeypatch, capsys):
    """只测 draw_menu：帮助长文在不缓存截断结果时，每次重绘 font.size 次数。"""
    from soundrts.lib import pygame_ui

    _boot_display_and_mixer()
    choices = _voice_libs_choices()
    pygame_ui._menu_label_cache_key = None

    calls = {"n": 0}
    real_pick = pygame_ui._pick_font

    def counting_pick(size, bold=False):
        font = real_pick(size, bold)

        class _P:
            def __init__(self, f):
                self._f = f

            def size(self, text):
                calls["n"] += 1
                return self._f.size(text)

            def render(self, *a, **k):
                return self._f.render(*a, **k)

            def get_height(self):
                return self._f.get_height()

            def __getattr__(self, name):
                return getattr(self._f, name)

        return _P(font)

    monkeypatch.setattr(pygame_ui, "_pick_font", counting_pick)

    calls["n"] = 0
    t0 = time.perf_counter()
    pygame_ui.draw_menu(["语音库设置"], choices, 0, None)
    ms0 = (time.perf_counter() - t0) * 1000
    n0 = calls["n"]

    calls["n"] = 0
    t0 = time.perf_counter()
    pygame_ui.draw_menu(["语音库设置"], choices, 1, None)  # leave help visible
    ms1 = (time.perf_counter() - t0) * 1000
    n1 = calls["n"]

    short = [(["短"], None)] + choices[1:]
    pygame_ui._menu_label_cache_key = None
    calls["n"] = 0
    t0 = time.perf_counter()
    pygame_ui.draw_menu(["语音库设置"], short, 0, None)
    ms_short = (time.perf_counter() - t0) * 1000
    n_short = calls["n"]

    report = (
        f"draw help-selected: {ms0:.1f}ms font_size={n0}\n"
        f"draw toggle-selected (help still visible): {ms1:.1f}ms font_size={n1}\n"
        f"draw short-first: {ms_short:.1f}ms font_size={n_short}"
    )
    print(report)
    with capsys.disabled():
        print("=== draw_menu font.size ===")
        print(report)

    # After fix: help-visible redraw must not burn hundreds of font.size calls.
    assert n0 < 40, (
        f"draw_menu still does {n0} font.size calls with help visible "
        f"({ms0:.1f}ms). Long VOICE_LIB_HELP must use O(log n) fit, not O(n)."
    )
    assert ms0 < 80, f"draw_menu with help still slow: {ms0:.1f}ms"
    print(f"HELP_FONT_SIZE_CALLS_PER_DRAW={n0}")
