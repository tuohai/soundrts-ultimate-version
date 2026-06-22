"""
属性界面模块 - 主入口文件
原来的大文件已经被拆分成15个小模块存放在attributes目录中
"""

# 导入新的模块化实现
from .attributes import AttributesInterface

# 为了保持向后兼容性，直接在这里暴露主类
__all__ = ['AttributesInterface']