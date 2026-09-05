"""Ctrl+F2：背包 / 装备栏可视化与鼠标操作。

复用 ``attributes/inventory_screen.py``、``equipment_screen.py`` 的命令逻辑；
仅在画面开启时绘制与点击。
"""

from __future__ import annotations

import pygame

from ..lib.screen import get_screen
from .game_hud import (
    _PAD,
    _ensure_fonts,
    _short_label,
    _voice_to_text,
    get_icon,
    get_map_sprite,
)

_SLOT = 48
_GAP = 6
_COLS = 6
_BTN_H = 28


def gear_screen_active(interface):
    return bool(
        getattr(interface, "_in_inventory_screen", False)
        or getattr(interface, "_in_equipment_screen", False)
    )


def _mode(interface):
    if getattr(interface, "_in_inventory_screen", False):
        return "inventory"
    if getattr(interface, "_in_equipment_screen", False):
        return "equipment"
    return None


def _screen_obj(interface, mode):
    if mode == "inventory":
        return getattr(interface, "inventory_screen", None)
    if mode == "equipment":
        return getattr(interface, "equipment_screen", None)
    return None


def _entries(interface, mode):
    scr = _screen_obj(interface, mode)
    if scr is None:
        return []
    if mode == "inventory":
        return [("inventory", it) for it in scr._get_inventory_items()]
    return list(scr._get_equipment_entries())


def _selected_index(interface, mode):
    if mode == "inventory":
        return int(getattr(interface, "_inventory_item_index", 0) or 0)
    return int(getattr(interface, "_equipment_item_index", 0) or 0)


def _set_selected_index(interface, mode, idx):
    if mode == "inventory":
        interface._inventory_item_index = idx
        interface._inventory_confirm_drop = False
        scr = interface.inventory_screen
        if scr:
            scr._display_current_item()
    else:
        interface._equipment_item_index = idx
        interface._equipment_confirm_drop = False
        scr = interface.equipment_screen
        if scr:
            scr._display_current_entry()


def _confirm_drop(interface, mode):
    if mode == "inventory":
        return bool(getattr(interface, "_inventory_confirm_drop", False))
    return bool(getattr(interface, "_equipment_confirm_drop", False))


def _entry_type_name(kind, data):
    if kind == "inventory":
        return getattr(data, "type_name", None)
    return data  # builtin type name


def _entry_label(scr, kind, data):
    if kind == "inventory":
        return _short_label(scr._item_title(data), 16)
    if hasattr(scr, "_type_title"):
        return _short_label(scr._type_title(data), 16)
    return _short_label([str(data)], 16)


def _entry_icon(kind, data, size=_SLOT):
    tn = _entry_type_name(kind, data)
    if not tn:
        return get_icon("default", "default", "?", size)
    surf = get_map_sprite(tn, size)
    if surf is not None:
        return surf
    return get_icon(tn, "default", tn, size)


def _is_equipped(scr, kind, data):
    if hasattr(scr, "_is_equipped_entry"):
        return bool(scr._is_equipped_entry(kind, data))
    if kind == "inventory" and hasattr(scr, "_is_equipped"):
        return bool(scr._is_equipped(data))
    return False


def _panel_title(mode):
    try:
        from .. import msgparts as mp

        if mode == "inventory":
            return _voice_to_text(mp.BACKPACK) or "Backpack"
        return _voice_to_text(mp.EQUIPMENT_BAR) or "Equipment"
    except Exception:
        return "Backpack" if mode == "inventory" else "Equipment"


def _selected_unit(interface):
    if len(getattr(interface, "group", None) or []) != 1:
        return None
    return interface.dobjets.get(interface.group[0])


def _unit_can_open_inventory(interface):
    from ..attributes.inventory_screen import unit_has_inventory

    u = _selected_unit(interface)
    if u is None or not unit_has_inventory(u):
        return False
    inv = getattr(u, "inventory", None) or []
    return bool(inv)


def _unit_can_open_equipment(interface):
    from ..attributes.inventory_screen import unit_has_inventory

    u = _selected_unit(interface)
    if u is None or not unit_has_inventory(u):
        return False
    uid = interface.group[0]
    old = getattr(interface, "_equipment_screen_unit_id", None)
    interface._equipment_screen_unit_id = uid
    try:
        scr = getattr(interface, "equipment_screen", None)
        if scr is None:
            return False
        return bool(scr._get_equipment_entries())
    except Exception:
        return False
    finally:
        interface._equipment_screen_unit_id = old


def draw_gear_open_buttons(interface, screen, *, anchor_rect):
    """选中栏旁的「背包 / 装备」入口按钮。返回占去的右缘 x。"""
    if gear_screen_active(interface):
        return anchor_rect.right
    _ensure_fonts(interface)
    font = interface._hud_font_small or interface._hud_font
    x = anchor_rect.right + _GAP
    y = anchor_rect.y
    buttons = []
    if _unit_can_open_inventory(interface):
        buttons.append(("open_inv", _voice_to_text(["背包"]) or "Bag"))
    if _unit_can_open_equipment(interface):
        buttons.append(("open_eq", _voice_to_text(["装备栏"]) or "Gear"))
    if not buttons:
        return anchor_rect.right
    mx, my = pygame.mouse.get_pos()
    for kind, label in buttons:
        tw, th = font.size(label)
        r = pygame.Rect(x, y, max(52, tw + 16), max(24, th + 8))
        hot = r.collidepoint(mx, my)
        pygame.draw.rect(screen, (55, 70, 100) if hot else (32, 38, 52), r, border_radius=5)
        pygame.draw.rect(screen, (255, 220, 120) if hot else (140, 155, 180), r, 1, border_radius=5)
        ts = font.render(label, True, (240, 240, 245))
        screen.blit(
            ts,
            (r.x + (r.w - ts.get_width()) // 2, r.y + (r.h - ts.get_height()) // 2),
        )
        interface._hud_hits.append((r, kind, None))
        x = r.right + _GAP
    return x


def _layout(interface, screen):
    mode = _mode(interface)
    if mode is None:
        return None
    sw, sh = screen.get_width(), screen.get_height()
    entries = _entries(interface, mode)
    rows = max(1, (max(1, len(entries)) + _COLS - 1) // _COLS)
    grid_h = rows * _SLOT + (rows - 1) * _GAP
    panel_w = min(520, sw - 40)
    panel_h = min(sh - 80, 56 + grid_h + 16 + _BTN_H + 12 + 36)
    px = (sw - panel_w) // 2
    py = max(40, (sh - panel_h) // 2 - 20)
    return {
        "mode": mode,
        "rect": pygame.Rect(px, py, panel_w, panel_h),
        "entries": entries,
        "grid_top": py + 40,
        "grid_left": px + 16,
    }


def draw_gear_hud(interface):
    """绘制背包/装备覆盖层；命中写入 ``interface._gear_hits``。"""
    interface._gear_hits = []
    mode = _mode(interface)
    if mode is None:
        return
    screen = get_screen()
    if screen is None:
        return
    _ensure_fonts(interface)
    font = interface._hud_font
    font_s = interface._hud_font_small
    layout = _layout(interface, screen)
    if layout is None:
        return
    scr = _screen_obj(interface, mode)
    if scr is None:
        return

    # 半透明遮罩，点击外部可关闭
    dim = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 120))
    screen.blit(dim, (0, 0))
    interface._gear_hits.append((screen.get_rect(), "backdrop", None))

    panel = layout["rect"]
    pygame.draw.rect(screen, (18, 22, 30), panel, border_radius=10)
    pygame.draw.rect(screen, (160, 170, 190), panel, 2, border_radius=10)
    # 面板本体挡住 backdrop
    interface._gear_hits.append((panel, "panel", None))

    title = _panel_title(mode)
    screen.blit(font.render(title, True, (255, 235, 160)), (panel.x + 14, panel.y + 10))

    # 切换 / 关闭
    mx, my = pygame.mouse.get_pos()
    btn_y = panel.y + 8
    close_r = pygame.Rect(panel.right - 36, btn_y, 28, 28)
    switch_label = "Equip" if mode == "inventory" else "Bag"
    try:
        from .. import msgparts as mp

        if mode == "inventory":
            switch_label = _short_label(mp.EQUIPMENT_BAR, 8) or "Equip"
        else:
            switch_label = _short_label(mp.BACKPACK, 8) or "Bag"
    except Exception:
        pass
    sw_w = max(64, font_s.size(switch_label)[0] + 16)
    switch_r = pygame.Rect(close_r.x - sw_w - 8, btn_y, sw_w, 28)
    for r, kind, label, fill in (
        (switch_r, "switch", switch_label, (50, 70, 100)),
        (close_r, "close", "X", (120, 50, 50)),
    ):
        hot = r.collidepoint(mx, my)
        pygame.draw.rect(screen, fill if not hot else tuple(min(255, c + 30) for c in fill), r, border_radius=5)
        pygame.draw.rect(screen, (220, 230, 245), r, 1, border_radius=5)
        ts = font_s.render(label, True, (245, 245, 250))
        screen.blit(
            ts,
            (r.x + (r.w - ts.get_width()) // 2, r.y + (r.h - ts.get_height()) // 2),
        )
        interface._gear_hits.append((r, kind, None))

    # 物品格
    entries = layout["entries"]
    sel = _selected_index(interface, mode)
    gx0, gy0 = layout["grid_left"], layout["grid_top"]
    for i, (kind, data) in enumerate(entries):
        col = i % _COLS
        row = i // _COLS
        r = pygame.Rect(
            gx0 + col * (_SLOT + _GAP),
            gy0 + row * (_SLOT + _GAP),
            _SLOT,
            _SLOT,
        )
        equipped = _is_equipped(scr, kind, data)
        selected = i == sel
        fill = (70, 90, 60) if equipped else (40, 46, 58)
        if selected:
            fill = (90, 110, 150)
        pygame.draw.rect(screen, fill, r, border_radius=6)
        border = (255, 230, 120) if selected else ((140, 200, 140) if equipped else (110, 120, 140))
        pygame.draw.rect(screen, border, r, 2 if selected else 1, border_radius=6)
        icon = _entry_icon(kind, data, _SLOT - 4)
        screen.blit(icon, icon.get_rect(center=r.center))
        if kind.startswith("builtin"):
            badge = font_s.render("B", True, (255, 200, 120))
            screen.blit(badge, (r.x + 2, r.y + 1))
        interface._gear_hits.append((r, "slot", i))

    # 当前项说明
    info_y = gy0 + max(1, (max(1, len(entries)) + _COLS - 1) // _COLS) * (_SLOT + _GAP) + 4
    if entries and 0 <= sel < len(entries):
        kind, data = entries[sel]
        label = _entry_label(scr, kind, data)
        if _is_equipped(scr, kind, data):
            label += "  [E]"
        if kind == "builtin_weapon":
            label += "  (builtin W)"
        elif kind == "builtin_armor":
            label += "  (builtin A)"
        screen.blit(
            font_s.render(label, True, (230, 235, 245)),
            (panel.x + 14, min(info_y, panel.bottom - _BTN_H - 40)),
        )

    # 操作按钮
    confirming = _confirm_drop(interface, mode)
    by = panel.bottom - _BTN_H - 12
    bx = panel.x + 14
    if confirming:
        actions = [
            ("drop_yes", "Confirm drop", (150, 60, 60)),
            ("drop_no", "Cancel", (60, 70, 90)),
        ]
    else:
        actions = [
            ("use", "Use/Equip", (50, 110, 70)),
            ("unequip", "Unequip", (90, 90, 50)),
            ("drop", "Drop", (130, 55, 55)),
            ("intro", "Info", (50, 80, 110)),
        ]
    for kind, label, fill in actions:
        tw = max(72, font_s.size(label)[0] + 14)
        r = pygame.Rect(bx, by, tw, _BTN_H)
        if r.right > panel.right - 12:
            break
        hot = r.collidepoint(mx, my)
        pygame.draw.rect(
            screen,
            tuple(min(255, c + 25) for c in fill) if hot else fill,
            r,
            border_radius=5,
        )
        pygame.draw.rect(screen, (210, 220, 235), r, 1, border_radius=5)
        ts = font_s.render(label, True, (245, 248, 255))
        screen.blit(
            ts,
            (r.x + (r.w - ts.get_width()) // 2, r.y + (r.h - ts.get_height()) // 2),
        )
        interface._gear_hits.append((r, kind, None))
        bx = r.right + _GAP


def hit_test_gear(interface, pos):
    hits = getattr(interface, "_gear_hits", None) or []
    # 后添加的控件优先（按钮/格子在 panel/backdrop 之上）
    for rect, kind, payload in reversed(hits):
        if kind in ("panel", "backdrop"):
            continue
        if rect.collidepoint(pos):
            return kind, payload
    for rect, kind, payload in reversed(hits):
        if rect.collidepoint(pos):
            return kind, payload
    return None


def handle_gear_click(interface, pos, mods=0):
    hit = hit_test_gear(interface, pos)
    if hit is None:
        return False
    kind, payload = hit
    mode = _mode(interface)
    from pygame.locals import KMOD_SHIFT

    shift = bool(mods & KMOD_SHIFT)

    if kind == "backdrop":
        if mode == "inventory":
            interface.inventory_screen.cmd__inventory_escape()
        elif mode == "equipment":
            interface.equipment_screen.cmd__equipment_escape()
        return True
    if kind == "panel":
        return True
    if kind == "close":
        if mode == "inventory":
            interface.inventory_screen.cmd__inventory_escape()
        else:
            interface.equipment_screen.cmd__equipment_escape()
        return True
    if kind == "switch":
        from .interface_modes import cmd_toggle_gear_screen

        cmd_toggle_gear_screen(interface)
        return True
    if kind == "slot":
        _set_selected_index(interface, mode, int(payload))
        return True
    if kind == "use":
        if mode == "inventory":
            if shift:
                interface.inventory_screen.cmd__inventory_unequip()
            else:
                interface.inventory_screen.cmd__inventory_use()
        else:
            if shift:
                interface.equipment_screen.cmd__equipment_unequip()
            else:
                interface.equipment_screen.cmd__equipment_use()
        return True
    if kind == "unequip":
        if mode == "inventory":
            interface.inventory_screen.cmd__inventory_unequip()
        else:
            interface.equipment_screen.cmd__equipment_unequip()
        return True
    if kind == "drop":
        if shift:
            if mode == "inventory":
                interface.inventory_screen.cmd__inventory_drop_now()
            else:
                interface.equipment_screen.cmd__equipment_drop_now()
        else:
            if mode == "inventory":
                interface.inventory_screen.cmd__inventory_drop_confirm()
            else:
                interface.equipment_screen.cmd__equipment_drop_confirm()
        return True
    if kind == "drop_yes":
        if mode == "inventory":
            interface.inventory_screen.cmd__inventory_drop_execute()
        else:
            interface.equipment_screen.cmd__equipment_drop_execute()
        return True
    if kind == "drop_no":
        if mode == "inventory":
            interface._inventory_confirm_drop = False
        else:
            interface._equipment_confirm_drop = False
        return True
    if kind == "intro":
        if mode == "inventory":
            interface.inventory_screen.cmd__inventory_intro()
        else:
            interface.equipment_screen.cmd__equipment_intro()
        return True
    return True
