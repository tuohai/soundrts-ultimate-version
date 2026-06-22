"""Generate cumulative xp_thresholds from compact growth rules."""
from __future__ import annotations

from .lib.log import warning


def generate_xp_thresholds(growth: list, max_level: int) -> list[int]:
    """Build cumulative XP gates for levels 2..max_level.

    ``growth`` is the token list after ``xp_threshold_growth`` in rules.txt.
    ``max_level`` is the hero cap (e.g. 100 → 99 thresholds).
    """
    if max_level < 2:
        return []
    count = max_level - 1
    if not growth:
        raise ValueError("xp_threshold_growth is empty")
    kind = str(growth[0]).lower()
    args = growth[1:]
    if kind == "linear":
        return _linear(count, args)
    if kind in ("quadratic", "quad"):
        return _quadratic(count, args)
    if kind in ("polynomial", "poly"):
        return _polynomial(count, args)
    if kind in ("geometric", "geo", "exponential", "exp"):
        return _geometric(count, args)
    raise ValueError(f"unknown xp_threshold_growth type: {kind}")


def _parse_numbers(args: list, expected: int, label: str) -> list[float]:
    if len(args) < expected:
        raise ValueError(f"{label} expects {expected} numeric argument(s), got {len(args)}")
    out = []
    for raw in args[:expected]:
        try:
            out.append(float(raw))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: invalid number {raw!r}") from exc
    return out


def _linear(count: int, args: list) -> list[int]:
    base, step = _parse_numbers(args, 2, "linear")
    thresholds = []
    for i in range(count):
        thresholds.append(max(1, int(round(base + step * i))))
    return _ensure_strictly_increasing(thresholds)


def _quadratic(count: int, args: list) -> list[int]:
    base, a, b = _parse_numbers(args, 3, "quadratic")
    thresholds = []
    for i in range(count):
        value = base + a * i + b * i * i
        thresholds.append(max(1, int(round(value))))
    return _ensure_strictly_increasing(thresholds)


def _polynomial(count: int, args: list) -> list[int]:
    if not args:
        raise ValueError("polynomial expects at least one coefficient")
    coeffs = []
    for raw in args:
        try:
            coeffs.append(float(raw))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"polynomial: invalid coefficient {raw!r}") from exc
    thresholds = []
    for i in range(count):
        value = 0.0
        power = 1.0
        for coeff in coeffs:
            value += coeff * power
            power *= i
        thresholds.append(max(1, int(round(value))))
    return _ensure_strictly_increasing(thresholds)


def _geometric(count: int, args: list) -> list[int]:
    first, ratio = _parse_numbers(args, 2, "geometric")
    if first <= 0:
        raise ValueError("geometric: first threshold must be positive")
    if ratio <= 0:
        raise ValueError("geometric: ratio must be positive")
    thresholds = []
    for i in range(count):
        thresholds.append(max(1, int(round(first * (ratio ** i)))))
    return _ensure_strictly_increasing(thresholds)


def _ensure_strictly_increasing(thresholds: list[int]) -> list[int]:
    if not thresholds:
        return thresholds
    fixed = [thresholds[0]]
    for value in thresholds[1:]:
        if value <= fixed[-1]:
            fixed.append(fixed[-1] + 1)
        else:
            fixed.append(value)
    if fixed != thresholds:
        warning(
            "xp_threshold_growth produced non-increasing values; "
            "adjusted later thresholds by +1 until strictly increasing"
        )
    return fixed


def expand_xp_thresholds_in_definition(defn: dict, unit_name: str) -> None:
    """If ``xp_threshold_growth`` is set, fill ``xp_thresholds`` and strip helpers."""
    if defn.get("xp_thresholds"):
        if defn.get("xp_threshold_growth"):
            warning(
                "in %s: xp_thresholds is set; ignoring xp_threshold_growth",
                unit_name,
            )
        return
    growth = defn.get("xp_threshold_growth")
    if not growth:
        return
    max_level = defn.get("max_level")
    if not max_level:
        warning(
            "in %s: xp_threshold_growth requires max_level",
            unit_name,
        )
        return
    try:
        max_level = int(max_level)
        if isinstance(growth, str):
            growth = growth.split()
        defn["xp_thresholds"] = generate_xp_thresholds(list(growth), max_level)
    except (TypeError, ValueError) as exc:
        warning("in %s: %s", unit_name, exc)
