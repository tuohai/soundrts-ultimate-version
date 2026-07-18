"""Accessible main window: menu list + message log + key capture."""

from __future__ import annotations

import wx

from .keymap import post_pygame_keydown


class _QuietAccessible(wx.Accessible):
    """Keep focus sinks from being announced as bare 'panel' / '客户端'."""

    def __init__(self, window, name: str = ""):
        super().__init__(window)
        self._name = name

    def GetName(self, childId):
        if childId == wx.ACC_SELF:
            return (wx.ACC_OK, self._name)
        return super().GetName(childId)

    def GetRole(self, childId):
        if childId == wx.ACC_SELF:
            # STATICTEXT is quieter than PANEL/CLIENT under some screen readers (zh: 「客户端」).
            return (wx.ACC_OK, wx.ROLE_SYSTEM_STATICTEXT)
        return super().GetRole(childId)

    def GetState(self, childId):
        if childId == wx.ACC_SELF:
            return (wx.ACC_OK, 0)
        return super().GetState(childId)


class _InvisibleToSRAccessible(wx.Accessible):
    """Visible on screen, omitted from the screen-reader tree."""

    def GetName(self, childId):
        if childId == wx.ACC_SELF:
            return (wx.ACC_OK, "")
        return super().GetName(childId)

    def GetState(self, childId):
        if childId == wx.ACC_SELF:
            return (wx.ACC_OK, wx.ACC_STATE_SYSTEM_INVISIBLE)
        return super().GetState(childId)


class _KeyCapturePanel(wx.Panel):
    """Invisible focus target that forwards keys to the pygame event queue."""

    def __init__(self, parent, on_any_key=None):
        super().__init__(parent, style=wx.WANTS_CHARS)
        self._on_any_key = on_any_key
        self.SetBackgroundColour(parent.GetBackgroundColour())
        self.SetName("")
        self.SetAccessible(_QuietAccessible(self, ""))
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)
        # Keep a tiny size so it can receive focus without eating layout.
        self.SetMinSize((1, 1))

    def _braille_hotkey(self, event: wx.KeyEvent) -> bool:
        """Ctrl+B / Ctrl+Shift+B → braille review; handled here because this
        panel swallows keys before the frame hook when it has focus."""
        code = event.GetKeyCode()
        if code not in (ord("B"), ord("b")) or not event.ControlDown():
            return False
        frame = self.GetTopLevelParent()
        if self._on_any_key:
            self._on_any_key()
        if event.ShiftDown():
            getattr(frame, "focus_message_log", lambda: None)()
        else:
            getattr(frame, "focus_braille_review", lambda: None)()
        return True

    def _on_char_hook(self, event: wx.KeyEvent):
        # Braille hotkeys only here. KEY_DOWN posts to pygame once — posting in
        # both CHAR_HOOK and KEY_DOWN would double every key.
        if self.HasFocus() and self._braille_hotkey(event):
            return
        event.Skip()

    def _on_key_down(self, event: wx.KeyEvent):
        if self.HasFocus():
            if self._braille_hotkey(event):
                return
            if self._on_any_key:
                self._on_any_key()
            post_pygame_keydown(event)
            return
        event.Skip()


class MainFrame(wx.Frame):
    """Primary accessible UI for SoundRTS (screen reader / braille friendly)."""

    def __init__(self, title: str, on_any_key=None, on_close=None):
        super().__init__(None, title=title, size=(900, 700))
        self._on_close = on_close
        self._on_any_key = on_any_key
        self._menu_labels: list[str] = []
        self._suppress_menu_event = False
        self._pending_list_index: int | None = None
        self._cutscene_display = False

        panel = wx.Panel(self)
        panel.SetName("")
        panel.SetAccessible(_QuietAccessible(panel, ""))
        root = wx.BoxSizer(wx.VERTICAL)

        self.status = wx.TextCtrl(
            panel,
            value=title,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL,
        )
        self.status.SetMinSize((-1, 48))
        self.status.SetName("Status")

        # Latest line: cut-scenes + braille review (Ctrl+B).
        # No caption text — a label like "Latest announcement" becomes the
        # accessible name and 争渡 speaks it before 编辑框/正文.
        # Do not SetName("") / custom Accessible either: empty name makes
        # 争渡 say「panel 编辑框」and skip the value until the user arrows.
        self.latest = wx.TextCtrl(
            panel,
            value="",
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL,
        )
        self.latest.SetMinSize((-1, 140))

        self.menu_list = wx.ListBox(
            panel,
            style=wx.LB_SINGLE | wx.LB_NEEDED_SB,
            name="Menu",
        )
        self.menu_list.SetMinSize((-1, 220))

        self.message_log = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL,
            name="Message log",
        )
        self.message_log.SetMinSize((-1, 280))

        help_line = wx.StaticText(
            panel,
            label=(
                "Ctrl+B: braille review (latest)  |  "
                "Ctrl+Shift+B: message log  |  "
                "Esc: back to game input  |  "
                "Arrows in log scroll for screen reader / braille"
            ),
        )
        # Sighted hint only — if this sits above a TextCtrl, 争渡 uses it as the
        # edit box name (exactly the bug we hit with 「Latest announcement」).
        help_line.SetAccessible(_InvisibleToSRAccessible(help_line))

        # Key capture sits at the top visually as a 1px strip but is the default focus.
        self.key_capture = _KeyCapturePanel(panel, on_any_key=on_any_key)

        root.Add(self.key_capture, 0, wx.EXPAND)
        root.Add(help_line, 0, wx.ALL | wx.EXPAND, 4)
        root.Add(wx.StaticText(panel, label="Status"), 0, wx.LEFT | wx.TOP, 4)
        root.Add(self.status, 0, wx.EXPAND | wx.ALL, 4)
        # Empty / SR-hidden caption so it cannot become 「Latest announcement」.
        latest_label = wx.StaticText(panel, label="")
        latest_label.SetAccessible(_InvisibleToSRAccessible(latest_label))
        root.Add(latest_label, 0, wx.LEFT | wx.TOP, 4)
        root.Add(self.latest, 0, wx.EXPAND | wx.ALL, 4)
        root.Add(wx.StaticText(panel, label="Menu"), 0, wx.LEFT | wx.TOP, 4)
        root.Add(self.menu_list, 1, wx.EXPAND | wx.ALL, 4)
        root.Add(wx.StaticText(panel, label="Message log"), 0, wx.LEFT | wx.TOP, 4)
        root.Add(self.message_log, 2, wx.EXPAND | wx.ALL, 4)

        self._panel = panel

        panel.SetSizer(root)
        self.Bind(wx.EVT_CLOSE, self._on_close_event)
        self.Bind(wx.EVT_CHAR_HOOK, self._on_frame_char_hook)
        self.menu_list.Bind(wx.EVT_LISTBOX, self._on_menu_listbox)
        self.menu_list.Bind(wx.EVT_LISTBOX_DCLICK, self._on_menu_activate)
        self.menu_list.Bind(wx.EVT_KEY_DOWN, self._on_menu_key)

        self.Centre()
        self.Show()
        self.focus_game_input()

    def _on_close_event(self, event):
        if self._on_close:
            self._on_close()
        event.Skip()

    def _on_frame_char_hook(self, event: wx.KeyEvent):
        code = event.GetKeyCode()
        # Ctrl+B / Ctrl+Shift+B: braille review (works even when classic legacy
        # bindings are active, and without requiring the F10 game menu).
        if code in (ord("B"), ord("b")) and event.ControlDown():
            if self._on_any_key:
                self._on_any_key()
            if event.ShiftDown():
                self.focus_message_log()
            else:
                self.focus_braille_review()
            return
        # Cut-scene on latest: Enter / Esc advance / skip; arrows browse text.
        if self._cutscene_display and self.latest.HasFocus():
            if self._on_any_key:
                self._on_any_key()
            if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE):
                post_pygame_keydown(event)
                return
            event.Skip()
            return
        # Esc from latest / message log: return to silent game key capture.
        # Do NOT steal Esc from the menu list — pygame must handle submenu back.
        if code == wx.WXK_ESCAPE and (
            self.message_log.HasFocus() or self.latest.HasFocus()
        ):
            self.focus_game_input()
            return
        # When latest or log has focus, let TextCtrl handle arrows (braille pan).
        if self.message_log.HasFocus() or self.latest.HasFocus():
            if self._on_any_key:
                self._on_any_key()
            event.Skip()
            return
        # Menu list: pygame Menu is the only selection authority. Never Skip, or
        # the native ListBox also moves and screen-reader/game cursors desync.
        if self.menu_list.HasFocus():
            if self._on_any_key:
                self._on_any_key()
            post_pygame_keydown(event)
            return
        event.Skip()

    def _on_menu_listbox(self, event):
        if self._suppress_menu_event:
            return
        # Mouse/touch changed the highlight — remember it so the next menu pump
        # can align the game cursor (keyboard path never relies on this).
        self._pending_list_index = self.menu_list.GetSelection()
        event.Skip()

    def _on_menu_activate(self, event):
        # Double-click = confirm current item
        self._pending_list_index = self.menu_list.GetSelection()
        fake = wx.KeyEvent(wx.wxEVT_KEY_DOWN)
        fake.m_keyCode = wx.WXK_RETURN
        post_pygame_keydown(fake)
        event.Skip()

    def _on_menu_key(self, event: wx.KeyEvent):
        # Backup path if CHAR_HOOK did not consume the key. Still no Skip:
        # native ListBox must not move independently of pygame.
        if self._on_any_key:
            self._on_any_key()
        post_pygame_keydown(event)

    def take_pending_list_index(self) -> int | None:
        idx = getattr(self, "_pending_list_index", None)
        self._pending_list_index = None
        if idx is None or idx < 0:
            return None
        return idx

    def focus_game_input(self):
        self.key_capture.SetFocus()

    def show_cutscene_line(self, text: str, focus: bool = True):
        """Put story text in latest and optionally focus it for review.

        争渡: empty accessible name →「panel 编辑框」and no body until arrows.
        「Latest announcement」as name was the old unwanted prefix.
        Set the accessible name to the story itself (not an English caption),
        and do not select-all (that would speak name + value twice).
        """
        self._cutscene_display = True
        text = (text or "").strip()
        try:
            # Non-empty name so focus speech includes the body; not a caption.
            self.latest.SetName(text)
        except Exception:
            pass
        self.latest.ChangeValue(text)
        if focus:
            self.latest.SetFocus()
            self.latest.SetInsertionPoint(0)
            self.latest.SetSelection(0, 0)
        else:
            self.key_capture.SetFocus()

    def end_cutscene_display(self):
        """Leave cut-scene review mode; restore game key-capture focus."""
        self._cutscene_display = False
        try:
            if self.latest.HasFocus():
                self.latest.SetSelection(0, 0)
                self.latest.SetInsertionPoint(0)
            self.latest.SetName("")
        except Exception:
            pass
        self.key_capture.SetFocus()

    def focus_latest(self):
        """Focus the latest-announcement field so braille can linger on it."""
        self.latest.SetFocus()
        end = self.latest.GetLastPosition()
        self.latest.SetInsertionPoint(0)
        self.latest.SetSelection(0, end)

    def focus_message_log(self):
        self.message_log.SetFocus()
        end = self.message_log.GetLastPosition()
        self.message_log.SetInsertionPoint(end)

    def focus_braille_review(self):
        """Cycle: latest → message log → game input (for touch-reading)."""
        if self.latest.HasFocus():
            self.focus_message_log()
        elif self.message_log.HasFocus():
            self.focus_game_input()
        else:
            self.focus_latest()

    def focus_menu(self):
        if self.menu_list.GetCount():
            self.menu_list.SetFocus()

    def set_status(self, text: str):
        self.status.ChangeValue(text or "")

    def set_latest(self, text: str):
        """Update the latest-announcement line for braille / screen-reader review."""
        text = (text or "").strip()
        if not text:
            return
        reviewing = self.latest.HasFocus()
        self.latest.ChangeValue(text)
        if reviewing:
            end = self.latest.GetLastPosition()
            self.latest.SetInsertionPoint(0)
            self.latest.SetSelection(0, end)

    def append_log(self, text: str):
        text = (text or "").strip()
        if not text:
            return
        self.set_latest(text)
        # Avoid flooding identical consecutive lines
        last = self.message_log.GetLineText(self.message_log.GetNumberOfLines() - 1)
        if last == text:
            return
        was_at_end = (
            self.message_log.GetInsertionPoint() >= self.message_log.GetLastPosition() - 1
        )
        if self.message_log.GetLastPosition() > 0:
            self.message_log.AppendText("\n" + text)
        else:
            self.message_log.AppendText(text)
        # Cap size roughly (~200 messages worth)
        max_chars = 80000
        if self.message_log.GetLastPosition() > max_chars:
            self.message_log.Remove(0, self.message_log.GetLastPosition() - max_chars)
        if was_at_end and not self.message_log.HasFocus():
            self.message_log.ShowPosition(self.message_log.GetLastPosition())

    def _apply_menu_selection(self, index: int | None, *, force_focus: bool):
        """Keep ListBox highlight + keyboard focus aligned with game choice_index."""
        if not self.menu_list.GetCount():
            return
        if index is None or index < 0:
            # No game cursor yet — do not pretend item 0 is selected.
            if self.menu_list.GetSelection() != wx.NOT_FOUND:
                self.menu_list.SetSelection(wx.NOT_FOUND)
            if force_focus:
                self.focus_menu()
            return
        index = max(0, min(index, self.menu_list.GetCount() - 1))
        if self.menu_list.GetSelection() != index:
            self.menu_list.SetSelection(index)
        self.menu_list.EnsureVisible(index)
        if force_focus or not self.menu_list.HasFocus():
            # Re-focus so the screen reader announces the real selected row, not a stale one.
            self.menu_list.SetFocus()

    def set_menu_choices(
        self,
        labels: list[str],
        selected: int | None = None,
        *,
        force_focus: bool = True,
    ):
        self._menu_labels = list(labels)
        self._pending_list_index = None
        self._suppress_menu_event = True
        try:
            self.menu_list.Set(labels)
            self._apply_menu_selection(selected, force_focus=force_focus)
        finally:
            self._suppress_menu_event = False

    def set_menu_selection(self, index: int | None):
        self._suppress_menu_event = True
        try:
            self._apply_menu_selection(index, force_focus=False)
        finally:
            self._suppress_menu_event = False

    def clear_menu(self):
        self._suppress_menu_event = True
        try:
            self.menu_list.Clear()
            self._menu_labels = []
            self._pending_list_index = None
            self.focus_game_input()
        finally:
            self._suppress_menu_event = False

    def menu_is_active(self) -> bool:
        """True while a Menu ListBox is populated (SR should read the list)."""
        return bool(self._menu_labels) or self.menu_list.GetCount() > 0
