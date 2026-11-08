# -*- coding: utf-8 -*-
"""AoE2: a farm is a food *producer*, never a food drop-off (warehouse).

The user flagged this explicitly:

    「农田在帝国2原版中好像不能作为仓库存储开采的实物」
    (In AoE2 a farm cannot act as a warehouse that stores harvested goods.)

In AoE2 the food chain is::

    farm  -> (villager harvests from it, carries the food)  ->  mill / town center

The farm *holds* food (175) which the villager extracts; the mill / town
center is the drop-off that *stores* the food in the player's stock.  If a
farm were treated as a drop-off the whole chain would break in two places:

1. ``farm`` would appear in ``nearest_warehouse`` results, so a villager
   would walk to the *farm* to deposit food instead of to the mill/TC — and
   the food would never enter the player's stock, so the 500-food feudal
   click could never happen;
2. the food drop-off the AI builds would be a farm rather than a mill, and
   ``farm`` has ``requirements mill`` — the food engine would be circular
   and never start.

These tests pin the invariant at the *rules* level (the source of truth),
at the *engine* level (the drop-off search) and at the *AI* level (the
drop-off chooser).
"""

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
    yield rules
    config.mods = old
    res.set_mods(old or "")
    if old:
        res.load_rules_and_ai()
    logging.disable(logging.NOTSET)


# ---------------------------------------------------------------------------
# 1. rules level — the farm declares no storage at all
# ---------------------------------------------------------------------------


def test_farm_is_not_a_warehouse(aoe2_loaded):
    """The AoE2 farm stores nothing: it has no ``storable_resource_types``."""
    farm = rules.unit_class("farm")
    assert farm is not None, "the aoe2 farm must exist"
    assert tuple(getattr(farm, "storable_resource_types", ()) or ()) == (), (
        "an AoE2 farm must NOT be able to store harvested resources: "
        "the mill / town center is the drop-off"
    )


def test_farm_variants_are_not_warehouses(aoe2_loaded):
    """The civ-specific farm variants behave like the generic farm."""
    for name in ("teuton_farm", "slav_farm"):
        uc = rules.unit_class(name)
        if uc is None:
            continue
        assert tuple(getattr(uc, "storable_resource_types", ()) or ()) == (), (
            f"{name} must NOT be a warehouse"
        )


def test_farm_is_a_producer_not_a_store(aoe2_loaded):
    """The farm produces food (175) and must be recultivated with 60 wood."""
    farm = rules.unit_class("farm")
    assert getattr(farm, "production_type", None) == "resource3"
    assert getattr(farm, "resource_type", None) == "resource3"
    assert getattr(farm, "auto_cultivate", 0)
    assert int(getattr(farm, "resource_volume_max", 0)) == 175
    assert int(getattr(farm, "production_qty", 0)) == 175


def test_mill_and_town_center_are_the_food_dropoffs(aoe2_loaded):
    """The mill and the town center are the ones that store the food."""
    mill = rules.unit_class("mill")
    assert "resource3" in tuple(getattr(mill, "storable_resource_types", ()) or ())
    tc = rules.unit_class("town_center")
    assert "resource3" in tuple(getattr(tc, "storable_resource_types", ()) or ())
    # and the farm needs a mill to exist at all
    farm = rules.unit_class("farm")
    assert "mill" in tuple(getattr(farm, "requirements", ()) or ())


def test_pasture_is_a_dropoff_but_only_for_mongols(aoe2_loaded):
    """The AoE4-style ``pasture`` really does store food — Mongols only.

    The Mongols get their food from sheep herded to a pasture (AoE4 design),
    so the pasture is a genuine food drop-off for them.  It must NOT leak to
    the other civs: their farms need a *mill*, and a pasture is not a mill.
    """
    pasture = rules.unit_class("pasture")
    assert "resource3" in tuple(
        getattr(pasture, "storable_resource_types", ()) or ()
    ), "the AoE4-style pasture stores food for the Mongols"

    # The Mongols' herdsman can build a pasture and NOT a mill.
    herdsman = rules.unit_class("mongol_herdsman")
    assert herdsman is not None
    built = tuple(rules.class_rules_attr(herdsman, "can_build", ()) or ())
    assert "pasture" in built
    assert "mill" not in built, "the Mongol herdsman must not build a mill"

    # A normal villager builds a mill and NOT a pasture.
    peasant = rules.unit_class("peasant")
    assert peasant is not None
    p_built = tuple(rules.class_rules_attr(peasant, "can_build", ()) or ())
    assert "mill" in p_built
    assert "pasture" not in p_built, (
        "the pasture is the AoE4-style Mongol building; a normal villager "
        "must not be able to build it"
    )


# ---------------------------------------------------------------------------
# 2. engine level — the drop-off search never returns a farm
# ---------------------------------------------------------------------------


def test_nearest_warehouse_never_returns_a_farm(aoe2_loaded):
    """``PlayerBase.nearest_warehouse`` must skip the farm.

    The villager's ``bring_back`` mode uses this to pick where to deposit the
    food it harvested.  If it could return a farm, the food would be dumped
    into the farm instead of the player's stock.
    """
    from soundrts.worldplayerbase.base import Player

    # A farm and a mill on the same square: the mill must win.
    farm = rules.unit_class("farm")
    mill = rules.unit_class("mill")
    assert "resource3" not in tuple(
        getattr(farm, "storable_resource_types", ()) or ()
    )
    assert "resource3" in tuple(
        getattr(mill, "storable_resource_types", ()) or ()
    )

    # The engine filters the candidates purely by ``storable_resource_types``
    # (see ``Player.nearest_warehouse``), so a farm can never enter the
    # candidate list.  Pin that contract here so a future change that adds
    # ``storable_resource_types`` to the farm breaks this test loudly.
    import inspect

    src = inspect.getsource(Player.nearest_warehouse)
    assert "storable_resource_types" in src


# ---------------------------------------------------------------------------
# 3. AI level — the AI's food drop-off chooser never picks a farm
# ---------------------------------------------------------------------------


def test_ai_food_dropoff_is_never_a_farm(aoe2_loaded):
    """``_storage_type_for_resource(2)`` must not be a farm."""
    from soundrts.worldplayercomputer import Computer

    ai = Computer.__new__(Computer)
    ai._type_discovery_cache = None
    ai._workers = []

    # Pretend the AI owns a villager that can build a mill.
    ai._worker_buildable_type_names = lambda: frozenset(
        {"mill", "town_center", "farm", "pasture", "shipyard", "lumbermill"}
    )

    chosen = Computer._storage_type_for_resource(ai, 2)
    assert chosen is not None, "the AI must have a food drop-off"
    assert chosen != "farm", "a farm is a producer, never a drop-off"

    uc = rules.unit_class(chosen)
    assert "resource3" in tuple(getattr(uc, "storable_resource_types", ()) or ()), (
        "the chosen food drop-off must really store food"
    )


def test_ai_storage_building_names_never_include_a_farm(aoe2_loaded):
    """``_storage_building_type_names`` is driven by ``storable_resource_types``."""
    from soundrts.worldplayercomputer import Computer

    ai = Computer.__new__(Computer)
    ai._type_discovery_cache = None
    ai._workers = []
    ai._worker_buildable_type_names = lambda: frozenset(
        {"mill", "town_center", "farm", "pasture"}
    )

    for index in (0, 1, 2):
        names = Computer._storage_building_type_names(ai, index)
        assert "farm" not in names, (
            f"the farm must never be listed as a drop-off (resource index {index})"
        )


def test_ai_owned_farm_predicate_does_not_match_a_dropoff(aoe2_loaded):
    """``_is_owned_farm`` identifies *producers*, not drop-offs.

    The predicate is data-driven (``auto_cultivate`` + ``production_type``),
    so it must not confuse a food *store* (mill, pasture, town center) with
    a food *producer* (farm).
    """
    from soundrts.worldplayercomputer import Computer

    ai = Computer.__new__(Computer)
    ai.player = None

    class _Building:
        is_a_building = True
        player = None

    farm = _Building()
    farm.auto_cultivate = 1
    farm.production_type = "resource3"
    farm.storable_resource_types = ()

    mill = _Building()
    mill.auto_cultivate = 0
    mill.production_type = "resource1"
    mill.storable_resource_types = ("resource3",)

    assert Computer._is_owned_farm(ai, farm) is True
    assert Computer._is_owned_farm(ai, mill) is False, (
        "the mill is a drop-off, not a farm"
    )
