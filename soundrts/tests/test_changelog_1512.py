"""Audit: 1.5.1.2 — the supported Python runtime is bumped to 3.12.8.

The 1.5.1.2 release was an interpreter-only bump: no engine source
changed, so the release notes describe the Python 3.12 specialising
adaptive interpreter, the measured tick-time improvement on cw1, and
the files that were realigned to the new runtime.

These tests assert that, in the five shipped languages, plus the
invariants that actually shipped with it (the runtime pinning in the
launcher / CI / build scripts).
"""
from __future__ import annotations

from pathlib import Path


_LANGS = ("zh", "en", "es", "it", "pt-BR")

# Per-language marker that must appear in the 1.5.1.2 section.
_PERF_WORD = {
    "zh": "性能",
    "en": "performance",
    "es": "rendimiento",
    "it": "prestazioni",
    "pt-BR": "desempenho",
}


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1512(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.2\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.1\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_all_relnotes_have_1512_before_1511():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("\n1.5.1.2\n") < src.index("\n1.5.1.1\n"), lang


def test_relnotes_1512_describe_python_312_upgrade():
    """Every shipped language must describe the interpreter bump."""
    for lang in _LANGS:
        section = _section_1512(lang)
        assert "3.12" in section, lang
        assert "3.12.8" in section, lang
        assert "Python" in section, lang
        assert "cx_Freeze" in section, lang
        assert "soundrts.bat" in section, lang
        assert "README.txt" in section, lang
        assert _PERF_WORD[lang] in section, lang


def test_relnotes_1512_mention_cw1_benchmark_numbers():
    """The cw1 measurement backing the speedup claim must be recorded."""
    for lang in _LANGS:
        section = _section_1512(lang)
        assert "cw1" in section, lang
        assert "44" in section, lang
        assert "41" in section, lang


def test_current_version_is_at_least_1512():
    """The current VERSION must be at least 1.5.1.2.

    Pinning the *exact* version made this test fail on every subsequent
    release, which is noise rather than signal.  Assert the "at least"
    property instead -- same pattern as test_changelog_1510.py.
    """
    import re

    src = _source("soundrts", "version.py")
    m = re.search(r'VERSION = "([^"]+)"', src)
    assert m, "VERSION literal not found in soundrts/version.py"
    assert tuple(int(x) for x in m.group(1).split(".")) >= (1, 5, 1, 2)


def test_player_init_initializes_last_positions_aggregate():
    """Player.__init__ must pre-initialise the perception move-check aggregate.

    The 1.5.1.0 optimisation gates the ``_last_unit_positions`` overwrite
    on an aggregate fold of unit positions.  The aggregate itself lives in
    ``_last_positions_hash`` (a sum of per-unit position hashes).
    """
    text = _source("soundrts", "worldplayerbase", "base.py")
    assert "self._last_positions_hash = 0" in text


def test_save_pickle_resets_last_positions_aggregate():
    """save_pickle must reset the aggregate when restoring a player."""
    text = _source("soundrts", "save_pickle.py")
    assert "player._last_positions_hash = 0" in text


def test_update_perception_uses_aggregate_for_move_check():
    """The perception hot path must gate on an aggregate position fold.

    The dict is only populated after the aggregate scan, and the
    overwrite of ``_last_unit_positions`` is gated on the aggregate
    having changed.
    """
    text = _source("soundrts", "worldplayerbase", "perception.py")
    func_start = text.index("def _update_perception_and_memory")
    func_text = text[func_start:func_start + 8000]

    assert "current_positions_hash" in func_text
    assert "_last_positions_hash" in func_text
    assert "current_positions_hash != self._last_positions_hash" in func_text
    # The aggregate fold must be computed before the dict is populated.
    aggregate_idx = func_text.index("current_positions_hash += pos_hash")
    dict_idx = func_text.index("current_unit_positions[unit.id] = pos_hash")
    assert aggregate_idx < dict_idx
