"""Rules-driven pack / unpack (AoE2 trebuchet siege mode).

Enable in ``rules.txt`` with ``packable 1`` and ``unpack_time`` / ``pack_time``
(seconds → PRECISION ms). Optional: ``packed_mdf`` / ``packed_rdf``,
``spawn_packed 1`` (default).

Packed: can move, cannot attack.
Unpacked: can attack, cannot move.
Transition progress uses the same ``completeness,0..10`` → ``proportion_*``
pipeline as training/research.
"""
from __future__ import annotations

MODE_PACKED = "packed"
MODE_UNPACKED = "unpacked"
MODE_PACKING = "packing"
MODE_UNPACKING = "unpacking"

_STABLE = frozenset((MODE_PACKED, MODE_UNPACKED))
_TRANS = frozenset((MODE_PACKING, MODE_UNPACKING))


def _raw_attr(unit, name, default=0):
    raw = getattr(unit, name, None)
    if raw is None:
        raw = getattr(type(unit), name, default)
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else default
    return raw


def _flag_enabled(unit, name) -> bool:
    raw = _raw_attr(unit, name, 0)
    return raw in (1, "1", True) or (
        isinstance(raw, str) and raw.lower() in ("1", "true")
    )


def _duration_raw_to_ms(raw) -> int:
    try:
        v = float(raw)
    except (TypeError, ValueError):
        return 0
    if v <= 0:
        return 0
    # Legacy: bare seconds before property joined precision_properties
    if v < 500:
        return int(v * 1000)
    return int(v)


def unpack_duration_ms(unit) -> int:
    return _duration_raw_to_ms(_raw_attr(unit, "unpack_time", 0))


def pack_duration_ms(unit) -> int:
    """Pack duration; falls back to ``unpack_time`` when ``pack_time`` is unset."""
    raw = _raw_attr(unit, "pack_time", 0)
    ms = _duration_raw_to_ms(raw)
    if ms > 0:
        return ms
    return unpack_duration_ms(unit)


def transition_duration_ms(unit, target_mode: str) -> int:
    if target_mode == MODE_PACKED:
        return pack_duration_ms(unit) or unpack_duration_ms(unit)
    return unpack_duration_ms(unit) or pack_duration_ms(unit)


def is_packable(unit) -> bool:
    """True when rules enable siege pack (``packable 1`` and/or a positive time).

    Fast reject: Creature defaults are unpack_time=0, pack_time=0, packable=0.
    Almost every unit hits this every tick; avoid _raw_attr there.
    """
    unpack_time = unit.unpack_time
    pack_time = unit.pack_time
    packable = unit.packable
    if unpack_time == 0 and pack_time == 0 and packable == 0:
        return False
    if isinstance(unpack_time, (list, tuple)):
        unpack_time = unpack_time[0] if unpack_time else 0
    if isinstance(pack_time, (list, tuple)):
        pack_time = pack_time[0] if pack_time else 0
    has_time = _duration_raw_to_ms(unpack_time) > 0 or _duration_raw_to_ms(pack_time) > 0
    if not has_time:
        return False
    # Explicit opt-in, or legacy: unpack_time alone
    if _flag_enabled(unit, "packable"):
        return True
    return unpack_duration_ms(unit) > 0 or pack_duration_ms(unit) > 0


def siege_mode(unit) -> str | None:
    if not is_packable(unit):
        return None
    mode = getattr(unit, "_siege_mode", None)
    if mode in _STABLE or mode in _TRANS:
        return mode
    return MODE_PACKED


def _world_time(unit) -> int:
    world = getattr(unit, "world", None)
    if world is None:
        player = getattr(unit, "player", None)
        world = getattr(player, "world", None) if player is not None else None
    return int(getattr(world, "time", 0) or 0) if world is not None else 0


def _armor_value(unit, name, default=0):
    raw = _raw_attr(unit, name, default)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return int(default or 0)


def _apply_armor_for_mode(unit, mode: str) -> None:
    if not hasattr(unit, "_siege_unpacked_mdf"):
        return
    if mode in (MODE_PACKED, MODE_PACKING):
        packed_mdf = _armor_value(unit, "packed_mdf", 0)
        packed_rdf = _armor_value(unit, "packed_rdf", 0)
        if packed_mdf or packed_rdf:
            if packed_mdf:
                unit.mdf = packed_mdf
            if packed_rdf:
                unit.rdf = packed_rdf
            return
    unit.mdf = unit._siege_unpacked_mdf
    unit.rdf = unit._siege_unpacked_rdf


def _notify_completeness(unit, force=None) -> None:
    """Emit ``completeness,0..10`` for proportion_* progress (same as train/research)."""
    if force is not None:
        c = max(0, min(10, int(force)))
    else:
        start = int(getattr(unit, "_siege_transition_start", 0) or 0)
        end = int(getattr(unit, "_siege_transition_end", 0) or 0)
        total = end - start
        if total <= 0:
            return
        now = _world_time(unit)
        elapsed = max(0, min(total, now - start))
        c = int(elapsed * 10 / total)
        if c > 10:
            c = 10
    prev = getattr(unit, "_siege_previous_completeness", None)
    if c == prev:
        return
    unit.notify("completeness,%s" % c)
    unit._siege_previous_completeness = c


def _clear_completeness_tracker(unit) -> None:
    unit._siege_previous_completeness = None


def init_siege_pack(unit) -> None:
    """Call once after Creature armor attrs are copied."""
    if not is_packable(unit):
        return
    # Normalize legacy list form onto the instance so effect_bonus % works
    for attr in ("unpack_time", "pack_time"):
        raw = getattr(unit, attr, None)
        if raw is None:
            raw = getattr(type(unit), attr, None)
        if isinstance(raw, (list, tuple)):
            ms = _duration_raw_to_ms(raw[0] if raw else 0)
            if ms:
                setattr(unit, attr, ms)
    unit._siege_unpacked_mdf = int(getattr(unit, "mdf", 0) or 0)
    unit._siege_unpacked_rdf = int(getattr(unit, "rdf", 0) or 0)
    # spawn_packed defaults to 1 when unset
    spawn_raw = _raw_attr(unit, "spawn_packed", 1)
    spawn_packed = spawn_raw not in (0, "0", False) and not (
        isinstance(spawn_raw, str) and spawn_raw.lower() in ("0", "false")
    )
    unit._siege_mode = MODE_PACKED if spawn_packed else MODE_UNPACKED
    unit._siege_transition_end = 0
    unit._siege_transition_start = 0
    _clear_completeness_tracker(unit)
    _apply_armor_for_mode(unit, unit._siege_mode)


def tick_siege_pack(unit) -> None:
    if not is_packable(unit):
        return
    mode = siege_mode(unit)
    if mode not in _TRANS:
        return
    _notify_completeness(unit)
    end = int(getattr(unit, "_siege_transition_end", 0) or 0)
    if _world_time(unit) < end:
        return
    _notify_completeness(unit, force=10)
    if mode == MODE_PACKING:
        unit._siege_mode = MODE_PACKED
        _apply_armor_for_mode(unit, MODE_PACKED)
        unit.notify("siege_packed")
    else:
        unit._siege_mode = MODE_UNPACKED
        _apply_armor_for_mode(unit, MODE_UNPACKED)
        unit.notify("siege_unpacked")
    unit._siege_transition_end = 0
    unit._siege_transition_start = 0
    _clear_completeness_tracker(unit)


def cancel_siege_transition(unit) -> None:
    """Instant cancel: packing → unpacked, unpacking → packed (AoE2 DE)."""
    if not is_packable(unit):
        return
    mode = siege_mode(unit)
    if mode == MODE_PACKING:
        unit._siege_mode = MODE_UNPACKED
        unit._siege_transition_end = 0
        unit._siege_transition_start = 0
        _clear_completeness_tracker(unit)
        _apply_armor_for_mode(unit, MODE_UNPACKED)
        unit.notify("siege_unpacked")
    elif mode == MODE_UNPACKING:
        unit._siege_mode = MODE_PACKED
        unit._siege_transition_end = 0
        unit._siege_transition_start = 0
        _clear_completeness_tracker(unit)
        _apply_armor_for_mode(unit, MODE_PACKED)
        unit.notify("siege_packed")


def _begin_transition(unit, target_mode: str) -> None:
    duration = transition_duration_ms(unit, target_mode)
    now = _world_time(unit)
    if target_mode == MODE_PACKED:
        unit._siege_mode = MODE_PACKING
        unit.notify("siege_packing")
    else:
        unit._siege_mode = MODE_UNPACKING
        unit.notify("siege_unpacking")
    unit._siege_transition_start = now
    unit._siege_transition_end = now + max(1, duration)
    _clear_completeness_tracker(unit)
    _notify_completeness(unit, force=0)
    # Stop locomotion / attack wind-up while transitioning
    stop = getattr(unit, "stop", None)
    if callable(stop):
        stop()
    if hasattr(unit, "rdg_prep_end_time"):
        unit.rdg_prep_end_time = 0
    if hasattr(unit, "mdg_prep_end_time"):
        unit.mdg_prep_end_time = 0


def ensure_packed(unit) -> bool:
    """True if the unit may move now. Starts/continues packing otherwise."""
    if not is_packable(unit):
        return True
    tick_siege_pack(unit)
    mode = siege_mode(unit)
    if mode == MODE_PACKED:
        return True
    if mode == MODE_UNPACKING:
        cancel_siege_transition(unit)
        return True
    if mode == MODE_PACKING:
        return False
    _begin_transition(unit, MODE_PACKED)
    return False


def ensure_unpacked(unit) -> bool:
    """True if the unit may attack now. Starts/continues unpacking otherwise."""
    if not is_packable(unit):
        return True
    tick_siege_pack(unit)
    mode = siege_mode(unit)
    if mode == MODE_UNPACKED:
        return True
    if mode == MODE_PACKING:
        cancel_siege_transition(unit)
        return True
    if mode == MODE_UNPACKING:
        return False
    _begin_transition(unit, MODE_UNPACKED)
    return False


def can_siege_move(unit) -> bool:
    if not is_packable(unit):
        return True
    return siege_mode(unit) == MODE_PACKED


def can_siege_attack(unit) -> bool:
    if not is_packable(unit):
        return True
    return siege_mode(unit) == MODE_UNPACKED
