"""成本相关效果处理模块

包含处理各种成本效果的方法，如：
- 资源成本修正
- 时间成本修正
- 人口成本修正
- 生产成本修正
"""

from ..definitions import MAX_NB_OF_RESOURCE_TYPES
from ..lib.nofloat import PRECISION


class CostEffectsMixin:
    """成本效果处理混入类"""

    @classmethod
    def _process_cost_effects(cls, effect_parts):
        """处理成本相关效果，返回效果参数"""
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

        if len(effect_parts) >= 3:
            if effect_parts[0] == "bonus":
                if effect_parts[1] == "cost":
                    # 检查是否是百分比值
                    if any(str(x).endswith('%') for x in effect_parts[2:]):
                        has_cost_percent_effect = True
                        # 解析cost加成百分比值
                        try:
                            for i in range(2, len(effect_parts)):
                                val = effect_parts[i]
                                if str(val).endswith('%'):
                                    # 将百分比字符串转换为浮点数并除以100
                                    val_str = str(val).rstrip('%')
                                    cost_percent_bonus_values.append(float(val_str) / 100.0)
                                else:
                                    # 不是百分比值的话，添加0.0
                                    cost_percent_bonus_values.append(0.0)
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing percent cost values in effect: {effect_parts}")
                    else:
                        has_cost_effect = True
                        # 解析cost加成值
                        try:
                            for i in range(2, len(effect_parts)):
                                # 将字符串转换为数值并应用PRECISION
                                cost_bonus_values.append(int(float(effect_parts[i]) * PRECISION))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing cost values in effect: {effect_parts}")
                elif effect_parts[1] == "population_cost" and len(effect_parts) >= 3:
                    # 检查是否是百分比值
                    if str(effect_parts[2]).endswith('%'):
                        has_population_cost_percent_effect = True
                        # 解析population_cost加成百分比值
                        try:
                            val_str = str(effect_parts[2]).rstrip('%')
                            population_cost_percent_bonus_value = float(val_str) / 100.0
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing population_cost percent value in effect: {effect_parts}")
                    else:
                        has_population_cost_effect = True
                        # 解析population_cost加成值
                        try:
                            population_cost_bonus_value = int(float(effect_parts[2]))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing population_cost value in effect: {effect_parts}")
                elif effect_parts[1] == "time_cost" and len(effect_parts) >= 3:
                    # 检查是否是百分比值
                    if str(effect_parts[2]).endswith('%'):
                        has_time_cost_percent_effect = True
                        # 解析time_cost加成百分比值
                        try:
                            val_str = str(effect_parts[2]).rstrip('%')
                            time_cost_percent_bonus_value = float(val_str) / 100.0
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing time_cost percent value in effect: {effect_parts}")
                    else:
                        has_time_cost_effect = True
                        # 解析time_cost加成值
                        try:
                            time_cost_bonus_value = int(float(effect_parts[2]))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing time_cost value in effect: {effect_parts}")
                # 添加对production_cost的支持
                elif effect_parts[1] == "production_cost" and len(effect_parts) >= 3:
                    # 检查是否是百分比值
                    if any(str(x).endswith('%') for x in effect_parts[2:]):
                        has_production_cost_percent_effect = True
                        # 解析production_cost加成百分比值
                        try:
                            for i in range(2, len(effect_parts)):
                                val = effect_parts[i]
                                if str(val).endswith('%'):
                                    # 将百分比字符串转换为浮点数并除以100
                                    val_str = str(val).rstrip('%')
                                    production_cost_percent_bonus_values.append(float(val_str) / 100.0)
                                else:
                                    # 不是百分比值的话，添加0.0
                                    production_cost_percent_bonus_values.append(0.0)
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing percent production_cost values in effect: {effect_parts}")
                    else:
                        has_production_cost_effect = True
                        # 解析production_cost加成值
                        try:
                            for i in range(2, len(effect_parts)):
                                # 将字符串转换为数值并应用PRECISION
                                production_cost_bonus_values.append(int(float(effect_parts[i]) * PRECISION))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing production_cost values in effect: {effect_parts}")
                # 添加对production_time的支持
                elif effect_parts[1] == "production_time" and len(effect_parts) >= 3:
                    # 检查是否是百分比值
                    if str(effect_parts[2]).endswith('%'):
                        has_production_time_percent_effect = True
                        # 解析production_time加成百分比值
                        try:
                            val_str = str(effect_parts[2]).rstrip('%')
                            production_time_percent_bonus_value = float(val_str) / 100.0
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing production_time percent value in effect: {effect_parts}")
                    else:
                        has_production_time_effect = True
                        # 解析production_time加成值
                        try:
                            production_time_bonus_value = int(float(effect_parts[2]))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing production_time value in effect: {effect_parts}")
                # 添加对production_qty的支持
                elif effect_parts[1] == "production_qty" and len(effect_parts) >= 3:
                    # 检查是否是百分比值
                    if str(effect_parts[2]).endswith('%'):
                        has_production_qty_percent_effect = True
                        # 解析production_qty加成百分比值
                        try:
                            val_str = str(effect_parts[2]).rstrip('%')
                            production_qty_percent_bonus_value = float(val_str) / 100.0
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing production_qty percent value in effect: {effect_parts}")
                    else:
                        has_production_qty_effect = True
                        # 解析production_qty加成值
                        try:
                            production_qty_bonus_value = int(float(effect_parts[2]))
                        except (ValueError, IndexError):
                            from ..lib.log import warning
                            warning(f"Error parsing production_qty value in effect: {effect_parts}")

        # 如果没有检测到任何成本效果，返回None
        if not any([has_cost_effect, has_cost_percent_effect, has_population_cost_effect,
                   has_population_cost_percent_effect, has_time_cost_effect, has_time_cost_percent_effect,
                   has_production_cost_effect, has_production_cost_percent_effect, has_production_time_effect,
                   has_production_time_percent_effect, has_production_qty_effect, has_production_qty_percent_effect]):
            return None

        return (has_cost_effect, cost_bonus_values, has_cost_percent_effect, cost_percent_bonus_values,
                has_population_cost_effect, population_cost_bonus_value, has_population_cost_percent_effect,
                population_cost_percent_bonus_value, has_time_cost_effect, time_cost_bonus_value,
                has_time_cost_percent_effect, time_cost_percent_bonus_value, has_production_cost_effect,
                production_cost_bonus_values, has_production_cost_percent_effect, production_cost_percent_bonus_values,
                has_production_time_effect, production_time_bonus_value, has_production_time_percent_effect,
                production_time_percent_bonus_value, has_production_qty_effect, production_qty_bonus_value,
                has_production_qty_percent_effect, production_qty_percent_bonus_value)

    @classmethod
    def _create_cost_effects_dict(cls, has_cost_effect, cost_bonus_values, has_cost_percent_effect, cost_percent_bonus_values,
                                 has_population_cost_effect, population_cost_bonus_value, has_population_cost_percent_effect,
                                 population_cost_percent_bonus_value, has_time_cost_effect, time_cost_bonus_value,
                                 has_time_cost_percent_effect, time_cost_percent_bonus_value, has_production_cost_effect,
                                 production_cost_bonus_values, has_production_cost_percent_effect, production_cost_percent_bonus_values,
                                 has_production_time_effect, production_time_bonus_value, has_production_time_percent_effect,
                                 production_time_percent_bonus_value, has_production_qty_effect, production_qty_bonus_value,
                                 has_production_qty_percent_effect, production_qty_percent_bonus_value, current_level):
        """创建成本效果字典"""
        return {
            'has_cost_effect': has_cost_effect,
            'cost_bonus_values': cost_bonus_values,
            'has_cost_percent_effect': has_cost_percent_effect,
            'cost_percent_bonus_values': cost_percent_bonus_values,
            'has_population_cost_effect': has_population_cost_effect,
            'population_cost_bonus_value': population_cost_bonus_value,
            'has_population_cost_percent_effect': has_population_cost_percent_effect,
            'population_cost_percent_bonus_value': population_cost_percent_bonus_value,
            'has_time_cost_effect': has_time_cost_effect,
            'time_cost_bonus_value': time_cost_bonus_value,
            'has_time_cost_percent_effect': has_time_cost_percent_effect,
            'time_cost_percent_bonus_value': time_cost_percent_bonus_value,
            'has_production_cost_effect': has_production_cost_effect,
            'production_cost_bonus_values': production_cost_bonus_values,
            'has_production_cost_percent_effect': has_production_cost_percent_effect,
            'production_cost_percent_bonus_values': production_cost_percent_bonus_values,
            'has_production_time_effect': has_production_time_effect,
            'production_time_bonus_value': production_time_bonus_value,
            'has_production_time_percent_effect': has_production_time_percent_effect,
            'production_time_percent_bonus_value': production_time_percent_bonus_value,
            'has_production_qty_effect': has_production_qty_effect,
            'production_qty_bonus_value': production_qty_bonus_value,
            'has_production_qty_percent_effect': has_production_qty_percent_effect,
            'production_qty_percent_bonus_value': production_qty_percent_bonus_value,
            'level': current_level
        }

    @classmethod
    def _apply_cost_effects_to_player(cls, player, has_cost_effect, cost_bonus_values, has_cost_percent_effect, 
                                     cost_percent_bonus_values, has_population_cost_effect, population_cost_bonus_value,
                                     has_population_cost_percent_effect, population_cost_percent_bonus_value,
                                     has_time_cost_effect, time_cost_bonus_value, has_time_cost_percent_effect,
                                     time_cost_percent_bonus_value, has_production_cost_effect, production_cost_bonus_values,
                                     has_production_cost_percent_effect, production_cost_percent_bonus_values,
                                     has_production_time_effect, production_time_bonus_value, has_production_time_percent_effect,
                                     production_time_percent_bonus_value, has_production_qty_effect, production_qty_bonus_value,
                                     has_production_qty_percent_effect, production_qty_percent_bonus_value):
        """将成本效果应用到玩家"""
        # 直接应用成本修正到玩家对象上
        if has_cost_effect:
            for i, bonus in enumerate(cost_bonus_values):
                if i < len(player.cost_bonus):
                    player.cost_bonus[i] += bonus
        
        if has_cost_percent_effect:
            for i, bonus in enumerate(cost_percent_bonus_values):
                if i < len(player.cost_percent_bonus):
                    player.cost_percent_bonus[i] += bonus
        
        if has_population_cost_effect:
            player.population_cost_bonus += population_cost_bonus_value
        
        if has_population_cost_percent_effect:
            player.population_cost_percent_bonus += population_cost_percent_bonus_value
        
        if has_time_cost_effect:
            player.time_cost_bonus += time_cost_bonus_value
        
        if has_time_cost_percent_effect:
            player.time_cost_percent_bonus += time_cost_percent_bonus_value
            
        # 添加对production_cost, production_time和production_qty的支持
        # 初始化玩家对象上的新属性（如果尚未存在）
        if has_production_cost_effect or has_production_cost_percent_effect:
            if not hasattr(player, 'production_cost_bonus'):
                player.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            if not hasattr(player, 'production_cost_percent_bonus'):
                player.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
                
            if has_production_cost_effect:
                for i, bonus in enumerate(production_cost_bonus_values):
                    if i < len(player.production_cost_bonus):
                        player.production_cost_bonus[i] += bonus
                        
            if has_production_cost_percent_effect:
                for i, bonus in enumerate(production_cost_percent_bonus_values):
                    if i < len(player.production_cost_percent_bonus):
                        player.production_cost_percent_bonus[i] += bonus
        
        if has_production_time_effect:
            if not hasattr(player, 'production_time_bonus'):
                player.production_time_bonus = 0
            player.production_time_bonus += production_time_bonus_value
        
        if has_production_time_percent_effect:
            if not hasattr(player, 'production_time_percent_bonus'):
                player.production_time_percent_bonus = 0.0
            player.production_time_percent_bonus += production_time_percent_bonus_value
            
        if has_production_qty_effect:
            if not hasattr(player, 'production_qty_bonus'):
                player.production_qty_bonus = 0
            player.production_qty_bonus += production_qty_bonus_value
            
        if has_production_qty_percent_effect:
            if not hasattr(player, 'production_qty_percent_bonus'):
                player.production_qty_percent_bonus = 0.0
            player.production_qty_percent_bonus += production_qty_percent_bonus_value

    @classmethod
    def _apply_unit_bonus_to_player(cls, player, unit_class, unit_type_name, bonus_type):
        """将单位的bonus应用到玩家"""
        bonus_value = getattr(unit_class, f'{bonus_type}_bonus')
        
        # 初始化玩家的相应加成（如果还没有）
        if bonus_type == "cost":
            if not hasattr(player, 'cost_bonus'):
                player.cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            if not hasattr(player, 'cost_percent_bonus'):
                player.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        elif bonus_type == "time_cost":
            if not hasattr(player, 'time_cost_bonus'):
                player.time_cost_bonus = 0
            if not hasattr(player, 'time_cost_percent_bonus'):
                player.time_cost_percent_bonus = 0.0
        elif bonus_type == "population_cost":
            if not hasattr(player, 'population_cost_bonus'):
                player.population_cost_bonus = 0
            if not hasattr(player, 'population_cost_percent_bonus'):
                player.population_cost_percent_bonus = 0.0
        elif bonus_type == "production_cost":
            if not hasattr(player, 'production_cost_bonus'):
                player.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            if not hasattr(player, 'production_cost_percent_bonus'):
                player.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        elif bonus_type == "production_time":
            if not hasattr(player, 'production_time_bonus'):
                player.production_time_bonus = 0
            if not hasattr(player, 'production_time_percent_bonus'):
                player.production_time_percent_bonus = 0.0
        elif bonus_type == "production_qty":
            if not hasattr(player, 'production_qty_bonus'):
                player.production_qty_bonus = 0
            if not hasattr(player, 'production_qty_percent_bonus'):
                player.production_qty_percent_bonus = 0.0
        
        # 初始化已应用的成本加成追踪（防止重复应用）
        if not hasattr(player, '_applied_cost_bonuses'):
            player._applied_cost_bonuses = set()
        
        # 创建一个唯一的标识符，用于跟踪这个特定的加成
        bonus_id = f"{unit_type_name}_{bonus_type}_{str(bonus_value)}"
        
        # 检查是否已经应用过这个加成
        if bonus_id not in player._applied_cost_bonuses:
            # 应用加成到玩家
            if bonus_type in ["cost", "production_cost"]:
                # 处理列表型成本
                bonus_attr = f'{bonus_type}_bonus'
                percent_attr = f'{bonus_type}_percent_bonus'
                
                if isinstance(bonus_value, (list, tuple)):
                    for i, bonus in enumerate(bonus_value):
                        current_bonus = getattr(player, bonus_attr)
                        current_percent = getattr(player, percent_attr)
                        
                        if i < len(current_bonus):
                            # 处理百分比格式和普通数值
                            if isinstance(bonus, str) and bonus.endswith('%'):
                                # 百分比格式
                                bonus_str = bonus.rstrip('%')
                                bonus_val = float(bonus_str) / 100.0
                                if i < len(current_percent):
                                    current_percent[i] += bonus_val
                            else:
                                # 普通数值格式
                                bonus_val = int(float(bonus) * PRECISION) if isinstance(bonus, str) else int(bonus * PRECISION)
                                current_bonus[i] += bonus_val
                else:
                    # 单个数值的情况
                    current_bonus = getattr(player, bonus_attr)
                    current_percent = getattr(player, percent_attr)
                    
                    if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                        # 百分比格式
                        bonus_str = bonus_value.rstrip('%')
                        bonus_val = float(bonus_str) / 100.0
                        if len(current_percent) > 0:
                            current_percent[0] += bonus_val
                    else:
                        # 普通数值格式
                        bonus_val = int(float(bonus_value) * PRECISION) if isinstance(bonus_value, str) else int(bonus_value * PRECISION)
                        if len(current_bonus) > 0:
                            current_bonus[0] += bonus_val
            else:
                # 处理单值型成本（time_cost, population_cost, production_time, production_qty）
                bonus_attr = f'{bonus_type}_bonus'
                percent_attr = f'{bonus_type}_percent_bonus'
                
                # 处理 bonus_value 可能是列表的情况
                if isinstance(bonus_value, list):
                    # 如果是列表，取第一个元素
                    bonus_value = bonus_value[0] if bonus_value else '0'
                
                if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                    # 百分比格式
                    bonus_str = bonus_value.rstrip('%')
                    bonus_val = float(bonus_str) / 100.0
                    current_val = getattr(player, percent_attr, 0.0)
                    setattr(player, percent_attr, current_val + bonus_val)
                else:
                    # 普通数值格式
                    bonus_val = int(float(bonus_value)) if isinstance(bonus_value, str) else int(bonus_value)
                    current_val = getattr(player, bonus_attr, 0)
                    setattr(player, bonus_attr, current_val + bonus_val)
            
            # 记录已应用的加成
            player._applied_cost_bonuses.add(bonus_id)
            
            from ..lib.log import debug
            debug(f"Applied {unit_type_name} {bonus_type} bonus {bonus_value} to player {player.number} via apply_bonus effect")