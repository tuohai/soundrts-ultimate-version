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
