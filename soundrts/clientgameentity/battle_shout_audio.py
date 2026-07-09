"""原版作战喊杀：战场背景 + 单位音色 + 事件高光（无军团编队）。"""

from __future__ import annotations

import math
import random
from typing import List, Optional, Sequence, Tuple

from ..definitions import style

SHOUT_COOLDOWN_GLOBAL_MS = 10000
SHOUT_COOLDOWN_PLACE_MS = 6000
SHOUT_PLACE_PEACE_MS = 15000
SHOUT_EVENT_COOLDOWN_PLACE_MS = 4000
_SKIRMISH_MIN_UNITS = 5
_DEFAULT_SPREAD = 0.45

_DENSITY_TABLES = {
    "shout_bg": [(1, 1), (10, 1), (25, 2), (50, 3), (999999, 3)],
    "shout_unit": [(1, 1), (5, 2), (10, 3), (25, 8), (50, 16), (999999, 16)],
    "shout_event": [(1, 1), (999999, 2)],
}

_STAGGER_SPAN = {
    "shout_bg": 0.95,
    "shout_unit": 0.75,
    "shout_event": 0.45,
}


def audio_headcount(raw: int) -> int:
    raw = max(1, int(raw))
    if raw >= 400:
        return 50
    if raw < 100:
        return max(1, round(raw / 5))
    if raw < 200:
        return 20 + round((raw - 100) * 0.1)
    if raw < 300:
        return 30 + round((raw - 200) * 0.1)
    if raw < 400:
        return 40 + round((raw - 300) * 0.1)
    return 50


def _lookup_burst(headcount: int, table: Sequence[Tuple[int, int]]) -> int:
    result = table[0][1]
    for threshold, count in table:
        if headcount >= threshold:
            result = count
    return result


def formation_density_burst(headcount: int, kind: str) -> int:
    table = _DENSITY_TABLES.get(kind, _DENSITY_TABLES["shout_unit"])
    return _lookup_burst(audio_headcount(headcount), table)


def scaled_shout_burst(headcount: int, kind: str) -> int:
    hc = audio_headcount(headcount)
    burst = formation_density_burst(headcount, kind)
    if burst <= 0:
        return 0
    if kind in ("shout", "shout_unit"):
        if hc >= 25 and burst < 3:
            burst = 3
        return max(0, burst)
    if kind == "shout_bg":
        return max(0, min(burst, 3))
    if kind == "shout_event":
        return max(1, min(burst, 2))
    return max(1, burst)


def burst_stagger_delays(burst: int, kind: str, headcount: int = 1) -> List[float]:
    if burst <= 1:
        return [random.uniform(0.0, 0.12)]
    span = _STAGGER_SPAN.get(kind, 0.75) * random.uniform(0.65, 1.45)
    hc = audio_headcount(headcount)
    if hc > 1:
        span *= 1.0 + math.log10(max(1, hc)) * 0.35
    delays = [random.uniform(0.0, span * 1.25) for _ in range(burst)]
    random.shuffle(delays)
    return delays


def shout_combat_priority(headcount: int, kind: str = "shout_unit") -> int:
    hc = audio_headcount(headcount)
    base = 12 + int(math.log10(max(1, hc)) * 4)
    if kind == "shout_event":
        return min(16, base + 3)
    if kind in ("shout", "shout_unit"):
        return min(16, base + 2)
    if kind == "shout_bg":
        return min(14, base)
    return min(16, base + 2)


def shout_combat_volume(base_vol: float, headcount: int, kind: str = "shout_unit") -> float:
    hc = audio_headcount(headcount)
    boost = min(1.6, 1.0 + math.log10(max(1, hc)) * 0.22)
    if kind in ("shout", "shout_unit"):
        boost = min(1.7, boost * 1.08)
    elif kind == "shout_event":
        boost = min(1.85, boost * 1.15)
    elif kind == "shout_bg":
        boost = min(1.25, boost * 0.72)
    floor = 0.65 + min(0.25, math.log10(max(1, hc)) * 0.1)
    return base_vol * boost * random.uniform(floor, 1.05)


def soldiers_in_place(interface, place, player) -> int:
    if place is None or player is None:
        return 0
    total = 0
    for view in interface.dobjets.values():
        if getattr(view, "place", None) is not place:
            continue
        if getattr(view, "player", None) is not player:
            continue
        model = getattr(view, "model", None)
        if model is None or not getattr(model, "menace", 0):
            continue
        total += 1
    return total


def soldiers_in_clash_place(interface, place) -> int:
    if place is None:
        return 0
    total = 0
    for view in interface.dobjets.values():
        if getattr(view, "place", None) is not place:
            continue
        model = getattr(view, "model", None)
        if model is None or not getattr(model, "menace", 0):
            continue
        total += 1
    return total


def clash_unit_count(defender, attacker_view, interface=None) -> int:
    own = 1
    other = 1 if attacker_view is not None else 0
    if interface is None:
        return max(own, other)
    place = getattr(defender, "place", None)
    if place is None and attacker_view is not None:
        place = getattr(attacker_view, "place", None)
    clash_total = soldiers_in_clash_place(interface, place)
    def_n = soldiers_in_place(interface, place, getattr(defender, "player", None))
    att_n = soldiers_in_place(
        interface, place, getattr(attacker_view, "player", None)
    ) if attacker_view is not None else 0
    return max(def_n, att_n, clash_total, 1)


def default_battle_shout_pool():
    pool = style.get("walking_unit", "shouts", warn_if_not_found=False)
    if pool:
        return pool
    return style.get("knight", "shouts", warn_if_not_found=False)


def battle_qualifies_for_shouts(defender_units: int, attacker_units: int) -> bool:
    return max(defender_units, attacker_units) >= _SKIRMISH_MIN_UNITS


def _place_key(place) -> int:
    return id(place)


def try_battle_shout_gates(interface, place, current_time_ms: int) -> bool:
    last_global = getattr(interface, "_last_global_battle_shout_ms", 0)
    if current_time_ms - last_global < SHOUT_COOLDOWN_GLOBAL_MS:
        return False
    place_times = getattr(interface, "_battle_shout_place_times", None) or {}
    if current_time_ms - place_times.get(_place_key(place), 0) < SHOUT_COOLDOWN_PLACE_MS:
        return False
    return True


def mark_battle_shout_played(interface, place, current_time_ms: int) -> None:
    interface._last_global_battle_shout_ms = current_time_ms
    place_times = getattr(interface, "_battle_shout_place_times", None)
    if place_times is None:
        place_times = {}
        interface._battle_shout_place_times = place_times
    place_times[_place_key(place)] = current_time_ms


def is_first_clash_at_place(interface, place, current_time_ms: int) -> bool:
    place_times = getattr(interface, "_battle_shout_place_times", None) or {}
    last = place_times.get(_place_key(place), 0)
    return current_time_ms - last >= SHOUT_PLACE_PEACE_MS


def try_shout_event_gate(interface, place, current_time_ms: int) -> bool:
    event_times = getattr(interface, "_battle_shout_event_times", None) or {}
    return current_time_ms - event_times.get(_place_key(place), 0) >= SHOUT_EVENT_COOLDOWN_PLACE_MS


def mark_shout_event_played(interface, place, current_time_ms: int) -> None:
    event_times = getattr(interface, "_battle_shout_event_times", None)
    if event_times is None:
        event_times = {}
        interface._battle_shout_event_times = event_times
    event_times[_place_key(place)] = current_time_ms


def shout_bg_burst_cap(headcount: int) -> int:
    return max(1, min(scaled_shout_burst(headcount, "shout_bg"), 2))


def shout_unit_burst_cap(headcount: int) -> int:
    return max(1, min(scaled_shout_burst(headcount, "shout_unit"), 2))


def clash_shout_speakers(defender, attacker_view, interface):
    place = getattr(defender, "place", None)
    def_n = soldiers_in_place(interface, place, getattr(defender, "player", None))
    att_n = 0
    if attacker_view is not None:
        att_n = soldiers_in_place(
            interface, place, getattr(attacker_view, "player", None)
        )
    if def_n >= att_n and defender is not None:
        return [defender]
    if attacker_view is not None:
        return [attacker_view]
    return []


def normalize_sound_pool(sound_ids) -> List:
    if not sound_ids:
        return []
    if isinstance(sound_ids, (list, tuple)) and sound_ids and sound_ids[0] == "if_me":
        return []
    flat: List = []
    for item in sound_ids if isinstance(sound_ids, (list, tuple)) else [sound_ids]:
        if isinstance(item, (list, tuple)):
            if item and item[0] == "if_me":
                continue
            flat.extend(normalize_sound_pool(item))
        else:
            flat.append(item)
    return flat
