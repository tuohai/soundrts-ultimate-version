"""Ally square ping: rules enable, style name and SFX."""
from __future__ import annotations

from typing import Any, List, Optional


def _flag_on(value) -> bool:
    if value in (0, "0", False, None, ""):
        return False
    if isinstance(value, list):
        if not value:
            return False
        return str(value[0]) not in ("0", "false", "False")
    return str(value) not in ("0", "false", "False")


def signal_flare_enabled() -> bool:
    """``rules.txt`` ``def parameters`` / ``signal_flare 1``."""
    try:
        from .definitions import rules

        return _flag_on(rules.get("parameters", "signal_flare", 0))
    except Exception:
        return False


def flare_title_msgs() -> List[Any]:
    """Style ``parameters.signal_flare_title``, else TTS 5842."""
    from . import msgparts as mp

    try:
        from .definitions import style

        title = style.get("parameters", "signal_flare_title", warn_if_not_found=False)
        if title:
            return list(title)
    except Exception:
        pass
    return list(mp.SIGNAL_FLARE)


def player_by_number(world, number) -> Optional[Any]:
    if number is None or world is None:
        return None
    try:
        number = int(number)
    except (TypeError, ValueError):
        return None
    for player in getattr(world, "players", None) or ():
        if getattr(player, "number", None) == number:
            return player
    return None


def flare_voice_msg(place, sender=None, local_player=None) -> List[Any]:
    """``[sender] <title> 在 <格子>``; own pings omit the name."""
    from . import msgparts as mp

    msg: List[Any] = flare_title_msgs()
    if sender is not None and sender is not local_player:
        name = getattr(sender, "name", None)
        if name:
            msg = list(name) + msg
    title = getattr(place, "title", None) if place is not None else None
    if title:
        msg = msg + list(mp.AT) + list(title)
    return msg
