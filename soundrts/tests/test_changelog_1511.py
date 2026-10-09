"""Audit: 1.5.1.1 — known_enemies empty-square fast path + fused enemy-menace kernel.
"""
from __future__ import annotations

from pathlib import Path


_LANGS = ("zh", "en", "es", "it", "pt-BR")


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1511(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.1\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.0\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_current_version_is_1512():
    """The current VERSION constant must equal the latest released version."""
    assert 'VERSION = "1.5.1.2"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1511_before_1510():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.1.1\n") < src.index("\n1.5.1.0\n"), lang


def test_zh_relnotes_1511_describes_fast_path_and_fused():
    section = _section_1511("zh")
    assert "known_enemies" in section
    assert "place.objects" in section
    assert "fused_enemy_place_build" in section
    assert "_refresh_combat_snapshot" in section
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in section
    assert "性能" in section


def test_en_relnotes_1511_describes_fast_path_and_fused():
    section = _section_1511("en")
    assert "known_enemies" in section
    assert "place.objects" in section
    assert "fused_enemy_place_build" in section
    assert "_refresh_combat_snapshot" in section
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in section
    assert "Performance" in section


def test_es_relnotes_1511_describes_fast_path_and_fused():
    section = _section_1511("es")
    assert "known_enemies" in section
    assert "place.objects" in section
    assert "fused_enemy_place_build" in section
    assert "_refresh_combat_snapshot" in section
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in section
    assert "Rendimiento" in section


def test_it_relnotes_1511_describes_fast_path_and_fused():
    section = _section_1511("it")
    assert "known_enemies" in section
    assert "place.objects" in section
    assert "fused_enemy_place_build" in section
    assert "_refresh_combat_snapshot" in section
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in section
    assert "Prestazioni" in section


def test_pt_br_relnotes_1511_describes_fast_path_and_fused():
    section = _section_1511("pt-BR")
    assert "known_enemies" in section
    assert "place.objects" in section
    assert "fused_enemy_place_build" in section
    assert "_refresh_combat_snapshot" in section
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in section
    assert "Desempenho" in section


def test_perception_known_enemies_has_empty_square_short_circuit():
    """known_enemies() must short-circuit on empty place.objects."""
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def known_enemies")
    func_text = text[func_start:func_start + 6000]
    # The empty-square fast path must appear BEFORE the heavy branch (Cython or Python).
    fast_idx = func_text.index("if not place.objects:")
    # Heavy branch: either the Cython dispatch or the Python for-loop must still exist
    # so that semantics on non-empty squares are preserved.
    has_cython_branch = "filter_visible_vulnerable_enemies" in func_text
    has_python_branch = "for obj in place.objects:" in func_text
    assert has_cython_branch or has_python_branch, (
        "Heavy branch (Cython or Python loop) must remain in known_enemies"
    )
    assert fast_idx < func_text.find(
        "filter_visible_vulnerable_enemies" if has_cython_branch else "for obj in place.objects:"
    ), (
        "Empty-square short-circuit must appear BEFORE the heavy branch"
    )
    # Must cache the empty list and return it.
    assert "self._known_enemies[place] = result" in func_text
    assert "return result" in func_text


def test_perception_uses_fused_enemy_place_build_when_available():
    """_refresh_combat_snapshot() must gate on _HAS_FAST_FUSED_ENEMY_BUILD."""
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def _refresh_combat_snapshot")
    func_text = text[func_start:func_start + 6000]
    # Gate pattern: import of _HAS_FAST_FUSED_ENEMY_BUILD plus an if-block.
    assert "_HAS_FAST_FUSED_ENEMY_BUILD" in func_text
    assert "fused_enemy_place_build" in func_text


def test_perception_fast_cython_has_fused_enemy_place_build():
    """perception_fast.pyx must export fused_enemy_place_build cpdef."""
    text = _source("soundrts", "worldplayerbase", "perception_fast.pyx")
    assert "cpdef tuple fused_enemy_place_build" in text
    # Must return place_enemy_menace, enemy_presence_places, live_presence.
    assert "place_enemy_menace" in text
    assert "enemy_presence_places" in text
    assert "live_presence" in text
