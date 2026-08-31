"""审计：1.4.9.1 — CrazyMod 大厅/虫族；星际 AI/地图/SC2；封建进度；初级采集；成就首次重复。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1491(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.1")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.0")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1491():
    # 1.4.9.1 notes remain after later bumps; current VERSION is owned by 1.4.9.2+.
    assert "1.4.9.1" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1491_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.1") < src.index("1.4.9.0"), lang


def test_zh_relnotes_1491_session_topics():
    s = _section_1491("zh")
    assert "chatelet" in s
    assert "vermine_nm_loop" in s
    assert "larve" in s or "幼虫" in s
    assert "a_larve" in s
    assert "projectile_speed" in s
    assert "peasant" in s
    assert "mineral_field" in s
    assert "geyser" in s
    assert "SC2" in s or "星际 2" in s or "星际2" in s
    assert "jl1" in s
    assert "time_cost" in s
    assert "重复完成" in s
    assert "once_keys" in s
    assert "is_dynamic" in s
    assert "ensure_resources" in s
    assert "调色板" in s or "forest" in s


def test_en_relnotes_1491_session_topics():
    s = _section_1491("en")
    assert "chatelet" in s
    assert "vermine_nm_loop" in s
    assert "larva" in s.lower()
    assert "a_larve" in s
    assert "projectile_speed" in s
    assert "peasant" in s
    assert "mineral_field" in s
    assert "geyser" in s
    assert "SC2" in s
    assert "jl1" in s
    assert "time_cost" in s
    assert "repeat" in s.lower()
    assert "once_keys" in s
    assert "is_dynamic" in s
    assert "ensure_resources" in s
    assert "palette" in s.lower()


def test_es_it_pt_relnotes_1491_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1491(lang)
        assert "chatelet" in s, lang
        assert "vermine_nm_loop" in s, lang
        assert "a_larve" in s, lang
        assert "projectile_speed" in s, lang
        assert "peasant" in s, lang
        assert "mineral_field" in s, lang
        assert "geyser" in s, lang
        assert "SC2" in s, lang
        assert "jl1" in s, lang
        assert "time_cost" in s, lang
        assert "once_keys" in s, lang
        assert "addon_grants_train" in s, lang
        assert "is_dynamic" in s, lang
        assert "ensure_resources" in s, lang
