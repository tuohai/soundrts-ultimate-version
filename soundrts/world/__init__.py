"""
World模块 - 游戏世界管理系统

该模块将原本庞大的world.py文件拆分为4个功能模块：
- world_core.py: 核心World类定义和基础方法
- world_objects.py: 对象查询、单位类管理和实体相关功能  
- world_game.py: 游戏更新循环、事件处理和游戏流程控制
- world_map.py: 地图解析、构建、保存和相关功能
"""

from .world_core import World as CoreWorld, GLOBAL_population_LIMIT, PROFILE
from .world_objects import WorldObjectsMixin
from .world_game import WorldGameMixin  
from .world_map import WorldMapMixin
from .world_core import MapError, map_error, map_warning, check_squares, convert_and_split_first_numbers


class World(CoreWorld, WorldObjectsMixin, WorldGameMixin, WorldMapMixin):
    """
    完整的游戏世界类
    
    通过多重继承组合各个功能模块，提供完整的游戏世界功能。
    这种设计保持了原有API的兼容性，同时大大提高了代码的可维护性。
    """
    pass


# 为了保持向后兼容性，导出所有原来world.py中的公共符号
__all__ = [
    'World',
    'MapError', 
    'map_error',
    'map_warning',
    'check_squares',
    'convert_and_split_first_numbers',
    'GLOBAL_population_LIMIT',
    'PROFILE'
]