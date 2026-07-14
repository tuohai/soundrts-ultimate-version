"""Parity tests for square_terrain_fast vs Python square_terrain_rules."""
from __future__ import annotations

import types

import pytest

from soundrts.lib import square_terrain_rules as strules

stf = pytest.importorskip(
    "soundrts.lib.square_terrain_fast",
    reason="Cython extension not built; run python setup_cython.py --inplace",
)


def _wood(n=1):
    return [types.SimpleNamespace(type_name="wood") for _ in range(n)]


def test_winning_terrain_entry_parity_requires_rules():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    objs = _wood(8)
    cy = stf.winning_terrain_entry(objs, strules.square_terrain_entries_for_type)
    counts = {}
    for o in objs:
        tn = o.type_name
        counts[tn] = counts.get(tn, 0) + 1
    qualified = []
    seen = set()
    for o in objs:
        tn = o.type_name
        if tn in seen:
            continue
        seen.add(tn)
        for entry in strules.square_terrain_entries_for_type(tn):
            if counts.get(tn, 0) >= entry.get("min_count", 1):
                qualified.append(entry)
    py_winner = max(qualified, key=lambda e: e.get("priority", 50)) if qualified else None
    assert cy == py_winner
    assert cy is not None
    assert cy["name"] in ("forest", "dense_forest")


def test_resolve_square_type_name_matches_layers_type_name():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        Path("res/rules.txt").read_text(encoding="utf-8"),
        base_classes=_get_base_classes(),
    )
    square = types.SimpleNamespace(
        objects=_wood(8),
        high_ground=False,
        is_water=False,
        fixed_terrain=False,
        type_name="",
        world=types.SimpleNamespace(),
    )
    fast = stf.resolve_square_type_name(
        square,
        strules.square_terrain_entries_for_type,
        strules._bridge_layer_voice,
    )
    layers = strules.resolve_square_layers(square)
    assert fast == layers["type_name"]
    assert strules.resolve_square_type_name(square) == layers["type_name"]
