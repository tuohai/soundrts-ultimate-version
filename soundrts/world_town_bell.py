"""Rule-driven Town Bell: garrison nearby workers, then send them back to work.

Range is Euclidean meters (PRECISION mm internally), not BFS squares.
``town_bell_range 0`` means unlimited (whole map).
"""

from .lib.nofloat import square_of_distance
from .worldunit import Worker


def snapshot_orders(unit):
    snaps = []
    for order in getattr(unit, "orders", None) or ():
        keyword = getattr(order, "keyword", None)
        if not keyword:
            continue
        args = list(getattr(order, "args", ()) or ())
        snaps.append([keyword] + [str(a) for a in args])
    return snaps


def restore_orders(unit, snaps):
    if not snaps or not hasattr(unit, "take_order"):
        return
    first = True
    for cmd in snaps:
        unit.take_order(list(cmd), forget_previous=first)
        first = False


def is_town_bell_worker(unit, type_names=None):
    """Villager-like target (may already be inside). Military stays garrisoned."""
    if getattr(unit, "hp", 1) <= 0:
        return False
    names = tuple(type_names or ())
    if names:
        type_name = getattr(unit, "type_name", None)
        expanded = getattr(unit, "expanded_is_a", None) or ()
        return type_name in names or any(name in expanded for name in names)
    if not isinstance(unit, Worker):
        return False
    return getattr(unit, "airground_type", "ground") != "water"


def is_town_bell_target(unit, type_names=None):
    """Outside workers the first ring should send into a building."""
    if getattr(unit, "is_inside", False):
        return False
    return is_town_bell_worker(unit, type_names)


def _bell_type_names(player):
    names = []
    bells = town_bell_buildings(player)
    if not bells:
        return ()
    for bell in bells:
        listed = tuple(getattr(bell, "town_bell_units", None) or ())
        if not listed:
            return ()
        names.extend(listed)
    return tuple(names)


def worker_in_bell_range(worker, bell):
    """True if *worker* is within *bell*'s Euclidean ``town_bell_range`` (mm).

    ``town_bell_range`` 0 (or missing) = unlimited.
    """
    rng = int(getattr(bell, "town_bell_range", 0) or 0)
    if rng <= 0:
        return True
    wx = getattr(worker, "x", 0) or 0
    wy = getattr(worker, "y", 0) or 0
    bx = getattr(bell, "x", 0) or 0
    by = getattr(bell, "y", 0) or 0
    return square_of_distance(wx, wy, bx, by) <= rng * rng


def town_bell_buildings(player):
    result = []
    for unit in getattr(player, "units", None) or ():
        if int(getattr(unit, "town_bell", 0) or 0) and getattr(unit, "hp", 1) > 0:
            result.append(unit)
    return result


def is_garrisonable_shelter(building, worker):
    if building is worker:
        return False
    if getattr(building, "hp", 1) <= 0:
        return False
    if int(getattr(building, "transport_capacity", 0) or 0) <= 0:
        return False
    have_space = getattr(building, "have_enough_space", None)
    if not callable(have_space):
        return False
    try:
        return bool(have_space(worker))
    except Exception:
        return False


def nearest_shelter(player, worker):
    wx = getattr(worker, "x", 0) or 0
    wy = getattr(worker, "y", 0) or 0
    best = None
    best_d2 = None
    for building in getattr(player, "units", None) or ():
        if not is_garrisonable_shelter(building, worker):
            continue
        d2 = square_of_distance(
            wx, wy, getattr(building, "x", 0) or 0, getattr(building, "y", 0) or 0
        )
        if best_d2 is None or d2 < best_d2:
            best = building
            best_d2 = d2
    return best


def workers_to_garrison(player):
    bells = town_bell_buildings(player)
    if not bells:
        return []
    seen_ids = set()
    result = []
    for bell in bells:
        type_names = getattr(bell, "town_bell_units", None) or ()
        for unit in getattr(player, "units", None) or ():
            uid = getattr(unit, "id", id(unit))
            if uid in seen_ids:
                continue
            if not is_town_bell_target(unit, type_names):
                continue
            if not worker_in_bell_range(unit, bell):
                continue
            seen_ids.add(uid)
            result.append(unit)
    return result


def workers_already_inside(player):
    """Matching workers already garrisoned (any building). AoE2 Return to Work."""
    type_names = _bell_type_names(player)
    result = []
    for unit in getattr(player, "units", None) or ():
        if not getattr(unit, "is_inside", False):
            continue
        if is_town_bell_worker(unit, type_names):
            result.append(unit)
    return result


def _tag_worker_for_bell(worker, snapshot=True):
    if snapshot and not getattr(worker, "_town_bell_resume", None):
        worker._town_bell_resume = snapshot_orders(worker)
    worker._town_bell_garrisoned = True


def ring_town_bell(player):
    """First ring: nearby workers enter; already-garrisoned villagers are tagged."""
    player._town_bell_active = True
    for worker in workers_already_inside(player):
        _tag_worker_for_bell(worker, snapshot=False)
    for worker in workers_to_garrison(player):
        shelter = nearest_shelter(player, worker)
        if shelter is None:
            continue
        _tag_worker_for_bell(worker, snapshot=True)
        worker.take_order(["enter", shelter.id])


def _container_of(unit):
    if not getattr(unit, "is_inside", False):
        return None
    place = getattr(unit, "place", None)
    return getattr(place, "container", None) if place is not None else None


def stop_town_bell(player):
    """Second ring: ungarrison matching villagers (tagged or already inside)."""
    player._town_bell_active = False
    seen = set()
    release = []
    for unit in workers_already_inside(player):
        uid = getattr(unit, "id", id(unit))
        if uid in seen:
            continue
        seen.add(uid)
        release.append(unit)
    for unit in list(getattr(player, "units", None) or ()):
        if not getattr(unit, "_town_bell_garrisoned", False):
            continue
        uid = getattr(unit, "id", id(unit))
        if uid in seen:
            continue
        seen.add(uid)
        release.append(unit)
    for unit in release:
        resume = getattr(unit, "_town_bell_resume", None) or []
        unit._town_bell_garrisoned = False
        unit._town_bell_resume = None
        container = _container_of(unit)
        if container is not None and hasattr(container, "unload_matching"):
            container.unload_matching(lambda obj, target=unit: obj is target)
        elif not getattr(unit, "is_inside", False) and hasattr(unit, "cancel_all_orders"):
            unit.cancel_all_orders()
        if resume and not getattr(unit, "is_inside", False):
            restore_orders(unit, resume)
