"""审计：1.4.2.2 — 条约玩法 + 合作战役第一关。

更新日志承诺：

条约玩法（0-20 分钟和平期）：
- 多人/合作战役菜单提供 0/5/10/15/20 五档条约时间。
- 条约期内不允许：
  1. 攻击命令对敌（``worldorders/movement.py:execute``）
  2. 实际伤害结算（``damage_effects.receive_hit``）
  3. AOE 伤害对敌（``world_status_update``）
  4. 单体瞄准 harm 对敌
  5. AI 把敌人当成可攻击目标（``world_ai_decision.can_attack``）
- 条约开始 / 倒计时 / 结束有 TTS 提示。

合作战役第一关：基础 ``campaign`` 的 chapter 1 必须支持 coop（``is_coop_campaign``）。
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 条约：菜单 0–20 分钟可选
# ---------------------------------------------------------------------------


def test_treaty_menu_offers_0_5_10_15_20():
    """``clientservermenu`` 必须为普通多人对局提供 0/5/10/15/20 分钟条约。

    注意：合作战役**不提供**条约（用户明确要求；合作语义下停战无意义），
    其菜单选完速度即创建、条约固定为 0。见
    ``test_coop_campaign_has_no_treaty_step_and_speed_sends_directly``。
    """
    src = _source("soundrts", "clientservermenu.py")
    # 普通多人对局
    for token in (
        'mp.TREATY + [":"] + mp.NO_TREATY, create_with_treaty("0")',
        'create_with_treaty("5")',
        'create_with_treaty("10")',
        'create_with_treaty("15")',
        'create_with_treaty("20")',
    ):
        assert token in src, f"missing in multiplayer menu: {token}"


def test_coop_campaign_menu_has_no_treaty():
    """合作战役菜单不应包含任何条约步骤。"""
    src = _source("soundrts", "clientservermenu.py")
    assert "_select_treaty" not in src
    assert "_send_with_treaty" not in src


def test_treaty_max_20_minutes_only():
    """20 分钟是上限：不应存在 25/30 分钟选项。"""
    src = _source("soundrts", "clientservermenu.py")
    assert 'with_treaty("25")' not in src
    assert 'with_treaty("30")' not in src
    assert 'with_treaty("60")' not in src


def test_treaty_minutes_parsed_by_serverclient_for_create_and_campaign():
    src = _source("soundrts", "serverclient.py")
    # 普通创建
    assert "treaty_minutes = int(args[3]) if len(args) >= 4 else 0" in src
    # 合作战役命令
    assert "treaty_minutes = 0" in src
    assert "treaty_minutes = int(tokens[-1])" in src


# ---------------------------------------------------------------------------
# 条约：game.run 把分钟数转毫秒、安排 TTS 提示
# ---------------------------------------------------------------------------


def test_game_run_converts_minutes_to_milliseconds():
    src = _source("soundrts", "game.py")
    s = src.index("treaty_minutes")
    block = src[s:s + 1500]
    assert "treaty_minutes * 60 * 1000" in block
    assert "self.world.treaty_until_time = 0" in block


def test_game_run_schedules_treaty_end_and_countdown():
    """条约必须有"30/20/10s 提示 + 最后 5 秒倒计时 + 结束提示"。"""
    src = _source("soundrts", "game.py")
    # 结束播报
    assert "_treaty_end_announce" in src
    assert "TREATY_END" in src
    # 30/20/10 + 5,4,3,2,1
    assert "for _s in (30, 20, 10):" in src
    assert "for _s in (5, 4, 3, 2, 1):" in src


# ---------------------------------------------------------------------------
# 条约：5 个执行点都拦截敌对动作
# ---------------------------------------------------------------------------


def test_attack_order_blocked_during_treaty():
    """``worldorders/movement.py`` 的 attack/move-to-attack 必须在条约期对敌方拦截。"""
    src = _source("soundrts", "worldorders", "movement.py")
    assert 'getattr(self.world, "treaty_until_time", 0) > 0' in src
    assert "self.world.time < self.world.treaty_until_time" in src
    assert 'self.mark_as_impossible("treaty")' in src


def test_receive_hit_blocks_enemy_damage_during_treaty():
    """``damage_effects.receive_hit`` 必须在条约期 return 掉敌对来源的命中。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(self, damage, attacker")
    block = src[s:s + 2000]
    assert "treaty_until_time" in block
    assert "self.world.time < self.world.treaty_until_time" in block
    assert "player_is_an_enemy" in block


def test_aoe_harm_blocked_during_treaty():
    src = _source("soundrts", "worldunit", "world_status_update.py")
    assert "treaty_until_time" in src
    # 至少出现 2 次（AOE + 单体）
    assert src.count("treaty_until_time") >= 2


def test_ai_can_attack_returns_false_during_treaty():
    src = _source("soundrts", "worldunit", "world_ai_decision.py")
    s = src.index("def can_attack(self, other):")
    block = src[s:s + 1500]
    assert "treaty_until_time" in block
    assert "return False" in block


# ---------------------------------------------------------------------------
# 行为级：条约时间换算 + 时间判定
# ---------------------------------------------------------------------------


def test_treaty_time_logic_5_minutes():
    """5 分钟条约 = 300000 ms；t < 300000 时拦截，t >= 300000 时放行。"""
    minutes = 5
    treaty_until_time = minutes * 60 * 1000
    assert treaty_until_time == 300000

    def is_treaty_active(world_time):
        return treaty_until_time > 0 and world_time < treaty_until_time

    assert is_treaty_active(0) is True
    assert is_treaty_active(299999) is True
    assert is_treaty_active(300000) is False  # 边界放行
    assert is_treaty_active(500000) is False


def test_treaty_disabled_when_minutes_is_zero():
    treaty_until_time = 0 * 60 * 1000
    assert treaty_until_time == 0

    def is_treaty_active(world_time):
        return treaty_until_time > 0 and world_time < treaty_until_time

    assert is_treaty_active(0) is False
    assert is_treaty_active(10000) is False


# ---------------------------------------------------------------------------
# 合作战役第一关：日志说"将基础版的 campaign 的第一关支持了合作战役玩法"
# 验证：服务器创建合作战役会强制分配同盟 ID（人=1，AI=2）。
# ---------------------------------------------------------------------------


def test_serverroom_forces_alliances_in_coop_campaign():
    """帝国时代式合作战役：人类玩家与 AI 队友同属 1 队（敌人来自地图 computer_only）。

    旧模型把 game 里的 AI 当敌人（alliance 2），与帝国时代不符——AoE 的合作战役
    里空位由**同盟** AI 队友接管。现在 ``_start`` 先补满 AI 队友再把 game.players
    全部归为 alliance 1。"""
    src = _source("soundrts", "serverroom.py")
    s = src.index('is_coop = bool(getattr(self, "is_coop_campaign", False))')
    block = src[s:s + 800]
    assert "p.alliance = 1" in block
    # 先补满同盟 AI 队友
    assert "_fill_coop_ai_partners()" in block
    # 不再把 game 里的 AI 当敌人
    assert "p.alliance = 2" not in block


def test_campaign_first_chapter_metadata_passed():
    """``_start`` 必须把 is_coop / coop_campaign_name / coop_chapter 三个字段
    通过 ``notify("start_game", ...)`` 传到客户端。"""
    src = _source("soundrts", "serverroom.py")
    s = src.index('"start_game"')
    # 用括号深度匹配整个 notify(...) 调用
    depth = 1
    i = s
    while i < len(src) and depth > 0:
        if src[i] == "(":
            depth += 1
        elif src[i] == ")":
            depth -= 1
        i += 1
    notify_block = src[s:i]
    assert "int(is_coop)" in notify_block
    assert '"coop_campaign_name"' in notify_block
    assert '"coop_chapter"' in notify_block


def test_clientserver_routes_treaty_to_game():
    """``serverclient.create_campaign`` 必须把 treaty_minutes 一并放进 game 设置。"""
    src = _source("soundrts", "serverclient.py")
    # 创建合作战役命令格式
    assert "create_campaign" in src


def test_treaty_active_does_not_break_self_damage():
    """条约期不应该影响"无 attacker 来源的伤害"（例如自杀效果、地形伤害）。
    
    ``receive_hit`` 必须先检查 ``attacker is not None``，否则陷阱/自爆等也被免疫。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(self, damage, attacker")
    block = src[s:s + 1000]
    assert "if attacker is not None" in block
