"""Cross-faction meta achievement progress (_meta.json)."""

from __future__ import annotations

import json
import os
from typing import Dict, List

from .faction_progress import achievements_per_faction_enabled
from .lib.log import warning
from .paths import CONFIG_DIR_PATH, current_mod_key

META_MENU_KEY = "__meta__"


def meta_enabled() -> bool:
    return achievements_per_faction_enabled()


def meta_save_path() -> str:
    directory = os.path.join(CONFIG_DIR_PATH, "achievements")
    mod_key = current_mod_key()
    faction_dir = os.path.join(directory, mod_key)
    try:
        os.makedirs(faction_dir, exist_ok=True)
    except OSError:
        pass
    return os.path.join(faction_dir, "_meta.json")


def empty_meta_state() -> dict:
    return {
        "unlocked": {},
        "once_keys": {},
        "medals": 0,
        "honors": [],
    }


def normalize_meta_state(data: dict) -> dict:
    if "unlocked" not in data:
        data["unlocked"] = {}
    if "once_keys" not in data:
        data["once_keys"] = {}
    if "medals" not in data:
        data["medals"] = 0
    if "honors" not in data:
        data["honors"] = []
    elif not isinstance(data["honors"], list):
        data["honors"] = list(data["honors"])
    return data


def load_meta_state() -> dict:
    path = meta_save_path()
    if not os.path.isfile(path):
        return empty_meta_state()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        warning("couldn't read meta achievements save: %s", path)
        return empty_meta_state()
    return normalize_meta_state(data)


def save_meta_state(data: dict) -> None:
    path = meta_save_path()
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    except OSError:
        warning("couldn't write meta achievements save: %s", path)


def list_faction_save_keys() -> List[str]:
    directory = os.path.join(CONFIG_DIR_PATH, "achievements", current_mod_key())
    if not os.path.isdir(directory):
        return []
    keys = []
    for name in os.listdir(directory):
        if not name.endswith(".json") or name == "_meta.json":
            continue
        keys.append(name[:-5])
    return sorted(keys)


def load_faction_snapshots() -> Dict[str, dict]:
    from .achievements import load_unlock_state

    return {key: load_unlock_state(key) for key in list_faction_save_keys()}


def count_factions_unlocked_at_least(snapshots: Dict[str, dict], min_unlocked: int) -> int:
    count = 0
    for state in snapshots.values():
        unlocked = state.get("unlocked") or {}
        if len(unlocked) >= min_unlocked:
            count += 1
    return count


def count_factions_medals_at_least(snapshots: Dict[str, dict], min_medals: int) -> int:
    count = 0
    for state in snapshots.values():
        if int(state.get("medals", 0)) >= min_medals:
            count += 1
    return count


def count_factions_honors_at_least(snapshots: Dict[str, dict], min_honors: int) -> int:
    count = 0
    for state in snapshots.values():
        honors = state.get("honors") or []
        if len(honors) >= min_honors:
            count += 1
    return count


def count_factions_achievement_id_contains(snapshots: Dict[str, dict], substring: str) -> int:
    count = 0
    for state in snapshots.values():
        unlocked = state.get("unlocked") or {}
        if any(substring in aid for aid in unlocked):
            count += 1
    return count


def count_factions_with_any_progress(snapshots: Dict[str, dict]) -> int:
    count = 0
    for state in snapshots.values():
        if state.get("unlocked") or int(state.get("medals", 0)) > 0:
            count += 1
    return count
