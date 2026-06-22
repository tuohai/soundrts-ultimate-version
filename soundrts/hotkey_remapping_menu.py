"""热键映射菜单 — 分层界面各层与经典单文件方案。"""

from __future__ import annotations

import pygame
from pygame.locals import K_RETURN, K_KP_ENTER, KEYDOWN, QUIT

from . import msgparts as mp
from .clientmedia import voice
from .clientmenu import CLOSE_MENU, Menu, _clipboard_set_text, input_string, input_text
from .hotkey_catalogs import (
    get_layer_variant_catalog,
    label_for_binding_id,
    mapping_layers_for_current_scheme,
)
from .hotkey_editor import (
    all_layer_catalog_entries,
    binding_catalog_entries,
    capture_binding_key,
    clear_layer_overrides,
    export_overrides_json_string,
    filter_catalog_entries,
    find_conflicting_binding_id,
    get_default_key,
    get_effective_alias_key,
    get_effective_key,
    import_overrides_json_string,
    layer_alias_catalog_entries,
    layer_catalog_entries,
    key_string_to_msgs,
    make_alias_override_id,
    set_layer_alias_override,
    set_layer_override,
    split_override_id,
)

_LAYER_MENU_TITLES = {
    "global": mp.GLOBAL_HOTKEYS_LAYER,
    "unit": mp.UNIT_SELECTION_INTERFACE,
    "building": mp.BUILDING_SELECTION_INTERFACE,
    "command": mp.COMMAND_INTERFACE,
    "skill": mp.SKILL_INTERFACE,
    "rpg": mp.RPG_INTERFACE,
    "help": mp.HELP_QUERY_INTERFACE,
    "map": mp.MAP_BROWSE_INTERFACE,
    "diplomacy": mp.DIPLOMACY_INTERFACE,
    "classic": mp.CLASSIC_HOTKEYS,
}


def _wait_confirm() -> bool:
    import sys
    import time

    pygame.event.clear([KEYDOWN])
    while True:
        e = pygame.event.poll()
        if e.type == QUIT:
            sys.exit()
        if e.type == KEYDOWN:
            if e.key in (K_RETURN, K_KP_ENTER):
                return True
            if e.key == pygame.K_ESCAPE:
                return False
        time.sleep(0.01)


def _label_for_override_id(override_id: str, layer: str) -> list:
    binding_id, alias_default = split_override_id(override_id)
    if alias_default is not None:
        return (
            label_for_binding_id(binding_id, layer)
            + mp.COMMA
            + list(mp.HOTKEY_ALIAS_DEFAULT)
            + key_string_to_msgs(alias_default)
        )
    return label_for_binding_id(binding_id, layer)


def _remap_alias_binding(
    layer: str, binding_id: str, alias_default_key: str
) -> None:
    override_id = make_alias_override_id(binding_id, alias_default_key)
    current_key = get_effective_alias_key(binding_id, layer, alias_default_key)
    label = _label_for_override_id(override_id, layer)
    voice.item(
        label
        + mp.COMMA
        + mp.HOTKEY_CURRENT_KEY
        + key_string_to_msgs(current_key)
        + mp.COMMA
        + mp.PRESS_ENTER_TO_REMAP
    )

    new_key = capture_binding_key(
        mp.HOTKEY_PRESS_NEW_KEY + mp.HOTKEY_CAPTURE_HINT
    )
    if new_key is None:
        voice.item(mp.BEEP)
        return

    if new_key == "":
        set_layer_alias_override(layer, binding_id, alias_default_key, None)
        voice.item(mp.HOTKEY_SAVED)
        return

    conflict_id = find_conflicting_binding_id(layer, new_key, override_id)
    if conflict_id:
        conflict_label = _label_for_override_id(conflict_id, layer)
        voice.item(
            mp.HOTKEY_KEY_IN_USE
            + conflict_label
            + mp.COMMA
            + mp.HOTKEY_CONFIRM_REPLACE
        )
        if not _wait_confirm():
            voice.item(mp.BEEP)
            return

    if new_key == alias_default_key:
        set_layer_alias_override(layer, binding_id, alias_default_key, None)
    else:
        set_layer_alias_override(layer, binding_id, alias_default_key, new_key)
    voice.item(mp.HOTKEY_SAVED + mp.HOTKEY_SET_TO + key_string_to_msgs(new_key))


def _remap_binding(layer: str, binding_id: str) -> None:
    current_key = get_effective_key(binding_id, layer)
    label = label_for_binding_id(binding_id, layer)
    voice.item(
        label
        + mp.COMMA
        + mp.HOTKEY_CURRENT_KEY
        + key_string_to_msgs(current_key)
        + mp.COMMA
        + mp.PRESS_ENTER_TO_REMAP
    )

    new_key = capture_binding_key(
        mp.HOTKEY_PRESS_NEW_KEY + mp.HOTKEY_CAPTURE_HINT
    )
    if new_key is None:
        voice.item(mp.BEEP)
        return

    if new_key == "":
        set_layer_override(layer, binding_id, None)
        voice.item(mp.HOTKEY_SAVED)
        return

    conflict_id = find_conflicting_binding_id(layer, new_key, binding_id)
    if conflict_id:
        conflict_label = label_for_binding_id(conflict_id, layer)
        voice.item(
            mp.HOTKEY_KEY_IN_USE
            + conflict_label
            + mp.COMMA
            + mp.HOTKEY_CONFIRM_REPLACE
        )
        if not _wait_confirm():
            voice.item(mp.BEEP)
            return

    default_key = get_default_key(binding_id, layer)
    if new_key == default_key:
        set_layer_override(layer, binding_id, None)
    else:
        set_layer_override(layer, binding_id, new_key)
    voice.item(mp.HOTKEY_SAVED + mp.HOTKEY_SET_TO + key_string_to_msgs(new_key))


def _reset_layer_hotkeys(layer: str) -> None:
    clear_layer_overrides(layer)
    if layer == "global":
        voice.item(mp.HOTKEY_GLOBAL_RESET)
    elif layer == "classic":
        voice.item(mp.HOTKEY_CLASSIC_RESET)
    else:
        voice.item(mp.HOTKEY_LAYER_RESET)


def _reset_label_for_layer(layer: str):
    if layer == "global":
        return mp.RESET_GLOBAL_HOTKEYS
    if layer == "classic":
        return mp.RESET_CLASSIC_HOTKEYS
    return mp.RESET_LAYER_HOTKEYS


def _catalog_to_choices(
    catalog_entries, layer: str
) -> list:
    choices = []
    for binding_id, label, effective_key in catalog_entries:
        choice_label = (
            label
            + mp.COMMA
            + mp.HOTKEY_CURRENT_KEY
            + key_string_to_msgs(effective_key)
        )
        choices.append((choice_label, (_remap_binding, layer, binding_id)))
    return choices


def _run_binding_list_menu(layer: str, title, catalog_entries) -> None:
    choices = _catalog_to_choices(catalog_entries, layer)
    choices.append((_reset_label_for_layer(layer), (_reset_layer_hotkeys, layer)))
    choices.append((mp.BACK, CLOSE_MENU))
    Menu(title, choices, menu_type="submenu").loop()


def _search_hotkeys_menu(layer: str) -> None:
    query = input_string(
        msg=list(mp.HOTKEY_SEARCH_PROMPT),
        pattern=r"^[\x20-\x7E\u4e00-\u9fff]$",
        default="",
        spell=False,
        max_length=40,
    )
    if query is None:
        return
    query = query.strip()
    if not query:
        return
    all_entries = all_layer_catalog_entries(layer)
    filtered = filter_catalog_entries(all_entries, query)
    if not filtered:
        voice.item(mp.HOTKEY_SEARCH_NO_RESULTS)
        return
    _run_binding_list_menu(layer, mp.HOTKEY_SEARCH, filtered)


def _variant_hotkeys_menu(layer: str) -> None:
    variants = get_layer_variant_catalog(layer)
    if not variants:
        voice.item(mp.HOTKEY_SEARCH_NO_RESULTS)
        return
    entries = binding_catalog_entries(variants, layer)
    _run_binding_list_menu(layer, mp.HOTKEY_ADVANCED_VARIANTS, entries)


def _alias_hotkeys_menu(layer: str) -> None:
    alias_entries = layer_alias_catalog_entries(layer)
    if not alias_entries:
        voice.item(mp.HOTKEY_SEARCH_NO_RESULTS)
        return
    choices = []
    for override_id, label, effective_key, binding_id, alias_default in alias_entries:
        choice_label = (
            label
            + mp.COMMA
            + mp.HOTKEY_CURRENT_KEY
            + key_string_to_msgs(effective_key)
        )
        choices.append(
            (
                choice_label,
                (_remap_alias_binding, layer, binding_id, alias_default),
            )
        )
    choices.append((mp.BACK, CLOSE_MENU))
    Menu(mp.HOTKEY_ALIAS_KEYS, choices, menu_type="submenu").loop()


def layer_hotkeys_mapping_menu(layer: str, *, title=None, prefix_choices=None):
    """列出指定层热键并允许逐项修改。"""
    if title is None:
        title = _LAYER_MENU_TITLES.get(layer, [layer])
    voice.item(mp.HOTKEY_SEARCH_HINT)
    choices = []
    if prefix_choices:
        choices.extend(prefix_choices)
    choices.append((mp.HOTKEY_SEARCH, (_search_hotkeys_menu, layer)))
    if get_layer_variant_catalog(layer):
        choices.append((mp.HOTKEY_ADVANCED_VARIANTS, (_variant_hotkeys_menu, layer)))
    if layer_alias_catalog_entries(layer):
        choices.append((mp.HOTKEY_ALIAS_KEYS, (_alias_hotkeys_menu, layer)))
    if layer == "classic":
        choices.append(
            (mp.RPG_INTERFACE, (layer_hotkeys_mapping_menu, "rpg"))
        )
    for binding_id, label, effective_key in layer_catalog_entries(layer):
        choice_label = (
            label
            + mp.COMMA
            + mp.HOTKEY_CURRENT_KEY
            + key_string_to_msgs(effective_key)
        )
        choices.append((choice_label, (_remap_binding, layer, binding_id)))
    choices.append((_reset_label_for_layer(layer), (_reset_layer_hotkeys, layer)))
    choices.append((mp.BACK, CLOSE_MENU))
    Menu(title, choices, menu_type="submenu").loop()


def global_hotkeys_mapping_menu():
    return layer_hotkeys_mapping_menu("global")


def _export_hotkeys() -> None:
    text = export_overrides_json_string()
    if _clipboard_set_text(text):
        voice.item(mp.HOTKEY_EXPORTED)
    else:
        voice.item(mp.BEEP)


def _import_hotkeys_merge() -> None:
    _import_hotkeys(merge=True)


def _import_hotkeys_replace() -> None:
    _import_hotkeys(merge=False)


def _import_hotkeys(merge: bool) -> None:
    text = input_text(
        msg=list(mp.HOTKEY_IMPORT),
        default="",
        max_length=200000,
    )
    if text is None:
        return
    if import_overrides_json_string(text.strip(), merge=merge):
        voice.item(mp.HOTKEY_IMPORT_SUCCESS)
    else:
        voice.item(mp.HOTKEY_IMPORT_FAILED)


def _import_hotkeys_menu() -> None:
    choices = [
        (mp.HOTKEY_IMPORT_MERGE, (_import_hotkeys_merge,)),
        (mp.HOTKEY_IMPORT_REPLACE, (_import_hotkeys_replace,)),
        (mp.BACK, CLOSE_MENU),
    ]
    Menu(mp.HOTKEY_IMPORT, choices, menu_type="submenu").loop()


def announce_hotkey_overrides_mod() -> None:
    """进入热键相关菜单前播报当前 mod 配置（播完后再开子菜单，避免被覆盖）。"""
    from .hotkey_editor import current_hotkey_overrides_mod_key, hotkey_mod_label_msgs

    voice.menu(
        mp.HOTKEY_OVERRIDES_FOR_MOD
        + hotkey_mod_label_msgs(current_hotkey_overrides_mod_key())
    )


def hotkey_mapping_menu():
    """按键映射入口：按当前热键方案列出可编辑层。"""
    announce_hotkey_overrides_mod()
    layers = mapping_layers_for_current_scheme()
    import_export = [
        (mp.HOTKEY_EXPORT, (_export_hotkeys,)),
        (mp.HOTKEY_IMPORT, (_import_hotkeys_menu,)),
    ]
    if layers == ("classic",):
        layer_hotkeys_mapping_menu(
            "classic",
            title=mp.HOTKEY_MAPPING,
            prefix_choices=import_export,
        )
        return
    choices = list(import_export)
    for layer in layers:
        title = _LAYER_MENU_TITLES.get(layer, [layer])
        choices.append((title, (layer_hotkeys_mapping_menu, layer)))
    choices.append((mp.BACK, CLOSE_MENU))
    Menu(mp.HOTKEY_MAPPING, choices, menu_type="submenu").loop()
