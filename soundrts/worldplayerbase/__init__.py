"""
玩家基础模块

这个模块包含游戏中玩家的核心功能，拆分为以下子模块：
- base: 玩家基础类和初始化
- perception: 视野和感知系统  
- resources: 资源和单位管理
- triggers: 触发器和游戏事件
- combat: 战斗和AI系统
- commands: 命令处理和控制
"""

from .base import Player as BasePlayer, Objective, A, VERY_SLOW
from .perception import PerceptionMixin
from .resources import ResourcesMixin
from .triggers import TriggersMixin
from .combat import CombatMixin
from .commands import CommandsMixin


class Player(BasePlayer, PerceptionMixin, ResourcesMixin, TriggersMixin, CombatMixin, CommandsMixin):
    """完整的玩家类，组合了所有功能模块"""
    
    def __init__(self, world, client):
        # 初始化空间索引
        self._buckets = {}
        super().__init__(world, client)

    def slow_update(self):
        """慢速更新 - 调用各模块功能"""
        # 纯旁观者不参与任何游戏逻辑：无单位、无触发器，且绝不能消耗 world.random，
        # 否则会让世界相对真实对局错位、全程不同步。直接跳过。
        if getattr(self, '_is_pure_spectator', False):
            return
        # 资源相关
        if not hasattr(self, '_resources_manager'):
            from .resources import ResourcesManager
            self._resources_manager = ResourcesManager(self)
        self._resources_manager.free_project_resources_if_no_worker_on_project()
        
        # 触发器相关
        self.run_triggers()

    def update(self):
        """主更新方法 - 调用各模块的更新功能"""
        # 纯旁观者：只更新感知（配合 cheatmode 揭示全图，供渲染），不跑 AI /
        # 威胁评估 / 反击等逻辑。这些逻辑可能消耗 world.random，会破坏与真实
        # 对局的确定性同步。感知更新本身不消耗随机数，可安全执行。
        if getattr(self, '_is_pure_spectator', False):
            self._update_perception_and_memory()
            return
        # 资源和单位管理更新
        self._update_actual_speed()
        self._update_storage_bonus()
        self._update_allied_upgrades()
        
        # 每帧：感知与记忆 + 威胁评估与AI决策（保持确定性，避免行为迟钝）
        self._update_perception_and_memory()
        self._update_menace()
        self._update_enemy_menace_and_presence_and_corpses()
        self.play()
        
        # 其他更新
        self._update_drowning()
        self._update_counterattacks()


# 导出主要类和常量
__all__ = ['Player', 'Objective', 'A', 'VERY_SLOW']
