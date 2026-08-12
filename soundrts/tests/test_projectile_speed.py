# -*- coding: utf-8 -*-
"""Split mdg_/rdg_projectile_speed flight time."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION


def _unit(**kwargs):
    from soundrts.combat.attack_action import AttackActionMixin

    class U(AttackActionMixin):
        def _int_distance(self, x1, y1, x2, y2):
            return abs(x2 - x1)

    u = U()
    u.x = u.y = 0
    for k, v in kwargs.items():
        setattr(u, k, v)
    return u


def test_rdg_flight_only_when_rdg_projectile():
    target = SimpleNamespace(x=4 * PRECISION, y=0)
    u = _unit(
        rdg_projectile=1,
        rdg_projectile_speed=7 * PRECISION,
        mdg_projectile=0,
        mdg_projectile_speed=3 * PRECISION,
    )
    assert u._calc_projectile_flight_ms(target, is_melee=False) == 571
    assert u._calc_projectile_flight_ms(target, is_melee=True) == 0


def test_mdg_flight_only_when_mdg_projectile():
    target = SimpleNamespace(x=4 * PRECISION, y=0)
    u = _unit(
        mdg_projectile=1,
        mdg_projectile_speed=4 * PRECISION,
        rdg_projectile=1,
        rdg_projectile_speed=0,
    )
    # 4 tiles / 4 tiles/s * 1000 = 1000 ms
    assert u._calc_projectile_flight_ms(target, is_melee=True) == 1000
    assert u._calc_projectile_flight_ms(target, is_melee=False) == 0


def test_non_projectile_melee_ignores_speed():
    target = SimpleNamespace(x=4 * PRECISION, y=0)
    u = _unit(mdg_projectile=0, mdg_projectile_speed=7 * PRECISION)
    assert u._calc_projectile_flight_ms(target, is_melee=True) == 0


def test_legacy_rdg_delay_migrates_to_rdg_projectile_speed():
    rules.load(
        """
def parameters
nb_of_resource_types 2

def archer
class soldier
rdg_projectile 1
rdg_delay 0.02
"""
    )
    assert rules.get("archer", "rdg_projectile_speed") == 50 * PRECISION


def test_legacy_projectile_speed_maps_by_flag():
    rules.load(
        """
def parameters
nb_of_resource_types 2

def mang
class soldier
mdg_projectile 1
projectile_speed 3.5
"""
    )
    assert rules.get("mang", "mdg_projectile_speed") == int(3.5 * PRECISION)
    assert not rules.get("mang", "rdg_projectile_speed")
