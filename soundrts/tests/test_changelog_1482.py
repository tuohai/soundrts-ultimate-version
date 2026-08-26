"""审计：1.4.8.2 — starting_squares 洗牌；入库音 store_resourceN。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1482(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.2")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.1")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1482():
    # 1.4.8.2 notes remain after later bumps; current VERSION is owned by 1483+.
    assert "1.4.8.2" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1482_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.2") < src.index("1.4.8.1"), lang


def test_zh_relnotes_1482_session_topics():
    s = _section_1482("zh")
    assert "gather_from_shore" in s
    assert "shore_fish" in s
    assert "deep_fish" in s
    assert "starting_squares" in s
    assert "starting_units" in s
    assert "random_starts" in s
    assert "store_resource1" in s
    assert "store_resource_0" in s
    assert "noise_when_building" in s
    assert "出生" in s
    assert "钓鱼" in s


def test_en_relnotes_1482_session_topics():
    s = _section_1482("en")
    assert "gather_from_shore" in s
    assert "shore_fish" in s
    assert "deep_fish" in s
    assert "starting_squares" in s
    assert "starting_units" in s
    assert "random_starts" in s
    assert "store_resource1" in s
    assert "store_resource_0" in s
    assert "spawn" in s.lower()
    assert "warehouse" in s.lower()


def test_es_it_pt_relnotes_1482_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1482(lang)
        assert "gather_from_shore" in s, lang
        assert "shore_fish" in s, lang
        assert "starting_squares" in s, lang
        assert "starting_units" in s, lang
        assert "random_starts" in s, lang
        assert "store_resource1" in s, lang
        assert "store_resource_0" in s, lang
        assert "noise_when_building" in s, lang


def test_mapmaking_docs_cover_faction_default_shuffle():
    for lang, needle in (
        ("zh", "自 1.4.8.2"),
        ("en", "Since 1.4.8.2"),
        ("es", "Desde 1.4.8.2"),
        ("it", "Da 1.4.8.2"),
        ("pt-BR", "Desde 1.4.8.2"),
    ):
        src = _source("doc_src", "src", lang, "mod", "mapmaking.rst")
        assert "starting_squares" in src
        assert needle in src, lang
        assert "starting_units" in src


def test_modding_docs_cover_store_resource_keys():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "store_resource1" in src, lang
        assert "store_resource_0" in src, lang
        assert "noise_when_building" in src, lang
