"""Phase 2 热键映射：各界面层 catalog 与加载。"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_all_layer_catalogs_have_default_keys():
    from soundrts.hotkey_catalogs import LAYER_ORDER, get_layer_catalog
    from soundrts.hotkey_editor import get_default_key

    missing_by_layer = {}
    for layer in LAYER_ORDER:
        missing = []
        for bid, _ in get_layer_catalog(layer):
            if get_default_key(bid, layer) is None:
                missing.append(bid)
        if missing:
            missing_by_layer[layer] = missing
    assert missing_by_layer == {}


def test_unit_worker_default_key():
    from soundrts.hotkey_editor import get_default_key

    assert get_default_key("unit.select_units.local.worker", "unit") == "s"


def test_building_building1_default_key():
    from soundrts.hotkey_editor import get_default_key

    assert get_default_key("building.select_unit.1.building1", "building") == "d"


def test_command_order_index_default_key():
    from soundrts.hotkey_editor import get_default_key

    assert (
        get_default_key("command.select_order_index.1.inactive_included", "command")
        == "s"
    )


def test_apply_unit_layer_overrides(monkeypatch):
    from soundrts.clientgame import interface_modes as im

    base = "s: select_units local worker\n"
    monkeypatch.setattr(im, "_read_bindings_layer", lambda filename: base)
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": (
            {"unit.select_units.local.worker": "w"} if layer == "unit" else {}
        ),
    )
    text = im._bindings_layer_with_overrides("unit")
    assert "w: select_units local worker" in text
    assert "s: select_units local worker" not in text


def test_get_bindings_text_applies_mode_overrides(monkeypatch):
    from soundrts.clientgame import interface_modes as im

    def fake_read(filename):
        if filename == "global_bindings.txt":
            return "z: resource_status resource1\n"
        if filename == "unit_bindings.txt":
            return "s: select_units local worker\n"
        return ""

    monkeypatch.setattr(im, "_read_bindings_layer", fake_read)
    monkeypatch.setattr(im, "_legacy_mod_bindings", lambda: "")
    monkeypatch.setattr(im, "_custom_bindings_suffix", lambda: "")
    monkeypatch.setattr(
        "soundrts.hotkey_editor.get_layer_overrides",
        lambda layer="global": (
            {"unit.select_units.local.worker": "x"} if layer == "unit" else {}
        ),
    )
    merged = im.get_bindings_text("unit")
    assert "x: select_units local worker" in merged
    assert "s: select_units local worker" not in merged


def test_keyboard_slot_label_is_generic():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import keyboard_slot_label
    from soundrts.lib.msgs import NB_ENCODE_SHIFT

    assert keyboard_slot_label("worker") == list(mp.HOTKEY_SLOT_WORKER)
    assert keyboard_slot_label("soldier1") == list(mp.HOTKEY_SLOT_SOLDIER) + [
        NB_ENCODE_SHIFT + 1
    ]
    assert keyboard_slot_label("building3") == list(mp.HOTKEY_SLOT_BUILDING) + [
        NB_ENCODE_SHIFT + 3
    ]


def test_unit_catalog_uses_generic_slot_labels():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import get_layer_catalog
    from soundrts.lib.msgs import NB_ENCODE_SHIFT

    labels = {bid: label for bid, label in get_layer_catalog("unit")}
    assert labels["unit.select_units.local.worker"] == list(
        mp.HOTKEY_SLOT_WORKER
    ) + list(mp.HOTKEY_LOCAL_SELECT_ALL)
    assert labels["unit.select_units.local.soldier1"] == list(
        mp.HOTKEY_SLOT_SOLDIER
    ) + [NB_ENCODE_SHIFT + 1] + list(mp.HOTKEY_LOCAL_SELECT_ALL)


def test_group_catalog_labels_describe_portions():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import get_layer_catalog

    labels = {bid: label for bid, label in get_layer_catalog("unit")}
    assert labels["unit.group.1.local"] == list(mp.HOTKEY_SELECT_UNITS) + list(
        mp.HOTKEY_SELECT_ALL
    )
    assert labels["unit.group.2.local"] == list(mp.HOTKEY_SELECT_UNITS) + list(
        mp.HOTKEY_SELECT_HALF
    )
    assert labels["unit.recall_group.6"] == list(mp.HOTKEY_CONTROL_GROUP_1)
    assert labels["unit.recall_group.7"] == list(mp.HOTKEY_CONTROL_GROUP_2)
    assert labels["unit.recall_group.8"] == list(mp.HOTKEY_CONTROL_GROUP_3)
    assert labels["unit.recall_group.9"] == list(mp.HOTKEY_CONTROL_GROUP_4)


def test_classic_catalog_covers_all_legacy_primary_bindings():
    from pathlib import Path

    from soundrts.hotkey_editor import parse_bindings_text
    from soundrts.hotkey_catalogs import get_layer_catalog

    legacy = Path("res/ui/legacy_bindings.txt").read_text(encoding="utf-8")
    catalog_ids = {bid for bid, _ in get_layer_catalog("classic")}
    missing = sorted(
        {
            e.binding_id
            for e in parse_bindings_text(legacy, "classic")
            if e.binding_id not in catalog_ids
        }
    )
    assert missing == []


def test_classic_catalog_includes_group_store_and_objectives_prev():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import get_layer_catalog
    from soundrts.lib.msgs import NB_ENCODE_SHIFT

    labels = {bid: label for bid, label in get_layer_catalog("classic")}
    assert "classic.set_group.6" in labels
    assert labels["classic.set_group.6"] == list(mp.HOTKEY_SAVE_GROUP) + [
        NB_ENCODE_SHIFT + 1
    ]
    assert "classic.append_group.6" in labels
    assert "classic.objectives.-1" in labels
    assert labels["classic.objectives.-1"] == list(mp.HOTKEY_OBJECTIVES_PREV)
    assert labels["classic.unit_status"] == list(mp.HOTKEY_UNIT_STATUS)
    assert labels["classic.immersion"] == list(mp.HOTKEY_VISUAL_IMMERSION)
    assert labels["classic.fullscreen"] == list(mp.HOTKEY_VISUAL_TOGGLE)
    assert labels["classic.toggle_cheatmode"] == list(mp.HOTKEY_TOGGLE_CHEATMODE)


def test_key_string_to_msgs_avoids_tts_digit_ids():
    from soundrts import msgparts as mp
    from soundrts.hotkey_editor import key_string_to_msgs
    from soundrts.lib.msgs import LITERAL_TEXT_PREFIX

    assert key_string_to_msgs("1") == [LITERAL_TEXT_PREFIX + "1"]
    assert key_string_to_msgs("6") == [LITERAL_TEXT_PREFIX + "6"]
    assert key_string_to_msgs("CTRL 1") == list(mp.HOTKEY_KEY_CTRL) + [
        LITERAL_TEXT_PREFIX + "1"
    ]
    assert key_string_to_msgs("d") == [LITERAL_TEXT_PREFIX + "D"]
    assert key_string_to_msgs("F1") == [LITERAL_TEXT_PREFIX + "F1"]
    assert key_string_to_msgs("BACKSLASH") == list(mp.HOTKEY_KEY_BACKSLASH)


def test_hotkey_mapping_menu_lists_all_layers():
    src = (ROOT / "soundrts" / "hotkey_remapping_menu.py").read_text(encoding="utf-8")
    assert "mapping_layers_for_current_scheme" in src
    catalogs = (ROOT / "soundrts" / "hotkey_catalogs.py").read_text(encoding="utf-8")
    assert "LAYER_ORDER" in catalogs
    assert "classic" in catalogs


def test_phase2_tts():
    from soundrts import msgparts as mp

    ids = (
        mp.MAP_BROWSE_INTERFACE[0],
        mp.RESET_LAYER_HOTKEYS[0],
        mp.HOTKEY_LAYER_RESET[0],
    )
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    for tid in ids:
        assert f"\n{tid} " in ("\n" + en)
        assert f"\n{tid} " in ("\n" + zh)


def test_skill_layer_twelve_skill_hotkeys():
    from soundrts import msgparts as mp
    from soundrts.hotkey_catalogs import get_layer_catalog
    from soundrts.hotkey_editor import get_default_key
    from soundrts.lib.msgs import NB_ENCODE_SHIFT

    skill_ids = [bid for bid, _ in get_layer_catalog("skill")]
    assert skill_ids == [
        "skill.select_order.1.inactive_included",
        "skill.select_order.-1.inactive_included",
    ]
    rpg_ids = [
        bid
        for bid, _ in get_layer_catalog("rpg")
        if bid.startswith("rpg.rpg_skill_") and bid != "rpg.rpg_skill_list"
    ]
    assert len(rpg_ids) == 12
    labels = {bid: label for bid, label in get_layer_catalog("rpg")}
    assert labels["rpg.rpg_skill_0"] == list(mp.HOTKEY_SKILL_LABEL) + [
        NB_ENCODE_SHIFT + 10
    ]
    assert labels["rpg.rpg_skill_11"] == list(mp.HOTKEY_SKILL_LABEL) + [
        NB_ENCODE_SHIFT + 12
    ]
    assert get_default_key("rpg.rpg_skill_10", "rpg") == "MINUS"
    assert get_default_key("rpg.rpg_skill_11", "rpg") == "EQUALS"
    assert get_default_key("rpg.rpg_skill_list", "rpg") == "ALT SLASH"
    assert get_default_key("rpg.rpg_auto_attack", "rpg") == "CTRL A"
