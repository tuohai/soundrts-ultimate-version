"""审计：1.4.9.4 — 开局后无法加入；房间列表 maps / invitations；默认游戏速度。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1494(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.4")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.3")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1494():
    # 1.4.9.4 notes remain after later bumps; current VERSION is owned by 1.4.9.5+.
    assert "1.4.9.4" in _source("doc_src", "src", "zh", "relnotes.rst")


def test_all_relnotes_have_1494_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.4") < src.index("1.4.9.3"), lang


def test_zh_relnotes_1494_session_topics():
    s = _section_1494("zh")
    assert "GAME_ALREADY_STARTED" in s
    assert "无法加入" in s
    assert "game_already_started" in s
    assert "cmd_register" in s
    assert "invitations" in s
    assert "srv_maps" in s
    assert "list_rooms" in s
    assert "RoomListMenu" in s
    assert "DEFAULT_GAME_SPEED" in s
    assert "默认游戏速度" in s
    assert "default_game_speed_menu" in s
    assert "DISPLAY_TOGGLE" in s
    assert "speech_enabled" in s


def test_en_relnotes_1494_session_topics():
    s = _section_1494("en")
    assert "GAME_ALREADY_STARTED" in s
    assert "game_already_started" in s
    assert "cmd_register" in s
    assert "invitations" in s
    assert "srv_maps" in s
    assert "list_rooms" in s
    assert "RoomListMenu" in s
    assert "DEFAULT_GAME_SPEED" in s
    assert "default_game_speed_menu" in s
    assert "DISPLAY_TOGGLE" in s
    assert "speech_enabled" in s


def test_es_it_pt_relnotes_1494_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1494(lang)
        assert "GAME_ALREADY_STARTED" in s, lang
        assert "game_already_started" in s, lang
        assert "cmd_register" in s, lang
        assert "invitations" in s, lang
        assert "srv_maps" in s, lang
        assert "list_rooms" in s, lang
        assert "RoomListMenu" in s, lang
        assert "DEFAULT_GAME_SPEED" in s, lang
        assert "default_game_speed_menu" in s, lang
        assert "DISPLAY_TOGGLE" in s, lang
        assert "speech_enabled" in s, lang
