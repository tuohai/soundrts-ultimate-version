"""
分层界面热键模式管理。

全局层 (global_bindings.txt) 始终加载；当前活动模式再叠加对应绑定文件。
F 键在模式组内切换；帮助/地图/外交为覆盖式界面，退出后恢复先前模式。
"""

import os

from .. import msgparts as mp
from ..clientmedia import voice
from ..lib.bindings import Bindings
from ..lib.log import warning
from ..lib.msgs import literal_text_msg
from ..paths import CUSTOM_BINDINGS_PATH

UI_DIR = os.path.join("res", "ui")

SELECTION_MODES = ("unit", "building")
ACTION_MODES = ("command", "skill")
OVERLAY_MODES = ("help", "map", "diplomacy")

MODE_FILES = {
    "global": "global_bindings.txt",
    "unit": "unit_bindings.txt",
    "building": "building_bindings.txt",
    "command": "command_bindings.txt",
    "skill": "skill_bindings.txt",
    "rpg": "rpg_bindings.txt",
    "help": "help_bindings.txt",
    "map": "map_bindings.txt",
    "diplomacy": "diplomacy_bindings.txt",
}

MODE_ANNOUNCE = {
    "unit": mp.UNIT_SELECTION_INTERFACE,
    "building": mp.BUILDING_SELECTION_INTERFACE,
    "command": mp.COMMAND_INTERFACE,
    "skill": mp.SKILL_INTERFACE,
    "help": mp.HELP_QUERY_INTERFACE,
    "map": ["地图浏览界面"],
    "diplomacy": mp.DIPLOMACY_INTERFACE,
}

LEGACY_BINDINGS_FILE = "legacy_bindings.txt"


def layered_hotkeys_enabled():
    """是否启用分层界面热键（默认开启，按当前 mod 读取）。"""
    from ..hotkey_editor import layered_hotkeys_enabled_for_current_mod

    return layered_hotkeys_enabled_for_current_mod()


def _read_bindings_layer(filename):
    """从资源栈读取分层绑定文件（兼容安装目录与打包运行）。"""
    stem = filename[:-4] if filename.endswith(".txt") else filename
    try:
        from ..lib.resource import res

        texts = res.texts(f"ui/{stem}", localize=False)
        if texts:
            return texts[-1]
    except Exception:
        pass
    path = os.path.join(UI_DIR, filename)
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            return f.read()
    warning("missing layered bindings file: %s", filename)
    return ""


def _custom_bindings_suffix():
    try:
        with open(CUSTOM_BINDINGS_PATH, encoding="utf-8") as f:
            return "\n" + f.read()
    except OSError:
        return ""


def _legacy_mod_bindings():
    """追加 mod 包中的 bindings.txt（兼容旧 mod 覆盖）。"""
    try:
        from ..lib.resource import res
        legacy = res.text("ui/bindings", append=True, localize=True)
        if legacy and "layered bindings" not in legacy:
            return legacy
    except Exception:
        pass
    return ""


def _legacy_bindings_with_overrides():
    from ..hotkey_editor import apply_overrides_to_bindings_text

    text = _read_bindings_layer(LEGACY_BINDINGS_FILE)
    return apply_overrides_to_bindings_text(text, "classic")


def get_legacy_bindings_text():
    """单文件经典热键：legacy_bindings.txt + mod + user/bindings.txt。"""
    parts = [_legacy_bindings_with_overrides()]
    legacy = _legacy_mod_bindings()
    if legacy:
        parts.append(legacy)
    suffix = _custom_bindings_suffix()
    if suffix.strip():
        parts.append(suffix.strip())
    return "\n\n".join(p for p in parts if p)


def _bindings_layer_with_overrides(layer):
    from ..hotkey_editor import apply_overrides_to_bindings_text

    text = _read_bindings_layer(MODE_FILES[layer])
    return apply_overrides_to_bindings_text(text, layer)


def rpg_bindings_with_overrides():
    """第一人称模式叠加的 RPG 热键（含用户自定义映射）。"""
    return _bindings_layer_with_overrides("rpg")


def _global_bindings_with_overrides():
    return _bindings_layer_with_overrides("global")


def get_bindings_text(mode):
    """返回 global + 指定模式的合并绑定文本。"""
    parts = [_global_bindings_with_overrides()]
    if mode and mode in MODE_FILES:
        parts.append(_bindings_layer_with_overrides(mode))
    legacy = _legacy_mod_bindings()
    if legacy:
        parts.append(legacy)
    parts.append(_custom_bindings_suffix())
    return "\n\n".join(p for p in parts if p)


def save_map_browse_target(interface):
    """记住地图浏览界面选中的目标（矿点/草地/通道等）。"""
    t = getattr(interface, "target", None)
    interface._map_browse_target_id = getattr(t, "id", None) if t else None


def restore_map_browse_target(interface, announce=False):
    """回到地图浏览界面时恢复先前选中的目标。"""
    tid = getattr(interface, "_map_browse_target_id", None)
    if tid is None:
        return False
    obj = interface.dobjets.get(tid)
    if obj is None:
        interface._map_browse_target_id = None
        return False
    interface.target = obj
    if announce:
        from .game_unit_control import say_target
        say_target(interface)
    return True


def _announce_map_mode_entry(interface):
    """进入地图界面且无焦点时，播报当前方格整体概况。"""
    if interface.place is not None:
        from .game_navigation import say_square
        say_square(
            interface,
            interface.place,
            prefix=MODE_ANNOUNCE.get("map", ["地图浏览界面"]) + mp.COMMA,
        )
    else:
        voice.item(MODE_ANNOUNCE.get("map", ["地图浏览界面"]))


def init_interface_modes(interface):
    interface._map_browse_target_id = None
    if not layered_hotkeys_enabled():
        interface._layered_bindings_active = False
        interface._ui_mode = "unit"
        interface._bindings = Bindings()
        interface._bindings.load(get_legacy_bindings_text(), interface)
        return
    interface._layered_bindings_active = True
    interface._ui_mode = "unit"
    interface._ui_mode_before_overlay = "unit"
    apply_active_mode_bindings(interface, announce=False)


def legacy_handle_escape(interface):
    """经典单文件热键下的 ESC：不进入地图浏览界面层。"""
    if interface.order:
        voice.item(mp.CANCEL)
        interface.order = None
        return True
    if getattr(interface, "_in_inventory_screen", False):
        interface.inventory_screen.cmd__inventory_escape()
        return True
    if getattr(interface, "_in_equipment_screen", False):
        interface.equipment_screen.cmd__equipment_escape()
        return True
    if getattr(interface, "_in_attributes_screen", False):
        interface.cmd__exit_attributes_screen()
        return True
    if interface.immersion:
        from .game_navigation import toggle_immersion
        toggle_immersion(interface)
        return True
    if interface.zoom_mode:
        from .game_navigation import cmd_toggle_zoom
        cmd_toggle_zoom(interface)
        return True
    return False


def apply_active_mode_bindings(interface, announce=False):
    """按当前模式重新加载热键绑定。"""
    if not getattr(interface, "_layered_bindings_active", False):
        interface.load_bindings(get_legacy_bindings_text())
        return
    mode = getattr(interface, "_ui_mode", "unit")
    interface._bindings = Bindings()
    interface._bindings.load(get_bindings_text(mode), interface)
    if announce:
        voice.item(MODE_ANNOUNCE.get(mode, literal_text_msg(mode)))


def restore_active_bindings(interface):
    """子界面（背包/属性/RPG 等）退出后恢复分层绑定。"""
    if getattr(interface, "_layered_bindings_active", False):
        apply_active_mode_bindings(interface, announce=False)
    elif hasattr(interface, "get_bindings"):
        interface.load_bindings(interface.get_bindings())


def _set_mode(interface, mode, announce=True):
    if not layered_hotkeys_enabled():
        voice.item(mp.BEEP)
        return
    if mode not in MODE_FILES and mode not in OVERLAY_MODES:
        voice.item(mp.BEEP)
        return
    old = getattr(interface, "_ui_mode", "unit")
    if old == "map" and mode != "map":
        save_map_browse_target(interface)
    interface._ui_mode = mode
    apply_active_mode_bindings(interface, announce=False)
    if mode == "map":
        restore_map_browse_target(interface, announce=False)
        if announce:
            _announce_map_mode_entry(interface)
    elif announce:
        voice.item(MODE_ANNOUNCE.get(mode, literal_text_msg(mode)))


def _toggle_in_group(interface, group, default):
    current = getattr(interface, "_ui_mode", default)
    if current in group:
        idx = group.index(current)
        new_mode = group[(idx + 1) % len(group)]
    else:
        new_mode = default
    _set_mode(interface, new_mode)


def cmd_toggle_selection_mode(interface):
    """F1：单位选择 ↔ 建筑选择。"""
    _toggle_in_group(interface, SELECTION_MODES, "unit")


def cmd_toggle_action_mode(interface):
    """F2：命令 ↔ 技能。"""
    _toggle_in_group(interface, ACTION_MODES, "command")


def cmd_enter_help_mode(interface):
    """F4：进入帮助与查询界面。"""
    if interface._ui_mode == "help":
        cmd_exit_overlay_mode(interface)
        return
    interface._ui_mode_before_overlay = (
        interface._ui_mode
        if interface._ui_mode not in OVERLAY_MODES
        else getattr(interface, "_ui_mode_before_overlay", "unit")
    )
    _set_mode(interface, "help")


def cmd_enter_diplomacy_mode(interface):
    """F12：进入外交界面。"""
    if interface._ui_mode == "diplomacy":
        cmd_exit_overlay_mode(interface)
        return
    interface._ui_mode_before_overlay = (
        interface._ui_mode
        if interface._ui_mode not in OVERLAY_MODES
        else getattr(interface, "_ui_mode_before_overlay", "unit")
    )
    _set_mode(interface, "diplomacy")


def cmd_enter_map_mode(interface):
    """进入地图浏览界面（由 ESC 在合适时机调用）。"""
    if interface._ui_mode == "map":
        cmd_exit_overlay_mode(interface)
        return
    interface._ui_mode_before_overlay = (
        interface._ui_mode
        if interface._ui_mode not in OVERLAY_MODES
        else getattr(interface, "_ui_mode_before_overlay", "unit")
    )
    _set_mode(interface, "map")


def cmd_exit_overlay_mode(interface):
    """退出帮助/地图/外交等覆盖界面。"""
    if interface._ui_mode not in OVERLAY_MODES:
        return
    _set_mode(
        interface,
        getattr(interface, "_ui_mode_before_overlay", "unit"),
        announce=True,
    )


def cmd_toggle_gear_screen(interface):
    """背包 ↔ 装备栏（分层 F3；经典 Shift+V）。"""
    if getattr(interface, "_in_inventory_screen", False):
        interface.inventory_screen._exit_inventory_screen()
        interface.equipment_screen.cmd_unit_equipment_screen()
        return
    if getattr(interface, "_in_equipment_screen", False):
        interface.equipment_screen._exit_equipment_screen()
        interface.inventory_screen.cmd_unit_inventory_screen()
        return
    interface.inventory_screen.cmd_unit_inventory_screen()


def handle_escape(interface):
    """ESC 逻辑；经典模式不进入地图浏览层。"""
    if not layered_hotkeys_enabled():
        legacy_handle_escape(interface)
        return True
    if interface._ui_mode in OVERLAY_MODES:
        cmd_exit_overlay_mode(interface)
        return True
    if interface.order:
        voice.item(mp.CANCEL)
        interface.order = None
        return True
    if getattr(interface, "_in_inventory_screen", False):
        interface.inventory_screen.cmd__inventory_escape()
        return True
    if getattr(interface, "_in_equipment_screen", False):
        interface.equipment_screen.cmd__equipment_escape()
        return True
    if getattr(interface, "_in_attributes_screen", False):
        interface.cmd__exit_attributes_screen()
        return True
    if interface.immersion:
        from .game_navigation import toggle_immersion
        toggle_immersion(interface)
        return True
    if interface.zoom_mode:
        from .game_navigation import cmd_toggle_zoom
        cmd_toggle_zoom(interface)
        return True
    cmd_enter_map_mode(interface)
    return True
