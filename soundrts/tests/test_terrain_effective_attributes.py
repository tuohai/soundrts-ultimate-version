"""Attributes screen mdg reflects terrain mdg_vs / mdg_on_terrain on current square."""
from __future__ import annotations

import os
import sys
import types

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.argv = [sys.argv[0]]

from soundrts import msgparts as mp
from soundrts.attributes.bonus_handler import BonusHandler
from soundrts.attributes.terrain_effective import (
    current_terrain_type,
    effective_stat_value,
    terrain_delta_for_attr,
)
from soundrts.attributes.vs_handler import VsHandler
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.nofloat import PRECISION
from soundrts.lib.square_terrain_rules import clear_terrain_lookup_caches

_RULES = """
def knight
class soldier
mdg 6
speed 4

def meadows
class terrain
mdg_vs knight .25

def marsh
class terrain
mdg_vs knight -.33
"""


@pytest.fixture(autouse=True)
def _load_rules():
    clear_terrain_lookup_caches()
    rules.load(_RULES, base_classes=_get_base_classes())
    clear_terrain_lookup_caches()
    yield
    clear_terrain_lookup_caches()


class _Place:
    def __init__(self, name):
        self.type_name = name

    def type_name_at(self, x, y):
        return self.type_name


class _FakeMain:
    def __init__(self):
        self.vs_handler = VsHandler(self)

    def _add_vs_attribute(self, *args, **kwargs):
        return None


def _knight(terrain_name=None, mdg_on_terrain=()):
    return types.SimpleNamespace(
        type_name="knight",
        expanded_is_a=("soldier",),
        mdg=6 * PRECISION,
        mdg_vs={},
        mdg_on_terrain=mdg_on_terrain,
        place=_Place(terrain_name) if terrain_name else None,
        x=0,
        y=0,
        model=None,
    )


def test_terrain_mdg_vs_boosts_effective_mdg_on_meadows():
    u = _knight("meadows")
    # +25% of 6000 = +1500 → 7500
    assert terrain_delta_for_attr(u, "mdg", u.mdg) == 1500
    assert effective_stat_value(u, "mdg", u.mdg) == 7500


def test_terrain_mdg_vs_ignored_off_terrain():
    u = _knight(None)
    assert current_terrain_type(u) is None
    assert effective_stat_value(u, "mdg", u.mdg) == u.mdg


def test_attributes_screen_mdg_row_uses_terrain_boost():
    u = _knight("meadows")
    u.model = u
    attrs = []
    BonusHandler(_FakeMain())._add_bonus_attribute(
        attrs, u, "mdg", "m", mp.MELEE_DAMAGE, True
    )
    mdg_rows = [a for a in attrs if a[1] == mp.MELEE_DAMAGE]
    assert mdg_rows
    assert mdg_rows[0][2] == ["7.5"]


def test_unit_mdg_on_terrain_stacks_with_terrain_vs():
    u = _knight("marsh", mdg_on_terrain=("marsh", "-.1"))
    # terrain mdg_vs -.33 → -1980; unit on_terrain -.1 → -600; total delta -2580
    assert terrain_delta_for_attr(u, "mdg", u.mdg) == -2580
    assert effective_stat_value(u, "mdg", u.mdg) == 6000 - 2580


def test_terrain_speed_vs_scales_displayed_speed():
    from soundrts.attributes.basic_attributes import BasicAttributes
    from soundrts.attributes.terrain_effective import effective_speed_value
    from soundrts.lib.square_terrain_rules import clear_terrain_lookup_caches
    from soundrts.definitions import _get_base_classes, rules

    clear_terrain_lookup_caches()
    rules.load(
        """
def knight
class soldier
speed 4

def meadows
class terrain
speed_vs knight .25
""",
        base_classes=_get_base_classes(),
    )
    clear_terrain_lookup_caches()

    class _Place:
        type_name = "meadows"
        terrain_speed = (100, 100)

        def type_name_at(self, x, y):
            return "meadows"

        def terrain_speed_at(self, x, y):
            return self.terrain_speed

    u = types.SimpleNamespace(
        type_name="knight",
        expanded_is_a=("soldier",),
        airground_type="ground",
        speed=4 * PRECISION,
        speed_on_terrain=(),
        place=_Place(),
        x=0,
        y=0,
        model=None,
    )
    u.model = u
    # .25 → 25% of base 4000 = 1000
    assert effective_speed_value(u, u.speed) == 1000
    attrs = []
    BasicAttributes(_FakeMain()).add_movement_attributes(u, attrs)
    speed_rows = [a for a in attrs if a[1] == mp.SPEED]
    assert speed_rows
    from soundrts.lib.msgs import nb2msg_float

    assert speed_rows[0][2] == nb2msg_float(1.0)


def test_speed_on_terrain_absolute_overrides_speed_vs():
    from soundrts.attributes.terrain_effective import effective_speed_value
    from soundrts.lib.square_terrain_rules import clear_terrain_lookup_caches
    from soundrts.definitions import _get_base_classes, rules

    clear_terrain_lookup_caches()
    rules.load(
        """
def knight
class soldier
speed 4
speed_on_terrain marsh 1.5

def marsh
class terrain
speed_vs knight .25
""",
        base_classes=_get_base_classes(),
    )
    clear_terrain_lookup_caches()

    class _Place:
        type_name = "marsh"
        terrain_speed = (100, 100)

        def type_name_at(self, x, y):
            return "marsh"

        def terrain_speed_at(self, x, y):
            return self.terrain_speed

    u = types.SimpleNamespace(
        type_name="knight",
        expanded_is_a=("soldier",),
        airground_type="ground",
        speed=4 * PRECISION,
        speed_on_terrain=("marsh", "1.5"),
        place=_Place(),
        x=0,
        y=0,
        model=None,
    )
    # absolute 1.5 wins over speed_vs .25
    assert effective_speed_value(u, u.speed) == int(1.5 * PRECISION)
