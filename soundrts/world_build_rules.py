"""Configurable build rules: power fields, creep marks, build modes, addons."""

from .definitions import rules
from .lib.log import warning
from .lib.nofloat import PRECISION


def _type_name(obj):
    return getattr(obj, "type_name", None) or getattr(obj, "__name__", None)


def _unit_class(type_name):
    if type_name is None:
        return None
    if not isinstance(type_name, str):
        return type_name
    try:
        return rules.unit_class(type_name)
    except (KeyError, AttributeError, TypeError):
        return None


def _expanded_type_names(type_name):
    names = {type_name}
    stack = [type_name]
    while stack:
        current = stack.pop()
        cls = _unit_class(current)
        if cls is None:
            continue
        for parent in getattr(cls, "is_a", ()) or ():
            if parent not in names:
                names.add(parent)
                stack.append(parent)
    return names


def type_matches(unit_or_class, allowed_types):
    """Return True if unit type matches any name in allowed_types (is_a chain)."""
    if not allowed_types:
        return False
    if isinstance(allowed_types, str):
        allowed_types = (allowed_types,)
    type_name = _type_name(unit_or_class)
    if type_name is None:
        return False
    expanded = _expanded_type_names(type_name)
    if getattr(unit_or_class, "expanded_is_a", None):
        expanded.update(unit_or_class.expanded_is_a)
    return bool(expanded.intersection(allowed_types))


def provides_build_field_type(unit_or_class):
    value = getattr(unit_or_class, "provides_build_field", "") or ""
    if not value or value == "0":
        return None
    return value


def requires_build_field_type(unit_or_class):
    value = getattr(unit_or_class, "requires_build_field", "") or ""
    if not value or value == "0":
        return None
    return value


def build_field_persists(unit_or_class):
    return bool(getattr(unit_or_class, "build_field_persists", 0))


def build_field_spreads(unit_or_class):
    return bool(getattr(unit_or_class, "build_field_spreads", 0))


def build_field_spread_squares(unit_or_class):
    """菌毯每秒蔓延格数；未写时启用蔓延的单位默认为 1。"""
    rate = getattr(unit_or_class, "build_field_spread_squares", 0) or 0
    if rate <= 0:
        return 1 if build_field_spreads(unit_or_class) else 0
    if rate >= PRECISION:
        return int(rate // PRECISION)
    return int(rate)


def requires_build_field_on_square(building_type):
    return bool(getattr(building_type, "requires_build_field_on_square", 0))


def requires_deposit_type(unit_or_class):
    """Return deposit type_name required to build on (e.g. geyser), or None."""
    value = getattr(unit_or_class, "requires_deposit", "") or ""
    if not value or value == "0":
        return None
    return value


def deposit_on_square(square, deposit_type):
    """First deposit of deposit_type on square, or None."""
    if square is None or not deposit_type:
        return None

    for obj in getattr(square, "objects", ()):
        if (
            getattr(obj, "type_name", None) == deposit_type
            and getattr(obj, "place", None) is not None
            and rules.get(obj.type_name, "class") == ["deposit"]
        ):
            return obj
    return None


def deposit_build_target_ok(player, deposit, building_type):
    """True if deposit is a valid build site for building_type."""
    required = requires_deposit_type(building_type)
    if not required:
        return False
    if getattr(deposit, "type_name", None) != required:
        return False
    if getattr(deposit, "place", None) is None:
        return False
    return build_field_ok(
        player,
        deposit.place,
        deposit.x,
        deposit.y,
        building_type,
    )


def loses_power_without_field(unit_or_class):
    return bool(getattr(unit_or_class, "loses_power_without_field", 0))


def build_field_radius_squares(unit_or_class):
    """供能半径，单位为地图格子数（与 rules 中 build_field_radius 6 一致）。"""
    radius = getattr(unit_or_class, "build_field_radius", 0) or 0
    if radius <= 0:
        return 0
    if radius >= PRECISION:
        return int(radius // PRECISION)
    return int(radius)


def build_field_radius_meters(unit_or_class):
    """供能半径（米），内部为与 rdg_range 相同的精度单位；0 表示不用米制。"""
    radius = getattr(unit_or_class, "build_field_radius_m", 0) or 0
    return int(radius)


def uses_meter_build_field(unit_or_class):
    return build_field_radius_meters(unit_or_class) > 0


def _build_field_target_xy(square, x=None, y=None):
    if x is not None and y is not None:
        return x, y
    return getattr(square, "x", 0), getattr(square, "y", 0)


def _point_in_meter_build_field(provider, tx, ty):
    radius = build_field_radius_meters(provider)
    if radius <= 0 or provider.place is None:
        return False
    from .lib.nofloat import square_of_distance

    return square_of_distance(provider.x, provider.y, tx, ty) <= radius * radius


def _squares_in_meter_build_field_range(unit):
    """米制供能/菌毯：标记中心落在半径内的连通格子。"""
    if not uses_meter_build_field(unit) or unit.place is None:
        return set()
    result = set()
    queue = [unit.place]
    seen = set()
    while queue:
        sq = queue.pop(0)
        if sq in seen:
            continue
        seen.add(sq)
        tx = getattr(sq, "x", getattr(unit, "x", 0))
        ty = getattr(sq, "y", getattr(unit, "y", 0))
        if not _point_in_meter_build_field(unit, tx, ty):
            continue
        result.add(sq)
        for neighbor in getattr(sq, "neighbors", ()):
            if neighbor not in seen:
                queue.append(neighbor)
    return result


def _squares_in_build_field_range(start_place, radius_squares):
    """从 start_place 出发，BFS 扩展 radius_squares 格（与视野 BFS 语义一致）。"""
    if start_place is None or radius_squares <= 0:
        return set()
    squares = {start_place}
    if radius_squares <= 1:
        return squares
    visited = {start_place}
    queue = [(start_place, 0)]
    qi = 0
    while qi < len(queue):
        current_place, distance = queue[qi]
        qi += 1
        if distance >= radius_squares:
            continue
        for neighbor in current_place.neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                squares.add(neighbor)
                queue.append((neighbor, distance + 1))
    return squares


def _square_for_build_target(world, place, x, y):
    if place is not None and hasattr(place, "neighbors"):
        return place
    if world is not None:
        return world.get_place_from_xy(x, y)
    return None


def _field_mark_key(player, field_type):
    return (player.id, field_type)


def _marked_squares(world, player, field_type):
    marks = getattr(world, "_build_field_marked_squares", None)
    if not marks:
        return set()
    return marks.get(_field_mark_key(player, field_type), set())


def mark_build_field_squares(world, player, field_type, squares):
    if world is None or player is None or not field_type or not squares:
        return
    if not hasattr(world, "_build_field_marked_squares"):
        init_world_build_rules(world)
    key = _field_mark_key(player, field_type)
    world._build_field_marked_squares.setdefault(key, set()).update(squares)


def paint_build_field_from_unit(unit):
    """将提供者当前供能范围内的格子写入持久地表标记（菌毯等）。"""
    field_type = provides_build_field_type(unit)
    if not field_type or unit.place is None:
        return
    radius = build_field_radius_squares(unit)
    squares = (
        _squares_in_build_field_range(unit.place, radius)
        if radius > 0
        else _squares_in_meter_build_field_range(unit)
    )
    if not squares:
        return
    mark_build_field_squares(unit.world, unit.player, field_type, squares)


def init_world_build_rules(world):
    world._build_field_provider_ids = set()
    world._build_field_marked_squares = {}


def _can_provide_build_field_now(unit):
    if not provides_build_field_type(unit):
        return False
    if (
        build_field_radius_squares(unit) <= 0
        and build_field_radius_meters(unit) <= 0
    ):
        return False
    if loses_power_without_field(unit) and not building_is_powered(unit):
        return False
    return True


def register_build_field_provider(unit):
    if not _can_provide_build_field_now(unit):
        return
    world = unit.world
    if not hasattr(world, "_build_field_provider_ids"):
        init_world_build_rules(world)
    world._build_field_provider_ids.add(unit.id)
    if build_field_persists(unit) or build_field_spreads(unit):
        paint_build_field_from_unit(unit)


def unregister_build_field_provider(unit):
    world = getattr(unit, "world", None)
    if world is None:
        return
    providers = getattr(world, "_build_field_provider_ids", None)
    if providers is not None:
        providers.discard(unit.id)


def has_live_build_field_on_square(
    world, square, player, field_type, exclude_unit_id=None, x=None, y=None
):
    """神族灵能场：仅活着的提供者按半径实时供能。"""
    if not field_type or player is None or square is None:
        return False
    providers = getattr(world, "_build_field_provider_ids", None)
    if not providers:
        return False
    tx, ty = _build_field_target_xy(square, x, y)
    radius_cache = {}
    meter_cache = {}
    for uid in list(providers):
        if exclude_unit_id is not None and uid == exclude_unit_id:
            continue
        unit = world.objects.get(uid)
        if unit is None or unit.player is not player:
            continue
        if unit.place is None:
            continue
        if not _can_provide_build_field_now(unit):
            continue
        ft = provides_build_field_type(unit)
        if ft != field_type:
            continue
        type_name = _type_name(unit)
        if type_name not in meter_cache:
            meter_cache[type_name] = build_field_radius_meters(unit)
        if meter_cache.get(type_name, 0) and _point_in_meter_build_field(unit, tx, ty):
            return True
        if uses_meter_build_field(unit):
            continue
        if type_name not in radius_cache:
            radius_cache[type_name] = build_field_radius_squares(unit)
        radius = radius_cache.get(type_name, 0)
        if radius and square in _squares_in_build_field_range(unit.place, radius):
            return True
    return False


def has_marked_build_field_on_square(world, square, player, field_type):
    """虫族菌毯：格子上是否有持久地表标记。"""
    if not field_type or player is None or square is None:
        return False
    return square in _marked_squares(world, player, field_type)


def has_build_field_at(world, x, y, player, field_type):
    square = world.get_place_from_xy(x, y) if world is not None else None
    return has_build_field_on_square(world, square, player, field_type)


def has_build_field_on_square(world, square, player, field_type):
    return has_live_build_field_on_square(
        world, square, player, field_type
    ) or has_marked_build_field_on_square(world, square, player, field_type)


def build_field_types_on_square(world, square, player):
    """Return sorted field type names active on square for player (live + marks)."""
    if world is None or square is None or player is None:
        return []
    types = set()
    marks = getattr(world, "_build_field_marked_squares", None)
    if marks:
        pid = player.id
        for (mark_pid, field_type), squares in marks.items():
            if mark_pid == pid and square in squares:
                types.add(field_type)
    providers = getattr(world, "_build_field_provider_ids", None)
    if providers:
        for uid in list(providers):
            unit = world.objects.get(uid)
            if unit is None or unit.player is not player or unit.place is None:
                continue
            if not _can_provide_build_field_now(unit):
                continue
            field_type = provides_build_field_type(unit)
            if not field_type:
                continue
            if uses_meter_build_field(unit):
                if _point_in_meter_build_field(
                    unit, getattr(square, "x", 0), getattr(square, "y", 0)
                ):
                    types.add(field_type)
                continue
            radius = build_field_radius_squares(unit)
            if radius and square in _squares_in_build_field_range(unit.place, radius):
                types.add(field_type)
    return sorted(types)


def _rules_subject_for_build_field(unit):
    """BuildingSite 用目标建筑类型判断供能/建造场需求。"""
    if getattr(unit, "type_name", None) == "buildingsite":
        building_type = getattr(unit, "type", None)
        if building_type is not None:
            return building_type
    return unit


def building_is_powered(unit):
    """神族断电：失去实时灵能场时停工、停供能。"""
    if unit is None or unit.place is None:
        return False
    required = requires_build_field_type(_rules_subject_for_build_field(unit))
    if not required:
        return True
    subject = _rules_subject_for_build_field(unit)
    if not loses_power_without_field(subject):
        return True
    exclude = unit.id if provides_build_field_type(subject) == required else None
    return has_live_build_field_on_square(
        unit.world,
        unit.place,
        unit.player,
        required,
        exclude_unit_id=exclude,
        x=unit.x,
        y=unit.y,
    )


def building_can_operate(unit):
    if not getattr(unit, "is_a_building", False):
        return True
    if is_flying_building_unit(unit):
        return False
    return building_is_powered(unit)


def construction_can_progress(unit):
    """工地/自动施工：受断电影响时暂停进度。"""
    building_type = getattr(unit, "type", None)
    if building_type is None:
        return True
    if not requires_build_field_type(building_type):
        return True
    if not loses_power_without_field(building_type):
        return True
    return building_is_powered(unit)


def build_field_ok(player, place, x, y, building_type):
    required = requires_build_field_type(building_type)
    if not required:
        return True
    world = getattr(place, "world", None)
    if world is None and place is not None and hasattr(place, "grid"):
        world = place
    if world is None:
        return False
    square = _square_for_build_target(world, place, x, y)
    if square is None:
        return False
    if requires_build_field_on_square(building_type):
        return has_marked_build_field_on_square(world, square, player, required)
    return has_live_build_field_on_square(
        world, square, player, required, x=x, y=y
    )


def tick_build_fields(world):
    """每秒：菌毯蔓延 + 神族建筑断电状态刷新。"""
    if world is None:
        return
    providers = getattr(world, "_build_field_provider_ids", None)
    if providers:
        spread_done = set()
        for uid in list(providers):
            unit = world.objects.get(uid)
            if unit is None or not build_field_spreads(unit):
                continue
            if not _can_provide_build_field_now(unit):
                continue
            field_type = provides_build_field_type(unit)
            if not field_type:
                continue
            key = (unit.player.id, field_type)
            if key in spread_done:
                continue
            spread_done.add(key)
            marks = _marked_squares(world, unit.player, field_type)
            if not marks:
                paint_build_field_from_unit(unit)
                marks = _marked_squares(world, unit.player, field_type)
            layers = build_field_spread_squares(unit)
            for _ in range(layers):
                new_marks = set()
                for sq in list(marks):
                    for neighbor in sq.neighbors:
                        if neighbor not in marks:
                            new_marks.add(neighbor)
                if not new_marks:
                    break
                mark_build_field_squares(world, unit.player, field_type, new_marks)
                marks = _marked_squares(world, unit.player, field_type)

    for player in getattr(world, "players", []):
        for unit in list(getattr(player, "units", [])):
            if not getattr(unit, "is_a_building", False):
                continue
            if not provides_build_field_type(unit):
                continue
            if not loses_power_without_field(unit):
                continue
            was_registered = unit.id in providers
            should_register = _can_provide_build_field_now(unit)
            if should_register and not was_registered:
                register_build_field_provider(unit)
            elif not should_register and was_registered:
                unregister_build_field_provider(unit)


def worker_build_mode(worker):
    return getattr(worker, "build_mode", "assisted") or "assisted"


def building_self_constructs(building_type):
    return bool(getattr(building_type, "self_constructs", 0))


def building_sacrifices_worker(building_type, worker):
    if getattr(building_type, "build_sacrifices_worker", 0):
        return True
    return worker_build_mode(worker) == "sacrifice"


def worker_place_and_leave(worker, building_type):
    if worker_build_mode(worker) == "place_and_leave":
        return True
    if worker_build_mode(worker) == "sacrifice":
        return True
    return building_self_constructs(building_type)


DEFAULT_ADDON_OFFSET_X = 3500
# 飞行中贴近宿主降落插槽才允许对齐降落（go 到科技实验室会飞向插槽）
ADDON_REATTACH_TOLERANCE = 2500
ADDON_LANDING_APPROACH_DIST = ADDON_REATTACH_TOLERANCE + 500
# 降落后重组：宿主必须落在附件对齐坐标（比飞行贴近判定更严）
ADDON_LANDED_SLOT_TOLERANCE = 300


def is_addon_type(building_type):
    return bool(getattr(building_type, "is_addon", 0))


def is_addon_unit(unit):
    return is_addon_type(getattr(unit, "type", unit))


def _unit_type(unit):
    return getattr(unit, "type", type(unit))


def is_flying_building_unit(unit):
    """飞行中的人族生产建筑（带 ground_form 的空中形态）。"""
    if unit is None:
        return False
    return bool(getattr(_unit_type(unit), "ground_form", ""))


def is_ground_host_building(unit):
    """可挂附件的地面生产建筑（兵营/工厂/星港等）。"""
    if unit is None or not getattr(unit, "is_a_building", False):
        return False
    if getattr(unit, "airground_type", "ground") == "air":
        return False
    return bool(getattr(_unit_type(unit), "can_have_addon", ()) or ())


def is_flying_building_type(building_type):
    return bool(getattr(building_type, "ground_form", ""))


def is_ground_host_building_type(building_type):
    return bool(getattr(building_type, "can_have_addon", ()) or ())


def addon_side_offset_x(host):
    t = _unit_type(host)
    offset = getattr(host, "addon_offset_x", 0) or getattr(t, "addon_offset_x", 0)
    return _parse_addon_offset(offset)


def addon_side_offset_x_for_type(building_type):
    offset = getattr(building_type, "addon_offset_x", 0) or 0
    return _parse_addon_offset(offset)


def _parse_addon_offset(offset):
    if offset <= 0:
        return DEFAULT_ADDON_OFFSET_X
    if offset >= PRECISION:
        return int(offset)
    return int(offset * PRECISION)


def _ground_type_hosts_addon(ground_type, addon):
    allowed = getattr(_unit_type(addon), "addon_host_types", ()) or ()
    if not allowed:
        return False
    return type_matches(ground_type, allowed)


def find_orphan_addons_on_square(player, place, ground_type):
    """同格、无宿主、与即将落地的地面建筑类型兼容的孤立附件。"""
    if player is None or place is None or ground_type is None:
        return []
    orphans = []
    for unit in list(getattr(player, "units", [])):
        if not is_addon_unit(unit):
            continue
        if getattr(unit, "attached_host", None) is not None:
            continue
        if unit.place is not place:
            continue
        if getattr(unit, "hp", 0) <= 0:
            continue
        if not _ground_type_hosts_addon(ground_type, unit):
            continue
        orphans.append(unit)
    return orphans


def _aligned_host_coords_for_addon(ground_type, addon):
    offset = addon_side_offset_x_for_type(ground_type)
    return addon.x - offset, addon.y


def _coords_within_tolerance(x1, y1, x2, y2, tolerance=ADDON_REATTACH_TOLERANCE):
    return (
        abs(x1 - x2) <= tolerance
        and abs(y1 - y2) <= tolerance
    )


def _manhattan_distance(x1, y1, x2, y2):
    return abs(x1 - x2) + abs(y1 - y2)


def _flying_near_addon_landing(flying_unit, ground_type, addon):
    """飞行建筑已贴近宿主降落插槽时，才按插槽对齐降落（非实验室本体）。"""
    align_x, align_y = _aligned_host_coords_for_addon(ground_type, addon)
    return (
        _manhattan_distance(flying_unit.x, flying_unit.y, align_x, align_y)
        <= ADDON_LANDING_APPROACH_DIST
    )


def has_pending_orphan_addons_for_host(host):
    """同格仍有与宿主兼容、尚未挂接的孤立附件。"""
    if not is_ground_host_building(host):
        return False
    ground_type = _unit_type(host)
    for addon in find_orphan_addons_on_square(host.player, host.place, ground_type):
        if can_host_addon(host, _unit_type(addon)):
            return True
    return False


def go_target_for_flying_building_addon(unit, target):
    """飞行生产建筑 go 到附件时，改飞向宿主降落插槽（贴脸降落）。"""
    if unit is None or target is None:
        return target
    if not is_addon_unit(target) or not is_flying_building_unit(unit):
        return target
    ground_name = getattr(_unit_type(unit), "ground_form", "")
    if not ground_name:
        return target
    ground_cls = _unit_class(ground_name)
    if ground_cls is None and _type_name(_unit_type(unit)) == ground_name:
        ground_cls = _unit_type(unit)
    if ground_cls is None or not is_ground_host_building_type(ground_cls):
        return target
    if not _ground_type_hosts_addon(ground_cls, target):
        return target
    from .worldroom import ZoomTarget

    align_x, align_y = _aligned_host_coords_for_addon(ground_cls, target)
    return ZoomTarget(target.place, align_x, align_y, id=getattr(target, "id", None))


def landing_coords_for_ground_building(place, flying_unit, ground_type):
    """降落坐标：贴近附件插槽时对齐插槽；否则落在当前位置附近草地。

    若飞行单位已贴近脚下最近草地（例如 go 到起飞留下的草地），优先占用该草地，
    不因同格存在孤立附件而被吸附到别的草地（重组需 go 到科技实验室/插槽旁）。
    """
    if place is None or flying_unit is None:
        return None, None, None
    meadow_at_unit = (
        place.find_meadow_near_xy(flying_unit.x, flying_unit.y)
        if hasattr(place, "find_meadow_near_xy")
        else None
    )
    player = getattr(flying_unit, "player", None)
    orphans = (
        find_orphan_addons_on_square(player, place, ground_type) if player else []
    )
    eligible = [
        addon
        for addon in orphans
        if _flying_near_addon_landing(flying_unit, ground_type, addon)
    ]
    if eligible:
        addon = min(
            eligible,
            key=lambda a: abs(a.x - flying_unit.x) + abs(a.y - flying_unit.y),
        )
        align_x, align_y = _aligned_host_coords_for_addon(ground_type, addon)
        if meadow_at_unit is not None:
            dist_meadow = _manhattan_distance(
                flying_unit.x, flying_unit.y, meadow_at_unit.x, meadow_at_unit.y
            )
            dist_align = _manhattan_distance(
                flying_unit.x, flying_unit.y, align_x, align_y
            )
            if dist_meadow < dist_align:
                eligible = []
        if eligible:
            meadow = (
                place.find_meadow_near_xy(align_x, align_y)
                if hasattr(place, "find_meadow_near_xy")
                else None
            )
            if meadow is None and hasattr(place, "find_nearest_meadow"):
                meadow = place.find_nearest_meadow(flying_unit)
            if meadow is not None:
                return align_x, align_y, meadow
    if hasattr(place, "find_meadow_near_xy"):
        meadow = place.find_meadow_near_xy(flying_unit.x, flying_unit.y)
        if meadow is not None:
            return flying_unit.x, flying_unit.y, meadow
    if hasattr(place, "find_nearest_meadow"):
        meadow = place.find_nearest_meadow(flying_unit)
        if meadow is not None:
            return meadow.x, meadow.y, meadow
    return None, None, None


def addon_slot_coords(host):
    return host.x + addon_side_offset_x(host), host.y


def host_attached_addons(host):
    return [
        a
        for a in getattr(host, "attached_addons", []) or []
        if a is not None
        and getattr(a, "place", None) is not None
        and getattr(a, "hp", 1) > 0
    ]


def _normalize_train_list(values):
    if not values:
        return ()
    if isinstance(values, property):
        return ()
    if isinstance(values, dict):
        return tuple(values.keys())
    if isinstance(values, str):
        return (values,)
    return tuple(values)


def _raw_class_attr(cls, name, default=()):
    """Read rules class attr; skip @property descriptors inherited from Building."""
    for base in getattr(cls, "__mro__", (cls,)):
        if name in base.__dict__:
            val = base.__dict__[name]
            if isinstance(val, property):
                continue
            return val if val else default
    return default


def _rules_can_train_dict(cls):
    raw = _raw_class_attr(cls, "_rules_can_train", None)
    if isinstance(raw, dict):
        return raw
    raw = _raw_class_attr(cls, "can_train", ())
    if isinstance(raw, dict):
        return raw
    return {}


def _base_can_train(host):
    return _normalize_train_list(_rules_can_train_dict(_unit_type(host)) or _raw_class_attr(_unit_type(host), "can_train", ()))


def _base_can_research(host):
    return _raw_class_attr(_unit_type(host), "can_research", ())


def _addon_train_grants_for_host(addon, host):
    host_name = _type_name(host)
    at = _unit_type(addon)
    specific = getattr(at, f"addon_grants_train_{host_name}", ()) or ()
    generic = getattr(at, "addon_grants_train", ()) or ()
    return _normalize_train_list(specific) + _normalize_train_list(generic)


def _addon_research_grants_for_host(addon, host):
    return _normalize_train_list(
        getattr(_unit_type(addon), "addon_grants_research", ()) or ()
    )


def _player_can_train_override(player, type_name):
    """Per-building-type train batch overrides from ``effect bonus can_train``."""
    if player is None or not type_name:
        return None
    by_type = getattr(player, "_can_train_overrides_by_type", None)
    if by_type and type_name in by_type:
        return by_type[type_name]
    return None


def _merge_player_can_train_override(host, result):
    """Apply researched ``can_train`` bonuses stored on the player."""
    player = getattr(host, "player", None)
    override = _player_can_train_override(player, _type_name(host))
    if not override:
        return result
    if isinstance(result, dict):
        merged = dict(result)
    elif isinstance(result, tuple):
        merged = {name: 1 for name in result}
    else:
        return result
    train_names = set(_normalize_train_list(_base_can_train(host)))
    train_names.update(merged.keys())
    for name in train_names:
        if name in override:
            merged[name] = max(1, int(override[name]))
    if any(v != 1 for v in merged.values()):
        return merged
    return tuple(merged.keys()) if isinstance(result, tuple) else merged


def effective_can_train(host):
    """合并宿主基础训练列表与附件加成（科技实验室解锁、反应堆双产）。"""
    if host is None or is_flying_building_unit(host):
        return ()
    base = _normalize_train_list(_base_can_train(host))
    train_names = list(base)
    multipliers = {}
    for addon in host_attached_addons(host):
        for name in _addon_train_grants_for_host(addon, host):
            if name not in train_names:
                train_names.append(name)
        mult = getattr(_unit_type(addon), "addon_train_multiplier", 0) or 0
        if mult > 1:
            for name in train_names:
                multipliers[name] = max(multipliers.get(name, 1), int(mult))
    base_counts = _rules_can_train_dict(_unit_type(host))
    if multipliers or base_counts:
        result = {}
        for name in train_names:
            count = base_counts.get(name, 1)
            if name in multipliers:
                count = max(count, multipliers[name])
            result[name] = max(1, int(count))
        if multipliers or any(v != 1 for v in result.values()):
            return _merge_player_can_train_override(host, result)
    base_result = tuple(train_names)
    return _merge_player_can_train_override(host, base_result)


def effective_can_research(host):
    if host is None or is_flying_building_unit(host):
        return ()
    names = list(_normalize_train_list(_base_can_research(host)))
    for addon in host_attached_addons(host):
        for name in _addon_research_grants_for_host(addon, host):
            if name not in names:
                names.append(name)
    return tuple(names)


def detach_addons_for_lift(host):
    """主建筑起飞：附件留在地面并解除关联。"""
    detached = []
    for addon in list(host_attached_addons(host)):
        detach_addon(host, addon)
        ax, ay = addon_slot_coords(host)
        if hasattr(addon, "move_to"):
            addon.move_to(host.place, ax, ay)
        else:
            addon.x, addon.y = ax, ay
        detached.append(addon)
    return detached


def _addon_near_host_slot(addon, host, tolerance=ADDON_REATTACH_TOLERANCE):
    ax, ay = addon_slot_coords(host)
    return (
        _manhattan_distance(addon.x, addon.y, ax, ay)
        <= tolerance
    )


def _host_landed_for_addon_reattach(host, addon):
    """宿主已落在该孤立附件的对接坐标（非仅同格或插槽近似）。"""
    align_x, align_y = _aligned_host_coords_for_addon(_unit_type(host), addon)
    return _coords_within_tolerance(
        host.x,
        host.y,
        align_x,
        align_y,
        tolerance=ADDON_LANDED_SLOT_TOLERANCE,
    )


def _host_has_addon_slot(host):
    current = host_attached_addons(host)
    addon_max = getattr(_unit_type(host), "addon_max", 1) or 1
    return len(current) < addon_max


def _iter_orphan_addons_for_host(host, require_near_slot=False):
    if not is_ground_host_building(host) or not _host_has_addon_slot(host):
        return
    if host.place is None or host.player is None:
        return
    candidates = []
    for unit in list(getattr(host.player, "units", [])):
        if not is_addon_unit(unit):
            continue
        if getattr(unit, "attached_host", None) is not None:
            continue
        if unit.place is not host.place:
            continue
        if getattr(unit, "hp", 0) <= 0:
            continue
        if not can_host_addon(host, _unit_type(unit)):
            continue
        if require_near_slot:
            if not _addon_near_host_slot(
                unit, host, tolerance=ADDON_LANDED_SLOT_TOLERANCE
            ):
                continue
            if not _host_landed_for_addon_reattach(host, unit):
                continue
        dist = abs(unit.x - host.x) + abs(unit.y - host.y)
        candidates.append((dist, unit))
    for _, unit in sorted(candidates, key=lambda item: item[0]):
        yield unit


def find_orphan_addon_for_host(host):
    """查找落点旁可接管的孤立附件（已完工、无宿主）。"""
    for unit in _iter_orphan_addons_for_host(host, require_near_slot=True):
        return unit
    return None


def try_reattach_orphan_addons(host):
    """主建筑降落：仅当落点与孤立附件插槽对齐时挂接（还原星际）。"""
    if not is_ground_host_building(host):
        return False
    reattached = False
    while _host_has_addon_slot(host):
        addon = find_orphan_addon_for_host(host)
        if addon is None:
            break
        if not can_host_addon(host, _unit_type(addon)):
            break
        attach_addon(host, addon)
        reattached = True
    if reattached and hasattr(host, "notify"):
        host.notify("addon_reattach")
    return reattached


def can_host_addon(host, addon_type):
    if host is None or not getattr(host, "is_a_building", False):
        return False
    if getattr(host, "player", None) is None:
        return False
    if is_flying_building_unit(host):
        return False
    if addon_type is not None:
        allowed = getattr(addon_type, "addon_host_types", ()) or ()
        if not type_matches(host, allowed):
            return False
    can_have = getattr(host, "can_have_addon", ()) or getattr(
        _unit_type(host), "can_have_addon", ()
    )
    if can_have and addon_type is not None:
        addon_name = _type_name(addon_type)
        if not _expanded_type_names(addon_name).intersection(can_have):
            return False
    current = [a for a in getattr(host, "attached_addons", []) if a.place is not None]
    addon_max = getattr(_unit_type(host), "addon_max", 1) or 1
    return len(current) < addon_max


def attach_addon(host, addon):
    if host is None or addon is None:
        return
    if not hasattr(host, "attached_addons"):
        host.attached_addons = []
    if addon not in host.attached_addons:
        host.attached_addons.append(addon)
    addon.attached_host = host
    if host.place is not None and hasattr(addon, "move_to"):
        ax, ay = addon_slot_coords(host)
        addon.move_to(host.place, ax, ay)


def detach_addon(host, addon):
    if host is None or addon is None:
        return
    addons = getattr(host, "attached_addons", None)
    if addons and addon in addons:
        addons.remove(addon)
    if getattr(addon, "attached_host", None) is host:
        addon.attached_host = None


def cleanup_build_rules_on_death(unit):
    place = getattr(unit, "place", None)
    if provides_build_field_type(unit) and build_field_persists(unit):
        paint_build_field_from_unit(unit)
    unregister_build_field_provider(unit)
    if bridge_terrain_type(_bridge_subject_type(unit)) and place is not None:
        refresh_bridge_terrain(place)
    if getattr(unit, "is_a_building", False):
        for addon in list(getattr(unit, "attached_addons", []) or []):
            if addon is not unit and addon.place is not None:
                addon.die()
        for addon in list(getattr(unit, "attached_addons", []) or []):
            detach_addon(unit, addon)
    host = getattr(unit, "attached_host", None)
    if host is not None:
        detach_addon(host, unit)


def bridge_terrain_type(unit_or_class):
    """Return terrain name applied when this building stands on water, or None."""
    value = getattr(unit_or_class, "bridge_terrain", "") or ""
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    if not value or value == "0":
        return None
    return value


def is_buildable_on_water_only_type(unit_or_class):
    return bool(getattr(unit_or_class, "is_buildable_on_water_only", 0))


def is_pure_water_square(square):
    """Water that blocks ground units (river/lake/ocean; not ford/bridge)."""
    if square is None:
        return False
    return getattr(square, "is_water", False) and not getattr(
        square, "is_ground", True
    )


def _bridge_subject_type(obj):
    if getattr(obj, "type_name", None) == "buildingsite":
        return getattr(obj, "type", obj)
    return getattr(obj, "type", type(obj))


def _bridge_terrain_providers(objects):
    """Completed bridge buildings that grant passage (not construction sites)."""
    for obj in objects or ():
        if getattr(obj, "hp", 1) <= 0:
            continue
        if getattr(obj, "type_name", None) == "buildingsite":
            continue
        name = bridge_terrain_type(_bridge_subject_type(obj))
        if name:
            yield name


def water_only_build_square_for(target):
    """Return the water square for a water-only build target, or None."""
    if target is None:
        return None
    if not is_buildable_on_water_only_type(_bridge_subject_type(target)):
        return None
    square = getattr(target, "place", None)
    if square is None or not is_pure_water_square(square):
        return None
    return square


def can_build_water_target_from_shore(target, worker):
    """True if *worker* on adjacent land may build a water-only target."""
    if worker is None or target is None:
        return False
    if getattr(target, "type_name", None) == "buildingsite":
        return False
    if getattr(worker, "airground_type", None) != "ground":
        return False
    if not is_buildable_on_water_only_type(_bridge_subject_type(target)):
        return False
    water_square = getattr(target, "place", None)
    if water_square is None or not getattr(water_square, "is_water", False):
        return False
    if worker.place is water_square and getattr(water_square, "is_ground", False):
        return True
    return worker_can_place_water_build(worker, water_square)


def square_has_bridge_building(square):
    """True if square already has a bridge/scaffold building or site."""
    if square is None:
        return False
    for obj in getattr(square, "objects", ()):
        if getattr(obj, "hp", 1) <= 0:
            continue
        if bridge_terrain_type(_bridge_subject_type(obj)):
            return True
    return False


def invalidate_world_regions(world):
    """Drop cached region graph so ground flood-fill picks up bridge changes."""
    if world is None:
        return
    if hasattr(world, "region_graph"):
        del world.region_graph
    if hasattr(world, "region_portals"):
        del world.region_portals
    for sq in getattr(world, "squares", ()):
        if hasattr(sq, "region"):
            sq.region = None


def square_has_construction_scaffold(square):
    """True if *square* is water with an active walk-on scaffold (BuildingSite)."""
    if square is None or not getattr(square, "_scaffold_terrain_saved", None):
        return False
    for obj in getattr(square, "objects", ()) or ():
        if getattr(obj, "type_name", None) != "buildingsite":
            continue
        if getattr(obj, "shore_land", None) is None:
            continue
        if getattr(obj, "hp", 1) <= 0:
            continue
        return True
    return False


def _scaffold_placed_from_shore(scaffold_square, shore_square):
    """True if *scaffold_square* has a walk-on scaffold placed from *shore_square*."""
    if not square_has_construction_scaffold(scaffold_square):
        return False
    for obj in getattr(scaffold_square, "objects", ()) or ():
        if getattr(obj, "type_name", None) != "buildingsite":
            continue
        if getattr(obj, "shore_land", None) is shore_square:
            return True
    return False


def scaffold_shore_land(scaffold_square):
    """Placer shore recorded on an active walk-on scaffold, or None."""
    if not square_has_construction_scaffold(scaffold_square):
        return None
    for obj in getattr(scaffold_square, "objects", ()) or ():
        if getattr(obj, "type_name", None) != "buildingsite":
            continue
        shore = getattr(obj, "shore_land", None)
        if shore is not None and getattr(obj, "hp", 1) > 0:
            return shore
    return None


def scaffold_go_forbidden(unit, dest_square):
    """Block ``go`` onto/off an unfinished span except via its placer shore."""
    if getattr(unit, "airground_type", None) != "ground":
        return False
    place = getattr(unit, "place", None)
    if place is None or dest_square is None or place is dest_square:
        return False

    if square_has_construction_scaffold(dest_square):
        shore = scaffold_shore_land(dest_square)
        if shore is None:
            return False
        if square_has_construction_scaffold(place):
            return True
        return place is not shore

    if square_has_construction_scaffold(place):
        shore = scaffold_shore_land(place)
        if shore is None:
            return False
        if square_has_construction_scaffold(dest_square):
            return True
        if not getattr(dest_square, "is_water", False):
            return dest_square is not shore
        return False

    return False


def _bridge_passage_allowed(a, b):
    """Whether an exit may exist between two squares (mirrors ``passage()``)."""
    if getattr(a, "is_water", False) != getattr(b, "is_water", False):
        return getattr(a, "is_ground", True) and getattr(b, "is_ground", True)
    if getattr(a, "is_water", False) and getattr(b, "is_water", False):
        if square_has_construction_scaffold(a) and square_has_construction_scaffold(b):
            return False
        if _bridge_square_active(a) and _scaffold_placed_from_shore(b, a):
            return True
        if _bridge_square_active(b) and _scaffold_placed_from_shore(a, b):
            return True
        if square_has_construction_scaffold(a) or square_has_construction_scaffold(b):
            return False
        return _bridge_square_active(a) and _bridge_square_active(b)
    return True


def _bridge_square_active(square):
    """True if *square* currently grants bridge passability."""
    return bool(getattr(square, "_bridge_terrain_voice", None))


def _passage_exit_type(a, b):
    """Exit style between two squares (bridge-to-bridge uses ``bridge``)."""
    if _bridge_square_active(a) and _bridge_square_active(b):
        return "bridge"
    return "path"


def is_scaffold_water_build_target(target):
    """Water-only BuildingSite with a recorded placer shore (walk-on build)."""
    if getattr(target, "type_name", None) != "buildingsite":
        return False
    if not is_buildable_on_water_only_type(_bridge_subject_type(target)):
        return False
    return getattr(target, "shore_land", None) is not None


def _apply_scaffold_passage(site):
    """Apply scaffold footing and shore-only exit for one site (no world sync)."""
    if site is None:
        return
    water = getattr(site, "place", None)
    shore = getattr(site, "shore_land", None)
    if water is None or shore is None:
        return
    if not is_buildable_on_water_only_type(_bridge_subject_type(site)):
        return
    from .lib.square_terrain_rules import DEFAULT_TERRAIN_SPEED, resolve_terrain_speed

    saved = getattr(water, "_scaffold_terrain_saved", None)
    if saved is None:
        water._scaffold_terrain_saved = {
            "is_ground": getattr(water, "is_ground", False),
            "terrain_speed": getattr(water, "terrain_speed", DEFAULT_TERRAIN_SPEED),
        }
    water.is_ground = True
    deck_name = bridge_terrain_type(_bridge_subject_type(site))
    water.terrain_speed = (
        resolve_terrain_speed(deck_name)
        if deck_name
        else getattr(water, "terrain_speed", DEFAULT_TERRAIN_SPEED)
    )
    deck_voice = deck_name
    water._scaffold_terrain_voice = deck_voice
    exit_type = _passage_exit_type(water, shore)
    water.ensure_path(shore, exit_type=exit_type)
    for neighbor in water.strict_neighbors:
        if neighbor is not shore:
            water.ensure_nopath(neighbor)


def resync_all_scaffold_passages(world):
    """Re-apply passage rules for every active water scaffold."""
    if world is None:
        return
    for player in getattr(world, "players", ()):
        for unit in getattr(player, "units", ()):
            if is_scaffold_water_build_target(unit):
                _apply_scaffold_passage(unit)


def refresh_scaffold_passage(site):
    """Scaffold: temporary ground on water, single exit to placer's shore only."""
    water = getattr(site, "place", None) if site is not None else None
    world = getattr(water, "world", None) if water is not None else None
    _apply_scaffold_passage(site)
    if world is not None:
        resync_all_scaffold_passages(world)
        invalidate_world_regions(world)
        if hasattr(world, "_create_graphs"):
            world._create_graphs()
        for player in getattr(world, "players", ()):
            for unit in getattr(player, "units", ()):
                if hasattr(unit, "_can_go_cache"):
                    unit._can_go_cache = {}


def clear_scaffold_passage(site):
    """Remove scaffold-only footing and the placer-shore link."""
    if site is None:
        return
    water = getattr(site, "place", None)
    shore = getattr(site, "shore_land", None)
    if water is None:
        return
    if shore is not None:
        water.ensure_nopath(shore)
    saved = getattr(water, "_scaffold_terrain_saved", None)
    if saved is not None:
        water.is_ground = saved["is_ground"]
        if "terrain_speed" in saved:
            water.terrain_speed = saved["terrain_speed"]
        del water._scaffold_terrain_saved
    if getattr(water, "_scaffold_terrain_voice", None):
        del water._scaffold_terrain_voice
    world = getattr(water, "world", None)
    if world is not None:
        invalidate_world_regions(world)
        if hasattr(world, "_create_graphs"):
            world._create_graphs()
        for player in getattr(world, "players", ()):
            for unit in getattr(player, "units", ()):
                if hasattr(unit, "_can_go_cache"):
                    unit._can_go_cache = {}


def _sync_bridge_passages(square):
    """Create/remove neighbor exits according to current terrain passability."""
    if square is None or not hasattr(square, "strict_neighbors"):
        return
    for neighbor in square.strict_neighbors:
        if _bridge_passage_allowed(square, neighbor):
            square.ensure_path(neighbor, exit_type=_passage_exit_type(square, neighbor))
        else:
            square.ensure_nopath(neighbor)


def refresh_bridge_terrain(square):
    """Apply or remove bridge passability from buildings on *square*."""
    if square is None:
        return
    world = getattr(square, "world", None)
    terrain_name = None
    providers = list(_bridge_terrain_providers(getattr(square, "objects", ())))
    if providers:
        terrain_name = providers[0]
    saved = getattr(square, "_bridge_terrain_saved", None)
    if terrain_name:
        from .lib.square_terrain_rules import (
            apply_terrain_map_flags,
            is_terrain_def,
            resolve_terrain_cover,
            resolve_terrain_speed,
        )

        if not is_terrain_def(terrain_name):
            warning("unknown bridge_terrain: %s", terrain_name)
            return
        if saved is None:
            square._bridge_terrain_saved = {
                "is_ground": square.is_ground,
                "is_water": square.is_water,
                "type_name": getattr(square, "type_name", "") or "",
                "terrain_speed": getattr(square, "terrain_speed", None),
                "terrain_cover": getattr(square, "terrain_cover", None),
            }
        apply_terrain_map_flags(square, terrain_name)
        square.terrain_speed = resolve_terrain_speed(terrain_name)
        square.terrain_cover = resolve_terrain_cover(terrain_name)
        square._bridge_terrain_voice = terrain_name
    elif saved is not None:
        square.is_ground = saved["is_ground"]
        square.is_water = saved["is_water"]
        if getattr(square, "fixed_terrain", False):
            square.type_name = saved["type_name"]
        if saved.get("terrain_speed") is not None:
            square.terrain_speed = saved["terrain_speed"]
        if saved.get("terrain_cover") is not None:
            square.terrain_cover = saved["terrain_cover"]
        square._bridge_terrain_voice = None
        del square._bridge_terrain_saved
    if terrain_name or saved is not None:
        _sync_bridge_passages(square)
        if saved is not None and not terrain_name:
            for neighbor in square.strict_neighbors:
                _sync_bridge_passages(neighbor)
        if world is not None:
            invalidate_world_regions(world)
            if hasattr(world, "_create_graphs"):
                world._create_graphs()
            for player in getattr(world, "players", ()):
                for unit in getattr(player, "units", ()):
                    if hasattr(unit, "_can_go_cache"):
                        unit._can_go_cache = {}


def worker_can_place_water_build(worker, water_square):
    """Worker may start a water-only build from the water cell or adjacent land."""
    if worker is None or water_square is None:
        return False
    if worker.place is water_square:
        return True
    if worker.place in water_square.strict_neighbors:
        if is_pure_water_square(water_square) and not is_pure_water_square(
            worker.place
        ):
            return True
    return False


def nearest_reachable_land_for_water_build(worker, water_square, avoid=False):
    """Best adjacent land square the worker can path to for placing a water build."""
    if worker is None or water_square is None or worker.place is None:
        return None
    if worker_can_place_water_build(worker, water_square):
        return worker.place
    best = None
    best_dist = None
    plane = getattr(worker, "airground_type", "ground")
    for neighbor in water_square.strict_neighbors:
        if is_pure_water_square(neighbor):
            continue
        dist = worker.place.shortest_path_distance_to(
            neighbor, player=worker.player, plane=plane, avoid=avoid
        )
        if dist == float("inf"):
            continue
        if best is None or dist < best_dist:
            best = neighbor
            best_dist = dist
    return best


def worker_can_reach_water_build(worker, water_square, avoid=False):
    return (
        nearest_reachable_land_for_water_build(worker, water_square, avoid=avoid)
        is not None
    )


def finalize_new_building(building, site=None):
    register_build_field_provider(building)
    if bridge_terrain_type(building) and building.place is not None:
        refresh_bridge_terrain(building.place)
    host = None
    if site is not None:
        host = getattr(site, "addon_host", None)
    if host is None:
        host = getattr(building, "addon_host", None)
    if host is not None and is_addon_type(building):
        attach_addon(host, building)
    _auto_start_gas_production(building)
    if getattr(building, "type_name", None) == "hatchery":
        fill_hatchery_larva(building, notify=False)


def _auto_start_gas_production(building):
    """Gas refineries (is_gather + auto_production) start producing on completion."""
    if not (
        getattr(building, "is_gather", 0)
        and getattr(building, "auto_production", 0)
        and requires_deposit_type(building)
    ):
        return
    if getattr(building, "is_producing", False):
        return
    building.current_production_mode = "auto"
    try:
        from .worldorders import AutoProduceOrder

        AutoProduceOrder(building, []).immediate_action()
    except Exception:
        pass


def hatchery_larva_cap(hatchery):
    cap = getattr(hatchery, "larva_cap", 0) or getattr(
        rules.unit_class("hatchery"), "larva_cap", 0
    )
    return int(cap) if cap else 3


def hatchery_larva_spawn_interval(hatchery):
    interval = getattr(hatchery, "larva_spawn_time", 0) or getattr(
        rules.unit_class("hatchery"), "larva_spawn_time", 0
    )
    if interval:
        return int(interval)
    from .lib.nofloat import to_int

    return to_int("15")


def count_larva_on_square(hatchery):
    place = getattr(hatchery, "place", None)
    if place is None:
        return 0
    n = 0
    for obj in place.objects:
        if (
            getattr(obj, "type_name", None) == "larva"
            and getattr(obj, "player", None) is hatchery.player
            and obj.hp > 0
        ):
            n += 1
    return n


def spawn_larva_at_hatchery(hatchery, count=1, notify=True):
    larva_cls = rules.unit_class("larva")
    if larva_cls is None or count <= 0:
        return 0
    place = hatchery.place
    spawned = 0
    for _ in range(count):
        if count_larva_on_square(hatchery) >= hatchery_larva_cap(hatchery):
            break
        x, y = hatchery.x, hatchery.y
        found = place.find_free_space("ground", x, y)
        if found[0] is not None:
            x, y = found[0], found[1]
        try:
            u = larva_cls(hatchery.player, place, x, y)
            if notify:
                u.notify("added")
            spawned += 1
        except Exception:
            break
    return spawned


def fill_hatchery_larva(hatchery, notify=True):
    cap = hatchery_larva_cap(hatchery)
    missing = cap - count_larva_on_square(hatchery)
    if missing > 0:
        spawn_larva_at_hatchery(hatchery, missing, notify=notify)


def tick_hatchery_larva(world):
    if world is None:
        return
    for player in world.players:
        if not getattr(player, "is_playing", True):
            continue
        for unit in list(getattr(player, "units", ())):
            if getattr(unit, "type_name", None) != "hatchery" or unit.hp <= 0:
                continue
            if count_larva_on_square(unit) >= hatchery_larva_cap(unit):
                continue
            interval = hatchery_larva_spawn_interval(unit)
            last = getattr(unit, "_larva_spawn_time", None)
            if last is None:
                unit._larva_spawn_time = world.time
                continue
            if world.time - last >= interval:
                if spawn_larva_at_hatchery(unit, 1):
                    unit._larva_spawn_time = world.time


def addon_build_target_coords(host, building_type, place):
    x, y = addon_slot_coords(host)
    if place is None:
        return x, y
    airground_type = getattr(building_type, "airground_type", "ground")
    found = place.find_free_space(airground_type, x, y)
    if found[0] is not None:
        return found
    return x, y
