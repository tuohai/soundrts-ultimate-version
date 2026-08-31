# -*- coding: utf-8 -*-
"""StarCraft mutalisk glaive bounce."""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts.combat.bounce import scale_bounce_damage
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, Rules, _get_base_classes, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient
    from soundrts.worldunit import Creature

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]


def _load():
    r = Rules()
    r.load(
        (ROOT / "mods/starcraft/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    return r


def test_mutalisk_has_rdg_bounce():
    r = _load()
    muta = r.unit_class("mutalisk")
    hydra = r.unit_class("hydralisk")
    assert int(getattr(muta, "rdg_bounce", 0) or 0) == 2
    assert int(getattr(muta, "rdg_bounce_range", 0) or 0) == 3 * PRECISION
    assert int(getattr(muta, "rdg_bounce_decay", 0) or 0) == 33
    assert getattr(muta, "rdg_projectile", 0)
    assert int(getattr(hydra, "rdg_bounce", 0) or 0) == 0


_MAP = """
nb_columns 3
nb_lines 3
nb_players_min 1
nb_players_max 2
starting_squares a1 c3
starting_resources 0 0
terrain plain a1 a2 a3 b1 b2 b3 c1 c2 c3
"""


def _sq(world, label):
    col = ord(label[0]) - ord("a")
    row = int(label[1]) - 1
    return world.grid["%s,%s" % (col, row)]


def test_headless_mutalisk_bounce_volley():
    """One glaive volley vs three clustered marines: 6 → ~2 → ~0.65."""
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "starcraft"
    res.set_mods("starcraft")
    res.load_rules_and_ai()
    try:
        world = World([], 7)
        world._parse_map(_MAP)
        world.square_width = int(world.square_width * PRECISION)
        world._build_map()
        world.treaty_until_time = 0
        zerg = DirectClient("zerg", None)
        zerg.faction = "zerg"
        zerg.alliance = "1"
        zerg.create_player(world)
        terran = DirectClient("terran", None)
        terran.faction = "terran"
        terran.alliance = "2"
        terran.create_player(world)
        sq = _sq(world, "b2")
        cx, cy = sq.x, sq.y
        muta_cls = rules.unit_class("mutalisk")
        marine_cls = rules.unit_class("marine")
        old_muta_col = muta_cls.collision
        old_marine_col = marine_cls.collision
        muta_cls.collision = 0
        marine_cls.collision = 0
        muta = muta_cls(zerg.player, sq, cx, cy)
        muta.rdg_crit_rate = 0
        muta.rdg_cover = 100 * PRECISION
        primary = marine_cls(terran.player, sq, cx + 400, cy)
        near = marine_cls(terran.player, sq, cx + 900, cy)
        far = marine_cls(terran.player, sq, cx + 1600, cy)
        for m in (primary, near, far):
            m.hp_max = 200 * PRECISION
            m.hp = 200 * PRECISION
            m.rdf = 0
            m.mdf = 0
            m.rdg = 0
            m.mdg = 0
        world._update_buckets()

        hits = []
        orig = Creature.receive_hit

        def wrapped(self, damage, attacker, *a, **k):
            orig(self, damage, attacker, *a, **k)
            if attacker is muta:
                hits.append((self.id, int(damage)))

        Creature.receive_hit = wrapped
        try:
            muta.take_order(
                ["attack", primary.id], imperative=True, forget_previous=True
            )
            for _ in range(int(2500 / VIRTUAL_TIME_INTERVAL)):
                world.update()
                if len(hits) >= 3:
                    break
        finally:
            Creature.receive_hit = orig
    finally:
        config.mods = old
        res.set_mods(old or "")
        res.load_rules_and_ai()
        logging.disable(logging.NOTSET)
        try:
            muta_cls.collision = old_muta_col
            marine_cls.collision = old_marine_col
        except NameError:
            pass

    rdg = int(muta.rdg)
    decay = int(muta.rdg_bounce_decay or 33)
    expect = [
        rdg,
        scale_bounce_damage(rdg, decay, 1),
        scale_bounce_damage(rdg, decay, 2),
    ]
    assert [h[1] for h in hits[:3]] == expect
    assert [h[0] for h in hits[:3]] == [primary.id, near.id, far.id]
    print(
        "mutalisk bounce volley: %s -> %s -> %s (tiles %s -> %s -> %s)"
        % (
            expect[0],
            expect[1],
            expect[2],
            expect[0] / PRECISION,
            expect[1] / PRECISION,
            expect[2] / PRECISION,
        )
    )
