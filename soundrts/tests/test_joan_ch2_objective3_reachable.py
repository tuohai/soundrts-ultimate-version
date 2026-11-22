"""Runtime regression test: Joan of Arc ch2 objective 3 must be reachable.

User-reported bug (2026-11-21):
  "My main objective 3 -- advance to Castle Age -- cannot be completed,
  because there is no Town Center."

The chapter was unwinnable *by construction*.  This module builds the
real ch2 world and asserts the whole chain end-to-end:

  * turn 0: the player owns a Town Center (the only building that carries
    ``can_advance``), has population headroom for training peasants, has
    a mill (food drop-off) and farms (renewable food), and enough food
    and gold to pay for both age-ups;
  * the farms really do replant themselves when harvested empty (the
    engine's ``_auto_enable_farm_cultivation``);
  * after the Orleans hand-over the player owns TWO different
    ``feudal_age_buildings`` (``scouttower`` + ``market``), which is the
    ``any_buildings 2 feudal_age_buildings`` gate of ``castle_age``;
  * with the hand-over done, ``AdvanceOrder`` allows ``feudal_age`` and
    -- once Feudal is paid for -- ``castle_age``;
  * paying both age-ups makes the objective-3 trigger condition
    (``(has castle_age)``) true.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

_saved_argv = sys.argv
try:
    sys.argv = [_saved_argv[0]] if _saved_argv else ["pytest"]
    import pygame

    # The world update loop ends up in sound.pause_music() when a trigger
    # fires (objective_complete), and that needs an initialized mixer.
    if not pygame.mixer.get_init():
        pygame.mixer.init()
finally:
    sys.argv = _saved_argv

JOAN = Path("mods/aoe2/single/Joan of Arc")


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


def _human(world):
    humans = [p for p in world.players if getattr(p, "is_human", False)]
    assert humans, "ch2 must build a human player"
    return humans[0]


def _buildings(player):
    return {
        u.type_name
        for u in player.units
        if getattr(u, "is_a_building", False)
    }


# ---------------------------------------------------------------------------
# Turn 0: the player must have a usable base.
# ---------------------------------------------------------------------------

def test_ch2_player_starts_with_a_town_center(ch2_world):
    """The reported bug: no Town Center -> no ``can_advance`` menu."""
    player = _human(ch2_world)
    assert "town_center" in _buildings(player), (
        "ch2 must give the player a town_center at turn 0 -- it is the "
        "only building with can_advance, so without it objective 3 "
        "(Castle Age) is impossible"
    )


def test_ch2_town_center_offers_the_age_advance_menu(ch2_world):
    """The Town Center must actually offer the two age-ups."""
    from soundrts.worldorders.production import AdvanceOrder

    player = _human(ch2_world)
    tc = [u for u in player.units if u.type_name == "town_center"][0]

    assert "feudal_age" in (getattr(tc, "can_advance", None) or ()), (
        "the starting town center must offer 'advance to Feudal Age'"
    )
    assert "castle_age" in (getattr(tc, "can_advance", None) or ()), (
        "the starting town center must offer 'advance to Castle Age'"
    )
    assert AdvanceOrder.is_allowed(tc, "feudal_age") is True


def test_ch2_player_has_population_headroom(ch2_world):
    """The escort uses 23 population; the player must be able to train."""
    player = _human(ch2_world)
    assert player.available_population - player.used_population > 0, (
        "ch2 must give the player population headroom (houses) -- "
        f"supply={player.available_population} used={player.used_population}"
    )


def test_ch2_player_starts_with_a_mill_and_farms(ch2_world):
    player = _human(ch2_world)
    buildings = _buildings(player)
    assert "mill" in buildings, (
        "ch2 must give the player a mill (the food drop-off)"
    )
    assert "farm" in buildings, (
        "ch2 must give the player farms (renewable food)"
    )


def test_ch2_player_can_afford_feudal_and_castle(ch2_world):
    """Feudal = 500 food, Castle = 200 gold + 800 food."""
    from soundrts.definitions import rules

    player = _human(ch2_world)
    resources = list(player.resources)
    feudal = rules.unit_class("feudal_age")
    castle = rules.unit_class("castle_age")

    assert resources[2] >= feudal.cost[2], (
        "ch2 must open with enough food for Feudal Age "
        f"({feudal.cost[2]}), got {resources[2]}"
    )
    assert resources[0] >= castle.cost[0], (
        "ch2 must open with enough gold for Castle Age "
        f"({castle.cost[0]}), got {resources[0]}"
    )


# ---------------------------------------------------------------------------
# The engine fix: farms must replant themselves.
# ---------------------------------------------------------------------------

def test_ch2_farms_start_in_auto_cultivate_mode(ch2_world):
    """A farm must start with ``current_production_mode == "auto"``.

    Otherwise a depleted farm is dead forever: ``world_status_update.py``
    has no branch for ``production_mode is None``, so the replant order
    is never issued.
    """
    player = _human(ch2_world)
    farms = [u for u in player.units if u.type_name == "farm"]
    assert farms, "ch2 must have farms"
    for farm in farms:
        assert getattr(farm, "current_production_mode", None) == "auto", (
            f"a farm must start in auto-cultivate mode, got "
            f"{getattr(farm, 'current_production_mode', None)!r}"
        )


def test_ch2_farm_replants_itself_when_depleted(ch2_world):
    """Emptied farm -> replanted -> full again (60 wood)."""
    player = _human(ch2_world)
    farm = [u for u in player.units if u.type_name == "farm"][0]
    farm.resource_qty = 0

    for _ in range(300):
        ch2_world.update()

    assert farm.resource_qty > 0, (
        "a depleted ch2 farm must replant itself; after 300 s it is still "
        f"empty (mode={getattr(farm, 'current_production_mode', None)!r})"
    )


# ---------------------------------------------------------------------------
# After the Orleans hand-over: the Castle Age gate must open.
# ---------------------------------------------------------------------------

def _hand_over(ch2_world):
    player = _human(ch2_world)
    player.lang_transfer_units(["orleans_h6", "player1"])
    player.lang_transfer_units(["orleans_h7", "player1"])
    return player


def test_ch2_handover_gives_two_feudal_age_buildings(ch2_world):
    """Castle Age needs TWO different ``feudal_age_buildings``.

    The group is ``archery_range, blacksmith, gate, market, scouttower,
    stables, wall`` -- the hand-over gives the scouttower AND the market.
    """
    from soundrts.worldrequirements import count_owned_buildings_of_group

    player = _hand_over(ch2_world)
    owned = count_owned_buildings_of_group(player, "feudal_age")
    assert owned >= 2, (
        "after the Orleans hand-over the player must own at least 2 "
        "feudal_age_buildings (the castle_age gate is "
        "'any_buildings 2 feudal_age_buildings'), got "
        f"{owned}: {sorted(_buildings(player))}"
    )


def test_ch2_castle_age_is_reachable_after_the_handover(ch2_world):
    """The full chain: hand over -> Feudal -> Castle -> objective 3."""
    from soundrts.definitions import rules
    from soundrts.worldorders.production import AdvanceOrder
    from soundrts.worldrequirements import missing_requirement_clauses

    player = _hand_over(ch2_world)
    tc = [u for u in player.units if u.type_name == "town_center"][0]

    feudal = rules.unit_class("feudal_age")
    castle = rules.unit_class("castle_age")

    assert AdvanceOrder.is_allowed(tc, "feudal_age") is True, (
        "the player must be able to advance to Feudal Age right after "
        "the Orleans hand-over"
    )

    player.pay(feudal.cost)
    feudal.upgrade_player(player)
    assert player.has("feudal_age")

    assert missing_requirement_clauses(player, castle.requirements) == [], (
        "Castle Age must have no unmet requirement after the hand-over "
        "and the Feudal Age advance, got: "
        f"{missing_requirement_clauses(player, castle.requirements)!r}"
    )
    assert AdvanceOrder.is_allowed(tc, "castle_age") is True, (
        "the player must be able to advance to Castle Age"
    )

    player.pay(castle.cost)
    castle.upgrade_player(player)
    assert player.has("castle_age")

    # The objective-3 trigger: (and (has castle_age) (not (has imperial_age)))
    assert player.has("castle_age") and not player.has("imperial_age"), (
        "the objective-3 condition must be satisfiable"
    )
