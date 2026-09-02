"""审计：1.4.9.5 — 自动探索非强制；回车/Ctrl+回车；aoe2 鹰斥候 Auto Scout；靶场升级从马厩挪回。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1495(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.5")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.4")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1495():
    assert 'VERSION = "1.4.9.5"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1495_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.5") < src.index("1.4.9.4"), lang


def test_zh_relnotes_1495_session_topics():
    s = _section_1495("zh")
    assert "AutoExploreOrder" in s
    assert "auto_explore" in s
    assert "eagle_scout" in s
    assert "mangudai" in s
    assert "can_auto_explore" in s
    assert "crossbowman" in s or "弩手" in s
    assert "frank" in s.lower() or "法兰克" in s
    assert "briton" in s.lower() or "不列颠" in s
    assert "mods/aoe2/rules.txt" in s
    assert "enable_auto_explore" in s
    assert "auto_explore_imperative" in s
    assert "Ctrl" in s


def test_en_es_it_pt_relnotes_1495_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1495(lang)
        assert "AutoExploreOrder" in s, lang
        assert "auto_explore" in s, lang
        assert "eagle_scout" in s, lang
        assert "mangudai" in s, lang
        assert "can_auto_explore" in s, lang
        assert "mods/aoe2/rules.txt" in s, lang
        assert "crossbowman" in s or "arbalester" in s, lang
        assert "enable_auto_explore" in s, lang
        assert "auto_explore_imperative" in s, lang
        assert "Ctrl" in s, lang
