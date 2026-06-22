from typing import Optional, List

from .definitions import rules
from .lib.log import warning
from .lib.nofloat import PRECISION
from .worldentity import Entity


class Weapon(Entity):
    """武器类，继承自Creature，用于实现武器系统。
    单位可以装备一个或多个武器，武器的属性会应用到单位上。
    """
    is_a_weapon = True
    type_name = None
    can_use_tech = ()  # 添加can_use_tech支持，让武器可以使用科技升级

    # 添加is_a机制支持
    is_a = ()  # 直接继承的父类列表
    expanded_is_a = set()  # 展开的继承链，包括间接继承的所有父类

    # 武器debuffs支持
    debuffs = ()  # 武器可以触发的debuff列表

    # 武器属性
    mdg = 0  # 近战基础伤害
    rdg = 0  # 远程基础伤害
    mdg_crit = 0 # 近战暴击倍率
    rdg_crit = 0 # 远程暴击倍率
    mdg_crit_rate = 0 # 近战暴击几率
    rdg_crit_rate = 0 # 远程暴击几率
    mdg_piercing = 0 # 近战穿透程度
    rdg_piercing = 0 # 远程穿透程度
    mdg_piercing_rate = 0 # 近战穿甲几率
    rdg_piercing_rate = 0 # 远程穿甲几率
    mdg_range = 0
    rdg_range = 0
    mdg_minimal_range = 0
    rdg_minimal_range = 0
    mdg_projectile = 0  # 近战攻击是否为投射物
    rdg_projectile = 0  # 远程攻击是否为投射物
    mdg_targets = ["ground"]
    rdg_targets = ["ground"]
    mdg_delay = 0 #近战伤害弹道
    rdg_delay = 0 #远程伤害弹道
    mdg_radius = 0
    rdg_radius = 0
    mdg_splash = 0
    rdg_splash = 0
    mdg_splash_decay_min = 0  # 近战默认最小衰减
    rdg_splash_decay_min = 0  # 远程默认最小衰减
    mdg_cd = 0
    rdg_cd = 0
    mdg_next_attack_time = 0
    rdg_next_attack_time = 0
    mdg_prep_end_time = 0
    rdg_prep_end_time = 0
    mdg_ready = 0
    rdg_ready = 0
    mdg_cover = 0
    rdg_cover = 0
    mdg_dodge = 0
    rdg_dodge = 0
    mdg_status_duration = 0      # 近战伤害持续时间
    rdg_status_duration = 0      # 远程伤害持续时间
    damage_seq = None # 攻击序列
    mdg_seq_times: int = 1      # 近战攻击次数
    mdg_seq_damages: List[int] = []  # 近战伤害序列
    mdg_seq_interval: float = 0  # 近战攻击间隔
    
    rdg_seq_times: int = 1      # 远程攻击次数  
    rdg_seq_damages: List[int] = []  # 远程伤害序列
    rdg_seq_interval: float = 0  # 远程攻击间隔
    # 添加自爆相关
    mdg_explode = False
    rdg_explode = False
    mdg_vs: dict = dict()       # 近战伤害 vs 某些单位
    rdg_vs: dict = dict()       # 远程伤害 vs 某些单位

    #新增暴击类修正
    mdg_crit_vs:dict = dict() # 对特定单位的近战暴击倍率
    rdg_crit_vs: dict = dict() # 对特定单位的远程暴击倍率
    mdg_crit_rate_vs: dict = dict() # 对特定单位的近战暴击几率
    rdg_crit_rate_vs: dict = dict() # 对特定单位的远程暴击几率
    mdg_piercing_vs: dict = dict() # 对特定单位的近战穿甲
    rdg_piercing_vs: dict = dict() # 对特定单位的远程穿甲
    mdg_piercing_rate_vs: dict = dict() # 对特定单位的近战穿甲几率
    rdg_piercing_rate_vs: dict = dict() # 对特定单位的远程穿甲几率

    # 自爆相关属性
    mdg_explode = False  # 近战自爆标志
    rdg_explode = False  # 远程自爆标志
    mdg_explode_vs: dict = dict()  # 针对特定单位的近战自爆
    rdg_explode_vs: dict = dict()  # 针对特定单位的远程自爆
    exp_hp_cost = 0  # 自爆扣血百分比(默认0%)
    exp_dgf = 0  # 爆炸伤害系数
    exp_dgf_vs: dict = dict()  # 对特定单位的额外爆炸伤害系数

    # 冷却、前摇、射程、最小射程、命中/闪避等 vs 修正
    mdg_cd_vs: dict = dict()
    rdg_cd_vs: dict = dict()
    mdg_ready_vs: dict = dict()
    rdg_ready_vs: dict = dict()
    mdg_range_vs: dict = dict()
    rdg_range_vs: dict = dict()
    mdg_minimal_range_vs: dict = dict()
    rdg_minimal_range_vs: dict = dict()
    mdg_cover_vs: dict = dict()
    rdg_cover_vs: dict = dict()
    mdg_dodge_vs: dict = dict()
    rdg_dodge_vs: dict = dict()
    mdg_splash_vs: dict = dict()
    rdg_splash_vs: dict = dict()
    mdg_splash_decay_min_vs: dict = dict()
    rdg_splash_decay_min_vs: dict = dict()
    mdg_radius_vs: dict = dict()
    rdg_radius_vs: dict = dict()

    def __init__(self, player=None, place=None, x=0, y=0, o=90):
        # 武器不会真正存在于世界中，只是一个数据容器
        # 直接初始化基本属性而不调用父类Creature的__init__方法
        self.player = player
        self.world = None  # 稍后会由拥有者设置
        self.id = -1  # 设置一个无效ID
        
        # 初始化is_a机制
        self.expanded_is_a = set()
        if hasattr(self, 'is_a') and self.is_a:
            self._expand_is_a(self.is_a)
        
        # 保存原始值，用于升级计算
        if hasattr(self, 'mdg'):
            self._original_mdg = self.mdg
        if hasattr(self, 'rdg'):
            self._original_rdg = self.rdg
        if hasattr(self, 'mdg_cd'):
            self._original_mdg_cd = self.mdg_cd
        if hasattr(self, 'rdg_cd'):
            self._original_rdg_cd = self.rdg_cd
        if hasattr(self, 'mdg_range'):
            self._original_mdg_range = self.mdg_range
        if hasattr(self, 'rdg_range'):
            self._original_rdg_range = self.rdg_range
        
        # 初始化bonus值，这些值会累加到基础属性上
        self._mdg_bonus = 0
        self._rdg_bonus = 0

    @classmethod
    def interpret(cls, d):
        """解析武器的所有属性"""
        # 解析基本属性
        for k, f in [
            ("mdg", int),
            ("rdg", int),
            ("mdg_bonus", float),
            ("rdg_bonus", float),
            ("mdg_crit", int),
            ("rdg_crit", int),
            ("mdg_crit_rate", int),
            ("rdg_crit_rate", int),
            ("mdg_piercing", int),
            ("rdg_piercing", int),
            ("mdg_piercing_rate", int),
            ("rdg_piercing_rate", int),
            ("mdg_range", int),
            ("rdg_range", int),
            ("mdg_minimal_range", int),
            ("rdg_minimal_range", int),
            ("mdg_projectile", int),
            ("rdg_projectile", int),
            ("mdg_delay", int),
            ("rdg_delay", int),
            ("mdg_radius", int),
            ("rdg_radius", int),
            ("mdg_splash", int),
            ("rdg_splash", int),
            ("mdg_splash_decay_min", float),
            ("rdg_splash_decay_min", float),
            ("mdg_cd", int),
            ("rdg_cd", int),
            ("mdg_ready", int),
            ("rdg_ready", int),
            ("mdg_cover", int),
            ("rdg_cover", int),
            ("mdg_dodge", int),
            ("rdg_dodge", int),
            ("mdg_status_duration", int),
            ("rdg_status_duration", int),
            ("mdg_seq_times", int),
            ("rdg_seq_times", int),
            ("mdg_seq_interval", float),
            ("rdg_seq_interval", float),
            ("exp_hp_cost", int),
            ("exp_dgf", int),
            # 添加更多bonus属性
            ("mdg_crit_bonus", float),
            ("rdg_crit_bonus", float),
            ("mdg_crit_rate_bonus", float),
            ("rdg_crit_rate_bonus", float),
            ("mdg_piercing_bonus", float),
            ("rdg_piercing_bonus", float),
            ("mdg_piercing_rate_bonus", float),
            ("rdg_piercing_rate_bonus", float),
            ("mdg_cd_bonus", float),
            ("rdg_cd_bonus", float),
            ("mdg_range_bonus", float),
            ("rdg_range_bonus", float),
            ("mdg_minimal_range_bonus", float),
            ("rdg_minimal_range_bonus", float),
            ("mdg_splash_bonus", float),
            ("rdg_splash_bonus", float),
            ("mdg_radius_bonus", float),
            ("rdg_radius_bonus", float),
            ("mdg_ready_bonus", float),
            ("rdg_ready_bonus", float),
            ("mdg_cover_bonus", float),
            ("rdg_cover_bonus", float),
            ("mdg_dodge_bonus", float),
            ("rdg_dodge_bonus", float),
            ("exp_hp_cost_bonus", float),
            ("exp_dgf_bonus", float),
        ]:
            if k in d:
                d[k] = f(d[k])
        
        # 解析布尔值属性
        for k in ["mdg_explode", "rdg_explode"]:
            if k in d:
                d[k] = bool(d[k])
        
        # 解析列表属性
        for k in ["mdg_targets", "rdg_targets", "mdg_seq_damages", "rdg_seq_damages"]:
            if k in d:
                if isinstance(d[k], str):
                    d[k] = d[k].split()
                elif not isinstance(d[k], list):
                    d[k] = [d[k]]
        
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
        
        # 解析debuffs属性
        if "debuffs" in d:
            if isinstance(d["debuffs"], str):
                d["debuffs"] = d["debuffs"].split()
            elif not isinstance(d["debuffs"], (list, tuple)):
                d["debuffs"] = [d["debuffs"]]
        
        # 解析vs字典属性
        cls._interpret_vs_attributes(d)
    
    @classmethod
    def _interpret_vs_attributes(cls, d):
        """解析所有vs相关的属性"""
        vs_attributes = [
            # 基本伤害vs
            "mdg_vs", "rdg_vs",
            # 暴击vs
            "mdg_crit_vs", "rdg_crit_vs",
            "mdg_crit_rate_vs", "rdg_crit_rate_vs",
            # 穿甲vs
            "mdg_piercing_vs", "rdg_piercing_vs",
            "mdg_piercing_rate_vs", "rdg_piercing_rate_vs",
            # 自爆vs
            "mdg_explode_vs", "rdg_explode_vs",
            "exp_dgf_vs",
            # 其他属性vs
            "mdg_cd_vs", "rdg_cd_vs",
            "mdg_ready_vs", "rdg_ready_vs",
            "mdg_range_vs", "rdg_range_vs",
            "mdg_minimal_range_vs", "rdg_minimal_range_vs",
            "mdg_cover_vs", "rdg_cover_vs",
            "mdg_dodge_vs", "rdg_dodge_vs",
            "mdg_splash_vs", "rdg_splash_vs",
            "mdg_splash_decay_min_vs", "rdg_splash_decay_min_vs",
            "mdg_radius_vs", "rdg_radius_vs",
        ]
        
        for attr in vs_attributes:
            if attr in d:
                vs_dict = {}
                vs_data = d[attr]
                
                # 检查是否需要PRECISION转换
                from .definitions import PRECISION
                needs_precision = any(precision_attr in attr for precision_attr in [
                    "mdg", "rdg", "mdf", "rdf", "cd", "range", "ready", "cover", "dodge", 
                    "splash", "radius", "minimal_range"
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
                                from .lib.log import warning
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
                            from .lib.log import warning
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
                                from .lib.log import warning
                                warning(f"Invalid value for {attr}: {vs_data[i + 1]}")
                
                d[attr] = vs_dict

    @property
    def mdg_bonus(self):
        """获取近战伤害加成值"""
        if hasattr(self, '_mdg_bonus'):
            return self._mdg_bonus
        else:
            self._mdg_bonus = 0
            return 0
    
    @mdg_bonus.setter
    def mdg_bonus(self, value):
        """设置近战伤害加成值"""
        self._mdg_bonus = value
    
    @property
    def rdg_bonus(self):
        """获取远程伤害加成值"""
        if hasattr(self, '_rdg_bonus'):
            return self._rdg_bonus
        else:
            self._rdg_bonus = 0
            return 0
    
    @rdg_bonus.setter
    def rdg_bonus(self, value):
        """设置远程伤害加成值"""
        self._rdg_bonus = value
    
    @property
    def upgrades(self):
        """获取武器可以使用的升级列表"""
        if not self.player:
            return []
        
        # 武器可用科技是武器自身的can_use_tech和武器拥有者的can_use_tech的组合
        result = []
        if hasattr(self, 'can_use_tech'):
            for tech_name in self.can_use_tech:
                if tech_name in self.player.upgrades:
                    result.append(tech_name)
        return result
    
    def upgrade_to_player_level(self):
        """根据玩家已研究的科技升级武器属性"""
        if not self.player or not hasattr(self.player, 'upgrades') or not self.player.upgrades:
            return
            
        # 确保原始值已保存（如果还没有保存的话）
        if not hasattr(self, '_original_mdg'):
            self._original_mdg = getattr(self.__class__, 'mdg', 0)
        if not hasattr(self, '_original_rdg'):
            self._original_rdg = getattr(self.__class__, 'rdg', 0)
        if not hasattr(self, '_original_mdg_cd'):
            self._original_mdg_cd = getattr(self.__class__, 'mdg_cd', 0)
        if not hasattr(self, '_original_rdg_cd'):
            self._original_rdg_cd = getattr(self.__class__, 'rdg_cd', 0)
        if not hasattr(self, '_original_mdg_range'):
            self._original_mdg_range = getattr(self.__class__, 'mdg_range', 0)
        if not hasattr(self, '_original_rdg_range'):
            self._original_rdg_range = getattr(self.__class__, 'rdg_range', 0)
            
        # 重置为原始值
        self.mdg = self._original_mdg
        self.rdg = self._original_rdg
        self.mdg_cd = self._original_mdg_cd
        self.rdg_cd = self._original_rdg_cd
        self.mdg_range = self._original_mdg_range
        self.rdg_range = self._original_rdg_range
            
        # 重置bonus值
        self._mdg_bonus = 0
        self._rdg_bonus = 0
            
        # 检查武器可以使用的科技
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
                                        
                                        if attr_name == "mdg":
                                            self._mdg_bonus += total_bonus
                                            self.mdg += total_bonus
                                        elif attr_name == "rdg":
                                            self._rdg_bonus += total_bonus
                                            self.rdg += total_bonus
                                        elif attr_name == "mdg_cd":
                                            self.mdg_cd -= total_bonus
                                        elif attr_name == "rdg_cd":
                                            self.rdg_cd -= total_bonus
                                        elif attr_name == "mdg_range":
                                            self.mdg_range += total_bonus
                                        elif attr_name == "rdg_range":
                                            self.rdg_range += total_bonus
                                        else:
                                            # 对于其他属性，直接加上bonus值
                                            current_value = getattr(self, attr_name)
                                            setattr(self, attr_name, current_value + total_bonus)
                                
                                # 处理apply_bonus效果
                                elif len(effect_parts) >= 2 and effect_parts[0] == "apply_bonus":
                                    # apply_bonus会查找武器的{attr}_bonus属性并应用
                                    for attr_name in effect_parts[1:]:
                                        bonus_attr = f"{attr_name}_bonus"
                                        if hasattr(self, bonus_attr):
                                            bonus_value = getattr(self, bonus_attr)
                                            if bonus_value:
                                                # 根据等级计算总加成
                                                total_bonus = bonus_value * tech_level
                                                
                                                if attr_name == "mdg":
                                                    self._mdg_bonus += total_bonus
                                                    self.mdg += total_bonus
                                                elif attr_name == "rdg":
                                                    self._rdg_bonus += total_bonus
                                                    self.rdg += total_bonus
                                                elif attr_name == "mdg_cd":
                                                    self.mdg_cd -= total_bonus
                                                elif attr_name == "rdg_cd":
                                                    self.rdg_cd -= total_bonus
                                                elif attr_name == "mdg_range":
                                                    self.mdg_range += total_bonus
                                                elif attr_name == "rdg_range":
                                                    self.rdg_range += total_bonus
                                                else:
                                                    # 对于其他属性，直接加上bonus值
                                                    if hasattr(self, attr_name):
                                                        current_value = getattr(self, attr_name)
                                                        setattr(self, attr_name, current_value + total_bonus)
                            except Exception as e:
                                from .lib.log import warning
                                warning(f"Error applying effect {effect} from tech {tech_name} to weapon: {e}")

    def apply_to_unit(self, unit):
        """将武器的属性应用到单位上"""
        # 近战伤害
        if hasattr(self, "mdg") and self.mdg > 0:
            if not hasattr(unit, "mdg") or unit.mdg == 0:
                unit.mdg = self.mdg
            else:
                unit.mdg += self.mdg_bonus
                
        # 远程伤害
        if hasattr(self, "rdg") and self.rdg > 0:
            if not hasattr(unit, "rdg") or unit.rdg == 0:
                unit.rdg = self.rdg
            else:
                unit.rdg += self.rdg_bonus
        
        # 应用武器的bonus属性到单位
        if hasattr(self, "mdg_bonus") and self.mdg_bonus > 0:
            if not hasattr(unit, "mdg_bonus"):
                unit.mdg_bonus = 0
            unit.mdg_bonus += self.mdg_bonus
            
        if hasattr(self, "rdg_bonus") and self.rdg_bonus > 0:
            if not hasattr(unit, "rdg_bonus"):
                unit.rdg_bonus = 0
            unit.rdg_bonus += self.rdg_bonus
                
        # 冷却时间
        if hasattr(self, "mdg_cd") and self.mdg_cd > 0:
            unit.mdg_cd = self.mdg_cd
            
        if hasattr(self, "rdg_cd") and self.rdg_cd > 0:
            unit.rdg_cd = self.rdg_cd
        
        # 射程
        if hasattr(self, "mdg_range") and self.mdg_range > 0:
            unit.mdg_range = self.mdg_range
            
        if hasattr(self, "rdg_range") and self.rdg_range > 0:
            unit.rdg_range = self.rdg_range
        
        # 其他基本属性
        self._apply_basic_attributes(unit)
        
        # 应用所有vs属性
        self._apply_vs_attributes(unit)
        
        # 应用武器的can_use_tech属性
        if hasattr(self, "can_use_tech") and self.can_use_tech:
            # 确保单位有can_use_tech属性
            if not hasattr(unit, "can_use_tech"):
                unit.can_use_tech = []
            # 如果can_use_tech是元组，转换为列表
            if isinstance(unit.can_use_tech, tuple):
                unit.can_use_tech = list(unit.can_use_tech)
            # 添加武器的can_use_tech到单位的can_use_tech中
            for tech in self.can_use_tech:
                if tech not in unit.can_use_tech:
                    unit.can_use_tech.append(tech)
        
        # 应用武器的debuffs属性
        if hasattr(self, "debuffs") and self.debuffs:
            # 确保单位有debuffs属性
            if not hasattr(unit, "debuffs"):
                unit.debuffs = []
            # 如果debuffs是元组，转换为列表
            if isinstance(unit.debuffs, tuple):
                unit.debuffs = list(unit.debuffs)
            # 添加武器的debuffs到单位的debuffs中（避免重复）
            for debuff in self.debuffs:
                if debuff not in unit.debuffs:
                    unit.debuffs.append(debuff)
    
    def _apply_basic_attributes(self, unit):
        """应用武器的基本属性到单位"""
        # 基本属性列表
        basic_attrs = [
            "mdg_crit", "rdg_crit", "mdg_crit_rate", "rdg_crit_rate",
            "mdg_piercing", "rdg_piercing", "mdg_piercing_rate", "rdg_piercing_rate",
            "mdg_minimal_range", "rdg_minimal_range", "mdg_projectile", "rdg_projectile",
            "mdg_delay", "rdg_delay", "mdg_radius", "rdg_radius",
            "mdg_splash", "rdg_splash", "mdg_splash_decay_min", "rdg_splash_decay_min",
            "mdg_ready", "rdg_ready", "mdg_cover", "rdg_cover",
            "mdg_dodge", "rdg_dodge", "mdg_status_duration", "rdg_status_duration",
            "mdg_seq_times", "rdg_seq_times", "mdg_seq_interval", "rdg_seq_interval",
            "mdg_explode", "rdg_explode", "exp_hp_cost", "exp_dgf"
        ]
        
        # 添加bonus属性的处理
        bonus_attrs = [
            "mdg_crit_bonus", "rdg_crit_bonus", "mdg_crit_rate_bonus", "rdg_crit_rate_bonus",
            "mdg_piercing_bonus", "rdg_piercing_bonus", "mdg_piercing_rate_bonus", "rdg_piercing_rate_bonus",
            "mdg_cd_bonus", "rdg_cd_bonus", "mdg_range_bonus", "rdg_range_bonus",
            "mdg_minimal_range_bonus", "rdg_minimal_range_bonus", "mdg_splash_bonus", "rdg_splash_bonus",
            "mdg_radius_bonus", "rdg_radius_bonus", "mdg_ready_bonus", "rdg_ready_bonus",
            "mdg_cover_bonus", "rdg_cover_bonus", "mdg_dodge_bonus", "rdg_dodge_bonus",
            "exp_hp_cost_bonus", "exp_dgf_bonus"
        ]
        
        for attr in basic_attrs:
            if hasattr(self, attr):
                weapon_value = getattr(self, attr)
                if weapon_value > 0 or (isinstance(weapon_value, bool) and weapon_value):
                    # 对于伤害属性，累加；对于其他属性，覆盖
                    if attr in ["mdg_crit", "rdg_crit", "mdg_splash", "rdg_splash"]:
                        if hasattr(unit, attr):
                            setattr(unit, attr, getattr(unit, attr) + weapon_value)
                        else:
                            setattr(unit, attr, weapon_value)
                    else:
                        setattr(unit, attr, weapon_value)
        
        # 处理bonus属性
        for attr in bonus_attrs:
            if hasattr(self, attr):
                weapon_value = getattr(self, attr)
                if weapon_value > 0:
                    # 对于bonus属性，总是累加
                    if hasattr(unit, attr):
                        setattr(unit, attr, getattr(unit, attr) + weapon_value)
                    else:
                        setattr(unit, attr, weapon_value)
        
        # 处理列表属性
        list_attrs = ["mdg_targets", "rdg_targets", "mdg_seq_damages", "rdg_seq_damages"]
        for attr in list_attrs:
            if hasattr(self, attr):
                weapon_value = getattr(self, attr)
                if weapon_value:
                    setattr(unit, attr, weapon_value[:])  # 复制列表
    
    def _apply_vs_attributes(self, unit):
        """应用所有vs属性到单位"""
        vs_attributes = [
            # 基本伤害vs
            "mdg_vs", "rdg_vs",
            # 暴击vs
            "mdg_crit_vs", "rdg_crit_vs",
            "mdg_crit_rate_vs", "rdg_crit_rate_vs",
            # 穿甲vs
            "mdg_piercing_vs", "rdg_piercing_vs",
            "mdg_piercing_rate_vs", "rdg_piercing_rate_vs",
            # 自爆vs
            "mdg_explode_vs", "rdg_explode_vs",
            "exp_dgf_vs",
            # 其他属性vs
            "mdg_cd_vs", "rdg_cd_vs",
            "mdg_ready_vs", "rdg_ready_vs",
            "mdg_range_vs", "rdg_range_vs",
            "mdg_minimal_range_vs", "rdg_minimal_range_vs",
            "mdg_cover_vs", "rdg_cover_vs",
            "mdg_dodge_vs", "rdg_dodge_vs",
            "mdg_splash_vs", "rdg_splash_vs",
            "mdg_splash_decay_min_vs", "rdg_splash_decay_min_vs",
            "mdg_radius_vs", "rdg_radius_vs",
        ]
        
        for attr in vs_attributes:
            if hasattr(self, attr):
                weapon_vs = getattr(self, attr)
                if weapon_vs and isinstance(weapon_vs, dict):
                    # 确保单位有该vs属性
                    if not hasattr(unit, attr):
                        setattr(unit, attr, dict())
                    unit_vs = getattr(unit, attr)
                    if not isinstance(unit_vs, dict):
                        setattr(unit, attr, dict())
                        unit_vs = getattr(unit, attr)
                    
                    # 合并武器的vs到单位的vs
                    for target_type, value in weapon_vs.items():
                        if target_type in unit_vs:
                            unit_vs[target_type] += value
                        else:
                            unit_vs[target_type] = value

    def _expand_is_a(self, is_a_list):
        """展开is_a列表，将直接继承的父类和间接继承的父类都添加到expanded_is_a中"""
        if not is_a_list:
            return
            
        for parent_name in is_a_list:
            if parent_name not in self.expanded_is_a:
                self.expanded_is_a.add(parent_name)
                # 递归处理基类的继承
                try:
                    parent_class = rules.unit_class(parent_name)
                    if parent_class and hasattr(parent_class, 'is_a'):
                        self._expand_is_a(parent_class.is_a)
                except (AttributeError, KeyError):
                    # 如果没有找到父类定义，或者rules对象还没有初始化，跳过
                    pass
    
    def is_a_type(self, type_name):
        """检查武器是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果武器属于指定类型返回True，否则返回False
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
    def is_weapon_type(cls, type_name):
        """检查武器类是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果武器类属于指定类型返回True，否则返回False
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