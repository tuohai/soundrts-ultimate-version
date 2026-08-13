# -*- coding: utf-8 -*-
"""Tests for full AoE2 unique-tech effects (no approximations)."""
from soundrts.worldupgrade.effect_bonus_parse import split_effect_bonus_args
from soundrts.worldupgrade.attribute_effects import AttributeEffectsMixin


class _U:
    def __init__(self):
        self.type_name = "scouttower"
        self.expanded_is_a = ["building", "scouttower"]
        self.rdg_seq_times = 1
        self.rdg_seq_secondary = 0
        self.rdg_seq_secondary_live = 0
        self.rdg_seq_interval = 0
        self.passenger_attack_types = ["archer_unit", "peasant"]
        self.kill_resource_vs = None
        self.gather_byproduct = None
        self.unpack_time = 11.0
        self.mdg_vs = {}


def test_split_yasama_seq_stats():
    bonus, units = split_effect_bonus_args(
        ["rdg_seq_times", "3", "scouttower", "guardtower"]
    )
    # without effect_bonus_targets stored inline, trailing types peel off
    assert bonus[:2] == ["rdg_seq_times", "3"]


def test_yasama_sets_seq_times_not_add():
    u = _U()
    AttributeEffectsMixin.effect_bonus(u, 0, "rdg_seq_times", 3)
    assert u.rdg_seq_times == 3
    AttributeEffectsMixin.effect_bonus(u, 0, "rdg_seq_secondary", 1)
    AttributeEffectsMixin.effect_bonus(u, 0, "rdg_seq_secondary_live", 1)
    assert u.rdg_seq_secondary == 1
    assert u.rdg_seq_secondary_live == 1


def test_crenellations_appends_passenger_attack_types():
    u = _U()
    AttributeEffectsMixin.effect_bonus(u, 0, "passenger_attack_types", "infantry")
    assert "infantry" in u.passenger_attack_types
    assert "archer_unit" in u.passenger_attack_types


def test_chieftains_kill_resource_vs_and_camel():
    u = _U()
    u.type_name = "militia"
    u.expanded_is_a = ["infantry"]
    AttributeEffectsMixin.effect_bonus(
        u, 0, "kill_resource_vs", "peasant", "resource1", 5
    )
    AttributeEffectsMixin.effect_bonus(u, 0, "mdg_vs", "camel_rider", 4)
    assert u.kill_resource_vs["peasant"]["resource1"] == 5
    assert u.mdg_vs["camel_rider"] == 4
    # gold alias normalizes to resource1
    AttributeEffectsMixin.effect_bonus(u, 0, "kill_resource_vs", "monk", "gold", 5)
    assert u.kill_resource_vs["monk"]["resource1"] == 5


def test_paper_money_gather_byproduct():
    u = _U()
    u.type_name = "peasant"
    AttributeEffectsMixin.effect_bonus(u, 0, "gather_byproduct", "wood", 0.014)
    assert abs(u.gather_byproduct["wood"] - 0.014) < 1e-9


def test_kataparuto_unpack_time_percent():
    u = _U()
    AttributeEffectsMixin.effect_bonus(u, 0, "unpack_time", "-75%")
    assert abs(u.unpack_time - 11.0 * 0.25) < 1e-6


def test_split_kill_resource_and_byproduct():
    b, t = split_effect_bonus_args(
        [
            "kill_resource_vs",
            "peasant",
            "resource1",
            "5",
            "gather_byproduct",
            "wood",
            "0.014",
        ]
    )
    assert b == [
        "kill_resource_vs",
        "peasant",
        "resource1",
        "5",
        "gather_byproduct",
        "wood",
        "0.014",
    ]
    assert t == []


def test_rules_unique_techs_no_approximations():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt").read_text(
        encoding="utf-8"
    )
    # Yasama must be multi-arrow, not +2 attack
    assert "def yasama" in text
    assert "rdg_seq_times 3" in text
    assert "rdg_seq_secondary_live 1" in text
    # Paper Money byproduct, not wood gather speed hack
    assert "gather_byproduct wood 0.014" in text
    assert "gather_time_wood -10%" not in text.split("def paper_money")[1].split("def ")[0]
    # Circumnavigation map reveal
    assert "reveal_map 1" in text.split("def circumnavigation")[1].split("def ")[0]
    # Arquebus = ballistics + DE absolute projectile speed (+0.5 / +0.2)
    ab = text.split("def arquebus")[1].split("def ")[0]
    assert "projectile_lead 1" in ab
    assert "rdg_cover 100" not in ab
    assert "rdg_projectile_speed 0.5" in ab
    assert "mdg_projectile_speed 0.2" in ab
    assert "rdg_projectile_speed 50%" not in ab
    # Chieftains camel + kill resource (resource1 = gold in aoe2)
    block = text.split("def chieftains")[1].split("def ")[0]
    assert "camel_rider 4" in block
    assert "kill_resource_vs peasant resource1 5" in block
    assert "kill_gold_vs" not in block
    # Crenellations infantry fire
    assert "passenger_attack_types infantry" in text.split("def crenellations")[1].split("def ")[0]
    # Kataparuto unpack
    assert "unpack_time -75%" in text.split("def kataparuto")[1].split("def ")[0]


def test_unique_tech_can_use_tech_wiring():
    from pathlib import Path
    from soundrts.definitions import Rules

    r = Rules()
    base = Path(__file__).resolve().parents[2] / "res" / "rules.txt"
    mod = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    r.load(base.read_text(encoding="utf-8"), mod.read_text(encoding="utf-8"))

    def techs(u):
        return list(r.get(u, "can_use_tech") or [])

    for u in ("scouttower", "guardtower", "keeptower"):
        assert "yasama" in techs(u), u
        assert "crenellations" in techs(u), u
    assert "kataparuto" in techs("trebuchet")
    assert "chieftains" in techs("militia")
    assert "paper_money" in techs("peasant")
    for u in (
        "organ_gun",
        "elite_organ_gun",
        "hand_cannoneer",
        "bombard_cannon",
        "cannontower",
        "cannon_galleon",
        "elite_cannon_galleon",
    ):
        assert "arquebus" in techs(u), u
    assert getattr(r.unit_class("circumnavigation"), "reveal_map", 0) == 1
