"""get_object_by_id must not scan fog memory for live object ids."""
from __future__ import annotations

from soundrts.worldplayerbase.base import Player


class _World:
    def __init__(self):
        self.grid = {}
        self.objects = {}
        self.name_to_square = {}


class _Unit:
    def __init__(self, uid, place="here"):
        self.id = uid
        self.place = place


class _Mem:
    def __init__(self, uid, initial_model):
        self.id = uid
        self.initial_model = initial_model
        self.place = "fog"


class _P(Player):
    def __init__(self):
        self.world = _World()
        self.perception = set()
        self.memory = set()
        self._memory_index = {}


def test_live_perceived_unit_is_o1():
    p = _P()
    u = _Unit("42")
    p.world.objects["42"] = u
    p.perception.add(u)
    assert p.get_object_by_id("42") is u


def test_live_unperceived_unit_uses_memory_index_not_scan():
    p = _P()
    u = _Unit("42")
    ghost = _Mem("42", u)
    p.world.objects["42"] = u
    p._memory_index[u] = ghost
    # Thousands of unrelated ghosts must not be visited.
    p.memory = {_Mem(str(i), _Unit(str(i))) for i in range(5000)}
    p.memory.add(ghost)
    assert p.get_object_by_id("42") is ghost


def test_a1_square_alias_still_resolves():
    p = _P()
    sq = object()
    p.world.grid["0,0"] = sq
    assert p.get_object_by_id("a1") is sq


def test_comma_one_based_coords_still_resolve():
    p = _P()
    sq = object()
    p.world.grid["1,2"] = sq
    assert p.get_object_by_id("2,3") is sq
