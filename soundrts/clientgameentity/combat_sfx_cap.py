# -*- coding: utf-8 -*-
"""Cap spammy SFX so a dense scene cannot stall the client loop.

Mixer cannot play hundreds of overlapping sounds; running every notify or
every unit's footstep/noise still costs milliseconds on the main thread.

Death, falling, and HP proportion sounds are not in these sets.
"""

from __future__ import annotations

from soundrts import parameters

# Fire / hit spam. Death and alerts are not in this set.
CAPPED_COMBAT_EVENTS = frozenset(
    {
        "launch_mdg",
        "launch_rdg",
        "launch_charge_mdg",
        "launch_charge_rdg",
        "wounded",
        "missed",
        "dodge",
        "splash_hit",
        "charge_splash_hit",
        "explode",
    }
)

# Group orders notify once per unit; one or two acks are enough.
CAPPED_ORDER_EVENTS = frozenset({"order_ok", "order_impossible"})


def event_kind(payload) -> str:
    if not isinstance(payload, str):
        return ""
    return payload.split(",", 1)[0]


def is_capped_combat_event(kind: str) -> bool:
    return kind in CAPPED_COMBAT_EVENTS


def is_capped_order_event(kind: str) -> bool:
    return kind in CAPPED_ORDER_EVENTS


def is_local_player_model(interface, model) -> bool:
    player = getattr(model, "player", None)
    return player is not None and player is getattr(interface, "player", None)


def _place_key(model):
    place = getattr(model, "place", None)
    if place is None:
        return 0
    return id(place)


def _noise_type_key(model) -> str:
    """Same unit/building type shares one noise budget.

    Construction sites count as the building being built, not a generic site.
    """
    tn = getattr(model, "type_name", None) or ""
    if tn == "buildingsite":
        building_type = getattr(model, "type", None)
        bt = getattr(building_type, "type_name", None)
        if bt:
            return str(bt)
    return str(tn) if tn else "?"


def _int_cap(name, default):
    try:
        n = int(parameters.d.get(name, default))
    except (TypeError, ValueError):
        n = default
    return n if n >= 1 else 1


def sfx_cap_reset(interface, bucket: str) -> None:
    setattr(interface, f"_sfx_cap_{bucket}_g", 0)
    setattr(interface, f"_sfx_cap_{bucket}_p", {})
    setattr(interface, f"_sfx_cap_{bucket}_t", {})


def reset_combat_sfx_cap(interface) -> None:
    sfx_cap_reset(interface, "combat")
    sfx_cap_reset(interface, "order")


def reset_animate_sfx_cap(interface) -> None:
    sfx_cap_reset(interface, "move")
    sfx_cap_reset(interface, "noise")


def sfx_cap_would_allow(interface, model, bucket: str, global_cap: int, place_cap=None) -> bool:
    used = int(getattr(interface, f"_sfx_cap_{bucket}_g", 0) or 0)
    if used >= global_cap:
        return False
    if place_cap is None:
        return True
    by = getattr(interface, f"_sfx_cap_{bucket}_p", None) or {}
    if int(by.get(_place_key(model), 0) or 0) >= place_cap:
        return False
    return True


def sfx_cap_consume(interface, model, bucket: str, global_cap: int, place_cap=None) -> bool:
    if not sfx_cap_would_allow(interface, model, bucket, global_cap, place_cap):
        return False
    g_attr = f"_sfx_cap_{bucket}_g"
    p_attr = f"_sfx_cap_{bucket}_p"
    setattr(interface, g_attr, int(getattr(interface, g_attr, 0) or 0) + 1)
    if place_cap is not None:
        by = getattr(interface, p_attr, None)
        if by is None:
            by = {}
            setattr(interface, p_attr, by)
        key = _place_key(model)
        by[key] = int(by.get(key, 0) or 0) + 1
    return True


def _combat_caps():
    return _int_cap("combat_sfx_per_tick", 16), _int_cap("combat_sfx_per_place_tick", 8)


def combat_sfx_would_allow(interface, model) -> bool:
    global_cap, place_cap = _combat_caps()
    return sfx_cap_would_allow(interface, model, "combat", global_cap, place_cap)


def combat_sfx_consume(interface, model) -> bool:
    global_cap, place_cap = _combat_caps()
    return sfx_cap_consume(interface, model, "combat", global_cap, place_cap)


def order_sfx_consume(interface, model) -> bool:
    return sfx_cap_consume(
        interface,
        model,
        "order",
        _int_cap("order_sfx_per_tick", 2),
        None,
    )


def move_sfx_consume(interface, model) -> bool:
    return sfx_cap_consume(
        interface,
        model,
        "move",
        _int_cap("move_sfx_per_wave", 8),
        _int_cap("move_sfx_per_place_wave", 4),
    )


def noise_sfx_consume(interface, model) -> bool:
    """Allow every type to play; cap identical unit/building types."""
    type_cap = _int_cap("noise_sfx_per_type", 3)
    key = _noise_type_key(model)
    by = getattr(interface, "_sfx_cap_noise_t", None)
    if by is None:
        by = {}
        interface._sfx_cap_noise_t = by
    n = int(by.get(key, 0) or 0)
    if n >= type_cap:
        return False
    by[key] = n + 1
    return True
