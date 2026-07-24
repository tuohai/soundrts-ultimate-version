"""Cut-scenes: Enter advances, Esc skips; pygame on-screen text (no wx)."""

from pathlib import Path


def test_play_cutscene_line_exists():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    assert "def play_cutscene_line(" in text
    assert "def _poll_cutscene_command(self)" in text
    assert 'return "next"' in text or 'result = "next"' in text
    assert 'return "skip"' in text or 'result = "skip"' in text
    block = text.split("def play_cutscene_line(", 1)[1].split("\n    def ", 1)[0]
    assert "self.channel.play" in block


def test_play_sequence_uses_cutscene_controls():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    block = text.split("def play_sequence(names):", 1)[1].split("\ndef ", 1)[0]
    assert "play_narrative_line" in block
    assert "force_voice_channel" not in block
    assert '== "skip"' in block


def test_campaign_skips_redundant_title_enter():
    """Selecting 序幕 from the menu must go straight into the story sequence."""
    text = Path("soundrts/campaign.py").read_text(encoding="utf-8")
    block = text.split("def run(self):", 1)[1].split("def run_for_coop", 1)[0]
    assert "play_sequence(self.sequence)" in block
    assert "play_cutscene_line(self.title)" not in block


def test_cutscene_uses_pygame_display():
    text = Path("soundrts/lib/voice.py").read_text(encoding="utf-8")
    block = text.split("def play_cutscene_line(", 1)[1]
    # Next method at class indent, or end of class
    nxt = block.find("\n    def ")
    if nxt != -1:
        block = block[:nxt]
    assert "show_narrative" in block
    assert "_ignore_enter_until" in block
    assert "pygame_ui" in block
