"""Queued passive lines that have not started yet still play after ops."""
from __future__ import annotations

import os
import sys
import warnings
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import soundrts.lib.voice as voice_mod
        from soundrts.lib.message import Message
finally:
    sys.argv = _saved_argv


def test_item_does_not_abandon_not_yet_started_queue():
    v = voice_mod._Voice()
    v.lock = mock.MagicMock()
    v.lock.__enter__ = mock.MagicMock(return_value=None)
    v.lock.__exit__ = mock.MagicMock(return_value=False)

    play_calls = []

    class FakeChannel:
        _tts_channel = "primary"

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            play_calls.append((list(msg.list_of_sound_numbers), tts_channel))

        def stop(self, *, tts_channel=None):
            pass

        def update(self):
            pass

        def get_busy(self):
            return False

        def is_almost_done(self):
            return False

    v.channel = FakeChannel()
    pending = Message(["scout", "enemy", "b2"], said=False)
    v.msgs = [pending]
    v.current = 0
    v.active = False  # queued but not started
    v.history = False

    v.item(["peasant"])

    assert pending.said is False
    play_calls.clear()
    v.update()
    assert len(play_calls) == 1
    assert play_calls[0][0] == ["scout", "enemy", "b2"]
