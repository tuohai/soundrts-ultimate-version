# -*- coding: utf-8 -*-
"""aoe2 ``clear`` must redeclare terrains + building_land for maps."""
from __future__ import annotations

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.lib.building_land import (
    building_land_types,
    default_building_land_type,
    nb_by_square_land_type,
)


def test_aoe2_clear_keeps_meadow_and_terrains(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    r = Rules()
    r.load(
        (root / "res" / "rules.txt").read_text(encoding="utf-8"),
        (root / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    monkeypatch.setattr("soundrts.lib.building_land.rules", r)

    assert r.get("meadow", "class") == ["building_land"]
    assert r.get("build_site", "class") == ["building_land"]
    assert r.get("meadows", "class") == ["terrain"]
    assert r.get("forest", "class") == ["terrain"]
    assert r.get("town", "class") == ["terrain"]
    assert "meadow" in building_land_types()
    assert "build_site" in building_land_types()
    assert default_building_land_type() == "meadow"
    assert nb_by_square_land_type("nb_meadow_by_square") == "meadow"
    assert nb_by_square_land_type("nb_build_site_by_square") == "build_site"


def test_aoe2_clear_keeps_peasant_worker_class():
    """After ``clear``, peasant must declare ``class worker`` or TC train menu crashes."""
    root = Path(__file__).resolve().parents[2]
    r = Rules()
    r.load(
        (root / "res" / "rules.txt").read_text(encoding="utf-8"),
        (root / "mods" / "aoe2" / "rules.txt").read_text(encoding="utf-8"),
    )
    assert r.get("peasant", "class") == ["worker"]
    for name in (
        "peasant",
        "chinese_villager",
        "mongol_herdsman",
        "portuguese_villager",
        "aztec_villager",
    ):
        assert r.unit_class(name) is not None, name
        assert hasattr(r.unit_class(name), "requirements")
