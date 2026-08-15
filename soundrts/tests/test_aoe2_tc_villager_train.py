# -*- coding: utf-8 -*-
"""Town Center must offer one villager train option (race-remapped)."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


def test_town_center_rules_train_only_peasant(aoe2_rules):
    raw = (aoe2_rules._dict.get("town_center") or {}).get("_rules_can_train") or {}
    assert list(raw.keys()) == ["peasant"]
    raw_th = (aoe2_rules._dict.get("townhall") or {}).get("_rules_can_train") or {}
    assert list(raw_th.keys()) == ["peasant"]


@pytest.mark.parametrize(
    "faction,expected",
    [
        ("britons", "peasant"),
        ("franks", "frank_villager"),
        ("byzantines", "peasant"),
        ("chinese", "chinese_villager"),
        ("mongols", "mongol_herdsman"),
        ("portuguese", "portuguese_villager"),
        ("aztecs", "aztec_villager"),
    ],
)
def test_effective_can_train_one_villager_per_civ(aoe2_rules, faction, expected):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_train
    from soundrts.worldplayerbase.base import Player

    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    global_rules._makers_cache = {}
    try:
        player = SimpleNamespace(
            faction=faction, upgrades=[], _can_train_overrides_by_type=None
        )
        player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)
        tc_cls = aoe2_rules.unit_class("town_center")
        unit = SimpleNamespace(type=tc_cls, type_name="town_center", player=player, place=None)
        trained = effective_can_train(unit)
        names = list(trained.keys()) if isinstance(trained, dict) else list(trained)
        assert names == [expected], (faction, names)
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c
        global_rules._makers_cache = {}


def test_chinese_villager_has_makers_via_peasant(aoe2_rules):
    makers = aoe2_rules.get_makers("chinese_villager")
    assert "town_center" in makers or "townhall" in makers
    makers_m = aoe2_rules.get_makers("mongol_herdsman")
    assert "town_center" in makers_m or "townhall" in makers_m
    makers_a = aoe2_rules.get_makers("aztec_villager")
    assert "town_center" in makers_a or "townhall" in makers_a
    makers_f = aoe2_rules.get_makers("frank_villager")
    assert "town_center" in makers_f or "townhall" in makers_f
