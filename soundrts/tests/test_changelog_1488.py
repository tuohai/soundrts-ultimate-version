"""审计：1.4.8.8 — 撤回 0 攻打负护甲。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1488(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.8")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.7")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1488():
    assert 'VERSION = "1.4.8.8"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1488_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.8") < src.index("1.4.8.7"), lang


def test_zh_relnotes_1488_session_topics():
    s = _section_1488("zh")
    assert "mdg 0" in s or "mdg == 0" in s
    assert "负" in s or "mdf" in s
    assert "穿透" in s or "投石车" in s or "1.4.8.7" in s


def test_en_relnotes_1488_session_topics():
    s = _section_1488("en")
    assert "mdg 0" in s or "mdg == 0" in s
    assert "negative" in s.lower() or "mdf" in s
    assert "pierce" in s.lower() or "mangonel" in s.lower() or "1.4.8.7" in s


def test_es_it_pt_relnotes_1488_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1488(lang)
        assert "mdg" in s, lang
        assert "1.4.8.7" in s, lang
