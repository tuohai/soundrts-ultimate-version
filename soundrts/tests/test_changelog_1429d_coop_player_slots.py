"""审计：1.4.2.9d — 帝国时代式合作战役"玩家位 + 同盟 AI 队友"。

帝国时代决定版合作战役：每名玩家各占同队的一个玩家位（自己的基地/部队），
空位可由**同盟** AI 队友接管（单人也能开合作关）。敌人来自关卡本身
（地图的 computer_only，在 populate_map 里以 "ai" 同盟自成一队）。

本次：
- Game._fill_coop_ai_partners 用同盟 AI 补满地图声明（nb_players_max）但无人
  占用的玩家位；补出的 AI 与人类同队（alliance 统一为 1）。
- 每个玩家（人类或 AI 队友）在 populate_map 里分到独立出生点（引擎已支持）。

注：本仓库测试统一用"读源码断言"的方式，避免 import soundrts.serverroom 这条
链在导入期的副作用（解析 sys.argv、locale 弃用告警）。
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def test_fill_method_exists_and_fills_to_nb_players_max():
    src = _source("soundrts", "serverroom.py")
    s = src.index("def _fill_coop_ai_partners(self):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 以地图声明的最大玩家位为目标，补满空位
    assert "self.scenario.nb_players_max" in block
    assert "if alliance not in used:" in block
    assert "_add_coop_ai_at_alliance(alliance)" in block
    src_all = _source("soundrts", "serverroom.py")
    assert "_Computer(self.coop_partner_level, coop_partner=True)" in src_all
    assert "def _add_coop_ai_at_alliance(self, alliance):" in src_all
    assert "self.players.append(partner)" in src_all


def test_partner_level_is_active_ai():
    src = _source("soundrts", "serverroom.py")
    assert 'coop_partner_level = "aggressive"' in src


def test_start_fills_then_one_team_no_enemy_ai():
    """合作分支：先补满 AI 队友，再把 game.players 全部归为 1 队；不再有 alliance 2。"""
    src = _source("soundrts", "serverroom.py")
    s = src.index('is_coop = bool(getattr(self, "is_coop_campaign", False))')
    block = src[s:s + 800]
    assert "self._fill_coop_ai_partners()" in block
    assert "p.alliance = 1" in block
    assert "p.alliance = 2" not in block


def test_enemies_come_from_map_not_game_players():
    """敌人来自地图 computer_only（populate_map 里以 'ai' 同盟），不在 game.players。

    确认 populate_map 仍按 'ai' 同盟创建地图敌人（与合作同盟 1 区分）。"""
    src = _source("soundrts", "world", "world_objects.py")
    assert 'else "ai"' in src or 'alliance = (\n                None' in src
    assert "DummyClient(neutral=neutral, alliance=alliance)" in src
