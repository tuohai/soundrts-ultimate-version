"""审计：1.4.9.5 — 选项改速度后开局仍用启动时的值。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1495(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.5")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.4")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1495():
    assert 'VERSION = "1.4.9.5"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1495_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.5") < src.index("1.4.9.4"), lang


def test_zh_relnotes_1495_session_topics():
    s = _section_1495("zh")
    assert "current_game_speed" in s
    assert "config.speed" in s
    assert "game.py" in s


def test_en_relnotes_1495_session_topics():
    s = _section_1495("en")
    assert "current_game_speed" in s
    assert "config.speed" in s


def test_other_langs_have_1495_scope():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1495(lang)
        assert "current_game_speed" in s, lang
        assert "game.py" in s, lang
