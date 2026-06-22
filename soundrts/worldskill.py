import re

from soundrts.lib.nofloat import PRECISION, to_int

from .definitions import MAX_NB_OF_RESOURCE_TYPES, rules
from .worldunit.world_attributes import CreatureAttributes


class Skill(CreatureAttributes):  # or UnitOption or UnitMenuItem or ActiveSkill or SpecialSkill
    global_count_limit = 0  # ugly but necessary; used by ComplexOrder.is_allowed()
    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES  # required by the user interface
    count_limit = 0  # ugly but necessary; used by ComplexOrder.is_allowed()
    time_cost = 0  # doesn't seem to be required
    ready = 0
    cooldown = 0
    requirements = ()
    population_cost = 0
    mana_cost = 0
    effect = None
    effect_target = ["self"]
    effect_range = 6 * PRECISION  # "square"
    effect_radius = 6 * PRECISION
    universal_notification = False
    summon_requires_build_field = ""
    summon_requires_marked_field = 0
    is_a = ()  # 添加is_a支持
    expanded_is_a = set()  # 添加expanded_is_a支持
    can_use = ()  # 添加can_use支持，表示技能可以使用的科技
    can_use_tech = ()  # 添加can_use_tech支持，表示技能可以使用的升级技术
    can_use_skill = ()  # 添加can_use_skill支持，表示技能可以使用的技能
    active_trigger_rate = 100
    passive_trigger_rate = 100
    auto_trigger = 0  # 1=学会后可在战斗中自动触发（can_use_skill）
    manual_use = 1  # 1=学会后可手动释放（can_use_skill）
    trigger_timing = "on_hit"  # on_hit | on_attack | on_attack_replace | on_damaged
    mdg_trigger_rate = 0
    rdg_trigger_rate = 0
    hp_threshold = 0
    trigger_condition = ""

    # 战斗属性默认值（与单位 rules 语法相同；非零值在释放时覆盖施法者）
    mdg = 0
    rdg = 0
    mdg_vs = {}
    rdg_vs = {}
    mdf = 0
    rdf = 0
    mdf_vs = {}
    rdf_vs = {}
    minimal_damage = 0
    forced_damage = 0
    mdg_cd = 0
    rdg_cd = 0
    mdg_cd_vs = {}
    rdg_cd_vs = {}
    mdg_ready = True
    rdg_ready = True
    mdg_ready_vs = {}
    rdg_ready_vs = {}
    mdg_range = 0
    rdg_range = 0
    mdg_range_vs = {}
    rdg_range_vs = {}
    mdg_minimal_range = 0
    rdg_minimal_range = 0
    mdg_minimal_range_vs = {}
    rdg_minimal_range_vs = {}
    speed = 0
    speed_vs = {}
    mdg_cover = 0
    rdg_cover = 0
    mdg_cover_vs = {}
    rdg_cover_vs = {}
    mdg_dodge = 0
    rdg_dodge = 0
    mdg_dodge_vs = {}
    rdg_dodge_vs = {}
    mdg_splash = 0
    rdg_splash = 0
    mdg_splash_vs = {}
    rdg_splash_vs = {}
    mdg_radius = 0
    rdg_radius = 0
    mdg_radius_vs = {}
    rdg_radius_vs = {}
    mdg_splash_decay_min = 0
    rdg_splash_decay_min = 0
    mdg_splash_decay_min_vs = {}
    rdg_splash_decay_min_vs = {}
    mdg_crit = 0
    rdg_crit = 0
    mdg_crit_vs = {}
    rdg_crit_vs = {}
    mdg_crit_rate = 0
    rdg_crit_rate = 0
    mdg_crit_rate_vs = {}
    rdg_crit_rate_vs = {}
    mdg_piercing = 0
    rdg_piercing = 0
    mdg_piercing_vs = {}
    rdg_piercing_vs = {}
    mdg_piercing_rate = 0
    rdg_piercing_rate = 0
    mdg_piercing_rate_vs = {}
    rdg_piercing_rate_vs = {}
    mdg_minimal_damage = 0
    rdg_minimal_damage = 0
    mdf_crit_rate = 0
    rdf_crit_rate = 0
    mdf_crit_rate_vs = {}
    rdf_crit_rate_vs = {}
    mdf_piercing = 0
    rdf_piercing = 0
    mdf_piercing_vs = {}
    rdf_piercing_vs = {}
    mdg_explode = 0
    rdg_explode = 0
    mdg_explode_vs = {}
    rdg_explode_vs = {}
    exp_dgf = 0
    exp_dgf_vs = {}
    charge_mdg = 0
    charge_rdg = 0
    charge_mdg_vs = {}
    charge_rdg_vs = {}
    op_charge_mdg = 0
    op_charge_rdg = 0
    op_charge_mdg_vs = {}
    op_charge_rdg_vs = {}
    charge_mdg_splash = 0
    charge_rdg_splash = 0
    charge_mdg_splash_vs = {}
    charge_rdg_splash_vs = {}
    charge_mdg_radius = 0
    charge_rdg_radius = 0
    charge_mdg_radius_vs = {}
    charge_rdg_radius_vs = {}
    charge_mdg_splash_decay_min = 0
    charge_rdg_splash_decay_min = 0
    charge_mdg_splash_decay_min_vs = {}
    charge_rdg_splash_decay_min_vs = {}
    debuffs = ()

    cls = object  # probably not used

    @classmethod
    def interpret(cls, d):
        """解析 skill 上的战斗属性（mdg/rdg/splash/range 等，与单位规则语法相同）。"""
        super().interpret(d)
        for k in (
            "active_trigger_rate",
            "passive_trigger_rate",
            "auto_trigger",
            "manual_use",
            "mdg_trigger_rate",
            "rdg_trigger_rate",
            "hp_threshold",
        ):
            if k in d:
                try:
                    value = d[k][0] if isinstance(d[k], list) else d[k]
                    d[k] = max(0, min(100, int(value)))
                except (TypeError, ValueError):
                    d[k] = getattr(cls, k)
        if "trigger_timing" in d:
            value = d["trigger_timing"]
            if isinstance(value, list):
                value = value[0] if value else "on_hit"
            d["trigger_timing"] = str(value)
        if "trigger_condition" in d and isinstance(d["trigger_condition"], list):
            d["trigger_condition"] = " ".join(str(x) for x in d["trigger_condition"])

    def __init__(self):
        # 初始化expanded_is_a
        self.expanded_is_a = set()
        if hasattr(self, 'is_a'):
            self._expand_is_a(self.is_a)
    
    def _expand_is_a(self, is_a_list):
        """展开并记录所有继承关系"""
        if not is_a_list:
            return
            
        for base_type in is_a_list:
            if base_type not in self.expanded_is_a:
                self.expanded_is_a.add(base_type)
                # 递归处理基类的继承
                base_class = rules.get(base_type)
                if base_class and hasattr(base_class, 'is_a'):
                    self._expand_is_a(base_class.is_a)

    # 新增方法来检查释放条件
    @classmethod
    def check_cast_requirements(cls, unit):
        # 检查法力消耗
        if cls.mana_cost and unit.mana < cls.mana_cost:
            return False, "not_enough_mana"
            
        # 检查资源消耗
        if any(cls.cost):
            result = unit.player.check_if_enough_resources(cls.cost)
            if result is not None:
                return False, result
                
        return True, None

    @classmethod
    def is_cast_necessary(cls, caster, target=None):
        """
        检查技能是否需要释放
        子类可以重写此方法来实现自定义逻辑
        
        Args:
            caster: 释放技能的单位
            target: 技能目标（如果有）
            
        Returns:
            bool: True表示需要释放，False表示不需要释放
        """
        # 默认实现：总是需要释放
        return True

    @classmethod  
    def execute_skill(cls, caster, target=None, world=None):
        """
        执行技能效果
        子类可以重写此方法来实现自定义技能逻辑
        
        Args:
            caster: 释放技能的单位
            target: 技能目标（如果有）
            world: 游戏世界对象
            
        Returns:
            bool: True表示执行成功，False表示执行失败
        """
        # 默认实现：根据effect属性执行对应的效果
        if not hasattr(cls, 'effect') or not cls.effect:
            return False
            
        effect_type = cls.effect[0] if isinstance(cls.effect, (list, tuple)) else cls.effect
        
        # 尝试调用对应的效果处理方法
        method_name = f"_execute_{effect_type}"
        if hasattr(cls, method_name):
            try:
                return bool(getattr(cls, method_name)(caster, target, world))
            except Exception as e:
                from .lib.log import warning
                warning(f"技能 {cls.type_name} 执行失败: {e}")
                return False
        
        # 如果没有找到对应的方法，尝试通用处理
        return cls._execute_generic_effect(caster, target, world)

    @classmethod
    def _execute_generic_effect(cls, caster, target, world):
        """
        通用效果处理
        处理一些常见的效果类型
        """
        if not hasattr(cls, 'effect') or not cls.effect:
            return False
            
        effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        effect_type = effect_parts[0]
        
        # 处理buff效果 (对友方或自己施加正面状态)
        if effect_type == "buffs" and len(effect_parts) > 1:
            if target and hasattr(target, "add_buff"):
                for buff_name in effect_parts[1:]:
                    target.add_buff(buff_name, caster)
                return True
                
        # 处理debuff效果 (对敌人施加负面状态)
        elif effect_type == "debuffs" and len(effect_parts) > 1:
            if target and hasattr(target, "add_buff") and caster.is_an_enemy(target):
                for debuff_name in effect_parts[1:]:
                    target.add_buff(debuff_name, caster)
                return True
                
        # 处理伤害效果  
        elif effect_type == "harm":
            if target and target.place:
                from .worldunit import Effect
                effect_class = world.unit_class(cls.type_name)
                if effect_class:
                    e = Effect(caster.player, target.place, target.x, target.y)
                    # 复制效果属性
                    for attr in ['harm_level', 'harm_target_type', 'decay']:
                        if hasattr(effect_class, attr):
                            setattr(e, attr, getattr(effect_class, attr))
                    return True
                    
        # 处理战场效果部署（class effect）
        elif effect_type == "deploy" and len(effect_parts) >= 3:
            return cls._execute_deploy(caster, target, world, effect_parts)

        # 处理召唤效果
        elif effect_type == "summon" and len(effect_parts) >= 3:
            ok, reason = cls.validate_summon_target(caster, target)
            if not ok:
                return False
            return cls._execute_summon(caster, target, world, effect_parts)
                
        return False

    @staticmethod
    def parse_deploy_args(effect_args):
        """解析 deploy 参数：duration [count] effect_type。"""
        if len(effect_args) < 2:
            return None
        duration = to_int(str(effect_args[0]))
        i = 1
        nb = 1
        if (
            i < len(effect_args)
            and re.match(r"^[0-9]+$", str(effect_args[i]))
            and i + 1 < len(effect_args)
            and not re.match(r"^[0-9]+$", str(effect_args[i + 1]))
        ):
            nb = int(effect_args[i])
            i += 1
        effect_type = effect_args[i]
        return duration, nb, effect_type

    @classmethod
    def _get_deploy_effect_class(cls, type_name):
        from .worldunit import Effect

        effect_cls = rules.unit_class(type_name)
        if effect_cls is None:
            return None
        if getattr(effect_cls, "cls", None) is Effect:
            return effect_cls
        if rules.get(type_name, "class") == ["effect"]:
            return effect_cls
        return None

    @classmethod
    def validate_summon_target(cls, caster, target):
        """召唤类技能：检查目标格是否满足建造场要求。"""
        field = getattr(cls, "summon_requires_build_field", "") or ""
        if not field or not field.isalpha():
            return True, None
        if target is None or caster is None:
            return False, "cannot_build_here"
        from .world_build_rules import (
            _square_for_build_target,
            has_build_field_on_square,
            has_marked_build_field_on_square,
        )

        world = getattr(caster, "world", None)
        place = target if hasattr(target, "neighbors") else getattr(target, "place", None)
        x = getattr(target, "x", 0)
        y = getattr(target, "y", 0)
        square = _square_for_build_target(world, place, x, y)
        if square is None:
            return False, "cannot_build_here"
        player = getattr(caster, "player", None)
        if getattr(cls, "summon_requires_marked_field", 0):
            ok = has_marked_build_field_on_square(world, square, player, field)
        else:
            ok = has_build_field_on_square(world, square, player, field)
        if not ok:
            return False, f"missing_build_field.{field}"
        return True, None

    @classmethod
    def _execute_deploy(cls, caster, target, world, effect_parts=None):
        if target is None:
            return False
        if effect_parts is None:
            effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        if len(effect_parts) < 3:
            return False
        ok, _reason = cls.validate_summon_target(caster, target)
        if not ok:
            return False
        parsed = cls.parse_deploy_args(effect_parts[1:])
        if parsed is None:
            return False
        duration, nb, effect_type = parsed
        if cls._get_deploy_effect_class(effect_type) is None:
            from .lib.log import warning

            warning(
                "deploy %s: %s is not class effect (use effect summon for units)",
                cls.type_name,
                effect_type,
            )
            return False
        unit_types = [str(nb), effect_type] if nb != 1 else [effect_type]
        caster.player.lang_add_units(
            unit_types,
            target=target,
            decay=duration,
            notify=False,
        )
        return True

    @classmethod
    def _execute_summon(cls, caster, target, world, effect_parts=None):
        if target is None:
            return False
        if effect_parts is None:
            effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        if len(effect_parts) < 3:
            return False
        ok, _reason = cls.validate_summon_target(caster, target)
        if not ok:
            return False
        from .lib.nofloat import to_int

        decay_time = to_int(effect_parts[1]) if len(effect_parts) > 1 else 0
        unit_types = effect_parts[2:]
        caster.player.lang_add_units(
            unit_types,
            target=target,
            decay=decay_time,
            notify=False,
        )
        return True

    # 特定技能的释放必要性检查方法
    @classmethod
    def _is_teleportation_necessary(cls, caster, target):
        """检查传送技能是否需要释放"""
        units = caster.world.get_objects(
            caster.x, caster.y, cls.effect_radius,
            filter=lambda x: x.player is caster.player and getattr(x, 'is_teleportable', True)
        )
        
        types = {u.airground_type for u in units}
        if not hasattr(target, "can_receive"):
            target = target.place
        if target is caster.place:
            return False
        elif not [t for t in types if target.can_receive(t)]:
            return False  # 会被标记为impossible
        return True

    @classmethod
    def _is_recall_necessary(cls, caster, target):
        """检查召回技能是否需要释放"""
        units = caster.world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: x.player is caster.player and getattr(x, 'is_teleportable', True)
        )
        if not units:
            return False
        types = {u.airground_type for u in units}
        if target is caster.place:
            return False
        elif not [t for t in types if caster.place.can_receive(t)]:
            return False
        return True

    @classmethod
    def _is_conversion_necessary(cls, caster, target):
        """检查转换技能是否需要释放"""
        # 特殊检查：不能转换memory单位
        if target and getattr(target, 'is_memory', False):
            return False
        return target and caster.is_an_enemy(target)  # 只对敌人使用

    @classmethod 
    def _is_buffs_necessary(cls, caster, target):
        """检查buff技能是否需要释放"""
        return target and hasattr(target, "add_buff")

    @classmethod
    def _is_debuffs_necessary(cls, caster, target):
        """检查debuff技能是否需要释放"""
        return target and hasattr(target, "add_buff") and caster.is_an_enemy(target)

    @classmethod
    def _is_summon_necessary(cls, caster, target):
        """检查召唤技能是否需要释放"""
        ok, _reason = cls.validate_summon_target(caster, target)
        return ok

    @classmethod
    def _is_deploy_necessary(cls, caster, target):
        """检查战场效果部署技能是否需要释放"""
        ok, _reason = cls.validate_summon_target(caster, target)
        return ok

    @classmethod
    def _is_raise_dead_necessary(cls, caster, target):
        """检查亡灵复活技能是否需要释放"""
        from .worldresource import Corpse
        corpses = caster.world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: isinstance(x, Corpse)
        )
        return len(corpses) > 0

    @classmethod
    def _is_resurrection_necessary(cls, caster, target):
        """检查复活技能是否需要释放"""
        from .worldresource import Corpse
        corpses = caster.world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: isinstance(x, Corpse) and x.unit.player is caster.player
        )
        return len(corpses) > 0

    @classmethod
    def _is_harm_necessary(cls, caster, target):
        """检查伤害技能是否需要释放"""
        return True  # 伤害技能总是可以释放

    # 重写is_cast_necessary以支持特定技能的检查
    @classmethod
    def is_cast_necessary(cls, caster, target=None):
        """
        检查技能是否需要释放
        """
        if not hasattr(cls, 'effect') or not cls.effect:
            return True
            
        effect_type = cls.effect[0] if isinstance(cls.effect, (list, tuple)) else cls.effect
        
        # 尝试调用特定技能的检查方法
        method_name = f"_is_{effect_type}_necessary"
        if hasattr(cls, method_name):
            try:
                return getattr(cls, method_name)(caster, target)
            except Exception:
                return True  # 出错时默认允许释放
                
        # 默认总是需要释放
        return True

    @classmethod
    def _execute_teleportation(cls, caster, target, world):
        """传送技能处理"""
        # 获取传送范围内的单位
        units = world.get_objects(
            caster.x, caster.y, cls.effect_radius,
            filter=lambda x: x.player is caster.player and getattr(x, 'is_teleportable', True)
        )
        
        if not hasattr(target, "can_receive"):
            target = target.place
            
        for u in units:
            if target.can_receive(u.airground_type):
                u.move_to(target, None, None)
        return True

    @classmethod
    def _execute_recall(cls, caster, target, world):
        """召回技能处理"""
        units = world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: x.player is caster.player and getattr(x, 'is_teleportable', True)
        )
        
        nearest_water = caster.nearest_water()
        for u in units:
            place = caster.place
            if u.airground_type == "water" and not place.is_water:
                place = nearest_water
                if place is None:
                    continue
            if place.can_receive(u.airground_type):
                u.move_to(place, None, None)
        return True

    @classmethod
    def _execute_conversion(cls, caster, target, world):
        """转换技能处理"""
        if target and hasattr(target, 'set_player') and caster.is_an_enemy(target):
            target.set_player(caster.player)
            return True
        return False

    @classmethod
    def _execute_raise_dead(cls, caster, target, world):
        """亡灵复活技能处理"""
        from .worldresource import Corpse
        from soundrts.lib.nofloat import square_of_distance
        
        corpses = world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: isinstance(x, Corpse)
        )
        
        if corpses and len(cls.effect) >= 3:
            from .lib.nofloat import to_int
            corpses = sorted(corpses, key=lambda o: square_of_distance(target.x, target.y, o.x, o.y))
            # 使用to_int将秒转换为毫秒
            decay_time = to_int(cls.effect[1]) if len(cls.effect) > 1 else 0
            unit_types = cls.effect[2:]
            caster.player.lang_add_units(
                unit_types,
                decay=decay_time,
                from_corpse=True,
                corpses=corpses,
                notify=False,
            )
            return True
        return False

    @classmethod
    def _execute_resurrection(cls, caster, target, world):
        """复活技能处理"""
        from .worldresource import Corpse
        from soundrts.lib.nofloat import square_of_distance
        
        corpses = world.get_objects(
            target.x, target.y, cls.effect_radius,
            filter=lambda x: isinstance(x, Corpse) and x.unit.player is caster.player
        )
        
        if corpses and len(cls.effect) >= 2:
            corpses = sorted(corpses, key=lambda o: square_of_distance(target.x, target.y, o.x, o.y))
            resurrection_count = int(cls.effect[1])
            
            for _ in range(resurrection_count):
                if corpses:
                    c = corpses.pop(0)
                    u = c.unit
                    if not caster.player.check_count_limit(u.type_name):
                        continue
                    u.player = None
                    u.place = None
                    u.id = None
                    u.hp = u.hp_max // 3
                    u.set_player(caster.player)
                    u.move_to(c.place, c.x, c.y)
                    if u.decay:
                        u.time_limit = u.world.time + u.decay
                    c.delete()
            return True
        return False

    # --- 武侠/通用技能 effect：burst / harm_area / harm_target / push ---

    @staticmethod
    def _skill_target_xy(target):
        """从 ask 目标（单位或格子）取得坐标。"""
        if target is None:
            return None, None
        x = getattr(target, "x", None)
        y = getattr(target, "y", None)
        if x is not None and y is not None:
            return int(x), int(y)
        place = target if hasattr(target, "neighbors") else getattr(target, "place", None)
        if place is not None:
            return int(getattr(place, "x", 0)), int(getattr(place, "y", 0))
        return None, None

    @staticmethod
    def _skill_treaty_blocks_harm(caster, victim):
        try:
            world = caster.world
            if getattr(world, "treaty_until_time", 0) > 0 and world.time < world.treaty_until_time:
                if caster.player and victim.player:
                    if victim.player.player_is_an_enemy(caster.player):
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def _skill_effect_range_met(skill_cls, caster, target):
        max_range = getattr(skill_cls, "effect_range", 0)
        if max_range <= 0:
            return True
        x, y = Skill._skill_target_xy(target)
        if x is None:
            return False
        from .lib.nofloat import int_distance

        collision = 0
        if hasattr(caster, "radius") and hasattr(target, "radius"):
            collision = caster.radius + target.radius
        return int_distance(caster.x, caster.y, x, y) <= max_range + collision

    @staticmethod
    def _skill_can_harm(caster, skill_cls, victim):
        from .worldunit.world_public_method import skill_can_harm

        return skill_can_harm(caster, skill_cls, victim)

    @staticmethod
    def _skill_combat_harm(caster, victim, attack_type, skill_cls):
        """通过 receive_hit 造成伤害（走护甲/暴击/溅射等战斗管线）。"""
        from .skill_combat import SkillCombatProxy

        if not Skill._skill_can_harm(caster, skill_cls, victim):
            return False
        if Skill._skill_treaty_blocks_harm(caster, victim):
            return False
        proxy = SkillCombatProxy(caster, skill_cls)
        if not proxy.in_skill_range(victim, attack_type):
            return False
        return proxy.apply_hit(victim, attack_type, notify=True)

    @staticmethod
    def parse_harm_area_args(effect_parts, skill_cls=None):
        """解析 harm_area：固定 harm_area N R；或 harm_area mdg|rdg [R]（R 省略时用 effect_radius）。"""
        if len(effect_parts) < 2 or effect_parts[0] != "harm_area":
            return None
        if str(effect_parts[1]) in ("mdg", "rdg"):
            attack_type = str(effect_parts[1])
            radius = None
            if len(effect_parts) >= 3:
                try:
                    radius = to_int(str(effect_parts[2]))
                except (TypeError, ValueError):
                    return None
            elif skill_cls is not None:
                radius = getattr(skill_cls, "effect_radius", 6 * PRECISION)
            else:
                return None
            return attack_type, radius
        if len(effect_parts) < 3:
            return None
        try:
            harm_level = int(effect_parts[1])
            radius = to_int(str(effect_parts[2]))
        except (TypeError, ValueError):
            return None
        return "fixed", harm_level, radius

    @staticmethod
    def parse_harm_target_args(effect_parts):
        """解析 harm_target：固定伤害 harm_target N，或 mdg/rdg harm_target mdg|rdg。"""
        if len(effect_parts) < 2 or effect_parts[0] != "harm_target":
            return None
        if str(effect_parts[1]) in ("mdg", "rdg"):
            return str(effect_parts[1]), None
        try:
            return "fixed", int(effect_parts[1])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _skill_direct_harm(caster, victim, harm_level, skill_cls=None):
        """直接扣血（绕过护甲），与 class effect 的 harm 一致。"""
        if skill_cls is not None and not Skill._skill_can_harm(caster, skill_cls, victim):
            return False
        if victim is None or not getattr(victim, "is_vulnerable", False):
            return False
        if victim.player is None or victim.hp <= 0:
            return False
        if Skill._skill_treaty_blocks_harm(caster, victim):
            return False
        hp = int(harm_level) * PRECISION
        if victim.player:
            victim.player.observe(caster)
            victim.last_attacker = caster
        victim.hp -= hp
        if victim.hp <= 0:
            victim.die(caster)
        return True

    @staticmethod
    def parse_burst_args(effect_parts):
        """解析 burst 参数：burst mdg|rdg N (interval X)|(delays A B C) (window Y)。"""
        if len(effect_parts) < 3 or effect_parts[0] != "burst":
            return None
        attack_type = str(effect_parts[1])
        if attack_type not in ("mdg", "rdg"):
            return None
        try:
            times = min(int(effect_parts[2]), 6)
        except (TypeError, ValueError):
            return None
        if times < 1:
            return None
        rest = " ".join(str(x) for x in effect_parts[3:])
        interval = 0.25
        window = None
        delays = None
        m = re.search(r"\(delays\s+([^)]+)\)", rest)
        if m:
            try:
                delays = [float(x) for x in m.group(1).split()]
            except ValueError:
                return None
            if len(delays) != times or any(x < 0 for x in delays):
                return None
            if delays != sorted(delays):
                return None
        m = re.search(r"\(interval\s+([\d.]+)\)", rest)
        if m:
            interval = float(m.group(1))
        m = re.search(r"\(window\s+([\d.]+)\)", rest)
        if m:
            window = float(m.group(1))
        if window is None:
            if delays:
                window = max(delays)
            else:
                window = (times - 1) * interval if times > 1 else 0.0
        return attack_type, times, interval, window, delays

    @classmethod
    def schedule_skill_burst(cls, caster, target, attack_type, times, interval, skill_cls, delays=None):
        """调度技能连击：支持统一 interval 或明确 delays（单位：秒）。"""
        if caster is None or target is None or times < 1:
            return
        world = getattr(caster, "world", None)
        if world is None:
            return
        from .skill_combat import SkillCombatProxy

        proxy = SkillCombatProxy(caster, skill_cls)

        if delays is None:
            scheduled_delays = [int(i * interval * 1000) for i in range(times)]
        else:
            scheduled_delays = [int(delay * 1000) for delay in delays]

        def do_hit(c=caster, t=target, at=attack_type, p=proxy, sk=skill_cls):
            if t is None or t.player is None or t.hp <= 0:
                return
            if c.player is None or c.hp <= 0:
                return
            if not Skill._skill_can_harm(c, sk, t):
                return
            if not p.in_skill_range(t, at):
                return
            p.apply_hit(t, at, notify=True)

        for delay in scheduled_delays:
            if delay <= 0:
                do_hit()
            else:
                world.schedule_after(delay, do_hit)

    @classmethod
    def _is_burst_necessary(cls, caster, target):
        return cls._skill_can_harm(caster, cls, target)

    @classmethod
    def _is_harm_target_necessary(cls, caster, target):
        return cls._skill_can_harm(caster, cls, target)

    @classmethod
    def _is_push_necessary(cls, caster, target):
        return cls._skill_can_harm(caster, cls, target)

    @classmethod
    def _is_harm_area_necessary(cls, caster, target):
        return target is not None

    @classmethod
    def _execute_burst(cls, caster, target, world):
        effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        parsed = cls.parse_burst_args(list(effect_parts))
        if parsed is None or not cls._skill_can_harm(caster, cls, target):
            return False
        attack_type, times, interval, _window, delays = parsed
        cls.schedule_skill_burst(caster, target, attack_type, times, interval, cls, delays)
        return True

    @classmethod
    def _execute_harm_area(cls, caster, target, world):
        if target is None or world is None:
            return False
        effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        parsed = cls.parse_harm_area_args(list(effect_parts), skill_cls=cls)
        if parsed is None:
            return False
        if parsed[0] in ("mdg", "rdg"):
            attack_type, radius = parsed
            from .skill_combat import SkillCombatProxy

            proxy = SkillCombatProxy(caster, cls)

            def apply_harm(u):
                if not cls._skill_can_harm(caster, cls, u):
                    return False
                if not proxy.in_skill_range(u, attack_type):
                    return False
                return proxy.apply_hit(u, attack_type, notify=True)
        else:
            _mode, harm_level, radius = parsed
            apply_harm = lambda u: cls._skill_direct_harm(caster, u, harm_level, cls)
        x, y = cls._skill_target_xy(target)
        if x is None:
            return False
        units = world.get_objects2(
            x,
            y,
            radius,
            filter=lambda u: cls._skill_can_harm(caster, cls, u),
            skip_cache=True,
        )
        seen = set()
        hit_any = False
        for u in units:
            uid = id(u)
            if uid in seen:
                continue
            seen.add(uid)
            if apply_harm(u):
                hit_any = True
        return hit_any

    @classmethod
    def _execute_harm_target(cls, caster, target, world):
        if not cls._skill_can_harm(caster, cls, target):
            return False
        effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        parsed = cls.parse_harm_target_args(list(effect_parts))
        if parsed is None:
            return False
        if parsed[0] in ("mdg", "rdg"):
            return cls._skill_combat_harm(caster, target, parsed[0], cls)
        _mode, harm_level = parsed
        return cls._skill_direct_harm(caster, target, harm_level)

    @classmethod
    def _execute_push(cls, caster, target, world):
        if not cls._skill_can_harm(caster, cls, target):
            return False
        if not cls._skill_effect_range_met(cls, caster, target):
            return False
        effect_parts = cls.effect if isinstance(cls.effect, (list, tuple)) else [cls.effect]
        if len(effect_parts) < 2:
            return False
        distance = to_int(str(effect_parts[1]))
        if distance <= 0:
            return False
        from soundrts.lib.nofloat import int_cos_1000, int_distance, int_sin_1000

        place = target.place
        if place is None:
            return False
        dx = target.x - caster.x
        dy = target.y - caster.y
        dist = int_distance(caster.x, caster.y, target.x, target.y)
        if dist > 0:
            new_x = target.x + dx * distance // dist
            new_y = target.y + dy * distance // dist
        else:
            angle = int(getattr(caster, "o", 90))
            new_x = target.x + distance * int_cos_1000(angle) // 1000
            new_y = target.y + distance * int_sin_1000(angle) // 1000
        new_x, new_y = place.find_free_space_for(target, new_x, new_y)
        if new_x is None:
            return False
        target.move_to(place, new_x, new_y)
        return True