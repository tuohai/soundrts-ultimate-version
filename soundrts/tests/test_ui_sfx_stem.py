"""ui/sounds event SFX vs ui/music BGM indexing."""
from soundrts.lib.sound_cache import ui_sfx_stem, _sfx_lookup_key


def test_ui_sfx_stem_accepts_ogg_wav_in_sounds():
    assert ui_sfx_stem("sounds/age_advance.ogg") == "age_advance"
    assert ui_sfx_stem("sounds/wolf.wav") == "wolf"
    assert ui_sfx_stem("ui/sounds/research.ogg") == "research"


def test_ui_sfx_stem_rejects_mp3():
    assert ui_sfx_stem("sounds/age_advance.mp3") is None


def test_ui_sfx_stem_skips_music_directory():
    assert ui_sfx_stem("music/town.mp3") is None
    assert ui_sfx_stem("music/xtown.mp3") is None
    assert ui_sfx_stem("music/age_advance.ogg") is None
    assert ui_sfx_stem(r"music\town.mp3") is None


def test_ui_sfx_stem_skips_non_audio():
    assert ui_sfx_stem("sounds/readme.txt") is None
    assert ui_sfx_stem("style.txt") is None


def test_sfx_lookup_key_strips_ogg_wav_only():
    assert _sfx_lookup_key("age_advance") == "age_advance"
    assert _sfx_lookup_key("age_advance.ogg") == "age_advance"
    assert _sfx_lookup_key("WOLF.WAV") == "WOLF"
    assert _sfx_lookup_key("age_advance.mp3") == "age_advance.mp3"
