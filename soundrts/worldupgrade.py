# 为了保持向后兼容性，从新的模块结构中导入所有内容
from .worldupgrade.base import Upgrade, is_an_upgrade

# 导出所有原来在此文件中的内容
__all__ = ['Upgrade', 'is_an_upgrade']

# 移除原始代码，所有功能现在都在worldupgrade模块中
# 原始的2366行代码已经被拆分成以下5个模块：
# - worldupgrade/base.py: 基础类和核心功能
# - worldupgrade/cost_effects.py: 成本相关效果处理
# - worldupgrade/attribute_effects.py: 属性效果处理器
# - worldupgrade/production_effects.py: 生产相关效果
# - worldupgrade/gather_effects.py: 采集奖励处理