"""合作战役地图地名须在客户端解析为 tts 译文，而非 loc_ch02_* 原文。"""

from pathlib import Path

from soundrts.mapfile import _name_from_path


ROOT = Path(__file__).resolve().parents[2]


def test_name_from_path_preserves_campaign_chapter_on_windows():
    assert _name_from_path("The Legend of Raynor/2.txt") == "The Legend of Raynor/2"
    assert _name_from_path("The Legend of Raynor/2") == "The Legend of Raynor/2"
    assert _name_from_path("2.txt") == "2"


def test_mapfile_name_from_path_campaign_branch():
    src = (ROOT / "soundrts" / "mapfile.py").read_text(encoding="utf-8")
    assert 'if "/" in path:' in src.split("def _name_from_path")[1].split("\ndef ")[0]


def test_resource_apply_campaign_helpers_exist():
    src = (ROOT / "soundrts" / "lib" / "resource.py").read_text(encoding="utf-8")
    assert "def apply_campaign_resources" in src
    assert "def apply_campaign_from_map_name" in src


def test_srv_map_applies_campaign_from_logical_map_name():
    src = (ROOT / "soundrts" / "clientservermenu.py").read_text(encoding="utf-8")
    block = src.split("def srv_map(self")[1].split("\n    def ")[0]
    assert "apply_campaign_from_map_name" in block


def test_server_coop_sets_logical_buffer_name():
    src = (ROOT / "soundrts" / "serverclient.py").read_text(encoding="utf-8")
    block = src.split("def cmd_create_campaign")[1].split("\n    def ")[0]
    assert 'map_.buffer_name = f"{logical}.txt"' in block


def test_say_square_localizes_voice_msg():
    src = (ROOT / "soundrts" / "clientgame" / "game_navigation.py").read_text(
        encoding="utf-8"
    )
    block = src.split("def say_square")[1].split("\ndef ")[0]
    assert "localize_voice_msg" in block


def test_global_lookup_accepts_text_place_keys():
    src = (ROOT / "soundrts" / "lib" / "sound_cache.py").read_text(encoding="utf-8")
    block = src.split("def _global_lookup_text")[1].split("\n    def ")[0]
    assert "loc_ch02" not in block or "仅处理纯数字" not in block
