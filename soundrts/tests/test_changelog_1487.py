"""审计：1.4.8.7 — 穿透；投石车降伤；0 攻打负护甲冲车。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1487(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.7")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.6")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1487():
    # 1.4.8.7 notes remain after later bumps; current VERSION is owned by 1488+.
    assert "1.4.8.7" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1487_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.7") < src.index("1.4.8.6"), lang


def test_zh_relnotes_1487_session_topics():
    s = _section_1487("zh")
    assert "rdg_pierce_line" in s
    assert "pierce_width" in s or "*_pierce_width" in s
    assert "投石车" in s or "40→30" in s
    assert "mdf -3" in s or "mdf −3" in s or "−3" in s
    assert "mdg_range" in s


def test_en_relnotes_1487_session_topics():
    s = _section_1487("en")
    assert "rdg_pierce_line" in s
    assert "scorpion" in s
    assert "40→30" in s or "40->30" in s
    assert "mdf -3" in s or "mdf −3" in s
    assert "mdg_range" in s


def test_es_it_pt_relnotes_1487_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1487(lang)
        assert "rdg_pierce_line" in s, lang
        assert "40→30" in s or "40->30" in s, lang
        assert "mdg_range" in s, lang
        assert "mdf -3" in s or "mdf −3" in s, lang
