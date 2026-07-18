"""Cut-scenes: Enter advances, Esc skips; no auto-scroll."""

from pathlib import Path


def test_play_cutscene_line_exists():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    assert "def play_cutscene_line(self," in text
    assert "def _poll_cutscene_command(self)" in text
    assert 'return "next"' in text
    assert 'return "skip"' in text
    # Cut-scenes with .ogg must play VoiceChannel even under screen reader.
    block = text.split("def play_cutscene_line(self,", 1)[1].split("\n    def ", 1)[0]
    assert "self.channel.play" in block
    assert "_cutscene_parts_have_audio" in block


def test_play_sequence_uses_cutscene_controls():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    block = text.split("def play_sequence(names):", 1)[1].split("\ndef ", 1)[0]
    assert "play_cutscene_line" in block
    assert "force_voice_channel" not in block
    assert '== "skip"' in block


def test_campaign_skips_redundant_title_enter():
    """Selecting 序幕 from the menu must go straight into the story sequence."""
    text = Path("soundrts/campaign.py").read_text(encoding="utf-8")
    block = text.split("def run(self):", 1)[1].split("def run_for_coop", 1)[0]
    assert "play_sequence(self.sequence)" in block
    assert "play_cutscene_line(self.title)" not in block


def test_cutscene_uses_textctrl_display():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def play_cutscene_line(self,", 1)[1].split("\n    def ", 1)[0]
    assert "show_cutscene_line" in block
    assert "_ignore_enter_until" in block
