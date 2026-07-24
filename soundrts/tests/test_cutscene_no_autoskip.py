"""Cut-scene player wiring (Enter/Esc locally; scroll when multi-human)."""

from pathlib import Path


def test_play_sequence_cutscene_style():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    block = text.split("def play_sequence(names):", 1)[1].split("\ndef ", 1)[0]
    assert "play_narrative_line" in block
    assert "force_voice_channel" not in block
