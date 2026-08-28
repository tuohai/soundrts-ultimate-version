"""审计：1.4.8.6 — aoe2 火枪兵；建筑详情文明壳；类型详情叠时代加成。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1486(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.8.6")
    rest = text[start:]
    next_idx = rest.find("\n1.4.8.5")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1486():
    assert 'VERSION = "1.4.8.6"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1486_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.8.6") < src.index("1.4.8.5"), lang


def test_zh_relnotes_1486_session_topics():
    s = _section_1486("zh")
    assert "hand_cannoneer" in s
    assert "chemistry" in s
    assert "can_train" in s
    assert "resolve_buildable_type" in s
    assert "briton_castle" in s or "aoe_castle" in s
    assert "_phase_bonus_pool" in s
    assert "Phase.apply_pool" in s


def test_en_relnotes_1486_session_topics():
    s = _section_1486("en")
    assert "hand_cannoneer" in s
    assert "chemistry" in s
    assert "can_train" in s
    assert "resolve_buildable_type" in s
    assert "_phase_bonus_pool" in s
    assert "Phase.apply_pool" in s


def test_es_it_pt_relnotes_1486_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1486(lang)
        assert "hand_cannoneer" in s, lang
        assert "chemistry" in s, lang
        assert "resolve_buildable_type" in s, lang
        assert "_phase_bonus_pool" in s, lang
        assert "Phase.apply_pool" in s, lang
