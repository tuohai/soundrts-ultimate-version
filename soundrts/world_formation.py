"""Rule-driven AoE2-style spatial formations.

Enable with ``def parameters`` / ``formations 1``. Layout types are
``class formation`` definitions (shape, spacing, ranks). Cartesian shapes
are line / box / staggered / flank; polar packing is ring / arc (aliases
circle, wedge, …). An unknown shape with radius / arc_span / rings still
uses polar packing. Military types are listed in ``formation_units``
(``is_a`` match) or flagged with ``use_formation 1``.
"""

from .definitions import MAX_NB_OF_RESOURCE_TYPES
from .lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_sin_1000,
    int_sqrt,
    square_of_distance,
    to_int,
)
from .worldroom import ZoomTarget, format_zoom_target_id

# Same arrive radius as combat slot hold (world_movement).
FORMATION_SLOT_ARRIVE_MM = 250


def _parse_bonus(value):
    """Absolute PRECISION int, or ``('pct', n)`` for ±n percent of the unit stat."""
    if value in (None, "", False):
        return 0
    if isinstance(value, tuple) and len(value) == 2 and value[0] == "pct":
        try:
            n = int(value[1])
        except (TypeError, ValueError):
            return 0
        return ("pct", n) if n else 0
    if isinstance(value, str):
        s = value.strip()
        if s.endswith("%"):
            try:
                n = int(float(s[:-1]))
            except (TypeError, ValueError):
                return 0
            return ("pct", n) if n else 0
        try:
            return int(s)
        except (TypeError, ValueError):
            return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bonus_delta(base, bonus) -> int:
    parsed = _parse_bonus(bonus)
    if not parsed:
        return 0
    if isinstance(parsed, tuple):
        try:
            return int(base or 0) * int(parsed[1]) // 100
        except (TypeError, ValueError):
            return 0
    return int(parsed)


def _bonus_set(bonus) -> bool:
    return bool(_parse_bonus(bonus))


class FormationRules:
    """Metadata for ``class formation`` (not a map entity)."""

    is_a = ()
    expanded_is_a = ()
    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    population_cost = 0
    shape = "line"
    spacing = 1500
    rank_gap = 1800
    flank_gap = 6000
    max_front = 0
    ranks = ()
    keep_pace = 1
    requirements = ()
    mdg = 0
    rdg = 0
    mdf = 0
    rdf = 0
    mdg_vs = {}
    rdg_vs = {}
    mdf_vs = {}
    rdf_vs = {}
    speed = 0
    radius = 0
    rings = 0
    ring_gap = 0
    arc_span = 0
    arc_start = None
    ring_rank = "in"

    @classmethod
    def interpret(cls, d):
        for attr in ("mdg_vs", "rdg_vs", "mdf_vs", "rdf_vs"):
            if attr not in d:
                continue
            parsed = {}
            targets = []
            for s in d.get(attr, []) or ():
                try:
                    if isinstance(s, str) and s.strip().endswith("%"):
                        n = _parse_bonus(s)
                    else:
                        n = to_int(s) if isinstance(s, str) else int(s)
                    for t in targets:
                        parsed[t] = n
                    targets = []
                except (TypeError, ValueError, AssertionError):
                    targets.append(s)
            d[attr] = parsed


_DEFAULT_RANKS = ("melee", "ranged", "siege")
_CARTESIAN_SHAPES = ("line", "box", "staggered", "flank")
_POLAR_SHAPES = ("ring", "arc")
_SHAPE_ALIASES = {
    "circle": "ring",
    "round": "ring",
    "wedge": "arc",
    "cone": "arc",
}
_SHAPES = _CARTESIAN_SHAPES + _POLAR_SHAPES + tuple(_SHAPE_ALIASES)
_TWO_PI_MILLI = 6283  # 2π × 1000
_PI_MILLI = 3142
_COMBAT_FLAT = ("mdg", "rdg", "mdf", "rdf")
_COMBAT_VS = ("mdg_vs", "rdg_vs", "mdf_vs", "rdf_vs")


def _flag_on(value) -> bool:
    if value in (0, "0", False, None, ""):
        return False
    if isinstance(value, (list, tuple)):
        if not value:
            return False
        return str(value[0]) not in ("0", "false", "False")
    return str(value) not in ("0", "false", "False")


def _as_name_list(value):
    if not value:
        return ()
    if isinstance(value, str):
        return tuple(value.split())
    if isinstance(value, (list, tuple)):
        return tuple(str(x) for x in value if x not in (None, ""))
    return ()


def _one_name(value, default):
    if isinstance(value, (list, tuple)):
        value = value[0] if value else default
    s = str(value or default).strip().lower()
    return s or default


def _optional_int(obj, name):
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    if value in (None, "", (), []):
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[0]
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _layout_kind(spec):
    shape = str((spec or {}).get("shape") or "line").strip().lower()
    shape = _SHAPE_ALIASES.get(shape, shape)
    if shape in _CARTESIAN_SHAPES or shape in _POLAR_SHAPES:
        return shape
    if (
        int((spec or {}).get("radius", 0) or 0)
        or int((spec or {}).get("arc_span", 0) or 0)
        or int((spec or {}).get("rings", 0) or 0)
    ):
        span = int((spec or {}).get("arc_span", 0) or 0)
        return "arc" if 0 < span < 360 else "ring"
    return "line"


def _rules():
    from .definitions import rules

    return rules


def formations_enabled() -> bool:
    try:
        return _flag_on(_rules().get("parameters", "formations", 0))
    except Exception:
        return False


def default_formation_name() -> str:
    try:
        name = _rules().get("parameters", "default_formation", "")
    except Exception:
        name = ""
    if isinstance(name, (list, tuple)):
        name = name[0] if name else ""
    name = str(name or "")
    names = formation_type_names()
    if name in names:
        return name
    return names[0] if names else ""


def formation_type_names():
    try:
        rules = _rules()
    except Exception:
        return []
    names = []
    classes = getattr(rules, "classes", None) or {}
    for name, cls in classes.items():
        if getattr(cls, "cls", None) is FormationRules:
            names.append(name)
    return names


def formation_class(name):
    if not name:
        return None
    try:
        cls = _rules().unit_class(name)
    except Exception:
        return None
    if cls is None or getattr(cls, "cls", None) is not FormationRules:
        return None
    return cls


def unit_matches_types(unit, type_names) -> bool:
    names = _as_name_list(type_names)
    if not names:
        return False
    type_name = getattr(unit, "type_name", None)
    if type_name in names:
        return True
    expanded = getattr(unit, "expanded_is_a", None) or ()
    return any(n in expanded for n in names)


def unit_can_form(unit) -> bool:
    if not formations_enabled():
        return False
    if getattr(unit, "hp", 1) <= 0:
        return False
    if getattr(unit, "is_inside", False):
        return False
    if getattr(unit, "speed", 0) <= 0:
        return False
    if int(getattr(unit, "use_formation", 0) or 0):
        return True
    try:
        listed = _rules().get("parameters", "formation_units", ())
    except Exception:
        listed = ()
    return unit_matches_types(unit, listed)


def unit_formation_rank(unit) -> str:
    explicit = getattr(unit, "formation_rank", None) or ""
    if isinstance(explicit, (list, tuple)):
        explicit = explicit[0] if explicit else ""
    explicit = str(explicit).strip()
    if explicit:
        return explicit
    try:
        rules = _rules()
    except Exception:
        return "melee"
    for rank in ("melee", "ranged", "siege"):
        listed = rules.get("parameters", "formation_rank_%s" % rank, ())
        if unit_matches_types(unit, listed):
            return rank
    rdg_range = int(getattr(unit, "rdg_range", 0) or 0)
    mdg_range = int(getattr(unit, "mdg_range", 0) or 0)
    if rdg_range > mdg_range and rdg_range > PRECISION:
        return "ranged"
    return "melee"


def unit_formation_name(unit) -> str:
    name = getattr(unit, "formation", None) or ""
    if isinstance(name, (list, tuple)):
        name = name[0] if name else ""
    name = str(name or "")
    if name and name in formation_type_names():
        return name
    return default_formation_name()


def set_unit_formation(unit, name) -> bool:
    if not unit_can_form(unit):
        return False
    if name not in formation_type_names():
        return False
    unit.formation = name
    return True


def cycle_next_formation(current) -> str:
    names = formation_type_names()
    if not names:
        return ""
    current = current or default_formation_name()
    try:
        idx = names.index(current)
    except ValueError:
        return names[0]
    return names[(idx + 1) % len(names)]


def _param_keep_pace() -> bool:
    try:
        return _flag_on(_rules().get("parameters", "formation_keep_pace", 1))
    except Exception:
        return True


def _spec(name):
    cls = formation_class(name) or formation_class(default_formation_name())
    if cls is None:
        return None
    shape = getattr(cls, "shape", "line") or "line"
    if isinstance(shape, (list, tuple)):
        shape = shape[0] if shape else "line"
    ranks = _as_name_list(getattr(cls, "ranks", ()) or ()) or _DEFAULT_RANKS
    keep = getattr(cls, "keep_pace", 1)
    if keep in (-1, None):
        keep_pace = _param_keep_pace()
    else:
        keep_pace = _flag_on(keep)
    spec = {
        "name": getattr(cls, "type_name", name),
        "shape": str(shape),
        "spacing": max(1, int(getattr(cls, "spacing", 1500) or 1500)),
        "rank_gap": max(1, int(getattr(cls, "rank_gap", 1800) or 1800)),
        "flank_gap": max(0, int(getattr(cls, "flank_gap", 6000) or 0)),
        "max_front": max(0, int(getattr(cls, "max_front", 0) or 0)),
        "ranks": ranks,
        "keep_pace": keep_pace,
        "radius": max(0, _int_stat(cls, "radius")),
        "rings": max(0, _int_stat(cls, "rings")),
        "ring_gap": max(0, _int_stat(cls, "ring_gap")),
        "arc_span": max(0, _int_stat(cls, "arc_span")),
        "arc_start": _optional_int(cls, "arc_start"),
        "ring_rank": _one_name(getattr(cls, "ring_rank", "in"), "in"),
        "mdg": _bonus_stat(cls, "mdg"),
        "rdg": _bonus_stat(cls, "rdg"),
        "mdf": _bonus_stat(cls, "mdf"),
        "rdf": _bonus_stat(cls, "rdf"),
        "mdg_vs": _vs_stat(cls, "mdg_vs"),
        "rdg_vs": _vs_stat(cls, "rdg_vs"),
        "mdf_vs": _vs_stat(cls, "mdf_vs"),
        "rdf_vs": _vs_stat(cls, "rdf_vs"),
        "speed": _bonus_stat(cls, "speed"),
    }
    spec["shape"] = _layout_kind(spec)
    return spec


def _bonus_stat(obj, name):
    return _parse_bonus(getattr(obj, name, 0) if not isinstance(obj, dict) else obj.get(name, 0))


def _int_stat(obj, name) -> int:
    value = obj.get(name, 0) if isinstance(obj, dict) else getattr(obj, name, 0)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else 0
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _vs_stat(obj, name):
    value = getattr(obj, name, None)
    if not isinstance(value, dict) or not value:
        return {}
    out = {}
    for key, val in value.items():
        parsed = _parse_bonus(val)
        if parsed:
            out[str(key)] = parsed
    return out


def _combat_from_spec(spec):
    """Subset of layout spec used in damage/armor/speed; None if all zeros."""
    if spec is None:
        return None
    out = {}
    any_bonus = False
    for key in _COMBAT_FLAT:
        val = _parse_bonus(spec.get(key, 0) if isinstance(spec, dict) else getattr(spec, key, 0))
        out[key] = val
        if _bonus_set(val):
            any_bonus = True
    for key in _COMBAT_VS:
        raw = spec.get(key) if isinstance(spec, dict) else getattr(spec, key, None)
        parsed = raw if isinstance(raw, dict) else {}
        copied = {}
        for name, val in parsed.items():
            bonus = _parse_bonus(val)
            if bonus:
                copied[str(name)] = bonus
        out[key] = copied
        if copied:
            any_bonus = True
    speed = _parse_bonus(spec.get("speed", 0) if isinstance(spec, dict) else getattr(spec, "speed", 0))
    out["speed"] = speed
    if _bonus_set(speed):
        any_bonus = True
    if not any_bonus:
        return None
    return out


def _formation_id_of(unit) -> str:
    name = getattr(unit, "_formation_layout_name", None)
    if isinstance(name, (list, tuple)):
        name = name[0] if name else ""
    name = str(name or "").strip()
    if name:
        return name
    name = getattr(unit, "formation", None)
    if isinstance(name, (list, tuple)):
        name = name[0] if name else ""
    return str(name or "").strip()


def formation_counter_keys(unit):
    """Names that ``mdg_vs`` / ``rdf_vs`` may match on a formed other unit.

    Order is specific first: ``class formation`` type name, then shape aliases
    (``cone`` / ``wedge``), then canonical ``shape`` (``arc``). Empty if the
    other unit is not standing on its slot yet.
    """
    if unit is None or not formation_ranks_formed(unit):
        return ()
    name = _formation_id_of(unit)
    kind = getattr(unit, "_formation_layout_kind", None)
    if not kind and name:
        layout = _spec(name)
        kind = _layout_kind(layout) if layout else None
    if kind:
        kind = str(kind).strip().lower()
    keys = []
    seen = set()
    for key in (name,):
        if key and key not in seen:
            seen.add(key)
            keys.append(key)
    if kind:
        for alias, canon in _SHAPE_ALIASES.items():
            if canon == kind and alias not in seen:
                seen.add(alias)
                keys.append(alias)
        if kind not in seen:
            seen.add(kind)
            keys.append(kind)
    return tuple(keys)


def formation_counter_vs_bonus(vs_dict, other) -> int:
    """First matching formation-name key in *vs_dict*, else 0. Does not stack aliases."""
    if not vs_dict:
        return 0
    for key in formation_counter_keys(other):
        if key not in vs_dict:
            continue
        try:
            return int(vs_dict[key] or 0)
        except (TypeError, ValueError):
            parsed = _parse_bonus(vs_dict[key])
            if not parsed:
                return 0
            if isinstance(parsed, tuple) and parsed[0] == "pct":
                return 0
            try:
                return int(parsed)
            except (TypeError, ValueError):
                return 0
    return 0


def formation_combat_stats(unit, flat_key, vs_key):
    """Unit flat + vs, plus ``class formation`` bonuses once standing on the slot."""
    base = getattr(unit, flat_key, 0)
    vs = getattr(unit, vs_key, None)
    spec = getattr(unit, "_formation_combat_spec", None)
    if not spec:
        return base, vs
    if not formation_ranks_formed(unit):
        return base, vs
    try:
        base_i = int(base or 0)
    except (TypeError, ValueError):
        base_i = 0
    extra = spec.get(flat_key, 0)
    delta = _bonus_delta(base_i, extra)
    if delta:
        base = base_i + delta
    extra_vs = spec.get(vs_key) or None
    if extra_vs:
        merged = dict(vs) if vs else {}
        for name, val in extra_vs.items():
            merged[name] = merged.get(name, 0) + _bonus_delta(base_i, val)
        vs = merged
    return base, vs


def formation_spec(name):
    """Public wrapper: layout dict for a ``class formation`` type name."""
    return _spec(name)


def _rank_index(rank, ranks) -> int:
    try:
        return list(ranks).index(rank)
    except ValueError:
        return len(ranks)


def _facing_from_delta(dx, dy, fallback=90) -> int:
    if dx == 0 and dy == 0:
        return int(fallback) % 360
    return int_angle(0, 0, dx, dy)


def _right_axis(facing):
    # perpendicular, 90° clockwise from facing
    a = (int(facing) - 90) % 360
    return int_cos_1000(a), int_sin_1000(a)


def _forward_axis(facing):
    a = int(facing) % 360
    return int_cos_1000(a), int_sin_1000(a)


def _offset(ox, oy, right_x, right_y, fwd_x, fwd_y, along, back):
    x = ox + (along * right_x) // 1000 - (back * fwd_x) // 1000
    y = oy + (along * right_y) // 1000 - (back * fwd_y) // 1000
    return int(x), int(y)


def _max_cols_for_place(place, spacing, margin) -> int:
    if place is None:
        return 8
    usable = int(place.xmax - place.xmin) - 2 * margin
    cols = usable // max(spacing, 1)
    return max(1, cols)


def _clamp_xy(place, x, y, margin):
    if place is None:
        return int(x), int(y)
    xmin = int(place.xmin) + margin
    xmax = int(place.xmax) - margin
    ymin = int(place.ymin) + margin
    ymax = int(place.ymax) - margin
    if xmin > xmax:
        xmin = xmax = (int(place.xmin) + int(place.xmax)) // 2
    if ymin > ymax:
        ymin = ymax = (int(place.ymin) + int(place.ymax)) // 2
    return max(xmin, min(xmax, int(x))), max(ymin, min(ymax, int(y)))


def _line_slots(n, spec, max_cols):
    """Rows by rank wrap; returns list of (along, back) in mm."""
    spacing = spec["spacing"]
    rank_gap = spec["rank_gap"]
    cols = min(n, max_cols) if n else 1
    cols = max(1, cols)
    slots = []
    for i in range(n):
        row = i // cols
        col = i % cols
        row_n = min(cols, n - row * cols)
        along = ((2 * col - (row_n - 1)) * spacing) // 2
        back = row * rank_gap
        slots.append((along, back))
    return slots


def _stagger_slots(n, spec, max_cols):
    spacing = spec["spacing"]
    rank_gap = spec["rank_gap"]
    cols = min(n, max_cols) if n else 1
    cols = max(1, cols)
    slots = []
    stagger = rank_gap // 2
    for i in range(n):
        row = i // cols
        col = i % cols
        row_n = min(cols, n - row * cols)
        along = ((2 * col - (row_n - 1)) * spacing) // 2
        back = row * rank_gap + (stagger if col % 2 else 0)
        slots.append((along, back))
    return slots


def _box_slots(n, spec):
    spacing = spec["spacing"]
    if n <= 0:
        return []
    cols = int_sqrt(n)
    if cols * cols < n:
        cols += 1
    cols = max(1, cols)
    rows = (n + cols - 1) // cols
    slots = []
    for i in range(n):
        row = i // cols
        col = i % cols
        row_n = min(cols, n - row * cols)
        along = ((2 * col - (row_n - 1)) * spacing) // 2
        back = ((2 * row - (rows - 1)) * spacing) // 2
        slots.append((along, back))
    return slots


def _flank_slots(n, spec, max_cols):
    if n <= 0:
        return []
    if n == 1:
        return [(0, 0)]
    left_n = n // 2
    right_n = n - left_n
    gap = spec["flank_gap"]
    left = _line_slots(left_n, spec, max_cols)
    right = _line_slots(right_n, spec, max_cols)
    half = gap // 2
    out = [(along - half, back) for along, back in left]
    out.extend((along + half, back) for along, back in right)
    return out


def _polar_default_span(kind):
    return 360 if kind == "ring" else 180


def _polar_span(spec, kind):
    span = abs(int((spec or {}).get("arc_span", 0) or 0))
    return span if span else _polar_default_span(kind)


def _polar_start(spec, span):
    start = spec.get("arc_start") if spec else None
    if start is None:
        return 0 if span >= 360 else -(span // 2)
    return int(start)


def _polar_xy(radius, deg):
    d = int(deg) % 360
    r = int(radius)
    along = r * int_sin_1000(d) // 1000
    back = -(r * int_cos_1000(d) // 1000)
    return along, back


def _polar_theta_deg(index, n, start, span):
    if n <= 1:
        return start if span >= 360 else start + span // 2
    if span >= 360:
        return start + (index * 360) // n
    return start + (index * span) // max(n - 1, 1)


def _polar_radius_for_count(n, spec, span):
    r = int((spec or {}).get("radius", 0) or 0)
    if r > 0:
        return r
    spacing = max(1, int((spec or {}).get("spacing", 1500) or 1500))
    if n <= 1:
        return spacing
    if span >= 360:
        return max(spacing // 2, (n * spacing * 1000) // _TWO_PI_MILLI)
    return max(
        spacing // 2,
        (max(n - 1, 1) * spacing * 180000) // (max(span, 1) * _PI_MILLI),
    )


def _polar_ring_gap(spec):
    gap = int((spec or {}).get("ring_gap", 0) or 0)
    if gap > 0:
        return gap
    return max(1, int((spec or {}).get("rank_gap", 1800) or 1800))


def _polar_slots(n, spec, kind):
    n = int(n)
    if n <= 0:
        return []
    if n == 1:
        return [(0, 0)]
    span = _polar_span(spec, kind)
    start = _polar_start(spec, span)
    rings = max(1, int((spec or {}).get("rings", 0) or 1))
    if rings == 1 or n <= rings:
        r = _polar_radius_for_count(n, spec, span)
        return [_polar_xy(r, _polar_theta_deg(i, n, start, span)) for i in range(n)]
    counts = [n // rings] * rings
    extra = n % rings
    for i in range(extra):
        counts[rings - 1 - i] += 1
    gap = _polar_ring_gap(spec)
    inner_n = next((c for c in counts if c), 1)
    inner_r = _polar_radius_for_count(inner_n, spec, span)
    slots = []
    for k, cnt in enumerate(counts):
        if cnt <= 0:
            continue
        r = inner_r + k * gap
        for i in range(cnt):
            slots.append(_polar_xy(r, _polar_theta_deg(i, cnt, start, span)))
    return slots


def compute_slot_offsets(n, spec, place=None, margin=500):
    """Return n (along, back) offsets in mm for the given shape."""
    n = int(n)
    if n <= 0:
        return []
    max_cols = _max_cols(spec, place, margin)
    kind = _layout_kind(spec)
    if kind == "box":
        return _box_slots(n, spec)
    if kind == "staggered":
        return _stagger_slots(n, spec, max_cols)
    if kind == "flank":
        return _flank_slots(n, spec, max_cols)
    if kind in _POLAR_SHAPES:
        return _polar_slots(n, spec, kind)
    return _line_slots(n, spec, max_cols)


def _max_cols(spec, place, margin):
    max_front = spec["max_front"]
    if max_front <= 0:
        return _max_cols_for_place(place, spec["spacing"], margin)
    return max(1, max_front)


def sort_units_for_formation(units, spec, right_x, right_y):
    ranks = spec["ranks"]

    def key(unit):
        rank = unit_formation_rank(unit)
        proj = (int(getattr(unit, "x", 0) or 0) * right_x
                + int(getattr(unit, "y", 0) or 0) * right_y)
        return (_rank_index(rank, ranks), proj, str(getattr(unit, "id", "")))

    return sorted(units, key=key)


def _sort_along_right(units, right_x, right_y):
    def key(unit):
        proj = (int(getattr(unit, "x", 0) or 0) * right_x
                + int(getattr(unit, "y", 0) or 0) * right_y)
        return (proj, str(getattr(unit, "id", "")))

    return sorted(units, key=key)


def _units_by_rank(units, spec):
    ranks = spec["ranks"]
    buckets = {r: [] for r in ranks}
    other = []
    for unit in units:
        rank = unit_formation_rank(unit)
        if rank in buckets:
            buckets[rank].append(unit)
        else:
            other.append(unit)
    groups = [(r, buckets[r]) for r in ranks if buckets[r]]
    if other:
        groups.append(("other", other))
    return groups


def _rank_row_slots(n, spec, max_cols, start_back, stagger=False):
    """One rank: wrap into rows. back grows away from the facing edge."""
    spacing = spec["spacing"]
    rank_gap = spec["rank_gap"]
    cols = min(n, max_cols) if n else 1
    cols = max(1, cols)
    stagger_off = rank_gap // 2 if stagger else 0
    slots = []
    rows = 0
    for i in range(n):
        row = i // cols
        col = i % cols
        row_n = min(cols, n - row * cols)
        along = ((2 * col - (row_n - 1)) * spacing) // 2
        extra = stagger_off if (stagger and col % 2) else 0
        slots.append((along, start_back + row * rank_gap + extra))
        rows = row + 1
    next_back = start_back + max(rows, 1) * rank_gap
    return slots, next_back


def _line_rank_offsets(units, spec, max_cols, right_x, right_y, stagger=False):
    result = []
    back = 0
    for _rank, members in _units_by_rank(units, spec):
        ordered = _sort_along_right(members, right_x, right_y)
        slots, back = _rank_row_slots(len(ordered), spec, max_cols, back, stagger=stagger)
        result.extend(zip(ordered, slots))
    return result


def _box_rank_offsets(units, spec, right_x, right_y):
    ordered = sort_units_for_formation(units, spec, right_x, right_y)
    return list(zip(ordered, _box_slots(len(ordered), spec)))


def _flank_rank_offsets(units, spec, max_cols, right_x, right_y):
    left = []
    right = []
    for _rank, members in _units_by_rank(units, spec):
        ordered = _sort_along_right(members, right_x, right_y)
        left_n = len(ordered) // 2
        left.extend(ordered[:left_n])
        right.extend(ordered[left_n:])
    if not left:
        return _line_rank_offsets(right, spec, max_cols, right_x, right_y)
    if not right:
        return _line_rank_offsets(left, spec, max_cols, right_x, right_y)
    half = spec["flank_gap"] // 2
    out = []
    for unit, (along, back) in _line_rank_offsets(left, spec, max_cols, right_x, right_y):
        out.append((unit, (along - half, back)))
    for unit, (along, back) in _line_rank_offsets(right, spec, max_cols, right_x, right_y):
        out.append((unit, (along + half, back)))
    return out


def _polar_rank_offsets(units, spec, right_x, right_y, kind):
    groups = _units_by_rank(units, spec)
    if not groups:
        return []
    if _one_name(spec.get("ring_rank"), "in") in ("out", "outer", "outside"):
        groups = list(reversed(groups))
    if len(groups) == 1:
        ordered = _sort_along_right(groups[0][1], right_x, right_y)
        return list(zip(ordered, _polar_slots(len(ordered), spec, kind)))
    span = _polar_span(spec, kind)
    start = _polar_start(spec, span)
    gap = _polar_ring_gap(spec)
    max_n = max(len(members) for _rank, members in groups)
    base_r = int(spec.get("radius", 0) or 0) or _polar_radius_for_count(max_n, spec, span)
    out = []
    for k, (_rank, members) in enumerate(groups):
        ordered = _sort_along_right(members, right_x, right_y)
        r = base_r + k * gap
        n = len(ordered)
        for i, unit in enumerate(ordered):
            out.append((unit, _polar_xy(r, _polar_theta_deg(i, n, start, span))))
    return out


def offsets_for_units(units, spec, place=None, margin=500, right_x=1000, right_y=0):
    """Assign (along, back) mm to each unit (AoE2 ranks: melee front, siege back)."""
    if not units or spec is None:
        return []
    max_cols = _max_cols(spec, place, margin)
    kind = _layout_kind(spec)
    if kind == "box":
        return _box_rank_offsets(units, spec, right_x, right_y)
    if kind == "staggered":
        return _line_rank_offsets(units, spec, max_cols, right_x, right_y, stagger=True)
    if kind == "flank":
        return _flank_rank_offsets(units, spec, max_cols, right_x, right_y)
    if kind in _POLAR_SHAPES:
        return _polar_rank_offsets(units, spec, right_x, right_y, kind)
    return _line_rank_offsets(units, spec, max_cols, right_x, right_y)


def _anchor_place_xy(target):
    if target is None:
        return None, 0, 0
    if hasattr(target, "xmin") and hasattr(target, "x"):
        return target, int(target.x), int(target.y)
    place = getattr(target, "place", None)
    x = int(getattr(target, "x", 0) or 0)
    y = int(getattr(target, "y", 0) or 0)
    return place, x, y


def _is_enemy_target(unit, target) -> bool:
    if target is None or unit is None:
        return False
    other = getattr(target, "player", None)
    if other is None:
        return False
    is_enemy = getattr(unit, "is_an_enemy", None)
    if callable(is_enemy):
        try:
            return bool(is_enemy(target))
        except Exception:
            return False
    return False


def assign_formation_slots(units, target, spec, facing=None):
    """Return list of (unit, place, x, y) for formable units."""
    if not units or spec is None:
        return []
    place, ox, oy = _anchor_place_xy(target)
    if facing is None:
        cx = sum(int(getattr(u, "x", 0) or 0) for u in units) // max(len(units), 1)
        cy = sum(int(getattr(u, "y", 0) or 0) for u in units) // max(len(units), 1)
        fallback = int(getattr(units[0], "o", 90) or 90)
        facing = _facing_from_delta(ox - cx, oy - cy, fallback)
    rx, ry = _right_axis(facing)
    fx, fy = _forward_axis(facing)
    margin = 500
    packed = offsets_for_units(units, spec, place, margin, rx, ry)
    result = []
    for unit, (along, back) in packed:
        x, y = _offset(ox, oy, rx, ry, fx, fy, along, back)
        unit_margin = max(margin, int(getattr(unit, "radius", 0) or 0))
        slot_place = place
        if slot_place is None:
            slot_place = getattr(unit, "place", None)
        x, y = _clamp_xy(slot_place, x, y, unit_margin)
        result.append((unit, slot_place, x, y))
    return result


def _zoom_for(place, x, y):
    if place is None:
        return None
    zid = format_zoom_target_id(place.id, x, y, precision=5)
    return ZoomTarget(place, x, y, id=zid, precision=5)


def clear_formation_speed_cap(unit):
    if unit is None:
        return
    if getattr(unit, "_formation_speed_cap", 0):
        unit._formation_speed_cap = 0


def _apply_speed_cap(units, spec):
    if not spec or not spec["keep_pace"]:
        for unit in units:
            clear_formation_speed_cap(unit)
        return
    speeds = [int(getattr(u, "speed", 0) or 0) for u in units]
    speeds = [s for s in speeds if s > 0]
    if not speeds:
        return
    cap = min(speeds)
    for unit in units:
        unit._formation_speed_cap = cap


def _fresh_go_orders(units):
    result = []
    for unit in units:
        world = getattr(unit, "world", None)
        now = getattr(world, "time", None)
        for order in reversed(getattr(unit, "orders", None) or ()):
            if getattr(order, "keyword", None) != "go":
                continue
            created = getattr(order, "_creation_time", None)
            if now is None or created == now:
                result.append((unit, order))
            break
    return result


def _active_go_orders(units):
    result = []
    for unit in units:
        orders = getattr(unit, "orders", None) or ()
        if orders and getattr(orders[0], "keyword", None) == "go":
            result.append((unit, orders[0]))
    return result


def _resolve_formation_anchor(unit, order):
    stored = getattr(order, "_formation_anchor", None)
    if stored is not None:
        return stored
    anchor_id = getattr(order, "_formation_anchor_id", None)
    if anchor_id:
        player = getattr(unit, "player", None)
        getter = getattr(player, "get_object_by_id", None) if player is not None else None
        if callable(getter):
            found = getter(anchor_id)
            if found is not None:
                return found
    return getattr(order, "target", None)


_COMBAT_REFRESH_MS = 400


def _clear_focus_fire(units):
    for unit in units or ():
        if unit is None:
            continue
        if getattr(unit, "_formation_focus_fire", 0):
            unit._formation_focus_fire = 0


def break_formation_hold(units):
    """Drop slots so the group can pile onto a clicked unit (AoE2 right-click)."""
    if units is None:
        return
    if not isinstance(units, (list, tuple)):
        units = (units,)
    for unit in units:
        if unit is None:
            continue
        unit._formation_slot = None
        unit._formation_combat_token = None
        unit._formation_combat_time = None
        unit._formation_combat_spec = None
        unit._formation_layout_name = None
        unit._formation_layout_kind = None
        unit._formation_focus_fire = 1
        clear_formation_speed_cap(unit)


def _bind_formation_slots(slots, token=None, spec=None):
    now = None
    combat = _combat_from_spec(spec)
    layout_name = spec.get("name") if isinstance(spec, dict) else None
    layout_kind = _layout_kind(spec) if spec else None
    for unit, place, x, y in slots:
        unit._formation_slot = (place, int(x), int(y))
        unit._formation_combat_spec = combat
        unit._formation_layout_name = layout_name
        unit._formation_layout_kind = layout_kind
        if token is not None:
            unit._formation_combat_token = token
        if now is None:
            world = getattr(unit, "world", None)
            now = getattr(world, "time", 0) if world is not None else 0
        unit._formation_combat_time = now
        unit._formation_focus_fire = 0


def _retarget_go_pairs(pairs, slots):
    by_id = {id(u): (place, x, y) for u, place, x, y in slots}
    for unit, order in pairs:
        packed = by_id.get(id(unit))
        if not packed:
            continue
        place, x, y = packed
        zoom = _zoom_for(place, x, y)
        if zoom is None:
            continue
        if getattr(order, "_formation_anchor", None) is None:
            order._formation_anchor = getattr(order, "target", None)
        if getattr(order, "_formation_anchor_id", None) is None:
            order._formation_anchor_id = getattr(order.target, "id", None)
        order.target = zoom


def apply_slots_to_go_orders(pairs, spec, facing=None):
    if len(pairs) < 2:
        return
    units = [u for u, _o in pairs]
    target = _resolve_formation_anchor(units[0], pairs[0][1])
    if _is_enemy_target(units[0], target):
        # Right-click / go onto a unit: break ranks and pile in (AoE2 focus fire).
        break_formation_hold(units)
        return
    _clear_focus_fire(units)
    slots = assign_formation_slots(units, target, spec, facing=facing)
    _bind_formation_slots(slots, spec=spec)
    _retarget_go_pairs(pairs, slots)
    _apply_speed_cap(units, spec)


def _formable_layers(units, require_can_form=True):
    pool = units
    if require_can_form:
        pool = [u for u in units if unit_can_form(u)]
    layers = {}
    for unit in pool:
        ag = getattr(unit, "airground_type", "ground") or "ground"
        fname = unit_formation_name(unit)
        layers.setdefault((ag, fname), []).append(unit)
    return layers


def _units_grouped_by_place(units):
    buckets = {}
    for unit in units:
        place = getattr(unit, "place", None)
        if place is None:
            continue
        buckets.setdefault(id(place), []).append(unit)
    return list(buckets.values())


def _go_pairs_grouped_by_place(pairs):
    buckets = {}
    for unit, order in pairs:
        target = _resolve_formation_anchor(unit, order)
        place, _x, _y = _anchor_place_xy(target)
        if place is None:
            place = getattr(unit, "place", None)
        buckets.setdefault(id(place), []).append((unit, order))
    return list(buckets.values())


def apply_move_formation(units):
    """Retarget fresh/current go orders of a command group into formation slots."""
    for layer_units in _formable_layers(units).values():
        if len(layer_units) < 2:
            continue
        spec = _spec(unit_formation_name(layer_units[0]))
        if spec is None:
            continue
        pairs = _fresh_go_orders(layer_units)
        if len(pairs) < 2:
            pairs = _active_go_orders(layer_units)
        for cluster in _go_pairs_grouped_by_place(pairs):
            if len(cluster) < 2:
                continue
            apply_slots_to_go_orders(cluster, spec)


def _rearrange_local_cluster(layer_units, spec):
    if len(layer_units) < 2 or spec is None:
        return
    cx = sum(int(getattr(u, "x", 0) or 0) for u in layer_units) // len(layer_units)
    cy = sum(int(getattr(u, "y", 0) or 0) for u in layer_units) // len(layer_units)
    place = getattr(layer_units[0], "place", None)
    for unit in layer_units:
        p = getattr(unit, "place", None)
        if p is None or getattr(p, "xmin", None) is None:
            continue
        if p.xmin <= cx < p.xmax and p.ymin <= cy < p.ymax:
            place = p
            break
    fallback = int(getattr(layer_units[0], "o", 90) or 90)
    dummy = type("Anchor", (), {"place": place, "x": cx, "y": cy, "id": "formation-idle"})()
    slots = assign_formation_slots(layer_units, dummy, spec, facing=fallback)
    _clear_focus_fire(layer_units)
    _bind_formation_slots(slots, spec=spec)
    _apply_speed_cap(layer_units, spec)
    for unit, slot_place, x, y in slots:
        zoom = _zoom_for(slot_place or place, x, y)
        if zoom is None or not hasattr(unit, "take_order"):
            continue
        unit.take_order(["go", zoom.id], forget_previous=True)
        orders = getattr(unit, "orders", None) or ()
        if orders and getattr(orders[0], "keyword", None) == "go":
            orders[0]._formation_anchor = dummy
            orders[0]._formation_anchor_id = "formation-idle"


def apply_idle_rearrange(units):
    """Idle formable units walk to in-place slots on their own square."""
    formable = [u for u in units if unit_can_form(u)]
    if len(formable) < 2:
        return
    moving_units = [u for u, _o in _active_go_orders(formable)]
    if len(moving_units) >= 2:
        apply_move_formation(moving_units)
    idle = [u for u in formable if u not in moving_units]
    for layer_units in _formable_layers(idle).values():
        spec = _spec(unit_formation_name(layer_units[0]))
        if spec is None:
            continue
        for cluster in _units_grouped_by_place(layer_units):
            _rearrange_local_cluster(cluster, spec)


def _front_standoff(units):
    melee = [u for u in units if unit_formation_rank(u) == "melee"]
    sample = melee or list(units)
    ranges = []
    for unit in sample:
        r = int(getattr(unit, "mdg_range", 0) or 0)
        if r <= 0:
            r = int(getattr(unit, "rdg_range", 0) or 0)
        if r > 0:
            ranges.append(r)
    if not ranges:
        return 800
    return max(400, min(ranges) * 7 // 10)


def _threat_place_xy(units, threat):
    place = getattr(units[0], "place", None)
    if threat is not None:
        tplace = getattr(threat, "place", None)
        if tplace is None and hasattr(threat, "xmin"):
            tplace = threat
        if tplace is not None and hasattr(threat, "x"):
            return tplace, int(threat.x or 0), int(threat.y or 0)
    if place is None:
        return None, 0, 0
    is_enemy = getattr(units[0], "is_an_enemy", None)
    enemies = []
    for obj in getattr(place, "objects", ()) or ():
        if obj is None or int(getattr(obj, "hp", 0) or 0) <= 0:
            continue
        if not callable(is_enemy):
            continue
        try:
            if is_enemy(obj):
                enemies.append(obj)
        except Exception:
            continue
    if not enemies:
        return None, 0, 0
    ex = sum(int(getattr(e, "x", 0) or 0) for e in enemies) // len(enemies)
    ey = sum(int(getattr(e, "y", 0) or 0) for e in enemies) // len(enemies)
    return place, ex, ey


def _combat_anchor(units, threat):
    tplace, ex, ey = _threat_place_xy(units, threat)
    if tplace is None:
        return None, None
    n = max(len(units), 1)
    cx = sum(int(getattr(u, "x", 0) or 0) for u in units) // n
    cy = sum(int(getattr(u, "y", 0) or 0) for u in units) // n
    fallback = int(getattr(units[0], "o", 90) or 90)
    facing = _facing_from_delta(ex - cx, ey - cy, fallback)
    fx, fy = _forward_axis(facing)
    standoff = _front_standoff(units)
    enemy_proj = (ex * fx + ey * fy) // 1000
    melee = [u for u in units if unit_formation_rank(u) == "melee"]
    sample = melee or list(units)
    front_proj = max(
        (int(getattr(u, "x", 0) or 0) * fx + int(getattr(u, "y", 0) or 0) * fy) // 1000
        for u in sample
    )
    # Advance to standoff; never back the line away from the threat.
    use_front = max(front_proj, enemy_proj - standoff)
    dist = enemy_proj - use_front
    ox = ex - (dist * fx) // 1000
    oy = ey - (dist * fy) // 1000
    ox, oy = _clamp_xy(tplace, ox, oy, 500)
    dummy = type(
        "Anchor",
        (),
        {"place": tplace, "x": ox, "y": oy, "id": "formation-combat", "player": None},
    )()
    return dummy, facing


def combat_peers(unit):
    if unit is None or not unit_can_form(unit):
        return []
    if getattr(unit, "ai_mode", None) == "chase":
        return []
    place = getattr(unit, "place", None)
    group = getattr(unit, "group", None)
    if group:
        peers = [
            u
            for u in group
            if u is not None
            and unit_can_form(u)
            and getattr(u, "place", None) is place
            and int(getattr(u, "hp", 0) or 0) > 0
        ]
        if len(peers) >= 2:
            return peers
    token = getattr(unit, "_formation_combat_token", None)
    if token is not None and place is not None:
        peers = [
            obj
            for obj in getattr(place, "objects", ()) or ()
            if getattr(obj, "_formation_combat_token", None) is token
            and unit_can_form(obj)
            and int(getattr(obj, "hp", 0) or 0) > 0
        ]
        if len(peers) >= 2:
            return peers
    return []


def unit_agro_on_sight(unit) -> bool:
    """Rules ``agro_on_sight``: 1 (default) = may fire without being hit.

    ``0`` matches AoE2 DE huntables (boar): only the struck animal fights.
    """
    if unit is None:
        return True
    return _flag_on(getattr(unit, "agro_on_sight", 1))


def formation_stand_ground(unit) -> bool:
    """AoE2 stand ground: fire in range, never walk.

    Units with ``agro_on_sight 0`` keep classic guard (hit then counterattack).
    """
    if unit is None or getattr(unit, "ai_mode", None) != "guard":
        return False
    if not formations_enabled():
        return False
    if not unit_agro_on_sight(unit):
        return False
    return True


def formation_hold_xy(unit):
    """Slot to hold while fighting; None means walk to the target as before."""
    if unit is None or getattr(unit, "ai_mode", None) == "chase":
        return None
    if getattr(unit, "_formation_focus_fire", 0):
        return None
    slot = getattr(unit, "_formation_slot", None)
    if not slot:
        return None
    place, x, y = slot
    if place is not None and getattr(unit, "place", None) is not place:
        return None
    return int(x), int(y)


def formation_slot_arrive_mm(unit) -> int:
    """Distance in mm at which a unit counts as standing on its slot."""
    try:
        radius = int(getattr(unit, "radius", 0) or 0)
    except (TypeError, ValueError):
        radius = 0
    return max(FORMATION_SLOT_ARRIVE_MM, radius + 50)


def formation_ranks_formed(unit) -> bool:
    """True when the unit is on its square and within arrive range of its slot.

    Combat flats/vs and formation-name counters apply only then. Walking to a
    new layout still uses ``formation_hold_xy`` (keep_pace, go-to-slot).
    """
    slot = formation_hold_xy(unit)
    if slot is None:
        return False
    try:
        x = int(getattr(unit, "x", 0) or 0)
        y = int(getattr(unit, "y", 0) or 0)
    except (TypeError, ValueError):
        return False
    arrive = formation_slot_arrive_mm(unit)
    return square_of_distance(x, y, slot[0], slot[1]) <= arrive * arrive


def _point_blocks_segment(x1, y1, x2, y2, px, py, radius):
    dx = int(x2) - int(x1)
    dy = int(y2) - int(y1)
    length2 = dx * dx + dy * dy
    if length2 <= 0:
        return False
    t_num = (int(px) - int(x1)) * dx + (int(py) - int(y1)) * dy
    if t_num <= 0 or t_num >= length2:
        return False
    qx = int(x1) + t_num * dx // length2
    qy = int(y1) + t_num * dy // length2
    r = max(1, int(radius))
    return square_of_distance(int(px), int(py), qx, qy) <= r * r


def formation_blocker(walker, target):
    """Front-rank enemy standing between walker and target (AoE2 collision wall)."""
    if walker is None or target is None:
        return None
    place = getattr(walker, "place", None)
    if place is None or getattr(target, "place", None) is not place:
        return None
    if formation_hold_xy(walker) is not None:
        return None
    is_enemy = getattr(walker, "is_an_enemy", None)
    if not callable(is_enemy):
        return None
    wx = int(getattr(walker, "x", 0) or 0)
    wy = int(getattr(walker, "y", 0) or 0)
    tx = int(getattr(target, "x", 0) or 0)
    ty = int(getattr(target, "y", 0) or 0)
    wr = int(getattr(walker, "radius", 0) or 0)
    best = None
    best_d2 = None
    for obj in getattr(place, "objects", ()) or ():
        if obj is None or obj is walker or obj is target:
            continue
        if int(getattr(obj, "hp", 0) or 0) <= 0:
            continue
        if not getattr(obj, "_formation_slot", None):
            continue
        try:
            if not is_enemy(obj):
                continue
        except Exception:
            continue
        ox = int(getattr(obj, "x", 0) or 0)
        oy = int(getattr(obj, "y", 0) or 0)
        radius = wr + int(getattr(obj, "radius", 0) or 0) + 400
        if not _point_blocks_segment(wx, wy, tx, ty, ox, oy, radius):
            continue
        d2 = square_of_distance(wx, wy, ox, oy)
        if best is None or d2 < best_d2:
            best = obj
            best_d2 = d2
    return best


def apply_combat_formation(units, threat=None, go_pairs=None):
    """Face the threat and park melee in front, ranged/siege behind."""
    alive = [u for u in units if int(getattr(u, "hp", 0) or 0) > 0]
    if go_pairs is None:
        formable = [u for u in alive if unit_can_form(u)]
        layers = _formable_layers(formable)
    else:
        formable = alive
        layers = _formable_layers(formable, require_can_form=False)
    if len(formable) < 2:
        return
    for layer_units in layers.values():
        if len(layer_units) < 2:
            continue
        spec = _spec(unit_formation_name(layer_units[0]))
        if spec is None:
            continue
        dummy, facing = _combat_anchor(layer_units, threat)
        if dummy is None:
            continue
        slots = assign_formation_slots(layer_units, dummy, spec, facing=facing)
        group = getattr(layer_units[0], "group", None)
        token = id(group) if group is not None else id(layer_units[0])
        _bind_formation_slots(slots, token=token, spec=spec)
        _apply_speed_cap(layer_units, spec)
        pairs = go_pairs
        if pairs is None:
            pairs = _active_go_orders(layer_units)
        else:
            wanted = {id(u) for u in layer_units}
            pairs = [(u, o) for u, o in pairs if id(u) in wanted]
        if len(pairs) >= 2:
            _retarget_go_pairs(pairs, slots)


def hold_combat_formation(unit, threat=None):
    """On engage: assign/refresh combat slots for the unit's formed peers."""
    if not formations_enabled() or unit is None:
        return
    if getattr(unit, "ai_mode", None) == "chase":
        return
    if getattr(unit, "_formation_focus_fire", 0):
        return
    if formation_stand_ground(unit):
        return
    orders = getattr(unit, "orders", None) or ()
    if orders and getattr(orders[0], "keyword", None) == "attack":
        return
    peers = combat_peers(unit)
    if len(peers) < 2:
        return
    world = getattr(unit, "world", None)
    now = getattr(world, "time", 0) if world is not None else 0
    last = getattr(unit, "_formation_combat_time", None)
    if (
        last is not None
        and getattr(unit, "_formation_slot", None)
        and now - last < _COMBAT_REFRESH_MS
    ):
        return
    apply_combat_formation(peers, threat)


def after_group_order(units, keyword):
    if keyword in ("go", "default"):
        apply_move_formation(units)
    elif keyword == "attack":
        break_formation_hold(units)
    elif keyword in ("set_formation", "cycle_formation"):
        apply_idle_rearrange(units)


def play_formation_change_sfx(player):
    if player is None:
        return
    world = getattr(player, "world", None)
    now = getattr(world, "time", None)
    group = getattr(player, "group", None)
    token = (id(group) if group is not None else 0, now)
    if getattr(player, "_formation_sfx_token", None) == token:
        return
    player._formation_sfx_token = token
    play = getattr(player, "play_parameter_sfx", None)
    if callable(play):
        play("formation_change")
