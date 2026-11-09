# -*- coding: utf-8 -*-
"""The AI's gather-target choice must be reproducible across processes.

``Computer._known_ok_deposits_compute`` collects the deposits from
``perception`` and ``memory`` — both are **sets**.  ``set`` iteration order
depends on the objects' ``id()`` (their memory address), and CPython's
allocator plus ASLR move those addresses around from one process to the
next.

Downstream, ``_choose_gather_target_compute`` sorts the candidates by
``(need_ratio, renewable_rank, distance)``.  When two deposits tie on all
three (very common: two gold mines at the same distance), the sort is
*stable* and the winner is decided by the input order — i.e. by the
memory address.  The same seed then produced different matches from run
to run (crazyMod z5, seed 42: 1209.0 s vs 1045.5 s kill time).

The fix is to sort the deposit list by a stable key (map coordinates,
then type name, then object id) before handing it downstream.
"""
from __future__ import annotations

from types import SimpleNamespace

from soundrts.worldplayercomputer import Computer
from soundrts.worldresource import Deposit


class _FakeDeposit(Deposit):
    """A minimal stand-in for a real deposit (gold mine / tree)."""

    def __init__(self, obj_id, x, y, type_name="goldmine"):
        self.id = obj_id
        self.type_name = type_name
        self.place = SimpleNamespace(x=x, y=y, id=obj_id)
        self.qty = 100
        self.qty_max = 100
        self.hp = 100
        self.player = None
        self.resource_qty = 100
        self.resource_type = "resource1"


class _FakeComp(Computer):
    """A Computer stub whose perception/memory are plain sets."""

    def __init__(self, deposits):
        self.perception = set(deposits)
        self.memory = set()
        self._gather_target_ok = lambda target: True


def _make_deposit(obj_id, x, y):
    return _FakeDeposit(obj_id, x, y)


def test_known_ok_deposits_are_sorted_deterministically():
    """The returned order must not depend on the set iteration order."""
    deposits = [
        _make_deposit(3, 10, 0),
        _make_deposit(1, 0, 0),
        _make_deposit(2, 0, 10),
    ]
    comp = _FakeComp(deposits)

    result = comp._known_ok_deposits_compute()

    assert [d.id for d in result] == [1, 2, 3]


def test_known_ok_deposits_order_is_stable_across_input_permutations():
    """Two different set contents (same deposits) give the same order."""
    a = _FakeComp(
        [
            _make_deposit(1, 0, 0),
            _make_deposit(2, 0, 10),
            _make_deposit(3, 10, 0),
        ]
    )
    b = _FakeComp(
        [
            _make_deposit(3, 10, 0),
            _make_deposit(1, 0, 0),
            _make_deposit(2, 0, 10),
        ]
    )

    assert (
        [d.id for d in a._known_ok_deposits_compute()]
        == [d.id for d in b._known_ok_deposits_compute()]
    )


def test_known_ok_deposits_tiebreak_is_not_the_memory_address():
    """Two deposits at the *same* place must still get a stable order.

    Same coordinates + same type name: the object id decides, never the
    address.  This is the case that used to flip between processes.
    """
    a = _make_deposit(7, 5, 5)
    b = _make_deposit(9, 5, 5)
    comp = _FakeComp([a, b])

    result = comp._known_ok_deposits_compute()

    assert [d.id for d in result] == [7, 9]
