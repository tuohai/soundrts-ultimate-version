# -*- coding: utf-8 -*-
"""heal_garrisoned: heal only transport passengers (AoE2 TC/castle/tower style)."""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.lib.nofloat import PRECISION
from soundrts.worldunit.world_status_update import CreatureStatusUpdate


class _Healer(CreatureStatusUpdate):
    pass


def _make_healer(*, garrisoned=1, heal_level=1):
    h = _Healer.__new__(_Healer)
    h.heal_level = heal_level
    h.heal_garrisoned = garrisoned
    h.heal_cd = 0
    h.heal_ready = 0
    h.heal_next_time = 0
    h.heal_prep_end_time = 0
    h.heal_target_type = ()
    h.heal_radius = 0
    h.heal_range = 0
    h.x = 0
    h.y = 0
    h.player = SimpleNamespace(player_is_an_enemy=lambda other: False)
    h.world = SimpleNamespace(time=1000, get_objects2=lambda *a, **k: [])
    h.inside = SimpleNamespace(objects=[])
    return h


def _make_unit(*, hp, hp_max, inside_healer=None):
    u = SimpleNamespace(
        hp=hp,
        hp_max=hp_max,
        is_healable=True,
        is_a_building=False,
        player=SimpleNamespace(),
    )
    if inside_healer is not None:
        inside_healer.inside.objects.append(u)
    return u


def test_heal_garrisoned_heals_passengers_only():
    healer = _make_healer(garrisoned=1)
    inside = _make_unit(hp=10 * PRECISION, hp_max=25 * PRECISION, inside_healer=healer)
    outside = _make_unit(hp=10 * PRECISION, hp_max=25 * PRECISION)
    healer.world.get_objects2 = lambda *a, **k: [outside]

    healer.heal_nearby_units()

    assert inside.hp > 10 * PRECISION
    assert outside.hp == 10 * PRECISION


def test_heal_without_garrisoned_flag_uses_area():
    healer = _make_healer(garrisoned=0)
    outside = _make_unit(hp=10 * PRECISION, hp_max=25 * PRECISION)
    healer.world.get_objects2 = lambda *a, **k: [outside]

    healer.heal_nearby_units()

    assert outside.hp > 10 * PRECISION


def test_aoe2_town_center_rules_flag():
    from pathlib import Path
    from soundrts.definitions import Rules
    from soundrts.lib.nofloat import PRECISION

    root = Path(__file__).resolve().parents[2]
    r = Rules()
    r.load(
        (root / "res" / "rules.txt").read_text(encoding="utf-8"),
        (root / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    tc = r.classes["town_center"]
    assert int(getattr(tc, "heal_garrisoned", 0) or 0) == 1
    assert int(getattr(tc, "heal_level", 0) or 0) == 1
    # DE 0.1 HP/s: heal_level 1 every heal_cd 10s
    assert int(getattr(tc, "heal_cd", 0) or 0) == 10 * PRECISION
    castle = r.classes["aoe_castle"]
    assert int(getattr(castle, "heal_garrisoned", 0) or 0) == 1
    assert int(getattr(castle, "heal_level", 0) or 0) == 1
    # DE 0.2 HP/s: heal_level 1 every heal_cd 5s
    assert int(getattr(castle, "heal_cd", 0) or 0) == 5 * PRECISION
    tower = r.classes["scouttower"]
    assert int(getattr(tower, "heal_garrisoned", 0) or 0) == 1
    assert int(getattr(tower, "heal_cd", 0) or 0) == 10 * PRECISION
    for name in (
        "vietnamese_castle",
        "celtic_castle",
        "aztec_castle",
        "viking_castle",
    ):
        shell = r.classes[name]
        assert int(getattr(shell, "heal_garrisoned", 0) or 0) == 1
    monastery = r.classes["monastery"]
    assert int(getattr(monastery, "heal_level", 0) or 0) == 0
    monk = r.classes["monk"]
    assert int(getattr(monk, "heal_level", 0) or 0) == 1
    # DE ~150 HP/min ≈ 1 HP / 0.4s
    assert int(getattr(monk, "heal_cd", 0) or 0) == int(0.4 * PRECISION)
    missionary = r.classes["missionary"]
    assert int(getattr(missionary, "heal_level", 0) or 0) == 1
    # DE missionary heals at half monk rate ≈ 1 HP / 0.8s
    assert int(getattr(missionary, "heal_cd", 0) or 0) == int(0.8 * PRECISION)
    herbal = r.classes["herbal_medicine"]
    # effect_bonus_targets are folded into the effect bonus row
    effect = tuple(getattr(herbal, "effect", ()) or ())
    assert "keeptower" in effect
    assert "aoe_castle" in effect
    assert effect[:3] == ("bonus", "heal_level", "5")
