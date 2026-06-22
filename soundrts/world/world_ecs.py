"""Hybrid C++ ECS coordinator (Phase 1).

Enable with environment variable ``SOUNDRTS_ECS=1`` (requires compiled
``world_ecs_fast`` extension).

Phase 1 scope:
  * Per-player unit position SoA snapshots
  * Spatial bucket build from typed arrays (replaces per-unit ``u.x`` reads
    in the bucket inner loop)

Later phases (not yet wired):
  * Batch perception visibility
  * Batch unit scalar updates
  * AI decide input from native arrays

The game logic, orders, triggers, UI, and networking remain Python.
"""

from __future__ import annotations

import os
from typing import Any

_ecs_fast: Any = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import world_ecs_fast as _ecs_fast
    except ImportError:
        _ecs_fast = None


def ecs_enabled() -> bool:
    flag = os.environ.get("SOUNDRTS_ECS", "").strip().lower()
    return flag in ("1", "true", "yes") and _ecs_fast is not None


class _PlayerSlice:
    __slots__ = ("store", "units", "id_to_slot")

    def __init__(self) -> None:
        self.store = _ecs_fast.UnitStore()
        self.units: list = []
        self.id_to_slot: dict = {}


class WorldEcs:
    """Per-world ECS registry. One dense slot list per player."""

    def __init__(self) -> None:
        if _ecs_fast is None:
            raise RuntimeError("world_ecs_fast extension is not available")
        self._slices: dict = {}

    def _slice_for(self, player) -> _PlayerSlice:
        key = player.id
        sl = self._slices.get(key)
        if sl is None:
            sl = _PlayerSlice()
            self._slices[key] = sl
        return sl

    def register(self, unit) -> None:
        player = getattr(unit, "player", None)
        if player is None or not hasattr(unit, "x"):
            return
        sl = self._slice_for(player)
        uid = getattr(unit, "id", None)
        if uid is None or uid in sl.id_to_slot:
            return
        slot = sl.store.add_slot(unit.x, unit.y)
        sl.units.append(unit)
        sl.id_to_slot[uid] = slot

    def unregister(self, unit) -> None:
        player = getattr(unit, "player", None)
        if player is None:
            return
        sl = self._slices.get(player.id)
        if sl is None:
            return
        uid = getattr(unit, "id", None)
        if uid is None:
            return
        slot = sl.id_to_slot.pop(uid, None)
        if slot is None:
            return
        moved = sl.store.remove_slot(slot)
        last = len(sl.units) - 1
        if slot != last:
            sl.units[slot] = sl.units[last]
            moved_unit = sl.units[slot]
            sl.id_to_slot[getattr(moved_unit, "id", None)] = slot
        sl.units.pop()

    def sync_all(self, players) -> None:
        for player in players:
            sl = self._slices.get(player.id)
            if sl is None or len(sl.units) != len(player.units):
                self.rebuild_player_from_units(player)
                sl = self._slices[player.id]
            n = len(sl.units)
            if n == 0:
                sl.store.clear()
                continue
            xs = [u.x for u in sl.units]
            ys = [u.y for u in sl.units]
            sl.store.sync_from_scalars(xs, ys)

    def build_buckets_for_player(self, player, bucket_size: int) -> dict:
        sl = self._slices.get(player.id)
        if sl is None or sl.store.count() == 0:
            return {}
        return sl.store.build_buckets(bucket_size, sl.units)

    def rebuild_player_from_units(self, player) -> None:
        """Full resync slice from ``player.units`` (safe after load / desync repair)."""
        key = player.id
        sl = _PlayerSlice()
        self._slices[key] = sl
        for unit in player.units:
            uid = getattr(unit, "id", None)
            if uid is None or not hasattr(unit, "x"):
                continue
            slot = sl.store.add_slot(unit.x, unit.y)
            sl.units.append(unit)
            sl.id_to_slot[uid] = slot

    def rebuild_all_players(self, players) -> None:
        self._slices.clear()
        for player in players:
            self.rebuild_player_from_units(player)
