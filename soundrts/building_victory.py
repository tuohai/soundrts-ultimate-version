"""Building victory countdown.

Any finished building with ``victory_time N`` (seconds) starts a countdown.
If it reaches zero while that building still stands, its owner (and
allied_victory camp) wins. Destroying the building cancels that countdown.
"""

from __future__ import annotations

from . import msgparts as mp
from .lib.log import exception
from .lib.msgs import nb2msg

# Mid-countdown voice thresholds (seconds), largest first.
_REMAINING_THRESHOLDS = (120, 60, 30, 10)


def victory_time_seconds(unit) -> int:
    value = getattr(unit, "victory_time", 0) or 0
    if not value:
        value = getattr(type(unit), "victory_time", 0) or 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _ensure_countdowns(world):
    countdowns = getattr(world, "victory_countdowns", None)
    if countdowns is None:
        countdowns = {}
        world.victory_countdowns = countdowns
    return countdowns


def _broadcast(world, msg):
    for player in getattr(world, "players", ()) or ():
        if getattr(player, "is_local_human", lambda: False)():
            try:
                player.send_voice_important(msg)
            except Exception:
                exception("victory timer broadcast failed")


def _owner_label(building):
    player = getattr(building, "player", None)
    name = getattr(player, "name", None) if player is not None else None
    if name:
        return list(name)
    return []


def _duration_msg(seconds: int):
    if seconds >= 60 and seconds % 60 == 0:
        return nb2msg(seconds // 60) + mp.MINUTES
    if seconds >= 60:
        minutes, rem = divmod(seconds, 60)
        return nb2msg(minutes) + mp.MINUTES + nb2msg(rem) + mp.SECONDS
    return nb2msg(seconds) + mp.SECONDS


def register_victory_timer_if_needed(building):
    """Start a victory countdown when a building with victory_time appears."""
    seconds = victory_time_seconds(building)
    if seconds <= 0:
        return
    world = getattr(building, "world", None)
    player = getattr(building, "player", None)
    if world is None or player is None:
        return
    unit_id = getattr(building, "id", None)
    if unit_id is None:
        return

    countdowns = _ensure_countdowns(world)
    if unit_id in countdowns:
        return

    coeff = getattr(world, "timer_coefficient", 1) or 1
    try:
        coeff = float(coeff)
    except (TypeError, ValueError):
        coeff = 1.0
    deadline = int(world.time + seconds * 1000 * coeff)
    countdowns[unit_id] = {
        "player_id": getattr(player, "id", None),
        "deadline": deadline,
        "announced": set(),
    }
    _broadcast(
        world,
        _owner_label(building) + mp.VICTORY_TIMER_STARTED + _duration_msg(seconds),
    )


def cancel_victory_timer_if_needed(building, announce=True):
    """Cancel the countdown when the victory building is destroyed or removed."""
    world = getattr(building, "world", None)
    if world is None:
        return
    countdowns = getattr(world, "victory_countdowns", None)
    if not countdowns:
        return
    unit_id = getattr(building, "id", None)
    if unit_id not in countdowns:
        return
    del countdowns[unit_id]
    if announce:
        _broadcast(world, _owner_label(building) + mp.VICTORY_TIMER_CANCELLED)


def _find_victory_building(world, unit_id):
    unit = getattr(world, "objects", {}).get(unit_id)
    if unit is None:
        return None
    if getattr(unit, "place", None) is None:
        return None
    if getattr(unit, "player", None) is None:
        return None
    if victory_time_seconds(unit) <= 0:
        return None
    return unit


def _announce_remaining(world, building, remaining_sec: int):
    _broadcast(
        world,
        _owner_label(building)
        + mp.VICTORY_TIMER_REMAINING
        + _duration_msg(remaining_sec),
    )


def _try_building_victory(world, unit_id, info):
    countdowns = _ensure_countdowns(world)
    countdowns.pop(unit_id, None)
    unit = _find_victory_building(world, unit_id)
    if unit is None:
        return
    player = unit.player
    if not getattr(player, "is_playing", False) or getattr(player, "has_victory", False):
        return
    try:
        player.victory()
    except Exception:
        exception("building victory failed")


def update_victory_timers(world):
    """Advance victory countdowns (call about once per game second)."""
    countdowns = getattr(world, "victory_countdowns", None)
    if not countdowns:
        return
    coeff = getattr(world, "timer_coefficient", 1) or 1
    try:
        coeff = float(coeff)
    except (TypeError, ValueError):
        coeff = 1.0
    if coeff <= 0:
        coeff = 1.0

    for unit_id, info in list(countdowns.items()):
        unit = _find_victory_building(world, unit_id)
        if unit is None:
            countdowns.pop(unit_id, None)
            continue
        deadline = info.get("deadline", 0)
        remaining_ms = deadline - world.time
        if remaining_ms <= 0:
            _try_building_victory(world, unit_id, info)
            continue
        remaining_sec = int(remaining_ms / (1000 * coeff))
        announced = info.setdefault("announced", set())
        if 1 <= remaining_sec <= 5:
            if remaining_sec not in announced:
                announced.add(remaining_sec)
                _broadcast(world, nb2msg(remaining_sec))
            continue
        for threshold in _REMAINING_THRESHOLDS:
            if remaining_sec <= threshold and threshold not in announced:
                for t in _REMAINING_THRESHOLDS:
                    if t >= threshold:
                        announced.add(t)
                _announce_remaining(world, unit, threshold)
                break
