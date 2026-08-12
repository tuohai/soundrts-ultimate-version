"""诸葛弩式连发攻击（damage_seq）解析与调度测试。"""
from __future__ import annotations

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.lib.nofloat import PRECISION

ROOT = Path(__file__).resolve().parents[2]


def _parse_unit_rules(text: str, name: str = "test_unit"):
    rules = Rules()
    rules.read(
        f"def {name}\nclass soldier\n{text}\n"
    )
    return rules._dict[name]


def test_damage_seq_auto_split_equal_shots():
    unit = _parse_unit_rules(
        "rdg 6\n"
        "damage_seq rdg 3 (interval 0.25)\n"
    )
    assert unit["rdg_seq_times"] == 3
    assert unit["rdg_seq_damages"] == [2000, 2000, 2000]
    assert unit["rdg_seq_interval"] == 0.25
    assert unit.get("rdg_seq_secondary", 0) == 0


def test_damage_seq_auto_split_fractional_base_damage():
    unit = _parse_unit_rules(
        "rdg 7.5\n"
        "damage_seq rdg 3 (interval 0.2)\n"
    )
    assert unit["rdg_seq_times"] == 3
    assert sum(unit["rdg_seq_damages"]) == int(7.5 * PRECISION)
    assert unit["rdg_seq_damages"] == [2500, 2500, 2500]


def test_damage_seq_explicit_damage_values():
    unit = _parse_unit_rules(
        "mdg 12\n"
        "damage_seq mdg 3 (damage 6 3 3) (interval 0.2)\n"
    )
    assert unit["mdg_seq_times"] == 3
    assert unit["mdg_seq_damages"] == [6000, 3000, 3000]
    assert unit["mdg_seq_interval"] == 0.2


def test_damage_seq_secondary_aoe2_chu_ko_nu():
    """DE 诸葛弩：首发 live rdg；后续固定 3 pierce + 0 melee（不要求 sum==base）。"""
    unit = _parse_unit_rules(
        "rdg 8\n"
        "damage_seq rdg 3 (secondary 3 0) (interval 0.23)\n"
    )
    assert unit["rdg_seq_times"] == 3
    assert unit["rdg_seq_damages"] == []
    assert unit["rdg_seq_interval"] == 0.23
    assert unit["rdg_seq_secondary"] == 1
    assert unit["rdg_seq_secondary_rdg"] == 3 * PRECISION
    assert unit["rdg_seq_secondary_mdg"] == 0


def test_damage_seq_secondary_elite_five_arrows():
    unit = _parse_unit_rules(
        "rdg 10\n"
        "damage_seq rdg 5 (secondary 3 0) (interval 0.23)\n"
    )
    assert unit["rdg_seq_times"] == 5
    assert unit["rdg_seq_secondary"] == 1
    assert unit["rdg_seq_secondary_rdg"] == 3 * PRECISION


def test_aoe2_chu_ko_nu_loaded_from_mod_rules():
    rules = Rules()
    base = (ROOT / "res/rules.txt").read_text(encoding="utf-8")
    mod = (ROOT / "mods/aoe2/rules.txt").read_text(encoding="utf-8")
    rules.load(base + "\n" + mod)
    ckn = rules.unit_class("chu_ko_nu")
    elite = rules.unit_class("elite_chu_ko_nu")
    assert ckn is not None and elite is not None
    assert ckn.rdg_seq_times == 3
    assert ckn.rdg_seq_secondary == 1
    assert ckn.rdg_seq_secondary_rdg == 3 * PRECISION
    assert ckn.rdg_seq_secondary_mdg == 0
    assert ckn.rdg_seq_interval == 0.23
    assert elite.rdg_seq_times == 5
    assert elite.rdg_seq_secondary == 1


def test_dual_damage_zero_melee_vs_negative_armor():
    """0 melee vs -3 mdf → +3；与 3 pierce vs 0 rdf 合计 6（冲车）。"""
    from soundrts.combat.damage_calculation import DamageCalculationMixin

    class T(DamageCalculationMixin):
        def _get_total_ranged_defense_vs(self, attacker):
            return 0

        def _get_total_melee_defense_vs(self, attacker):
            return -3 * PRECISION

    class A:
        minimal_damage = 0
        forced_damage = 0
        rdg_range = 4 * PRECISION

    actual = T()._calculate_actual_damage(
        3 * PRECISION, A(), is_melee=False, extra_melee_damage=0
    )
    assert actual == 6 * PRECISION


def test_repeating_crossbowman_loaded_from_rules():
    rules = Rules()
    rules.load((ROOT / "res/rules.txt").read_text(encoding="utf-8"))
    unit_cls = rules.unit_class("repeating_crossbowman")
    assert unit_cls is not None
    assert unit_cls.rdg_seq_times == 3
    assert sum(unit_cls.rdg_seq_damages) == unit_cls.rdg
    assert unit_cls.rdg_seq_interval == 0.25


def test_units_without_damage_seq_do_not_inherit_burst_from_soldier_base():
    rules = Rules()
    rules.load((ROOT / "res/rules.txt").read_text(encoding="utf-8"))

    for unit_name in ("archer", "darkarcher", "skeleton"):
        unit_cls = rules.unit_class(unit_name)
        assert unit_cls.rdg_seq_times == 1
        assert unit_cls.rdg_seq_damages == []
        assert unit_cls.rdg_seq_interval == 0


def test_schedule_ballistic_hit_uses_configured_interval():
    src = (ROOT / "soundrts/combat/damage_effects.py").read_text(encoding="utf-8")
    assert "interval = self.rdg_seq_interval" in src
    assert "interval = 0.4" not in src
    assert "launch_notify" in src
    assert "rdg_seq_secondary" in src
    assert "extra_melee_damage" in src


def test_volley_cooldown_includes_sequence_span():
    src = (ROOT / "soundrts/combat/attack_action.py").read_text(encoding="utf-8")
    assert "_get_volley_attack_cooldown" in src
    assert "(times - 1) * interval" in src


def test_launch_sound_scheduled_per_shot_not_in_attack_action():
    attack_src = (ROOT / "soundrts/combat/attack_action.py").read_text(encoding="utf-8")
    assert 'notify(f"launch_rdg' not in attack_src
    assert 'notify(f"launch_mdg' not in attack_src
