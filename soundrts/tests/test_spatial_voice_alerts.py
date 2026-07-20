"""Directional secondary-voice alerts (stereo pan for enemy / square cues)."""

from pathlib import Path

from soundrts.lib.sound import DEFAULT_VOLUME, stereo
from soundrts.lib.voicechannel import _wants_spatial_tts

_ROOT = Path(__file__).resolve().parents[1]


def test_wants_spatial_tts_detects_left_right_imbalance():
    assert _wants_spatial_tts(0.2, 0.9) is True
    assert _wants_spatial_tts(0.9, 0.2) is True
    assert _wants_spatial_tts(DEFAULT_VOLUME, DEFAULT_VOLUME) is False


def test_wants_spatial_tts_detects_attenuated_rear():
    quiet = DEFAULT_VOLUME / 2.0
    assert _wants_spatial_tts(quiet, quiet) is True


def test_stereo_distance_cap_keeps_far_near_adjacent_loudness():
    """Far sources without a cap go very quiet; with cap they stay near adjacent."""
    adjacent = stereo(0, 0, 1.0, 0, 90)
    far = stereo(0, 0, 12.0, 0, 90)
    far_capped = stereo(0, 0, 12.0, 0, 90, distance_cap=1.15)
    adj_peak = max(adjacent)
    far_peak = max(far)
    capped_peak = max(far_capped)
    assert far_peak < adj_peak * 0.25
    # Floor ≈ adjacent / 1.15 (slightly quieter than one-square)
    assert capped_peak >= adj_peak / 1.15 * 0.95
    assert capped_peak <= adj_peak * 1.01


def test_place_voice_pan_caps_distance_attenuation():
    text = (_ROOT / "clientgame" / "game_unit_control.py").read_text(encoding="utf-8")
    assert "distance_cap" in text.split("def _place_voice_pan", 1)[1].split(
        "\ndef ", 1
    )[0]
    text_res = (_ROOT / "clientgame" / "game_resources.py").read_text(encoding="utf-8")
    assert "distance_cap" in text_res.split("def _minimap_stereo", 1)[1].split(
        "\ndef ", 1
    )[0]


def test_units_alert_passes_minimap_stereo_pan():
    text = (_ROOT / "clientgame" / "game_unit_control.py").read_text(encoding="utf-8")
    assert "def _place_voice_pan" in text
    assert "def _place_pan_fn" in text
    assert "_minimap_stereo" in text
    body = text.split("def units_alert", 1)[1].split("\ndef ", 1)[0]
    assert "pan_fn=_place_pan_fn(interface, place)" in body


def test_nuance_speak_forwards_lv_rv():
    text = (_ROOT / "lib" / "nuance_tts.py").read_text(encoding="utf-8")
    assert '"lv": gain_l' in text
    assert '"rv": gain_r' in text
    assert "def set_pan(" in text


def test_voicechannel_spatial_path_uses_synthesize_or_pan_speak():
    text = (_ROOT / "lib" / "voicechannel.py").read_text(encoding="utf-8")
    assert "synthesize_sound" in text
    assert "lv=lv, rv=rv" in text
    assert "_play_spatial_tts" in text
    assert "_play_spatial_text" in text
    assert "_refresh_live_pan" in text
    assert "pan_fn" in text


def test_game_tts_has_synthesize_sound():
    text = (_ROOT / "lib" / "game_tts.py").read_text(encoding="utf-8")
    assert "def synthesize_sound(" in text
    assert "SpFileStream" in text
    assert "def set_pan(" in text


def test_message_accepts_pan_fn():
    from soundrts.lib.message import Message

    called = []

    def pan():
        called.append(1)
        return 0.2, 0.9

    msg = Message(["x"], 0.2, 0.9, pan_fn=pan)
    assert msg.pan_fn is pan
    assert msg.pan_fn() == (0.2, 0.9)
    assert called == [1]
