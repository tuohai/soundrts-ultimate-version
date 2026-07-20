"""热键映射编辑器 — 解析、存储、各界面层覆盖。"""

from __future__ import annotations

import json
import os
import re
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame
from pygame.locals import (
    K_BACKSPACE,
    K_DELETE,
    K_ESCAPE,
    K_F1,
    K_F10,
    K_F11,
    K_F12,
    K_F2,
    K_F3,
    K_F4,
    K_F5,
    K_F6,
    K_F7,
    K_F8,
    K_F9,
    K_KP_ENTER,
    K_KP_MINUS,
    K_KP_PLUS,
    K_LALT,
    K_LCTRL,
    K_LSHIFT,
    K_RALT,
    K_RCTRL,
    K_RSHIFT,
    K_RETURN,
    K_SPACE,
    K_TAB,
    KEYDOWN,
    KMOD_ALT,
    KMOD_CTRL,
    KMOD_LSHIFT,
    KMOD_RSHIFT,
    KMOD_SHIFT,
    QUIT,
)

from .lib.defs import preprocess
from . import msgparts as mp
from .lib.msgs import literal_text_msg
from .paths import (
    BASE_MOD_KEY,
    HOTKEY_OVERRIDES_DIR,
    LEGACY_HOTKEY_OVERRIDES_PATH,
    current_hotkey_overrides_path,
)

_OVERRIDES_VERSION = 1
ALIAS_OVERRIDE_SEP = "@"


def encode_alias_key_token(key_string: str) -> str:
    return key_string.replace(" ", "+")


def decode_alias_key_token(token: str) -> str:
    return token.replace("+", " ")


def make_alias_override_id(binding_id: str, alias_default_key: str) -> str:
    return (
        f"{binding_id}{ALIAS_OVERRIDE_SEP}"
        f"{encode_alias_key_token(alias_default_key)}"
    )


def split_override_id(override_id: str) -> Tuple[str, Optional[str]]:
    if ALIAS_OVERRIDE_SEP not in override_id:
        return override_id, None
    binding_id, token = override_id.rsplit(ALIAS_OVERRIDE_SEP, 1)
    return binding_id, decode_alias_key_token(token)


def parse_layer_override_map(
    overrides: Dict[str, str],
) -> Tuple[Dict[str, str], Dict[Tuple[str, str], str]]:
    primary: Dict[str, str] = {}
    alias: Dict[Tuple[str, str], str] = {}
    for override_id, new_key in overrides.items():
        binding_id, alias_default = split_override_id(override_id)
        if alias_default is not None:
            alias[(binding_id, alias_default)] = new_key
        else:
            primary[binding_id] = new_key
    return primary, alias


def get_hotkey_overrides_path() -> str:
    os.makedirs(HOTKEY_OVERRIDES_DIR, exist_ok=True)
    return current_hotkey_overrides_path()


def current_hotkey_overrides_mod_key() -> str:
    from .paths import current_mod_key

    return current_mod_key()


def hotkey_mod_label_msgs(mod_key: str) -> list:
    if mod_key == BASE_MOD_KEY:
        return list(mp.HOTKEY_MOD_NONE)
    return literal_text_msg(mod_key.replace("_", " ").replace("+", " "))


def get_layered_hotkeys_scheme() -> int:
    """当前 mod 的热键方案：1=分层，0=经典。

    未单独配置时：无 mod（_base）回退 SoundRTS.ini；其它 mod 默认分层。
    """
    data = load_overrides_data()
    if "layered_hotkeys" in data:
        try:
            return 1 if int(data["layered_hotkeys"]) != 0 else 0
        except (TypeError, ValueError):
            pass
    if current_hotkey_overrides_mod_key() == BASE_MOD_KEY:
        from . import config

        try:
            return 1 if int(getattr(config, "layered_hotkeys", 1)) != 0 else 0
        except (TypeError, ValueError):
            return 1
    return 1


def set_layered_hotkeys_scheme(value: int) -> None:
    """保存当前 mod 的热键方案到 hotkey_overrides/{mod_key}.json。"""
    data = load_overrides_data()
    data["layered_hotkeys"] = 1 if int(value) != 0 else 0
    save_overrides_data(data)


def layered_hotkeys_enabled_for_current_mod() -> bool:
    return get_layered_hotkeys_scheme() != 0


def _migrate_legacy_overrides_if_needed(path: str) -> None:
    """将旧版 user/hotkey_overrides.json 一次性迁入 _base 配置。"""
    if os.path.exists(path) or not os.path.exists(LEGACY_HOTKEY_OVERRIDES_PATH):
        return
    if os.path.basename(path) != f"{BASE_MOD_KEY}.json":
        return
    os.makedirs(HOTKEY_OVERRIDES_DIR, exist_ok=True)
    shutil.copy2(LEGACY_HOTKEY_OVERRIDES_PATH, path)

# 全局层主绑定目录：binding_id → 显示名（msg 列表）
GLOBAL_PRIMARY_CATALOG: List[Tuple[str, list]] = [
    ("global.resource_status.resource1", list(mp.HOTKEY_RESOURCE1_STATUS)),
    ("global.resource_status.resource2", list(mp.HOTKEY_RESOURCE2_STATUS)),
    ("global.resource_status.resource3", list(mp.HOTKEY_RESOURCE3_STATUS)),
    ("global.population_status", list(mp.HOTKEY_POPULATION_STATUS)),
    ("global.ui_escape", list(mp.HOTKEY_UI_ESCAPE)),
    ("global.toggle_selection_mode", list(mp.HOTKEY_TOGGLE_SELECTION_MODE)),
    ("global.toggle_action_mode", list(mp.HOTKEY_TOGGLE_ACTION_MODE)),
    ("global.toggle_gear_screen", list(mp.HOTKEY_TOGGLE_GEAR_SCREEN)),
    ("global.enter_help_mode", list(mp.HOTKEY_ENTER_HELP_MODE)),
    ("global.enter_diplomacy_mode", list(mp.HOTKEY_ENTER_DIPLOMACY_MODE)),
    ("global.unit_attributes_screen", list(mp.HOTKEY_ATTRIBUTES_SCREEN)),
    ("global.select_target.1", list(mp.HOTKEY_SELECT_TARGET_NEXT)),
    ("global.select_target.-1", list(mp.HOTKEY_SELECT_TARGET_PREV)),
    ("global.select_target.1.useful", list(mp.HOTKEY_SELECT_USEFUL_TARGET_NEXT)),
    ("global.select_target.-1.useful", list(mp.HOTKEY_SELECT_USEFUL_TARGET_PREV)),
    ("global.select_square.0.1", list(mp.HOTKEY_MOVE_NORTH)),
    ("global.select_square.0.-1", list(mp.HOTKEY_MOVE_SOUTH)),
    ("global.select_square.-1.0", list(mp.HOTKEY_MOVE_WEST)),
    ("global.select_square.1.0", list(mp.HOTKEY_MOVE_EAST)),
    ("global.select_scouted_square.1", list(mp.HOTKEY_SCOUTED_SQUARE_NEXT)),
    ("global.select_scouted_square.-1", list(mp.HOTKEY_SCOUTED_SQUARE_PREV)),
    ("global.select_conflict_square.1", list(mp.HOTKEY_CONFLICT_SQUARE_NEXT)),
    ("global.select_conflict_square.-1", list(mp.HOTKEY_CONFLICT_SQUARE_PREV)),
    ("global.select_unknown_square.1", list(mp.HOTKEY_UNKNOWN_SQUARE_NEXT)),
    ("global.select_unknown_square.-1", list(mp.HOTKEY_UNKNOWN_SQUARE_PREV)),
    ("global.select_resource_square.1", list(mp.HOTKEY_RESOURCE_SQUARE_NEXT)),
    ("global.select_resource_square.-1", list(mp.HOTKEY_RESOURCE_SQUARE_PREV)),
    ("global.default", list(mp.HOTKEY_DEFAULT_COMMAND)),
    ("global.validate", list(mp.HOTKEY_VALIDATE_COMMAND)),
    ("global.examine", list(mp.HOTKEY_EXAMINE)),
    ("global.unit_status", list(mp.HOTKEY_UNIT_STATUS)),
    ("global.unit_hp_status", list(mp.HOTKEY_UNIT_HP_STATUS)),
    ("global.objectives.1", list(mp.HOTKEY_OBJECTIVES_NEXT)),
    ("global.objectives.-1", list(mp.HOTKEY_OBJECTIVES_PREV)),
    ("global.say_players", list(mp.HOTKEY_SAY_PLAYERS)),
    ("global.history_previous", list(mp.HOTKEY_HISTORY_PREV)),
    ("global.history_next", list(mp.HOTKEY_HISTORY_NEXT)),
    ("global.gamemenu", list(mp.HOTKEY_GAME_MENU)),
    ("global.volume", list(mp.HOTKEY_VOLUME_UP)),
    ("global.volume.-1", list(mp.HOTKEY_VOLUME_DOWN)),
    (
        "global.immersion",
        list(mp.HOTKEY_VISUAL_IMMERSION),
    ),
    ("global.console", list(mp.HOTKEY_CONSOLE)),
    ("global.toggle_music", list(mp.HOTKEY_TOGGLE_MUSIC)),
    (
        "global.fullscreen",
        list(mp.HOTKEY_VISUAL_TOGGLE),
    ),
    ("global.toggle_talking_clock", list(mp.HOTKEY_TOGGLE_TALKING_CLOCK)),
    ("global.change_player", list(mp.HOTKEY_CHANGE_PLAYER)),
    ("global.toggle_cheatmode", list(mp.HOTKEY_TOGGLE_CHEATMODE)),
]

# 与 bindings.py 一致：部分 pygame 版本缺少 scancode 常量
pygame.KSCAN_QUOTE = getattr(pygame, "KSCAN_QUOTE", 52)
pygame.KSCAN_BACKQUOTE = getattr(pygame, "KSCAN_BACKQUOTE", 53)

# pygame 键名 → bindings.txt 键名
_PYGAME_KEY_NAMES = {
    pygame.K_UP: "UP",
    pygame.K_DOWN: "DOWN",
    pygame.K_LEFT: "LEFT",
    pygame.K_RIGHT: "RIGHT",
    pygame.K_PAGEUP: "PAGEUP",
    pygame.K_PAGEDOWN: "PAGEDOWN",
    pygame.K_HOME: "HOME",
    pygame.K_END: "END",
    pygame.K_TAB: "TAB",
    pygame.K_SPACE: "SPACE",
    pygame.K_RETURN: "RETURN",
    pygame.K_KP_ENTER: "KP_ENTER",
    pygame.K_ESCAPE: "ESCAPE",
    pygame.K_BACKSPACE: "BACKSPACE",
    pygame.K_KP_PLUS: "KP_PLUS",
    pygame.K_KP_MINUS: "KP_MINUS",
    pygame.K_EQUALS: "EQUALS",
    pygame.K_MINUS: "MINUS",
    pygame.K_BACKSLASH: "BACKSLASH",
    pygame.K_SEMICOLON: "SEMICOLON",
    K_F1: "F1",
    K_F2: "F2",
    K_F3: "F3",
    K_F4: "F4",
    K_F5: "F5",
    K_F6: "F6",
    K_F7: "F7",
    K_F8: "F8",
    K_F9: "F9",
    K_F10: "F10",
    K_F11: "F11",
    K_F12: "F12",
    K_LCTRL: "LCTRL",
    K_RCTRL: "RCTRL",
    K_LALT: "LALT",
    K_RALT: "RALT",
    K_LSHIFT: "LSHIFT",
    K_RSHIFT: "RSHIFT",
}

_STANDALONE_MODIFIER_KEYS = frozenset(
    (K_LCTRL, K_RCTRL, K_LALT, K_RALT, K_LSHIFT, K_RSHIFT)
)

_KEY_NAME_SPEECH = {
    "CTRL": list(mp.HOTKEY_KEY_CTRL),
    "SHIFT": list(mp.HOTKEY_KEY_SHIFT),
    "ALT": list(mp.HOTKEY_KEY_ALT),
    "UP": list(mp.HOTKEY_KEY_UP),
    "DOWN": list(mp.HOTKEY_KEY_DOWN),
    "LEFT": list(mp.HOTKEY_KEY_LEFT),
    "RIGHT": list(mp.HOTKEY_KEY_RIGHT),
    "PAGEUP": list(mp.HOTKEY_KEY_PAGEUP),
    "PAGEDOWN": list(mp.HOTKEY_KEY_PAGEDOWN),
    "HOME": list(mp.HOTKEY_KEY_HOME),
    "END": list(mp.HOTKEY_KEY_END),
    "TAB": list(mp.HOTKEY_KEY_TAB),
    "SPACE": list(mp.HOTKEY_KEY_SPACE),
    "RETURN": list(mp.HOTKEY_KEY_RETURN),
    "KP_ENTER": list(mp.HOTKEY_KEY_KP_ENTER),
    "ESCAPE": list(mp.HOTKEY_KEY_ESCAPE),
    "BACKSPACE": list(mp.HOTKEY_KEY_BACKSPACE),
    "KP_PLUS": list(mp.HOTKEY_KEY_KP_PLUS),
    "KP_MINUS": list(mp.HOTKEY_KEY_KP_MINUS),
    "EQUALS": list(mp.HOTKEY_KEY_EQUALS),
    "MINUS": list(mp.HOTKEY_KEY_MINUS),
    "BACKSLASH": list(mp.HOTKEY_KEY_BACKSLASH),
    "SEMICOLON": list(mp.HOTKEY_KEY_SEMICOLON),
    "BACKQUOTE": list(mp.HOTKEY_KEY_BACKQUOTE),
    "QUOTE": list(mp.HOTKEY_KEY_QUOTE),
    "LCTRL": list(mp.HOTKEY_KEY_LCTRL),
    "RCTRL": list(mp.HOTKEY_KEY_RCTRL),
    "LALT": list(mp.HOTKEY_KEY_LALT),
    "RALT": list(mp.HOTKEY_KEY_RALT),
    "LSHIFT": list(mp.HOTKEY_KEY_LSHIFT),
    "RSHIFT": list(mp.HOTKEY_KEY_RSHIFT),
}


@dataclass(frozen=True)
class BindingEntry:
    key_string: str
    command_name: str
    args: Tuple[str, ...]
    command_string: str
    binding_id: str
    layer: str


def make_binding_id(layer: str, command_name: str, args: Tuple[str, ...]) -> str:
    parts = [layer, command_name]
    if args:
        parts.extend(args)
    return ".".join(parts)


def _expand_definitions(text: str, definitions: Dict[str, str]) -> str:
    for name, value in definitions.items():
        text = re.sub(r"(?<!\w)%s(?!\w)" % re.escape(name), value, text)
    return text


def parse_bindings_text(text: str, layer: str = "global") -> List[BindingEntry]:
    """解析 bindings 文本，展开 #define 宏。"""
    definitions: Dict[str, str] = {}
    entries: List[BindingEntry] = []
    for raw_line in preprocess(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#define "):
            try:
                _, name, value = line.split(" ", 2)
            except ValueError:
                continue
            definitions[name] = value
            continue
        if ":" not in line:
            continue
        key_string, command_string = line.split(":", 1)
        key_string = key_string.strip()
        command_string = _expand_definitions(command_string.strip(), definitions)
        parts = command_string.split()
        if not parts:
            continue
        command_name = parts[0]
        args = tuple(parts[1:])
        entries.append(
            BindingEntry(
                key_string=key_string,
                command_name=command_name,
                args=args,
                command_string=command_string,
                binding_id=make_binding_id(layer, command_name, args),
                layer=layer,
            )
        )
    return entries


def _default_primary_keys(
    entries: List[BindingEntry], catalog: List[Tuple[str, list]]
) -> Dict[str, str]:
    catalog_ids = {bid for bid, _ in catalog}
    defaults: Dict[str, str] = {}
    for entry in entries:
        if entry.binding_id in catalog_ids and entry.binding_id not in defaults:
            defaults[entry.binding_id] = entry.key_string
    return defaults


def load_overrides_data() -> dict:
    path = get_hotkey_overrides_path()
    _migrate_legacy_overrides_if_needed(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": _OVERRIDES_VERSION, "overrides": {}}
        data.setdefault("version", _OVERRIDES_VERSION)
        data.setdefault("overrides", {})
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": _OVERRIDES_VERSION, "overrides": {}}


def save_overrides_data(data: dict) -> None:
    path = get_hotkey_overrides_path()
    os.makedirs(HOTKEY_OVERRIDES_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_layer_overrides(layer: str = "global") -> Dict[str, str]:
    data = load_overrides_data()
    layer_map = data.get("overrides", {}).get(layer, {})
    if not isinstance(layer_map, dict):
        return {}
    return {str(k): str(v) for k, v in layer_map.items() if v}


def set_layer_override(layer: str, binding_id: str, key_string: Optional[str]) -> None:
    """设置或清除某功能的自定义键。key_string 为 None 表示恢复默认。"""
    data = load_overrides_data()
    overrides = data.setdefault("overrides", {})
    layer_map = overrides.setdefault(layer, {})
    if not isinstance(layer_map, dict):
        layer_map = {}
        overrides[layer] = layer_map

    default_key = get_default_key(binding_id, layer)
    if not key_string or key_string == default_key:
        layer_map.pop(binding_id, None)
    else:
        # 冲突：同一层内若其他功能已占用该键，清除其覆盖
        for other_id, other_key in list(layer_map.items()):
            if other_id != binding_id and other_key == key_string:
                del layer_map[other_id]
        layer_map[binding_id] = key_string

    if not layer_map:
        overrides.pop(layer, None)
    save_overrides_data(data)


def clear_layer_overrides(layer: str = "global") -> None:
    data = load_overrides_data()
    overrides = data.get("overrides", {})
    if layer in overrides:
        del overrides[layer]
        save_overrides_data(data)


def _read_bindings_source(layer: str) -> str:
    from .clientgame.interface_modes import (
        LEGACY_BINDINGS_FILE,
        MODE_FILES,
        _read_bindings_layer,
    )

    if layer == "classic":
        return _read_bindings_layer(LEGACY_BINDINGS_FILE)
    filename = MODE_FILES.get(layer)
    if not filename:
        return ""
    return _read_bindings_layer(filename)


def _read_global_bindings_source() -> str:
    return _read_bindings_source("global")


def get_all_default_keys(binding_id: str, layer: str = "global") -> List[str]:
    text = _read_bindings_source(layer)
    if not text:
        return []
    keys: List[str] = []
    for entry in parse_bindings_text(text, layer):
        if entry.binding_id == binding_id and entry.key_string not in keys:
            keys.append(entry.key_string)
    return keys


def get_alias_default_keys(binding_id: str, layer: str = "global") -> List[str]:
    primary = get_default_key(binding_id, layer)
    if primary is None:
        return []
    return [key for key in get_all_default_keys(binding_id, layer) if key != primary]


def get_effective_alias_key(
    binding_id: str, layer: str, alias_default_key: str
) -> str:
    override_id = make_alias_override_id(binding_id, alias_default_key)
    overrides = get_layer_overrides(layer)
    if override_id in overrides:
        return overrides[override_id]
    return alias_default_key


def set_layer_alias_override(
    layer: str,
    binding_id: str,
    alias_default_key: str,
    key_string: Optional[str],
) -> None:
    """设置或清除某别名键的自定义映射。"""
    override_id = make_alias_override_id(binding_id, alias_default_key)
    data = load_overrides_data()
    overrides = data.setdefault("overrides", {})
    layer_map = overrides.setdefault(layer, {})
    if not isinstance(layer_map, dict):
        layer_map = {}
        overrides[layer] = layer_map

    if not key_string or key_string == alias_default_key:
        layer_map.pop(override_id, None)
    else:
        for other_id, other_key in list(layer_map.items()):
            if other_id != override_id and other_key == key_string:
                del layer_map[other_id]
        layer_map[override_id] = key_string

    if not layer_map:
        overrides.pop(layer, None)
    save_overrides_data(data)


def get_default_key(binding_id: str, layer: str = "global") -> Optional[str]:
    from .hotkey_catalogs import get_layer_catalog

    catalog = get_layer_catalog(layer)
    text = _read_bindings_source(layer)
    if not text:
        return None
    entries = parse_bindings_text(text, layer)
    if catalog:
        defaults = _default_primary_keys(entries, catalog)
        if binding_id in defaults:
            return defaults[binding_id]
    for entry in entries:
        if entry.binding_id == binding_id:
            return entry.key_string
    return None


def get_effective_key(binding_id: str, layer: str = "global") -> Optional[str]:
    overrides = get_layer_overrides(layer)
    if binding_id in overrides:
        return overrides[binding_id]
    return get_default_key(binding_id, layer)


def apply_overrides_to_bindings_text(text: str, layer: str = "global") -> str:
    """按功能 ID 覆盖键位，移除被替换的主绑定键与别名键。"""
    from .hotkey_catalogs import get_layer_catalog, get_layer_variant_catalog

    overrides = get_layer_overrides(layer)
    if not overrides:
        return text

    catalog = get_layer_catalog(layer)
    variant_catalog = get_layer_variant_catalog(layer)
    entries = parse_bindings_text(text, layer)
    if not entries:
        return text

    default_primary = _default_primary_keys(entries, catalog)
    for bid, _label in variant_catalog:
        if bid not in default_primary:
            for entry in entries:
                if entry.binding_id == bid:
                    default_primary[bid] = entry.key_string
                    break

    primary_overrides, alias_overrides = parse_layer_override_map(overrides)
    all_new_keys = set(primary_overrides.values()) | set(alias_overrides.values())

    id_to_command: Dict[str, str] = {}
    for entry in entries:
        id_to_command.setdefault(entry.binding_id, entry.command_string)

    replaced: set = set()
    for bid, new_key in primary_overrides.items():
        default_key = default_primary.get(bid)
        if default_key:
            replaced.add((bid, default_key))
    for (bid, alias_default), _new_key in alias_overrides.items():
        replaced.add((bid, alias_default))

    kept: List[BindingEntry] = []
    for entry in entries:
        key = (entry.binding_id, entry.key_string)
        if key in replaced:
            continue
        if entry.key_string in all_new_keys:
            continue
        kept.append(entry)

    lines = [f"{e.key_string}: {e.command_string}" for e in kept]
    for bid, key_string in primary_overrides.items():
        command_string = id_to_command.get(bid)
        if command_string and key_string:
            lines.append(f"{key_string}: {command_string}")
    for (bid, _alias_default), key_string in alias_overrides.items():
        command_string = id_to_command.get(bid)
        if command_string and key_string:
            lines.append(f"{key_string}: {command_string}")
    return "\n".join(lines)


def key_string_to_msgs(key_string: Optional[str]) -> list:
    from . import msgparts as mp
    from .lib.msgs import literal_text_msg

    if not key_string:
        return list(mp.HOTKEY_UNBOUND)
    msgs: list = []
    for part in key_string.split():
        if part in _KEY_NAME_SPEECH:
            msgs.extend(_KEY_NAME_SPEECH[part])
        elif part.isdigit() or (part.startswith("F") and part[1:].isdigit()):
            msgs.extend(literal_text_msg(part))
        elif len(part) == 1:
            msgs.extend(literal_text_msg(part.upper()))
        else:
            msgs.extend(literal_text_msg(part))
    return msgs


def key_event_to_binding_string(e) -> Optional[str]:
    """将 pygame KEYDOWN 事件转为 bindings.txt 键名字符串。"""
    if e.key in _STANDALONE_MODIFIER_KEYS:
        return _PYGAME_KEY_NAMES.get(e.key)

    mods: List[str] = []
    if e.mod & KMOD_CTRL:
        mods.append("CTRL")
    # Prefer LSHIFT/RSHIFT over generic SHIFT when the side is known.
    left = bool(e.mod & KMOD_LSHIFT)
    right = bool(e.mod & KMOD_RSHIFT)
    try:
        import ctypes

        win_left = bool(ctypes.windll.user32.GetKeyState(0xA0) & 0x8000)
        win_right = bool(ctypes.windll.user32.GetKeyState(0xA1) & 0x8000)
        if win_left or win_right:
            left, right = win_left, win_right
    except Exception:
        pass
    if left and not right:
        mods.append("LSHIFT")
    elif right and not left:
        mods.append("RSHIFT")
    elif e.mod & KMOD_SHIFT:
        mods.append("SHIFT")
    if e.mod & KMOD_ALT:
        mods.append("ALT")

    if pygame.K_a <= e.key <= pygame.K_z:
        key_name = chr(ord("a") + e.key - pygame.K_a)
    elif e.key in _PYGAME_KEY_NAMES:
        key_name = _PYGAME_KEY_NAMES[e.key]
    elif getattr(e, "scancode", None) == pygame.KSCAN_BACKQUOTE:
        key_name = "BACKQUOTE"
    elif getattr(e, "scancode", None) == pygame.KSCAN_QUOTE:
        key_name = "QUOTE"
    else:
        return None

    if len(key_name) == 1:
        parts = mods + [key_name]
    else:
        parts = mods + [key_name.upper()]
    return " ".join(parts)


def find_conflicting_binding_id(
    layer: str, key_string: str, exclude_id: str
) -> Optional[str]:
    """返回同层内已占用该键的功能 ID（含主键、别名键、默认与覆盖）。"""
    from .hotkey_catalogs import get_layer_catalog, get_layer_variant_catalog

    if not key_string:
        return None
    exclude_binding_id, _ = split_override_id(exclude_id)
    seen: set = set()
    catalog_items = get_layer_catalog(layer) + get_layer_variant_catalog(layer)
    for binding_id, _label in catalog_items:
        if binding_id in seen:
            continue
        seen.add(binding_id)
        if binding_id == exclude_binding_id:
            continue
        if get_effective_key(binding_id, layer) == key_string:
            return binding_id
        for alias_default in get_alias_default_keys(binding_id, layer):
            alias_id = make_alias_override_id(binding_id, alias_default)
            if alias_id == exclude_id:
                continue
            if get_effective_alias_key(binding_id, layer, alias_default) == key_string:
                return alias_id
    return None


def layer_catalog_entries(layer: str) -> List[Tuple[str, list, Optional[str]]]:
    """返回 (binding_id, label_msgs, effective_key) 列表。"""
    from .hotkey_catalogs import get_layer_catalog

    result = []
    for binding_id, label in get_layer_catalog(layer):
        result.append((binding_id, label, get_effective_key(binding_id, layer)))
    return result


def binding_catalog_entries(
    catalog: List[Tuple[str, list]], layer: str
) -> List[Tuple[str, list, Optional[str]]]:
    """任意 catalog 列表的有效键条目。"""
    return [
        (binding_id, label, get_effective_key(binding_id, layer))
        for binding_id, label in catalog
    ]


def label_msgs_to_search_text(label_msgs: list) -> str:
    """将 catalog 标签转为可搜索的小写文本。"""
    from .lib import sound_cache
    from .lib.msgs import NB_ENCODE_SHIFT

    parts: List[str] = []
    for item in label_msgs:
        if isinstance(item, int):
            if item >= NB_ENCODE_SHIFT:
                n = item - NB_ENCODE_SHIFT
                parts.append(str(n))
                continue
            text = sound_cache.sounds.translate_sound_number(item)
            if text and not str(text).startswith("文本: "):
                parts.append(str(text).lower())
        elif isinstance(item, str):
            if item.startswith("文本: "):
                parts.append(item[4:].lower())
            else:
                parts.append(item.lower())
    return " ".join(parts)


def filter_catalog_entries(
    entries: List[Tuple[str, list, Optional[str]]], query: str
) -> List[Tuple[str, list, Optional[str]]]:
    """按搜索词过滤 catalog 条目（匹配标签或 binding_id）。"""
    q = query.strip().lower()
    if not q:
        return entries
    tokens = q.split()
    result = []
    for binding_id, label, effective_key in entries:
        haystack = label_msgs_to_search_text(label) + " " + binding_id.lower()
        if all(token in haystack for token in tokens):
            result.append((binding_id, label, effective_key))
    return result


def all_layer_catalog_entries(layer: str) -> List[Tuple[str, list, Optional[str]]]:
    """主 catalog 与高级变体合并列表。"""
    from .hotkey_catalogs import get_layer_variant_catalog

    primary = layer_catalog_entries(layer)
    primary_ids = {bid for bid, _, _ in primary}
    extras = binding_catalog_entries(
        [
            (bid, label)
            for bid, label in get_layer_variant_catalog(layer)
            if bid not in primary_ids
        ],
        layer,
    )
    return primary + extras


def layer_alias_catalog_entries(
    layer: str,
) -> List[Tuple[str, list, Optional[str], str, str]]:
    """返回 (override_id, label, effective_key, binding_id, alias_default_key)。"""
    from . import msgparts as mp
    from .hotkey_catalogs import get_layer_catalog, get_layer_variant_catalog, label_for_binding_id

    result: List[Tuple[str, list, Optional[str], str, str]] = []
    seen_bindings: set = set()
    for binding_id, _label in get_layer_catalog(layer) + get_layer_variant_catalog(layer):
        if binding_id in seen_bindings:
            continue
        seen_bindings.add(binding_id)
        alias_keys = get_alias_default_keys(binding_id, layer)
        if not alias_keys:
            continue
        function_label = label_for_binding_id(binding_id, layer)
        for alias_default in alias_keys:
            override_id = make_alias_override_id(binding_id, alias_default)
            choice_label = (
                function_label
                + mp.COMMA
                + list(mp.HOTKEY_ALIAS_DEFAULT)
                + key_string_to_msgs(alias_default)
            )
            result.append(
                (
                    override_id,
                    choice_label,
                    get_effective_alias_key(binding_id, layer, alias_default),
                    binding_id,
                    alias_default,
                )
            )
    return result


def export_overrides_json_string() -> str:
    """导出当前 mod 热键 JSON 字符串。"""
    return json.dumps(load_overrides_data(), ensure_ascii=False, indent=2)


def import_overrides_json_string(text: str, merge: bool = False) -> bool:
    """导入热键 JSON。merge=True 时合并 overrides 段。"""
    try:
        incoming = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return False
    if not isinstance(incoming, dict):
        return False
    if "overrides" in incoming and not isinstance(incoming["overrides"], dict):
        return False
    if merge:
        current = load_overrides_data()
        if "layered_hotkeys" in incoming:
            current["layered_hotkeys"] = incoming["layered_hotkeys"]
        incoming_overrides = incoming.get("overrides", {})
        if isinstance(incoming_overrides, dict):
            merged = current.setdefault("overrides", {})
            for layer, layer_map in incoming_overrides.items():
                if not isinstance(layer_map, dict):
                    continue
                target = merged.setdefault(layer, {})
                if not isinstance(target, dict):
                    target = {}
                    merged[layer] = target
                target.update({str(k): str(v) for k, v in layer_map.items() if v})
        save_overrides_data(current)
    else:
        data = {
            "version": incoming.get("version", _OVERRIDES_VERSION),
            "overrides": incoming.get("overrides", {}),
        }
        if "layered_hotkeys" in incoming:
            data["layered_hotkeys"] = incoming["layered_hotkeys"]
        save_overrides_data(data)
    return True


def capture_binding_key(prompt_msgs: list) -> Optional[str]:
    """等待玩家按下新键。返回键字符串；None 表示取消；空字符串表示清除绑定。"""
    import sys
    import time

    from .clientmedia import voice

    voice.item(list(prompt_msgs))
    pygame.event.clear([KEYDOWN])
    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        if e.type == KEYDOWN:
            if e.key == K_ESCAPE:
                return None
            if e.key in (K_BACKSPACE, K_DELETE):
                return ""
            key_string = key_event_to_binding_string(e)
            if key_string:
                voice.item(key_string_to_msgs(key_string))
                return key_string
        time.sleep(0.01)


def global_catalog_entries() -> List[Tuple[str, list, Optional[str]]]:
    """返回 global 层 (binding_id, label_msgs, effective_key) 列表。"""
    return layer_catalog_entries("global")
