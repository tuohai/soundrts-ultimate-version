"""审计：1.4.7.5 — 工人对损坏建筑默认修理。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1475(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.7.5")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.4")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1475():
    # 1.4.7.5 notes remain after later bumps; current VERSION is owned by 1476+.
    assert "1.4.7.5" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1475_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.7.5") < src.index("1.4.7.4"), lang


def test_zh_relnotes_1475_session_topics():
    s = _section_1475("zh")
    assert "修理" in s
    assert "损坏" in s
    assert "is_repairable" in s
    assert "go" in s


def test_en_relnotes_1475_session_topics():
    s = _section_1475("en")
    assert "repair" in s.lower()
    assert "damaged" in s.lower()
    assert "is_repairable" in s
    assert "go" in s


def test_es_it_pt_relnotes_1475_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1475(lang)
        assert "is_repairable" in s, lang
        assert "go" in s, lang
        assert "can_repair" in s, lang
