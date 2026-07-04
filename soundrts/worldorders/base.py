import copy
import random
import time

import pygame

from soundrts.lib.nofloat import square_of_distance

from ..definitions import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL, rules
from ..lib.nofloat import to_int
from ..worldaction import AttackAction
from ..worldresource import Corpse, Deposit
from ..worldroom import Square
from ..lib.log import info, warning
from ..lib.nofloat import PRECISION, int_distance
from ..worldupgrade.base import Upgrade

ORDERS_QUEUE_LIMIT = 10


def _order_target_square(target):
    from ..worldroom import Square, ZoomTarget

    if isinstance(target, ZoomTarget):
        return target.place
    if isinstance(target, Square):
        return target
    if hasattr(target, "is_water"):
        return target
    place = getattr(target, "place", None)
    if place is not None and hasattr(place, "is_water"):
        return place
    return None


def _is_impassable_water_for_ground_unit(unit, square):
    """地面单位不可进入纯水路方格（河流/海洋/湖泊等；渡口/大桥除外）。"""
    if getattr(unit, "airground_type", None) != "ground":
        return False
    if square is None:
        return False
    return getattr(square, "is_water", False) and not getattr(square, "is_ground", True)


def _is_impassable_land_for_water_unit(unit, square):
    """水上单位不可进入陆地方格。"""
    if getattr(unit, "airground_type", None) != "water":
        return False
    if square is None:
        return False
    return not getattr(square, "is_water", False)


def _terrain_impassable_reason(unit, square):
    if _is_impassable_water_for_ground_unit(unit, square):
        return "water_impassable"
    if _is_impassable_land_for_water_unit(unit, square):
        return "land_impassable"
    return None


class Order:

    target = None
    type = None
    is_impossible = False
    is_complete = False
    is_imperative = False
    cancel_order = "stop"
    never_forget_previous = False
    can_be_followed = True

    cost = (0,) * MAX_NB_OF_RESOURCE_TYPES
    population_cost = 0

    is_deferred = False
    nb_args = 0

    def __init__(self, unit, args):
        self.unit = unit
        self.args = args

    def __getstate__(self):
        from ..save_pickle import strip_target_for_pickle

        state = self.__dict__.copy()
        strip_target_for_pickle(state)
        return state

    def __setstate__(self, state):
        from ..save_pickle import restore_target_after_pickle

        self.__dict__.update(state)
        restore_target_after_pickle(self)

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    __first_update = True

    def execute(self):
        self.unit.counterattack_enabled = not self.unit.counterattack_enabled
        if self.unit.counterattack_enabled:
            self.unit.notify("counterattack_enabled")
        else:
            self.unit.notify("counterattack_disabled")

    def update(self):
        if self.__first_update:
            self.unit.stop()
            self.__first_update = False
        self.execute()

    @property
    def player(self):
        return self.unit.player

    @property
    def world(self):
        return self.unit.world

    def cancel(self, unpay=True):
        pass


    def mark_as_impossible(self, reason=None):
        self.is_impossible = True
        n = "order_impossible"
        if reason is not None:
            n += "," + reason
        self.unit.notify(n)
        self.unit.distance_to_goal = float("inf")

    def _reject_if_terrain_impassable(self, target):
        square = _order_target_square(target)
        reason = _terrain_impassable_reason(self.unit, square)
        if reason:
            self.mark_as_impossible(reason)
            return True
        return False

    def mark_as_complete(self):
        self.is_complete = True
        self.unit.distance_to_goal = 0

    def update_target(self):
        if self.target:
            self.target = self.player.updated_target(self.target)

    def _group_is_ready(self):
        for u in self.player.units:
            if (
                u is not self.unit
                and u.orders
                and u.orders[0] == self
                and u.place is not self.unit.place
            ):
                return False
        return True

    def _grouped_attack(self, target):
        # goal: make sure no unit starts deploying instead of attacking
        # (the recently arrived units used to deploy before attacking)
        self.unit.notify("attack")
        for u in self.player.units:
            if u.orders and u.orders[0] == self and u.place is self.unit.place:
                u.start_moving_to(target)

    def _default_move_to_or_fail(self, target):
        self.unit.start_moving_to(target)
        if self.unit.is_idle:  # target is unreachable
            self.mark_as_impossible()
            self.unit.deploy()  # do not block the path

    def _smart_move_to_or_fail(self, target):
        # 如果目标是具体的方格或方格内落点（如草地/建造点/资源/敌人/可修理建筑），允许进入该方格，不启用“避敌”绕行
        force_enter_square = False
        try:
            # Square 或 ZoomTarget 指向方格内坐标都视为需要强制进入方格
            from ..worldroom import Square, ZoomTarget
            from ..worldresource import Deposit, is_building_land
            force_enter_square = (
                isinstance(target, Square) or
                isinstance(target, ZoomTarget) or
                (self.keyword == "build" and is_building_land(target)) or
                (self.keyword == "gather" and (
                    isinstance(target, Deposit) or
                    (getattr(target, "is_a_building", False) and getattr(target, "resource_type", None))
                )) or
                (self.keyword in ("repair", "build_phase_two") and getattr(target, "is_repairable", False)) or
                (self.keyword == "attack") or
                (self.keyword == "capture") or
                (self.keyword == "herd" and getattr(target, "herdable", 0)) or
                # 关键补充：当是普通 go 到当前方格中的对象（建筑/草地/资源/单位）时，也必须允许进入该方格
                (self.keyword == "go" and (
                    isinstance(target, (Square, ZoomTarget, Deposit)) or
                    is_building_land(target) or
                    getattr(target, "is_a_building", False) or
                    getattr(target, "is_vulnerable", False)
                ))
            )
        except Exception:
            force_enter_square = False

        if force_enter_square:
            # 直接朝目标移动，不使用 avoid=True，这样不会因为敌人威胁拒绝到达目标方格的草地/建造位置
            self.unit.start_moving_to(target, avoid=False)
        else:
            self.unit.start_moving_to(target, avoid=True)
        if self.unit.is_idle and self.keyword in ("go", "patrol", "herd"):
            # eventually attack the obstacle
            next_square = self.unit.next_square(target)
            if force_enter_square:
                # 目标就是该方格，允许继续进入
                self.unit.start_moving_to(next_square)
            elif self.player.enemy_menace(next_square) == 0:  # no obstacle yet
                self.unit.start_moving_to(next_square)
            elif next_square is target:
                if (
                    self.player.balance(next_square, self.unit.place, mult=10) > 11
                    or self._group_is_ready()
                ):
                    self._grouped_attack(next_square)
                    return
                else:
                    self.unit.deploy()
                    return
            elif self.player.balance(next_square, self.unit.place, mult=10) > 11:
                self._grouped_attack(next_square)
            else:
                self.unit.deploy()
                return
        if self.unit.is_idle:  # target is unreachable
            self.mark_as_impossible()
            self.unit.deploy()  # do not block the path

    def move_to_or_fail(self, target):
        if self.unit.speed == 0:
            self.mark_as_impossible()
            return
        if self._reject_if_terrain_impassable(target):
            self.unit.deploy()
            return

        # 统一强制进入方格的快捷通道（无论是否smart_units）
        force_enter_square = False
        try:
            from ..worldroom import Square, ZoomTarget
            from ..worldresource import Deposit, is_building_land
            force_enter_square = (
                isinstance(target, Square) or
                isinstance(target, ZoomTarget) or
                (self.keyword == "build" and is_building_land(target)) or
                (self.keyword == "gather" and (
                    isinstance(target, Deposit) or
                    (getattr(target, "is_a_building", False) and getattr(target, "resource_type", None))
                )) or
                (self.keyword in ("repair", "build_phase_two") and getattr(target, "is_repairable", False)) or
                (self.keyword == "attack") or
                (self.keyword == "capture") or
                (self.keyword == "herd" and getattr(target, "herdable", 0)) or
                (self.keyword == "go" and (
                    isinstance(target, (Square, ZoomTarget, Deposit)) or
                    is_building_land(target) or
                    getattr(target, "is_a_building", False) or
                    getattr(target, "is_vulnerable", False)
                ))
            )
        except Exception:
            force_enter_square = False

        if force_enter_square:
            # 尝试直接进入目标所在方格，不使用避敌逻辑
            self.unit.start_moving_to(target, avoid=False)
            if self.unit.is_idle and self.keyword in (
                "go", "patrol", "herd", "gather", "repair", "build_phase_two", "attack", "capture"
            ):
                next_square = self.unit.next_square(target)
                if next_square is not None:
                    self.unit.start_moving_to(next_square, avoid=False)
            # 不标记为不可能，交给后续帧继续尝试
            if self.unit.is_idle and not self.player.smart_units:
                # 对于非smart单位，避免直接判定失败导致放弃
                return

        # 常规路径
        if self.player.smart_units:
            self._smart_move_to_or_fail(target)
        else:
            self._default_move_to_or_fail(target)

    def immediate_action(self):
        if len(self.unit.orders) >= ORDERS_QUEUE_LIMIT:
            self.unit.notify("order_impossible,the_queue_is_full")
        # check population requirement only if the queue is empty
        elif (
            not self.unit.orders
            and self.population_cost != 0
            and self.unit.player.available_population
            < self.unit.player.used_population + self.population_cost
        ):
            self.unit.notify("order_impossible,not_enough_population")
        else:
            self.unit.orders.append(self)
            self.on_queued()

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return cls.keyword in unit.basic_skills

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []


class ComplexOrder(Order):

    unit_menu_attribute: str

    def __init__(self, unit, args):
        Order.__init__(self, unit, args[1:])
        self.type = rules.unit_class(args[0])

    @staticmethod
    def _merge_phase_resource_cost(player, modified_cost):
        """合并时代 phase_bonus 中的多资源 cost（含百分比）。"""
        if player is None or not modified_cost:
            return
        pb = getattr(player, "phase_cost_bonus", None)
        if pb:
            for i, bonus in enumerate(pb):
                if i < len(modified_cost):
                    modified_cost[i] += bonus
        pbp = getattr(player, "phase_cost_percent_bonus", None)
        if pbp:
            for i, percent_bonus in enumerate(pbp):
                if i < len(modified_cost) and percent_bonus != 0:
                    modified_cost[i] += int(modified_cost[i] * percent_bonus)

    @staticmethod
    def _merge_phase_scalar_cost(player, base, abs_attr, pct_attr):
        """合并 phase 的标量成本修正（time_cost / population_cost）与百分比。"""
        if player is None:
            return base
        r = base + int(getattr(player, abs_attr, 0) or 0)
        p = getattr(player, pct_attr, 0.0) or 0.0
        if p != 0:
            r += int(r * p)
        return r

    @property
    def cost(self):
        # 获取基础成本
        base_cost = self.type.cost
        
        try:
            from ..definitions import rules
            from ..lib.log import warning, info
            from ..lib.nofloat import PRECISION
            
            # 创建一个新的成本列表，避免修改原始类型的cost
            modified_cost = list(base_cost)
            
            # 检查当前单位是否可以使用已研究的科技（精确作用域：仅应用这些科技的效果）
            applicable_techs = []
            
            if hasattr(self.unit, 'player') and self.unit.player:
                # 只针对具有can_use或can_use_tech的单位应用科技效果
                for tech_name in self.unit.player.upgrades:
                    # 跳过无效的tech_name
                    if not tech_name or not isinstance(tech_name, str):
                        continue
                        
                    # 检查单位是否可以使用该科技
                    can_use = False
                    
                    # 检查can_use
                    if hasattr(self.type, 'can_use') and tech_name in self.type.can_use:
                        can_use = True
                        
                    # 检查can_use_tech
                    if not can_use and hasattr(self.type, 'can_use_tech') and tech_name in self.type.can_use_tech:
                        can_use = True
                        
                    # 检查can_use_skill
                    if not can_use and hasattr(self.type, 'can_use_skill') and tech_name in self.type.can_use_skill:
                        can_use = True
                    
                    # 如果可以使用该科技，加入适用科技列表
                    if can_use:
                        applicable_techs.append(tech_name)
                        
                # 仅聚合 applicable_techs 对应的效果值
                if applicable_techs:
                    local_cost_bonus = [0] * len(modified_cost)
                    local_cost_percent = [0.0] * len(modified_cost)
                    for tech_name in applicable_techs:
                        for effect_data in Upgrade._global_cost_effects.get(tech_name, []):
                            # 跳过未达等级
                            if self.unit.player.level(tech_name) < effect_data.get('level', 0):
                                continue
                            if effect_data.get('has_cost_effect'):
                                for i, bonus in enumerate(effect_data.get('cost_bonus_values', [])):
                                    if i < len(local_cost_bonus):
                                        local_cost_bonus[i] += bonus
                            if effect_data.get('has_cost_percent_effect'):
                                for i, p in enumerate(effect_data.get('cost_percent_bonus_values', [])):
                                    if i < len(local_cost_percent):
                                        local_cost_percent[i] += p
                    # 应用本地聚合
                    for i, bonus in enumerate(local_cost_bonus):
                        if i < len(modified_cost):
                            modified_cost[i] += bonus
                    for i, percent_bonus in enumerate(local_cost_percent):
                        if i < len(modified_cost) and percent_bonus != 0:
                            bonus_amount = int(modified_cost[i] * percent_bonus)
                            modified_cost[i] += bonus_amount

            if hasattr(self.unit, "player") and self.unit.player:
                self._merge_phase_resource_cost(self.unit.player, modified_cost)

            # 确保所有成本不为负
            for i in range(len(modified_cost)):
                modified_cost[i] = max(0, modified_cost[i])
            
            return tuple(modified_cost)
        except Exception as e:
            warning(f"计算成本时出错: {e}")
        
        return base_cost

    @property
    def population_cost(self):
        # 获取基础人口成本
        base_population_cost = self.type.population_cost
        
        try:
            from ..lib.log import warning, info

            modified_population_cost = base_population_cost

            if hasattr(self.unit, 'player') and self.unit.player:
                # 检查当前单位是否可以使用已研究的科技
                applicable_techs = []

                for tech_name in self.unit.player.upgrades:
                    # 跳过无效的tech_name
                    if not tech_name or not isinstance(tech_name, str):
                        continue

                    # 检查单位是否可以使用该科技
                    can_use = False

                    # 检查can_use
                    if hasattr(self.type, 'can_use') and tech_name in self.type.can_use:
                        can_use = True

                    # 检查can_use_tech
                    if not can_use and hasattr(self.type, 'can_use_tech') and tech_name in self.type.can_use_tech:
                        can_use = True

                    # 检查can_use_skill
                    if not can_use and hasattr(self.type, 'can_use_skill') and tech_name in self.type.can_use_skill:
                        can_use = True

                    if can_use:
                        applicable_techs.append(tech_name)

                if applicable_techs:
                    local_pop_bonus = 0
                    local_pop_percent = 0.0
                    for tech_name in applicable_techs:
                        for effect_data in Upgrade._global_cost_effects.get(tech_name, []):
                            if self.unit.player.level(tech_name) < effect_data.get('level', 0):
                                continue
                            if effect_data.get('has_population_cost_effect'):
                                local_pop_bonus += effect_data.get('population_cost_bonus_value', 0)
                            if effect_data.get('has_population_cost_percent_effect'):
                                local_pop_percent += effect_data.get('population_cost_percent_bonus_value', 0.0)
                    modified_population_cost += local_pop_bonus
                    if local_pop_percent != 0:
                        bonus_amount = int(modified_population_cost * local_pop_percent)
                        modified_population_cost += bonus_amount

                modified_population_cost = self._merge_phase_scalar_cost(
                    self.unit.player,
                    modified_population_cost,
                    "phase_population_cost_bonus",
                    "phase_population_cost_percent_bonus",
                )

            return max(0, modified_population_cost)

        except Exception as e:
            warning(f"计算人口成本时出错: {e}")
        
        return base_population_cost

    @property
    def time_cost(self):
        # 获取基础时间成本
        base_time_cost = self.type.time_cost
        
        try:
            from ..lib.log import warning, info

            modified_time_cost = base_time_cost

            if hasattr(self.unit, 'player') and self.unit.player:
                applicable_techs = []

                for tech_name in self.unit.player.upgrades:
                    if not tech_name or not isinstance(tech_name, str):
                        continue

                    can_use = False

                    if hasattr(self.type, 'can_use') and tech_name in self.type.can_use:
                        can_use = True

                    if not can_use and hasattr(self.type, 'can_use_tech') and tech_name in self.type.can_use_tech:
                        can_use = True

                    if not can_use and hasattr(self.type, 'can_use_skill') and tech_name in self.type.can_use_skill:
                        can_use = True

                    if can_use:
                        applicable_techs.append(tech_name)

                if applicable_techs:
                    local_time_bonus = 0
                    local_time_percent = 0.0
                    for tech_name in applicable_techs:
                        for effect_data in Upgrade._global_cost_effects.get(tech_name, []):
                            if self.unit.player.level(tech_name) < effect_data.get('level', 0):
                                continue
                            if effect_data.get('has_time_cost_effect'):
                                local_time_bonus += effect_data.get('time_cost_bonus_value', 0)
                            if effect_data.get('has_time_cost_percent_effect'):
                                local_time_percent += effect_data.get('time_cost_percent_bonus_value', 0.0)
                    modified_time_cost += local_time_bonus
                    if local_time_percent != 0:
                        bonus_amount = int(modified_time_cost * local_time_percent)
                        modified_time_cost += bonus_amount

                modified_time_cost = self._merge_phase_scalar_cost(
                    self.unit.player,
                    modified_time_cost,
                    "phase_time_cost_bonus",
                    "phase_time_cost_percent_bonus",
                )

            buff_pct = getattr(self.unit, "_buff_time_cost_percent", 0)
            if buff_pct:
                modified_time_cost = max(
                    0, modified_time_cost * (100 + buff_pct) // 100
                )

            return max(0, modified_time_cost)

        except Exception as e:
            warning(f"计算时间成本时出错: {e}")
        
        return base_time_cost

    @property
    def production_qty(self):
        # 获取基础产量
        base_qty = getattr(self.type, 'production_qty', 1)
        
        try:
            from ..lib.log import warning, info
            
            # 检查当前单位是否可以使用已研究的科技
            applicable_techs = []
            
            if hasattr(self.unit, 'player') and self.unit.player:
                # 只针对具有can_use或can_use_tech的单位应用科技效果
                for tech_name in self.unit.player.upgrades:
                    # 跳过无效的tech_name
                    if not tech_name or not isinstance(tech_name, str):
                        continue
                        
                    # 检查单位是否可以使用该科技
                    can_use = False
                    
                    # 检查can_use
                    if hasattr(self.type, 'can_use') and tech_name in self.type.can_use:
                        can_use = True
                        
                    # 检查can_use_tech
                    if not can_use and hasattr(self.type, 'can_use_tech') and tech_name in self.type.can_use_tech:
                        can_use = True
                        
                    # 检查can_use_skill
                    if not can_use and hasattr(self.type, 'can_use_skill') and tech_name in self.type.can_use_skill:
                        can_use = True
                    
                    # 如果可以使用该科技，加入适用科技列表
                    if can_use:
                        applicable_techs.append(tech_name)
                
                # 对所有适用的科技应用效果
                if applicable_techs:
                    # 应用玩家全局产量修正
                    modified_qty = base_qty
                    
                    # 应用固定值修正
                    if hasattr(self.unit.player, 'production_qty_bonus'):
                        modified_qty += self.unit.player.production_qty_bonus
                    
                    # 应用百分比修正
                    if hasattr(self.unit.player, 'production_qty_percent_bonus') and self.unit.player.production_qty_percent_bonus != 0:
                        percent_bonus = self.unit.player.production_qty_percent_bonus
                        bonus_amount = int(modified_qty * percent_bonus)
                        modified_qty += bonus_amount
                    
                    # 确保产量不为负
                    return max(0, modified_qty)
            
            # 如果没有适用的科技，返回基础值
            return base_qty
            
        except Exception as e:
            warning(f"计算产量时出错: {e}")
        
        return base_qty

    @staticmethod
    def additional_condition(unit, type_name):
        return True

    @classmethod
    def _is_almost_allowed(cls, unit, type_name):
        return (
            type_name in getattr(unit, cls.unit_menu_attribute)
            and unit.player is not None
            and type_name not in unit.player.forbidden_techs
            and (not unit.orders or unit.orders[-1].can_be_followed)
            and cls.additional_condition(unit, type_name)
            and unit.player.check_count_limit(type_name)
        )

    @classmethod
    def is_allowed(cls, unit, type_name, *unused_args):
        return cls._is_almost_allowed(unit, type_name) and unit.player.has_all(
            rules.unit_class(type_name).requirements
        )

    @classmethod
    def _hide_locked_commands(cls):
        unlockable_menu_attributes = {
            "can_build",
            "can_train",
            "can_research",
            "can_advance",
            "can_upgrade_to",
            "can_change_to",
        }
        return (
            cls.unit_menu_attribute in unlockable_menu_attributes
            and rules.get("parameters", "hide_locked_commands", 0)
        )

    @classmethod
    def menu(cls, unit, strict=False):
        hide_locked = strict or cls._hide_locked_commands()
        is_allowed = cls.is_allowed if hide_locked else cls._is_almost_allowed
        m = []
        for t in getattr(unit, cls.unit_menu_attribute):
            if is_allowed(unit, t):
                m.append(cls.keyword + " " + t)
        return m


class BasicOrder(Order):

    pass