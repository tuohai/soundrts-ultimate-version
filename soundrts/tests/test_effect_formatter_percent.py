# -*- coding: utf-8 -*-
"""Percent effect bonuses must display as +10%, not +0.01."""
from __future__ import annotations

from types import SimpleNamespace

import soundrts.msgparts as mp
from soundrts.attributes.effect_formatter import EffectFormatter
from soundrts.lib.nofloat import PRECISION


class _Parent:
    def _get_stat_tts_name(self, stat):
        return [str(stat)]

    def _is_precision_stat(self, stat):
        return stat in ("hp_max", "mdf", "rdf", "speed")


def test_zero_bonus_omitted_but_info_shown():
    fmt = EffectFormatter(_Parent())
    assert fmt._format_bonus_effect_attribute_rows(["rdg_cover", 0]) == []
    rows = fmt._format_effect_attribute_rows(["info", "8510"])
    assert rows == [("", [8510], ())]


def test_projectile_lead_bonus_hidden_in_attr_rows():
    fmt = EffectFormatter(_Parent())
    assert fmt._format_bonus_effect_attribute_rows(["projectile_lead", 1]) == []


def test_percent_hp_max_displays_as_percent_not_precision():
    fmt = EffectFormatter(_Parent())
    parts = fmt._format_bonus_value_parts("hp_max", "10%")
    assert parts[0] == "+"
    assert "10" in "".join(str(x) for x in parts) or any(
        x == 10 or x == "10" for x in parts
    )
    assert parts[-1] in mp.PERCENT or parts[-1] == "%"
    # Must not look like 10/PRECISION
    flat = " ".join(str(x) for x in parts)
    assert "0.01" not in flat


def test_architecture_effect_rows_show_percent_and_armor():
    fmt = EffectFormatter(_Parent())
    rows = fmt._format_bonus_effect_attribute_rows(
        ["hp_max", "10%", "mdf", 1000, "rdf", 1000, "building"]
    )
    assert len(rows) == 3
    hp_row = rows[0]
    flat = " ".join(str(x) for x in hp_row[2])
    assert "0.01" not in flat
    assert any(x in mp.PERCENT or x == "%" for x in hp_row[2])
    # mdf 1000 → +1
    assert rows[1][2][0] == "+"
