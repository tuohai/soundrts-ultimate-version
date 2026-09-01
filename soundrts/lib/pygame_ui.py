"""Pygame visual shell for menus and narrative (no wxPython).

Menus and cut-scenes draw on the SDL window. Blind play keeps TTS/keyboard;
sighted play gets a readable list and mouse hits.
"""

from __future__ import annotations

import sys

import pygame

from .screen import get_screen

# Preferred UI window when not fullscreen (classic 400x75 is too small).
UI_WINDOW_SIZE = (960, 640)

_fonts: dict[str, pygame.font.Font | None] = {}
_narrative_text = ""
_narrative_hint = ""
_narrative_active = False
_confirm_active = False
_confirm_yes_rect: pygame.Rect | None = None
_confirm_no_rect: pygame.Rect | None = None
_menu_item_rects: list[pygame.Rect] = []
_last_menu_key: tuple | None = None
_menu_label_cache_key = None
_menu_label_cache: list[str] = []


def msgparts_to_text(parts) -> str:
    """Collapse SoundRTS message parts to one readable string."""
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
                bits.append(key)
        return " ".join(bits).strip()
    except Exception:
        try:
            return " ".join(str(p) for p in parts)
        except Exception:
            return str(parts)


def msgparts_to_display_text(parts) -> str:
    """Fast labels for pygame menus — never scan campaign TTS globally.

    Map titles like ``['m1', 5012, 3001]`` must keep the literal ``m1`` and only
    resolve numeric ids from the **current** resource layer. Full
    ``msgparts_to_text`` / ``translate_sound_number`` can cost ~10ms per map
    via ``_global_lookup_text``, so an 80-map list freezes for ~0.8s.
    """
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    try:
        from soundrts.lib.msgs import LITERAL_TEXT_PREFIX, NB_ENCODE_SHIFT
        from soundrts.lib.sound_cache import sounds

        bits = []
        for p in parts:
            if p is None:
                continue
            if isinstance(p, str):
                if p.startswith(LITERAL_TEXT_PREFIX):
                    bits.append(p[len(LITERAL_TEXT_PREFIX) :])
                    continue
                # Map / literal labels (“m1”, “pm1”, …): never global-scan.
                if p and not p.isdigit():
                    bits.append(p)
                    continue
                key = p
            else:
                key = "%s" % p
            if not key:
                continue
            # Local layer only (no _global_lookup_text).
            label = sounds.text(key)
            if label:
                bits.append(label)
                continue
            if key.isdigit():
                n = int(key)
                if n >= NB_ENCODE_SHIFT:
                    bits.append(str(n - NB_ENCODE_SHIFT))
                # else: pure TTS id with no local text — omit
            else:
                bits.append(key)
        return " ".join(bits).strip()
    except Exception:
        return msgparts_to_text(parts)


def _menu_labels_for(choices) -> list[str]:
    """Cache display labels while the same choices list object is shown."""
    global _menu_label_cache_key, _menu_label_cache
    key = id(choices)
    if key == _menu_label_cache_key and len(_menu_label_cache) == len(choices or []):
        return _menu_label_cache
    labels = []
    for choice in choices or []:
        if not choice:
            labels.append("")
            continue
        label = msgparts_to_display_text(choice[0])
        labels.append(label or "(item)")
    _menu_label_cache_key = key
    _menu_label_cache = labels
    return labels


def resolve_choice_status(choice):
    """Third tuple item: frozen msgparts, or a callable for live status."""
    if not choice or len(choice) < 3:
        return None
    status = choice[2]
    if callable(status):
        try:
            status = status()
        except Exception:
            return None
    return status


def _menu_explanation_text(choice) -> str:
    status = resolve_choice_status(choice)
    if not status:
        return ""
    return msgparts_to_display_text(status)


# (font_id, max_width, text) -> fitted text; avoids O(n) font.size on long help rows.
_fit_text_cache: dict[tuple, str] = {}
_FIT_TEXT_CACHE_MAX = 256


def _fit_menu_text(font: pygame.font.Font, text: str, max_width: int) -> str:
    """Clip ``text`` to ``max_width`` pixels (ellipsis if clipped).

    Binary search: a 500+ char 语音库帮助 line costs ~O(log n) ``font.size``
    calls instead of one call per two characters (froze ↑↓ for ~1s each).
    """
    if not text:
        return ""
    if max_width <= 0:
        return "…"
    cache_key = (id(font), int(max_width), text)
    cached = _fit_text_cache.get(cache_key)
    if cached is not None:
        return cached
    if font.size(text)[0] <= max_width:
        _fit_text_cache[cache_key] = text
        return text
    ell = "…"
    ell_w = font.size(ell)[0]
    budget = max_width - ell_w
    if budget <= 0:
        _fit_text_cache[cache_key] = ell
        return ell
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font.size(text[:mid])[0] <= budget:
            lo = mid
        else:
            hi = mid - 1
    fitted = (text[:lo] + ell) if lo < len(text) else text
    if len(_fit_text_cache) >= _FIT_TEXT_CACHE_MAX:
        _fit_text_cache.clear()
    _fit_text_cache[cache_key] = fitted
    return fitted


def _pick_font(size: int, bold: bool = False) -> pygame.font.Font:
    key = f"{size}:{int(bold)}"
    cached = _fonts.get(key)
    if cached is not None:
        return cached
    # Prefer CJK-capable faces on Windows; fall back gracefully.
    names = (
        "microsoft yahei",
        "microsoft jhenghei",
        "simhei",
        "simsun",
        "nirmala ui",
        "segoe ui",
        "arial",
    )
    font = None
    for name in names:
        try:
            font = pygame.font.SysFont(name, size, bold=bold)
            if font is not None and font.get_height() > 0:
                # Prefer a face that can measure CJK at a sane width.
                probe = font.size("测")[0]
                if probe >= size // 2:
                    break
        except Exception:
            font = None
    if font is None:
        font = pygame.font.Font(None, size)
    _fonts[key] = font
    return font


def ensure_window_for_ui() -> None:
    """Grow the windowed SDL surface so menus/narrative fit."""
    from .. import config
    from . import screen as screen_mod

    try:
        from ..clientmedia import get_fullscreen

        if get_fullscreen():
            return
    except Exception:
        pass
    surf = get_screen()
    if surf is None:
        return
    w, h = surf.get_size()
    tw, th = UI_WINDOW_SIZE
    if w >= tw - 20 and h >= th - 20:
        return
    # Respect tiny debug windows only when explicitly tiny-dev and already ok.
    if getattr(config, "debug_mode", 0) and w <= 220 and h <= 220:
        tw, th = 800, 560
    try:
        screen_mod._screen = pygame.display.set_mode((tw, th))
    except Exception:
        pass


def raise_game_window() -> None:
    """Bring the SDL window to the foreground (Windows) so prompts are visible."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        info = pygame.display.get_wm_info()
        hwnd = info.get("window")
        if not hwnd:
            return
        user32 = ctypes.windll.user32
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        user32.SetForegroundWindow(hwnd)
    except Exception:
        pass


def narrative_is_active() -> bool:
    return _narrative_active


def show_narrative(text: str, hint: str | None = None) -> None:
    """Show story / objective text on the pygame surface."""
    global _narrative_text, _narrative_hint, _narrative_active
    ensure_window_for_ui()
    _narrative_text = (text or "").strip()
    if hint is None:
        hint = "Enter: next   Esc: skip"
    _narrative_hint = hint
    _narrative_active = True
    draw_narrative()


def end_narrative() -> None:
    global _narrative_text, _narrative_hint, _narrative_active
    _narrative_active = False
    _narrative_text = ""
    _narrative_hint = ""


def show_confirm(text: str, hint: str | None = None) -> None:
    """Show a yes/no prompt with on-screen text and clickable buttons."""
    global _narrative_text, _narrative_hint, _narrative_active, _confirm_active
    ensure_window_for_ui()
    raise_game_window()
    _narrative_text = (text or "").strip()
    if hint is None:
        hint = "Enter: Yes    Esc: No    or click a button"
    _narrative_hint = hint
    _narrative_active = True
    _confirm_active = True
    draw_confirm()


def end_confirm() -> None:
    global _confirm_active, _confirm_yes_rect, _confirm_no_rect
    _confirm_active = False
    _confirm_yes_rect = None
    _confirm_no_rect = None
    end_narrative()


def confirm_is_active() -> bool:
    return _confirm_active


def draw_confirm(*, flip: bool = True) -> None:
    """Paint confirm prompt + Yes/No buttons."""
    global _confirm_yes_rect, _confirm_no_rect, _narrative_hint
    if not _confirm_active:
        return
    surf = get_screen()
    if surf is None:
        return
    # Leave room at the bottom for Yes/No buttons.
    saved_hint = _narrative_hint
    _narrative_hint = ""
    try:
        w, h = surf.get_size()
        # Dim + text box without the usual bottom hint (buttons replace it).
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        surf.blit(overlay, (0, 0))

        margin = max(24, w // 20)
        box_w = w - margin * 2
        box_h = min(h - margin * 2 - 90, max(160, h // 2))
        box = pygame.Rect(margin, max(margin, (h - box_h - 90) // 2), box_w, box_h)
        pygame.draw.rect(surf, (28, 32, 40), box)
        pygame.draw.rect(surf, (180, 190, 210), box, 2)

        body_font = _pick_font(22, bold=False)
        max_text_w = box_w - 32
        lines = _wrap_lines(body_font, _narrative_text, max_text_w)
        y = box.y + 20
        line_h = body_font.get_height() + 4
        for line in lines:
            if y + line_h > box.bottom - 16:
                more = body_font.render("…", True, (200, 200, 200))
                surf.blit(more, (box.x + 16, y))
                break
            img = body_font.render(line, True, (235, 235, 240))
            surf.blit(img, (box.x + 16, y))
            y += line_h
    finally:
        _narrative_hint = saved_hint

    btn_font = _pick_font(20, bold=True)
    hint_font = _pick_font(15, bold=False)
    btn_w, btn_h = 140, 44
    gap = 24
    total = btn_w * 2 + gap
    x0 = (w - total) // 2
    y = h - 72
    yes_r = pygame.Rect(x0, y, btn_w, btn_h)
    no_r = pygame.Rect(x0 + btn_w + gap, y, btn_w, btn_h)
    pygame.draw.rect(surf, (46, 120, 72), yes_r)
    pygame.draw.rect(surf, (200, 220, 200), yes_r, 2)
    pygame.draw.rect(surf, (120, 50, 50), no_r)
    pygame.draw.rect(surf, (220, 180, 180), no_r, 2)
    yes_img = btn_font.render("Yes / 是", True, (245, 245, 245))
    no_img = btn_font.render("No / 否", True, (245, 245, 245))
    surf.blit(
        yes_img,
        (
            yes_r.x + (btn_w - yes_img.get_width()) // 2,
            yes_r.y + (btn_h - yes_img.get_height()) // 2,
        ),
    )
    surf.blit(
        no_img,
        (
            no_r.x + (btn_w - no_img.get_width()) // 2,
            no_r.y + (btn_h - no_img.get_height()) // 2,
        ),
    )
    if saved_hint:
        hint = hint_font.render(saved_hint[:80], True, (160, 170, 190))
        surf.blit(hint, (28, h - 28))
    _confirm_yes_rect = yes_r
    _confirm_no_rect = no_r
    if flip:
        pygame.display.flip()


def confirm_button_at(pos) -> bool | None:
    """Return True (Yes), False (No), or None if no button under ``pos``."""
    if not _confirm_active:
        return None
    x, y = pos
    if _confirm_yes_rect is not None and _confirm_yes_rect.collidepoint(x, y):
        return True
    if _confirm_no_rect is not None and _confirm_no_rect.collidepoint(x, y):
        return False
    return None


def show_status_banner(text: str, hint: str | None = None) -> None:
    """Show a short status line (checking / up to date / launching…)."""
    show_narrative(
        text,
        hint=hint if hint is not None else "Esc or Enter: dismiss",
    )


def _wrap_lines(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    if not text:
        return []
    lines: list[str] = []
    for paragraph in text.replace("\r\n", "\n").split("\n"):
        if not paragraph:
            lines.append("")
            continue
        # Prefer wrapping on spaces; for CJK, wrap by character.
        if " " in paragraph and not any("\u4e00" <= c <= "\u9fff" for c in paragraph[:8]):
            words = paragraph.split(" ")
            cur = ""
            for word in words:
                trial = word if not cur else f"{cur} {word}"
                if font.size(trial)[0] <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = word
            if cur:
                lines.append(cur)
        else:
            cur = ""
            for ch in paragraph:
                trial = cur + ch
                if font.size(trial)[0] <= max_width:
                    cur = trial
                else:
                    if cur:
                        lines.append(cur)
                    cur = ch
            if cur:
                lines.append(cur)
    return lines


def draw_narrative(*, flip: bool = True) -> None:
    """Paint the current narrative overlay (full window or in-game panel)."""
    if not _narrative_active:
        return
    surf = get_screen()
    if surf is None:
        return
    draw_narrative_onto(surf)
    if flip:
        pygame.display.flip()


def draw_narrative_onto(surf) -> None:
    """Blit narrative onto an existing surface without flipping."""
    if not _narrative_active or surf is None:
        return
    w, h = surf.get_size()
    # Dim background
    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    surf.blit(overlay, (0, 0))

    margin = max(24, w // 20)
    box_w = w - margin * 2
    box_h = min(h - margin * 2, max(180, h * 2 // 3))
    box = pygame.Rect(margin, (h - box_h) // 2, box_w, box_h)
    pygame.draw.rect(surf, (28, 32, 40), box)
    pygame.draw.rect(surf, (180, 190, 210), box, 2)

    body_font = _pick_font(20, bold=False)
    hint_font = _pick_font(16, bold=False)

    text_top = box.y + 20
    max_text_w = box_w - 32
    lines = _wrap_lines(body_font, _narrative_text, max_text_w)
    y = text_top
    line_h = body_font.get_height() + 4
    for line in lines:
        if y + line_h > box.bottom - 40:
            more = body_font.render("…", True, (200, 200, 200))
            surf.blit(more, (box.x + 16, y))
            break
        img = body_font.render(line, True, (235, 235, 240))
        surf.blit(img, (box.x + 16, y))
        y += line_h

    if _narrative_hint:
        hint = hint_font.render(_narrative_hint, True, (160, 170, 190))
        surf.blit(hint, (box.x + 16, box.bottom - hint.get_height() - 12))


def draw_menu(
    title_parts,
    choices,
    selected_index: int | None,
    hover_index: int | None = None,
) -> list[pygame.Rect]:
    """Draw a full-window menu list. Returns clickable item rects."""
    global _menu_item_rects, _last_menu_key
    ensure_window_for_ui()
    surf = get_screen()
    if surf is None:
        return []
    w, h = surf.get_size()
    surf.fill((18, 20, 26))

    title_font = _pick_font(26, bold=True)
    item_font = _pick_font(20, bold=False)
    hint_font = _pick_font(15, bold=False)

    title = msgparts_to_display_text(title_parts) if title_parts else "Menu"
    title_img = title_font.render(title[:120], True, (235, 238, 245))
    surf.blit(title_img, (28, 20))

    labels = _menu_labels_for(choices)

    detail = ""
    if selected_index is not None and 0 <= selected_index < len(choices or []):
        detail = _menu_explanation_text(choices[selected_index])
    detail_h = min(168, max(88, h // 5)) if detail else 0

    list_top = 64
    list_bottom = h - 48 - detail_h
    row_h = max(28, item_font.get_height() + 10)
    pad_x = 28
    visible = max(1, (list_bottom - list_top) // row_h)

    # Scroll so selection stays in view
    start = 0
    focus = selected_index if selected_index is not None else hover_index
    if focus is not None and focus >= visible:
        start = focus - visible + 1
    if focus is not None and focus < start:
        start = max(0, focus)
    start = max(0, min(start, max(0, len(labels) - visible)))

    rects: list[pygame.Rect | None] = [None] * len(labels)
    y = list_top
    for i in range(start, min(len(labels), start + visible)):
        rect = pygame.Rect(pad_x, y, w - pad_x * 2, row_h - 2)
        rects[i] = rect
        is_sel = selected_index is not None and i == selected_index
        is_hov = hover_index is not None and i == hover_index
        if is_sel:
            pygame.draw.rect(surf, (50, 90, 140), rect)
        elif is_hov:
            pygame.draw.rect(surf, (40, 48, 62), rect)
        else:
            pygame.draw.rect(surf, (28, 32, 40), rect)
        pygame.draw.rect(surf, (70, 78, 95), rect, 1)
        color = (255, 240, 180) if is_sel else (220, 224, 230)
        text = _fit_menu_text(item_font, labels[i], rect.width - 20)
        img = item_font.render(text, True, color)
        surf.blit(img, (rect.x + 10, rect.y + (row_h - 2 - img.get_height()) // 2))
        y += row_h

    if detail:
        box = pygame.Rect(pad_x, list_bottom + 8, w - pad_x * 2, detail_h - 16)
        pygame.draw.rect(surf, (24, 28, 36), box)
        pygame.draw.rect(surf, (90, 110, 140), box, 1)
        body_font = _pick_font(18, bold=False)
        lines = _wrap_lines(body_font, detail, box.width - 20)
        ty = box.y + 8
        line_h = body_font.get_height() + 3
        for line in lines:
            if ty + line_h > box.bottom - 6:
                more = body_font.render("…", True, (200, 200, 200))
                surf.blit(more, (box.x + 10, ty))
                break
            img = body_font.render(line, True, (220, 228, 238))
            surf.blit(img, (box.x + 10, ty))
            ty += line_h

    hint = hint_font.render(
        "↑↓ / click: select   Enter / double-click: confirm   Esc: back",
        True,
        (140, 150, 170),
    )
    surf.blit(hint, (28, h - 32))
    pygame.display.flip()

    _menu_item_rects = [r for r in rects if r is not None]
    # Keep parallel index map: store full list with None holes replaced by empty
    _menu_item_rects = []
    for r in rects:
        if r is None:
            _menu_item_rects.append(pygame.Rect(0, 0, 0, 0))
        else:
            _menu_item_rects.append(r)
    _last_menu_key = (title, tuple(labels), selected_index, hover_index, start)
    return list(_menu_item_rects)


def menu_index_at(pos) -> int | None:
    """Return choice index under mouse, or None."""
    x, y = pos
    for i, rect in enumerate(_menu_item_rects):
        if rect.width > 0 and rect.collidepoint(x, y):
            return i
    return None


def clear_menu_view() -> None:
    global _menu_item_rects, _last_menu_key, _menu_label_cache_key, _menu_label_cache
    _menu_item_rects = []
    _last_menu_key = None
    _menu_label_cache_key = None
    _menu_label_cache = []
