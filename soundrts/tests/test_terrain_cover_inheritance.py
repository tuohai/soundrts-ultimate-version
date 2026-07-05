"""地形 is_a 继承对 cover/dodge_on_terrain 的回归测试。"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401

from soundrts.combat.hit_miss import HitMissMixin
from soundrts.definitions import _get_base_classes, rules
from soundrts.lib.nofloat import PRECISION


class _ForestPlace:
    type_name = "forest"

    def type_name_at(self, x, y):
        return "forest"


class _Target(HitMissMixin):
    type_name = "footman"
    expanded_is_a = ()
    mdg_dodge = 0
    rdg_dodge = 0
    mdg_dodge_vs = {}
    rdg_dodge_vs = {}
    airground_type = "ground"
    height = 0
    place = _ForestPlace()
    x = 0
    y = 0

    def notify(self, *args, **kwargs):
        pass


class _Archer(HitMissMixin):
    type_name = "archer"
    expanded_is_a = ()
    mdg = 0
    rdg = 3 * PRECISION
    rdg_range = 5 * PRECISION
    mdg_cover = 100 * PRECISION
    rdg_cover = 100 * PRECISION
    mdg_cover_vs = {}
    rdg_cover_vs = {}
    mdg_cover_on_terrain = ()
    rdg_cover_on_terrain = ("forests", "60")
    mdg_dodge_on_terrain = ()
    rdg_dodge_on_terrain = ()
    place = _ForestPlace()
    x = 0
    y = 0
    height = 0

    def __init__(self):
        self.world = types.SimpleNamespace(random=types.SimpleNamespace(randint=lambda a, b: 1))

    def in_ranged_range(self, target):
        return True

    def in_melee_range(self, target):
        return False


def test_rdg_cover_on_terrain_applies_to_child_terrain():
    rules.load(
        """
def forests
class terrain

def forest
class terrain
is_a forests
""",
        base_classes=_get_base_classes(),
    )
    archer = _Archer()
    target = _Target()
    assert archer._hit_or_miss(target) is True
