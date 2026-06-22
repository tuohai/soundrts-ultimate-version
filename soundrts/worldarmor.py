from typing import Optional, List

from .definitions import rules
from .lib.log import warning
from .lib.nofloat import PRECISION
from .worldentity import Entity


class Armor(Entity):
    """护甲类，继承自Entity，用于实现护甲系统。
    单位通常装备一套护甲，护甲的属性会应用到单位上。
    """
    type_name = None
    can_use_tech = ()  # 添加can_use_tech支持，让护甲可以使用科技升级

    # 添加is_a机制支持
    is_a = ()  # 直接继承的父类列表
    expanded_is_a = set()  # 展开的继承链，包括间接继承的所有父类

    # 护甲基础防御属性
    mdf = 0  # 近战防御
    rdf = 0  # 远程防御
    
    # 抗暴击和抗穿甲属性
    mdf_crit_rate = 0  # 近战暴击抗性
    rdf_crit_rate = 0  # 远程暴击抗性
    mdf_piercing = 0  # 近战穿甲抗性
    rdf_piercing = 0  # 远程穿甲抗性
    
    # 护甲vs属性
    mdf_vs: dict = dict()  # 对特定单位的近战防御
    rdf_vs: dict = dict()  # 对特定单位的远程防御
    mdf_crit_rate_vs: dict = dict()  # 对特定单位的近战暴击抗性
    rdf_crit_rate_vs: dict = dict()  # 对特定单位的远程暴击抗性
    mdf_piercing_vs: dict = dict()  # 对特定单位的近战穿甲抗性
    rdf_piercing_vs: dict = dict()  # 对特定单位的远程穿甲抗性

    @classmethod
    def interpret(cls, d):
        """解析护甲的所有属性"""
        # 解析基本属性
        for k, f in [
            ("mdf", int),
            ("rdf", int),
            ("mdf_crit_rate", int),
            ("rdf_crit_rate", int),
            ("mdf_piercing", int),
            ("rdf_piercing", int),
            # 添加更多bonus属性
            ("mdf_bonus", float),
            ("rdf_bonus", float),
            ("mdf_crit_rate_bonus", float),
            ("rdf_crit_rate_bonus", float),
            ("mdf_piercing_bonus", float),
            ("rdf_piercing_bonus", float),
        ]:
            if k in d:
                d[k] = f(d[k])
        
        # 解析can_use_tech属性
        if "can_use_tech" in d:
            if isinstance(d["can_use_tech"], str):
                d["can_use_tech"] = d["can_use_tech"].split()
            elif not isinstance(d["can_use_tech"], (list, tuple)):
                d["can_use_tech"] = [d["can_use_tech"]]
        
        # 解析is_a属性
        if "is_a" in d:
            if isinstance(d["is_a"], str):
                d["is_a"] = d["is_a"].split()
            elif not isinstance(d["is_a"], (list, tuple)):
                d["is_a"] = [d["is_a"]]
        
        # 解析vs字典属性
        cls._interpret_vs_attributes(d)
    
    @classmethod
    def _interpret_vs_attributes(cls, d):
        """解析所有vs相关的属性"""
        vs_attributes = [
            # 防御vs属性
            "mdf_vs", "rdf_vs",
            # 抗性vs属性
            "mdf_crit_rate_vs", "rdf_crit_rate_vs",
            "mdf_piercing_vs", "rdf_piercing_vs",
        ]
        
        for attr in vs_attributes:
            if attr in d:
                vs_dict = {}
                vs_data = d[attr]
                
                # 检查是否需要PRECISION转换
                needs_precision = any(precision_attr in attr for precision_attr in [
                    "mdf", "rdf", "crit_rate", "piercing"
                ])
                
                # 处理不同的输入格式
                if isinstance(vs_data, str):
                    # 格式: "unit1 value1 unit2 value2"
                    parts = vs_data.split()
                    for i in range(0, len(parts), 2):
                        if i + 1 < len(parts):
                            unit_type = parts[i]
                            try:
                                value = float(parts[i + 1])
                                # 对于需要精度的属性，乘以PRECISION
                                if needs_precision:
                                    value *= PRECISION
                                vs_dict[unit_type] = value
                            except ValueError:
                                warning(f"Invalid value for {attr}: {parts[i + 1]}")
                
                elif isinstance(vs_data, dict):
                    # 已经是字典格式
                    for unit_type, value in vs_data.items():
                        try:
                            value = float(value)
                            # 对于需要精度的属性，乘以PRECISION
                            if needs_precision:
                                value *= PRECISION
                            vs_dict[unit_type] = value
                        except ValueError:
                            warning(f"Invalid value for {attr}[{unit_type}]: {value}")
                
                elif isinstance(vs_data, list):
                    # 列表格式: [unit1, value1, unit2, value2, ...]
                    for i in range(0, len(vs_data), 2):
                        if i + 1 < len(vs_data):
                            unit_type = vs_data[i]
                            try:
                                value = float(vs_data[i + 1])
                                # 对于需要精度的属性，乘以PRECISION
                                if needs_precision:
                                    value *= PRECISION
                                vs_dict[unit_type] = value
                            except ValueError:
                                warning(f"Invalid value for {attr}: {vs_data[i + 1]}")
                
                d[attr] = vs_dict

    def __init__(self, player=None, place=None, x=0, y=0, o=90):
        # 护甲不会真正存在于世界中，只是一个数据容器
        # 直接初始化基本属性而不调用父类的__init__方法
        self.player = player
        self.world = None  # 稍后会由拥有者设置
        self.id = -1  # 设置一个无效ID
        
        # 初始化is_a机制
        self.expanded_is_a = set()
        if hasattr(self, 'is_a') and self.is_a:
            self._expand_is_a(self.is_a)
        
        # 保存原始值，用于升级计算
        if hasattr(self, 'mdf'):
            self._original_mdf = self.mdf
        if hasattr(self, 'rdf'):
            self._original_rdf = self.rdf
        if hasattr(self, 'mdf_crit_rate'):
            self._original_mdf_crit_rate = self.mdf_crit_rate
        if hasattr(self, 'rdf_crit_rate'):
            self._original_rdf_crit_rate = self.rdf_crit_rate
        if hasattr(self, 'mdf_piercing'):
            self._original_mdf_piercing = self.mdf_piercing
        if hasattr(self, 'rdf_piercing'):
            self._original_rdf_piercing = self.rdf_piercing
        
        # 初始化bonus值，这些值会累加到基础属性上
        self._mdf_bonus = 0
        self._rdf_bonus = 0
        self._mdf_crit_rate_bonus = 0
        self._rdf_crit_rate_bonus = 0
        self._mdf_piercing_bonus = 0
        self._rdf_piercing_bonus = 0
    
    def _expand_is_a(self, is_a_tuple):
        """递归展开is_a继承链"""
        if not is_a_tuple:
            return
        
        for parent_type in is_a_tuple:
            if parent_type not in self.expanded_is_a:
                self.expanded_is_a.add(parent_type)
                # 递归展开父类型的is_a
                try:
                    parent_class = rules.unit_class(parent_type)
                    if parent_class and hasattr(parent_class, 'is_a'):
                        self._expand_is_a(parent_class.is_a)
                except:
                    pass  # 忽略错误，继续处理其他类型
    
    @property
    def mdf_bonus(self):
        """获取近战防御加成值"""
        if hasattr(self, '_mdf_bonus'):
            return self._mdf_bonus
        else:
            self._mdf_bonus = 0
            return 0
    
    @mdf_bonus.setter
    def mdf_bonus(self, value):
        """设置近战防御加成值"""
        self._mdf_bonus = value
    
    @property
    def rdf_bonus(self):
        """获取远程防御加成值"""
        if hasattr(self, '_rdf_bonus'):
            return self._rdf_bonus
        else:
            self._rdf_bonus = 0
            return 0
    
    @rdf_bonus.setter
    def rdf_bonus(self, value):
        """设置远程防御加成值"""
        self._rdf_bonus = value
    
    @property
    def mdf_crit_rate_bonus(self):
        """获取近战暴击抗性加成值"""
        if hasattr(self, '_mdf_crit_rate_bonus'):
            return self._mdf_crit_rate_bonus
        else:
            self._mdf_crit_rate_bonus = 0
            return 0
    
    @mdf_crit_rate_bonus.setter
    def mdf_crit_rate_bonus(self, value):
        """设置近战暴击抗性加成值"""
        self._mdf_crit_rate_bonus = value
    
    @property
    def rdf_crit_rate_bonus(self):
        """获取远程暴击抗性加成值"""
        if hasattr(self, '_rdf_crit_rate_bonus'):
            return self._rdf_crit_rate_bonus
        else:
            self._rdf_crit_rate_bonus = 0
            return 0
    
    @rdf_crit_rate_bonus.setter
    def rdf_crit_rate_bonus(self, value):
        """设置远程暴击抗性加成值"""
        self._rdf_crit_rate_bonus = value
    
    @property
    def mdf_piercing_bonus(self):
        """获取近战穿甲抗性加成值"""
        if hasattr(self, '_mdf_piercing_bonus'):
            return self._mdf_piercing_bonus
        else:
            self._mdf_piercing_bonus = 0
            return 0
    
    @mdf_piercing_bonus.setter
    def mdf_piercing_bonus(self, value):
        """设置近战穿甲抗性加成值"""
        self._mdf_piercing_bonus = value
    
    @property
    def rdf_piercing_bonus(self):
        """获取远程穿甲抗性加成值"""
        if hasattr(self, '_rdf_piercing_bonus'):
            return self._rdf_piercing_bonus
        else:
            self._rdf_piercing_bonus = 0
            return 0
    
    @rdf_piercing_bonus.setter
    def rdf_piercing_bonus(self, value):
        """设置远程穿甲抗性加成值"""
        self._rdf_piercing_bonus = value
    
    @property
    def upgrades(self):
        """获取护甲可以使用的升级列表"""
        if not self.player:
            return []
        
        # 护甲可用科技是护甲自身的can_use_tech和护甲拥有者的can_use_tech的组合
        result = []
        if hasattr(self, 'can_use_tech'):
            for tech_name in self.can_use_tech:
                if tech_name in self.player.upgrades:
                    result.append(tech_name)
        return result
    
    def upgrade_to_player_level(self):
        """根据玩家已研究的科技升级护甲属性"""
        if not self.player or not hasattr(self.player, 'upgrades') or not self.player.upgrades:
            return
            
        # 确保原始值已保存（如果还没有保存的话）
        if not hasattr(self, '_original_mdf'):
            self._original_mdf = getattr(self.__class__, 'mdf', 0)
        if not hasattr(self, '_original_rdf'):
            self._original_rdf = getattr(self.__class__, 'rdf', 0)
        if not hasattr(self, '_original_mdf_crit_rate'):
            self._original_mdf_crit_rate = getattr(self.__class__, 'mdf_crit_rate', 0)
        if not hasattr(self, '_original_rdf_crit_rate'):
            self._original_rdf_crit_rate = getattr(self.__class__, 'rdf_crit_rate', 0)
        if not hasattr(self, '_original_mdf_piercing'):
            self._original_mdf_piercing = getattr(self.__class__, 'mdf_piercing', 0)
        if not hasattr(self, '_original_rdf_piercing'):
            self._original_rdf_piercing = getattr(self.__class__, 'rdf_piercing', 0)
            
        # 重置为原始值
        self.mdf = self._original_mdf
        self.rdf = self._original_rdf
        self.mdf_crit_rate = self._original_mdf_crit_rate
        self.rdf_crit_rate = self._original_rdf_crit_rate
        self.mdf_piercing = self._original_mdf_piercing
        self.rdf_piercing = self._original_rdf_piercing
            
        # 重置bonus值
        self._mdf_bonus = 0
        self._rdf_bonus = 0
        self._mdf_crit_rate_bonus = 0
        self._rdf_crit_rate_bonus = 0
        self._mdf_piercing_bonus = 0
        self._rdf_piercing_bonus = 0
            
        # 检查护甲可以使用的科技
        for tech_name in getattr(self, 'can_use_tech', ()):
            if tech_name in self.player.upgrades:
                # 获取科技等级
                tech_level = self.player.level(tech_name)
                if tech_level > 0:
                    # 获取科技定义
                    tech_class = rules.unit_class(tech_name)
                    if tech_class and hasattr(tech_class, 'effect'):
                        # 处理多个effects的情况
                        effects_to_process = []
                        if isinstance(tech_class.effect, list) and len(tech_class.effect) > 0 and isinstance(tech_class.effect[0], list):
                            effects_to_process = tech_class.effect
                        else:
                            effects_to_process = [tech_class.effect]
                            
                        # 应用每个效果
                        for effect in effects_to_process:
                            try:
                                if isinstance(effect, str):
                                    effect_parts = effect.split()
                                else:
                                    effect_parts = list(effect)
                                    
                                # 处理bonus效果
                                if len(effect_parts) >= 3 and effect_parts[0] == "bonus":
                                    attr_name = effect_parts[1]
                                    if hasattr(self, attr_name):
                                        # 解析bonus值
                                        value = float(effect_parts[2])
                                        # 根据等级计算总加成 (不要循环累加)
                                        total_bonus = value * tech_level
                                        
                                        if attr_name == "mdf":
                                            self._mdf_bonus += total_bonus
                                            self.mdf += total_bonus
                                        elif attr_name == "rdf":
                                            self._rdf_bonus += total_bonus
                                            self.rdf += total_bonus
                                        elif attr_name == "mdf_crit_rate":
                                            self._mdf_crit_rate_bonus += total_bonus
                                            self.mdf_crit_rate += total_bonus
                                        elif attr_name == "rdf_crit_rate":
                                            self._rdf_crit_rate_bonus += total_bonus
                                            self.rdf_crit_rate += total_bonus
                                        elif attr_name == "mdf_piercing":
                                            self._mdf_piercing_bonus += total_bonus
                                            self.mdf_piercing += total_bonus
                                        elif attr_name == "rdf_piercing":
                                            self._rdf_piercing_bonus += total_bonus
                                            self.rdf_piercing += total_bonus
                                        else:
                                            # 对于其他属性，直接加上bonus值
                                            current_value = getattr(self, attr_name)
                                            setattr(self, attr_name, current_value + total_bonus)
                                
                                # 处理apply_bonus效果
                                elif len(effect_parts) >= 2 and effect_parts[0] == "apply_bonus":
                                    # apply_bonus会查找护甲的{attr}_bonus属性并应用
                                    for attr_name in effect_parts[1:]:
                                        bonus_attr = f"{attr_name}_bonus"
                                        if hasattr(self, bonus_attr):
                                            bonus_value = getattr(self, bonus_attr)
                                            if bonus_value:
                                                # 根据等级计算总加成
                                                total_bonus = bonus_value * tech_level
                                                
                                                if attr_name == "mdf":
                                                    self._mdf_bonus += total_bonus
                                                    self.mdf += total_bonus
                                                elif attr_name == "rdf":
                                                    self._rdf_bonus += total_bonus
                                                    self.rdf += total_bonus
                                                elif attr_name == "mdf_crit_rate":
                                                    self._mdf_crit_rate_bonus += total_bonus
                                                    self.mdf_crit_rate += total_bonus
                                                elif attr_name == "rdf_crit_rate":
                                                    self._rdf_crit_rate_bonus += total_bonus
                                                    self.rdf_crit_rate += total_bonus
                                                elif attr_name == "mdf_piercing":
                                                    self._mdf_piercing_bonus += total_bonus
                                                    self.mdf_piercing += total_bonus
                                                elif attr_name == "rdf_piercing":
                                                    self._rdf_piercing_bonus += total_bonus
                                                    self.rdf_piercing += total_bonus
                                                else:
                                                    # 对于其他属性，直接加上bonus值
                                                    if hasattr(self, attr_name):
                                                        current_value = getattr(self, attr_name)
                                                        setattr(self, attr_name, current_value + total_bonus)
                            except Exception as e:
                                warning(f"Error applying effect {effect} from tech {tech_name} to armor: {e}")
    
    def apply_to_unit(self, unit):
        """将护甲的属性应用到单位上"""
        # 近战防御
        if hasattr(self, "mdf") and self.mdf > 0:
            if not hasattr(unit, "mdf") or unit.mdf == 0:
                unit.mdf = self.mdf
            else:
                unit.mdf += self.mdf_bonus
                
        # 远程防御
        if hasattr(self, "rdf") and self.rdf > 0:
            if not hasattr(unit, "rdf") or unit.rdf == 0:
                unit.rdf = self.rdf
            else:
                unit.rdf += self.rdf_bonus
        
        # 应用护甲的bonus属性到单位
        if hasattr(self, "mdf_bonus") and self.mdf_bonus > 0:
            if not hasattr(unit, "mdf_bonus"):
                unit.mdf_bonus = 0
            unit.mdf_bonus += self.mdf_bonus
            
        if hasattr(self, "rdf_bonus") and self.rdf_bonus > 0:
            if not hasattr(unit, "rdf_bonus"):
                unit.rdf_bonus = 0
            unit.rdf_bonus += self.rdf_bonus
        
        # 暴击抗性
        if hasattr(self, "mdf_crit_rate") and self.mdf_crit_rate > 0:
            if not hasattr(unit, "mdf_crit_rate") or unit.mdf_crit_rate == 0:
                unit.mdf_crit_rate = self.mdf_crit_rate
            else:
                unit.mdf_crit_rate += self.mdf_crit_rate_bonus
                
        if hasattr(self, "rdf_crit_rate") and self.rdf_crit_rate > 0:
            if not hasattr(unit, "rdf_crit_rate") or unit.rdf_crit_rate == 0:
                unit.rdf_crit_rate = self.rdf_crit_rate
            else:
                unit.rdf_crit_rate += self.rdf_crit_rate_bonus
        
        # 穿甲抗性
        if hasattr(self, "mdf_piercing") and self.mdf_piercing > 0:
            if not hasattr(unit, "mdf_piercing") or unit.mdf_piercing == 0:
                unit.mdf_piercing = self.mdf_piercing
            else:
                unit.mdf_piercing += self.mdf_piercing_bonus
                
        if hasattr(self, "rdf_piercing") and self.rdf_piercing > 0:
            if not hasattr(unit, "rdf_piercing") or unit.rdf_piercing == 0:
                unit.rdf_piercing = self.rdf_piercing
            else:
                unit.rdf_piercing += self.rdf_piercing_bonus
        
        # 应用所有vs属性
        self._apply_vs_attributes(unit)
        
        # 应用护甲的can_use_tech属性
        if hasattr(self, "can_use_tech") and self.can_use_tech:
            # 确保单位有can_use_tech属性
            if not hasattr(unit, "can_use_tech"):
                unit.can_use_tech = []
            # 如果can_use_tech是元组，转换为列表
            if isinstance(unit.can_use_tech, tuple):
                unit.can_use_tech = list(unit.can_use_tech)
            # 添加护甲的can_use_tech到单位的can_use_tech中
            for tech in self.can_use_tech:
                if tech not in unit.can_use_tech:
                    unit.can_use_tech.append(tech)
    
    def _apply_vs_attributes(self, unit):
        """应用vs属性到单位"""
        # 防御vs属性
        vs_attrs = [
            "mdf_vs", "rdf_vs", "mdf_crit_rate_vs", "rdf_crit_rate_vs",
            "mdf_piercing_vs", "rdf_piercing_vs"
        ]
        
        for attr in vs_attrs:
            if hasattr(self, attr):
                armor_vs_dict = getattr(self, attr)
                if armor_vs_dict:
                    # 添加类型检查
                    if not isinstance(armor_vs_dict, dict):
                        warning(f"Armor {getattr(self, 'type_name', 'unknown')} has invalid {attr} type: {type(armor_vs_dict).__name__}, expected dict. Skipping.")
                        continue
                    
                    # 确保单位有对应的vs属性
                    if not hasattr(unit, attr):
                        setattr(unit, attr, {})
                    
                    unit_vs_dict = getattr(unit, attr)
                    
                    # 合并vs属性
                    for target_type, value in armor_vs_dict.items():
                        if target_type in unit_vs_dict:
                            unit_vs_dict[target_type] += value
                        else:
                            unit_vs_dict[target_type] = value
    
    def is_a_type(self, type_name):
        """检查护甲是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果护甲属于指定类型返回True，否则返回False
        """
        # 检查直接类型匹配
        if hasattr(self, 'type_name') and self.type_name == type_name:
            return True
        
        # 检查is_a直接继承
        if hasattr(self, 'is_a') and type_name in self.is_a:
            return True
        
        # 检查expanded_is_a间接继承
        if hasattr(self, 'expanded_is_a') and type_name in self.expanded_is_a:
            return True
        
        return False
    
    @classmethod
    def is_armor_type(cls, type_name):
        """检查护甲类是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果护甲类属于指定类型返回True，否则返回False
        """
        # 检查直接类型匹配
        if hasattr(cls, 'type_name') and cls.type_name == type_name:
            return True
        
        # 检查is_a直接继承
        if hasattr(cls, 'is_a') and type_name in cls.is_a:
            return True
        
        # 检查expanded_is_a间接继承
        if hasattr(cls, 'expanded_is_a') and type_name in cls.expanded_is_a:
            return True
        
        return False 