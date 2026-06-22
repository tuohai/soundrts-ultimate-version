"""Phase 1 热键映射编辑器测试。"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_parse_bindings_expands_define():
    from soundrts.hotkey_editor import parse_bindings_text, make_binding_id

    text = """
#define SOLDIER soldier1 soldier2
d: select_units local SOLDIER
"""
    entries = parse_bindings_text(text, "global")
    assert len(entries) == 1
    assert entries[0].command_string == "select_units local soldier1 soldier2"
    assert entries[0].binding_id == make_binding_id(
        "global", "select_units", ("local", "soldier1", "soldier2")
    )


def test_make_binding_id():
    from soundrts.hotkey_editor import make_binding_id

    assert make_binding_id("global", "resource_status", ("resource1",)) == (
        "global.resource_status.resource1"
    )


def test_apply_overrides_replaces_primary_key(monkeypatch):
    from soundrts.hotkey_editor import apply_overrides_to_bindings_text

    base = "z: resource_status resource1\nx: resource_status resource2"
    overrides = {"global.resource_status.resource1": "y"}
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": overrides if layer == "global" else {},
    )
    result = apply_overrides_to_bindings_text(base, "global")
    assert "y: resource_status resource1" in result
    assert "z: resource_status resource1" not in result
    assert "x: resource_status resource2" in result


def test_key_event_to_binding_string_letter_and_mods():
    import pygame
    from pygame.locals import KMOD_CTRL, KMOD_SHIFT

    from soundrts.hotkey_editor import key_event_to_binding_string

    class E:
        pass

    e = E()
    e.key = pygame.K_d
    e.mod = KMOD_CTRL | KMOD_SHIFT
    e.scancode = 0
    assert key_event_to_binding_string(e) == "CTRL SHIFT d"

    e2 = E()
    e2.key = pygame.K_F1
    e2.mod = 0
    e2.scancode = 0
    assert key_event_to_binding_string(e2) == "F1"


def test_key_event_to_binding_string_standalone_ctrl():
    import pygame

    from soundrts.hotkey_editor import key_event_to_binding_string

    class E:
        pass

    e = E()
    e.key = pygame.K_LCTRL
    e.mod = 0
    e.scancode = 0
    assert key_event_to_binding_string(e) == "LCTRL"


def test_load_save_overrides(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    mod_dir.mkdir()
    path = mod_dir / "_base.json"
    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(path)
    )
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(path))

    he.set_layer_override("global", "global.resource_status.resource1", "y")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["overrides"]["global"]["global.resource_status.resource1"] == "y"

    he.set_layer_override("global", "global.resource_status.resource1", None)
    data2 = json.loads(path.read_text(encoding="utf-8"))
    assert "global" not in data2.get("overrides", {})


def test_clear_layer_overrides(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    mod_dir = tmp_path / "hotkey_overrides"
    mod_dir.mkdir()
    path = mod_dir / "_base.json"
    monkeypatch.setattr(he, "HOTKEY_OVERRIDES_DIR", str(mod_dir))
    monkeypatch.setattr(he, "current_hotkey_overrides_mod_key", lambda: "_base")
    monkeypatch.setattr(
        he, "current_hotkey_overrides_path", lambda: str(path)
    )
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(path))

    he.set_layer_override("global", "global.resource_status.resource1", "y")
    he.clear_layer_overrides("global")
    assert he.get_layer_overrides("global") == {}


def test_global_bindings_source_applies_overrides(monkeypatch):
    from soundrts.clientgame import interface_modes as im

    monkeypatch.setattr(
        im,
        "_read_bindings_layer",
        lambda filename: "z: resource_status resource1\n",
    )
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": {"global.resource_status.resource1": "q"},
    )
    text = im._global_bindings_with_overrides()
    assert "q: resource_status resource1" in text
    assert "z: resource_status resource1" not in text


def test_hotkey_mapping_in_options_menu():
    src = (ROOT / "soundrts" / "clientmain.py").read_text(encoding="utf-8")
    options = src.split("def options_menu")[1].split("\ndef ")[0]
    assert "mp.HOTKEY_MAPPING" in options
    assert "hotkey_mapping_menu" in options
    hotkeys = src.split("def hotkeys_menu")[1].split("\ndef ")[0]
    assert "mp.HOTKEY_MAPPING" not in hotkeys


def test_hotkey_submenus_return_to_options_not_main():
    remapping = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    hotkey_map = remapping.split("def hotkey_mapping_menu")[1].split("\ndef ")[0]
    layer_map = remapping.split("def layer_hotkeys_mapping_menu")[1].split("\ndef ")[0]
    binding_list = remapping.split("def _run_binding_list_menu")[1].split("\ndef ")[0]
    alias_map = remapping.split("def _alias_hotkeys_menu")[1].split("\ndef ")[0]
    import_map = remapping.split("def _import_hotkeys_menu")[1].split("\ndef ")[0]
    assert ".loop()" in hotkey_map
    assert ".loop()" in layer_map
    assert ".loop()" in binding_list
    assert ".loop()" in alias_map
    assert ".loop()" in import_map
    assert "return CLOSE_MENU" not in hotkey_map
    assert "return CLOSE_MENU" not in layer_map
    assert "mapping_layers_for_current_scheme" in hotkey_map
    assert ".run()" not in layer_map
    assert ".run()" not in binding_list
    assert ".run()" not in alias_map
    assert ".run()" not in import_map


def test_hotkey_mapping_tts():
    from soundrts import msgparts as mp

    ids = (
        mp.HOTKEY_MAPPING[0],
        mp.GLOBAL_HOTKEYS_LAYER[0],
        mp.HOTKEY_SAVED[0],
        mp.HOTKEY_MAPPING_LAYERED_ONLY[0],
    )
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en), f"ui/tts.txt missing {tid}"
        assert f"\n{tid} " in ("\n" + zh), f"ui-zh/tts.txt missing {tid}"


def test_global_catalog_covers_resource1():
    from soundrts.hotkey_editor import GLOBAL_PRIMARY_CATALOG, get_default_key

    ids = [bid for bid, _ in GLOBAL_PRIMARY_CATALOG]
    assert "global.resource_status.resource1" in ids
    assert get_default_key("global.resource_status.resource1") == "z"
