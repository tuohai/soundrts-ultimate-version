"""审计：1.4.8.3 — aoe2 HUD/地图图与建筑风格套。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1483(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.3")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.2")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1483():
    # 1.4.8.3 notes remain after later bumps; current VERSION is owned by 1484+.
    assert "1.4.8.3" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1483_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.3") < src.index("1.4.8.2"), lang


def test_zh_relnotes_1483_session_topics():
    s = _section_1483("zh")
    assert "architecture.txt" in s
    assert "gen_aoe2_hud_icons.py" in s
    assert "ui/icons" in s
    assert "ui/map" in s
    assert "western_european" in s
    assert "marine" in s
    assert "zergling" in s
    assert "zealot" in s
    assert "建筑风格" in s


def test_en_relnotes_1483_session_topics():
    s = _section_1483("en")
    assert "architecture.txt" in s
    assert "gen_aoe2_hud_icons.py" in s
    assert "ui/icons" in s
    assert "ui/map" in s
    assert "western_european" in s
    assert "marine" in s
    assert "zergling" in s
    assert "zealot" in s
    assert "architecture set" in s.lower()


def test_es_it_pt_relnotes_1483_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1483(lang)
        assert "architecture.txt" in s, lang
        assert "gen_aoe2_hud_icons.py" in s, lang
        assert "ui/icons" in s, lang
        assert "ui/map" in s, lang
        assert "western_european" in s, lang
        assert "marine" in s, lang
        assert "zergling" in s, lang
        assert "zealot" in s, lang


def test_modding_docs_cover_architecture_sets():
    for lang, needle in (
        ("zh", "自 1.4.8.3"),
        ("en", "since 1.4.8.3"),
        ("es", "desde 1.4.8.3"),
        ("it", "da 1.4.8.3"),
        ("pt-BR", "desde 1.4.8.3"),
    ):
        src = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "architecture.txt" in src, lang
        assert needle.lower() in src.lower(), lang
        assert "gen_aoe2_hud_icons.py" in src, lang


def test_player_manuals_cover_mod_art_overlay():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "player", "manual.rst")
        assert "architecture.txt" in src, lang
        assert "1.4.8.3" in src, lang
