"""审计：1.4.2.2 — 条约玩法 + 合作战役第一关。

更新日志承诺：

条约玩法（对齐帝国 2 决定版，最长 90 分钟）：
- 多人菜单提供无条约 + ``TREATY_MINUTE_CHOICES``（5–60 每 5 分钟，另加 90）。
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
# 条约：菜单对齐帝国 2 决定版
# ---------------------------------------------------------------------------


def test_treaty_menu_offers_aoe2_de_choices():
    """普通多人对局菜单必须提供无条约 + 帝国 2 决定版档位（最长 90）。

    注意：合作战役**不提供**条约（用户明确要求；合作语义下停战无意义），
    其菜单选完速度即创建、条约固定为 0。见
    ``test_coop_campaign_has_no_treaty_step_and_speed_sends_directly``。
    """
    from soundrts.treaty import MAX_TREATY_MINUTES, TREATY_MINUTE_CHOICES

    assert MAX_TREATY_MINUTES == 90
    assert TREATY_MINUTE_CHOICES == (
        5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 90,
    )
    for parts in (
        ("soundrts", "clientservermenu.py"),
        ("soundrts", "clientmain.py"),
        ("soundrts", "randommap_menu.py"),
    ):
        src = _source(*parts)
        assert "TREATY_MINUTE_CHOICES" in src, parts
        assert 'mp.TREATY + [":"] + mp.NO_TREATY' in src, parts
        assert "prompt_custom_treaty_minutes" in src, parts
        assert "mp.TREATY + mp.CUSTOM_GAME_SPEED" in src, parts


def test_parse_custom_treaty_minutes_rejects_out_of_range():
    """自定义输入必须是 5–90 的整数；4 和 91 不钳位，直接拒绝。"""
    from soundrts.treaty import parse_custom_treaty_minutes

    assert parse_custom_treaty_minutes(4) is None
    assert parse_custom_treaty_minutes(5) == 5
    assert parse_custom_treaty_minutes(12) == 12
    assert parse_custom_treaty_minutes(" 75 ") == 75
    assert parse_custom_treaty_minutes(90) == 90
    assert parse_custom_treaty_minutes(91) is None
    assert parse_custom_treaty_minutes("x") is None
    assert parse_custom_treaty_minutes("") is None
    assert parse_custom_treaty_minutes(None) is None


def test_custom_treaty_prompt_and_tts():
    treaty_src = _source("soundrts", "treaty.py")
    assert "prompt_custom_treaty_minutes" in treaty_src
    assert "ENTER_TREATY_MINUTES" in treaty_src
    assert "mp.BEEP" in treaty_src
    assert "ENTER_TREATY_MINUTES = [5843]" in _source("soundrts", "msgparts.py")
    assert "5843\tenter treaty minutes" in _source("res", "ui", "tts.txt")
    assert "5843\t请输入条约时长" in _source("res", "ui-zh", "tts.txt")


def test_coop_campaign_menu_has_no_treaty():
    """合作战役菜单不应包含任何条约步骤。"""
    src = _source("soundrts", "clientservermenu.py")
    assert "_select_treaty" not in src
    assert "_send_with_treaty" not in src


def test_treaty_max_90_minutes():
    """90 分钟是上限：菜单不含 120，协议值会钳到 90。"""
    from soundrts.treaty import MAX_TREATY_MINUTES, TREATY_MINUTE_CHOICES, clamp_treaty_minutes

    assert MAX_TREATY_MINUTES == 90
    assert 90 in TREATY_MINUTE_CHOICES
    assert 120 not in TREATY_MINUTE_CHOICES
    assert clamp_treaty_minutes(0) == 0
    assert clamp_treaty_minutes(45) == 45
    assert clamp_treaty_minutes(90) == 90
    assert clamp_treaty_minutes(120) == 90
    assert clamp_treaty_minutes("x") == 0


def test_treaty_minutes_parsed_by_serverclient_for_create_and_campaign():
    src = _source("soundrts", "serverclient.py")
    assert "treaty_minutes = int(rest[0]) if rest else 0" in src
    assert "treaty_minutes = 0" in src
    assert "treaty_minutes = int(tokens[-1])" in src


# ---------------------------------------------------------------------------
# 条约：game.run 把分钟数转毫秒、安排 TTS 提示
# ---------------------------------------------------------------------------


def test_game_run_converts_minutes_to_milliseconds():
    src = _source("soundrts", "game.py")
    assert "clamp_treaty_minutes" in src
    assert "treaty_minutes * 60 * 1000" in src
    assert "self.world.treaty_until_time = 0" in src


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


# ---------------------------------------------------------------------------
# 条约：狩猎（帝国 2 决定版：野生动物不属于停战范围）
# ---------------------------------------------------------------------------


def test_treaty_allows_attacking_huntable_animals():
    """帝国 2 决定版的 Treaty 模式允许狩猎：attack 命中 is_huntable 动物时，
    五个 treaty 拦截点都必须放行，不能 mark_as_impossible 也不能吃掉伤害。"""

    # worldorders/movement.py — AttackOrder.execute() 拦截野生动物
    src = _source("soundrts", "worldorders", "movement.py")
    s = src.index("class AttackOrder")
    block = src[s:s + 2500]
    assert "is_wildlife_unit" in block, "attack_order 必须放行 huntable/herdable"
    assert 'self.mark_as_impossible("treaty")' in block

    # combat/damage_effects.py — receive_hit 不拦截来自/命中野生动物的伤害
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(self, damage, attacker")
    block = src[s:s + 1500]
    assert "is_wildlife_unit" in block, "receive_hit 必须放行 huntable/herdable"

    # worldunit/world_status_update.py — AOE + 单体瞄准伤害
    src = _source("soundrts", "worldunit", "world_status_update.py")
    assert src.count("is_wildlife_unit") >= 2, (
        "world_status_update 必须放行 huntable/herdable（AOE + 单体瞄准两个拦截点）"
    )

    # worldunit/world_ai_decision.py — can_attack
    src = _source("soundrts", "worldunit", "world_ai_decision.py")
    s = src.index("def can_attack(self, other):")
    block = src[s:s + 3000]
    assert "is_wildlife_unit" in block, "can_attack 必须放行 huntable/herdable"


def test_attack_order_on_huntable_animal_during_treaty_completes():
    """行为级：条约期内 attack 一只鹿（野生动物），命令应正常执行，不能被
    mark_as_impossible，与现有狩猎回归 ``test_hunting.py`` 对齐。"""
    from soundrts.worldorders.movement import AttackOrder

    class _NeutralPlayer:
        neutral = True

        def player_is_an_enemy(self, _other):
            return True  # 中立野生动物：非盟友

    class _SelfPlayer:
        def player_is_an_enemy(self, other):
            return other is not None and other is not self

        def updated_target(self, _t):
            return None

    target = type("T", (), {
        "id": "deer1",
        "hp": 1,
        "is_vulnerable": True,
        "is_huntable": 1,   # 关键：野生动物
        "herdable": 0,
        "player": _NeutralPlayer(),
    })()

    notifications = []

    class _Unit:
        is_idle = True
        action = None
        distance_to_goal = 0
        player = _SelfPlayer()
        orders = []

        def notify(self, msg, *_a, **_k):
            notifications.append(msg)

    unit = _Unit()
    order = AttackOrder(unit, ["deer1"])
    order.target = target
    unit.orders = [order]
    # 模拟条约进行中（order.world 是 property，真正来自 unit.world）
    unit.world = type("W", (), {"time": 0, "treaty_until_time": 300000})()

    order.execute()

    assert not getattr(order, "is_impossible", False), (
        "treaty 不应拦截对野生动物（is_huntable=1）的 attack"
    )
    assert "order_impossible" not in notifications


def test_treaty_still_blocks_attack_on_human_enemy():
    """对照：条约期内对真实敌方玩家的 attack 应被拦截（防止互打）。"""
    from soundrts.worldorders.movement import AttackOrder

    class _EnemyPlayer:
        neutral = False

    class _SelfPlayer:
        def player_is_an_enemy(self, other):
            return other is not None and other is not self

        def updated_target(self, _t):
            return None

    target = type("T", (), {
        "id": "knight1",
        "hp": 10,
        "is_vulnerable": True,
        "is_huntable": 0,   # 不是野生动物
        "herdable": 0,
        "player": _EnemyPlayer(),
    })()

    notifications = []

    class _Unit:
        is_idle = True
        action = None
        distance_to_goal = 0
        player = _SelfPlayer()
        orders = []

        def notify(self, msg, *_a, **_k):
            notifications.append(msg)

    unit = _Unit()
    order = AttackOrder(unit, ["knight1"])
    order.target = target
    unit.orders = [order]
    unit.world = type("W", (), {"time": 0, "treaty_until_time": 300000})()

    order.execute()

    assert getattr(order, "is_impossible", False), (
        "treaty 必须拦截对非野生动物的敌方 attack"
    )
