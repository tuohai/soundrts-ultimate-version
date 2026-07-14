"""Attribute-driven AI type discovery: no faction type-name literals in economy code."""
from __future__ import annotations

import logging
import os
import sys
import warnings

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

saved_argv = sys.argv
sys.argv = [saved_argv[0] if saved_argv else "pytest"]
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from soundrts.lib.resource import res
    from soundrts.worldplayercomputer import Computer

sys.argv = saved_argv


def setup_module():
    logging.disable(logging.CRITICAL)
    res.load_rules_and_ai()


def _ai():
    ai = Computer.__new__(Computer)
    ai._workers = []
    ai.units = []
    ai._type_discovery_cache = None
    ai.world = type("W", (), {"turn": 0})()
    return ai


def test_discovery_finds_human_faction_roles_from_attributes():
    ai = _ai()
    assert ai._primary_worker_type_name() == "peasant"
    assert "townhall" in ai._main_base_type_names()
    assert "house" in ai._housing_type_names()
    assert "lumbermill" in ai._storage_building_type_names(1)
    assert "townhall" in ai._storage_building_type_names(0)
    assert "gate" in ai._gate_type_names()
    assert "shipyard" in ai._naval_yard_type_names()
    assert "boat" in ai._water_transport_type_names()
    assert ai._water_warship_type_names()[0] == "destroyer"
    assert "farm" in ai._resource_building_types("resource3")


def test_preferred_warehouse_prefers_dedicated_wood_store():
    ai = _ai()
    wh = ai._preferred_warehouse_class(resource_type="resource2")
    assert wh is not None
    assert wh.type_name == "lumbermill"
    hall = ai._preferred_warehouse_class()
    assert hall is not None
    assert hall.type_name == "townhall"


def test_worldplayercomputer_has_no_faction_type_literals():
    from pathlib import Path

    src = Path(__file__).resolve().parents[1].joinpath("worldplayercomputer.py").read_text(
        encoding="utf-8"
    )
    # Economy/naval helpers must not hardcode these names as string literals.
    forbidden = (
        'equivalent("peasant")',
        'equivalent("townhall")',
        'equivalent("lumbermill")',
        'equivalent("house")',
        'equivalent("shipyard")',
        'equivalent("boat")',
        'equivalent("destroyer")',
        'unit_class("farm")',
        'unit_class("gate")',
    )
    for token in forbidden:
        assert token not in src, token
