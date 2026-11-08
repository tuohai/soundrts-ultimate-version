# -*- coding: utf-8 -*-
"""res intermediate AI: discovers the enemy and attacks on a stable schedule.

Regression coverage for the jl1 "sometimes attacks at 10 min, sometimes never
attacks until 16-20 min" bug.

Root cause (fixed in ``soundrts/worldunit/worldcreature.py``):
``_pick_unknown_squares`` probed ``player.strictly_observed_squares``, an
attribute that does not exist on ``PlayerBase``.  ``getattr`` therefore
returned ``None`` and the function fell back to ``world.squares[:10]`` — a
fixed prefix.  Once the scout had walked past the first few squares, the
destination oscillated between two squares forever, so the AI stayed blind
until an AI building site happened to come within sight range.  First
discovery therefore ranged from 8m07s to 16m59s depending on which opening
branch the random plan picked, and the attack could not be dispatched before
discovery (the attack gate needs ``_enemy_presence``).

The fix uses the *cumulative* ``strictly_observed_before_squares`` set and
reproduces 1.3.8.1's ``random.sample`` semantics on normal-sized maps, which
makes first discovery uniform at ~3m32s on jl1.
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

# Discovery must be the same for every seed (the jitter loop made it depend
# on the random opening branch, 8m07s .. 16m59s).
DISCOVERY_LIMIT_MS = 5 * 60 * 1000


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
    """Build a headless jl1 match: player 0 is the idle "human", player 1 the AI.

    The human side is a ``DirectClient`` (a real ``Human`` player that never
    issues orders); the CPU side is a ``DummyClient("intermediate")`` so it
    becomes a scripted ``Computer``.
    """
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


def test_pick_unknown_squares_uses_cumulative_observed_set(res_loaded):
    """The unknown-square probe must read the attribute that actually exists.

    ``strictly_observed_squares`` (per-frame) does not exist on PlayerBase;
    reading it always produced ``None`` and degraded the AI to a fixed
    ``world.squares[:10]`` prefix.
    """
    import inspect

    from soundrts.worldplayerbase.base import Player
    from soundrts.worldunit.worldcreature import Creature

    # The cumulative set is what the probe must use.
    assert hasattr(Player, "strictly_observed_before_squares") or (
        "strictly_observed_before_squares" in Player.__init__.__code__.co_names
    )
    # The per-frame name must NOT be probed: it does not exist on the player.
    assert "strictly_observed_squares" not in Player.__init__.__code__.co_names

    src = inspect.getsource(Creature._pick_unknown_squares)
    # Strip the docstring: only the code matters.
    code = src.split('"""', 2)[-1] if src.count('"""') >= 2 else src
    assert "strictly_observed_before_squares" in code
    assert "strictly_observed_squares" not in code


def test_pick_unknown_squares_excludes_seen_squares(res_loaded):
    """A square already seen must never be handed out as an explore target."""
    from soundrts.worldunit.worldcreature import Creature

    class _FakePlayer:
        def __init__(self, squares, observed):
            self._squares = squares
            self.strictly_observed_before_squares = set(observed)

        @property
        def world(self):
            return self

        @property
        def squares(self):
            return self._squares

        class random:
            @staticmethod
            def sample(population, k):
                return list(population)[:k]

    squares = [object() for _ in range(20)]
    seen = squares[:5]
    player = _FakePlayer(squares, seen)
    creature = Creature.__new__(Creature)
    creature.player = player
    picked = creature._pick_unknown_squares(max_n=10)
    assert len(picked) == 10
    for s in picked:
        assert s not in seen


def test_res_jl1_intermediate_discovers_enemy_fast_and_uniformly(res_loaded):
    """Every seed must find the human base within 5 minutes (was 8-17 min)."""
    if not JL1.is_file():
        pytest.skip("res jl1 map not present")

    discoveries = []
    for seed in (42, 43, 44, 45, 46):
        world, hp, comp = _build_world(seed)
        disc = None
        ticks = int((10 * 60 * 1000) / VIRTUAL_TIME_INTERVAL)
        for _ in range(ticks):
            world.update()
            if disc is None:
                for o in comp.perception:
                    if getattr(o, "player", None) is hp:
                        disc = world.time
                        break
            if disc is not None:
                break
        assert disc is not None, f"seed {seed}: AI never discovered the human base"
        discoveries.append(disc)

    assert max(discoveries) <= DISCOVERY_LIMIT_MS, discoveries
    # Uniform across seeds: the old jitter loop made this depend on the
    # random opening branch.
    assert max(discoveries) - min(discoveries) < 1000, discoveries


def test_res_intermediate_phase2_wave_is_not_blocked_by_castle_age(res_loaded):
    """The first phase2 wave must not require castle_age units.

    ``new_flyingmachine`` / ``knight`` / ``priest`` all need castle_age, so a
    single mixed get line stalled the whole opening wave until castle was
    researched (~2.5 minutes later) and delayed the first attack.
    """
    from soundrts.definitions import get_ai

    plan = get_ai("intermediate")
    idx = plan.index("label phase2")
    # The first get line after ``label phase2`` must be satisfiable in
    # feudal age: it may only ask for archer/footman-class units.
    first_get = plan[idx + 1]
    assert first_get.startswith("get ")
    assert "new_flyingmachine" not in first_get
    assert "knight" not in first_get
    assert "priest" not in first_get


def test_res_jl1_intermediate_attacks_by_ten_minutes(res_loaded):
    """The AI must reach the human base and start fighting within ~10 min."""
    if not JL1.is_file():
        pytest.skip("res jl1 map not present")

    for seed in (42, 45, 47):
        world, hp, comp = _build_world(seed)
        human_start = next(
            (u.place for u in hp.units if getattr(u, "is_a_building", False)), None
        )
        enter = None
        ticks = int((12 * 60 * 1000) / VIRTUAL_TIME_INTERVAL)
        for _ in range(ticks):
            world.update()
            if human_start is not None:
                for u in list(comp.units):
                    tn = getattr(u, "type_name", "")
                    if (
                        not getattr(u, "is_a_building", False)
                        and tn not in ("peasant", "worker")
                        and u.place is human_start
                    ):
                        enter = world.time
                        break
            if enter is not None:
                break
        assert enter is not None, f"seed {seed}: AI never reached the human base"
        assert enter <= 10 * 60 * 1000, (seed, enter)
