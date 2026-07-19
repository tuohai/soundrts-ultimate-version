"""Left Alt filters primary; Right Alt filters secondary."""
from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import soundrts.lib.game_tts as game_tts
        import soundrts.lib.voice as voice_mod
        from soundrts.lib.message import Message
finally:
    sys.argv = _saved_argv


def test_bindings_split_alt_history_stop():
    for name in ("legacy_bindings.txt", "global_bindings.txt"):
        src = (Path("res/ui") / name).read_text(encoding="utf-8")
        assert "LALT: history_stop_primary" in src
        assert "RALT: history_stop_secondary" in src
        assert "LSHIFT: history_stop" not in src
        assert "RSHIFT: history_stop" not in src


def test_item_parallel_does_not_stop_secondary():
    v = voice_mod._Voice()
    v.lock = mock.MagicMock()
    v.lock.__enter__ = mock.MagicMock(return_value=None)
    v.lock.__exit__ = mock.MagicMock(return_value=False)

    stop_calls = []
    play_kwargs = []

    class FakeChannel:
        _tts_channel = game_tts.SECONDARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            play_kwargs.append(
                {
                    "parts": list(msg.list_of_sound_numbers),
                    "tts_channel": tts_channel,
                    "parallel_primary": parallel_primary,
                }
            )

        def stop(self, *, tts_channel=None):
            stop_calls.append(tts_channel)

        def update(self):
            pass

        def get_busy(self):
            return True

        def is_almost_done(self):
            return False

    v.channel = FakeChannel()
    alert = Message(["knight", "enemy", "a1"], said=False)
    v.msgs = [alert]
    v.current = 0
    v.active = True
    game_tts.set_in_match(True)
    try:
        v.item(["peasant"])
    finally:
        game_tts.set_in_match(False)

    assert alert.said is False  # secondary not abandoned
    assert v.active is True
    assert stop_calls == []
    assert play_kwargs and play_kwargs[0]["parallel_primary"] is True
    assert play_kwargs[0]["tts_channel"] == game_tts.PRIMARY


def test_voicechannel_play_parallel_primary_source():
    text = Path("soundrts/lib/voicechannel.py").read_text(encoding="utf-8")
    assert "parallel_primary" in text
    assert "_play_primary_parallel" in text


def test_say_now_secondary_uses_right_alt():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def _say_now(", 1)[1].split("\n    def ", 1)[0]
    assert "_right_alt_hit" in block
    assert "_left_alt_hit" in block
    assert "SECONDARY" in block


def test_say_next_right_alt_skips_secondary_queue_line():
    v = voice_mod._Voice()
    stop_calls = []

    class FakeChannel:
        _tts_channel = game_tts.SECONDARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            self._tts_channel = tts_channel

        def stop(self, *, tts_channel=None):
            stop_calls.append(tts_channel)

        def update(self):
            pass

        def get_busy(self):
            return False

    v.channel = FakeChannel()
    alert = Message(
        ["knight", "enemy"], said=False, tts_channel=game_tts.SECONDARY
    )
    done = Message(["house"], said=False, tts_channel=game_tts.PRIMARY)
    v.msgs = [alert, done]
    v.current = 0
    v.active = True
    game_tts.set_in_match(True)
    try:
        v.say_next(tts_channel=game_tts.SECONDARY)
    finally:
        game_tts.set_in_match(False)

    assert alert.said is True
    assert game_tts.SECONDARY in stop_calls


def test_say_next_left_alt_does_not_skip_secondary_queue_line():
    v = voice_mod._Voice()
    stop_calls = []

    class FakeChannel:
        _tts_channel = game_tts.SECONDARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            pass

        def stop(self, *, tts_channel=None):
            stop_calls.append(tts_channel)

        def update(self):
            pass

        def get_busy(self):
            return True

    v.channel = FakeChannel()
    alert = Message(
        ["knight", "enemy"], said=False, tts_channel=game_tts.SECONDARY
    )
    v.msgs = [alert]
    v.current = 0
    v.active = True
    game_tts.set_in_match(True)
    try:
        v.say_next(tts_channel=game_tts.PRIMARY)
    finally:
        game_tts.set_in_match(False)

    assert alert.said is False
    assert v.current == 0
    assert stop_calls == [game_tts.PRIMARY]


def test_say_next_right_alt_skips_primary_when_secondary_disabled():
    import soundrts.config as config

    v = voice_mod._Voice()
    stop_calls = []

    class FakeChannel:
        _tts_channel = game_tts.PRIMARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            self._tts_channel = tts_channel

        def stop(self, *, tts_channel=None):
            stop_calls.append(tts_channel)

        def update(self):
            pass

        def get_busy(self):
            return False

    v.channel = FakeChannel()
    line = Message(["house", "complete"], said=False, tts_channel=game_tts.PRIMARY)
    v.msgs = [line]
    v.current = 0
    v.active = True
    old = getattr(config, "secondary_voice_enabled", 1)
    try:
        config.secondary_voice_enabled = 0
        game_tts.set_in_match(True)
        v.say_next(tts_channel=game_tts.SECONDARY)
    finally:
        game_tts.set_in_match(False)
        config.secondary_voice_enabled = old

    assert line.said is True
    assert game_tts.PRIMARY in stop_calls
