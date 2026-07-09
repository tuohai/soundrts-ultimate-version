"""战斗音效延迟队列：把喊杀 burst 错开播放，避免同帧齐射。"""

from __future__ import annotations

import time
from typing import Any, Dict, List


def _ensure_queue(interface) -> List[Dict[str, Any]]:
    queue = getattr(interface, "_formation_sound_queue", None)
    if queue is None:
        queue = []
        interface._formation_sound_queue = queue
    return queue


def queue_formation_sound(
    interface,
    entity_id,
    play_at: float,
    sound,
    volume: float,
    priority: int,
    limit: float,
    x: float,
    y: float,
) -> None:
    _ensure_queue(interface).append(
        {
            "play_at": play_at,
            "entity_id": entity_id,
            "sound": sound,
            "volume": volume,
            "priority": priority,
            "limit": limit,
            "x": x,
            "y": y,
        }
    )


def flush_formation_sound_queue(interface) -> None:
    queue = _ensure_queue(interface)
    if not queue:
        return
    now = time.time()
    remaining: List[Dict[str, Any]] = []
    for item in queue:
        if item["play_at"] > now:
            remaining.append(item)
            continue
        view = interface.dobjets.get(item["entity_id"])
        if view is None:
            continue
        try:
            view.launch_event(
                item["sound"],
                item["volume"],
                priority=item["priority"],
                limit=item["limit"],
                x=item["x"],
                y=item["y"],
            )
        except Exception:
            continue
    interface._formation_sound_queue = remaining
