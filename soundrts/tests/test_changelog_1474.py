"""审计：1.4.7.4 — 本会话客户端音效/开局播报/训练线隔离的发行说明。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1474(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.7.4")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.3")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1474():
    # 1.4.7.4 notes remain after later bumps; current VERSION is owned by 1475+.
    assert "1.4.7.4" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1474_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.7.4") < src.index("1.4.7.3"), lang


def test_zh_relnotes_1474_session_topics():
    s = _section_1474("zh")
    assert "F 键" in s
    assert "voila" in s
    assert "order_ok" in s
    assert "proportion_" in s
    assert "line_upgrade" in s
    assert "暗黑弓箭手" in s
    assert "坐标" in s
    assert "5762" in s
    assert "副语音" in s


def test_en_relnotes_1474_session_topics():
    s = _section_1474("en")
    assert "F-key" in s
    assert "voila" in s
    assert "order_ok" in s
    assert "line_upgrade" in s
    assert "darkarcher" in s
    assert "opening square" in s.lower()
    assert "5762" in s
    assert "secondary voice" in s.lower()


def test_es_it_pt_relnotes_1474_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1474(lang)
        assert "voila" in s, lang
        assert "order_ok" in s, lang
        assert "line_upgrade" in s, lang
        assert "5762" in s, lang
        assert (
            "darkarcher" in s
            or "oscuro" in s.lower()
            or "negro" in s.lower()
        ), lang
