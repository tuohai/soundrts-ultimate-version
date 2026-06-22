"""
伤害计算模块 - 仅用于向后兼容
实际实现已拆分到 damage_calculation.py 和 damage_effects.py
"""

# 导入并重新导出DamageMixin，保持向后兼容性
from .damage_effects import DamageMixin

# 对于需要直接访问子模块的情况
from .damage_calculation import DamageCalculationMixin
from .damage_effects import DamageEffectsMixin

# 提供一个简单的导入接口，可以导入这个文件来获取所有相关类
__all__ = ['DamageMixin', 'DamageCalculationMixin', 'DamageEffectsMixin']