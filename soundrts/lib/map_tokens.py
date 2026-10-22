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


def item_names() -> list[str]:
    """Return item type names from rules, longest first for regex matching."""
    try:
        return sorted(
            (
                name
                for name in rules.classnames()
                if rules.get(name, "class") == ["item"]
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


def expand_item_qty_first(s: str) -> str:
    """Convert ``<qty> <item> <squares...>`` lines to the engine's native
    ``<item> <qty> <squares...>`` ordering.

    The map parser only understands ``<item> [<qty>] <squares...>``, but the
    quantity-first form reads much better when a single item is scattered
    over several squares::

        4 joan_relic a1 b1 d2   ->   joan_relic 4 a1 b1 d2

    which places 4 of the item on *each* of a1, b1 and d2.

    Both orderings stay supported; this only rewrites the leading-quantity
    form so the existing item branch handles it unchanged.
    """
    names = item_names()
    if not names:
        return s
    pattern = re.compile(
        rf"(?m)^([0-9]+)\s+({'|'.join(re.escape(n) for n in names)})\s+(.*)$"
    )
    return pattern.sub(r"\2 \1 \3", s)
