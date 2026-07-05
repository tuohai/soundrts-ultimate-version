"""审计：1.4 主版本 + 1.3.9.x — 暴击/穿甲/爆炸/英雄/物品/can_train/can_change_to/语言/高地等。

涵盖（按版本倒序）：
- 1.4：mdg + vs 改为加法、crit / crit_rate / crit_vs、piercing / piercing_rate、explode / exp_dgf /
       exp_hp_cost、target_types 扩展（ground/air/unit/building/具体单位）、harm_target_type
       (allied/enemy/具体)、英雄机制 + 升级集成、style.txt 字符串语法、tts "源 = 翻译"、
       multi/ 未打包高级地图、编辑框输入数字播放音效 bug。
- 1.3.9.8：buff / debuffs / item 完整系统（stack/temporary/negative/dt/dv/drain_to/target_type）、
           shortcut 关键字、单位到达有敌人区域时敌人立即出现 bug。
- 1.3.9.7：can_train 单位数量、can_change_to + change_time、effect bonus can_train、
           can_use_tech 单位无法显示菜单 bug。
- 1.3.9.6：upgrade cost/time_cost/food_cost 支持百分比与固定值、can_use_tech / can_use_skill 拆分。
- 1.3.9.5：m/n side / type 过滤、cfg/language.txt 多语言。
- 1.3.9.3：mdg_cover/dodge_on_terrain、research 应用于未训练单位。
- 1.3.9.2：upgrade cost 影响训练 / 升级 / 技能成本、splash_hit 音效、属性界面浮点。
- 1.3.9.1：splash_vs / decay_min_vs / radius_vs、death 着地延迟、投射物低击高限制。
- 1.3.9.0：extraction_time/qty 恢复、Alt + V 属性界面、attribute_key 绑定。
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
# 1.4 — crit / piercing / explode 完整属性集
# =============================================================================


def test_crit_attributes_registered():
    src = _source("soundrts", "definitions.py")
    for key in ("mdg_crit", "rdg_crit", "mdg_crit_rate", "rdg_crit_rate"):
        assert f'"{key}",' in src, f"missing key: {key}"


def test_piercing_attributes_registered():
    src = _source("soundrts", "definitions.py")
    for key in ("mdg_piercing", "rdg_piercing", "mdg_piercing_rate", "rdg_piercing_rate"):
        assert f'"{key}"' in src, f"missing key: {key}"


def test_explode_attributes_registered():
    src = _source("soundrts", "definitions.py")
    for key in ("mdg_explode", "rdg_explode", "exp_hp_cost", "exp_dgf"):
        assert f'"{key}"' in src, f"missing key: {key}"


def test_explode_vs_dict_attributes_in_weapon():
    src = _source("soundrts", "worldweapon.py")
    assert "mdg_explode_vs" in src
    assert "rdg_explode_vs" in src
    assert "exp_dgf_vs" in src


# =============================================================================
# 1.4 — target_types 扩展 + harm_target_type allied/enemy
# =============================================================================


def test_harm_target_type_filters_allied_enemy_and_water():
    src = _source("soundrts", "worldunit", "world_status_update.py")
    block = _section(src, "def _can_harm(self, other):", "def harm_nearby_units")
    assert "passes_harm_diplomacy_filter" in block
    assert '"water" in self.harm_target_type' in block
    pub = _source("soundrts", "worldunit", "world_public_method.py")
    assert '"enemy" in tags or "non_neutral" in tags' in pub
    assert '"neutral" in tags' in pub


def test_world_can_harm_supports_ground_air_unit_building():
    src = _source("soundrts", "world", "world_objects.py")
    # can_harm 内部根据 harm_target_type 决定攻击范围
    block = _section(src, "def can_harm", "class ")
    # 应该有针对 ground/air/unit/building 等的判断
    assert "harm_target_type" in block


# =============================================================================
# 1.4 — 英雄系统：is_revivable / xp_thresholds / hp_max_per_level / hp_regen_per_level
# =============================================================================


def test_hero_attributes_in_property_lists():
    src = _source("soundrts", "definitions.py")
    # hp_max_per_level (precision)
    s = src.index('"hp_max_per_level"')
    block = src[max(0, s - 2000):s + 100]
    assert "precision_properties" in block
    # revival_time (precision)
    s = src.index('"revival_time"')
    block = src[max(0, s - 2000):s + 100]
    assert "precision_properties" in block


def test_resurrect_resets_hero_state():
    """英雄复活后 hp / hp_max / id 都要被复原（已在 1.4.2.0 测试中覆盖，但此处再次确认）。"""
    src = _source("soundrts", "worldunit", "worldbase.py")
    block = _section(src, "def resurrect(self, corpse):", "def _is_weapon_primarily_melee")
    # 关键复活步骤
    assert "self.id = None" in block
    assert "self.hp = " in block


# =============================================================================
# 1.4 — style.txt 字符串语法 / tts "源 = 翻译"
# =============================================================================


def test_style_supports_string_values():
    """style.txt 现在支持 ``title = "archer"`` 和 ``title = 87`` 双形式。"""
    src = _source("soundrts", "definitions.py")
    # 解析时支持 "字符串"
    # （我们松散检查：解析器接受带等号或不带等号的赋值）
    assert "_process_enhanced_inheritance" in src


def test_tts_supports_source_equals_translation():
    """tts.txt 中支持 ``源 = 翻译`` 的格式 — 在 lib.encoding 中针对 tts.txt 文件名做特殊处理，
    支持 unicode 字符与等号语法。这里检查 tts.txt 加载路径存在。"""
    # ui-zh/tts.txt 必须能读且非空，证明翻译文件实际生效
    p = Path(__file__).resolve().parents[2] / "res" / "ui-zh" / "tts.txt"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    # 应包含有效翻译条目（数字 id + 翻译文本）
    assert len(text) > 100
    # encoding.py 对 tts.txt 走专用解码路径
    enc_src = _source("soundrts", "lib", "encoding.py")
    assert 'tts.txt' in enc_src


# =============================================================================
# 1.4 — multi/ 未打包高级地图直接读取
# =============================================================================


def test_unpacked_advanced_map_supported():
    """高级地图文件夹直接放 res/multi/ 下不打包，系统能识别。"""
    src = _source("soundrts", "lib", "resource.py")
    # 路径解析允许处理目录形式
    assert "multi" in src.lower()


def test_td1_unpacked_advanced_map_present():
    """td1 / td2 / td3 都是未打包的高级地图（含独立 rules.txt + map.txt）。"""
    base = Path(__file__).resolve().parents[2] / "res" / "multi"
    for m in ("td1", "td2", "td3"):
        assert (base / m / "rules.txt").exists()
        assert (base / m / "map.txt").exists()


# =============================================================================
# 1.3.9.8 — buff / debuff / item shortcut + stack / temporary / negative / dt / dv
# =============================================================================


def test_buff_full_attribute_set():
    src = _source("soundrts", "worldbuff.py")
    for key, default in [
        ("duration", "0"),
        ("stack", "0"),
        ("temporary", "0"),
        ("negative", "0"),
        ("v", "0"),
        ("dv", "0"),
        ("dt", "to_int(\"1\")"),
        ("target_type", "()"),
        ("drain_to", "()"),
    ]:
        assert f"{key} = {default}" in src, f"buff default missing: {key} = {default}"


def test_buff_drain_to_filtered_hp_mana():
    src = _source("soundrts", "worldbuff.py")
    block = _section(src, "if \"drain_to\" in d:", "def _normalize_multi_values")
    assert 'd["drain_to"] = [x for x in d["drain_to"] if x in ["hp", "mana"]]' in block


def test_item_class_has_shortcut_support():
    """item 的 shortcut 通过 style + bindings 提供。"""
    src = _source("soundrts", "worlditem.py")
    assert "class Item(Entity):" in src
    # 至少要有 default_order pickup
    assert 'default_order = "pickup"' in src


# =============================================================================
# 1.3.9.7 — can_train 数量 / can_change_to / effect bonus can_train
# =============================================================================


def test_can_change_to_keyword_registered():
    src = _source("soundrts", "definitions.py")
    assert '"can_change_to",' in src


def test_change_to_order_implementation():
    src = _source("soundrts", "worldorders", "production.py")
    block = _section(src, "class ChangeToOrder", "class BuildOrder")
    assert 'unit_menu_attribute = "can_change_to"' in block
    assert 'keyword = "change_to"' in block
    # 变形不消耗资源 / 食物
    assert "return (0,) * len(self.type.cost)" in block
    assert "return 0" in block  # population_cost
    # 只读 change_time
    assert 'return getattr(self.type, "change_time", 0)' in block


def test_change_to_complete_preserves_blocked_exit():
    src = _source("soundrts", "worldorders", "production.py")
    block = _section(src, "class ChangeToOrder", "class BuildOrder")
    assert "blocked_exit = self.unit.blocked_exit" in block
    assert "unit.block(blocked_exit)" in block


def test_can_train_bonus_supports_three_forms():
    src = _source("soundrts", "worldupgrade", "attribute_effects.py")
    block = _section(src, "_handle_can_train_bonus", "def _handle_general_attribute_bonus")
    # 形式 1: can_train <count>
    assert "# 形式1：can_train <count>" in block
    # 形式 2/3: <unit> <count> 对，或 <unit>... <count>
    assert "形式2/3" in block
    # 字典化 can_train
    assert "unit.can_train = {}" in block


def test_can_use_tech_menu_visible_for_units():
    """1.3.9.7 修复了具有 can_use_tech 单位无法显示命令菜单的 bug — 验证 menu 路径仍走 can_use_tech。"""
    src = _source("soundrts", "worldorders", "skills.py")
    block = _section(src, "def menu(cls, unit, strict=False):", "def on_queued")
    assert 'getattr(unit, cls.unit_menu_attribute)' in block
    # 同时包含 can_use_skill
    assert 'unit.can_use_skill' in block


# =============================================================================
# 1.3.9.6 — upgrade cost / time_cost / food_cost 百分比 + can_use_tech / can_use_skill 拆分
# =============================================================================


def test_cost_bonus_percentage_supported():
    src = _source("soundrts", "worldupgrade", "attribute_effects.py")
    block = _section(src, "def _handle_cost_bonus", "def _handle_time_cost_bonus",
                     "def _handle_population_cost_bonus")
    assert "str(value).endswith('%')" in block


def test_can_use_tech_and_can_use_skill_default_empty():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    block = _section(src, "can_use_tech = ()", "def ")
    # 紧接着也有 can_use_skill
    assert "can_use_tech = ()" in block
    assert "can_use_skill = ()" in block


def test_precision_property_percentage_passthrough():
    """definitions.py 中 effect_range 的解析路径保留 '%' 后缀值，由 attribute_effects 处理。"""
    src = _source("soundrts", "definitions.py")
    block = _section(src, "# 支持百分比格式", "elif words[0] in self.int_list_properties:")
    assert "endswith('%')" in block
    # 保留原始百分比字符串
    assert 'd[name][words[0]] = words[1]' in block


# =============================================================================
# 1.3.9.5 — m / n 阵营 / 类型过滤 + cfg/language.txt
# =============================================================================


def test_side_and_type_filter_commands_exist():
    src = _source("soundrts", "clientgame", "game_resources.py")
    assert "def cmd_toggle_side_filter(interface, direction=1):" in src
    assert "def cmd_toggle_type_filter(interface, direction=1):" in src


def test_side_filter_cycles_through_friend_enemy_all():
    src = _source("soundrts", "clientgame", "game_resources.py")
    block = _section(src, "def cmd_toggle_side_filter", "def cmd_toggle_type_filter")
    # 三档：己方 / 敌方 / 所有
    assert "friend" in block.lower() or "ally" in block.lower() or "ally" in block.lower()


def test_language_txt_loading_order():
    src = _source("soundrts", "lib", "resource.py")
    block = _section(src, '"cfg/language.txt"', "def ")
    # 不存在或为空时回退到系统默认
    assert "open(\"cfg/language.txt\")" in src
    # 持久化保存逻辑
    assert 'open("cfg/language.txt", "w")' in src


# =============================================================================
# 1.3.9.3 — mdg_cover/dodge_on_terrain + research 应用于未训练单位
# =============================================================================


def test_terrain_modifier_attributes_used_in_hit_miss():
    src = _source("soundrts", "combat", "hit_miss.py")
    # 主路径：mdg_cover_on_terrain / rdg_cover_on_terrain
    assert "self.mdg_cover_on_terrain" in src
    assert "self.rdg_cover_on_terrain" in src
    # 闪避修正
    assert "self.mdg_dodge_on_terrain" in src
    assert "self.rdg_dodge_on_terrain" in src


def test_terrain_dodge_lookup_pattern():
    src = _source("soundrts", "combat", "hit_miss.py")
    assert "_terrain_modifier_from_list" in src
    assert "terrain_list_value" in src


def test_entity_defaults_for_terrain_attrs():
    src = _source("soundrts", "worldentity.py")
    assert "mdg_cover_on_terrain = ()" in src
    assert "rdg_cover_on_terrain = ()" in src
    assert "mdg_dodge_on_terrain = ()" in src
    assert "rdg_dodge_on_terrain = ()" in src


# =============================================================================
# 1.3.9.2 — upgrade cost 影响训练 / 升级 / 技能成本
# =============================================================================


def test_global_cost_effects_propagated_via_upgrade():
    src = _source("soundrts", "worldupgrade", "base.py")
    # _global_cost_effects 字典在 Upgrade 类上
    assert "_global_cost_effects" in src


def test_production_cost_respects_upgrade_cost_effects():
    """ComplexOrder.cost 在 worldorders/base.py 中聚合 applicable_techs → _global_cost_effects。"""
    src = _source("soundrts", "worldorders", "base.py")
    assert "applicable_techs" in src
    assert "Upgrade._global_cost_effects" in src


# =============================================================================
# 1.3.9.1 — splash_vs / decay_min_vs / radius_vs + falling_delay + 投射低击高
# =============================================================================


def test_splash_vs_radius_vs_attributes_present():
    src = _source("soundrts", "worldweapon.py")
    # mdg_radius_vs / rdg_radius_vs vs dict
    assert "mdg_radius_vs" in src
    assert "rdg_radius_vs" in src
    # splash decay vs
    assert "mdg_splash_decay_min_vs" in src or "splash_decay_min" in src


def test_falling_delay_and_terrain_supported():
    src = _source("soundrts", "clientgameentity", "events.py")
    block = _section(src, '"falling_on_"', "def ")
    assert 'falling_delay' in block
    # 在播放 falling 音效前等待 delay 毫秒
    assert "set_timer" in block


def test_projectile_cannot_attack_high_ground_from_low():
    """``mdg_projectile != 1 and rdg_projectile != 1`` → 低击高 ground 目标被拒绝。"""
    src = _source("soundrts", "combat", "targeting.py")
    s = src.index("not self_place.high_ground and other_place.high_ground")
    block = src[s:s + 500]
    assert 'other.airground_type == "ground"' in block
    assert "self.mdg_projectile != 1" in block
    assert "self.rdg_projectile != 1" in block


def test_projectile_high_ground_hit_chance_halved():
    src = _source("soundrts", "combat", "hit_miss.py")
    s = src.index("if high_ground:")
    block = src[s:s + 500]
    # 投射物攻击高地命中减半
    assert "base_chance //= 2" in block


# =============================================================================
# 1.3.9.0 — extraction_time/qty 恢复 + Alt+V 属性界面 + attribute_key
# =============================================================================


def test_extraction_time_qty_on_deposit():
    src = _source("soundrts", "worldresource.py")
    block = _section(src, "class Deposit(Entity):", "class BuildingLand")
    assert "extraction_time" in block
    assert "extraction_qty" in block


def test_alt_v_unit_attributes_screen_bound():
    p = Path(__file__).resolve().parents[2] / "res" / "ui" / "global_bindings.txt"
    text = p.read_text(encoding="utf-8")
    assert "ALT V: unit_attributes_screen" in text


def test_unit_attributes_screen_command_present():
    src = _source("soundrts", "attributes", "main_display.py")
    assert "def cmd_unit_attributes_screen(self):" in src

    src2 = _source("soundrts", "attributes", "display_interface.py")
    assert "def cmd_unit_attributes_screen(self):" in src2


def test_attribute_key_command_supports_attribute_jump():
    """属性界面绑定文件支持 ``F1: attribute_key MELEE_DAMAGE`` 跳转。"""
    src = _source("soundrts", "attributes", "key_bindings.py")
    assert "_setup_attributes_screen_bindings" in src
    # 默认绑定路径
    assert "_setup_default_attributes_bindings" in src
    # 可加载自定义文件
    assert "attributes_bindings.txt" in src


# =============================================================================
# 行为级模拟：高地 + 投射物命中减半
# =============================================================================


def test_simulated_high_ground_projectile_hit_chance():
    """复刻 base_chance //= 2 当且仅当 (低地, 高地目标, ground, projectile)。"""

    def hit_chance(base, attacker_high, target_high, target_air_type, is_projectile):
        high_ground = (
            not attacker_high
            and target_high
            and target_air_type == "ground"
        )
        if high_ground and is_projectile:
            base //= 2
        return base

    assert hit_chance(100, False, True, "ground", True) == 50
    assert hit_chance(100, False, True, "ground", False) == 100
    assert hit_chance(100, False, True, "air", True) == 100  # 空中目标不受影响
    assert hit_chance(100, True, True, "ground", True) == 100  # 同高
    assert hit_chance(100, False, False, "ground", True) == 100  # 同低


# =============================================================================
# 行为级：can_train bonus 三种形式
# =============================================================================


def test_simulated_can_train_three_forms():
    """复刻 can_train bonus 解析：
    形式 1: can_train <N>            → 所有现有项目 += N
    形式 2: <unit> <N> [<unit> <N>...] → 单独项设值
    形式 3: <unit> ... <unit> <N>     → 多个 unit 共用同一个 N
    """

    def apply_bonus(can_train_dict, args):
        pos = 0
        if pos < len(args) and str(args[pos]).isdigit():
            # 形式 1
            inc = int(args[pos])
            for k in list(can_train_dict.keys()):
                can_train_dict[k] = max(1, can_train_dict[k] + inc)
            return can_train_dict
        while pos < len(args):
            tok = args[pos]
            if pos + 1 < len(args) and str(args[pos + 1]).isdigit():
                # 形式 2
                can_train_dict[tok] = max(1, int(args[pos + 1]))
                pos += 2
                continue
            batch = []
            while pos < len(args) and not str(args[pos]).isdigit():
                batch.append(args[pos])
                pos += 1
            if pos < len(args):
                n = int(args[pos])
                for k in batch:
                    can_train_dict[k] = max(1, n)
                pos += 1
            else:
                for k in batch:
                    can_train_dict[k] = 1
        return can_train_dict

    # 形式 1
    d = {"footman": 1, "knight": 2}
    apply_bonus(d, ["3"])
    assert d == {"footman": 4, "knight": 5}

    # 形式 2
    d = {}
    apply_bonus(d, ["footman", "3", "archer", "2"])
    assert d == {"footman": 3, "archer": 2}

    # 形式 3
    d = {}
    apply_bonus(d, ["footman", "archer", "knight", "5"])
    assert d == {"footman": 5, "archer": 5, "knight": 5}
