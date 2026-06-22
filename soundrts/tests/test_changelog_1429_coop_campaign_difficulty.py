"""审计：1.4.2.9 — 合作战役改造为帝国时代决定版风格（难度选择）。

更新承诺：
- 合作战役创建流程新增 5 档难度（简单/标准/中等/困难/极难），越难敌人越强。
- 敌人强度随参战玩家人数提升（与决定版一致：人多→敌人更猛）。
- 难度系数全程整数运算、由服务器一次性算定后分发，保证 lockstep 同步：
  对局、旁观、回放三条"重建世界"的路径都套用相同的敌人 hp%/伤害%。
- 敌方（非人类、非中立）单位生成时按 hp% 缩放生命；结算其输出伤害时按 伤害% 缩放。
  玩家自身输出不受影响。
"""
from __future__ import annotations

from pathlib import Path

from soundrts import coop_difficulty as cd


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 难度数据源：等级表 + 玩家人数缩放（整数、确定性）
# ---------------------------------------------------------------------------


def test_difficulty_levels_are_five_de_style_tiers():
    assert cd.LEVELS == (
        cd.EASY, cd.STANDARD, cd.MODERATE, cd.HARD, cd.EXTREME
    )
    assert cd.DEFAULT_LEVEL == cd.STANDARD


def test_standard_single_player_is_unchanged_baseline():
    """标准难度 + 单人 = 敌人 100%/100%（不改变原版关卡平衡）。"""
    assert cd.factors(cd.STANDARD, 1) == (100, 100)


def test_harder_levels_strengthen_enemies_monotonically():
    hp_seq = [cd.factors(lvl, 1)[0] for lvl in cd.LEVELS]
    dmg_seq = [cd.factors(lvl, 1)[1] for lvl in cd.LEVELS]
    assert hp_seq == sorted(hp_seq)
    assert dmg_seq == sorted(dmg_seq)
    # 简单档低于标准，极难档高于标准
    assert cd.factors(cd.EASY, 1)[0] < 100 < cd.factors(cd.EXTREME, 1)[0]


def test_more_players_scale_enemies_up():
    """决定版风格：人越多敌人越强。"""
    one = cd.factors(cd.HARD, 1)
    three = cd.factors(cd.HARD, 3)
    assert three[0] > one[0]
    assert three[1] > one[1]
    # 单人乘子为 100，3 人为 100 + 2*PER_EXTRA_PLAYER_BONUS
    assert cd.player_count_multiplier(1) == 100
    assert cd.player_count_multiplier(3) == 100 + 2 * cd.PER_EXTRA_PLAYER_BONUS


def test_factors_are_integers_for_determinism():
    for lvl in cd.LEVELS:
        for n in (1, 2, 3, 4, 8):
            hp, dmg = cd.factors(lvl, n)
            assert isinstance(hp, int) and isinstance(dmg, int)
            assert hp >= 1 and dmg >= 1


def test_normalize_level_falls_back_to_standard():
    assert cd.normalize_level("HARD") == cd.HARD
    assert cd.normalize_level(" extreme ") == cd.EXTREME
    assert cd.normalize_level("nonsense") == cd.STANDARD
    assert cd.normalize_level(None) == cd.STANDARD


# ---------------------------------------------------------------------------
# 客户端菜单：难度被插入到 章节 -> 难度 -> 速度 流程，并以带标记 token 下发
# ---------------------------------------------------------------------------


def test_menu_inserts_difficulty_step_and_sends_tagged_token():
    src = _source("soundrts", "clientservermenu.py")
    assert "_select_difficulty" in src
    # 章节选择跳转到难度选择
    assert "_select_difficulty(_c, _ch)" in src
    # 难度作为带标记 token 追加（避免与可含空格的战役名冲突）
    assert 'cmd += f" difficulty={normalize_level(difficulty)}"' in src


def test_coop_campaign_has_no_treaty_step_and_offers_room_visibility():
    """合作战役不应有条约；选完速度后选择私人/公开房间再 create_campaign（treaty 固定 0）。"""
    src = _source("soundrts", "clientservermenu.py")
    assert "_select_treaty" not in src
    assert "_send_with_treaty" not in src
    assert "_select_visibility" in src
    assert "mp.COOP_PUBLIC_ROOM" in src
    compact = " ".join(src.split())
    assert '"public", "0", difficulty' in compact


def test_client_receives_coop_difficulty_before_start():
    src = _source("soundrts", "clientservermenu.py")
    assert "def srv_coop_difficulty(self, args):" in src
    # start_game 时把收到的百分比塞进 game
    assert "game.enemy_hp_factor = int(getattr(self, \"_coop_enemy_hp\", 100)" in src
    assert "game.enemy_damage_factor = int(getattr(self, \"_coop_enemy_damage\", 100)" in src


# ---------------------------------------------------------------------------
# 服务器：解析难度 token，开局算定百分比（含人数缩放）并先于 start_game 下发
# ---------------------------------------------------------------------------


def test_server_parses_difficulty_token():
    src = _source("soundrts", "serverclient.py")
    assert 'if t.startswith("difficulty="):' in src
    assert "coop_difficulty=coop_difficulty" in src


def test_server_computes_and_sends_difficulty_before_start_game():
    src = _source("soundrts", "serverroom.py")
    # 用 factors() 按人数算定
    assert "from .coop_difficulty import factors" in src
    compact = " ".join(src.split())
    assert "= factors( coop_difficulty, len(self.human_players) )" in compact
    # coop_difficulty 行在 start_game notify 之前
    i_diff = src.index('"coop_difficulty"')
    i_start = src.index('"start_game"')
    assert i_diff < i_start, "coop_difficulty 必须在 start_game 之前下发"


# ---------------------------------------------------------------------------
# 世界应用：敌方单位 hp/伤害缩放，玩家不受影响
# ---------------------------------------------------------------------------


def test_world_has_difficulty_factor_defaults():
    src = _source("soundrts", "world", "world_core.py")
    assert "enemy_hp_factor = 100" in src
    assert "enemy_damage_factor = 100" in src


def test_creature_scales_enemy_hp_on_spawn():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "_apply_coop_difficulty_hp" in src
    assert "self.hp_max = max(1, int(self.hp_max) * factor // 100)" in src
    # 只对敌方（非人类、非中立）生效
    assert "_is_coop_difficulty_enemy" in src


def test_damage_scaled_for_enemy_attackers_only():
    src = _source("soundrts", "combat", "damage_effects.py")
    assert "_scale_coop_difficulty_damage" in src
    assert "return actual_damage * factor // 100" in src
    # 攻击者为人类/中立时不缩放
    assert 'getattr(p, "is_human", False) or getattr(p, "neutral", False)' in src


# ---------------------------------------------------------------------------
# 确定性：旁观与回放两条重建路径也携带难度
# ---------------------------------------------------------------------------


def test_spectate_carries_difficulty():
    src = _source("soundrts", "serverroom.py")
    s = src.index('"start_spectating"')
    block = src[s:s + 600]
    assert '_coop_enemy_hp' in block and '_coop_enemy_damage' in block
    client_src = _source("soundrts", "clientservermenu.py")
    assert "game.enemy_hp_factor = enemy_hp" in client_src


def test_replay_seed_line_carries_difficulty_backward_compatibly():
    src = _source("soundrts", "game.py")
    # 写：seed 行可选追加两个百分比
    assert 'self.replay_write(f"{self.seed} {ehp} {edmg}")' in src
    # 读：按空格切分，缺省向后兼容
    assert "seed_parts = self.replay_read().split()" in src
    assert "self.seed = int(seed_parts[0])" in src


# ---------------------------------------------------------------------------
# TTS / 消息常量
# ---------------------------------------------------------------------------


def test_difficulty_msgparts_constants_exist():
    from soundrts import msgparts as mp

    assert mp.DIFFICULTY == [5193]
    assert mp.DIFFICULTY_EASY == [5205]
    assert mp.DIFFICULTY_EXTREME == [5206]


def test_difficulty_tts_entries_present_in_both_languages():
    for rel in (("res", "ui", "tts.txt"), ("res", "ui-zh", "tts.txt")):
        txt = _source(*rel)
        for tid in (5193, 5194, 5195, 5196, 5205, 5206):
            assert f"\n{tid} " in ("\n" + txt), f"{rel} missing tts {tid}"
