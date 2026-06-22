"""Phase 4 热键映射：搜索、高级变体、导入导出。"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_global_variant_catalog_non_empty():
    from soundrts.hotkey_catalogs import get_layer_variant_catalog

    variants = get_layer_variant_catalog("global")
    assert len(variants) >= 10
    ids = {bid for bid, _ in variants}
    assert "global.validate.queue_order" in ids
    assert "global.select_square.0.5" in ids


def test_classic_has_no_variants():
    from soundrts.hotkey_catalogs import get_layer_variant_catalog

    assert get_layer_variant_catalog("classic") == []


def test_variant_default_keys():
    from soundrts.hotkey_catalogs import get_layer_variant_catalog
    from soundrts.hotkey_editor import get_default_key

    for bid, _ in get_layer_variant_catalog("global"):
        assert get_default_key(bid, "global") is not None, bid


def test_filter_catalog_entries_matches_label():
    from soundrts.hotkey_editor import (
        filter_catalog_entries,
        layer_catalog_entries,
        label_msgs_to_search_text,
    )

    entries = layer_catalog_entries("global")
    text = label_msgs_to_search_text(entries[0][1])
    assert text
    matched = filter_catalog_entries(entries, text.split()[0])
    assert any(e[0] == entries[0][0] for e in matched)


def test_apply_overrides_variant_binding(monkeypatch):
    from soundrts.hotkey_editor import apply_overrides_to_bindings_text

    base = (
        "SHIFT RETURN: validate queue_order\n"
        "RETURN: validate\n"
    )
    overrides = {"global.validate.queue_order": "y"}
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": overrides if layer == "global" else {},
    )
    result = apply_overrides_to_bindings_text(base, "global")
    assert "y: validate queue_order" in result
    assert "SHIFT RETURN: validate queue_order" not in result


def test_export_import_roundtrip(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    sample = {
        "version": 1,
        "layered_hotkeys": 1,
        "overrides": {"global": {"global.volume": "HOME"}},
    }
    path = tmp_path / "_base.json"
    path.write_text(json.dumps(sample), encoding="utf-8")
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(path))
    exported = he.export_overrides_json_string()
    path.write_text('{"version":1,"overrides":{}}', encoding="utf-8")
    assert he.import_overrides_json_string(exported, merge=False)
    data = he.load_overrides_data()
    assert data["overrides"]["global"]["global.volume"] == "HOME"


def test_import_merge_preserves_existing(tmp_path, monkeypatch):
    from soundrts import hotkey_editor as he

    path = tmp_path / "_base.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "overrides": {
                    "global": {"global.volume": "HOME"},
                    "unit": {"unit.select_units.local.worker": "d"},
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(he, "get_hotkey_overrides_path", lambda: str(path))
    incoming = json.dumps(
        {"overrides": {"global": {"global.console": "BACKQUOTE"}}}
    )
    assert he.import_overrides_json_string(incoming, merge=True)
    data = he.load_overrides_data()
    assert data["overrides"]["global"]["global.volume"] == "HOME"
    assert data["overrides"]["global"]["global.console"] == "BACKQUOTE"
    assert data["overrides"]["unit"]["unit.select_units.local.worker"] == "d"


def test_import_invalid_json():
    from soundrts.hotkey_editor import import_overrides_json_string

    assert import_overrides_json_string("{bad", merge=False) is False


def test_variant_label_uses_msgparts():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import variant_label_for_binding_id

    label = variant_label_for_binding_id("global.validate.queue_order", "global")
    assert mp.HOTKEY_VALIDATE_COMMAND[0] in label
    assert mp.HOTKEY_VALIDATE_QUEUE[0] in label


def test_phase4_tts():
    from soundrts import msgparts as mp

    ids = (
        mp.HOTKEY_SEARCH[0],
        mp.HOTKEY_EXPORT[0],
        mp.HOTKEY_IMPORT_SUCCESS[0],
        mp.HOTKEY_ADVANCED_VARIANTS[0],
    )
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en)
        assert f"\n{tid} " in ("\n" + zh)


def test_remapping_menu_has_phase4_entries():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    assert "HOTKEY_SEARCH" in src
    assert "HOTKEY_EXPORT" in src
    assert "HOTKEY_ADVANCED_VARIANTS" in src
