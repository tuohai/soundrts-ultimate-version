"""Rules menace + multi-dim auto threat + menace_vs targeting."""
from __future__ import annotations

import os
import types

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import soundrts.worldunit  # noqa: F401 — break import cycles

from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.combat.targeting import TargetingMixin
from soundrts.definitions import rules
from soundrts.lib.nofloat import PRECISION
from soundrts.lib.resource import res


@pytest.fixture(autouse=True)
def _reload_default_rules():
    """Tests that call rules.load must not leave custom classes for later tests."""
    yield
    res.load_rules_and_ai()


class _MockTarget:
    def __init__(self, type_name, menace=100, x=0, y=0, uid=1):
        self.type_name = type_name
        self.expanded_is_a = ()
        self.menace = menace
        self.x = x
        self.y = y
        self.id = uid
        self.hp = 100
        self.place = object()


class _Chooser(TargetingMixin, DamageCalculationMixin):
    def __init__(self, smart_units=False, counter_skill=0):
        self.mdg = 6
        self.rdg = 0
        self.mdg_vs = {}
        self.rdg_vs = {}
        self.x = 0
        self.y = 0
        self.player = types.SimpleNamespace(
            smart_units=smart_units, counter_skill=counter_skill
        )
        self.attacked = []

    def can_attack(self, other):
        return True

    def _attack(self, target):
        self.attacked.append(target)


def test_rules_menace_overrides_auto_damage_threat():
    rules.load(
        """
def glass
class soldier
mdg 10
menace 1

def tanky
class soldier
mdg 2
menace 20
"""
    )
    glass = rules.unit_class("glass")
    tanky = rules.unit_class("tanky")
    assert glass is not None and tanky is not None
    assert glass.menace == 1 * PRECISION
    assert tanky.menace == 20 * PRECISION
    assert glass.mdg == 10 * PRECISION
    assert tanky.mdg == 2 * PRECISION


def test_choose_enemy_prefers_rules_menace_over_lower_damage_label():
    """High rules menace wins even if the other target's label looks glassier."""
    chooser = _Chooser(smart_units=False)
    soft = _MockTarget("glass", menace=1 * PRECISION, uid=1)
    hard = _MockTarget("tanky", menace=20 * PRECISION, uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        @staticmethod
        def known_enemies(place):
            return [soft, hard]

    chooser.player = _Player()
    chooser.player.smart_units = False
    chooser._choose_enemy(_Place())
    assert chooser.attacked == [hard]


def test_choose_enemy_without_rules_menace_uses_damage_order():
    """Unset menace → sort by threat values on mocks (higher first)."""
    chooser = _Chooser(smart_units=False)
    mage = _MockTarget("mage", menace=8, uid=1)
    knight = _MockTarget("knight", menace=6, uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        @staticmethod
        def known_enemies(place):
            return [knight, mage]

    chooser.player = _Player()
    chooser.player.smart_units = False
    chooser._choose_enemy(_Place())
    assert chooser.attacked == [mage]


def _stub_unit(cls, *, mdg=None, rdg=None, hp=None):
    u = object.__new__(cls)
    u.mdg = cls.mdg if mdg is None else mdg
    u.rdg = cls.rdg if rdg is None else rdg
    u.transport_capacity = getattr(cls, "transport_capacity", 0)
    u.menace_mult = getattr(cls, "menace_mult", PRECISION)
    u.hp_max = getattr(cls, "hp_max", 30 * PRECISION)
    u.hp = u.hp_max if hp is None else hp
    u.mdf = getattr(cls, "mdf", 0)
    u.rdf = getattr(cls, "rdf", 0)
    u.speed = getattr(cls, "speed", PRECISION)
    u.mdg_cd = getattr(cls, "mdg_cd", 0)
    u.rdg_cd = getattr(cls, "rdg_cd", 0)
    u.mdg_ready = getattr(cls, "mdg_ready", 0)
    u.rdg_ready = getattr(cls, "rdg_ready", 0)
    u.mdg_cover = getattr(cls, "mdg_cover", 0)
    u.rdg_cover = getattr(cls, "rdg_cover", 0)
    u.mdg_dodge = getattr(cls, "mdg_dodge", 0)
    u.rdg_dodge = getattr(cls, "rdg_dodge", 0)
    u.mdg_range = getattr(cls, "mdg_range", 0)
    u.rdg_range = getattr(cls, "rdg_range", 0)
    u.world = types.SimpleNamespace(time=0)
    u._cached_menace = 0
    u._menace_cache_timestamp = -1_000_000
    return u


def test_auto_menace_uses_multidim_not_raw_damage_only():
    """Knight with more HP/armor/speed ranks above same-dps fragile caster."""
    rules.load(
        """
def glass_m
class soldier
rdg 6
rdg_cd 1.5
hp_max 10
speed 1

def tank_m
class soldier
mdg 6
mdg_cd 1.5
mdf 2
hp_max 45
speed 2.5
"""
    )
    glass = _stub_unit(rules.unit_class("glass_m"))
    tank = _stub_unit(rules.unit_class("tank_m"))
    assert tank.menace > glass.menace


def test_menace_mult_scales_auto_score():
    rules.load(
        """
def knight_w
class soldier
mdg 6
mdg_cd 1.5
hp_max 45
mdf 1
speed 2.5
menace_mult 1.5

def mage_w
class soldier
rdg 8
rdg_cd 1.5
rdg_range 6
hp_max 30
speed 1
menace_mult 0.8
"""
    )
    knight = _stub_unit(rules.unit_class("knight_w"))
    mage = _stub_unit(rules.unit_class("mage_w"))
    base_k = knight._auto_combat_menace_base()
    assert knight.menace == base_k * int(1.5 * PRECISION) // PRECISION
    # Upgrade damage → auto base rises, mult still applies
    knight.mdg = 12 * PRECISION
    knight._menace_cache_timestamp = -1_000_000
    assert knight.menace > base_k * int(1.5 * PRECISION) // PRECISION
    assert knight.menace > mage.menace


def test_choose_enemy_prefers_higher_effective_menace_mult():
    chooser = _Chooser(smart_units=False)
    knight = _MockTarget("knight", menace=9 * PRECISION, uid=1)
    mage = _MockTarget("mage", menace=int(6.4 * PRECISION), uid=2)

    class _Place:
        strict_neighbors = []

    class _Player:
        @staticmethod
        def known_enemies(place):
            return [mage, knight]

    chooser.player = _Player()
    chooser.player.smart_units = False
    chooser._choose_enemy(_Place())
    assert chooser.attacked == [knight]


class _VsTarget(TargetingMixin):
    """Enemy stub with menace_versus for choose_enemy tests."""

    def __init__(
        self,
        type_name,
        *,
        menace,
        mdg=0,
        rdg=0,
        menace_vs=None,
        menace_mult_vs=None,
        uid=1,
    ):
        self.type_name = type_name
        self.expanded_is_a = ()
        self.menace = menace
        self.mdg = mdg
        self.rdg = rdg
        self.transport_capacity = 0
        self.menace_vs = menace_vs or {}
        self.menace_mult_vs = menace_mult_vs or {}
        self.x = 0
        self.y = 0
        self.id = uid
        self.hp = 100
        self.place = object()


def test_rules_parse_menace_vs_and_mult_vs():
    rules.load(
        """
def footman_v
class soldier
mdg 4
menace_vs knight 2

def archer_v
class soldier
rdg 5
menace_vs knight 3
menace_mult_vs mage 1.2
"""
    )
    foot = rules.unit_class("footman_v")
    arch = rules.unit_class("archer_v")
    assert foot.menace_vs["knight"] == 2 * PRECISION
    assert arch.menace_vs["knight"] == 3 * PRECISION
    assert arch.menace_mult_vs["mage"] == int(1.2 * PRECISION)


def test_menace_versus_absolute_vs_beats_global():
    rules.load(
        """
def archer_v2
class soldier
rdg 8
menace 1
menace_vs knight 5
"""
    )
    cls = rules.unit_class("archer_v2")
    u = _stub_unit(cls)
    u.menace_vs = dict(cls.menace_vs)
    u.menace_mult_vs = dict(getattr(cls, "menace_mult_vs", {}) or {})
    u.type_name = "archer_v2"
    u.expanded_is_a = ()
    obs = types.SimpleNamespace(type_name="knight", expanded_is_a=())
    assert TargetingMixin.menace_versus(u, obs) == 5 * PRECISION
    obs2 = types.SimpleNamespace(type_name="peasant", expanded_is_a=())
    assert isinstance(cls.menace, int)
    assert TargetingMixin.menace_versus(u, obs2) == cls.menace


def test_menace_versus_mult_vs_scales_auto_base():
    rules.load(
        """
def foot_mv
class soldier
mdg 4
mdg_cd 1.5
hp_max 30
menace_mult_vs knight 0.5
"""
    )
    cls = rules.unit_class("foot_mv")
    u = _stub_unit(cls)
    u.menace_vs = {}
    u.menace_mult_vs = dict(cls.menace_mult_vs)
    u.type_name = "foot_mv"
    u.expanded_is_a = ()
    obs = types.SimpleNamespace(type_name="knight", expanded_is_a=())
    base = u._auto_combat_menace_base()
    assert TargetingMixin.menace_versus(u, obs) == base * int(0.5 * PRECISION) // PRECISION
    u.mdg = 8 * PRECISION
    u._menace_cache_timestamp = -1_000_000
    assert TargetingMixin.menace_versus(u, obs) > base * int(0.5 * PRECISION) // PRECISION


def test_choose_enemy_uses_menace_vs_for_observer():
    """Knight prefers archer (menace_vs knight 3) over footman (2)."""
    chooser = _Chooser(smart_units=False)
    chooser.type_name = "knight"
    chooser.expanded_is_a = ()
    foot = _VsTarget(
        "footman",
        menace=10 * PRECISION,
        mdg=4 * PRECISION,
        menace_vs={"knight": 2 * PRECISION},
        uid=1,
    )
    arch = _VsTarget(
        "archer",
        menace=1 * PRECISION,
        rdg=5 * PRECISION,
        menace_vs={"knight": 3 * PRECISION},
        uid=2,
    )

    class _Place:
        strict_neighbors = []

    class _Player:
        @staticmethod
        def known_enemies(place):
            return [foot, arch]

    chooser.player = _Player()
    chooser.player.smart_units = False
    chooser._choose_enemy(_Place())
    assert chooser.attacked == [arch]


def test_ready_slows_auto_menace_vs_same_damage():
    """Longer mdg_ready reduces auto threat vs same mdg/cd/hp."""
    rules.load(
        """
def quick
class soldier
mdg 6
mdg_cd 1
mdg_ready 0
hp_max 30

def slow
class soldier
mdg 6
mdg_cd 1
mdg_ready 1
hp_max 30
"""
    )
    quick = _stub_unit(rules.unit_class("quick"))
    slow = _stub_unit(rules.unit_class("slow"))
    assert quick.menace > slow.menace
