"""世界升级系统模块

这个模块包含游戏中的升级系统实现，被拆分为多个子模块：
- base: 基础类和核心功能
- cost_effects: 成本相关效果处理
- attribute_effects: 属性效果处理器
- production_effects: 生产相关效果
- gather_effects: 采集奖励处理
"""

from .base import Upgrade, is_an_upgrade

# 导出主要的类和函数
__all__ = ['Upgrade', 'is_an_upgrade']