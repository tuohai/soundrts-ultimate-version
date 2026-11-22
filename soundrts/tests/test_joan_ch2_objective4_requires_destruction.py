"""Regression tests for the Joan of Arc ch. 2 "objective 4 completes
for free" bug (user-reported 2026-11-21).

Reported symptom
----------------
"第二章的主要目标4摧毁一座英军城堡莫名其妙的就完成了，是在完成目标2后
紧接着就完成了 ... 我都没摧毁英军城堡，反倒是英军的城堡和军队归我了导致目标
完成。"

Translation: main objective 4 ("destroy 1 English Castle") completed right
after objective 2, and the English castle + army ended up belonging to the
player.

Root cause (two independent bugs)
----------------------------------
1. **Engine: alias resolution was positional.**  A named ``computer_only``
   slot (``name orleans_h7``) was resolved by indexing into the *live*
   ``world.players`` list.  When a computer is defeated it is removed from
   that list (``defeat()`` -> ``quit_game()``), so the live list shrinks and
   every *later* alias silently points at the *wrong* slot.  The ch2 map has
   ``trigger all (no_unit_left) (defeat)``, so wiping out the small Burgundy
   outpost at f3 (or english_k6) was enough to shift the aliases:
   ``orleans_h7`` then resolved to ``english_k5`` and objective 2's
   ``transfer_units orleans_h7 player1`` handed the ENGLISH castle and army
   to the player.

2. **Map: the objective condition was ownership-based.**  ``enemy_building_
   destroyed <sq> <type>`` means "there is no *enemy* building of this type
   on that square any more".  It also becomes true when the building merely
   *changes owner* (hand-over / capture) -- it is no longer an enemy
   building, but it was not destroyed either.  With bug 1 above, the
   hand-over left no enemy castle on k5, so objective 4 fired for free.

Fix
---
* Engine: map slots are now bound to their runtime Player **by identity**
  (``world.computer_slot_players`` / ``world.human_slot_players``), so
  aliases and ordinals survive the removal of a player from the world.
* Map: objective 4 additionally requires that the castle was actually
  destroyed (``killed_target <sq> 1 aoe_castle enemy``).

These tests build the real chapter and assert the whole chain.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

JOAN = Path("mods/aoe2/single/Joan of Arc")

CH2 = (JOAN / "2.txt").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _build_ch2_world():
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
        world._parse_map(CH2)
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
        return world
    finally:
        config.mods = saved_mods
        if res.mods != saved_res_mods:
            res.set_mods(saved_res_mods)


def _human(world):
    return next(p for p in world.players if getattr(p, "is_human", False))


def _alias_squares(human, alias):
    """Sorted unique [(col, row)] of the buildings owned by ``alias``'s player."""
    player = human._named_computer_player(alias)
    if player is None:
        return None
    return sorted({
        (u.place.col, u.place.row)
        for u in player.units
        if getattr(u, "is_a_building", False)
    })


def _wipe_out(human, alias):
    """Destroy every unit of ``alias``'s player (the player kills them).

    This is what happens in-game when the player wipes out a small camp:
    the units die and the computer is defeated and removed from
    ``world.players``.
    """
    player = human._named_computer_player(alias)
    assert player is not None, f"alias {alias!r} must resolve to a player"
    attacker = next(
        u for u in human.units if not getattr(u, "is_a_building", False)
    )
    for unit in list(player.units):
        unit.die(attacker)
    return player


# ---------------------------------------------------------------------------
# 1. Engine: aliases survive a computer leaving the world
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("victim", ["burgundy_f3", "english_k6"])
def test_alias_resolution_survives_a_defeated_computer(victim):
    """Defeating a computer must NOT shift the later named slots.

    Before the fix, defeating ``burgundy_f3`` (slot 3) made
    ``orleans_h7`` resolve to ``english_k5`` -- the English castle.
    """
    world = _build_ch2_world()
    human = _human(world)

    # Baseline: every alias must point at its own base.
    assert _alias_squares(human, "orleans_h6") == [(7, 5)]
    assert _alias_squares(human, "orleans_h7") == [(7, 6)]
    assert _alias_squares(human, "english_k5") == [(10, 4)]
    assert _alias_squares(human, "english_l5") == [(11, 4)]

    _wipe_out(human, victim)

    # The alias table must still point at the same bases.
    assert _alias_squares(human, "orleans_h6") == [(7, 5)], (
        f"orleans_h6 must still be the Orleans citadel after {victim} died"
    )
    assert _alias_squares(human, "orleans_h7") == [(7, 6)], (
        f"orleans_h7 must still be the Orleans garrison after {victim} died"
    )
    assert _alias_squares(human, "english_k5") == [(10, 4)], (
        f"english_k5 must still be the English castle after {victim} died"
    )
    assert _alias_squares(human, "english_l5") == [(11, 4)], (
        f"english_l5 must still be the outer English fort after {victim} died"
    )


def test_ordinal_computer_refs_survive_a_defeated_computer():
    """``computerN`` must also stay bound to the Nth map slot."""
    world = _build_ch2_world()
    human = _human(world)

    english_k5 = human._named_computer_player("english_k5")
    _wipe_out(human, "burgundy_f3")

    assert human._resolve_map_player_ref("computer6") is english_k5, (
        "computer6 must still resolve to the english_k5 slot after "
        "burgundy_f3 was defeated"
    )


def test_world_exposes_identity_slot_tables():
    """The identity tables must exist and cover every map slot."""
    world = _build_ch2_world()
    slots = getattr(world, "computer_slot_players", None)
    assert slots, "world must expose computer_slot_players"
    assert len(slots) == len(world.computers_starts), (
        "computer_slot_players must cover every computer_only slot"
    )
    assert all(p is not None for p in slots), (
        "every computer slot must be bound to a runtime player"
    )
    humans = getattr(world, "human_slot_players", None)
    assert humans and humans[0] is _human(world), (
        "human_slot_players must bind player1 to the human player"
    )


# ---------------------------------------------------------------------------
# 2. The reported scenario, end to end
# ---------------------------------------------------------------------------

def test_objective2_handover_never_gives_the_player_the_english_base():
    """Wiping out Burgundy then completing objective 2 must not hand over
    the English castle / army.

    This is the user's exact report.
    """
    world = _build_ch2_world()
    human = _human(world)

    # The player wipes out the small Burgundy outpost at f3 (this is what
    # triggers ``trigger all (no_unit_left) (defeat)`` in the map).
    _wipe_out(human, "burgundy_f3")

    # ... and then objective 2 fires: Orleans is handed over.
    human.lang_transfer_units(["orleans_h6", "player1"])
    human.lang_transfer_units(["orleans_h7", "player1"])

    player_castles = [
        (u.place.col, u.place.row)
        for u in human.units
        if getattr(u, "is_a_building", False) and u.type_name == "aoe_castle"
    ]
    assert player_castles == [], (
        f"the player must NOT own an English castle, got {player_castles!r}"
    )

    # The English bases must still be hostile and still hold their castles.
    english_k5 = human._named_computer_player("english_k5")
    assert english_k5 is not None
    assert human.player_is_an_enemy(english_k5), (
        "the English k5 base must still be an enemy of the player"
    )
    assert any(
        getattr(u, "is_a_building", False) and u.type_name == "aoe_castle"
        for u in english_k5.units
    ), "the English k5 castle must still exist and belong to the English"


def test_objective4_does_not_complete_without_destroying_a_castle():
    """Objective 4's condition must be false until a castle is destroyed."""
    world = _build_ch2_world()
    human = _human(world)

    _wipe_out(human, "burgundy_f3")
    human.lang_transfer_units(["orleans_h6", "player1"])
    human.lang_transfer_units(["orleans_h7", "player1"])

    # The raw "no enemy castle here" check is the one that used to fire.
    assert human.lang_enemy_building_destroyed(["k5", "aoe_castle"]) is False
    assert human.lang_enemy_building_destroyed(["l5", "aoe_castle"]) is False

    # And the map's actual objective-4 condition must be false too.
    cond = _objective4_condition()
    assert cond is not None, "ch2 must declare the objective 4 condition"
    assert human.my_eval(cond) is False, (
        "objective 4 must NOT be satisfiable without destroying a castle"
    )


def test_objective4_completes_when_the_player_destroys_the_castle():
    """After actually destroying the k5 castle, objective 4 must fire."""
    world = _build_ch2_world()
    human = _human(world)

    _wipe_out(human, "burgundy_f3")

    english_k5 = human._named_computer_player("english_k5")
    castle = next(
        u for u in english_k5.units
        if getattr(u, "is_a_building", False) and u.type_name == "aoe_castle"
    )
    attacker = next(
        u for u in human.units if not getattr(u, "is_a_building", False)
    )
    castle.die(attacker)

    cond = _objective4_condition()
    assert human.my_eval(cond) is True, (
        "objective 4 must fire once an English castle is really destroyed"
    )


# ---------------------------------------------------------------------------
# 3. The map's objective-4 condition itself
# ---------------------------------------------------------------------------

def _objective4_condition():
    """Parse the objective-4 condition out of the map.

    Returns the parsed S-expression list, or None if not found.
    """
    from soundrts.trigger_script import parse_trigger_tree
    from soundrts.world.world_map import WorldMapMixin

    for raw in CH2.splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line.startswith("trigger player1 "):
            continue
        if "objective_complete 4" not in line:
            continue
        words = _tokenize(line[len("trigger "):])
        tree = WorldMapMixin._list_to_tree(None, words)
        _owners, condition, _action, _meta = parse_trigger_tree(tree)
        return condition
    return None


def _tokenize(text):
    """Split a trigger line into words, keeping '(' / ')' as tokens."""
    return text.replace("(", " ( ").replace(")", " ) ").split()


def test_objective4_requires_an_actual_destruction():
    """The map must require a real kill, not just "no enemy castle left".

    ``enemy_building_destroyed`` alone also fires when the castle merely
    changes owner, which is how the objective used to complete for free.
    """
    cond = _objective4_condition()
    assert cond is not None

    flat = repr(cond)
    assert "enemy_building_destroyed" in flat, (
        "objective 4 must still check the English castle squares"
    )
    assert "killed_target" in flat, (
        "objective 4 must additionally require that the castle was "
        "actually destroyed (killed_target), not merely handed over"
    )
    assert "enemy" in flat, (
        "the kill must be attributed to the enemy (the English), not to an "
        "ally"
    )


def test_objective4_still_targets_both_english_castles():
    cond = _objective4_condition()
    flat = repr(cond)
    assert "k5" in flat and "l5" in flat, (
        "objective 4 must accept either English castle (k5 or l5)"
    )
