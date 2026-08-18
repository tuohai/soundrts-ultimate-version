"""Worker default order on damaged buildings must be repair, not go."""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.worldunit.worldcreature import BuildingSite
from soundrts.worldunit.worldsoldier import Soldier
from soundrts.worldunit.worldworker import Worker


class _TestWorker(Worker):
    _test_can_build = ("townhall",)

    @property
    def can_build(self):
        return self._test_can_build


class _TestSoldier(Soldier):
    @property
    def can_build(self):
        return ()


class _OwnPlayer:
    allied = None

    def __init__(self):
        self.allied = [self]

    def player_is_an_enemy(self, other):
        return other is not None and other not in self.allied


class _DamagedBuilding:
    is_repairable = True
    is_a_building = True
    is_an_exit = False
    herdable = 0
    hp = 40
    hp_max = 100
    resource_type = None

    def __init__(self, owner):
        self.player = owner

    def have_enough_space(self, _unit):
        return False


def _make_worker(target):
    worker = _TestWorker.__new__(_TestWorker)
    worker._basic_skills = {
        "go",
        "attack",
        "herd",
        "gather",
        "repair",
        "block",
        "join_group",
        "pickup",
        "drop",
    }
    worker.orders = []
    worker.can_repair = 1
    worker._test_can_build = ("townhall",)
    worker.can_herd = 0
    worker.world = None
    owner = _OwnPlayer()
    worker.player = owner
    worker.is_an_enemy = lambda other: getattr(other, "player", None) is not owner
    worker.player.get_object_by_id = lambda _id: target
    target.player = owner
    return worker


def test_worker_default_order_on_damaged_building_is_repair():
    b = _DamagedBuilding(None)
    worker = _make_worker(b)
    assert worker.get_default_order(1) == "repair"


def test_worker_default_order_on_intact_building_is_go():
    b = _DamagedBuilding(None)
    b.hp = b.hp_max
    worker = _make_worker(b)
    assert worker.get_default_order(1) == "go"


def test_worker_default_order_on_enemy_damaged_building_is_go():
    enemy = _OwnPlayer()
    b = _DamagedBuilding(enemy)
    worker = _make_worker(b)
    b.player = enemy
    assert worker.get_default_order(1) == "go"


def test_worker_without_can_repair_defaults_to_go():
    b = _DamagedBuilding(None)
    worker = _make_worker(b)
    worker.can_repair = 0
    assert worker.get_default_order(1) == "go"


def test_worker_default_order_on_building_site_is_repair():
    site = BuildingSite.__new__(BuildingSite)
    site.type = types.SimpleNamespace(__name__="townhall")
    site.hp = 5
    site.hp_max = 100
    site.is_repairable = True
    site.is_an_exit = False
    site.herdable = 0
    site.resource_type = None
    site.have_enough_space = lambda _u: False
    worker = _make_worker(site)
    assert worker.get_default_order(1) == "repair"


def test_soldier_default_order_on_damaged_building_is_go():
    b = _DamagedBuilding(None)
    soldier = _TestSoldier.__new__(_TestSoldier)
    soldier._basic_skills = {"go", "attack", "block", "join_group"}
    soldier.orders = []
    soldier.world = None
    owner = _OwnPlayer()
    soldier.player = owner
    soldier.is_an_enemy = lambda other: False
    b.player = owner
    soldier.player.get_object_by_id = lambda _id: b
    assert soldier.get_default_order(1) == "go"
