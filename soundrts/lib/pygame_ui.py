"""Pygame visual shell for menus and narrative (no wxPython).

Menus and cut-scenes draw on the SDL window. Blind play keeps TTS/keyboard;
sighted play gets a readable list and mouse hits.
"""

from __future__ import annotations

import pygame

from .screen import get_screen

# Preferred UI window when not fullscreen (classic 400x75 is too small).
UI_WINDOW_SIZE = (960, 640)

_fonts: dict[str, pygame.font.Font | None] = {}
_narrative_text = ""
_narrative_hint = ""
_narrative_active = False
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
        if len(choice) > 2 and choice[2]:
            extra = msgparts_to_display_text(choice[2])
            if extra:
                label = f"{label} — {extra}" if label else extra
        labels.append(label or "(item)")
    _menu_label_cache_key = key
    _menu_label_cache = labels
    return labels


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

    list_top = 64
    list_bottom = h - 48
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
        text = labels[i]
        # Truncate visually if needed
        while text and item_font.size(text)[0] > rect.width - 20:
            text = text[:-2]
        if text != labels[i] and text:
            text = text[:-1] + "…"
        img = item_font.render(text, True, color)
        surf.blit(img, (rect.x + 10, rect.y + (row_h - 2 - img.get_height()) // 2))
        y += row_h

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
