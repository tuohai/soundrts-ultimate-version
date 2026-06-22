"""
武器详情显示模块
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from ..clientmedia import voice
from ..definitions import style
from .utils import format_class_text


class WeaponDetail:
    def __init__(self, parent):
        self.parent = parent

    def _show_weapon_detail(self, unit, weapon_type_name):
        """显示指定武器类型的详细属性界面"""
        try:
            # 导入 rules
            from ..definitions import rules
            
            # 获取武器类型定义
            weapon_class = rules.unit_class(weapon_type_name)
            
            # 如果找不到武器类型定义，显示基本信息
            if weapon_class is None:
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
            
            # 构建武器属性列表
            attrs = []
            
            # 显示武器名称
            weapon_title = style.get(weapon_type_name, "title")
            if weapon_title:
                if isinstance(weapon_title, list):
                    title_text = weapon_title
                else:
                    title_text = [str(weapon_title)]
            else:
                title_text = [weapon_type_name]
            
            attrs.append(("", mp.WEAPON_NAME, title_text))

            intro = style.get(weapon_type_name, "intro")
            if intro:
                if isinstance(intro, list):
                    attrs.append(("?", mp.INTRO, intro))
                else:
                    attrs.append(("?", mp.INTRO, [str(intro)]))
            
            # 创建临时武器实例来获取property属性的值
            try:
                temp_weapon = weapon_class()
            except:
                temp_weapon = None
            
            # 显示武器类型 (is_a)
            if hasattr(weapon_class, "is_a") and weapon_class.is_a:
                is_a_text = []
                if isinstance(weapon_class.is_a, (list, tuple)):
                    for weapon_type in weapon_class.is_a:
                        type_title = style.get(weapon_type, "title")
                        if type_title:
                            if isinstance(type_title, list):
                                is_a_text.extend(type_title)
                            else:
                                is_a_text.append(str(type_title))
                        else:
                            is_a_text.append(str(weapon_type))
                        is_a_text.extend(mp.COMMA)
                    # 移除最后一个逗号
                    if is_a_text and is_a_text[-1] in mp.COMMA:
                        is_a_text = is_a_text[:-1]
                else:
                    # 单个类型
                    type_title = style.get(weapon_class.is_a, "title")
                    if type_title:
                        if isinstance(type_title, list):
                            is_a_text.extend(type_title)
                        else:
                            is_a_text.append(str(type_title))
                    else:
                        is_a_text.append(str(weapon_class.is_a))
                
                if is_a_text:
                    attrs.append(("i", mp.IS_A, is_a_text))
            
            # 显示武器职业 (class)
            class_text = format_class_text(weapon_class, "weapon", rules)
            if class_text:
                attrs.append(("c", mp.CLASS, class_text))
            
            # 显示武器的攻击力
            mdg_value = getattr(weapon_class, "mdg", 0) if hasattr(weapon_class, "mdg") else 0
            if mdg_value and isinstance(mdg_value, (int, float)) and mdg_value > 0:
                mdg_text = nb2msg_float(mdg_value / PRECISION)
                attrs.append(("m", mp.MELEE_DAMAGE, mdg_text))
            
            rdg_value = getattr(weapon_class, "rdg", 0) if hasattr(weapon_class, "rdg") else 0
            if rdg_value and isinstance(rdg_value, (int, float)) and rdg_value > 0:
                rdg_text = nb2msg_float(rdg_value / PRECISION)
                attrs.append(("r", mp.RANGE_DAMAGE, rdg_text))
            
            # 显示bonus属性
            mdg_bonus_value = getattr(weapon_class, "mdg_bonus", 0) if hasattr(weapon_class, "mdg_bonus") else 0
            if mdg_bonus_value and isinstance(mdg_bonus_value, (int, float)) and mdg_bonus_value > 0:
                mdg_bonus_text = nb2msg_float(mdg_bonus_value / PRECISION)
                attrs.append(("", mp.MELEE_DAMAGE + [" "] + mp.BONUS, mdg_bonus_text))

                
            rdg_bonus_value = getattr(weapon_class, "rdg_bonus", 0) if hasattr(weapon_class, "rdg_bonus") else 0

            if rdg_bonus_value and isinstance(rdg_bonus_value, (int, float)) and rdg_bonus_value > 0:
                rdg_bonus_text = nb2msg_float(rdg_bonus_value / PRECISION)
                attrs.append(("", mp.RANGE_DAMAGE + [" "] + mp.BONUS, rdg_bonus_text))

            
            # 显示防御力
            mdf_value = getattr(weapon_class, "mdf", 0) if hasattr(weapon_class, "mdf") else 0
            if mdf_value and isinstance(mdf_value, (int, float)) and mdf_value > 0:
                mdf_text = nb2msg_float(mdf_value / PRECISION)
                attrs.append(("d", mp.MELEE_DEFENSE, mdf_text))

            
            rdf_value = getattr(weapon_class, "rdf", 0) if hasattr(weapon_class, "rdf") else 0
            if rdf_value and isinstance(rdf_value, (int, float)) and rdf_value > 0:
                rdf_text = nb2msg_float(rdf_value / PRECISION)
                attrs.append(("f", mp.RANGE_DEFENSE, rdf_text))

            
            # 显示攻击间隔
            mdg_cd_value = getattr(weapon_class, "mdg_cd", 0) if hasattr(weapon_class, "mdg_cd") else 0
            if mdg_cd_value and isinstance(mdg_cd_value, (int, float)) and mdg_cd_value > 0:
                mdg_cd_text = nb2msg_float(mdg_cd_value / PRECISION) + mp.SECONDS
                attrs.append(("a", mp.MDG_CD, mdg_cd_text))

            
            rdg_cd_value = getattr(weapon_class, "rdg_cd", 0) if hasattr(weapon_class, "rdg_cd") else 0
            if rdg_cd_value and isinstance(rdg_cd_value, (int, float)) and rdg_cd_value > 0:
                rdg_cd_text = nb2msg_float(rdg_cd_value / PRECISION) + mp.SECONDS
                attrs.append(("c", mp.RDG_CD, rdg_cd_text))

            
            # 显示攻击范围
            mdg_range_value = getattr(weapon_class, "mdg_range", 0) if hasattr(weapon_class, "mdg_range") else 0
            if mdg_range_value and isinstance(mdg_range_value, (int, float)) and mdg_range_value > 0:
                mdg_range_text = nb2msg_float(mdg_range_value / PRECISION)
                attrs.append(("g", mp.MDG_RANGE, mdg_range_text))

            
            rdg_range_value = getattr(weapon_class, "rdg_range", 0) if hasattr(weapon_class, "rdg_range") else 0
            if rdg_range_value and isinstance(rdg_range_value, (int, float)) and rdg_range_value > 0:
                rdg_range_text = nb2msg_float(rdg_range_value / PRECISION)
                attrs.append(("e", mp.RANGED_RANGE, rdg_range_text))

            
            # 显示暴击属性
            mdg_crit_value = getattr(weapon_class, "mdg_crit", 0) if hasattr(weapon_class, "mdg_crit") else 0
            if mdg_crit_value and isinstance(mdg_crit_value, (int, float)) and mdg_crit_value > 0:
                mdg_crit_text = nb2msg_float(mdg_crit_value / 1000)  # 暴击倍率除以1000
                attrs.append(("", mp.MDG_CRIT, mdg_crit_text))

            
            rdg_crit_value = getattr(weapon_class, "rdg_crit", 0) if hasattr(weapon_class, "rdg_crit") else 0
            if rdg_crit_value and isinstance(rdg_crit_value, (int, float)) and rdg_crit_value > 0:
                rdg_crit_text = nb2msg_float(rdg_crit_value / 1000)  # 暴击倍率除以1000
                attrs.append(("", mp.RDG_CRIT, rdg_crit_text))

            
            mdg_crit_rate_value = getattr(weapon_class, "mdg_crit_rate", 0) if hasattr(weapon_class, "mdg_crit_rate") else 0
            if mdg_crit_rate_value and isinstance(mdg_crit_rate_value, (int, float)) and mdg_crit_rate_value > 0:
                mdg_crit_rate_text = nb2msg_float(mdg_crit_rate_value / PRECISION) + ["%"]
                attrs.append(("", mp.MDG_CRIT_RATE, mdg_crit_rate_text))

            
            rdg_crit_rate_value = getattr(weapon_class, "rdg_crit_rate", 0) if hasattr(weapon_class, "rdg_crit_rate") else 0
            if rdg_crit_rate_value and isinstance(rdg_crit_rate_value, (int, float)) and rdg_crit_rate_value > 0:
                rdg_crit_rate_text = nb2msg_float(rdg_crit_rate_value / PRECISION) + ["%"]
                attrs.append(("", mp.RDG_CRIT_RATE, rdg_crit_rate_text))

            
            # 显示溅射属性
            mdg_splash_value = getattr(weapon_class, "mdg_splash", 0) if hasattr(weapon_class, "mdg_splash") else 0
            if mdg_splash_value and isinstance(mdg_splash_value, (int, float)) and mdg_splash_value > 0:
                mdg_splash_text = nb2msg_float(mdg_splash_value / PRECISION)
                attrs.append(("", mp.MDG_SPLASH, mdg_splash_text))

            
            rdg_splash_value = getattr(weapon_class, "rdg_splash", 0) if hasattr(weapon_class, "rdg_splash") else 0
            if rdg_splash_value and isinstance(rdg_splash_value, (int, float)) and rdg_splash_value > 0:
                rdg_splash_text = nb2msg_float(rdg_splash_value / PRECISION)
                attrs.append(("", mp.RDG_SPLASH, rdg_splash_text))

            
            # 显示穿甲属性
            mdg_piercing_value = getattr(weapon_class, "mdg_piercing", 0) if hasattr(weapon_class, "mdg_piercing") else 0
            if mdg_piercing_value and isinstance(mdg_piercing_value, (int, float)) and mdg_piercing_value > 0:
                mdg_piercing_text = nb2msg_float(mdg_piercing_value / PRECISION)
                attrs.append(("", mp.MDG_PIERCING, mdg_piercing_text))

            
            rdg_piercing_value = getattr(weapon_class, "rdg_piercing", 0) if hasattr(weapon_class, "rdg_piercing") else 0
            if rdg_piercing_value and isinstance(rdg_piercing_value, (int, float)) and rdg_piercing_value > 0:
                rdg_piercing_text = nb2msg_float(rdg_piercing_value / PRECISION)
                attrs.append(("", mp.RDG_PIERCING, rdg_piercing_text))

            
            # 显示可使用的科技 (can_use_tech)
            if hasattr(weapon_class, "can_use_tech") and weapon_class.can_use_tech:
                tech_text = []
                if isinstance(weapon_class.can_use_tech, (list, tuple)):
                    for tech_name in weapon_class.can_use_tech:
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
                    tech_title = style.get(weapon_class.can_use_tech, "title")
                    if tech_title:
                        if isinstance(tech_title, list):
                            tech_text.extend(tech_title)
                        else:
                            tech_text.append(str(tech_title))
                    else:
                        tech_text.append(str(weapon_class.can_use_tech))
                
                if tech_text:
                    attrs.append(("", mp.CAN_USE_TECH, tech_text))
            

            
            # 创建一个简单的临时对象用于属性界面
            class SimpleWeapon:
                def __init__(self):
                    self.model = weapon_class
                    self.hp = 0
                    self.hp_max = 0
                    self.mana = 0
                    self.mana_max = 0
                    self.is_a_building = False
                    
                @property
                def hp_status(self):
                    return ["无生命值"]
                    
                @property
                def mana_status(self):
                    return ["无魔法值"]
            
            # 设置新的属性界面
            self.parent._attributes_screen_unit = SimpleWeapon()
            self.parent._attributes_screen_attrs = attrs
            self.parent._current_attribute_index = 0
            self.parent._current_sub_item_index = 0
            self.parent._current_attribute_sub_items = []
            
            # 播放武器名称
            if len(attrs) > 1:
                voice.item(title_text + ["的属性"])
            else:
                voice.item(title_text + ["没有可用属性"])
            
            # 显示第一个属性
            if len(attrs) > 1:
                self.parent.main_display._display_current_attribute()
            
        except Exception as e:
            # 错误处理
            voice.item(["显示武器详情时出错"] + [str(e)])