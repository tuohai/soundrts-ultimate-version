# -*- coding: utf-8 -*-
"""Headless AoE2 scorpion line-pierce (弩炮)."""
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
    from soundrts.definitions import VIRTUAL_TIME_INTERVAL, rules
    from soundrts.lib.nofloat import PRECISION
    from soundrts.lib.resource import res
    from soundrts.world import World
    from soundrts.worldclient import DirectClient
    from soundrts.worldunit import Creature

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

import pytest

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)

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


def test_headless_scorpion_pierce_line_volley():
    """Aim past two militia: both extras take full scorpion-vs-infantry dmg; off-line missed."""
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    try:
        world = World([], 7)
        world._parse_map(_MAP)
        world.square_width = int(world.square_width * PRECISION)
        world._build_map()
        world.treaty_until_time = 0
        p1 = DirectClient("p1", None)
        p1.faction = "britons"
        p1.alliance = "1"
        p1.create_player(world)
        p2 = DirectClient("p2", None)
        p2.faction = "britons"
        p2.alliance = "2"
        p2.create_player(world)
        sq = _sq(world, "b2")
        cx, cy = sq.x, sq.y
        scorp_cls = rules.unit_class("scorpion")
        mil_cls = rules.unit_class("militia")
        scorp_cls.collision = 0
        mil_cls.collision = 0
        scorp = scorp_cls(p1.player, sq, cx, cy)
        scorp.rdg_crit_rate = 0
        scorp.rdg_cover = 100 * PRECISION
        # Min range is 2 tiles; aim at 3.5 so the bolt segment covers two in front.
        mid1 = mil_cls(p2.player, sq, cx + 1200, cy)
        mid2 = mil_cls(p2.player, sq, cx + 2200, cy)
        primary = mil_cls(p2.player, sq, cx + 3500, cy)
        off = mil_cls(p2.player, sq, cx + 2200, cy + 800)
        for m in (mid1, mid2, primary, off):
            m.hp_max = 200 * PRECISION
            m.hp = 200 * PRECISION
            m.rdf = 0
            m.mdf = 0
            m.rdg = 0
            m.mdg = 0
            p1.player.perception.add(m)
        world._update_buckets()

        hits = []
        orig = Creature.receive_hit

        def wrapped(self, damage, attacker, *a, **k):
            before = int(getattr(self, "hp", 0) or 0)
            orig(self, damage, attacker, *a, **k)
            after = int(getattr(self, "hp", 0) or 0)
            if attacker is scorp:
                hits.append((self.id, before - after))

        Creature.receive_hit = wrapped
        try:
            scorp.take_order(
                ["attack", primary.id], imperative=True, forget_previous=True
            )
            scorp.ai_mode = "guard"
            for _ in range(int(5000 / VIRTUAL_TIME_INTERVAL)):
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

    vs = scorp._get_ranged_damage_vs(primary)
    assert int(getattr(scorp, "rdg_pierce_decay", 0) or 0) == 50
    assert vs > 0
    ids = [h[0] for h in hits[:3]]
    dmgs = [h[1] for h in hits[:3]]
    assert len(hits) >= 3, hits
    assert ids[0] == primary.id
    assert set(ids[1:]) == {mid1.id, mid2.id}
    assert off.id not in ids
    extra = (vs * 50 + 50) // 100
    assert dmgs == [vs, extra, extra]
    print(
        "scorpion pierce volley: primary %s dmg=%s (tiles %s); extras %s, %s dmg=%s (tiles %s); off-line missed"
        % (
            primary.id,
            vs,
            vs / PRECISION,
            ids[1],
            ids[2],
            extra,
            extra / PRECISION,
        )
    )
