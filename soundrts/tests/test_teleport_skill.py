# -*- coding: utf-8 -*-
"""Teleport (a_passe_muraille) must not crash when allies are already at dest."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from soundrts.worldentity import Entity
from soundrts.worldskill import Skill
from soundrts.worldunit.worldcreature import Creature


def test_creature_move_to_same_place_with_none_coords():
    """Skill teleport calls move_to(place, None, None); same-place must not subtract None."""
    unit = Creature.__new__(Creature)
    dest = object()
    unit.place = dest
    unit.x = 1000
    unit.y = 2000
    unit.charge_mdg_dist = 0
    unit.charge_rdg_dist = 0
    seen = {}

    def _entity_move_to(self, place, x, y, o=90):
        seen["args"] = (place, x, y, o)

    with patch.object(Entity, "move_to", _entity_move_to):
        unit.move_to(dest, None, None)

    assert seen["args"][0] is dest
    assert seen["args"][1] is None
    assert seen["args"][2] is None


def test_teleport_skips_allies_already_at_destination():
    player = object()
    dest = SimpleNamespace()
    dest.can_receive = lambda ag, unit=None: True
    origin = SimpleNamespace()
    origin.can_receive = lambda ag, unit=None: True

    caster = SimpleNamespace(
        x=0,
        y=0,
        player=player,
        place=origin,
        airground_type="ground",
        is_teleportable=True,
    )
    caster.move_to = lambda place, x, y: setattr(caster, "place", place)
    already = SimpleNamespace(
        x=10,
        y=10,
        player=player,
        place=dest,
        airground_type="ground",
        is_teleportable=True,
        moved=False,
    )
    traveler = SimpleNamespace(
        x=0,
        y=0,
        player=player,
        place=origin,
        airground_type="ground",
        is_teleportable=True,
        moved=False,
    )

    def _move_to(place, x, y):
        traveler.moved = True
        traveler.place = place

    already.move_to = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("already-at-dest unit must not move_to")
    )
    traveler.move_to = _move_to

    world = SimpleNamespace(
        get_objects=lambda x, y, r, filter=None: [
            u for u in (caster, already, traveler) if filter(u)
        ]
    )
    assert Skill._execute_teleportation(caster, dest, world) is True
    assert traveler.moved
    assert traveler.place is dest
    assert already.place is dest
