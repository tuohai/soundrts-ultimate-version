"""
单位详情显示模块
处理单位类型详细信息的显示 - 完全按照原始attributes_face.py实现
"""

from soundrts.lib.voice import voice
from ..lib.msgs import nb2msg, nb2msg_float
from ..lib.nofloat import PRECISION
from .. import msgparts as mp
from ..definitions import style
from .effect_formatter import EffectFormatter
from .utils import RULES_DETAIL_ATTRS, class_attr_for_detail

class UnitDetail:
    def __init__(self, parent):
        self.parent = parent
        self.effect_formatter = EffectFormatter(self.parent)  # 创建effect formatter实例
    
    def _show_unit_detail(self, unit_type_name):
        """显示指定单位类型的详细属性界面 - 完全按照原始代码实现"""
        try:
            # 导入 rules
            from ..definitions import rules
            from ..worldupgrade import Upgrade
            from ..worldskill import Skill
            
            # 获取单位类型定义
            unit_class = rules.unit_class(unit_type_name)
            
            # 判断是否为科技或技能类型
            is_tech = isinstance(unit_class, type) and (issubclass(unit_class, Upgrade) or issubclass(unit_class, Skill))
            
            # 创建一个更完整的临时单位对象，模拟真实单位的所有属性 - 完全复制原始代码
            class TempUnit:
                def __init__(self, unit_class, unit_type_name):
                    # 设置基本属性
                    self.model = unit_class
                    self.title = style.get(unit_type_name, "title")
                    self.type_name = unit_type_name  # 添加type_name属性
                    
                    # 从单位类获取所有属性，保持原始值
                    # 生命值
                    if hasattr(unit_class, "hp_max"):
                        self.hp_max = unit_class.hp_max
                        self.hp = unit_class.hp_max  # 假设满血
                    
                    # 魔法值
                    if hasattr(unit_class, "mana_max"):
                        self.mana_max = getattr(unit_class, "mana_max", 0)
                        self.mana = self.mana_max
                    
                    # 武器系统
                    if hasattr(unit_class, "weapons"):
                        self.weapons = getattr(unit_class, "weapons", [])
                    else:
                        self.weapons = []
                    
                    # 护甲系统
                    if hasattr(unit_class, "armor"):
                        self.armor = getattr(unit_class, "armor", [])
                    else:
                        self.armor = []
                    
                    # 可用武器列表
                    if hasattr(unit_class, "available_weapons"):
                        self.available_weapons = getattr(unit_class, "available_weapons", [])
                    else:
                        self.available_weapons = self.weapons[:]  # 复制武器列表
                    
                    # 当前武器
                    if self.weapons:
                        self.current_weapon = self.weapons[0]
                    else:
                        self.current_weapon = None
                    
                    # 升级信息（如果有的话）
                    if hasattr(unit_class, "upgrades"):
                        self.upgrades = getattr(unit_class, "upgrades", [])
                    
                    # 属性界面从 rules 类读取能力属性（can_train 等为 @property，不能 getattr 类）
                    for attr in RULES_DETAIL_ATTRS + ("speed", "sight_range"):
                        value = class_attr_for_detail(unit_class, attr)
                        if value:
                            setattr(self, attr, value)
                    
                @property
                def hp_status(self):
                    if hasattr(self, "hp") and hasattr(self, "hp_max"):
                        return nb2msg(int(self.hp/PRECISION)) + mp.ON + nb2msg(int(self.hp_max/PRECISION))
                    return ["无生命值信息"]
                    
                @property
                def mana_status(self):
                    if hasattr(self, "mana") and hasattr(self, "mana_max") and self.mana_max > 0:
                        return nb2msg(int(self.mana/PRECISION)) + mp.ON + nb2msg(int(self.mana_max/PRECISION))
                    return ["无魔法值信息"]
                
                @property
                def upgrades_status(self):
                    """获取升级状态信息"""
                    if hasattr(self, "upgrades") and self.upgrades:
                        upgrades_list = []
                        for upgrade in self.upgrades:
                            upgrade_title = style.get(upgrade, "title")
                            if upgrade_title:
                                # 确保 upgrade_title 是列表
                                if isinstance(upgrade_title, list):
                                    upgrades_list.extend(upgrade_title)
                                else:
                                    upgrades_list.append(str(upgrade_title))
                                upgrades_list.extend(mp.COMMA)
                        if upgrades_list:
                            return upgrades_list[:-1]  # 移除最后一个逗号
                    return []
            
            # 创建临时单位对象
            temp_unit = TempUnit(unit_class, unit_type_name)
            
            # 保存当前状态，以便返回
            self.parent._saved_attributes_state = {
                'unit': self.parent._attributes_screen_unit,
                'attrs': self.parent._attributes_screen_attrs,
                'index': self.parent._current_attribute_index,
                'sub_index': self.parent._current_sub_item_index,
                'sub_items': self.parent._current_attribute_sub_items
            }
            
            # 设置详细属性界面标志
            self.parent._in_detail_attributes_screen = True
            
            # 设置新的单位
            self.parent._attributes_screen_unit = temp_unit
            
            # 重新调用完整的属性构建逻辑，完全按照原始代码实现
            u = temp_unit
            attrs = []
            
            if is_tech:
                self.parent.main_display.display_interface.populate_tech_attributes(
                    u, attrs, self.effect_formatter
                )
            else:
                # 单位/建筑：与主属性界面相同的全量属性
                self.parent.main_display.display_interface.populate_unit_attributes(u, attrs)
            
            # 设置属性
            self.parent._attributes_screen_attrs = attrs
            self.parent._current_attribute_index = 0
            self.parent._current_sub_item_index = 0
            self.parent._current_attribute_sub_items = []
            
            # 刷新详情界面的按键绑定（成本/效果等首字母跳转）
            self.parent.key_bindings._setup_attributes_screen_bindings()
            # 播放属性界面声音
            self.parent.main_display._display_current_attribute()
            
        except Exception as e:
            voice.info(f"显示单位详情时出错: {e}")
            print(f"Error in _show_unit_detail: {e}")
    
    def _format_effect_description(self, effect_def):
        """格式化效果描述 - 委托给effect_formatter"""
        return self.effect_formatter._format_effect_description(effect_def)
    
    def _add_weapon_armor_attributes(self, attrs, u):
        """添加武器和护甲属性 - 按照原始代码实现，并显示武器/护甲的攻击防御属性"""
        print(f"DEBUG: Adding weapon/armor attributes")
        print(f"DEBUG: Unit has weapons: {hasattr(u, 'weapons')}, weapons: {getattr(u, 'weapons', [])}")
        print(f"DEBUG: Unit has armor: {hasattr(u, 'armor')}, armor: {getattr(u, 'armor', [])}")
        
        # 武器信息显示 - 完全按照原始代码，并添加武器属性
        if hasattr(u, 'weapons') and u.weapons:
            weapon_info = []
            
            # 获取当前武器
            current_weapon = None
            if hasattr(u, 'current_weapon'):
                current_weapon = u.current_weapon
            elif hasattr(u.model, 'current_weapon'):
                current_weapon = u.model.current_weapon
            
            # 如果没有current_weapon或者为None，使用第一个武器
            if not current_weapon and u.weapons:
                current_weapon = u.weapons[0]
            
            if current_weapon:
                weapon_title = style.get(current_weapon, "title")
                if weapon_title:
                    if isinstance(weapon_title, list):
                        weapon_info.extend(weapon_title)
                    else:
                        weapon_info.append(str(weapon_title))
                else:
                    weapon_info.append(current_weapon)
                
                # 如果有多个武器，显示可切换提示
                if len(u.weapons) > 1:
                    weapon_info.extend(mp.COMMA)
                    weapon_info.extend(mp.SWITCHABLE)
            
            if weapon_info:
                attrs.append(("w", mp.CURRENT_WEAPON, weapon_info))
                print(f"DEBUG: Added current weapon: {weapon_info}")
            
            # 添加武器的攻击属性 - 这是关键！
            if current_weapon:
                try:
                    from ..definitions import rules
                    weapon_class = rules.unit_class(current_weapon)
                    print(f"DEBUG: Weapon class for {current_weapon}: {weapon_class}")
                    
                    if weapon_class:
                        # 显示武器的攻击力（安全获取属性值）
                        mdg_value = getattr(weapon_class, "mdg", 0) if hasattr(weapon_class, "mdg") else 0
                        if isinstance(mdg_value, (int, float)) and mdg_value > 0:
                            mdg_text = nb2msg_float(mdg_value / PRECISION)
                            attrs.append(("m", mp.MELEE_DAMAGE, mdg_text))
                            print(f"DEBUG: Added weapon MDG: {mdg_text} (raw: {mdg_value})")
                        
                        rdg_value = getattr(weapon_class, "rdg", 0) if hasattr(weapon_class, "rdg") else 0
                        if isinstance(rdg_value, (int, float)) and rdg_value > 0:
                            rdg_text = nb2msg_float(rdg_value / PRECISION)
                            attrs.append(("r", mp.RANGE_DAMAGE, rdg_text))
                            print(f"DEBUG: Added weapon RDG: {rdg_text} (raw: {rdg_value})")
                        
                        # 显示武器的bonus属性 - 这是新增的！
                        mdg_bonus_value = getattr(weapon_class, "mdg_bonus", 0) if hasattr(weapon_class, "mdg_bonus") else 0
                        if isinstance(mdg_bonus_value, (int, float)) and mdg_bonus_value > 0:
                            mdg_bonus_text = nb2msg_float(mdg_bonus_value / PRECISION)
                            attrs.append(("", mp.MELEE_DAMAGE + [" "] + mp.BONUS, mdg_bonus_text))
                            print(f"DEBUG: Added weapon MDG_BONUS: {mdg_bonus_text} (raw: {mdg_bonus_value})")
                        
                        rdg_bonus_value = getattr(weapon_class, "rdg_bonus", 0) if hasattr(weapon_class, "rdg_bonus") else 0
                        if isinstance(rdg_bonus_value, (int, float)) and rdg_bonus_value > 0:
                            rdg_bonus_text = nb2msg_float(rdg_bonus_value / PRECISION)
                            attrs.append(("", mp.RANGE_DAMAGE + [" "] + mp.BONUS, rdg_bonus_text))
                            print(f"DEBUG: Added weapon RDG_BONUS: {rdg_bonus_text} (raw: {rdg_bonus_value})")
                        
                        # 显示武器的防御力bonus
                        mdf_bonus_value = getattr(weapon_class, "mdf_bonus", 0) if hasattr(weapon_class, "mdf_bonus") else 0
                        if isinstance(mdf_bonus_value, (int, float)) and mdf_bonus_value > 0:
                            mdf_bonus_text = nb2msg_float(mdf_bonus_value / PRECISION)
                            attrs.append(("", mp.MELEE_DEFENSE + [" "] + mp.BONUS, mdf_bonus_text))
                            print(f"DEBUG: Added weapon MDF_BONUS: {mdf_bonus_text} (raw: {mdf_bonus_value})")
                        
                        rdf_bonus_value = getattr(weapon_class, "rdf_bonus", 0) if hasattr(weapon_class, "rdf_bonus") else 0
                        if isinstance(rdf_bonus_value, (int, float)) and rdf_bonus_value > 0:
                            rdf_bonus_text = nb2msg_float(rdf_bonus_value / PRECISION)
                            attrs.append(("", mp.RANGE_DEFENSE + [" "] + mp.BONUS, rdf_bonus_text))
                            print(f"DEBUG: Added weapon RDF_BONUS: {rdf_bonus_text} (raw: {rdf_bonus_value})")
                        
                        # 显示武器的攻击间隔
                        mdg_cd_value = getattr(weapon_class, "mdg_cd", 0) if hasattr(weapon_class, "mdg_cd") else 0
                        if isinstance(mdg_cd_value, (int, float)) and mdg_cd_value > 0:
                            mdg_cd_text = nb2msg_float(mdg_cd_value / PRECISION) + mp.SECONDS
                            attrs.append(("a", mp.MDG_CD, mdg_cd_text))
                            print(f"DEBUG: Added weapon MDG_CD: {mdg_cd_text}")
                        
                        rdg_cd_value = getattr(weapon_class, "rdg_cd", 0) if hasattr(weapon_class, "rdg_cd") else 0
                        if isinstance(rdg_cd_value, (int, float)) and rdg_cd_value > 0:
                            rdg_cd_text = nb2msg_float(rdg_cd_value / PRECISION) + mp.SECONDS
                            attrs.append(("c", mp.RDG_CD, rdg_cd_text))
                            print(f"DEBUG: Added weapon RDG_CD: {rdg_cd_text}")
                        
                        # 显示武器的攻击范围
                        mdg_range_value = getattr(weapon_class, "mdg_range", 0) if hasattr(weapon_class, "mdg_range") else 0
                        if isinstance(mdg_range_value, (int, float)) and mdg_range_value > 0:
                            mdg_range_text = nb2msg_float(mdg_range_value / PRECISION)
                            attrs.append(("g", mp.MDG_RANGE, mdg_range_text))
                            print(f"DEBUG: Added weapon MDG_RANGE: {mdg_range_text}")
                        
                        rdg_range_value = getattr(weapon_class, "rdg_range", 0) if hasattr(weapon_class, "rdg_range") else 0
                        if isinstance(rdg_range_value, (int, float)) and rdg_range_value > 0:
                            rdg_range_text = nb2msg_float(rdg_range_value / PRECISION)
                            attrs.append(("e", mp.RANGED_RANGE, rdg_range_text))
                            print(f"DEBUG: Added weapon RDG_RANGE: {rdg_range_text}")
                
                except Exception as e:
                    print(f"DEBUG: Error getting weapon attributes: {e}")
            
            # 如果有多个武器，显示所有可用武器，并支持导航
            if len(u.weapons) > 1:
                weapon_items = []
                for weapon_name in u.weapons:
                    weapon_title = style.get(weapon_name, "title")
                    if weapon_title:
                        if isinstance(weapon_title, list):
                            weapon_items.append(weapon_title)
                        else:
                            weapon_items.append([str(weapon_title)])
                    else:
                        weapon_items.append([weapon_name])
                
                if weapon_items:
                    # 保存为特殊格式，用 "AVAILABLE_WEAPONS_ITEMS" 标记这是可导航的项目列表
                    attrs.append(("", mp.AVAILABLE_WEAPONS, ("AVAILABLE_WEAPONS_ITEMS", weapon_items)))
                    print(f"DEBUG: Added available weapons: {weapon_items}")
        
        # 护甲信息显示 - 按照原始代码，并添加护甲属性
        if hasattr(u, 'armor') and u.armor:
            armor_info = []
            
            # 获取当前护甲
            current_armor = None
            if hasattr(u, 'current_armor'):
                current_armor = u.current_armor
            elif hasattr(u.model, 'current_armor'):
                current_armor = u.model.current_armor
            
            # 如果没有current_armor或者为None，使用第一个护甲
            if not current_armor and u.armor:
                current_armor = u.armor[0] if isinstance(u.armor, list) else u.armor
            
            if current_armor:
                armor_title = style.get(current_armor, "title")
                if armor_title:
                    if isinstance(armor_title, list):
                        armor_info.extend(armor_title)
                    else:
                        armor_info.append(str(armor_title))
                else:
                    armor_info.append(current_armor)
            
            if armor_info:
                attrs.append(("", mp.CURRENT_ARMOR, armor_info))
                print(f"DEBUG: Added current armor: {armor_info}")
            
            # 添加护甲的防御属性 - 这也是关键！
            if current_armor:
                try:
                    from ..definitions import rules
                    armor_class = rules.unit_class(current_armor)
                    print(f"DEBUG: Armor class for {current_armor}: {armor_class}")
                    
                    if armor_class:
                        # 显示护甲的防御力（安全获取属性值）
                        mdf_value = getattr(armor_class, "mdf", 0) if hasattr(armor_class, "mdf") else 0
                        if isinstance(mdf_value, (int, float)) and mdf_value > 0:
                            mdf_text = nb2msg_float(mdf_value / PRECISION)
                            attrs.append(("d", mp.MELEE_DEFENSE, mdf_text))
                            print(f"DEBUG: Added armor MDF: {mdf_text} (raw: {mdf_value})")
                        
                        rdf_value = getattr(armor_class, "rdf", 0) if hasattr(armor_class, "rdf") else 0
                        if isinstance(rdf_value, (int, float)) and rdf_value > 0:
                            rdf_text = nb2msg_float(rdf_value / PRECISION)
                            attrs.append(("f", mp.RANGE_DEFENSE, rdf_text))
                            print(f"DEBUG: Added armor RDF: {rdf_text} (raw: {rdf_value})")
                        
                        # 显示护甲的bonus属性 - 这是新增的！
                        mdf_bonus_value = getattr(armor_class, "mdf_bonus", 0) if hasattr(armor_class, "mdf_bonus") else 0
                        if isinstance(mdf_bonus_value, (int, float)) and mdf_bonus_value > 0:
                            mdf_bonus_text = nb2msg_float(mdf_bonus_value / PRECISION)
                            attrs.append(("", mp.MELEE_DEFENSE + [" "] + mp.BONUS, mdf_bonus_text))
                            print(f"DEBUG: Added armor MDF_BONUS: {mdf_bonus_text} (raw: {mdf_bonus_value})")
                        
                        rdf_bonus_value = getattr(armor_class, "rdf_bonus", 0) if hasattr(armor_class, "rdf_bonus") else 0
                        if isinstance(rdf_bonus_value, (int, float)) and rdf_bonus_value > 0:
                            rdf_bonus_text = nb2msg_float(rdf_bonus_value / PRECISION)
                            attrs.append(("", mp.RANGE_DEFENSE + [" "] + mp.BONUS, rdf_bonus_text))
                            print(f"DEBUG: Added armor RDF_BONUS: {rdf_bonus_text} (raw: {rdf_bonus_value})")
                        
                        # 显示护甲可能的攻击属性（某些护甲可能有攻击力）
                        mdg_bonus_value = getattr(armor_class, "mdg_bonus", 0) if hasattr(armor_class, "mdg_bonus") else 0
                        if isinstance(mdg_bonus_value, (int, float)) and mdg_bonus_value > 0:
                            mdg_bonus_text = nb2msg_float(mdg_bonus_value / PRECISION)
                            attrs.append(("", mp.MELEE_DAMAGE + [" "] + mp.BONUS, mdg_bonus_text))
                            print(f"DEBUG: Added armor MDG_BONUS: {mdg_bonus_text} (raw: {mdg_bonus_value})")
                        
                        rdg_bonus_value = getattr(armor_class, "rdg_bonus", 0) if hasattr(armor_class, "rdg_bonus") else 0
                        if isinstance(rdg_bonus_value, (int, float)) and rdg_bonus_value > 0:
                            rdg_bonus_text = nb2msg_float(rdg_bonus_value / PRECISION)
                            attrs.append(("", mp.RANGE_DAMAGE + [" "] + mp.BONUS, rdg_bonus_text))
                            print(f"DEBUG: Added armor RDG_BONUS: {rdg_bonus_text} (raw: {rdg_bonus_value})")
                
                except Exception as e:
                    print(f"DEBUG: Error getting armor attributes: {e}")
    
    def _add_all_original_attributes(self, attrs, u):
        """完全按照原始代码添加所有属性"""
        print(f"DEBUG: Starting to add attributes. Current attrs count: {len(attrs)}")
        print(f"DEBUG: Unit model type: {type(u.model)}")
        print(f"DEBUG: Unit model attributes sample: {[attr for attr in dir(u.model) if not attr.startswith('_')][:10]}")
        
        # 治疗能力
        if hasattr(u.model, "heal_level") and u.model.heal_level > 0:
            heal_level_text = nb2msg_float(u.model.heal_level / PRECISION)
            attrs.append(("", mp.HEAL_LEVEL, heal_level_text))
            print(f"DEBUG: Added heal_level")
        
        # 近战伤害
        print(f"DEBUG: Checking mdg - hasattr: {hasattr(u.model, 'mdg')}")
        if hasattr(u.model, "mdg"):
            mdg = getattr(u.model, "mdg", 0)
            print(f"DEBUG: MDG value: {mdg}")
            if mdg > 0:
                mdg_text = nb2msg_float(mdg/PRECISION)
                attrs.append(("m", mp.MELEE_DAMAGE, mdg_text))
                print(f"DEBUG: Added MDG: {mdg_text}")
        
        # 远程伤害
        print(f"DEBUG: Checking rdg - hasattr: {hasattr(u.model, 'rdg')}")
        if hasattr(u.model, "rdg"):
            rdg = getattr(u.model, "rdg", 0)
            print(f"DEBUG: RDG value: {rdg}")
            if rdg > 0:
                rdg_text = nb2msg_float(rdg/PRECISION)
                attrs.append(("r", mp.RANGE_DAMAGE, rdg_text))
                print(f"DEBUG: Added RDG: {rdg_text}")
        
        # 近战防御
        print(f"DEBUG: Checking mdf - hasattr: {hasattr(u.model, 'mdf')}")
        if hasattr(u.model, "mdf"):
            mdf = getattr(u.model, "mdf", 0)
            print(f"DEBUG: MDF value: {mdf}")
            if mdf > 0:
                mdf_text = nb2msg_float(mdf/PRECISION)
                attrs.append(("d", mp.MELEE_DEFENSE, mdf_text))
                print(f"DEBUG: Added MDF: {mdf_text}")

        # 远程防御
        print(f"DEBUG: Checking rdf - hasattr: {hasattr(u.model, 'rdf')}")
        if hasattr(u.model, "rdf"):
            rdf = getattr(u.model, "rdf", 0)
            print(f"DEBUG: RDF value: {rdf}")
            if rdf > 0:
                rdf_text = nb2msg_float(rdf/PRECISION)
                attrs.append(("f", mp.RANGE_DEFENSE, rdf_text))
                print(f"DEBUG: Added RDF: {rdf_text}")

        # 近战射程
        if hasattr(u.model, "mdg_range") and u.model.mdg_range > 0:
            # 检查是否为无限射程（32位整数最大值或接近值）
            if u.model.mdg_range >= 2147483647 or u.model.mdg_range >= 2147483:
                mdg_range_text = mp.INFINITE
            else:
                mdg_range = round(u.model.mdg_range / 1000.0, 1)
                mdg_range_text = nb2msg_float(mdg_range)
            attrs.append(("g", mp.MDG_RANGE, mdg_range_text))

        # 远程射程
        if hasattr(u.model, "rdg_range") and u.model.rdg_range > 0:
            # 检查是否为无限射程（32位整数最大值或接近值）
            if u.model.rdg_range >= 2147483647 or u.model.rdg_range >= 2147483:
                rdg_range_text = mp.INFINITE
            else:
                rdg_range = round(u.model.rdg_range / 1000.0, 1)
                rdg_range_text = nb2msg_float(rdg_range)
            attrs.append(("e", mp.RANGED_RANGE, rdg_range_text))

        # 近战攻击冷却
        if hasattr(u.model, "mdg_cd") and u.model.mdg_cd > 0:
            cd = round(u.model.mdg_cd / 1000.0, 1)
            cd_text = nb2msg_float(cd) + mp.SECONDS
            attrs.append(("a", mp.MDG_CD, cd_text))

        # 远程攻击冷却
        if hasattr(u.model, "rdg_cd") and u.model.rdg_cd > 0:
            cd = round(u.model.rdg_cd / 1000.0, 1)
            cd_text = nb2msg_float(cd) + mp.SECONDS
            attrs.append(("c", mp.RDG_CD, cd_text))

        # 速度
        print(f"DEBUG: Checking speed - hasattr: {hasattr(u.model, 'speed')}")
        if hasattr(u.model, "speed"):
            speed_value = getattr(u.model, "speed", 0)
            print(f"DEBUG: Speed value: {speed_value}")
            if speed_value > 0:
                speed = round(speed_value / 1000.0, 1)
                speed_text = nb2msg_float(speed)
                attrs.append(("s", mp.SPEED, speed_text))
                print(f"DEBUG: Added Speed: {speed_text}")

        # 视线范围
        print(f"DEBUG: Checking sight_range - hasattr: {hasattr(u.model, 'sight_range')}")
        if hasattr(u.model, "sight_range"):
            sight_range_value = getattr(u.model, "sight_range", 0)
            print(f"DEBUG: Sight range value: {sight_range_value}")
            if sight_range_value > 0:
                sight_range = round(sight_range_value / 1000.0, 1)
                sight_range_text = nb2msg_float(sight_range)
                attrs.append(("v", mp.SIGHT_RANGE, sight_range_text))
                print(f"DEBUG: Added Sight Range: {sight_range_text}")

        # 暴击相关属性
        if hasattr(u.model, "mdg_crit") and u.model.mdg_crit > 0:
            mdg_crit_text = nb2msg_float(u.model.mdg_crit/1000)  # 暴击倍率确实应该除以1000
            attrs.append(("", mp.MDG_CRIT, mdg_crit_text))

        if hasattr(u.model, "rdg_crit") and u.model.rdg_crit > 0:
            rdg_crit_text = nb2msg_float(u.model.rdg_crit/1000)  # 暴击倍率确实应该除以1000
            attrs.append(("", mp.RDG_CRIT, rdg_crit_text))

        if hasattr(u.model, "mdg_crit_rate") and u.model.mdg_crit_rate > 0:
            mdg_crit_rate_text = nb2msg_float(u.model.mdg_crit_rate)
            attrs.append(("", mp.MDG_CRIT_RATE, mdg_crit_rate_text))

        if hasattr(u.model, "rdg_crit_rate") and u.model.rdg_crit_rate > 0:
            rdg_crit_rate_text = nb2msg_float(u.model.rdg_crit_rate)
            attrs.append(("", mp.RDG_CRIT_RATE, rdg_crit_rate_text))

        # 特殊状态
        status_text = []
        if getattr(u.model, "is_invisible", 0) or getattr(u.model, "is_cloaked", 0):
            status_text.extend(mp.INVISIBLE)
        if getattr(u.model, "is_a_detector", 0):
            status_text.extend(mp.DETECTOR)
        if getattr(u.model, "is_a_cloaker", 0):
            status_text.extend(mp.CLOAKER)
        
        if status_text:
            attrs.append(("t", mp.STATS, status_text))
        
        # 单位类型
        if hasattr(u.model, "is_a") and u.model.is_a:
            is_a_text = []
            if isinstance(u.model.is_a, list):
                for unit_type in u.model.is_a:
                    type_title = style.get(unit_type, "title")
                    if type_title:
                        if isinstance(type_title, list):
                            is_a_text.extend(type_title)
                        else:
                            is_a_text.append(str(type_title))
                        is_a_text.extend(mp.COMMA)
                # 移除最后一个逗号
                if is_a_text and is_a_text[-1] in mp.COMMA:
                    is_a_text = is_a_text[:-1]
            else:
                # 单个类型
                type_title = style.get(u.model.is_a, "title")
                if type_title:
                    if isinstance(type_title, list):
                        is_a_text.extend(type_title)
                    else:
                        is_a_text.append(str(type_title))
                else:
                    is_a_text.append(str(u.model.is_a))
            
            if is_a_text:
                attrs.append(("i", mp.IS_A, is_a_text))
        
        try:
            from .build_rules_attributes import BuildRulesAttributes
            BuildRulesAttributes(self.parent).add_build_rules_attributes(u, attrs)
        except Exception:
            pass

        print(f"DEBUG: Original attributes logic completed. Total attrs: {len(attrs)}")
        print(f"DEBUG: Final attributes list:")
        for i, (key, msg, text) in enumerate(attrs):
            print(f"  {i}: key={key}, msg={msg}, text={text}")
        print(f"DEBUG: Attributes added in this function: {len(attrs) - 3}")  # 减去hp/mana/intro