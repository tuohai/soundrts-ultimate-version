"""Menace appears on the attributes screen for combat units."""
from __future__ import annotations

import os
import sys
import types

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.argv = [sys.argv[0]]

from soundrts import msgparts as mp
from soundrts.attributes.basic_attributes import BasicAttributes
from soundrts.attributes.vs_handler import VsHandler
from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION
from soundrts.lib.resource import res


class _FakeMain:
    def __init__(self):
        self.vs_handler = VsHandler(self)

    def _add_bonus_attribute(self, attrs, u, *args, **kwargs):
        return None


def test_menace_on_attributes_list_for_footman_class():
    res.load_rules_and_ai()
    foot = rules.unit_class("footman")
    assert foot is not None

    u = types.SimpleNamespace(model=foot)
    attrs = []
    BasicAttributes(main_interface=_FakeMain()).add_basic_combat_attributes(u, attrs)
    menace_rows = [a for a in attrs if a[1] == mp.MENACE]
    assert menace_rows, "expected threat row for footman"
    assert menace_rows[0][2]


def test_effective_menace_reads_live_property():
    class _Live:
        menace = 3500
        menace_mult = PRECISION
        menace_vs = {}
        menace_mult_vs = {}

    assert BasicAttributes._effective_menace(_Live()) == 3500


def test_menace_shows_both_value_and_weight():
    res.load_rules_and_ai()
    foot = rules.unit_class("footman")
    u = types.SimpleNamespace(model=foot)
    attrs = []
    BasicAttributes(main_interface=_FakeMain()).add_basic_combat_attributes(u, attrs)
    assert any(a[1] == mp.MENACE for a in attrs)
    assert any(a[1] == mp.MENACE_MULT for a in attrs)


def test_menace_vs_row_when_configured():
    res.load_rules_and_ai()
    foot = rules.unit_class("footman")

    class _Model:
        mdg = 0
        rdg = 0
        mdf = 0
        rdf = 0
        mdg_crit = 0
        rdg_crit = 0
        mdg_crit_rate = 0
        rdg_crit_rate = 0
        mdg_piercing = 0
        rdg_piercing = 0
        mdg_piercing_rate = 0
        rdg_piercing_rate = 0
        mdf_crit_rate = 0
        rdf_crit_rate = 0
        menace = 2000
        menace_mult = PRECISION
        menace_vs = {"knight": 3 * PRECISION}
        menace_mult_vs = {}

    # Prefer absolute menace from __dict__ path via instance
    u = types.SimpleNamespace(model=_Model())
    attrs = []
    BasicAttributes(main_interface=_FakeMain()).add_basic_combat_attributes(u, attrs)
    assert any(a[1] == mp.MENACE_VS for a in attrs)
