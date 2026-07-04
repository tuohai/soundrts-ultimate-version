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
