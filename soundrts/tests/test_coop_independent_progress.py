"""合作战役进度与单人战役进度独立持久化。"""
from __future__ import annotations

import configparser
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.filterwarnings("ignore::DeprecationWarning"),
    pytest.mark.filterwarnings("ignore::ResourceWarning"),
]


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2]
        .joinpath(*path_parts)
        .read_text(encoding="utf-8")
    )


def test_campaign_has_independent_coop_progress_api():
    src = _source("soundrts", "campaign.py")
    assert "def _get_coop_bookmark(self):" in src
    assert "def _set_coop_bookmark(self, number):" in src
    assert "def coop_mission_chapters(self):" in src
    assert "def coop_menu_chapters(self):" in src
    assert "def run_for_coop(self):" in src
    assert "def unlock_next_coop(self, chapter):" in src
    assert "def get_coop_difficulty(self):" in src
    assert "def set_coop_difficulty(self, level):" in src
    assert '"coop_chapter"' in src
    assert '"coop_difficulty"' in src


def test_coop_menu_uses_coop_bookmark_not_single_player():
    src = _source("soundrts", "clientservermenu.py")
    s = src.index("def _coop_campaign_menu(self):")
    block = src[s : s + 4500]
    assert "res.coop_campaigns()" in block
    assert "campaign.coop_menu_chapters()" in block
    assert "run_for_coop" in block
    assert "_run_coop_cutscene" in block
    assert "campaign.coop_mission_chapters()" not in block.split("_select_chapter")[1].split("def _on_coop")[0]
    assert "campaign._get_coop_bookmark()" in block
    assert "mp.MISSION_LOCKED" in block
    assert "campaign.get_coop_difficulty()" in block
    assert "campaign.set_coop_difficulty(difficulty)" in block
    assert "campaign._available_chapters()" not in block
    assert "res.campaigns()" not in block.split("def _coop_campaign_menu")[1].split("def ")[0]


def test_coop_victory_unlocks_coop_bookmark_only():
    src = _source("soundrts", "game.py")
    assert "unlock_next_coop" in src
    assert "campaign._set_bookmark(next_ch.number)" not in src.split("def post_run(self):")[1]


@pytest.fixture
def campaigns_ini(tmp_path, monkeypatch):
    ini_path = tmp_path / "campaigns.ini"
    monkeypatch.setattr("soundrts.campaign.CAMPAIGNS_CONFIG_PATH", str(ini_path))
    return ini_path


def _make_campaign(name="Test Campaign"):
    from soundrts.campaign import Campaign, MissionChapter
    from soundrts.lib.package import resource_layer

    class FakeMap:
        title = ["title", 9999]

    campaign = Campaign.__new__(Campaign)
    campaign.name = name
    campaign.resources = resource_layer("", name)
    campaign.chapters = [
        MissionChapter(campaign, 0, FakeMap()),
        MissionChapter(campaign, 1, FakeMap()),
        MissionChapter(campaign, 2, FakeMap()),
    ]
    return campaign


def test_single_and_coop_bookmarks_are_independent(campaigns_ini):
    campaign = _make_campaign("Raynor")
    section = campaign._id()

    c = campaign._read_config()
    c.set(section, "chapter", "2")
    c.set(section, "coop_chapter", "0")
    campaign._write_config(c)

    assert campaign._get_coop_bookmark() == 0
    assert len(campaign._available_coop_chapters()) == 1

    campaign.unlock_next_coop(campaign.chapters[0])

    c2 = campaign._read_config()
    assert c2.getint(section, "coop_chapter") == 1
    assert c2.getint(section, "chapter") == 2


def test_coop_difficulty_is_independent_from_single_player(campaigns_ini):
    campaign = _make_campaign("Raynor")

    campaign.set_difficulty("hard")
    campaign.set_coop_difficulty("easy")

    assert campaign.get_difficulty() == "hard"
    assert campaign.get_coop_difficulty() == "easy"


def test_coop_cutscene_unlocks_coop_bookmark_only(campaigns_ini):
    from soundrts.campaign import CutSceneChapter

    class FakeCut(CutSceneChapter):
        def __init__(self, campaign, number):
            self.campaign = campaign
            self.number = number
            self.title = [4272]
            self.sequence = [7500]
            self.path = f"{number}.txt"

        def run_for_coop(self):
            self.campaign.unlock_next_coop(self)

    campaign = _make_campaign("Raynor")
    campaign.chapters = [
        FakeCut(campaign, 0),
        campaign.chapters[1],
        campaign.chapters[2],
    ]
    assert campaign._get_coop_bookmark() == 0
    campaign.chapters[0].run_for_coop()
    assert campaign._get_coop_bookmark() == 1


def test_coop_progress_persisted_in_campaigns_ini(campaigns_ini):
    campaign = _make_campaign("Raynor")
    campaign._set_coop_bookmark(1)
    campaign.set_coop_difficulty("moderate")

    c = configparser.ConfigParser()
    with open(campaigns_ini, encoding="utf-8") as f:
        c.read_file(f)
    section = campaign._id()
    assert c.getint(section, "coop_chapter") == 1
    assert c.get(section, "coop_difficulty") == "moderate"
    assert not c.has_option(section, "chapter")
