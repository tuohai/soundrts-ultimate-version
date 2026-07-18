"""Main-menu F3 speech channel toggle (voice <-> screen reader)."""

from pathlib import Path


def test_toggle_speech_channel_exists():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    assert "def toggle_speech_channel(" in text
    assert "def set_speech_channel(" in text
    assert "_ui_backend_runtime" in text


def test_main_menu_f3_wired():
    text = Path("soundrts/clientmenu.py").read_text(encoding="utf-8")
    assert "K_F3" in text
    assert "toggle_speech_channel()" in text
    assert 'menu_type", "main") == "main"' in text or "menu_type', 'main') == 'main'" in text


def test_speech_channel_msgparts():
    text = Path("soundrts/msgparts.py").read_text(encoding="utf-8")
    assert "SPEECH_CHANNEL_VOICE" in text
    assert "SPEECH_CHANNEL_SCREEN_READER" in text


def test_wx_set_frame_visible():
    text = Path("soundrts/lib/wxui/bootstrap.py").read_text(encoding="utf-8")
    assert "def set_frame_visible(" in text
