# clientgameentity模块 - 客户端游戏实体视图
from .base import SquareView, EntityViewBase
from .properties import EntityViewProperties
from .audio import EntityViewAudio
from .combat import EntityViewCombat
from .events import EntityViewEvents

# 重新组合EntityView类
class EntityView(EntityViewBase, EntityViewProperties, EntityViewAudio, EntityViewCombat, EntityViewEvents):
    """完整的实体视图类，组合了所有功能模块"""
    pass

# 导出主要类和函数
from .base import flatten, direction_to_msgpart, compute_title, _order_title_msg

__all__ = [
    'SquareView', 'EntityView', 'flatten', 'direction_to_msgpart', 
    'compute_title', '_order_title_msg'
]