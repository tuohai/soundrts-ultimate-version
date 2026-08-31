"""AoE2 Aztec eagle scout must morph when Eagle Warrior is researched."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def _load_aoe2():
    from soundrts.definitions import Rules
    from soundrts.definitions import rules as global_rules

    r = Rules()
    r.load(
        (ROOT / "res" / "rules.txt").read_text(encoding="utf-8"),
        (ROOT / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    saved = global_rules._dict
    saved_c = getattr(global_rules, "classes", None)
    global_rules._dict = r._dict
    global_rules.classes = r.classes
    return r, saved, saved_c, global_rules


def test_aoe2_eagle_line_can_upgrade_to_chain():
    r, saved, saved_c, global_rules = _load_aoe2()
    try:
        scout = r.unit_class("eagle_scout")
        aztec = r.unit_class("aztec_eagle_scout")
        warrior = r.unit_class("eagle_warrior")
        assert "eagle_warrior" in (getattr(scout, "can_upgrade_to", ()) or ())
        assert "eagle_warrior" in (getattr(aztec, "can_upgrade_to", ()) or ())
        assert "elite_eagle_warrior" in (getattr(warrior, "can_upgrade_to", ()) or ())
        jaguar = r.unit_class("jaguar_warrior")
        assert "elite_jaguar_warrior" in (getattr(jaguar, "can_upgrade_to", ()) or ())
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c


def test_research_eagle_warrior_morphs_aztec_eagle_scout():
    from soundrts.world_build_rules import (
        apply_unit_line_upgrade,
        resolve_trainable_unit_type,
    )
    import soundrts.worldphase as worldphase

    r, saved, saved_c, global_rules = _load_aoe2()
    try:
        aztec_cls = r.unit_class("aztec_eagle_scout")
        unit = SimpleNamespace(
            type_name="aztec_eagle_scout",
            can_upgrade_to=getattr(aztec_cls, "can_upgrade_to", ()) or (),
        )
        player = SimpleNamespace(
            upgrades=["castle_age"],
            units=[unit],
            has_all=lambda reqs: True,
        )
        morphs = []

        def fake_morph(u, target_cls):
            morphs.append(
                (u.type_name, getattr(target_cls, "type_name", None) or target_cls.__name__)
            )
            u.type_name = "eagle_warrior"

        saved_morph = worldphase.Phase._instant_morph
        worldphase.Phase._instant_morph = staticmethod(fake_morph)
        try:
            apply_unit_line_upgrade(player, "eagle_warrior")
        finally:
            worldphase.Phase._instant_morph = saved_morph

        assert "eagle_warrior" in player.upgrades
        assert morphs == [("aztec_eagle_scout", "eagle_warrior")]
        assert (
            resolve_trainable_unit_type(player, "aztec_eagle_scout") == "eagle_warrior"
        )
    finally:
        global_rules._dict = saved
        if saved_c is not None:
            global_rules.classes = saved_c
