"""审计：1.4.8.4 — Ctrl+F2 俯视图与世界模拟热路径。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1484(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.4")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.3")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1484():
    # 1.4.8.4 notes remain after later bumps; current VERSION is owned by 1485+.
    assert "1.4.8.4" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1484_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.4") < src.index("1.4.8.3"), lang


def test_zh_relnotes_1484_session_topics():
    s = _section_1484("zh")
    assert "Ctrl+F2" in s
    assert "stamp_map_view_cache" in s
    assert "_map_kind" in s
    assert "display_objects" in s
    assert "is_memory" in s
    assert "memory_for_display" in s
    assert "_next_decide_time" in s
    assert "used_square_space" in s
    assert "visible_cell_range" in s
    assert "decide" in s
    assert "俯视图" in s
    assert "迷雾" in s


def test_en_relnotes_1484_session_topics():
    s = _section_1484("en")
    assert "Ctrl+F2" in s
    assert "stamp_map_view_cache" in s
    assert "_map_kind" in s
    assert "display_objects" in s
    assert "is_memory" in s
    assert "memory_for_display" in s
    assert "_next_decide_time" in s
    assert "used_square_space" in s
    assert "visible_cell_range" in s
    assert "fog" in s.lower()


def test_es_it_pt_relnotes_1484_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1484(lang)
        assert "Ctrl+F2" in s, lang
        assert "stamp_map_view_cache" in s, lang
        assert "_map_kind" in s, lang
        assert "display_objects" in s, lang
        assert "is_memory" in s, lang
        assert "memory_for_display" in s, lang
        assert "_next_decide_time" in s, lang
        assert "used_square_space" in s, lang
        assert "visible_cell_range" in s, lang
