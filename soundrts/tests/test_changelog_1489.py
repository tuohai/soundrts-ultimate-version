"""审计：1.4.8.9 — 渔船征用崩溃；弩炮穿透挂属性；岸边鱼迷雾采集。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1489(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.9")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.8")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1489():
    assert 'VERSION = "1.4.8.9"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1489_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.9") < src.index("1.4.8.8"), lang


def test_zh_relnotes_1489_session_topics():
    s = _section_1489("zh")
    assert "deep_fish" in s
    assert "rdg_pierce_line" in s
    assert "shore_fish" in s or "岸边鱼" in s
    assert "memorized" in s or "记忆" in s


def test_en_relnotes_1489_session_topics():
    s = _section_1489("en")
    assert "deep_fish" in s
    assert "rdg_pierce_line" in s
    assert "shore_fish" in s
    assert "memorized" in s.lower() or "memory" in s.lower()


def test_es_it_pt_relnotes_1489_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1489(lang)
        assert "deep_fish" in s, lang
        assert "rdg_pierce_line" in s, lang
        assert "shore_fish" in s, lang
