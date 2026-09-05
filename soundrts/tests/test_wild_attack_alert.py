"""Victim alert_<attacker> / alert_<style ancestor> (AoE2 DE wildlife warning)."""
from types import SimpleNamespace

from soundrts.clientgameentity import combat as combat_module
from soundrts.clientgameentity.combat import attacked_alert_style


class _FakeStyle:
    def __init__(self, entries):
        self.entries = entries

    def get(self, obj, attr, warn_if_not_found=True):
        return self.entries.get((obj, attr), [])


def _patch_style(monkeypatch, entries):
    monkeypatch.setattr(combat_module, "style", _FakeStyle(entries))
    monkeypatch.setattr(
        combat_module,
        "rules",
        SimpleNamespace(
            unit_class=lambda name: SimpleNamespace(
                is_a_building=name in ("town_center", "building")
            )
        ),
    )


def test_boar_matches_peasant_alert_animal(monkeypatch):
    _patch_style(
        monkeypatch,
        {
            ("boar", "is_a"): ["animal"],
            ("animal", "is_a"): ["walking_unit"],
            ("peasant", "alert_animal"): ["attack_warning_wild_animal"],
        },
    )
    assert attacked_alert_style("peasant", "boar") == "alert_animal"
    assert attacked_alert_style("peasant", "militia") == "alert"


def test_alert_boar_wins_over_alert_animal(monkeypatch):
    _patch_style(
        monkeypatch,
        {
            ("boar", "is_a"): ["animal"],
            ("animal", "is_a"): ["walking_unit"],
            ("peasant", "alert_animal"): ["attack_warning_wild_animal"],
            ("peasant", "alert_boar"): ["boar_specific"],
        },
    )
    assert attacked_alert_style("peasant", "boar") == "alert_boar"


def test_building_keeps_base_alert(monkeypatch):
    _patch_style(
        monkeypatch,
        {
            ("boar", "is_a"): ["animal"],
            ("town_center", "alert_animal"): ["attack_warning_wild_animal"],
        },
    )
    assert attacked_alert_style("town_center", "boar") == "alert"


def test_aoe2_style_animal_line_and_peasant():
    from pathlib import Path

    style = (
        Path(__file__).resolve().parents[2]
        / "mods"
        / "aoe2"
        / "ui"
        / "style.txt"
    ).read_text(encoding="utf-8")
    rules = (
        Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    ).read_text(encoding="utf-8")
    assert "def animal" in style
    assert "alert_animal attack_warning_wild_animal" in style
    assert "wild_attack_alert" not in rules
    boar = style.split("def boar", 1)[1].split("\ndef ", 1)[0]
    assert "is_a animal" in boar
    deer = style.split("def deer", 1)[1].split("\ndef ", 1)[0]
    assert "is_a animal" in deer
