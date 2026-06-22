"""玩家基础模块 - 使用拆分的模块结构

将原来的大文件拆分为6个模块：
- base.py: 基础属性和初始化  
- perception.py: 视野、感知、记忆系统
- resources.py: 资源和单位管理
- triggers.py: 触发器和游戏事件
- combat.py: 战斗和威胁评估
- commands.py: 命令处理
"""

# 从拆分的模块导入所有功能
from .worldplayerbase.base import Player as BasePlayer, Objective, A, VERY_SLOW
from .worldplayerbase.perception import PerceptionMixin
from .worldplayerbase.resources import ResourcesMixin
from .worldplayerbase.triggers import TriggersMixin
from .worldplayerbase.combat import CombatMixin
from .worldplayerbase.commands import CommandsMixin


class Player(BasePlayer, PerceptionMixin, ResourcesMixin, TriggersMixin, CombatMixin, CommandsMixin):
    """完整的玩家类，组合了所有功能模块"""
    
    def __init__(self, world, client):
        # 初始化空间索引
        self._buckets = {}
        super().__init__(world, client)

    def slow_update(self):
        """慢速更新 - 调用各模块功能"""
        # 资源相关
        if not hasattr(self, '_resources_manager'):
            from .worldplayerbase.resources import ResourcesManager
            self._resources_manager = ResourcesManager(self)
        self._resources_manager.free_project_resources_if_no_worker_on_project()
        
        # 触发器相关
        self.run_triggers()

    def update(self):
        """主更新方法 - 调用各模块的更新功能"""
        # 资源和单位管理更新
        self._update_actual_speed()
        self._update_storage_bonus()
        self._update_allied_upgrades()
        
        # 感知和记忆更新
        self._update_perception_and_memory()
        
        # 战斗相关更新
        self._update_menace()
        self._update_enemy_menace_and_presence_and_corpses()
        
        # AI逻辑
        self.play()
        
        # 其他更新
        self._update_drowning()
        self._update_counterattacks()


# 导出主要类和常量  
__all__ = ['Player', 'Objective', 'A', 'VERY_SLOW']