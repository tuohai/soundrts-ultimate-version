"""开放式容器（attack_inside_chance > 0）的可见性辅助。"""


def container_attack_inside_chance(container):
    if container is None:
        return 0
    return max(0, min(100, getattr(container, "attack_inside_chance", 0)))


def is_open_container(container):
    return container_attack_inside_chance(container) > 0


def container_visible_from_place(container, place):
    """容器（及其内部单位）是否从 ``place`` 这一格可见。"""
    if container is None or place is None:
        return False
    outside = getattr(container, "place", None)
    if outside is place:
        return True
    blocked_exit = getattr(container, "blocked_exit", None)
    other_place = None
    if blocked_exit is not None:
        other_place = getattr(getattr(blocked_exit, "other_side", None), "place", None)
        if other_place is place:
            return True
    if is_open_container(container):
        neighbors = getattr(outside, "neighbors", None)
        if neighbors and place in neighbors:
            return True
        if other_place is not None:
            other_neighbors = getattr(other_place, "neighbors", None)
            if other_neighbors and place in other_neighbors:
                return True
    return False


def inside_unit_visible_from_place(unit, place):
    if not getattr(unit, "is_inside", False):
        return unit.place is place
    container = getattr(unit.place, "container", None)
    return container_visible_from_place(container, place)


def exit_blocker_visible_from_observed_squares(unit, observed_squares):
    """出口阻挡物是否处于当前观察区的任一格的可见范围内。"""
    if not getattr(unit, "blocked_exit", None):
        return False
    unit_place = getattr(unit, "place", None)
    if unit_place is None:
        return False
    other_place = getattr(
        getattr(getattr(unit, "blocked_exit", None), "other_side", None),
        "place",
        None,
    )
    for sq in observed_squares or ():
        if sq is unit_place or sq is other_place:
            return True
        neighbors = getattr(sq, "neighbors", None)
        if neighbors and unit_place in neighbors:
            return True
        if other_place is not None:
            other_neighbors = getattr(other_place, "neighbors", None)
            if other_neighbors and sq in other_neighbors:
                return True
        if container_visible_from_place(unit, sq):
            return True
    return False
