"""secondary_voice_enabled: dual voice vs primary-only (E-style)."""
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
        import soundrts.config as config
        import soundrts.lib.game_tts as game_tts
        import soundrts.lib.voice as voice_mod
        from soundrts.lib import voice_libs
        from soundrts.lib.message import Message
finally:
    sys.argv = _saved_argv


def test_passive_channel_uses_secondary_when_enabled():
    old = getattr(config, "secondary_voice_enabled", 1)
    try:
        config.secondary_voice_enabled = 1
        game_tts.set_in_match(True)
        assert game_tts.passive_channel() == game_tts.SECONDARY
        game_tts.set_in_match(False)
        assert game_tts.passive_channel() == game_tts.PRIMARY
    finally:
        game_tts.set_in_match(False)
        config.secondary_voice_enabled = old


def test_passive_channel_primary_when_secondary_disabled():
    old = getattr(config, "secondary_voice_enabled", 1)
    try:
        config.secondary_voice_enabled = 0
        game_tts.set_in_match(True)
        assert game_tts.passive_channel() == game_tts.PRIMARY
        assert game_tts.secondary_voice_enabled() is False
    finally:
        game_tts.set_in_match(False)
        config.secondary_voice_enabled = old


def test_item_preempts_when_secondary_disabled():
    """With secondary off, ops must not use parallel_primary (E-style)."""
    old = getattr(config, "secondary_voice_enabled", 1)
    v = voice_mod._Voice()
    v.lock = mock.MagicMock()
    v.lock.__enter__ = mock.MagicMock(return_value=None)
    v.lock.__exit__ = mock.MagicMock(return_value=False)

    play_kwargs = []

    class FakeChannel:
        _tts_channel = game_tts.SECONDARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            play_kwargs.append(
                {
                    "tts_channel": tts_channel,
                    "parallel_primary": parallel_primary,
                }
            )

        def stop(self, *, tts_channel=None):
            pass

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
    try:
        config.secondary_voice_enabled = 0
        game_tts.set_in_match(True)
        v.item(["peasant"])
    finally:
        game_tts.set_in_match(False)
        config.secondary_voice_enabled = old

    assert play_kwargs
    assert play_kwargs[0]["tts_channel"] == game_tts.PRIMARY
    assert play_kwargs[0]["parallel_primary"] is False
    assert v.active is False


def test_menu_f3_toggles_secondary_voice():
    text = Path("soundrts/clientmenu.py").read_text(encoding="utf-8")
    assert "K_F3" in text
    assert "toggle_secondary_voice_enabled" in text
    # Must not be wired into in-match bindings (F3 stays gear/time there).
    for name in ("global_bindings.txt", "legacy_bindings.txt"):
        bindings = Path("res/ui") / name
        src = bindings.read_text(encoding="utf-8")
        assert "toggle_secondary_voice" not in src


def test_toggle_secondary_voice_enabled_flips_config(monkeypatch):
    old = getattr(config, "secondary_voice_enabled", 1)
    saves = []
    monkeypatch.setattr(config, "save", lambda: saves.append(1))
    try:
        config.secondary_voice_enabled = 1
        with mock.patch("soundrts.clientmedia.voice") as v:
            v.channel.stop = mock.MagicMock()
            v.item = mock.MagicMock()
            enabled = voice_libs.toggle_secondary_voice_enabled(announce=True)
            assert enabled is False
            assert config.secondary_voice_enabled == 0
            enabled = voice_libs.toggle_secondary_voice_enabled(announce=False)
            assert enabled is True
            assert config.secondary_voice_enabled == 1
        assert saves
    finally:
        config.secondary_voice_enabled = old
