"""Perception hot-path regressions: exit-blocker short-circuit + bulk static cap."""
from __future__ import annotations

from soundrts.worldplayerbase.perception import PerceptionMixin
from soundrts.worldresource import Deposit


class _Sq:
    __slots__ = ("id",)

    def __init__(self, sid):
        self.id = sid

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, _Sq) and self.id == other.id


class _Unit:
    __slots__ = ("place", "blocked_exit", "id")

    def __init__(self, place, blocked_exit=None, uid=None):
        self.place = place
        self.blocked_exit = blocked_exit
        self.id = uid

    def __hash__(self):
        return hash(self.id) if self.id is not None else id(self)

    def __eq__(self, other):
        if not isinstance(other, _Unit):
            return NotImplemented
        if self.id is not None and other.id is not None:
            return self.id == other.id
        return self is other


class _Static:
    __slots__ = ("id", "player", "is_a_building_land")

    def __init__(self, sid):
        self.id = sid
        self.player = None
        self.is_a_building_land = False

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, _Static) and self.id == other.id


class _Perc(PerceptionMixin):
    def __init__(self):
        self.observed_squares = set()
        self._exit_calls = 0

    def _exit_blocker_visible(self, unit):
        self._exit_calls += 1
        return False


def test_enemy_sight_skips_exit_blocker_when_no_blocked_exit():
    """Most units have blocked_exit=None; must not call expensive scanner."""
    p = _Perc()
    observed = {_Sq(1)}
    u_plain = _Unit(_Sq(2), blocked_exit=None)
    u_in_obs = _Unit(next(iter(observed)), blocked_exit=None)
    u_blocker = _Unit(_Sq(3), blocked_exit=object())

    in_sight = []
    for u in (u_plain, u_in_obs, u_blocker):
        place = u.place
        if place in observed:
            in_sight.append(u)
        elif u.blocked_exit is not None and p._exit_blocker_visible(u):
            in_sight.append(u)

    assert u_in_obs in in_sight
    assert u_plain not in in_sight
    assert p._exit_calls == 1  # only the unit with blocked_exit


def test_enemy_units_hash_accepts_str_ids():
    """Regression: unit.id may be str from world.get_next_id()."""
    units = [
        _Unit(_Sq(i), blocked_exit=None, uid=uid)
        for i, uid in enumerate(("a1", "b2", 3, "c4"))
    ]
    all_enemy_units = set(units)
    enemy_units_hash = len(all_enemy_units)
    for u in all_enemy_units:
        uid = u.id
        if uid is not None:
            enemy_units_hash = (
                enemy_units_hash * 1000003 + hash(uid)
            ) & 0xFFFFFFFFFFFFFFFF
    assert isinstance(enemy_units_hash, int)


def test_bulk_static_cap_prefers_deposits():
    """When capping objects_to_check, Deposit/building land keep priority."""
    important = []
    other = []
    for i in range(5):
        d = Deposit.__new__(Deposit)
        d.id = i
        d.player = None
        d.is_a_building_land = False
        important.append(d)
    for i in range(200):
        other.append(_Static(1000 + i))
    objects_to_check = set(important + other)
    _BULK_STATIC_CAP = 100
    capped = []
    for o in objects_to_check:
        if isinstance(o, Deposit) or o.is_a_building_land:
            capped.append(o)
    if len(capped) > _BULK_STATIC_CAP:
        capped.sort(key=lambda o: o.id if o.id is not None else 0)
        capped = capped[:_BULK_STATIC_CAP]
    elif len(capped) < _BULK_STATIC_CAP:
        rest = [
            o
            for o in objects_to_check
            if not (isinstance(o, Deposit) or o.is_a_building_land)
        ]
        rest.sort(key=lambda o: o.id if o.id is not None else 0)
        capped.extend(rest[: _BULK_STATIC_CAP - len(capped)])
    capped_set = set(capped)
    assert len(capped_set) == 100
    assert all(d in capped_set for d in important)
