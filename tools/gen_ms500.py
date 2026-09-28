"""Generate res/multi/msN.txt — large procedurally-generated land FFA maps.

The layout is generated with a fixed seed so re-runs are reproducible.
It is *not* a copy of any existing map.

Output targets (size -> filename)
---------------------------------
* 500x500 -> res/multi/ms500.txt   (giant, engine-friendly with patches)
* 200x200 -> res/multi/ms200.txt   (perf-safe fallback)

Design notes
------------
* Coordinates use the parser's 1-based "col,row" form, e.g. "1,1".
* Main east-west corridors every (size // 10) rows; main north-south corridors
  every (size // 10) columns. Keeps the map navigable at any scale.
* Players start at the four inner corners (clamped well inside the borders).
* Goldmines and woods are sprinkled on free squares; the count is scaled
  with the map area.
* Default starting loadout (`townhall house peasant`) matches the common
  pattern in res/multi.
"""

import argparse
import random
from pathlib import Path


def _corridor_step(n):
    # corridor every size//10, min 5 cells apart
    return max(5, n // 10)


def _start_squares(n):
    margin = max(10, n // 10)
    inner = n - margin
    return [
        f"{margin},{margin}",
        f"{margin},{inner}",
        f"{inner},{margin}",
        f"{inner},{inner}",
    ]


def coord(col, row):
    return f"{col},{row}"


def chunk(values, per_line):
    values = list(values)
    return [values[i:i + per_line] for i in range(0, len(values), per_line)]


def build_paths(rng, n):
    step = _corridor_step(n)
    we_rows = [1] + list(range(step, n + 1, step))
    sn_cols = [1] + list(range(step, n + 1, step))

    # NB: range goes up to n-1 (inclusive) instead of n to avoid the engine's
    # toroidal wrap. _create_we_passage treats cx+1 == nb_columns as a portal
    # back to col 0; a 1-based ``(N, row)`` would become 0-based ``(N-1, row)``
    # and trigger ``(N-1, row) -> (0, row)``. Same idea for sn.
    we = {}
    sn = {}
    for y in we_rows:
        we.setdefault(y, set()).update(range(1, n))
    for x in sn_cols:
        sn.setdefault(x, set()).update(range(1, n))

    starts = {tuple(map(int, s.split(","))) for s in _start_squares(n)}
    busy = {(x, y) for y, xs in we.items() for x in xs}
    busy |= {(x, y) for x, ys in sn.items() for y in ys}
    busy |= starts

    # secondary branches — count scales with area
    extra = max(80, n * n // 2000)
    for _ in range(extra):
        x = rng.randint(1, n)
        y = rng.randint(1, n)
        if (x, y) in busy:
            continue
        # Drop secondary branches that would land on (n, *) or (*, n) or
        # (0, *) or (*, 0) — engine would either wrap or reject them.
        if x == n or x == 0 or y == n or y == 0:
            continue
        busy.add((x, y))
        if rng.random() < 0.5:
            we.setdefault(y, set()).add(x)
            for dx in range(1, rng.randint(3, 30)):
                nx = x + dx * rng.choice((-1, 1))
                if 1 <= nx < n:
                    we[y].add(nx)
        else:
            sn.setdefault(x, set()).add(y)
            for dy in range(1, rng.randint(3, 30)):
                ny = y + dy * rng.choice((-1, 1))
                if 1 <= ny < n:
                    sn[x].add(ny)

    we_lines = []
    for y in sorted(we):
        xs = sorted(we[y])
        for c in chunk(xs, per_line=40):
            we_lines.append(
                f"west_east_paths {' '.join(coord(x, y) for x in c)}"
            )

    sn_lines = []
    for x in sorted(sn):
        ys = sorted(sn[x])
        for c in chunk(ys, per_line=40):
            sn_lines.append(
                f"south_north_paths {' '.join(coord(x, y) for y in c)}"
            )

    return we_lines, sn_lines, busy, starts


def build_resources(rng, n, busy):
    # density ~1 deposit per (n*n / 80) cells, capped
    n_each = max(40, min(800, n * n // 80))

    def random_free_square():
        for _ in range(50):
            x = rng.randint(1, n)
            y = rng.randint(1, n)
            if (x, y) not in busy:
                return x, y
        return None

    deposits = []
    used = set()
    for kind, target in (("goldmine", n_each), ("wood", n_each)):
        for _ in range(target):
            s = random_free_square()
            if s is None or s in used:
                continue
            used.add(s)
            deposits.append((kind, s))

    gold_lines, wood_lines = [], []
    for kind, (x, y) in deposits:
        if kind == "goldmine":
            gold_lines.append(f"goldmines 50 {coord(x, y)}")
        else:
            wood_lines.append(f"woods 50 {coord(x, y)}")
    return gold_lines, wood_lines


def build_high_grounds(rng, n, busy, starts):
    squares = []
    target = max(10, n // 12)
    for _ in range(target):
        for _ in range(20):
            x = rng.randint(1, n)
            y = rng.randint(1, n)
            if (x, y) not in busy:
                squares.append(coord(x, y))
                break
    return squares


def emit(n, we_lines, sn_lines, gold_lines, wood_lines, high_grounds):
    lines = []
    lines.append(
        f"; multiplayer map ms{n} - {n}x{n} land FFA (2-4 players)"
    )
    lines.append("; procedurally generated, see tools/gen_ms500.py")
    lines.append("title 5012 5009 3500")
    lines.append("objective 145 88")
    lines.append("")
    lines.append("square_width 12")
    lines.append(f"nb_columns {n}")
    lines.append(f"nb_lines {n}")
    lines.append("")
    lines.extend(we_lines)
    lines.append("")
    lines.extend(sn_lines)
    if high_grounds:
        lines.append("")
        lines.append("high_grounds " + " ".join(high_grounds))
    lines.append("")
    lines.extend(gold_lines)
    lines.append("")
    lines.extend(wood_lines)
    lines.append("")
    # 1 meadow per square is enough on maps >= 200x200 (40K+ cells; players
    # never build on more than a tiny fraction). Smaller maps keep 4 to give
    # each starting base several expansion slots.
    nb_meadows = 1 if n >= 200 else 4
    lines.append(f"nb_meadows_by_square {nb_meadows}")
    lines.append("global_population_limit 200")
    lines.append("")
    lines.append("nb_players_min 2")
    lines.append("nb_players_max 4")
    lines.append("")
    lines.append(
        "starting_squares " + " ".join(_start_squares(n))
    )
    lines.append("starting_units townhall house peasant")
    lines.append("starting_resources 100 100")
    return "\n".join(lines) + "\n"


def generate(n, seed):
    rng = random.Random(seed)
    we_lines, sn_lines, busy, starts = build_paths(rng, n)
    gold_lines, wood_lines = build_resources(rng, n, busy)
    high_grounds = build_high_grounds(rng, n, busy, starts)
    return emit(n, we_lines, sn_lines, gold_lines, wood_lines, high_grounds)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[500, 200],
        help="Map sizes to generate (default: 500 200)",
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    out_dir = repo / "res" / "multi"
    out_dir.mkdir(parents=True, exist_ok=True)
    for size in args.sizes:
        content = generate(size, seed=20260926)
        path = out_dir / f"ms{size}.txt"
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path} ({len(content):,} bytes, {size}x{size})")


if __name__ == "__main__":
    main()
