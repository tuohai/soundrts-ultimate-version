"""审计：1.4.9.9 — 升级时代音效 age_advance（ui/sounds 的 mp3/wav）。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1499(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.9")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.8")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1499():
    # 1.4.9.9 notes remain after later bumps; current VERSION is owned by 1.5+.
    assert "1.4.9.9" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1499_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.9") < src.index("1.4.9.8"), lang


def test_zh_relnotes_1499_session_topics():
    s = _section_1499("zh")
    assert "age_advance" in s
    assert "ui/sounds" in s
    assert "ui/music" in s
    assert "sound_cache.py" in s
    assert "test_ui_sfx_stem.py" in s


def test_en_es_it_pt_relnotes_1499_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1499(lang)
        assert "age_advance" in s, lang
        assert "ui/sounds" in s, lang
        assert "ui/music" in s, lang
        assert "sound_cache.py" in s, lang
        assert "test_ui_sfx_stem.py" in s, lang


def test_engine_indexes_ogg_wav_sfx_outside_music():
    cache = _source("soundrts", "lib", "sound_cache.py")
    style = _source("mods", "aoe2", "ui", "style.txt")
    events = _source("soundrts", "clientgameentity", "events.py")
    prod = _source("soundrts", "worldorders", "production.py")
    assert "def ui_sfx_stem" in cache
    assert '_SFX_SUFFIXES = (".ogg", ".wav")' in cache
    assert "upgrade_complete age_advance" in style
    assert 'launch_event_style("upgrade_complete"' in events
    assert 'self.unit.notify("upgrade_complete")' in prod
    sounds = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "ui" / "sounds"
    assert (sounds / "age_advance.ogg").is_file()
    assert not (sounds / "age_advance.mp3").exists()
