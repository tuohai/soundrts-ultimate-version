"""Rules-driven hold-all inventory victory (AoE2 relic victory pattern).

Item flag::

    inventory_victory 1

Parameters::

    inventory_victory_time 1000   ; seconds; 0 disables (DE ~200 years ≈ 1000s)

When every living instance of such items is held in inventories of one
allied_victory camp, a countdown starts (same voice lines as building
``victory_time``). Losing any item cancels it.
"""

from __future__ import annotations

from . import msgparts as mp
from .building_victory import _broadcast, _duration_msg, _REMAINING_THRESHOLDS
from .definitions import rules
from .lib.log import exception
from .lib.msgs import nb2msg
from .worlditem import Item


def _as_int(val, default=0):
    if isinstance(val, (list, tuple)):
        val = val[0] if val else default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def inventory_victory_time_seconds() -> int:
    raw = rules.get("parameters", "inventory_victory_time")
    return max(0, _as_int(raw, 0))


def item_counts_for_inventory_victory(item) -> bool:
    if item is None:
        return False
    if _as_int(getattr(item, "inventory_victory", 0), 0) > 0:
        return True
    cls = type(item)
    return _as_int(getattr(cls, "inventory_victory", 0), 0) > 0


def _team_key(player):
    allies = getattr(player, "allied_victory", None) or (player,)
    ids = []
    for a in allies:
        ids.append(getattr(a, "id", id(a)))
    return frozenset(ids)


def _ensure_state(world):
    state = getattr(world, "inventory_victory_state", None)
    if state is None:
        state = {"team": None, "deadline": None, "announced": set(), "holder": None}
        world.inventory_victory_state = state
    return state


def _iter_victory_item_holders(world):
    """Yield (item, holder_player|None). None = on ground / unowned."""
    seen = set()
    for player in getattr(world, "players", ()) or ():
        for unit in list(getattr(player, "units", ()) or ()):
            for item in list(getattr(unit, "inventory", ()) or ()):
                if not item_counts_for_inventory_victory(item):
                    continue
                iid = getattr(item, "id", None)
                if iid is not None:
                    seen.add(iid)
                yield item, player
    objects = getattr(world, "objects", None) or {}
    for obj in list(objects.values()):
        if not isinstance(obj, Item):
            continue
        if not item_counts_for_inventory_victory(obj):
            continue
        iid = getattr(obj, "id", None)
        if iid is not None and iid in seen:
            continue
        if getattr(obj, "place", None) is None:
            # In inventory but holder not found (edge); treat as unheld
            yield obj, None
        else:
            yield obj, None


def controlling_team(world):
    """Return (team_key, representative_player) if one camp holds all victory items."""
    held = list(_iter_victory_item_holders(world))
    if not held:
        return None, None
    team = None
    representative = None
    for _item, holder in held:
        if holder is None:
            return None, None
        key = _team_key(holder)
        if team is None:
            team = key
            representative = holder
        elif key != team:
            return None, None
    return team, representative


def update_inventory_victory(world):
    """Advance hold-all inventory victory (call about once per game second)."""
    seconds = inventory_victory_time_seconds()
    state = _ensure_state(world)
    if seconds <= 0:
        state["team"] = None
        state["deadline"] = None
        state["announced"] = set()
        state["holder"] = None
        return

    team, holder = controlling_team(world)
    if team is None or holder is None:
        if state.get("deadline") is not None:
            _broadcast(world, mp.VICTORY_TIMER_CANCELLED)
        state["team"] = None
        state["deadline"] = None
        state["announced"] = set()
        state["holder"] = None
        return

    coeff = getattr(world, "timer_coefficient", 1) or 1
    try:
        coeff = float(coeff)
    except (TypeError, ValueError):
        coeff = 1.0
    if coeff <= 0:
        coeff = 1.0

    if state.get("team") != team or state.get("deadline") is None:
        state["team"] = team
        state["holder"] = holder
        state["announced"] = set()
        state["deadline"] = int(world.time + seconds * 1000 * coeff)
        name = getattr(holder, "name", None) or []
        label = list(name) if name else []
        _broadcast(world, label + mp.VICTORY_TIMER_STARTED + _duration_msg(seconds))
        return

    deadline = state["deadline"]
    remaining_ms = deadline - world.time
    if remaining_ms <= 0:
        state["deadline"] = None
        state["team"] = None
        state["announced"] = set()
        player = state.get("holder") or holder
        state["holder"] = None
        if player is None:
            return
        if not getattr(player, "is_playing", False) or getattr(player, "has_victory", False):
            return
        try:
            player.victory()
        except Exception:
            exception("inventory victory failed")
        return

    remaining_sec = int(remaining_ms / (1000 * coeff))
    announced = state.setdefault("announced", set())
    if 1 <= remaining_sec <= 5:
        if remaining_sec not in announced:
            announced.add(remaining_sec)
            _broadcast(world, nb2msg(remaining_sec))
        return
    for threshold in _REMAINING_THRESHOLDS:
        if remaining_sec <= threshold and threshold not in announced:
            for t in _REMAINING_THRESHOLDS:
                if t >= threshold:
                    announced.add(t)
            name = getattr(holder, "name", None) or []
            label = list(name) if name else []
            _broadcast(
                world,
                label + mp.VICTORY_TIMER_REMAINING + _duration_msg(threshold),
            )
            break
