"""Map definition token helpers (deposit plurals, etc.)."""
from __future__ import annotations

import re

from ..definitions import rules


def deposit_plural_names() -> list[str]:
    """Return deposit type names from rules, longest first for regex matching."""
    try:
        return sorted(
            (
                name
                for name in rules.classnames()
                if rules.get(name, "class") == ["deposit"]
            ),
            key=len,
            reverse=True,
        )
    except Exception:
        return []


def expand_deposit_plurals(s: str) -> str:
    """Convert ``<deposit>s <qty> ...`` lines to singular deposit map syntax."""
    names = deposit_plural_names()
    if not names:
        names = ["goldmine", "wood", "geyser", "mineral_field"]
    pattern = re.compile(
        rf"(?m)^({'|'.join(re.escape(n) for n in names)})s\s+([0-9]+)\s+(.*)$"
    )
    return pattern.sub(r"\1 \2 \3", s)
