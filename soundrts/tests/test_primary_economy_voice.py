"""Economy / production feedback must use the primary voice library."""
from __future__ import annotations

from pathlib import Path
from unittest import mock

import soundrts.config as config
import soundrts.lib.game_tts as game_tts
import soundrts.lib.voice as voice_mod
from soundrts.lib.message import Message

_ROOT = Path(__file__).resolve().parents[1]


def test_message_stores_tts_channel():
    msg = Message(["x"], tts_channel=game_tts.PRIMARY)
    assert msg.tts_channel == game_tts.PRIMARY


def test_voice_update_honors_message_tts_channel():
    v = voice_mod._Voice()
    v.lock = mock.MagicMock()
    play_kwargs = []

    class FakeChannel:
        _tts_channel = game_tts.PRIMARY

        def play(self, msg, *, tts_channel=None, parallel_primary=False):
            play_kwargs.append({"tts_channel": tts_channel, "msg": msg})

        def stop(self, *, tts_channel=None):
            pass

        def update(self):
            pass

        def get_busy(self):
            return False

    v.channel = FakeChannel()
    v.msgs = [Message(["house", "complete"], said=False, tts_channel=game_tts.PRIMARY)]
    v.current = 0
    v.active = False
    v.history = False
    old = getattr(config, "secondary_voice_enabled", 1)
    try:
        config.secondary_voice_enabled = 1
        game_tts.set_in_match(True)
        v.update()
    finally:
        game_tts.set_in_match(False)
        config.secondary_voice_enabled = old

    assert play_kwargs
    assert play_kwargs[0]["tts_channel"] == game_tts.PRIMARY


def test_complete_and_research_route_primary():
    events = (_ROOT / "clientgameentity" / "events.py").read_text(encoding="utf-8")
    assert "_PRIMARY = dict(tts_channel=game_tts.PRIMARY)" in events
    assert 'voice.info(self.get_style("research_complete_msg"), **_PRIMARY)' in events
    assert 'voice.info(self.get_style("upgrade_complete_msg"), **_PRIMARY)' in events
    complete = events.split("def on_complete", 1)[1].split("def on_resource_complete", 1)[0]
    assert "**_PRIMARY" in complete
    added = events.split("def on_added", 1)[1].split("def on_placed", 1)[0]
    assert "**_PRIMARY" in added


def test_resource_and_menu_alerts_route_primary():
    resources = (_ROOT / "clientgame" / "game_resources.py").read_text(encoding="utf-8")
    block = resources.split("def send_msg_if_playing", 1)[1].split("\ndef ", 1)[0]
    assert "tts_channel=game_tts.PRIMARY" in block

    save = resources.split("def gm_save", 1)[1].split("\ndef ", 1)[0]
    assert 'voice.info(mp.OK, tts_channel="primary")' in save

    unit = (_ROOT / "clientgame" / "game_unit_control.py").read_text(encoding="utf-8")
    menu = unit.split("def _send_menu_alert_if_needed", 1)[1].split("\ndef ", 1)[0]
    assert "tts_channel=game_tts.PRIMARY" in menu
