"""Pierce-line geometry unit tests."""
from __future__ import annotations

import logging

from soundrts.combat.pierce_line import _point_segment_dist2
from soundrts.lib.nofloat import PRECISION


class TestPierceGeometry:
    def test_on_segment(self):
        assert _point_segment_dist2(500, 0, 0, 0, 1000, 0) == 0

    def test_off_segment_width(self):
        d2 = _point_segment_dist2(500, 400, 0, 0, 1000, 0)
        assert d2 == 400 * 400
        assert d2 <= 500 * 500

    def test_beyond_endpoint(self):
        d2 = _point_segment_dist2(1200, 0, 0, 0, 1000, 0)
        assert d2 == 200 * 200


def test_soldier_has_pierce_line_rule_attrs():
    from soundrts.worldunit.worldsoldier import Soldier

    for name in (
        "rdg_pierce_line",
        "rdg_pierce_width",
        "rdg_pierce_max",
        "mdg_pierce_line",
        "mdg_pierce_width",
        "mdg_pierce_max",
    ):
        assert hasattr(Soldier, name), name


def test_rules_apply_rdg_pierce_line_on_soldier(caplog):
    from soundrts.definitions import Rules

    caplog.set_level(logging.WARNING)
    r = Rules()
    r.load(
        """
def dummy_scorpion
class soldier
rdg_pierce_line 1
rdg_pierce_width 0.5
rdg_pierce_max 3
"""
    )
    assert not any(
        "rdg_pierce" in rec.getMessage() for rec in caplog.records
    ), [rec.getMessage() for rec in caplog.records if "rdg_pierce" in rec.getMessage()]
    cls = r.unit_class("dummy_scorpion")
    assert cls is not None
    assert int(cls.rdg_pierce_line) == 1
    assert int(cls.rdg_pierce_width) == PRECISION // 2
    assert int(cls.rdg_pierce_max) == 3
