"""End-of-game stats: browse under wx, queued speech under voice channel."""

from pathlib import Path


def test_browse_stat_messages_voice_queues():
    text = Path("soundrts/game.py").read_text(encoding="utf-8")
    assert "def _browse_stat_messages(self, msgs):" in text
    assert "voice.flush()" in text
    # Edit box for both channels; voice.info only as no-wx fallback
    assert "browse_message_list" in text
    assert "on_voice_channel" in text
    assert "set_frame_visible" in text
    block = text.split("def _browse_stat_messages", 1)[1].split(
        "def present_end_stats", 1
    )[0]
    # Must not speak-then-dialog (that was the unwanted rapid scroll).
    assert "if on_voice_channel:\n            for msg in msgs:\n                voice.info" not in block


def test_browse_message_list_uses_edit_box():
    text = Path("soundrts/lib/wxui/dialogs.py").read_text(encoding="utf-8")
    block = text.split("def browse_message_list", 1)[1].split("\ndef ", 1)[0]
    assert "wx.TextCtrl" in block
    assert "TE_READONLY" in block
    assert "ListBox" not in block


def test_present_end_stats_wired():
    text = Path("soundrts/game.py").read_text(encoding="utf-8")
    assert "def present_end_stats(self):" in text
    assert "self._browse_stat_messages(" in text
    assert "self.present_end_stats()" in text
