"""Braille / screen-reader review helpers for the wx UI."""

from pathlib import Path


def test_tts_exposes_braille():
    text = Path("soundrts/lib/tts.py").read_text(encoding="utf-8")
    assert "def Braille(self, text):" in text
    assert "def braille(text: str):" in text


def test_voice_mirrors_latest_and_braille():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    assert "wxui.set_latest_message(text)" in text
    assert "tts.braille(text)" in text


def test_wx_frame_has_latest_field():
    text = Path("soundrts/lib/wxui/frame.py").read_text(encoding="utf-8")
    assert "self.latest" in text
    assert "def show_cutscene_line" in text
    assert "def focus_braille_review(self):" in text
    assert "def set_latest(self, text: str):" in text
    assert "AppendText" in text
    # Must not reintroduce the English caption as the accessible name.
    assert 'label="Latest announcement"' not in text


def test_voice_avoids_double_braille_on_interrupt():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    # interrupt path must not call tts.braille before speak (double flash).
    block_start = text.index("def _wx_announce")
    block = text[block_start : text.index("def _wx_play_sfx_from_parts")]
    assert "tts.speak(text, interrupt=True)" in block
    # braille only on the queued (non-interrupt) path
    assert "tts.braille(text)" in block
    assert "if interrupt:" in block
    assert block.index("if interrupt:") < block.index("tts.speak(text, interrupt=True)")
    interrupt_branch = block.split("if interrupt:")[1].split("else:")[0]
    assert "tts.braille(text)" not in interrupt_branch
    assert "tts.speak(text, interrupt=True)" in interrupt_branch


def test_bindings_include_braille_hotkeys():
    for path in (
        "res/ui/global_bindings.txt",
        "res/ui/legacy_bindings.txt",
        "res/ui/help_bindings.txt",
    ):
        text = Path(path).read_text(encoding="utf-8")
        assert "CTRL B: focus_braille_review" in text, path
        assert "CTRL SHIFT B: focus_message_log" in text, path


def test_game_commands_registered():
    text = Path("soundrts/clientgame/__init__.py").read_text(encoding="utf-8")
    assert "cmd_focus_braille_review" in text
    assert "cmd_focus_message_log" in text
