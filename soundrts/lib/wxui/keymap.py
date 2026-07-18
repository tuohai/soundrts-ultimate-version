"""Map wx key events to pygame-compatible KEYDOWN attributes."""

from __future__ import annotations

import pygame
import wx

# wx.WXK_* → pygame.K_*
_WXK_TO_PYGAME = {
    wx.WXK_BACK: pygame.K_BACKSPACE,
    wx.WXK_TAB: pygame.K_TAB,
    wx.WXK_RETURN: pygame.K_RETURN,
    wx.WXK_ESCAPE: pygame.K_ESCAPE,
    wx.WXK_SPACE: pygame.K_SPACE,
    wx.WXK_DELETE: pygame.K_DELETE,
    wx.WXK_START: pygame.K_HOME,  # rare
    wx.WXK_LEFT: pygame.K_LEFT,
    wx.WXK_UP: pygame.K_UP,
    wx.WXK_RIGHT: pygame.K_RIGHT,
    wx.WXK_DOWN: pygame.K_DOWN,
    wx.WXK_HOME: pygame.K_HOME,
    wx.WXK_END: pygame.K_END,
    wx.WXK_PAGEUP: pygame.K_PAGEUP,
    wx.WXK_PAGEDOWN: pygame.K_PAGEDOWN,
    wx.WXK_INSERT: pygame.K_INSERT,
    wx.WXK_NUMPAD_ENTER: pygame.K_KP_ENTER,
    wx.WXK_NUMPAD_ADD: pygame.K_KP_PLUS,
    wx.WXK_NUMPAD_SUBTRACT: pygame.K_KP_MINUS,
    wx.WXK_NUMPAD_MULTIPLY: pygame.K_KP_MULTIPLY,
    wx.WXK_NUMPAD_DIVIDE: pygame.K_KP_DIVIDE,
    wx.WXK_NUMPAD0: pygame.K_KP0,
    wx.WXK_NUMPAD1: pygame.K_KP1,
    wx.WXK_NUMPAD2: pygame.K_KP2,
    wx.WXK_NUMPAD3: pygame.K_KP3,
    wx.WXK_NUMPAD4: pygame.K_KP4,
    wx.WXK_NUMPAD5: pygame.K_KP5,
    wx.WXK_NUMPAD6: pygame.K_KP6,
    wx.WXK_NUMPAD7: pygame.K_KP7,
    wx.WXK_NUMPAD8: pygame.K_KP8,
    wx.WXK_NUMPAD9: pygame.K_KP9,
    wx.WXK_F1: pygame.K_F1,
    wx.WXK_F2: pygame.K_F2,
    wx.WXK_F3: pygame.K_F3,
    wx.WXK_F4: pygame.K_F4,
    wx.WXK_F5: pygame.K_F5,
    wx.WXK_F6: pygame.K_F6,
    wx.WXK_F7: pygame.K_F7,
    wx.WXK_F8: pygame.K_F8,
    wx.WXK_F9: pygame.K_F9,
    wx.WXK_F10: pygame.K_F10,
    wx.WXK_F11: pygame.K_F11,
    wx.WXK_F12: pygame.K_F12,
    wx.WXK_SHIFT: pygame.K_LSHIFT,
    wx.WXK_ALT: pygame.K_LALT,
    wx.WXK_CONTROL: pygame.K_LCTRL,
}

# SoundRTS binds BACKQUOTE/QUOTE by SDL scancode (layout-independent).
_PYGAME_KEY_TO_SCANCODE = {
    pygame.K_BACKQUOTE: 53,  # SDL_SCANCODE_GRAVE
    getattr(pygame, "K_QUOTE", 39): 52,  # SDL_SCANCODE_APOSTROPHE
}


def wx_mod_to_pygame(event: wx.KeyEvent) -> int:
    mod = 0
    if event.ControlDown():
        mod |= pygame.KMOD_CTRL
    if event.AltDown():
        mod |= pygame.KMOD_ALT
    if event.ShiftDown():
        # Do not OR KMOD_SHIFT (it equals LSHIFT|RSHIFT and would mark both).
        # Distinguish sides for Left/Right Shift+C; wx only has ShiftDown().
        try:
            import ctypes

            left = bool(ctypes.windll.user32.GetKeyState(0xA0) & 0x8000)  # VK_LSHIFT
            right = bool(ctypes.windll.user32.GetKeyState(0xA1) & 0x8000)  # VK_RSHIFT
            if left:
                mod |= pygame.KMOD_LSHIFT
            if right:
                mod |= pygame.KMOD_RSHIFT
            if not (left or right):
                mod |= pygame.KMOD_LSHIFT
        except Exception:
            mod |= pygame.KMOD_LSHIFT
    return mod


def wx_key_to_pygame(event: wx.KeyEvent) -> tuple[int, str]:
    """Return (pygame_key, unicode_char)."""
    code = event.GetKeyCode()
    if code in _WXK_TO_PYGAME:
        return _WXK_TO_PYGAME[code], ""
    # Printable ASCII / letters
    if 32 <= code <= 126:
        ch = chr(code)
        if ch.isalpha():
            # Always use pygame K_a..K_z (lowercase). Shift+letter must not
            # become ord('C') or handle_hotkey / K_c checks miss the event
            # (breaks Right Shift+C on the screen-reader channel).
            key = getattr(pygame, "K_" + ch.lower(), ord(ch.lower()))
            uni = ch.upper() if event.ShiftDown() else ch.lower()
            return key, uni
        return code, ch
    # Unicode from wx when available
    uni = event.GetUnicodeKey()
    if uni and uni >= 32:
        ch = chr(uni)
        if ch in ("`", "~"):
            return pygame.K_BACKQUOTE, ch
        if ch in ("'", '"'):
            return getattr(pygame, "K_QUOTE", ord("'")), ch
        if ch.isalpha():
            key = getattr(pygame, "K_" + ch.lower(), ord(ch.lower()))
            return key, ch.upper() if event.ShiftDown() else ch.lower()
        return uni, ch
    return code, ""


def post_pygame_keydown(event: wx.KeyEvent) -> None:
    """Inject a KEYDOWN into the pygame event queue."""
    key, uni = wx_key_to_pygame(event)
    mod = wx_mod_to_pygame(event)
    # Prefer unicode for grave/apostrophe (layout-independent physical key).
    if uni in ("`", "~"):
        key = pygame.K_BACKQUOTE
    elif uni in ("'", '"'):
        key = getattr(pygame, "K_QUOTE", key)
    scancode = _PYGAME_KEY_TO_SCANCODE.get(key, 0)
    try:
        pygame.event.post(
            pygame.event.Event(
                pygame.KEYDOWN,
                key=key,
                mod=mod,
                unicode=uni,
                scancode=scancode,
            )
        )
    except pygame.error:
        pass
