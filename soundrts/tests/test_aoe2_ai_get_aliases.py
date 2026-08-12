# -*- coding: utf-8 -*-
"""aoe2 AI must name real mod unit types after rules ``clear``."""
from __future__ import annotations

from pathlib import Path

from soundrts import definitions
from soundrts.definitions import Rules
from soundrts.worldplayerbase import base as player_base
from soundrts import worldplayercomputer as wpc


def _load_aoe2(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    r = Rules()
    r.load(
        (root / "res" / "rules.txt").read_text(encoding="utf-8"),
        (root / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    monkeypatch.setattr(definitions, "rules", r)
    monkeypatch.setattr(player_base, "rules", r)
    monkeypatch.setattr(wpc, "rules", r)
    return r


def test_aoe2_clear_removes_base_aliases(monkeypatch):
    """clear drops footman/archer/knight classes — ai.txt must not use them."""
    r = _load_aoe2(monkeypatch)
    assert r.unit_class("militia") is not None
    assert r.unit_class("aoe_archer") is not None
    assert r.unit_class("aoe_knight") is not None
    assert r.unit_class("mangonel") is not None
    assert r.unit_class("archer") is None
    assert r.unit_class("knight") is None
    assert r.unit_class("footman") is None
    assert r.unit_class("catapult") is None


def test_aoe2_ai_txt_has_no_mage():
    text = Path("mods/aoe2/ai.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.lstrip().startswith(";"):
            continue
        assert " mage" not in f" {line} ", line


def test_aoe2_ai_txt_uses_real_units_and_unique_units():
    """AI plans must name aoe2 types (not footman/archer) and include castle UUs."""
    text = Path("mods/aoe2/ai.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        if not line.startswith("get "):
            continue
        for tok in line.split():
            assert tok not in ("footman", "archer", "knight", "catapult"), line
    for uu in (
        "longbowman",
        "throwing_axeman",
        "chu_ko_nu",
        "mangudai",
        "cataphract",
        "samurai",
        "teutonic_knight",
        "berserk",
        "rattan_archer",
        "organ_gun",
    ):
        assert uu in text, uu
    assert "militia" in text and "aoe_archer" in text and "mangonel" in text
    assert "portuguese_villager" in text and "chinese_villager" in text
