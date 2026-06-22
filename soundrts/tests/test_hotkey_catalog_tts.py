"""按键映射 catalog 标签 TTS 覆盖。"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _collect_tts_ids(parts: list) -> set:
    from soundrts.lib.msgs import NB_ENCODE_SHIFT

    ids = set()
    for item in parts:
        if isinstance(item, int):
            if item >= NB_ENCODE_SHIFT:
                continue
            ids.add(item)
        elif isinstance(item, list):
            ids.update(_collect_tts_ids(item))
        elif isinstance(item, str) and item.startswith("文本: "):
            continue
    return ids


def _all_catalog_tts_ids():
    from soundrts.hotkey_catalogs import LAYER_ORDER, get_layer_catalog

    ids = set()
    for layer in LAYER_ORDER + ("classic", "global"):
        for _bid, label in get_layer_catalog(layer):
            ids.update(_collect_tts_ids(label))
    from soundrts import msgparts as mp

    ids.add(mp.HOTKEY_MOD_NONE[0])
    return ids


def test_hotkey_catalog_tts_coverage():
    en = (ROOT / "res" / "ui" / "tts.txt").read_text(encoding="utf-8")
    zh = (ROOT / "res" / "ui-zh" / "tts.txt").read_text(encoding="utf-8")
    missing_en = []
    missing_zh = []
    for tid in sorted(_all_catalog_tts_ids()):
        needle = f"\n{tid} "
        if needle not in ("\n" + en):
            missing_en.append(tid)
        if needle not in ("\n" + zh):
            missing_zh.append(tid)
    assert missing_en == [], f"ui/tts.txt missing: {missing_en}"
    assert missing_zh == [], f"ui-zh/tts.txt missing: {missing_zh}"


def test_key_name_speech_uses_tts_ids():
    from soundrts import msgparts as mp
    from soundrts.hotkey_editor import _KEY_NAME_SPEECH

    assert _KEY_NAME_SPEECH["BACKSLASH"] == list(mp.HOTKEY_KEY_BACKSLASH)
    assert _KEY_NAME_SPEECH["CTRL"] == list(mp.HOTKEY_KEY_CTRL)
