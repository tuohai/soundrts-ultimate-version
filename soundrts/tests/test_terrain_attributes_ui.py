"""Terrain combat modifiers appear on the attributes screen."""
from __future__ import annotations

import os
import sys
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.argv = [sys.argv[0]]

from soundrts import msgparts as mp
from soundrts.attributes.combat_attributes import CombatAttributes


class _FakeMain:
    pass


def _model(**kwargs):
    defaults = {
        "mdg_cover_on_terrain": (),
        "rdg_cover_on_terrain": (),
        "mdg_dodge_on_terrain": (),
        "rdg_dodge_on_terrain": (),
        "mdg_on_terrain": (),
        "rdg_on_terrain": (),
        "mdg_cd_on_terrain": (),
        "rdg_cd_on_terrain": (),
        "charge_mdg_terrain": (),
        "charge_rdg_terrain": (),
        "charge_mdg_cd_on_terrain": (),
        "charge_rdg_cd_on_terrain": (),
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


def test_combat_terrain_attrs_on_attributes_screen():
    u = types.SimpleNamespace(
        model=_model(
            mdg_on_terrain=("marsh", "-.33"),
            rdg_on_terrain=("marsh", ".5"),
            mdg_cd_on_terrain=("marsh", ".33"),
            rdg_cd_on_terrain=("ford", ".2"),
            charge_mdg_terrain=("marsh", ".25"),
            charge_rdg_terrain=("plain", ".1"),
            charge_mdg_cd_on_terrain=("marsh", ".2"),
            charge_rdg_cd_on_terrain=("forest", ".15"),
        )
    )
    attrs = []
    CombatAttributes(_FakeMain()).add_terrain_modifier_attributes(u, attrs)
    keys = [a[1] for a in attrs]
    assert keys == [
        mp.MDG_ON_TERRAIN,
        mp.RDG_ON_TERRAIN,
        mp.MDG_CD_ON_TERRAIN,
        mp.RDG_CD_ON_TERRAIN,
        mp.CHARGE_MDG_TERRAIN,
        mp.CHARGE_RDG_TERRAIN,
        mp.CHARGE_MDG_CD_ON_TERRAIN,
        mp.CHARGE_RDG_CD_ON_TERRAIN,
    ]
    # -.33 → -33%
    value = attrs[0][2]
    assert "%" in value
    assert any(isinstance(x, str) and "-33" in x for x in value)


def test_cover_list_does_not_block_combat_terrain_attrs():
    """cover/dodge are string lists; must not crash before combat terrain rows."""
    u = types.SimpleNamespace(
        model=_model(
            mdg_cover_on_terrain=("marsh", "60"),
            mdg_on_terrain=("marsh", "-.33"),
            charge_mdg_terrain=("marsh", ".2"),
        )
    )
    attrs = []
    CombatAttributes(_FakeMain()).add_terrain_modifier_attributes(u, attrs)
    keys = [a[1] for a in attrs]
    assert mp.MDG_COVER_ON_TERRAIN in keys
    assert mp.MDG_ON_TERRAIN in keys
    assert mp.CHARGE_MDG_TERRAIN in keys
