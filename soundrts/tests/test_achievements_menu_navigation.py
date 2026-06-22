"""Achievement menu navigation for per-faction mods."""

from __future__ import annotations

import pytest

from soundrts import achievements_menu as ach_menu


def test_achievements_menu_returns_to_faction_picker_after_hub_back(monkeypatch):
    """Back from list/armory hub should reopen faction selection, not the main menu."""
    monkeypatch.setattr(ach_menu, "achievements_enabled", lambda: True)
    monkeypatch.setattr(ach_menu, "achievements_per_faction_enabled", lambda: True)
    monkeypatch.setattr(ach_menu, "rules", type("R", (), {"factions": ["traditionnel", "orc"]})())
    monkeypatch.setattr(ach_menu.res, "load_rules_and_ai", lambda: None)

    calls = []

    def fake_select_faction(_caption=None):
        calls.append("select_faction")
        if calls.count("select_faction") == 1:
            return "traditionnel"
        return None

    def fake_hub(_faction):
        calls.append("hub")

    monkeypatch.setattr(ach_menu, "select_faction_or_meta_menu", fake_select_faction)
    monkeypatch.setattr(ach_menu, "_run_faction_hub_menu", fake_hub)

    ach_menu.achievements_menu()

    assert calls == ["select_faction", "hub", "select_faction"]
