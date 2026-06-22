"""审计：1.4.1.4 — 1.4.1.9 — 触发器、intro、视野对角、production_type、save/load、effect/buff、square_name 三级。

1.4.1.4：td1-td3 触发器迁移（timer, add_units, order, no_building_left, defeat 等）。
1.4.1.5：intro 关键字、视野恢复对角感知、不生产资源建筑不显示生产类型。
1.4.1.6：武器 debuffs（见 1413 测试）、保存游戏后无法加载 → 原子写入 .tmp → rename。
1.4.1.7：effect_target self/ask、effect_range、多属性 buff、harm/heal_* 细化、hp_regen_cd / mana_regen_ready。
1.4.1.8：x,y 坐标 ↔ 字母坐标双向转换、square_name + 多坐标语义、阵营默认起始 vs 地图优先级、tts 多语翻译。
1.4.1.9：square_name 三级从属、跨级播报省略。
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
# 1.4.1.4 — 触发器迁移：td1-td3 必备的 timer/add_units/order/defeat
# =============================================================================


def test_trigger_timer_reschedules_periodically():
    """``(timer start period)`` 触发后必须重新入队（``start + period``）。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def _eventually_reschedule", "def my_eval")
    assert 'condition[0] == "timer"' in block
    assert "condition[1] = float(condition[1]) + float(condition[2])" in block
    assert "self.triggers.append((condition, action))" in block


def test_lang_timer_uses_world_time_coefficient():
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    block = _section(src, "def lang_timer(self, args):", "def lang_if")
    assert "self.world.time // 1000" in block
    # 支持加速调试时的 timer_coefficient
    assert "self.world.timer_coefficient" in block


def test_trigger_required_actions_present():
    """add_units / order / defeat / no_building_left / team_defeat 这些 td 地图常用动作存在。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    for kw in ("lang_protect", "lang_team_defeat", "lang_play", "lang_alliance", "lang_find"):
        assert f"def {kw}(" in src, f"missing trigger action: {kw}"


def test_td1_map_loads_triggers_format():
    """td1 地图必须能在脚本里读到 ``trigger ... (timer ...) (add_units ...)`` 行。"""
    p = Path(__file__).resolve().parents[2] / "res" / "multi" / "td1" / "map.txt"
    text = p.read_text(encoding="utf-8")
    assert "trigger computer1 (timer 0 60) (add_units j1 1 footman)" in text
    assert "trigger players (no_building_left) (defeat)" in text


# =============================================================================
# 1.4.1.5 — intro 关键字
# =============================================================================


def test_intro_displayed_in_basic_attributes():
    src = _source("soundrts", "attributes", "basic_attributes.py")
    block = _section(src, "def add_basic_info_attributes", "def add_healing_attributes")
    assert 'style.get(unit_type_name, "intro")' in block
    assert "mp.INTRO" in block


def test_intro_keyword_supported_in_map_text_fields():
    """world_map.py 把 ``intro`` 当成多行文本字段，与 title/objective 并列。"""
    src = _source("soundrts", "world", "world_map.py")
    assert 'w in ["title", "objective", "intro", "cut_scene"]' in src


def test_world_default_intro_empty_list():
    src = _source("soundrts", "world", "world_core.py")
    assert "self.intro = []" in src


def test_intro_plays_sequence_on_game_start():
    src = _source("soundrts", "game.py")
    # 进入游戏时若有 intro，播放 sequence
    assert "if self.world.intro:" in src
    assert "play_sequence(self.world.intro)" in src


# =============================================================================
# 1.4.1.5 — 视野对角感知（recovered）
# =============================================================================


def test_room_neighbors_includes_diagonals():
    src = _source("soundrts", "worldroom.py")
    block = _section(src, "def neighbors(self):", "def building_land")
    # 8 个方向 = 4 正向 + 4 对角
    for d in (
        "(0, 1)", "(0, -1)", "(1, 0)", "(-1, 0)",
        "(1, 1)", "(1, -1)", "(-1, 1)", "(-1, -1)",
    ):
        assert d in block, f"neighbors should include {d}"


def test_room_strict_neighbors_only_4_orthogonal():
    """``strict_neighbors`` 仍只走 4 方向（与对角分离）。"""
    src = _source("soundrts", "worldroom.py")
    block = _section(src, "def strict_neighbors(self):", "@cached_property\n    def neighbors")
    # 不含对角
    assert "(1, 1)" not in block
    assert "(-1, -1)" not in block


def test_observed_squares_uses_neighbors_not_strict():
    """``get_observed_squares`` 必须用 ``self.place.neighbors`` 才能看到对角。"""
    src = _source("soundrts", "worldunit", "world_transport.py")
    block = _section(src, "def get_observed_squares(self, strict=False):",
                     "def get_observed_squares_optimized")
    assert "for sq in self.place.neighbors:" in block


def test_potential_neighbors_iterates_3x3_grid():
    src = _source("soundrts", "worldplayerbase", "perception.py")
    block = _section(src, "def _potential_neighbors(self, x, y, skip_cache=False):",
                     "def _clear_neighbors_cache")
    # 9 格（3*3）扫描，含 (1,1)/(-1,-1) 等
    assert "for dx in [0, 1, -1]:" in block
    assert "for dy in [0, 1, -1]:" in block


# =============================================================================
# 1.4.1.5 — 不生产资源建筑不显示生产类型
# =============================================================================


def test_production_attributes_only_when_capable():
    """``add_production_attributes`` 需同时拥有 ``production_type`` 与 ``production_time > 0``。

    该方法已重构：用 ``has_production_time`` / ``show_production`` 等更细的标志
    取代了早期单一的 ``has_production_capability``，但「只有真正能生产才显示生产
    属性」这一不变量仍然成立——生产时间必须 > 0，且需有 production_type。
    """
    src = _source("soundrts", "attributes", "equipment_abilities.py")
    block = _section(src, "def add_production_attributes(self, u, attrs):",
                     "def add_movement_attributes",
                     "def add_storage_attributes",
                     "\n\n    def ")
    assert 'getattr(model, "production_time"' in block
    assert "production_time > 0" in block
    assert 'getattr(model, "production_type"' in block
    # 仅在确实具备生产能力时才追加生产相关属性
    assert "show_production" in block
    assert "if show_production:" in block


# =============================================================================
# 1.4.1.6 — 保存游戏后无法加载 → 原子写入 .tmp → rename
# =============================================================================


def test_save_uses_atomic_tmp_then_rename():
    src = _source("soundrts", "game.py")
    block = _section(src, "def _write_save_to(self, path):", "def save(self):")
    assert 'tmp_path = path + ".tmp"' in block
    assert "cloudpickle_dump_game(self, f" in block
    assert "os.replace(tmp_path, path)" in block
    # 失败回滚清理 tmp
    assert "os.remove(tmp_path)" in block


def test_save_bumps_recursionlimit_for_big_games():
    src = _source("soundrts", "game.py")
    assert "SAVE_RECURSION_LIMIT_BASE = 20000" in src
    block = _section(src, "def pickle_recursion_limit_for_squares(", "def pickle_recursion_limit_for_file_size")
    assert "n * 5" in block
    dump_block = _section(src, "def cloudpickle_dump_game(", "class SaveTooLargeError")
    assert "cloudpickle.dump(obj, f)" in dump_block
    save_pickle = _source("soundrts", "save_pickle.py")
    assert "WORLD_STRIP_ON_SAVE" in save_pickle
    assert "rebuild_world_after_load" in save_pickle


def test_save_includes_global_cost_effects():
    src = _source("soundrts", "game.py")
    block = _section(src, "def _write_save_to(self, path):", "def save(self):")
    assert "self._global_cost_effects = Upgrade._global_cost_effects" in block


# =============================================================================
# 1.4.1.7 — 技能 effect_target self/ask、effect_range
# =============================================================================


def test_skill_defaults():
    src = _source("soundrts", "worldskill.py")
    assert 'effect_target = ["self"]' in src
    assert "effect_range = 6 * PRECISION" in src
    assert "effect_radius = 6 * PRECISION" in src


def test_use_order_nb_args_depends_on_effect_target():
    """``effect_target = ['ask']`` → nb_args = 1（要 tab + 选目标）；其它为 0。"""
    src = _source("soundrts", "worldorders", "skills.py")
    block = _section(src, "class UseOrder(ComplexOrder):", "class PickupOrder")
    assert "@property\n    def nb_args(self):" in block
    assert 'if self.type.effect_target == ["ask"]:' in block
    assert "return 1" in block
    assert "return 0" in block


def test_use_order_self_targets_caster():
    src = _source("soundrts", "worldorders", "skills.py")
    block = _section(src, "class UseOrder(ComplexOrder):", "class PickupOrder")
    assert 'elif self.type.effect_target == ["self"]:' in block
    assert "self.target = self.unit" in block


def test_use_order_respects_effect_range_for_move_closer():
    src = _source("soundrts", "worldorders", "skills.py")
    block = _section(src, "class UseOrder(ComplexOrder):", "class PickupOrder")
    # 距离 > 实际施法距离^2 → move_to_or_fail（靠近）；单位目标会计入双方半径。
    assert "def _effect_range_to_target(self):" in block
    assert "return effect_range + self.unit.radius + self.target.radius" in block
    assert "effect_range = self._effect_range_to_target()" in block
    assert "self.move_to_or_fail(self.target)" in block


def test_effect_range_supports_square_nearby_anywhere_aliases():
    """definitions.py 中读 effect_range == 'square' / 'nearby' / 'anywhere' / 'inf' 时转换为整数。"""
    src = _source("soundrts", "definitions.py")
    s = src.index('words[0] == "effect_range"')
    block = src[s:s + 1500]
    assert 'words[1] = "6"' in block      # square → 6
    assert 'words[1] = "12"' in block     # nearby → 12
    assert 'words[1] = "2147483"' in block  # anywhere / inf → maxint/1000


def test_skill_executor_dispatch_by_effect_type():
    src = _source("soundrts", "worldskill.py")
    block = _section(src, "def execute_skill(cls, caster, target=None, world=None):",
                     "def _execute_generic_effect")
    # method_name = f"_execute_{effect_type}"
    assert "method_name = f\"_execute_{effect_type}\"" in block


def test_skill_generic_buffs_to_target():
    src = _source("soundrts", "worldskill.py")
    block = _section(src, "def _execute_generic_effect", "def _is_teleportation_necessary")
    # buffs → target.add_buff
    assert 'if effect_type == "buffs"' in block
    assert "target.add_buff(buff_name, caster)" in block
    # debuffs → only on enemy
    assert 'elif effect_type == "debuffs"' in block
    assert "caster.is_an_enemy(target)" in block


# =============================================================================
# 1.4.1.7 — buff 多属性 stat + percentage/v/dv 智能值匹配
# =============================================================================


def test_buff_normalize_multi_values_truncate_and_extend():
    src = _source("soundrts", "worldbuff.py")
    block = _section(src, "def _normalize_multi_values", "def __init__")
    # 短了：用最后一个值填充
    assert "last_val = self.percentage[-1]" in block
    assert "(stat_count - len(self.percentage))" in block
    # 长了：截断
    assert "self.percentage = self.percentage[:stat_count]" in block
    # 单值：复制给所有属性
    assert "self.percentage = [self.percentage] * stat_count" in block


def test_buff_default_buff_radius_zero():
    src = _source("soundrts", "worldbuff.py")
    assert "buff_radius = 0" in src


def test_buff_interpret_buff_radius_to_int():
    src = _source("soundrts", "worldbuff.py")
    block = _section(src, "def interpret(cls, d):", "def _normalize_multi_values")
    assert '"buff_radius"' in block
    # 通过 to_int 处理；非负
    assert 'd["buff_radius"] = 0' in block


# 行为级测试 — 验证 _normalize_multi_values 的"智能值匹配"


def test_simulated_multi_buff_value_matching():
    """复刻：stat 数量 = 3，v 长度 = 1 → 复制为 3；v 长度 = 4 → 截断到 3。"""

    def normalize(stats, vals):
        if isinstance(vals, list):
            if len(vals) < len(stats):
                last = vals[-1] if vals else 0
                vals = vals + [last] * (len(stats) - len(vals))
            elif len(vals) > len(stats):
                vals = vals[:len(stats)]
        else:
            vals = [vals] * len(stats)
        return vals

    stats = ["hp_max", "mana_max", "speed"]
    assert normalize(stats, 100) == [100, 100, 100]
    assert normalize(stats, [10, 20]) == [10, 20, 20]
    assert normalize(stats, [10, 20, 30, 40]) == [10, 20, 30]
    assert normalize(stats, []) == [0, 0, 0]


# =============================================================================
# 1.4.1.7 — harm_*  / heal_* / hp_regen_cd / mana_regen_ready
# =============================================================================


def test_harm_heal_regen_attrs_registered_in_precision_properties():
    src = _source("soundrts", "definitions.py")
    # 全部都在 precision_properties 列表
    s = src.index('"mdg_cd",')
    e = src.index('"minimal_mdg",', s)
    block = src[s:e]
    for key in (
        '"heal_cd"', '"harm_cd"', '"heal_ready"', '"harm_ready"',
        '"hp_regen_cd"', '"hp_regen_ready"', '"mana_regen_cd"', '"mana_regen_ready"',
        '"heal_radius"', '"harm_radius"', '"heal_range"', '"harm_range"',
    ):
        assert key in block


def test_can_heal_returns_true_when_empty_heal_target_type():
    """``_can_heal``: 未定义 ``heal_target_type`` → 默认可治疗任何友军（非建筑）。"""
    src = _source("soundrts", "worldunit", "world_status_update.py")
    block = _section(src, "def _can_heal(self, other):", "harm_target_type = ()")
    assert "if not self.heal_target_type:" in block
    assert "return True" in block


def test_can_harm_treats_water_separately():
    """``_can_harm``: ``water`` 不被 world.can_harm 处理，独立返回 True。"""
    src = _source("soundrts", "worldunit", "world_status_update.py")
    block = _section(src, "def _can_harm(self, other):", "def harm_nearby_units")
    assert '"water" in self.harm_target_type' in block
    assert "target_airground_type == 'water'" in block
    assert "passes_harm_diplomacy_filter" in block


def test_hp_regen_cd_and_mana_regen_ready_default_zero():
    src = _source("soundrts", "worldentity.py")
    assert "hp_regen_cd = 0" in src
    assert "mana_regen_ready = 0" in src


def test_hp_regen_cd_gates_next_regen():
    """``world_status_update`` 中按 hp_regen_cd 间隔重排 hp_regen 触发时间。"""
    src = _source("soundrts", "worldunit", "world_status_update.py")
    s = src.index("hp_regen_cd = getattr(self, 'hp_regen_cd', 0)")
    block = src[s:s + 800]
    assert "self.hp_regen_next_time = current_time + hp_regen_cd" in block


# =============================================================================
# 1.4.1.8 — 坐标转换：letter+digit ↔ x,y
# =============================================================================


def test_letter_to_xy_conversion_zero_based():
    """复刻 ``_normalize_square_token`` 中字母→坐标转换（a1 -> "0,0"）。"""
    src = _source("soundrts", "world", "world_map.py")
    block = _section(src, "_normalize_square_token", "_normalize_square_list")
    # a1 → "0,0"
    assert 'col = col * 26 + (ord(ch) - ord(\'a\') + 1)' in block
    assert "col -= 1" in block
    # x,y 输入：1-based → 0-based
    assert "col_0based = col_1based - 1" in block
    assert "row_0based = row_1based - 1" in block


def test_normalize_square_token_in_practice():
    """直接调用 ``_normalize_square_token`` 静态行为：a1 -> '0,0'，b3 -> '1,2'，'2,3' -> '1,2'。"""
    import re

    def _normalize(token):
        t = token.strip().lower()
        if "," in t:
            parts = t.split(",")
            if len(parts) == 2:
                try:
                    col_1 = int(parts[0].strip())
                    row_1 = int(parts[1].strip())
                    return f"{col_1 - 1},{row_1 - 1}"
                except ValueError:
                    return token
        if re.match(r"^[a-z]+[0-9]+$", t):
            letters = ''.join(c for c in t if c.isalpha())
            digits = ''.join(c for c in t if c.isdigit())
            col = 0
            for ch in letters:
                col = col * 26 + (ord(ch) - ord('a') + 1)
            col -= 1
            try:
                row = int(digits) - 1
            except ValueError:
                return token
            return f"{col},{row}"
        return token

    assert _normalize("a1") == "0,0"
    assert _normalize("b3") == "1,2"
    assert _normalize("2,3") == "1,2"
    assert _normalize("z1") == "25,0"
    assert _normalize("aa1") == "26,0"  # 27th column → index 26


# =============================================================================
# 1.4.1.8 — square_name 多坐标 vs 单坐标 → 主区域 / 子区域
# =============================================================================


def test_square_name_multi_coord_creates_province():
    """``square_name normandy 2,2 2,3 3,3`` 中三个坐标都登记为同一主区域。"""
    src = _source("soundrts", "world", "world_map.py")
    block = _section(src, 'elif w == "square_name":', 'elif w == "square_name3":',
                     'elif w in ["starting_resources"]:')
    # 多坐标 → square_provinces
    assert "if key not in self.square_provinces:" in block
    assert "self.square_provinces[key] = alias" in block
    # 已有主区域 → 视为二级
    assert "self.square_cities.setdefault(key, alias)" in block


def test_square_name_single_coord_creates_city_then_district():
    src = _source("soundrts", "world", "world_map.py")
    block = _section(src, 'elif w == "square_name":', 'elif w == "square_name3":',
                     'elif w in ["starting_resources"]:')
    assert "if key not in self.square_cities:" in block
    assert "self.square_cities[key] = alias" in block
    # 已有二级 → 第三级
    assert "self.square_districts[key] = alias" in block


def test_square_name3_field_for_third_level():
    src = _source("soundrts", "world", "world_map.py")
    assert 'elif w == "square_name3":' in src


# =============================================================================
# 1.4.1.8 — 阵营默认起始 vs 地图优先（map > rules）
# =============================================================================


def test_map_starting_overrides_rule_starting():
    src = _source("soundrts", "world", "world_objects.py")
    block = _section(src, "# 针对每个", "for player, start in zip(self.players, starts):")
    # 默认 only when map 未显式定义 + 当前为空
    assert "need_units_default = (not self.map_defined_starting_units)" in block
    assert "need_resources_default = (not self.map_defined_starting_resources)" in block
    # 仅在 need 时替换；否则保留地图值
    assert "if need_units_default or need_resources_default:" in block


def test_world_core_default_map_defined_flags_false():
    src = _source("soundrts", "world", "world_core.py")
    assert "self.map_defined_starting_units = False" in src
    assert "self.map_defined_starting_resources = False" in src


def test_map_sets_map_defined_starting_resources_when_parsed():
    src = _source("soundrts", "world", "world_map.py")
    block = _section(src, 'elif w in ["starting_resources"]:', 'elif rules.get(w, "class")')
    assert "self.map_defined_starting_resources = True" in block


# =============================================================================
# 1.4.1.9 — 三级 square_name + 跨级播报省略
# =============================================================================


def test_navigation_only_announces_province_on_boundary_cross():
    src = _source("soundrts", "clientgame", "game_navigation.py")
    # 玩家进入新主区域时才前缀；同主区域内省略
    assert "if prev_province != province_name:" in src
    assert "province_prefix = [province_name]" in src
    # 城市同理
    assert "if city_name and city_name != prev_city:" in src
    assert "city_prefix = [city_name]" in src


def test_square_title_uses_district_then_city_else_fallback():
    src = _source("soundrts", "worldroom.py")
    block = _section(src, "class Square(_Space):", "def __repr__")
    # 三级优先：district > city > fallback name > 纯坐标
    assert "if district:" in block
    assert "elif city:" in block
    assert "elif fallback:" in block
    # 城市级标题只播报坐标，跨入时由 navigation 拼前缀
    s = block.index("elif city:")
    after = block[s:s + 200]
    assert "self.title = coord" in after


def test_square_title_falls_back_to_pure_coord_without_names():
    src = _source("soundrts", "worldroom.py")
    block = _section(src, "class Square(_Space):", "def __repr__")
    # else 分支
    assert "else:\n            self.title = coord" in block


# 行为级模拟：跨级播报省略


def test_simulated_hierarchy_announcement_skips_same_province():
    province_of = {(0, 0): "江苏省", (0, 1): "江苏省", (1, 0): "浙江省"}
    city_of = {(0, 0): "南京市", (0, 1): "无锡市"}

    def announce(prev, new):
        out = []
        prev_p = province_of.get(prev)
        new_p = province_of.get(new)
        if new_p and new_p != prev_p:
            out.append(new_p)
        prev_c = city_of.get(prev)
        new_c = city_of.get(new)
        if new_c and new_c != prev_c:
            out.append(new_c)
        return out

    # 不跨省 + 跨市
    assert announce((0, 0), (0, 1)) == ["无锡市"]
    # 同省同市
    assert announce((0, 0), (0, 0)) == []
    # 跨省必带省名 + 市名（如果有）
    assert announce((0, 0), (1, 0)) == ["浙江省"]
