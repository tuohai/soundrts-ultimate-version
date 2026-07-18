"""Game VoiceChannel uses SAPI; screen-reader ops use AO2 — separate mouths."""

from pathlib import Path
import re


def test_voicechannel_uses_game_tts_not_ao2():
    text = Path("soundrts/lib/voicechannel.py").read_text(encoding="utf-8")
    assert "game_tts.speak" in text
    assert "game_tts.stop" in text
    assert "game_tts.is_speaking" in text
    assert "tts.init(" in text
    # Reject bare AO2 calls (not the game_tts.* ones).
    assert re.search(r"(?<![.\w])tts\.speak\(", text) is None
    assert re.search(r"(?<![.\w])tts\.stop\(", text) is None
    assert re.search(r"(?<![.\w])tts\.is_speaking\(", text) is None


def test_game_tts_module_exists():
    text = Path("soundrts/lib/game_tts.py").read_text(encoding="utf-8")
    assert "SAPI.SpVoice" in text
    assert "def speak(" in text
    assert "def stop(" in text
    assert "screen reader" in text.lower()


def test_sound_stop_does_not_kill_screen_reader():
    text = Path("soundrts/lib/sound.py").read_text(encoding="utf-8")
    block = text.split("def stop(stop_voice_too=True):", 1)[1].split("\nclass ", 1)[0]
    assert "game_tts.stop()" in block
    assert re.search(r"(?<![.\w])tts\.stop\(\)", block) is None
