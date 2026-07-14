# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython hot path for square terrain resolution.

Call sites keep Python wrappers in ``square_terrain_rules.py``; this module
only accelerates object scans / priority picks. ``entries_for_type`` is the
Python ``square_terrain_entries_for_type`` callable (rules cache stays there).
"""

cimport cython


cpdef dict type_counts(objects):
    """Count ``type_name`` occurrences in *objects*."""
    cdef dict counts = {}
    cdef object o, tn
    for o in objects:
        tn = getattr(o, "type_name", None)
        if tn:
            counts[tn] = counts.get(tn, 0) + 1
    return counts


cpdef list qualifying_terrain_entries(objects, entries_for_type):
    """Mirror ``square_terrain_rules.qualifying_terrain_entries``."""
    cdef dict counts = type_counts(objects)
    cdef list qualified = []
    cdef object seen_types = set()
    cdef object o, tn, entry
    for o in objects:
        tn = getattr(o, "type_name", None)
        if not tn or tn in seen_types:
            continue
        seen_types.add(tn)
        for entry in entries_for_type(tn):
            if counts.get(tn, 0) >= entry.get("min_count", 1):
                qualified.append(entry)
    return qualified


cpdef object winning_terrain_entry(objects, entries_for_type):
    """Highest-priority qualifying ``square_terrain`` entry, or None."""
    cdef list qualified = qualifying_terrain_entries(objects, entries_for_type)
    cdef object best = None
    cdef object entry
    cdef object best_pri = None
    cdef object pri
    if not qualified:
        return None
    for entry in qualified:
        pri = entry.get("priority", 50)
        if best is None or pri > best_pri:
            best = entry
            best_pri = pri
    return best


cpdef object winning_building_land_terrain_entry(objects, entries_for_type):
    """Highest-priority building_land terrain entry among *objects*, or None."""
    cdef object best = None
    cdef object best_priority = None
    cdef object o, tn, entry, pri
    for o in objects:
        if not getattr(o, "is_a_building_land", False) or getattr(
            o, "is_an_exit", False
        ):
            continue
        tn = getattr(o, "type_name", None)
        if not tn:
            continue
        for entry in entries_for_type(tn):
            pri = entry.get("priority", 50)
            if best is None or pri > best_priority:
                best = entry
                best_priority = pri
    return best


cpdef object resolve_square_type_name(square, entries_for_type, bridge_layer_voice):
    """Fast type_name only — skips overlay / building_land voice work.

    Semantics match ``resolve_square_layers(... )['type_name']``:
    feature from winning square_terrain, overridden by bridge voice.
    """
    cdef object objects, winner, feature, bridge_voice
    if getattr(square, "fixed_terrain", False):
        return square.type_name or ""
    objects = square.objects
    winner = winning_terrain_entry(objects, entries_for_type)
    feature = winner["name"] if winner else None
    bridge_voice = bridge_layer_voice(square)
    if bridge_voice:
        feature = bridge_voice
    return feature or ""
