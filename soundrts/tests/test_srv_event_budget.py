# -*- coding: utf-8 -*-
"""Burst cheap notifies; do not run voila in the same drain call."""

from __future__ import annotations

import queue
from types import SimpleNamespace

from soundrts import parameters
from soundrts.clientgame.game_interface_base import GameInterface


def _stub():
    processed = []
    stub = SimpleNamespace(
        _srv_queue=queue.Queue(),
        _process_srv_event=lambda *e: processed.append(e),
    )
    stub._processed = processed
    return stub


def test_budget_drains_several_notifies(monkeypatch):
    monkeypatch.setitem(parameters.d, "srv_event_budget_ms", 8)
    stub = _stub()
    for i in range(20):
        stub._srv_queue.put(("event", i))
    GameInterface._process_srv_events(stub)
    assert len(stub._processed) == 20
    assert stub._srv_queue.empty()


def test_leaves_voila_for_next_frame(monkeypatch):
    monkeypatch.setitem(parameters.d, "srv_event_budget_ms", 8)
    stub = _stub()
    stub._srv_queue.put(("event", 1))
    stub._srv_queue.put(("event", 2))
    stub._srv_queue.put(("voila", 0))
    GameInterface._process_srv_events(stub)
    assert [e[0] for e in stub._processed] == ["event", "event"]
    assert stub._srv_queue.get()[0] == "voila"


def test_voila_alone_still_runs(monkeypatch):
    monkeypatch.setitem(parameters.d, "srv_event_budget_ms", 8)
    stub = _stub()
    stub._srv_queue.put(("voila", 0))
    GameInterface._process_srv_events(stub)
    assert stub._processed == [("voila", 0)]
