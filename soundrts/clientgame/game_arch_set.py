"""AoE2 DE architecture sets: civs in the same set share unit/building art."""

from __future__ import annotations

from typing import Dict, Optional

from ..lib.arch_set import parse_architecture, safe_token

_CACHE: Optional[Dict[str, str]] = None
_CACHE_MODS = object()


def _parse(text: str) -> Dict[str, str]:
    """Civ → set name (tests and callers that only need membership)."""
    mapping, _, _ = parse_architecture(text)
    return mapping


def _safe_token(name: str) -> bool:
    return safe_token(name)


def _load_mapping() -> Dict[str, str]:
    global _CACHE, _CACHE_MODS
    try:
        from ..lib.resource import res

        mods = getattr(res, "mods", None)
        if _CACHE is not None and _CACHE_MODS == mods:
            return _CACHE
        texts = res.texts("ui/architecture")
        mapping = _parse(texts[-1]) if texts else {}
        _CACHE = mapping
        _CACHE_MODS = mods
        return mapping
    except Exception:
        _CACHE = {}
        _CACHE_MODS = None
        return _CACHE


def architecture_set_for_faction(faction) -> Optional[str]:
    """Return DE architecture-set folder name, or None."""
    try:
        from ..faction_progress import normalize_faction_key
    except Exception:
        def normalize_faction_key(f):
            if f is None:
                return None
            if hasattr(f, "type_name"):
                f = f.type_name
            f = str(f).strip()
            return f or None

    key = normalize_faction_key(faction)
    if not key:
        return None
    return _load_mapping().get(key)


def architecture_set_for_entity(entity) -> Optional[str]:
    """Owner civ → architecture set. Neutral / missing owner → None."""
    if entity is None:
        return None
    fac = getattr(entity, "faction", None)
    if fac is None:
        player = getattr(entity, "player", None)
        if player is None:
            player = getattr(getattr(entity, "model", None), "player", None)
        fac = getattr(player, "faction", None)
    return architecture_set_for_faction(fac)
