"""When a screen reader is active, primary speech goes through AO2, not Nuance."""

from pathlib import Path
from unittest import mock


def test_tts_exposes_using_screen_reader():
    text = Path("soundrts/lib/tts.py").read_text(encoding="utf-8")
    assert "def using_screen_reader" in text
    assert "_SYSTEM_TTS_NAMES" in text


def test_game_tts_primary_delegates_to_ao2_when_sr(monkeypatch):
    import soundrts.lib.game_tts as game_tts

    calls = []

    class FakeAo2:
        @staticmethod
        def using_screen_reader():
            return True

        @staticmethod
        def speak(text, interrupt=True):
            calls.append(("speak", text, interrupt))

        @staticmethod
        def stop():
            calls.append(("stop",))

        @staticmethod
        def is_speaking():
            return False

    monkeypatch.setattr(game_tts, "nuance_tts", mock.Mock(), raising=False)
    import soundrts.lib.tts as ao2_mod

    monkeypatch.setattr(ao2_mod, "using_screen_reader", FakeAo2.using_screen_reader)
    monkeypatch.setattr(ao2_mod, "speak", FakeAo2.speak)
    monkeypatch.setattr(ao2_mod, "stop", FakeAo2.stop)
    monkeypatch.setattr(ao2_mod, "is_speaking", FakeAo2.is_speaking)

    game_tts.speak("菜单测试", interrupt=True, channel=game_tts.PRIMARY)
    assert any(c[0] == "speak" and c[1] == "菜单测试" for c in calls)
    assert game_tts.last_spoken(game_tts.PRIMARY) == "菜单测试"


def test_game_tts_secondary_does_not_delegate_to_ao2(monkeypatch):
    import soundrts.lib.game_tts as game_tts
    import soundrts.lib.tts as ao2_mod

    ao2_calls = []

    monkeypatch.setattr(ao2_mod, "using_screen_reader", lambda: True)
    monkeypatch.setattr(
        ao2_mod, "speak", lambda *a, **k: ao2_calls.append(("speak", a, k))
    )

    nuance_calls = []

    class FakeNuance:
        @staticmethod
        def is_nuance_voice(voice_id):
            return True

        @staticmethod
        def speak(*args, **kwargs):
            nuance_calls.append((args, kwargs))

        @staticmethod
        def stop():
            pass

        @staticmethod
        def set_audio_device(*_a, **_k):
            pass

        @staticmethod
        def is_speaking():
            return False

    monkeypatch.setattr(game_tts, "nuance_tts", FakeNuance, raising=False)

    import soundrts.lib.voice_libs as voice_libs

    monkeypatch.setattr(voice_libs, "load_from_config", lambda: None)
    monkeypatch.setattr(voice_libs, "get_voice", lambda ch: "nuance:test")
    monkeypatch.setattr(voice_libs, "get_rate", lambda ch: 50)
    monkeypatch.setattr(voice_libs, "get_volume", lambda ch: 80)
    monkeypatch.setattr(voice_libs, "get_pitch", lambda ch: 50)
    monkeypatch.setattr(voice_libs, "get_device", lambda ch: "default")
    monkeypatch.setattr(voice_libs, "sapi_rate_from_100", lambda r: 0)

    game_tts.set_in_match(True)
    try:
        game_tts.speak("伤亡提示", interrupt=True, channel=game_tts.SECONDARY)
        import time

        time.sleep(0.05)
    finally:
        game_tts.set_in_match(False)

    assert not ao2_calls
    assert nuance_calls or game_tts.last_spoken(game_tts.SECONDARY) == "伤亡提示"
