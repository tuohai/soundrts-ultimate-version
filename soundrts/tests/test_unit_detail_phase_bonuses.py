# -*- coding: utf-8 -*-
"""Type-detail preview must stack player phase/civ bonuses (not rules base only)."""
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


def test_malian_militia_detail_includes_feudal_rdf(aoe2_rules, monkeypatch):
    from soundrts.attributes.unit_detail import UnitDetail
    from soundrts.definitions import rules as global_rules
    from soundrts.lib.nofloat import PRECISION

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes

    militia_cls = aoe2_rules.unit_class("militia")
    base_rdf = int(getattr(militia_cls, "rdf", 0) or 0)

    player = SimpleNamespace(
        faction="malians",
        upgrades=["feudal_age"],
        _phase_bonus_pool=[
            (["rdf", 1 * PRECISION], ["militia", "spearman"]),
        ],
    )
    source = SimpleNamespace(player=player, type_name="malian_barracks")
    captured = {}

    def populate_unit_attributes(u, attrs):
        captured["unit"] = u
        attrs.append(("f", ["rdf"], [str(getattr(u, "rdf", None))]))

    parent = SimpleNamespace(
        _attributes_screen_unit=source,
        _attributes_screen_attrs=[],
        _current_attribute_index=0,
        _current_sub_item_index=0,
        _current_attribute_sub_items=[],
        _saved_attributes_state=None,
        _in_detail_attributes_screen=False,
        key_bindings=SimpleNamespace(
            _setup_attributes_screen_bindings=lambda: None
        ),
        main_display=SimpleNamespace(
            display_interface=SimpleNamespace(
                populate_unit_attributes=populate_unit_attributes,
                populate_tech_attributes=lambda *_a, **_k: None,
            ),
            _display_current_attribute=lambda: None,
        ),
    )

    monkeypatch.setattr(
        "soundrts.lib.voice.voice.info", lambda *_a, **_k: None, raising=False
    )
    UnitDetail(parent)._show_unit_detail("militia")

    unit = captured["unit"]
    assert int(unit.rdf) == base_rdf + PRECISION


def test_briton_archer_detail_includes_castle_range(aoe2_rules, monkeypatch):
    from soundrts.attributes.unit_detail import UnitDetail
    from soundrts.definitions import rules as global_rules
    from soundrts.lib.nofloat import PRECISION

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes

    archer_cls = aoe2_rules.unit_class("aoe_archer")
    base_range = int(getattr(archer_cls, "rdg_range", 0) or 0)

    player = SimpleNamespace(
        faction="britons",
        upgrades=["castle_age"],
        _phase_bonus_pool=[
            (
                ["rdg_range", 1 * PRECISION],
                [
                    "aoe_archer",
                    "crossbowman",
                    "arbalester",
                    "longbowman",
                    "elite_longbowman",
                ],
            ),
        ],
    )
    source = SimpleNamespace(player=player, type_name="briton_archery")
    captured = {}

    def populate_unit_attributes(u, attrs):
        captured["unit"] = u

    parent = SimpleNamespace(
        _attributes_screen_unit=source,
        _attributes_screen_attrs=[],
        _current_attribute_index=0,
        _current_sub_item_index=0,
        _current_attribute_sub_items=[],
        _saved_attributes_state=None,
        _in_detail_attributes_screen=False,
        key_bindings=SimpleNamespace(
            _setup_attributes_screen_bindings=lambda: None
        ),
        main_display=SimpleNamespace(
            display_interface=SimpleNamespace(
                populate_unit_attributes=populate_unit_attributes,
                populate_tech_attributes=lambda *_a, **_k: None,
            ),
            _display_current_attribute=lambda: None,
        ),
    )

    monkeypatch.setattr(
        "soundrts.lib.voice.voice.info", lambda *_a, **_k: None, raising=False
    )
    UnitDetail(parent)._show_unit_detail("aoe_archer")

    assert int(captured["unit"].rdg_range) == base_range + PRECISION


def test_detail_without_pool_keeps_base_stats(aoe2_rules, monkeypatch):
    from soundrts.attributes.unit_detail import UnitDetail
    from soundrts.definitions import rules as global_rules

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes

    militia_cls = aoe2_rules.unit_class("militia")
    base_rdf = int(getattr(militia_cls, "rdf", 0) or 0)

    player = SimpleNamespace(
        faction="malians",
        upgrades=[],
        _phase_bonus_pool=[],
    )
    source = SimpleNamespace(player=player, type_name="malian_barracks")
    captured = {}

    def populate_unit_attributes(u, attrs):
        captured["unit"] = u

    parent = SimpleNamespace(
        _attributes_screen_unit=source,
        _attributes_screen_attrs=[],
        _current_attribute_index=0,
        _current_sub_item_index=0,
        _current_attribute_sub_items=[],
        _saved_attributes_state=None,
        _in_detail_attributes_screen=False,
        key_bindings=SimpleNamespace(
            _setup_attributes_screen_bindings=lambda: None
        ),
        main_display=SimpleNamespace(
            display_interface=SimpleNamespace(
                populate_unit_attributes=populate_unit_attributes,
                populate_tech_attributes=lambda *_a, **_k: None,
            ),
            _display_current_attribute=lambda: None,
        ),
    )

    monkeypatch.setattr(
        "soundrts.lib.voice.voice.info", lambda *_a, **_k: None, raising=False
    )
    UnitDetail(parent)._show_unit_detail("militia")

    # Pool empty → no instance rdf seed required; display falls back to model.
    assert not hasattr(captured["unit"], "rdf") or int(
        getattr(captured["unit"], "rdf", base_rdf)
    ) == base_rdf
