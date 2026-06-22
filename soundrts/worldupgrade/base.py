import copy
from ..definitions import MAX_NB_OF_RESOURCE_TYPES, rules
from ..lib.nofloat import PRECISION
from .cost_effects import CostEffectsMixin
from .attribute_effects import AttributeEffectsMixin
from .production_effects import ProductionEffectsMixin
from .gather_effects import GatherEffectsMixin


def is_an_upgrade(o):
    return hasattr(o, "upgrade_player")


class Upgrade(CostEffectsMixin, AttributeEffectsMixin, ProductionEffectsMixin, GatherEffectsMixin):
    """升级系统基类"""
    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    count_limit = 0
    time_cost = 0
    requirements = ()
    population_cost = 0
    effect = None
    is_a = ()  # 添加is_a支持
    expanded_is_a = set()  # 添加expanded_is_a支持
    can_use = ()  # 添加can_use支持，表示科技可以使用的其他科技
    can_use_tech = ()  # 添加can_use_tech支持，表示单位可以使用的升级技术
    can_use_skill = ()  # 添加can_use_skill支持，表示单位可以使用的技能
    
    # 定义必须使用整数的属性集合
    integer_stats = {'hp', 'hp_max', 'minimal_damage', 'population_cost', 'time_cost', 'resource_volume_max'}

    # 保留成本相关的全局效果字典
    _global_cost_effects = {}

    @classmethod
    def reset(cls):
        """在游戏结束时重置数据"""
        cls._global_cost_effects = {}
        # 注意：_applied_cost_bonuses 是玩家级别的，会在玩家对象销毁时自动清理

    def __init__(self):
        # 初始化expanded_is_a
        self.expanded_is_a = set()
        if hasattr(self, 'is_a'):
            self._expand_is_a(self.is_a)
    
    def _expand_is_a(self, is_a_list):
        """展开并记录所有继承关系"""
        if not is_a_list:
            return
            
        for base_type in is_a_list:
            if base_type not in self.expanded_is_a:
                self.expanded_is_a.add(base_type)
                # 递归处理基类的继承
                base_class = rules.get(base_type)
                if base_class and hasattr(base_class, 'is_a'):
                    self._expand_is_a(base_class.is_a)

    @classmethod
    def _expand_is_a_for_unit(cls, unit, is_a_list):
        """为单位展开并记录所有继承关系"""
        if not is_a_list:
            return
            
        for base_type in is_a_list:
            if base_type not in unit.expanded_is_a:
                unit.expanded_is_a.add(base_type)
                # 递归处理基类的继承
                base_class = rules.get(base_type)
                if base_class and hasattr(base_class, 'is_a'):
                    cls._expand_is_a_for_unit(unit, base_class.is_a)

    @classmethod
    def upgrade_player(cls, player):
        """为玩家应用升级效果"""
        # 初始化成本相关效果的标志和值
        has_cost_effect = False
        cost_bonus_values = []
        has_cost_percent_effect = False
        cost_percent_bonus_values = []
        has_population_cost_effect = False
        population_cost_bonus_value = 0
        has_population_cost_percent_effect = False
        population_cost_percent_bonus_value = 0.0
        has_time_cost_effect = False
        time_cost_bonus_value = 0
        has_time_cost_percent_effect = False
        time_cost_percent_bonus_value = 0.0
        # 生产相关成本效果
        has_production_cost_effect = False
        production_cost_bonus_values = []
        has_production_cost_percent_effect = False
        production_cost_percent_bonus_values = []
        has_production_time_effect = False
        production_time_bonus_value = 0
        has_production_time_percent_effect = False
        production_time_percent_bonus_value = 0.0
        has_production_qty_effect = False
        production_qty_bonus_value = 0
        has_production_qty_percent_effect = False
        production_qty_percent_bonus_value = 0.0
        
        # 获取当前科技等级
        current_level = player.level(cls.type_name)
        
        # 保存成本相关效果到全局字典中
        if cls.type_name not in cls._global_cost_effects:
            cls._global_cost_effects[cls.type_name] = []
        
        # 确保玩家有必要的成本相关属性
        if not hasattr(player, 'cost_bonus'):
            player.cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        if not hasattr(player, 'cost_percent_bonus'):
            player.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        if not hasattr(player, 'population_cost_bonus'):
            player.population_cost_bonus = 0
        if not hasattr(player, 'population_cost_percent_bonus'):
            player.population_cost_percent_bonus = 0.0
        if not hasattr(player, 'time_cost_bonus'):
            player.time_cost_bonus = 0
        if not hasattr(player, 'time_cost_percent_bonus'):
            player.time_cost_percent_bonus = 0.0
        
        # 处理已有的单位
        # 直接遍历所有单位并应用非成本相关效果
        for unit in player.units:
            # 检查单位是否可以使用这个科技
            if cls.type_name in getattr(unit, 'can_use', ()):
                cls._apply_effects_to_unit(unit, player)
            
            # 也检查can_use_tech和can_use_skill
            if cls.type_name in getattr(unit, 'can_use_tech', ()):
                cls._apply_effects_to_unit(unit, player)
            
            if cls.type_name in getattr(unit, 'can_use_skill', ()):
                cls._apply_effects_to_unit(unit, player)
        
        # 升级所有单位的武器（在应用科技效果后）
        for unit in player.units:
            if hasattr(unit, 'update_weapons'):
                unit.update_weapons()
        
        # 处理多个effects的情况，解析出成本相关效果
        effects_to_process = []
        if cls.effect:
            # 如果是列表的列表，则为多个effect
            if isinstance(cls.effect, list) and cls.effect and isinstance(cls.effect[0], list):
                effects_to_process = cls.effect
            else:
                effects_to_process = [cls.effect]
        
        # 检查每个效果，提取成本相关效果
        for current_effect in effects_to_process:
            effect_parts = current_effect.split() if isinstance(current_effect, str) else list(current_effect)
            
            # 处理 apply_bonus 效果
            if len(effect_parts) >= 2 and effect_parts[0] == "apply_bonus":
                # apply_bonus效果直接应用到玩家，不需要累积到变量中
                cls._handle_apply_bonus_effects(player, effect_parts)
                continue
            
            # 处理其他成本相关效果
            cost_effect_results = cls._process_cost_effects(effect_parts)
            if cost_effect_results:
                # 累积成本效果变量（而不是直接赋值）
                (new_has_cost_effect, new_cost_bonus_values, new_has_cost_percent_effect, new_cost_percent_bonus_values,
                 new_has_population_cost_effect, new_population_cost_bonus_value, new_has_population_cost_percent_effect,
                 new_population_cost_percent_bonus_value, new_has_time_cost_effect, new_time_cost_bonus_value,
                 new_has_time_cost_percent_effect, new_time_cost_percent_bonus_value, new_has_production_cost_effect,
                 new_production_cost_bonus_values, new_has_production_cost_percent_effect, new_production_cost_percent_bonus_values,
                 new_has_production_time_effect, new_production_time_bonus_value, new_has_production_time_percent_effect,
                 new_production_time_percent_bonus_value, new_has_production_qty_effect, new_production_qty_bonus_value,
                 new_has_production_qty_percent_effect, new_production_qty_percent_bonus_value) = cost_effect_results
                
                # 累积到现有变量中
                if new_has_cost_effect:
                    has_cost_effect = True
                    cost_bonus_values.extend(new_cost_bonus_values)
                
                if new_has_cost_percent_effect:
                    has_cost_percent_effect = True
                    cost_percent_bonus_values.extend(new_cost_percent_bonus_values)
                
                if new_has_population_cost_effect:
                    has_population_cost_effect = True
                    population_cost_bonus_value += new_population_cost_bonus_value
                
                if new_has_population_cost_percent_effect:
                    has_population_cost_percent_effect = True
                    population_cost_percent_bonus_value += new_population_cost_percent_bonus_value
                
                if new_has_time_cost_effect:
                    has_time_cost_effect = True
                    time_cost_bonus_value += new_time_cost_bonus_value
                
                if new_has_time_cost_percent_effect:
                    has_time_cost_percent_effect = True
                    time_cost_percent_bonus_value += new_time_cost_percent_bonus_value
                
                if new_has_production_cost_effect:
                    has_production_cost_effect = True
                    production_cost_bonus_values.extend(new_production_cost_bonus_values)
                
                if new_has_production_cost_percent_effect:
                    has_production_cost_percent_effect = True
                    production_cost_percent_bonus_values.extend(new_production_cost_percent_bonus_values)
                
                if new_has_production_time_effect:
                    has_production_time_effect = True
                    production_time_bonus_value += new_production_time_bonus_value
                
                if new_has_production_time_percent_effect:
                    has_production_time_percent_effect = True
                    production_time_percent_bonus_value += new_production_time_percent_bonus_value
                
                if new_has_production_qty_effect:
                    has_production_qty_effect = True
                    production_qty_bonus_value += new_production_qty_bonus_value
                
                if new_has_production_qty_percent_effect:
                    has_production_qty_percent_effect = True
                    production_qty_percent_bonus_value += new_production_qty_percent_bonus_value
        
        # 存储成本相关效果到全局字典
        cost_effects = cls._create_cost_effects_dict(
            has_cost_effect, cost_bonus_values, has_cost_percent_effect, cost_percent_bonus_values,
            has_population_cost_effect, population_cost_bonus_value, has_population_cost_percent_effect,
            population_cost_percent_bonus_value, has_time_cost_effect, time_cost_bonus_value,
            has_time_cost_percent_effect, time_cost_percent_bonus_value, has_production_cost_effect,
            production_cost_bonus_values, has_production_cost_percent_effect, production_cost_percent_bonus_values,
            has_production_time_effect, production_time_bonus_value, has_production_time_percent_effect,
            production_time_percent_bonus_value, has_production_qty_effect, production_qty_bonus_value,
            has_production_qty_percent_effect, production_qty_percent_bonus_value, current_level
        )
        
        # 检查是否已存在相同等级的效果
        existing_effect_idx = -1
        for i, effect_data in enumerate(cls._global_cost_effects[cls.type_name]):
            if effect_data['level'] == current_level:
                existing_effect_idx = i
                break
                
        if existing_effect_idx >= 0:
            # 更新现有效果
            cls._global_cost_effects[cls.type_name][existing_effect_idx] = cost_effects
        else:
            # 添加新效果
            cls._global_cost_effects[cls.type_name].append(cost_effects)
            
        # 直接应用成本修正到玩家对象上
        cls._apply_cost_effects_to_player(
            player, has_cost_effect, cost_bonus_values, has_cost_percent_effect, cost_percent_bonus_values,
            has_population_cost_effect, population_cost_bonus_value, has_population_cost_percent_effect,
            population_cost_percent_bonus_value, has_time_cost_effect, time_cost_bonus_value,
            has_time_cost_percent_effect, time_cost_percent_bonus_value, has_production_cost_effect,
            production_cost_bonus_values, has_production_cost_percent_effect, production_cost_percent_bonus_values,
            has_production_time_effect, production_time_bonus_value, has_production_time_percent_effect,
            production_time_percent_bonus_value, has_production_qty_effect, production_qty_bonus_value,
            has_production_qty_percent_effect, production_qty_percent_bonus_value
        )
        
        # 记录升级
        if cls.type_name not in player.upgrades:
            player.upgrades.append(cls.type_name)
            
        # 新增：科技加入后再次为现有单位应用效果（带去重，确保仅应用新等级且仅限有权限单位）
        for unit in player.units:
            try:
                if (
                    cls.type_name in getattr(unit, 'can_use', ()) or
                    cls.type_name in getattr(unit, 'can_use_tech', ()) or
                    cls.type_name in getattr(unit, 'can_use_skill', ())
                ):
                    cls._apply_effects_to_unit(unit, player)
            except Exception:
                pass

        # 修复：科技研究完成后，更新所有现有单位的武器和护甲属性
        # 确保现有单位也能获得新科技的加成
        for unit in player.units:
            try:
                # 更新单位的武器属性（如果武器使用了此科技）
                if hasattr(unit, 'update_weapons'):
                    unit.update_weapons()
                
                # 更新单位的护甲属性（如果护甲使用了此科技）
                if hasattr(unit, 'update_armors'):
                    unit.update_armors()
                    
            except Exception as e:
                from ..lib.log import warning
                warning(f"Error updating unit {unit.type_name} weapons/armors after tech {cls.type_name}: {e}")

    @classmethod
    def _apply_effects_to_unit(cls, unit, player):
        """为单位应用科技效果（仅限有权限的单位）"""
        # 仅对具备该科技权限的单位应用
        if not (
            cls.type_name in getattr(unit, 'can_use', ()) or
            cls.type_name in getattr(unit, 'can_use_tech', ()) or
            cls.type_name in getattr(unit, 'can_use_skill', ())
        ):
            return
        if cls.effect:
            # 初始化单位去重集合
            if not hasattr(unit, '_applied_upgrade_effects'):
                unit._applied_upgrade_effects = set()

            current_level = player.level(cls.type_name)

            def _apply_once(level, effect_def_list):
                applied_key = f"{cls.type_name}:{level}"
                if applied_key in unit._applied_upgrade_effects:
                    return
                effect_type = "effect_" + effect_def_list[0]
                if hasattr(cls, effect_type):
                    try:
                        getattr(cls, effect_type)(unit, level, *effect_def_list[1:])
                        unit._applied_upgrade_effects.add(applied_key)
                    except Exception as e:
                        from ..lib.log import warning
                        warning(f"Error applying effect {effect_type} to {unit}: {str(e)}")

            # 按等级逐级、且带去重地应用效果
            if isinstance(cls.effect[0], list):
                for lvl in range(current_level):
                    for effect_def in cls.effect:
                        _apply_once(lvl, effect_def)
            else:
                for lvl in range(current_level):
                    _apply_once(lvl, cls.effect)

    @classmethod
    def _handle_apply_bonus_effects(cls, player, effect_parts):
        """处理apply_bonus效果"""
        from ..definitions import rules
        bonus_applied = False
        
        # 遍历所有定义的单位类型
        for unit_type_name in rules.classnames():
            unit_class = rules.unit_class(unit_type_name)
            if unit_class and hasattr(unit_class, 'can_use_tech') and cls.type_name in unit_class.can_use_tech:
                # 找到可以使用此科技的单位类型
                
                # 处理各种类型的bonus
                for bonus_type in ['cost', 'time_cost', 'population_cost', 'production_cost', 'production_time', 'production_qty']:
                    if bonus_type in effect_parts[1:] and hasattr(unit_class, f'{bonus_type}_bonus'):
                        cls._apply_unit_bonus_to_player(player, unit_class, unit_type_name, bonus_type)
                        bonus_applied = True
                
                # 处理 gather_time_bonus 和 gather_qty_bonus
                if cls._has_gather_time_bonus(unit_class):
                    cls._apply_gather_time_bonus(player, unit_class, unit_type_name)
                    bonus_applied = True
                
                if cls._has_gather_qty_bonus(unit_class):
                    cls._apply_gather_qty_bonus(player, unit_class, unit_type_name)
                    bonus_applied = True
        
        return bonus_applied

    # 这些方法的具体实现通过混入类提供

    @classmethod
    def apply_global_cost_effects(cls, player):
        """应用成本相关的全局效果到玩家上，用于初始化新单位时保持一致的成本"""
        for tech_name, effects in cls._global_cost_effects.items():
            for effect_data in effects:
                level = effect_data['level']
                
                # 跳过玩家尚未研究的科技等级
                if player.level(tech_name) < level:
                    continue
                    
                # 应用成本效果
                if effect_data['has_cost_effect']:
                    for i, bonus in enumerate(effect_data['cost_bonus_values']):
                        if i < len(player.cost_bonus):
                            player.cost_bonus[i] += bonus
                
                if effect_data['has_cost_percent_effect']:
                    for i, bonus in enumerate(effect_data['cost_percent_bonus_values']):
                        if i < len(player.cost_percent_bonus):
                            player.cost_percent_bonus[i] += bonus
                
                if effect_data['has_population_cost_effect']:
                    player.population_cost_bonus += effect_data['population_cost_bonus_value']
                
                if effect_data['has_population_cost_percent_effect']:
                    player.population_cost_percent_bonus += effect_data['population_cost_percent_bonus_value']
                
                if effect_data['has_time_cost_effect']:
                    player.time_cost_bonus += effect_data['time_cost_bonus_value']
                
                if effect_data['has_time_cost_percent_effect']:
                    player.time_cost_percent_bonus += effect_data['time_cost_percent_bonus_value']
                    
                # 应用production相关效果
                if effect_data['has_production_cost_effect'] or effect_data['has_production_cost_percent_effect']:
                    if not hasattr(player, 'production_cost_bonus'):
                        player.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
                    if not hasattr(player, 'production_cost_percent_bonus'):
                        player.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
                        
                    if effect_data['has_production_cost_effect']:
                        for i, bonus in enumerate(effect_data['production_cost_bonus_values']):
                            if i < len(player.production_cost_bonus):
                                player.production_cost_bonus[i] += bonus
                                
                    if effect_data['has_production_cost_percent_effect']:
                        for i, bonus in enumerate(effect_data['production_cost_percent_bonus_values']):
                            if i < len(player.production_cost_percent_bonus):
                                player.production_cost_percent_bonus[i] += bonus
                
                if effect_data['has_production_time_effect']:
                    if not hasattr(player, 'production_time_bonus'):
                        player.production_time_bonus = 0
                    player.production_time_bonus += effect_data['production_time_bonus_value']
                
                if effect_data['has_production_time_percent_effect']:
                    if not hasattr(player, 'production_time_percent_bonus'):
                        player.production_time_percent_bonus = 0.0
                    player.production_time_percent_bonus += effect_data['production_time_percent_bonus_value']
                    
                if effect_data['has_production_qty_effect']:
                    if not hasattr(player, 'production_qty_bonus'):
                        player.production_qty_bonus = 0
                    player.production_qty_bonus += effect_data['production_qty_bonus_value']
                    
                if effect_data['has_production_qty_percent_effect']:
                    if not hasattr(player, 'production_qty_percent_bonus'):
                        player.production_qty_percent_bonus = 0.0
                    player.production_qty_percent_bonus += effect_data['production_qty_percent_bonus_value']

    @classmethod
    def upgrade_unit_to_player_level(cls, unit):
        """为单位应用玩家已拥有的所有升级效果，用于新创建的单位"""
        if not hasattr(unit, 'player') or not unit.player:
            return
        
        # 初始化单位去重集合
        if not hasattr(unit, '_applied_upgrade_effects'):
            unit._applied_upgrade_effects = set()
        
        # 检查单位是否可以使用这个科技
        if cls.type_name in getattr(unit, 'can_use', ()) or \
           cls.type_name in getattr(unit, 'can_use_tech', ()) or \
           cls.type_name in getattr(unit, 'can_use_skill', ()):
            
            # 获取玩家当前等级
            current_level = unit.player.level(cls.type_name)
            for level in range(current_level):
                if cls.effect:
                    applied_key = f"{cls.type_name}:{level}"
                    if applied_key in unit._applied_upgrade_effects:
                        continue
                    # 处理多个effects的情况
                    if isinstance(cls.effect[0], list):
                        # 处理多个effect定义的情况
                        for effect_def in cls.effect:
                            effect_type = "effect_" + effect_def[0]
                            if hasattr(cls, effect_type):
                                try:
                                    getattr(cls, effect_type)(
                                        unit, level, *effect_def[1:]
                                    )
                                except Exception as e:
                                    from ..lib.log import warning
                                    warning(f"Error applying effect {effect_type} to {unit}: {str(e)}")
                    else:
                        # 处理单个effect定义的情况
                        effect_type = "effect_" + cls.effect[0]
                        if hasattr(cls, effect_type):
                            try:
                                getattr(cls, effect_type)(
                                    unit, level, *cls.effect[1:]
                                )
                            except Exception as e:
                                from ..lib.log import warning
                                warning(f"Error applying effect {effect_type} to {unit}: {str(e)}")
                    # 标记该等级效果已应用
                    unit._applied_upgrade_effects.add(applied_key)

    # 这些方法的具体实现将在相应的子模块中定义
    @classmethod
    def _has_gather_time_bonus(cls, unit_class):
        """检查单位类是否有 gather_time_bonus 相关属性"""
        # 实现将在gather_effects.py中
        return False

    @classmethod
    def _has_gather_qty_bonus(cls, unit_class):
        """检查单位类是否有 gather_qty_bonus 相关属性"""
        # 实现将在gather_effects.py中
        return False

    @classmethod
    def _apply_gather_time_bonus(cls, player, unit_class, unit_type_name):
        """应用 gather_time_bonus 到玩家"""
        # 实现将在gather_effects.py中
        pass

    @classmethod
    def _apply_gather_qty_bonus(cls, player, unit_class, unit_type_name):
        """应用 gather_qty_bonus 到玩家"""
        # 实现将在gather_effects.py中
        pass

    @classmethod
    def _apply_unit_bonus_to_player(cls, player, unit_class, unit_type_name, bonus_type):
        """将单位的bonus应用到玩家"""
        # 实现将在cost_effects.py中
        pass