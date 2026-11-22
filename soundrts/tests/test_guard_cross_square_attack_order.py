"""Regression tests: guard units must obey an explicit cross-square attack order.

Reproduces the bug reported on save ``save_1795266725`` (AoE2 Joan of Arc
chapter 2): the player ordered the whole army in square ``j5`` (9,4) to
attack the English castle in ``k5`` (10,4).  Seven units (5 militia + 2
archers) refused to move, while the UI announced "攻击 城堡 , 去 到 k , 5".

Three independent engine bugs were involved; each is covered here:

1. ``formation_stand_ground`` vetoed the *explicit* attack order, so the
   unit never even started walking to the neighbouring square.
2. The guard counterattack loop kept re-creating an ``AttackAction`` on a
   distant attacker it could never reach.  Because ``update()`` skips
   ``_execute_orders()`` while an ``AttackAction`` is running, the player's
   order queue was starved forever.
3. Even inside the target's own square, a stand-ground unit whose target
   was out of weapon range only *turned* towards it and never closed the
   distance — so a melee unit stood there announcing "attacking castle"
   while dealing zero damage.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from soundrts.world_formation import formation_stand_ground
from soundrts.worldunit.world_ai_decision import CreatureAIDecision
from soundrts.worldunit.world_movement import CreatureMovement


ROOT = Path(__file__).resolve().parents[2]


def _square(name, col, row):
    return SimpleNamespace(
        id=name,
        name=name,
        col=col,
        row=row,
        objects=[],
        neighbors=[],
        strict_neighbors=[],
        exits=[],
        high_ground=False,
    )


def _target(tid, place, x, y, hp=100, radius=200, type_name="aoe_castle"):
    return SimpleNamespace(
        id=tid,
        place=place,
        x=x,
        y=y,
        hp=hp,
        hp_max=hp,
        radius=radius,
        type_name=type_name,
        is_creature=True,
        is_vulnerable=True,
        menace=10,
        expanded_is_a=(),
        airground_type="ground",
    )


def _guard_unit(uid, place, x=0, y=0, **extra):
    """A minimal stand-ground (guard) unit."""
    data = dict(
        id=uid,
        place=place,
        x=x,
        y=y,
        o=90,
        hp=40,
        hp_max=40,
        speed=900,
        radius=175,
        ai_mode="guard",
        agro_on_sight=1,
        counterattack_enabled=True,
        mdg=4000,
        mdg_range=1000,
        rdg=0,
        rdg_range=0,
        airground_type="ground",
        collision=True,
        type_name=uid,
        expanded_is_a=(),
        is_creature=True,
        is_vulnerable=True,
        menace=5,
        minimal_damage=0,
        mdg_projectile=0,
        rdg_projectile=0,
        last_attacker=None,
        action=None,
        action_target=None,
        orders=[],
        walked=[],
        is_moving=False,
        _formation_slot=None,
        _formation_focus_fire=0,
        can_fire_on_move=0,
    )
    data.update(extra)
    unit = SimpleNamespace(**data)
    unit._collision_range = lambda other: unit.radius + other.radius
    unit._target_in_own_square = lambda t: CreatureMovement._target_in_own_square(unit, t)
    unit._close_in_on_target = lambda t: CreatureMovement._close_in_on_target(unit, t)

    def _default_near_enough_to_aim(t):
        dist = ((unit.x - t.x) ** 2 + (unit.y - t.y) ** 2) ** 0.5
        reach = max(unit.mdg_range or 0, unit.rdg_range or 0)
        return dist <= reach

    unit._near_enough_to_aim = _default_near_enough_to_aim
    unit.get_effective_mdg_range = lambda t: unit.mdg_range or 0
    unit.get_effective_rdg_range = lambda t: unit.rdg_range or 0
    unit.aim = lambda t: None
    unit._reach = lambda d: None
    unit._weapon_reach_for = lambda t: CreatureMovement._weapon_reach_for(unit, t)
    unit._slot_can_reach_target = lambda s, t: CreatureMovement._slot_can_reach_target(unit, s, t)
    return unit


# ---------------------------------------------------------------------------
# 1. An explicit cross-square order must not be vetoed by stand ground
# ---------------------------------------------------------------------------


def test_stand_ground_allows_explicit_cross_square_target(monkeypatch):
    """A guard unit ordered to attack a target in another square must walk."""
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    here = _square("9,4", 9, 4)
    there = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here)
    castle = _target("castle", there, 63000, 27000)

    # Without a target the unit keeps its stand-ground (fire, never walk).
    assert formation_stand_ground(unit) is True
    # With an explicit cross-square target the veto is lifted.
    assert formation_stand_ground(unit, castle) is False


def test_stand_ground_keeps_same_square_target_veto(monkeypatch):
    """A target on the unit's own square still stands ground."""
    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)
    here = _square("9,4", 9, 4)
    unit = _guard_unit("militia", here)
    nearby = _target("tower", here, 60000, 27000)

    assert formation_stand_ground(unit, nearby) is True


# ---------------------------------------------------------------------------
# 2. The guard counterattack must not lock the order queue
# ---------------------------------------------------------------------------


def test_guard_counterattack_requires_reachable_attacker():
    """A guard unit must not counterattack an attacker it cannot reach.

    Otherwise it holds an ``AttackAction`` forever, and ``update()`` skips
    ``_execute_orders()`` while an ``AttackAction`` runs — so the player's
    own attack/go orders are never executed.
    """
    here = _square("9,4", 9, 4)
    there = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here, x=57000, y=27000)
    distant = _target("scouttower", there, 63000, 27000, type_name="scouttower")

    unit._near_enough_to_aim = lambda t: False
    unit.last_attacker = distant

    assert CreatureAIDecision._can_reach_attacker(unit, distant) is False
    # The unreachable attacker is forgotten so no dead-end action is rebuilt.
    assert unit.last_attacker is None


def test_guard_counterattack_allowed_for_same_square_attacker():
    here = _square("9,4", 9, 4)
    unit = _guard_unit("militia", here)
    attacker = _target("militia2", here, 59000, 27000, type_name="militia")

    unit._near_enough_to_aim = lambda t: False
    unit.last_attacker = attacker

    assert CreatureAIDecision._can_reach_attacker(unit, attacker) is True
    assert unit.last_attacker is attacker


def test_guard_counterattack_allowed_when_target_in_weapon_range():
    """An archer may shoot a tower in the next square."""
    here = _square("9,4", 9, 4)
    there = _square("10,4", 10, 4)
    unit = _guard_unit("archer", here, x=57000, y=27000)
    tower = _target("scouttower", there, 60000, 27000, type_name="scouttower")

    unit._near_enough_to_aim = lambda t: True
    unit.last_attacker = tower

    assert CreatureAIDecision._can_reach_attacker(unit, tower) is True
    assert unit.last_attacker is tower


def test_can_reach_attacker_is_conservative_when_range_unknown():
    """If reachability cannot be determined the old behaviour is kept."""
    here = _square("9,4", 9, 4)
    there = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here)
    distant = _target("scouttower", there, 63000, 27000, type_name="scouttower")
    unit.last_attacker = distant
    # No ``_near_enough_to_aim`` at all -> cannot tell -> keep old behaviour.
    del unit._near_enough_to_aim
    assert CreatureAIDecision._can_reach_attacker(unit, distant) is True


# ---------------------------------------------------------------------------
# 3. A stand-ground unit must close the distance to a same-square target
# ---------------------------------------------------------------------------


def test_stand_ground_unit_closes_in_on_same_square_target(monkeypatch):
    """A melee unit facing a castle on its own square must walk into range.

    Regression for "显示正在攻击城堡但实际没有攻击": the unit used to only
    turn towards the out-of-range target and never close the gap, so it
    dealt no damage at all while the interface announced "attacking castle".
    """
    from soundrts.worldunit.world_movement import CreatureMovement

    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)

    here = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here, x=54000, y=27000)
    castle = _target("castle", here, 63000, 27000, radius=175)

    reached = []

    def fake_reach(distance):
        reached.append(distance)
        unit.x += 3000
        return True

    unit._reach = fake_reach
    unit.aim = lambda t: reached.append("aim")
    unit.action_target = castle

    CreatureMovement.action_reach_and_aim(unit)

    # It must have tried to walk (not merely turned).
    assert reached, "stand-ground unit must close the gap to its target"
    assert "aim" not in reached, "must not fire while out of weapon range"


def test_stand_ground_unit_fires_when_target_already_in_range():
    from soundrts.worldunit.world_movement import CreatureMovement

    here = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here, x=63000, y=27000)
    castle = _target("castle", here, 63200, 27000, radius=175)

    aimed = []
    unit._near_enough_to_aim = lambda t: True
    unit.aim = lambda t: aimed.append(t)
    unit._reach = lambda d: pytest.fail("must not walk when already in range")
    unit.action_target = castle

    CreatureMovement.action_reach_and_aim(unit)

    assert aimed == [castle]


def test_stand_ground_unit_does_not_chase_into_other_squares(monkeypatch):
    """Stand ground still means "do not chase into another square"."""
    from soundrts.worldunit.world_movement import CreatureMovement

    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)

    here = _square("9,4", 9, 4)
    there = _square("10,4", 10, 4)
    unit = _guard_unit("militia", here, x=57000, y=27000)
    distant = _target("scouttower", there, 63000, 27000, type_name="scouttower")

    unit._near_enough_to_aim = lambda t: False
    unit._reach = lambda d: pytest.fail("must not walk towards another square")
    unit.aim = lambda t: pytest.fail("must not fire out of range")
    unit.action_target = distant

    CreatureMovement.action_reach_and_aim(unit)


# ---------------------------------------------------------------------------
# 4. A formation slot must never freeze a unit out of weapon range
# ---------------------------------------------------------------------------


def test_formation_slot_out_of_range_unit_closes_in(monkeypatch):
    """A unit whose formation slot is out of weapon range must close in.

    Regression for "骑士 4 在 11,5, 攻击 城堡 ... 但什么也没做":
    ``apply_combat_formation`` lays the melee rank out along a line, so the
    units at the ends of the line sit several metres from the castle -- far
    outside their own ``mdg_range``.  The formation-slot branch of
    ``action_reach_and_aim`` used to make such a unit merely turn towards
    the target and return, so it stood there for ever announcing
    "attacking castle" while dealing zero damage.
    """
    from soundrts.worldunit.world_movement import CreatureMovement

    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)

    here = _square("11,4", 11, 4)
    unit = _guard_unit("knight", here, x=139700, y=54000, ai_mode="offensive",
                       mdg_range=1000)
    castle = _target("castle", here, 142200, 54000, radius=175)

    # The unit has ARRIVED on its slot, but the slot is out of its range.
    unit._formation_slot = (here, 139700, 54000)
    unit._formation_focus_fire = 0
    unit.action_target = castle

    reached = []
    unit._reach = lambda d: reached.append(d)
    unit.aim = lambda t: pytest.fail("must not fire out of weapon range")

    CreatureMovement.action_reach_and_aim(unit)

    assert reached, "a unit out of range on its slot must walk towards the target"


def test_formation_slot_in_range_unit_fires(monkeypatch):
    """A unit whose slot IS in weapon range keeps holding the formation."""
    from soundrts.worldunit.world_movement import CreatureMovement

    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)

    here = _square("11,4", 11, 4)
    unit = _guard_unit("knight", here, x=142100, y=54000, ai_mode="offensive",
                       mdg_range=1000)
    castle = _target("castle", here, 142200, 54000, radius=175)

    unit._formation_slot = (here, 142100, 54000)
    unit._formation_focus_fire = 0
    unit.action_target = castle

    aimed = []
    unit._reach = lambda d: pytest.fail("must not walk when the slot is in range")
    unit.aim = lambda t: aimed.append(t)

    CreatureMovement.action_reach_and_aim(unit)

    assert aimed == [castle]


def test_slot_can_reach_target_uses_weapon_reach():
    """``_slot_can_reach_target`` must compare against the real reach."""
    from soundrts.worldunit.world_movement import CreatureMovement

    here = _square("11,4", 11, 4)
    unit = _guard_unit("knight", here, x=139700, y=54000, ai_mode="offensive",
                       mdg_range=1000)
    castle = _target("castle", here, 142200, 54000, radius=175)

    unit.get_effective_mdg_range = lambda t: 1000
    unit.get_effective_rdg_range = lambda t: 0

    # 2500mm away, reach is mdg_range + collision (1000 + 175 + 175)
    assert CreatureMovement._slot_can_reach_target(unit, (139700, 54000), castle) is False
    # 1200mm away -> inside the reach
    assert CreatureMovement._slot_can_reach_target(unit, (141000, 54000), castle) is True


def test_ranged_unit_in_range_slot_is_not_pulled_forward(monkeypatch):
    """Archers must stay on their slot: their range already covers it."""
    from soundrts.worldunit.world_movement import CreatureMovement

    monkeypatch.setattr("soundrts.world_formation.formations_enabled", lambda: True)

    here = _square("11,4", 11, 4)
    unit = _guard_unit("archer", here, x=139214, y=55026, ai_mode="offensive",
                       mdg_range=0, rdg_range=5000)
    castle = _target("castle", here, 142200, 54000, radius=175)

    unit.get_effective_mdg_range = lambda t: 0
    unit.get_effective_rdg_range = lambda t: 5000
    unit._formation_slot = (here, 139214, 55026)
    unit._formation_focus_fire = 0
    unit.action_target = castle

    unit._reach = lambda d: pytest.fail("a ranged unit in range must hold its slot")

    CreatureMovement.action_reach_and_aim(unit)


# ---------------------------------------------------------------------------
# Source-level guards: the fixes must stay in place
# ---------------------------------------------------------------------------


def test_movement_orders_pass_target_to_stand_ground():
    """Both order types must forward the target to the stand-ground check."""
    src = (ROOT / "soundrts" / "worldorders" / "movement.py").read_text(encoding="utf-8")
    assert "formation_stand_ground(self.unit, self.target)" in src


def test_stand_ground_supports_target_argument():
    src = (ROOT / "soundrts" / "world_formation.py").read_text(encoding="utf-8")
    assert "def formation_stand_ground(unit, target=None)" in src
