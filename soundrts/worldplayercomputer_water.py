"""Computer-player helpers for water pathfinding and amphibious transport."""

from .lib.nofloat import int_distance


def path_plane(unit):
    ag = getattr(unit, "airground_type", None) or "ground"
    if ag == "air":
        return "air"
    if ag == "water":
        return "water"
    return "ground"


def is_passable_land(place):
    return (
        place is not None
        and place.is_ground
        and not place.is_water
        and not place.high_ground
    )


def is_land_shore(place):
    if not is_passable_land(place):
        return False
    for neighbor in place.strict_neighbors:
        if neighbor.is_water:
            return True
    return False


def water_neighbors_of_land(land_place):
    for neighbor in land_place.strict_neighbors:
        if neighbor.is_water:
            yield neighbor


def gather_shore_lands_near(from_place, max_hops=12):
    if from_place is None:
        return []
    # Shore topology is static for a square during a game; cache per place.
    cache = getattr(from_place, "_shore_lands_cache", None)
    if cache is not None and cache[0] == max_hops:
        return list(cache[1])
    shores = []
    seen = {id(from_place)}
    queue = [(from_place, 0)]
    qi = 0
    while qi < len(queue):
        place, hops = queue[qi]
        qi += 1
        if is_land_shore(place):
            shores.append(place)
        if hops >= max_hops:
            continue
        for neighbor in place.neighbors:
            nid = id(neighbor)
            if nid in seen or not is_passable_land(neighbor):
                continue
            seen.add(nid)
            queue.append((neighbor, hops + 1))
    from_place._shore_lands_cache = (max_hops, shores)
    return list(shores)


def find_amphibious_crossing(start_place, dest_place, player):
    """Return (load_land, load_water, unload_water, unload_land) or None."""
    if start_place is None or dest_place is None:
        return None

    load_lands = gather_shore_lands_near(start_place)
    dest_seed = dest_place if is_passable_land(dest_place) else None
    if dest_seed is None:
        for neighbor in dest_place.strict_neighbors:
            if is_passable_land(neighbor):
                dest_seed = neighbor
                break
    if dest_seed is None:
        return None
    unload_lands = gather_shore_lands_near(dest_seed, max_hops=8)
    if dest_place in unload_lands or is_land_shore(dest_place):
        if dest_place not in unload_lands:
            unload_lands.insert(0, dest_place)

    best = None
    best_cost = None
    for load_land in load_lands:
        load_waters = list(water_neighbors_of_land(load_land))
        if not load_waters:
            continue
        ground_to_load = start_place.shortest_path_distance_to(
            load_land, player, "ground"
        )
        if ground_to_load is None or ground_to_load == float("inf"):
            continue
        for unload_land in unload_lands:
            unload_waters = list(water_neighbors_of_land(unload_land))
            if not unload_waters:
                continue
            ground_from_unload = unload_land.shortest_path_distance_to(
                dest_place, player, "ground"
            )
            if ground_from_unload is None or ground_from_unload == float("inf"):
                continue
            for load_water in load_waters:
                for unload_water in unload_waters:
                    water_dist = load_water.shortest_path_distance_to(
                        unload_water, player, "water"
                    )
                    if water_dist is None or water_dist == float("inf"):
                        continue
                    cost = ground_to_load + water_dist + ground_from_unload
                    if best_cost is None or cost < best_cost:
                        best_cost = cost
                        best = (load_land, load_water, unload_water, unload_land)
    return best


def _water_path_distance(from_sq, to_sq, player):
    if from_sq is None or to_sq is None:
        return float("inf")
    d = from_sq.shortest_path_distance_to(to_sq, player, "water")
    if d is None or d == float("inf"):
        return float("inf")
    return d


def _iter_map_water_squares(anchor):
    world = anchor.world
    names = getattr(world, "water_squares", None)
    if names:
        for name in names:
            sq = world.grid.get(name)
            if sq is not None and getattr(sq, "is_water", False):
                yield sq
        return
    for sq in world.squares:
        if getattr(sq, "is_water", False):
            yield sq


def _nearest_reachable_water_to_land(unit_place, land_place, player):
    """When land has no adjacent water (e.g. M3 corners), pick reachable lake water."""
    if unit_place is None or land_place is None:
        return None
    best = None
    best_key = None
    for sq in _iter_map_water_squares(land_place):
        d_from = _water_path_distance(unit_place, sq, player)
        if d_from == float("inf"):
            continue
        d_to_land = land_place.shortest_path_distance_to(sq, player, "ground")
        if d_to_land is None or d_to_land == float("inf"):
            d_to_land = int_distance(land_place.x, land_place.y, sq.x, sq.y)
        key = (d_to_land, d_from)
        if best_key is None or key < best_key:
            best_key = key
            best = sq
    return best


def movement_target_for_unit(unit, place, player):
    """Water units stop on adjacent water; others use the place itself."""
    if getattr(unit, "airground_type", None) != "water":
        return place
    if getattr(place, "is_water", False):
        return place
    candidates = [
        n for n in place.strict_neighbors if getattr(n, "is_water", False)
    ]
    start = getattr(unit, "place", None)

    def _dist(square):
        if start is None:
            return 0
        return _water_path_distance(start, square, player)

    if candidates:
        if start is None:
            return candidates[0]
        return min(candidates, key=_dist)
    fallback = _nearest_reachable_water_to_land(start, place, player)
    if fallback is not None:
        return fallback
    return place


def water_path_destination(unit, place, player):
    """Square used for water-plane pathfinding toward place (land or water)."""
    if getattr(unit, "airground_type", None) != "water":
        return place
    if place is None or getattr(place, "is_water", False):
        return place
    return movement_target_for_unit(unit, place, player)


def spawn_place_for_trained_water_unit(building, unit_type):
    """Return (place, x, y) to spawn a unit from a dock/shipyard, or Nones."""
    building_type = getattr(building, "type", type(building))
    building_place = getattr(building, "place", None)
    bx = getattr(building, "x", None)
    by = getattr(building, "y", None)
    if bx is None and building_place is not None:
        bx = building_place.x
    if by is None and building_place is not None:
        by = building_place.y

    def _spawn_on(place, ox, oy):
        if place is None or ox is None or oy is None:
            return None, None, None
        if hasattr(place, "have_enough_square_space") and not place.have_enough_square_space(
            unit_type
        ):
            return None, None, None
        x, y = place.find_free_space(unit_type.airground_type, ox, oy)
        if x is None:
            return None, None, None
        return place, x, y

    if getattr(unit_type, "airground_type", None) != "water":
        return _spawn_on(building_place, bx, by)

    if not getattr(building_type, "is_buildable_near_water_only", False):
        return _spawn_on(building_place, bx, by)

    candidates = []
    nearest = building.nearest_water() if hasattr(building, "nearest_water") else None
    if nearest is not None:
        candidates.append(nearest)
    if building_place is not None:
        for sq in building_place.strict_neighbors:
            if getattr(sq, "is_water", False) and sq not in candidates:
                candidates.append(sq)

    for place in candidates:
        for ox, oy in ((place.x, place.y), (bx, by)):
            result = _spawn_on(place, ox, oy)
            if result[0] is not None:
                return result

    # No room on water: spawn on the dock square so AI can push the unit out.
    return _spawn_on(building_place, bx, by)
