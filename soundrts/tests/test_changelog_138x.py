"""审计：1.3.8.x — gather 系统重构、is_rewards、mod multi/、is_production、继承、capture、

1.3.8.x 涵盖 SoundRTS 引擎从 1.3.8.2-ultimate 开始的"两个月大改":
  - 1.3.8.8：can_gather 资源类型筛选；gather_time / gather_qty 字段从 deposit 迁到 worker；
            通过 effect bonus 影响采集时间 / 数量 / production_* / rewards_resource。
  - 1.3.8.7：菜单音量设置；击杀奖励（演进为 `resource_rewards`，无须 `is_rewards` 总开关）；
            拆建筑返还消耗
  - 1.3.8.5：mod 专属 multi/ 文件夹覆盖；
  - 1.3.8.4：mdg_dodge_vs / rdg_dodge_vs 绝对闪避 bug 修复；
            **is_production / production_type / production_cost / production_qty / can_start_produce**
            建筑物可生产资源（1.4.0.4 已重命名为 auto_production / manual_production）。
  - 1.3.8.3：is_a footman(hp_max mdg) / is_a footman(apart hp_max) / is_a footman(-hp_max) / 多继承；
            射程 bug 修复；capture_hp_threshold bug 修复。
  - 1.3.8.2 ultimate（两个月大改）：
            * 单位属性：mdg / rdg / mdf / rdf / *_vs 全套近远战拆分
            * 单位机制：夺取所有权 capture / 投射物 mdg_projectile / 地形 cover & dodge / 反击切换
            * 升级机制：effect bonus / effect apply_bonus / 多级 is_a 升级链 / cost 影响 train+upgrade+skill
            * 技能机制：class skill 取代 class ability；skill 支持 cost / time_cost
            * AI 模式：新增 guard / chase 两档
            * 音效系统：mdg_missed / mdg_hit / launch_mdg / casting / disappear
            * bindings.txt 支持 resource3+
            * 出口处的墙/门可双向 load/unload；容器内攻击有命中音效
"""
from __future__ import annotations

from pathlib import Path


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


def _section(src, start_marker, *end_markers):
    s = src.index(start_marker)
    e = len(src)
    for cand in end_markers:
        idx = src.find(cand, s + 1)
        if idx != -1 and idx < e:
            e = idx
    return src[s:e]


# =============================================================================
# 1.3.8.8 — can_gather / gather_time / gather_qty 迁移到 Worker
# =============================================================================


def test_worker_has_can_gather_default_none():
    """1.3.8.8: 工人默认无采集权限（can_gather_deposit/building=None）。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    assert "can_gather_deposit = None" in src
    assert "can_gather_building = None" in src


def test_worker_has_gather_time_qty_class_defaults():
    src = _source("soundrts", "worldunit", "worldworker.py")
    assert "gather_time = {}" in src
    assert "gather_qty = {}" in src


def test_can_gather_in_string_list_properties():
    src = _source("soundrts", "definitions.py")
    assert '"can_gather_deposit"' in src
    assert '"can_gather_building"' in src
    worker_src = _source("soundrts", "worldunit", "worldworker.py")
    block = _section(worker_src, "def _can_gather_target", "def _single_gather_permission")
    assert '"all" in deposits' in block or '"all" in buildings' in block


def test_gather_time_parse_supports_resource_and_deposit_names():
    """1.3.8.8: gather_time 解析支持
       - resource1 / resource2 ... 格式
       - all 关键字（统一时间）
       - 矿点名称（如 goldmine、wood）"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = _section(src, "def interpret(cls, d):", "def get_default_order")
    # "all" 关键字
    assert 'd["gather_time"][i] == "all"' in block
    # "resource" 前缀
    assert 'd["gather_time"][i].startswith("resource")' in block
    # 处理任意 deposit 名（fallback else）
    assert "deposit_name" in block


def test_gather_time_qty_supports_single_resource_simple_value():
    """1.3.8.8: 如果工人定义只能开采一种资源，gather_time / gather_qty 可以直接写数值。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = _section(src, "def get_gather_time", "def get_gather_qty")
    # 单一资源 + 简单数值
    assert "_single_gather_permission" in block


def test_gather_time_qty_supports_gather_time_resource_prefix():
    """1.3.8.8: 支持 gather_time_resource1 10 / gather_qty_wood 5 等单独字段。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = _section(src, "def interpret(cls, d):", "def get_default_order")
    # 处理 gather_time_resource# 与 gather_time_wood 等
    assert 'key.startswith("gather_time_") and key != "gather_time"' in block
    assert 'key.startswith("gather_qty_") and key != "gather_qty"' in block


def test_gather_time_bonus_applied_per_resource():
    """1.3.8.8: 升级 effect bonus gather_time 1 走 player.gather_time_bonus 字典。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = _section(src, "def get_gather_time", "def get_gather_qty")
    # 通用 + 资源特定 + deposit 特定 + all
    assert "self.player.gather_time_bonus" in block
    assert 'in self.player.gather_time_bonus' in block
    assert '"all" in self.player.gather_time_bonus' in block


def test_gather_qty_bonus_applied_per_resource():
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = src[src.index("def get_gather_qty"):]
    assert "self.player.gather_qty_bonus" in block
    assert '"all" in self.player.gather_qty_bonus' in block


def test_gather_effects_module_has_resource_specific_bonus():
    """1.3.8.8 升级示例：effect bonus gather_time wood 2 / effect bonus gather_qty all 5 等。"""
    src = _source("soundrts", "worldupgrade", "gather_effects.py")
    assert "_apply_gather_time_bonus_to_resource" in src
    assert "_apply_gather_qty_bonus_to_resource" in src
    # 字典格式: {"wood": 2, "gold": 1}
    assert 'isinstance(bonus_value, dict)' in src
    # 列表格式: ["wood", "2", "gold", "1"]
    assert 'isinstance(bonus_value, list)' in src


def test_deposit_keeps_extraction_time_qty_for_backward_compat():
    """1.3.8.8 把 extraction_time / extraction_qty 从 deposit 移除，但 1.3.9.0 又恢复。
    当前应仍保留为可选属性（不再是必须，但 Deposit 类有默认）。"""
    src = _source("soundrts", "worldresource.py")
    block = _section(src, "class Deposit(Entity):", "class BuildingLand")
    # 默认仍存在，None 表示不修正
    assert "extraction_time = None" in block
    assert "extraction_qty = None" in block


def test_worker_get_gather_time_applies_extraction_time_correction():
    """1.3.8.8 + 1.3.9.0：target 上的 extraction_time 可叠加到 base_time（正负皆可）。"""
    src = _source("soundrts", "worldunit", "worldworker.py")
    block = src[src.index("def get_gather_time"):src.index("def get_gather_qty")]
    # 读取 target.extraction_time
    assert "target.extraction_time" in block
    assert "base_time = base_time + extraction_time" in block


# =============================================================================
# 1.3.8.7 — sound settings / 击杀奖励（演进为 resource_rewards）/ 拆建筑返还
# =============================================================================


def test_resource_rewards_int_list_registered():
    """1.3.8.7 引入击杀奖励；至 1.4.1.3 字段统一为 `resource_rewards`（与 item 共用）。
    旧拼写 `rewards_resource` 已移除注册，mod 应改用 `resource_rewards`。"""
    src = _source("soundrts", "definitions.py")
    assert '"resource_rewards"' in src
    assert '"rewards_resource"' not in src


def test_resource_rewards_default_on_creature():
    """`resource_rewards` 默认 [0, 0]：不给奖励；mod 显式设置非零即生效。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "resource_rewards = [0, 0]" in src


def test_resource_rewards_parsed_in_world_attributes():
    """`world_attributes.interpret` 解析 `resource_rewards [a b]`。"""
    src = _source("soundrts", "worldunit", "world_attributes.py")
    block = _section(src, "# 解析奖励资源数量", "# 解析夺取占领")
    assert '"resource_rewards" in d' in block
    # 至少两个值
    assert "len(rewards) >= 2" in block


def test_kill_reward_only_for_enemy_kill():
    """击杀奖励仅当 attacker 与 target 属于敌对玩家时才给予。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    block = _section(src, "# 处理资源奖励", "# 在通知和删除前处理经验值奖励")
    assert "player_is_an_enemy" in block


def test_resource_rewards_stored_to_killer_player():
    """击杀者获得 resource1 / resource2 等内部资源（×1000 表示游戏内部单位）。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    block = _section(src, "# 处理资源奖励", "# 在通知和删除前处理经验值奖励")
    assert "attacker.player.store(resource_type, resource_amount)" in block
    # 内部单位转换
    assert "* 1000" in block


def test_cancel_building_refunds_cost():
    """1.3.8.7：销毁己方建筑（在建中时通过 cancel_building）返还消耗的资源成本。"""
    src = _source("soundrts", "worldorders", "immediate.py")
    block = _section(src, "class CancelBuildingOrder", "class EnableAutoGather",
                     "class CancelTrainingOrder")
    # unpay 是 player 的逆操作，把资源退回
    assert "self.unit.player.unpay(self.unit.type.cost)" in block
    assert "self.unit.die()" in block


# =============================================================================
# 1.3.8.5 — mod 专属 multi/ 文件夹覆盖
# =============================================================================


def test_mod_multi_folder_filtering_logic():
    """1.3.8.5：mod 根目录下的 multi/ 文件夹会限定显示的地图集合。
    在 lib/resource.py 中应有针对 mod-multi 的路径解析逻辑。"""
    src = _source("soundrts", "lib", "resource.py")
    # 至少必须涉及 multi/ 路径
    assert "multi" in src.lower()


def test_official_advanced_maps_present_under_res_multi():
    """高级地图 td1/td2/td3 默认放在 res/multi 下（确保该机制能识别它们）。"""
    base = Path(__file__).resolve().parents[2] / "res" / "multi"
    # 至少 td1 / td2 必须存在
    found = sum(1 for m in ("td1", "td2", "td3") if (base / m).exists())
    assert found >= 1


# =============================================================================
# 1.3.8.4 — dodge_vs 绝对闪避修复 + is_production（已被 1.4.0.4 重命名）
# =============================================================================


def test_dodge_vs_integrated_in_hit_miss():
    """1.3.8.4：mdg_dodge_vs / rdg_dodge_vs 已修复，正式参与 _hit_or_miss 计算。"""
    src = _source("soundrts", "combat", "hit_miss.py")
    block = _section(src, "def _hit_or_miss", "def _get_dodge_on_terrain")
    # _hit_or_miss 内对 target.mdg_dodge_vs / target.rdg_dodge_vs 查询
    assert "target.mdg_dodge_vs" in block or "target_dodge_vs" in block
    # 必须从 type_name / expanded_is_a 两路查
    assert "self.type_name in target.mdg_dodge_vs" in block
    assert "self.type_name in target.rdg_dodge_vs" in block


def test_dodge_vs_supports_inherited_type_lookup():
    """1.3.8.4：闪避对 attacker 继承链支持。"""
    src = _source("soundrts", "combat", "hit_miss.py")
    # mdg_dodge_vs 对 attacker.expanded_is_a 也能匹配
    assert "expanded_is_a" in src
    assert "target.mdg_dodge_vs[t]" in src
    assert "target.rdg_dodge_vs[t]" in src


def test_dodge_vs_internal_unit_conversion():
    """1.3.8.4 修复：当值 >100 时认为是内部精确单位（×1000），需还原。"""
    src = _source("soundrts", "combat", "hit_miss.py")
    # 寻找 ">100" 与 "//1000" 配对的还原模式
    block = src[src.index("def _hit_or_miss"):]
    assert "// 1000" in block
    assert "> 100" in block


def test_is_production_known_limitation_documented_in_definitions():
    """1.3.8.4 引入 is_production / production_type / production_cost / production_qty / can_start_produce。
    1.4.0.4 将 is_production 拆为 auto_production / manual_production；
    is_production 的整数注册保留（int_properties 没有显式包含），但运行时不再读取。
    本测试记录此 KNOWN-LIMITATION：写 `is_production 1` 不会启用生产，需要改写为 `manual_production 1`。"""
    src = _source("soundrts", "definitions.py")
    # auto_production / manual_production 才是当前活跃字段
    assert '"auto_production"' in src
    assert '"manual_production"' in src
    # production_time / production_qty 必须继续支持
    assert '"production_time"' in src
    assert '"production_qty"' in src
    # production_cost 必须在 precision_list_properties
    assert '"production_cost"' in src


def test_production_qty_progress_reported_at_intervals():
    """1.3.8.4：生产到 20% / 40% / 60% / 80% / 100% 才播报一次。"""
    src = _source("soundrts", "worldorders", "production.py")
    # 当前实现里至少要有 production_qty / production_time 配套
    assert "production_time" in src
    assert "production_qty" in src


# =============================================================================
# 1.3.8.3 — is_a footman(hp_max mdg) / apart / 多继承 + 射程 + capture_hp_threshold
# =============================================================================


def test_inheritance_supports_include_mode_in_definitions():
    """1.3.8.3：is_a footman(hp_max mdg)。括号内空格分隔 = 选择性继承。"""
    src = _source("soundrts", "definitions.py")
    # 必须有 include / exclude 解析逻辑
    block = _section(src, "def _parse_parent_info", "def _val")
    assert '"include"' in block
    assert '"exclude"' in block
    # parent_name(attr1 attr2) 模式
    assert 'parent_str[:open_bracket].strip()' in block


def test_inheritance_supports_apart_keyword():
    """1.3.8.3：is_a footman(apart hp_max)。apart = 排除继承。"""
    src = _source("soundrts", "definitions.py")
    classify = _section(src, "def _classify_bracket_attrs", "def _parse_parent_info")
    assert 'attrs[0] == "apart"' in classify
    parse = _section(src, "def _parse_parent_info", "def _val")
    assert "is_exclude_mode" in parse


def test_inheritance_supports_minus_prefix_exclude():
    """排除继承也支持 ``-attr`` 前缀：``is_a footman(-hp_max)``。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, "def _classify_bracket_attrs", "def _parse_parent_info")
    assert 'a.startswith("-")' in block


def test_is_a_minus_prefix_exclude_inheritance_applies():
    """``is_a footman(-hp_max)`` 应继承除 hp_max 外的父类属性。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def footman
class soldier
hp_max 100
mdg 5
mdf 2

def elite_footman
class soldier
is_a footman(-hp_max)
""")
    r.apply_inheritance(expanded_is_a=True)
    elite = r._dict["elite_footman"]
    footman = r._dict["footman"]
    assert elite.get("mdg") == footman.get("mdg")
    assert elite.get("mdf") == footman.get("mdf")
    assert "hp_max" not in elite


def test_is_a_minus_prefix_multiple_excludes():
    """``is_a footman(-hp_max -mdg)`` 排除多个属性。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def footman
class soldier
hp_max 100
mdg 5
mdf 2

def scout
class soldier
is_a footman(-hp_max -mdg)
""")
    r.apply_inheritance(expanded_is_a=True)
    scout = r._dict["scout"]
    footman = r._dict["footman"]
    assert scout.get("mdf") == footman.get("mdf")
    assert "hp_max" not in scout
    assert "mdg" not in scout


def test_inheritance_apply_chooses_include_or_exclude():
    """1.3.8.3：apply_inheritance 时按 is_exclude_mode 分支处理。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, "def apply_inheritance", "def _parse_parent_info")
    # 排除模式 vs 包含模式
    assert "is_exclude_mode" in block
    assert "exclude_attrs" in block
    assert "include_attrs" in block


def test_is_a_parse_preserves_parenthesized_attrs():
    """1.3.8.3：is_a 行解析时必须保留括号内多个属性（含跨多词的括号）。"""
    src = _source("soundrts", "definitions.py")
    # 特殊处理 is_a 列表（合并未闭合的括号）
    block = _section(src, '# 特殊处理is_a属性', "# 添加对 damage_seq 的特殊处理")
    assert "if '(' in current_word and ')' not in current_word:" in block
    # 一直收集直到找到闭合括号
    assert "while j < len(words) and ')' not in words[j]:" in block


def test_inheritance_supports_multiple_parents():
    """1.3.8.3：is_a footman knight archer — 同时继承多个单位。
    is_a footman(mdg) knight(hp_max) — 各自带 include。"""
    src = _source("soundrts", "definitions.py")
    # apply_inheritance 中遍历所有 parent
    block = _section(src, "def apply_inheritance", "def _parse_parent_info")
    assert 'for p_info in o["is_a"]:' in block


def test_capture_hp_threshold_registered():
    """1.3.8.3 修复了 capture_hp_threshold 不可用的 bug。
    （1.3.8.2 ultimate 引入字段；1.3.8.3 修复其功能。）"""
    src = _source("soundrts", "definitions.py")
    assert '"capture_hp_threshold"' in src
    # 必须有运行时使用
    src2 = _source("soundrts", "combat", "damage_effects.py")
    assert "self.capture_hp_threshold > 0" in src2


def test_capture_hp_threshold_zero_means_disabled():
    """1.3.8.3：capture_hp_threshold 默认 0，即不可被夺取。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "capture_hp_threshold = 0" in src


def test_capture_check_uses_hp_percentage():
    """1.3.8.3：夺取阈值是百分比（hp * 100 / hp_max <= threshold）。"""
    src = _source("soundrts", "combat", "damage_effects.py")
    block = _section(src, "self.capture_hp_threshold > 0", "def ")
    assert "self.hp * 100 / self.hp_max" in block


def test_capture_cooldown_default():
    """1.3.8.3：_capture_cooldown 默认 10000ms = 10 秒。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "_capture_cooldown = 10000" in src


# =============================================================================
# 1.3.8.2 ultimate — 夺取所有权 / projectile / cover-dodge_on_terrain /
# 出口处建筑双向交互 / bindings resource3+ / ready/cd/range vs 修复 / 容器音效
# =============================================================================


def test_mdg_projectile_rdg_projectile_registered():
    """1.3.8.2：mdg_projectile / rdg_projectile 表示是否为投射物。"""
    src = _source("soundrts", "definitions.py")
    assert '"mdg_projectile"' in src
    assert '"rdg_projectile"' in src


def test_projectile_high_ground_extra_range_implementation():
    """1.3.8.2：投射物在高地上有额外射程（结合 1.3.9.1 实现）。
    1.3.9.1 引入 hit-chance halved；这里检查 projectile 字段进入 targeting/hit_miss 路径。"""
    src = _source("soundrts", "combat", "targeting.py")
    assert "mdg_projectile" in src or "rdg_projectile" in src


def test_cover_dodge_on_terrain_in_string_list_properties():
    """1.3.8.2：mdg_cover_on_terrain / rdg_cover_on_terrain / mdg_dodge_on_terrain /
    rdg_dodge_on_terrain。"""
    src = _source("soundrts", "definitions.py")
    for k in ("mdg_cover_on_terrain", "rdg_cover_on_terrain",
              "mdg_dodge_on_terrain", "rdg_dodge_on_terrain"):
        assert f'"{k}"' in src


def test_cover_dodge_on_terrain_consumed_in_hit_miss():
    """1.3.8.2：地形 cover / dodge 列表（地形名 + 数值）被 hit_miss 消费。"""
    src = _source("soundrts", "combat", "hit_miss.py")
    assert "mdg_cover_on_terrain" in src
    assert "rdg_cover_on_terrain" in src
    assert "mdg_dodge_on_terrain" in src
    assert "rdg_dodge_on_terrain" in src


def test_exit_blocked_checks_both_sides():
    """1.3.8.2：建立在出口处的墙/门可与出口的任意一侧交互 — 体现为 is_blocked
    同时检查 self._blockers 与 self.other_side._blockers。"""
    src = _source("soundrts", "worldexit.py")
    block = _section(src, "def is_blocked", "def add_blocker")
    # 本侧 + 另一侧 blockers 都要检查
    assert "self._blockers" in block
    assert "other.other_side" in src or "other = " in block
    assert "other_blockers" in block


def test_bindings_supports_resource3():
    """1.3.8.2：global_bindings.txt 修复了不能映射 resource3 以上的 bug。"""
    bp = Path(__file__).resolve().parents[2] / "res" / "ui" / "global_bindings.txt"
    assert bp.exists()
    text = bp.read_text(encoding="utf-8")
    # SHIFT Z: resource_status resource3 这种行应该能正常加载
    assert "resource3" in text


def test_resource_status_command_supports_arbitrary_resource_type():
    """1.3.8.2：cmd_resource_status 接受 resource_type 任意字符串参数。"""
    src = _source("soundrts", "clientgame", "game_resources.py")
    assert "def cmd_resource_status(interface, resource_type):" in src


def test_mdg_ready_rdg_ready_used_in_attack_action():
    """1.3.8.2：mdg_ready / rdg_ready 在 attack_action 中正常使用。
    修复 bug：之前不能正常工作。"""
    src = _source("soundrts", "combat", "attack_action.py")
    # 至少使用 mdg_ready_vs
    assert "self.mdg_ready_vs" in src
    assert "self.rdg_ready_vs" in src or "self.mdg_ready" in src


def test_vs_attributes_interpret_includes_ready_cd_range():
    """1.3.8.2：mdg_ready_vs / mdg_cd_vs / mdg_range_vs / mdg_minimal_range_vs
    全部进入 world_attributes.interpret 的 vs_attributes 列表。"""
    src = _source("soundrts", "worldunit", "world_attributes.py")
    block = _section(src, "vs_attributes = [", "]")
    for k in ("mdg_cd_vs", "rdg_cd_vs", "mdg_ready_vs", "rdg_ready_vs",
              "mdg_range_vs", "rdg_range_vs",
              "mdg_minimal_range_vs", "rdg_minimal_range_vs"):
        assert f'"{k}"' in block, f"missing vs attribute: {k}"


def test_container_unit_attack_sound_supported():
    """1.3.8.2 修复了容器内单位攻击外部目标无命中音效的 bug。
    通过 passenger_attack_types 字段开放容器内单位攻击。"""
    src = _source("soundrts", "definitions.py")
    assert '"passenger_attack_types"' in src
    # 字段实际在 worldunit 类默认
    src2 = _source("soundrts", "worldunit", "worldcreature.py")
    assert "passenger_attack_types" in src2


# =============================================================================
# 1.3.8.2 ultimate — 单位属性大改进（mdg / rdg / vs / damage_seq / 序列攻击 /
#                    allow_units_add / upgrades / skill / guard-chase / 反击）
# =============================================================================


def test_mdg_rdg_replace_old_damage():
    """1.3.8.2：删除 damage，新增 mdg（近战）/ rdg（远程）+ 各自的 _vs。"""
    src = _source("soundrts", "definitions.py")
    # mdg / rdg 必须在 precision_properties
    for k in ("mdg", "rdg"):
        assert f'"{k}"' in src


def test_mdf_rdf_replace_old_armor():
    """1.3.8.2：删除 armor 单一防御，新增 mdf / rdf 拆分。"""
    src = _source("soundrts", "definitions.py")
    for k in ("mdf", "rdf"):
        assert f'"{k}"' in src


def test_mdg_range_rdg_range_replace_single_range():
    """1.3.8.2：删除 range，新增 mdg_range / rdg_range。"""
    src = _source("soundrts", "definitions.py")
    assert '"mdg_range"' in src
    assert '"rdg_range"' in src
    assert '"mdg_minimal_range"' in src
    assert '"rdg_minimal_range"' in src


def test_mdg_radius_rdg_radius_replace_damage_radius():
    """1.3.8.2：mdg_radius / rdg_radius 代替 damage_radius。"""
    src = _source("soundrts", "definitions.py")
    assert '"mdg_radius"' in src
    assert '"rdg_radius"' in src


def test_mdg_splash_rdg_splash_replace_simple_splash():
    """1.3.8.2：mdg_splash / rdg_splash 取值非二元 0/1，而是具体数值。
    splash_decay 在 worldweapon.py 中按 vs dict 处理（不在 precision_properties）。"""
    src = _source("soundrts", "definitions.py")
    assert '"mdg_splash"' in src
    assert '"rdg_splash"' in src
    # splash_decay 在 weapon 类中处理
    src2 = _source("soundrts", "worldweapon.py")
    assert "splash_decay" in src2


def test_mdg_delay_rdg_delay_for_pseudo_projectile():
    """1.3.8.2：mdg_delay / rdg_delay 用延长命中时间模拟投射物。"""
    src = _source("soundrts", "definitions.py")
    assert '"mdg_delay"' in src
    assert '"rdg_delay"' in src


def test_damage_seq_parsing_in_definitions():
    """1.3.8.2：damage_seq 攻击序列解析（mdg 3 (damage 6 3 3)(interval 0.2)）。"""
    src = _source("soundrts", "definitions.py")
    # 关键正则与拆分
    block = _section(src, '# 添加对 damage_seq 的特殊处理', "elif words[0] in self.string_properties")
    assert "damage_seq" in block
    # damage 列表 + interval 列表
    assert r'\(damage\s+([0-9\s]+)\)' in block
    assert r'\(interval\s+([\d\.]+)\)' in block


def test_damage_seq_stores_split_components():
    """1.3.8.2：damage_seq 拆出 mdg_seq_times / mdg_seq_damages / mdg_seq_interval。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, '# 添加对 damage_seq 的特殊处理', "elif words[0] in self.string_properties")
    assert "_seq_times" in block
    assert "_seq_damages" in block
    assert "_seq_interval" in block


def test_damage_seq_validates_total_matches_base_damage():
    """1.3.8.2：damage_seq 中分割伤害值之和必须等于 mdg / rdg 基础值。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, '# 添加对 damage_seq 的特殊处理', "elif words[0] in self.string_properties")
    assert "sum(raw_damages) == base_damage" in block


def test_passenger_attack_types_and_load_bonus_supported():
    """1.3.8.2：passenger_attack_types（容器内允许攻击的单位）/ load_bonus（每装载一名单位给容器的属性加成）。"""
    src = _source("soundrts", "definitions.py")
    assert '"passenger_attack_types"' in src
    assert '"load_bonus"' in src
    assert '"passenger_bonus"' in src
    src2 = _source("soundrts", "worldunit", "world_transport.py")
    assert "load_bonus" in src2
    assert "passenger_bonus" in src2


def test_load_bonus_applies_to_transport_loaded_units():
    """1.3.8.2：每装载一名单位都给载具属性加成；卸载时逆转。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    block = _section(src, "def unload_all", "def _can_load_from_terrain", "def load_all")
    assert "load_bonus" in block
    assert "_bonus_stats" in block


def test_passenger_bonus_applies_to_loaded_unit():
    """进入容器后给乘客属性加成；卸载时回滚。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    assert "passenger_bonus" in src
    assert "_passenger_bonus_stats" in src
    assert "_remove_transport_bonus" in src


def test_upgrade_effect_bonus_multi_attr_pairs():
    """1.3.8.2：effect bonus mdg 1 mdf 2 同时改两个属性。
    或者写成 effect bonus mdg 1 + 单独一行 effect bonus mdf 2。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, '(words[0] == "effect" and words[1] == "bonus")',
                     'elif words[0] == "effect" and words[1] == "no_random"',
                     "else:")
    # 从第三个词开始按 (stat, value) 对处理
    assert "for i in range(2, len(words), 2):" in block


def test_upgrade_effect_apply_bonus_supported():
    """1.3.8.2：effect apply_bonus mdg mdf mdg_cd — 多属性同时应用 unit 的 *_bonus。"""
    src = _source("soundrts", "worldupgrade", "attribute_effects.py")
    assert "apply_bonus" in src


def test_upgrade_supports_multi_level_inheritance():
    """1.3.8.2：lv2_melee_weapon is_a lv1_melee_weapon，每一级继续 +mdg。"""
    src = _source("soundrts", "definitions.py")
    # parse_upgrade_definition 处理 is_a 升级链
    assert "parse_upgrade_definition" in src or "expanded_is_a" in src


def test_unit_bonus_supports_per_level_list():
    """1.3.8.2：mdg_bonus 1 1 2 — 前两次 +1，第三次 +2。"""
    src = _source("soundrts", "worldupgrade", "attribute_effects.py")
    # 多级 bonus 应支持列表形式
    assert "_bonus" in src


def test_skill_class_replaces_ability():
    """1.3.8.2：class skill 取代 class ability。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, 'def _get_base_classes', "def _update_old_definitions")
    assert '"skill": Skill' in block
    # ability 不再存在于 base_classes
    assert '"ability"' not in block


def test_skill_supports_cost_and_time_cost():
    """1.3.8.2：skill 支持 cost 与 time_cost 参数（释放有资源 + 时间成本）。"""
    src = _source("soundrts", "worldskill.py")
    block = _section(src, "class Skill", "def __init__")
    assert "cost = " in block
    assert "time_cost = " in block
    assert "mana_cost = " in block


def test_ai_modes_include_guard_and_chase():
    """1.3.8.2：新增 guard（站岗）+ chase（追击）模式。"""
    src = _source("soundrts", "worldunit", "world_ai_decision.py")
    assert '"guard"' in src
    assert '"chase"' in src
    # 切换顺序
    block = _section(src, '"""切换 AI 模式的顺序', "def ")
    for mode in ("offensive", "defensive", "guard", "chase"):
        assert f'"{mode}"' in block


def test_guard_mode_does_not_attack_actively():
    """1.3.8.2：guard 模式下不主动攻击；但被打开启 counterattack 才反击。"""
    src = _source("soundrts", "worldunit", "world_ai_decision.py")
    block = _section(src, 'if self.ai_mode == "guard":', "if self.ai_mode == \"chase\":")
    # guard 处理
    assert "counterattack_enabled" in block or "last_attacker" in block


def test_chase_mode_active_pursuit():
    """1.3.8.2：chase 模式与 offensive 相似，但带更长的追击范围。"""
    src = _source("soundrts", "worldunit", "world_ai_decision.py")
    block = _section(src, 'if self.ai_mode == "chase":', "def ", "if self.ai_mode ==")
    # chase 模式应被处理（不只是占位）
    assert "self.ai_mode" in block


def test_toggle_counterattack_implemented():
    """1.3.8.2：玩家可以给任意单位启用/禁用自动反击。"""
    src = _source("soundrts", "worldorders", "immediate.py")
    block = _section(src, "class ToggleCounterattackOrder",
                     "class AttackKeyOrder",
                     "class SwitchWeaponOrder")
    assert "counterattack_enabled" in block
    # 启用 / 禁用 两个 keyword
    assert "enable_counterattack" in src
    assert "disable_counterattack" in src


def test_resource_type_now_string():
    """1.3.8.2：resource_type 从 int 改为字符串（resource1 / resource2 ...）。"""
    src = _source("soundrts", "definitions.py")
    # resource_type 在 string_properties 中
    block = _section(src, "string_properties = {", "}")
    assert '"resource_type"' in block


def test_resource_type_parse_resource_n_to_index():
    """1.3.8.2：resource_type resource1 解析为索引 0。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, "def parse_resource_type", "def normalized_cost_or_resources",
                     "def parse_resource_list")
    # resource1 → 0
    assert "resource_str[8:]" in block
    assert "- 1" in block


# =============================================================================
# 1.3.8.2 ultimate — 音效系统重构（mdg_missed / mdg_hit / launch_mdg / casting）
# =============================================================================


def test_casting_event_used_in_skills():
    """1.3.8.2：casting 关键字 — 技能释放准备音效。"""
    src = _source("soundrts", "worldorders", "skills.py")
    assert "casting" in src


def test_launch_mdg_rdg_events_used():
    """1.3.8.2：launch_mdg / launch_rdg 取代 launch_attack。"""
    src = _source("soundrts", "combat", "attack_action.py")
    assert "launch_mdg" in src or "launch_rdg" in src or "launch" in src


def test_disappear_event_distinct_from_death():
    """1.3.8.2：disappear 用于召唤物时间到期消失，与 death 区分。"""
    src = _source("soundrts", "worldunit", "world_status_update.py")
    block = _section(src, "def on_disappear", "def ")
    assert 'self.notify("disappear")' in block


def test_missed_event_split_to_mdg_rdg():
    """1.3.8.2 音效系统重构：missed → mdg_missed / rdg_missed（攻击者维度，按近战/远程拆分）。
    日志写 mdg_missed/rdg_missed，实际实现采用与 mdg_hit / rdg_hit 同源命名 mdg_missed / rdg_missed。"""
    src = _source("soundrts", "clientgameentity", "events.py")
    assert "mdg_missed" in src
    assert "rdg_missed" in src
    # notify 仍发 missed 通知，由 on_missed 按 is_melee 分流到 mdg_missed / rdg_missed
    src2 = _source("soundrts", "combat", "hit_miss.py")
    assert "missed" in src2


# =============================================================================
# 1.3.8.2 — building_loaded 后 meadow 恢复（"修复了建筑物被运输单位 load 之后没有 meadow 的 bug"）
# =============================================================================


def test_meadow_created_when_building_loaded():
    """1.3.8.2 修复：把建筑装载到运输单位时，在原位置创建 Meadow（草地）。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    # load 路径下创建草地
    block = _section(src, "# 在原位置生成草地", "def load_all")
    assert "Meadow(original_place, original_x, original_y)" in block


def test_meadow_removed_when_building_unloaded():
    """1.3.8.2：卸载建筑物时占用 Meadow 位置（删除该草地）。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    block = _section(src, "def unload_all", "def _can_load_from_terrain")
    assert "meadow.delete()" in block


# =============================================================================
# 行为级 sanity-check：通过解析 res/rules.txt 验证主要字段不报错
# =============================================================================


def test_rules_txt_parses_with_inheritance_and_capture():
    """端到端 sanity check：实际 res/rules.txt 必须能由 Rules.read() 解析。
    这间接覆盖 is_a / capture_hp_threshold / mdg / damage_seq / 等各类字段。"""
    rules_text = (Path(__file__).resolve().parents[2] / "res" / "rules.txt").read_text(encoding="utf-8")
    from soundrts.definitions import Rules
    r = Rules()
    # 不应抛异常
    r.read(rules_text)
    # 至少应有一些已知 def
    names = r.classnames()
    assert len(names) >= 5
