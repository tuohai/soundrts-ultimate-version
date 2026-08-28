"""Pierce-line geometry + 0 melee vs negative mdf (rams)."""
from __future__ import annotations

import soundrts.worldunit  # noqa: F401

from soundrts.combat.damage_calculation import DamageCalculationMixin
from soundrts.combat.pierce_line import _point_segment_dist2
from soundrts.lib.nofloat import PRECISION


class _DefTarget(DamageCalculationMixin):
    _armor_instance = None
    armor = None
    type_name = "ram"
    expanded_is_a = ("siege_unit",)
    mdf = -3 * PRECISION
    rdf = 0
    mdf_vs = {}
    rdf_vs = {}
    minimal_damage = 0
    forced_damage = 0

    def _get_total_melee_defense_vs(self, attacker):
        return self.mdf

    def _get_total_ranged_defense_vs(self, attacker):
        return self.rdf


class _ZeroMelee(DamageCalculationMixin):
    mdg = 0
    mdg_vs = {}
    rdg = 0
    rdg_vs = {}
    mdg_range = PRECISION  # 1 tile
    mdg_explode = False
    rdg_explode = False
    minimal_damage = 0


class _MonkLike(DamageCalculationMixin):
    mdg = 0
    mdg_vs = {}
    rdg = 0
    rdg_vs = {}
    mdg_range = 0
    mdg_explode = False


class TestPierceGeometry:
    def test_on_segment(self):
        # A(0,0) -> B(1000,0); P(500,0) on line
        assert _point_segment_dist2(500, 0, 0, 0, 1000, 0) == 0

    def test_off_segment_width(self):
        # half-width 0.5 tile = 500; point at 400 should be inside width^2
        d2 = _point_segment_dist2(500, 400, 0, 0, 1000, 0)
        assert d2 == 400 * 400
        assert d2 <= 500 * 500

    def test_beyond_endpoint(self):
        d2 = _point_segment_dist2(1200, 0, 0, 0, 1000, 0)
        assert d2 == 200 * 200


class TestZeroAtkVsNegativeArmor:
    def test_actual_damage_zero_vs_minus_three(self):
        t = _DefTarget()
        a = _ZeroMelee()
        # mdf stored as PRECISION units in real units; mock uses -3*PRECISION
        # _calculate_actual_damage: max(1, 0 - (-3000)) = 3001... use raw ints
        t.mdf = -3
        assert t._calculate_actual_damage(0, a, is_melee=True) == 3

    def test_offensive_melee_with_range(self):
        a = _ZeroMelee()
        t = _DefTarget()
        t.mdf = -3
        assert a._offensive_melee_vs(t) is True
        assert a._projected_melee_hit_damage_vs(t) == 3

    def test_monk_without_mdg_range_blocked(self):
        a = _MonkLike()
        t = _DefTarget()
        t.mdf = -3
        assert a._has_melee_attack_capability() is False
        assert a._offensive_melee_vs(t) is False
