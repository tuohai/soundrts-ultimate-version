"""审计：1.4.8.5 — 框选优先军事单位；起步单位序列帧动画（可选 Spine）。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1485(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.5")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.4")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1485():
    # 1.4.8.5 notes remain after later bumps; current VERSION is owned by 1486+.
    assert "1.4.8.5" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1485_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.5") < src.index("1.4.8.4"), lang


def test_zh_relnotes_1485_session_topics():
    s = _section_1485("zh")
    assert "class soldier" in s
    assert "class worker" in s
    assert "框选" in s
    assert "gen_unit_anims" in s
    assert "dirs: 4" in s or '"dirs": 4' in s
    assert "Spine" in s
    assert "walk" in s
    assert "停止耕种" in s or "stop cultivate" in s.lower()
    assert "get_default_order" in s
    assert "gather" in s
    assert "frank_horse_collar" in s
    assert "player.has" in s


def test_en_relnotes_1485_session_topics():
    s = _section_1485("en")
    assert "class soldier" in s
    assert "class worker" in s
    assert "box-select" in s
    assert "gen_unit_anims" in s
    assert "dirs: 4" in s or '"dirs": 4' in s
    assert "Spine" in s
    assert "walk" in s
    assert "stop cultivate" in s.lower()
    assert "get_default_order" in s
    assert "frank_horse_collar" in s
    assert "player.has" in s


def test_es_it_pt_relnotes_1485_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1485(lang)
        assert "class soldier" in s, lang
        assert "class worker" in s, lang
        assert "gen_unit_anims" in s, lang
        assert "Spine" in s, lang
        assert "get_default_order" in s, lang
        assert "frank_horse_collar" in s, lang
        assert "player.has" in s, lang
