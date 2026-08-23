"""审计：1.4.7.9 — 领羊/抢羊播报文明与敌我；占领建筑播报名称与数量。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1479(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.7.9")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.8")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1479():
    # 1.4.7.9 notes remain after later bumps; current VERSION is owned by 1480+.
    assert "1.4.7.9" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1479_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.7.9") < src.index("1.4.7.8"), lang


def test_zh_relnotes_1479_session_topics():
    s = _section_1479("zh")
    assert "claimable" in s
    assert "已归属" in s
    assert "拜占庭" in s
    assert "敌人" in s
    assert "盟友" in s
    assert "迷雾" in s
    assert "被占领" in s
    assert "已占领" in s
    assert "no_number" in s
    assert "阵亡" in s


def test_en_relnotes_1479_session_topics():
    s = _section_1479("en")
    assert "claimable" in s
    assert "claimed" in s
    assert "Byzantines" in s
    assert "enemy" in s
    assert "ally" in s
    assert "fog" in s
    assert "occupied" in s
    assert "captured" in s
    assert "no_number" in s
    assert "death" in s


def test_es_it_pt_relnotes_1479_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1479(lang)
        assert "claimable" in s, lang
        assert "no_number" in s, lang
        if lang == "es":
            assert "bizantinos" in s
            assert "enemigo" in s
            assert "aliado" in s
            assert "ocupado" in s
            assert "capturado" in s
        elif lang == "it":
            assert "bizantini" in s
            assert "nemico" in s
            assert "alleato" in s
            assert "occupato" in s
            assert "catturato" in s
        else:
            assert "bizantinos" in s
            assert "inimigo" in s
            assert "aliado" in s
            assert "ocupado" in s
            assert "capturado" in s
