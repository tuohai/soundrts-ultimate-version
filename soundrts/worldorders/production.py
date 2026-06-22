from ..definitions import VIRTUAL_TIME_INTERVAL, rules, style
from ..world_build_rules import (
    build_field_ok,
    deposit_build_target_ok,
    deposit_on_square,
    detach_addons_for_lift,
    has_pending_orphan_addons_for_host,
    is_flying_building_type,
    is_flying_building_unit,
    is_ground_host_building,
    is_ground_host_building_type,
    landing_coords_for_ground_building,
    requires_build_field_type,
    requires_deposit_type,
    try_reattach_orphan_addons,
    building_can_operate,
    can_host_addon,
    is_addon_type,
)
from ..worldresource import Meadow
from .base import ComplexOrder, Order, ORDERS_QUEUE_LIMIT
from .immediate import ImmediateOrder


def _source_morphs_as_train(unit):
    return bool(getattr(unit, "morph_as_train", 0))


def _hatchery_inject_time_multiplier(unit):
    """幼虫变形时继承同格主巢的注卵加速（time_cost 百分比 buff）。"""
    place = getattr(unit, "place", None)
    if place is None:
        return 100
    for obj in place.objects:
        if (
            getattr(obj, "type_name", None) == "hatchery"
            and getattr(obj, "player", None) is unit.player
        ):
            pct = getattr(obj, "_buff_time_cost_percent", 0)
            if pct:
                return max(1, 100 + int(pct))
    return 100


def _morph_train_time_cost(unit, target_type):
    base = getattr(target_type, "time_cost", 0) or 0
    mult = _hatchery_inject_time_multiplier(unit)
    if mult != 100:
        base = max(0, base * mult // 100)
    unit_time = getattr(unit, "time_cost", 0) or 0
    return max(0, base - unit_time)


def _upgrade_cost_diff(unit, target_type):
    current_cost = unit.cost
    target_cost = target_type.cost
    diff_cost = []
    for i in range(len(target_cost)):
        current_value = current_cost[i] if i < len(current_cost) else 0
        target_value = target_cost[i] if i < len(target_cost) else 0
        diff_cost.append(max(0, target_value - current_value))
    return tuple(diff_cost)


def _production_order_title(status_msg, unit):
    """状态播报：正在生产/耕种 + 资源类型名称（如黄金、食物）。"""
    result = list(status_msg)
    production_type = getattr(unit, "production_type", None)
    if production_type:
        resource_title = style.get(production_type, "title")
        if resource_title:
            result += resource_title
    return result


class ProductionOrder(ComplexOrder):

    is_imperative = True
    never_forget_previous = True

    def on_queued(self):
        result = self.unit.check_if_enough_resources(self.cost, self.population_cost)
        if result is not None:
            self.mark_as_impossible(result)
            return
        self.player.pay(self.cost)
        self.time = self.time_cost

    _previous_completeness = None

    def _notify_completeness(self):
        if self.time_cost == 0:
            return
        if self.time < 0:
            t = 0
        elif self.time > self.time_cost:  # can happen when training archers
            t = self.time_cost
        else:
            t = self.time
        c = int((self.time_cost - t) * 10 / self.time_cost)
        if c != self._previous_completeness:
            self.unit.notify("completeness,%s" % c)
            self._previous_completeness = c

    _has_started = False

    def _can_start(self):
        # 检查是否有population_cost属性
        if not hasattr(self, "population_cost"):
            return True
            
        # 对于TrainOrder，使用total_population_cost而不是population_cost
        if hasattr(self, "total_population_cost"):
            return (
                self.total_population_cost == 0
                or self.player.available_population >= self.player.used_population + self.total_population_cost
            )
        # 默认逻辑保持不变
        return (
            self.population_cost == 0
            or self.player.available_population >= self.player.used_population + self.population_cost
        )


    def _start(self):
        self._has_started = True
        self.is_deferred = False
        self.player.used_population += self.population_cost  # population reservation
        self._notify_completeness()

    def _defer(self):
        self.is_deferred = True
        self.unit.notify("production_deferred")

    def complete(self):
        pass

    def execute(self):
        if not self._has_started:
            if self._can_start():
                self._start()
            elif not self.is_deferred:
                self._defer()
        elif self.time > 0:
            self.time -= VIRTUAL_TIME_INTERVAL
            self._notify_completeness()
        else:
            self.complete()
            self.is_complete = True

    def cancel(self, unpay=True):
        if unpay:
            self.player.unpay(self.cost)
        if self._has_started:
            self.player.used_population -= self.population_cost  # end population reservation
        self.unit.notify("order_ok")


class StartProduceOrder(ImmediateOrder):
    """开始生产资源的命令"""
    keyword = "start_produce"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 通用的start_produce命令已被移除
        # 现在总是返回False，因为此命令被auto_produce和manual_produce替代
        return False

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def immediate_action(self):
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            base_production_cost = getattr(self.unit, 'production_cost', (0, 0))
            self.unit.debug_log(f"开始执行StartProduceOrder，基础生产成本：{base_production_cost}")
            self.unit.debug_log(f"生产参数：auto_production={getattr(self.unit, 'auto_production', 0)}, "
                  f"production_time={getattr(self.unit, 'production_time', 0)}, "
                  f"production_qty={getattr(self.unit, 'production_qty', 0)}, "
                  f"production_type={getattr(self.unit, 'production_type', 'resource1')}")
        
        # 获取修正后的生产成本
        production_cost = self._calculate_production_cost()
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"修正后的生产成本：{production_cost}")
            
        # 检查是否有足够的资源
        result = self.unit.check_if_enough_resources(production_cost, 0)
        if result is not None:
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log(f"资源不足，无法生产: {result}")
            self.mark_as_impossible(result)
            return

        # 支付生产成本
        self.player.pay(production_cost)
        
        # 开始生产
        self.unit.is_producing = True
        self.unit.production_progress = 0
        self.unit._previous_completeness = None
        
        # 更新生产时间和产量
        self._update_production_parameters()
        
        # 添加虚拟的生产订单到单位的orders列表中
        producing_order = ProducingOrder(self.unit, [])
        self.unit.orders.insert(0, producing_order)
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"已开始生产，设置is_producing={self.unit.is_producing}, 已支付成本")
            self.unit.debug_log(f"修正后的参数：production_time={self.unit.production_time}, production_qty={self.unit.production_qty}")
        
        self.unit.notify("order_ok")
        
    def _calculate_production_cost(self):
        """计算修正后的生产成本"""
        # 获取单位类定义的原始基础成本，而不是当前实例的值
        unit_class = type(self.unit)
        base_cost = getattr(unit_class, "production_cost", (0, 0))
        
        # 创建一个用于修改的成本列表（避免修改原始值）
        modified_cost = list(base_cost)
        
        # 检查玩家是否有生产成本修正
        if hasattr(self.player, 'production_cost_bonus'):
            # 应用固定值修正
            for i, bonus in enumerate(self.player.production_cost_bonus):
                if i < len(modified_cost):
                    modified_cost[i] += bonus
        
        if hasattr(self.player, 'production_cost_percent_bonus'):
            # 应用百分比修正
            for i, percent_bonus in enumerate(self.player.production_cost_percent_bonus):
                if i < len(modified_cost) and percent_bonus != 0:
                    bonus_amount = int(modified_cost[i] * percent_bonus)
                    modified_cost[i] += bonus_amount
        
        # 确保所有成本不为负
        for i in range(len(modified_cost)):
            modified_cost[i] = max(0, modified_cost[i])
        
        return tuple(modified_cost)
        
    def _update_production_parameters(self):
        """更新单位的生产参数（时间和产量）"""
        # 获取单位类定义的原始基础值，而不是当前实例的值（可能已被修改）
        unit_class = type(self.unit)
        
        # 更新生产时间 - 使用单位类的原始值
        base_time = getattr(unit_class, "production_time", 0)
        modified_time = base_time
        
        # 应用固定值修正
        if hasattr(self.player, 'production_time_bonus'):
            modified_time += self.player.production_time_bonus
        
        # 应用百分比修正
        if hasattr(self.player, 'production_time_percent_bonus') and self.player.production_time_percent_bonus != 0:
            # 正确的百分比计算：-50% 意味着时间变为原来的 50%
            final_multiplier = 1.0 + self.player.production_time_percent_bonus
            modified_time = int(modified_time * final_multiplier)
        
        # 确保生产时间不为负
        modified_time = max(1, modified_time)  # 至少需要1秒
        
        # 更新单位的生产时间
        self.unit.production_time = modified_time
        
        # 更新产量 - 使用单位类的原始值
        base_qty = getattr(unit_class, "production_qty", 0)
        modified_qty = base_qty
        
        # 应用固定值修正
        if hasattr(self.player, 'production_qty_bonus'):
            modified_qty += self.player.production_qty_bonus
        
        # 应用百分比修正
        if hasattr(self.player, 'production_qty_percent_bonus') and self.player.production_qty_percent_bonus != 0:
            # 正确的百分比计算：+50% 意味着数量变为原来的 150%
            final_multiplier = 1.0 + self.player.production_qty_percent_bonus
            modified_qty = int(modified_qty * final_multiplier)
        
        # 确保产量不为负
        modified_qty = max(0, modified_qty)
        
        # 更新单位的产量
        self.unit.production_qty = modified_qty

class AutoProduceOrder(StartProduceOrder):
    """开始自动生产资源的命令"""
    keyword = "auto_produce"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否可以自动生产资源
        auto_prod = getattr(unit, "auto_production", 0) == 1
        
        # 如果is_gather=1且资源已满，则不允许生产
        if getattr(unit, "is_gather", 0) == 1:
            if (hasattr(unit, "resource_volume_max") and unit.resource_volume_max > 0 and
                hasattr(unit, "resource_qty") and unit.resource_qty >= unit.resource_volume_max):
                # 资源已满，设置为自动生产模式但不启动生产
                if hasattr(unit, "debug_log"):
                    unit.debug_log(f"is_gather模式下资源已满({unit.resource_qty}/{unit.resource_volume_max})，设置为自动生产模式但暂不启动")
                return False
        
        # 当建筑设置了auto_production=1且当前没有生产时显示
        return auto_prod and not unit.is_producing

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def immediate_action(self):
        # 设置为自动生产模式
        self.unit.current_production_mode = "auto"
        
        # 清除用户手动停止标志，允许自动重启
        if hasattr(self.unit, "_user_manually_stopped"):
            self.unit._user_manually_stopped = False
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"开始执行AutoProduceOrder，设置生产模式为：auto")
        
        # 检查is_gather=1模式下资源是否已满
        if getattr(self.unit, "is_gather", 0) == 1:
            if (hasattr(self.unit, "resource_volume_max") and self.unit.resource_volume_max > 0 and
                hasattr(self.unit, "resource_qty") and self.unit.resource_qty >= self.unit.resource_volume_max):
                # 资源已满，设置为自动生产模式但不启动生产
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"is_gather模式下资源已满({self.unit.resource_qty}/{self.unit.resource_volume_max})，设置为自动生产模式但暂不启动")
                self.unit.notify("order_ok")
                return
                
        # 调用父类的方法执行常规生产逻辑
        super().immediate_action()


class ManualProduceOrder(StartProduceOrder):
    """开始手动生产资源的命令"""
    keyword = "manual_produce"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否可以手动生产资源
        manual_prod = getattr(unit, "manual_production", 0) == 1
        
        # 如果is_gather=1且资源已满，则不允许生产
        if getattr(unit, "is_gather", 0) == 1:
            if (hasattr(unit, "resource_volume_max") and unit.resource_volume_max > 0 and
                hasattr(unit, "resource_qty") and unit.resource_qty >= unit.resource_volume_max):
                # 添加调试日志说明原因
                if hasattr(unit, "debug_log"):
                    unit.debug_log(f"手动生产不可用：资源已满({unit.resource_qty}/{unit.resource_volume_max})")
                return False
        
        # 当建筑设置了manual_production=1且当前没有生产时显示
        return manual_prod and not unit.is_producing

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def immediate_action(self):
        # 设置为手动生产模式
        self.unit.current_production_mode = "manual"
        
        # 清除用户手动停止标志，允许生产
        if hasattr(self.unit, "_user_manually_stopped"):
            self.unit._user_manually_stopped = False
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"开始执行ManualProduceOrder，设置生产模式为：manual")
        
        # 调用父类的方法执行常规生产逻辑
        super().immediate_action()


class AutoCultivateOrder(AutoProduceOrder):
    """开始自动耕种的命令（auto_produce的别名）"""
    keyword = "start_automatic_cultivate"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否可以自动耕种资源（使用auto_cultivate属性）
        auto_cultivate = getattr(unit, "auto_cultivate", 0) == 1
        
        # 如果is_gather=1且资源已满，则不允许耕种
        if getattr(unit, "is_gather", 0) == 1:
            if (hasattr(unit, "resource_volume_max") and unit.resource_volume_max > 0 and
                hasattr(unit, "resource_qty") and unit.resource_qty >= unit.resource_volume_max):
                # 资源已满，设置为自动耕种模式但不启动耕种
                if hasattr(unit, "debug_log"):
                    unit.debug_log(f"is_gather模式下资源已满({unit.resource_qty}/{unit.resource_volume_max})，设置为自动耕种模式但暂不启动")
                return False
        
        # 当建筑设置了auto_cultivate=1且当前没有生产时显示
        return auto_cultivate and not unit.is_producing

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []
            
    def immediate_action(self):
        # 设置为自动生产模式
        self.unit.current_production_mode = "auto"
        
        # 清除用户手动停止标志，允许自动重启
        if hasattr(self.unit, "_user_manually_stopped"):
            self.unit._user_manually_stopped = False
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"开始执行AutoCultivateOrder，设置生产模式为：auto")
        
        # 检查is_gather=1模式下资源是否已满
        if getattr(self.unit, "is_gather", 0) == 1:
            if (hasattr(self.unit, "resource_volume_max") and self.unit.resource_volume_max > 0 and
                hasattr(self.unit, "resource_qty") and self.unit.resource_qty >= self.unit.resource_volume_max):
                # 资源已满，设置为自动耕种模式但不启动耕种
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"is_gather模式下资源已满({self.unit.resource_qty}/{self.unit.resource_volume_max})，设置为自动耕种模式但暂不启动")
                self.unit.notify("order_ok")
                return
                
        # 执行常规生产逻辑
        # 计算修正后的生产成本
        production_cost = self._calculate_production_cost()
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"修正后的生产成本：{production_cost}")
            
        # 检查是否有足够的资源
        result = self.unit.check_if_enough_resources(production_cost, 0)
        if result is not None:
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log(f"资源不足，无法生产: {result}")
            self.mark_as_impossible(result)
            return

        # 支付生产成本
        self.player.pay(production_cost)
        
        # 开始生产
        self.unit.is_producing = True
        self.unit.production_progress = 0
        self.unit._previous_completeness = None
        
        # 更新生产时间和产量
        self._update_production_parameters()
        
        # 添加虚拟的耕种订单到单位的orders列表中（使用PlowingOrder代替ProducingOrder）
        plowing_order = PlowingOrder(self.unit, [])
        self.unit.orders.insert(0, plowing_order)
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"已开始耕种，设置is_producing={self.unit.is_producing}, 已支付成本")
            self.unit.debug_log(f"修正后的参数：production_time={self.unit.production_time}, production_qty={self.unit.production_qty}")
        
        self.unit.notify("order_ok")


class ManualCultivateOrder(ManualProduceOrder):
    """开始手动耕种的命令（manual_produce的别名）"""
    keyword = "start_manual_cultivate"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否可以手动耕种资源（使用manual_cultivate属性）
        manual_cultivate = getattr(unit, "manual_cultivate", 0) == 1
        
        # 如果is_gather=1且资源已满，则不允许耕种
        if getattr(unit, "is_gather", 0) == 1:
            if (hasattr(unit, "resource_volume_max") and unit.resource_volume_max > 0 and
                hasattr(unit, "resource_qty") and unit.resource_qty >= unit.resource_volume_max):
                # 添加调试日志说明原因
                if hasattr(unit, "debug_log"):
                    unit.debug_log(f"手动耕种不可用：资源已满({unit.resource_qty}/{unit.resource_volume_max})")
                return False
        
        # 当建筑设置了manual_cultivate=1且当前没有生产时显示
        return manual_cultivate and not unit.is_producing

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []
            
    def immediate_action(self):
        # 设置为手动生产模式
        self.unit.current_production_mode = "manual"
        
        # 清除用户手动停止标志，允许耕种
        if hasattr(self.unit, "_user_manually_stopped"):
            self.unit._user_manually_stopped = False
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"开始执行ManualCultivateOrder，设置生产模式为：manual")
        
        # 执行常规生产逻辑
        # 计算修正后的生产成本
        production_cost = self._calculate_production_cost()
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"修正后的生产成本：{production_cost}")
            
        # 检查是否有足够的资源
        result = self.unit.check_if_enough_resources(production_cost, 0)
        if result is not None:
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log(f"资源不足，无法生产: {result}")
            self.mark_as_impossible(result)
            return

        # 支付生产成本
        self.player.pay(production_cost)
        
        # 开始生产
        self.unit.is_producing = True
        self.unit.production_progress = 0
        self.unit._previous_completeness = None
        
        # 更新生产时间和产量
        self._update_production_parameters()
        
        # 添加虚拟的耕种订单到单位的orders列表中（使用PlowingOrder代替ProducingOrder）
        plowing_order = PlowingOrder(self.unit, [])
        self.unit.orders.insert(0, plowing_order)
        
        # 添加调试日志
        if hasattr(self.unit, "debug_log"):
            self.unit.debug_log(f"已开始耕种，设置is_producing={self.unit.is_producing}, 已支付成本")
            self.unit.debug_log(f"修正后的参数：production_time={self.unit.production_time}, production_qty={self.unit.production_qty}")
        
        self.unit.notify("order_ok")


class PlowingOrder(Order):
    """表示正在耕种的状态"""
    keyword = "plowing"
    
    def __init__(self, unit, args):
        super().__init__(unit, args)
        self.is_complete = False
        # 这个订单不是真实的订单，只是用于显示状态
        
    def execute(self):
        # 如果建筑物不再处于生产状态，则标记为完成
        if not getattr(self.unit, "is_producing", False):
            self.is_complete = True

    @property
    def title(self):
        from soundrts import msgparts as mp

        return _production_order_title(mp.PLOWING, self.unit)

    def _order_title_msg(self, place=None):
        return self.title


class ProducingOrder(Order):
    """表示正在生产资源的状态"""
    keyword = "producing"
    
    def __init__(self, unit, args):
        super().__init__(unit, args)
        self.is_complete = False
        # 这个订单不是真实的订单，只是用于显示状态
        
    def execute(self):
        # 如果建筑物不再处于生产状态，则标记为完成
        if not getattr(self.unit, "is_producing", False):
            self.is_complete = True

    @property
    def title(self):
        from soundrts import msgparts as mp

        return _production_order_title(mp.PRODUCTION, self.unit)

    def _order_title_msg(self, place=None):
        return self.title


class StopProduceOrder(ImmediateOrder):
    """停止生产资源的命令"""
    keyword = "stop_produce"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否正在生产资源
        is_producing = getattr(unit, "is_producing", False)
        # 检查当前命令是否是ProducingOrder
        has_producing_order = any(order.keyword == "producing" for order in unit.orders)
        
        # 检查是否设置了auto_production或manual_production，且有对应的资源类型
        has_production_ability = (getattr(unit, "auto_production", 0) == 1 or 
                                 getattr(unit, "manual_production", 0) == 1)
        
        # 检查是否同时设置了auto_cultivate和manual_cultivate
        has_cultivate_both = (getattr(unit, "auto_cultivate", 0) == 1 and 
                            getattr(unit, "manual_cultivate", 0) == 1)
        
        # 如果同时设置了auto_cultivate和manual_cultivate，则不显示stop_produce按钮
        if has_cultivate_both:
            return False
            
        # 如果正在生产，或者有生产能力且当前模式为auto，则允许显示停止按钮
        return (is_producing and has_producing_order) or (
            has_production_ability and 
            getattr(unit, "current_production_mode", None) == "auto"
        )

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def immediate_action(self):
        # 停止生产并返还资源
        if self.unit.is_producing:
            # 添加调试日志
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log(f"执行停止生产命令，当前进度: {self.unit.production_progress}/{self.unit.production_time}")
            
            # 只有在生产未完成时才返还资源
            if getattr(self.unit, "production_progress", 0) < getattr(self.unit, "production_time", 0):
                # 使用与StartProduceOrder相同的方法计算修正后的生产成本
                production_cost = self._calculate_production_cost()
                
                # 记录返还前的资源量
                if hasattr(self.unit, "debug_log"):
                    before_resources = self.player.resources[:]
                    self.unit.debug_log(f"返还资源前: {before_resources}, 返还金额: {production_cost}")
                
                # 返还资源
                self.player.unpay(production_cost)
                
                # 记录返还后的资源量
                if hasattr(self.unit, "debug_log"):
                    after_resources = self.player.resources[:]
                    self.unit.debug_log(f"返还资源后: {after_resources}")
            else:
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"生产已完成，无需返还资源")
            
            # 重置生产状态
            self.unit.is_producing = False
            self.unit.production_progress = 0
            self.unit._previous_completeness = None
            
            # 重要：重置生产模式，防止自动重启
            if hasattr(self.unit, "current_production_mode"):
                old_mode = getattr(self.unit, "current_production_mode", None)
                self.unit.current_production_mode = None
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"重置生产模式: {old_mode} -> None，防止自动重启")
            
            # 设置用户手动停止标志，防止自动重启逻辑再次启动生产
            self.unit._user_manually_stopped = True
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log("设置用户手动停止标志，防止自动重启")
            
            # 移除ProducingOrder或PlowingOrder
            for i, order in enumerate(self.unit.orders[:]):
                if isinstance(order, ProducingOrder) or isinstance(order, PlowingOrder):
                    self.unit.orders.pop(i)
                    break
            
            # 通知玩家
            self.unit.notify("order_ok")
            
    def _calculate_production_cost(self):
        """计算修正后的生产成本"""
        # 获取单位类定义的原始基础成本，而不是当前实例的值
        unit_class = type(self.unit)
        base_cost = getattr(unit_class, "production_cost", (0, 0))
        
        # 创建一个用于修改的成本列表（避免修改原始值）
        modified_cost = list(base_cost)
        
        # 检查玩家是否有生产成本修正
        if hasattr(self.player, 'production_cost_bonus'):
            # 应用固定值修正
            for i, bonus in enumerate(self.player.production_cost_bonus):
                if i < len(modified_cost):
                    modified_cost[i] += bonus
        
        if hasattr(self.player, 'production_cost_percent_bonus'):
            # 应用百分比修正
            for i, percent_bonus in enumerate(self.player.production_cost_percent_bonus):
                if i < len(modified_cost) and percent_bonus != 0:
                    bonus_amount = int(modified_cost[i] * percent_bonus)
                    modified_cost[i] += bonus_amount
        
        # 确保所有成本不为负
        for i in range(len(modified_cost)):
            modified_cost[i] = max(0, modified_cost[i])
        
        return tuple(modified_cost)


class StopCultivateOrder(StopProduceOrder):
    """停止耕种的命令"""
    keyword = "stop_cultivate"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查是否正在耕种
        is_producing = getattr(unit, "is_producing", False)
        # 检查当前命令是否是PlowingOrder
        has_plowing_order = any(order.keyword == "plowing" for order in unit.orders)
        
        # 检查是否设置了auto_cultivate或manual_cultivate
        has_cultivate_ability = (getattr(unit, "auto_cultivate", 0) == 1 or 
                                getattr(unit, "manual_cultivate", 0) == 1)
        
        # 如果正在耕种，或者有耕种能力且当前模式为auto，则允许显示停止按钮
        return (is_producing and has_plowing_order) or (
            has_cultivate_ability and 
            getattr(unit, "current_production_mode", None) == "auto"
        )

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []
    
    def immediate_action(self):
        # 停止耕种并返还资源
        if self.unit.is_producing:
            # 只有在耕种未完成时才返还资源
            if getattr(self.unit, "production_progress", 0) < getattr(self.unit, "production_time", 0):
                # 使用与StartProduceOrder相同的方法计算修正后的生产成本
                production_cost = self._calculate_production_cost()
                # 返还资源
                self.player.unpay(production_cost)
            
            # 重置生产状态
            self.unit.is_producing = False
            self.unit.production_progress = 0
            self.unit._previous_completeness = None
            
            # 移除PlowingOrder
            for i, order in enumerate(self.unit.orders[:]):
                if isinstance(order, PlowingOrder):
                    self.unit.orders.pop(i)
                    break
        
        # 重要：重置生产模式，防止自动重启
        if hasattr(self.unit, "current_production_mode"):
            self.unit.current_production_mode = None
        
        # 设置用户手动停止标志，防止自动重启逻辑再次启动耕种
        self.unit._user_manually_stopped = True
        
        # 通知玩家
        self.unit.notify("order_ok")


class TrainOrder(ProductionOrder):

    unit_menu_attribute = "can_train"
    keyword = "train"
    cancel_order = "cancel_training"

    def _requested_train_count(self):
        train_count = 1
        if hasattr(self.unit, "can_train") and isinstance(self.unit.can_train, dict):
            unit_type_name = self.type.__name__
            if unit_type_name in self.unit.can_train:
                train_count = max(1, self.unit.can_train[unit_type_name])
        return train_count

    def _train_should_apply_bonuses(self):
        try:
            if hasattr(self.unit, "player") and self.unit.player:
                for tech_name in self.unit.player.upgrades:
                    if not tech_name or not isinstance(tech_name, str):
                        continue
                    can_use = False
                    if hasattr(self.type, "can_use") and tech_name in self.type.can_use:
                        can_use = True
                    if not can_use and hasattr(self.type, "can_use_tech") and tech_name in self.type.can_use_tech:
                        can_use = True
                    if not can_use and hasattr(self.type, "can_use_skill") and tech_name in self.type.can_use_skill:
                        can_use = True
                    if can_use:
                        return True
        except Exception:
            pass
        return False

    def _total_population_cost_for_count(self, count, should_apply_bonuses):
        base_total_population_cost = self.type.population_cost * count
        modified_population_cost = base_total_population_cost
        if should_apply_bonuses:
            if hasattr(self.unit.player, "population_cost_bonus"):
                modified_population_cost += self.unit.player.population_cost_bonus
            if (
                hasattr(self.unit.player, "population_cost_percent_bonus")
                and self.unit.player.population_cost_percent_bonus != 0
            ):
                bonus_amount = int(
                    modified_population_cost * self.unit.player.population_cost_percent_bonus
                )
                modified_population_cost += bonus_amount
        modified_population_cost = self._merge_phase_scalar_cost(
            self.unit.player,
            modified_population_cost,
            "phase_population_cost_bonus",
            "phase_population_cost_percent_bonus",
        )
        return max(0, modified_population_cost)

    def _max_train_count_for_population(self, requested, should_apply_bonuses):
        headroom = self.player.available_population - self.player.used_population
        if headroom <= 0:
            return 0
        for count in range(requested, 0, -1):
            if self._total_population_cost_for_count(count, should_apply_bonuses) <= headroom:
                return count
        return 0

    def _max_train_count_for_count_limit(self, requested):
        from ..worldplayerbase.base import Player

        type_name = getattr(self.type, "type_name", None) or self.type.__name__
        limit = Player.effective_count_limit(type_name)
        if limit == 0:
            return requested
        if not hasattr(self.player, "future_count"):
            return requested
        current = self.player.future_count(type_name, exclude_order=self)
        room = limit - current
        if room <= 0:
            return 0
        return min(requested, room)

    def immediate_action(self):
        if len(self.unit.orders) >= ORDERS_QUEUE_LIMIT:
            self.unit.notify("order_impossible,the_queue_is_full")
            return
        if not self.unit.orders and self.type.population_cost > 0:
            affordable = self._max_train_count_for_population(
                self._requested_train_count(),
                self._train_should_apply_bonuses(),
            )
            if affordable == 0:
                self.unit.notify("order_impossible,not_enough_population")
                return
        self.unit.orders.append(self)
        self.on_queued()

    def on_queued(self):
        if not building_can_operate(self.unit):
            self.mark_as_impossible("cannot_build_here")
            return
        # 获取要训练的单位数量
        self.train_count = self._requested_train_count()
        should_apply_bonuses = self._train_should_apply_bonuses()

        # 人口不足时按剩余人口训练尽可能多的单位
        affordable = self._max_train_count_for_population(
            self.train_count, should_apply_bonuses
        )
        if affordable == 0:
            self.mark_as_impossible("not_enough_population")
            return
        self.train_count = affordable

        affordable = self._max_train_count_for_count_limit(self.train_count)
        if affordable == 0:
            self.mark_as_impossible("count_limit_reached")
            return
        self.train_count = affordable
        
        # 修改成本计算逻辑
        # 先获取未经修正的基础单位成本
        base_unit_cost = self.type.cost
        
        # 计算多个单位的总基础成本
        base_total_cost = [c * self.train_count for c in base_unit_cost]
        
        # 创建一个用于应用修正的成本列表
        modified_cost = list(base_total_cost)
        
        if should_apply_bonuses:
            # 应用玩家的成本修正（只应用一次）
            if hasattr(self.unit.player, 'cost_bonus'):
                for i, bonus in enumerate(self.unit.player.cost_bonus):
                    if i < len(modified_cost):
                        modified_cost[i] += bonus  # 只加一次，而不是每个单位都加
            
            # 应用玩家的百分比成本修正
            if hasattr(self.unit.player, 'cost_percent_bonus'):
                for i, percent_bonus in enumerate(self.unit.player.cost_percent_bonus):
                    if i < len(modified_cost) and percent_bonus != 0:
                        bonus_amount = int(modified_cost[i] * percent_bonus)
                        modified_cost[i] += bonus_amount

        self._merge_phase_resource_cost(self.unit.player, modified_cost)
        
        # 确保所有成本不为负
        for i in range(len(modified_cost)):
            modified_cost[i] = max(0, modified_cost[i])
        
        # 存储修正后的总成本
        self.total_cost = tuple(modified_cost)

        modified_population_cost = self._total_population_cost_for_count(
            self.train_count, should_apply_bonuses
        )

        # 存储单个单位和总食物成本（用于显示和退款计算）
        self.single_population_cost = self.population_cost  # 保存单个单位的修正后食物成本，可能在某些地方用到
        self.total_population_cost = modified_population_cost
        
        # 检查是否有足够的资源和人口
        result = self.unit.check_if_enough_resources(self.total_cost, self.total_population_cost)
        if result is not None:
            self.mark_as_impossible(result)
            return
            
        # 预扣除全部资源成本
        self.player.pay(self.total_cost)
        self.time = self.time_cost

    def _start(self):
        # 覆盖父类方法，正确预扣除食物成本
        self._has_started = True
        self.is_deferred = False
        # 预扣除所有单位的总食物成本
        self.player.used_population += self.total_population_cost  # population reservation
        self._notify_completeness()

    def complete(self):
        # 跟踪成功创建的单位数量
        created_units = 0
        
        # 循环创建多个单位
        from ..worldplayercomputer_water import spawn_place_for_trained_water_unit

        for _ in range(self.train_count):
            place, x, y = spawn_place_for_trained_water_unit(self.unit, self.type)
            if (
                x is None
                and self.type.airground_type == "water"
                and getattr(getattr(self.unit, "type", type(self.unit)), "is_buildable_near_water_only", False)
                and self.unit.nearest_water() is None
            ):
                # 如果还没创建任何单位，则取消整个命令
                if created_units == 0:
                    self.cancel()
                    self.mark_as_impossible("not_enough_space")
                # 如果已经创建了部分单位但没有足够空间继续创建，需要返还未使用的资源
                elif created_units < self.train_count:
                    refund_ratio = (self.train_count - created_units) / self.train_count
                    refund_cost = [int(c * refund_ratio) for c in self.total_cost]
                    self.player.unpay(refund_cost)
                    population_used = int(self.total_population_cost * (created_units / self.train_count))
                    self.player.used_population -= self.total_population_cost - population_used
                break

            if x is None:
                # 如果没有更多空间，返还未使用的资源，并停止创建
                if created_units < self.train_count:
                    # 计算退款比例
                    refund_ratio = (self.train_count - created_units) / self.train_count
                    # 计算退款金额
                    refund_cost = [int(c * refund_ratio) for c in self.total_cost]
                    self.player.unpay(refund_cost)
                    # 计算需要减少的食物预订量（已使用的食物数量）
                    population_used = int(self.total_population_cost * (created_units / self.train_count))
                    # 结束食物预订，但只减去已使用的部分
                    self.player.used_population -= self.total_population_cost - population_used
                break
            
            # 创建单位
            u = self.type(self.player, place, x, y)
            # 记录该单位实际占用的人口（受科技等修正后），用于死亡/删除时正确返还
            try:
                base_pop = getattr(self.type, "population_cost", 0)
                effective_pop = getattr(self, "single_population_cost", base_pop)
                eff_int = max(0, int(effective_pop))
                u.effective_population_cost = eff_int
                # 由于 Player.add 在构造期间已按基础人口计入，这里做一次差值校正：
                delta_pop = eff_int - max(0, int(base_pop))
                if delta_pop != 0:
                    self.player.used_population += delta_pop
            except Exception:
                pass
            u.notify("complete")
            if getattr(u, "airground_type", None) == "water":
                from ..worldplayercomputer_water import movement_target_for_unit

                u_place = u.place
                if u_place is not None and not getattr(u_place, "is_water", False):
                    neighbors = [
                        n
                        for n in u_place.strict_neighbors
                        if getattr(n, "is_water", False)
                    ]
                    if neighbors:
                        target = min(
                            neighbors,
                            key=lambda sq: u_place.shortest_path_distance_to(
                                sq, self.player, "water"
                            ),
                        )
                        u.take_order(["go", target.id], forget_previous=True)
                elif self.unit.rallying_point:
                    rally = self.player.get_object_by_id(self.unit.rallying_point)
                    rally_place = (
                        rally
                        if rally is not None and hasattr(rally, "strict_neighbors")
                        else getattr(rally, "place", None)
                    )
                    if rally_place is not None:
                        move_target = movement_target_for_unit(
                            u, rally_place, self.player
                        )
                        if getattr(move_target, "is_water", False):
                            u.take_order(["go", move_target.id], forget_previous=True)
            else:
                u.take_default_order(self.unit.rallying_point)
            if not u.orders:
                u.take_default_order(self.unit.rallying_point)
            from ..card_loadout import apply_train_bonus_for_unit

            apply_train_bonus_for_unit(
                self.player,
                self.type,
                place,
                x,
                y,
                self.unit.rallying_point,
            )
            created_units += 1
        
        # 如果成功创建了所有单位，减少已用食物（因为单位现在会自己计算食物消耗）
        if created_units == self.train_count:
            self.player.used_population -= self.total_population_cost  # end population reservation
        # 如果没有创建任何单位且未标记为impossible，则标记为impossible
        elif created_units == 0 and not self.is_impossible:
            self.mark_as_impossible("not_enough_space")

    def cancel(self, unpay=True):
        """覆盖父类方法，确保使用total_cost和total_population_cost"""
        if unpay:
            self.player.unpay(self.total_cost)
        if self._has_started:
            self.player.used_population -= self.total_population_cost  # 结束食物预订，使用total_population_cost
        self.unit.notify("order_ok")


class ResearchOrder(ProductionOrder):

    unit_menu_attribute = "can_research"
    keyword = "research"
    cancel_order = "cancel_upgrading"

    def complete(self):
        self.type.upgrade_player(self.player)
        self.unit.notify("research_complete")

    @staticmethod
    def additional_condition(unit, type_name):
        if type_name in unit.player.upgrades:
            return False
        # phase（时代）必须通过 can_advance / AdvanceOrder 推进，
        # 不允许出现在科技研究通道里，避免 UI 与 AI 把"推进时代"
        # 错当成"研究科技"显示/执行。
        from ..definitions import rules
        from ..worldphase import is_a_phase
        if is_a_phase(rules.unit_class(type_name)):
            return False
        for u in unit.player.units:
            for w in unit.orders:
                if w.__class__ == ResearchOrder and w.type.__name__ == type_name:
                    return False
        return True


class AdvanceOrder(ResearchOrder):
    """时代推进命令：与研究科技分离的独立命令。

    用于通过 ``can_advance`` 字段升级 phase（时代）。其行为类似
    ``ResearchOrder``，但 keyword/属性不同，因此 UI 与 AI 能清晰区分
    "推进时代" 和 "研究科技" 两种概念。

    与 ``ResearchOrder`` 的差异：
    - ``unit_menu_attribute``: ``can_advance``
    - ``keyword``: ``advance``
    - ``complete()`` 发送 ``upgrade_complete`` 通知（更贴合时代切换的语义）
    - ``additional_condition`` 在并发推进同一时代时排重
    """

    unit_menu_attribute = "can_advance"
    keyword = "advance"
    cancel_order = "cancel_upgrading"

    def complete(self):
        self.type.upgrade_player(self.player)
        self.unit.notify("upgrade_complete")

    @staticmethod
    def additional_condition(unit, type_name):
        if type_name in unit.player.upgrades:
            return False
        # 仅允许 phase（时代）类型进入推进通道；普通科技必须走 can_research。
        from ..definitions import rules
        from ..worldphase import is_a_phase
        if not is_a_phase(rules.unit_class(type_name)):
            return False
        for u in unit.player.units:
            for w in unit.orders:
                if w.__class__ == AdvanceOrder and w.type.__name__ == type_name:
                    return False
        return True


class UpgradeToOrder(ProductionOrder):

    unit_menu_attribute = "can_upgrade_to"
    keyword = "upgrade_to"
    cancel_order = "cancel_upgrading"
    can_be_followed = False
    
    @property
    def cost(self):
        return _upgrade_cost_diff(self.unit, self.type)

    @property
    def population_cost(self):
        return self.type.population_cost - self.unit.population_cost

    @property
    def time_cost(self):
        if _source_morphs_as_train(self.unit):
            return _morph_train_time_cost(self.unit, self.type)
        return self.type.time_cost - self.unit.time_cost

    def complete(self):
        player, place, x, y, hp, hp_max = (
            self.player,
            self.unit.place,
            self.unit.x,
            self.unit.y,
            self.unit.hp,
            self.unit.hp_max,
        )
        leave_meadow = (
            not self.unit.is_buildable_anywhere and self.type.is_buildable_anywhere
        )
        consume_meadow = (
            self.unit.is_buildable_anywhere and not self.type.is_buildable_anywhere
        )
        blocked_exit = self.unit.blocked_exit
        if consume_meadow:
            meadow = place.find_nearest_meadow(self.unit)
            if meadow:
                x, y = meadow.x, meadow.y
                meadow.delete()
            else:
                self.unit.notify("order_impossible")
                return
        self.unit.notify("upgrade_to,%s" % self.world.get_next_id(increment=False))
        # 升级前保存旧单位的库存物品，升级后转移到新单位身上
        old_unit = self.unit
        old_unit.delete()
        unit = self.type(player, place, x, y)
        if blocked_exit:
            unit.block(blocked_exit)
        if not _source_morphs_as_train(old_unit) and hp != hp_max:
            unit.hp = hp
        # 把旧单位携带的物品转移到新单位（避免升级后物品消失）
        if hasattr(old_unit, "transfer_inventory_to"):
            old_unit.transfer_inventory_to(unit)
        unit.notify("complete")
        if leave_meadow:
            Meadow(place, x, y)

    @staticmethod
    def additional_condition(unit, unused_type_name):
        return not unit.orders


class ChangeToOrder(ProductionOrder):
    """
    变形命令：默认不消耗资源，用 change_time 控制时间。
    morph_as_train 1 时按目标单位训练成本/时间计费（如异虫幼虫）。
    """
    unit_menu_attribute = "can_change_to"
    keyword = "change_to"
    cancel_order = "cancel_changing"
    can_be_followed = False

    @property
    def cost(self):
        if _source_morphs_as_train(self.unit):
            return tuple(self.type.cost)
        return (0,) * len(self.type.cost)

    @property
    def population_cost(self):
        if _source_morphs_as_train(self.unit):
            return self.type.population_cost
        return 0

    @property
    def time_cost(self):
        if _source_morphs_as_train(self.unit):
            return _morph_train_time_cost(self.unit, self.type)
        return getattr(self.type, "change_time", 0)

    def complete(self):
        player, place, x, y = (
            self.player,
            self.unit.place,
            self.unit.x,
            self.unit.y,
        )
        leave_meadow = (
            not self.unit.is_buildable_anywhere and self.type.is_buildable_anywhere
        )
        consume_meadow = (
            self.unit.is_buildable_anywhere and not self.type.is_buildable_anywhere
        )
        blocked_exit = self.unit.blocked_exit
        old_unit = self.unit
        is_lift = is_ground_host_building(old_unit) and is_flying_building_type(
            self.type
        )
        is_land = is_flying_building_unit(old_unit) and is_ground_host_building_type(
            self.type
        )
        if consume_meadow:
            if is_land:
                x, y, meadow = landing_coords_for_ground_building(
                    place, old_unit, self.type
                )
            else:
                meadow = place.find_nearest_meadow(old_unit)
                if meadow:
                    x, y = meadow.x, meadow.y
                else:
                    meadow = None
            if meadow:
                meadow.delete()
            else:
                self.unit.notify("order_impossible")
                return
        self.unit.notify("change_to,%s" % self.world.get_next_id(increment=False))
        if is_lift:
            detach_addons_for_lift(old_unit)
        old_unit.delete()
        # 直接创建新单位，不继承属性
        unit = self.type(player, place, x, y)
        if blocked_exit:
            unit.block(blocked_exit)
        # 把旧单位携带的物品转移到新单位（避免变形后物品消失）
        if hasattr(old_unit, "transfer_inventory_to"):
            old_unit.transfer_inventory_to(unit)
        if is_land:
            reattached = try_reattach_orphan_addons(unit)
            if not reattached and has_pending_orphan_addons_for_host(unit):
                unit.notify("addon_reattach_failed")
        unit.notify("complete")
        if leave_meadow:
            Meadow(place, x, y)

    @staticmethod
    def additional_condition(unit, unused_type_name):
        return not unit.orders


class BuildOrder(ComplexOrder):

    unit_menu_attribute = "can_build"
    keyword = "build"
    nb_args = 1
    
    def __init__(self, unit, args):
        super().__init__(unit, args)
        # 添加一个标记，用于跟踪资源预留状态
        self.resources_reserved = False
        
    @staticmethod
    def additional_condition(unit, type_name):
        """确保只有建筑物能被建造，不允许建造任何单位"""
        from ..definitions import rules
        unit_class = rules.unit_class(type_name)
        # 检查是否为建筑物类型，只有建筑物可以建造
        if unit_class and hasattr(unit_class, "class"):
            unit_classes = getattr(unit_class, "class")
            # 如果class是building，允许建造
            if "building" in unit_classes:
                return True
            # 否则不允许建造（包括soldier、worker等所有非建筑单位）
            else:
                return False
        return True

    def __eq__(self, other):
        # BuildOrder.id is used to make the difference between 2 successive
        # "no meadow needed" building projects on the same square. Orders
        # given for the same group and at the same "time" (same cmd_order call)
        # have the same id.
        return (
            self.__class__ == other.__class__
            and self.type == other.type
            and getattr(self.target, "id", None) == getattr(other.target, "id", None)
            and self.id == other.id
        )

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        self.addon_host = None
        if is_addon_type(self.type):
            host = self.target
            if getattr(host, "is_memory", False):
                host = host.initial_model
            if not can_host_addon(host, self.type):
                self.mark_as_impossible("cannot_build_here")
                return
            self.addon_host = host
            self.target = host
        elif self.type.is_buildable_on_exits_only:
            if not getattr(self.target, "is_an_exit", False):
                self.target = getattr(self.target, "exit", None)
                if self.target is None:
                    self.mark_as_impossible("cannot_build_here")
                    return
            if self.target.is_blocked():
                self.mark_as_impossible("cannot_build_here")
                return
        elif self.type.is_buildable_near_water_only and not getattr(
            self.target, "is_near_water", False
        ):
            self.mark_as_impossible("cannot_build_here")
            return
        elif requires_deposit_type(self.type):
            from ..worldresource import Deposit

            required_deposit = requires_deposit_type(self.type)
            deposit = None
            if isinstance(self.target, Deposit):
                deposit = self.target
            else:
                place = getattr(self.target, "place", None)
                if place is None and hasattr(self.target, "find_free_space_for"):
                    place = self.target
                deposit = deposit_on_square(place, required_deposit)
            if deposit is None or not deposit_build_target_ok(
                self.player, deposit, self.type
            ):
                self.mark_as_impossible("cannot_build_here")
                return
            self.target = deposit
        elif self.type.is_buildable_anywhere:
            land = getattr(self.target, "any_land", None)
            if land is None and hasattr(self.target, "find_free_space_for"):
                land = self.target
            self.target = land
            if self.target is None:
                self.mark_as_impossible("cannot_build_here")
                return
        else:
            if not getattr(self.target, "is_a_building_land", False):
                self.target = getattr(self.target, "building_land", None)
                if self.target is None:
                    self.mark_as_impossible("cannot_build_here")
                    return
        if not self.player.resources_are_reserved(self):
            result = self.unit.check_if_enough_resources(self.cost, self.population_cost)
            if result is not None:
                self.mark_as_impossible(result)
                return
        if (
            self.unit.next_stage(self.target) is None
            and self.target is not self.unit.place
        ):  # target must be reachable
            self.mark_as_impossible()
            return
        build_x = getattr(self.target, "x", 0)
        build_y = getattr(self.target, "y", 0)
        build_place = getattr(self.target, "place", None)
        if is_addon_type(self.type) and self.addon_host is not None:
            build_x = self.addon_host.x
            build_y = self.addon_host.y
            build_place = self.addon_host.place
        if not build_field_ok(self.player, build_place, build_x, build_y, self.type):
            required = requires_build_field_type(self.type)
            if required:
                self.mark_as_impossible(f"missing_build_field.{required}")
            else:
                self.mark_as_impossible("cannot_build_here")
            return
        self.unit.notify("order_ok")
        self.player.reserve_resources_if_needed(self)
        self.resources_reserved = True  # 标记资源已被预留

    def execute(self):
        self.update_target()
        # 额外的提前失效判定：
        # 如果是记忆对象但真实对象已被删除（或非地块），直接判定不可行，避免进入 _put_building_site
        try:
            if getattr(self.target, "is_memory", False):
                real = getattr(self.target, "initial_model", None)
                if real is None or (getattr(real, "place", None) is None and not hasattr(real, "find_free_space_for")):
                    self.mark_as_impossible()
                    return
            if self.target is not None and getattr(self.target, "place", None) is None and not hasattr(self.target, "find_free_space_for"):
                self.mark_as_impossible()
                return
        except Exception:
            pass
        if self.target is None:  # meadow already used
            self.mark_as_impossible()
            return
        if self.target is self.unit.place or self.target.place is self.unit.place:
            # 释放预留的资源，但只有在资源被预留的情况下
            if self.resources_reserved:
                self.player.free_resources(self)
                self.resources_reserved = False  # 重置标记
            
            x, _ = self.unit.place.find_free_space(self.type.airground_type, self.target.x, self.target.y)
            if x is None:
                self.cancel(unpay=False)  # 不需要返还资源，因为没有创建BuildingSite
                self.mark_as_impossible("not_enough_space")
                return
            if self.player.check_count_limit(self.type.type_name):
                # 记录建筑所在的出口
                if self.type.is_buildable_on_exits_only and hasattr(self.target, "other_side"):
                    self.type.blocked_exit = self.target
                self.unit._put_building_site(
                    self.type,
                    self.target,
                    addon_host=getattr(self, "addon_host", None),
                )
            else:
                self.cancel(unpay=False)  # 不需要返还资源，因为没有创建BuildingSite
                self.mark_as_impossible("count_limit_reached")
        elif self.unit.is_idle:
            self.move_to_or_fail(self.target)