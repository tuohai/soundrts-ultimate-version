"""Ctrl+F2：图标命令卡 + 生产队列。

- 优先加载 ``ui/icons/<name>.png``（有则用真图）
- 否则程序生成色块+字母图标
- 点击逻辑同前：复用 orders / validate / cancel
"""

from __future__ import annotations

import io
import os

import pygame

from ..lib.screen import get_screen

# 布局：右下角命令卡（类似传统 RTS）
_ICON = 48
_QICON = 32
_GAP = 4
_PAD = 8
_COLS = 5
_ROWS = 3
_LABEL_H = 22
_QUEUE_H = _QICON + _PAD

_KW_COLORS = {
    "train": (52, 118, 68),
    "build": (68, 98, 148),
    "research": (118, 88, 158),
    "advance": (148, 108, 52),
    "upgrade_to": (138, 112, 58),
    "change_to": (128, 100, 70),
    "cancel_training": (148, 52, 52),
    "cancel_upgrading": (148, 52, 52),
    "cancel_changing": (148, 52, 52),
    "cancel_building": (148, 52, 52),
    "stop": (110, 60, 60),
    "rallying_point": (70, 120, 140),
    "attack": (160, 55, 50),
    "patrol": (90, 110, 70),
    "repair": (70, 130, 120),
    "gather": (120, 110, 50),
    "default": (55, 60, 72),
}

_icon_cache = {}  # (key, size) -> Surface
_png_miss = set()  # keys already checked missing


def _voice_to_text(parts):
    if not parts:
        return ""
    if isinstance(parts, str):
        return parts.strip()
    try:
        from ..lib.message import Message, is_text
        from ..lib.msgs import LITERAL_TEXT_PREFIX, NB_ENCODE_SHIFT, localize_voice_msg
        from ..lib.sound_cache import sounds

        collapsed = Message(
            list(localize_voice_msg(list(parts)))
        ).translate_and_collapse(remove_sounds=False)
        bits = []
        for p in collapsed:
            if p is None:
                continue
            if is_text(p):
                bits.append(p)
                continue
            if isinstance(p, int):
                if p >= NB_ENCODE_SHIFT:
                    bits.append(str(p - NB_ENCODE_SHIFT))
                else:
                    label = sounds.text(str(p))
                    if label:
                        bits.append(label)
                continue
            if isinstance(p, str):
                if p.startswith(LITERAL_TEXT_PREFIX):
                    bits.append(p[len(LITERAL_TEXT_PREFIX) :])
                else:
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
            return " ".join(str(p) for p in parts).strip()
        except Exception:
            return str(parts)


def _short_label(parts, max_len=18):
    text = _voice_to_text(parts) or "?"
    text = " ".join(text.replace(",", " ").split())
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _ensure_fonts(interface):
    if getattr(interface, "_hud_font", None) is not None:
        return
    interface._hud_font = pygame.font.SysFont("arial", 13, bold=True)
    interface._hud_font_small = pygame.font.SysFont("arial", 11, bold=False)
    if interface._hud_font.get_height() == 0:
        interface._hud_font = pygame.font.SysFont("consolas", 13, bold=True)
    if interface._hud_font_small.get_height() == 0:
        interface._hud_font_small = pygame.font.SysFont("consolas", 11)


def _letter_from_key(key, title_text=""):
    for src in (key, title_text):
        if not src:
            continue
        for ch in str(src):
            if ch.isalnum():
                return ch.upper()
    return "?"


def _kw_color(keyword):
    return _KW_COLORS.get(keyword, _KW_COLORS["default"])


def _load_png_icon(key, size):
    """从资源包 ``ui/icons/<key>.png`` 加载；找不到返回 None。"""
    if not key or key in _png_miss:
        return None
    cache_key = ("png", key, size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    try:
        from ..lib.resource import res

        candidates = (
            "ui/icons/%s.png" % key,
            "ui/icons/%s.PNG" % key,
            "ui/icons/%s.jpg" % key,
        )
        for rel in candidates:
            for package, path in res.paths(rel, localize=False):
                try:
                    if hasattr(package, "has_file") and not package.has_file(path):
                        if not (hasattr(package, "isfile") and package.isfile(path)):
                            continue
                except Exception:
                    pass
                try:
                    with package.open_binary(path) as f:
                        data = f.read()
                    surf = pygame.image.load(io.BytesIO(data)).convert_alpha()
                    if surf.get_width() != size or surf.get_height() != size:
                        surf = pygame.transform.smoothscale(surf, (size, size))
                    _icon_cache[cache_key] = surf
                    return surf
                except Exception:
                    continue
        for rel in candidates:
            local = os.path.join("res", rel.replace("/", os.sep))
            if os.path.isfile(local):
                try:
                    surf = pygame.image.load(local).convert_alpha()
                    if surf.get_width() != size or surf.get_height() != size:
                        surf = pygame.transform.smoothscale(surf, (size, size))
                    _icon_cache[cache_key] = surf
                    return surf
                except Exception:
                    pass
    except Exception:
        pass
    _png_miss.add(key)
    return None


def _make_generated_icon(key, keyword, title_text, size):
    cache_key = ("gen", key, keyword, title_text[:8], size)
    if cache_key in _icon_cache:
        return _icon_cache[cache_key]
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = _kw_color(keyword)
    pygame.draw.rect(surf, color, (0, 0, size, size), border_radius=6)
    pygame.draw.rect(
        surf,
        (
            min(255, color[0] + 40),
            min(255, color[1] + 40),
            min(255, color[2] + 40),
        ),
        (2, 2, size - 4, size - 4),
        1,
        border_radius=5,
    )
    letter = _letter_from_key(key, title_text)
    font_size = max(14, size * 22 // 48)
    font = pygame.font.SysFont("arial", font_size, bold=True)
    if font.get_height() == 0:
        font = pygame.font.SysFont("consolas", font_size, bold=True)
    ts = font.render(letter, True, (245, 248, 255))
    surf.blit(ts, ((size - ts.get_width()) // 2, (size - ts.get_height()) // 2 - 1))
    pygame.draw.rect(surf, (20, 22, 28), (0, size - 5, size, 5))
    pygame.draw.rect(
        surf,
        (
            min(255, color[0] + 60),
            min(255, color[1] + 60),
            min(255, color[2] + 60),
        ),
        (4, size - 4, size - 8, 2),
    )
    _icon_cache[cache_key] = surf
    return surf


def get_icon(key, keyword="default", title_text="", size=_ICON):
    """真图优先，否则生成。"""
    key = (key or keyword or "default").strip()
    png = _load_png_icon(key, size)
    if png is not None:
        return png
    if key != keyword:
        png = _load_png_icon(keyword, size)
        if png is not None:
            return png
    return _make_generated_icon(key, keyword or "default", title_text, size)


def _order_icon_key(order_view):
    return getattr(order_view, "type", None) or getattr(
        getattr(order_view, "cls", None), "keyword", "default"
    )


def _queue_unit(interface):
    for uid in interface.group or ():
        ev = interface.dobjets.get(uid)
        if ev is None:
            continue
        model = getattr(ev, "model", ev)
        orders = getattr(model, "orders", None) or []
        if orders:
            return ev, model, orders
    if interface.group:
        uid = interface.group[0]
        ev = interface.dobjets.get(uid)
        if ev is not None:
            model = getattr(ev, "model", ev)
            return ev, model, getattr(model, "orders", None) or []
    return None, None, []


def _order_label(world_order, interface=None):
    try:
        from ..clientgameentity.base import _order_title_msg

        return _short_label(_order_title_msg(world_order, interface), max_len=18)
    except Exception:
        kw = getattr(world_order, "keyword", "?")
        typ = getattr(getattr(world_order, "type", None), "type_name", None) or ""
        return ("%s %s" % (kw, typ)).strip()


def _progress_ratio(world_order):
    time_cost = getattr(world_order, "time_cost", 0) or 0
    time_left = getattr(world_order, "time", None)
    if not time_cost or time_left is None:
        return None
    try:
        done = 1.0 - float(time_left) / float(time_cost)
        return max(0.0, min(1.0, done))
    except Exception:
        return None


def _card_size():
    w = _COLS * _ICON + (_COLS - 1) * _GAP + _PAD * 2
    h = _ROWS * _ICON + (_ROWS - 1) * _GAP + _PAD * 2 + _LABEL_H
    return w, h


def hud_panel_rect(screen=None):
    screen = screen or get_screen()
    if screen is None:
        return pygame.Rect(0, 0, 0, 0)
    sw, sh = screen.get_width(), screen.get_height()
    _cw, ch = _card_size()
    h = max(ch, _QUEUE_H + _PAD) + _PAD
    return pygame.Rect(0, sh - h, sw, h)


def hit_test_hud(interface, pos):
    hits = getattr(interface, "_hud_hits", None) or []
    x, y = pos
    for rect, kind, payload in hits:
        if rect.collidepoint(x, y):
            return kind, payload
    if hud_panel_rect().collidepoint(x, y) and getattr(interface, "group", None):
        return "panel", None
    return None


def handle_hud_click(interface, pos, mods=0):
    hit = hit_test_hud(interface, pos)
    if hit is None:
        return False
    kind, payload = hit
    if kind == "panel":
        return True

    from pygame.locals import KMOD_CTRL, KMOD_SHIFT

    from .game_orders import _select_order, cmd_validate

    shift = bool(mods & KMOD_SHIFT)
    ctrl = bool(mods & KMOD_CTRL)
    args = []
    if shift:
        args.append("queue_order")
    if ctrl:
        args.append("imperative")

    if kind == "objectives":
        from .game_resources import cmd_objectives

        # 左键下一条；Shift+左键上一条（对齐 F9 / Shift+F9）
        cmd_objectives(interface, -1 if shift else 1)
        return True

    if kind == "order":
        order = payload
        _select_order(interface, order, help=False)
        if order.nb_args == 0:
            cmd_validate(interface, *args)
        return True

    if kind == "cancel_queue":
        cancel_kw = payload
        if cancel_kw:
            from .game_unit_control import send_order

            send_order(interface, cancel_kw, None, [])
        return True

    return True


def _blit_icon_btn(screen, rect, icon, *, selected=False, needs_tgt=False, hot=False):
    if selected:
        border = (255, 230, 120)
        pad_c = (70, 110, 160)
    elif hot:
        border = (220, 230, 255)
        pad_c = (60, 70, 90)
    elif needs_tgt:
        border = (150, 165, 200)
        pad_c = (40, 45, 60)
    else:
        border = (100, 110, 125)
        pad_c = (30, 34, 42)
    pygame.draw.rect(screen, pad_c, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    ix = rect.x + (rect.w - icon.get_width()) // 2
    iy = rect.y + (rect.h - icon.get_height()) // 2
    screen.blit(icon, (ix, iy))


def _objectives_button_label(interface):
    try:
        from .. import msgparts as mp
        from ..lib.pygame_ui import msgparts_to_text

        label = msgparts_to_text(mp.OBJECTIVE).strip()
        if label:
            # 去掉末尾冒号类标点，按钮上更干净
            return label.rstrip("：: ")
    except Exception:
        pass
    return "Objectives"


def _draw_objectives_button(interface, screen):
    """Always-visible objectives button (sighted; same as hotkey browse)."""
    _ensure_fonts(interface)
    font = interface._hud_font_small or interface._hud_font
    label = _objectives_button_label(interface)
    tw, th = font.size(label)
    pad_x, pad_y = 12, 6
    w = max(72, tw + pad_x * 2)
    h = max(26, th + pad_y * 2)
    # 左上角：避开小地图（右上）
    rect = pygame.Rect(8, 8, w, h)
    mx, my = pygame.mouse.get_pos()
    hot = rect.collidepoint(mx, my)
    fill = (55, 70, 100) if hot else (32, 38, 52)
    border = (255, 220, 120) if hot else (140, 155, 180)
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, border, rect, 2, border_radius=6)
    text = font.render(label, True, (240, 240, 245))
    screen.blit(
        text,
        (rect.x + (rect.w - text.get_width()) // 2, rect.y + (rect.h - text.get_height()) // 2),
    )
    interface._hud_hits.append((rect, "objectives", None))


def draw_hud(interface):
    """绘制图标命令卡与队列；写入 ``interface._hud_hits``。"""
    interface._hud_hits = []
    screen = get_screen()
    if screen is None:
        return

    # 无选中时也画「目标」按钮，便于明眼人用鼠标查看（同目标热键）
    _draw_objectives_button(interface, screen)

    if not getattr(interface, "group", None):
        return

    _ensure_fonts(interface)
    font = interface._hud_font
    font_s = interface._hud_font_small
    sw, sh = screen.get_width(), screen.get_height()
    mx, my = pygame.mouse.get_pos()

    from .game_orders import orders as list_orders

    try:
        order_list = list_orders(interface)
    except Exception:
        order_list = []

    _, _model, queue = _queue_unit(interface)
    show_queue = bool(queue)

    cw, ch = _card_size()
    panel_h = max(ch, (_QUEUE_H if show_queue else 0) + _PAD) + _PAD
    panel = pygame.Rect(0, sh - panel_h, sw, panel_h)
    bg = pygame.Surface((panel.w, panel.h), pygame.SRCALPHA)
    bg.fill((12, 14, 20, 215))
    screen.blit(bg, panel.topleft)
    pygame.draw.line(screen, (120, 130, 150), (0, panel.top), (sw, panel.top), 1)

    # --- 右下角命令卡 ---
    card_x = sw - cw - _PAD
    card_y = sh - ch - _PAD
    pygame.draw.rect(screen, (22, 26, 34), (card_x, card_y, cw, ch), border_radius=8)
    pygame.draw.rect(screen, (90, 100, 120), (card_x, card_y, cw, ch), 1, border_radius=8)

    selected = getattr(interface, "order", None)
    hover_label = None
    slots = _COLS * _ROWS
    for i, o in enumerate(order_list[:slots]):
        col = i % _COLS
        row = i // _COLS
        x = card_x + _PAD + col * (_ICON + _GAP)
        y = card_y + _PAD + row * (_ICON + _GAP)
        rect = pygame.Rect(x, y, _ICON, _ICON)
        title = _short_label(o.title)
        key = _order_icon_key(o)
        kw = getattr(getattr(o, "cls", None), "keyword", "default")
        icon = get_icon(key, kw, title, _ICON)
        is_sel = selected is not None and selected == o
        needs_tgt = bool(getattr(o, "nb_args", 0))
        hot = rect.collidepoint(mx, my)
        _blit_icon_btn(
            screen, rect, icon, selected=is_sel, needs_tgt=needs_tgt, hot=hot
        )
        sc = getattr(o, "shortcut", None)
        if sc:
            badge = font_s.render(str(sc)[0].upper(), True, (255, 255, 220))
            screen.blit(badge, (rect.right - badge.get_width() - 3, rect.y + 2))
        interface._hud_hits.append((rect, "order", o))
        if hot:
            hover_label = title
            if sc:
                hover_label = "%s  [%s]" % (title, sc)

    label_y = card_y + ch - _LABEL_H + 2
    tip = hover_label
    if tip is None and selected is not None:
        tip = _short_label(selected.title)
        if getattr(selected, "nb_args", 0):
            tip = "%s → 点地图选目标" % tip
    if tip:
        ts = font_s.render(tip, True, (255, 235, 160))
        screen.blit(ts, (card_x + (cw - ts.get_width()) // 2, label_y))

    # --- 左侧队列图标条 ---
    if show_queue:
        qx = _PAD
        qy = sh - _QICON - _PAD - 4
        cancel_kw = getattr(queue[-1], "cancel_order", None) if queue else None
        if cancel_kw:
            crect = pygame.Rect(qx, qy, _QICON, _QICON)
            pygame.draw.rect(screen, (120, 45, 45), crect, border_radius=5)
            pygame.draw.rect(screen, (220, 120, 120), crect, 2, border_radius=5)
            cx = font.render("X", True, (255, 220, 220))
            screen.blit(
                cx,
                (
                    crect.x + (crect.w - cx.get_width()) // 2,
                    crect.y + (crect.h - cx.get_height()) // 2,
                ),
            )
            interface._hud_hits.append((crect, "cancel_queue", cancel_kw))
            if crect.collidepoint(mx, my):
                hover_label = "Cancel queue"
            qx = crect.right + _GAP

        for i, o in enumerate(queue[:10]):
            kw = getattr(o, "keyword", "default")
            typ = getattr(getattr(o, "type", None), "type_name", None) or kw
            title = _order_label(o, interface)
            icon = get_icon(typ, kw, title, _QICON)
            r = pygame.Rect(qx, qy, _QICON, _QICON)
            fill = (45, 70, 50) if i == 0 else (35, 40, 50)
            pygame.draw.rect(screen, fill, r, border_radius=5)
            pygame.draw.rect(
                screen,
                (140, 200, 140) if i == 0 else (110, 120, 135),
                r,
                1,
                border_radius=5,
            )
            screen.blit(icon, r.topleft)
            if i == 0:
                ratio = _progress_ratio(o)
                if ratio is not None:
                    pr = pygame.Rect(
                        r.x + 2, r.bottom - 5, max(1, int((r.w - 4) * ratio)), 3
                    )
                    pygame.draw.rect(screen, (120, 220, 120), pr)
            if r.collidepoint(mx, my):
                hover_label = title
            qx = r.right + _GAP
            if qx > card_x - _PAD:
                break

        if hover_label and mx < card_x:
            ts = font_s.render(hover_label, True, (255, 235, 160))
            screen.blit(ts, (_PAD, panel.top + 4))
