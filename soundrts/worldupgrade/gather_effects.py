"""采集奖励处理模块

包含处理采集相关奖励的方法，如：
- 采集时间奖励检测和应用
- 采集数量奖励检测和应用
"""


class GatherEffectsMixin:
    """采集效果处理混入类"""

    @classmethod
    def _has_gather_time_bonus(cls, unit_class):
        """检查单位类是否有 gather_time_bonus 相关属性"""
        # 检查通用的 gather_time_bonus
        if hasattr(unit_class, 'gather_time_bonus'):
            return True
        
        # 检查所有以 gather_time_ 开头的属性，看是否有对应的 _bonus 属性
        for attr_name in dir(unit_class):
            if (attr_name.startswith('gather_time_') and 
                not attr_name.endswith('_bonus') and 
                hasattr(unit_class, f'{attr_name}_bonus')):
                return True
            elif attr_name.startswith('gather_time_') and attr_name.endswith('_bonus'):
                return True
        
        return False

    @classmethod
    def _has_gather_qty_bonus(cls, unit_class):
        """检查单位类是否有 gather_qty_bonus 相关属性"""
        # 检查通用的 gather_qty_bonus
        if hasattr(unit_class, 'gather_qty_bonus'):
            return True
        
        # 检查所有以 gather_qty_ 开头的属性，看是否有对应的 _bonus 属性
        for attr_name in dir(unit_class):
            if (attr_name.startswith('gather_qty_') and 
                not attr_name.endswith('_bonus') and 
                hasattr(unit_class, f'{attr_name}_bonus')):
                return True
            elif attr_name.startswith('gather_qty_') and attr_name.endswith('_bonus'):
                return True
        
        return False

    @classmethod
    def _apply_gather_time_bonus(cls, player, unit_class, unit_type_name):
        """应用 gather_time_bonus 到玩家"""
        # 初始化玩家的 gather_time_bonus（如果还没有）
        if not hasattr(player, 'gather_time_bonus'):
            player.gather_time_bonus = {}
        
        # 初始化已应用的加成追踪（防止重复应用）
        if not hasattr(player, '_applied_cost_bonuses'):
            player._applied_cost_bonuses = set()
        
        # 检查通用的 gather_time_bonus
        if hasattr(unit_class, 'gather_time_bonus'):
            bonus_value = unit_class.gather_time_bonus
            bonus_id = f"{unit_type_name}_gather_time_{str(bonus_value)}"
            
            if bonus_id not in player._applied_cost_bonuses:
                cls._process_gather_time_bonus_value(player, bonus_value)
                
                # 记录已应用的加成
                player._applied_cost_bonuses.add(bonus_id)
                
                from ..lib.log import debug
                debug(f"Applied {unit_type_name} gather_time bonus {bonus_value} to player {player.number}")
        
        # 检查所有以 _bonus 结尾且与 gather_time 相关的属性
        for attr_name in dir(unit_class):
            if attr_name.endswith('_bonus') and 'gather_time' in attr_name:
                bonus_value = getattr(unit_class, attr_name)
                bonus_id = f"{unit_type_name}_{attr_name}_{str(bonus_value)}"
                
                if bonus_id not in player._applied_cost_bonuses:
                    # 解析资源类型
                    # gather_time_wood_bonus -> wood
                    # gather_time_bonus -> all (通用)
                    if attr_name == 'gather_time_bonus':
                        resource_type = 'all'
                    elif attr_name.startswith('gather_time_') and attr_name.endswith('_bonus'):
                        resource_type = attr_name.replace('gather_time_', '').replace('_bonus', '')
                    else:
                        continue  # 跳过不识别的格式
                    
                    cls._apply_gather_time_bonus_to_resource(player, resource_type, bonus_value)
                    
                    # 记录已应用的加成
                    player._applied_cost_bonuses.add(bonus_id)
                    
                    from ..lib.log import debug
                    debug(f"Applied {unit_type_name} {resource_type} gather_time bonus {bonus_value} to player {player.number}")

    @classmethod
    def _apply_gather_qty_bonus(cls, player, unit_class, unit_type_name):
        """应用 gather_qty_bonus 到玩家"""
        # 初始化玩家的 gather_qty_bonus（如果还没有）
        if not hasattr(player, 'gather_qty_bonus'):
            player.gather_qty_bonus = {}
        
        # 初始化已应用的加成追踪（防止重复应用）
        if not hasattr(player, '_applied_cost_bonuses'):
            player._applied_cost_bonuses = set()
        
        # 检查通用的 gather_qty_bonus
        if hasattr(unit_class, 'gather_qty_bonus'):
            bonus_value = unit_class.gather_qty_bonus
            bonus_id = f"{unit_type_name}_gather_qty_{str(bonus_value)}"
            
            if bonus_id not in player._applied_cost_bonuses:
                cls._process_gather_qty_bonus_value(player, bonus_value)
                
                # 记录已应用的加成
                player._applied_cost_bonuses.add(bonus_id)
                
                from ..lib.log import debug
                debug(f"Applied {unit_type_name} gather_qty bonus {bonus_value} to player {player.number}")
        
        # 检查所有以 _bonus 结尾且与 gather_qty 相关的属性
        for attr_name in dir(unit_class):
            if attr_name.endswith('_bonus') and 'gather_qty' in attr_name:
                bonus_value = getattr(unit_class, attr_name)
                bonus_id = f"{unit_type_name}_{attr_name}_{str(bonus_value)}"
                
                if bonus_id not in player._applied_cost_bonuses:
                    # 解析资源类型
                    # gather_qty_wood_bonus -> wood
                    # gather_qty_bonus -> all (通用)
                    if attr_name == 'gather_qty_bonus':
                        resource_type = 'all'
                    elif attr_name.startswith('gather_qty_') and attr_name.endswith('_bonus'):
                        resource_type = attr_name.replace('gather_qty_', '').replace('_bonus', '')
                    else:
                        continue  # 跳过不识别的格式
                    
                    cls._apply_gather_qty_bonus_to_resource(player, resource_type, bonus_value)
                    
                    # 记录已应用的加成
                    player._applied_cost_bonuses.add(bonus_id)
                    
                    from ..lib.log import debug
                    debug(f"Applied {unit_type_name} {resource_type} gather_qty bonus {bonus_value} to player {player.number}")

    @classmethod
    def _process_gather_time_bonus_value(cls, player, bonus_value):
        """处理gather_time_bonus的值"""
        if isinstance(bonus_value, list):
            # 列表格式: ["wood", "-7"] 或 ["wood", "-7", "gold", "-5"]
            i = 0
            while i < len(bonus_value) - 1:
                resource_type = bonus_value[i]
                value = bonus_value[i + 1]
                
                cls._apply_gather_time_bonus_to_resource(player, resource_type, value)
                i += 2
        elif isinstance(bonus_value, dict):
            # 字典格式: {"wood": -7, "gold": -5}
            for resource, value in bonus_value.items():
                cls._apply_gather_time_bonus_to_resource(player, resource, value)
        else:
            # 单一数值格式，应用到 "all"
            cls._apply_gather_time_bonus_to_resource(player, "all", bonus_value)

    @classmethod
    def _process_gather_qty_bonus_value(cls, player, bonus_value):
        """处理gather_qty_bonus的值"""
        if isinstance(bonus_value, list):
            # 列表格式: ["wood", "2"] 或 ["wood", "2", "gold", "1"]
            i = 0
            while i < len(bonus_value) - 1:
                resource_type = bonus_value[i]
                value = bonus_value[i + 1]
                
                cls._apply_gather_qty_bonus_to_resource(player, resource_type, value)
                i += 2
        elif isinstance(bonus_value, dict):
            # 字典格式: {"wood": 2, "gold": 1}
            for resource, value in bonus_value.items():
                cls._apply_gather_qty_bonus_to_resource(player, resource, value)
        else:
            # 单一数值格式，应用到 "all"
            cls._apply_gather_qty_bonus_to_resource(player, "all", bonus_value)

    @classmethod
    def _apply_gather_time_bonus_to_resource(cls, player, resource_type, value):
        """将gather_time_bonus应用到特定资源类型"""
        if resource_type not in player.gather_time_bonus:
            player.gather_time_bonus[resource_type] = 0
        
        if isinstance(value, str) and value.endswith('%'):
            # 保持百分比格式
            player.gather_time_bonus[resource_type] = value
        else:
            # 累加数值
            current_value = player.gather_time_bonus[resource_type]
            if isinstance(current_value, str) and current_value.endswith('%'):
                # 如果当前是百分比，转换为数值再累加
                current_numeric = float(current_value[:-1])
                player.gather_time_bonus[resource_type] = current_numeric + int(value)
            else:
                player.gather_time_bonus[resource_type] = int(current_value) + int(value)

    @classmethod
    def _apply_gather_qty_bonus_to_resource(cls, player, resource_type, value):
        """将gather_qty_bonus应用到特定资源类型"""
        if resource_type not in player.gather_qty_bonus:
            player.gather_qty_bonus[resource_type] = 0
        
        if isinstance(value, str) and value.endswith('%'):
            # 保持百分比格式
            player.gather_qty_bonus[resource_type] = value
        else:
            # 累加数值
            current_value = player.gather_qty_bonus[resource_type]
            if isinstance(current_value, str) and current_value.endswith('%'):
                # 如果当前是百分比，转换为数值再累加
                current_numeric = float(current_value[:-1])
                player.gather_qty_bonus[resource_type] = current_numeric + int(value)
            else:
                player.gather_qty_bonus[resource_type] = int(current_value) + int(value)