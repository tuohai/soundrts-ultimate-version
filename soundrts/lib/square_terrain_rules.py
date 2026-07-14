"""Square terrain from map placement and object contributions only."""

import os

HIGH_GROUND_VOICE = "_high_ground"
DEFAULT_TERRAIN_SPEED = (100, 100)
DEFAULT_TERRAIN_COVER = (0, 0)

_fast = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import square_terrain_fast as _fast  # type: ignore[no-redef]
    except ImportError:
        _fast = None

# Hot-path caches. Cleared on rules.load via clear_terrain_lookup_caches().
_IS_TERRAIN_CACHE = {}
_TERRAIN_PROP_CACHE = {}
_SQUARE_TERRAIN_ENTRIES_CACHE = {}
_EMPTY_SQUARE_TERRAIN_ENTRIES = ()
_MISSING_PROP = object()
# None = not built yet; frozenset of prop names that at least one terrain defines.
_TERRAIN_PROPS_PRESENT = None

# Combat/path props that damage/CD/hit code may query millions of times per game.
_INDEXED_TERRAIN_UNIT_PROPS = (
    "mdg_vs",
    "rdg_vs",
    "mdg_cd_vs",
    "rdg_cd_vs",
    "speed_vs",
    "cover_vs",
    "dodge_vs",
)


def clear_terrain_lookup_caches():
    """Drop terrain lookup caches after rules reload."""
    global _IS_TERRAIN_CACHE, _TERRAIN_PROP_CACHE, _SQUARE_TERRAIN_ENTRIES_CACHE
    global _TERRAIN_PROPS_PRESENT
    _IS_TERRAIN_CACHE = {}
    _TERRAIN_PROP_CACHE = {}
    _SQUARE_TERRAIN_ENTRIES_CACHE = {}
    _TERRAIN_PROPS_PRESENT = None


def _is_int_token(token):
    try:
        int(token)
        return True
    except (TypeError, ValueError):
        return False


def is_terrain_def(name):
    if not name:
        return False
    cached = _IS_TERRAIN_CACHE.get(name)
    if cached is not None:
        return cached
    from ..definitions import rules

    # Prefer raw dict to avoid rules.get list-copy on every call.
    raw = getattr(rules, "_dict", {}).get(name)
    if raw is not None and "class" in raw:
        cls = raw.get("class")
        result = cls == ["terrain"] or (
            isinstance(cls, list) and len(cls) == 1 and cls[0] == "terrain"
        )
    else:
        result = rules.get(name, "class") == ["terrain"]
    _IS_TERRAIN_CACHE[name] = result
    return result


def _ensure_terrain_props_index():
    """Build set of terrain unit-props that exist on any terrain (incl. inheritance)."""
    global _TERRAIN_PROPS_PRESENT
    if _TERRAIN_PROPS_PRESENT is not None:
        return _TERRAIN_PROPS_PRESENT
    from ..definitions import rules

    present = set()
    remaining = set(_INDEXED_TERRAIN_UNIT_PROPS)
    for name in list(getattr(rules, "_dict", {})):
        if not remaining:
            break
        if not is_terrain_def(name):
            continue
        for prop in tuple(remaining):
            val = rules.get(name, prop)
            if val:
                present.add(prop)
                remaining.discard(prop)
    _TERRAIN_PROPS_PRESENT = frozenset(present)
    return _TERRAIN_PROPS_PRESENT


def any_terrain_defines(prop):
    """True if at least one terrain defines a non-empty *prop* (cached)."""
    if not prop:
        return False
    return prop in _ensure_terrain_props_index()


def terrain_is_a_type(terrain_name, type_name):
    """Whether *terrain_name* is *type_name* or inherits it via ``is_a``."""
    if not terrain_name or not type_name:
        return False
    if terrain_name == type_name:
        return True
    if not is_terrain_def(terrain_name):
        return False
    from ..definitions import rules

    is_a = rules.get(terrain_name, "is_a", []) or []
    if type_name in is_a:
        return True
    expanded = rules.get(terrain_name, "expanded_is_a", []) or []
    return type_name in expanded


def terrain_list_value(terrain_type, terrain_list, default=None):
    """Read paired value from ``[name, value, name, value, ...]``.

    Exact *terrain_type* wins; else first list name inherited by *terrain_type*
    via ``terrain_is_a_type``.
    """
    if not terrain_type or not terrain_list:
        return default
    tokens = list(terrain_list)
    inherited = None
    i = 0
    while i + 1 < len(tokens):
        name = tokens[i]
        value = tokens[i + 1]
        if name == terrain_type:
            return value
        if inherited is None and terrain_is_a_type(terrain_type, name):
            inherited = value
        i += 2
    return inherited if inherited is not None else default


def terrain_property(name, prop, default=None):
    cache_key = (name, prop)
    if cache_key in _TERRAIN_PROP_CACHE:
        val = _TERRAIN_PROP_CACHE[cache_key]
        return default if val is _MISSING_PROP else val
    if not is_terrain_def(name):
        _TERRAIN_PROP_CACHE[cache_key] = _MISSING_PROP
        return default
    from ..definitions import rules

    val = rules.get(name, prop, None)
    if val is None:
        _TERRAIN_PROP_CACHE[cache_key] = _MISSING_PROP
        return default
    _TERRAIN_PROP_CACHE[cache_key] = val
    return val


def terrain_is_dynamic(name):
    if not is_terrain_def(name):
        return False
    return bool(terrain_property(name, "is_dynamic", 0))


def parse_terrain_speed_pair(raw):
    """Parse map/rules ``speed <ground> <air>`` into integer percent pair."""
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        tokens = list(raw)
    else:
        tokens = [raw]
    if len(tokens) < 2:
        return None
    try:
        return (
            int(float(tokens[0]) * 100),
            int(float(tokens[1]) * 100),
        )
    except (TypeError, ValueError):
        return None


def terrain_default_speed(terrain_name):
    """Default ``terrain_speed`` from ``rules.txt`` ``class terrain`` (or None)."""
    if not is_terrain_def(terrain_name):
        return None
    raw = terrain_property(terrain_name, "speed", ())
    if not raw:
        return None
    return parse_terrain_speed_pair(raw)


def resolve_terrain_speed(terrain_name, map_speed=None):
    """Runtime speed: explicit map value wins, else rules default, else 100/100."""
    if map_speed is not None:
        return map_speed
    if terrain_name:
        default = terrain_default_speed(terrain_name)
        if default is not None:
            return default
    return DEFAULT_TERRAIN_SPEED


def palette_speed_default(style_name, palette_speed):
    """Editor palette: keep explicit palette speed, else inherit from rules."""
    if palette_speed != DEFAULT_TERRAIN_SPEED:
        return palette_speed
    return terrain_default_speed(style_name) or palette_speed


def parse_terrain_cover_pair(raw):
    """Parse map/rules ``cover <ground> <air>`` into integer percent pair."""
    return parse_terrain_speed_pair(raw)


def terrain_default_cover(terrain_name):
    """Default ``terrain_cover`` from ``rules.txt`` ``class terrain`` (or None)."""
    if not is_terrain_def(terrain_name):
        return None
    raw = terrain_property(terrain_name, "cover", ())
    if not raw:
        return None
    return parse_terrain_cover_pair(raw)


def resolve_terrain_cover(terrain_name, map_cover=None):
    """Runtime cover: explicit map value wins, else rules default, else 0/0."""
    if map_cover is not None:
        return map_cover
    if terrain_name:
        default = terrain_default_cover(terrain_name)
        if default is not None:
            return default
    return DEFAULT_TERRAIN_COVER


def palette_cover_default(style_name, palette_cover):
    """Editor palette: keep explicit palette cover, else inherit from rules."""
    if palette_cover != DEFAULT_TERRAIN_COVER:
        return palette_cover
    return terrain_default_cover(style_name) or palette_cover


def unit_list_value(unit, unit_list, default=None):
    """Read paired value from ``[unit_type, value, unit_type, value, ...]``.

    Exact ``type_name`` wins; else first match via ``expanded_is_a``.
    """
    if unit is None or not unit_list:
        return default
    type_name = getattr(unit, "type_name", None)
    if not type_name:
        return default
    tokens = list(unit_list)
    inherited = None
    expanded = getattr(unit, "expanded_is_a", ()) or ()
    i = 0
    while i + 1 < len(tokens):
        name = tokens[i]
        value = tokens[i + 1]
        if name == type_name:
            return value
        if inherited is None and name in expanded:
            inherited = value
        i += 2
    return inherited if inherited is not None else default


def terrain_unit_list_value(terrain_name, unit, prop, default=None):
    """Read a terrain ``*_vs`` list entry for *unit* on *terrain_name*."""
    if not terrain_name:
        return default
    # Global short-circuit: default rules have almost no combat *_vs props.
    if prop in _INDEXED_TERRAIN_UNIT_PROPS and not any_terrain_defines(prop):
        return default
    if not is_terrain_def(terrain_name):
        return default
    raw = terrain_property(terrain_name, prop, ())
    if not raw:
        return default
    return unit_list_value(unit, raw, default)


def _percent_from_multiplier(value):
    try:
        return int(float(value) * 100)
    except (TypeError, ValueError):
        return None


def terrain_unit_speed_percent(terrain_name, unit, square_speed=None):
    """Return ``(ground_pct, air_pct)`` for *unit* on *terrain_name*.

    Priority: ``speed_vs`` match > *square_speed* > rules ``speed`` default >
    ``DEFAULT_TERRAIN_SPEED``.
    """
    vs_val = terrain_unit_list_value(terrain_name, unit, "speed_vs")
    if vs_val is not None:
        pct = _percent_from_multiplier(vs_val)
        if pct is not None:
            return (pct, pct)
    if square_speed is not None:
        return square_speed
    return resolve_terrain_speed(terrain_name)


def terrain_unit_cover_percent(terrain_name, unit, square_cover=None):
    """Return cover percent (0-100) for *unit* on *terrain_name*.

    Priority: ``cover_vs`` match > ground/air component of *square_cover* /
    rules ``cover`` default > 0.
    """
    vs_val = terrain_unit_list_value(terrain_name, unit, "cover_vs")
    if vs_val is not None:
        pct = _percent_from_multiplier(vs_val)
        if pct is not None:
            return pct
    if square_cover is None:
        square_cover = resolve_terrain_cover(terrain_name)
    terrain_type = 0 if getattr(unit, "airground_type", None) != "air" else 1
    if terrain_type < len(square_cover):
        return square_cover[terrain_type]
    return 0


def terrain_unit_percent_points(terrain_name, unit, prop):
    """Parse terrain ``*_vs`` as a fraction of 100% (``.1`` -> 10, ``-.2`` -> -20)."""
    value = terrain_unit_list_value(terrain_name, unit, prop)
    return parse_percent_points(value)


def parse_percent_points(value):
    """Parse a decimal fraction as percent points (``.1`` -> 10, ``-.2`` -> -20)."""
    if value is None:
        return None
    try:
        return int(float(value) * 100)
    except (TypeError, ValueError):
        return None


def stat_percent_delta(value, base_value):
    """Apply percent points from *value* to *base_value*."""
    pct = parse_percent_points(value)
    if pct is None or not base_value:
        return 0
    return base_value * pct // 100


def terrain_list_stat_percent_delta(terrain_type, terrain_list, base_value):
    """Read unit ``*_on_terrain`` percent modifier for *terrain_type*."""
    if not terrain_type or not terrain_list or not base_value:
        return 0
    value = terrain_list_value(terrain_type, terrain_list)
    if value is None:
        return 0
    return stat_percent_delta(value, base_value)


def terrain_unit_dodge_bonus(terrain_name, unit):
    """Dodge points (0~100 scale) from ``dodge_vs``."""
    if not any_terrain_defines("dodge_vs"):
        return 0
    pct = terrain_unit_percent_points(terrain_name, unit, "dodge_vs")
    return pct if pct is not None else 0


def terrain_unit_stat_percent_delta(terrain_name, unit, base_value, prop):
    """Apply terrain ``*_vs`` percent of *base_value* (``.5`` -> +50% of base)."""
    if prop in _INDEXED_TERRAIN_UNIT_PROPS and not any_terrain_defines(prop):
        return 0
    value = terrain_unit_list_value(terrain_name, unit, prop)
    if value is None:
        return 0
    return stat_percent_delta(value, base_value)


def _filter_spawn_inheritance(spawns):
    """Drop types that only match via inherited ``square_terrain`` (``is_a``)."""
    if len(spawns) <= 1:
        return spawns
    from ..definitions import rules

    candidates = list(spawns.keys())
    filtered = {}
    for obj_name in candidates:
        parents = set(rules.get(obj_name, "is_a", []) or [])
        parents.update(rules.get(obj_name, "expanded_is_a", []) or [])
        if any(other in parents for other in candidates if other != obj_name):
            continue
        filtered[obj_name] = spawns[obj_name]
    return filtered


def terrain_map_object_spawns(terrain_name):
    """Objects to spawn for map ``terrain <name>`` when terrain is dynamic.

    Reads ``square_terrain`` on each rules def: if an entry's terrain name
    matches *terrain_name*, use that entry's ``min_count``.
    """
    if not is_terrain_def(terrain_name) or not terrain_is_dynamic(terrain_name):
        return {}
    from ..definitions import rules

    spawns = {}
    for obj_name in rules.classnames():
        if rules.get(obj_name, "class") == ["terrain"]:
            continue
        for entry in square_terrain_entries_for_type(obj_name):
            if entry.get("name") != terrain_name:
                continue
            count = entry.get("min_count", 1)
            spawns[obj_name] = max(spawns.get(obj_name, 0), count)
    return _filter_spawn_inheritance(spawns)


def terrain_object_spawn_kind(obj_type):
    """How to place a map-spawned object: deposit, building_land, or unit."""
    from ..definitions import rules

    if rules.get(obj_type, "class") == ["building_land"]:
        return "building_land"
    cls = rules.get(obj_type, "class", [None])
    if cls == ["deposit"]:
        return "deposit"
    if cls and cls[0] in ("building", "worker", "soldier"):
        return "unit"
    return None


def terrain_deposit_spawn_qty(obj_type):
    """Default harvestable amount for auto-spawned deposits."""
    from ..definitions import rules

    start = rules.get(obj_type, "resource_volume_start", None)
    if start not in (None, []):
        if isinstance(start, list):
            return str(start[0])
        return str(start)
    return "100"


def terrain_is_high_ground(name):
    if not is_terrain_def(name):
        return False
    return bool(terrain_property(name, "is_high_ground", 0))


def terrain_is_water(name):
    if not is_terrain_def(name):
        return False
    return bool(terrain_property(name, "is_water", 0))


def terrain_effective_is_ground(name):
    """Return whether ground units may stand here; None if not a terrain def."""
    if not is_terrain_def(name):
        return None
    val = terrain_property(name, "is_ground", None)
    if val is not None:
        return bool(val)
    if terrain_is_water(name):
        return False
    return True


def terrain_map_square_flags(terrain_name):
    """All square/sub-cell flags to apply for ``terrain <name>`` on a map."""
    if not is_terrain_def(terrain_name):
        return None
    is_ground = terrain_effective_is_ground(terrain_name)
    return {
        "high_ground": bool(terrain_property(terrain_name, "is_high_ground", 0)),
        "is_water": bool(terrain_property(terrain_name, "is_water", 0)),
        "is_ground": is_ground if is_ground is not None else True,
        "is_air": bool(terrain_property(terrain_name, "is_air", 1)),
    }


def apply_terrain_map_flags(square, terrain_name, cx=None, cy=None):
    """Apply every ``class terrain`` square flag when map sets ``terrain <name>``."""
    flags = terrain_map_square_flags(terrain_name)
    if not flags:
        return
    subcell = (
        cx is not None
        and cy is not None
        and hasattr(square, "subcells")
    )
    if subcell:
        sc = square.subcells
        sc.set_high_ground(cx, cy, flags["high_ground"])
        sc.set_is_water(cx, cy, flags["is_water"])
        sc.set_is_ground(cx, cy, flags["is_ground"])
        sc.set_is_air(cx, cy, flags["is_air"])
    else:
        square.high_ground = flags["high_ground"]
        square.is_water = flags["is_water"]
        square.is_ground = flags["is_ground"]
        square.is_air = flags["is_air"]


def apply_terrain_high_ground_flag(square, terrain_name, x=None, y=None):
    apply_terrain_map_flags(square, terrain_name, x, y)


def _square_high_ground(square, x=None, y=None):
    if x is not None and y is not None and hasattr(square, "high_ground_at"):
        return square.high_ground_at(x, y)
    return square.high_ground


def _high_ground_voice(square, x=None, y=None):
    if _square_high_ground(square, x, y):
        return HIGH_GROUND_VOICE
    return None


def _bridge_layer_voice(square):
    """Completed bridge deck voice on a water square (not scaffold construction)."""
    return getattr(square, "_bridge_terrain_voice", None)


def _bridge_voice_from_objects(objects):
    from ..world_build_rules import (
        _bridge_terrain_providers,
        bridge_terrain_type,
        is_scaffold_water_build_target,
    )

    providers = list(_bridge_terrain_providers(objects or ()))
    if providers:
        return providers[0]
    for obj in objects or ():
        if is_scaffold_water_build_target(obj):
            name = bridge_terrain_type(getattr(obj, "type", obj))
            if name:
                return name
    return None


def _building_site_land_voices(objects):
    """Voices from building_land remembered on active BuildingSite construction."""
    voices = []
    for obj in objects or ():
        if getattr(obj, "type_name", None) != "buildingsite":
            continue
        land = getattr(obj, "building_land", None)
        if land is None:
            continue
        tn = getattr(land, "type_name", None)
        if not tn:
            continue
        for entry in square_terrain_entries_for_type(tn):
            name = entry.get("name")
            if name and name not in voices:
                voices.append(name)
    return voices


def overlay_voices_for_square(square, x=None, y=None, winner=None, bl_entry=None):
    """Ordered overlay terrain voices for footstep/falling (excludes base map terrain).

    Priority: scaffold → bridge → square_terrain feature → building_land →
    construction-site remembered building_land.

    Optional *winner* / *bl_entry* avoid recomputing the same scans when the
    caller already resolved layers (resolve_square_layers hot path).
    """
    objects = getattr(square, "objects", None)
    if objects is None:
        objects = ()
    voices = []

    def _add(voice):
        if voice and voice not in voices:
            voices.append(voice)

    _add(getattr(square, "_scaffold_terrain_voice", None))
    bridge_voice = _bridge_layer_voice(square)
    if bridge_voice:
        _add(bridge_voice)
    else:
        _add(_bridge_voice_from_objects(objects))

    if not getattr(square, "fixed_terrain", False):
        if winner is None:
            winner = winning_terrain_entry(objects)
        if winner:
            _add(winner.get("name"))
        if bl_entry is None:
            bl_entry = winning_building_land_terrain_entry(objects)
        if bl_entry:
            _add(bl_entry.get("name"))

    for name in _building_site_land_voices(objects):
        _add(name)

    return voices


def resolve_square_layers(square, x=None, y=None):
    """Return voice layers and gameplay type_name for a square.

    No engine default terrain: only map ``terrain``, object ``square_terrain``,
    and the separate ``_high_ground`` voice when marked high ground.
    """
    if getattr(square, "fixed_terrain", False):
        if x is not None and y is not None and hasattr(square, "type_name_at"):
            name = square.type_name_at(x, y)
        else:
            name = square.type_name
        bridge_voice = getattr(square, "_bridge_terrain_voice", None)
        feature = bridge_voice or name or None
        overlay_voices = overlay_voices_for_square(square, x, y)
        return {
            "static_voices": [],
            "dynamic_voice": None,
            "feature_voice": feature,
            "high_ground_voice": _high_ground_voice(square, x, y),
            "type_name": bridge_voice or name or "",
            "building_land_voice": None,
            "overlay_voices": overlay_voices,
        }
    objects = square.objects
    winner = winning_terrain_entry(objects)
    feature = winner["name"] if winner else None
    bridge_voice = _bridge_layer_voice(square)
    if bridge_voice:
        feature = bridge_voice
    bl_entry = winning_building_land_terrain_entry(objects)
    blt = bl_entry["name"] if bl_entry else None
    type_name = feature or ""
    building_land_voice = blt if blt and blt != feature else None
    overlay_voices = overlay_voices_for_square(
        square, x, y, winner=winner, bl_entry=bl_entry
    )
    return {
        "static_voices": [],
        "dynamic_voice": None,
        "feature_voice": feature,
        "high_ground_voice": _high_ground_voice(square, x, y),
        "type_name": type_name,
        "building_land_voice": building_land_voice,
        "overlay_voices": overlay_voices,
    }


def resolve_square_type_name(square):
    """Map/gameplay type_name only — does not build overlay voice layers.

    ``update_terrain`` calls this every tick for every square; previously it
    ran full ``resolve_square_layers`` (building_land + overlay scans) just to
    read ``type_name``. Feature voice semantics stay identical.
    """
    if getattr(square, "fixed_terrain", False):
        return square.type_name or ""
    if _fast is not None:
        return _fast.resolve_square_type_name(
            square, square_terrain_entries_for_type, _bridge_layer_voice
        )
    objects = square.objects
    winner = winning_terrain_entry(objects)
    feature = winner["name"] if winner else None
    bridge_voice = _bridge_layer_voice(square)
    if bridge_voice:
        feature = bridge_voice
    return feature or ""


def parse_square_terrain_entries(words):
    """Parse ``square_terrain`` tokens: name [priority] [min_count] ..."""
    entries = []
    i = 0
    while i < len(words):
        name = words[i]
        i += 1
        priority = 50
        min_count = 1
        if i < len(words) and _is_int_token(words[i]):
            priority = int(words[i])
            i += 1
        if i < len(words) and _is_int_token(words[i]):
            min_count = int(words[i])
            i += 1
        entries.append(
            {"name": name, "priority": priority, "min_count": min_count}
        )
    return entries


def square_terrain_entries_for_type(type_name):
    """Return cached ``square_terrain`` entries for *type_name* (tuple, may be empty).

    Avoids per-call ``rules.get`` list copies and function-local imports on the
    millions of add/remove / resolve_layers lookups in a long game.
    """
    if not type_name:
        return _EMPTY_SQUARE_TERRAIN_ENTRIES
    cached = _SQUARE_TERRAIN_ENTRIES_CACHE.get(type_name)
    if cached is not None:
        return cached
    from ..definitions import rules

    # _val resolves is_a inheritance without the list copy from rules.get.
    entries = rules._val(type_name, "square_terrain")
    if not entries:
        result = _EMPTY_SQUARE_TERRAIN_ENTRIES
    elif isinstance(entries, dict):
        result = (entries,)
    else:
        result = tuple(entries)
    _SQUARE_TERRAIN_ENTRIES_CACHE[type_name] = result
    return result


def type_affects_square_terrain(type_name):
    return bool(square_terrain_entries_for_type(type_name))


def object_affects_square_terrain(obj):
    return type_affects_square_terrain(getattr(obj, "type_name", None))


def _type_counts(objects):
    if _fast is not None:
        return _fast.type_counts(objects)
    counts = {}
    for o in objects:
        tn = getattr(o, "type_name", None)
        if tn:
            counts[tn] = counts.get(tn, 0) + 1
    return counts


def qualifying_terrain_entries(objects):
    if _fast is not None:
        return _fast.qualifying_terrain_entries(
            objects, square_terrain_entries_for_type
        )
    counts = _type_counts(objects)
    qualified = []
    seen_types = set()
    for o in objects:
        tn = getattr(o, "type_name", None)
        if not tn or tn in seen_types:
            continue
        seen_types.add(tn)
        for entry in square_terrain_entries_for_type(tn):
            if counts.get(tn, 0) >= entry.get("min_count", 1):
                qualified.append(entry)
    return qualified


def winning_terrain_entry(objects):
    if _fast is not None:
        return _fast.winning_terrain_entry(objects, square_terrain_entries_for_type)
    qualified = qualifying_terrain_entries(objects)
    if not qualified:
        return None
    return max(qualified, key=lambda e: e.get("priority", 50))


def winning_building_land_terrain_entry(objects):
    if _fast is not None:
        return _fast.winning_building_land_terrain_entry(
            objects, square_terrain_entries_for_type
        )
    best = None
    best_priority = None
    for o in objects:
        if not getattr(o, "is_a_building_land", False) or getattr(
            o, "is_an_exit", False
        ):
            continue
        tn = getattr(o, "type_name", None)
        if not tn:
            continue
        for entry in square_terrain_entries_for_type(tn):
            pri = entry.get("priority", 50)
            if best is None or pri > best_priority:
                best = entry
                best_priority = pri
    return best


_PASSABLE_UNITS_SENTINEL = object()


def squares_same_ground_region(a, b):
    """Whether two map squares belong to the same ground flood-fill region.

    Walkable land (``is_ground``) includes fords and bridges (``is_water`` + ``is_ground``).
    Pure water without ground (rivers, lakes) stays separate from land/ford.
    """
    g_a = getattr(a, "is_ground", True)
    g_b = getattr(b, "is_ground", True)
    if g_a and g_b:
        return True
    if not g_a and not g_b:
        return getattr(a, "is_water", False) == getattr(b, "is_water", False)
    return False


def terrain_passable_units(terrain_name):
    """Return the whitelist for *terrain_name*, or None if not configured."""
    if not is_terrain_def(terrain_name):
        return None
    from ..definitions import rules

    val = rules.get(terrain_name, "passable_units", _PASSABLE_UNITS_SENTINEL)
    if val is _PASSABLE_UNITS_SENTINEL:
        return None
    if isinstance(val, list):
        return [str(x) for x in val]
    return [str(val)] if val else []


def terrain_has_passable_units(terrain_name):
    return terrain_passable_units(terrain_name) is not None


def unit_matches_passable_units(unit, allowed_types):
    """Whether *unit* matches any entry in *allowed_types* (direct or via is_a)."""
    if not allowed_types:
        return False
    type_name = getattr(unit, "type_name", None)
    if type_name and type_name in allowed_types:
        return True
    expanded = getattr(unit, "expanded_is_a", ()) or ()
    return any(t in allowed_types for t in expanded)


def terrain_allows_unit(terrain_name, unit):
    """Whitelist pass check; None if *terrain_name* has no passable_units."""
    allowed = terrain_passable_units(terrain_name)
    if allowed is None:
        return None
    return unit_matches_passable_units(unit, allowed)


def terrain_name_at_square(square, x=None, y=None):
    """Resolve gameplay terrain type name at *square* (optionally at *x*, *y*)."""
    if square is None:
        return ""
    if x is None:
        x = getattr(square, "x", 0)
    if y is None:
        y = getattr(square, "y", 0)
    if hasattr(square, "type_name_at"):
        name = square.type_name_at(x, y)
        if name:
            return name
    if getattr(square, "fixed_terrain", False):
        return getattr(square, "type_name", "") or ""
    return resolve_square_type_name(square) or ""


def passable_units_denied_reason(terrain_name, unit):
    """Return ``passable_units_denied,<type_name>`` if whitelist blocks *unit*."""
    if not terrain_name or not terrain_has_passable_units(terrain_name):
        return None
    if terrain_allows_unit(terrain_name, unit):
        return None
    type_name = getattr(unit, "type_name", None) or "unknown"
    return f"passable_units_denied,{type_name}"


def terrain_blocks_path(terrain_name):
    if not terrain_name:
        return False
    if is_terrain_def(terrain_name):
        return bool(terrain_property(terrain_name, "blocks_path", 0))
    from ..definitions import style

    val = style.get(terrain_name, "blocks_path")
    if val == []:
        return False
    if isinstance(val, list) and val:
        try:
            return bool(int(val[0]))
        except (TypeError, ValueError):
            return bool(val[0])
    return bool(val)
