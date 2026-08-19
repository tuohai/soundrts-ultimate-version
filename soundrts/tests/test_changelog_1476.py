"""审计：1.4.7.6 — aoe2 DE 文明奖励、领羊/抢羊、开局、多语言简介。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1476(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.7.6")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.5")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1476():
    assert 'VERSION = "1.4.7.6"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1476_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.7.6") < src.index("1.4.7.5"), lang


def test_zh_relnotes_1476_session_topics():
    s = _section_1476("zh")
    assert "Definitive Edition" in s
    assert "team_share_research" in s
    assert "herdable_steal_ignore_guards" in s
    assert "herdable_steal_protected" in s
    assert "6 村民" in s
    assert "8520" in s


def test_en_relnotes_1476_session_topics():
    s = _section_1476("en")
    assert "Definitive Edition" in s
    assert "team_share_research" in s
    assert "herdable_steal_ignore_guards" in s
    assert "6 villagers" in s.lower() or "6 villagers" in s
    assert "8520" in s
    assert "scout" in s.lower()


def test_es_it_pt_relnotes_1476_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1476(lang)
        assert "team_share_research" in s, lang
        assert "herdable_steal_protected" in s, lang
        assert "8520" in s, lang
        assert "starting_units" in s, lang
