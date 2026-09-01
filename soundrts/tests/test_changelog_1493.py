"""审计：1.4.9.3 — 联机旁观 id、追帧播报、开局镜头、大厅公开房间。"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1493(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("1.4.9.3")
    rest = text[start:]
    next_idx = rest.find("\n1.4.9.2")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_1493():
    assert 'VERSION = "1.4.9.3"' in _source("soundrts", "version.py")


def test_all_relnotes_have_1493_heading():
    for lang in ("zh", "en", "es", "it", "pt-BR"):
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert src.index("1.4.9.3") < src.index("1.4.9.2"), lang


def test_zh_relnotes_1493_session_topics():
    s = _section_1493("zh")
    assert "旁观" in s
    assert "get_next_id" in s
    assert "pure_spectator" in s
    assert "all_orders" in s
    assert "_create_spectator_player" in s
    assert "test_multiplayer_spectate" in s
    assert "YOU_ARE_SPECTATING" in s
    assert "_initial_observer_place" in s
    assert "方向键" in s or "PageUp" in s
    assert "spectator_joined" in s
    assert "ROOM_LIST" in s or "房间列表" in s
    assert "test_open_rooms_lobby" in s
    assert "password" in s.lower() or "密码" in s
    assert "可加入或旁观" in s
    assert "voice.alert" in s
    assert "WaitingToSpectateMenu" in s


def test_en_relnotes_1493_session_topics():
    s = _section_1493("en")
    assert "spectat" in s.lower()
    assert "get_next_id" in s
    assert "pure_spectator" in s
    assert "all_orders" in s
    assert "_create_spectator_player" in s
    assert "test_multiplayer_spectate" in s
    assert "YOU_ARE_SPECTATING" in s
    assert "_initial_observer_place" in s
    assert "arrow" in s.lower() or "PageUp" in s
    assert "spectator_joined" in s
    assert "ROOM_LIST" in s or "room list" in s.lower()
    assert "test_open_rooms_lobby" in s
    assert "password" in s.lower()
    assert "joined or spectated" in s
    assert "voice.alert" in s
    assert "WaitingToSpectateMenu" in s


def test_es_it_pt_relnotes_1493_session_topics():
    for lang in ("es", "it", "pt-BR"):
        s = _section_1493(lang)
        assert "get_next_id" in s, lang
        assert "pure_spectator" in s, lang
        assert "all_orders" in s, lang
        assert "_create_spectator_player" in s, lang
        assert "test_multiplayer_spectate" in s, lang
        assert "YOU_ARE_SPECTATING" in s, lang
        assert "_initial_observer_place" in s, lang
        assert "PageUp" in s, lang
        assert "spectator_joined" in s, lang
        assert "test_open_rooms_lobby" in s, lang
        assert "password" in s.lower() or "senha" in s.lower() or "contraseña" in s.lower(), lang
        assert "voice.alert" in s, lang
        assert "WaitingToSpectateMenu" in s, lang
        assert (
            "espectador" in s.lower()
            or "spettatore" in s.lower()
            or "espectador" in s.lower()
        ), lang
