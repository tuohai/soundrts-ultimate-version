"""审计：1.4.9.6 — 电脑自适应大脑；补训克制兵；if_enemy / if_attacked；专家/噩梦默认 adaptive。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1496(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.6")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.5")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1496():
    assert 'VERSION = "1.4.9.6"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1496_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.6") < src.index("1.4.9.5"), lang
        assert "1.4.9.7" not in src.split("1.4.9.5")[0], lang


def test_zh_relnotes_1496_session_topics():
    s = _section_1496("zh")
    assert "brain" in s
    assert "adaptive" in s
    assert "if_enemy" in s
    assert "if_attacked" in s
    assert "ai_brain.py" in s
    assert "_follow_plan" in s
    assert "res/ai.txt" in s
    assert "inject_counter_pairs" in s
    assert "set_ai" in s
    assert "can_train" in s
    assert "choose_utility_goal" in s
    assert "_play_body" in s
    assert "utility" in s
    assert "assign_attack_groups" in s
    assert "_eventually_attack" in s
    assert "test_ai_attack_split.py" in s
    assert "tick_behavior_tree" in s
    assert "BEHAVIOR_TREE" in s
    assert "peel_home_guard" in s
    assert "assign_attack_groups_with_home" in s
    assert "_home_base_places" in s
    assert "_sticky_guard_order" in s
    assert "_home_guard_ids" in s
    assert "_tree_scout" in s
    assert "SCOUT_THEN_PRODUCE_MS" in s
    assert "_scout_sequence_started" in s


def test_en_es_it_pt_relnotes_1496_session_topics():
    for lang in ("en", "es", "it", "pt-BR"):
        s = _section_1496(lang)
        assert "brain" in s, lang
        assert "adaptive" in s, lang
        assert "if_enemy" in s, lang
        assert "if_attacked" in s, lang
        assert "ai_brain.py" in s, lang
        assert "_follow_plan" in s, lang
        assert "res/ai.txt" in s, lang
        assert "inject_counter_pairs" in s, lang
        assert "set_ai" in s, lang
        assert "can_train" in s, lang
        assert "choose_utility_goal" in s, lang
        assert "_play_body" in s, lang
        assert "utility" in s, lang
        assert "assign_attack_groups" in s, lang
        assert "_eventually_attack" in s, lang
        assert "test_ai_attack_split.py" in s, lang
        assert "tick_behavior_tree" in s, lang
        assert "BEHAVIOR_TREE" in s, lang
        assert "peel_home_guard" in s, lang
        assert "assign_attack_groups_with_home" in s, lang
        assert "_home_base_places" in s, lang
        assert "_sticky_guard_order" in s, lang
        assert "_home_guard_ids" in s, lang
        assert "_tree_scout" in s, lang
        assert "SCOUT_THEN_PRODUCE_MS" in s, lang
        assert "_scout_sequence_started" in s, lang


def test_vanilla_expert_nightmare_have_scout_jumps():
    src = _source("res", "ai.txt")
    assert "if_attacked goto exp_hold" in src
    assert "if_enemy dragon goto exp_air" in src
    assert "if_enemy knight goto exp_anti_cav" in src
    assert "if_attacked goto nm_hold" in src
    assert "if_enemy dragon goto nm_air" in src
    assert "if_enemy knight goto nm_anti_cav" in src
