"""Hybrid speech: VoiceChannel for in-match passive, SR for primary under wx."""

from pathlib import Path


def test_speech_enabled_under_wx():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def _speech_enabled", 1)[1].split("\n    def ", 1)[0]
    # Must not disable VoiceChannel merely because wx UI is active.
    assert "using_wx_ui()" not in block
    assert "return True" in block


def test_info_queues_then_update():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def info(self,", 1)[1].split("\n    def ", 1)[0]
    assert "self.update()" in block
    assert "_wx_append_log" in block


def test_alert_important_prefer_voice():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    alert = text.split("def alert(self,", 1)[1].split("\n    def ", 1)[0]
    important = text.split("def important(self,", 1)[1].split("\n    def ", 1)[0]
    assert 'keywords["prefer_voice"] = True' in alert
    assert 'keywords["prefer_voice"] = True' in important


def test_ops_stay_on_screen_reader():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    confirmation = text.split("def confirmation(self,", 1)[1].split("\n    def ", 1)[0]
    item = text.split("def item(", 1)[1].split("\n    def ", 1)[0]
    assert 'keywords["prefer_voice"] = False' in confirmation
    assert "_ops_via_screen_reader" in item
    assert "_wx_announce" in item
    assert "force=False" in item
    assert "allow_in_menu=True" in item


def test_say_now_sr_takes_primary_out_of_match():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def _say_now(", 1)[1].split("\n    def ", 1)[0]
    assert "prefer_voice and _game_tts.in_match()" in block
    assert "allow_in_menu=bool(allow_in_menu or prefer_voice)" in block


def test_update_history_uses_sr_out_of_match():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def update(self):", 1)[1].split("\n    def ", 1)[0]
    assert "not _game_tts.in_match()" in block
    assert "_wx_announce" in block
    assert "_wx_busy()" in block
