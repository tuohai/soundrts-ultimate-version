# -*- coding: utf-8 -*-
"""Villagers list generic buildings; race equivalent applies when building."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]

CIV_CASTLE = [
    ("britons", "briton_castle", "longbowman"),
    ("franks", "frank_castle", "throwing_axeman"),
    ("chinese", "chinese_castle", "chu_ko_nu"),
    ("mongols", "mongol_castle", "mangudai"),
    ("byzantines", "byzantine_castle", "cataphract"),
    ("japanese", "japanese_castle", "samurai"),
    ("teutons", "teuton_castle", "teutonic_knight"),
    ("vikings", "viking_castle", "berserk"),
    ("vietnamese", "vietnamese_castle", "rattan_archer"),
    ("portuguese", "portuguese_castle", "organ_gun"),
    ("celts", "celtic_castle", "woad_raider"),
    ("malians", "malian_castle", "gbeto"),
]


@pytest.fixture(scope="module")
def aoe2_rules():
    from soundrts.definitions import Rules

    base = (ROOT / "res" / "rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8")
    r = Rules()
    r.load(base, mod)
    return r


def test_peasant_rules_list_generic_castle(aoe2_rules):
    raw = aoe2_rules.class_rules_attr(aoe2_rules.classes["peasant"], "can_build", ())
    assert "aoe_castle" in raw
    assert "chinese_castle" not in raw


@pytest.mark.parametrize("faction,castle,uu", CIV_CASTLE)
def test_build_menu_stays_generic_then_resolves_shell(aoe2_rules, faction, castle, uu):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import (
        effective_can_build,
        effective_can_train,
        resolve_buildable_type,
    )
    from soundrts.worldplayerbase.base import Player

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes

    player = SimpleNamespace(
        faction=faction,
        upgrades=[],
        _can_train_overrides_by_type=None,
    )
    player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)

    worker_name = (aoe2_rules._dict.get(faction) or {}).get("peasant") or ["peasant"]
    if isinstance(worker_name, (list, tuple)):
        worker_name = worker_name[0]
    cls = aoe2_rules.unit_class(worker_name)
    unit = SimpleNamespace(player=player, type=cls, type_name=worker_name)
    builds = effective_can_build(unit)
    assert "aoe_castle" in builds, (faction, builds)
    assert castle not in builds or castle == "aoe_castle"
    assert resolve_buildable_type(player, "aoe_castle") == castle

    castle_cls = aoe2_rules.unit_class(castle)
    cunit = SimpleNamespace(
        player=player, type=castle_cls, type_name=castle, attached_addons=[]
    )
    assert uu in effective_can_train(cunit)
    assert "trebuchet" in effective_can_train(cunit)


def test_trebuchet_is_castle_not_workshop(aoe2_rules):
    """AoE2 DE: Trebuchet is trained at the Castle in Imperial Age."""
    workshop_train = aoe2_rules.class_rules_attr(
        aoe2_rules.unit_class("workshop"), "can_train", ()
    )
    assert "trebuchet" not in workshop_train
    assert "mangonel" in workshop_train
    castle_train = aoe2_rules.class_rules_attr(
        aoe2_rules.unit_class("aoe_castle"), "can_train", ()
    )
    assert "trebuchet" in castle_train
    makers = aoe2_rules.get_makers("trebuchet") or []
    assert "aoe_castle" in makers
    assert "workshop" not in makers
    assert "byzantine_workshop" not in makers
    assert aoe2_rules.get("trebuchet", "requirements") == ["imperial_age"]


def test_portuguese_resolve_buildable_uses_raw_race_shell(aoe2_rules):
    """AI equivalent may keep barracks; BuildOrder still places portuguese_barracks."""
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import resolve_buildable_type
    from soundrts.worldplayerbase.base import Player

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    player = SimpleNamespace(faction="portuguese", upgrades=[], _can_train_overrides_by_type=None)
    player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)
    assert player.equivalent("barracks") == "barracks"
    assert resolve_buildable_type(player, "barracks") == "portuguese_barracks"
    assert resolve_buildable_type(player, "aoe_castle") == "portuguese_castle"


def test_teuton_farm_not_on_build_menu(aoe2_rules):
    from soundrts.definitions import rules as global_rules
    from soundrts.world_build_rules import effective_can_build, resolve_buildable_type
    from soundrts.worldplayerbase.base import Player

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes
    player = SimpleNamespace(faction="teutons", upgrades=[], _can_train_overrides_by_type=None)
    player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)
    cls = aoe2_rules.unit_class("peasant")
    unit = SimpleNamespace(player=player, type=cls, type_name="peasant")
    builds = effective_can_build(unit)
    assert "farm" in builds
    assert "teuton_farm" not in builds
    assert resolve_buildable_type(player, "farm") == "teuton_farm"


_BUILDING_RACE_KEYS = (
    "barracks",
    "archery_range",
    "stables",
    "blacksmith",
    "university",
    "aoe_castle",
    "workshop",
    "shipyard",
    "monastery",
    "mill",
    "townhall",
    "farm",
)


def test_civ_building_shells_have_style_titles(aoe2_rules):
    """Built shells (malian_barracks, …) must inherit a spoken title."""
    from soundrts.definitions import Style

    st = Style()
    st.load(
        (ROOT / "res" / "ui" / "style.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "ui" / "style.txt").read_text(encoding="utf-8"),
    )
    missing = []
    for faction, _castle, uu in CIV_CASTLE:
        race = aoe2_rules._dict.get(faction) or {}
        names = [uu]
        for key in _BUILDING_RACE_KEYS:
            raw = race.get(key)
            if not raw:
                continue
            names.append(raw[0] if isinstance(raw, (list, tuple)) else raw)
        for name in names:
            title = st.get(name, "title", warn_if_not_found=False)
            if not title:
                missing.append((faction, name))
    assert not missing, "style.txt missing title/is_a for %s" % missing
