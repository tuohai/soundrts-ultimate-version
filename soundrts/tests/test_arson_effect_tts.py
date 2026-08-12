# -*- coding: utf-8 -*-
"""Arson / effect-bonus mdg_vs rows must be localized and PRECISION-scaled."""
from __future__ import annotations

import logging
import os
import sys
import warnings
from pathlib import Path

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved = sys.argv
sys.argv = [saved[0] if saved else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts import config
    from soundrts import msgparts as mp
    from soundrts.attributes.effect_formatter import EffectFormatter
    from soundrts.attributes.utils import AttributeUtils, get_stat_tts_name
    from soundrts.definitions import rules
    from soundrts.lib.resource import res

sys.argv = saved

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (ROOT / "mods/aoe2/rules.txt").is_file(), reason="aoe2 mod not present"
)


@pytest.fixture
def aoe2_loaded():
    logging.disable(logging.WARNING)
    old = getattr(config, "mods", "")
    config.mods = "aoe2"
    res.set_mods("aoe2")
    res.load_rules_and_ai()
    res.load_style()
    yield
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
        res.load_style()
    logging.disable(logging.NOTSET)


class _Parent:
    def _get_stat_tts_name(self, stat):
        return get_stat_tts_name(stat)

    def _is_precision_stat(self, stat):
        return AttributeUtils(self)._is_precision_stat(stat)


def test_arson_effect_row_translates_mdg_vs_and_scales_value(aoe2_loaded):
    cls = rules.unit_class("arson")
    assert cls is not None and getattr(cls, "effect", None)
    rows = EffectFormatter(_Parent())._format_effect_attribute_rows(cls.effect)
    assert rows, cls.effect
    label, value = rows[0][1], rows[0][2]
    assert list(mp.MDG_VS)[0] in label
    assert "mdg_vs" not in label
    # rules ``mdg_vs building 2`` is stored as 2000; UI must say +2
    assert value == ["+", 1000002] or (
        "+" in value and 1000002 in value
    ), value
