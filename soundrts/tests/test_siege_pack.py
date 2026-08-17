# -*- coding: utf-8 -*-
"""AoE2 trebuchet pack/unpack (siege mode) — rules-driven + completeness progress."""
from __future__ import annotations

import types

import pytest

from soundrts.world_siege_pack import (
    MODE_PACKED,
    MODE_UNPACKED,
    cancel_siege_transition,
    ensure_packed,
    ensure_unpacked,
    init_siege_pack,
    is_packable,
    siege_mode,
    tick_siege_pack,
    unpack_duration_ms,
)


def _unit(
    world_time=0,
    unpack_time=11000,
    pack_time=0,
    packable=1,
    packed_mdf=2000,
    packed_rdf=8000,
    mdf=1000,
    rdf=150000,
):
    world = types.SimpleNamespace(time=world_time)
    player = types.SimpleNamespace(world=world)
    u = types.SimpleNamespace(
        unpack_time=unpack_time,
        pack_time=pack_time,
        packable=packable,
        spawn_packed=1,
        packed_mdf=packed_mdf,
        packed_rdf=packed_rdf,
        mdf=mdf,
        rdf=rdf,
        player=player,
        world=world,
        rdg_prep_end_time=0,
        mdg_prep_end_time=0,
        notifies=[],
    )
    u.stop = lambda: None
    u.notify = lambda ev: u.notifies.append(ev)
    return u


def test_unpack_time_precision_from_rules():
    from pathlib import Path
    from soundrts.definitions import Rules

    root = Path(__file__).resolve().parents[2]
    base = root / "res" / "rules.txt"
    mod = root / "mods" / "aoe2" / "rules.txt"
    if not base.is_file() or not mod.is_file():
        pytest.skip("aoe2 rules tree not present")
    r = Rules()
    r.load(base.read_text(encoding="utf-8"), mod.read_text(encoding="utf-8"))
    cls = r.unit_class("trebuchet")
    assert getattr(cls, "packable") == 1
    assert unpack_duration_ms(cls) == 11000
    assert getattr(cls, "packed_mdf") == 2000
    assert getattr(cls, "packed_rdf") == 8000


def test_spawn_packed_and_armor():
    u = _unit()
    init_siege_pack(u)
    assert is_packable(u)
    assert siege_mode(u) == MODE_PACKED
    assert u.mdf == 2000
    assert u.rdf == 8000


def test_cannot_attack_until_unpacked():
    u = _unit()
    init_siege_pack(u)
    assert ensure_unpacked(u) is False
    assert siege_mode(u) == "unpacking"
    assert ensure_unpacked(u) is False
    u.world.time = 11000
    tick_siege_pack(u)
    assert siege_mode(u) == MODE_UNPACKED
    assert u.mdf == 1000
    assert u.rdf == 150000
    assert ensure_unpacked(u) is True


def test_cannot_move_until_packed():
    u = _unit()
    init_siege_pack(u)
    u.world.time = 0
    ensure_unpacked(u)
    u.world.time = 11000
    tick_siege_pack(u)
    assert siege_mode(u) == MODE_UNPACKED
    assert ensure_packed(u) is False
    assert siege_mode(u) == "packing"
    u.world.time = 22000
    tick_siege_pack(u)
    assert siege_mode(u) == MODE_PACKED
    assert ensure_packed(u) is True


def test_cancel_unpack_to_move_instantly():
    u = _unit()
    init_siege_pack(u)
    ensure_unpacked(u)
    assert siege_mode(u) == "unpacking"
    assert ensure_packed(u) is True  # cancel unpack → packed
    assert siege_mode(u) == MODE_PACKED


def test_stop_cancels_packing():
    u = _unit()
    init_siege_pack(u)
    ensure_unpacked(u)
    u.world.time = 11000
    tick_siege_pack(u)
    ensure_packed(u)
    assert siege_mode(u) == "packing"
    cancel_siege_transition(u)
    assert siege_mode(u) == MODE_UNPACKED


def test_kataparuto_shortens_unpack_ms():
    from soundrts.worldupgrade.attribute_effects import AttributeEffectsMixin

    u = _unit(unpack_time=11000)
    AttributeEffectsMixin.effect_bonus(u, 0, "unpack_time", "-75%")
    assert abs(u.unpack_time - 2750) < 1e-6
    assert unpack_duration_ms(u) == 2750


def test_completeness_progress_during_unpack():
    u = _unit()
    init_siege_pack(u)
    u.notifies.clear()
    ensure_unpacked(u)
    assert "completeness,0" in u.notifies
    assert "siege_unpacking" in u.notifies
    u.notifies.clear()
    u.world.time = 5500  # 50%
    tick_siege_pack(u)
    assert "completeness,5" in u.notifies
    u.notifies.clear()
    u.world.time = 11000
    tick_siege_pack(u)
    assert "completeness,10" in u.notifies
    assert siege_mode(u) == MODE_UNPACKED


def test_completeness_progress_during_pack():
    u = _unit(pack_time=8000, unpack_time=11000)
    init_siege_pack(u)
    ensure_unpacked(u)
    u.world.time = 11000
    tick_siege_pack(u)
    u.notifies.clear()
    ensure_packed(u)
    assert "completeness,0" in u.notifies
    u.notifies.clear()
    u.world.time = 11000 + 4000  # 50% of pack_time 8000
    tick_siege_pack(u)
    assert "completeness,5" in u.notifies


def test_not_packable_without_time():
    u = _unit(unpack_time=0, pack_time=0, packable=1)
    assert not is_packable(u)


def test_not_packable_creature_defaults():
    """Villager-like defaults must reject without _raw_attr."""
    u = _unit(unpack_time=0, pack_time=0, packable=0)
    assert not is_packable(u)


def test_packable_list_unpack_time():
    u = _unit(unpack_time=[11000], pack_time=0, packable=1)
    assert is_packable(u)
