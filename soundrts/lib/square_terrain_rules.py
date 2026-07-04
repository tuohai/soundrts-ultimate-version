"""Square terrain from map placement and object contributions only."""

HIGH_GROUND_VOICE = "_high_ground"
DEFAULT_TERRAIN_SPEED = (100, 100)


def _is_int_token(token):
    try:
        int(token)
        return True
    except (TypeError, ValueError):
        return False


def is_terrain_def(name):
    from ..definitions import rules

    if not name:
        return False
    return rules.get(name, "class") == ["terrain"]


def terrain_property(name, prop, default=None):
    from ..definitions import rules

    if not is_terrain_def(name):
        return default
    val = rules.get(name, prop, default)
    if val is None:
        return default
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
        return {
            "static_voices": [],
            "dynamic_voice": None,
            "feature_voice": feature,
            "high_ground_voice": _high_ground_voice(square, x, y),
            "type_name": bridge_voice or name or "",
            "building_land_voice": None,
        }
    winner = winning_terrain_entry(square.objects)
    feature = winner["name"] if winner else None
    bridge_voice = _bridge_layer_voice(square)
    if bridge_voice:
        feature = bridge_voice
    bl_entry = winning_building_land_terrain_entry(square.objects)
    blt = bl_entry["name"] if bl_entry else None
    type_name = feature or ""
    building_land_voice = blt if blt and blt != feature else None
    return {
        "static_voices": [],
        "dynamic_voice": None,
        "feature_voice": feature,
        "high_ground_voice": _high_ground_voice(square, x, y),
        "type_name": type_name,
        "building_land_voice": building_land_voice,
    }


def resolve_square_type_name(square):
    if getattr(square, "fixed_terrain", False):
        return square.type_name or ""
    return resolve_square_layers(square)["type_name"]


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
    from ..definitions import rules

    if not type_name:
        return []
    entries = rules.get(type_name, "square_terrain", [])
    if not entries:
        return []
    if isinstance(entries, dict):
        return [entries]
    return list(entries)


def type_affects_square_terrain(type_name):
    return bool(square_terrain_entries_for_type(type_name))


def object_affects_square_terrain(obj):
    return type_affects_square_terrain(getattr(obj, "type_name", None))


def _type_counts(objects):
    counts = {}
    for o in objects:
        tn = getattr(o, "type_name", None)
        if tn:
            counts[tn] = counts.get(tn, 0) + 1
    return counts


def qualifying_terrain_entries(objects):
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
    qualified = qualifying_terrain_entries(objects)
    if not qualified:
        return None
    return max(qualified, key=lambda e: e.get("priority", 50))


def winning_building_land_terrain_entry(objects):
    qualified = []
    for o in objects:
        if not getattr(o, "is_a_building_land", False) or getattr(
            o, "is_an_exit", False
        ):
            continue
        tn = getattr(o, "type_name", None)
        if not tn:
            continue
        for entry in square_terrain_entries_for_type(tn):
            qualified.append(entry)
    if not qualified:
        return None
    return max(qualified, key=lambda e: e.get("priority", 50))


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
