"""Options → secondary voice editor must speak TTS ids, not digits 5762/5778."""
from __future__ import annotations

from pathlib import Path


def test_secondary_editor_intro_uses_tts_ids_not_digit_strings():
    from soundrts.lib.voice_libs import SECONDARY, editor_intro_msgparts
    import soundrts.msgparts as mp

    parts = editor_intro_msgparts(SECONDARY)
    assert mp.VOICE_LIB_SECONDARY[0] in parts
    assert mp.VOICE_LIB_EDITOR_HINT[0] in parts
    assert 5762 in parts
    assert 5778 in parts
    literals = [x for x in parts if isinstance(x, str)]
    assert all("5762" not in x and "5778" not in x for x in literals)


def test_primary_editor_intro_uses_primary_title_id():
    from soundrts.lib.voice_libs import PRIMARY, editor_intro_msgparts
    import soundrts.msgparts as mp

    parts = editor_intro_msgparts(PRIMARY)
    assert mp.VOICE_LIB_PRIMARY[0] in parts
    assert 5761 in parts
    assert 5762 not in parts


def test_voice_lib_editor_does_not_stringify_title_hint_ids():
    src = Path(__file__).resolve().parents[1].joinpath("clientmain.py").read_text(
        encoding="utf-8"
    )
    start = src.index("def voice_lib_editor")
    end = src.index("\ndef voice_libs_menu")
    block = src[start:end]
    assert "editor_intro_msgparts" in block
    assert 'f"{title}' not in block
    assert "literal_text_msg(f" not in block
