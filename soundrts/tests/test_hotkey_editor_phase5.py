"""Phase 5 热键映射：别名键独立映射。"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_alias_override_id_roundtrip():
    from soundrts.hotkey_editor import (
        decode_alias_key_token,
        encode_alias_key_token,
        make_alias_override_id,
        split_override_id,
    )

    assert encode_alias_key_token("CTRL KP_ENTER") == "CTRL+KP_ENTER"
    assert decode_alias_key_token("CTRL+KP_ENTER") == "CTRL KP_ENTER"
    oid = make_alias_override_id("global.validate.imperative", "CTRL KP_ENTER")
    assert oid == "global.validate.imperative@CTRL+KP_ENTER"
    bid, alias = split_override_id(oid)
    assert bid == "global.validate.imperative"
    assert alias == "CTRL KP_ENTER"


def test_examine_has_rctrl_alias():
    from soundrts.hotkey_editor import get_alias_default_keys

    aliases = get_alias_default_keys("global.examine", "global")
    assert aliases == ["RCTRL"]


def test_validate_has_kp_enter_alias():
    from soundrts.hotkey_editor import get_alias_default_keys

    aliases = get_alias_default_keys("global.validate", "global")
    assert "KP_ENTER" in aliases


def test_apply_overrides_alias_independent_of_primary(monkeypatch):
    from soundrts.hotkey_editor import (
        apply_overrides_to_bindings_text,
        make_alias_override_id,
    )

    base = "LCTRL: examine\nRCTRL: examine\n"
    overrides = {
        make_alias_override_id("global.examine", "RCTRL"): "F1",
    }
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": overrides if layer == "global" else {},
    )
    result = apply_overrides_to_bindings_text(base, "global")
    assert "LCTRL: examine" in result
    assert "RCTRL: examine" not in result
    assert "F1: examine" in result


def test_apply_overrides_primary_independent_of_alias(monkeypatch):
    from soundrts.hotkey_editor import apply_overrides_to_bindings_text

    base = "LCTRL: examine\nRCTRL: examine\n"
    overrides = {"global.examine": "F2"}
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": overrides if layer == "global" else {},
    )
    result = apply_overrides_to_bindings_text(base, "global")
    assert "F2: examine" in result
    assert "LCTRL: examine" not in result
    assert "RCTRL: examine" in result


def test_alias_catalog_lists_examine_rctrl():
    from soundrts.hotkey_editor import layer_alias_catalog_entries

    entries = layer_alias_catalog_entries("global")
    ids = {item[0] for item in entries}
    assert "global.examine@RCTRL" in ids


def test_classic_alias_catalog_includes_kp_enter():
    from soundrts.hotkey_editor import layer_alias_catalog_entries

    entries = layer_alias_catalog_entries("classic")
    assert any("validate@KP_ENTER" in item[0] for item in entries)


def test_set_alias_override_persisted(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    path = tmp_path / "_base.json"
    path.write_text(json.dumps({"version": 1, "overrides": {}}), encoding="utf-8")
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(path))
    he.set_layer_alias_override("global", "global.examine", "RCTRL", "F3")
    data = he.load_overrides_data()
    assert data["overrides"]["global"]["global.examine@RCTRL"] == "F3"
    assert he.get_effective_alias_key("global.examine", "global", "RCTRL") == "F3"


def test_find_conflict_skips_same_binding_family():
    from soundrts.hotkey_editor import find_conflicting_binding_id

    assert (
        find_conflicting_binding_id("global", "RCTRL", "global.examine") is None
    )


def test_phase5_tts():
    from soundrts import msgparts as mp

    ids = (mp.HOTKEY_ALIAS_KEYS[0], mp.HOTKEY_ALIAS_DEFAULT[0])
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en)
        assert f"\n{tid} " in ("\n" + zh)


def test_remapping_menu_has_alias_entry():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    assert "HOTKEY_ALIAS_KEYS" in src
    assert "_alias_hotkeys_menu" in src
