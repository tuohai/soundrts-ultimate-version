"""审计：1.4.9.7 — 飞行农民算陆地工人；电脑造好当前训练建筑后仍出兵；穿墙传送；单机失败后的房主警告；转化间隔掷骰。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1497(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.7")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.6")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1497():
    assert 'VERSION = "1.4.9.7"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1497_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.7") < src.index("1.4.9.6"), lang
        assert "1.4.9.8" not in src.split("1.4.9.6")[0], lang


def test_zh_relnotes_1497_session_topics():
    s = _section_1497("zh")
    assert "is_land_economy_worker" in s
    assert "_primary_worker_type_name" in s
    assert "_current_get_line_has_unpaid_production_building" in s
    assert "_defer_plan_get_token" in s
    assert "elemental_de_terre" in s
    assert "tour_du_feu" in s
    assert "keep" in s
    assert "castle" in s
    assert "test_crazymod_pra1_ai.py" in s
    assert "a_passe_muraille" in s
    assert "_execute_teleportation" in s
    assert "test_teleport_skill.py" in s
    assert "is_admin" in s
    assert "test_is_admin_after_defeat.py" in s
    assert "conversion_interval" in s
    assert "conversion_chance" in s
    assert "conversion_roll_params" in s
    assert "conversion_roll_after_interval" in s
    assert "conversion_miss" in s
    assert "conversion_fail_at_max" in s
    assert "test_conversion_interval_roll.py" in s
    assert "_worker_buildable_type_names" in s
    assert "_faction_peasant_type_name" in s
    assert "ouvriere_marcheuse" in s
    assert "mairie" in s


def test_en_es_it_pt_relnotes_1497_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1497(lang)
        assert "is_land_economy_worker" in s, lang
        assert "_primary_worker_type_name" in s, lang
        assert "_current_get_line_has_unpaid_production_building" in s, lang
        assert "_defer_plan_get_token" in s, lang
        assert "elemental_de_terre" in s, lang
        assert "tour_du_feu" in s, lang
        assert "keep" in s, lang
        assert "castle" in s, lang
        assert "test_crazymod_pra1_ai.py" in s, lang
        assert "a_passe_muraille" in s, lang
        assert "_execute_teleportation" in s, lang
        assert "test_teleport_skill.py" in s, lang
        assert "is_admin" in s, lang
        assert "test_is_admin_after_defeat.py" in s, lang
        assert "conversion_interval" in s, lang
        assert "conversion_chance" in s, lang
        assert "conversion_roll_params" in s, lang
        assert "conversion_roll_after_interval" in s, lang
        assert "conversion_miss" in s, lang
        assert "conversion_fail_at_max" in s, lang
        assert "test_conversion_interval_roll.py" in s, lang
        assert "_worker_buildable_type_names" in s, lang
        assert "_faction_peasant_type_name" in s, lang
        assert "ouvriere_marcheuse" in s, lang
        assert "mairie" in s, lang
