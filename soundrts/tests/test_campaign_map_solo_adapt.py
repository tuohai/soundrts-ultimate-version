"""单人战役加载共用 N.txt 时剥离合作向地图强化。"""
from __future__ import annotations

import pytest

from soundrts.campaign import Campaign
from soundrts.campaign_map_mode import adapt_definition_for_solo, map_for_solo_campaign
from soundrts.coop_difficulty import MODERATE
from soundrts.lib.resource import res

pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::ResourceWarning"),
]

RAYNOR = "The Legend of Raynor"


def _raynor():
    for c in res.campaigns():
        if c.name == RAYNOR:
            return c
    pytest.skip(f"{RAYNOR} not in resources")


def test_chapter1_solo_adapt_removes_coop_player_and_deintensifies_enemies():
    campaign = _raynor()
    raw = campaign.chapter(1).map.definition
    solo = adapt_definition_for_solo(raw)
    assert "nb_players_max 2" not in solo
    assert solo.count("player ") == 1
    assert "trigger player2 (" not in solo
    assert "computer_only 0 0 a5 footman c5 2 footman c3 footman" in solo


def test_map_for_solo_campaign_returns_adapted_copy():
    campaign = _raynor()
    chapter_map = campaign.chapter(1).map
    solo_map = map_for_solo_campaign(chapter_map)
    assert solo_map is not chapter_map
    assert solo_map.definition != chapter_map.definition
    assert solo_map.nb_players_max == 1


def test_coop_difficulty_defaults_to_moderate_independent_of_solo(tmp_path, monkeypatch):
    ini_path = tmp_path / "campaigns.ini"
    monkeypatch.setattr("soundrts.campaign.CAMPAIGNS_CONFIG_PATH", str(ini_path))

    from soundrts.campaign import Campaign, MissionChapter
    from soundrts.lib.package import resource_layer

    class FakeMap:
        title = ["title", 9999]

    campaign = Campaign.__new__(Campaign)
    campaign.name = "Raynor"
    campaign.resources = resource_layer("", "Raynor")
    campaign.chapters = [MissionChapter(campaign, 1, FakeMap())]

    campaign.set_difficulty("easy")
    assert campaign.get_difficulty() == "easy"
    assert campaign.get_coop_difficulty() == MODERATE

    campaign.set_coop_difficulty("hard")
    assert campaign.get_coop_difficulty() == "hard"
    assert campaign.get_difficulty() == "easy"
