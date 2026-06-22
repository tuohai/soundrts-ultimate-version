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


def test_launch_sound_scheduled_per_shot_not_in_attack_action():
    attack_src = (ROOT / "soundrts/combat/attack_action.py").read_text(encoding="utf-8")
    assert 'notify(f"launch_rdg' not in attack_src
    assert 'notify(f"launch_mdg' not in attack_src
