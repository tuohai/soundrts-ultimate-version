# -*- coding: utf-8 -*-
"""jl1: the intermediate AI must attack even when it never saw the enemy.

The user reported that on ``res/multi/jl1.txt`` an intermediate computer
attacks at ~8 minutes when its villagers explore at the start, but only at
~15 minutes when they do not explore.  The cause is that the attack trigger
is ``_enemy_presence`` — the list of squares where the AI has *seen* an
enemy.  With ``constant_attacks 1`` and an empty list, ``_eventually_attack``
assigned the whole army to the home guard, so the army idled in the base.

The fix: when the enemy has never been seen, the army marches to the
*enemy starting squares*, which the map declares (``players_starts``).

These tests cover:
  * the fallback picks the enemy start square and never the AI's own,
  * ``_eventually_attack`` really sends the units to the enemy square,
  * a map with no start squares keeps the old behaviour (no crash, no
    phantom attack),
  * the population-cap deadlock fix: an unaffordable house now asks the
    workers for the missing resources.
"""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer
    from soundrts.worldunit.worldsoldier import Soldier

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"

pytestmark = pytest.mark.skipif(
    not JL1.is_file(), reason="jl1 map not present"
)


@pytest.fixture
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


class _StubInterface:
    def queue_srv_event(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: None


def _build_jl1_world():
    world = World([], 42)
    world._parse_map(JL1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()
    faction = rules.factions[0] if rules.factions else "britons"
    human = DirectClient("idle_human", None)
    human.faction = faction
    human.alliance = "1"
    human.interface = _StubInterface()
    cpu = DummyClient("intermediate")
    cpu.faction = faction
    cpu.alliance = "2"
    world.populate_map([human, cpu], random_starts=False, equivalents=True)
    comp = [p for p in world.players
            if getattr(p, "is_computer_player", False)][0]
    foe = [p for p in world.players if p is not comp][0]
    return world, comp, foe


# ---------------------------------------------------------------------------
# the blind-attack fallback
# ---------------------------------------------------------------------------

def test_blind_attack_targets_are_the_enemy_start_square(aoe2_loaded):
    """The fallback must point at the *other* player's start, not our own."""
    world, comp, _foe = _build_jl1_world()

    targets = comp._blind_attack_targets()
    assert targets, "the AI found no enemy start square to march on"

    own = {id(p) for p in comp._home_base_places()}
    assert all(id(t) not in own for t in targets), (
        "the AI would send its army to its own base"
    )

    foe_squares = {
        id(u.place)
        for u in _foe.units
        if getattr(u, "type_name", "") in ("townhall", "town_center")
    }
    assert foe_squares, "the opponent has no town hall"
    assert {id(t) for t in targets} & foe_squares, (
        "the blind-attack target is not the opponent's start square"
    )


def test_blind_attack_targets_empty_without_start_squares(aoe2_loaded):
    """A map with no recorded spawn squares must not produce a phantom target."""
    world, comp, _foe = _build_jl1_world()
    world.players_starts = []
    world.starting_squares = []
    for p in world.players:
        p._map_start_square = None
    assert comp._blind_attack_targets() == []


def test_blind_attack_targets_skip_allies(aoe2_loaded):
    """The AI must never march on an ally's town.

    A 4-player game has two enemies and one ally.  The blind-attack
    fallback must pick only the hostile players' start squares.
    """
    world, comp, foe = _build_jl1_world()
    ally = foe  # reuse the opponent as a stand-in ally
    ally.client.alliance = comp.client.alliance
    comp.update_alliance()
    # ``player_is_an_enemy`` caches its answer for 5 seconds of game time.
    comp._enemy_player_timestamp = -10 ** 9
    comp._enemy_player_cache = {}

    targets = comp._blind_attack_targets()
    assert targets == [], (
        "the AI would march on an ally's town when it has no enemy target"
    )


def test_blind_attack_targets_use_the_players_own_spawn_square(aoe2_loaded):
    """The target must be the square the *enemy player* spawned on.

    ``world.players_starts`` and ``world.players`` do not line up (the
    slots get shuffled by ``random_starts``), so the fallback has to use
    the spawn square each player remembers.
    """
    world, comp, foe = _build_jl1_world()

    foe_square = getattr(foe, "_map_start_square", None)
    assert foe_square is not None, "the player did not record its spawn square"
    targets = comp._blind_attack_targets()
    assert foe_square in targets, (
        "the blind-attack target is not the enemy player's spawn square"
    )


def test_eventually_attack_sends_the_army_to_the_enemy_start(aoe2_loaded):
    """The army must leave the base even though the enemy was never seen."""
    world, comp, foe = _build_jl1_world()
    # One tick so the per-tick bookkeeping (``_places_with_friends`` and
    # friends) is initialised.
    world.update()

    # Give the AI a small army directly, so the test does not depend on the
    # whole dark-age economy of jl1 (one starting villager, no food).
    from soundrts.definitions import rules as r

    militia = r.unit_class("militia")
    assert militia is not None, "aoe2 mod without militia"
    home = [u.place for u in comp.units
            if getattr(u, "type_name", "") in ("townhall", "town_center")][0]
    for _i in range(6):
        comp.add_unit(militia, home)
    soldiers = [u for u in comp.units if isinstance(u, Soldier)]
    if not soldiers:
        pytest.skip("cannot spawn units directly in this build")

    comp._enemy_presence = []
    assert comp._enemy_is_known() is False

    sent = []
    original_send = comp._send_units

    def spy(units, place, *a, **kw):
        sent.append((list(units), place))
        return original_send(units, place, *a, **kw)

    comp._send_units = spy
    comp._eventually_attack([])

    assert sent, "the AI did not send anybody anywhere"
    own = {id(p) for p in comp._home_base_places()}
    off_base = [s for s in sent if id(s[1]) not in own]
    assert off_base, "the whole army stayed in the home base"
    for _units, place in off_base:
        assert place in comp._blind_attack_targets()


def test_eventually_attack_without_targets_does_nothing(aoe2_loaded):
    """No enemy, no start squares: the old behaviour (stay home) is kept."""
    world, comp, _foe = _build_jl1_world()
    world.players_starts = []
    world.starting_squares = []
    sent = []
    comp._send_units = lambda units, place, *a, **kw: sent.append(place)
    comp._eventually_attack([])
    assert not sent


# ---------------------------------------------------------------------------
# the population-cap deadlock
# ---------------------------------------------------------------------------

def test_unaffordable_house_asks_the_workers_for_the_missing_resource(
    aoe2_loaded,
):
    """An AI stuck at the population cap must not sit there silently.

    On jl1 the AI paid for a barracks and was left with too little gold and
    wood to afford either the next villager or the next house, so the
    population stayed capped for minutes.  ``_ensure_housing`` now asks the
    workers for whatever the house is missing.
    """
    world, comp, _foe = _build_jl1_world()

    asked = []
    comp._send_workers_toward_resources = lambda idx, **kw: asked.append(
        list(idx)
    )
    # Pretend every house type is buildable and unaffordable.
    comp._housing_type_names = lambda: ["house"]
    comp._worker_buildable_type_names = lambda: ["house"]
    comp.missing_resources = lambda cost: [0, 1]
    comp.future_nb = lambda name: 0
    comp.nb = lambda name: 0
    # The population is capped: that is the situation the fix is about.
    comp.population = 10
    comp.used_population = 10

    assert comp._ensure_housing() is False
    assert asked, "the AI did not ask the workers for the missing resources"
    assert set(asked[0]) == {0, 1}
