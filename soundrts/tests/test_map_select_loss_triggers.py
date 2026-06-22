"""序号格式失败条件：unit_lost / building_lost / key_unit_killed。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.worldplayerbase.triggers import TriggersMixin


class _StubWorld:
    def __init__(self, players):
        self.players = players
        self.ex_players = []
        self.grid = {}
        self.squares = []
        self.time = 0
        for p in players:
            p.world = self


class _StubPlayer:
    def __init__(self, player_id="h1"):
        self.id = player_id
        self.units = []
        self.allied = [self]
        self.world = None


class _StubUnit:
    def __init__(self, player, type_name="footman", unit_id="u1", *, provides_survival=False):
        self.player = player
        self.type_name = type_name
        self.id = unit_id
        self.presence = True
        self.expanded_is_a = []
        self.provides_survival = provides_survival
        self.map_select_square = None
        self.map_select_type = None
        self.map_select_index = None
        self.map_select_global_index = None
        player.units.append(self)


class _TriggerOwner(TriggersMixin, _StubPlayer):
    pass


def _make_owner(world=None):
    owner = _TriggerOwner(player_id="h1")
    world = world or _StubWorld([owner])
    owner.world = world
    return owner


def _assign_slots(owner, square_key, type_name, count):
    units = []
    for idx in range(1, count + 1):
        u = _StubUnit(owner, type_name=type_name, unit_id=f"{type_name}{idx}")
        u.map_select_square = square_key
        u.map_select_type = type_name
        u.map_select_index = idx
        u.map_select_global_index = idx
        units.append(u)
    return units


def _assign_global_slots(owner, type_name, count):
    units = []
    for idx in range(1, count + 1):
        u = _StubUnit(owner, type_name=type_name, unit_id=f"g{type_name}{idx}")
        u.map_select_global_index = idx
        units.append(u)
    return units


def test_unit_lost_map_select_only_specific_unit():
    owner = _make_owner()
    footmen = _assign_slots(owner, "1,1", "footman", 3)

    assert owner.lang_unit_lost(["1,1", "3", "footman"]) is False

    footmen[2].presence = False
    assert owner.lang_unit_lost(["1,1", "3", "footman"]) is True
    assert owner.lang_unit_lost(["1,1", "1", "footman"]) is False


def test_unit_lost_map_select_survives_move():
    owner = _make_owner()
    u3 = _StubUnit(owner, type_name="footman", unit_id="f3")
    u3.map_select_square = "1,1"
    u3.map_select_type = "footman"
    u3.map_select_index = 3

    assert owner.lang_unit_lost(["1,1", "3", "footman"]) is False
    u3.presence = False
    assert owner.lang_unit_lost(["1,1", "3", "footman"]) is True


def test_building_lost_global_only_first_townhall():
    owner = _make_owner()
    th1 = _StubUnit(owner, type_name="townhall", unit_id="th1", provides_survival=True)
    th1.map_select_global_index = 1
    th1.map_select_square = "1,1"
    th1.map_select_index = 1
    th2 = _StubUnit(owner, type_name="townhall", unit_id="th2", provides_survival=True)
    th2.map_select_global_index = 2
    th2.map_select_square = "2,2"
    th2.map_select_index = 1

    assert owner.lang_building_lost(["1", "townhall"]) is False
    assert owner.lang_building_lost(["2", "townhall"]) is False

    th2.presence = False
    owner.units.remove(th2)
    assert owner.lang_building_lost(["2", "townhall"]) is True
    assert owner.lang_building_lost(["1", "townhall"]) is False

    th1.presence = False
    owner.units.remove(th1)
    assert owner.lang_building_lost(["1", "townhall"]) is True


def test_key_unit_killed_global_only_specific_unit():
    owner = _make_owner()
    enemy = _TriggerOwner(player_id="e1")
    owner.world.players.append(enemy)
    enemy.world = owner.world

    victim = _StubUnit(owner, type_name="footman", unit_id="f3")
    victim.map_select_global_index = 3
    victim.killer_id = enemy.id
    enemy.record_unit_killed(victim)

    assert owner.lang_key_unit_killed(["3", "footman"]) is True
    assert owner.lang_key_unit_killed(["1", "footman"]) is False


def test_assign_map_global_select_slot_increments_per_type():
    owner = _make_owner()
    square = types.SimpleNamespace(objects=[], name="1,1")
    owner.world.grid = {"1,1": square}

    u1 = types.SimpleNamespace(type_name="townhall")
    u2 = types.SimpleNamespace(type_name="townhall")
    u3 = types.SimpleNamespace(type_name="barracks")
    owner._assign_map_select_slot(u1, square)
    owner._assign_map_select_slot(u2, square)
    owner._assign_map_select_slot(u3, square)

    assert u1.map_select_global_index == 1
    assert u2.map_select_global_index == 2
    assert u3.map_select_global_index == 1


def test_building_lost_map_select_only_specific_townhall():
    owner = _make_owner()
    th_a1 = _StubUnit(owner, type_name="townhall", unit_id="th1", provides_survival=True)
    th_a1.map_select_square = "1,1"
    th_a1.map_select_type = "townhall"
    th_a1.map_select_index = 1
    th_b1 = _StubUnit(owner, type_name="townhall", unit_id="th2", provides_survival=True)
    th_b1.map_select_square = "2,2"
    th_b1.map_select_type = "townhall"
    th_b1.map_select_index = 1

    assert owner.lang_building_lost(["2,2", "1", "townhall"]) is False
    th_b1.presence = False
    assert owner.lang_building_lost(["2,2", "1", "townhall"]) is True
    assert owner.lang_building_lost(["1,1", "1", "townhall"]) is False

    th_a1.presence = False
    assert owner.lang_building_lost(["1,1", "1", "townhall"]) is True


def test_key_unit_killed_map_select_only_specific_unit():
    owner = _make_owner()
    enemy = _TriggerOwner(player_id="e1")
    owner.world.players.append(enemy)
    enemy.world = owner.world

    victim = _StubUnit(owner, type_name="footman", unit_id="f3")
    victim.map_select_square = "1,1"
    victim.map_select_type = "footman"
    victim.map_select_index = 3
    victim.killer_id = enemy.id

    enemy.record_unit_killed(victim)

    assert owner.lang_key_unit_killed(["1,1", "3", "footman"]) is True
    assert owner.lang_key_unit_killed(["1,1", "1", "footman"]) is False


def test_legacy_unit_lost_and_building_lost_unchanged():
    owner = _make_owner()
    knight = _StubUnit(owner, type_name="knight", unit_id="k1")
    townhall = _StubUnit(owner, type_name="townhall", unit_id="th", provides_survival=True)

    assert owner.lang_unit_lost(["knight"]) is False
    assert owner.lang_building_lost(["townhall"]) is False

    knight.presence = False
    owner.units.remove(knight)
    assert owner.lang_unit_lost(["knight"]) is True

    townhall.presence = False
    owner.units.remove(townhall)
    assert owner.lang_building_lost(["townhall"]) is True


def test_legacy_key_unit_killed_by_type():
    owner = _make_owner()
    enemy = _TriggerOwner(player_id="e1")
    owner.world.players.append(enemy)
    enemy.world = owner.world

    victim = _StubUnit(owner, type_name="raynor", unit_id="r1")
    victim.killer_id = enemy.id
    enemy.record_unit_killed(victim)

    assert owner.lang_key_unit_killed(["raynor"]) is True
    assert owner.lang_key_unit_killed(["knight"]) is False


def test_unit_lost_single_token_still_type_name():
    owner = _make_owner()
    assert owner.lang_unit_lost(["a1"]) is True
