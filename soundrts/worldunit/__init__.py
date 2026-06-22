"""
worldunit 包 - 包含所有世界单位相关的类和功能的具体实现
"""

# 从各个子模块导入主要类，供包内部使用
from .worldbase import Unit
from .worldcreature import Creature, Building, BuildingSite
from .worldworker import Worker
from .worldsoldier import Soldier
from .worldeffect import Effect
from .world_public_method import ground_or_air, has_target_type, matches_attack_targets, matches_heal_targets

# 确保包内部可以使用这些类
__all__ = [
    'Unit',
    'Creature', 
    'Building',
    'BuildingSite',
    'Worker',
    'Soldier', 
    'Effect',
    'ground_or_air',
    'has_target_type',
    'matches_attack_targets',
    'matches_heal_targets',
]