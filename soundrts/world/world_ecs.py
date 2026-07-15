"""Hybrid C++ ECS coordinator (Phase 1–2 + batch visibility).

Default-on when ``world_ecs_fast`` is built. Disable with ``SOUNDRTS_ECS=0``.

Phase 1:
  * Per-player unit position SoA snapshots
  * Spatial bucket build from typed arrays (cold / heal only)

Phase 2:
  * Snapshot ``sight_range`` / ``is_inside``
  * ``batch_see_enemies`` for perception enemy loop

Tick path:
  * Python incremental ``_buckets``
  * In-place SoA scalar sync
  * Batch visibility (deduped observers + tick-cached observed sets)

The game logic, orders, triggers, UI, and networking remain Python.
"""

from __future__ import annotations

import os
from typing import Any

_ecs_fast: Any = None
_merge_buckets_3x3 = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import world_ecs_fast as _ecs_fast
    except ImportError:
        _ecs_fast = None
    try:
        from soundrts.worldplayerbase.perception_fast import merge_buckets_3x3 as _merge_buckets_3x3
    except ImportError:
        _merge_buckets_3x3 = None

FLAG_INSIDE = 1


def ecs_enabled() -> bool:
    """ECS on by default when the extension is available.

    Set ``SOUNDRTS_ECS=0`` (or false/no/off) to disable.
    """
    if _ecs_fast is None:
        return False
    flag = os.environ.get("SOUNDRTS_ECS", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def _unit_flags(unit) -> int:
    return FLAG_INSIDE if getattr(unit, "is_inside", False) else 0


def _unit_sight(unit) -> int:
    return int(getattr(unit, "sight_range", 0) or 0)


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
        slot = sl.store.add_slot(
            unit.x, unit.y, _unit_sight(unit), _unit_flags(unit)
        )
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
        sl.store.remove_slot(slot)
        last = len(sl.units) - 1
        if slot != last:
            sl.units[slot] = sl.units[last]
            moved_unit = sl.units[slot]
            sl.id_to_slot[getattr(moved_unit, "id", None)] = slot
        sl.units.pop()

    def sync_all(self, players) -> None:
        """Full scalar reload from each slice's unit list (tests / cold paths)."""
        for player in players:
            self.sync_player(player, force_rebuild=False)

    def sync_player(self, player, force_rebuild: bool = False) -> None:
        """Keep SoA aligned with live units.

        * ``force_rebuild`` or length mismatch → full ``rebuild_player_from_units``
        * else in-place ``sync_slots_from_units`` (hot tick path)

        Membership drift is healed when bucket maintenance forces rebuild
        (every ``_BUCKET_HEAL_TICKS``) or when lengths diverge after
        register/unregister.
        """
        sl = self._slices.get(player.id)
        if force_rebuild or sl is None:
            self.rebuild_player_from_units(player)
            return
        n = len(player.units)
        if n != len(sl.units):
            self.rebuild_player_from_units(player)
            return
        if n == 0:
            sl.store.clear()
            return
        sl.store.sync_slots_from_units(sl.units)

    def build_buckets_for_player(self, player, bucket_size: int) -> dict:
        sl = self._slices.get(player.id)
        if sl is None or sl.store.count() == 0:
            return {}
        return sl.store.build_buckets(bucket_size, sl.units)

    def observers_for_target(self, player, tx: int, ty: int, bucket_size: int) -> list:
        """Units of *player* that pass halo + Euclidean sight for ``(tx, ty)``.

        Uses ``player._potential_neighbors`` so the class-level neighbor merge
        cache stays warm (same candidates as non-ECS ``_is_seeing``). Euclidean
        / inside filtering runs on SoA when slots exist.

        Does not apply ``get_observed_squares`` / cloak / exit-blocker — callers
        (``_is_seeing``) keep those semantics in Python.
        """
        sl = self._slices.get(player.id)
        if sl is None or sl.store.count() == 0:
            return []
        get_nb = getattr(player, "_potential_neighbors", None)
        if get_nb is not None:
            candidates = get_nb(tx, ty)
        else:
            buckets = getattr(player, "_buckets", None)
            if not isinstance(buckets, dict) or not buckets:
                return sl.store.observers_seeing_point(sl.units, tx, ty, bucket_size)
            gx = tx // bucket_size
            gy = ty // bucket_size
            try:
                from soundrts.worldplayerbase.perception_fast import merge_buckets_3x3
                candidates = merge_buckets_3x3(buckets, gx, gy)
            except ImportError:
                candidates = []
                for dx in (0, 1, -1):
                    for dy in (0, 1, -1):
                        bl = buckets.get((gx + dx, gy + dy))
                        if bl:
                            candidates.extend(bl)
        filt = getattr(sl.store, "filter_candidates_euclidean", None)
        if filt is not None:
            return filt(candidates, sl.id_to_slot, tx, ty)
        out = []
        for u in candidates:
            if getattr(u, "is_inside", False):
                continue
            sr = int(getattr(u, "sight_range", 0) or 0)
            if not sr:
                continue
            dx = u.x - tx
            dy = u.y - ty
            if dx * dx + dy * dy >= sr * sr:
                continue
            out.append(u)
        return out

    def batch_see_enemies(self, viewer, enemies, bucket_size: int):
        """Return enemies visible to *viewer* (parity with ``_is_seeing``).

        Optimizations vs per-enemy ``_is_seeing``:
        - cloak / exit-blocker handled once up front
        - enemies grouped by bucket cell; observers from warm 3×3 ``_buckets``
        - observed-square sets from ``get_observed_squares_optimized`` + shared
          cache across overlapping cells (pay topology once per observer)
        - Euclidean uses SoA when observer slots exist
        - process *viewer* before other allied_vision (prune remaining faster)
        """
        visible = set()
        if not enemies:
            return visible
        detected = getattr(viewer, "detected_units", None)
        exit_vis = getattr(viewer, "_exit_blocker_visible", None)
        pending = []
        for u in enemies:
            if u is None:
                continue
            # Direct attrs (hot path; avoid getattr).
            if (u.is_invisible or u.is_cloaked) and detected is not None and u not in detected:
                continue
            if u.place is None:
                continue
            if exit_vis is not None and exit_vis(u):
                visible.add(u)
                continue
            pending.append(u)
        if not pending:
            return visible

        by_cell: dict = {}
        for u in pending:
            k = (u.x // bucket_size, u.y // bucket_size)
            bl = by_cell.get(k)
            if bl is None:
                by_cell[k] = [u]
            else:
                bl.append(u)

        merge_buckets_3x3 = _merge_buckets_3x3
        remaining = {id(u): u for u in pending}
        # Own observers first — typically resolve most enemies before other allies.
        allies = list(viewer.allied_vision)
        try:
            allies.remove(viewer)
            allies.insert(0, viewer)
        except ValueError:
            pass
        for avp in allies:
            if not remaining or not by_cell:
                break
            sl = self._slices.get(avp.id)
            if sl is None or sl.store.count() == 0:
                continue
            buckets = getattr(avp, "_buckets", None)
            mark = getattr(sl.store, "mark_enemies_seen_by_observers", None)
            if mark is None:
                continue
            observed_cache = {}
            exhausted = []
            for (gx, gy), group in list(by_cell.items()):
                if not group:
                    exhausted.append((gx, gy))
                    continue
                if isinstance(buckets, dict) and buckets:
                    if merge_buckets_3x3 is not None:
                        observers = merge_buckets_3x3(buckets, gx, gy)
                    else:
                        observers = []
                        for dx in (0, 1, -1):
                            for dy in (0, 1, -1):
                                bl = buckets.get((gx + dx, gy + dy))
                                if bl:
                                    observers.extend(bl)
                else:
                    get_nb = getattr(avp, "_potential_neighbors", None)
                    if get_nb is None:
                        continue
                    probe = group[0]
                    observers = get_nb(probe.x, probe.y)
                if not observers:
                    continue
                for u in mark(sl.id_to_slot, observers, group, observed_cache):
                    if remaining.pop(id(u), None) is not None:
                        visible.add(u)
                if not remaining:
                    by_cell.clear()
                    exhausted.clear()
                    break
                group[:] = [u for u in group if id(u) in remaining]
                if not group:
                    exhausted.append((gx, gy))
            for key in exhausted:
                by_cell.pop(key, None)
        return visible

    def rebuild_player_from_units(self, player) -> None:
        """Full resync slice from ``player.units`` (safe after load / desync repair)."""
        key = player.id
        sl = _PlayerSlice()
        self._slices[key] = sl
        for unit in player.units:
            uid = getattr(unit, "id", None)
            if uid is None or not hasattr(unit, "x"):
                continue
            slot = sl.store.add_slot(
                unit.x, unit.y, _unit_sight(unit), _unit_flags(unit)
            )
            sl.units.append(unit)
            sl.id_to_slot[uid] = slot

    def rebuild_all_players(self, players) -> None:
        self._slices.clear()
        for player in players:
            self.rebuild_player_from_units(player)
