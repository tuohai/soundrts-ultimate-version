"""审计：1.4.9.2 — 弹跳；星际潜伏者/巨像穿透；弩炮沿线 50%。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1492(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.2")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.1")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1492():
    assert 'VERSION = "1.4.9.2"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1492_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.2") < src.index("1.4.9.1"), lang


def test_zh_relnotes_1492_session_topics():
    s = _section_1492("zh")
    assert "rdg_bounce" in s
    assert "bounce_decay" in s or "*_bounce_decay" in s
    assert "飞龙" in s or "mutalisk" in s.lower()
    assert "rdg_pierce_line" in s
    assert "潜伏者" in s or "lurker" in s.lower()
    assert "巨像" in s or "colossus" in s.lower()
    assert "rdg_pierce_decay" in s
    assert "50" in s
    assert "弩炮" in s or "scorpion" in s.lower()
    assert "hit_scale" in s
    assert "属性界面" in s
    assert "5800" in s or "msgparts" in s
    assert "rdg_pierce_line" in s and "pierce_width" in s and "pierce_decay" in s
    assert "rdg_bounce" in s and "bounce_range" in s
    assert "spawns_unit" in s
    assert "larva_spawn_time" in s
    assert "spawn_player_cap" in s
    assert "claimable" in s
    assert "can_herd" in s
    assert "aztec_eagle_scout" in s
    assert "eagle_warrior" in s
    assert "训练队列" in s
    assert "TrainOrder" in s


def test_en_relnotes_1492_session_topics():
    s = _section_1492("en")
    assert "rdg_bounce" in s
    assert "bounce_decay" in s or "*_bounce_decay" in s
    assert "mutalisk" in s.lower() or "glaive" in s.lower()
    assert "rdg_pierce_line" in s
    assert "lurker" in s.lower()
    assert "colossus" in s.lower()
    assert "rdg_pierce_decay" in s
    assert "50" in s
    assert "scorpion" in s.lower()
    assert "hit_scale" in s
    assert "attributes screen" in s.lower()
    assert "pasture" in s.lower() or "spawn" in s.lower()
    assert "pierce_width" in s and "pierce_decay" in s
    assert "bounce_range" in s
    assert "spawns_unit" in s
    assert "larva_spawn_time" in s
    assert "spawn_player_cap" in s
    assert "claimable" in s
    assert "can_herd" in s
    assert "aztec_eagle_scout" in s
    assert "eagle_warrior" in s
    assert "production queue" in s.lower()
    assert "TrainOrder" in s


def test_es_it_pt_relnotes_1492_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1492(lang)
        assert "rdg_bounce" in s, lang
        assert "rdg_pierce_line" in s, lang
        assert "lurker" in s.lower() or "Lurker" in s, lang
        assert "colossus" in s.lower() or "Coloso" in s or "Colosso" in s, lang
        assert "rdg_pierce_decay" in s, lang
        assert "50" in s, lang
        assert "hit_scale" in s, lang
        assert "scorpion" in s.lower() or "escorpión" in s.lower() or "scorpione" in s.lower() or "escorpião" in s.lower(), lang
        assert "5800" in s or "msgparts" in s, lang
        assert "pasture" in s.lower() or "pasto" in s.lower() or "pascolo" in s.lower() or "claimable" in s.lower(), lang
        assert "spawns_unit" in s, lang
        assert "larva_spawn_time" in s, lang
        assert "spawn_player_cap" in s, lang
        assert "can_herd" in s, lang
        assert "aztec_eagle_scout" in s, lang
        assert "eagle_warrior" in s, lang
        assert "TrainOrder" in s, lang


def test_modding_docs_cover_bounce_and_pierce_decay():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "mod", "modding.rst")
        assert "rdg_bounce" in src, lang
        assert "rdg_pierce_decay" in src, lang
