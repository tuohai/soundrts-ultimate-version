# 重新导入拆分后的模块
from .clientgameentity import SquareView, EntityView, flatten, direction_to_msgpart, compute_title, _order_title_msg

# 为了保持向后兼容性，重新导出所有类和函数
__all__ = ['SquareView', 'EntityView', 'flatten', 'direction_to_msgpart', 'compute_title', '_order_title_msg']