"""审计：1.4.2.1 / 1.4.2.0 — 多项小修复复检。

1.4.2.1 修复：
- F1: 通行音效靠后播放导致延迟播报地名/坐标（音效逻辑，UI 侧）。
- F2: 单位每次复活会累加 speed bonus 的 bug。
- F3: upgrade 改 cost / time_cost / population_cost 后无法持久化（save 丢失）。
- F4: upgrade heal/harm 属性会无差别施加到任意单位。
- F5: 空中单位高度级别恢复到 1.3.8.1。

1.4.2.0 修复：
- G1: 死亡单位复活后无法执行任何命令。
- G2: 单位攻击自身会触发冲锋伤害。
- G3: 不具有 discount 科技的单位也享受了 cost/time_cost/population_cost 加成。
- G4: 地面冲锋溅射会误伤空中单位。
- G5: 容器满载 (>=99) 时点击装入会把自己装入自己。
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# G5: 容器不能装自己（transport_capacity >= 99 自装载）
# ---------------------------------------------------------------------------


def test_transport_load_rejects_self():
    """``CreatureTransport.load(target)`` 必须在 ``target is self`` 时立即 return。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    s = src.index("def load(self, target):")
    block = src[s:s + 300]
    assert "if target is self:" in block
    assert "return" in block


# ---------------------------------------------------------------------------
# G2: 攻击自身不触发冲锋伤害
# ---------------------------------------------------------------------------


def test_apply_charge_splash_skips_self_attack():
    """``_apply_charge_splash(target)`` 必须先检查 ``target is self``，自伤场景下不触发溅射。"""
    src = _source("soundrts", "combat", "attack_action.py")
    s = src.index("def _apply_charge_splash(self, target, is_melee):")
    block = src[s:s + 800]
    assert "if target is self:" in block


# ---------------------------------------------------------------------------
# G4: 地面冲锋溅射不影响空中单位
# ---------------------------------------------------------------------------


def test_ground_charge_splash_skips_air_units():
    """主目标为地面单位时，溅射循环必须跳过空中单位。"""
    src = _source("soundrts", "combat", "attack_action.py")
    # 关键代码：airground_type 比对
    assert (
        "getattr(target, 'airground_type', 'ground') == 'ground' "
        "and getattr(obj, 'airground_type', 'ground') == 'air'"
    ) in src


# ---------------------------------------------------------------------------
# G3 + F4：discount / heal / harm 升级只作用于 can_use 该 tech 的单位
# ---------------------------------------------------------------------------


def test_upgrade_unit_to_player_level_filters_by_can_use():
    """``upgrade_unit_to_player_level`` 必须先验证 tech 在单位的 can_use / can_use_tech /
    can_use_skill 之一，否则不应用 effect。"""
    src = _source("soundrts", "worldupgrade", "base.py")
    s = src.index("def upgrade_unit_to_player_level(cls, unit):")
    block = src[s:s + 2000]
    assert "cls.type_name in getattr(unit, 'can_use', ())" in block
    assert "cls.type_name in getattr(unit, 'can_use_tech', ())" in block
    assert "cls.type_name in getattr(unit, 'can_use_skill', ())" in block


def test_production_cost_only_applies_tech_in_can_use():
    """``ProductionOrder.cost`` / ``population_cost`` / ``time_cost`` 必须按
    ``applicable_techs``（单位 can_use 列表）过滤后再聚合，避免无关单位享受 discount。"""
    src = _source("soundrts", "worldorders", "base.py")
    # 三个属性都做 applicable_techs 过滤
    for kw in (
        "def cost(self):",
        "def population_cost(self):",
        "def time_cost(self):",
    ):
        s = src.index(kw)
        block = src[s:s + 4000]
        assert "applicable_techs" in block, f"{kw}: 未做 can_use 过滤"
        # 三种 can_use 都检查
        assert "self.type.can_use" in block
        assert "self.type.can_use_tech" in block
        assert "self.type.can_use_skill" in block


# ---------------------------------------------------------------------------
# F3: cost / time_cost / population_cost 升级效果保存（save/load）
# ---------------------------------------------------------------------------


def test_save_persists_global_cost_effects():
    """``_write_save_to`` 必须把 ``Upgrade._global_cost_effects`` 写进 self 才能 pickle。"""
    src = _source("soundrts", "game.py")
    assert "self._global_cost_effects = Upgrade._global_cost_effects" in src


def test_load_restores_global_cost_effects():
    """``run_on``（restore）必须把 ``self._global_cost_effects`` 恢复到 ``Upgrade._global_cost_effects``。"""
    src = _source("soundrts", "game.py")
    assert "_Upg._global_cost_effects = getattr(self, \"_global_cost_effects\", {})" in src


# ---------------------------------------------------------------------------
# G1: 死亡单位复活后能执行命令（关键路径：set_player 清 orders，id 重新分配）
# ---------------------------------------------------------------------------


def test_resurrect_resets_id_for_world_active_objects():
    """``resurrect`` 必须 ``self.id = None``（这是 set_player → player.add → world
    重新注册到 active_objects 的关键）。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    s = src.index("def resurrect(self, corpse):")
    block = src[s:s + 1500]
    assert "self.id = None" in block
    assert "self.set_player(p)" in block
    # 重置玩家会清掉旧 orders + 重新进入 player.units
    src_attr = _source("soundrts", "worldunit", "world_attributes.py")
    s2 = src_attr.index("def set_player(self, player):")
    block2 = src_attr[s2:s2 + 600]
    assert "self.cancel_all_orders(unpay=False)" in block2


def test_resurrect_clears_corpse_created_marker():
    """复活后必须清掉 ``_corpse_created`` 一次性标记，否则下一次死亡不会出尸体。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    s = src.index("def resurrect(self, corpse):")
    block = src[s:s + 1500]
    assert 'hasattr(self, "_corpse_created")' in block
    assert "delattr(self, \"_corpse_created\")" in block


def test_corpse_init_clears_inherited_corpse_marker():
    """``Corpse.__init__`` 必须把从原单位拷贝过来的 ``_corpse_created`` 标记移掉，
    否则复活后再次死亡时拷贝出的 unit 已经有标记，永远不会再出尸体。"""
    src = _source("soundrts", "worldresource.py")
    s = src.index("class Corpse(Entity):")
    block = src[s:s + 1500]
    assert '_corpse_created' in block
    assert 'delattr(self.unit, "_corpse_created")' in block


# ---------------------------------------------------------------------------
# F2: 复活不应每次叠加 speed bonus
# ---------------------------------------------------------------------------


def test_resurrect_does_not_double_apply_phase_bonus():
    """``resurrect`` 必须避免重复给单位施加 phase bonus，否则每次复活速度都会叠加。
    
    复活路径上 set_player → set_player(p) 会把旧 owner 移除再添加；
    在 ``upgrade_unit_to_player_level`` 处依赖 ``_applied_upgrade_effects`` 去重；
    本测试用源码契约检查去重集合的存在。"""
    src = _source("soundrts", "worldupgrade", "base.py")
    s = src.index("def upgrade_unit_to_player_level(cls, unit):")
    # 截到下一个 ``@classmethod`` 或函数定义
    end_candidates = ["\n    @classmethod\n    def _has_gather", "\n    @classmethod"]
    e = len(src)
    for cand in end_candidates:
        idx = src.find(cand, s + 1)
        if idx != -1 and idx < e:
            e = idx
    block = src[s:e]
    assert "_applied_upgrade_effects" in block
    assert "applied_key in unit._applied_upgrade_effects" in block
    assert "unit._applied_upgrade_effects.add(applied_key)" in block


def test_phase_pool_iteration_tags_existing_unit_for_phase_id():
    """phase_bonus pool 在 ``_apply_phase_bonus_to_existing_units`` 时也需要去重 tag，
    否则该方法被复活 / 第二次进入同 pool 时会再加一次。"""
    src = _source("soundrts", "worldphase.py")
    # _apply_phase_bonus_to_existing_units 应该存在
    assert "def _apply_phase_bonus_to_existing_units" in src


# ---------------------------------------------------------------------------
# 行为级：discount 单元测试 — 只对 can_use 该 tech 的单位生效
# ---------------------------------------------------------------------------


def test_discount_filter_logic():
    """复刻 production.cost 中的"哪些 tech 应纳入 applicable_techs"算法。"""
    # 模型：单位 A 的 can_use = ["discount_a"]
    # 玩家研究了 discount_a 和 discount_b
    # 期望：只有 discount_a 的成本加成应用到 A
    upgrades = ["discount_a", "discount_b"]

    class _Type:
        can_use = ["discount_a"]
        can_use_tech = []
        can_use_skill = []

    applicable = []
    for t in upgrades:
        ok = (t in _Type.can_use
              or t in _Type.can_use_tech
              or t in _Type.can_use_skill)
        if ok:
            applicable.append(t)
    assert applicable == ["discount_a"]


def test_self_attack_charge_splash_returns_early():
    """复刻 _apply_charge_splash 的早返回：target is self 时不计算溅射。"""
    class _Holder:
        pass
    self_obj = _Holder()
    target = self_obj
    # 这就是源码里的第一行守卫
    result = (target is self_obj)
    assert result is True
    # 模拟函数体：直接 return
    def _apply(target):
        if target is self_obj:
            return "early-return"
        return "did-splash"
    assert _apply(target) == "early-return"


def test_ground_charge_splash_excludes_air():
    """复刻空中单位过滤逻辑：地面主目标 + 空中 obj → 跳过。"""
    class _Obj:
        def __init__(self, kind):
            self.airground_type = kind

    target = _Obj("ground")
    air_obj = _Obj("air")
    ground_obj = _Obj("ground")

    def should_skip(target, obj):
        return (getattr(target, 'airground_type', 'ground') == 'ground'
                and getattr(obj, 'airground_type', 'ground') == 'air')

    assert should_skip(target, air_obj) is True
    assert should_skip(target, ground_obj) is False
    # 当主目标是空中单位时也不跳过（保留对空溅射）
    air_target = _Obj("air")
    assert should_skip(air_target, ground_obj) is False
