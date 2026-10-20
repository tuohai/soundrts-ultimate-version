"""测试 Joan 战役流程：贞德在 ch4 被俘 → 进入 ch4.5 cutscene → ch5 → ch6。

不实际启动游戏引擎，模拟：
1. ch4 贞德死亡 → (campaign_defeat 8845)
2. lang_campaign_defeat 设置 has_victory=True
3. MissionGame.post_run 检测 has_victory → unlock_next
4. Campaign.next 找到下一章 (4.5 cutscene)
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

# Make sure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_campaign_chapter_order_includes_capture_cutscene():
    """4a cutscene 必须在 ch4 和 ch5 之间。"""
    from soundrts.lib.resource import res
    res.set_mods("aoe2")
    joan = [c for c in res.campaigns() if c.name == "Joan of Arc"][0]
    numbers = [ch.number for ch in joan.chapters]
    # 0, 1, 2, 3, 4, 4.5, 5, 6
    assert 4.5 in numbers, f"missing 4.5 cutscene in {numbers}"
    idx_4 = numbers.index(4)
    idx_45 = numbers.index(4.5)
    idx_5 = numbers.index(5)
    assert idx_4 < idx_45 < idx_5, f"order wrong: {numbers}"


def test_chapter4_uses_campaign_defeat_trigger():
    """ch4 必须在贞德死亡时触发 (campaign_defeat 8845)。"""
    from pathlib import Path
    text = Path("mods/aoe2/single/Joan of Arc/4.txt").read_text(encoding="utf-8")
    assert "(campaign_defeat 8845)" in text, "ch4 must trigger (campaign_defeat 8845) on Joan's death"


def test_chapter6_uses_burgundian_faction():
    """ch6 玩家必须扮演勃艮第军（攻方）。"""
    from pathlib import Path
    text = Path("mods/aoe2/single/Joan of Arc/6.txt").read_text(encoding="utf-8")
    assert "(faction burgundians)" in text, "ch6 player1 must be burgundians (attacker)"
    # 贞德不再是关键单位
    assert "key_unit_killed monk" not in text, "ch6 has no Joan (Burgundians attacking)"


def test_campaign_chapter_type_for_45():
    """4a 必须是 cutscene 章节。"""
    from soundrts.lib.resource import res
    res.set_mods("aoe2")
    joan = [c for c in res.campaigns() if c.name == "Joan of Arc"][0]
    ch_45 = [ch for ch in joan.chapters if ch.number == 4.5][0]
    assert type(ch_45).__name__ == "CutSceneChapter"


def test_campaign_defeat_then_unlocks_next():
    """模拟 ch4 贞德死亡 → has_victory=True → unlock_next → 进入 ch4.5。"""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    class _Player:
        is_human = True
        is_playing = True
        broadcasts_defeat_and_quit = False
        name = "Joan"
        id = "p1"
        units = []
        allied = None
        allied_victory = None
        has_victory = False
        has_been_defeated = False
        _stats = types.SimpleNamespace(freeze=lambda: None)

        @property
        def stats(self):
            return self._stats

        def __init__(self):
            self.allied = [self]
            self.allied_victory = [self]
            self._pending = []

        def push(self, what, payload=None):
            self._pending.append((what, payload))

    class _World:
        def __init__(self, players):
            self.players = players

    human = _Player()
    enemy = _Player()
    enemy.name = "English"
    world = _World([human, enemy])
    human.world = world
    enemy.world = world

    t = TriggersMixin.__new__(TriggersMixin)
    t.world = world
    t.allied = human.allied
    t.allied_victory = human.allied_victory
    t.push = human.push
    t.has_victory = False
    t.has_been_defeated = False

    t.lang_campaign_defeat(["8845"])

    # has_victory 应该为 True
    assert t.has_victory is True
    # enemy 应该被标记为 defeated
    assert enemy.has_been_defeated is True
    # 贞德被俘 cutscene 应该被 push
    seq_pushed = any(p[0] == "sequence" and p[1] == ["8845"] for p in human._pending)
    assert seq_pushed
    # quit 应该被 push
    quit_pushed = any(p[0] == "quit" for p in human._pending)
    assert quit_pushed
    # world 应该被标记
    assert world.campaign_defeat_pending is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
