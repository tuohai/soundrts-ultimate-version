"""squares_to_watch must not rescan every fog tree on each explorer."""

import types

from soundrts.worldplayerbase.perception import PerceptionMixin
from soundrts.worldresource import Deposit


class _Sq:
    def __init__(self, sid, name=None):
        self.id = sid
        self.name = name or str(sid)
        self.exits = []
        self.is_inside_place = False

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, _Sq) and self.id == other.id


class _Exit:
    def __init__(self, dest):
        self.other_side = types.SimpleNamespace(place=dest)


class _Tree(Deposit):
    is_deposit = True

    def __init__(self, tid, place):
        self.id = tid
        self.place = place
        self.player = None
        self.initial_model = self
        self.time_stamp = 0


class _Enemy:
    is_deposit = False

    def __init__(self, uid, place, player):
        self.id = uid
        self.place = place
        self.player = player
        self.initial_model = self
        self.time_stamp = 0


class _Player(PerceptionMixin):
    def __init__(self, memory, world, allied=()):
        self.memory = set(memory)
        self.world = world
        self.allied = allied
        self._memory_by_place = None
        self._memory_by_place_count = -1
        self._memory_unit_by_place = None
        self._enemy_player_cache = {}
        self._enemy_player_timestamp = None
        self._squares_to_watch_cache = None

    def unit_under_allied_control(self, o):
        return False

    def player_is_an_enemy(self, p):
        return p not in self.allied and p is not self

    def is_an_enemy(self, o):
        p = getattr(o, "player", None)
        if p is None:
            return False
        if self.unit_under_allied_control(o):
            return False
        return self.player_is_an_enemy(p)


def test_squares_to_watch_one_square_for_many_trees():
    forest = _Sq(1, "a1")
    trees = [_Tree(i, forest) for i in range(50)]
    rng = types.SimpleNamespace(sample=lambda seq, n: list(seq))
    world = types.SimpleNamespace(time=1000, random=rng)
    p = _Player(trees, world)
    watched = p.squares_to_watch
    assert watched == [forest]
    # same tick: no rebuild
    assert p.squares_to_watch is watched


def test_squares_to_watch_enemy_adds_neighbor():
    here = _Sq(1, "a1")
    nxt = _Sq(2, "b1")
    here.exits = [_Exit(nxt)]
    foe_player = object()
    enemy = _Enemy(9, here, foe_player)
    rng = types.SimpleNamespace(sample=lambda seq, n: list(seq))
    world = types.SimpleNamespace(time=7, random=rng)
    p = _Player([enemy], world)
    watched = set(p.squares_to_watch)
    assert watched == {here, nxt}


def test_squares_to_watch_skips_inside_place():
    inside = _Sq(1, "in")
    inside.is_inside_place = True
    tree = _Tree(1, inside)
    rng = types.SimpleNamespace(sample=lambda seq, n: list(seq))
    world = types.SimpleNamespace(time=3, random=rng)
    p = _Player([tree], world)
    assert p.squares_to_watch == []
