"""审计：1.4.6.3 — 边缘滚屏/滚轮缩放 + 自动更新写入发行说明 / 手册。"""
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


def test_version_is_1463():
    assert 'VERSION = "1.4.6.3"' in _source("soundrts", "version.py")


def test_zh_relnotes_1463_edge_scroll_and_wheel_zoom():
    src = _source("doc_src", "src", "zh", "relnotes.rst")
    section = _section_after_heading(src, "1.4.6.3")
    assert "边缘滚屏" in section
    assert "滚轮" in section
    assert "update_edge_scroll" in _source("soundrts", "clientgamegridview.py")
    assert "zoom_at_mouse" in section or "test_gridview_viewport.py" in section
    assert "clientgamegridview.py" in section
    assert "test_gridview_viewport.py" in section


def test_en_relnotes_1463_edge_scroll_and_wheel_zoom():
    src = _source("doc_src", "src", "en", "relnotes.rst")
    section = _section_after_heading(src, "1.4.6.3")
    assert "Edge scroll" in section
    assert "Mouse-wheel zoom" in section or "wheel" in section.lower()
    assert "test_gridview_viewport.py" in section
    assert "clientgamegridview.py" in section


def test_es_it_pt_relnotes_1463_mention_edge_or_wheel():
    for lang in ("es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        section = _section_after_heading(src, "1.4.6.3")
        assert "1.4.6.3" in src
        low = section.lower()
        assert "borde" in low or "bordi" in low or "borda" in low or "edge" in low
        assert "rueda" in low or "rotella" in low or "roda" in low or "wheel" in low


def test_zh_relnotes_1463_documents_auto_update():
    src = _source("doc_src", "src", "zh", "relnotes.rst")
    section = _section_after_heading(src, "1.4.6.3")
    assert "检查" in section and "更新" in section
    assert "check_updates_on_start" in section
    assert "auto_update.py" in section
    assert "test_auto_update.py" in section
    assert "tuohai/soundrts-ultimate-version" in section


def test_en_relnotes_1463_documents_auto_update():
    src = _source("doc_src", "src", "en", "relnotes.rst")
    section = _section_after_heading(src, "1.4.6.3")
    assert "GitHub" in section
    assert "check_updates_on_start" in section
    assert "auto_update.py" in section
    assert "test_auto_update.py" in section


def test_es_it_pt_relnotes_1463_documents_auto_update():
    markers = {
        "es": ("GitHub", "check_updates_on_start", "auto_update.py"),
        "it": ("GitHub", "check_updates_on_start", "auto_update.py"),
        "pt-BR": ("GitHub", "check_updates_on_start", "auto_update.py"),
    }
    for lang, needles in markers.items():
        src = _source("doc_src", "src", lang, "relnotes.rst")
        section = _section_after_heading(src, "1.4.6.3")
        for needle in needles:
            assert needle in section, f"{lang} missing {needle}"


def test_zh_en_manual_document_edge_scroll():
    zh = _source("doc_src", "src", "zh", "player", "manual.rst")
    en = _source("doc_src", "src", "en", "player", "manual.rst")
    assert "边缘滚屏" in zh or "主地图边缘" in zh
    assert "滚轮" in zh
    assert "edge" in en.lower()
    assert "wheel" in en.lower()
    assert "following the focused square" not in en


def test_manuals_document_auto_update():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        manual = _source("doc_src", "src", lang, "player", "manual.rst")
        assert "check_updates_on_start" in manual
        assert "tuohai/soundrts-ultimate-version" in manual


def test_getting_started_mentions_auto_update():
    zh = _source("doc_src", "src", "zh", "player", "getting-started.rst")
    en = _source("doc_src", "src", "en", "player", "getting-started.rst")
    assert "自动更新" in zh
    assert "check_updates_on_start" in zh
    assert "Automatic updates" in en or "updates" in en.lower()


def test_code_wires_edge_scroll_and_wheel():
    grid = _source("soundrts", "clientgamegridview.py")
    inp = _source("soundrts", "clientgame", "game_input_handler.py")
    nav = _source("soundrts", "clientgame", "game_navigation.py")
    assert "def update_edge_scroll" in grid
    assert "def zoom_at_mouse" in grid
    assert "MOUSEWHEEL" in inp
    assert "update_edge_scroll" in inp
    assert "center_view=False" in inp
    assert "center_view=True" in nav or "center_view" in nav
