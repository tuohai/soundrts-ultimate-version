"""技能战斗属性：合并施法者与 skill 定义上的战斗参数，供 harm/burst 走完整战斗管线。"""


# 技能 rules 可声明、并在释放时与施法者合并的战斗属性（与单位战斗系统对齐）
SKILL_COMBAT_ATTRS = (
    "mdg",
    "rdg",
    "mdg_vs",
    "rdg_vs",
    "mdf",
    "rdf",
    "mdf_vs",
    "rdf_vs",
    "minimal_damage",
    "forced_damage",
    "mdg_minimal_damage",
    "rdg_minimal_damage",
    "mdg_crit",
    "rdg_crit",
    "mdg_crit_rate",
    "rdg_crit_rate",
    "mdg_crit_vs",
    "rdg_crit_vs",
    "mdg_crit_rate_vs",
    "rdg_crit_rate_vs",
    "mdg_piercing",
    "rdg_piercing",
    "mdg_piercing_rate",
    "rdg_piercing_rate",
    "mdg_piercing_vs",
    "rdg_piercing_vs",
    "mdg_piercing_rate_vs",
    "rdg_piercing_rate_vs",
    "mdf_crit_rate",
    "rdf_crit_rate",
    "mdf_piercing",
    "rdf_piercing",
    "mdg_range",
    "rdg_range",
    "mdg_minimal_range",
    "rdg_minimal_range",
    "mdg_range_vs",
    "rdg_range_vs",
    "mdg_minimal_range_vs",
    "rdg_minimal_range_vs",
    "mdg_splash",
    "rdg_splash",
    "mdg_radius",
    "rdg_radius",
    "mdg_splash_vs",
    "rdg_splash_vs",
    "mdg_radius_vs",
    "rdg_radius_vs",
    "mdg_splash_decay_min",
    "rdg_splash_decay_min",
    "mdg_splash_decay_min_vs",
    "rdg_splash_decay_min_vs",
    "mdg_explode",
    "rdg_explode",
    "mdg_explode_vs",
    "rdg_explode_vs",
    "exp_dgf",
    "exp_dgf_vs",
    "debuffs",
)


def merge_combat_stat(skill_val, caster_val):
    """技能上非零/非空的战斗属性覆盖施法者；字典类合并。"""
    if isinstance(skill_val, dict):
        if not skill_val:
            return caster_val if isinstance(caster_val, dict) else {}
        base = dict(caster_val) if isinstance(caster_val, dict) else {}
        base.update(skill_val)
        return base
    if isinstance(skill_val, (list, tuple, set)):
        if skill_val:
            return skill_val
        return caster_val
    if skill_val:
        return skill_val
    return caster_val


def resolve_combat_attacker(attacker):
    """SkillCombatProxy 为单次施法临时对象，不应进入感知/记忆/反击链。"""
    if getattr(attacker, "_is_skill_combat_proxy", False):
        return attacker._caster
    return attacker


class SkillCombatProxy:
    """单次技能释放用的虚拟攻击者：属性=skill 覆盖 caster，行为委托给 combat mixin。"""
    _is_skill_combat_proxy = True

    def __init__(self, caster, skill_cls):
        self._caster = caster
        self.player = getattr(caster, "player", None)
        self.world = getattr(caster, "world", None)
        self.id = getattr(caster, "id", None)
        self.type_name = getattr(caster, "type_name", "")
        self.expanded_is_a = getattr(caster, "expanded_is_a", set())
        self.x = getattr(caster, "x", 0)
        self.y = getattr(caster, "y", 0)
        self.o = getattr(caster, "o", 0)
        self.place = getattr(caster, "place", None)
        self.menace = getattr(caster, "menace", 0)
        self.collision = getattr(caster, "collision", 1)
        self.time_limit = getattr(caster, "time_limit", None)
        self.harm_level = getattr(caster, "harm_level", 0)
        self.is_vulnerable = getattr(caster, "is_vulnerable", True)
        self.is_a_unit = getattr(caster, "is_a_unit", True)
        self.is_a_building = getattr(caster, "is_a_building", False)
        self.is_invisible = getattr(caster, "is_invisible", False)
        self.is_cloakable = getattr(caster, "is_cloakable", False)
        self.is_cloaked = getattr(caster, "is_cloaked", False)
        self.is_a_detector = getattr(caster, "is_a_detector", False)
        self.detection_range = getattr(caster, "detection_range", 0)
        self.sight_range = getattr(caster, "sight_range", 0)
        self.is_a_cloaker = getattr(caster, "is_a_cloaker", False)
        self.cloaking_range = getattr(caster, "cloaking_range", 0)
        self.airground_type = getattr(caster, "airground_type", "ground")
        self.is_memory = getattr(caster, "is_memory", False)
        self.is_inside = getattr(caster, "is_inside", False)
        for attr in SKILL_COMBAT_ATTRS:
            skill_val = getattr(skill_cls, attr, 0)
            caster_val = getattr(caster, attr, 0 if attr != "debuffs" else [])
            setattr(self, attr, merge_combat_stat(skill_val, caster_val))

    def __getattr__(self, name):
        try:
            caster = object.__getattribute__(self, "_caster")
        except AttributeError:
            raise AttributeError(name) from None
        return getattr(caster, name)

    def is_an_enemy(self, other):
        return self._caster.is_an_enemy(other)

    def notify(self, *args, **kwargs):
        notify = getattr(self._caster, "notify", None)
        if notify:
            notify(*args, **kwargs)

    def _get_attack_damage_vs(self, target, attack_type):
        from .combat.damage_calculation import DamageCalculationMixin

        is_melee = attack_type == "mdg"
        if is_melee:
            return DamageCalculationMixin._get_melee_damage_vs(self, target), True
        return DamageCalculationMixin._get_ranged_damage_vs(self, target), False

    def apply_hit(self, target, attack_type, notify=True):
        """对目标造成一次技能伤害，并在配置了溅射时触发 splash_aim。"""
        if target is None or not getattr(target, "is_vulnerable", False):
            return False
        if target.player is None or target.hp <= 0:
            return False
        damage, is_melee = self._get_attack_damage_vs(target, attack_type)
        if damage <= 0:
            return False
        target.receive_hit(damage, self, notify=notify, is_melee=is_melee)
        if is_melee:
            splash = getattr(self, "mdg_splash", 0)
            radius = getattr(self, "mdg_radius", 0)
        else:
            splash = getattr(self, "rdg_splash", 0)
            radius = getattr(self, "rdg_radius", 0)
        if splash > 0 and radius > 0 and getattr(target, "place", None) is not None:
            from .combat.splash import SplashMixin

            SplashMixin.splash_aim(self, target, is_melee=is_melee)
        return True

    def attack_range(self, attack_type):
        if attack_type == "rdg":
            return getattr(self, "rdg_range", 0)
        return getattr(self, "mdg_range", 0)

    def in_skill_range(self, target, attack_type):
        """目标是否在技能声明的 mdg_range / rdg_range 内（0 表示不限）。"""
        max_range = self.attack_range(attack_type)
        if max_range <= 0:
            return True
        from .lib.nofloat import int_distance

        collision = getattr(self, "radius", 0) + getattr(target, "radius", 0)
        return int_distance(self.x, self.y, target.x, target.y) <= max_range + collision
