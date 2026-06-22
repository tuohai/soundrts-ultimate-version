"""生产相关效果模块

包含处理各种生产相关效果的方法，如：
- 生产时间和数量修正
- 自动/手动生产控制
- 存储容量升级
- 资源容量上限修正
"""

from ..definitions import MAX_NB_OF_RESOURCE_TYPES


class ProductionEffectsMixin:
    """生产效果处理混入类"""

    @classmethod
    def effect_production_time(cls, unit, start_level, value=None):
        """处理生产时间的升级效果
        格式: effect production_time value
        """
        if not hasattr(unit, "production_time") or value is None:
            return
            
        try:
            # 转换value为整数（秒）
            new_time = int(float(value))
            unit.production_time = new_time
        except (ValueError, TypeError):
            pass

    @classmethod
    def effect_production_qty(cls, unit, start_level, value):
        """处理生产数量的升级效果
        格式: effect production_qty value
        """
        if not hasattr(unit, "production_qty"):
            return
            
        try:
            # 转换value为整数
            new_qty = int(float(value))
            unit.production_qty = new_qty
        except (ValueError, TypeError):
            pass

    @classmethod
    def effect_resource_rewards(cls, unit, start_level, *args):
        """升级击杀奖励资源量"""
        # 不对单位进行操作，仅对技术等级有效
        pass

    @classmethod
    def effect_storage_bonus_upgrade(cls, unit, start_level, *args):
        """升级存储容量
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        args -- 存储奖励增量，按照资源类型顺序：resource1增量, resource2增量, resource3增量, ...
        """
        if not args:
            return
            
        try:
            # 检查unit是否有storage_bonus属性
            if not hasattr(unit, 'storage_bonus') or not unit.storage_bonus:
                # 如果没有则初始化
                unit.storage_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
                
            # 动态应用每个参数到对应的资源类型索引
            for i, bonus_value in enumerate(args):
                if i < len(unit.storage_bonus):
                    try:
                        bonus_int = int(bonus_value)
                        unit.storage_bonus[i] += bonus_int
                    except (ValueError, TypeError):
                        from ..lib.log import warning
                        warning(f"Invalid storage bonus value at index {i}: {bonus_value}")
                        
            # 如果单位是玩家单位，更新玩家的存储奖励
            if hasattr(unit, 'player') and unit.player:
                unit.player._update_storage_bonus()
                
        except Exception as e:
            from ..lib.log import warning
            warning(f"Error in effect_storage_bonus_upgrade: {str(e)}")

    @classmethod
    def effect_auto_production(cls, unit, start_level, value=None):
        """处理自动生产的启用状态
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        value -- 自动生产的启用状态，1表示启用，0表示禁用
        """
        if value is None:
            return
            
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 设置auto_production属性
            unit.auto_production = enabled
            
            # 记录级别信息
            if not hasattr(unit, 'auto_production_level'):
                unit.auto_production_level = start_level
                
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_auto_production: {str(e)}")

    @classmethod
    def effect_manual_production(cls, unit, start_level, value=None):
        """处理手动生产的启用状态
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        value -- 手动生产的启用状态，1表示启用，0表示禁用
        """
        if value is None:
            return
            
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 设置manual_production属性
            unit.manual_production = enabled
            
            # 记录级别信息
            if not hasattr(unit, 'manual_production_level'):
                unit.manual_production_level = start_level
                
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_manual_production: {str(e)}")

    @classmethod
    def effect_auto_cultivate(cls, unit, start_level, value=None):
        """处理自动耕种的启用状态（auto_production的别名）
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        value -- 自动耕种的启用状态，1表示启用，0表示禁用
        """
        if value is None:
            return
            
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 同时设置auto_cultivate和auto_production属性
            unit.auto_cultivate = enabled
            unit.auto_production = enabled  # 同时设置auto_production以保持兼容性
            
            # 记录升级信息
            if not hasattr(unit, 'auto_cultivate_level'):
                unit.auto_cultivate_level = start_level
                
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_auto_cultivate: {str(e)}")

    @classmethod
    def effect_manual_cultivate(cls, unit, start_level, value=None):
        """处理手动耕种的启用状态（manual_production的别名）
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        value -- 手动耕种的启用状态，1表示启用，0表示禁用
        """
        if value is None:
            return
            
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 同时设置manual_cultivate和manual_production属性
            unit.manual_cultivate = enabled
            unit.manual_production = enabled  # 同时设置manual_production以保持兼容性
            
            # 记录升级信息
            if not hasattr(unit, 'manual_cultivate_level'):
                unit.manual_cultivate_level = start_level
                
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_manual_cultivate: {str(e)}")

    @classmethod
    def effect_resource_volume_max(cls, unit, start_level, *args):
        """升级资源容量上限
        
        参数:
        unit -- 单位对象
        start_level -- 开始的升级等级
        args -- 资源容量上限增量，可以是单一数值或多个资源类型的值
        """
        if not args:
            return
            
        try:
            # 检查unit是否有resource_volume_max属性
            if not hasattr(unit, 'resource_volume_max'):
                return
                
            # 如果只有一个参数，应用于所有资源类型
            if len(args) == 1:
                value_int = int(float(args[0]))
                if isinstance(unit.resource_volume_max, list):
                    # 对每个资源类型应用相同的增量
                    for i in range(len(unit.resource_volume_max)):
                        unit.resource_volume_max[i] += value_int
                else:
                    # 单一资源类型
                    unit.resource_volume_max += value_int
            else:
                # 多个参数，对应不同资源类型
                if isinstance(unit.resource_volume_max, list):
                    # 逐个应用每种资源类型的增量
                    for i in range(min(len(unit.resource_volume_max), len(args))):
                        value_int = int(float(args[i]))
                        unit.resource_volume_max[i] += value_int
                else:
                    # 单一资源类型，使用第一个参数
                    value_int = int(float(args[0]))
                    unit.resource_volume_max += value_int
                    
            # 如果单位有qty属性，确保当前资源量不超过新的上限
            if hasattr(unit, 'qty') and hasattr(unit, 'qty_max'):
                # 更新qty_max值与resource_volume_max保持一致
                if isinstance(unit.resource_volume_max, list):
                    if not isinstance(unit.qty_max, list):
                        unit.qty_max = unit.resource_volume_max[0]
                    else:
                        for i in range(min(len(unit.qty_max), len(unit.resource_volume_max))):
                            unit.qty_max[i] = unit.resource_volume_max[i]
                else:
                    unit.qty_max = unit.resource_volume_max
                    
                # 通知资源量更新
                if hasattr(unit, 'notify'):
                    unit.notify(f"qty_max_update,{unit.qty_max}")
                
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_resource_volume_max: {str(e)}")