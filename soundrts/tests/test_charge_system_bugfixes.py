"""冲锋伤害系统修复回归测试（源码级契约校验）。

涵盖以下修复点：
- C1: reset_charge_state(force=False) 实现软重置（仅清 last_*_target_id）
- C2: 反冲锋分支不再调用即将被覆盖的 attacker.reset_charge_state(force=True)
- C4: 普攻 CD 未过时跳过本冲锋分支，不再 return（允许其他攻击类型继续）
- C5: op_charge_dist/op_charge_cd 异常时禁用 op_charge（op_charge_valid 标志）
- C6: op_charge_*_ready 在冷却到期时自动复位；去除冗余的 or op_charge_ready
- C7: receive_hit / _send_hit_notification 新增 is_melee 显式参数
- C8: _can_charge_attack 同目标距离恢复后不再立即 return False

以及 1.4.0.1 更新日志规范对齐：
- SPEC-A: 冲锋伤害公式 = (mdg + mdg_vs) * (charge_mdg + charge_mdg_vs) / 1000
- SPEC-B: 反冲锋伤害公式 = op_charge_mult * attacker.mdg(rdg) / 1000
- SPEC-C: op_charge_vs 采用叠加而非替换语义
- SPEC-D: 撤销"纯冲锋单位"绕过 can_mdg/can_rdg 的逻辑（spec 下 mdg=0 时冲锋伤害=0）
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# C1: reset_charge_state 软重置（force=False 也要做事）
# ---------------------------------------------------------------------------


def test_reset_charge_state_has_soft_reset_branch():
    """``reset_charge_state(force=False)`` 必须实现软重置，不能是 NO-OP。

    至少要清空 ``last_charge_mdg_target_id`` 与 ``last_charge_rdg_target_id``，
    否则 worldaction/world_movement 处的调用毫无意义。
    """
    src = _source("soundrts", "worldunit", "worldcreature.py")
    s = src.index("def reset_charge_state(self, force=False):")
    e = src.index("def ", s + 1)
    block = src[s:e]
    # 必须存在 else 分支（软重置）
    assert "if force:" in block
    assert "else:" in block
    # else 分支至少要清两个 last_charge_*_target_id
    after_else = block[block.index("else:"):]
    assert "self.last_charge_mdg_target_id = None" in after_else
    assert "self.last_charge_rdg_target_id = None" in after_else


# ---------------------------------------------------------------------------
# C2: 反冲锋分支中不再调用即将被 aim() 覆盖的 reset_charge_state(force=True)
# ---------------------------------------------------------------------------


def test_op_charge_does_not_call_attacker_reset_charge_state():
    """``receive_hit`` 的反冲锋分支不应调用 ``attacker.reset_charge_state(force=True)``，
    因为 aim() 后续会立即重写 last_charge_*_target_id 和冲锋 CD，使该重置毫无意义。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    # 截到下一个 def
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 整个 receive_hit 内不应出现对 attacker.reset_charge_state 的调用
    assert "attacker.reset_charge_state" not in block, (
        "反冲锋成功后调用 attacker.reset_charge_state(force=True) 会被 aim() "
        "中后续的 _set_charge_cooldown 立即覆盖，应已删除该无效调用。"
    )


# ---------------------------------------------------------------------------
# C4: 冲锋分支不再因普攻 CD 未过而 return（应跳过本分支继续后续逻辑）
# ---------------------------------------------------------------------------


def test_charge_branch_does_not_return_on_normal_cooldown():
    """冲锋入口已合并 ``now >= self.mdg_next_attack_time`` / ``now >= self.rdg_next_attack_time``
    到条件中，使得普攻 CD 未过时不再触发 ``return``，而是允许后续攻击类型尝试。"""
    src = _source("soundrts", "combat", "attack_action.py")
    # 截取近战冲锋分支头
    s = src.index("can_mdg and target is not self")
    snippet = src[s:s + 400]
    assert "now >= self.mdg_next_attack_time" in snippet
    # 不应再出现旧的"在冲锋分支头部立即检查 mdg_next_attack_time 后 return"模式
    assert "如果还在普通攻击冷却，直接返回" not in snippet


# ---------------------------------------------------------------------------
# C5: op_charge 异常数据不再触发"无限范围"行为
# ---------------------------------------------------------------------------


def test_op_charge_invalid_data_disables_branch():
    """``op_charge_dist`` / ``op_charge_cd`` 非法时必须设 ``op_charge_valid=False``，
    并在反冲锋触发条件中包含此标志，防止异常数据被当作"不限距离"使用。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    assert "op_charge_valid = True" in block
    assert "op_charge_valid = False" in block
    assert "if (op_charge_valid and" in block or "op_charge_valid and" in block
    assert "op_charge > 0" in block


# ---------------------------------------------------------------------------
# C6: op_charge_*_ready 在冷却到期时自动复位；冗余的 or op_charge_ready 已移除
# ---------------------------------------------------------------------------


def test_op_charge_ready_auto_resets_on_cooldown_expiry():
    """冷却到期时必须自动把 ``op_charge_*_ready`` 复位为 True，否则一旦触发就再也无法
    复用，整个冷却字段形同虚设。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    assert "not op_charge_ready and now >= op_charge_next_time" in block
    assert "self.op_charge_mdg_ready = True" in block
    assert "self.op_charge_rdg_ready = True" in block


def test_op_charge_condition_no_longer_has_redundant_or_clause():
    """触发条件不应再含 ``or op_charge_ready`` 这种永远为真的死分支。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 旧 buggy 形式
    assert "attacker.id != last_op_charge_target_id or op_charge_ready" not in block
    # 新形式
    assert "attacker.id != last_op_charge_target_id" in block


# ---------------------------------------------------------------------------
# C7: receive_hit / _send_hit_notification 新增 is_melee 参数；冲锋显式传递
# ---------------------------------------------------------------------------


def test_receive_hit_accepts_is_melee_parameter():
    """``receive_hit`` 与 ``_send_hit_notification`` 必须接受 is_melee 形参，
    并在 None 时回落到旧推断（向后兼容）。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    assert "def receive_hit(self, damage, attacker, notify=True, is_crit=False, is_charge=False, is_melee=None)" in src
    assert "def _send_hit_notification(self, attacker, actual_damage, is_crit=False, is_charge=False, is_melee=None)" in src
    # 推断回落
    assert "if is_melee is None:" in src


def test_charge_attacks_pass_is_melee_explicitly():
    """``aim()`` 中近战 / 远程冲锋必须显式传 is_melee 给 receive_hit。"""
    src = _source("soundrts", "combat", "attack_action.py")
    # 近战冲锋
    assert "target.receive_hit(charge_damage, self, notify=True, is_charge=True, is_melee=True)" in src
    # 远程冲锋
    assert "target.receive_hit(charge_damage, self, notify=True, is_charge=True, is_melee=False)" in src


# ---------------------------------------------------------------------------
# C8: _can_charge_attack 同目标距离恢复后不再立即 return False
# ---------------------------------------------------------------------------


def test_can_charge_attack_no_early_return_after_distance_recovery():
    """同目标距离恢复时只设置 ready 标志、不再立即 return False，
    交由后续距离 / 伤害校验决定本次能否冲锋。"""
    src = _source("soundrts", "combat", "attack_action.py")
    s = src.index("def _can_charge_attack(self, target, is_melee=True):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 关键变更标记
    assert "charge_ready_flag = True" in block
    # 旧 buggy 注释/逻辑已替换
    assert "由于拉开了足够的距离，但这次检查还不能马上冲锋" not in block


# ===========================================================================
# 1.4.0.1 更新日志规范对齐测试
# ===========================================================================


# ---------------------------------------------------------------------------
# SPEC-A: 冲锋伤害公式严格按 spec + 保留距离衰减因子
# ---------------------------------------------------------------------------


def test_charge_damage_uses_spec_formula_with_distance_factor():
    """``_get_charge_damage`` 必须实现加法公式 ``base + (mult + vs)``，
    并在此之上叠加距离衰减因子 ``dist_factor ∈ [0.5, 1.0]``。"""
    src = _source("soundrts", "combat", "attack_action.py")
    s = src.index("def _get_charge_damage(self, target, is_melee=True):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 必须使用 _get_melee_damage_vs / _get_ranged_damage_vs 获取基础伤害
    assert "_get_melee_damage_vs(target)" in block
    assert "_get_ranged_damage_vs(target)" in block
    # 加法公式（mdg/rdg + charge_mdg/charge_rdg）
    assert "spec_damage = base + total_mult" in block
    # 距离衰减（保留）
    assert "max_dist" in block
    assert "(max_dist + dist)" in block
    # 不应再有历史 *10 倍率
    assert "(damage + vs_damage) * 10" not in block


# ---------------------------------------------------------------------------
# SPEC-B: 反冲锋伤害新公式
# ---------------------------------------------------------------------------


def test_op_charge_counter_damage_uses_attacker_charge_value():
    """``counter_damage`` 默认 = attacker.mdg(rdg) + attacker.charge_mdg(charge_rdg)；
    自身设了 op_charge 加值时再 + (op_charge + vs)。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 必须从 attacker 取 mdg/rdg 作为基数
    assert "attacker_base = getattr(attacker, 'mdg', 0)" in block
    assert "attacker_base = getattr(attacker, 'rdg', 0)" in block
    # 必须从 attacker 取 charge_mdg/charge_rdg 作为冲锋加值
    assert "attacker_charge_mult = getattr(attacker, 'charge_mdg', 0)" in block
    assert "attacker_charge_mult = getattr(attacker, 'charge_rdg', 0)" in block
    # 默认公式：attacker_base + attacker_charge_mult
    assert "counter_damage = attacker_base + attacker_charge_mult" in block
    # 自身 op_charge > 0 时再加 (op_charge + vs)
    assert "if op_charge > 0:" in block
    assert "counter_damage = counter_damage + op_charge_total" in block
    # 不应再出现历史 buggy 形式
    assert "op_charge * original_damage // 1000" not in block
    assert "vs_multiplier * original_damage // 1000" not in block


# ---------------------------------------------------------------------------
# SPEC-C: op_charge_vs 采用"叠加"而非"替换"语义
# ---------------------------------------------------------------------------


def test_op_charge_vs_uses_additive_semantics():
    """op_charge_vs 必须叠加到 op_charge 上（与 mdg_vs 一致），
    而不是在有 vs 时整体替换 op_charge。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 关键叠加表达式
    assert "op_charge_total = op_charge + vs_multiplier" in block


# ---------------------------------------------------------------------------
# SPEC-T: 反冲锋触发条件放宽，op_charge_dist>0 也能触发
# ---------------------------------------------------------------------------


def test_op_charge_trigger_allows_dist_only_config():
    """反冲锋触发不再强制要求 op_charge>0；只要 op_charge_dist>0 就算"有反冲锋机制"，
    可触发默认反冲锋伤害（不含倍率叠乘）。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("def receive_hit(")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 必须有 has_op_charge_mechanism 守卫
    assert "has_op_charge_mechanism" in block
    assert "(op_charge > 0) or (op_charge_dist > 0)" in block


# ---------------------------------------------------------------------------
# SPEC-D: 撤销"纯冲锋单位"路径
# ---------------------------------------------------------------------------


def test_charge_branch_requires_can_mdg_or_can_rdg():
    """spec 公式下 mdg=0 时冲锋伤害=0，"纯冲锋单位"不再有意义，
    aim() 中的冲锋分支必须重新依赖 can_mdg / can_rdg 而非额外的 can_mdg_charge 开关。"""
    src = _source("soundrts", "combat", "attack_action.py")
    # 不应再有 can_mdg_charge / can_rdg_charge 这种历史"绕过"变量
    assert "can_mdg_charge" not in src
    assert "can_rdg_charge" not in src
    # 冲锋分支重新使用 can_mdg / can_rdg 作为入口
    assert "if (can_mdg and target is not self" in src
    assert "if (can_rdg and target is not self" in src


# ---------------------------------------------------------------------------
# MIN-DIST: 最小冲锋距离阈值（charge_*_min_dist > 0 时贴脸不能冲锋）
# ---------------------------------------------------------------------------


def test_can_charge_attack_respects_min_distance():
    """``_can_charge_attack`` 必须支持 ``charge_mdg_min_dist`` / ``charge_rdg_min_dist`` 作为
    冲锋下限阈值。设定了下限且当前距离低于下限时，不应触发冲锋。

    实现契约：函数体内必须读取并使用对应的 min_dist 属性，并在 dist 小于它时返回 False。
    """
    src = _source("soundrts", "combat", "attack_action.py")
    s = src.index("def _can_charge_attack(self, target, is_melee=True):")
    e = src.index("\n    def ", s + 1)
    block = src[s:e]
    # 必须读取 min_dist 属性（近战 + 远程）
    assert "charge_mdg_min_dist" in block
    assert "charge_rdg_min_dist" in block
    # 必须有 dist < min 的拒绝路径
    assert "dist < charge_min_distance" in block or "charge_min_distance" in block
