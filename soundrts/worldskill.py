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
    trigger_timing = "on_hit"  # on_hit | on_attack | on_attack_replace | on_damaged | on_death
    mdg_trigger_rate = 0
    rdg_trigger_rate = 0
    hp_threshold = 0
    trigger_condition = ""
    conversion_interval = 0
    conversion_min_intervals = 0
    conversion_max_intervals = 0
    conversion_chance = 0
    conversion_resist = 0
    conversion_fail_at_max = 0

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
                success = bool(getattr(cls, method_name)(caster, target, world))
            except Exception as e:
                from .lib.log import warning
                warning(f"技能 {cls.type_name} 执行失败: {e}")
                return False
        else:
            # 如果没有找到对应的方法，尝试通用处理
            success = bool(cls._execute_generic_effect(caster, target, world))

        # Manual (or any) cast of an on_death skill counts as the death blast:
        # when the blast then destroys the caster, die() must not fire it again.
        if success and str(getattr(cls, "trigger_timing", "") or "") == "on_death":
            skill_name = getattr(cls, "type_name", None)
            if skill_name and hasattr(caster, "_mark_death_skill_done"):
                caster._mark_death_skill_done(skill_name)
            elif skill_name and caster is not None:
                done = getattr(caster, "_death_skills_done", None)
                if done is None:
                    done = set()
                    caster._death_skills_done = done
                done.add(skill_name)
        return success

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
        if not (target and caster.is_an_enemy(target)):
            return False
        if cls._conversion_tech_gated_caster(caster) and not cls._conversion_target_allowed(
            caster, target
        ):
            return False
        return True

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
        if target is None or world is None:
            return False
        if getattr(caster, "x", None) is None or getattr(caster, "y", None) is None:
            return False
        dest = target
        if not hasattr(dest, "can_receive"):
            dest = getattr(dest, "place", None)
        if dest is None or not hasattr(dest, "can_receive"):
            return False
        units = world.get_objects(
            caster.x, caster.y, cls.effect_radius,
            filter=lambda x: (
                x.player is caster.player
                and getattr(x, "is_teleportable", True)
                and getattr(x, "x", None) is not None
                and getattr(x, "y", None) is not None
            ),
        )
        for u in units:
            if getattr(u, "place", None) is dest:
                continue
            if dest.can_receive(u.airground_type, unit=u):
                u.move_to(dest, None, None)
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
            if place.can_receive(u.airground_type, unit=u):
                u.move_to(place, None, None)
        return True

    @classmethod
    def _conversion_tech_gated_caster(cls, caster):
        """True when caster uses researched conversion allow/rest rules."""
        from .world_conversion import is_conversion_tech_gated

        return is_conversion_tech_gated(caster)

    @classmethod
    def _is_aoe2_monk_caster(cls, caster):
        """Deprecated alias — prefer ``_conversion_tech_gated_caster``."""
        return cls._conversion_tech_gated_caster(caster)

    @classmethod
    def _conversion_unconvertible_building(cls, target):
        """Buildings marked ``conversion_immune`` (or legacy name heuristics)."""
        from .world_conversion import is_conversion_immune

        if is_conversion_immune(target):
            return True
        # Legacy fallback for maps/mods that have not set conversion_immune yet
        tn = getattr(target, "type_name", None)
        if tn in (
            "town_center",
            "townhall",
            "monastery",
            "aoe_castle",
            "farm",
            "wall",
            "gate",
            "wonder",
        ):
            return True
        if tn and (
            tn.endswith("_town_center")
            or tn.endswith("_castle")
            or tn.endswith("_wall")
            or tn.endswith("_monastery")
        ):
            return True
        return False

    @classmethod
    def _conversion_target_allowed(cls, caster, target):
        """Tech-gated conversion filters (allows_monk / siege / building)."""
        from .world_conversion import (
            is_conversion_cleric,
            player_has_upgrade_flag,
        )
        from .worldunit.worldcreature import Building, BuildingSite

        upgrades_player = getattr(caster, "player", None)
        if is_conversion_cleric(target) and not player_has_upgrade_flag(
            upgrades_player, "conversion_allows_monk"
        ):
            return False

        expanded = getattr(target, "expanded_is_a", None) or ()
        is_building = isinstance(target, (Building, BuildingSite)) or (
            "building" in expanded
        )
        is_siege = "siege_unit" in expanded
        if is_building or is_siege:
            if is_siege and not player_has_upgrade_flag(
                upgrades_player, "conversion_allows_siege"
            ):
                return False
            if is_building and not player_has_upgrade_flag(
                upgrades_player, "conversion_allows_building"
            ):
                return False
            if is_building and cls._conversion_unconvertible_building(target):
                return False
        return True

    @classmethod
    def _conversion_target_allowed_for_monk(cls, caster, target):
        """Deprecated alias for ``_conversion_target_allowed``."""
        return cls._conversion_target_allowed(caster, target)

    @classmethod
    def conversion_channel_time(cls, caster, target, skill_cls=None):
        """Conversion channel length (ms / PRECISION units).

        Interval-roll skills last ``max_intervals * conversion_interval``
        (may finish early on a successful roll). Otherwise: base unit
        ``time_cost`` (~6s); siege/buildings longer; researched resist
        attrs on the target's owner lengthen the channel.
        """
        from .lib.nofloat import PRECISION
        from .world_conversion import (
            apply_conversion_channel_resist,
            conversion_roll_params,
        )
        from .worldunit.worldcreature import Building, BuildingSite

        roll = conversion_roll_params(caster, target, skill_cls)
        if roll is not None:
            return max(int(roll.interval) * int(roll.max_ci), PRECISION)

        base = getattr(skill_cls, "time_cost", 0) if skill_cls is not None else 0
        if not base:
            base = 6 * PRECISION

        expanded = getattr(target, "expanded_is_a", None) or ()
        is_building = isinstance(target, (Building, BuildingSite)) or (
            "building" in expanded
        )
        is_siege = "siege_unit" in expanded
        if is_building:
            base = max(int(base), 15 * PRECISION)
        elif is_siege:
            base = max(int(base), 10 * PRECISION)

        enemy = getattr(target, "player", None)
        return apply_conversion_channel_resist(base, enemy)

    @classmethod
    def _execute_conversion(cls, caster, target, world):
        """转换技能处理（规则驱动：allows_* / conversion_victim_dies）"""
        from .world_conversion import player_has_upgrade_flag

        if not (target and hasattr(target, "set_player") and caster.is_an_enemy(target)):
            return False

        if cls._conversion_tech_gated_caster(caster):
            if not cls._conversion_target_allowed(caster, target):
                return False

        # Victim dies instead of changing owner (e.g. Heresy)
        enemy = getattr(target, "player", None)
        if enemy and player_has_upgrade_flag(enemy, "conversion_victim_dies"):
            if hasattr(target, "die"):
                try:
                    target.die(attacker=caster)
                except TypeError:
                    target.die()
                return True
            try:
                target.hp = 0
            except Exception:
                pass
            return True

        target.set_player(caster.player)
        return True

    @classmethod
    def _skill_effect_is_conversion(cls, skill_cls):
        effect = getattr(skill_cls, "effect", None)
        if not effect:
            return False
        et = effect[0] if isinstance(effect, (list, tuple)) else effect
        return et == "conversion"

    @classmethod
    def _monk_is_converting_target(cls, unit, target):
        """True if *unit* has an active conversion UseOrder on *target*."""
        if target is None or unit is None:
            return False
        tid = getattr(target, "id", None)
        for order in getattr(unit, "orders", ()) or ():
            if getattr(order, "keyword", None) != "use":
                continue
            otype = getattr(order, "type", None)
            if otype is None or not cls._skill_effect_is_conversion(otype):
                continue
            ot = getattr(order, "target", None)
            if ot is target:
                return True
            if tid is not None and getattr(ot, "id", None) == tid:
                return True
        return False

    @classmethod
    def conversion_mana_participants(cls, caster, target):
        """Converters that should rest after a group conversion.

        Without ``conversion_rest_only_success``, every tech-gated ally also
        converting the same target rests; with the flag only *caster* rests.
        Non-gated casters always just return [caster].
        """
        from .world_conversion import player_has_upgrade_flag

        if caster is None:
            return []
        if not cls._conversion_tech_gated_caster(caster):
            return [caster]
        player = getattr(caster, "player", None)
        if player_has_upgrade_flag(player, "conversion_rest_only_success"):
            return [caster]
        if player is None:
            return [caster]
        participants = []
        for u in list(getattr(player, "units", ()) or ()):
            if not cls._conversion_tech_gated_caster(u):
                continue
            if u is caster or cls._monk_is_converting_target(u, target):
                participants.append(u)
        if caster not in participants:
            participants.append(caster)
        return participants

    @classmethod
    def apply_conversion_mana_costs(cls, caster, target, mana_cost):
        """Apply faith/mana rest after a successful conversion."""
        try:
            cost = int(mana_cost or 0)
        except (TypeError, ValueError):
            cost = 0
        if cost <= 0 or caster is None:
            return
        for u in cls.conversion_mana_participants(caster, target):
            try:
                u.mana = max(0, int(getattr(u, "mana", 0)) - cost)
            except (TypeError, ValueError):
                pass

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
        # Unit rdg_range (e.g. Block Printing) can extend conversion / skill reach.
        unit_range = getattr(caster, "rdg_range", 0) or 0
        try:
            unit_range = int(unit_range)
        except (TypeError, ValueError):
            unit_range = 0
        if unit_range > max_range:
            max_range = unit_range
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
            attacker_player = getattr(caster, "player", None)
            if hasattr(victim.player, "note_combat_with"):
                victim.player.note_combat_with(attacker_player)
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