from soundrts.worldentity import Entity
from .targeting import TargetingMixin
from .damage import DamageMixin
from .splash import SplashMixin
from .hit_miss import HitMissMixin
from .attack_action import AttackActionMixin

class CreatureAttack(Entity, TargetingMixin, DamageMixin, SplashMixin, HitMissMixin, AttackActionMixin):
    """
    攻击系统的主要入口类
    通过混入不同的功能模块，实现完整的攻击系统
    """
    pass 