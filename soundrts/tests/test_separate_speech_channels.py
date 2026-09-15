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
    """Verify stop(stop_voice_too=True) doesn't shut down the active screen reader.

    Two valid implementations exist:
      (a) stop calls game_tts.stop() (preferred — game_tts ignores AO2 reader)
      (b) stop calls tts.stop() which itself guards using_screen_reader() and
          bails out when a screen reader is active.

    Both are correct; only forbid the naive ``pygame.mixer.Channel(0).stop()`` style
    which kills the voice channel a screen reader may be sharing.
    """
    text = Path("soundrts/lib/sound.py").read_text(encoding="utf-8")
    block = text.split("def stop(stop_voice_too=True):", 1)[1].split("\nclass ", 1)[0]
    # At least one of these must be present.
    assert ("game_tts.stop()" in block) or ("tts.stop()" in block)
    # When delegating to bare tts.stop(), confirm the tts module itself
    # has the screen-reader guard (otherwise we WOULD kill the reader).
    if "tts.stop()" in block and "game_tts.stop()" not in block:
        tts_text = Path("soundrts/lib/tts.py").read_text(encoding="utf-8")
        assert "using_screen_reader" in tts_text
    # Must NOT call bare pygame.mixer.Channel(0).stop() — that would kill the
    # voice channel the screen reader is sharing. Other mixer channels are fine.
    assert "Channel(0).stop()" not in block or "tts.stop()" in block
    assert "pygame.mixer.Channel(0).stop()" not in block
