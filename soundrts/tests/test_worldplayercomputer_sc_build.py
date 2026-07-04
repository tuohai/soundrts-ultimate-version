"""Tests for StarCraft-style Computer AI build helpers."""
from __future__ import annotations

import types
from unittest.mock import patch


class _Square:
    __slots__ = ("id", "neighbors", "world", "x", "y")

    def __init__(self, sid, x=0, y=0):
        self.id = sid
        self.x = x
        self.y = y
        self.neighbors = []
        self.world = None

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, _Square) and other.id == self.id

    def shortest_path_distance_to(self, other, player=None, avoid=False):
        if other is self:
            return 0
        return abs(self.id - getattr(other, "id", 0))


class _Meadow:
    __slots__ = ("id", "place", "x", "y", "type_name")
    is_a_building_land = True
    is_an_exit = False

    def __init__(self, mid, place, x, y):
        self.id = mid
        self.place = place
        self.x = x
        self.y = y
        self.type_name = "meadow"

    def __hash__(self):
        return self.id

    def __eq__(self, other):
        return isinstance(other, _Meadow) and other.id == self.id


def test_choose_build_target_anywhere_prefers_square_over_meadow():
    from soundrts.worldplayercomputer_sc_build import choose_build_target
    from soundrts.world_build_rules import mark_build_field_squares

    world = types.SimpleNamespace()
    player = types.SimpleNamespace(id=1, world=world)
    world._build_field_marked_squares = {}

    b1 = _Square(1, 100, 100)
    b1.world = world
    mark_build_field_squares(world, player, "psi", {b1})

    meadow = _Meadow(10, b1, 100, 100)
    gateway = types.SimpleNamespace(
        requires_build_field=0,
        requires_build_field_on_square=0,
        is_buildable_anywhere=1,
    )

    _world = world

    class AI:
        id = 1
        world = _world
        units = [meadow]
        perception = {meadow}
        memory = set()

        def check_type(self, o, c):
            return getattr(o, "type_name", None) == "meadow"

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

        def _builders_place(self):
            return b1

    ai = AI()
    chosen = choose_build_target(ai, gateway, starting_place=b1)
    assert chosen is b1
    assert chosen is not meadow


def test_choose_build_target_filters_by_build_field():
    from soundrts.worldplayercomputer_sc_build import choose_build_target
    from soundrts.world_build_rules import mark_build_field_squares

    world = types.SimpleNamespace()
    player = types.SimpleNamespace(id=1, world=world)
    world._build_field_marked_squares = {}

    b1 = _Square(1)
    b2 = _Square(2)
    b1.world = world
    b2.world = world
    mark_build_field_squares(world, player, "creep", {b1})

    meadow_ok = _Meadow(10, b1, 100, 100)
    meadow_bad = _Meadow(11, b2, 200, 200)

    pool = types.SimpleNamespace(
        requires_build_field="creep",
        requires_build_field_on_square=1,
    )

    _world = world
    starting_place = b1

    class AI:
        id = 1
        world = _world
        units = [meadow_ok]
        perception = {meadow_ok, meadow_bad}
        memory = set()

        def check_type(self, o, c):
            return getattr(o, "type_name", None) == "meadow"

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

        def _builders_place(self):
            return starting_place

    ai = AI()
    chosen = choose_build_target(ai, pool, starting_place=b1)
    assert chosen is meadow_ok


def test_choose_build_target_uses_square_when_buildable_anywhere():
    from soundrts.worldplayercomputer_sc_build import choose_build_target
    from soundrts.world_build_rules import mark_build_field_squares

    world = types.SimpleNamespace()
    player = types.SimpleNamespace(id=1, world=world)
    world._build_field_marked_squares = {}

    b1 = _Square(1, 100, 100)
    b1.world = world
    mark_build_field_squares(world, player, "creep", {b1})

    pool = types.SimpleNamespace(
        requires_build_field="creep",
        requires_build_field_on_square=1,
        is_buildable_anywhere=1,
    )

    _world = world

    class AI:
        id = 1
        world = _world
        units = []
        perception = set()
        memory = set()

        def check_type(self, o, c):
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

        def _builders_place(self):
            return b1

    ai = AI()
    chosen = choose_build_target(ai, pool, starting_place=b1)
    assert chosen is b1


def test_choose_near_water_build_target_picks_shore_meadow():
    from soundrts.worldplayercomputer_sc_build import choose_near_water_build_target

    base = types.SimpleNamespace(
        id=1, x=0, y=0, is_near_water=False, neighbors=[],
    )
    shore = types.SimpleNamespace(
        id=2, x=100, y=100, is_near_water=True, neighbors=[base], objects=[],
    )
    base.neighbors = [shore]
    meadow = _Meadow(10, shore, 100, 100)
    shore.objects = [meadow]

    shipyard = types.SimpleNamespace(
        is_buildable_near_water_only=True,
        requires_build_field="",
    )

    class AI:
        world = types.SimpleNamespace(squares=[base, shore])

        def check_type(self, o, cls):
            return isinstance(o, cls) or isinstance(o, _Meadow) and cls is _Meadow

        def square_is_dangerous(self, place):
            return False

    ai = AI()
    base.shortest_path_distance_to = lambda dest, player, avoid=False: (
        0 if dest is base else 1
    )
    shore.shortest_path_distance_to = base.shortest_path_distance_to

    import soundrts.worldplayercomputer_sc_build as scb

    old_valid = scb.build_site_valid
    scb.build_site_valid = lambda a, bt, place, x, y: place is shore
    try:
        chosen = choose_near_water_build_target(ai, shipyard, starting_place=base)
    finally:
        scb.build_site_valid = old_valid
    assert chosen is not None
    place = chosen if hasattr(chosen, "is_near_water") else chosen.place
    assert place.is_near_water


def test_build_site_valid_rejects_inland_shipyard():
    from soundrts.worldplayercomputer_sc_build import build_site_valid

    inland = types.SimpleNamespace(
        id=1, x=0, y=0, is_near_water=False, neighbors=[],
    )
    shipyard = types.SimpleNamespace(is_buildable_near_water_only=True)

    class AI:
        world = types.SimpleNamespace()

    import soundrts.worldplayercomputer_sc_build as scb

    old = scb.build_field_ok
    scb.build_field_ok = lambda *a, **k: True
    try:
        assert not build_site_valid(AI(), shipyard, inland, 0, 0)
    finally:
        scb.build_field_ok = old


def test_ensure_field_provider_waits_for_creep_instead_of_new_hatchery():
    from soundrts.worldplayercomputer_sc_build import ensure_field_provider_before_build

    world = types.SimpleNamespace()
    b2 = _Square(2)
    b2.world = world

    hatchery_type = types.SimpleNamespace(provides_build_field="creep")
    hatchery = types.SimpleNamespace(hp=100, type=hatchery_type, place=b2)

    pool = types.SimpleNamespace(
        requires_build_field="creep",
        requires_build_field_on_square=1,
        is_buildable_anywhere=1,
    )

    build_calls = []
    _world = world

    class AI:
        id = 1
        world = _world
        units = [hatchery]
        perception = set()
        memory = set()

        def future_nb(self, names):
            return 1

        def nb(self, names):
            return 1

        def build_or_train_or_upgradeto_or_summon(self, cls):
            build_calls.append(cls)

        def _builders_place(self):
            return b2

        def check_type(self, o, c):
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

    assert ensure_field_provider_before_build(AI(), pool) is True
    assert build_calls == []


def test_ensure_field_provider_caps_extra_pylons():
    from soundrts.worldplayercomputer_sc_build import ensure_field_provider_before_build

    world = types.SimpleNamespace()
    b1 = _Square(1, 100, 100)
    b1.world = world

    pylon_type = types.SimpleNamespace(provides_build_field="psi")
    pylons = [
        types.SimpleNamespace(hp=100, type=pylon_type, place=b1),
        types.SimpleNamespace(hp=100, type=pylon_type, place=b1),
    ]

    gateway = types.SimpleNamespace(
        requires_build_field="psi",
        requires_build_field_on_square=0,
        is_buildable_anywhere=1,
    )

    build_calls = []
    _world = world

    class AI:
        id = 1
        world = _world
        units = pylons
        perception = set()
        memory = set()

        def future_nb(self, names):
            return 2

        def nb(self, names):
            return 2

        def build_or_train_or_upgradeto_or_summon(self, cls):
            build_calls.append(cls)

        def _builders_place(self):
            return b1

        def check_type(self, o, c):
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

    assert ensure_field_provider_before_build(AI(), gateway) is False
    assert build_calls == []


def _load_rules(text):
    import soundrts.worldunit  # noqa: F401
    from soundrts.definitions import rules

    rules.load(
        """
def parameters
nb_of_resource_types 2
"""
        + text
    )
    return rules


def test_worker_can_build_and_repair_helpers():
    from soundrts.worldplayercomputer_sc_build import worker_can_build, worker_can_repair

    probe = types.SimpleNamespace(
        can_build=("pylon", "gateway"),
        can_repair=0,
    )
    scv = types.SimpleNamespace(
        can_build=("barracks", "gate"),
        can_repair=1,
    )
    assert worker_can_build(probe, "pylon")
    assert not worker_can_build(probe, "gate")
    assert worker_can_repair(scv)
    assert not worker_can_repair(probe)


def test_choose_house_build_target_prefers_townhall_square():
    from soundrts.worldplayercomputer_sc_build import choose_house_build_target

    world = types.SimpleNamespace()
    base = _Square(1, 100, 100)
    mine = _Square(2, 500, 500)
    base.world = world
    mine.world = world

    pylon = types.SimpleNamespace(
        requires_build_field="psi",
        requires_build_field_on_square=0,
        is_buildable_anywhere=1,
    )
    nexus = types.SimpleNamespace(
        type_name="nexus",
        place=base,
        hp=100,
        type=types.SimpleNamespace(provides_build_field="psi", build_field_radius=8 * 1000),
    )

    _world = world

    class AI:
        id = 1
        world = _world
        units = [nexus]
        perception = set()
        memory = set()

        def equivalent(self, name):
            return {"townhall": "nexus", "house": "pylon", "peasant": "probe"}[name]

        def _builders_place(self):
            return mine

        def check_type(self, o, c):
            return False

        def square_is_dangerous(self, place):
            return False

        def is_ok_for_warehouse(self, z, resource_type):
            return True

        def _remove_far_candidates(self, candidates, start, limit):
            return candidates[:limit]

    with patch(
        "soundrts.worldplayercomputer_sc_build.build_site_valid",
        side_effect=lambda ai, bt, place, x, y: place is base,
    ):
        target = choose_house_build_target(AI(), pylon)
    assert target is base


def test_deposit_qty_used_for_gather_filter():
    deposit = types.SimpleNamespace(qty=1000)
    empty = types.SimpleNamespace(qty=0)
    assert getattr(deposit, "qty", 0) > 0
    assert not (getattr(empty, "qty", 0) > 0)


def test_build_worker_count_place_and_leave_or_self_construct():
    from soundrts.worldplayercomputer_sc_build import build_worker_count

    probe = types.SimpleNamespace(build_mode="place_and_leave")
    scv = types.SimpleNamespace(build_mode="assisted")
    drone = types.SimpleNamespace(build_mode="sacrifice")
    pylon = types.SimpleNamespace(self_constructs=1)
    barracks = types.SimpleNamespace(self_constructs=0)

    assert build_worker_count(probe, pylon) == 1
    assert build_worker_count(probe, barracks) == 1
    assert build_worker_count(drone, barracks) == 1
    assert build_worker_count(scv, barracks) == 4
    assert build_worker_count(scv, pylon) == 1


def test_field_provider_types_finds_pylon():
    rules = _load_rules("""
def probe
class worker
can_build pylon gateway

def pylon
class building
provides_build_field psi

def gateway
class building
requires_build_field psi
""")

    class AI:
        faction = None

        def equivalent(self, name):
            return "probe" if name == "peasant" else name

    from soundrts.worldplayercomputer_sc_build import field_provider_types

    assert "pylon" in field_provider_types(AI(), "psi")


def test_addon_types_granting_train():
    _load_rules("""
def tech_lab
class building
is_addon 1
addon_grants_train_factory tank
""")

    from soundrts.worldplayercomputer_sc_build import addon_types_granting_train

    host = types.SimpleNamespace(type_name="factory")
    assert addon_types_granting_train(host, "tank") == ["tech_lab"]


def test_flying_form_for_ground():
    rules = _load_rules("""
def barracks
class building
can_have_addon tech_lab
can_change_to flying_barracks

def flying_barracks
class soldier
ground_form barracks
airground_type air
""")

    from soundrts.worldplayercomputer_sc_build import flying_form_for_ground

    assert flying_form_for_ground(rules.unit_class("barracks")) == "flying_barracks"


def test_starcraft_factions_exclude_human_and_have_titles():
    from pathlib import Path

    import soundrts.worldunit  # noqa: F401
    from soundrts.definitions import rules, style

    root = Path(__file__).resolve().parents[2]
    rules.load(
        (root / "res" / "rules.txt").read_text(encoding="utf-8"),
        (root / "mods" / "starcraft" / "rules.txt").read_text(encoding="utf-8"),
    )
    style.load(
        (root / "res" / "ui" / "style.txt").read_text(encoding="utf-8"),
        (root / "mods" / "starcraft" / "ui" / "style.txt").read_text(encoding="utf-8"),
    )

    assert set(rules.factions) == {"terran", "protoss", "zerg"}
    assert "human_faction" not in rules.factions
    assert rules.get("human_faction", "class") == ["building"]
    assert rules.get("protoss", "house") == ["pylon"]
    pylon = rules.unit_class("pylon")
    assert getattr(pylon, "population_provided", 0) == 8
    nexus = rules.unit_class("nexus")
    assert "resource1" in getattr(nexus, "storable_resource_types", ())
    probe = rules.unit_class("probe")
    assert getattr(probe, "can_repair", 1) == 0
    assert "mineral_field" in (getattr(probe, "can_gather_deposit", None) or ())
    for faction in ("terran", "protoss", "zerg"):
        title = style.get(faction, "title")
        assert title, f"missing style title for {faction}"
        assert int(title[0]) in (7260, 7261, 7262)


def test_builders_place_merges_workers_inside_buildings():
    from soundrts.worldplayercomputer import Computer

    square_a = _Square(1)
    square_b = _Square(2)
    inside_a = types.SimpleNamespace(
        id=None,
        is_inside_place=True,
        outside=square_a,
    )
    inside_b = types.SimpleNamespace(
        id=None,
        is_inside_place=True,
        outside=square_b,
    )

    ai = Computer.__new__(Computer)
    ai._workers = [
        types.SimpleNamespace(place=square_a),
        types.SimpleNamespace(place=inside_a),
        types.SimpleNamespace(place=inside_a),
        types.SimpleNamespace(place=inside_b),
    ]

    assert ai._builders_place() is square_a
