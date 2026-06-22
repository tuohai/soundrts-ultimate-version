"""审计：1.4.3.2 — no_number 无序号单位文档与变更日志。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_after_heading(text: str, heading: str) -> str:
    start = text.index(heading)
    rest = text[start + len(heading) :]
    next_idx = rest.find("\n1.4.")
    return rest if next_idx == -1 else rest[:next_idx]


def test_changelog_1432_documents_no_number():
    src = _source("更新日志.txt")
    assert "1.4.3.2" in src
    section = _section_after_heading(src, "1.4.3.2")
    assert "no_number" in section
    assert "无序号单位" in section
    section_131 = _section_after_heading(src, "1.4.3.1")
    assert "no_number" not in section_131


def test_zh_relnotes_1432_documents_no_number():
    src = _source("doc_src", "src", "zh", "relnotes.rst")
    assert "1.4.3.2" in src
    section = _section_after_heading(src, "1.4.3.2")
    assert "no_number" in section
    assert "无序号单位" in section


def test_en_relnotes_1432_documents_no_number():
    src = _source("doc_src", "src", "en", "relnotes.rst")
    assert "1.4.3.2" in src
    section = _section_after_heading(src, "1.4.3.2")
    assert "no_number" in section
    assert "Unnumbered units" in section


def test_modding_notes_1432_version():
    zh = _source("doc_src", "src", "zh", "modding.rst")
    en = _source("doc_src", "src", "en", "modding.rst")
    assert "1.4.3.2" in zh
    assert "no_number" in zh
    assert "1.4.3.2" in en
    assert "no_number" in en
