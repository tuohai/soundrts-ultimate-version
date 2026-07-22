"""
显示接口模块
处理主要的显示逻辑和接口方法
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import format_signed_number, nb2msg, nb2msg_float
from ..clientmedia import voice
from ..definitions import style
from ..level_up_stats import LEVEL_UP_INT_STAT_ATTRS, LEVEL_UP_STAT_ATTRS
from .utils import NAVIGABLE_ITEM_TYPES, get_stat_tts_name, normalize_nav_item


class DisplayInterface:
    def __init__(self, main_interface, basic_attributes, build_rules_attributes,
                 equipment_abilities, combat_attributes):
        self.main_interface = main_interface
        self.basic_attributes = basic_attributes
        self.build_rules_attributes = build_rules_attributes
        self.equipment_abilities = equipment_abilities
        self.combat_attributes = combat_attributes
    
    def cmd_unit_attributes_screen(self):
        """打开单位或建筑的属性界面，显示单位的全部信息
        
        玩家可以通过按首字母直接跳转到对应属性：
        h - HP (生命值)
        m - MDG (近战伤害)
        r - RDG (远程伤害)
        d - MDF/RDF (防御值)
        s - 速度
        a - 攻击间隔/冷却
        """
        if not self.main_interface.group:
            voice.item(mp.NO_UNIT_CONTROLLED)
            return
        
        if len(self.main_interface.group) == 1:
            u = self.main_interface.dobjets[self.main_interface.group[0]]
            # 保存当前单位以供界面使用
            self.main_interface._attributes_screen_unit = u
            
            
            from ..worldresource import Deposit
            if isinstance(u, Deposit):
                self.main_interface._show_resource_attributes(u)
                return
            
            # 构建属性列表
            attrs = []
            self.populate_unit_attributes(u, attrs)
            
            # 保存属性列表以供界面使用
            self.main_interface._attributes_screen_attrs = attrs
            from .terrain_effective import current_terrain_type
            self.main_interface._attrs_terrain_type = current_terrain_type(u)
            
            # 显示标题和提示
            voice.item(u.title + mp.ATTRIBUTES + mp.PRESS_LETTER_FOR_INFO + mp.COMMA + mp.PRESS_ESC_TO_EXIT)
            
            # 检查是否有属性
            if not attrs:
                voice.item(mp.NO_ATTRIBUTES)
                return
            
            # 显示第一个属性开始
            self.main_interface._current_attribute_index = 0
            self.main_interface._current_sub_item_index = 0
            self._display_current_attribute()
            
            # 进入属性界面模式
            self.main_interface._in_attributes_screen = True
            
            # 保存原始按键绑定
            self.main_interface._original_bindings = self.main_interface._bindings
            
            # 创建新的按键绑定用于属性界面
            self.main_interface.key_bindings._setup_attributes_screen_bindings()
        else:
            # 如果选择了多个单位，显示数量
            voice.item(str(len(self.main_interface.group)) + mp.UNITS_SELECTED)
    
    def _add_remaining_attributes(self, u, attrs):
        """添加剩余的特殊属性"""
        # 最小伤害属性
        if hasattr(u.model, "mdg_minimal_damage") and u.model.mdg_minimal_damage > 0:
            mdg_minimal_damage_text = nb2msg_float(u.model.mdg_minimal_damage / PRECISION)
            if hasattr(mp, 'MDG_MINIMAL_DAMAGE'):
                attrs.append(("", mp.MDG_MINIMAL_DAMAGE, mdg_minimal_damage_text))
            else:
                attrs.append(("", ["近战最小伤害"], mdg_minimal_damage_text))
        
        if hasattr(u.model, "rdg_minimal_damage") and u.model.rdg_minimal_damage > 0:
            rdg_minimal_damage_text = nb2msg_float(u.model.rdg_minimal_damage / PRECISION)
            if hasattr(mp, 'RDG_MINIMAL_DAMAGE'):
                attrs.append(("", mp.RDG_MINIMAL_DAMAGE, rdg_minimal_damage_text))
            else:
                attrs.append(("", ["远程最小伤害"], rdg_minimal_damage_text))
        
        # 投射物属性（只在有投射物时显示）
        if hasattr(u.model, "mdg_projectile") and u.model.mdg_projectile:
            if hasattr(mp, 'MDG_PROJECTILE'):
                attrs.append(("", mp.MDG_PROJECTILE, mp.YES))
            else:
                attrs.append(("", ["近战投射物"], mp.YES))
        
        if hasattr(u.model, "rdg_projectile") and u.model.rdg_projectile:
            if hasattr(mp, 'RDG_PROJECTILE'):
                attrs.append(("", mp.RDG_PROJECTILE, mp.YES))
            else:
                attrs.append(("", ["远程投射物"], mp.YES))
        
        # 等级相关属性 - 每级增长（所有战斗属性均支持 <stat>_per_level）
        for stat in LEVEL_UP_STAT_ATTRS:
            per_level = getattr(u.model, f"{stat}_per_level", 0)
            if not per_level:
                continue
            if stat in LEVEL_UP_INT_STAT_ATTRS:
                per_level_text = nb2msg_float(per_level)
            else:
                per_level_text = nb2msg_float(per_level / PRECISION)
            stat_name = get_stat_tts_name(stat)
            per_level_label = mp.PER_LEVEL + stat_name + mp.GROWTH
            attrs.append(("", per_level_label, per_level_text))
        
        # 移除可传送属性显示（通常无需显示）
        # if hasattr(u.model, "is_teleportable") and u.model.is_teleportable:
        #     if hasattr(mp, 'IS_TELEPORTABLE'):
        #         attrs.append(("", mp.IS_TELEPORTABLE, mp.YES))
        #     else:
        #         attrs.append(("", ["可传送"], mp.YES))
        
        # 占地体积（格子容量 = 地图 square_width）
        if hasattr(u.model, "space") and u.model.space > 0:
            space_text = nb2msg_float(u.model.space / PRECISION)
            if hasattr(mp, "SPACE"):
                attrs.append(("", mp.SPACE, space_text))
            else:
                attrs.append(("", ["占地体积"], space_text))

        # 体积属性
        if hasattr(u.model, "transport_volume") and u.model.transport_volume > 0:
            transport_volume_text = nb2msg(u.model.transport_volume)
            if hasattr(mp, 'TRANSPORT_VOLUME'):
                attrs.append(("", mp.TRANSPORT_VOLUME, transport_volume_text))
            else:
                attrs.append(("", ["运输体积"], transport_volume_text))
        
        # 运输容量
        if hasattr(u.model, "transport_capacity") and u.model.transport_capacity > 0:
            transport_capacity_text = nb2msg(u.model.transport_capacity)
            attrs.append(("", mp.TRANSPORT_CAPACITY, transport_capacity_text))

        self._add_transport_container_attributes(u, attrs)
        
        # 人口成本（只在大于1时显示）
        if hasattr(u.model, "population_cost") and u.model.population_cost > 1:
            pop_cost_text = nb2msg(u.model.population_cost)
            attrs.append(("", mp.POPULATION_COST_NAME, pop_cost_text))
        
        # 处理是否属于亡灵单位 - 只有在原始定义中明确设置时才显示
        if (hasattr(u.model, "__dict__") and "is_undead" in u.model.__dict__):
            is_undead_value = getattr(u.model, "is_undead", False)
            if is_undead_value:  # 只在为True时显示
                attrs.append(("", mp.IS_UNDEAD, mp.YES))
        
        # 只在True时显示的布尔属性
        if hasattr(u.model, "can_repair_ships") and u.model.can_repair_ships:
            attrs.append(("", mp.CAN_REPAIR_SHIPS, mp.YES))
        
        # 只对非建筑单位显示是否可修理（建筑默认都可修理，无需显示）
        if hasattr(u.model, "is_repairable") and u.model.is_repairable and not getattr(u.model, "is_a_building", False):
            attrs.append(("", mp.IS_REPAIRABLE, mp.YES))
        
        # 提供生存能力 (暂时跳过，msgparts中没有这个常量)
        # if hasattr(u.model, "provides_survival") and u.model.provides_survival:
        #     attrs.append(("", ["提供生存能力"], mp.YES))
        
        if hasattr(u.model, "can_repair") and u.model.can_repair:
            attrs.append(("", mp.CAN_REPAIR, mp.YES))

    def _normalize_transport_bonus(self, bonus):
        """将 load_bonus / passenger_bonus 规范为 {stat: value}（rules 中常为列表）。"""
        if isinstance(bonus, dict):
            return {str(k): v for k, v in bonus.items()}
        if isinstance(bonus, list):
            result = {}
            i = 0
            while i < len(bonus):
                if i + 1 < len(bonus):
                    try:
                        result[str(bonus[i])] = float(bonus[i + 1])
                    except (TypeError, ValueError):
                        pass
                i += 2
            return result
        return {}

    def _format_transport_bonus_value_parts(self, value):
        """格式化单个加成数值，避免小整数被 tts.txt 误解析为语音 ID。"""
        try:
            coerced = float(value)
        except (TypeError, ValueError):
            return [str(value)]
        if coerced == 0:
            return []
        if coerced == int(coerced):
            value_text = format_signed_number(int(coerced))
        else:
            value_text = format_signed_number(coerced, as_float=True)
        if coerced > 0:
            return ["+"] + value_text
        return value_text

    def _format_transport_bonus_dict(self, bonus):
        """格式化 load_bonus / passenger_bonus 为属性界面文本。"""
        bonus_text = []
        normalized = self._normalize_transport_bonus(bonus)
        for attr_name, value in normalized.items():
            attr_display_name = get_stat_tts_name(attr_name)
            if isinstance(attr_display_name, list):
                bonus_text.extend(attr_display_name)
            else:
                bonus_text.append(str(attr_display_name))
            bonus_text.extend(self._format_transport_bonus_value_parts(value))
            bonus_text.extend(mp.COMMA)
        if bonus_text and bonus_text[-1] in mp.COMMA:
            bonus_text = bonus_text[:-1]
        elif not normalized and bonus:
            bonus_text.append(str(bonus))
        return bonus_text

    def _format_passenger_attack_types(self, attack_types):
        """格式化 passenger_attack_types 为属性界面文本。"""
        attack_text = []
        if isinstance(attack_types, list):
            for unit_type in attack_types:
                unit_title = style.get(unit_type, "title")
                if unit_title:
                    if isinstance(unit_title, list):
                        attack_text.extend(unit_title)
                    else:
                        attack_text.append(str(unit_title))
                else:
                    attack_text.append(str(unit_type))
                attack_text.extend(mp.COMMA)
            if attack_text and attack_text[-1] in mp.COMMA:
                attack_text = attack_text[:-1]
        elif attack_types:
            unit_title = style.get(attack_types, "title")
            if unit_title:
                if isinstance(unit_title, list):
                    attack_text.extend(unit_title)
                else:
                    attack_text.append(str(unit_title))
            else:
                attack_text.append(str(attack_types))
        return attack_text

    def _add_transport_container_attributes(self, u, attrs):
        """运输容器：容器内可攻击单位、装载加成、乘客加成。"""
        model = u.model

        passenger_attack_types = getattr(model, "passenger_attack_types", None)
        if passenger_attack_types:
            attack_text = self._format_passenger_attack_types(passenger_attack_types)
            if attack_text:
                attrs.append(("", mp.PASSENGER_ATTACK_TYPES, attack_text))

        load_bonus = getattr(model, "load_bonus", None)
        if load_bonus:
            load_bonus_text = self._format_transport_bonus_dict(load_bonus)
            if load_bonus_text:
                attrs.append(("", mp.LOAD_BONUS, load_bonus_text))

        passenger_bonus = getattr(model, "passenger_bonus", None)
        if passenger_bonus:
            passenger_bonus_text = self._format_transport_bonus_dict(passenger_bonus)
            if passenger_bonus_text:
                attrs.append(("", mp.PASSENGER_BONUS, passenger_bonus_text))

        attack_inside_chance = getattr(model, "attack_inside_chance", 0)
        if attack_inside_chance:
            attrs.append(
                ("", mp.ATTACK_INSIDE_CHANCE, nb2msg(attack_inside_chance) + mp.PERCENT)
            )

    def populate_tech_attributes(self, u, attrs, effect_formatter):
        """构建科技/技能/时代的完整属性列表。"""
        model = u.model

        if hasattr(model, "cost") and model.cost:
            cost_text = []
            for i, cost_value in enumerate(model.cost):
                if cost_value > 0:
                    cost_text.extend(nb2msg(int(cost_value / PRECISION)))
                    resource_title = style.get(f"resource{i + 1}", "title")
                    if resource_title:
                        if isinstance(resource_title, list):
                            cost_text.extend(resource_title)
                        else:
                            cost_text.append(str(resource_title))
                    cost_text.extend(mp.COMMA)
            if cost_text:
                attrs.append(("c", mp.COST, cost_text[:-len(mp.COMMA)]))

        if hasattr(model, "time_cost") and model.time_cost > 0:
            time_text = nb2msg_float(model.time_cost / 1000) + mp.SECONDS
            attrs.append(("t", mp.TIME, time_text))

        if hasattr(model, "population_cost") and model.population_cost > 0:
            pop_text = nb2msg(model.population_cost)
            attrs.append(("p", mp.POPULATION, pop_text))

        try:
            from ..worldrequirements import format_belonging_phase_titles

            phase_text = format_belonging_phase_titles(model)
            if phase_text:
                attrs.append(("", mp.BELONGS_TO_AGE, phase_text))
        except Exception:
            pass

        effect_rows = []
        if hasattr(model, "effect") and model.effect:
            effects = model.effect
            if isinstance(effects, list):
                if effects and isinstance(effects[0], list):
                    for effect_def in effects:
                        if effect_def:
                            effect_rows.extend(
                                effect_formatter._format_effect_attribute_rows(effect_def)
                            )
                else:
                    effect_rows.extend(
                        effect_formatter._format_effect_attribute_rows(effects)
                    )
        if hasattr(model, "phase_bonus") and model.phase_bonus:
            effect_rows.extend(
                effect_formatter._format_phase_bonus_attribute_rows(model.phase_bonus)
            )
        if effect_rows:
            effect_items = effect_formatter.effect_attribute_rows_to_items(effect_rows)
            if effect_items:
                attrs.append(("e", mp.EFFECT, ("EFFECT_ITEMS", effect_items)))

        if hasattr(model, "requirements") and model.requirements:
            from ..worldrequirements import format_clause_titles, parse_requirement_clauses

            req_text = []
            for clause in parse_requirement_clauses(model.requirements):
                clause_title = format_clause_titles(clause)
                if clause_title:
                    req_text.extend(clause_title)
                    req_text.extend(mp.COMMA)
            if req_text:
                attrs.append(("r", mp.REQUIREMENTS, req_text[:-len(mp.COMMA)]))

        phase_targets = effect_formatter._format_phase_targets_text(
            getattr(model, "phase_targets", None)
        )
        if phase_targets:
            attrs.append(("", mp.PHASE_TARGETS, phase_targets))

        if int(getattr(model, "units_auto_upgrade", 0) or 0):
            attrs.append(("", mp.UNITS_AUTO_UPGRADE, mp.YES))

        if hasattr(model, "can_upgrade_to") and model.can_upgrade_to:
            upgrade_text = []
            upgrades = model.can_upgrade_to
            if isinstance(upgrades, str):
                upgrades = [upgrades]
            for upgrade_type in upgrades:
                upgrade_title = style.get(upgrade_type, "title")
                if upgrade_title:
                    if isinstance(upgrade_title, list):
                        upgrade_text.extend(upgrade_title)
                    else:
                        upgrade_text.append(str(upgrade_title))
                else:
                    upgrade_text.append(str(upgrade_type))
                upgrade_text.extend(mp.COMMA)
            if upgrade_text:
                attrs.append(("", mp.CAN_UPGRADE_TO, upgrade_text[:-len(mp.COMMA)]))

    def populate_unit_attributes(self, u, attrs):
        """构建单位/建筑的完整属性列表（主界面与详情界面共用）。"""
        steps = [
            self.basic_attributes.add_basic_info_attributes,
            self.basic_attributes.add_healing_attributes,
            self.basic_attributes.add_regeneration_attributes,
            self.basic_attributes.add_harm_attributes,
            self.basic_attributes.add_movement_attributes,
            self.basic_attributes.add_basic_combat_attributes,
            self.basic_attributes.add_sight_attributes,
            self.combat_attributes.add_attack_defense_attributes,
            self.combat_attributes.add_charge_attributes,
            self.equipment_abilities.add_weapon_attributes,
            self.equipment_abilities.add_armor_attributes,
            self.equipment_abilities.add_inventory_attributes,
            self.equipment_abilities.add_status_attributes,
            self.equipment_abilities.add_unit_type_attributes,
            self.equipment_abilities.add_class_attributes,
            self.equipment_abilities.add_training_attributes,
            self.equipment_abilities.add_building_attributes,
            self.build_rules_attributes.add_build_rules_attributes,
            self.equipment_abilities.add_upgrade_attributes,
            self.equipment_abilities.add_research_attributes,
            self.equipment_abilities.add_advance_attributes,
            self.equipment_abilities.add_tech_skill_attributes,
            self.equipment_abilities.add_gather_attributes,
            self.equipment_abilities.add_building_resource_attributes,
            self.equipment_abilities.add_production_attributes,
            self.combat_attributes.add_explode_attributes,
            self.combat_attributes.add_explode_vs_attributes,
            self.combat_attributes.add_target_attributes,
            self.combat_attributes.add_minimal_range_attributes,
            self.combat_attributes.add_ready_attributes,
            self.combat_attributes.add_splash_decay_attributes,
            self.combat_attributes.add_splash_decay_vs_attributes,
            self.combat_attributes.add_terrain_modifier_attributes,
            self._add_remaining_attributes,
        ]
        for step in steps:
            try:
                step(u, attrs)
            except Exception:
                pass

    def refresh_attributes_for_terrain_if_needed(self):
        """单位换地形后重建属性列表，使 mdg 等显示即时修正。"""
        mi = self.main_interface
        if not getattr(mi, "_in_attributes_screen", False):
            return False
        if getattr(mi, "_in_detail_attributes_screen", False):
            return False
        u = getattr(mi, "_attributes_screen_unit", None)
        if u is None:
            return False
        from .terrain_effective import current_terrain_type

        terrain = current_terrain_type(u)
        if terrain == getattr(mi, "_attrs_terrain_type", object()):
            return False

        prev_name = None
        idx = getattr(mi, "_current_attribute_index", 0)
        attrs_old = getattr(mi, "_attributes_screen_attrs", None) or []
        if 0 <= idx < len(attrs_old):
            prev_name = attrs_old[idx][1]

        attrs = []
        self.populate_unit_attributes(u, attrs)
        mi._attributes_screen_attrs = attrs
        mi._attrs_terrain_type = terrain

        if prev_name is not None:
            for i, (_, name, _) in enumerate(attrs):
                if name == prev_name:
                    mi._current_attribute_index = i
                    break
            else:
                mi._current_attribute_index = min(idx, max(0, len(attrs) - 1))
        else:
            mi._current_attribute_index = min(idx, max(0, len(attrs) - 1))
        mi._current_sub_item_index = 0
        return True

    def _display_current_attribute(self, show_attribute_name=True):
        """显示当前选中的属性
        
        Args:
            show_attribute_name: 是否显示属性名称，False时只显示值（用于子项导航）
        """
        self.refresh_attributes_for_terrain_if_needed()
        if self.main_interface._current_attribute_index < 0 or self.main_interface._current_attribute_index >= len(self.main_interface._attributes_screen_attrs):
            return
            
        _, name, value = self.main_interface._attributes_screen_attrs[self.main_interface._current_attribute_index]
        
        # 检查是否是特殊的可导航项目列表
        if isinstance(value, tuple) and len(value) == 2 and value[0] in NAVIGABLE_ITEM_TYPES:
            items = value[1]
            self.main_interface._current_attribute_sub_items = items
            
            if len(items) > 0:
                # 确保子项索引在有效范围内
                if self.main_interface._current_sub_item_index >= len(items):
                    self.main_interface._current_sub_item_index = 0
                elif self.main_interface._current_sub_item_index < 0:
                    self.main_interface._current_sub_item_index = len(items) - 1
                    
                current_item = normalize_nav_item(items[self.main_interface._current_sub_item_index])
                counter = [f" ({self.main_interface._current_sub_item_index + 1}/{len(items)})"]
                
                # 根据是否显示属性名称来构建输出
                if show_attribute_name:
                    # 显示："属性名: 当前项 , (x/总数)"
                    output = name + mp.COLON + current_item + mp.COMMA + counter
                else:
                    # 只显示当前项 , 编号
                    output = current_item + mp.COMMA + counter
                
                voice.item(output)
            else:
                # 空列表的情况
                if show_attribute_name:
                    voice.item(name + mp.COLON + mp.NO_SUCH_ATTRIBUTE)
                else:
                    voice.item(mp.NO_SUCH_ATTRIBUTE)
        else:
            # 普通属性
            self.main_interface._current_attribute_sub_items = []
            if show_attribute_name:
                voice.item(name + mp.COLON + value)
            else:
                voice.item(value)
    
    def _build_unit_attributes(self, u, attrs=None, is_detail_view=False):
        """构建单位属性列表 - 用于详情视图等特殊场合"""
        if attrs is None:
            attrs = []
        
        # 基础信息
        if hasattr(u, "hp") and hasattr(u, "hp_max"):
            attrs.append(("h", mp.HP, u.hp_status))
            
        # 简介
        unit_type_name = getattr(u, 'type_name', None) or getattr(u.model, 'type_name', None)
        if unit_type_name:
            intro = style.get(unit_type_name, "intro")
            if intro:
                if isinstance(intro, list):
                    attrs.append(("?", mp.INTRO, intro))
                else:
                    attrs.append(("?", mp.INTRO, [str(intro)]))
        
        # 速度
        if hasattr(u.model, "speed") and u.model.speed > 0:
            speed_text = nb2msg_float(u.model.speed / PRECISION)
            attrs.append(("s", mp.SPEED, speed_text))
        
        # 视野范围
        if hasattr(u.model, "sight_range") and u.model.sight_range > 0:
            sight_range_text = nb2msg_float(u.model.sight_range / 1000)
            attrs.append(("v", mp.SIGHT_RANGE, sight_range_text))
        
        # 基础战斗属性
        self.main_interface._add_bonus_attribute(attrs, u, "mdg", "m", mp.MELEE_DAMAGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg", "r", mp.RANGE_DAMAGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdf", "d", mp.MELEE_DEFENSE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdf", "", mp.RANGE_DEFENSE, True)

        from .basic_attributes import BasicAttributes

        src = BasicAttributes._attribute_source(u)
        menace_val = BasicAttributes._effective_menace(src)
        if menace_val > 0:
            attrs.append(("", mp.MENACE, nb2msg_float(menace_val / PRECISION)))
        
        # vs属性
        if hasattr(u.model, "mdg_vs") and u.model.mdg_vs:
            self.main_interface._add_vs_attribute(attrs, u.model.mdg_vs, "mdg", True)
        if hasattr(u.model, "rdg_vs") and u.model.rdg_vs:
            self.main_interface._add_vs_attribute(attrs, u.model.rdg_vs, "rdg", True)
        
        # 防御vs属性
        if hasattr(u.model, "mdf_vs") and u.model.mdf_vs:
            self.main_interface._add_vs_attribute(attrs, u.model.mdf_vs, "mdf", True)
        if hasattr(u.model, "rdf_vs") and u.model.rdf_vs:
            self.main_interface._add_vs_attribute(attrs, u.model.rdf_vs, "rdf", True)
        
        # 速度地形修正
        if hasattr(u.model, "speed_on_terrain") and u.model.speed_on_terrain:
            terrain_dict = u.model.speed_on_terrain
            if terrain_dict:
                terrain_text = []
                for terrain_type, speed_value in terrain_dict.items():
                    terrain_title = style.get(terrain_type, "title")
                    if terrain_title:
                        if isinstance(terrain_title, list):
                            terrain_text.extend(terrain_title)
                        else:
                            terrain_text.append(str(terrain_title))
                    else:
                        terrain_text.append(str(terrain_type))
                    
                    terrain_text.extend(mp.COLON)
                    terrain_text.extend(nb2msg_float(speed_value))
                    terrain_text.extend(mp.COMMA)
                
                if terrain_text:
                    # 移除最后一个逗号
                    terrain_text = terrain_text[:-1]
                    attrs.append(("", mp.SPEED_ON_TERRAIN, terrain_text))
        
        # 攻击间隔
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_cd", "a", mp.MDG_CD, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_cd", "a", mp.RDG_CD, True)
        
        # 攻击射程
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_range", "", mp.MDG_RANGE, True, divide_by_1000=True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_range", "", mp.RDG_RANGE, True, divide_by_1000=True)
        
        # 更多战斗属性...
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_crit", "", mp.MDG_CRIT, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_crit", "", mp.RDG_CRIT, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_crit_rate", "", mp.MDG_CRIT_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_crit_rate", "", mp.RDG_CRIT_RATE, False)
        
        # 穿透
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_piercing", "", mp.MDG_PIERCING, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_piercing", "", mp.RDG_PIERCING, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_piercing_rate", "", mp.MDG_PIERCING_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_piercing_rate", "", mp.RDG_PIERCING_RATE, False)
        
        # 防御暴击
        self.main_interface._add_bonus_attribute(attrs, u, "mdf_crit_rate", "d", mp.MDF_CRIT_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdf_crit_rate", "", mp.RDF_CRIT_RATE, False)
        
        # 溅射
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_splash", "", mp.MDG_SPLASH, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_splash", "", mp.RDG_SPLASH, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_radius", "", mp.MDG_RADIUS, True, divide_by_1000=True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_radius", "", mp.RDG_RADIUS, True, divide_by_1000=True)

        try:
            self.build_rules_attributes.add_build_rules_attributes(u, attrs)
        except Exception:
            pass
        
        return attrs