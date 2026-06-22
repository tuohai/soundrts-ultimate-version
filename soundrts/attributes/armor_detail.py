"""
护甲详情显示模块
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg_float
from ..clientmedia import voice
from ..definitions import style
from .utils import format_class_text


class ArmorDetail:
    def __init__(self, parent):
        self.parent = parent

    def _show_armor_detail(self, unit, armor_type_name):
        """显示指定护甲类型的详细属性界面"""
        try:
            # 导入 rules
            from ..definitions import rules
            
            # 获取护甲类型定义
            armor_class = rules.unit_class(armor_type_name)
            
            # 如果找不到护甲类型定义，显示基本信息
            if armor_class is None:
                voice.item(mp.NO_SUCH_ATTRIBUTE)
                return
            
            # 保存当前状态，以便返回
            self.parent._saved_attributes_state = {
                'unit': self.parent._attributes_screen_unit,
                'attrs': self.parent._attributes_screen_attrs,
                'index': self.parent._current_attribute_index,
                'sub_index': self.parent._current_sub_item_index,
                'sub_items': self.parent._current_attribute_sub_items
            }
            
            # 切换到详细界面
            self.parent._in_detail_attributes_screen = True
            
            # 构建护甲属性列表
            attrs = []
            
            # 显示护甲名称
            armor_title = style.get(armor_type_name, "title")
            if armor_title:
                if isinstance(armor_title, list):
                    title_text = armor_title
                else:
                    title_text = [str(armor_title)]
            else:
                title_text = [armor_type_name]
            
            attrs.append(("", mp.ARMOR_NAME, title_text))

            intro = style.get(armor_type_name, "intro")
            if intro:
                if isinstance(intro, list):
                    attrs.append(("?", mp.INTRO, intro))
                else:
                    attrs.append(("?", mp.INTRO, [str(intro)]))
            
            # 创建临时护甲实例来获取property属性的值
            try:
                temp_armor = armor_class()
            except:
                temp_armor = None
            
            # 显示护甲类型 (is_a)
            if hasattr(armor_class, "is_a") and armor_class.is_a:
                is_a_text = []
                if isinstance(armor_class.is_a, (list, tuple)):
                    for armor_type in armor_class.is_a:
                        type_title = style.get(armor_type, "title")
                        if type_title:
                            if isinstance(type_title, list):
                                is_a_text.extend(type_title)
                            else:
                                is_a_text.append(str(type_title))
                        else:
                            is_a_text.append(str(armor_type))
                        is_a_text.extend(mp.COMMA)
                    # 移除最后一个逗号
                    if is_a_text and is_a_text[-1] in mp.COMMA:
                        is_a_text = is_a_text[:-1]
                else:
                    # 单个类型
                    type_title = style.get(armor_class.is_a, "title")
                    if type_title:
                        if isinstance(type_title, list):
                            is_a_text.extend(type_title)
                        else:
                            is_a_text.append(str(type_title))
                    else:
                        is_a_text.append(str(armor_class.is_a))
                
                if is_a_text:
                    attrs.append(("i", mp.IS_A, is_a_text))
            
            # 显示护甲职业 (class)
            class_text = format_class_text(armor_class, "armor", rules)
            if class_text:
                attrs.append(("c", mp.CLASS, class_text))
            
            # 显示护甲的各种属性
            # 从护甲类获取基础属性值
            if hasattr(armor_class, "mdf") and armor_class.mdf > 0:
                mdf_text = nb2msg_float(armor_class.mdf / PRECISION)
                attrs.append(("d", mp.MELEE_DEFENSE, mdf_text))
            
            if hasattr(armor_class, "rdf") and armor_class.rdf > 0:
                rdf_text = nb2msg_float(armor_class.rdf / PRECISION)
                attrs.append(("f", mp.RANGE_DEFENSE, rdf_text))
            
            # 显示bonus属性
            mdf_bonus_value = getattr(armor_class, "mdf_bonus", 0) if hasattr(armor_class, "mdf_bonus") else 0
            if mdf_bonus_value and isinstance(mdf_bonus_value, (int, float)) and mdf_bonus_value > 0:
                mdf_bonus_text = nb2msg_float(mdf_bonus_value / PRECISION)
                attrs.append(("", mp.MELEE_DEFENSE + [" "] + mp.BONUS, mdf_bonus_text))
            
            rdf_bonus_value = getattr(armor_class, "rdf_bonus", 0) if hasattr(armor_class, "rdf_bonus") else 0
            if rdf_bonus_value and isinstance(rdf_bonus_value, (int, float)) and rdf_bonus_value > 0:
                rdf_bonus_text = nb2msg_float(rdf_bonus_value / PRECISION)
                attrs.append(("", mp.RANGE_DEFENSE + [" "] + mp.BONUS, rdf_bonus_text))
            
            # 显示其他可能的bonus属性
            mdg_bonus_value = getattr(armor_class, "mdg_bonus", 0) if hasattr(armor_class, "mdg_bonus") else 0
            if mdg_bonus_value and isinstance(mdg_bonus_value, (int, float)) and mdg_bonus_value > 0:
                mdg_bonus_text = nb2msg_float(mdg_bonus_value / PRECISION)
                attrs.append(("", mp.MELEE_DAMAGE + [" "] + mp.BONUS, mdg_bonus_text))
            
            rdg_bonus_value = getattr(armor_class, "rdg_bonus", 0) if hasattr(armor_class, "rdg_bonus") else 0
            if rdg_bonus_value and isinstance(rdg_bonus_value, (int, float)) and rdg_bonus_value > 0:
                rdg_bonus_text = nb2msg_float(rdg_bonus_value / PRECISION)
                attrs.append(("", mp.RANGE_DAMAGE + [" "] + mp.BONUS, rdg_bonus_text))
            
            # 显示生命值bonus
            hp_max_bonus_value = getattr(armor_class, "hp_max_bonus", 0) if hasattr(armor_class, "hp_max_bonus") else 0
            if hp_max_bonus_value and isinstance(hp_max_bonus_value, (int, float)) and hp_max_bonus_value > 0:
                hp_max_bonus_text = nb2msg_float(hp_max_bonus_value / PRECISION)
                attrs.append(("", mp.HIT_POINTS + [" "] + mp.BONUS, hp_max_bonus_text))
            
            # 显示速度bonus
            speed_bonus_value = getattr(armor_class, "speed_bonus", 0) if hasattr(armor_class, "speed_bonus") else 0
            if speed_bonus_value and isinstance(speed_bonus_value, (int, float)) and speed_bonus_value > 0:
                speed_bonus_text = nb2msg_float(speed_bonus_value / PRECISION)
                attrs.append(("", mp.MOVE_SPEED + [" "] + mp.BONUS, speed_bonus_text))
            
            # 显示视野范围bonus
            sight_range_bonus_value = getattr(armor_class, "sight_range_bonus", 0) if hasattr(armor_class, "sight_range_bonus") else 0
            if sight_range_bonus_value and isinstance(sight_range_bonus_value, (int, float)) and sight_range_bonus_value > 0:
                sight_range_bonus_text = nb2msg_float(sight_range_bonus_value / PRECISION)
                attrs.append(("", mp.SIGHT_RANGE_NAME + [" "] + mp.BONUS, sight_range_bonus_text))
            
            # 显示魔法值bonus
            mana_max_bonus_value = getattr(armor_class, "mana_max_bonus", 0) if hasattr(armor_class, "mana_max_bonus") else 0
            if mana_max_bonus_value and isinstance(mana_max_bonus_value, (int, float)) and mana_max_bonus_value > 0:
                mana_max_bonus_text = nb2msg_float(mana_max_bonus_value / PRECISION)
                attrs.append(("", mp.MANA_NAME + [" "] + mp.BONUS, mana_max_bonus_text))
            
            # 显示生命回复bonus
            hp_regen_bonus_value = getattr(armor_class, "hp_regen_bonus", 0) if hasattr(armor_class, "hp_regen_bonus") else 0
            if hp_regen_bonus_value and isinstance(hp_regen_bonus_value, (int, float)) and hp_regen_bonus_value > 0:
                hp_regen_bonus_text = nb2msg_float(hp_regen_bonus_value / PRECISION)
                attrs.append(("", mp.HP_REGEN_NAME + [" "] + mp.BONUS, hp_regen_bonus_text))
            
            # 显示魔法回复bonus
            mana_regen_bonus_value = getattr(armor_class, "mana_regen_bonus", 0) if hasattr(armor_class, "mana_regen_bonus") else 0
            if mana_regen_bonus_value and isinstance(mana_regen_bonus_value, (int, float)) and mana_regen_bonus_value > 0:
                mana_regen_bonus_text = nb2msg_float(mana_regen_bonus_value / PRECISION)
                attrs.append(("", mp.MANA_REGEN_NAME + [" "] + mp.BONUS, mana_regen_bonus_text))
            
            # 显示可使用的科技 (can_use_tech)
            if hasattr(armor_class, "can_use_tech") and armor_class.can_use_tech:
                tech_text = []
                if isinstance(armor_class.can_use_tech, (list, tuple)):
                    for tech_name in armor_class.can_use_tech:
                        tech_title = style.get(tech_name, "title")
                        if tech_title:
                            if isinstance(tech_title, list):
                                tech_text.extend(tech_title)
                            else:
                                tech_text.append(str(tech_title))
                        else:
                            tech_text.append(str(tech_name))
                        tech_text.extend(mp.COMMA)
                    # 移除最后一个逗号
                    if tech_text and tech_text[-1] in mp.COMMA:
                        tech_text = tech_text[:-1]
                else:
                    # 单个科技
                    tech_title = style.get(armor_class.can_use_tech, "title")
                    if tech_title:
                        if isinstance(tech_title, list):
                            tech_text.extend(tech_title)
                        else:
                            tech_text.append(str(tech_title))
                    else:
                        tech_text.append(str(armor_class.can_use_tech))
                
                if tech_text:
                    attrs.append(("", mp.CAN_USE_TECH, tech_text))
            
            # 创建临时护甲对象用于显示
            class SimpleArmor:
                def __init__(self):
                    self.type_name = armor_type_name
                
                @property
                def title(self):
                    return title_text
                
                @property
                def hp_status(self):
                    return ["无生命值"]
                
                @property
                def mana_status(self):
                    return ["无魔法值"]
                
                @property
                def upgrades_status(self):
                    return []
            
            # 设置新的属性界面
            self.parent._attributes_screen_unit = SimpleArmor()
            self.parent._attributes_screen_attrs = attrs
            self.parent._current_attribute_index = 0
            self.parent._current_sub_item_index = 0
            self.parent._current_attribute_sub_items = []
            
            # 播放护甲名称
            if len(attrs) > 1:
                voice.item(title_text + ["的属性"])
            else:
                voice.item(title_text + ["没有可用属性"])
            
            # 显示第一个属性
            if len(attrs) > 1:
                self.parent.main_display._display_current_attribute()
            
        except Exception as e:
            # 错误处理
            voice.item(["显示护甲详情时出错"] + [str(e)])