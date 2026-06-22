"""审计：1.4.2.9c — 合作战役按"帝国时代式剧情关卡"运行（而非多人遭遇战）。

帝国时代决定版的合作战役 = 多名玩家一起打同一张**剧情关卡**：
- 关卡用它自己的目标/触发器决定胜负（引擎里 default_triggers 仅在地图无触发器时
  才生效，所以战役关的自带目标本就主导胜负）；
- 开场过场、过场对白、任务目标都对所有人类玩家共享；
- 敌人随玩家人数增强（难度系统已实现）。

本次改动：
1. 合作战役世界标记 is_campaign=True（战役音乐 / 抑制 NPC 播报 / 战役语义）；
   且不设置 world.campaign，使 campaign_flag 成为确定性 no-op，避免多人不同步。
2. 合作战役开局播放关卡开场过场（world.intro），与单人一致。
3. cut_scene 过场对触发器所属玩家及其全部盟友广播（合作时人人都听到剧情）。
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def test_coop_campaign_world_marked_as_campaign():
    src = _source("soundrts", "game.py")
    s = src.index("self.world.is_campaign = (")
    block = src[s:s + 200]
    assert 'getattr(self, "is_coop_campaign", False)' in block, (
        "合作战役世界必须标记 is_campaign=True（战役语义）"
    )


def test_coop_campaign_plays_intro_on_start():
    src = _source("soundrts", "game.py")
    s = src.index("def pre_run(self):", src.index("class MultiplayerGame"))
    block = src[s:s + 600]
    assert 'getattr(self, "is_coop_campaign", False)' in block
    assert "play_sequence(self.world.intro)" in block


def test_cutscene_broadcasts_to_allies():
    """cut_scene 必须像目标播报那样对盟友广播，合作战役里人人听到剧情。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    s = src.index("def lang_cut_scene(self, args):")
    e = src.index("def _parse_objective_content", s)
    block = src[s:e]
    # 仍然推送 sequence，但通过 _emit 对 self + 盟友逐个发送
    assert 'p.push("sequence", payload)' in block
    assert 'for ally in getattr(self, "allied", [])' in block
    assert "_emit(self)" in block


def test_campaign_flag_is_noop_without_world_campaign():
    """合作战役不设置 world.campaign，campaign_flag 读到 None 返回 False（确定性）。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    s = src.index("def lang_campaign_flag(self, args):")
    block = src[s:s + 300]
    assert "campaign = self._get_campaign()" in block
    assert "if campaign is None:" in block
    assert "return False" in block
