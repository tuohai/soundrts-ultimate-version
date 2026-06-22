"""Tests for computer-player water pathfinding and amphibious transport helpers."""
from __future__ import annotations

import types

from soundrts.worldplayercomputer_water import (
    find_amphibious_crossing,
    gather_shore_lands_near,
    is_land_shore,
    movement_target_for_unit,
    path_plane,
)


def _square(name, *, is_water=False, is_ground=True, high_ground=False, neighbors=None, x=0, y=0):
    sq = types.SimpleNamespace(
        id=name,
        x=x,
        y=y,
        is_water=is_water,
        is_ground=is_ground,
        high_ground=high_ground,
        strict_neighbors=neighbors or [],
        neighbors=neighbors or [],
    )
    return sq


def test_path_plane_for_water_and_air():
    assert path_plane(types.SimpleNamespace(airground_type="water")) == "water"
    assert path_plane(types.SimpleNamespace(airground_type="air")) == "air"
    assert path_plane(types.SimpleNamespace(airground_type="ground")) == "ground"


def test_is_land_shore():
    water = _square("w", is_water=True, is_ground=False)
    shore = _square("s", neighbors=[water])
    land = _square("l", neighbors=[shore])
    assert is_land_shore(shore)
    assert not is_land_shore(water)
    assert not is_land_shore(land)


def test_gather_shore_lands_near_finds_reachable_shore():
    water = _square("w", is_water=True, is_ground=False)
    shore = _square("s", neighbors=[water])
    inland = _square("i", neighbors=[shore])
    shore.neighbors = [water, inland]
    inland.neighbors = [shore]
    water.neighbors = [shore]
    shores = gather_shore_lands_near(inland)
    assert shore in shores


def test_movement_target_for_water_unit_picks_adjacent_water():
    land = _square("land", is_water=False, is_ground=True)
    water_a = _square("wa", is_water=True, is_ground=False)
    water_b = _square("wb", is_water=True, is_ground=False)
    land.strict_neighbors = [water_a, water_b]
    land.neighbors = [water_a, water_b]

    unit = types.SimpleNamespace(
        airground_type="water",
        place=water_a,
    )
    unit.place.shortest_path_distance_to = lambda dest, player, plane: (
        0 if dest is water_a else 5
    )

    target = movement_target_for_unit(unit, land, player=None)
    assert target is water_a


def test_movement_target_for_land_without_adjacent_water_picks_lake():
    """M3-style: enemy base on land with no neighboring water."""
    land = _square("base", is_water=False, is_ground=True, x=100, y=0)
    land.strict_neighbors = []
    land.neighbors = []
    lake_near = _square("lake", is_water=True, is_ground=False, x=90, y=0)
    lake_far = _square("far", is_water=True, is_ground=False, x=0, y=0)
    unit = types.SimpleNamespace(airground_type="water", place=lake_far)
    world = types.SimpleNamespace(
        water_squares={lake_near.id, lake_far.id},
        grid={lake_near.id: lake_near, lake_far.id: lake_far},
        squares=[land, lake_near, lake_far],
    )
    land.world = world
    lake_near.world = world
    lake_far.world = world

    def water_dist(src, dest, player, plane="water"):
        if plane != "water":
            return float("inf")
        if src is lake_far and dest is lake_near:
            return 3
        if src is lake_far and dest is lake_far:
            return 0
        if src is lake_near and dest is lake_near:
            return 0
        return float("inf")

    for sq in (land, lake_near, lake_far):
        sq.shortest_path_distance_to = (
            lambda dest, player, plane="ground", _sq=sq: (
                water_dist(_sq, dest, player, plane)
                if plane == "water"
                else (10 if _sq is land and dest is lake_near else float("inf"))
            )
        )

    target = movement_target_for_unit(unit, land, player=None)
    assert target is lake_near
    assert target.is_water


def test_find_amphibious_crossing_links_two_shores():
    left_water = _square("lw", is_water=True, is_ground=False)
    right_water = _square("rw", is_water=True, is_ground=False)
    left_shore = _square("ls", neighbors=[left_water])
    right_shore = _square("rs", neighbors=[right_water])
    left_inland = _square("li", neighbors=[left_shore])
    right_inland = _square("ri", neighbors=[right_shore])
    left_water.neighbors = [left_shore, right_water]
    right_water.neighbors = [right_shore, left_water]
    left_shore.neighbors = [left_water, left_inland]
    right_shore.neighbors = [right_water, right_inland, left_shore]
    left_inland.neighbors = [left_shore]
    right_inland.neighbors = [right_shore]

    def ground_dist(src, dest, plane="ground"):
        if plane != "ground":
            return float("inf")
        pairs = {
            ("li", "li"): 0,
            ("li", "ls"): 1,
            ("ls", "li"): 1,
            ("ri", "ri"): 0,
            ("ri", "rs"): 1,
            ("rs", "ri"): 1,
        }
        return pairs.get((src.id, dest.id), float("inf"))

    def water_dist(src, dest, plane="water"):
        if plane != "water":
            return float("inf")
        pairs = {
            ("lw", "lw"): 0,
            ("rw", "rw"): 0,
            ("lw", "rw"): 1,
            ("rw", "lw"): 1,
        }
        return pairs.get((src.id, dest.id), float("inf"))

    for sq in (
        left_inland,
        left_shore,
        right_shore,
        right_inland,
        left_water,
        right_water,
    ):
        sq.shortest_path_distance_to = (
            lambda dest, player, plane="ground", _sq=sq: (
                water_dist(_sq, dest, plane)
                if plane == "water"
                else ground_dist(_sq, dest, plane)
            )
        )

    player = types.SimpleNamespace()
    route = find_amphibious_crossing(left_inland, right_inland, player)
    assert route is not None
    load_land, load_water, unload_water, unload_land = route
    assert load_land is left_shore
    assert load_water is left_water
    assert unload_water is right_water
    assert unload_land is right_shore


def test_spawn_place_for_trained_water_unit_tries_shore_neighbors():
    from soundrts.worldplayercomputer_water import spawn_place_for_trained_water_unit

    land = _square("land", is_water=False, is_ground=True, x=0, y=0)
    water_a = _square("wa", is_water=True, is_ground=False, x=10, y=0)
    land.strict_neighbors = [water_a]
    land.neighbors = [water_a]
    water_a.strict_neighbors = [land]
    calls = []

    class FakeDock:
        type = types.SimpleNamespace(is_buildable_near_water_only=True)
        place = land
        x = 0
        y = 0

        def nearest_water(self):
            return water_a

    water_a.find_free_space = lambda ag, x, y: calls.append((ag, x, y)) or (None, None)
    land.find_free_space = lambda ag, x, y: (1, 1)

    unit_type = types.SimpleNamespace(airground_type="water")
    place, x, y = spawn_place_for_trained_water_unit(FakeDock(), unit_type)
    assert calls
    assert place is land
    assert (x, y) == (1, 1)
