"""Bridge buildings convert impassable water into walkable bridge terrain."""
from __future__ import annotations

import os
import types

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from soundrts.definitions import rules
from soundrts.lib.resource import res
from soundrts.lib.square_terrain_rules import squares_same_ground_region
from soundrts.world import World
from soundrts.world_build_rules import (
    can_build_water_target_from_shore,
    clear_scaffold_passage,
    is_pure_water_square,
    refresh_bridge_terrain,
    refresh_scaffold_passage,
    square_has_bridge_building,
    worker_can_place_water_build,
    worker_can_reach_water_build,
)
from soundrts.lib.square_terrain_rules import DEFAULT_TERRAIN_SPEED, resolve_terrain_speed
from soundrts.worldclient import DummyClient
from soundrts.worldorders.base import _is_impassable_water_for_ground_unit
from soundrts.worldorders.production import BuildOrder


@pytest.fixture(autouse=True)
def _load_rules():
    res.load_rules_and_ai()


def _mini_map(*lines: str) -> str:
    body = "\n".join(lines)
    return f"""
nb_columns 3
nb_lines 3
nb_players_min 1
nb_players_max 1
starting_squares 1,1
starting_resources 100 100
{body}
"""


def _world_from_map(text: str):
    world = World([], 42)
    world._parse_map(text)
    world._build_map()
    client = DummyClient(alliance=1)
    client.create_player(world)
    return world, client.player


def _sq(world, label: str):
    col = ord(label[0]) - ord("a")
    row = int(label[1:]) - 1
    return world.grid[f"{col},{row}"]


def _bridge_site(river, building_type=None):
    if building_type is None:
        building_type = rules.unit_class("wooden_bridge")
    return types.SimpleNamespace(
        type_name="buildingsite",
        type=building_type,
        hp=1,
        place=river,
        x=river.x,
        y=river.y,
    )


def _make_water_scaffold(player, river, shore_land, building_type=None):
    from soundrts.worldunit.worldcreature import BuildingSite

    if building_type is None:
        building_type = rules.unit_class("wooden_bridge")
    old_collision = BuildingSite.collision
    BuildingSite.collision = 0
    try:
        site = BuildingSite(player, river, river.x, river.y, building_type)
    finally:
        BuildingSite.collision = old_collision
    site.shore_land = shore_land
    refresh_scaffold_passage(site)
    return site


def _completed_bridge(river, building_type=None):
    if building_type is None:
        building_type = rules.unit_class("wooden_bridge")
    return types.SimpleNamespace(
        type_name="wooden_bridge",
        type=building_type,
        hp=400,
        place=river,
        x=river.x,
        y=river.y,
    )


def test_wooden_bridge_rules_loaded():
    cls = rules.unit_class("wooden_bridge")
    assert cls is not None
    assert getattr(cls, "is_buildable_on_water_only", 0)
    assert getattr(cls, "bridge_terrain", None) in ("bridge_deck", ["bridge_deck"])


def test_refresh_bridge_terrain_makes_water_passable():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    assert is_pure_water_square(river)
    assert _is_impassable_water_for_ground_unit(
        types.SimpleNamespace(airground_type="ground"), river
    )

    building_type = rules.unit_class("wooden_bridge")
    bridge = _completed_bridge(river, building_type)
    river.objects = [bridge]
    refresh_bridge_terrain(river)

    assert river.is_water
    assert river.is_ground
    assert getattr(river, "_bridge_terrain_voice", None) == "bridge_deck"
    assert not _is_impassable_water_for_ground_unit(
        types.SimpleNamespace(airground_type="ground"), river
    )
    land = _sq(world, "b1")
    assert squares_same_ground_region(river, land)


def test_refresh_bridge_terrain_reverts_when_building_removed():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    building_type = rules.unit_class("wooden_bridge")
    bridge = _completed_bridge(river, building_type)
    river.objects = [bridge]
    refresh_bridge_terrain(river)
    river.objects = []
    refresh_bridge_terrain(river)
    assert is_pure_water_square(river)


def test_building_site_does_not_open_full_bridge_passage():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    site = _bridge_site(river)
    river.objects = [site]
    refresh_bridge_terrain(river)

    assert is_pure_water_square(river)
    assert not any(e.other_side.place is river for e in land.exits)


def test_scaffold_only_links_placer_shore():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "a2")
    _make_water_scaffold(player, river, land)

    assert river.is_ground
    assert any(e.other_side.place is river for e in land.exits)
    assert not any(e.other_side.place is river for e in _sq(world, "b1").exits)
    assert not any(e.other_side.place is river for e in _sq(world, "b3").exits)


def test_scaffold_no_link_to_adjacent_scaffold():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    river1 = _sq(world, "b1")
    river2 = _sq(world, "b2")
    land = _sq(world, "a1")
    _make_water_scaffold(player, river1, land)
    _make_water_scaffold(player, river2, land)

    assert not any(e.other_side.place is river2 for e in river1.exits)
    assert not any(e.other_side.place is river1 for e in river2.exits)


def test_water_building_site_survives_drowning():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    building_type = rules.unit_class("wooden_bridge")
    from soundrts.worldunit.worldcreature import BuildingSite

    site = BuildingSite(player, river, river.x, river.y, building_type)
    player.units.append(site)
    assert is_pure_water_square(river)

    player._update_drowning()

    assert site in player.units
    assert site.hp > 0


def test_ground_unit_still_drowns_on_water():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, river, river.x, river.y)
    player.units.append(peasant)
    assert is_pure_water_square(river)

    player._update_drowning()

    assert peasant.place is None


def test_water_build_site_cannot_be_built_from_shore():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, land, land.x, land.y)
    site = _make_water_scaffold(player, river, land)
    assert not can_build_water_target_from_shore(site, peasant)


def test_worker_can_place_from_adjacent_land():
    water = types.SimpleNamespace(
        strict_neighbors=[types.SimpleNamespace(is_water=False, is_ground=True)],
        is_water=True,
        is_ground=False,
    )
    land = water.strict_neighbors[0]
    worker = types.SimpleNamespace(place=land)
    assert worker_can_place_water_build(worker, water)


def test_build_order_accepts_water_square_target():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, land, land.x, land.y)
    player.units.append(peasant)
    player.resources = [100000, 100000, 0, 0, 0, 0, 0, 0, 0, 0]

    order = BuildOrder(peasant, ["wooden_bridge", river.id])
    order.on_queued()
    assert not order.is_impossible
    assert order.target is river


def test_build_order_rejects_land_target():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    land = _sq(world, "b1")
    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, land, land.x, land.y)
    player.units.append(peasant)

    order = BuildOrder(peasant, ["wooden_bridge", land.id])
    order.on_queued()
    assert order.is_impossible


def test_square_has_bridge_building_detects_site():
    building_type = rules.unit_class("wooden_bridge")
    square = types.SimpleNamespace(
        objects=[
            types.SimpleNamespace(
                type_name="buildingsite",
                type=building_type,
                hp=1,
            )
        ]
    )
    assert square_has_bridge_building(square)


def test_refresh_bridge_terrain_creates_exit_from_land():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    assert not any(e.other_side.place is river for e in land.exits)

    building_type = rules.unit_class("wooden_bridge")
    bridge = _completed_bridge(river, building_type)
    river.objects = [bridge]
    refresh_bridge_terrain(river)

    assert any(e.other_side.place is river for e in land.exits)
    nxt = land.shortest_path_to(river)
    assert nxt is not None
    assert nxt.other_side.place is river


def test_worker_can_reach_water_from_land():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, land, land.x, land.y)
    assert worker_can_reach_water_build(peasant, river)


def test_peasant_paths_onto_scaffold_to_build():
    from soundrts.worldorders.movement import BuildPhaseTwoOrder

    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    player.resources = [100000] * 10
    site = _make_water_scaffold(player, river, land)

    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, land, land.x, land.y)

    assert land.shortest_path_to(river) is not None
    peasant.move_to(river, river.x, river.y)
    assert peasant.place is river

    order = BuildPhaseTwoOrder(peasant, [site.id])
    order.on_queued()
    assert not order.is_impossible

    hp0 = site.hp
    order.execute()
    assert order.mode == "build"
    order.execute()
    assert site.hp > hp0


def test_scaffold_passage_works_with_scaled_square_width():
    """Scaffold shore link must work on real-scale square_width."""
    from soundrts.lib.nofloat import PRECISION

    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    world.square_width = int(world.square_width * PRECISION)
    for sq in world.squares:
        width = world.square_width
        sq.xmin = sq.col * width
        sq.ymin = sq.row * width
        sq.xmax = sq.xmin + width
        sq.ymax = sq.ymin + width
        sq.x = (sq.xmax + sq.xmin) // 2
        sq.y = (sq.ymax + sq.ymin) // 2

    river = _sq(world, "b2")
    land = _sq(world, "b1")
    _make_water_scaffold(player, river, land)

    assert any(e.other_side.place is river for e in land.exits)
    nxt = land.shortest_path_to(river)
    assert nxt is not None
    assert nxt.other_side.place is river


def test_completed_bridge_restores_full_passage():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land_b1 = _sq(world, "b1")
    land_b3 = _sq(world, "b3")
    site = _make_water_scaffold(player, river, land_b1)
    assert not any(e.other_side.place is river for e in land_b3.exits)

    while site in player.units and site.timer > 0:
        site.be_built(None)

    assert site not in player.units
    assert getattr(river, "_bridge_terrain_voice", None) == "bridge_deck"
    assert any(e.other_side.place is river for e in land_b1.exits)
    assert any(e.other_side.place is river for e in land_b3.exits)


def test_adjacent_bridges_connect_with_bridge_exit():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    river1 = _sq(world, "b1")
    river2 = _sq(world, "b2")
    building_type = rules.unit_class("wooden_bridge")

    for river in (river1, river2):
        bridge = _completed_bridge(river, building_type)
        river.objects = [bridge]
        refresh_bridge_terrain(river)

    link = None
    for e in river1.exits:
        if e.other_side.place is river2:
            link = e
            break
    assert link is not None
    assert link.type_name == "bridge"
    assert link.other_side.type_name == "bridge"


def test_land_to_single_bridge_still_uses_path_exit():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    building_type = rules.unit_class("wooden_bridge")
    bridge = _completed_bridge(river, building_type)
    river.objects = [bridge]
    refresh_bridge_terrain(river)

    link = next(e for e in land.exits if e.other_side.place is river)
    assert link.type_name == "path"
    assert link.other_side.type_name == "path"


def test_bridge_destruction_clears_exits_and_objects():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    site = _make_water_scaffold(player, river, land)
    while site in player.units and site.timer > 0:
        site.be_built(None)

    bridge = next(
        o for o in river.objects if getattr(o, "type_name", None) == "wooden_bridge"
    )
    assert any(e.other_side.place is river for e in land.exits)

    bridge.hp = 0
    bridge.die()

    assert is_pure_water_square(river)
    assert river.exits == []
    assert not any(getattr(o, "is_an_exit", False) for o in river.objects)
    assert not any(e.other_side.place is river for e in land.exits)


def test_adjacent_bridge_destruction_clears_destroyed_cell():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    river1 = _sq(world, "b2")
    river2 = _sq(world, "c2")
    site1 = _make_water_scaffold(player, river1, _sq(world, "b1"))
    while site1 in player.units and site1.timer > 0:
        site1.be_built(None)
    site2 = _make_water_scaffold(player, river2, _sq(world, "c1"))
    while site2 in player.units and site2.timer > 0:
        site2.be_built(None)

    bridge1 = next(
        o for o in river1.objects if getattr(o, "type_name", None) == "wooden_bridge"
    )
    assert any(e.other_side.place is river2 for e in river1.exits)

    bridge1.hp = 0
    bridge1.die()

    assert is_pure_water_square(river1)
    assert river1.exits == []
    assert not any(getattr(o, "is_an_exit", False) for o in river1.objects)
    assert getattr(river2, "_bridge_terrain_voice", None) == "bridge_deck"
    assert any(e.other_side.place is river2 for e in _sq(world, "c1").exits)


def test_building_site_silent_without_active_builder():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    site = _make_water_scaffold(player, river, land)
    player.units.append(site)

    assert site.timer > 0
    assert site.activity is None


def test_building_site_activity_while_worker_builds():
    from soundrts.worldorders.movement import BuildPhaseTwoOrder

    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "b1")
    site = _make_water_scaffold(player, river, land)
    player.units.append(site)

    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, river, river.x, river.y)
    player.units.append(peasant)

    order = BuildPhaseTwoOrder(peasant, [site.id])
    order.on_queued()
    order.mode = "build"
    peasant.orders = [order]

    assert site.activity == "building"


def test_scaffold_no_move_between_adjacent_scaffolds_via_shore():
    """Two scaffolds sharing a shore must not allow direct scaffold-to-scaffold steps."""
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    river1 = _sq(world, "b2")
    river2 = _sq(world, "c2")
    shore = _sq(world, "b1")
    site1 = _make_water_scaffold(player, river1, shore)
    site2 = _make_water_scaffold(player, river2, shore)
    player.units.extend([site1, site2])

    assert not any(e.other_side.place is river2 for e in river1.exits)

    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, river1, river1.x, river1.y)
    player.units.append(peasant)

    assert not peasant._can_go(river2)
    assert not peasant.can_move_to(river2)


def test_go_order_scaffold_to_scaffold_is_impossible():
    from soundrts.worldorders import GoOrder

    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    river1 = _sq(world, "b2")
    river2 = _sq(world, "c2")
    shore = _sq(world, "b1")
    _make_water_scaffold(player, river1, shore)
    _make_water_scaffold(player, river2, shore)

    peasant_cls = rules.unit_class("peasant")
    peasant = peasant_cls(player, river1, river1.x, river1.y)
    player.units.append(peasant)
    msgs = []
    peasant.notify = lambda msg, *_a, **_k: msgs.append(msg)

    order = GoOrder(peasant, [river2.id])
    order.on_queued()
    assert order.is_impossible
    assert "order_impossible,scaffold_impassable" in msgs
    assert "order_ok" not in msgs


def test_go_order_wrong_shore_to_scaffold_is_impossible():
    """Only the placer shore may ``go`` onto an unfinished span."""
    import types

    from soundrts.worldorders import GoOrder

    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain ocean a2 b2 c2",
            "terrain plain a3 b3 c3",
        )
    )
    ocean = _sq(world, "b2")
    placer_shore = _sq(world, "b1")
    far_shore = _sq(world, "b3")
    _make_water_scaffold(player, ocean, placer_shore)

    def _unit_on(place):
        unit = types.SimpleNamespace(
            airground_type="ground",
            place=place,
            player=player,
            world=world,
            is_imperative=False,
        )
        msgs = []
        unit.notify = lambda msg, *_a, **_k: msgs.append(msg)
        return unit, msgs

    unit, msgs = _unit_on(placer_shore)
    ok = GoOrder(unit, [ocean.id])
    ok.on_queued()
    assert not ok.is_impossible
    assert "order_ok" in msgs

    unit, msgs = _unit_on(far_shore)
    bad = GoOrder(unit, [ocean.id])
    bad.on_queued()
    assert bad.is_impossible
    assert "order_impossible,scaffold_impassable" in msgs

    unit, msgs = _unit_on(ocean)
    leave = GoOrder(unit, [far_shore.id])
    leave.on_queued()
    assert leave.is_impossible
    assert "order_impossible,scaffold_impassable" in msgs


def test_completed_bridge_keeps_exit_to_next_scaffold():
    """Finishing span N must not sever the link to span N+1 scaffold placed from it."""
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 b1 c1",
            "terrain river a2 b2 c2",
            "terrain river a3 b3 c3",
        )
    )
    span1 = _sq(world, "b2")
    span2 = _sq(world, "c2")
    land = _sq(world, "b1")
    building_type = rules.unit_class("wooden_bridge")

    site1 = _make_water_scaffold(player, span1, land)
    _make_water_scaffold(player, span2, span1)
    assert any(e.other_side.place is span2 for e in span1.exits)

    clear_scaffold_passage(site1)
    span1.objects = [_completed_bridge(span1, building_type)]
    refresh_bridge_terrain(span1)

    assert any(e.other_side.place is span2 for e in span1.exits)
    assert any(e.other_side.place is span1 for e in span2.exits)


def test_ocean_scaffold_restores_terrain_speed():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain ocean b2",
        )
    )
    ocean = _sq(world, "b2")
    land = _sq(world, "b1")
    assert ocean.terrain_speed == (0, 25)

    site = _make_water_scaffold(player, ocean, land)
    expected_deck_speed = resolve_terrain_speed("bridge_deck")
    assert ocean.terrain_speed == expected_deck_speed
    assert expected_deck_speed == DEFAULT_TERRAIN_SPEED

    clear_scaffold_passage(site)
    assert ocean.terrain_speed == (0, 25)


def test_ocean_bridge_deck_restores_terrain_speed():
    world, _player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain ocean b2",
        )
    )
    ocean = _sq(world, "b2")
    assert ocean.terrain_speed == (0, 25)

    building_type = rules.unit_class("wooden_bridge")
    bridge = _completed_bridge(ocean, building_type)
    ocean.objects = [bridge]
    refresh_bridge_terrain(ocean)

    assert ocean.terrain_speed == DEFAULT_TERRAIN_SPEED
    assert getattr(ocean, "_bridge_terrain_voice", None) == "bridge_deck"

    ocean.objects = []
    refresh_bridge_terrain(ocean)
    assert ocean.terrain_speed == (0, 25)


def test_bridge_layer_voice_only_when_deck_complete():
    from soundrts.lib.square_terrain_rules import resolve_square_layers

    square = types.SimpleNamespace(
        objects=[],
        high_ground=False,
        is_water=True,
        fixed_terrain=False,
        _scaffold_terrain_voice="bridge_deck",
        _bridge_terrain_voice=None,
    )
    layers = resolve_square_layers(square)
    assert layers["feature_voice"] is None

    square._bridge_terrain_voice = "bridge_deck"
    layers = resolve_square_layers(square)
    assert layers["feature_voice"] == "bridge_deck"


def test_scaffold_footstep_uses_bridge_deck_voice():
    world, player = _world_from_map(
        _mini_map(
            "terrain plain a1 a2 a3",
            "terrain plain b1 b3",
            "terrain river b2",
        )
    )
    river = _sq(world, "b2")
    land = _sq(world, "a2")
    site = _make_water_scaffold(player, river, land)
    assert getattr(river, "_scaffold_terrain_voice", None) == "bridge_deck"


def test_wooden_bridge_not_tab_exit():
    from pathlib import Path

    from soundrts.clientgameentity import EntityView
    from soundrts.definitions import style

    style.load(Path("res/ui/style.txt").read_text(encoding="utf-8"))
    cls = rules.unit_class("wooden_bridge")
    model = cls.__new__(cls)
    model.type_name = "wooden_bridge"
    model.is_a_building = True
    model.is_an_exit = False
    model.place = types.SimpleNamespace(name="b2")
    model.x = model.y = 6000
    model.player = None
    model.hp = 400000
    iface = types.SimpleNamespace(
        place=model.place,
        zoom_mode=False,
        zoom=None,
        group=[],
        immersion=False,
        player=types.SimpleNamespace(allied=[]),
        square_width=12,
        dobjects={},
    )
    view = EntityView(iface, model)
    assert view.is_an_exit is False


def test_square_allows_passage_tab_on_bridge_and_scaffold():
    from soundrts.clientgame import game_unit_control as guc

    bridge = types.SimpleNamespace(_bridge_terrain_voice="bridge_deck")
    scaffold = types.SimpleNamespace(_scaffold_terrain_voice="bridge_deck")
    plain = types.SimpleNamespace()
    assert guc._square_allows_passage_tab(bridge)
    assert guc._square_allows_passage_tab(scaffold)
    assert not guc._square_allows_passage_tab(plain)
    assert not guc._square_allows_passage_tab(None)
