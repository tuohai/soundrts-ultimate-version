# -*- coding: utf-8 -*-
"""StarCraft lurker / colossus line-pierce like AoE2 scorpion."""
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


def test_lurker_and_colossus_have_rdg_pierce_line():
    r = _load()
    lurker = r.unit_class("lurker")
    burrowed = r.unit_class("burrowed_lurker")
    colossus = r.unit_class("colossus")
    hydra = r.unit_class("hydralisk")
    for u in (lurker, burrowed, colossus):
        assert int(getattr(u, "rdg_pierce_line", 0) or 0) == 1, u
        assert getattr(u, "rdg_projectile", 0)
    assert int(getattr(hydra, "rdg_pierce_line", 0) or 0) == 0
    assert "lurker" in r.unit_class("larva").can_upgrade_to
    assert "lurker" in r.unit_class("hydralisk").can_change_to
    assert "lurker_den" in r.get("lurker", "requirements", ())
    assert "robotics_bay" in r.get("colossus", "requirements", ())
    assert "colossus" in r.class_can_train(r.unit_class("robotics_facility"))
    assert r.unit_class("lurker_den") is not None
    assert r.unit_class("robotics_facility") is not None


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


def test_headless_lurker_pierce_line_volley():
    """Aim past two marines: both extras take full lurker-vs-light damage; off-line missed."""
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
        lurker_cls = rules.unit_class("lurker")
        marine_cls = rules.unit_class("marine")
        lurker_cls.collision = 0
        marine_cls.collision = 0
        lurker = lurker_cls(zerg.player, sq, cx, cy)
        lurker.rdg_crit_rate = 0
        lurker.rdg_cover = 100 * PRECISION
        # Line along +x; aim at the farthest so the segment covers the two in front.
        mid1 = marine_cls(terran.player, sq, cx + 800, cy)
        mid2 = marine_cls(terran.player, sq, cx + 1600, cy)
        primary = marine_cls(terran.player, sq, cx + 2400, cy)
        off = marine_cls(terran.player, sq, cx + 1600, cy + 800)
        for m in (mid1, mid2, primary, off):
            m.hp_max = 200 * PRECISION
            m.hp = 200 * PRECISION
            m.rdf = 0
            m.mdf = 0
            m.rdg = 0
            m.mdg = 0
            zerg.player.perception.add(m)
        world._update_buckets()

        hits = []
        orig = Creature.receive_hit

        def wrapped(self, damage, attacker, *a, **k):
            orig(self, damage, attacker, *a, **k)
            if attacker is lurker:
                hits.append((self.id, int(damage)))

        Creature.receive_hit = wrapped
        try:
            lurker.take_order(
                ["attack", primary.id], imperative=True, forget_previous=True
            )
            lurker.ai_mode = "guard"
            for _ in range(int(3000 / VIRTUAL_TIME_INTERVAL)):
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

    vs = lurker._get_ranged_damage_vs(primary)
    assert vs > 0
    ids = [h[0] for h in hits[:3]]
    dmgs = [h[1] for h in hits[:3]]
    assert ids[0] == primary.id
    assert set(ids[1:]) == {mid1.id, mid2.id}
    assert off.id not in ids
    assert dmgs == [vs, vs, vs]
    print(
        "lurker pierce volley: primary %s + extras %s, %s  dmg=%s (tiles %s); off-line missed"
        % (
            primary.id,
            ids[1],
            ids[2],
            vs,
            vs / PRECISION,
        )
    )
