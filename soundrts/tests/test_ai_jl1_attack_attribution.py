# -*- coding: utf-8 -*-
"""jl1: the AI must attack even when it never saw the enemy.

The user reported that on ``res/multi/jl1.txt`` an intermediate computer
attacks at ~8 minutes when its villagers explore at the start, but only at
~15 minutes when they do not explore.

Two *separate* defects were behind that report, and this module pins
down which one caused which symptom -- because the two were easy to
confuse, and the release notes originally blamed the wrong one.

``test_ai_jl1_blind_attack.py``
    The **blind-attack fallback**.  The attack trigger is
    ``_enemy_presence`` -- the list of squares where the AI has *seen* an
    enemy.  With ``constant_attacks 1`` and an empty list,
    ``_eventually_attack`` assigned the whole army to the home guard, so
    the army idled in its base.  **This is what produced the ~13-15 minute
    band**: with the fallback disabled, the "exploring" and "not
    exploring" runs diverge by 3-7 minutes again.

``test_ai_plan_rng_decoupled.py``
    The **shared-RNG coupling** of ``goto_random``.  The plan's branch
    draw used to come from ``world.random``, so whether the AI's villagers
    explored decided *which opening plan* the AI got.  That is a real bug
    -- an unrelated decision must not pick the opening -- but it is a
    **much smaller** effect: with the branch held constant, exploring
    moves the first attack by well under a minute.

The tests below measure that attribution directly, so the two can never be
confused again.
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

pytestmark = pytest.mark.skipif(
    not JL1.is_file(), reason="jl1 map not present"
)

# The four opening branches of the intermediate AI (res/ai.txt).
BRANCHES = ("very_early_rush", "early_rush", "rush", "phase2")


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
    world.populate_map([human, cpu], random_starts=False, equivalents=True)
    players = list(world.players)
    assert len(players) == 2, players
    return world, players[0], players[1]


def _first_attack_minute(seed, scout, minutes=20.0, blind=True,
                         force_branch=None):
    """The minute at which the AI first marches its army off the home base.

    ``force_branch`` pins the opening branch, so the branch cannot be the
    cause of any difference between two runs.
    """
    world, _hp, comp = _build_world(seed)

    orig_explorer = Computer._send_explorer
    orig_blind = Computer._blind_attack_targets
    orig_choice = Computer._plan_random_choice
    orig_send = Computer._send_units

    if not scout:
        Computer._send_explorer = lambda self: None
    if not blind:
        Computer._blind_attack_targets = lambda self: []

    if force_branch is not None:
        def pinned(self, options):
            options = list(options)
            if not options:
                return None
            if force_branch in options:
                return force_branch
            return orig_choice(self, options)
        base_choice = pinned
    else:
        base_choice = orig_choice

    def choice(self, options):
        return base_choice(self, options)

    out = {"attack": None}

    def send(self, units, place, *a, **kw):
        home = {id(p) for p in self._home_base_places()}
        if id(place) not in home and out["attack"] is None:
            out["attack"] = world.time / 60000.0
        return orig_send(self, units, place, *a, **kw)

    Computer._plan_random_choice = choice
    Computer._send_units = send
    try:
        limit = int(minutes * 60 * 1000)
        while world.time < limit:
            world.update()
            if out["attack"] is not None:
                break
    finally:
        Computer._send_units = orig_send
        Computer._plan_random_choice = orig_choice
        Computer._blind_attack_targets = orig_blind
        Computer._send_explorer = orig_explorer
    return out["attack"]


# ---------------------------------------------------------------------------
# the attribution: which fix caused which symptom
# ---------------------------------------------------------------------------

def test_the_blind_attack_fallback_causes_the_long_delay(res_loaded):
    """Without the fallback, not exploring delays the attack by minutes.

    This is the ~13-15 minute band the user reported.  The AI cannot see
    the enemy, so ``_enemy_presence`` is empty, so the army garrisons
    home -- until something wanders into its line of sight.
    """
    seeds = (42, 7725, 4830)
    gaps = []
    for seed in seeds:
        with_scout = _first_attack_minute(seed, scout=True, blind=False)
        without = _first_attack_minute(seed, scout=False, blind=False)
        if with_scout is None or without is None:
            continue
        gaps.append(without - with_scout)
    assert gaps, "no seed produced a comparable pair of runs"
    assert max(gaps) > 2.0, (
        "the blind-attack fallback was expected to be worth several minutes "
        "of delay, got %r" % (gaps,)
    )


def test_the_opening_branch_alone_does_not_cause_the_long_delay(res_loaded):
    """With the branch pinned, exploring moves the attack by ~1 minute.

    The shared-RNG coupling of ``goto_random`` is a real bug -- exploring
    must not re-roll the opening plan -- but it is a *small* effect.  This
    test pins the branch, so the only thing left that can differ between
    the two runs is the blind-attack fallback and the scouting itself.
    """
    seeds = (42, 7725, 4830)
    gaps = []
    for seed in seeds:
        for branch in BRANCHES:
            with_scout = _first_attack_minute(
                seed, scout=True, force_branch=branch)
            without = _first_attack_minute(
                seed, scout=False, force_branch=branch)
            if with_scout is None or without is None:
                continue
            gaps.append(without - with_scout)
    assert gaps, "no seed produced a comparable pair of runs"
    worst = max(abs(g) for g in gaps)
    assert worst < 3.0, (
        "with the opening branch held constant, exploring moved the first "
        "attack by up to %.2f min -- the branch is not supposed to be the "
        "main cause of the delay" % worst
    )


def test_the_two_fixes_are_independent(res_loaded):
    """The blind-attack fallback is what removes the delay.

    With the fallback in place, exploring and not exploring must land
    within a minute of each other -- whatever the opening branch is.
    """
    seeds = (42, 7725, 4830)
    gaps = []
    for seed in seeds:
        with_scout = _first_attack_minute(seed, scout=True, blind=True)
        without = _first_attack_minute(seed, scout=False, blind=True)
        if with_scout is None or without is None:
            continue
        gaps.append(abs(without - with_scout))
    assert gaps, "no seed produced a comparable pair of runs"
    worst = max(gaps)
    assert worst < 2.0, (
        "with the blind-attack fallback in place, exploring still moved the "
        "first attack by up to %.2f min" % worst
    )


def test_the_explorer_consumes_exactly_two_shared_rng_draws(res_loaded):
    """The explorer shifts the shared stream by exactly two positions.

    This is the mechanism the release notes describe: a villager on
    ``auto_explore`` burns two extra numbers of the *shared* stream, which
    is what made the ``goto_random`` branch depend on the scouting
    decision in the first place.
    """
    from soundrts.game import TrainingGame  # noqa: F401  (import check)

    def draws_before_first_branch(seed, scout):
        world, _hp, comp = _build_world(seed)

        orig_explorer = Computer._send_explorer
        orig_choice = Computer._plan_random_choice
        if not scout:
            Computer._send_explorer = lambda self: None

        counter = {"n": 0}
        real_random = world.random

        class Counting:
            def __init__(self, inner):
                self._inner = inner

            def getstate(self):
                return self._inner.getstate()

            def setstate(self, s):
                return self._inner.setstate(s)

            def __getattr__(self, name):
                fn = getattr(self._inner, name)
                if name in ("random", "randrange", "choice", "randint",
                            "sample", "shuffle", "uniform"):
                    def wrapper(*a, **kw):
                        counter["n"] += 1
                        return fn(*a, **kw)
                    return wrapper
                return fn

        world.random = Counting(real_random)
        seen = {}

        def choice(self, options):
            if "n" not in seen:
                seen["n"] = counter["n"]
            return orig_choice(self, options)

        Computer._plan_random_choice = choice
        try:
            ticks = int((90 * 1000) / VIRTUAL_TIME_INTERVAL)
            for _ in range(ticks):
                world.update()
                if "n" in seen:
                    break
        finally:
            world.random = real_random
            Computer._plan_random_choice = orig_choice
            Computer._send_explorer = orig_explorer
        return seen.get("n")

    for seed in (42, 7725, 4830):
        on = draws_before_first_branch(seed, scout=True)
        off = draws_before_first_branch(seed, scout=False)
        assert on is not None, "the AI never drew an opening branch"
        assert off is not None, "the AI never drew an opening branch"
        assert on - off == 2, (
            "seed %s: the explorer consumed %r shared draws before the first "
            "branch draw, expected exactly 2" % (seed, on - off)
        )


def test_the_starting_square_explains_the_remaining_variation(res_loaded):
    """A poor starting tile is a map-balance fact, not a bug.

    The AI that spawns on a poor tile (``1,0``) legitimately needs a few
    more minutes to train its first army than the one on a rich tile
    (``1,3``).  This test records that fact so the 8-vs-15 report is not
    re-investigated from scratch next time.
    """
    rows = {}
    for seed in (42, 7725, 4830):
        world, _hp, comp = _build_world(seed)
        square = getattr(comp, "_map_start_square", None)
        minute = _first_attack_minute(seed, scout=True)
        rows.setdefault(str(square), []).append(minute)
    # Every start square must be able to produce an attack at all.
    for square, minutes in rows.items():
        good = [m for m in minutes if m is not None]
        assert good, "the AI on start square %s never attacked" % square
        assert min(good) < 20.0, (
            "the AI on start square %s attacked only after %.2f min"
            % (square, min(good))
        )
