"""Speak the resolved faction after a random civ roll (no heavy UI imports)."""
from __future__ import annotations

from typing import Any, List, Optional


def _multi_faction_mod() -> bool:
    from .definitions import rules

    return len(getattr(rules, "factions", None) or []) > 1


def player_faction_label_msgs(player) -> Optional[List[Any]]:
    """Civ/race title for labeling another player's units, or None.

    Silent when the mod has only one faction (base ``res``) or the player
    has no resolved faction key.
    """
    from .faction_progress import faction_title_msgs, normalize_faction_key

    if player is None or not _multi_faction_mod():
        return None
    key = normalize_faction_key(getattr(player, "faction", None))
    if not key:
        return None
    return faction_title_msgs(key)


def owner_label_with_faction_msgs(player, owner_name) -> List[Any]:
    """``[faction,] owner_name,`` for enemy/ally titles (faction omitted if N/A)."""
    from . import msgparts as mp

    name = list(owner_name) if isinstance(owner_name, (list, tuple)) else [owner_name]
    fac = player_faction_label_msgs(player)
    if fac:
        return list(fac) + list(mp.COMMA) + name + list(mp.COMMA)
    return name + list(mp.COMMA)


def name_with_faction_msgs(player, owner_name=None) -> List[Any]:
    """``name, [faction,]`` for roster / diplomacy candidate speech."""
    from . import msgparts as mp

    if owner_name is None:
        owner_name = getattr(player, "name", None) or ["?"]
    name = list(owner_name) if isinstance(owner_name, (list, tuple)) else [owner_name]
    fac = player_faction_label_msgs(player)
    if fac:
        return name + list(mp.COMMA) + list(fac) + list(mp.COMMA)
    return name + list(mp.COMMA)


def player_faction_you_are_msgs(player) -> Optional[List[Any]]:
    """``YOU_ARE`` + resolved faction title, or None if nothing to announce.

    Only when the lobby choice was ``random_faction`` *and* the mod has more
    than one race. Manual picks and single-faction mods stay silent.
    """
    from . import msgparts as mp
    from .definitions import rules
    from .faction_progress import faction_title_msgs, normalize_faction_key

    if player is None:
        return None
    if getattr(player, "_is_pure_spectator", False):
        return None
    if not getattr(player, "faction_was_random", False):
        return None
    factions = getattr(rules, "factions", None) or []
    if len(factions) <= 1:
        return None
    key = normalize_faction_key(getattr(player, "faction", None))
    if not key:
        return None
    return list(mp.YOU_ARE) + faction_title_msgs(key)


def announce_resolved_faction(player, voice=None) -> None:
    """Speak the civ once; call after opening objective and ``flush``.

    ``voice`` defaults to ``clientmedia.voice`` (injected in tests).
    """
    if voice is None:
        from .clientmedia import voice as voice

    msgs = player_faction_you_are_msgs(player)
    if msgs:
        voice.info(msgs)
        voice.flush()
