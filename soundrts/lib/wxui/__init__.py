"""wxPython UI shell: accessible text UI while Pygame keeps audio/logic.

Enable with config ``ui_backend = wx`` (default) or env ``SOUNDRTS_UI_BACKEND=wx``.
Set to ``pygame`` to use the classic tiny SDL window only.
"""

from .bootstrap import (
    append_message_log,
    clear_menu,
    consume_key_hit,
    end_cutscene_display,
    focus_braille_review,
    focus_game_input,
    focus_latest_message,
    focus_menu,
    focus_message_log,
    is_active,
    menu_is_active,
    msgparts_to_text,
    pump,
    set_frame_visible,
    set_latest_message,
    set_menu_choices,
    set_menu_entries,
    set_menu_selection,
    set_status,
    show_cutscene_line,
    shutdown,
    start,
    take_pending_list_index,
)
from .dialogs import browse_message_list, text_entry_dialog, yes_no_dialog

__all__ = [
    "append_message_log",
    "browse_message_list",
    "clear_menu",
    "consume_key_hit",
    "end_cutscene_display",
    "focus_braille_review",
    "focus_game_input",
    "focus_latest_message",
    "focus_menu",
    "focus_message_log",
    "is_active",
    "menu_is_active",
    "msgparts_to_text",
    "pump",
    "set_frame_visible",
    "set_latest_message",
    "set_menu_choices",
    "set_menu_entries",
    "set_menu_selection",
    "set_status",
    "show_cutscene_line",
    "shutdown",
    "start",
    "take_pending_list_index",
    "text_entry_dialog",
    "yes_no_dialog",
]
