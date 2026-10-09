"""审计：1.5.1.3 — 方格地形热路径 ms500（无界面对局提速）。"""
from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def test_version_is_1513():
    assert VERSION == "1.5.1.3"


def test_all_relnotes_have_1513_before_1509_in_all_five_languages():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.3\n" in src, (lang, "missing 1.5.1.3 header")
        assert src.index("\n1.5.1.3\n") < src.index("\n1.5.0.9\n"), lang


def test_zh_relnotes_1513_mentions_ms500_and_square_terrain():
    src = _source("doc_src", "src", "zh", "relnotes.rst")
    section_start = src.index("\n1.5.1.3\n")
    section_end = src.index("\n1.5.0.9\n")
    section = src[section_start:section_end]
    assert "ms500" in section
    assert "update_terrain" in section
    assert "Square" in section or "方格" in section
    # 列出 4 个改动文件
    for path in (
        "soundrts/world/world_game.py",
        "soundrts/world/world_objects.py",
        "soundrts/worldroom.py",
        "soundrts/version.py",
    ):
        assert path in section, path


def test_en_relnotes_1513_mentions_ms500_and_square_terrain():
    src = _source("doc_src", "src", "en", "relnotes.rst")
    section_start = src.index("\n1.5.1.3\n")
    section_end = src.index("\n1.5.0.9\n")
    section = src[section_start:section_end]
    assert "ms500" in section
    assert "update_terrain" in section
    assert "Square" in section
    assert "headless" in section or "fast-path" in section


def test_es_relnotes_1513_mentions_ms500_and_square_terrain():
    src = _source("doc_src", "src", "es", "relnotes.rst")
    section_start = src.index("\n1.5.1.3\n")
    section_end = src.index("\n1.5.0.9\n")
    section = src[section_start:section_end]
    assert "ms500" in section
    assert "update_terrain" in section
    assert "Square" in section or "casilla" in section


def test_it_relnotes_1513_mentions_ms500_and_square_terrain():
    src = _source("doc_src", "src", "it", "relnotes.rst")
    section_start = src.index("\n1.5.1.3\n")
    section_end = src.index("\n1.5.0.9\n")
    section = src[section_start:section_end]
    assert "ms500" in section
    assert "update_terrain" in section
    assert "Square" in section or "casella" in section


def test_ptbr_relnotes_1513_mentions_ms500_and_square_terrain():
    src = _source("doc_src", "src", "pt-BR", "relnotes.rst")
    section_start = src.index("\n1.5.1.3\n")
    section_end = src.index("\n1.5.0.9\n")
    section = src[section_start:section_end]
    assert "ms500" in section
    assert "update_terrain" in section
    assert "Square" in section or "casas" in section
