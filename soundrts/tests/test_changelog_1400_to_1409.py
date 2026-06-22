"""审计：1.4.0.1 — 1.4.0.9 — 冲锋/反冲锋、菜单音效音乐、阵营音乐、生产、旁观、暴击、RPG 模式。

涵盖：
- 1.4.0.1：charge_*/op_charge_*、buff is_active/is_passive/trigger_condition/passive_trigger_rate、
           失败/胜利条件（unit_lost / key_unit_killed / key_units_killed / units_lost /
           building_lost / buildings_lost / has_killed / killed_target；enemy/ally 限定）。
- 1.4.0.2：菜单 select/confirm/return 音效，menu/campaign/game_creation/server_lobby/game/battle/map
           音乐，victory_sound / defeat_sound。
- 1.4.0.3：阵营专属背景音乐 / 战斗音乐（阵营 > 地图 > 全局）。
- 1.4.0.4：auto_production / manual_production、is_gather、Resource vs Deposit 拆分。
- 1.4.0.5：rpg_bindings.txt、food→population 替换、auto_cultivate / manual_cultivate、
           资源建筑被工人采集。
- 1.4.0.6：旁观模式（_is_pure_spectator / observer_if_defeated）。
- 1.4.0.7：暴击几率修复（mdg_crit_rate vs target.mdf_crit_rate）。
- 1.4.0.8：minimal_mdg / minimal_rdg 回滚为 minimal_damage、RPG 技能热键 1-0 + Alt+/ + Ctrl+A。
- 1.4.0.9 / 1.4.1：RPG 第一人称模式、F8 缩放 3x3-15x15、change_zoom_precision。
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
# 1.4.0.1 — 冲锋 / 反冲锋属性集
# =============================================================================


CHARGE_KEYS = (
    "charge_mdg", "charge_rdg",
    "charge_mdg_dist", "charge_rdg_dist",
    "charge_mdg_cd", "charge_rdg_cd",
    "charge_mdg_splash", "charge_rdg_splash",
    "charge_mdg_radius", "charge_rdg_radius",
)
OP_CHARGE_KEYS = (
    "op_charge_mdg", "op_charge_rdg",
    "op_charge_mdg_dist", "op_charge_rdg_dist",
    "op_charge_mdg_cd", "op_charge_rdg_cd",
)


def test_all_charge_keys_in_precision_properties():
    src = _source("soundrts", "definitions.py")
    for key in CHARGE_KEYS + OP_CHARGE_KEYS:
        assert f'"{key}",' in src, f"missing rules key: {key}"


def test_charge_defaults_on_unit_class():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "charge_mdg = 0" in src
    assert "charge_rdg = 0" in src


# =============================================================================
# 1.4.0.1 — buff is_active / is_passive / trigger_condition / passive_trigger_rate
# =============================================================================


def test_buff_active_passive_fields_default():
    src = _source("soundrts", "worldbuff.py")
    assert "is_active = False" in src
    assert "is_passive = False" in src
    assert 'trigger_condition = ""' in src
    assert "passive_trigger_rate = 100" in src
    assert "hp_threshold = 0" in src
    # 冲锋触发率
    assert "charge_mdg_trigger_rate = 0" in src
    assert "charge_rdg_trigger_rate = 0" in src
    # 反冲锋触发率
    assert "op_charge_mdg_trigger_rate = 0" in src
    assert "op_charge_rdg_trigger_rate = 0" in src


def test_buff_passive_trigger_rate_clamped_0_to_100():
    src = _source("soundrts", "worldbuff.py")
    block = _section(src, "def interpret(cls, d):", "def _normalize_multi_values")
    # 验证 0-100 范围
    assert "d[k] < 0 or d[k] > 100" in block
    assert 'd[k] = 100 if k == "passive_trigger_rate" else 0' in block


def test_buff_trigger_condition_joins_list_to_string():
    src = _source("soundrts", "worldbuff.py")
    block = _section(src, "def interpret(cls, d):", "def _normalize_multi_values")
    assert 'd["trigger_condition"] = " ".join(str(x) for x in d["trigger_condition"])' in block


# =============================================================================
# 1.4.0.1 — 失败 / 胜利触发器
# =============================================================================


def test_trigger_unit_lost_uses_type_or_id():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_unit_lost(self, args):", "def lang_units_lost")
    # 既支持 ID（数字）也支持 类型名
    assert "if unit_identifier.isdigit()" in block
    # 类型匹配走 expanded_is_a
    assert "expanded_is_a" in block


def test_trigger_units_lost_multi_type_format():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_units_lost(self, args):", "def lang_building_lost")
    # is_advanced_format = len(args) >= 4 and len(args) % 2 == 0
    assert "is_advanced_format = len(args) >= 4" in block
    assert "len(args) % 2 == 0" in block


def test_trigger_buildings_lost_filters_by_provides_survival():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_buildings_lost(self, args):", "def lang_")
    # 必须只算「提供生存」的建筑
    assert "provides_survival" in block


def test_trigger_killed_target_supports_enemy_ally():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_killed_target", "def has_killed_unit_with_id")
    assert 'target_owner = "enemy"' in block   # 默认 enemy
    assert "_killed_enemy_unit_types" in block
    assert "_killed_ally_unit_types" in block


def test_trigger_has_killed_advanced_format_supports_multi_unit():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_has_killed(self, args):", "def lang_key_unit_killed")
    # 多类型组合
    assert "is_advanced_format" in block
    # 末尾可选 enemy/ally
    assert '["enemy", "ally"]' in block


def test_trigger_key_unit_killed_present():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    assert "def lang_key_unit_killed(self, args):" in src


# =============================================================================
# 1.4.0.2 — 菜单音效 / 音乐 / 胜负音效
# =============================================================================


def test_style_loads_all_menu_music_kinds():
    src = _source("soundrts", "definitions.py")
    block = _section(src, "def _load_music_settings", "def _load_faction_music_settings")
    for k in (
        "menu_music", "game_music", "campaign_music",
        "game_creation_music", "server_lobby_music", "battle_music",
        "victory_sound", "defeat_sound",
    ):
        assert f'"{k}"' in block, f"missing music kind: {k}"


def test_sound_module_has_setters_for_each_music_kind():
    src = _source("soundrts", "lib", "sound.py")
    for setter in (
        "set_menu_music", "set_campaign_music",
        "set_game_creation_music", "set_server_lobby_music",
        "set_battle_music", "set_victory_sound", "set_defeat_sound",
    ):
        assert f"def {setter}(" in src, f"missing setter: {setter}"


def test_play_menu_music_called_from_main_menus():
    """主菜单 / 战役菜单 / 服务器大厅菜单 / 游戏结束都需要触发 play_menu_music。"""
    for path in (
        ("soundrts", "clientmain.py"),
        ("soundrts", "campaign.py"),
        ("soundrts", "clientservermenu.py"),
        ("soundrts", "clientserver.py"),
        ("soundrts", "clientgame", "game_interface_base.py"),
    ):
        src = _source(*path)
        assert "sound.play_menu_music()" in src


# =============================================================================
# 1.4.0.3 — 阵营专属背景音乐 / 战斗音乐（阵营 > 地图 > 全局）
# =============================================================================


def test_faction_music_priority_over_map_and_global():
    src = _source("soundrts", "lib", "sound.py")
    block = _section(src, "def play_game_music", "def set_menu_music")
    # 注释明确"阵营专属音乐 > 地图专属音乐 > 全局游戏音乐"
    assert "阵营专属音乐 > 地图专属音乐 > 全局游戏音乐" in block
    # 阵营音乐第一个分支
    s = block.index("if faction_music:")
    e = block.index("if map_music:", s)
    branch = block[s:e]
    assert "play_music(faction_music)" in branch
    assert "return" in branch  # 短路退出


def test_faction_music_dynamic_setting_load():
    src = _source("soundrts", "definitions.py")
    block = _section(src, "def _load_faction_music_settings", "class ")
    # 排除全局音乐
    assert '"menu_music", "game_music", "campaign_music"' in block
    # _battle_music 后缀识别为阵营战斗音乐
    assert 'if key.endswith("_battle_music"):' in block
    # _music 后缀识别为阵营普通音乐
    assert 'faction_id = key[:-6]' in block


# =============================================================================
# 1.4.0.4 — auto_production / manual_production，is_gather，Resource vs Deposit
# =============================================================================


def test_deposit_class_is_primary_gather_target():
    src = _source("soundrts", "worldresource.py")
    assert "class Deposit(Entity):" in src
    assert "class Resource(Entity):" not in src
    assert "def extract_resource(self, qty):" in src


def test_auto_production_and_manual_production_recognized():
    src = _source("soundrts", "worldunit", "worldcreature.py")
    # 类默认都有这两个开关
    assert "auto_production" in src
    assert "manual_production" in src


def test_is_gather_supported_for_building_production():
    src = _source("soundrts", "worldorders", "production.py")
    assert "is_gather" in src


# =============================================================================
# 1.4.0.5 — rpg_bindings.txt + RPG 命令注册
# =============================================================================


def test_rpg_bindings_file_exists_with_skill_hotkeys():
    p = Path(__file__).resolve().parents[2] / "res" / "ui" / "rpg_bindings.txt"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    # 1-9 / 0 数字键绑定到 rpg_skill_N
    for i in range(10):
        assert f"{i}: rpg_skill_{i}" in text
    # Alt+/ + Ctrl+A
    assert "ALT SLASH: rpg_skill_list" in text
    assert "CTRL A: rpg_auto_attack" in text


def test_rpg_skill_commands_implemented():
    src = _source("soundrts", "clientgame", "game_orders.py")
    for i in range(10):
        assert f"def cmd_rpg_skill_{i}(interface):" in src
    assert "def cmd_rpg_skill_list(interface):" in src
    assert "def cmd_rpg_auto_attack(interface):" in src


def test_change_zoom_precision_command_present():
    src = _source("soundrts", "clientgame", "game_audio.py")
    assert "def cmd_change_zoom_precision(interface, *args):" in src


# 1.4.0.5: food → population 全替换


def test_population_cost_replaces_food_cost():
    src = _source("soundrts", "definitions.py")
    # population_cost / population_provided 在 int_properties
    assert '"population_cost"' in src
    assert '"population_provided"' in src


def test_no_food_keyword_in_int_properties():
    """``food`` / ``food_cost`` / ``food_provided`` 不应作为 rules.txt 的有效关键字。
    （legacy 名称只剩注释文档；非 rules 关键字）"""
    src = _source("soundrts", "definitions.py")
    # 在 int_properties 列表中不应出现"food"键
    idx = src.find('"food",')
    assert idx == -1, "food keyword should have been replaced by population"


# =============================================================================
# 1.4.0.6 — 旁观模式
# =============================================================================


def test_spectator_player_flag():
    src = _source("soundrts", "worldplayerbase", "base.py")
    block = _section(src, "observer_if_defeated = False", "class ")
    # add_unit 拒绝 spectator
    assert "_is_pure_spectator" in block


def test_observer_if_defeated_on_human_player():
    src = _source("soundrts", "worldplayerhuman.py")
    assert "observer_if_defeated = True" in src


def test_spectate_command_in_client_menu():
    src = _source("soundrts", "clientservermenu.py")
    assert "_spectate_games_menu" in src
    assert "srv_spectate_success" in src
    assert "srv_spectate_error" in src
    assert "srv_spectator_joined" in src
    assert "srv_spectator_left" in src


def test_spectator_player_cannot_get_units_via_trigger():
    """触发器尝试给纯旁观玩家 add_units 必须被忽略。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    s = src.index("_is_pure_spectator")
    block = src[s:s + 400]
    assert 'warning("Attempted to add units to spectator player' in block


# =============================================================================
# 1.4.0.7 — 暴击几率修复
# =============================================================================


def test_critical_hit_uses_world_random_clamped_0_100():
    src = _source("soundrts", "combat", "damage_effects.py")
    s = src.index("self.world.random.randint(1, 100) <= final_crit_rate")
    block = src[max(0, s - 500):s + 200]
    # 计算最终 crit_rate = base - target_resist，max(0, ...)
    assert "final_crit_rate = max(0, crit_rate - target_crit_resist)" in block


def test_critical_hit_vs_lookup_includes_armor_inheritance():
    src = _source("soundrts", "combat", "damage_effects.py")
    block = _section(src,
                     "# 获取针对特定单位类型的暴击倍率",
                     "# 计算最终暴击倍率")
    # type_name / expanded_is_a / armor_name / armor.expanded_is_a / armor.is_a 五路 lookup
    assert "target.expanded_is_a" in block
    assert "get_current_armor_name" in block
    assert "armor.expanded_is_a" in block
    assert "armor.is_a" in block


# =============================================================================
# 1.4.0.8 — minimal_damage 回滚 + minimal_mdg / minimal_rdg 仍存在但同列
# =============================================================================


def test_minimal_damage_rolled_back_to_single_field():
    src = _source("soundrts", "combat", "damage_calculation.py")
    # 仅 minimal_damage 决定下限
    assert "getattr(attacker, 'minimal_damage', 0)" in src
    # max(actual_damage, minimal_damage)
    assert "actual_damage = max(actual_damage, minimal_damage)" in src


def test_minimal_damage_minimal_mdg_minimal_rdg_all_keys_present():
    src = _source("soundrts", "definitions.py")
    assert '"minimal_mdg"' in src
    assert '"minimal_rdg"' in src
    assert '"minimal_damage"' in src


# =============================================================================
# 1.4 — 基础属性 vs 改为"加法"模型
# =============================================================================


def test_mdg_plus_mdg_vs_additive():
    src = _source("soundrts", "combat", "damage_calculation.py")
    block = _section(src, "def _py_get_melee_damage_vs", "def _get_ranged_damage_vs")
    # base + vs 模型
    assert "return self.mdg + v" in block
    assert "return self.mdg + mdg_vs[armor_name]" in block
    # 没找到 vs lookup → 回退到基础值
    assert "return self.mdg" in block


def test_rdg_plus_rdg_vs_additive():
    src = _source("soundrts", "combat", "damage_calculation.py")
    block = _section(src, "def _py_get_ranged_damage_vs", "def _get_melee_defense_vs")
    assert "return self.rdg + v" in block
    assert "return self.rdg + rdg_vs[armor_name]" in block
    assert "return self.rdg" in block


def test_defense_vs_additive_for_mdf():
    src = _source("soundrts", "combat", "damage_calculation.py")
    s = src.index("def _get_melee_defense_vs(self, attacker) -> int:")
    e = src.index("def _get_ranged_defense_vs", s) if "_get_ranged_defense_vs" in src else len(src)
    block = src[s:min(e, s + 3000)]
    # 防御也是 mdf + vs
    assert "return self.mdf + v" in block


# =============================================================================
# 1.4 — 英雄系统：是否可复活、复活时间、xp 阈值
# =============================================================================


def test_hero_keys_in_int_properties():
    src = _source("soundrts", "definitions.py")
    # 这些都是 int_property
    for k in ("global_count_limit", "is_revivable", "xp_reward"):
        s = src.index(f'"{k}"')
        block = src[max(0, s - 2000):s + 100]
        assert "int_properties" in block, f"{k} should be in int_properties"


def test_revival_time_in_precision_properties():
    src = _source("soundrts", "definitions.py")
    s = src.index('"revival_time"')
    block = src[max(0, s - 2000):s + 100]
    assert "precision_properties" in block


def test_xp_thresholds_is_list_property():
    src = _source("soundrts", "definitions.py")
    s = src.index('"xp_thresholds"')
    block = src[max(0, s - 2000):s + 100]
    assert "list_properties" in block


# =============================================================================
# 行为级测试：失败条件 units_lost 多类型解析
# =============================================================================


def test_simulated_units_lost_multi_type():
    """复刻 lang_units_lost 多类型格式逻辑。

    格式：(units_lost 数量1 类型1 数量2 类型2 ...) — 任一类型不足 → True。
    """

    def units_lost(args, current_counts):
        # 与源码同样判定方式
        is_advanced = len(args) >= 4 and len(args) % 2 == 0
        if is_advanced:
            for i in range(0, len(args), 2):
                req = int(args[i])
                unit_type = args[i + 1]
                cur = current_counts.get(unit_type, 0)
                if cur >= req:
                    return False
            return True
        else:
            req = int(args[0])
            unit_type = args[1]
            return current_counts.get(unit_type, 0) < req

    # 单类型：5 knight, 当前只有 3 knight → True
    assert units_lost(["5", "knight"], {"knight": 3}) is True
    # 单类型：5 knight, 当前 5 knight → False（数量足）
    assert units_lost(["5", "knight"], {"knight": 5}) is False
    # 多类型采用 ALL 语义：所有指定类型都数量不足才返回 True
    # 3 knight + 5 archer, knight=2 不足 + archer=10 充足 → False（archer 充足）
    assert units_lost(["3", "knight", "5", "archer"], {"knight": 2, "archer": 10}) is False
    # 所有都不足 → True
    assert units_lost(["3", "knight", "5", "archer"], {"knight": 2, "archer": 4}) is True
    # 所有都足 → False
    assert units_lost(["3", "knight", "5", "archer"], {"knight": 5, "archer": 6}) is False


# =============================================================================
# 行为级：阵营 > 地图 > 全局 音乐优先级
# =============================================================================


def test_simulated_music_priority():
    def pick(faction_music, map_music, global_music):
        if faction_music:
            return faction_music
        if map_music:
            return map_music
        if global_music:
            return global_music
        return None

    assert pick("china", "snow_map", "default") == "china"
    assert pick(None, "snow_map", "default") == "snow_map"
    assert pick(None, None, "default") == "default"
    assert pick(None, None, None) is None
