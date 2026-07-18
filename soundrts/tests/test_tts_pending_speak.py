"""TTS busy flag must stay true while speak is still queued (cut-scene wait)."""

from pathlib import Path


def test_tts_tracks_pending_speak():
    text = Path("soundrts/lib/tts.py").read_text(encoding="utf-8")
    assert "_pending_speak" in text
    assert "or _pending_speak > 0" in text
    assert "_pending_speak = max(0, _pending_speak - 1)" in text
    # Must not clear busy while a speak is still pending
    assert "_pending_speak <= 0" in text


def test_play_sequence_not_auto_skippable():
    text = Path("soundrts/clientmedia.py").read_text(encoding="utf-8")
    block = text.split("def play_sequence(names):", 1)[1].split("\ndef ", 1)[0]
    assert "play_cutscene_line" in block
    assert '== "skip"' in block
    # Must not wipe VoiceChannel before hybrid .ogg / important lines.
    assert "voice.channel.stop()" not in block
