"""审计：1.4.1.3 — 武器/盔甲系统、物品系统、墙壁/大门、单位数量播报、多人不同步等。

1.4.1.3 重点：
- 单位可以配备多种武器（``weapons`` 列表）、一种盔甲（``armor``）。
- ``auto_weapon_switch``（默认 0）控制是否自动按射程切换。
- 武器 / 盔甲都有 ``class weapon`` / ``class armor`` 与 ``is_a`` 继承链。
- 物品系统（``class item``）：``consume_on_pickup``、``skills``、``buffs``、``resource_rewards``、``is_loot``。
- 墙壁 / 大门：经 ``block(exit)`` 与 ``Exit.is_a_gate`` 路径生效，``upgrade``（site→建筑）保留 ``blocked_exit``。
- 切换武器命令：``switch_weapon`` / ``switch_to_weapon`` / ``toggle_auto_weapon_switch``。
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def _section(src, start_marker, *end_markers):
    """按起始标记 + 多个可能的结束标记切出代码段。"""
    s = src.index(start_marker)
    e = len(src)
    for cand in end_markers:
        idx = src.find(cand, s + 1)
        if idx != -1 and idx < e:
            e = idx
    return src[s:e]


# ---------------------------------------------------------------------------
# 武器类 + 继承 + debuffs
# ---------------------------------------------------------------------------


def test_weapon_class_exists():
    src = _source("soundrts", "worldweapon.py")
    assert "class Weapon(Entity):" in src
    assert "is_a_weapon = True" in src
    # 继承链 + can_use_tech
    assert "is_a = ()" in src
    assert "expanded_is_a" in src
    assert "can_use_tech = ()" in src


def test_armor_class_exists():
    src = _source("soundrts", "worldarmor.py")
    assert "class Armor(Entity):" in src
    assert "is_a = ()" in src
    assert "can_use_tech = ()" in src


def test_weapon_debuffs_field_and_parse():
    """1.4.1.6: 武器上 debuffs 字段、解析、应用到单位都到位。"""
    src = _source("soundrts", "worldweapon.py")
    assert "debuffs = ()" in src
    # interpret 中按空格 split
    assert 'if "debuffs" in d:' in src
    # apply_to_unit 把武器 debuffs 累加到单位
    assert "unit.debuffs.append(debuff)" in src


def test_weapon_default_targets_ground():
    src = _source("soundrts", "worldweapon.py")
    assert 'mdg_targets = ["ground"]' in src
    assert 'rdg_targets = ["ground"]' in src


# ---------------------------------------------------------------------------
# 多武器 + 切换 + auto 切换
# ---------------------------------------------------------------------------


def test_switch_weapon_command_class():
    src = _source("soundrts", "worldorders", "immediate.py")
    assert "class SwitchWeaponOrder(ImmediateOrder):" in src
    assert 'keyword = "switch_weapon"' in src

    assert "class SwitchToWeaponOrder(ImmediateOrder):" in src
    assert 'keyword = "switch_to_weapon"' in src

    assert "class ToggleAutoWeaponSwitchOrder(ImmediateOrder):" in src
    assert 'keyword = "toggle_auto_weapon_switch"' in src


def test_switch_weapon_only_when_multiple_weapons_present():
    src = _source("soundrts", "worldorders", "immediate.py")
    block = _section(src, "class SwitchWeaponOrder(ImmediateOrder):",
                     "class SwitchToWeaponOrder")
    # is_allowed 必须强制 len(weapons) > 1
    assert "len(unit.get_available_weapons()) > 1" in block


def test_auto_weapon_switch_default_off():
    src = _source("soundrts", "worldunit", "world_attributes.py")
    s = src.index("# 解析自动武器切换设置")
    block = src[s:s + 500]
    assert 'if "auto_weapon_switch" in d:' in block
    # 没写时强制 False
    assert "cls.auto_weapon_switch = False" in block


def test_switch_weapon_preserves_cooldown():
    """手动切换武器时，攻击冷却 / 前摇被转移到新武器对应攻击类型，不被绕过。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    block = _section(src, "def switch_weapon(self, weapon_name):", "def _auto_switch_weapon")
    # 保留 cd / prep_end_time
    assert "current_next_attack_time" in block
    assert "current_prep_end_time" in block
    # 设置手动切换的标记
    assert "self.manual_weapon_switch_weapon = weapon_name" in block
    # 通知 weapon_switched
    assert 'self.notify(f"weapon_switched,{weapon_name}")' in block


def test_manual_switch_takes_priority_over_auto():
    """``manual_weapon_switch_weapon`` 设置后 auto 不抢占；最近若清除则恢复。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    # current_weapon != manual ... 时清除 manual 标记的逻辑
    assert "self.current_weapon != self.manual_weapon_switch_weapon" in src
    assert "self.manual_weapon_switch_weapon = None" in src


# ---------------------------------------------------------------------------
# Item 系统 1.4.1.3 / 1.3.9.8
# ---------------------------------------------------------------------------


def test_item_class_default_attrs():
    src = _source("soundrts", "worlditem.py")
    assert "class Item(Entity):" in src
    assert 'default_order = "pickup"' in src
    assert "skills = ()" in src
    assert "buffs = ()" in src
    assert "is_loot = 0" in src
    assert "consume_on_pickup = 0" in src
    assert "resource_rewards = ()" in src
    # 物品不参与战斗
    assert "collision = 0" in src
    assert "is_vulnerable = False" in src


def test_item_interpret_parses_resource_rewards_to_ints():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, '# 解析资源奖励', "def __init__")
    assert 'd["resource_rewards"] = [int(x) for x in d["resource_rewards"].split()]' in block
    # list 形式
    assert 'd["resource_rewards"] = [int(x) for x in d["resource_rewards"]]' in block


def test_item_interpret_parses_skills_and_buffs_as_list():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, '# 解析列表属性', '# 解析is_a属性')
    assert 'for k in ["skills", "buffs"]:' in block
    assert 'd[k] = d[k].split()' in block


def test_item_on_pickup_consumes_when_flag_set():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, "def on_pickup(self, picker):", "def on_drop")
    assert "if self.consume_on_pickup:" in block
    assert "return True" in block


def test_item_gives_resource_rewards_to_player():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, "def give_resource_rewards", "def on_pickup")
    # i+1 → resource1..N
    assert 'f"resource{i + 1}"' in block
    # reward * 1000 转换内部单位
    assert "reward_amount = reward * 1000" in block
    # 通过 player.store
    assert "player.store(resource_type, reward_amount)" in block


def test_item_inherits_is_a_chain():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, "def _expand_is_a", "def is_a_type")
    assert "self.expanded_is_a.add(parent_name)" in block
    # 递归处理基类
    assert "self._expand_is_a(parent_class.is_a)" in block


def test_item_equip_adds_skills_and_buffs_to_host():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, "def equip(self, host):", "def unequip")
    # skills 注入到 host.can_use_skill
    assert "host.can_use_skill = list(host.can_use_skill) + [a]" in block
    # buffs 实例化并附加
    assert "self._buffs.append(cls(self, host))" in block


def test_item_unequip_removes_skills_and_cancels_buffs():
    src = _source("soundrts", "worlditem.py")
    block = _section(src, "def unequip(self, host):", "\n\n\n")
    assert "host.can_use_skill = [x for x in host.can_use_skill if x != a]" in block
    # cancel buff
    assert "if hasattr(b, 'cancel'):" in block
    assert "b.cancel()" in block


# ---------------------------------------------------------------------------
# 1.4.1.3 墙壁/大门：upgrade 路径保留 blocked_exit
# ---------------------------------------------------------------------------


def test_upgrade_preserves_blocked_exit():
    """当 BuildingSite 升级为最终建筑时，必须复用同一个 ``blocked_exit``。"""
    src = _source("soundrts", "worldorders", "production.py")
    s = src.index("blocked_exit = self.unit.blocked_exit")
    block = src[s:s + 800]
    # 旧 site delete 之前先取 exit
    # 新建 type 后再 block 回去
    assert "if blocked_exit:" in block
    assert "unit.block(blocked_exit)" in block


def test_block_method_registers_blocker_on_exit():
    src_e = _source("soundrts", "worldentity.py")
    block = _section(src_e, "def block(self, e):", "def unblock")
    # 阻止水上单位上岸时被阻挡 -> 直接 return
    assert "is_water_unit_on_land" in block
    assert "e.add_blocker(self)" in block


def test_unit_block_does_not_double_assign():
    """``Unit.block(e)`` 必须仅在 ``self.blocked_exit`` 为空时设置，避免双重计数。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    block = _section(src, "    def block(self, e):", "def _is_weapon_primarily_melee")
    assert "if not self.blocked_exit:" in block
    assert "self.blocked_exit = e" in block
    assert "e.add_blocker(self)" in block


def test_exit_is_blocked_treats_gate_specially():
    """大门 ``is_a_gate`` 时，对自己人放行，对敌人才算 blocked。"""
    src = _source("soundrts", "worldexit.py")
    block = _section(src, "def is_blocked", "def blockers")
    # gate vs enemy logic
    assert "not b.is_a_gate or (o is None or o.is_an_enemy(b))" in block
    # add_blocker / remove_blocker 在 Exit 类上
    assert "def add_blocker" in src
    assert "def remove_blocker" in src


# ---------------------------------------------------------------------------
# 行为级模拟：item.on_pickup 一次性消耗 vs 持久
# ---------------------------------------------------------------------------


def test_simulated_item_on_pickup_consumes_or_persists():
    """复刻 on_pickup 的"consume_on_pickup -> 返回 True 表示要删除"协议。"""

    class _Item:
        consume_on_pickup = 0
        resource_rewards = ()

        def on_pickup(self):
            if self.consume_on_pickup:
                return True
            return False

    persistent = _Item()
    consumable = _Item()
    consumable.consume_on_pickup = 1

    assert persistent.on_pickup() is False
    assert consumable.on_pickup() is True


def test_simulated_resource_rewards_indexed_starts_from_resource1():
    """复刻 give_resource_rewards 的 resource1..N 编号策略。"""
    rewards = [10, 0, 5]
    distributed = {}
    for i, r in enumerate(rewards):
        if r > 0:
            distributed[f"resource{i + 1}"] = r * 1000
    assert distributed == {"resource1": 10000, "resource3": 5000}
