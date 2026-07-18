"""Native Windows-style dialogs for confirmations and text entry."""

from __future__ import annotations

from typing import Optional


def _silence_game_voice() -> None:
    """Stop game TTS so the screen reader alone can announce the native dialog."""
    try:
        from soundrts.lib.voice import voice

        voice.silent_flush()
    except Exception:
        pass


def yes_no_dialog(prompt: str, title: str = "") -> Optional[bool]:
    """Show a standard Yes/No message box.

    Returns True (Yes), False (No), or None if wx UI is unavailable.
    """
    try:
        import wx

        from . import bootstrap
    except Exception:
        return None
    if not bootstrap.is_active():
        return None
    _silence_game_voice()
    parent = bootstrap._frame
    # Put the question in the window title so the screen reader announces it
    # once; keep the body empty when title was not given separately.
    caption = title or (prompt or "Confirm?")
    body = prompt if title else ""
    dlg = wx.MessageDialog(
        parent,
        body,
        caption,
        wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
    )
    try:
        result = dlg.ShowModal()
        return result == wx.ID_YES
    finally:
        dlg.Destroy()


def text_entry_dialog(
    prompt: str,
    default: str = "",
    title: Optional[str] = None,
    max_length: Optional[int] = None,
) -> Optional[str]:
    """Show a standard single-line edit dialog.

    The prompt becomes the window title (e.g. 「输入你的登录名」);
    the body above the edit box stays empty. Game TTS is stopped so only
    the screen reader speaks.

    Returns the entered string, or None if cancelled / wx unavailable.
    """
    try:
        import wx

        from . import bootstrap
    except Exception:
        return None
    if not bootstrap.is_active():
        return None
    _silence_game_voice()
    parent = bootstrap._frame
    caption = (title if title is not None else prompt) or ""
    dlg = wx.TextEntryDialog(parent, "", caption, default or "")
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return None
        text = dlg.GetValue()
        if max_length is not None and max_length >= 0:
            text = text[:max_length]
        return text
    finally:
        dlg.Destroy()


def browse_message_list(labels: list[str], title: str = "Statistics") -> bool:
    """Show stats / messages in a readonly multiline edit box.

    Arrow keys browse the text (same idea as cut-scene review). Enter / Esc
    closes. Used for end-of-game score summaries under the wx UI.

    Returns True if the dialog was shown, False if wx UI is unavailable or
    ``labels`` is empty.
    """
    try:
        import wx

        from . import bootstrap
        from .bootstrap import pump
    except Exception:
        return False
    if not bootstrap.is_active():
        return False
    lines = [((lab or "").strip()) for lab in (labels or ()) if (lab or "").strip()]
    if not lines:
        return False
    _silence_game_voice()
    parent = bootstrap._frame
    caption = (title or "").strip() or "Statistics"
    body = "\n".join(lines)

    dlg = wx.Dialog(
        parent,
        title=caption,
        style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
    )
    try:
        root = wx.BoxSizer(wx.VERTICAL)
        # No caption StaticText above the edit — that becomes the accessible
        # name (e.g. English help junk). Put the story in SetName instead.
        textctrl = wx.TextCtrl(
            dlg,
            value=body,
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_RICH2 | wx.HSCROLL,
        )
        textctrl.SetMinSize((520, 360))
        try:
            # Non-empty name so 争渡 speaks the body (empty →「panel 编辑框」).
            textctrl.SetName(body)
        except Exception:
            pass
        btn = wx.Button(dlg, wx.ID_OK, label="OK")
        root.Add(textctrl, 1, wx.ALL | wx.EXPAND, 8)
        root.Add(btn, 0, wx.ALL | wx.ALIGN_RIGHT, 8)
        dlg.SetSizerAndFit(root)
        dlg.SetMinSize((480, 400))

        def _on_key(event: wx.KeyEvent):
            code = event.GetKeyCode()
            if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_ESCAPE):
                dlg.EndModal(wx.ID_OK)
                return
            # Let the TextCtrl handle arrows / home / end for SR review.
            event.Skip()

        dlg.Bind(wx.EVT_CHAR_HOOK, _on_key)
        btn.Bind(wx.EVT_BUTTON, lambda e: dlg.EndModal(wx.ID_OK))

        textctrl.SetFocus()
        textctrl.SetInsertionPoint(0)
        textctrl.SetSelection(0, 0)
        pump()
        dlg.ShowModal()
        return True
    finally:
        try:
            dlg.Destroy()
        except Exception:
            pass
        try:
            from . import bootstrap as _b

            if _b.is_active():
                _b.focus_game_input()
                _b.pump()
        except Exception:
            pass
