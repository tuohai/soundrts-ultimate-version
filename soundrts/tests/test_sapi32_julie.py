"""32-bit-only SAPI voices (VW Julie) via Wow6432Node / sapi32 helper."""

from soundrts.lib import game_tts, sapi32_tts


def test_wow6432_lists_vw_julie():
    names = sapi32_tts.list_wow6432_token_names()
    assert any("julie" in (n or "").lower() for n in names), names


def test_needs_sapi32_for_vw_julie():
    assert game_tts.needs_sapi32("VW Julie") is True
    assert game_tts.needs_sapi32("auto") is False


def test_list_sapi_voices_includes_julie_when_helper_available():
    if not sapi32_tts.available():
        return
    names = game_tts.list_sapi_voices()
    assert any("julie" in (n or "").lower() for n in names), names
