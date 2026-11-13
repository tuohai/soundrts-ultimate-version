#!/usr/bin/env python3
"""Sweep seeds on the real jl1 game path and report when the AI attacks.

For every seed we run 4 configurations:

    scout=on/off   x   blind-attack fix on/off

and report the minute at which the AI first marched its army off the home
base towards the enemy.  The user's complaint is that this number swings
between ~8 min and ~13 min depending on whether the AI's villagers explore.
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(_HERE))
_REAL_ARGV = sys.argv[1:]
sys.argv = [sys.argv[0]]

import logging

from soundrts import config
from soundrts.lib.resource import res

logging.disable(logging.WARNING)
config.mods = ""
res.set_mods("")
res.load_rules_and_ai()

from soundrts.game import TrainingGame
from soundrts.mapfile import Map
from soundrts.world import World
from soundrts.worldplayercomputer import Computer
from soundrts.worldunit.worldsoldier import Soldier

JL1 = _HERE / "res" / "multi" / "jl1.txt"


class _StubInterface:
    def queue_srv_event(self, *a, **k):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: None


def run(seed, scout, blind, minutes=18.0, trace=False, old_rng=False):
    m = Map(str(JL1))
    game = TrainingGame(m, ["test", "intermediate"],
                        ["random_faction", "random_faction"], ["1", "2"])
    game.record_replay = False
    game.seed = seed
    game.world = World(game.default_triggers, seed)
    game.world.load_and_build_map(m)
    for p in game.players:
        if not hasattr(p, "interface"):
            p.interface = _StubInterface()
    game.world.populate_map(game.players, equivalents=True)

    comp = next(p for p in game.world.players if isinstance(p, Computer))
    foe = next(p for p in game.world.players if p is not comp)

    orig_blind = Computer._blind_attack_targets
    orig_explorer = Computer._send_explorer
    orig_send = Computer._send_units
    orig_choice = Computer._plan_random_choice
    if not blind:
        Computer._blind_attack_targets = lambda self: []
    if not scout:
        Computer._send_explorer = lambda self: None
    if old_rng:
        # The pre-fix behaviour: the plan's ``goto_random`` drew its branch
        # from the *shared* world RNG, so exploring (or not) shifted the
        # stream and re-rolled the AI's opening plan.
        def old_choice(self, options):
            options = list(options)
            if not options:
                return None
            return self.world.random.choice(options)
        Computer._plan_random_choice = old_choice

    out = {"first_attack": None, "first_sighting": None, "first_army": None,
           "sight_min": None, "army_min": None}

    def send(self, units, place, *a, **kw):
        home = {id(p) for p in self._home_base_places()}
        if id(place) not in home and out["first_attack"] is None:
            out["first_attack"] = self.world.time / 60000.0
            out["army_min"] = len(list(units))
        return orig_send(self, units, place, *a, **kw)

    Computer._send_units = send

    try:
        limit = int(minutes * 60 * 1000)
        while game.world.time < limit:
            game.world.update()
            minute = game.world.time / 60000.0
            if out["first_sighting"] is None and getattr(comp, "_enemy_presence", None):
                out["first_sighting"] = minute
            if out["first_army"] is None:
                if any(isinstance(u, Soldier) for u in (comp.units or ())):
                    out["first_army"] = minute
            if getattr(comp, "defeated", False):
                break
    finally:
        Computer._send_units = orig_send
        Computer._blind_attack_targets = orig_blind
        Computer._send_explorer = orig_explorer
        Computer._plan_random_choice = orig_choice
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--seeds", type=int, default=8)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--minutes", type=float, default=18.0)
    p.add_argument("--old-rng", action="store_true",
                   help="reproduce the pre-fix behaviour: the plan's "
                        "goto_random branch is drawn from the shared world RNG")
    p.add_argument("--seed-list", type=str, default=None,
                   help="comma-separated explicit seeds (overrides --seeds)")
    a = p.parse_args(_REAL_ARGV)

    if a.seed_list:
        seeds = [int(x) for x in a.seed_list.replace(" ", "").split(",") if x]
    else:
        seeds = [a.start + i for i in range(a.seeds)]
    table = {}
    for scout in (True, False):
        for blind in (True, False):
            times = []
            for s in seeds:
                r = run(s, scout, blind, a.minutes, old_rng=a.old_rng)
                times.append(r["first_attack"])
                print(f"  seed={s:5d} scout={'on ' if scout else 'off'} "
                      f"fix={'on ' if blind else 'off'}  "
                      f"attack={r['first_attack']}  "
                      f"army_at={r['army_min']}  "
                      f"sighting={r['first_sighting']}")
            good = [t for t in times if t is not None]
            table[(scout, blind)] = good
            print()

    print("=" * 70)
    print("首次进攻时间分布（分钟）"
          + ("  [旧行为: 分支取自 world.random]" if a.old_rng else ""))
    print("=" * 70)
    for (scout, blind), good in table.items():
        if not good:
            print(f"  scout={'on ' if scout else 'off'} fix={'on ' if blind else 'off'}"
                  f"  : 从未进攻")
        else:
            print(f"  scout={'on ' if scout else 'off'} fix={'on ' if blind else 'off'}"
                  f"  : min={min(good):.2f} max={max(good):.2f} "
                  f"avg={statistics.mean(good):.2f} "
                  f"极差={max(good) - min(good):.2f}")
    return table


if __name__ == "__main__":
    main()
