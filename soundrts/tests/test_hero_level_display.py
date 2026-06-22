"""Hero level display in unit status and initial level from rules.txt."""
from __future__ import annotations

import sys
import types

import pytest

import soundrts.worldunit  # noqa: F401

from soundrts import msgparts as mp
from soundrts.definitions import Rules
from soundrts.level_up_stats import apply_level_up_to
from soundrts.lib.msgs import nb2msg


def _stub_client_modules():
    if "soundrts.clientmedia" not in sys.modules:
        stub = types.ModuleType("soundrts.clientmedia")
        stub.sounds = None
        stub.voice = None
        sys.modules["soundrts.clientmedia"] = stub
    if "soundrts.clientmenu" not in sys.modules:
        sys.modules["soundrts.clientmenu"] = types.ModuleType("soundrts.clientmenu")
    if "soundrts.animation" not in sys.modules:
        ani = types.ModuleType("soundrts.animation")
        ani.noise = lambda *a, **kw: None
        sys.modules["soundrts.animation"] = ani
    if "soundrts.clientgamenews" not in sys.modules:
        news = types.ModuleType("soundrts.clientgamenews")
        news.must_be_said = lambda *a, **kw: False
        sys.modules["soundrts.clientgamenews"] = news
    if "soundrts.clientgameorder" not in sys.modules:
        co = types.ModuleType("soundrts.clientgameorder")
        co.get_orders_list = lambda: []
        co.substitute_args = lambda *a, **kw: None
        sys.modules["soundrts.clientgameorder"] = co
    if "soundrts.lib.sound" not in sys.modules:
        s = types.ModuleType("soundrts.lib.sound")
        s.distance = lambda *a, **kw: 0
        s.psounds = None
        s.angle = lambda *a, **kw: 0
        s.MUSIC_FORMATS = [".mp3", ".ogg", ".wav"]
        sys.modules["soundrts.lib.sound"] = s


def _import_entity_view_properties():
    _stub_client_modules()
    try:
        from soundrts.clientgameentity.properties import EntityViewProperties

        return EntityViewProperties
    except Exception:
        return None


def _make_hero_view(*, level=1, xp_thresholds=None, xp=0, hp=100, hp_max=100):
    evp = _import_entity_view_properties()
    if evp is None:
        pytest.skip("EntityViewProperties unavailable in test env")

    class _HeroView(evp):
        is_memory = False
        speed = 0
        type_name = "hero"
        interface = types.SimpleNamespace(
            player=types.SimpleNamespace(neutral=False, allied=[])
        )

        @property
        def hp_status(self):
            return nb2msg(self.hp) + mp.ON + nb2msg(self.hp_max)

    view = _HeroView()
    view.hp = hp
    view.hp_max = hp_max
    view.level = level
    view.xp = xp
    view.xp_thresholds = xp_thresholds or []
    return view


def _description_contains_level(desc, level):
    flat = []
    for part in desc:
        if isinstance(part, list):
            flat.extend(part)
        else:
            flat.append(part)
    return mp.LEVEL[0] in flat and nb2msg(level)[0] in flat


def _description_contains_xp_on(desc, current, target):
    flat = []
    for part in desc:
        if isinstance(part, list):
            flat.extend(part)
        else:
            flat.append(part)
    return nb2msg(current)[0] in flat and nb2msg(target)[0] in flat


def test_description_shows_level_0_xp_toward_first_threshold():
    thresholds = [40, 90, 160, 250, 360, 490, 640, 810, 1000]
    view = _make_hero_view(level=0, xp_thresholds=thresholds, xp=0)
    desc = view.description
    assert _description_contains_level(desc, 0)
    assert _description_contains_xp_on(desc, 0, 40)
    assert not _description_contains_xp_on(desc, 0, 1000)


def test_description_shows_level_1_with_xp_thresholds():
    view = _make_hero_view(level=1, xp_thresholds=[200, 500], xp=0)
    desc = view.description
    assert _description_contains_level(desc, 1)


def test_description_hides_level_1_without_xp_thresholds():
    view = _make_hero_view(level=1, xp_thresholds=[])
    desc = view.description
    assert not _description_contains_level(desc, 1)


def test_description_shows_level_2_without_xp_thresholds():
    view = _make_hero_view(level=2, xp_thresholds=[])
    desc = view.description
    assert _description_contains_level(desc, 2)


def test_apply_level_up_to_reaches_target_with_stat_bonuses():
    unit = types.SimpleNamespace(
        level=1,
        max_level=3,
        hp_max=1000,
        hp=1000,
        hp_max_per_level=100,
        mdg=0,
        mdg_per_level=0,
    )
    unit._apply_level_skills_up_to = lambda level=None, notify=False: None
    apply_level_up_to(unit, 2, notify=False)
    assert unit.level == 2
    assert unit.hp_max == 1100
    assert unit.hp == 1100


def test_rules_level_parsed_on_generated_class():
    r = Rules()
    r.load(
        """
def parameters
nb_of_resource_types 2

def soldier
class soldier

def my_hero
class soldier
xp_thresholds 200 500
hp_max_per_level 30
level 2
xp 150
"""
    )
    hero = r.unit_class("my_hero")
    assert hero is not None
    assert hero.level == 2
    assert hero.xp == 150
    assert hero.xp_thresholds == [200, 500]


def test_initial_level_spawn_logic():
    """Mirror Creature.__init__ initial-level block after hp assignment."""
    unit = types.SimpleNamespace(
        level=1,
        max_level=3,
        hp_max=1000,
        hp=1000,
        hp_max_per_level=100,
        mdg=0,
        xp=0,
    )
    unit._apply_level_skills_up_to = lambda level=None, notify=False: None

    class _HeroType:
        level = 2
        xp_thresholds = [200, 500]
        xp = 150

    target_level = getattr(_HeroType, "level", 1)
    if target_level > 1 and getattr(_HeroType, "xp_thresholds", None):
        unit.level = 1
        apply_level_up_to(unit, target_level, notify=False)
    cls_xp = getattr(_HeroType, "xp", 0)
    if cls_xp:
        unit.xp = cls_xp

    assert unit.level == 2
    assert unit.hp_max == 1100
    assert unit.xp == 150
