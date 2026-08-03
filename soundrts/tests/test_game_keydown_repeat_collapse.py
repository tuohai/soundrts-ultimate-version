"""Game loop must not browse multiple squares from one arrow-key press.

Regression (campaign ch.28 + cheatmode): pygame key-repeat queues several
KEYDOWNs while ``select_square`` is slow (full-map perception). The game loop
used to process every KEYDOWN in the batch, so a1→b1→c1→d1 from one press.
Menus already clear KEYDOWN; the game loop must collapse the fetched batch
and clear the queue after handling.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock

import pygame
from pygame.locals import KEYDOWN, K_RIGHT, K_LEFT, USEREVENT

from soundrts.clientgame import game_input_handler as gih


def _kd(key, mod=0):
    return pygame.event.Event(KEYDOWN, key=key, mod=mod, unicode="", scancode=0)


def test_collapse_keydown_repeats_keeps_first_per_key():
    events = [
        _kd(K_RIGHT),
        _kd(K_RIGHT),
        _kd(K_RIGHT),
        pygame.event.Event(USEREVENT),
        _kd(K_LEFT),
        _kd(K_LEFT),
    ]
    out = gih._collapse_keydown_repeats(events)
    assert [getattr(e, "key", None) for e in out if e.type == KEYDOWN] == [
        K_RIGHT,
        K_LEFT,
    ]
    assert sum(1 for e in out if e.type == USEREVENT) == 1


def test_collapse_preserves_non_keydown_order():
    a = pygame.event.Event(USEREVENT)
    b = _kd(K_RIGHT)
    c = pygame.event.Event(USEREVENT + 1)
    d = _kd(K_RIGHT)
    out = gih._collapse_keydown_repeats([a, b, c, d])
    assert out == [a, b, c]


def test_process_events_one_arrow_press_moves_one_square(monkeypatch):
    """Queued RIGHT repeats must not each invoke the binding."""
    calls = []

    class _Bindings:
        def process_keydown_event(self, e):
            calls.append(e.key)
            return True

    interface = types.SimpleNamespace(
        _falling_callbacks={},
        _zoom_input_mode=False,
        shortcut_mode=False,
        display_is_active=False,
        _bindings=_Bindings(),
        _process_keyboard_event=lambda e: False,
    )

    queued = [_kd(K_RIGHT), _kd(K_RIGHT), _kd(K_RIGHT)]
    cleared = []

    monkeypatch.setattr(pygame.event, "get", lambda: list(queued))
    monkeypatch.setattr(
        pygame.event, "clear", lambda types=None: cleared.append(types)
    )
    monkeypatch.setattr(gih, "voice", MagicMock())

    gih._process_events(interface)

    assert calls == [K_RIGHT]
    assert [KEYDOWN] in cleared


def test_process_events_clears_keydown_after_slow_handler(monkeypatch):
    """KEYDOWNs posted during a slow select_square must be discarded."""
    calls = []
    queue_after_handler = []

    class _Bindings:
        def process_keydown_event(self, e):
            calls.append(e.key)
            # Simulate key-repeat arriving while the handler runs.
            queue_after_handler.extend([_kd(K_RIGHT), _kd(K_RIGHT)])
            return True

    interface = types.SimpleNamespace(
        _falling_callbacks={},
        _zoom_input_mode=False,
        shortcut_mode=False,
        display_is_active=False,
        _bindings=_Bindings(),
        _process_keyboard_event=lambda e: False,
    )

    cleared = []

    monkeypatch.setattr(pygame.event, "get", lambda: [_kd(K_RIGHT)])
    monkeypatch.setattr(
        pygame.event,
        "clear",
        lambda types=None: (
            cleared.append(types),
            queue_after_handler.clear(),
        ),
    )
    monkeypatch.setattr(gih, "voice", MagicMock())

    gih._process_events(interface)

    assert calls == [K_RIGHT]
    assert [KEYDOWN] in cleared
    assert queue_after_handler == []
