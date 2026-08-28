"""AoE2-style box-select: military beats workers, workers beat buildings."""

from types import SimpleNamespace

from soundrts.clientgamegridview import (
    _BOX_TIER_BUILDING,
    _BOX_TIER_MILITARY,
    _BOX_TIER_WORKER,
    box_select_tier,
    filter_box_selection,
)


class _Obj:
    def __init__(self, *, is_building=False, gather=False, type_name="x"):
        self.model = self
        self.is_a_building = is_building
        self.type_name = type_name
        self._basic_skills = {"go", "attack", "gather"} if gather else {"go", "attack"}
        self.id = id(self)


def test_tiers():
    assert box_select_tier(_Obj()) == _BOX_TIER_MILITARY
    assert box_select_tier(_Obj(gather=True, type_name="peasant")) == _BOX_TIER_WORKER
    assert box_select_tier(_Obj(is_building=True, type_name="townhall")) == _BOX_TIER_BUILDING


def test_mixed_box_keeps_only_military():
    mil = _Obj(type_name="militia")
    wrk = _Obj(gather=True, type_name="peasant")
    bld = _Obj(is_building=True, type_name="townhall")
    assert filter_box_selection([wrk, mil, bld, wrk]) == [mil]


def test_workers_beat_buildings_when_no_military():
    wrk = _Obj(gather=True, type_name="peasant")
    bld = _Obj(is_building=True, type_name="barracks")
    assert filter_box_selection([bld, wrk, bld]) == [wrk]


def test_buildings_kept_when_alone():
    a = _Obj(is_building=True, type_name="house")
    b = _Obj(is_building=True, type_name="mill")
    assert filter_box_selection([a, b]) == [a, b]


def test_single_and_empty_unchanged():
    u = _Obj(gather=True)
    assert filter_box_selection([u]) == [u]
    assert filter_box_selection([]) == []


def test_view_wrapper_uses_model():
    model = _Obj(gather=True, type_name="peasant")
    view = SimpleNamespace(model=model, type_name="peasant")
    assert box_select_tier(view) == _BOX_TIER_WORKER


def test_map_icon_size_shrinks_when_crowded():
    from soundrts.clientgamegridview import map_icon_size_for

    alone = map_icon_size_for(48, "unit", 1)
    packed = map_icon_size_for(48, "unit", 16)
    building = map_icon_size_for(48, "building", 16)
    assert packed < alone
    assert packed >= 8
    assert building >= alone
