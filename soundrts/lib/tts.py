"""Screen-reader TTS via accessible_output2 (争渡 / NVDA / JAWS / …).

When a dedicated screen reader is active, it takes over the game's
**primary** voice duties (menus, player ops, out-of-match alerts) so
Nuance/SAPI primary does not fight the reader. In-match passive lines
still use ``game_tts`` secondary.
"""
from __future__ import annotations

import threading
import time
from queue import Queue
from typing import Callable, List, Optional, Tuple

import accessible_output2.outputs.auto

from .log import exception


# Backends that are bare system TTS — not a dedicated screen reader.
_SYSTEM_TTS_NAMES = frozenset({"sapi5", "sapi", "speech dispatcher", "e_speak"})


class _TTS:

    _end_time = None

    def __init__(self, wait_delay_per_character):
        self.o = accessible_output2.outputs.auto.Auto()
        self._wait_delay_per_character = wait_delay_per_character

    def IsSpeaking(self):
        if self._end_time is None:
            return False
        return self._end_time > time.time()

    def Speak(self, text, interrupt=True):
        self.o.output(text, interrupt=interrupt)
        delay = max(0.05, float(self._wait_delay_per_character or 0.05))
        duration = len(text) * delay
        nb_digits = sum(c.isdigit() for c in text)
        try:
            from soundrts import parameters

            digit_bonus = parameters.d.get("tts_digit_coefficient", 1) - 1
            duration += nb_digits * digit_bonus * delay
        except Exception:
            pass
        duration = max(0.5, duration)
        now = time.time()
        if interrupt or self._end_time is None or self._end_time < now:
            self._end_time = now + duration
        else:
            self._end_time += duration

    def Stop(self):
        self.o.output("", interrupt=True)
        self._end_time = None


_tts = None
_is_speaking = False
_pending_speak = 0
_sr_cache: Optional[bool] = None
_sr_cache_at = 0.0
_SR_CACHE_TTL = 2.0

_queue: Queue[Tuple[Callable, List]] = Queue()


def using_screen_reader() -> bool:
    """True when AO2 will talk through a dedicated screen reader (not bare SAPI)."""
    global _sr_cache, _sr_cache_at
    now = time.time()
    if _sr_cache is not None and (now - _sr_cache_at) < _SR_CACHE_TTL:
        return _sr_cache
    active = False
    try:
        if _tts is not None and getattr(_tts, "o", None) is not None:
            out = _tts.o.get_first_available_output()
            if out is not None:
                name = (getattr(out, "name", None) or type(out).__name__ or "").lower()
                active = bool(name) and name not in _SYSTEM_TTS_NAMES and "sapi" not in name
    except Exception:
        active = False
    _sr_cache = active
    _sr_cache_at = now
    return active


def is_speaking():
    if _pending_speak > 0:
        return True
    if _is_speaking:
        return True
    try:
        if _tts is not None and _tts.IsSpeaking():
            return True
    except Exception:
        pass
    return False


def _speak(text, interrupt=True):
    global _pending_speak
    try:
        with _lock:
            try:
                _tts.Speak(text, interrupt=interrupt)
            except Exception:
                exception("error during _tts.Speak('%s')", text)
    finally:
        with _lock:
            _pending_speak = max(0, _pending_speak - 1)


def speak(text: str, interrupt: bool = True):
    global _is_speaking, _pending_speak
    assert isinstance(text, str)
    with _lock:
        _pending_speak += 1
        _is_speaking = True
    _queue.put((_speak, [text, interrupt]))


def _stop():
    global _is_speaking, _pending_speak
    with _lock:
        try:
            if _tts is not None:
                _tts.Stop()
        except Exception:
            pass
        _is_speaking = False
        _pending_speak = 0


def stop():
    _queue.put((_stop, []))


def _init_com_for_this_thread():
    try:
        import pythoncom
    except ImportError:
        pass
    else:
        pythoncom.CoInitialize()


def _loop():
    global _pending_speak
    _init_com_for_this_thread()
    while True:
        cmd, args = _queue.get()
        if not _queue.empty() and cmd is _speak and (not args or args[-1] is True):
            with _lock:
                _pending_speak = max(0, _pending_speak - 1)
            continue
        try:
            cmd(*args)
        except Exception:
            exception("")


def _loop2():
    global _is_speaking
    while True:
        time.sleep(0.1)
        with _lock:
            if _is_speaking and not _tts.IsSpeaking() and _pending_speak <= 0:
                _is_speaking = False


def init(wait_delay_per_character):
    global _tts, _lock, _pending_speak, _is_speaking, _sr_cache, _sr_cache_at
    _lock = threading.Lock()
    _tts = _TTS(wait_delay_per_character)
    _pending_speak = 0
    _is_speaking = False
    _sr_cache = None
    _sr_cache_at = 0.0
    t = threading.Thread(target=_loop)
    t.daemon = True
    t.start()
    t = threading.Thread(target=_loop2)
    t.daemon = True
    t.start()
