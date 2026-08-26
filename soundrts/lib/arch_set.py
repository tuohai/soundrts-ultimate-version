"""Parse ``ui/architecture.txt``: civ → architecture set (and optional palettes).

Engine and the HUD-icon generator share this parser so set membership is
never hardcoded in Python.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

COLOR_KEYS = (
    "rim",
    "armor",
    "tunic",
    "horse",
    "wood",
    "roof",
    "stone",
    "tab",
)


def safe_token(name: str) -> bool:
    if not name or name in (".", ".."):
        return False
    return all(ch.isalnum() or ch in "_-" for ch in name)


def _rgb(parts: Iterable[str]) -> Optional[Tuple[int, int, int]]:
    vals = list(parts)
    if len(vals) < 3:
        return None
    try:
        rgb = tuple(max(0, min(255, int(v))) for v in vals[:3])
    except ValueError:
        return None
    return rgb  # type: ignore[return-value]


def parse_architecture(text: str) -> Tuple[Dict[str, str], Dict[str, dict], List[str]]:
    """Return ``(civ_to_set, set_styles, neutral_type_names)``.

    Accepts either::

        def western_european
        factions britons franks
        kit western
        rim 196 168 84

    or a compact line ``western_european britons franks``.
    """
    mapping: Dict[str, str] = {}
    sets: Dict[str, dict] = {}
    neutral: List[str] = []
    current: Optional[str] = None
    for raw in (text or "").splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.startswith("def "):
            name = line.split()[1] if len(line.split()) > 1 else ""
            current = name if safe_token(name) else None
            if current is not None:
                sets.setdefault(current, {"name": current, "civs": []})
            continue
        parts = line.split()
        key = parts[0]
        rest = parts[1:]
        if key == "neutral":
            for token in rest:
                if safe_token(token):
                    neutral.append(token)
            continue
        if key in ("class",):
            continue
        if current is None:
            # compact: set_name civ1 civ2 ...
            if len(parts) >= 2 and safe_token(key):
                set_name = key
                sets.setdefault(set_name, {"name": set_name, "civs": []})
                for civ in rest:
                    if safe_token(civ):
                        mapping[civ] = set_name
                        sets[set_name]["civs"].append(civ)
            continue
        if key in ("factions", "civs"):
            for civ in rest:
                if safe_token(civ):
                    mapping[civ] = current
                    sets[current]["civs"].append(civ)
            continue
        if key == "kit" and rest and safe_token(rest[0]):
            sets[current]["kit"] = rest[0]
            continue
        if key in COLOR_KEYS:
            rgb = _rgb(rest)
            if rgb is not None:
                sets[current][key] = rgb
    return mapping, sets, neutral
