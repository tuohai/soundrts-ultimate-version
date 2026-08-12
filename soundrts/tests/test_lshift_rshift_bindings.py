"""LSHIFT / RSHIFT as distinct modifiers for voice-lib clipboard bindings."""
from __future__ import annotations

import pygame
from pygame.locals import KMOD_LSHIFT, KMOD_RSHIFT, KMOD_SHIFT

from soundrts.lib.bindings import Bindings, _normalized_key


class _Stub:
    def __init__(self):
        self.calls = []

    def cmd_voice_lib_copy(self, *args):
        self.calls.append(("copy", args))

    def cmd_voice_lib_append_copy(self, *args):
        self.calls.append(("append", args))

    def cmd_voice_lib_device(self, *args):
        self.calls.append(("device", args))


def test_normalized_key_accepts_lshift_rshift():
    assert _normalized_key("LSHIFT C")[0] == (0, 0, 0, 1, 0)
    assert _normalized_key("RSHIFT C")[0] == (0, 0, 0, 0, 1)
    assert _normalized_key("SHIFT C")[0] == (0, 0, 1, 0, 0)


def test_lshift_c_and_rshift_c_dispatch_distinct_commands():
    client = _Stub()
    b = Bindings()
    b.load(
        "LSHIFT C: voice_lib_copy primary\n"
        "RSHIFT C: voice_lib_copy secondary\n"
        "LSHIFT B: voice_lib_append_copy primary\n"
        "RSHIFT B: voice_lib_append_copy secondary\n",
        client,
    )

    # KMOD_SHIFT == KMOD_LSHIFT|KMOD_RSHIFT — use the side bit alone.
    left_c = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_c, mod=KMOD_LSHIFT, scancode=0
    )
    right_c = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_c, mod=KMOD_RSHIFT, scancode=0
    )
    left_b = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_b, mod=KMOD_LSHIFT, scancode=0
    )
    right_b = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_b, mod=KMOD_RSHIFT, scancode=0
    )

    assert b.process_keydown_event(left_c)
    assert b.process_keydown_event(right_c)
    assert b.process_keydown_event(left_b)
    assert b.process_keydown_event(right_b)
    assert client.calls == [
        ("copy", ("primary",)),
        ("copy", ("secondary",)),
        ("append", ("primary",)),
        ("append", ("secondary",)),
    ]


def test_generic_shift_still_matches_either_side():
    """SHIFT F9 (secondary voice) must still work with left or right Shift."""
    client = _Stub()
    b = Bindings()
    b.load("SHIFT F9: voice_lib_device 1", client)

    left = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_F9, mod=KMOD_LSHIFT, scancode=0
    )
    right = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_F9, mod=KMOD_RSHIFT, scancode=0
    )
    assert b.process_keydown_event(left)
    assert b.process_keydown_event(right)
    assert client.calls == [("device", ("1",)), ("device", ("1",))]


def test_commented_lshift_c_does_not_fire_when_only_rshift_bound():
    """If LSHIFT C is omitted (commented out), left Shift+C must not run."""
    client = _Stub()
    b = Bindings()
    b.load(
        "RSHIFT C: voice_lib_copy secondary\n"
        "RSHIFT B: voice_lib_append_copy secondary\n",
        client,
    )
    left_c = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_c, mod=KMOD_LSHIFT, scancode=0
    )
    left_b = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_b, mod=KMOD_LSHIFT, scancode=0
    )
    right_c = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_c, mod=KMOD_RSHIFT, scancode=0
    )
    assert not b.process_keydown_event(left_c)
    assert not b.process_keydown_event(left_b)
    assert b.process_keydown_event(right_c)
    assert client.calls == [("copy", ("secondary",))]


def test_handle_hotkey_still_supports_menu_shift_c_b(monkeypatch):
    """Menus keep hardcoded Shift+C/B via handle_hotkey; game uses bindings."""
    from soundrts.lib import voice_libs

    calls = []

    def _fake_copy(which, *, append=False):
        calls.append((which, append))
        return True

    monkeypatch.setattr(voice_libs, "copy_voice_info", _fake_copy)
    assert voice_libs.handle_hotkey(pygame.K_c, KMOD_LSHIFT)
    assert voice_libs.handle_hotkey(pygame.K_c, KMOD_RSHIFT)
    assert voice_libs.handle_hotkey(pygame.K_b, KMOD_LSHIFT)
    assert voice_libs.handle_hotkey(pygame.K_b, KMOD_RSHIFT)
    assert calls == [
        (voice_libs.PRIMARY, False),
        (voice_libs.SECONDARY, False),
        (voice_libs.PRIMARY, True),
        (voice_libs.SECONDARY, True),
    ]
