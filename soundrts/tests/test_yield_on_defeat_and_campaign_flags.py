"""战败投降 (yield_on_defeat) 与战役进度标记 (campaign_flag)。"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

import soundrts.worldunit  # noqa: F401

from soundrts.worldplayerbase.triggers import TriggersMixin
from soundrts.worldunit.worldcreature import Creature

_RAYNOR_CAMPAIGN = (
    Path(__file__).resolve().parents[2] / "res" / "single" / "The Legend of Raynor"
)


class _StubWorld:
    players = []

    def __init__(self, players=None):
        self.players = players or []


class _StubPlayer(TriggersMixin):
    is_human = True
    allied = None

    def __init__(self):
        self.id = "h1"
        self.allied = [self]
        self.units = []
        self.world = None
        self.allied_control = (self,)
        self.allied_control_units_set = set()

    def notify(self, *args):
        pass

    def observe(self, *args):
        pass

    def player_is_an_enemy(self, p):
        return p is not self and getattr(p, "id", None) != self.id

    def unit_under_allied_control(self, unit):
        if unit.player in self.allied_control:
            return True
        return unit in self.allied_control_units_set

    def is_an_enemy(self, o):
        p = getattr(o, "player", None)
        if p is None:
            return False
        if self.unit_under_allied_control(o):
            return False
        return self.player_is_an_enemy(p)


class _StubCampaign:
    def __init__(self, flags=None):
        self._flags = set(flags or [])

    def has_flag(self, flag):
        return flag in self._flags

    def set_flag(self, flag):
        self._flags.add(flag)

    def clear_flag(self, flag):
        self._flags.discard(flag)


class _StubSquare:
    def __init__(self):
        self.objects = []


class _YieldUnit(Creature):
    type_name = "npc_count_roland"
    expanded_is_a = set()
    yield_on_defeat = 1
    hp_max = 200
    presence = True

    def __init__(self):
        self.hp = 200
        self.player = types.SimpleNamespace(id="ai1")
        self.id = "u1"
        self.world = _StubWorld()
        self.action_target = None
        self._buffs = []
        self.inside = None
        self.airground_type = "ground"

    def stop(self):
        pass

    def notify(self, *args):
        self.notifications = getattr(self, "notifications", []) + [args]

    def delete(self):
        self.deleted = True


def test_without_yield_on_defeat_unit_can_die():
    human = _StubPlayer()
    enemy = _StubPlayer()
    world = _StubWorld([human, enemy])
    world.time = 0
    human.world = world
    enemy.world = world
    unit = _YieldUnit()
    unit.world = world
    unit.player = enemy
    enemy.on_unit_attacked = lambda *a, **k: None
    unit.yield_on_defeat = 0

    attacker = types.SimpleNamespace(player=human, id="atk1")
    unit.die(attacker=attacker)

    assert getattr(unit, "deleted", False)
    assert not getattr(unit, "_has_yielded", False)


def test_yield_on_defeat_prevents_death_and_records_yield():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    unit = _YieldUnit()
    unit.world = world

    unit.die(attacker=types.SimpleNamespace(player=human))

    assert not getattr(unit, "deleted", False)
    assert unit.hp > 0
    assert getattr(unit, "_has_yielded", False)
    assert unit.is_vulnerable is False
    assert human._yielded_enemy_unit_counts.get("npc_count_roland") == 1


def test_yielded_unit_cannot_die_or_take_damage_again():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    unit = _YieldUnit()
    unit.world = world
    unit.die(attacker=types.SimpleNamespace(player=human))
    hp_after_yield = unit.hp

    unit.die(attacker=types.SimpleNamespace(player=human))
    assert not getattr(unit, "deleted", False)
    assert unit.hp == hp_after_yield

    from soundrts.combat.damage_effects import DamageEffectsMixin

    class _HitTest(DamageEffectsMixin):
        pass

    hitter = _HitTest()
    hitter.world = world
    hitter.player = human
    unit.receive_hit(9999, hitter)
    assert unit.hp == hp_after_yield


def test_yielded_unit_cannot_attack_or_deal_damage():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    yielded = _YieldUnit()
    yielded.world = world
    yielded.die(attacker=types.SimpleNamespace(player=human))

    target = _YieldUnit()
    target.world = world
    target.player = human
    target.yield_on_defeat = 0
    target.hp = 100
    hp_before = target.hp

    from soundrts.combat.damage_effects import DamageEffectsMixin

    class _HitTest(DamageEffectsMixin):
        pass

    yielded._attack = Creature._attack.__get__(yielded, Creature)
    yielded._attack(target)
    assert target.action_target is None

    hitter = _HitTest()
    hitter.world = world
    hitter.player = types.SimpleNamespace(id="ai1")
    hitter._has_yielded = True
    target.receive_hit(50, hitter)
    assert target.hp == hp_before


def test_release_yield_invulnerability_restores_combat():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    unit = _YieldUnit()
    unit.world = world
    unit.die(attacker=types.SimpleNamespace(player=human))
    assert unit.is_vulnerable is False

    unit.release_yield_invulnerability()
    assert not getattr(unit, "_has_yielded", False)
    assert unit.is_vulnerable is True
    assert unit.yield_on_defeat == 0
    # 解除后不再走认输短路，会进入正常死亡流程
    assert not (
        getattr(unit, "_has_yielded", False)
        or (getattr(unit, "yield_on_defeat", 0) and not getattr(unit, "_has_yielded", False))
    )


def test_lang_release_yielded_units_for_computer():
    human = _StubPlayer()
    ai = types.SimpleNamespace(id="ai1", units=[])
    world = _StubWorld([human, ai])
    human.world = world
    unit = _YieldUnit()
    unit.world = world
    unit.player = ai
    unit.die(attacker=types.SimpleNamespace(player=human))
    ai.units = [unit]

    human.lang_release_yielded_units(["computer1"])
    assert unit.is_vulnerable is True
    assert not getattr(unit, "_has_yielded", False)


def test_yield_cancels_attacks_against_unit():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    victim = _YieldUnit()
    victim.world = world
    attacker = _YieldUnit()
    attacker.id = "u2"
    attacker.type_name = "knight"
    attacker.world = world
    attacker.player = human
    attacker.orders = []
    attacker.yield_on_defeat = 0
    attacker.action_target = victim
    human.units = [attacker]

    victim.die(attacker=attacker)

    assert attacker.action_target is None
    assert victim.is_vulnerable is False


def test_units_yielded_trigger_matches_recorded_yields():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    victim = types.SimpleNamespace(
        id="v1",
        type_name="npc_roland_guard",
        expanded_is_a=set(),
        player=types.SimpleNamespace(id="ai1"),
    )
    human.record_unit_yielded(victim)
    assert human.lang_units_yielded(["1", "npc_roland_guard", "enemy"]) is True
    assert human.lang_units_yielded(["2", "npc_roland_guard", "enemy"]) is False


def test_units_yielded_by_matches_attacker_type():
    human = _StubPlayer()
    world = _StubWorld([human])
    human.world = world
    victim = types.SimpleNamespace(
        id="m1",
        type_name="npc_marco_ironhand",
        expanded_is_a=set(),
        player=types.SimpleNamespace(id="ai1"),
    )
    raynor = types.SimpleNamespace(type_name="raynor6", expanded_is_a={"raynor", "knight"})
    footman = types.SimpleNamespace(type_name="footman", expanded_is_a=set())
    human.record_unit_yielded(victim, raynor)
    assert human.lang_units_yielded_by(["raynor6", "1", "npc_marco_ironhand", "enemy"]) is True
    assert human.lang_units_yielded_by(["raynor", "1", "npc_marco_ironhand", "enemy"]) is True
    assert human.lang_units_yielded_by(["footman", "1", "npc_marco_ironhand", "enemy"]) is False
    victim2 = types.SimpleNamespace(
        id="m2",
        type_name="npc_marco_ironhand",
        expanded_is_a=set(),
        player=types.SimpleNamespace(id="ai1"),
    )
    human.record_unit_yielded(victim2, footman)
    assert human.lang_units_yielded(["1", "npc_marco_ironhand", "enemy"]) is True
    assert human.lang_units_yielded_by(["raynor6", "1", "npc_marco_ironhand", "enemy"]) is True
    assert human.lang_units_yielded_by(["footman", "1", "npc_marco_ironhand", "enemy"]) is True


def test_campaign_flag_condition_and_action():
    human = _StubPlayer()
    campaign = _StubCampaign()
    human.world = types.SimpleNamespace(campaign=campaign)

    assert human.lang_campaign_flag(["ch24_garrek"]) is False
    human.lang_set_campaign_flag(["ch24_garrek"])
    assert human.lang_campaign_flag(["ch24_garrek"]) is True


def test_map_flag_and_unset_campaign_flag():
    human = _StubPlayer()
    campaign = _StubCampaign(flags={"ch27_duel_started"})
    human.world = types.SimpleNamespace(campaign=campaign)

    assert human.lang_map_flag(["ch27_duel_started"]) is False
    human.lang_set_map_flag(["ch27_duel_started"])
    assert human.lang_map_flag(["ch27_duel_started"]) is True

    assert human.lang_campaign_flag(["ch27_duel_started"]) is True
    human.lang_unset_campaign_flag(["ch27_duel_started"])
    assert human.lang_campaign_flag(["ch27_duel_started"]) is False


def test_has_entered_requires_matching_unit_on_square():
    human = _StubPlayer()
    square = _StubSquare()
    world = types.SimpleNamespace(
        grid={"2,1": square},
        squares=[],
        name_to_square={},
    )
    human.world = world
    human.units = []
    footman = types.SimpleNamespace(
        type_name="footman",
        expanded_is_a=set(),
        presence=True,
    )
    raynor = types.SimpleNamespace(
        type_name="raynor6",
        expanded_is_a={"raynor", "knight"},
        presence=True,
    )
    human.units.append(footman)
    square.objects.append(footman)
    assert human.lang_has_entered(["c2", "raynor6"]) is False

    square.objects.append(raynor)
    human.units.append(raynor)
    assert human.lang_has_entered(["c2", "raynor6"]) is True
    assert human.lang_has_entered(["3,2", "raynor"]) is True


def test_has_entered_one_based_coords_not_confused_with_zero_based_grid_key():
    """lanes 9×3 等地图上 1 基 "8,2" 与 0 基键 "8,2" 并存时，应指向 7,1。"""
    human = _StubPlayer()
    ruin_square = _StubSquare()
    wrong_square = _StubSquare()
    world = types.SimpleNamespace(
        grid={"7,1": ruin_square, "8,2": wrong_square},
        squares=[],
        name_to_square={},
    )
    human.world = world
    human.units = []
    footman = types.SimpleNamespace(
        type_name="footman",
        expanded_is_a=set(),
        presence=True,
    )
    human.units.append(footman)
    ruin_square.objects.append(footman)
    assert human.lang_has_entered(["8,2"]) is True
    wrong_square.objects.append(footman)
    ruin_square.objects.clear()
    assert human.lang_has_entered(["8,2"]) is False


def test_campaign_module_exposes_flag_persistence_api():
    src = (Path(__file__).resolve().parents[1] / "campaign.py").read_text(encoding="utf-8")
    assert "def get_flags(self):" in src
    assert "def set_flag(self, flag):" in src
    assert "def clear_flag(self, flag):" in src
    assert 'c.set(self._id(), "flags"' in src


def test_chapter_maps_use_distinct_heroes_and_carryover():
    base = _RAYNOR_CAMPAIGN
    ch24 = (base / "24.txt").read_text(encoding="utf-8")
    ch25 = (base / "25.txt").read_text(encoding="utf-8")
    ch26 = (base / "26.txt").read_text(encoding="utf-8")
    ch27 = (base / "27.txt").read_text(encoding="utf-8")

    assert "npc_knight_leader" in ch24
    assert "set_campaign_flag ch24_garrek" in ch24
    assert "garrek_token" in ch24
    assert "set_campaign_flag ch24_garrek_token" in ch24

    assert "npc_count_roland" in ch25
    assert "garrek_token" in ch25
    assert "npc_has_item npc_count_roland garrek_token" in ch25
    assert "set_ai_mode offensive" in ch25
    assert "set_yield_on_defeat 1" in ch25
    assert "ch25_duel_started" in ch25
    assert "campaign_flag ch24_garrek_token" in ch25
    assert "units_yielded 1 npc_count_roland 6 npc_roland_guard" in ch25
    assert "(stop_all_units)" in ch25
    assert "(stop_all_units computer1)" in ch25
    assert "(release_yielded_units computer1)" in ch25
    assert "trigger players (no_unit_left) (defeat)" in ch25
    assert "campaign_flag ch24_garrek" in ch25
    assert "(add_inventory_item garrek_token 1 raynor)" in ch25
    assert "npc_knight_leader" not in ch25.split("computer_only")[1].split("\n")[0]

    assert "npc_general_vera" in ch26
    assert "war_banner" in ch26
    assert "campaign_flag ch25_roland_allied" in ch26

    assert "npc_marco_ironhand" in ch27
    assert "units_yielded_by raynor 1 npc_marco_ironhand" in ch27
    assert "starting_units raynor7" in ch27
    assert "raynor77" not in ch27
    assert "campaign_flag ch26_vera" in ch27
