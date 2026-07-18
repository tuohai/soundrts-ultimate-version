#!/usr/bin/env python3
"""Apply co-op layout to Raynor campaign mission maps (single ``N.txt`` per chapter).

AoE-style: one mission file supports solo and co-op via ``nb_players_min/max`` and
dual player starts. Run after editing solo baselines, or to refresh co-op transforms.
"""

from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_DIR = ROOT / "res" / "single" / "The Legend of Raynor"

GRID_REF_RE = re.compile(r"^[a-z][0-9]+$", re.IGNORECASE)
LETTER_GRID_RE = re.compile(r"^([a-z]+)(\d+)$", re.IGNORECASE)
INT_RE = re.compile(r"^[0-9]+$")
COORD_RE = re.compile(r"^(\d+),(\d+)$")

COOP_HEADER_TMPL = "; co-op duo version; single-player uses {n}.txt"

ALLIANCE_TRIGGERS = [
    "trigger player1 (timer 0) (alliance 1)",
    "trigger player2 (timer 0) (alliance 1)",
    "trigger computers (timer 0) (alliance 2)",
]

NB_PLAYERS_BLOCK = [
    "",
    "; co-op: 1-2 human allies (AoE-style cooperative campaign)",
    "nb_players_min 1",
    "nb_players_max 2",
    "random_starts 0",
]

RESOURCE_KEYS = frozenset({"goldmines", "woods"})
PATH_KEYS = frozenset({"west_east_paths", "west_east_bridges"})


def is_grid_ref(token: str) -> bool:
    return bool(GRID_REF_RE.match(token.strip()))


def col_to_idx(col: str) -> int:
    return ord(col.lower()[0]) - ord("a")


def idx_to_col(idx: int) -> str:
    return chr(ord("a") + idx)


def parse_square_token(token: str) -> tuple[int, int] | None:
    """Parse a map square token; return (col_0based, row_1based) or None."""
    t = token.strip()
    m = COORD_RE.match(t)
    if m:
        return int(m.group(1)) - 1, int(m.group(2))
    m = LETTER_GRID_RE.match(t)
    if not m:
        return None
    letters, digits = m.group(1), m.group(2)
    col = 0
    for ch in letters.lower():
        col = col * 26 + (ord(ch) - ord("a") + 1)
    col -= 1
    try:
        row = int(digits)
    except ValueError:
        return None
    return col, row


def parse_grid_ref(ref: str) -> tuple[int, int] | None:
    return parse_square_token(ref)


def format_square_token(col_0based: int, row_1based: int) -> str:
    if 0 <= col_0based < 26:
        return f"{idx_to_col(col_0based)}{row_1based}"
    return f"{col_0based + 1},{row_1based}"


def format_grid_ref(col: int, row: int) -> str:
    return format_square_token(col, row)


def mirror_grid_ref(ref: str, nb_columns: int) -> str:
    parsed = parse_grid_ref(ref)
    if parsed is None:
        return ref
    col, row = parsed
    return format_grid_ref(nb_columns - 1 - col, row)


def scale_resource_amount(amount: int) -> int:
    return max(amount, int(math.ceil(amount * 1.75)))


def scale_player_start_values(res: str, pop: str) -> tuple[str, str]:
    try:
        res_i = max(5, int(math.ceil(int(res) * 1.6)))
        pop_i = max(5, int(math.ceil(int(pop) * 1.6)))
        return str(res_i), str(pop_i)
    except ValueError:
        return res, pop


def coop_dimensions(nb_columns: int, nb_lines: int) -> tuple[int, int]:
    if nb_columns <= 3:
        new_cols = nb_columns + 2
    elif nb_columns <= 6:
        new_cols = nb_columns + 2
    else:
        new_cols = nb_columns + 1
    new_lines = nb_lines
    if nb_lines <= 3:
        new_lines = max(nb_lines + 1, 4)
    return new_cols, new_lines


def read_map_dimensions(lines: list[str]) -> tuple[int, int]:
    cols, lines_count = 3, 5
    for line in lines:
        parts = line.split()
        if len(parts) == 2 and parts[0] == "nb_columns":
            cols = int(parts[1])
        elif len(parts) == 2 and parts[0] == "nb_lines":
            lines_count = int(parts[1])
    return cols, lines_count


def first_player_start_square(player_line: str) -> str | None:
    parts = player_line.split()
    if not parts or parts[0] != "player":
        return None
    i = 1
    while i < len(parts):
        tok = parts[i]
        if tok.startswith("-"):
            i += 1
            continue
        if INT_RE.match(tok):
            i += 1
            continue
        if is_grid_ref(tok):
            return tok
        i += 1
    return None


def mirror_player_line(player_line: str, nb_columns: int) -> str:
    """Build a fair partner spawn on the opposite flank (not a naive text mirror)."""
    parts = player_line.split()
    if not parts or parts[0] != "player":
        return player_line

    p1_sq = first_player_start_square(player_line)
    if p1_sq is None:
        return player_line
    p1_col, p1_row = parse_grid_ref(p1_sq)  # type: ignore[misc]
    p2_col = nb_columns - 1 - p1_col
    p2_sq = format_grid_ref(p2_col, p1_row)
    p2_side = format_grid_ref(max(0, p2_col - 1), p1_row)

    res, pop = parts[1], parts[2]
    bans = [p for p in parts[3:] if p.startswith("-")]
    ban_text = (" ".join(bans) + " ") if bans else ""
    return (
        f"player {res} {pop} {ban_text}{p2_sq} townhall 2 peasant footman "
        f"{p2_side} house footman"
    ).replace("  ", " ")


def extend_square_name_line(line: str, new_cols: int) -> str:
    parts = line.split()
    if len(parts) < 2 or parts[0] != "square_name":
        return line
    coords: list[tuple[int, int]] = []
    for tok in parts[1:]:
        m = COORD_RE.match(tok)
        if m:
            coords.append((int(m.group(1)), int(m.group(2))))
    if not coords:
        return line
    max_x = max(x for x, _y in coords)
    if max_x >= new_cols:
        return line
    rows: dict[int, set[int]] = {}
    for x, y in coords:
        rows.setdefault(y, set()).add(x)
    extras: list[str] = []
    for y in sorted(rows):
        if max(rows[y]) >= max_x:
            for x in range(max_x + 1, new_cols + 1):
                pair = f"{x},{y}"
                if pair not in parts:
                    extras.append(pair)
    if not extras:
        return line
    return line + " " + " ".join(extras)


def sanitize_we_path_line(line: str, nb_columns: int) -> str:
    """Remove easternmost-column tokens that would create a wrap-around portal."""
    parts = line.split()
    if len(parts) < 2 or parts[0] not in PATH_KEYS:
        return line
    east_col = nb_columns - 1
    kept = [parts[0]]
    for tok in parts[1:]:
        parsed = parse_square_token(tok)
        if parsed is None:
            continue
        col, _row = parsed
        if col != east_col:
            kept.append(tok)
    return " ".join(kept)


def full_grid_we_path_lines(nb_columns: int, nb_lines: int) -> list[str]:
    """Build west_east_paths rows using x,y tokens (cols 1..nb_columns-1)."""
    lines: list[str] = []
    for row in range(1, nb_lines + 1):
        tokens = [f"{col},{row}" for col in range(1, nb_columns)]
        lines.append("west_east_paths " + " ".join(tokens))
    return lines


def extend_west_east_paths_line(line: str, old_cols: int, new_cols: int) -> str:
    parts = line.split()
    if len(parts) < 2 or parts[0] not in PATH_KEYS:
        return line
    refs = parts[1:]
    by_row: dict[int, set[int]] = {}
    for ref in refs:
        parsed = parse_square_token(ref)
        if parsed is None:
            continue
        col, row = parsed
        by_row.setdefault(row, set()).add(col)
    additions: list[str] = []
    for row, cols in by_row.items():
        for col in range(max(cols) + 1, new_cols - 1):
            additions.append(format_square_token(col, row))
    if not additions:
        return line
    return line + " " + " ".join(additions)


def fix_map_path_wrap(lines: list[str]) -> list[str]:
    """Fix west-east path wrap portals in an existing mission map."""
    nb_columns, nb_lines = read_map_dimensions(lines)
    out: list[str] = []
    we_path_block: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("west_east_paths "):
            if we_path_block is None:
                we_path_block = []
            we_path_block.append(line)
            continue
        if we_path_block is not None:
            if nb_columns > 26 and len(we_path_block) >= nb_lines:
                out.extend(full_grid_we_path_lines(nb_columns, nb_lines))
            else:
                for path_line in we_path_block:
                    out.append(sanitize_we_path_line(path_line, nb_columns))
            we_path_block = None
        if stripped.startswith("west_east_bridges "):
            out.append(sanitize_we_path_line(line, nb_columns))
            continue
        out.append(line)
    if we_path_block is not None:
        if nb_columns > 26 and len(we_path_block) >= nb_lines:
            out.extend(full_grid_we_path_lines(nb_columns, nb_lines))
        else:
            for path_line in we_path_block:
                out.append(sanitize_we_path_line(path_line, nb_columns))
    return out


def boost_resource_lines(lines: list[str], nb_columns: int) -> list[str]:
    out: list[str] = []
    for line in lines:
        parts = line.split()
        if not parts:
            out.append(line)
            continue
        key = parts[0]
        if key in RESOURCE_KEYS and len(parts) >= 3 and INT_RE.match(parts[1]):
            amount = scale_resource_amount(int(parts[1]))
            refs = parts[2:]
            out.append(f"{key} {amount} " + " ".join(refs))
            mirror_refs: list[str] = []
            for ref in refs:
                if not is_grid_ref(ref):
                    continue
                mref = mirror_grid_ref(ref, nb_columns)
                if mref != ref and mref not in refs and mref not in mirror_refs:
                    mirror_refs.append(mref)
            if mirror_refs:
                out.append(f"{key} {amount} " + " ".join(mirror_refs))
            continue
        if key == "additional_meadows" and len(parts) >= 2:
            refs = parts[1:]
            extra = list(refs)
            for ref in refs:
                if is_grid_ref(ref):
                    mref = mirror_grid_ref(ref, nb_columns)
                    if mref not in extra:
                        extra.append(mref)
            out.append("additional_meadows " + " ".join(extra))
            continue
        if key == "nb_meadows_by_square" and len(parts) == 2:
            try:
                n = int(parts[1])
                out.append(f"nb_meadows_by_square {max(n + 1, 2)}")
                continue
            except ValueError:
                pass
        out.append(line)
    return out


def partner_base_block(p2_start: str, nb_columns: int) -> list[str]:
    parsed = parse_grid_ref(p2_start)
    if parsed is None:
        return []
    col, row = parsed
    side_col = max(0, col - 1)
    wood_sq = format_grid_ref(side_col, row)
    return [
        "",
        "; co-op symmetric partner economy",
        f"woods 100 {wood_sq} {p2_start}",
        f"additional_meadows {p2_start} {wood_sq}",
    ]


def expand_coop_layout(lines: list[str]) -> tuple[list[str], int]:
    old_cols, old_lines = read_map_dimensions(lines)
    new_cols, new_lines = coop_dimensions(old_cols, old_lines)

    out: list[str] = []
    first_player: str | None = None

    for line in lines:
        stripped = line.strip()
        parts = stripped.split() if stripped else []

        if len(parts) == 2 and parts[0] == "nb_columns":
            out.append(f"nb_columns {new_cols}")
            continue
        if len(parts) == 2 and parts[0] == "nb_lines":
            out.append(f"nb_lines {new_lines}")
            continue
        if stripped.startswith("square_name "):
            out.append(extend_square_name_line(line, new_cols))
            continue
        if stripped.startswith("west_east_paths ") or stripped.startswith(
            "west_east_bridges "
        ):
            fixed = sanitize_we_path_line(line, old_cols)
            fixed = extend_west_east_paths_line(fixed, old_cols, new_cols)
            out.append(sanitize_we_path_line(fixed, new_cols))
            continue
        if stripped.startswith("player ") and first_player is None:
            first_player = line
            p = line.split()
            if len(p) >= 3 and INT_RE.match(p[1]) and INT_RE.match(p[2]):
                res, pop = scale_player_start_values(p[1], p[2])
                out.append(f"player {res} {pop} " + " ".join(p[3:]))
            else:
                out.append(line)
            continue

        out.append(line)

    boosted: list[str] = []
    in_resources = False
    for line in out:
        s = line.strip()
        if s == "; resources":
            in_resources = True
            boosted.append(line)
            continue
        if in_resources and s.startswith("; players"):
            if first_player:
                p1_sq = first_player_start_square(first_player)
                if p1_sq:
                    p2_sq = mirror_grid_ref(p1_sq, new_cols)
                    boosted.extend(partner_base_block(p2_sq, new_cols))
            in_resources = False
            boosted.append(line)
            continue
        if in_resources:
            boosted.extend(boost_resource_lines([line], new_cols))
        else:
            boosted.append(line)

    return boosted, new_cols


def intensify_computer_only_line(line: str) -> str:
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
        new_count = max(1, int(math.ceil(count * 1.5)))
        if new_count > 1:
            out_items.append(str(new_count))
        out_items.append(unit_tok)

    for tok in items:
        if tok in ("neutral", "non_neutral"):
            out_items.append(tok)
            continue
        if is_grid_ref(tok) or COORD_RE.match(tok):
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


def adjust_timer_coefficient(line: str, *, random_chapter: bool) -> str:
    parts = line.split()
    if len(parts) != 2 or parts[0] != "timer_coefficient":
        return line
    try:
        old = int(parts[1])
    except ValueError:
        return line
    if random_chapter:
        new_val = 70
    else:
        new_val = max(40, int(old * 0.7))
    return f"timer_coefficient {new_val}"


def is_nb_players_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("nb_players_min ") or stripped.startswith("nb_players_max ")


def is_alliance_trigger_line(line: str) -> bool:
    return line.strip() in ALLIANCE_TRIGGERS


def mirror_player1_trigger(line: str) -> str | None:
    stripped = line.strip()
    if not stripped.startswith("trigger player1 ("):
        return None
    if "cut_scene" in stripped:
        return None
    return stripped.replace("trigger player1 (", "trigger player2 (", 1)


def find_triggers_section_start(lines: list[str]) -> int:
    for i, line in enumerate(lines):
        if line.strip().lower() == "; triggers":
            return i
    for i, line in enumerate(lines):
        if line.strip().startswith("timer_coefficient "):
            return i
    for i, line in enumerate(lines):
        if line.strip().startswith("trigger "):
            return i
    return len(lines)


def insert_nb_players_after_map_size(lines: list[str]) -> list[str]:
    last_size_idx = -1
    for i, line in enumerate(lines):
        key = line.strip().split()[0] if line.strip() else ""
        if key in ("square_width", "nb_columns", "nb_lines"):
            last_size_idx = i
    if last_size_idx < 0:
        return lines
    out = lines[: last_size_idx + 1]
    out.extend(NB_PLAYERS_BLOCK)
    out.extend(lines[last_size_idx + 1 :])
    return out


def strip_coop_artifacts(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        s = line.strip()
        if is_nb_players_line(line):
            continue
        if is_alliance_trigger_line(line):
            continue
        if s.startswith("; co-op duo version;"):
            continue
        if s == "; co-op: 1-2 human allies (AoE-style cooperative campaign)":
            continue
        if s.startswith("; co-op symmetric partner economy"):
            continue
        if s.startswith("trigger player2 ("):
            continue
        if s.startswith("random_starts "):
            continue
        out.append(line)
    return out


def process_triggers(lines: list[str], *, random_chapter: bool) -> list[str]:
    start = find_triggers_section_start(lines)
    before = lines[:start]
    section = lines[start:]

    processed_before: list[str] = []
    for line in before:
        if line.strip().startswith("trigger player1 ("):
            processed_before.append(line)
            m = mirror_player1_trigger(line)
            if m:
                processed_before.append(m)
        else:
            processed_before.append(line)

    out_section: list[str] = []
    alliance_inserted = False
    i = 0
    while i < len(section):
        line = section[i]
        stripped = line.strip()

        if stripped.startswith("timer_coefficient "):
            out_section.append(adjust_timer_coefficient(line, random_chapter=random_chapter))
            i += 1
            if not alliance_inserted:
                out_section.append("")
                out_section.append("; co-op alliances at start")
                out_section.extend(ALLIANCE_TRIGGERS)
                alliance_inserted = True
            continue

        if stripped.lower() == "; triggers":
            out_section.append(line)
            i += 1
            continue

        if stripped.startswith("trigger player1 ("):
            out_section.append(line)
            m = mirror_player1_trigger(line)
            if m:
                out_section.append(m)
            i += 1
            continue

        out_section.append(line)
        i += 1

    if not alliance_inserted and section:
        out_section = [
            "",
            "; co-op alliances at start",
            *ALLIANCE_TRIGGERS,
            "",
            *out_section,
        ]

    return processed_before + out_section


def transform_mission_lines(lines: list[str]) -> list[str]:
    lines = strip_coop_artifacts(lines)
    lines, nb_columns = expand_coop_layout(lines)

    player_indices = [i for i, ln in enumerate(lines) if ln.strip().startswith("player ")]
    duplicate_at: int | None = None
    duplicate_line: str | None = None
    if len(player_indices) == 1:
        idx = player_indices[0]
        duplicate_at = idx + 1
        duplicate_line = mirror_player_line(lines[idx], nb_columns)

    out: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("computer_only "):
            out.append(intensify_computer_only_line(line))
        else:
            out.append(line)
        if duplicate_at is not None and i == player_indices[0]:
            out.append(duplicate_line)

    out = insert_nb_players_after_map_size(out)
    out = process_triggers(out, random_chapter=False)
    return out


def transform_random_chapter_lines(lines: list[str], n: int) -> list[str]:
    lines = strip_coop_artifacts(lines)
    out: list[str] = []
    has_random_starts = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("players "):
            out.append("players 2")
        elif stripped.startswith("timer_coefficient "):
            out.append("timer_coefficient 70")
        elif stripped.startswith("random_starts "):
            out.append("random_starts 0")
            has_random_starts = True
        elif stripped.startswith("treasure "):
            parts = stripped.split()
            if len(parts) == 2:
                level = parts[1].lower()
                order = ("none", "low", "medium", "high")
                if level in order:
                    idx = min(len(order) - 1, order.index(level) + 1)
                    out.append(f"treasure {order[idx]}")
                    continue
        else:
            out.append(line)
    if not has_random_starts:
        out.insert(1, "random_starts 0")
    return process_triggers(out, random_chapter=True)


def generate_coop_map(n: int) -> Path | None:
    src = MAP_DIR / f"{n}.txt"
    if not src.is_file():
        return None
    text = src.read_text(encoding="utf-8")
    raw_lines = text.splitlines()
    is_random = any(ln.strip() == "random_map_chapter" for ln in raw_lines)

    if is_random:
        out_lines = transform_random_chapter_lines(raw_lines, n)
    else:
        body = transform_mission_lines(raw_lines)
        if body and body[0].strip().startswith("; co-op duo version;"):
            body = body[1:]
            while body and not body[0].strip():
                body = body[1:]
        out_lines = body
    dest = MAP_DIR / f"{n}.txt"
    dest.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return dest


def main() -> None:
    generated: list[Path] = []
    for n in range(1, 30):
        path = generate_coop_map(n)
        if path is not None:
            generated.append(path)
    print(f"Updated {len(generated)} mission map file(s) for co-op.")
    for p in generated:
        print(p)


if __name__ == "__main__":
    main()
