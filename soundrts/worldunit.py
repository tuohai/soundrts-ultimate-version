"""
Base module for organizing all world-related classes and functionality.
This module serves as the main entry point for importing world-related classes.
"""

from .worldunit.world_public_method import ground_or_air, has_target_type
from .worldunit.worldcreature import Creature, Building, BuildingSite
from .worldunit.worldworker import Worker
from .worldunit.worldsoldier import Soldier
from .worldunit.worldeffect import Effect
from .worldunit.worldbase import Unit

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
]