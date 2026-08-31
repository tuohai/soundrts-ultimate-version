"""Rules-driven projectile bounce (Mutalisk-style)."""
from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import MagicMock

from soundrts.combat.bounce import (
    BounceMixin,
    scale_bounce_damage,
)
from soundrts.lib.nofloat import PRECISION
from soundrts.worldunit import Creature


def test_scale_bounce_damage_mutalisk_9_3_1():
    assert scale_bounce_damage(9, 33, 0) == 9
    assert scale_bounce_damage(9, 33, 1) == 3
    assert scale_bounce_damage(9, 33, 2) == 1
    assert scale_bounce_damage(9, 100, 2) == 9
    assert scale_bounce_damage(9, 33, 3) == 0


def test_soldier_has_bounce_rule_attrs():
    from soundrts.worldunit.worldsoldier import Soldier

    for name in (
        "rdg_bounce",
        "rdg_bounce_range",
        "rdg_bounce_decay",
        "mdg_bounce",
        "mdg_bounce_range",
        "mdg_bounce_decay",
    ):
        assert hasattr(Soldier, name), name


def test_rules_apply_rdg_bounce_on_soldier(caplog):
    from soundrts.definitions import Rules

    caplog.set_level(logging.WARNING)
    r = Rules()
    r.load(
        """
def dummy_muta
class soldier
rdg_bounce 2
rdg_bounce_range 3
rdg_bounce_decay 33
"""
    )
    assert not any(
        "rdg_bounce" in rec.getMessage() for rec in caplog.records
    ), [rec.getMessage() for rec in caplog.records if "rdg_bounce" in rec.getMessage()]
    cls = r.unit_class("dummy_muta")
    assert cls is not None
    assert int(cls.rdg_bounce) == 2
    assert int(cls.rdg_bounce_range) == 3 * PRECISION
    assert int(cls.rdg_bounce_decay) == 33


def _creature(name, x, y, place, hp=50, air="ground", uid=1):
    obj = MagicMock(spec=Creature)
    obj.type_name = name
    obj.expanded_is_a = ()
    obj.x = x
    obj.y = y
    obj.hp = hp
    obj.airground_type = air
    obj.id = uid
    obj.place = place
    obj.is_a_building = False
    obj.is_a_unit = True
    obj.receive_hit = MagicMock()
    return obj


def test_bounce_hits_nearest_then_next_with_decay():
    hits = {}

    primary = None
    near = None
    far = None

    place = SimpleNamespace(objects=[], neighbors=())

    attacker_dummy = SimpleNamespace(x=0, y=0)
    primary = _creature("a", 0, 0, place, uid=1)
    near = _creature("b", 500, 0, place, uid=2)
    far = _creature("c", 1500, 0, place, uid=3)
    out = _creature("d", 5000, 0, place, uid=4)
    place.objects = [attacker_dummy, primary, near, far, out]

    class Dummy(BounceMixin):
        rdg_bounce = 2
        rdg_bounce_range = 2000
        rdg_bounce_decay = 33
        rdg_range = 4000
        rdg_targets = ["ground", "air"]
        x = 0
        y = 0
        place = None

        def is_an_enemy(self, obj):
            return obj not in (self, attacker_dummy)

        def _get_ranged_damage_vs(self, target):
            return 9

    attacker = Dummy()
    attacker.place = place
    place.objects[0] = attacker

    attacker.apply_projectile_bounce(primary, is_melee=False)

    assert near.receive_hit.call_count == 1
    assert far.receive_hit.call_count == 1
    assert out.receive_hit.call_count == 0
    assert primary.receive_hit.call_count == 0
    assert near.receive_hit.call_args[0][0] == 3
    assert far.receive_hit.call_args[0][0] == 1


def test_bounce_skips_air_when_rdg_targets_ground():
    place = SimpleNamespace(objects=[], neighbors=())
    primary = _creature("a", 0, 0, place, uid=1)
    flyer = _creature("b", 200, 0, place, uid=2, air="air")
    ground = _creature("c", 400, 0, place, uid=3)
    place.objects = [primary, flyer, ground]

    class Dummy(BounceMixin):
        rdg_bounce = 1
        rdg_bounce_range = 2000
        rdg_bounce_decay = 100
        rdg_targets = ["ground"]
        x = 0
        y = 0
        place = None

        def is_an_enemy(self, obj):
            return obj is not self

        def _get_ranged_damage_vs(self, target):
            return 10

    attacker = Dummy()
    attacker.place = place
    attacker.apply_projectile_bounce(primary, is_melee=False)
    assert flyer.receive_hit.call_count == 0
    assert ground.receive_hit.call_count == 1
    assert ground.receive_hit.call_args[0][0] == 10


def test_bounce_off_when_count_zero():
    place = SimpleNamespace(objects=[], neighbors=())
    primary = _creature("a", 0, 0, place, uid=1)
    other = _creature("b", 100, 0, place, uid=2)
    place.objects = [primary, other]

    class Dummy(BounceMixin):
        rdg_bounce = 0
        rdg_bounce_range = 2000
        rdg_bounce_decay = 33
        rdg_targets = ["ground"]
        place = None

        def is_an_enemy(self, obj):
            return True

        def _get_ranged_damage_vs(self, target):
            return 9

    Dummy().apply_projectile_bounce(primary, is_melee=False)
    assert other.receive_hit.call_count == 0
