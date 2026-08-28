"""Pierce-line geometry unit tests."""
from __future__ import annotations

from soundrts.combat.pierce_line import _point_segment_dist2


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
