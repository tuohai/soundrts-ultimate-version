# -*- coding: utf-8 -*-
"""Repeated ``*_vs`` lines must merge; one line may hold many pairs."""
from __future__ import annotations

from soundrts.definitions import Rules, _get_base_classes
from soundrts.lib.nofloat import PRECISION


_RULES = """
def building
class building

def siege_unit
class soldier

def ram_multi_line
class soldier
mdg 2
mdg_vs building 150
mdg_vs siege_unit 40

def ram_one_line
class soldier
mdg 2
mdg_vs building 150 siege_unit 40

def archer_mix
class soldier
rdg 5
rdg_vs spearman 3
rdg_vs archer_unit 4
rdg_vs cavalry_archer 2
"""


def test_mdg_vs_multi_line_and_one_line_merge():
    r = Rules()
    r.load(_RULES, base_classes=_get_base_classes())
    for name in ("ram_multi_line", "ram_one_line"):
        vs = r.unit_class(name).mdg_vs
        assert vs["building"] == 150 * PRECISION, name
        assert vs["siege_unit"] == 40 * PRECISION, name


def test_rdg_vs_three_lines_merge():
    r = Rules()
    r.load(_RULES, base_classes=_get_base_classes())
    vs = r.unit_class("archer_mix").rdg_vs
    assert vs["spearman"] == 3 * PRECISION
    assert vs["archer_unit"] == 4 * PRECISION
    assert vs["cavalry_archer"] == 2 * PRECISION


def test_aoe2_battering_ram_keeps_building_and_siege():
    from pathlib import Path

    mod = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    if not mod.is_file():
        import pytest

        pytest.skip("aoe2 mod not present")
    base = Path(__file__).resolve().parents[2] / "res" / "rules.txt"
    r = Rules()
    r.load(base.read_text(encoding="utf-8"), mod.read_text(encoding="utf-8"))
    vs = r.unit_class("battering_ram").mdg_vs
    assert vs.get("building") == 150 * PRECISION
    assert vs.get("siege_unit") == 40 * PRECISION


def _isa(uc):
    names = set(getattr(uc, "expanded_is_a", ()) or ())
    names.update(getattr(uc, "is_a", ()) or ())
    return names


def test_aoe2_buildings_inherit_building_for_vs_bonus():
    """Rams/masonry look up ``building`` on expanded_is_a, not Python class name."""
    from pathlib import Path

    from soundrts.combat.damage_calculation import _resolve_vs

    mod = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    if not mod.is_file():
        import pytest

        pytest.skip("aoe2 mod not present")
    base = Path(__file__).resolve().parents[2] / "res" / "rules.txt"
    r = Rules()
    r.load(base.read_text(encoding="utf-8"), mod.read_text(encoding="utf-8"))
    for name in (
        "house",
        "town_center",
        "workshop",
        "aoe_castle",
        "wall",
        "fortified_wall",
        "scouttower",
        "guardtower",
        "chinese_town_center",
        "briton_castle",
        "farm",
        "monastery",
    ):
        uc = r.unit_class(name)
        assert uc is not None, name
        assert "building" in _isa(uc), name
    peasant = r.unit_class("peasant")
    assert "building" not in _isa(peasant)
    ram = r.unit_class("battering_ram")
    house = r.unit_class("house")
    assert _resolve_vs(ram.mdg_vs, house.type_name, house.expanded_is_a) == 150 * PRECISION
