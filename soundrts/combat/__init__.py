"""
Sound RTS游戏世界攻击处理模块
"""
# 确保导出关键模块
from .damage import DamageMixin, DamageCalculationMixin, DamageEffectsMixin

# 导入其他必要的模块
from .targeting import *
from .splash import *
from .hit_miss import *
from .attack_action import *

# 为了保证兼容性，从CreatureAttack导入所有方法到当前命名空间
from .creature_attack import CreatureAttack 

__all__ = [
    'DamageMixin', 'DamageCalculationMixin', 'DamageEffectsMixin',
    'CreatureAttack'
] 