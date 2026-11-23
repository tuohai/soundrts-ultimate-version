#!/usr/bin/env python3
"""Shared helpers for the ``can_reach`` verification tools.

These tools back the claims made in the 1.5.2.5 release notes:

* the differential test  (``diff_test.py``)
* the exhaustive test   (``exhaustive_test.py``)
* the A/B cost probe    (``ab_probe.py``)

They build a headless world directly, so they do not depend on the
ad-hoc ``bench_headless.py`` scratch script.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
MAP = ROOT / "res" / "multi" / "cw1.txt"

#: The benchmark configuration quoted in the release notes.
NB_AI = 15
AI_TYPE = "beginner"
SEED = 42

os.chdir(ROOT)
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, str(ROOT))

import warnings  # noqa: E402

warnings.simplefilter("ignore")


def silence_logs() -> None:
    import logging

    logging.disable(logging.CRITICAL)
    try:
        from soundrts.lib import log as _log

        _log.warning = lambda *a, **k: None
        _log.info = lambda *a, **k: None
        _log.debug = lambda *a, **k: None
    except Exception:
        pass


def build_world(map_path: Path = MAP, nb_ai: int = NB_AI, ai_type: str = AI_TYPE,
                seed: int = SEED, all_ai: bool = True, mods: str = ""):
    """Build a headless world with *nb_ai* computer players."""
    from soundrts.definitions import rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient, DummyClient

    if mods:
        res.set_mods(mods)
    res.load_rules_and_ai()
    text = map_path.read_text(encoding="utf-8")
    world = World([], seed)
    world._parse_map(text)
    world.square_width = int(world.square_width * PRECISION)
    world._build_map()

    clients = []
    if not all_ai:
        human = DirectClient("bench_human", None)
        human.faction = rules.factions[0]
        human.alliance = "1"
        clients.append(human)
    for i in range(nb_ai):
        c = DummyClient(ai_type)
        c.faction = rules.factions[0]
        c.alliance = "1" if i < nb_ai // 2 else "2"
        clients.append(c)
    world.populate_map(clients, random_starts=False)
    return world


def run_world(world, game_minutes: float) -> int:
    """Advance *world* for *game_minutes* of in-game time; return the tick count."""
    limit = int(game_minutes * 60 * 1000)
    ticks = 0
    while world.time < limit:
        world.update()
        ticks += 1
    return ticks


def use_legacy_can_reach(legacy: bool) -> None:
    """Set the ``SOUNDRTS_LEGACY_CAN_REACH`` toggle and reimport the engine."""
    if legacy:
        os.environ["SOUNDRTS_LEGACY_CAN_REACH"] = "1"
    else:
        os.environ.pop("SOUNDRTS_LEGACY_CAN_REACH", None)
    for mod in list(sys.modules):
        if mod.startswith("soundrts"):
            del sys.modules[mod]
