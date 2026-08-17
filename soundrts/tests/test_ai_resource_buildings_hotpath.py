# -*- coding: utf-8 -*-
"""Play-turn memo for pending makers / trainer food / resource thresholds."""
from soundrts.worldplayercomputer import Computer


def _computer(**fields):
    p = Computer.__new__(Computer)
    p.units = []
    p.upgrades = []
    p._play_memo = {}
    p._line_nb = 0
    p._plan = []
    p._workers = []
    p.resources = [0, 0, 0]
    for k, v in fields.items():
        setattr(p, k, v)
    return p


def test_worker_buildable_type_names_scans_each_type_once():
    from types import SimpleNamespace

    calls = []

    class _W:
        type_name = "peasant"

        @property
        def can_build(self):
            calls.append(1)
            return ("townhall", "farm")

    p = _computer(_workers=[_W(), _W(), _W()])
    names = p._worker_buildable_type_names()
    assert "farm" in names
    assert calls == [1]
    p._worker_buildable_type_names()
    assert calls == [1]


def test_pending_production_makers_memoized_per_play():
    walks = []
    p = _computer()
    p._iter_pending_production_makers = lambda ignore_age_defer=False: (
        walks.append(ignore_age_defer) or iter(())
    )
    assert p._pending_production_makers() == ()
    assert p._pending_production_makers() == ()
    assert p._plan_wood_building_cost() == 0
    assert p._plan_next_production_building_cost() == (0, 0)
    assert walks == [False]


def test_pending_production_makers_keys_ignore_age_defer():
    walks = []
    p = _computer()
    p._iter_pending_production_makers = lambda ignore_age_defer=False: (
        walks.append(bool(ignore_age_defer)) or iter(())
    )
    p._pending_production_makers(False)
    p._pending_production_makers(True)
    p._pending_production_makers(False)
    p._pending_production_makers(True)
    assert walks == [False, True]


def test_resource_low_threshold_gold_is_generic():
    p = _computer()
    p._age_up_needs_food = lambda: False
    p._ruleset_has_expensive_food_age = lambda: False
    a = p._resource_low_threshold(0)
    b = p._resource_low_threshold(1)
    assert a == b
    assert p._resource_low_threshold(0) is a or p._resource_low_threshold(0) == a


def test_owned_trainer_food_need_empty_when_no_get_line():
    p = _computer(_plan=["wait 10"])
    assert p._owned_trainer_food_need() == 0
    assert p._owned_trainer_food_need() == 0
    assert p._owned_trainer_wood_need() == 0
    assert p._owned_trainer_wood_need() == 0


def test_pending_makers_skips_defer_token_for_workers():
    calls = []
    p = _computer(_plan=["get 6 peasant 1 militia"])
    p._iter_plan_production_type_names = lambda: iter(("peasant", "militia"))
    p._is_worker_type_name = lambda name: name == "peasant"
    p._defer_plan_get_token = lambda name, saving_for_feudal=False: (
        calls.append(name) or False
    )
    p._unmet_phase_names_for_type = lambda *_a, **_k: ()
    p._worker_buildable_type_names = lambda: frozenset()
    p.nb = lambda _n: 0
    p.future_nb = lambda _n: 0
    p._saving_food_for_age = lambda: False
    list(p._iter_pending_production_makers())
    assert calls == []


def test_pending_makers_skips_line_when_saving_food_for_age():
    seen = []
    p = _computer()
    p._iter_plan_production_type_names = lambda: iter(("militia",))
    p._is_worker_type_name = lambda _n: False
    p._unmet_phase_names_for_type = lambda *_a, **_k: seen.append("unmet") or ()
    p._defer_plan_get_token = lambda *_a, **_k: seen.append("defer") or False
    p._worker_buildable_type_names = lambda: frozenset()
    p.nb = lambda _n: 0
    p.future_nb = lambda _n: 0
    p._saving_food_for_age = lambda: True
    assert list(p._iter_pending_production_makers()) == []
    assert seen == []


def test_get_line_types_memoized_per_play():
    splits = []

    class _Line(str):
        def split(self, *a, **k):
            splits.append(1)
            return str.split(self, *a, **k)

    p = _computer(_plan=[_Line("get 6 peasant")])
    p.equivalent = lambda token: token
    from soundrts.definitions import rules as global_rules

    saved = global_rules.unit_class
    global_rules.unit_class = lambda name: object if name == "peasant" else None
    try:
        a = p._types_on_get_line(p._plan[0])
        b = p._types_on_get_line(p._plan[0])
        assert a == b == ("peasant",)
        assert splits == [1]
    finally:
        global_rules.unit_class = saved


def test_saving_food_for_age_memoized_per_play():
    walks = []
    p = _computer()
    p._plan_unmet_phase_names = lambda lookahead=False: walks.append(1) or ()
    assert p._saving_food_for_age() is False
    assert p._saving_food_for_age() is False
    assert walks == [1]
