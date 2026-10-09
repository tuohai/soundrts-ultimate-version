"""Audit: 1.5.1.2 — _update_perception() move-check uses integer XOR fold
instead of per-unit dict.get + tuple compare.
"""
from __future__ import annotations

from pathlib import Path


_LANGS = ("zh", "en", "es", "it", "pt-BR")


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


def _section_asserts():
    return ("_update_perception" in _section_1512("zh")
            and "XOR" in _section_1512("zh"))


def test_zh_relnotes_1512_describes_xor_fold():
    section = _section_1512("zh")
    assert "_update_perception" in section
    assert "XOR" in section or "整数" in section
    assert "性能" in section


def test_en_relnotes_1512_describes_xor_fold():
    section = _section_1512("en")
    assert "_update_perception" in section
    assert "XOR" in section
    assert "Performance" in section


def test_es_relnotes_1512_describes_xor_fold():
    section = _section_1512("es")
    assert "_update_perception" in section
    assert "XOR" in section
    assert "Rendimiento" in section


def test_it_relnotes_1512_describes_xor_fold():
    section = _section_1512("it")
    assert "_update_perception" in section
    assert "XOR" in section
    assert "Prestazioni" in section


def test_pt_br_relnotes_1512_describes_xor_fold():
    section = _section_1512("pt-BR")
    assert "_update_perception" in section
    assert "XOR" in section
    assert "Desempenho" in section


def test_player_init_initializes_last_positions_xor():
    text = _source("soundrts", "worldplayerbase", "base.py")
    assert "self._last_positions_xor = 0" in text


def test_save_pickle_resets_last_positions_xor():
    text = _source("soundrts", "save_pickle.py")
    assert "player._last_positions_xor = 0" in text


def test_update_perception_uses_xor_for_move_check():
    text = _source("soundrts", "worldplayerbase", "perception.py")
    # The new XOR aggregate must be present.
    assert "current_positions_xor" in text
    assert "_last_positions_xor" in text
    # The XOR-vs-last comparison must drive the gate.
    needle = "current_positions_xor != self._last_positions_xor"
    assert needle in text


def test_current_version_is_1512():
    """The current VERSION constant must equal the latest released version."""
    assert 'VERSION = "1.5.1.2"' in _source("soundrts", "version.py")
