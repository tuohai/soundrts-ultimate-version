"""审计：1.4.8.1 — 领羊距离 4 米 + 碰撞半径；数字存档/回放名按字面朗读。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1481(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.1")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.0")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1481():
    # 1.4.8.1 notes remain after later bumps; current VERSION is owned by 1482+.
    assert "1.4.8.1" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1481_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.1") < src.index("1.4.8.0"), lang


def test_zh_relnotes_1481_session_topics():
    s = _section_1481("zh")
    assert "claim_range 12000" in s
    assert "claim_range 4000" in s
    assert "radius" in s
    assert "175" in s
    assert "claimable" in s
    assert "领羊" in s
    assert "抢羊" in s
    assert "literal_text_msg" in s
    assert "tts.txt" in s
    assert "存档" in s
    assert "回放" in s


def test_en_relnotes_1481_session_topics():
    s = _section_1481("en")
    assert "claim_range 12000" in s
    assert "claim_range 4000" in s
    assert "radius" in s
    assert "175" in s
    assert "claimable" in s
    assert "collision" in s
    assert "Claim/steal" in s or "claim/steal" in s.lower()
    assert "literal_text_msg" in s
    assert "tts.txt" in s
    assert "save" in s.lower()
    assert "replay" in s.lower()


def test_es_it_pt_relnotes_1481_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1481(lang)
        assert "claim_range 12000" in s, lang
        assert "claim_range 4000" in s, lang
        assert "radius" in s, lang
        assert "175" in s, lang
        assert "claimable" in s, lang
        assert "literal_text_msg" in s, lang
        assert "tts.txt" in s, lang
        if lang == "es":
            assert "colisión" in s
            assert "Reclamar/robar" in s or "reclamar" in s
            assert "replay" in s.lower()
        elif lang == "it":
            assert "collisione" in s
            assert "Reclamo/furto" in s or "reclamo" in s
            assert "replay" in s.lower()
        else:
            assert "colisão" in s
            assert "Reivindicar/roubar" in s or "reivindicar" in s
            assert "replay" in s.lower()
