"""Tests for cross-chapter hero persistence (rules-driven)."""
from __future__ import annotations

import configparser
from pathlib import Path

import pytest

from soundrts.campaign_hero import (
    carryover_id_for_type,
    carryover_modes_for_id,
    chapter_min_level,
    clear_hero_snapshot,
    load_hero_snapshot,
    save_hero_snapshot,
)
from soundrts.paths import CAMPAIGNS_CONFIG_PATH


class _FakeCampaign:
    def __init__(self, section="test_hero_campaign", hero_min_level=None):
        self._section = section
        self.hero_min_level = hero_min_level or {}

    def _id(self):
        return self._section


class _FakeUnit:
    type_name = "raynor"

    def __init__(self):
        self.xp = 450
        self.level = 2
        self.inventory = []


@pytest.fixture
def hero_ini(tmp_path, monkeypatch):
    path = tmp_path / "campaigns.ini"
    path.write_text("", encoding="utf-8")
    monkeypatch.setattr("soundrts.paths.CAMPAIGNS_CONFIG_PATH", str(path))
    return path


def test_chapter_min_level_from_campaign_txt():
    campaign = _FakeCampaign(
        hero_min_level={13: 2, 16: 3, 19: 4, 22: 5, 25: 6, 27: 7}
    )
    assert chapter_min_level(1, campaign) == 1
    assert chapter_min_level(13, campaign) >= 2
    assert chapter_min_level(27, campaign) >= 7


def test_chapter_min_level_without_campaign_defaults_to_one():
    assert chapter_min_level(27) == 1


def test_carryover_id_for_raynor_family():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    raynor_rules = (
        Path(__file__).resolve().parents[2]
        / "res"
        / "single"
        / "The Legend of Raynor"
        / "rules.txt"
    ).read_text(encoding="utf-8")
    rules.load(raynor_rules, base_classes=_get_base_classes())
    assert carryover_id_for_type("raynor") == "raynor"
    assert carryover_id_for_type("raynor7") == "raynor"
    assert carryover_id_for_type("footman") is None


def test_save_and_load_hero_snapshot(hero_ini):
    campaign = _FakeCampaign()
    unit = _FakeUnit()
    save_hero_snapshot(campaign, unit, "raynor")
    snap = load_hero_snapshot(campaign, "raynor")
    assert snap is not None
    assert snap["xp"] == 450
    assert snap["level"] == 2
    c = configparser.ConfigParser()
    c.read(hero_ini, encoding="utf-8")
    assert c.get(campaign._id(), "hero_raynor_xp") == "450"


def test_clear_hero_snapshot(hero_ini):
    campaign = _FakeCampaign()
    save_hero_snapshot(campaign, _FakeUnit(), "raynor")
    clear_hero_snapshot(campaign, "raynor")
    assert load_hero_snapshot(campaign, "raynor") is None


def test_carryover_modes_default_both_enabled():
    from pathlib import Path

    from soundrts.definitions import _get_base_classes, rules

    text = (
        Path(__file__).resolve().parents[2]
        / "res"
        / "single"
        / "The Legend of Raynor"
        / "rules.txt"
    ).read_text(encoding="utf-8")
    rules.load(text, base_classes=_get_base_classes())
    stats, inv = carryover_modes_for_id("raynor")
    assert stats is True
    assert inv is True


def test_carryover_modes_can_disable_inventory():
    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        "def hero_a\nclass soldier\ncampaign_carryover 1\ncampaign_carryover_inventory 0\n",
        base_classes=_get_base_classes(),
    )
    stats, inv = carryover_modes_for_id("hero_a")
    assert stats is True
    assert inv is False


def test_save_skips_inventory_when_disabled(hero_ini):
    from soundrts.definitions import _get_base_classes, rules

    rules.load(
        "def hero_b\nclass soldier\ncampaign_carryover 1\ncampaign_carryover_stats 0\n",
        base_classes=_get_base_classes(),
    )
    campaign = _FakeCampaign()
    unit = _FakeUnit()
    unit.type_name = "hero_b"
    unit.inventory = [type("Item", (), {"type_name": "potion"})()]
    save_hero_snapshot(campaign, unit, "hero_b")
    snap = load_hero_snapshot(campaign, "hero_b")
    assert snap is not None
    assert snap["inventory"] == ["potion"]
    c = configparser.ConfigParser()
    c.read(hero_ini, encoding="utf-8")
    assert not c.has_option(campaign._id(), "hero_hero_b_xp")
    assert c.get(campaign._id(), "hero_hero_b_inventory") == "potion"
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Fake(TriggersMixin):
        def __init__(self):
            self.resources = [0, 0, 0]
            self.is_playing = True

    p = _Fake()
    p.lang_grant_resources(["500", "resource1", "100", "resource2"])
    assert p.resources[0] >= 500
    assert p.resources[1] >= 100
