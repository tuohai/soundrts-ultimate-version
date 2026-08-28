# -*- coding: utf-8 -*-
"""Villager can_build detail must resolve civ shells (aoe_castle → briton_castle)."""
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


def test_unit_detail_resolves_briton_castle_can_train(aoe2_rules, monkeypatch):
    from soundrts import msgparts as mp
    from soundrts.attributes.unit_detail import UnitDetail
    from soundrts.definitions import rules as global_rules
    from soundrts.worldplayerbase.base import Player

    global_rules._dict = aoe2_rules._dict
    global_rules.classes = aoe2_rules.classes

    player = SimpleNamespace(
        faction="britons",
        upgrades=[],
        _can_train_overrides_by_type=None,
    )
    player.equivalent = lambda tn, _p=player: Player.equivalent(_p, tn)

    villager = SimpleNamespace(player=player, type_name="peasant")
    captured = {}

    class FakeParent:
        def __init__(self):
            self._attributes_screen_unit = villager
            self._attributes_screen_attrs = []
            self._current_attribute_index = 0
            self._current_sub_item_index = 0
            self._current_attribute_sub_items = []
            self._saved_attributes_state = None
            self._in_detail_attributes_screen = False
            self.key_bindings = SimpleNamespace(
                _setup_attributes_screen_bindings=lambda: None
            )
            self.main_display = SimpleNamespace(
                display_interface=SimpleNamespace(
                    populate_unit_attributes=lambda u, attrs: (
                        captured.update(unit=u),
                        attrs.append(
                            (
                                "o",
                                mp.CAN_TRAIN,
                                (
                                    "CAN_TRAIN_ITEMS",
                                    list(getattr(u, "can_train", {}) or {}),
                                ),
                            )
                        ),
                    ),
                    populate_tech_attributes=lambda *_a, **_k: None,
                ),
                _display_current_attribute=lambda: None,
            )

    detail = UnitDetail(FakeParent())
    monkeypatch.setattr(
        "soundrts.lib.voice.voice.info", lambda *_a, **_k: None, raising=False
    )
    detail._show_unit_detail("aoe_castle")

    unit = captured.get("unit")
    assert unit is not None
    assert unit.type_name == "briton_castle"
    train = getattr(unit, "can_train", None) or {}
    assert "longbowman" in train
    assert "trebuchet" in train
