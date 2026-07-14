"""StarCraft-style build rules: fields, build modes, addons."""
from __future__ import annotations

import types

import pytest

from soundrts.world_build_rules import (
    attach_addon,
    build_field_ok,
    build_field_types_on_square,
    building_sacrifices_worker,
    building_self_constructs,
    can_host_addon,
    detach_addon,
    finalize_new_building,
    has_build_field_at,
    is_addon_type,
    register_build_field_provider,
    requires_build_field_type,
    type_matches,
    unregister_build_field_provider,
    worker_build_mode,
    worker_place_and_leave,
)


def _stub_world():
    return types.SimpleNamespace(
        objects={},
        _build_field_provider_ids=set(),
        _build_field_marked_squares={},
        players=[],
    )


def _stub_unit(world, uid, x, y, player, **attrs):
    unit = types.SimpleNamespace(
        id=uid,
        world=world,
        x=x,
        y=y,
        player=player,
        place=types.SimpleNamespace(world=world),
        is_a_building=True,
        attached_addons=[],
        attached_host=None,
        **attrs,
    )
    world.objects[uid] = unit
    return unit


class _Player:
    def __init__(self, pid=1):
        self.id = pid


def test_requires_and_provides_build_field_parsing():
    nexus = types.SimpleNamespace(
        provides_build_field="psi",
        requires_build_field="0",
        build_field_radius=8 * 1000,
    )
    pool = types.SimpleNamespace(requires_build_field="creep")
    assert requires_build_field_type(nexus) is None
    assert requires_build_field_type(pool) == "creep"


def test_build_field_coverage_and_validation():
    """供能范围按格子 BFS 计算，相邻格在半径 6 内。"""

    from soundrts.world_build_rules import (
        _squares_in_build_field_range,
        build_field_radius_squares,
        has_build_field_on_square,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1, g1 = _Sq(), _Sq(), _Sq()
    s2, s3, s4, s5, s6 = _Sq(), _Sq(), _Sq(), _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1, s2)
    s2.neighbors = (b1, s3)
    s3.neighbors = (s2, s4)
    s4.neighbors = (s3, s5)
    s5.neighbors = (s4, s6)
    s6.neighbors = (s5, g1)
    g1.neighbors = (s6,)

    covered = _squares_in_build_field_range(a1, 6)
    assert b1 in covered
    # a1 到 g1 链上 7 跳，半径 6 刚好够不到 g1
    assert g1 not in covered
    assert g1 in _squares_in_build_field_range(a1, 7)

    pylon_type = types.SimpleNamespace(build_field_radius=6 * 1000)
    assert build_field_radius_squares(pylon_type) == 6

    world = _stub_world()
    player = _Player()
    pylon = _stub_unit(
        world,
        1,
        0,
        0,
        player,
        provides_build_field="psi",
        build_field_radius=6 * 1000,
        type_name="pylon",
    )
    pylon.place = a1
    register_build_field_provider(pylon)
    assert has_build_field_on_square(world, b1, player, "psi")
    assert not has_build_field_on_square(world, g1, player, "psi")

    world.grid = {}
    world.get_place_from_xy = lambda x, y: b1
    gateway = types.SimpleNamespace(requires_build_field="psi")
    assert build_field_ok(player, world, 0, 0, gateway)

    unregister_build_field_provider(pylon)
    assert not has_build_field_on_square(world, b1, player, "psi")


def test_meter_build_field_radius():
    """build_field_radius_m 按米（与射程同尺度）判定供能距离。"""

    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_build_rules import (
        build_field_radius_meters,
        build_field_ok,
        has_build_field_on_square,
        register_build_field_provider,
        unregister_build_field_provider,
    )

    class _Sq:
        def __init__(self, x, y, neighbors=()):
            self.x = x
            self.y = y
            self.neighbors = neighbors

    a1 = _Sq(0, 0)
    b1 = _Sq(12 * PRECISION, 0)
    c1 = _Sq(24 * PRECISION, 0)
    world = _stub_world()
    a1.world = world
    b1.world = world
    c1.world = world
    player = _Player()
    pylon = _stub_unit(
        world,
        1,
        0,
        0,
        player,
        provides_build_field="psi",
        build_field_radius_m=12 * PRECISION,
        type_name="pylon",
    )
    pylon.place = a1
    register_build_field_provider(pylon)
    assert build_field_radius_meters(pylon) == 12 * PRECISION
    assert has_build_field_on_square(world, a1, player, "psi")
    assert has_build_field_on_square(world, b1, player, "psi")
    assert not has_build_field_on_square(world, c1, player, "psi")

    gateway = types.SimpleNamespace(requires_build_field="psi")
    world.get_place_from_xy = lambda x, y: b1
    assert build_field_ok(player, b1, 12 * PRECISION, 0, gateway)
    assert not build_field_ok(player, c1, 24 * PRECISION, 0, gateway)

    unregister_build_field_provider(pylon)
    pylon_small = _stub_unit(
        world,
        2,
        0,
        0,
        player,
        provides_build_field="psi",
        build_field_radius_m=int(0.5 * PRECISION),
        type_name="pylon",
    )
    pylon_small.place = a1
    register_build_field_provider(pylon_small)
    assert build_field_ok(player, a1, 400, 0, gateway)
    assert not build_field_ok(player, a1, 600, 0, gateway)


def test_creep_persists_and_requires_square_mark():
    from soundrts.world_build_rules import (
        build_field_ok,
        cleanup_build_rules_on_death,
        has_live_build_field_on_square,
        has_marked_build_field_on_square,
        register_build_field_provider,
        unregister_build_field_provider,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1 = _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1,)
    world = _stub_world()
    a1.world = world
    b1.world = world
    player = _Player()
    hatchery = types.SimpleNamespace(
        id=1,
        type_name="hatchery",
        provides_build_field="creep",
        build_field_radius=6,
        build_field_persists=1,
        build_field_spreads=0,
        requires_build_field="0",
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
    )
    world.objects[1] = hatchery
    register_build_field_provider(hatchery)
    assert has_marked_build_field_on_square(world, b1, player, "creep")
    pool = types.SimpleNamespace(
        requires_build_field="creep",
        requires_build_field_on_square=1,
    )
    assert build_field_ok(player, b1, 0, 0, pool)
    cleanup_build_rules_on_death(hatchery)
    assert not has_live_build_field_on_square(world, b1, player, "creep")
    assert has_marked_build_field_on_square(world, b1, player, "creep")
    assert build_field_ok(player, b1, 0, 0, pool)


def test_build_field_types_on_square_merges_live_and_marks():
    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1 = _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1,)
    world = _stub_world()
    a1.world = world
    b1.world = world
    player = _Player()
    pylon = _stub_unit(
        world,
        3,
        0,
        0,
        player,
        provides_build_field="psi",
        build_field_radius=6,
        type_name="pylon",
    )
    pylon.place = a1
    register_build_field_provider(pylon)
    from soundrts.world_build_rules import mark_build_field_squares

    mark_build_field_squares(world, player, "creep", {b1})
    assert build_field_types_on_square(world, a1, player) == ["psi"]
    assert build_field_types_on_square(world, b1, player) == ["creep", "psi"]
    unregister_build_field_provider(pylon)
    assert build_field_types_on_square(world, b1, player) == ["creep"]


def test_psi_requires_live_provider_not_marks():
    from soundrts.world_build_rules import (
        build_field_ok,
        has_marked_build_field_on_square,
        mark_build_field_squares,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1 = _Sq(), _Sq()
    world = _stub_world()
    b1.world = world
    player = _Player()
    mark_build_field_squares(world, player, "psi", {b1})
    assert has_marked_build_field_on_square(world, b1, player, "psi")
    gateway = types.SimpleNamespace(requires_build_field="psi")
    assert not build_field_ok(player, b1, 0, 0, gateway)


def test_summon_creep_tumor_requires_creep():
    from soundrts.worldskill import Skill
    from soundrts.world_build_rules import mark_build_field_squares

    class _Sq:
        def __init__(self, x, y, neighbors=()):
            self.x = x
            self.y = y
            self.neighbors = neighbors
            self.world = None

    b1 = _Sq(12000, 0)
    c1 = _Sq(24000, 0)
    world = _stub_world()
    b1.world = world
    c1.world = world
    player = _Player()
    mark_build_field_squares(world, player, "creep", {b1})
    queen = types.SimpleNamespace(player=player, world=world, x=0, y=0)
    skill = types.SimpleNamespace(
        summon_requires_build_field="creep",
        summon_requires_marked_field=0,
    )
    _validate = Skill.validate_summon_target.__func__
    ok_b, _ = _validate(skill, queen, b1)
    ok_c, reason_c = _validate(skill, queen, c1)
    assert ok_b
    assert not ok_c
    assert reason_c == "missing_build_field.creep"


def test_extend_creep_tumor_requires_marked_not_live_only():
    """肿瘤延伸必须在已标记菌毯格上；仅有主巢实时范围、无标记的格不可用。"""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldskill import Skill
    from soundrts.world_build_rules import (
        has_build_field_on_square,
        has_marked_build_field_on_square,
        mark_build_field_squares,
        register_build_field_provider,
    )

    class _Sq:
        def __init__(self, x, y, neighbors=()):
            self.x = x
            self.y = y
            self.neighbors = neighbors
            self.world = None

    a1 = _Sq(0, 0)
    b1 = _Sq(12000, 0)
    c1 = _Sq(24000, 0)
    a1.neighbors = (b1,)
    b1.neighbors = (a1, c1)
    c1.neighbors = (b1,)
    world = _stub_world()
    for sq in (a1, b1, c1):
        sq.world = world
    player = _Player()
    hatchery = types.SimpleNamespace(
        id=1,
        type_name="hatchery",
        provides_build_field="creep",
        build_field_radius=0,
        build_field_radius_m=36 * PRECISION,
        build_field_persists=0,
        build_field_spreads=0,
        requires_build_field="0",
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
        x=0,
        y=0,
    )
    world.objects[1] = hatchery
    register_build_field_provider(hatchery)
    mark_build_field_squares(world, player, "creep", {b1})
    queen = types.SimpleNamespace(player=player, world=world, x=0, y=0)
    assert has_build_field_on_square(world, c1, player, "creep")
    assert not has_marked_build_field_on_square(world, c1, player, "creep")
    assert has_marked_build_field_on_square(world, b1, player, "creep")
    _validate = Skill.validate_summon_target.__func__
    spawn = types.SimpleNamespace(
        summon_requires_build_field="creep",
        summon_requires_marked_field=0,
    )
    extend = types.SimpleNamespace(
        summon_requires_build_field="creep",
        summon_requires_marked_field=1,
    )
    ok_spawn_c, _ = _validate(spawn, queen, c1)
    ok_extend_c, reason_c = _validate(extend, queen, c1)
    ok_extend_b, _ = _validate(extend, queen, b1)
    assert ok_spawn_c
    assert not ok_extend_c
    assert reason_c == "missing_build_field.creep"
    assert ok_extend_b


def test_hatchery_meter_radius_paints_creep_marks():
    """主巢仅写 build_field_radius_m 时也应铺设菌毯格标记（供 zerg 建造判定）。"""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_build_rules import (
        build_field_ok,
        has_marked_build_field_on_square,
        register_build_field_provider,
    )

    class _Sq:
        def __init__(self, x, y, neighbors=()):
            self.x = x
            self.y = y
            self.neighbors = neighbors

    a1 = _Sq(0, 0)
    b1 = _Sq(12000, 0)
    a1.neighbors = (b1,)
    b1.neighbors = (a1,)
    world = _stub_world()
    a1.world = world
    b1.world = world
    player = _Player()
    hatchery = types.SimpleNamespace(
        id=1,
        type_name="hatchery",
        provides_build_field="creep",
        build_field_radius=0,
        build_field_radius_m=12 * PRECISION,
        build_field_persists=1,
        build_field_spreads=0,
        requires_build_field="0",
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
        x=0,
        y=0,
    )
    world.objects[1] = hatchery
    register_build_field_provider(hatchery)
    assert has_marked_build_field_on_square(world, a1, player, "creep")
    assert has_marked_build_field_on_square(world, b1, player, "creep")
    spire = types.SimpleNamespace(
        requires_build_field="creep",
        requires_build_field_on_square=1,
    )
    assert build_field_ok(player, b1, b1.x, b1.y, spire)


def test_creep_spread_tick():
    from soundrts.world_build_rules import (
        has_marked_build_field_on_square,
        register_build_field_provider,
        tick_build_fields,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1, c1 = _Sq(), _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1, c1)
    c1.neighbors = (b1,)
    world = _stub_world()
    player = _Player()
    world.players = [player]
    hatchery = types.SimpleNamespace(
        id=2,
        type_name="hatchery",
        provides_build_field="creep",
        build_field_radius=1,
        build_field_persists=1,
        build_field_spreads=1,
        requires_build_field="0",
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
    )
    world.objects[2] = hatchery
    register_build_field_provider(hatchery)
    assert has_marked_build_field_on_square(world, a1, player, "creep")
    assert not has_marked_build_field_on_square(world, c1, player, "creep")
    tick_build_fields(world)
    assert has_marked_build_field_on_square(world, b1, player, "creep")
    tick_build_fields(world)
    assert has_marked_build_field_on_square(world, c1, player, "creep")


def test_creep_spread_squares_custom_rate():
    from soundrts.world_build_rules import (
        build_field_spread_squares,
        has_marked_build_field_on_square,
        register_build_field_provider,
        tick_build_fields,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1, c1 = _Sq(), _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1, c1)
    c1.neighbors = (b1,)
    world = _stub_world()
    player = _Player()
    world.players = [player]
    hatchery = types.SimpleNamespace(
        id=5,
        type_name="hatchery",
        provides_build_field="creep",
        build_field_radius=1,
        build_field_persists=1,
        build_field_spreads=1,
        build_field_spread_squares=2,
        requires_build_field="0",
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
    )
    assert build_field_spread_squares(hatchery) == 2
    world.objects[5] = hatchery
    register_build_field_provider(hatchery)
    tick_build_fields(world)
    assert has_marked_build_field_on_square(world, c1, player, "creep")


def test_pylon_unpowered_when_isolated():
    from soundrts.world_build_rules import (
        building_is_powered,
        register_build_field_provider,
    )

    class _Sq:
        def __init__(self, neighbors=()):
            self.neighbors = neighbors

    a1, b1 = _Sq(), _Sq()
    a1.neighbors = (b1,)
    b1.neighbors = (a1,)
    world = _stub_world()
    player = _Player()
    pylon = types.SimpleNamespace(
        id=3,
        type_name="pylon",
        provides_build_field="psi",
        requires_build_field="psi",
        build_field_radius=6,
        build_field_persists=0,
        build_field_spreads=0,
        loses_power_without_field=1,
        player=player,
        place=b1,
        world=world,
        is_a_building=True,
        x=0,
        y=0,
    )
    world.objects[3] = pylon
    assert not building_is_powered(pylon)
    nexus = types.SimpleNamespace(
        id=4,
        type_name="nexus",
        provides_build_field="psi",
        requires_build_field="0",
        build_field_radius=8,
        build_field_persists=0,
        build_field_spreads=0,
        loses_power_without_field=0,
        player=player,
        place=a1,
        world=world,
        is_a_building=True,
        x=0,
        y=0,
    )
    world.objects[4] = nexus
    register_build_field_provider(nexus)
    assert building_is_powered(pylon)


def test_worker_build_modes():
    probe_type = types.SimpleNamespace(self_constructs=0, build_sacrifices_worker=0)
    probe = types.SimpleNamespace(build_mode="place_and_leave")
    drone_type = types.SimpleNamespace(self_constructs=0, build_sacrifices_worker=1)
    drone = types.SimpleNamespace(build_mode="sacrifice")
    scv = types.SimpleNamespace(build_mode="assisted")

    assert worker_build_mode(probe) == "place_and_leave"
    assert worker_place_and_leave(probe, probe_type)
    assert not building_sacrifices_worker(probe_type, probe)

    assert building_sacrifices_worker(drone_type, drone)
    assert worker_place_and_leave(drone, drone_type)

    assert not worker_place_and_leave(scv, probe_type)
    assert building_self_constructs(types.SimpleNamespace(self_constructs=1))


def test_landing_coords_align_only_when_flying_near_addon():
    from soundrts.world_build_rules import (
        DEFAULT_ADDON_OFFSET_X,
        landing_coords_for_ground_building,
    )

    class _P:
        id = 1

    player = _P()
    place = types.SimpleNamespace()

    class _Meadow:
        def __init__(self, x, y, mid):
            self.x, self.y, self.id = x, y, mid
            self.deleted = False

        def delete(self):
            self.deleted = True

    meadow_a = _Meadow(1000, 2000, "ma")
    meadow_b = _Meadow(8000, 2000, "mb")
    place.objects = [meadow_a, meadow_b]

    def find_meadow_near_xy(x, y):
        meadows = sorted(
            place.objects,
            key=lambda m: (abs(m.x - x) + abs(m.y - y), m.id),
        )
        return meadows[0] if meadows else None

    place.find_meadow_near_xy = find_meadow_near_xy
    place.find_nearest_meadow = lambda u: find_meadow_near_xy(u.x, u.y)

    factory_type = types.SimpleNamespace(
        type_name="factory",
        can_have_addon=("tech_lab",),
        addon_offset_x=0,
        is_a=(),
    )
    tech_type = types.SimpleNamespace(
        type_name="tech_lab",
        is_addon=1,
        addon_host_types=("factory",),
        is_a=(),
    )
    lab_x = 1000 + DEFAULT_ADDON_OFFSET_X
    addon = types.SimpleNamespace(
        type_name="tech_lab",
        type=tech_type,
        place=place,
        x=lab_x,
        y=2000,
        hp=100,
        attached_host=None,
    )
    player.units = [addon]

    far_flying = types.SimpleNamespace(
        type_name="flying_factory",
        x=8000,
        y=9000,
        player=player,
    )
    x, y, meadow = landing_coords_for_ground_building(
        place, far_flying, factory_type
    )
    assert meadow is meadow_b
    assert x == 8000
    assert y == 9000

    near_flying = types.SimpleNamespace(
        type_name="flying_factory",
        x=1000,
        y=2000,
        player=player,
    )
    x, y, meadow = landing_coords_for_ground_building(
        place, near_flying, factory_type
    )
    assert meadow is meadow_a
    assert x == 1000
    assert y == 2000

    # 同格有孤立附件且在吸附范围内，但飞行单位已 go 到另一块草地 → 落脚下草地
    at_factory_meadow = types.SimpleNamespace(
        type_name="flying_factory",
        x=8000,
        y=2000,
        player=player,
    )
    x, y, meadow = landing_coords_for_ground_building(
        place, at_factory_meadow, factory_type
    )
    assert meadow is meadow_b
    assert x == 8000
    assert y == 2000

    # 贴近科技实验室本体但远离插槽 → 不吸附，落当前位置
    near_lab_not_slot = types.SimpleNamespace(
        type_name="flying_factory",
        x=lab_x,
        y=2000,
        player=player,
    )
    x, y, meadow = landing_coords_for_ground_building(
        place, near_lab_not_slot, factory_type
    )
    assert meadow is meadow_a
    assert x == lab_x
    assert y == 2000


def test_reattach_requires_slot_alignment():
    from soundrts.world_build_rules import (
        DEFAULT_ADDON_OFFSET_X,
        effective_can_train,
        try_reattach_orphan_addons,
    )

    class _P:
        id = 1

    player = _P()
    place = types.SimpleNamespace()

    def _bind_move(obj):
        def move_to(p, x, y, o=90):
            obj.place = p
            obj.x = x
            obj.y = y
        return move_to

    factory_type = types.SimpleNamespace(
        type_name="factory",
        can_have_addon=("tech_lab",),
        addon_max=1,
        can_train=("hellion",),
        addon_offset_x=0,
        is_a=(),
    )
    tech_type = types.SimpleNamespace(
        type_name="tech_lab",
        is_addon=1,
        addon_host_types=("factory",),
        addon_grants_train_factory=("tank",),
        is_a=(),
    )
    lab_x = 1000 + DEFAULT_ADDON_OFFSET_X
    addon = types.SimpleNamespace(
        type_name="tech_lab",
        type=tech_type,
        is_a_building=True,
        player=player,
        place=place,
        x=lab_x,
        y=2000,
        hp=100,
        attached_host=None,
    )
    addon.move_to = _bind_move(addon)
    factory = types.SimpleNamespace(
        type_name="factory",
        type=factory_type,
        is_a_building=True,
        airground_type="ground",
        player=player,
        place=place,
        x=8000,
        y=2000,
        hp=100,
        attached_addons=[],
        notify=lambda *a, **k: None,
    )
    factory.move_to = _bind_move(factory)
    player.units = [factory, addon]

    try_reattach_orphan_addons(factory)
    assert factory.x == 8000
    assert addon.attached_host is None
    assert "tank" not in effective_can_train(factory)


def test_detach_and_reattach_orphan_addon():
    from soundrts.world_build_rules import (
        addon_slot_coords,
        attach_addon,
        detach_addons_for_lift,
        effective_can_train,
        try_reattach_orphan_addons,
    )

    class _P:
        id = 1

    player = _P()
    place = types.SimpleNamespace(world=None)

    def _bind_move(obj):
        def move_to(p, x, y, o=90):
            obj.place = p
            obj.x = x
            obj.y = y
        return move_to

    barracks_type = types.SimpleNamespace(
        type_name="barracks",
        can_have_addon=("tech_lab",),
        addon_max=1,
        can_train=("marine",),
        addon_offset_x=0,
    )
    tech_type = types.SimpleNamespace(
        type_name="tech_lab",
        is_addon=1,
        addon_host_types=("barracks", "factory"),
        addon_grants_train_barracks=("marauder",),
        addon_grants_train_factory=("tank",),
        is_a=(),
    )
    factory_type = types.SimpleNamespace(
        type_name="factory",
        can_have_addon=("tech_lab",),
        addon_max=1,
        can_train=("hellion",),
        addon_offset_x=0,
    )
    barracks = types.SimpleNamespace(
        type_name="barracks",
        type=barracks_type,
        is_a_building=True,
        airground_type="ground",
        player=player,
        place=place,
        x=1000,
        y=2000,
        hp=100,
        attached_addons=[],
    )
    barracks.move_to = _bind_move(barracks)
    addon = types.SimpleNamespace(
        type_name="tech_lab",
        type=tech_type,
        is_a_building=True,
        player=player,
        place=place,
        x=0,
        y=0,
        hp=100,
        attached_host=None,
    )
    addon.move_to = _bind_move(addon)
    attach_addon(barracks, addon)
    player.units = [barracks, addon]

    detached = detach_addons_for_lift(barracks)
    assert len(detached) == 1
    assert addon.attached_host is None
    assert addon not in barracks.attached_addons

    factory = types.SimpleNamespace(
        type_name="factory",
        type=factory_type,
        is_a_building=True,
        airground_type="ground",
        player=player,
        place=place,
        x=3000,
        y=2000,
        hp=100,
        attached_addons=[],
    )
    factory.move_to = _bind_move(factory)
    player.units.append(factory)
    ax, ay = addon_slot_coords(factory)
    addon.x, addon.y = ax, ay

    try_reattach_orphan_addons(factory)
    assert addon.attached_host is factory
    assert addon in factory.attached_addons
    assert "hellion" in effective_can_train(factory)
    assert "tank" in effective_can_train(factory)


def test_reactor_doubles_train_count():
    from soundrts.world_build_rules import attach_addon, effective_can_train

    class _P:
        id = 1

    player = _P()
    place = types.SimpleNamespace()
    barracks_type = types.SimpleNamespace(
        type_name="barracks",
        can_have_addon=("reactor",),
        addon_max=1,
        can_train=("marine",),
        addon_offset_x=0,
    )
    reactor_type = types.SimpleNamespace(
        type_name="reactor",
        is_addon=1,
        addon_host_types=("barracks",),
        addon_train_multiplier=2,
        is_a=(),
    )
    barracks = types.SimpleNamespace(
        type_name="barracks",
        type=barracks_type,
        is_a_building=True,
        airground_type="ground",
        player=player,
        place=place,
        x=0,
        y=0,
        hp=100,
        attached_addons=[],
        move_to=lambda *a, **k: None,
    )
    reactor = types.SimpleNamespace(
        type_name="reactor",
        type=reactor_type,
        is_a_building=True,
        player=player,
        place=place,
        x=0,
        y=0,
        hp=100,
        attached_host=None,
        move_to=lambda *a, **k: None,
    )
    attach_addon(barracks, reactor)
    assert effective_can_train(barracks) == {"marine": 2}


def test_addon_host_and_attachment():
    barracks = types.SimpleNamespace(
        is_a_building=True,
        type_name="barracks",
        player=_Player(),
        attached_addons=[],
        can_have_addon=("tech_lab", "reactor"),
        addon_max=1,
        place=types.SimpleNamespace(),
        x=1000,
        y=2000,
        move_to=lambda *a, **k: None,
    )
    tech_lab = types.SimpleNamespace(
        is_addon=1,
        type_name="tech_lab",
        addon_host_types=("barracks", "factory"),
        is_a=(),
    )
    assert is_addon_type(tech_lab)
    assert can_host_addon(barracks, tech_lab)

    site = types.SimpleNamespace(addon_host=barracks)
    building = types.SimpleNamespace(
        type_name="tech_lab",
        is_addon=1,
        attached_host=None,
        provides_build_field="",
        build_field_radius=0,
        world=_stub_world(),
        id=99,
        player=barracks.player,
        x=0,
        y=0,
        place=barracks.place,
        move_to=lambda *a, **k: None,
    )
    finalize_new_building(building, site)
    assert building.attached_host is barracks
    assert building in barracks.attached_addons

    addon = types.SimpleNamespace(
        type_name="tech_lab", attached_host=None, place=barracks.place
    )
    attach_addon(barracks, addon)
    assert addon in barracks.attached_addons
    detach_addon(barracks, addon)
    assert addon not in barracks.attached_addons
    assert addon.attached_host is None


def test_type_matches_is_a_chain():
    cls = types.SimpleNamespace(type_name="gateway", is_a=("protoss_building", "sc_building"))
    rules_mod = types.SimpleNamespace(
        unit_class=lambda name: {
            "gateway": cls,
            "protoss_building": types.SimpleNamespace(is_a=("sc_building",)),
            "sc_building": types.SimpleNamespace(is_a=()),
        }.get(name)
    )
    import soundrts.world_build_rules as br

    old = br.rules
    br.rules = rules_mod
    try:
        assert type_matches(cls, ("protoss_building",))
        assert type_matches(cls, ("sc_building",))
    finally:
        br.rules = old


def test_starcraft_mod_rules_parse():
    from pathlib import Path

    from soundrts.definitions import Rules, _get_base_classes

    text = Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(text, base_classes=_get_base_classes())
    probe = r.unit_class("probe")
    drone = r.unit_class("drone")
    pylon = r.unit_class("pylon")
    tech_lab = r.unit_class("tech_lab")
    reactor = r.unit_class("reactor")
    barracks = r.unit_class("barracks")
    gateway = r.unit_class("gateway")
    photon_cannon = r.unit_class("photon_cannon")
    protoss_building = r.unit_class("protoss_building")
    zerg_building = r.unit_class("zerg_building")
    assert probe.build_mode == "place_and_leave"
    assert drone.build_mode == "sacrifice"
    assert pylon.self_constructs == 1
    assert protoss_building.self_constructs == 1
    assert gateway.self_constructs == 1
    assert photon_cannon.self_constructs == 1
    assert tech_lab.is_addon == 1
    assert "barracks" in tech_lab.addon_host_types
    flying_barracks = r.unit_class("flying_barracks")
    assert flying_barracks.ground_form == "barracks"
    assert "flying_barracks" in barracks.can_change_to
    assert reactor.addon_train_multiplier == 2
    assert "marauder" in tech_lab.addon_grants_train_barracks
    assert "tank" in tech_lab.addon_grants_train_factory
    assert protoss_building.is_buildable_anywhere
    assert protoss_building.loses_power_without_field
    assert zerg_building.is_buildable_anywhere
    assert zerg_building.requires_build_field_on_square
    hatchery = r.unit_class("hatchery")
    assert hatchery.build_field_persists
    assert hatchery.build_field_spreads
    creep_tumor = r.unit_class("creep_tumor")
    assert creep_tumor.provides_build_field == "creep"
    assert creep_tumor.build_field_spreads
    queen = r.unit_class("queen")
    assert "sc_spawn_creep_tumor" in queen.can_use_skill
    sc_tumor = r.unit_class("sc_spawn_creep_tumor")
    assert sc_tumor.summon_requires_build_field == "creep"
    sc_extend = r.unit_class("sc_extend_creep_tumor")
    assert sc_extend.summon_requires_marked_field == 1
    assimilator = r.unit_class("assimilator")
    extractor = r.unit_class("extractor")
    refinery = r.unit_class("refinery")
    assert assimilator.requires_deposit == "geyser"
    assert extractor.requires_deposit == "geyser"
    assert refinery.requires_deposit == "geyser"
    assert assimilator.self_constructs == 1
    assert extractor.self_constructs == 1
    assert assimilator.is_buildable_anywhere == 0
    assert extractor.is_buildable_anywhere == 0
    assert refinery.is_buildable_anywhere == 0
    assert "protoss_building" in assimilator.is_a
    assert "sc_gas_building" in assimilator.is_a
    assert assimilator.is_gather == 1
    assert assimilator.auto_production == 1
    assert assimilator.auto_cultivate == 0
    assert "mineral_field" in probe.can_gather_deposit
    assert "assimilator" in probe.can_gather_building
    assert "geyser" not in probe.can_gather_deposit
    assert "geyser" not in probe.can_gather_building
    nb_res = r.get("parameters", "nb_of_resource_types", 0)
    assert str(nb_res) == "2"
    dragoon = r.unit_class("dragoon")
    cyber = r.unit_class("cybernetics_core")
    roach = r.unit_class("roach")
    roach_warren = r.unit_class("roach_warren")
    engineering_bay = r.unit_class("engineering_bay")
    assert "cybernetics_core" in r.get("dragoon", "requirements", ())
    assert "dragoon" in r.class_can_train(gateway)
    assert "observer" in r.class_can_train(r.unit_class("stargate"))
    # 异虫 roach 由幼虫变形产出（larva morph_as_train），并以 roach_warren 为前置，
    # 而非由 roach_warren 直接训练。
    assert "roach" in r.unit_class("larva").can_upgrade_to
    assert "roach_warren" in r.get("roach", "requirements", ())
    assert "spawning_pool" in r.get("roach_warren", "requirements", ())
    assert int(r.get("roach", "cost", (0, 0))[1]) > 0
    assert "infantry_weapons" in r.get("engineering_bay", "can_research", ())
    assert "infantry_weapons" not in tech_lab.addon_grants_research
    assert "infantry_weapons" in r.get("infantry_weapons_2", "requirements", ())
    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_build_rules import (
        build_field_radius_meters,
        build_field_radius_squares,
    )

    nexus = r.unit_class("nexus")
    pylon = r.unit_class("pylon")
    hatchery = r.unit_class("hatchery")
    assert build_field_radius_meters(nexus) == 18 * PRECISION
    assert build_field_radius_meters(pylon) == 12 * PRECISION
    assert build_field_radius_squares(nexus) == 0
    assert build_field_radius_squares(hatchery) == 0
    assert build_field_radius_meters(hatchery) == 12 * PRECISION


def test_has_resources_trigger():
    from soundrts.lib.nofloat import to_int
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Player(TriggersMixin):
        def __init__(self):
            self.resources = [0, 0]

    player = _Player()
    player.resources[1] = to_int("8")
    assert player.lang_has_resources(["resource2", "8"])
    assert player.lang_has_resources(["8", "resource2"])
    assert not player.lang_has_resources(["resource2", "9"])


def test_has_gathered_trigger_excludes_starting_resources():
    from soundrts.lib.nofloat import to_int
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Stats:
        def __init__(self, starting):
            self._starting = list(starting)

        def _starting_resources(self):
            return list(self._starting)

        def get(self, event, index):
            assert event == "gathered"
            return self._gathered[index]

        def add_gathered(self, index, qty):
            self._gathered[index] += qty

    class _Player(TriggersMixin):
        def __init__(self, starting):
            self.resources = list(starting)
            self.stats = _Stats(starting)
            self.stats._gathered = list(starting)

    player = _Player([to_int("200"), 0])
    player.stats.add_gathered(0, to_int("500"))
    assert player.lang_has_gathered(["resource1", "500"])
    assert not player.lang_has_gathered(["resource1", "501"])
    assert player.lang_has_gathered(["500", "resource1"])
    player.resources[0] = to_int("50")
    assert player.lang_has_gathered(["resource1", "500"])


def test_rmg_all_ruins_discovered_by_allies():
    from soundrts.worldplayerbase.triggers import TriggersMixin

    world = type("W", (), {"_map_flags": set()})()

    class _Player(TriggersMixin):
        def __init__(self, pid):
            self.id = pid
            self.allied = []
            self.world = world

        @property
        def allied_victory(self):
            return self.allied

    p1 = _Player("p1")
    p2 = _Player("p2")
    p1.allied = [p1, p2]
    p2.allied = [p1, p2]
    assert not p1.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0"])
    p1.lang_rmg_mark_ruin_discovered(["rmg_ruin_0"])
    assert p1.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0"])
    assert not p1.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0", "rmg_ruin_1"])
    p2.lang_rmg_mark_ruin_discovered(["rmg_ruin_1"])
    assert p1.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0", "rmg_ruin_1"])

    solo = _Player("solo")
    solo.allied = [solo]
    solo.lang_rmg_mark_ruin_discovered(["rmg_ruin_0"])
    assert solo.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0"])
    assert not solo.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0", "rmg_ruin_1"])


def test_rmg_enemy_discovered_ruin_still_counts_for_player():
    """Enemy first visit must not block the human player's victory credit."""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    world = type("W", (), {"_map_flags": set()})()

    class _Player(TriggersMixin):
        def __init__(self, pid):
            self.id = pid
            self.allied = []
            self.world = world

        @property
        def allied_victory(self):
            return self.allied

    human = _Player("human")
    enemy = _Player("enemy_ai")
    human.allied = [human]

    enemy.lang_rmg_mark_ruin_discovered(["rmg_ruin_0"])
    assert not human.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0"])

    human.lang_rmg_mark_ruin_discovered(["rmg_ruin_0"])
    assert human.lang_rmg_all_ruins_discovered_by_allies(["rmg_ruin_0"])
    assert human.lang_rmg_ruin_discovered_by_self(["rmg_ruin_0"])


def test_rmg_announce_ruins_remaining():
    from soundrts.worldplayerbase.triggers import TriggersMixin

    world = type("W", (), {"_map_flags": set()})()
    sequences = []

    class _Player(TriggersMixin):
        def __init__(self, pid):
            self.id = pid
            self.allied = []
            self.world = world

        @property
        def allied_victory(self):
            return self.allied

        def push(self, cmd, payload):
            if cmd == "sequence":
                sequences.append(list(payload))

    player = _Player("p1")
    player.allied = [player]
    player.lang_rmg_announce_ruins_remaining(["rmg_ruin_0", "rmg_ruin_1", "rmg_ruin_2"])
    assert sequences == [[5492, 1000003, 5431]]

    sequences.clear()
    player.lang_rmg_mark_ruin_discovered(["rmg_ruin_0"])
    player.lang_rmg_announce_ruins_remaining(["rmg_ruin_0", "rmg_ruin_1", "rmg_ruin_2"])
    assert sequences == [[5492, 1000002, 5431]]

    sequences.clear()
    player.lang_rmg_mark_ruin_discovered(["rmg_ruin_1"])
    player.lang_rmg_announce_ruins_remaining(["rmg_ruin_0", "rmg_ruin_1", "rmg_ruin_2"])
    assert sequences == [[5493]]

    sequences.clear()
    player.lang_rmg_mark_ruin_discovered(["rmg_ruin_2"])
    player.lang_rmg_announce_ruins_remaining(["rmg_ruin_0", "rmg_ruin_1", "rmg_ruin_2"])
    assert sequences == []


def test_requires_deposit_build_helpers():
    from soundrts.world_build_rules import (
        deposit_build_target_ok,
        deposit_on_square,
        requires_deposit_type,
    )
    from soundrts.worldresource import Deposit

    building = types.SimpleNamespace(requires_deposit="geyser")
    assert requires_deposit_type(building) == "geyser"
    square = types.SimpleNamespace(objects=[])
    geyser = types.SimpleNamespace(
        type_name="geyser",
        place=square,
        x=1000,
        y=2000,
    )
    square.objects = [geyser]
    player = types.SimpleNamespace()
    import soundrts.world_build_rules as br

    old_build = br.build_field_ok
    old_rules = br.rules
    br.build_field_ok = lambda *args, **kwargs: True
    br.rules = types.SimpleNamespace(
        get=lambda name, key, default=None: ["deposit"] if key == "class" else default
    )
    try:
        assert deposit_on_square(square, "geyser") is geyser
        assert deposit_on_square(square, "mineral_field") is None
        assert deposit_build_target_ok(player, geyser, building)
        wrong = types.SimpleNamespace(type_name="mineral_field", place=square, x=0, y=0)
        assert not deposit_build_target_ok(player, wrong, building)
    finally:
        br.build_field_ok = old_build
        br.rules = old_rules


def test_starcraft_mod_maps_and_ui_load():
    from pathlib import Path

    from soundrts.definitions import Style
    from soundrts.mapfile import Map

    root = Path("mods/starcraft")
    for name in (
        "multi/protoss_psi_test.txt",
        "multi/zerg_creep_test.txt",
        "multi/terran_addon_test.txt",
        "multi/terran_recombine_test.txt",
        "multi/sc_resources_test.txt",
        "multi/sc_tech_test.txt",
        "single/sc_campaign/1.txt",
        "single/sc_campaign/2.txt",
        "single/sc_campaign/3.txt",
        "single/sc_campaign/4.txt",
        "single/sc_campaign/6.txt",
        "single/sc_campaign/8.txt",
    ):
        path = root / name
        m = Map.loads(path.read_text(encoding="utf-8").encode("utf-8"), path.name)
        assert m.definition
        assert "starting_units" in m.definition
        assert "trigger player1" in m.definition

    psi_map = (root / "multi/protoss_psi_test.txt").read_text(encoding="utf-8")
    assert "(has 4 pylon)" in psi_map
    assert "(has_entered f1 gateway)" in psi_map

    base_style = Path("res/ui/style.txt").read_text(encoding="utf-8")
    mod_style = (root / "ui/style.txt").read_text(encoding="utf-8")
    style = Style()
    style.load(base_style + "\n" + mod_style)
    assert style.get("nexus", "title") == ["7210"]
    assert style.get("probe", "title") == ["7215"]
    assert style.get("tech_lab", "title") == ["7234"]
    # 分层热键方案把 "building" 槽细分为 building1..building16
    assert style.get("nexus", "keyboard") == ["building1"]
    assert style.get("probe", "keyboard") == ["worker"]
    assert "building" in style.get("barracks", "is_a")
    # 旧版 is_a barracks 会无限递归，导致 W/E 等热键全部失效
    kb_building = [
        x
        for x in style.classnames()
        if style.has(x, "keyboard")
        and style.get(x, "keyboard")[0].startswith("building")
    ]
    assert "nexus" in kb_building
    assert "pylon" in kb_building

    tts = (root / "ui/tts.txt").read_text(encoding="utf-8")
    assert "7210 Nexus" in tts
    # 派系名 Protoss 现为 7261（7310 已改作 Vehicle Armor level 1）
    assert "7261 Protoss" in tts
    zh = (root / "ui-zh/tts.txt").read_text(encoding="utf-8")
    assert "7210 主基地" in zh
    assert "7240 灵能场" in zh
    assert "7241 菌毯" in zh
    mod_style = (root / "ui/style.txt").read_text(encoding="utf-8")
    assert "build_field_psi" in mod_style
    assert "build_field_creep" in mod_style
    base_zh = Path("res/ui-zh/tts.txt").read_text(encoding="utf-8")
    assert "7240 灵能场" not in base_zh


def test_zoom_target_contains_respects_precision():
    """F8 精细比例下子格建造：ZoomTarget.contains 须与客户端 precision 一致。"""
    from soundrts.lib.nofloat import PRECISION
    from soundrts.worldroom import ZoomTarget, format_zoom_target_id, parse_zoom_target_id

    class _Sq:
        def __init__(self):
            self.id = "a1"
            self.xmin = 0
            self.ymin = 0
            self.xmax = 12 * PRECISION
            self.ymax = 12 * PRECISION
            self.x = 6 * PRECISION
            self.y = 6 * PRECISION
            self.title = ["a1"]
            self.objects = []
            self.exits = []
            self.world = types.SimpleNamespace(
                get_subsquare_id_from_xy=lambda x, y: (
                    x * 3 // (12 * PRECISION),
                    y * 3 // (12 * PRECISION),
                )
            )

    sq = _Sq()
    precision = 9
    xstep = (sq.xmax - sq.xmin) / precision
    ystep = (sq.ymax - sq.ymin) / precision
    # 子格 (7,7) 中心 — 远离主基地常用中心格
    sub_ix, sub_iy = 7, 7
    cx = sq.xmin + (sub_ix + 0.5) * xstep
    cy = sq.ymin + (sub_iy + 0.5) * ystep
    nexus_x, nexus_y = sq.x, sq.y

    zid = format_zoom_target_id(sq.id, cx, cy, precision)
    assert parse_zoom_target_id(zid) == (sq.id, int(cx), int(cy), precision)
    zt = ZoomTarget(sq, int(cx), int(cy), id=zid, precision=precision)

    assert zt.contains(cx, cy)
    assert not zt.contains(nexus_x, nexus_y)

    class _Nexus:
        is_buildable_anywhere = True
        x = nexus_x
        y = nexus_y

    sq.objects = [_Nexus()]
    assert zt.any_land is zt


def test_voice_missing_build_field_no_duplicate_field_title():
    """缺建造场时只播一条提示，不再追加 build_field_<type> 名称。"""
    from pathlib import Path

    from soundrts.definitions import Style

    src = Path("soundrts/clientgame/build_field_voice.py").read_text(encoding="utf-8")
    voice_fn = src.split("def voice_missing_build_field", 1)[1].split("\ndef ", 1)[0]
    assert "build_field_title_msg" not in voice_fn
    assert "missing_build_field_{field_type}" in voice_fn

    base_style = Path("res/ui/style.txt").read_text(encoding="utf-8")
    mod_style = Path("mods/starcraft/ui/style.txt").read_text(encoding="utf-8")
    style = Style()
    style.load(base_style + "\n" + mod_style)
    assert style.get("messages", "missing_build_field_psi") == ["7394"]


def test_build_field_display_uses_mod_style():
    import importlib
    import sys
    import warnings
    from pathlib import Path

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.definitions import Rules, Style, _get_base_classes

            BuildRulesAttributes = importlib.import_module(
                "soundrts.attributes.build_rules_attributes"
            ).BuildRulesAttributes
            root = Path("mods/starcraft")
            base_style = Path("res/ui/style.txt").read_text(encoding="utf-8")
            mod_style = (root / "ui/style.txt").read_text(encoding="utf-8")
            style = Style()
            style.load(base_style + "\n" + mod_style)
            import soundrts.definitions as defs

            old_style = defs.style
            defs.style = style
            try:
                bra = BuildRulesAttributes(None)
                assert bra._format_build_field("psi") == ["7240"]
                assert bra._format_build_field("creep") == ["7241"]
                assert bra._format_build_field("city") == ["city"]
            finally:
                defs.style = old_style
    finally:
        sys.argv = saved_argv


def test_build_rules_attributes_in_attributes_screen():
    import importlib
    import sys
    import warnings
    from pathlib import Path

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts import msgparts as mp
            from soundrts.definitions import Rules, _get_base_classes

            BuildRulesAttributes = importlib.import_module(
                "soundrts.attributes.build_rules_attributes"
            ).BuildRulesAttributes
            from soundrts.definitions import style

            root = Path("mods/starcraft")
            style.load(
                Path("res/ui/style.txt").read_text(encoding="utf-8")
                + "\n"
                + (root / "ui/style.txt").read_text(encoding="utf-8")
            )

            text = root / "rules.txt"
            r = Rules()
            r.load(text.read_text(encoding="utf-8"), base_classes=_get_base_classes())
            gateway = r.unit_class("gateway")
            probe = r.unit_class("probe")
            tech_lab = r.unit_class("tech_lab")

            class _U:
                def __init__(self, model):
                    self.model = model

            bra = BuildRulesAttributes(None)
            gw_attrs = []
            bra.add_build_rules_attributes(_U(gateway), gw_attrs)
            assert any(a[1] == mp.SELF_CONSTRUCTS for a in gw_attrs)
            assert any(a[1] == mp.REQUIRES_BUILD_FIELD for a in gw_attrs)
            assert any(a[1] == mp.IS_BUILDABLE_ANYWHERE for a in gw_attrs)
            req = next(a for a in gw_attrs if a[1] == mp.REQUIRES_BUILD_FIELD)
            assert req[2] == ["7240"]

            pr_attrs = []
            bra.add_build_rules_attributes(_U(probe), pr_attrs)
            assert any(a[1] == mp.BUILD_MODE for a in pr_attrs)
            assert not any(a[1] == mp.IS_BUILDABLE_ANYWHERE for a in pr_attrs)

            tl_attrs = []
            bra.add_build_rules_attributes(_U(tech_lab), tl_attrs)
            assert any(a[1] == mp.IS_ADDON for a in tl_attrs)
            assert any(a[1] == mp.SELF_CONSTRUCTS for a in tl_attrs)

            assimilator = r.unit_class("assimilator")
            as_attrs = []
            bra.add_build_rules_attributes(_U(assimilator), as_attrs)
            assert any(a[1] == mp.REQUIRES_DEPOSIT for a in as_attrs)
            dep = next(a for a in as_attrs if a[1] == mp.REQUIRES_DEPOSIT)
            assert dep[2] == ["7274"]

            ResourceUtils = importlib.import_module(
                "soundrts.attributes.resource_utils"
            ).ResourceUtils

            class _RU:
                interface = None

            ru = ResourceUtils(_RU())
            assert ru._get_resource_type_name("resource1") == "7270"
            assert ru._get_resource_type_name("resource2") == "7271"
    finally:
        sys.argv = saved_argv


def test_gateway_building_site_self_constructs():
    """gateway 带 self_constructs：工地创建后 slow_update 自动涨进度（无需修理）。"""
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import soundrts.worldunit  # noqa: F401
            from pathlib import Path

            from soundrts import config
            from soundrts.definitions import rules
            from soundrts.lib.resource import res
            from soundrts.mapfile import Map
            from soundrts.world import World
            from soundrts.worldclient import DirectClient
            from soundrts.worldunit.worldcreature import BuildingSite

            config.debug_mode = 0
            config.mods = "starcraft"
            res.set_mods("starcraft")
            path = Path("mods/starcraft/multi/protoss_psi_test.txt")
            m = Map.loads(path.read_text(encoding="utf-8").encode("utf-8"), path.name)
            res.set_map(m)
            res.load_rules_and_ai()
            world = World(seed=1)
            world.load_and_build_map(m)
            client = DirectClient("p1", None)
            world.populate_map([client])
            player = world.players[0]
            b1 = next(s for s in world.squares if s.name == "1,0")
            gw_cls = rules.unit_class("gateway")
            assert gw_cls.self_constructs == 1

            site = BuildingSite(player, b1, b1.x, b1.y, gw_cls)
            assert site._self_construct
            timer_before = site.timer
            site.slow_update()
            assert site.timer < timer_before
    finally:
        sys.argv = saved_argv


def test_change_to_factory_reattaches_orphan_tech_lab():
    """Real units have no .type attr; landing must still reattach addons."""
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import soundrts.worldunit  # noqa: F401
            from pathlib import Path

            from soundrts import config
            from soundrts.definitions import rules
            from soundrts.lib.resource import res
            from soundrts.mapfile import Map
            from soundrts.world import World
            from soundrts.world_build_rules import attach_addon, effective_can_train
            from soundrts.worldclient import DirectClient
            from soundrts.worldorders.production import ChangeToOrder

            config.debug_mode = 0
            config.mods = "starcraft"
            res.set_mods("starcraft")
            path = Path("mods/starcraft/multi/terran_recombine_test.txt")
            m = Map.loads(path.read_text(encoding="utf-8").encode("utf-8"), path.name)
            res.set_map(m)
            res.load_rules_and_ai()
            world = World(seed=42)
            world.load_and_build_map(m)
            world.populate_map([DirectClient("p1", None)])
            player = world.players[0]

            barracks = next(u for u in player.units if u.type_name == "barracks")
            factory = next(u for u in player.units if u.type_name == "factory")
            tech_cls = rules.unit_class("tech_lab")
            tech = tech_cls(player, barracks.place, barracks.x, barracks.y)
            attach_addon(barracks, tech)
            assert not hasattr(tech, "type")

            ChangeToOrder(barracks, ["flying_barracks"]).complete()
            factory = next(u for u in player.units if u.type_name == "factory")
            ChangeToOrder(factory, ["flying_factory"]).complete()
            ff = next(u for u in player.units if u.type_name == "flying_factory")
            from soundrts.world_build_rules import go_target_for_flying_building_addon

            slot = go_target_for_flying_building_addon(ff, tech)
            ff.move_to(slot.place, slot.x, slot.y)
            # change_to 读取当前坐标；测试里 move_to 不会同步到位，需落到插槽坐标
            ff.x, ff.y = slot.x, slot.y

            ChangeToOrder(ff, ["factory"]).complete()
            landed = next(u for u in player.units if u.type_name == "factory")
            assert tech.attached_host is landed
            assert "tank" in effective_can_train(landed)
            # 训练菜单走 unit.can_train；不能被 rules dict 遮蔽 @property
            assert "tank" in landed.can_train
            factory_cls = rules.unit_class("factory")
            assert not hasattr(factory_cls, "can_train") or not isinstance(
                getattr(factory_cls, "can_train", None), dict
            )
    finally:
        sys.argv = saved_argv


def test_change_to_factory_on_own_meadow_does_not_reattach():
    """落在工厂起飞草地不对接；重组需飞到科技实验室插槽。"""
    import os
    import sys
    import warnings

    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["test"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import soundrts.worldunit  # noqa: F401
            from pathlib import Path

            from soundrts import config
            from soundrts.definitions import rules
            from soundrts.lib.resource import res
            from soundrts.mapfile import Map
            from soundrts.world import World
            from soundrts.world_build_rules import attach_addon, effective_can_train
            from soundrts.worldclient import DirectClient
            from soundrts.worldorders.production import ChangeToOrder

            config.debug_mode = 0
            config.mods = "starcraft"
            res.set_mods("starcraft")
            path = Path("mods/starcraft/multi/terran_recombine_test.txt")
            m = Map.loads(path.read_text(encoding="utf-8").encode("utf-8"), path.name)
            res.set_map(m)
            res.load_rules_and_ai()
            world = World(seed=42)
            world.load_and_build_map(m)
            world.populate_map([DirectClient("p1", None)])
            player = world.players[0]

            barracks = next(u for u in player.units if u.type_name == "barracks")
            factory = next(u for u in player.units if u.type_name == "factory")
            tech_cls = rules.unit_class("tech_lab")
            tech = tech_cls(player, barracks.place, barracks.x, barracks.y)
            attach_addon(barracks, tech)

            ChangeToOrder(barracks, ["flying_barracks"]).complete()
            factory = next(u for u in player.units if u.type_name == "factory")
            factory_x, factory_y = factory.x, factory.y
            place = factory.place
            ChangeToOrder(factory, ["flying_factory"]).complete()
            ff = next(u for u in player.units if u.type_name == "flying_factory")

            factory_meadow = place.find_meadow_near_xy(factory_x, factory_y)
            assert factory_meadow is not None
            ff.move_to(place, factory_meadow.x, factory_meadow.y)

            ChangeToOrder(ff, ["factory"]).complete()
            landed = next(u for u in player.units if u.type_name == "factory")
            assert tech.attached_host is None
            assert "tank" not in effective_can_train(landed)
    finally:
        sys.argv = saved_argv


def test_go_to_orphan_addon_targets_host_landing_slot():
    from soundrts.world_build_rules import (
        DEFAULT_ADDON_OFFSET_X,
        go_target_for_flying_building_addon,
    )
    from soundrts.worldroom import ZoomTarget

    factory_type = types.SimpleNamespace(
        type_name="factory",
        ground_form="factory",
        can_have_addon=("tech_lab",),
        is_a=(),
    )
    flying = types.SimpleNamespace(
        type_name="flying_factory",
        type=factory_type,
    )
    place = types.SimpleNamespace(title=[])
    tech_type = types.SimpleNamespace(
        type_name="tech_lab",
        is_addon=1,
        addon_host_types=("factory",),
        is_a=(),
    )
    addon = types.SimpleNamespace(
        type_name="tech_lab",
        type=tech_type,
        place=place,
        x=1000 + DEFAULT_ADDON_OFFSET_X,
        y=2000,
    )
    slot = go_target_for_flying_building_addon(flying, addon)
    assert isinstance(slot, ZoomTarget)
    assert slot.x == 1000
    assert slot.y == 2000
