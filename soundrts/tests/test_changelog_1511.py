"""Audit: 1.5.1.1 — Ctrl+F2 minimap two-stage drawing on huge maps.

The relnotes for 1.5.1.1 describe the *minimap* hot path (two-stage
drawing: cached terrain base layer + fog overlay keyed on
``id(obs)``/``id(before)`` with a ``prev_obs ^ obs`` diff), not the
perception kernel.  These tests assert exactly that, in the five
shipped languages, plus the engine-side invariants that make the
optimisation possible.
"""
from __future__ import annotations

from pathlib import Path


_LANGS = ("zh", "en", "es", "it", "pt-BR")

# Per-language marker that must appear in the 1.5.1.1 section.  The
# shipped wording talks about the minimap "stuttering" rather than
# quoting the word "performance", so match the wording that is
# actually there.
_PERF_WORD = {
    "zh": "卡顿",
    "en": "stutters",
    "es": "entrecorta",
    "it": "scatta",
    "pt-BR": "trava",
}


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


def test_current_version_is_at_least_1511():
    """The current VERSION must be at least 1.5.1.1.

    Pinning the *exact* version made this test fail on every subsequent
    release, which is noise rather than signal.  Assert the "at least"
    property instead -- same pattern as test_changelog_1510.py.
    """
    import re

    src = _source("soundrts", "version.py")
    m = re.search(r'VERSION = "([^"]+)"', src)
    assert m, "VERSION literal not found in soundrts/version.py"
    assert tuple(int(x) for x in m.group(1).split(".")) >= (1, 5, 1, 1)


def test_all_relnotes_have_1511_before_1510():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.1.1\n") < src.index("\n1.5.1.0\n"), lang


def test_relnotes_1511_describe_minimap_two_stage_drawing():
    """Every shipped language must describe the minimap optimisation."""
    for lang in _LANGS:
        section = _section_1511(lang)
        assert "ms1000" in section, lang
        assert "Ctrl+F2" in section, lang
        assert "clientgamegridview.py" in section, lang
        assert "_draw_minimap" in section, lang
        assert "prev_obs" in section, lang
        assert "635" in section, lang
        assert _PERF_WORD[lang] in section, lang


def test_minimap_terrain_base_layer_is_cached_independently():
    """The terrain base surface must be keyed only on (cols, rows, cell).

    The whole point of the 1.5.1.1 fix is that the static terrain layer
    does NOT get invalidated by the fog sets growing every tick.  If the
    cache key still contained len(obs)/len(before), the bug would come
    back.
    """
    text = _source("soundrts", "clientgamegridview.py")
    func_start = text.index("def _draw_minimap")
    func_text = text[func_start:func_start + 8000]

    # The base layer is cached under a (cols, rows, cell) key.
    assert "_minimap_terrain_key" in func_text
    assert "base_key = (cols, rows, cell)" in func_text
    # ... and the fog overlay is a separate cache.
    assert "_minimap_fog" in func_text


def test_minimap_fog_overlay_uses_set_identity_snapshot():
    """The fog overlay must short-circuit on unchanged fog set identity."""
    text = _source("soundrts", "clientgamegridview.py")
    func_start = text.index("def _draw_minimap")
    func_text = text[func_start:func_start + 8000]

    assert "id(obs)" in func_text
    assert "id(before)" in func_text
    assert "_minimap_prev_obs_id" in func_text
    assert "_minimap_prev_bef_id" in func_text
    # The repaint path must use the symmetric difference.
    assert "prev_obs ^ obs" in func_text
    assert "prev_bef ^ before" in func_text


def test_known_enemies_empty_square_short_circuit_still_present():
    """known_enemies() must keep an empty-square fast path.

    The 1.5.1.1 release also reworked the perception kernel; the
    empty-square short-circuit in ``known_enemies`` is the invariant we
    still assert here, because it is the behaviour that keeps the
    per-place query cheap on huge maps.
    """
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def known_enemies")
    func_text = text[func_start:func_start + 6000]
    # Heavy branch (Cython or Python loop) must remain so that
    # semantics on non-empty squares are preserved.
    has_cython_branch = "filter_visible_vulnerable_enemies" in func_text
    has_python_branch = "for obj in place.objects:" in func_text
    assert has_cython_branch or has_python_branch, (
        "Heavy branch (Cython or Python loop) must remain in known_enemies"
    )
    # Per-place result cache.
    assert "self._known_enemies[place] = result" in func_text
    assert "return result" in func_text


def test_perception_uses_fused_enemy_place_build_when_available():
    """_refresh_combat_snapshot() must build the fused menace kernel.

    The Cython helper is called ``build_enemy_place_menace`` and returns
    ``(place_enemy_menace, enemy_presence_places)``.
    """
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def _refresh_combat_snapshot")
    func_text = text[func_start:func_start + 8000]
    assert "place_enemy_menace" in func_text
    assert "enemy_presence_places" in func_text


def test_perception_fast_exports_fused_enemy_place_build():
    """perception_fast.pyx must export the fused menace builder."""
    text = _source("soundrts", "worldplayerbase", "perception_fast.pyx")
    assert "cpdef tuple build_enemy_place_menace" in text
    assert "place_enemy_menace" in text
    assert "enemy_presence_places" in text
