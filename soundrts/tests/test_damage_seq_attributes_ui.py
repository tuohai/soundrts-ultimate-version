"""damage_seq appears on the attributes screen."""
from __future__ import annotations

import os
import sys
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.argv = [sys.argv[0]]

from soundrts import msgparts as mp
from soundrts.attributes.combat_attributes import CombatAttributes
from soundrts.lib.nofloat import PRECISION


def test_explicit_damage_seq_on_attributes_screen():
    model = types.SimpleNamespace(
        mdg_seq_times=1,
        mdg_seq_damages=[],
        mdg_seq_interval=0,
        mdg_seq_secondary=0,
        mdg_seq_secondary_rdg=0,
        mdg_seq_secondary_mdg=0,
        rdg_seq_times=3,
        rdg_seq_damages=[6000, 3000, 3000],
        rdg_seq_interval=0.2,
        rdg_seq_secondary=0,
        rdg_seq_secondary_rdg=0,
        rdg_seq_secondary_mdg=0,
    )
    attrs = []
    CombatAttributes.append_damage_seq_attrs(attrs, model)
    assert len(attrs) == 1
    key, name, value = attrs[0]
    assert name == mp.DAMAGE_SEQ_RDG
    assert value[0] == "VS_ITEMS"
    items = value[1]
    assert any(mp.DAMAGE_SEQ_SHOTS[0] in item or mp.DAMAGE_SEQ_SHOTS == item[:1] for item in items)
    # 3 shots + shots count + interval
    assert len(items) == 5


def test_secondary_damage_seq_on_attributes_screen():
    model = types.SimpleNamespace(
        mdg_seq_times=1,
        mdg_seq_damages=[],
        mdg_seq_interval=0,
        mdg_seq_secondary=0,
        mdg_seq_secondary_rdg=0,
        mdg_seq_secondary_mdg=0,
        rdg_seq_times=3,
        rdg_seq_damages=[],
        rdg_seq_interval=0.23,
        rdg_seq_secondary=1,
        rdg_seq_secondary_rdg=3 * PRECISION,
        rdg_seq_secondary_mdg=0,
    )
    attrs = []
    CombatAttributes.append_damage_seq_attrs(attrs, model)
    assert len(attrs) == 1
    _, name, value = attrs[0]
    assert name == mp.DAMAGE_SEQ_RDG
    items = value[1]
    flat = [str(p) for item in items for p in item]
    assert str(mp.DAMAGE_SEQ_PRIMARY[0]) in flat or mp.DAMAGE_SEQ_PRIMARY[0] in [
        p for item in items for p in item
    ]
    assert any(mp.DAMAGE_SEQ_SECONDARY[0] in item for item in items)
    assert any(mp.DAMAGE_SEQ_INTERVAL[0] in item for item in items)


def test_no_damage_seq_when_default_single_shot():
    model = types.SimpleNamespace(
        mdg_seq_times=1,
        mdg_seq_damages=[],
        mdg_seq_interval=0,
        mdg_seq_secondary=0,
        mdg_seq_secondary_rdg=0,
        mdg_seq_secondary_mdg=0,
        rdg_seq_times=1,
        rdg_seq_damages=[],
        rdg_seq_interval=0,
        rdg_seq_secondary=0,
        rdg_seq_secondary_rdg=0,
        rdg_seq_secondary_mdg=0,
    )
    attrs = []
    CombatAttributes.append_damage_seq_attrs(attrs, model)
    assert attrs == []
