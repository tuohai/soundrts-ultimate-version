"""审计：1.4.2.9b — 单人战役难度 + 帝国时代决定版风格任务浏览器。

更新承诺：
- 单人战役支持难度选择（持久化于战役配置），MissionChapter 运行前把敌人强度
  百分比写入会话，与合作战役共用同一套世界缩放逻辑。
- 战役菜单升级为决定版风格浏览器：可选"战役简介"、显示并可修改"难度"、
  章节标注 已完成 / 未解锁（未解锁不可选、不剧透标题）。
- 通关播报"下一关已解锁"，失败菜单提供"重新挑战本关"。
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def test_campaign_has_difficulty_persistence_api():
    src = _source("soundrts", "campaign.py")
    assert "def get_difficulty(self):" in src
    assert "def set_difficulty(self, level):" in src
    assert "def difficulty_factors(self):" in src
    # 通过战役配置持久化（复用 _read_config/_write_config）
    assert 'c.set(self._id(), "difficulty"' in src


def test_mission_chapter_applies_difficulty_to_game():
    src = _source("soundrts", "campaign.py")
    assert "self.campaign.difficulty_factors()" in src
    assert "game.enemy_hp_factor = hp" in src
    assert "game.enemy_damage_factor = dmg" in src


def test_campaign_menu_is_de_style_browser():
    src = _source("soundrts", "campaign.py")
    # 难度项与简介项
    assert "mp.DIFFICULTY + _difficulty_label(self.get_difficulty())" in src
    assert "mp.CAMPAIGN_SYNOPSIS" in src
    # 已完成 / 未解锁标记
    assert "mp.MISSION_COMPLETED" in src
    assert "mp.MISSION_LOCKED" in src
    # 难度子菜单 + 选择
    assert "def _difficulty_menu(self" in src
    assert "def _choose_difficulty(self, level):" in src


def test_synopsis_parsed_from_campaign_txt():
    src = _source("soundrts", "campaign.py")
    assert 'm = re.search("(?m)^synopsis[ \\t]+(.+)$", s)' in src
    assert "self.synopsis" in src


def test_synopsis_crlf_resolves_tts_id():
    import os
    import sys
    import warnings as _warnings

    _warnings.filterwarnings("ignore")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    _saved_argv = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        from soundrts.lib.resource import res
        from soundrts.lib.sound_cache import sounds
    finally:
        sys.argv = _saved_argv

    # Other test modules may leave the starcraft mod active in the global
    # resource manager; reset to base so the base campaign is discoverable.
    from soundrts import config

    config.mods = ""
    res.set_map()
    res.set_mods("")
    res.load_rules_and_ai()
    res.load_style()

    campaign = res.find_campaign("The Legend of Raynor")
    assert campaign is not None
    assert campaign.synopsis == [7751]

    res.set_campaign(campaign)
    sounds.load_default(res)
    text = sounds.translate_sound_number(7751)
    assert text != "7500"
    assert "Raynor" in text or "雷诺" in text or "realm" in text.lower()
    res.set_campaign()


def test_victory_defeat_feedback_uses_de_phrases():
    src = _source("soundrts", "campaign.py")
    assert "voice.important(mp.NEXT_MISSION_UNLOCKED)" in src
    assert "menu.append(mp.RETRY_THIS_MISSION, self)" in src


def test_browser_msgparts_constants_exist():
    from soundrts import msgparts as mp

    assert mp.CAMPAIGN_SYNOPSIS == [5199]
    assert mp.MISSION_LOCKED == [5197]
    assert mp.MISSION_COMPLETED == [5198]
    assert mp.NEXT_MISSION_UNLOCKED == [5203]
    assert mp.RETRY_THIS_MISSION == [5204]
