"""Defeat must exit to the statistics screen immediately.

Regression: on defeat the client used to drain the whole passive voice
backlog (``voice.flush()``) before showing the statistics, so the player
waited minutes while every queued combat alert was recited.
"""
from __future__ import annotations

import os
import sys
import threading
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from soundrts.lib.voice import _Voice
        from soundrts.lib.message import Message
finally:
    sys.argv = _saved_argv


class _FakeChannel:
    def __init__(self):
        self.stopped = []

    def stop(self, *, tts_channel=None):
        self.stopped.append(tts_channel)

    def get_busy(self):
        return False

    def update(self):
        pass

    def is_almost_done(self):
        return True


def _voice_with_backlog(count=30):
    v = _Voice.__new__(_Voice)
    v.lock = threading.Lock()
    v.channel = _FakeChannel()
    v.msgs = []
    v.active = False
    v.history = False
    v.muted = False
    v.speech_enabled = True
    v.current = 0
    for _ in range(count):
        v.msgs.append(Message([1], said=False))
    return v


def test_discard_pending_drops_the_backlog_without_blocking():
    v = _voice_with_backlog(30)
    v.discard_pending()
    assert all(m.said for m in v.msgs)
    assert v.current == len(v.msgs)
    assert v.active is False


def test_discard_pending_only_silences_the_secondary_library():
    v = _voice_with_backlog(5)
    v.discard_pending()
    # A full stop (None) would also silence the primary library, which
    # carries the post-match statistics.
    assert v.channel.stopped == ["secondary"]


def test_discard_pending_does_not_speak_anything():
    """discard_pending() must never block waiting for the backlog."""
    v = _voice_with_backlog(30)
    # A wrong implementation would call flush() -> update() -> channel.play().
    v.discard_pending()
    assert v.channel.get_busy() is False
