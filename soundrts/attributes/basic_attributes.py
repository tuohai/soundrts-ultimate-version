"""
基础属性显示模块
处理HP、MP、治疗、基本状态等核心属性
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from ..definitions import style


class BasicAttributes:
    def __init__(self, main_interface):
        self.main_interface = main_interface

    @staticmethod
    def _attribute_source(u):
        return getattr(u, "model", None) or u

    @staticmethod
    def _absolute_menace(src):
        """Return class/instance absolute ``menace`` if rules fixed it; else None."""
        if src is None:
            return None
        if isinstance(src, type):
            raw = src.__dict__.get("menace")
        else:
            raw = type(src).__dict__.get("menace")
            if raw is None and hasattr(src, "__dict__"):
                raw = src.__dict__.get("menace")
        if isinstance(raw, property):
            return None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            return int(raw)
        return None

    @staticmethod
    def _effective_menace(src):
        """PRECISION-scaled threat for a live unit or a rules unit class."""
        if src is None:
            return 0
        absolute = BasicAttributes._absolute_menace(src)
        if absolute is not None:
            return absolute
        if not isinstance(src, type):
            try:
                val = src.menace
            except Exception:
                return 0
            if isinstance(val, property):
                return 0
            try:
                return int(val or 0)
            except (TypeError, ValueError):
                return 0
        try:
            from ..worldunit.world_attributes import CreatureAttributes

            base = CreatureAttributes._auto_combat_menace_base(src)
            if not base:
                return 0
            mult = getattr(src, "menace_mult", PRECISION) or PRECISION
            return int(base * mult // PRECISION)
        except Exception:
            return 0

    def add_basic_info_attributes(self, u, attrs):
        """添加基础信息属性"""
        # 基本信息 - HP和MP（如果有的话）
        if hasattr(u, "hp") and hasattr(u, "hp_max"):
            attrs.append(("h", mp.HP, u.hp_status))
            
            # 魔法值/能量
            if hasattr(u, "mana") and hasattr(u, "mana_max") and u.mana_max > 0:
                attrs.append(("n", mp.MANA, u.mana_status))
        
        # 单位简介（总是检查）
        unit_type_name = getattr(u, 'type_name', None) or getattr(u.model, 'type_name', None)
        if unit_type_name:
            intro = style.get(unit_type_name, "intro")
            if intro:
                if isinstance(intro, list):
                    attrs.append(("i", mp.INTRO, intro))
                else:
                    attrs.append(("i", mp.INTRO, [str(intro)]))
            
        # 提供人口（总是检查）
        if hasattr(u.model, "population_provided") and u.model.population_provided > 0:
            pop_provided_text = nb2msg(u.model.population_provided)
            attrs.append(("", mp.POPULATION_PROVIDED, pop_provided_text))
        
        # 建造成本与时间（建筑/单位类型定义）
        if hasattr(u.model, "cost") and u.model.cost:
            cost_text = []
            for i, cost_value in enumerate(u.model.cost):
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
                attrs.append(("", mp.COST, cost_text[:-len(mp.COMMA)]))
        
        if hasattr(u.model, "time_cost") and u.model.time_cost > 0:
            time_text = nb2msg_float(u.model.time_cost / 1000) + mp.SECONDS
            attrs.append(("", mp.TIME, time_text))

        # 所属时代：简单 requirements 中的 phase（如 barracks → feudal_age）
        try:
            from ..worldrequirements import format_belonging_phase_titles

            phase_text = format_belonging_phase_titles(u.model)
            if phase_text:
                attrs.append(("", mp.BELONGS_TO_AGE, phase_text))
        except Exception:
            pass
    
    def add_healing_attributes(self, u, attrs):
        """添加治疗相关属性"""
        # 治疗能力
        if hasattr(u.model, "heal_level") and u.model.heal_level > 0:
            heal_level_text = nb2msg_float(u.model.heal_level)
            attrs.append(("", mp.HEAL_LEVEL, heal_level_text))
            
            # 治疗半径
            if hasattr(u.model, "heal_radius"):
                heal_radius = getattr(u.model, "heal_radius", 0)
                heal_radius_text = nb2msg_float(heal_radius / PRECISION)
                attrs.append(("", mp.HEAL_RADIUS, heal_radius_text))
            
            # 治疗射程（单体瞄准）
            if hasattr(u.model, "heal_range") and u.model.heal_range > 0:
                heal_range_text = nb2msg_float(u.model.heal_range / PRECISION)
                attrs.append(("", mp.HEAL_RANGE, heal_range_text))
            
            # 治疗冷却时间
            if hasattr(u.model, "heal_cd"):
                heal_cd = getattr(u.model, "heal_cd", 7500)
                heal_cd_text = nb2msg_float(heal_cd / 1000)  # 转换为秒
                attrs.append(("", mp.HEAL_CD, heal_cd_text))
            
            # 治疗前摇时间
            if hasattr(u.model, "heal_ready") and u.model.heal_ready > 0:
                heal_ready_text = nb2msg_float(u.model.heal_ready / 1000)  # 转换为秒
                attrs.append(("", mp.HEAL_READY, heal_ready_text))
    
    def add_regeneration_attributes(self, u, attrs):
        """添加回复相关属性"""
        # 生命回复冷却时间
        if hasattr(u.model, "hp_regen_cd") and u.model.hp_regen_cd > 0:
            hp_regen_cd_text = nb2msg_float(u.model.hp_regen_cd / 1000)  # 转换为秒
            attrs.append(("", mp.HP_REGEN_CD, hp_regen_cd_text))
        
        # 生命回复前摇时间
        if hasattr(u.model, "hp_regen_ready") and u.model.hp_regen_ready > 0:
            hp_regen_ready_text = nb2msg_float(u.model.hp_regen_ready / 1000)  # 转换为秒
            attrs.append(("", mp.HP_REGEN_READY, hp_regen_ready_text))
        
        # 生命回复值
        if hasattr(u.model, "hp_regen") and u.model.hp_regen > 0:
            hp_regen_text = nb2msg_float(u.model.hp_regen / PRECISION)
            attrs.append(("", mp.HP_REGEN_NAME, hp_regen_text))
        
        # 法力回复冷却时间
        if hasattr(u.model, "mana_regen_cd") and u.model.mana_regen_cd > 0:
            mana_regen_cd_text = nb2msg_float(u.model.mana_regen_cd / 1000)  # 转换为秒
            attrs.append(("", mp.MANA_REGEN_CD, mana_regen_cd_text))
        
        # 法力回复前摇时间
        if hasattr(u.model, "mana_regen_ready") and u.model.mana_regen_ready > 0:
            mana_regen_ready_text = nb2msg_float(u.model.mana_regen_ready / 1000)  # 转换为秒
            attrs.append(("", mp.MANA_REGEN_READY, mana_regen_ready_text))
        
        # 法力回复值
        if hasattr(u.model, "mana_regen") and u.model.mana_regen > 0:
            mana_regen_text = nb2msg_float(u.model.mana_regen / PRECISION)
            attrs.append(("", mp.MANA_REGEN_NAME, mana_regen_text))
    
    def add_harm_attributes(self, u, attrs):
        """添加伤害能力相关属性"""
        # 伤害能力
        if hasattr(u.model, "harm_level") and u.model.harm_level > 0:
            harm_level_text = nb2msg_float(u.model.harm_level)
            attrs.append(("", mp.HARM_LEVEL, harm_level_text))
            
            # 伤害半径
            if hasattr(u.model, "harm_radius"):
                harm_radius = getattr(u.model, "harm_radius", 0)
                harm_radius_text = nb2msg_float(harm_radius / PRECISION)
                attrs.append(("", mp.HARM_RADIUS, harm_radius_text))
            
            # 伤害射程（单体瞄准）
            if hasattr(u.model, "harm_range") and u.model.harm_range > 0:
                harm_range_text = nb2msg_float(u.model.harm_range / PRECISION)
                attrs.append(("", mp.HARM_RANGE, harm_range_text))
            
            # 伤害冷却时间
            if hasattr(u.model, "harm_cd"):
                harm_cd = getattr(u.model, "harm_cd", 7500)
                harm_cd_text = nb2msg_float(harm_cd / 1000)  # 转换为秒
                attrs.append(("", mp.HARM_CD, harm_cd_text))
            
            # 伤害前摇时间
            if hasattr(u.model, "harm_ready") and u.model.harm_ready > 0:
                harm_ready_text = nb2msg_float(u.model.harm_ready / 1000) + mp.SECONDS
                attrs.append(("", mp.HARM_READY, harm_ready_text))
    
    def add_movement_attributes(self, u, attrs):
        """添加移动相关属性"""
        from .terrain_effective import effective_speed_value

        # 移动速度 - 先检查单位本身，再检查model
        speed_value = 0
        if hasattr(u, "speed"):
            speed_value = getattr(u, "speed", 0)
        elif hasattr(u.model, "speed"):
            speed_value = getattr(u.model, "speed", 0)

        # 当前格：speed_on_terrain 绝对替换，或 speed_vs / 地形 speed 倍率
        if speed_value > 0:
            speed_value = effective_speed_value(u, speed_value)
            
        if speed_value > 0:
            speed_text = nb2msg_float(speed_value / PRECISION)
            attrs.append(("s", mp.SPEED, speed_text))
        
        # 处理单位在各种地形上的移动速度
        if hasattr(u.model, "speed_on_terrain") and u.model.speed_on_terrain:
            speed_terrain_list = getattr(u.model, "speed_on_terrain", [])
            if speed_terrain_list:
                terrain_text = []
                # 处理地形速度列表，格式为[地形类型, 速度值, 地形类型, 速度值, ...]
                for i in range(0, len(speed_terrain_list), 2):
                    if i + 1 < len(speed_terrain_list):
                        terrain_type = speed_terrain_list[i]
                        speed_value = speed_terrain_list[i + 1]
                        # 获取地形类型的标题
                        terrain_title = style.get(terrain_type, "title") or [terrain_type]
                        # 将速度值转换为合适的格式
                        try:
                            # 尝试将速度值转换为数字并乘以1000
                            if isinstance(speed_value, (int, float)):
                                speed_text = nb2msg_float(speed_value)
                            else:
                                # 如果是字符串，尝试转换为整数
                                speed_text = nb2msg_float(int(speed_value))
                        except (ValueError, TypeError):
                            # 如果转换失败，直接显示原始值
                            speed_text = [str(speed_value)]
                        
                        terrain_text.extend(terrain_title)
                        terrain_text.extend(mp.COLON)
                        terrain_text.extend(speed_text)
                        terrain_text.extend(mp.COMMA)
                
                if terrain_text:
                    # 移除最后一个逗号
                    terrain_text = terrain_text[:-1]
                    attrs.append(("", mp.SPEED_ON_TERRAIN, terrain_text))
    
    def add_basic_combat_attributes(self, u, attrs):
        """添加基础战斗属性"""
        # 基础攻击防御属性 - 使用bonus处理函数
        self.main_interface._add_bonus_attribute(attrs, u, "mdg", "m", mp.MELEE_DAMAGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg", "r", mp.RANGE_DAMAGE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdf", "d", mp.MELEE_DEFENSE, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdf", "f", mp.RANGE_DEFENSE, True)
        
        # 暴击属性
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_crit", "m", mp.MDG_CRIT, False, True)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_crit", "", mp.RDG_CRIT, False, True)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_crit_rate", "m", mp.MDG_CRIT_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_crit_rate", "", mp.RDG_CRIT_RATE, False)
        
        # 穿透属性
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_piercing", "", mp.MDG_PIERCING, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_piercing", "", mp.RDG_PIERCING, False)
        self.main_interface._add_bonus_attribute(attrs, u, "mdg_piercing_rate", "", mp.MDG_PIERCING_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdg_piercing_rate", "", mp.RDG_PIERCING_RATE, False)
        
        # 防御暴击率
        self.main_interface._add_bonus_attribute(attrs, u, "mdf_crit_rate", "d", mp.MDF_CRIT_RATE, False)
        self.main_interface._add_bonus_attribute(attrs, u, "rdf_crit_rate", "", mp.RDF_CRIT_RATE, False)

        # 威胁：绝对值（rules 写死的 menace）或自动综合威胁；
        # 权重 menace_mult / menace_mult_vs 与绝对值并列显示。
        src = self._attribute_source(u)
        absolute = self._absolute_menace(src)
        menace_val = absolute if absolute is not None else self._effective_menace(src)
        if menace_val > 0 or absolute is not None:
            attrs.append(("", mp.MENACE, nb2msg_float((absolute if absolute is not None else menace_val) / PRECISION)))

        mult = getattr(src, "menace_mult", PRECISION) or PRECISION
        if isinstance(mult, property):
            mult = PRECISION
        try:
            mult = int(mult)
        except (TypeError, ValueError):
            mult = PRECISION
        # 有威胁时始终显示权重（含默认 1），便于对照绝对威胁/自动威胁
        if menace_val > 0 or absolute is not None or mult != PRECISION:
            attrs.append(("", mp.MENACE_MULT, nb2msg_float(mult / PRECISION)))

        menace_vs = getattr(src, "menace_vs", None) or {}
        if isinstance(menace_vs, dict) and menace_vs:
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                menace_vs,
                mp.MENACE_VS,
                precision_divide=True,
                min_positive=False,
            )

        menace_mult_vs = getattr(src, "menace_mult_vs", None) or {}
        if isinstance(menace_mult_vs, dict) and menace_mult_vs:
            self.main_interface.vs_handler.add_grouped_vs_attribute(
                attrs,
                menace_mult_vs,
                mp.MENACE_MULT_VS,
                precision_divide=True,
                min_positive=False,
            )
    
    def add_sight_attributes(self, u, attrs):
        """添加视野相关属性"""
        # 视野范围 - 先检查单位本身，再检查model
        sight_value = 0
        if hasattr(u, "sight_range"):
            sight_value = getattr(u, "sight_range", 0)
        elif hasattr(u.model, "sight_range"):
            sight_value = getattr(u.model, "sight_range", 0)
            
        if sight_value > 0:
            sight_range_text = nb2msg_float(sight_value / 1000)  # 转换为格子单位
            attrs.append(("v", mp.SIGHT_RANGE, sight_range_text))
        
        # 隐身范围（只有隐身单位才显示）
        if getattr(u.model, "is_a_cloaker", 0) and hasattr(u.model, "cloaking_range") and u.model.cloaking_range > 0:
            cloaking_range_text = nb2msg_float(u.model.cloaking_range / 1000)  # 转换为格子单位
            attrs.append(("", mp.CLOAKING_RANGE, cloaking_range_text))
        
        # 侦测范围（只有侦测单位才显示）
        if getattr(u.model, "is_a_detector", 0) and hasattr(u.model, "detection_range") and u.model.detection_range > 0:
            detection_range_text = nb2msg_float(u.model.detection_range / 1000)  # 转换为格子单位
            attrs.append(("", mp.DETECTION_RANGE, detection_range_text))