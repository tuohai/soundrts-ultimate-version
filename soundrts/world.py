"""
World模块兼容性导入文件

该文件保持对原world.py的向后兼容性，将导入重定向到新的world包。
原来的庞大world.py文件已被拆分为更小、更易维护的模块。
"""

# 从新的world包导入所有原有功能
from .world import (
    World,
    MapError,
    map_error, 
    map_warning,
    check_squares,
    convert_and_split_first_numbers,
    GLOBAL_population_LIMIT,
    PROFILE
)

# 导出所有原来world.py中的公共符号，保持API兼容性
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