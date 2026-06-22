"""合作战役与单人共用 ``N.txt``；``campaign.txt`` 声明合作章节。"""
from __future__ import annotations

from pathlib import Path

import pytest

from soundrts.campaign import Campaign, ensure_chapter_map, parse_chapter_spec
from soundrts.lib.resource import res

RAYNOR = "The Legend of Raynor"
ROOT = Path(__file__).resolve().parents[2]


def _raynor_campaign() -> Campaign:
    for c in res.campaigns():
        if c.name == RAYNOR:
            return c
    pytest.skip(f"{RAYNOR} not in resources")


def test_parse_chapter_spec_ranges_and_lists():
    assert parse_chapter_spec("1-29") == frozenset(range(1, 30))
    assert parse_chapter_spec("0 1 2") == frozenset({0, 1, 2})
    assert parse_chapter_spec("1-29 0") == frozenset(range(0, 30))


def test_no_coop_txt_files_in_raynor():
    coop_files = list(
        (ROOT / "res" / "single" / RAYNOR).glob("*.coop.txt")
    )
    assert coop_files == []


def test_raynor_campaign_txt_coop_metadata():
    campaign = _raynor_campaign()
    assert campaign.coop_campaign is True
    assert 0 in campaign.coop_intro
    assert campaign.coop_missions == frozenset(range(1, 30))


def test_chapter_1_map_has_two_player_slots():
    campaign = _raynor_campaign()
    chapter = campaign.chapter(1)
    mission_map = ensure_chapter_map(chapter)
    assert mission_map.nb_players_max == 2
    assert "random_starts 0" in mission_map.definition
    assert "nb_columns 5" in mission_map.definition
    assert "trigger player2 (building_lost 2 townhall)" not in mission_map.definition
    assert "trigger player2 (building_lost 1 townhall)" in mission_map.definition
    assert "player 8 16" in mission_map.definition
    assert " e1 townhall 2 peasant footman d1 house footman" in mission_map.definition
    assert "west_east_paths" in mission_map.definition and " e1" in mission_map.definition
    assert "goldmines 44 e1" in mission_map.definition


def test_coop_chapter_1_player2_townhall_not_lost_at_start():
    """player2 的 building_lost 序号必须是 1（该玩家名下第 1 个 townhall），不能误写成 2。"""
    from soundrts.tests.test_map_select_loss_triggers import _StubUnit, _make_owner

    owner = _make_owner()
    th = _StubUnit(owner, type_name="townhall", unit_id="th1", provides_survival=True)
    th.map_select_global_index = 1
    assert owner.lang_building_lost(["1", "townhall"]) is False
    assert owner.lang_building_lost(["2", "townhall"]) is True


def test_chapter_29_is_random_map_with_two_players():
    campaign = _raynor_campaign()
    chapter = campaign.chapter(29)
    mission_map = ensure_chapter_map(chapter)
    assert mission_map.nb_players_max == 2
    assert "trigger player2" in mission_map.definition


def test_server_create_campaign_uses_ensure_chapter_map():
    src = (ROOT / "soundrts" / "serverclient.py").read_text(encoding="utf-8")
    block = src.split("def cmd_create_campaign")[1].split("\n    def ")[0]
    assert "ensure_chapter_map" in block
    assert "load_coop_chapter_map" not in block


def test_raynor_supports_coop_and_other_campaigns_may_not():
    from soundrts.campaign import CutSceneChapter

    raynor = next(c for c in res.campaigns() if c.name == RAYNOR)
    assert raynor.supports_coop()
    assert len(raynor.coop_mission_chapters()) == 29
    menu_chapters = raynor.coop_menu_chapters()
    assert len(menu_chapters) == 30
    assert isinstance(menu_chapters[0], CutSceneChapter)
    assert menu_chapters[0].number == 0
    coop_names = {c.name for c in res.coop_campaigns()}
    assert RAYNOR in coop_names
    assert len(coop_names) >= 1
    assert len(res.coop_campaigns()) <= len(res.campaigns())
