# -*- coding: utf-8 -*-
"""Computer.nb / future_nb play-turn index must match the uncached scan."""
from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer
from soundrts.worldunit import Worker


class _FakeOrder:
    def __init__(self, keyword, type_obj, is_deferred=False):
        self.keyword = keyword
        self.type = type_obj
        self.is_deferred = is_deferred


def _unit(type_name, expanded=(), orders=(), **extra):
    u = SimpleNamespace(
        type_name=type_name,
        expanded_is_a=set(expanded),
        orders=list(orders),
        **extra,
    )
    return u


def _computer(units, upgrades=None, memo=True):
    p = Computer.__new__(Computer)
    p.units = list(units)
    p.upgrades = list(upgrades or [])
    p._play_memo = {} if memo else None
    return p


def test_nb_string_and_expanded_is_a_match_scan():
    militia = _unit("militia", expanded=("militia",))
    maa = _unit("man_at_arms", expanded=("militia", "man_at_arms"))
    peasant = _unit("peasant", expanded=("peasant",))
    p = _computer([militia, maa, peasant])
    assert p.nb("peasant") == 1
    assert p.nb("militia") == 2
    assert p.nb("man_at_arms") == 1
    p._play_memo = None
    assert p.nb("peasant") == 1
    assert p.nb("militia") == 2
    assert p.nb("man_at_arms") == 1


def test_nb_upgrade_list_shortcut():
    p = _computer([], upgrades=["feudal_age"])
    assert p.nb(["feudal_age"]) == 1
    assert p._nb_in_production(["feudal_age"]) == 0
    assert p.future_nb(["feudal_age"]) == 1


def test_nb_single_item_list_uses_name_index():
    p = _computer([_unit("peasant", expanded=("peasant",))])
    assert p.nb(["peasant"]) == 1
    assert "_nb_name_counts" in p._play_memo


def test_future_nb_counts_train_order_and_invalidates():
    peasant_type = SimpleNamespace(type_name="peasant", expanded_is_a={"peasant"})
    barracks = _unit("barracks", expanded=("barracks",))
    p = _computer([barracks])
    assert p.nb("peasant") == 0
    assert p.future_nb("peasant") == 0
    barracks.orders = [_FakeOrder("train", peasant_type)]
    p._invalidate_play_derived_counts()
    assert p._play_memo.get("_nb_prod_name_counts") is None
    assert p.nb("peasant") == 0
    assert p.future_nb("peasant") == 1
    assert p._play_memo.get("_nb_name_counts") is not None
    assert p._play_memo.get("_nb_prod_name_counts") == {"peasant": 1}


def test_nb_worker_class_uses_isinstance():
    class Peasant(Worker):
        pass

    peasant = Peasant.__new__(Peasant)
    peasant.type_name = "peasant"
    peasant.expanded_is_a = {"peasant"}
    peasant.orders = []
    other = _unit("barracks", expanded=("barracks",))
    p = _computer([peasant, other])
    assert p.nb(Worker) == 1
    p._play_memo = None
    assert p.nb(Worker) == 1


def test_check_type_string_does_not_require_inspect():
    p = _computer([])
    u = _unit("man_at_arms", expanded=("militia", "man_at_arms"))
    assert p.check_type(u, "man_at_arms")
    assert p.check_type(u, "militia")
    assert not p.check_type(u, "knight")
    assert p.check_type(u, ["knight", "militia"])
