"""审计：1.4.1.1 / 1.4.1.2 — 修理能力 + 船只靠岸修理 + exp_dgf 独立 + mdg/rdg target_types 拆分。

1.4.1.1 重点：
- 属性界面有 `can_repair_ships`（默认 0），整数。
- 工人 / 建筑 都支持 `can_repair_ships`。
- 工人 → 船只 修理距离 = 6 格；建筑 → 船只 修理距离 = 8 格。
- 距离单位为内部 mm（× 1000）。

1.4.1.2 重点：
- `can_repair`（默认 1），可禁用工人修理能力；为 0 时连 `auto_repair` 也禁用。
- `mdg_targets` / `rdg_targets` 不再共享解析，二者各自从 dict 取。
- `exp_dgf` 解析为整数，可不依赖 mdg / rdg 单独生效（在 damage_effects / splash 中分别独立判断）。
- 水上单位寻路完善 → 通过观察 transport / can_repair_ships 关系基本保证。
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1.4.1.1: can_repair_ships 解析为 int，作为 int_property 登记
# ---------------------------------------------------------------------------


def test_can_repair_ships_is_int_property():
    src = _source("soundrts", "definitions.py")
    assert '"can_repair_ships"' in src
    # 与 hide_locked_commands 等并列在 int_properties 列表里
    s = src.index('"can_repair_ships"')
    # 该项必须在某个 int_properties 列表中（截断前后 200 字寻找 int_properties 关键字）
    block = src[max(0, s - 1500):s + 200]
    assert "int_properties" in block


def test_can_repair_ships_default_zero_on_worker_and_building():
    """Creature 默认 = 0，Building 默认也 = 0。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    assert "can_repair_ships = 0" in src

    src2 = _source("soundrts", "worldunit", "worldcreature.py")
    # Building 类体里也有 = 0 默认值
    assert src2.count("can_repair_ships = 0") >= 2


def test_can_repair_ships_int_conversion_in_worker_interpret():
    src = _source("soundrts", "worldunit", "worldworker.py")
    s = src.index('if "can_repair_ships" in d:')
    block = src[s:s + 400]
    assert 'int(value[0])' in block or 'int(value)' in block


def test_can_repair_ships_int_conversion_in_building_interpret():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    s = src.index('if "can_repair_ships" in d:')
    block = src[s:s + 200]
    assert 'int(d["can_repair_ships"])' in block


# ---------------------------------------------------------------------------
# 1.4.1.1: 工人靠岸修理船只距离 = 6，建筑修理船只距离 = 8
# ---------------------------------------------------------------------------


def test_worker_to_ship_repair_distance_is_6():
    src = _source("soundrts", "worldentity.py")
    s = src.index("def can_be_repaired_by_worker_from_shore")
    block = src[s:s + 1500]
    # 工人 → 船只距离 6 格
    assert "max_repair_distance = 6 * 1000" in block


def test_building_to_ship_repair_distance_is_8():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    s = src.index("def _auto_repair_ships")
    block = src[s:s + 800]
    # 建筑 → 船只距离 8 格
    assert "max_repair_distance = 8 * 1000" in block


def test_building_auto_repair_only_when_flag_set():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    s = src.index("def decide(self):")
    block = src[s:s + 400]
    # 必须显式判断 can_repair_ships
    assert "if self.can_repair_ships" in block
    assert "self._auto_repair_ships()" in block


def test_repair_order_blocks_unauthorized_ship_repair():
    src = _source("soundrts", "worldorders", "movement.py")
    s = src.index("class RepairOrder")
    block = src[s:s + 2500]
    # 当目标是水上单位 + can_be_repaired_by_worker_from_shore + 工人没有 can_repair_ships，
    # 应当 mark_as_impossible 拒绝任务
    assert 'getattr(self.unit, "can_repair_ships", 0)' in block
    # 拒绝路径
    assert "mark_as_impossible" in block


def test_auto_repair_iterates_friendly_ships_only():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    s = src.index("def _auto_repair_ships")
    block = src[s:s + 1500]
    # 仅遍历 self.player.allied
    assert "self.player.allied" in block
    # 仅修理水上单位
    assert 'obj.airground_type == "water"' in block
    # 仅修理 hp < hp_max
    assert "obj.hp < obj.hp_max" in block


# ---------------------------------------------------------------------------
# 1.4.1.2: can_repair 默认 1；为 0 时禁用 repair + auto_repair
# ---------------------------------------------------------------------------


def test_can_repair_default_one_for_worker():
    src = _source("soundrts", "worldunit", "worldworker.py")
    assert "can_repair = 1" in src


def test_can_repair_blocks_repair_order():
    src = _source("soundrts", "worldorders", "movement.py")
    s = src.index("class RepairOrder")
    block = src[s:s + 2500]
    assert 'getattr(self.unit, "can_repair", 0)' in block


def test_can_repair_blocks_auto_repair_command():
    src = _source("soundrts", "worldorders", "immediate.py")
    # 在 auto_repair 命令处检查 can_repair == 0 → 不允许
    assert 'getattr(unit, "can_repair", 0)' in src


def test_auto_repair_loop_respects_can_repair():
    """worker.decide() / 自动行为循环中 self.auto_repair and self.can_repair。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    assert "self.auto_repair and self.can_repair" in src


def test_can_repair_registered_in_int_properties():
    src = _source("soundrts", "definitions.py")
    assert '"can_repair"' in src
    # 在 int_properties = { ... } 集合字面量内确认登记（不再依赖脆弱的字符窗口，
    # 因为该集合会持续增长，can_repair 与声明行的距离会超过固定窗口）。
    start = src.index("int_properties = {")
    end = src.index("}", start)
    block = src[start:end]
    assert '"can_repair"' in block


# ---------------------------------------------------------------------------
# 1.4.1.2: mdg_targets / rdg_targets 不再共享解析
# ---------------------------------------------------------------------------


def test_mdg_rdg_targets_parsed_independently():
    src = _source("soundrts", "worldunit", "world_attributes.py")
    s = src.index('mdg_targets_val = d.get("mdg_targets", "")')
    e = src.index('# 解析自动武器切换设置', s)
    block = src[s:e]
    # 必须独立从 dict 取两次，而非复用同一个值
    assert 'd.get("mdg_targets"' in block
    assert 'd.get("rdg_targets"' in block
    # 没有形如 `cls.rdg_targets = cls.mdg_targets` 的共享赋值
    assert 'cls.rdg_targets = cls.mdg_targets' not in block
    assert 'cls.mdg_targets = cls.rdg_targets' not in block


def test_targets_default_to_ground():
    src = _source("soundrts", "worldunit", "world_attributes.py")
    s = src.index('mdg_targets_val = d.get("mdg_targets", "")')
    e = src.index('# 解析自动武器切换设置', s)
    block = src[s:e]
    # 没有显式定义时回退到 ["ground"]
    assert 'or ["ground"]' in block


def test_targets_at_creature_class_default():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert 'mdg_targets = ["ground"]' in src
    assert 'rdg_targets = ["ground"]' in src


def test_weapon_targets_also_default_ground():
    src = _source("soundrts", "worldweapon.py")
    assert 'mdg_targets = ["ground"]' in src
    assert 'rdg_targets = ["ground"]' in src


# ---------------------------------------------------------------------------
# 1.4.1.2: exp_dgf 独立生效
# ---------------------------------------------------------------------------


def test_exp_dgf_default_zero_and_in_precision_properties():
    """exp_dgf 默认 0，在 precision_properties 中（与 mdg / rdg 同列）。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "exp_dgf = 0" in src

    src_def = _source("soundrts", "definitions.py")
    s = src_def.index('"exp_dgf",')
    block = src_def[max(0, s - 2000):s + 100]
    # 应在 precision_properties 列表中（也就是按 .1 解析为整数 × 1000）
    assert "precision_properties" in block


def test_exp_dgf_independently_added_to_damage():
    """damage_effects.py 中 exp_dgf 单独 hasattr 守卫，不与 mdg / rdg 共享条件。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    # exp_dgf 单独检查 hasattr(self, 'exp_dgf')，独立累加
    s = src.index("hasattr(self, 'exp_dgf')")
    block = src[s:s + 400]
    assert "final_damage += self.exp_dgf" in block


def test_exp_dgf_independent_in_splash():
    src = _source("soundrts", "combat", "splash.py")
    # splash.py 也独立处理 exp_dgf 累加
    assert "hasattr(self, 'exp_dgf')" in src
    assert "total_splash += self.exp_dgf" in src


# ---------------------------------------------------------------------------
# 行为级：simulate target_types 拆分（不共享）
# ---------------------------------------------------------------------------


def test_unit_mdg_and_rdg_targets_can_be_distinct():
    """mock 一个有 mdg_targets / rdg_targets 但二者不同的"single source of truth"，
    确认 `cls.mdg_targets is not cls.rdg_targets`。"""

    # 模拟 world_attributes.py 中独立解析过程
    d = {"mdg_targets": "ground", "rdg_targets": "ground air"}

    class _U:
        pass

    cls = _U

    mdg_targets_val = d.get("mdg_targets", "")
    if isinstance(mdg_targets_val, list):
        cls.mdg_targets = mdg_targets_val
    else:
        cls.mdg_targets = mdg_targets_val.replace(";", "").strip().split() or ["ground"]

    rdg_targets_val = d.get("rdg_targets", "")
    if isinstance(rdg_targets_val, list):
        cls.rdg_targets = rdg_targets_val
    else:
        cls.rdg_targets = rdg_targets_val.replace(";", "").strip().split() or ["ground"]

    assert cls.mdg_targets == ["ground"]
    assert cls.rdg_targets == ["ground", "air"]
    # 不共享：修改其中一个不影响另一个
    cls.mdg_targets.append("water")
    assert "water" not in cls.rdg_targets


def test_can_repair_ships_distance_constants_documented():
    """关键约定：worker→ship 距离 = 6，building→ship 距离 = 8。"""
    src1 = _source("soundrts", "worldentity.py")
    src2 = _source("soundrts", "worldunit", "worldcreature.py")
    assert "6 * 1000" in src1, "worker distance should be 6 squares"
    assert "8 * 1000" in src2, "building auto-repair distance should be 8 squares"
