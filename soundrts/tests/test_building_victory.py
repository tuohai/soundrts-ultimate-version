"""Tests for building victory_time countdown."""

import types

from soundrts import msgparts as mp
from soundrts.building_victory import (
    cancel_victory_timer_if_needed,
    register_victory_timer_if_needed,
    update_victory_timers,
    victory_time_seconds,
)


def _make_player(pid="p1", name=None):
    voice = []
    player = types.SimpleNamespace(
        id=pid,
        name=name or [f"player-{pid}"],
        has_victory=False,
        is_playing=True,
        allied_victory=None,
        voice=voice,
    )
    player.allied_victory = [player]
    player.is_local_human = lambda: True
    player.send_voice_important = lambda msg: voice.append(list(msg))
    player.victory = lambda: setattr(player, "has_victory", True)
    return player


def _make_world(players):
    return types.SimpleNamespace(
        time=0,
        timer_coefficient=1,
        players=players,
        objects={},
        victory_countdowns={},
    )


def _make_building(world, player, unit_id="1", seconds=10):
    building = types.SimpleNamespace(
        id=unit_id,
        world=world,
        player=player,
        place=object(),
        victory_time=seconds,
    )
    world.objects[unit_id] = building
    return building


def test_victory_time_seconds_reads_attribute():
    unit = types.SimpleNamespace(victory_time=300)
    assert victory_time_seconds(unit) == 300
    assert victory_time_seconds(types.SimpleNamespace()) == 0


def test_register_starts_countdown_and_announces():
    owner = _make_player("1", name=["Alice"])
    rival = _make_player("2", name=["Bob"])
    world = _make_world([owner, rival])
    building = _make_building(world, owner, seconds=300)

    register_victory_timer_if_needed(building)

    assert building.id in world.victory_countdowns
    assert world.victory_countdowns[building.id]["deadline"] == 300_000
    assert owner.voice
    assert rival.voice
    assert mp.VICTORY_TIMER_STARTED[0] in owner.voice[0]


def test_update_grants_victory_when_timer_expires():
    owner = _make_player("1")
    rival = _make_player("2")
    world = _make_world([owner, rival])
    building = _make_building(world, owner, seconds=5)
    register_victory_timer_if_needed(building)

    world.time = 5_000
    update_victory_timers(world)

    assert owner.has_victory is True
    assert building.id not in world.victory_countdowns


def test_destroy_cancels_countdown():
    owner = _make_player("1")
    rival = _make_player("2")
    world = _make_world([owner, rival])
    building = _make_building(world, owner, seconds=60)
    register_victory_timer_if_needed(building)
    owner.voice.clear()
    rival.voice.clear()

    cancel_victory_timer_if_needed(building)

    assert building.id not in world.victory_countdowns
    assert any(mp.VICTORY_TIMER_CANCELLED[0] in msg for msg in owner.voice)
    world.time = 60_000
    update_victory_timers(world)
    assert owner.has_victory is False


def test_destroyed_building_does_not_win_after_deadline():
    owner = _make_player("1")
    world = _make_world([owner])
    building = _make_building(world, owner, seconds=10)
    register_victory_timer_if_needed(building)
    building.place = None
    world.time = 10_000
    update_victory_timers(world)
    assert owner.has_victory is False
    assert building.id not in world.victory_countdowns


def test_building_without_victory_time_ignored():
    owner = _make_player("1")
    world = _make_world([owner])
    building = types.SimpleNamespace(
        id="9",
        world=world,
        player=owner,
        place=object(),
        victory_time=0,
    )
    register_victory_timer_if_needed(building)
    assert world.victory_countdowns == {}


def test_rules_wonder_uses_victory_time():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    cls = rules.unit_class("wonder")
    assert cls is not None
    assert cls.victory_time == 300
    assert cls.count_limit == 1
    assert cls.hp_max > 0
