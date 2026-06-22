"""
SoundRTS 客户端游戏接口 - 兼容性重定向文件

这个文件已经被重构为模块化结构。原来的单一文件已经拆分为8个子模块：
- game_interface_base: 基础接口类和初始化
- game_input_handler: 输入处理模块  
- game_unit_control: 单位控制模块
- game_navigation: 地图导航模块
- game_orders: 指令管理模块
- game_display: 显示和渲染模块
- game_audio: 音频和语音模块
- game_resources: 资源和状态管理模块

为了保持向后兼容性，这个文件会重定向到新的模块化结构。
"""

# 重定向到新的模块化结构
from .clientgame import GameInterface, direction_to_msgpart, load_palette
from . import msgparts as mp

# 保持一些常量的定义以确保兼容性
PROFILE = False

# minimal interval (in seconds) between 2 sounds
ALERT_LIMIT = 0.5

# don't play events after this limit (in seconds)
EVENT_LIMIT = 3

BEEP_SOUND = mp.BEEP[0]
POSITIONAL_BEEP_SOUND = mp.POSITIONAL_BEEP[0]

# 导出主要内容
__all__ = ['GameInterface', 'direction_to_msgpart', 'load_palette', 'PROFILE', 'ALERT_LIMIT', 'EVENT_LIMIT', 'BEEP_SOUND', 'POSITIONAL_BEEP_SOUND']