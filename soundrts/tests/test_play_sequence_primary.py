"""Campaign intro / cut-scene sequences must use primary (not in-match secondary)."""

from pathlib import Path


def test_play_sequence_forces_primary_channel():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    block = text.split("def play_sequence(names):", 1)[1].split("\ndef ", 1)[0]
    assert "tts_channel=game_tts.PRIMARY" in block
    assert "voice.important([name], tts_channel=game_tts.PRIMARY)" in block
