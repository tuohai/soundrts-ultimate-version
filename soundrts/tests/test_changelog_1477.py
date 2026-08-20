"""审计：1.4.7.7 — 城镇中心驻军射箭、马里文明、文明建筑壳样式标题。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1477(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.7.7")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.6")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1477():
    assert 'VERSION = "1.4.7.7"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1477_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.7.7") < src.index("1.4.7.6"), lang


def test_zh_relnotes_1477_session_topics():
    s = _section_1477("zh")
    assert "garrison_arrows" in s
    assert "base_arrows" in s
    assert "max_garrison_arrows" in s
    assert "马里" in s
    assert "提圭" in s
    assert "法林巴" in s
    assert "女卫兵" in s
    assert "8532" in s
    assert "malian_barracks" in s
    assert "style.txt" in s


def test_en_relnotes_1477_session_topics():
    s = _section_1477("en")
    assert "garrison_arrows" in s
    assert "base_arrows" in s
    assert "Malians" in s
    assert "Tigui" in s
    assert "Farimba" in s
    assert "Gbeto" in s
    assert "8532" in s
    assert "malian_barracks" in s
    assert "style.txt" in s


def test_es_it_pt_relnotes_1477_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1477(lang)
        assert "garrison_arrows" in s, lang
        assert "base_arrows" in s, lang
        assert "Tigui" in s, lang
        assert "Farimba" in s, lang
        assert "Gbeto" in s, lang
        assert "8532" in s, lang
        assert "malian_barracks" in s, lang
        assert "style.txt" in s, lang
