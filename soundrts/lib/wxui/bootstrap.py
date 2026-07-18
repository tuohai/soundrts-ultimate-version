"""Start / pump / shut down the wx UI shell."""

from __future__ import annotations

import sys
import threading
from typing import Callable, Optional

_app = None
_frame = None
_active = False
_key_hit = False
_key_hit_lock = threading.Lock()


def is_active() -> bool:
    return _active and _frame is not None


def mark_key_hit() -> None:
    global _key_hit
    with _key_hit_lock:
        _key_hit = True


def consume_key_hit() -> bool:
    global _key_hit
    with _key_hit_lock:
        hit = _key_hit
        _key_hit = False
        return hit


def _on_any_key() -> None:
    mark_key_hit()


def _on_close() -> None:
    # Post QUIT so blocking pygame loops exit cleanly.
    try:
        import pygame

        pygame.event.post(pygame.event.Event(pygame.QUIT))
    except Exception:
        pass


def start(title: str = "SoundRTS") -> bool:
    """Create the wx application and main frame. Safe to call once."""
    global _app, _frame, _active
    if _active:
        return True
    try:
        import wx
    except ImportError:
        from ..log import warning

        warning("wxPython is not installed; falling back to pygame UI")
        return False

    _app = wx.App(False)
    from .frame import MainFrame

    _frame = MainFrame(title=title, on_any_key=_on_any_key, on_close=_on_close)
    _active = True
    pump()
    return True


def shutdown() -> None:
    global _app, _frame, _active
    if not _active:
        return
    _active = False
    try:
        if _frame is not None:
            _frame.Destroy()
    except Exception:
        pass
    _frame = None
    try:
        if _app is not None:
            _app.Destroy()
    except Exception:
        pass
    _app = None


def set_frame_visible(visible: bool) -> None:
    """Show or hide the main wx frame (speech-channel toggle)."""
    if _frame is None:
        return
    try:
        if visible:
            _frame.Show()
            _frame.Raise()
            try:
                focus_game_input()
            except Exception:
                pass
        else:
            _frame.Hide()
    except Exception:
        pass


def pump() -> None:
    """Process pending wx events (call from pygame busy-wait loops)."""
    if not _active or _app is None:
        return
    try:
        _app.Yield(True)
    except Exception:
        pass


def set_status(text: str) -> None:
    if is_active() and _frame is not None:
        try:
            _frame.set_status(text)
        except Exception:
            pass


def append_message_log(text: str) -> None:
    if not text:
        return
    if is_active() and _frame is not None:
        try:
            _frame.append_log(text)
        except Exception:
            pass


def set_latest_message(text: str) -> None:
    """Update the persistent braille / review line without stealing focus."""
    if is_active() and _frame is not None:
        try:
            _frame.set_latest(text)
        except Exception:
            pass


def show_cutscene_line(text: str, focus: bool = True) -> None:
    """Put cut-scene / opening-objective text in the Latest TextCtrl."""
    if is_active() and _frame is not None:
        try:
            _frame.show_cutscene_line(text or "", focus=focus)
            pump()
        except Exception:
            pass


def end_cutscene_display() -> None:
    """Restore focus after a cut-scene / objective TextCtrl readout."""
    if is_active() and _frame is not None:
        try:
            _frame.end_cutscene_display()
            pump()
            # Prefer menu ListBox when a menu is open; otherwise silent key capture.
            if _frame.menu_is_active():
                _frame.focus_menu()
            else:
                _frame.focus_game_input()
            pump()
        except Exception:
            pass


def set_menu_choices(
    labels: list,
    selected: Optional[int] = None,
    *,
    force_focus: bool = True,
) -> None:
    if is_active() and _frame is not None:
        try:
            _frame.set_menu_choices(labels, selected, force_focus=force_focus)
        except Exception:
            pass


def set_menu_selection(index: Optional[int]) -> None:
    if is_active() and _frame is not None:
        try:
            _frame.set_menu_selection(index)
        except Exception:
            pass


def take_pending_list_index() -> Optional[int]:
    """Index chosen by mouse in the menu ListBox, if any."""
    if is_active() and _frame is not None:
        try:
            return _frame.take_pending_list_index()
        except Exception:
            return None
    return None


def clear_menu() -> None:
    if is_active() and _frame is not None:
        try:
            _frame.clear_menu()
        except Exception:
            pass


def menu_is_active() -> bool:
    """True when the accessible menu list has items (menus, not in-game)."""
    if is_active() and _frame is not None:
        try:
            return bool(_frame.menu_is_active())
        except Exception:
            return False
    return False


def focus_message_log() -> None:
    if is_active() and _frame is not None:
        _frame.focus_message_log()


def focus_latest_message() -> None:
    if is_active() and _frame is not None:
        _frame.focus_latest()


def focus_braille_review() -> None:
    """Cycle latest → message log → game input for braille touch-reading."""
    if is_active() and _frame is not None:
        _frame.focus_braille_review()


def focus_menu() -> None:
    if is_active() and _frame is not None:
        _frame.focus_menu()


def focus_game_input() -> None:
    if is_active() and _frame is not None:
        _frame.focus_game_input()


def set_menu_entries(entries, selected=None) -> None:
    """Compatibility helper: entries are (label_parts, expl_parts) tuples."""
    labels = []
    for entry in entries or []:
        if isinstance(entry, (list, tuple)) and len(entry) >= 1:
            label = msgparts_to_text(entry[0])
            if len(entry) > 1 and entry[1]:
                expl = msgparts_to_text(entry[1])
                if expl:
                    label = f"{label} — {expl}" if label else expl
            labels.append(label or "(item)")
        else:
            labels.append(msgparts_to_text(entry) or "(item)")
    set_menu_choices(labels, selected)


def msgparts_to_text(parts) -> str:
    """Collapse SoundRTS message parts to a single readable string.

    Pure SFX (e.g. ``when_moving_through`` 1092) become Sound objects with no
    TTS label — those must be omitted so the screen reader does not read the filename.
    """
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    try:
        from soundrts.lib.message import Message, is_text
        from soundrts.lib.sound_cache import sounds

        collapsed = Message(list(parts)).translate_and_collapse(remove_sounds=False)
        bits = []
        for p in collapsed:
            if p is None:
                continue
            if is_text(p):
                bits.append(p)
                continue
            name = getattr(p, "name", None)
            if name is None:
                continue
            key = "%s" % name
            label = sounds.text(key)
            if label:
                bits.append(label)
            elif not key.isdigit():
                # Named asset without TTS (e.g. peasant.ogg) — speak the id.
                bits.append(key)
            # else: numeric SFX-only id (1092, 1027, …) — skip
        return " ".join(bits).strip()
    except Exception:
        try:
            return " ".join(str(p) for p in parts)
        except Exception:
            return str(parts)
