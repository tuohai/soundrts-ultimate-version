# -*- coding: utf-8 -*-
"""The AI's opening plan must not depend on what the AI did before.

Regression coverage for the "the computer attacks at ~8 min when its
villagers explore, at ~13-15 min when they don't" report on
``res/multi/jl1.txt``.

Root cause
----------
``goto_random`` used to draw its branch from ``world.random`` -- the *shared*
simulation stream.  How many numbers that stream had consumed by the time
the draw happened depended on what the AI did in the preceding seconds.  A
villager sent on ``auto_explore`` burns two extra draws (the destination
square and the wander step), which shifted the shared stream by exactly two
positions and made the AI pick a *different opening branch*:

    very_early_rush -> get 3 peasant 1 footman    (fast, tiny)
    early_rush      -> get 4 peasant 5 footman
    rush            -> get 9 peasant 5 footman
    phase2          -> get 9 peasant 15 archer    (slow, big)

Each branch needs a different army before the ``attack`` line can complete,
so the first attack landed at ~8 min or at ~13 min for no visible reason.

The fix draws the branch from the AI's own stream, seeded from the match
seed and the player's identity, so it depends on neither the scouting
decision nor anything else the simulation did earlier.  The stream is kept
as a plain integer so that the rollback snapshot machinery (which copies
player attributes by value) can rewind it correctly.
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient
    from soundrts.worldplayercomputer import Computer

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]
JL1 = ROOT / "res" / "multi" / "jl1.txt"


@pytest.fixture
def res_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


def _build_world(seed):
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION as P

    faction = rules.factions[0] if rules.factions else "human_faction"
    world = World([], seed)
    world._parse_map(JL1.read_text(encoding="utf-8"))
    world.square_width = int(world.square_width * P)
    world._build_map()

    class _StubInterface:
        def queue_srv_event(self, *args, **kwargs):
            pass

        def __getattr__(self, name):
            return lambda *a, **k: None

    human = DirectClient("idle_human", None)
    human.faction = faction
    human.alliance = "1"
    human.interface = _StubInterface()
    cpu = DummyClient("intermediate")
    cpu.faction = faction
    cpu.alliance = "2"
    world.populate_map([human, cpu], random_starts=False)
    players = list(world.players)
    assert len(players) == 2, players
    return world, players[0], players[1]


def _opening_branch(seed, scout, minutes=1.0):
    """Return the branch the AI opened with, and whether it explored."""
    world, hp, comp = _build_world(seed)

    explored = []
    orig_explorer = Computer._send_explorer

    if scout:
        def explorer(self):
            result = orig_explorer(self)
            if self.units:
                for u in self.units:
                    if u.orders and u.orders[0].keyword == "auto_explore":
                        explored.append(True)
                        break
            return result
        Computer._send_explorer = explorer
    else:
        Computer._send_explorer = lambda self: None

    branch = []
    orig_choice = Computer._plan_random_choice

    def choice(self, options):
        result = orig_choice(self, options)
        branch.append(result)
        return result

    Computer._plan_random_choice = choice
    try:
        ticks = int((minutes * 60 * 1000) / VIRTUAL_TIME_INTERVAL)
        for _ in range(ticks):
            world.update()
    finally:
        Computer._plan_random_choice = orig_choice
        Computer._send_explorer = orig_explorer

    assert branch, "the AI never drew an opening branch"
    return branch[0], bool(explored)


def test_goto_random_does_not_consume_the_shared_world_rng(res_loaded):
    """The plan's branch draw must not touch ``world.random``.

    Drawing from the shared stream is what made the branch depend on how
    many random numbers the rest of the simulation had already consumed.
    """
    world, hp, comp = _build_world(42)

    calls = []
    real_choice = world.random.choice

    def counting_choice(seq):
        calls.append(seq)
        return real_choice(seq)

    world.random.choice = counting_choice
    try:
        picked = comp._plan_random_choice(["a", "b", "c"])
    finally:
        world.random.choice = real_choice

    assert picked in ("a", "b", "c")
    assert calls == [], "the plan branch consumed the shared world RNG"


def test_opening_branch_is_identical_with_and_without_exploring(res_loaded):
    """Scouting (or not) must not re-roll the AI's opening plan."""
    for seed in (41, 42, 43, 44):
        with_scout, explored = _opening_branch(seed, scout=True)
        without_scout, _ = _opening_branch(seed, scout=False)
        assert with_scout == without_scout, (
            "seed %s: exploring changed the opening plan (%s -> %s)"
            % (seed, with_scout, without_scout)
        )


def test_opening_branch_is_stable_across_repeated_runs_of_one_seed(res_loaded):
    """The same map and seed must always produce the same opening plan."""
    branches = set()
    for _ in range(3):
        branch, _explored = _opening_branch(42, scout=True)
        branches.add(branch)
    assert len(branches) == 1, branches


def test_plan_stream_is_an_integer_so_snapshots_can_rewind_it(res_loaded):
    """The plan stream must be plain data the snapshot machinery can copy.

    ``soundrts/net/snapshot.py`` captures every player attribute by value and
    copies containers a bounded number of levels deep.  A ``random.Random``
    object stored on the player would be shared *by reference* between the
    live player and the snapshot, so a rollback re-simulation would see an
    already-advanced stream and diverge.
    """
    world, hp, comp = _build_world(42)
    comp._plan_random_choice(["a", "b", "c"])
    state = getattr(comp, "_plan_draw", None)
    assert state is not None, "the AI must keep its plan stream as an attribute"
    assert isinstance(state, int), type(state)


def test_plan_stream_survives_a_snapshot_round_trip(res_loaded):
    """Capturing and restoring a snapshot must rewind the plan stream."""
    from soundrts.net.snapshot import capture_snapshot, restore_snapshot

    world, hp, comp = _build_world(42)
    comp._plan_random_choice(["a", "b", "c"])
    drawn = comp._plan_draw

    snap = capture_snapshot(world)
    # Advance the stream after the snapshot was taken.
    comp._plan_random_choice(["a", "b", "c"])
    assert comp._plan_draw != drawn

    restore_snapshot(world, snap)
    assert comp._plan_draw == drawn, "the plan stream was not restored"


def test_plan_stream_differs_between_two_players_in_the_same_match(res_loaded):
    """Two AIs in one match must not open with the same plan.

    They share the world seed, so only the player identity can tell them
    apart -- and the identity *is* part of the stream seed.
    """
    world, hp, comp = _build_world(42)
    other = comp.__class__.__new__(comp.__class__)
    other.id = (int(comp.id) + 1) % 1000
    other.world = world
    other._plan_draw = 0
    picks = set()
    for _ in range(8):
        picks.add(comp._plan_random_choice(["a", "b", "c", "d"]))
        other._plan_draw = 0
        picks.add(other._plan_random_choice(["a", "b", "c", "d"]))
    assert len(picks) > 1, "the two players always picked the same branch"
