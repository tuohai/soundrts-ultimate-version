# -*- coding: utf-8 -*-
"""Spies / Conscription / Hoardings / Sappers wiring smoke tests."""
from __future__ import annotations

import inspect
from pathlib import Path


def test_upgrade_attrs_and_definitions():
    from soundrts.definitions import rules
    from soundrts.worldupgrade.base import Upgrade

    assert "reveal_enemies" in rules.int_properties
    assert "cost_per_enemy_worker" in rules.int_properties
    assert hasattr(Upgrade, "reveal_enemies")
    assert hasattr(Upgrade, "cost_per_enemy_worker")


def test_perception_has_reveal_helper():
    from soundrts.worldplayerbase import perception as perc

    src = inspect.getsource(perc)
    assert "def _has_reveal_enemies" in src
    assert "if self._has_reveal_enemies():" in src


def test_research_order_cost_mentions_worker():
    from soundrts.worldorders.production import ResearchOrder

    src = inspect.getsource(ResearchOrder.cost.fget)
    assert "cost_per_enemy_worker" in src
    assert "Worker" in src


def test_aoe2_rules_castle_imperial_techs():
    rules_path = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    text = rules_path.read_text(encoding="utf-8")
    assert "def hoardings" in text
    assert "def sappers" in text
    assert "def spies" in text
    assert "reveal_enemies 1" in text
    assert "cost_per_enemy_worker 200" in text
    assert "effect bonus time_cost -33%" in text
    assert "effect bonus hp 1000" in text
    assert "effect bonus mdg_vs building 15" in text
    assert "hoardings sappers spies" in text
