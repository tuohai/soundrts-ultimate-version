"""``input_string`` / ``input_text`` 撤销与重做（Ctrl+Z / Ctrl+Shift+Z）。"""
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
        import pygame
        from pygame.locals import KEYDOWN, K_RETURN, K_z, KMOD_CTRL, KMOD_SHIFT
        from soundrts import clientmenu as _preload_clientmenu  # noqa: F401
    finally:
        sys.argv = _saved_argv


def _make_event(event_type: int, **fields):
    e = types.SimpleNamespace()
    e.type = event_type
    for k, v in fields.items():
        setattr(e, k, v)
    return e


def _keydown(key: int, unicode: str = "", mod: int = 0) -> object:
    return _make_event(KEYDOWN, key=key, unicode=unicode, mod=mod)


@pytest.fixture
def stub_input_env(monkeypatch):
    queue: list = []

    def feed(events):
        queue.clear()
        queue.extend(events)

    def poll():
        if queue:
            return queue.pop(0)
        return _keydown(K_RETURN)

    monkeypatch.setattr(pygame.event, "poll", poll)
    monkeypatch.setattr(pygame.event, "clear", lambda *a, **k: None)
    monkeypatch.setattr(pygame.key, "get_mods", lambda: 0)
    monkeypatch.setattr(_preload_clientmenu, "voice", types.SimpleNamespace(
        item=lambda *a, **k: None,
        update=lambda: None,
    ))
    return feed


def test_input_string_undo_redo(stub_input_env):
    from soundrts.clientmenu import input_string

    feed = stub_input_env
    feed([
        _keydown(ord("a"), "a"),
        _keydown(ord("b"), "b"),
        _keydown(K_z, mod=KMOD_CTRL),
        _keydown(K_z, mod=KMOD_CTRL | KMOD_SHIFT),
    ])
    assert input_string(pattern=r"^[a-z]$") == "ab"


def test_input_text_ctrl_a_select_all(stub_input_env, monkeypatch):
    from soundrts.clientmenu import input_text

    feed = stub_input_env
    monkeypatch.setattr(pygame.key, "start_text_input", lambda: None)
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)

    from pygame.locals import K_a

    feed([_keydown(K_a, mod=KMOD_CTRL)])
    assert input_text(default="旧名", max_length=20) == "旧名"


def test_input_string_ctrl_v_paste(stub_input_env, monkeypatch):
    from soundrts.clientmenu import input_string

    feed = stub_input_env
    monkeypatch.setattr(
        "soundrts.clientmenu._clipboard_get_text",
        lambda: "RMG1:l:s:2:w:b:r:f:n:hi:x:6685",
    )

    from pygame.locals import K_v

    feed([_keydown(K_v, mod=KMOD_CTRL)])
    assert input_string(
        pattern=r"^[a-zA-Z0-9:./\-]$",
        max_length=80,
    ) == "RMG1:l:s:2:w:b:r:f:n:hi:x:6685"
