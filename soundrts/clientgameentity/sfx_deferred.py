# -*- coding: utf-8 -*-
"""Background-load combat SFX; retry a miss instead of decoding on the client loop.

Cold OGG decode was measured at 300–800ms. allow_load=True on hit/proportion/death
made event bursts hitch; allow_load=False with no retry made those SFX silent.
Prefetch when a type is first seen, and replay from a short pending queue.
"""

from __future__ import annotations

import time

from .. import parameters
from ..clientmedia import sounds
from ..definitions import style
from ..lib.sound import psounds

_PREFETCH_ATTRS = (
    "death",
    "falling",
    "healed",
    "launch_mdg",
    "launch_rdg",
    "launch_charge_mdg",
    "launch_charge_rdg",
    "mdg_hit",
    "rdg_hit",
    "charge_mdg_hit",
    "charge_rdg_hit",
    "mdg_missed",
    "rdg_missed",
) + tuple(f"proportion_{i}" for i in range(11))

_PENDING_ATTR = "_pending_sfx"
_SEEN_ATTR = "_sfx_prefetched_types"


def _int_param(name, default):
    try:
        n = int(parameters.d.get(name, default))
    except (TypeError, ValueError):
        n = default
    return n


def _style_sound_names(type_name, attr):
    st = style.get(type_name, attr, warn_if_not_found=False)
    if not st:
        return
    for item in st:
        if not item or item == "if_me":
            continue
        try:
            float(item)
            continue
        except (TypeError, ValueError):
            pass
        yield item


def prefetch_type_combat_sfx(interface, type_name) -> None:
    if not type_name or type_name == "unknown":
        return
    seen = getattr(interface, _SEEN_ATTR, None)
    if seen is None:
        seen = set()
        setattr(interface, _SEEN_ATTR, seen)
    if type_name in seen:
        return
    seen.add(type_name)
    for attr in _PREFETCH_ATTRS:
        for name in _style_sound_names(type_name, attr):
            sounds.get_sound(name, allow_load=False, warn=False)


def queue_pending_sfx(
    interface,
    sound,
    volume=1,
    x=0,
    y=0,
    priority=0,
    limit=0,
    ambient=False,
) -> None:
    q = getattr(interface, _PENDING_ATTR, None)
    if q is None:
        q = []
        setattr(interface, _PENDING_ATTR, q)
    cap = max(1, _int_param("pending_sfx_queue", 24))
    if len(q) >= cap:
        return
    ttl = float(parameters.d.get("pending_sfx_ttl_s", 2.0) or 2.0)
    if ttl < 0.2:
        ttl = 0.2
    q.append(
        {
            "sound": sound,
            "volume": volume,
            "x": x,
            "y": y,
            "priority": priority,
            "limit": limit,
            "ambient": ambient,
            "deadline": time.time() + ttl,
        }
    )


def flush_pending_sfx(interface, max_items=8) -> int:
    q = getattr(interface, _PENDING_ATTR, None)
    if not q:
        return 0
    now = time.time()
    remain = []
    played = 0
    max_items = max(1, int(max_items))
    for item in q:
        if item["deadline"] < now:
            continue
        s = sounds.get_sound(item["sound"], allow_load=False, warn=False)
        if s is None:
            remain.append(item)
            continue
        if played >= max_items:
            remain.append(item)
            continue
        psounds.play(
            s,
            item["volume"],
            item["x"],
            item["y"],
            item["priority"],
            item["limit"],
            item["ambient"],
        )
        played += 1
    setattr(interface, _PENDING_ATTR, remain)
    return played
