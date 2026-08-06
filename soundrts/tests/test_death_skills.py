"""on_death skill trigger: death-time AoE / chain explode."""
from __future__ import annotations

import types

from soundrts.lib.nofloat import PRECISION, int_distance
from soundrts.worldskill import Skill
from soundrts.worldunit.world_attributes import CreatureAttributes


class _StubPlayer:
    def __init__(self, pid="p1"):
        self.id = pid
        self.neutral = False
        self.is_human = True
        self.observed_objects = {}
        self.perception = set()
        self.stats = types.SimpleNamespace(add=lambda *_a, **_k: None)

    def observe(self, _unit):
        pass

    def player_is_an_enemy(self, other):
        return other is not None and other.id != self.id

    def player_is_a_hostile_enemy(self, other):
        return self.player_is_an_enemy(other)

    def on_unit_attacked(self, _unit, _attacker):
        pass

    def note_combat_with(self, _other):
        pass


class _DeathSkill(Skill):
    type_name = "skill_death_nova"
    auto_trigger = 1
    manual_use = 0
    trigger_timing = "on_death"
    effect = ["harm_area", "40", "6"]
    effect_target = ["self"]
    passive_trigger_rate = 100


def _bind_death_helpers(unit):
    for name in (
        "iter_skills_with_trigger_timing",
        "iter_death_trigger_skill_names",
        "_skill_trigger_timing",
        "_skill_class",
        "_mark_death_skill_done",
        "_death_skill_already_done",
        "_trigger_death_skills",
    ):
        setattr(unit, name, getattr(CreatureAttributes, name).__get__(unit, type(unit)))


def _make_dying_unit(player, *, x=0, y=0, skills=None, is_building=False, world=None, units=None):
    unit = types.SimpleNamespace(
        player=player,
        hp=0,
        hp_max=50 * PRECISION,
        is_vulnerable=True,
        type_name="ammo_depot" if is_building else "bomb_unit",
        is_a_building=is_building,
        expanded_is_a=set(),
        id=id(object()),
        place=types.SimpleNamespace(),
        x=x,
        y=y,
        can_use_skill=list(skills or ()),
        death_trigger_skills=(),
        _buffs=[],
        inside=None,
        airground_type="ground",
        resource_rewards=[0, 0],
        xp_reward=0,
        _has_yielded=False,
        yield_on_defeat=0,
        notifications=[],
        deleted=False,
        _death_effect_fired=False,
        _triggering_skill=False,
        world=world,
    )
    unit.notify = lambda msg: unit.notifications.append(msg)
    unit.is_an_enemy = lambda other: (
        other is not None
        and getattr(other, "player", None) is not None
        and other.player.id != player.id
    )
    unit.delete = lambda: setattr(unit, "deleted", True) or setattr(unit, "place", None)
    unit.reset_charge_state = lambda force=False: None

    def die(attacker=None, notify_death=True):
        if unit.place is None:
            return
        unit.hp = 0
        unit._trigger_death_skills(attacker)
        unit.delete()

    unit.die = die
    _bind_death_helpers(unit)

    skill_map = {_DeathSkill.type_name: _DeathSkill}
    if world is None:
        unit_list = units if units is not None else []

        def get_objects2(cx, cy, r, filter=None, skip_cache=False):
            return [
                u
                for u in unit_list
                if getattr(u, "place", None) is not None
                and int_distance(cx, cy, u.x, u.y) <= r
                and (filter is None or filter(u))
            ]

        world = types.SimpleNamespace(
            time=0,
            treaty_until_time=0,
            random=types.SimpleNamespace(randint=lambda a, b: 1),
            unit_class=lambda name: skill_map.get(name),
            get_objects2=get_objects2,
        )
        unit.world = world
    else:
        unit.world = world

    if units is not None and unit not in units:
        units.append(unit)

    unit._skill_class = lambda name: skill_map.get(name)
    return unit


def test_on_death_harm_area_damages_nearby_enemies():
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []
    depot = _make_dying_unit(
        owner, x=0, y=0, skills=["skill_death_nova"], is_building=True, units=units
    )
    world = depot.world
    near = _make_dying_unit(enemy_p, x=500, y=0, skills=(), world=world, units=units)
    near.hp = 100 * PRECISION
    far = _make_dying_unit(enemy_p, x=20 * PRECISION, y=0, skills=(), world=world, units=units)
    far.hp = 100 * PRECISION
    # far should stay out of radius 6
    far.x = 20 * PRECISION

    depot.die()
    assert depot.deleted is True
    assert near.hp == 60 * PRECISION
    assert far.hp == 100 * PRECISION


def test_unit_without_death_skill_does_not_aoe():
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []
    unit = _make_dying_unit(owner, skills=(), units=units)
    near = _make_dying_unit(enemy_p, x=0, y=0, skills=(), world=unit.world, units=units)
    near.hp = 100 * PRECISION
    unit.die()
    assert near.hp == 100 * PRECISION


def test_chain_death_explosion():
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []
    a = _make_dying_unit(
        owner, x=0, y=0, skills=["skill_death_nova"], units=units
    )
    b = _make_dying_unit(
        enemy_p,
        x=500,
        y=0,
        skills=["skill_death_nova"],
        world=a.world,
        units=units,
    )
    b.hp = 30 * PRECISION  # 40 harm kills B
    c = _make_dying_unit(
        enemy_p,
        x=1000,
        y=0,
        skills=(),
        world=a.world,
        units=units,
    )
    c.hp = 100 * PRECISION

    a.die()
    assert b.deleted is True
    # B's death nova should hit C (distance from B at 500 to C at 1000 is 500 < 6*PRECISION)
    assert c.hp == 60 * PRECISION


def test_death_skill_skips_mana_and_allows_zero_hp():
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []

    class _CostlyDeath(_DeathSkill):
        type_name = "skill_costly_death"
        mana_cost = 999
        cooldown = 999

    units = []
    unit = _make_dying_unit(owner, skills=["skill_costly_death"], units=units)
    unit.mana = 0
    unit.world.unit_class = lambda name: _CostlyDeath if name == "skill_costly_death" else None
    unit._skill_class = lambda name: _CostlyDeath if name == "skill_costly_death" else None
    near = _make_dying_unit(enemy_p, x=0, y=0, skills=(), world=unit.world, units=units)
    near.hp = 100 * PRECISION
    unit.hp = 0
    unit._trigger_death_skills()
    assert near.hp == 60 * PRECISION


def test_manual_on_death_cast_does_not_explode_twice_on_self_kill():
    """Like CrazyMod poudriere: manual detonate then die must not re-fire on_death."""
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []
    calls = []

    class _ManualDeath(_DeathSkill):
        type_name = "a_faire_exploser_poudriere"
        auto_trigger = 1
        manual_use = 1
        trigger_timing = "on_death"
        effect = ["harm_area", "40", "6"]
        effect_target = ["self"]

        @classmethod
        def execute_skill(cls, caster, target=None, world=None):
            calls.append("cast")
            return Skill.execute_skill.__func__(cls, caster, target, world)

    depot = _make_dying_unit(
        owner,
        x=0,
        y=0,
        skills=["a_faire_exploser_poudriere"],
        is_building=True,
        units=units,
    )
    depot.hp = 50 * PRECISION
    depot._skill_class = (
        lambda name: _ManualDeath if name == "a_faire_exploser_poudriere" else None
    )
    near = _make_dying_unit(enemy_p, x=500, y=0, skills=(), world=depot.world, units=units)
    near.hp = 100 * PRECISION

    # Manual self-detonate (same skill as on_death)
    assert _ManualDeath.execute_skill(depot, depot, depot.world) is True
    assert calls == ["cast"]
    assert "a_faire_exploser_poudriere" in getattr(depot, "_death_skills_done", ())

    # Blast then destroys the depot → on_death must not cast again
    depot.die()
    assert calls == ["cast"]
    assert near.hp == 60 * PRECISION  # damaged only once from the manual cast


def test_enemy_destroy_still_fires_on_death_once():
    owner = _StubPlayer("owner")
    enemy_p = _StubPlayer("enemy")
    units = []
    calls = []

    class _CountingDeath(_DeathSkill):
        type_name = "skill_death_nova"

        @classmethod
        def execute_skill(cls, caster, target=None, world=None):
            calls.append("cast")
            return Skill.execute_skill.__func__(cls, caster, target, world)

    depot = _make_dying_unit(
        owner, skills=["skill_death_nova"], is_building=True, units=units
    )
    depot._skill_class = lambda name: _CountingDeath if name == "skill_death_nova" else None
    near = _make_dying_unit(enemy_p, x=0, y=0, skills=(), world=depot.world, units=units)
    near.hp = 100 * PRECISION

    depot.die()
    assert calls == ["cast"]
    assert near.hp == 60 * PRECISION
