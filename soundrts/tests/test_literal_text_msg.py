"""用户输入文本应强制按字面朗读，不能当作 tts.txt ID 解析。"""
from __future__ import annotations

import os
import sys
import types
import warnings as _warnings

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

_saved_argv = sys.argv
sys.argv = [sys.argv[0]]
with _warnings.catch_warnings():
    _warnings.simplefilter("ignore")
    try:
        from soundrts.lib.msgs import LITERAL_TEXT_PREFIX, literal_text_msg
        from soundrts import clientmenu as _preload_clientmenu  # noqa: F401
    finally:
        sys.argv = _saved_argv


def test_literal_text_msg_wraps_non_empty_text():
    assert literal_text_msg("4373") == [LITERAL_TEXT_PREFIX + "4373"]
    assert literal_text_msg("玩家123") == [LITERAL_TEXT_PREFIX + "玩家123"]


def test_literal_text_msg_empty():
    assert literal_text_msg("") == []
    assert literal_text_msg(None) == []


def test_translate_sound_number_keeps_literal_prefix():
    from soundrts.lib.sound_cache import sounds

    result = sounds.translate_sound_number(LITERAL_TEXT_PREFIX + "4373")
    assert result == LITERAL_TEXT_PREFIX + "4373"


def test_input_text_announces_with_literal_prefix(monkeypatch):
    import pygame
    from pygame.locals import KEYDOWN, K_RETURN

    import soundrts.clientmenu as clientmenu

    announced = []

    monkeypatch.setattr(clientmenu, "voice", types.SimpleNamespace(
        item=lambda msg: announced.append(list(msg)),
        update=lambda: None,
    ))
    monkeypatch.setattr(pygame.event, "clear", lambda *a, **k: None)
    monkeypatch.setattr(pygame.key, "start_text_input", lambda: None)
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)

    events = [
        types.SimpleNamespace(type=KEYDOWN, key=0, unicode="4", mod=0),
        types.SimpleNamespace(type=KEYDOWN, key=K_RETURN, unicode="", mod=0),
    ]
    monkeypatch.setattr(
        pygame.event,
        "poll",
        lambda: events.pop(0) if events else types.SimpleNamespace(type=0),
    )

    result = clientmenu.input_text(max_length=10)
    assert result == "4"
    assert any(LITERAL_TEXT_PREFIX + "4" in item for sub in announced for item in sub)
