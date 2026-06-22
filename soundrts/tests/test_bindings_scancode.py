"""BACKQUOTE / QUOTE 绑定应使用物理 scancode，兼容 AZERTY 等布局。"""

import pygame

from soundrts.lib.bindings import Bindings


class _StubClient:
    def __init__(self):
        self.called = None

    def cmd_console(self, *args):
        self.called = ("console", args)

    def cmd_reload_parameters(self, *args):
        self.called = ("reload_parameters", args)


def test_backquote_matches_by_scancode_not_keycode():
    client = _StubClient()
    bindings = Bindings()
    bindings.load("BACKQUOTE: console", client)

    us_event = pygame.event.Event(
        pygame.KEYDOWN, key=pygame.K_BACKQUOTE, scancode=53, mod=0
    )
    assert bindings.process_keydown_event(us_event)
    assert client.called[0] == "console"

    client.called = None
    azerty_event = pygame.event.Event(
        pygame.KEYDOWN, key=178, scancode=53, mod=0
    )
    assert bindings.process_keydown_event(azerty_event)
    assert client.called[0] == "console"


def test_ctrl_backquote_uses_scancode_with_modifier():
    client = _StubClient()
    bindings = Bindings()
    bindings.load("CTRL BACKQUOTE: reload_parameters", client)

    event = pygame.event.Event(
        pygame.KEYDOWN, key=178, scancode=53, mod=pygame.KMOD_CTRL
    )
    assert bindings.process_keydown_event(event)
    assert client.called[0] == "reload_parameters"


def test_crlf_blank_lines_do_not_warn():
    import soundrts.lib.log as log

    client = _StubClient()
    bindings = Bindings()
    warnings = []
    log.warning = lambda fmt, *args: warnings.append(args)

    bindings.load("; comment\r\n\r\nBACKQUOTE: console\r\n", client)
    assert not warnings
    assert bindings.process_keydown_event(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKQUOTE, scancode=53, mod=0)
    )
