"""StarCraft-style build decisions for Computer AI (fields, creep, addons, recombine)."""

from .definitions import rules
from .world_build_rules import (
    _flying_near_addon_landing,
    _ground_type_hosts_addon,
    _host_has_addon_slot,
    _unit_type,
    build_field_ok,
    building_can_operate,
    building_self_constructs,
    can_host_addon,
    deposit_build_target_ok,
    effective_can_train,
    find_orphan_addons_on_square,
    is_addon_type,
    is_flying_building_type,
    is_flying_building_unit,
    is_ground_host_building,
    provides_build_field_type,
    requires_build_field_on_square,
    requires_build_field_type,
    requires_deposit_type,
    try_reattach_orphan_addons,
)

def _is_building_land_obj(obj):
    return getattr(obj, "is_a_building_land", False) and not getattr(
        obj, "is_an_exit", False
    )


def _is_buildable_anywhere_type(building_type):
    return bool(getattr(building_type, "is_buildable_anywhere", 0))


def _is_square_place(place):
    return place is not None and hasattr(place, "neighbors")


def _place_candidates(ai, starting_place=None):
    places = set()
    if starting_place is not None and _is_square_place(starting_place):
        places.add(starting_place)
    for u in ai.units:
        p = getattr(u, "place", None)
        if _is_square_place(p):
            places.add(p)
    for o in ai.perception.union(ai.memory):
        p = getattr(o, "place", None)
        if _is_square_place(p):
            places.add(p)
    return [p for p in places if not ai.square_is_dangerous(p)]


def _live_field_provider_count(ai, field_type):
    n = 0
    for u in ai.units:
        if getattr(u, "hp", 0) <= 0:
            continue
        if provides_build_field_type(getattr(u, "type", u)) == field_type:
            n += 1
    return n


def _provider_in_flight(ai, type_name):
    return max(0, ai.future_nb([type_name]) - ai.nb([type_name]))


def build_worker_count(maker_cls, building_type):
    """How many workers to assign to one build order."""
    mode = getattr(maker_cls, "build_mode", "assisted") or "assisted"
    if mode in ("place_and_leave", "sacrifice"):
        return 1
    if building_self_constructs(building_type):
        return 1
    return 4


def worker_can_repair(worker):
    return bool(getattr(worker, "can_repair", 0))


def worker_can_build(worker, type_name):
    return type_name in getattr(worker, "can_build", ())


def _peasant_class(ai):
    return rules.unit_class(ai.equivalent("peasant"))


def _builders_place(ai):
    if hasattr(ai, "_builders_place"):
        return ai._builders_place()
    if ai.units:
        return ai.units[0].place
    return None


def _meadow_candidates(ai, starting_place=None, resource_type=None):
    if not ai.units:
        return []
    if starting_place is None:
        starting_place = _builders_place(ai) or ai.units[0].place

    def is_ok(o):
        return (
            o.place is not None
            and (
                resource_type is None
                or ai.is_ok_for_warehouse(o.place, resource_type)
            )
            and not ai.square_is_dangerous(o.place)
        )

    candidates = [
        o
        for o in ai.perception.union(ai.memory)
        if _is_building_land_obj(o) and is_ok(o)
    ]
    candidates.sort(key=lambda x: x.id)
    if len(candidates) > 10:
        candidates = ai._remove_far_candidates(candidates, starting_place, 10)
    else:
        candidates.sort(
            key=lambda x: starting_place.shortest_path_distance_to(
                x.place, ai, avoid=True
            )
        )
        while candidates and starting_place.shortest_path_distance_to(
            candidates[-1].place, ai, avoid=True
        ) is float("inf"):
            del candidates[-1]
    return candidates


def resolve_build_target(ai, building_type, target):
    """Validate or normalize an AI build target before issuing a build order."""
    if target is None:
        return None
    from .worldresource import Deposit

    required_deposit = requires_deposit_type(building_type)
    target_is_deposit = isinstance(target, Deposit) or rules.get(
        getattr(target, "type_name", None), "class"
    ) == ["deposit"]
    if target_is_deposit:
        if not required_deposit:
            return None
        if getattr(target, "type_name", None) != required_deposit:
            return None
        if not deposit_build_target_ok(ai, target, building_type):
            return None
        return target
    if _is_building_land_obj(target):
        place = target.place
        if place is None:
            return None
        if build_site_valid(ai, building_type, place, target.x, target.y):
            return target
        return None
    if _is_square_place(target):
        if required_deposit:
            return None
        if getattr(building_type, "is_buildable_anywhere", 0):
            return target
        starting_place = _builders_place(ai)
        for meadow in _meadow_candidates(ai, starting_place):
            if meadow.place is target and build_site_valid(
                ai, building_type, target, meadow.x, meadow.y
            ):
                return meadow
        for obj in getattr(target, "objects", ()):
            if _is_building_land_obj(obj) and build_site_valid(
                ai, building_type, target, obj.x, obj.y
            ):
                return obj
        return None
    return target


def build_site_valid(ai, building_type, place, x, y):
    if getattr(place, "world", None) is None:
        w = getattr(ai, "world", None)
        if w is not None:
            place.world = w
    if not build_field_ok(ai, place, x, y, building_type):
        return False
    required = requires_build_field_type(building_type)
    if required and requires_build_field_on_square(building_type):
        from .world_build_rules import has_marked_build_field_on_square

        world = getattr(place, "world", None) or ai.world
        square = place if hasattr(place, "neighbors") else None
        if square is None:
            return False
        if not has_marked_build_field_on_square(world, square, ai, required):
            return False
    if getattr(building_type, "is_buildable_near_water_only", False):
        square = place if hasattr(place, "neighbors") else None
        if square is None or not getattr(square, "is_near_water", False):
            return False
    if getattr(building_type, "is_buildable_on_water_only", False):
        from .world_build_rules import is_pure_water_square, square_has_bridge_building

        square = place if hasattr(place, "neighbors") else None
        if square is None or not is_pure_water_square(square):
            return False
        if square_has_bridge_building(square):
            return False
    return True


def townhall_place(ai):
    townhall = ai.equivalent("townhall")
    for u in ai.units:
        if getattr(u, "type_name", None) == townhall:
            place = getattr(u, "place", None)
            if _is_square_place(place):
                return place
    return None


def choose_house_build_target(ai, house_type, starting_place=None):
    """Pick a build site for population buildings near the main base."""
    if starting_place is None:
        starting_place = townhall_place(ai) or _builders_place(ai)
    return choose_build_target(
        ai, house_type, starting_place=starting_place, resource_type=None
    )


def choose_near_water_build_target(ai, building_type, starting_place=None):
    """Pick a reachable shore meadow/square for is_buildable_near_water_only buildings."""
    if not getattr(building_type, "is_buildable_near_water_only", False):
        return None
    if starting_place is None:
        starting_place = townhall_place(ai) or _builders_place(ai)
    if starting_place is None:
        return None
    best = None
    best_dist = None
    for sq in getattr(ai.world, "squares", ()):
        if not getattr(sq, "is_near_water", False):
            continue
        if ai.square_is_dangerous(sq):
            continue
        dist = starting_place.shortest_path_distance_to(sq, ai, avoid=True)
        if dist is None or dist == float("inf"):
            dist = starting_place.shortest_path_distance_to(sq, ai, avoid=False)
        if dist is None or dist == float("inf"):
            continue
        for obj in sq.objects:
            if not _is_building_land_obj(obj):
                continue
            if not build_site_valid(ai, building_type, sq, obj.x, obj.y):
                continue
            if best is None or dist < best_dist:
                best = obj
                best_dist = dist
        if best is None and build_site_valid(ai, building_type, sq, sq.x, sq.y):
            if best is None or dist < best_dist:
                best = sq
                best_dist = dist
    return best


def _water_build_path_distance(from_sq, water_sq, ai):
    from .world_build_rules import is_pure_water_square

    if from_sq is water_sq:
        return 0
    best = float("inf")
    for neighbor in water_sq.strict_neighbors:
        if is_pure_water_square(neighbor):
            continue
        dist = from_sq.shortest_path_distance_to(neighbor, ai, avoid=True)
        if dist < best:
            best = dist
    return best


def choose_water_build_target(ai, building_type, starting_place=None):
    """Pick a pure-water square reachable from land for bridge-style buildings."""
    from .world_build_rules import is_pure_water_square, square_has_bridge_building

    if not getattr(building_type, "is_buildable_on_water_only", False):
        return None
    if starting_place is None:
        starting_place = townhall_place(ai) or _builders_place(ai)
    best = None
    best_dist = None
    for sq in getattr(ai.world, "squares", ()):
        if not is_pure_water_square(sq):
            continue
        if square_has_bridge_building(sq):
            continue
        if not build_site_valid(ai, building_type, sq, sq.x, sq.y):
            continue
        if starting_place is None:
            return sq
        dist = _water_build_path_distance(starting_place, sq, ai)
        if dist == float("inf"):
            continue
        if best is None or dist < best_dist:
            best = sq
            best_dist = dist
    return best


def choose_build_target(ai, building_type, starting_place=None, resource_type=None):
    """Pick a meadow or square where building_type passes build_field_ok."""
    if is_addon_type(building_type):
        return choose_addon_host(ai, building_type)
    if getattr(building_type, "is_buildable_on_water_only", False):
        return choose_water_build_target(ai, building_type, starting_place)
    if starting_place is None:
        starting_place = _builders_place(ai)
    anywhere = _is_buildable_anywhere_type(building_type)
    best = None
    best_dist = None

    def _consider(place, x, y):
        nonlocal best, best_dist
        if not build_site_valid(ai, building_type, place, x, y):
            return
        if starting_place is None:
            best = place
            best_dist = 0
            return
        dist = starting_place.shortest_path_distance_to(place, ai, avoid=True)
        if dist is float("inf"):
            return
        if best is None or dist < best_dist:
            best = place
            best_dist = dist

    required_deposit = requires_deposit_type(building_type)
    if required_deposit:
        from .worldresource import Deposit

        for deposit in ai.perception.union(ai.memory):
            if not isinstance(deposit, Deposit):
                continue
            if getattr(deposit, "type_name", None) != required_deposit:
                continue
            if not deposit_build_target_ok(ai, deposit, building_type):
                continue
            if starting_place is None:
                return deposit
            dist = starting_place.shortest_path_distance_to(
                deposit.place, ai, avoid=True
            )
            if dist == float("inf"):
                continue
            if best is None or dist < best_dist:
                best = deposit
                best_dist = dist
        return best

    if not anywhere:
        for meadow in _meadow_candidates(ai, starting_place, resource_type):
            if not build_site_valid(ai, building_type, meadow.place, meadow.x, meadow.y):
                continue
            if starting_place is None:
                return meadow
            dist = starting_place.shortest_path_distance_to(
                meadow.place, ai, avoid=True
            )
            if dist == float("inf"):
                continue
            if best is None or dist < best_dist:
                best = meadow
                best_dist = dist

    if anywhere:
        for place in _place_candidates(ai, starting_place):
            _consider(place, place.x, place.y)

    if best is None:
        return None
    if anywhere:
        return best
    if _is_building_land_obj(best):
        return best
    from .worldresource import Deposit

    if isinstance(best, Deposit):
        return None
    for meadow in _meadow_candidates(ai, starting_place, resource_type):
        if meadow.place is best:
            return meadow
    return None


def field_provider_types(ai, field_type):
    """Building type names peasants can build that provide field_type."""
    peasant = _peasant_class(ai)
    if peasant is None:
        return []
    result = []
    for name in rules.class_rules_attr(peasant, "can_build", ()):
        cls = rules.unit_class(name)
        if cls is not None and provides_build_field_type(cls) == field_type:
            result.append(name)
    return result


def ensure_field_provider_before_build(ai, building_type):
    """If building needs a field and no valid site exists, build a provider first."""
    required = requires_build_field_type(building_type)
    if not required or provides_build_field_type(building_type) == required:
        return False
    if choose_build_target(ai, building_type) is not None:
        return False
    on_square = requires_build_field_on_square(building_type)
    live = _live_field_provider_count(ai, required)
    if on_square and live > 0:
        return True
    if not on_square and live >= 2:
        return False
    providers = field_provider_types(ai, required)
    for name in providers:
        cls = rules.unit_class(name)
        if cls is None or ai.missing_resources(cls.cost):
            continue
        if _provider_in_flight(ai, name) > 0:
            return True
        if on_square and live > 0:
            return True
        if not on_square and live + _provider_in_flight(ai, name) >= 2:
            return False
        if choose_build_target(ai, cls) is None:
            continue
        ai.build_or_train_or_upgradeto_or_summon(cls)
        return True
    return False


def choose_addon_host(ai, addon_type):
    """Host building with a free addon slot compatible with addon_type."""
    hosts = []
    for u in ai.units:
        if not is_ground_host_building(u):
            continue
        if not can_host_addon(u, addon_type):
            continue
        if u.place is None or ai.square_is_dangerous(u.place):
            continue
        if not build_site_valid(ai, addon_type, u.place, u.x, u.y):
            continue
        busy = bool(u.orders)
        hosts.append((busy, u.id, u))
    if not hosts:
        return None
    hosts.sort(key=lambda t: (t[0], t[1]))
    return hosts[0][2]


def addon_types_granting_train(host, train_name):
    host_name = getattr(host, "type_name", None) or _type_name(host)
    result = []
    classes = getattr(rules, "classes", None) or {}
    for name in classes:
        if name == "parameters":
            continue
        cls = rules.unit_class(name)
        if cls is None or not is_addon_type(cls):
            continue
        grants = getattr(cls, f"addon_grants_train_{host_name}", ()) or ()
        if isinstance(grants, str):
            grants = (grants,)
        if train_name in grants:
            result.append(name)
    return result


def _type_name(obj):
    return getattr(obj, "type_name", None) or getattr(obj, "__name__", None)


def host_has_addon_in_progress(ai, host, addon_name):
    for u in ai.units:
        if getattr(u, "addon_host", None) is host and _type_name(u) == addon_name:
            return True
        for o in getattr(u, "orders", []) or []:
            if (
                getattr(o, "keyword", None) == "build"
                and getattr(o, "type", None) is not None
                and _type_name(o.type) == addon_name
                and getattr(o, "addon_host", None) is host
            ):
                return True
    return False


def ensure_host_addon_for_train(ai, host, train_name):
    if train_name in effective_can_train(host):
        return True
    for addon_name in addon_types_granting_train(host, train_name):
        addon_cls = rules.unit_class(addon_name)
        if addon_cls is None or not can_host_addon(host, addon_cls):
            continue
        if host_has_addon_in_progress(ai, host, addon_name):
            return False
        ai.build_or_train_or_upgradeto_or_summon(addon_cls)
        return False
    return False


def find_train_host(ai, maker_names, train_name):
    makers = []
    for u in ai.units:
        if not ai.check_type(u, maker_names):
            continue
        if u.orders:
            continue
        if not building_can_operate(u):
            continue
        if train_name in effective_can_train(u):
            return u
        makers.append(u)
    for u in makers:
        if ensure_host_addon_for_train(ai, u, train_name):
            return u
    return None


def flying_form_for_ground(ground_cls):
    for name in rules.class_rules_attr(ground_cls, "can_change_to", ()):
        cls = rules.unit_class(name)
        if cls is not None and is_flying_building_type(cls):
            return name
    return None


def _all_orphan_addons(ai):
    orphans = []
    seen = set()
    for u in ai.units:
        from .world_build_rules import is_addon_unit

        if not is_addon_unit(u):
            continue
        if getattr(u, "attached_host", None) is not None:
            continue
        if u.id in seen or u.place is None:
            continue
        seen.add(u.id)
        orphans.append(u)
    return orphans


def maintain_terran_recombine(ai):
    """Lift / fly / land to reattach orphaned addons; reattach same-square orphans."""
    for u in ai.units:
        if is_ground_host_building(u) and not u.orders:
            try_reattach_orphan_addons(u)

    for u in ai.units:
        if not is_flying_building_unit(u) or u.orders:
            continue
        ground_name = getattr(_unit_type(u), "ground_form", "")
        if not ground_name:
            continue
        ground_cls = rules.unit_class(ground_name)
        if ground_cls is None:
            continue
        orphans = find_orphan_addons_on_square(ai, u.place, ground_cls)
        for addon in orphans:
            if _flying_near_addon_landing(u, ground_cls, addon):
                u.take_order(["change_to", ground_name])
                break

    for u in ai.units:
        if not is_ground_host_building(u) or u.orders:
            continue
        if not _host_has_addon_slot(u):
            continue
        ground_cls = _unit_type(u)
        flying_name = flying_form_for_ground(ground_cls)
        if not flying_name:
            continue
        for addon in _all_orphan_addons(ai):
            if addon.place is u.place:
                continue
            if not _ground_type_hosts_addon(ground_cls, addon):
                continue
            if not can_host_addon(u, _unit_type(addon)):
                continue
            u.take_order(["change_to", flying_name])
            u.take_order(["go", addon.id])
            break
