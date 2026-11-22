"""Runtime regression test for Joan of Arc ch2's computer slots.

This is the end-to-end guard for the user-reported bug (2026-11-21):
the Orleans h7 garrison displayed as "Neutral" yet attacked the
player, and flipped to "Franks" once attacked.

The static map assertions live in ``test_joan_ch2_computer_slots.py``.
This module builds the actual world and checks the RUNTIME state:
each computer slot's alliance, its neutrality flag and the mutual
"is this an enemy?" relation with the human player.

It also checks the two map features the fix relies on:
  * ``name <alias>`` slots can be resolved at runtime by alias
    (``transfer_units orleans_h6 player1``);
  * the neutral h7 garrison does NOT treat the player as an enemy,
    while the hostile f3 Burgundy outpost DOES.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

JOAN = Path("mods/aoe2/single/Joan of Arc")

# slot index (1-based) -> (square, expected alliance, expected relation)
EXPECTED_SLOTS = {
    1: ("e2", 1, "ally"),     # Blois town center
    2: ("e3", 1, "ally"),     # Blois army + monastery
    3: ("f3", 2, "enemy"),    # Burgundy bridge outwork
    4: ("h6", 1, "ally"),     # Orleans citadel
    5: ("h7", 1, "ally"),     # Orleans garrison  <-- the reported bug
    6: ("k5", 2, "enemy"),    # North English keep
    7: ("k6", 2, "enemy"),    # North English outpost
    8: ("l5", 2, "enemy"),    # Outer English fortification
    9: ("l6", 2, "enemy"),    # Outer English outpost
}


@pytest.fixture(scope="module")
def ch2_world():
    """Build the real ch2 world and populate it with one human player."""
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient

    saved_mods = getattr(config, "mods", "")
    saved_res_mods = res.mods
    try:
        config.mods = "aoe2"
        res.set_mods("aoe2")
        res.load_rules_and_ai()
        rules.load(
            res.text("rules", append=True),
            (JOAN / "rules.txt").read_text(encoding="utf-8"),
        )

        world = World([], 42)
        world.scenario_difficulty = "standard"
        world._parse_map((JOAN / "2.txt").read_text(encoding="utf-8"))
        world.square_width = int(world.square_width * 1000)
        world._build_map()

        client = DirectClient("player1", None)
        client.faction = "franks"
        client.alliance = None
        client.interface = type(
            "I", (), {"queue_srv_event": lambda *a, **k: None}
        )()
        world.populate_map([client], random_starts=False)
        world._update_buckets()
        yield world
    finally:
        config.mods = saved_mods
        if res.mods != saved_res_mods:
            res.set_mods(saved_res_mods)


def _split_players(world):
    humans = [p for p in world.players if getattr(p, "is_human", False)]
    computers = [p for p in world.players if not getattr(p, "is_human", False)]
    return humans[0], computers


def test_ch2_world_builds_with_nine_computer_slots(ch2_world):
    _human, computers = _split_players(ch2_world)
    assert len(computers) == 9, (
        f"ch2 must build 9 computer players, got {len(computers)}"
    )


@pytest.mark.parametrize("slot", sorted(EXPECTED_SLOTS))
def test_ch2_slot_alliance_and_relation(ch2_world, slot):
    """Every slot must sit on the alliance its map position implies."""
    square, want_alliance, want_relation = EXPECTED_SLOTS[slot]
    human, computers = _split_players(ch2_world)
    computer = computers[slot - 1]

    assert str(computer.client.alliance) == str(want_alliance), (
        f"ch2 slot {slot} ({square}) must be on alliance {want_alliance}, "
        f"got {computer.client.alliance}"
    )
    relation = "enemy" if human.player_is_an_enemy(computer) else "ally"
    assert relation == want_relation, (
        f"ch2 slot {slot} ({square}) must be a {want_relation} of the "
        f"player, got {relation}"
    )


def test_ch2_h7_garrison_is_neutral_and_not_an_enemy(ch2_world):
    """The reported bug, asserted against the live world.

    The h7 garrison must be NEUTRAL (drawn as "Neutral") AND on the
    player's own alliance (so it never attacks the player).
    """
    human, computers = _split_players(ch2_world)
    h7 = computers[4]  # slot 5

    assert getattr(h7, "neutral", False), (
        "the h7 garrison must be drawn as neutral"
    )
    assert not human.player_is_an_enemy(h7), (
        "the h7 garrison must not treat the player as an enemy"
    )
    assert not h7.player_is_an_enemy(human), (
        "the h7 garrison must not attack the player"
    )
    # It must actually hold the watch tower and militia the user saw.
    types = {u.type_name for u in h7.units}
    assert "scouttower" in types
    assert "militia" in types


def test_ch2_f3_burgundy_is_hostile(ch2_world):
    """The mirror case: the f3 Burgundy outpost must attack."""
    human, computers = _split_players(ch2_world)
    f3 = computers[2]  # slot 3

    assert not getattr(f3, "neutral", False), (
        "the f3 Burgundy outpost must be a hostile base, not neutral"
    )
    assert human.player_is_an_enemy(f3)
    assert f3.player_is_an_enemy(human)


def test_ch2_blois_monastery_is_a_french_ally(ch2_world):
    """The Blois e3 monastery was the extra line that shifted everything.

    It must be part of the French ally camp."""
    human, computers = _split_players(ch2_world)
    blois = computers[1]  # slot 2
    types = {u.type_name for u in blois.units}
    assert "monastery" in types
    assert not human.player_is_an_enemy(blois), (
        "the Blois camp must be a French ally"
    )


def test_ch2_named_slots_are_resolvable_by_alias(ch2_world):
    """``name <alias>`` slots must resolve to their runtime player."""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    human, computers = _split_players(ch2_world)

    class _Probe:
        world = ch2_world

    probe = _Probe()
    probe._named_computer_player = (
        TriggersMixin._named_computer_player.__get__(probe, _Probe)
    )

    names = getattr(ch2_world, "computers_names", None)
    assert names, (
        "the ch2 map must expose its computer slot names at runtime"
    )
    assert set(names) == {
        "blois_e2", "blois_e3", "burgundy_f3", "orleans_h6", "orleans_h7",
        "english_k5", "english_k6", "english_l5", "english_l6",
    }
    # Every alias must resolve to the computer player that owns it.
    for alias, idx in sorted(names.items()):
        assert probe._named_computer_player(alias) is computers[idx], (
            f"alias {alias!r} must resolve to computer slot {idx + 1}"
        )
