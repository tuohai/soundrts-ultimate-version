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
