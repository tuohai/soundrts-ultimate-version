"""Phase 3 经典单文件热键映射。"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_classic_catalog_has_default_keys():
    from soundrts.hotkey_catalogs import get_layer_catalog
    from soundrts.hotkey_editor import get_default_key

    missing = []
    for bid, _ in get_layer_catalog("classic"):
        if get_default_key(bid, "classic") is None:
            missing.append(bid)
    assert missing == []


def test_classic_worker_default_is_d():
    from soundrts.hotkey_editor import get_default_key

    assert get_default_key("classic.select_units.local.worker", "classic") == "d"


def test_classic_escape_not_ui_escape():
    from soundrts.hotkey_editor import get_default_key

    assert get_default_key("classic.escape", "classic") == "ESCAPE"
    assert get_default_key("global.ui_escape", "global") == "ESCAPE"


def test_legacy_bindings_apply_classic_overrides(monkeypatch):
    from soundrts.clientgame import interface_modes as im

    base = "d: select_units local worker\n"
    monkeypatch.setattr(im, "_read_bindings_layer", lambda filename: base)
    monkeypatch.setattr(im, "_legacy_mod_bindings", lambda: "")
    monkeypatch.setattr(im, "_custom_bindings_suffix", lambda: "")
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": (
            {"classic.select_units.local.worker": "w"} if layer == "classic" else {}
        ),
    )
    text = im._legacy_bindings_with_overrides()
    assert "w: select_units local worker" in text
    assert "d: select_units local worker" not in text


def test_mapping_layers_classic_when_legacy(monkeypatch):
    from soundrts.hotkey_catalogs import mapping_layers_for_current_scheme
    from soundrts import hotkey_editor as he

    monkeypatch.setattr(he, "get_layered_hotkeys_scheme", lambda: 0)
    assert mapping_layers_for_current_scheme() == ("classic",)
    monkeypatch.setattr(he, "get_layered_hotkeys_scheme", lambda: 1)
    assert mapping_layers_for_current_scheme()[0] == "global"


def test_classic_mapping_menu_includes_rpg_submenu():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    block = src.split("def layer_hotkeys_mapping_menu")[1].split("\ndef ")[0]
    assert 'layer == "classic"' in block
    assert "mp.RPG_INTERFACE" in block
    assert 'layer_hotkeys_mapping_menu, "rpg"' in block


def test_classic_scheme_skips_classic_layer_submenu():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    block = src.split("def hotkey_mapping_menu")[1].split("\ndef ")[0]
    assert 'layers == ("classic",)' in block
    assert "title=mp.HOTKEY_MAPPING" in block
    assert "prefix_choices=import_export" in block


def test_hotkey_mapping_menu_no_layered_only_block():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    assert "HOTKEY_MAPPING_LAYERED_ONLY" not in src
    assert "mapping_layers_for_current_scheme" in src


def test_phase3_tts():
    from soundrts import msgparts as mp

    ids = (mp.RESET_CLASSIC_HOTKEYS[0], mp.HOTKEY_CLASSIC_RESET[0])
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en)
        assert f"\n{tid} " in ("\n" + zh)
