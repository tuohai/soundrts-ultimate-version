"""审计：1.4.8.0 — 增益播报精度、诱野猪、资源4映射、经典副语音复制键。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1480(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.0")
    rest = text[start:]
    next_idx = rest.find("\n1.4.7.9")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1480():
    assert 'VERSION = "1.4.8.0"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1480_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.0") < src.index("1.4.7.9"), lang


def test_zh_relnotes_1480_session_topics():
    s = _section_1480("zh")
    assert "PRECISION" in s
    assert "mdg" in s
    assert "7000000" in s
    assert "is_huntable" in s
    assert "pursue_attacker" in s
    assert "herdable" in s
    assert "claimable" in s
    assert "资源4" in s
    assert "5508" in s
    assert "legacy_bindings.txt" in s
    assert "副语音" in s


def test_en_relnotes_1480_session_topics():
    s = _section_1480("en")
    assert "PRECISION" in s
    assert "mdg" in s
    assert "is_huntable" in s
    assert "pursue_attacker" in s
    assert "resource 4" in s
    assert "5508" in s
    assert "legacy_bindings.txt" in s
    assert "secondary" in s


def test_es_it_pt_relnotes_1480_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1480(lang)
        assert "PRECISION" in s, lang
        assert "is_huntable" in s, lang
        assert "pursue_attacker" in s, lang
        assert "5508" in s, lang
        assert "legacy_bindings.txt" in s, lang
        if lang == "es":
            assert "recurso 4" in s
            assert "voz secundaria" in s
        elif lang == "it":
            assert "risorsa 4" in s
            assert "voce secondaria" in s
        else:
            assert "recurso 4" in s
            assert "voz secundária" in s
