"""审计：1.4.9.0 — 溅射 *_vs 按被命中单位；投石车 40/50/75；帝国2溅射池对齐。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1490(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.0")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.9")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1490():
    assert 'VERSION = "1.4.9.0"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1490_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.0") < src.index("1.4.8.9"), lang


def test_zh_relnotes_1490_session_topics():
    s = _section_1490("zh")
    assert "mdg_splash_vs" in s
    assert "被溅到" in s or "被命中" in s
    assert "40" in s and "50" in s and "75" in s
    assert "投石" in s or "mangonel" in s.lower()
    assert "mdg_splash" in s
    assert "手推炮" in s or "炮舰" in s or "炮塔" in s


def test_en_relnotes_1490_session_topics():
    s = _section_1490("en")
    assert "mdg_splash_vs" in s
    assert "victim" in s.lower() or "splashed" in s.lower()
    assert "40" in s and "50" in s and "75" in s
    assert "mdg_splash" in s
    assert "bombard" in s.lower() or "cannon" in s.lower()


def test_es_it_pt_relnotes_1490_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1490(lang)
        assert "mdg_splash_vs" in s, lang
        assert "40" in s and "50" in s and "75" in s, lang
        assert "mdg_splash" in s, lang
        assert "mdg" in s and "rdg" in s, lang


def test_modding_docs_cover_splash_vs():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "mdg_splash_vs" in src, lang
        assert "rdg_splash_vs" in src, lang
