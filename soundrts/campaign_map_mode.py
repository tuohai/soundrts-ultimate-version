"""Adapt shared campaign ``N.txt`` maps for solo vs co-op play.

Co-op authoring tools (e.g. ``tools/generate_raynor_coop_maps.py``) bake co-op
layout and enemy intensification into the on-disk map. Solo campaign must strip
those artifacts at load time so difficulty comes from ``coop_difficulty.py``
(``difficulty`` / ``coop_difficulty`` + player count), not from map file edits.
"""
from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .mapfile import Map

INT_RE = re.compile(r"^[0-9]+$")
GRID_REF_RE = re.compile(r"^[a-z][0-9]+$", re.IGNORECASE)

COOP_MARKER = "; co-op: 1-2 human allies (AoE-style cooperative campaign)"
PARTNER_ECONOMY_MARKER = "; co-op symmetric partner economy"

ALLIANCE_TRIGGERS = frozenset(
    {
        "trigger player1 (timer 0) (alliance 1)",
        "trigger player2 (timer 0) (alliance 1)",
        "trigger computers (timer 0) (alliance 2)",
    }
)


def is_coop_authored_map(definition: str) -> bool:
    return COOP_MARKER in definition or "nb_players_max 2" in definition


def _is_grid_ref(token: str) -> bool:
    return bool(GRID_REF_RE.match(token.strip()))


def _deintensify_computer_only_line(line: str) -> str:
    """Reverse ``intensify_computer_only_line`` (×1.5 ceil) from co-op map tool."""
    parts = line.split()
    if len(parts) < 3 or parts[0] != "computer_only":
        return line
    i = 1
    while i < len(parts) and INT_RE.match(parts[i]):
        i += 1
    if i >= len(parts):
        return line

    prefix = parts[:i]
    items = parts[i:]
    out_items: list[str] = []
    pending_count: int | None = None

    def flush_unit(unit_tok: str) -> None:
        nonlocal pending_count
        count = pending_count if pending_count is not None else 1
        pending_count = None
        new_count = max(1, int(round(count / 1.5)))
        if new_count > 1:
            out_items.append(str(new_count))
        out_items.append(unit_tok)

    for tok in items:
        if tok in ("neutral", "non_neutral"):
            out_items.append(tok)
            continue
        if _is_grid_ref(tok):
            out_items.append(tok)
            continue
        if tok.startswith("-"):
            out_items.append(tok)
            continue
        if INT_RE.match(tok):
            pending_count = int(tok)
            continue
        flush_unit(tok)

    return " ".join(prefix + out_items)


def _restore_player_start_values(line: str) -> str:
    parts = line.split()
    if not parts or parts[0] != "player" or len(parts) < 3:
        return line
    if not (INT_RE.match(parts[1]) and INT_RE.match(parts[2])):
        return line
    try:
        res = max(5, int(round(int(parts[1]) / 1.6)))
        pop = max(5, int(round(int(parts[2]) / 1.6)))
    except ValueError:
        return line
    return f"player {res} {pop} " + " ".join(parts[3:])


def _restore_resource_amount(line: str) -> str:
    parts = line.split()
    if len(parts) < 3 or parts[0] not in ("goldmines", "woods"):
        return line
    if not INT_RE.match(parts[1]):
        return line
    try:
        amount = max(1, int(round(int(parts[1]) / 1.75)))
    except ValueError:
        return line
    return f"{parts[0]} {amount} " + " ".join(parts[2:])


def adapt_definition_for_solo(definition: str) -> str:
    """Strip co-op-only map edits so solo uses baseline layout/enemy counts."""
    if not is_coop_authored_map(definition):
        return definition

    lines = definition.splitlines()
    out: list[str] = []
    player_kept = False
    skip_partner_block = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("nb_players_min ") or stripped.startswith("nb_players_max "):
            continue
        if stripped.startswith("random_starts "):
            continue
        if stripped in ALLIANCE_TRIGGERS:
            continue
        if stripped.startswith("; co-op duo version;"):
            continue
        if stripped == COOP_MARKER:
            continue
        if stripped.startswith("; co-op alliances at start"):
            continue

        if stripped == PARTNER_ECONOMY_MARKER:
            skip_partner_block = True
            continue
        if skip_partner_block:
            if stripped.startswith("; ") or stripped.startswith("player "):
                skip_partner_block = False
            elif stripped.startswith("woods ") or stripped.startswith("additional_meadows "):
                continue
            else:
                skip_partner_block = False

        if stripped.startswith("trigger player2 ("):
            continue

        if stripped.startswith("player "):
            if player_kept:
                continue
            player_kept = True
            out.append(_restore_player_start_values(line))
            continue

        if stripped.startswith("computer_only "):
            out.append(_deintensify_computer_only_line(line))
            continue

        if stripped.startswith("goldmines ") or stripped.startswith("woods "):
            out.append(_restore_resource_amount(line))
            continue

        out.append(line)

    result = "\n".join(out)
    if definition.endswith("\n"):
        result += "\n"
    return result


def map_for_solo_campaign(map_: "Map") -> "Map":
    """Return a ``Map`` copy whose definition is adapted for single-player."""
    from .mapfile import Map

    adapted_def = adapt_definition_for_solo(map_.definition or "")
    if adapted_def == (map_.definition or ""):
        return map_

    solo = Map()
    solo.name = map_.name
    solo.buffer_name = map_.buffer_name
    solo.resources = map_.resources
    solo.definition = adapted_def
    solo._load_header()
    solo.buffer = adapted_def.encode("utf-8", errors="replace")
    return solo
