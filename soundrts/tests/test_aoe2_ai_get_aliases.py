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
    """Real DE trainables exist; base aliases are decay stubs for old maps."""
    r = _load_aoe2(monkeypatch)
    assert r.unit_class("militia") is not None
    assert r.unit_class("aoe_archer") is not None
    assert r.unit_class("aoe_knight") is not None
    assert r.unit_class("mangonel") is not None
    for name in ("archer", "knight", "footman", "catapult"):
        uc = r.unit_class(name)
        assert uc is not None, name
        assert getattr(uc, "decay", 0), name


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
        "woad_raider",
        "jaguar_warrior",
    ):
        assert uu in text, uu
    assert "militia" in text and "aoe_archer" in text and "mangonel" in text
    assert "battering_ram" in text
    assert "portuguese_villager" in text and "chinese_villager" in text
    assert "aztec_villager" in text and "scout_cavalry" in text


def test_aoe2_ai_txt_dark_feudal_lines_have_no_castle_units():
    """First two get lines of each def are dark eco + feudal army only."""
    castle = {
        "aoe_knight",
        "mangonel",
        "battering_ram",
        "monk",
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
        "jaguar_warrior",
        "woad_raider",
        "eagle_warrior",
        "cavalry_archer",
    }
    n = 0
    for line in Path("mods/aoe2/ai.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("def "):
            n = 0
            continue
        if not line.startswith("get "):
            continue
        n += 1
        if n > 2:
            continue
        toks = set(line.split())
        assert not (toks & castle), line


def test_aoe2_ai_txt_asks_for_rams_after_feudal():
    """Castle/siege waves must request battering rams to crack town centers."""
    n = 0
    found_ram = False
    for line in Path("mods/aoe2/ai.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("def "):
            if n >= 3:
                assert found_ram
            n = 0
            found_ram = False
            continue
        if not line.startswith("get "):
            continue
        n += 1
        if n >= 3 and "battering_ram" in line.split():
            found_ram = True
    assert n < 3 or found_ram
