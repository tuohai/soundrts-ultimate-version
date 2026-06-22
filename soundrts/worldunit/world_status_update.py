from ..worldorders import (
    ORDERS_DICT,
    BuildPhaseTwoOrder,
    GoOrder,
    RallyingPointOrder,
    UpgradeToOrder,
    ProducingOrder,
    StartProduceOrder,
    AutoProduceOrder,
    AutoCultivateOrder,
)
from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)
from ..worldaction import Action, AttackAction, MoveAction, MoveXYAction
from .world_public_method import *
from ..worldentity import Entity


class CreatureStatusUpdate(Entity):
    # Round 4: class-level cache defaults 避免 update 每帧 hasattr.
    # update 是单位主循环 (1.16M calls/5min); -1 作为 hash sentinel,
    # 保证首帧 hash 不等于 sentinel, 强制重建.
    _cached_inventory_hash = -1
    _cached_sorted_inventory = ()
    _cached_buffs_hash = -1
    _cached_sorted_buffs = ()

    def update(self):
        """更新单位状态"""
        # 确保坐标为整数
        self.x = int(self.x)
        self.y = int(self.y)

        """在每帧更新时检查并应用持续伤害"""
        super().update()  # 确保调用父类的update

        now = self.world.time

        # 检查近战持续伤害
        if now < self.mdg_dot_end_time and self.mdg_dot_damage > 0:
            self.receive_hit(self.mdg_dot_damage, None, notify=False)

        # 检查远程持续伤害
        if now < self.rdg_dot_end_time and self.rdg_dot_damage > 0:
            self.receive_hit(self.rdg_dot_damage, None, notify=False)
    def _update_cooldowns(self):
        for t, c in list(self._cooldowns.items()):
            if self.world.time >= c:
                del self._cooldowns[t]
                self.notify("cooldown_end,%s" % t.type_name)
    def regenerate(self):
        """生命和法力回复，支持自定义冷却时间和前摇"""
        current_time = self.world.time
        
        # 生命回复
        if self.hp_regen and self.hp < self.hp_max:
            # 检查冷却时间
            if current_time >= self.hp_regen_next_time:
                # 检查前摇时间
                hp_regen_ready = getattr(self, 'hp_regen_ready', 0)
                if hp_regen_ready > 0:
                    if current_time < self.hp_regen_prep_end_time:
                        return  # 还在前摇中
                    # 如果还没开始前摇，开始前摇
                    if self.hp_regen_prep_end_time == 0:
                        self.hp_regen_prep_end_time = current_time + hp_regen_ready
                        return
                
                # 执行生命回复
                hp_regen_cd = getattr(self, 'hp_regen_cd', 0)
                if hp_regen_cd > 0:
                    # 有冷却时间：一次性回复完整的hp_regen
                    regen_amount = self.hp_regen
                else:
                    # 无冷却时间：维持原始的每帧回复
                    regen_amount = self.hp_regen
                
                self.hp = min(self.hp_max, self.hp + regen_amount)
                
                # 设置下次回复时间
                if hp_regen_cd > 0:
                    self.hp_regen_next_time = current_time + hp_regen_cd
                self.hp_regen_prep_end_time = 0  # 重置前摇时间
        
        # 法力回复
        if self.mana_regen and self.mana < self.mana_max:
            # 检查冷却时间
            if current_time >= self.mana_regen_next_time:
                # 检查前摇时间
                mana_regen_ready = getattr(self, 'mana_regen_ready', 0)
                if mana_regen_ready > 0:
                    if current_time < self.mana_regen_prep_end_time:
                        return  # 还在前摇中
                    # 如果还没开始前摇，开始前摇
                    if self.mana_regen_prep_end_time == 0:
                        self.mana_regen_prep_end_time = current_time + mana_regen_ready
                        return
                
                # 执行法力回复
                mana_regen_cd = getattr(self, 'mana_regen_cd', 0)
                if mana_regen_cd > 0:
                    # 有冷却时间：一次性回复完整的mana_regen
                    regen_amount = self.mana_regen
                else:
                    # 无冷却时间：维持原始的每帧回复
                    regen_amount = self.mana_regen
                
                self.mana = min(self.mana_max, self.mana + regen_amount)
                
                # 设置下次回复时间
                if mana_regen_cd > 0:
                    self.mana_regen_next_time = current_time + mana_regen_cd
                self.mana_regen_prep_end_time = 0  # 重置前摇时间

    def slow_update(self):
        self.regenerate()
        # 处理资源再生
        if (hasattr(self, "resource_type") and self.resource_type and 
            hasattr(self, "resource_regen") and self.resource_regen and 
            hasattr(self, "resource_qty") and hasattr(self, "resource_volume_max")):
            
            # 检查是否是Building类型并且有资源上限
            if (getattr(self, "is_a_building", False) and self.resource_volume_max > 0 and 
                self.resource_qty < self.resource_volume_max):
                # 增加资源，但不超过最大值
                self.resource_qty = min(self.resource_qty + self.resource_regen, self.resource_volume_max)
                # 发送资源量更新通知
                self.notify(f"qty_update,{self.resource_qty}")
        
        # 如果单位正在生产资源，处理生产逻辑
        if getattr(self, "is_producing", False):
            self.update_production()
            
        # 处理is_gather=1模式下的自动生产逻辑
        elif (not getattr(self, "is_producing", False) and 
              getattr(self, "is_gather", 0) == 1):
            
            # 检查当前生产模式
            production_mode = getattr(self, "current_production_mode", None)
            
            # 检查是否同时设置了自动和手动生产/耕种
            is_auto_manual_both = False
            if (getattr(self, "auto_production", 0) == 1 and getattr(self, "manual_production", 0) == 1) or \
               (getattr(self, "auto_cultivate", 0) == 1 and getattr(self, "manual_cultivate", 0) == 1):
                is_auto_manual_both = True
                self.debug_log("检测到同时设置了自动和手动生产/耕种")
            
            # 只在自动模式下重启生产（必须明确设置为"auto"）
            if production_mode == "auto":
                # 检查是否被用户手动停止过
                user_manually_stopped = getattr(self, "_user_manually_stopped", False)
                if user_manually_stopped:
                    self.debug_log("用户已手动停止生产，不自动重启")
                    return
                
                # 检查资源是否已满
                resource_is_full = False
                if (hasattr(self, "resource_volume_max") and self.resource_volume_max > 0 and
                    hasattr(self, "resource_qty") and self.resource_qty >= self.resource_volume_max):
                    resource_is_full = True
                    self.debug_log(f"is_gather模式下资源已满({self.resource_qty}/{self.resource_volume_max})，暂停自动生产")
                
                # 只有当资源不满时，才检查是否需要重启生产
                if not resource_is_full:
                    # 检查资源是否枯竭（资源量为0）
                    resource_depleted = (hasattr(self, "resource_volume_max") and self.resource_volume_max > 0 and
                                      hasattr(self, "resource_qty") and self.resource_qty == 0)
                    
                    # 修改耕种机制：只有在资源完全枯竭时才重新耕种
                    # 对于普通自动生产，保持原有逻辑（资源不满时重启）
                    should_restart = False
                    if getattr(self, "auto_cultivate", 0) == 1:
                        # 耕种模式：只有资源完全枯竭时才重新耕种
                        should_restart = resource_depleted
                        if should_restart:
                            self.debug_log(f"耕种模式：资源已完全枯竭({self.resource_qty}/{self.resource_volume_max})，满足重新耕种条件")
                        else:
                            self.debug_log(f"耕种模式：资源未完全枯竭({self.resource_qty}/{self.resource_volume_max})，不进行耕种")
                    elif getattr(self, "auto_production", 0) == 1:
                        # 普通生产模式：如果同时设置了自动和手动模式，则只有在资源完全枯竭时才重启
                        # 如果只设置了自动模式，则在资源不满时就可以重启
                        should_restart = resource_depleted or not is_auto_manual_both
                        
                    if should_restart:
                        # 在重启生产前先检查资源是否足够
                        temp_order = StartProduceOrder(self, [])
                        production_cost = temp_order._calculate_production_cost()
                        
                        # 检查资源是否足够支付生产成本
                        result = self.check_if_enough_resources(production_cost, 0)
                        
                        if result is None:  # 资源足够
                            # 判断是普通生产还是耕种模式
                            if getattr(self, "auto_production", 0) == 1:
                                # 资源满足重启条件且有足够的资源重新启动自动生产
                                self.debug_log(f"is_gather模式下资源满足重启条件({self.resource_qty}/{self.resource_volume_max})，资源足够，重新启动自动生产")
                                temp_order = AutoProduceOrder(self, [])
                                temp_order.immediate_action()
                            
                            elif getattr(self, "auto_cultivate", 0) == 1:
                                # 资源已完全枯竭且有足够的资源重新启动自动耕种
                                self.debug_log(f"is_gather模式下资源已完全枯竭({self.resource_qty}/{self.resource_volume_max})，资源足够，重新启动自动耕种")
                                temp_order = AutoCultivateOrder(self, [])
                                temp_order.immediate_action()
                        else:
                            # 资源不足，不重新启动生产
                            self.debug_log(f"is_gather模式下满足重启条件，但资源不足无法重新启动生产: {result}")
                            # 可以选择性地通知玩家资源不足
                            if hasattr(self, "notify"):
                                self.notify(f"auto_production_blocked,{result}")
            elif production_mode is None:
                # 如果当前没有设置生产模式，记录日志但不自动启动
                # 这种情况通常发生在用户手动停止生产后
                if hasattr(self, "debug_log"):
                    self.debug_log("生产模式未设置，不自动启动生产（可能是用户手动停止了生产）")
        
        if self.time_limit is not None and self.place.world.time >= self.time_limit:
            self.on_disappear()  # 使用on_disappear而不是die，以便正确播放disappear音效
    def update_production(self):
        """更新资源生产进度"""
        if not hasattr(self, "is_producing") or not self.is_producing:
            self.debug_log(f"单位 {self.type_name}({self.id}) 不在生产状态")
            return

        # 确保生产时间不为零
        if getattr(self, "production_time", 0) <= 0:
            self.debug_log(f"生产时间为零或不存在，无法生产: {self.production_time}")
            return

        # 计算每秒应增加的进度量（因为slow_update每秒调用一次）
        # 例如：如果production_time=300秒，那么每秒增加的进度应为1
        progress_per_second = 1  # 每秒增加1点进度

        # 增加生产进度
        old_progress = self.production_progress
        # self.production_progress += VIRTUAL_TIME_INTERVAL  # 原来的代码
        self.production_progress += progress_per_second  # 每秒增加1点进度

        # 添加调试日志，帮助追踪生产进度
        progress_percent = int(self.production_progress * 100 / self.production_time)
        self.debug_log(
            f"资源生产进度: {progress_percent}%, 当前进度: {self.production_progress}/{self.production_time}, 增加: {progress_per_second}")

        # 添加进度条通知，使用与ProductionOrder类相同的机制
        self._notify_production_completeness()

        # 当进度达到生产时间时，完成生产
        if self.production_progress >= self.production_time:
            self.debug_log(f"生产进度已达到目标，准备完成生产")
            self.complete_production()

    def _notify_production_completeness(self):
        """通知生产进度，与ProductionOrder._notify_completeness逻辑一致"""
        # 确保production_time不为0
        if getattr(self, "production_time", 0) == 0:
            return

        # 计算完成度（0-10的整数）
        c = int(self.production_progress * 10 / self.production_time)
        if c > 10:  # 确保不超过10
            c = 10

        # 检查是否有_previous_completeness属性，如果没有则初始化
        if not hasattr(self, "_previous_completeness"):
            self._previous_completeness = None

        # 只有当完成度发生变化时才发送通知
        if c != self._previous_completeness:
            self.debug_log(f"发送进度条通知: completeness,{c}")
            self.notify("completeness,%s" % c)
            self._previous_completeness = c

    @staticmethod
    def _normalize_production_item_name(raw):
        if isinstance(raw, (list, tuple)):
            return raw[0] if raw else None
        return raw

    def _spawn_production_items(self, item_type_name, count):
        """在建筑旁生成可拾取物品。"""
        from ..worlditem import Item

        item_cls = self.world.unit_class(item_type_name)
        if item_cls is None or not issubclass(item_cls, Item):
            self.debug_log(f"无法生产物品：未知类型 {item_type_name}")
            return 0
        place = self.place
        spawned = 0
        for i in range(max(1, int(count))):
            offset_x = (i % 3 - 1) * 100 + 1000
            offset_y = (i // 3) * 100
            item_cls(place, self.x + offset_x, self.y + offset_y)
            spawned += 1
        return spawned

    def complete_production(self):
        """完成资源生产"""
        # 导入需要的类，确保在整个方法中可用
        from ..worldorders import ProducingOrder, StartProduceOrder
        
        if not self.player:
            self.debug_log("无法完成生产: 单位没有所属玩家")
            return

        production_item = self._normalize_production_item_name(
            getattr(self, "production_item", None)
        )
        if production_item:
            item_count = max(1, int(getattr(self, "production_qty", 1) or 1))
            spawned = self._spawn_production_items(production_item, item_count)
            self.debug_log(
                f"完成物品生产，类型：{production_item}，数量：{spawned}"
            )
            self.notify(f"produced_item,{production_item},{spawned}")
        else:
            # 获取生产的资源类型和修正后的产量（已在StartProduceOrder._update_production_parameters中设置）
            resource_type = getattr(self, "production_type", None)
            if resource_type is None:
                resource_type = "resource1"
            production_qty = getattr(self, "production_qty", 0)
            production_qty *= 1000
            self.debug_log(f"完成资源生产，类型：{resource_type}，数量：{production_qty}")

            # 检查是否需要将产出的资源添加到建筑自身 (is_gather = 1)
            if getattr(self, "is_gather", 0) == 1:
                if hasattr(self, "resource_volume_max") and self.resource_volume_max > 0:
                    if not hasattr(self, "resource_qty"):
                        self.resource_qty = 0
                    if not hasattr(self, "resource_type") or self.resource_type is None:
                        self.resource_type = resource_type
                    add_qty = production_qty // 1000
                    self.resource_qty = min(self.resource_qty + add_qty, self.resource_volume_max)
                    self.debug_log(
                        f"自身收集模式：将产出的资源添加到建筑，资源类型：{resource_type}，"
                        f"数量：{add_qty}，建筑当前资源量：{self.resource_qty}/{self.resource_volume_max}"
                    )
                    self.notify(f"qty_update,{self.resource_qty}")
                    self.notify(
                        "gathered_produced_%s,%s"
                        % (resource_type.replace("resource", ""), production_qty)
                    )
                else:
                    self.debug_log("建筑没有资源存储能力，自动切换到普通收集模式")
                    before_resources = self.player.resources[:]
                    self.player.store(resource_type, production_qty)
                    after_resources = self.player.resources[:]
                    self.debug_log(f"资源变化: {before_resources} -> {after_resources}")
                    self.notify(
                        "produced_%s,%s"
                        % (resource_type.replace("resource", ""), production_qty)
                    )
            else:
                if production_qty > 0:
                    before_resources = self.player.resources[:]
                    self.player.store(resource_type, production_qty)
                    after_resources = self.player.resources[:]
                    self.debug_log(f"资源变化: {before_resources} -> {after_resources}")
                    self.notify(
                        "produced_%s,%s"
                        % (resource_type.replace("resource", ""), production_qty)
                    )

        # 播放资源生产完成声音
        for player in self.player.world.players:
            if player is self.player:
                player.send_event(self, "resource_complete")
                
        # 根据生产模式决定是否继续生产周期
        production_mode = getattr(self, "current_production_mode", None)
        
        # 如果设置了current_production_mode，优先使用它
        if production_mode == "manual":
            # 手动生产模式下生产完成后停止生产周期
            self.is_producing = False
            self.production_progress = 0
            self._previous_completeness = None
            
            # 从命令队列中移除ProducingOrder
            for i, order in enumerate(self.orders[:]):
                if isinstance(order, ProducingOrder):
                    self.orders.pop(i)
                    break
                    
            self.debug_log("手动生产模式：生产完成，已停止生产周期，需要玩家再次点击开始生产")
        elif production_mode == "auto" or (production_mode is None and getattr(self, "manual_production", 0) != 1):
            # 如果是is_gather=1模式，检查资源是否已满，如果已满则不开始新的生产周期
            is_gather_mode = getattr(self, "is_gather", 0) == 1
            resource_is_full = False
            
            if is_gather_mode:
                if (hasattr(self, "resource_volume_max") and self.resource_volume_max > 0 and
                    hasattr(self, "resource_qty") and self.resource_qty >= self.resource_volume_max):
                    resource_is_full = True
                    
                    # 检查是否同时设置了自动和手动生产/耕种
                    is_auto_manual_both = False
                    if (getattr(self, "auto_production", 0) == 1 and getattr(self, "manual_production", 0) == 1) or \
                       (getattr(self, "auto_cultivate", 0) == 1 and getattr(self, "manual_cultivate", 0) == 1):
                        is_auto_manual_both = True
                        self.debug_log("检测到同时设置了自动和手动生产/耕种，资源满时的行为与手动生产一致")
                    
                    self.debug_log(f"is_gather模式下资源已满({self.resource_qty}/{self.resource_volume_max})，暂停自动生产")
                    # 停止生产
                    self.is_producing = False
                    self.production_progress = 0
                    self._previous_completeness = None
                    
                    # 从命令队列中移除ProducingOrder
                    for i, order in enumerate(self.orders[:]):
                        if isinstance(order, ProducingOrder):
                            self.orders.pop(i)
                            break
                    
                    # 跳过后续的资源检查和生产逻辑
                    return
            
            # 自动生产模式：检查是否有足够资源开始新的生产周期
            # 使用StartProduceOrder中的方法来计算修正后的生产成本
            temp_order = StartProduceOrder(self, [])
            production_cost = temp_order._calculate_production_cost()

            result = self.check_if_enough_resources(production_cost, 0)

            if result is None:  # 如果有足够的资源
                # 支付新的生产成本
                self.player.pay(production_cost)

                # 重置生产进度并保持生产状态
                self.production_progress = 0
                self._previous_completeness = None  # 重置进度条通知的上一次完成度
                self.debug_log("资源足够，自动开始新的生产周期")

                # 确保orders中有一个ProducingOrder
                has_producing_order = False
                for order in self.orders:
                    if isinstance(order, ProducingOrder):
                        has_producing_order = True
                        break

                if not has_producing_order:
                    # 添加新的ProducingOrder
                    producing_order = ProducingOrder(self, [])
                    self.orders.insert(0, producing_order)

                # 发送通知
                self.notify("order_ok")
            else:
                # 如果资源不足，停止生产
                self.is_producing = False
                self.production_progress = 0
                self._previous_completeness = None
                self.debug_log(f"资源不足，停止生产循环: {result}")

                # 从命令队列中移除ProducingOrder
                for i, order in enumerate(self.orders[:]):
                    if isinstance(order, ProducingOrder):
                        self.orders.pop(i)
                        break

                # 发送资源不足通知
                self.notify(result)
        else:
            # 手动生产模式（当没有设置current_production_mode但manual_production=1时）
            self.is_producing = False
            self.production_progress = 0
            self._previous_completeness = None
            
            # 从命令队列中移除ProducingOrder
            for i, order in enumerate(self.orders[:]):
                if isinstance(order, ProducingOrder):
                    self.orders.pop(i)
                    break
                    
            self.debug_log("手动生产模式：生产完成，已停止生产周期，需要玩家再次点击开始生产")
    def apply_damage_over_time(self, is_melee: bool, base_damage: int):
        """应用持续伤害效果"""
        now = self.world.time

        if is_melee and self.mdg_status_duration > 0:
            self.mdg_dot_end_time = now + int(self.mdg_status_duration * 1000)  # 转换为毫秒
            self.mdg_dot_damage = base_damage // 4  # 可以调整持续伤害比例

        elif not is_melee and self.rdg_status_duration > 0:
            self.rdg_dot_end_time = now + int(self.rdg_status_duration * 1000)
            self.rdg_dot_damage = base_damage // 4
    def update(self):
        # 仅在单位存在于游戏世界中时才进行更新
        if self.player is None:
            return

        # 确保位置坐标是整数，但避免每次转换
        # 只有在值不是整数时才进行转换
        if not isinstance(self.x, int):
            self.x = int(self.x)
        if not isinstance(self.y, int):
            self.y = int(self.y)
        if not isinstance(self.o, int):
            self.o = int(self.o)

        # 优化：缓存排序结果，避免每次update都重新排序
        # (_cached_*_hash / _cached_sorted_* 已在类体设默认值)
        current_time = self.world.time

        # 缓存库存排序 (inventory item 都是 Entity, .id 永远存在)
        inventory_hash = hash(tuple(i.id for i in self.inventory))
        if self._cached_inventory_hash != inventory_hash:
            self._cached_sorted_inventory = sorted(self.inventory, key=lambda i: i.id)
            self._cached_inventory_hash = inventory_hash

        for i in self._cached_sorted_inventory:
            if hasattr(i, "update_in_inventory"):
                i.update_in_inventory(self)

        # 缓存buff排序 (buff 有 type_name)
        buffs_hash = hash(tuple(b.type_name for b in self._buffs))
        if self._cached_buffs_hash != buffs_hash:
            self._cached_sorted_buffs = sorted(list(self._buffs), key=lambda b: b.type_name)
            self._cached_buffs_hash = buffs_hash
        
        for b in self._cached_sorted_buffs:
            if b.should_stop():
                b.stop(self)
                self._buffs.remove(b)
            else:
                b.update(self)
                if self.is_dead:
                    return

        self._update_cooldowns()

        self.is_moving = False

        # 依次处理各种行为
        if self.heal_level:
            self.heal_nearby_units()
        if self.harm_level:
            self.harm_nearby_units()
        if self.inside:
            self.inside.update()

        # 再次检查单位是否仍然存在
        if self.player is None:
            return

        # 牧羊：每帧维护跟随，避免 imperative 命令阻断 decide 后不再跟随
        if getattr(type(self), "herdable", 0) and getattr(self, "_herd_leader", None):
            self._maintain_herd_follow()

        # 执行当前动作
        if self.action:
            self.action.update()

        # 再次检查单位是否仍然存在
        if self.player is None:
            return

        # 处理命令队列
        if self.has_imperative_orders():
            # warning: completing UpgradeToOrder deletes the object
            self._execute_orders()
        else:
            self.decide()
            if not self._is_attacking() and self.orders:
                self._execute_orders()
    # update
    def has_imperative_orders(self):
        return self.orders and self.orders[0].is_imperative
    def _execute_orders(self):
        queue = self.orders
        # 批量弹出已完成/不可执行的订单，避免一帧内多次进入本函数
        while queue and (queue[0].is_complete or queue[0].is_impossible):
            queue.pop(0)
        if not queue:
            return
        # 只更新当前头部订单一次
        queue[0].update()
    def _is_attacking(self):
        return isinstance(self.action, AttackAction)

    # slow update
    def debug_log(self, message):
        """输出调试日志到文件"""
        if not hasattr(self, "player") or not self.player or not hasattr(self.player,
                                                                         "is_human") or not self.player.is_human:
            return

        try:
            import os
            import datetime
            log_dir = os.path.join(os.path.dirname(__file__), "logs")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            log_file = os.path.join(log_dir, "production_debug.log")
            with open(log_file, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"日志记录失败: {e}")
    def _raise_subsquare_threat(self, delta):
        player = self.player
        if player is None:
            return
        subsquare = self.world.get_subsquare_id_from_xy(self.x, self.y)
        for p in player.allied_vision:
            if p in player.allied:
                p.raise_threat(subsquare, delta)
    
    def _apply_single_buff(self, name, author, target):
        """对单个目标应用buff的内部方法"""
        # 获取buff类
        cls = self.world.unit_class(name)
        if cls is None:
            return False  # 如果找不到buff类，返回False

        # 检查buff是否适用于此目标
        if not hasattr(cls, 'target_type') or cls.target_type is None:
            return False  # 如果buff类没有target_type属性或为None，返回False

        from .world_public_method import has_target_type
        if has_target_type(target, cls.target_type):
            # 检查是否允许堆叠
            if cls.stack:
                n = cls.stack
                for b in target._buffs:
                    if isinstance(b, cls):
                        b.renew()
                        n -= 1
                        if n == 0:
                            return True  # 成功更新现有buff
            else:
                # 不允许堆叠，检查是否已存在
                for b in target._buffs:
                    if isinstance(b, cls):
                        return True  # buff已存在，不需要重复添加

            # 添加buff
            target._buffs.append(cls(author, target))
            return True  # 成功添加buff
        return False  # 目标类型不匹配
    
    def add_buff(self, name, author):
        """给单位或范围内的单位添加buff"""
        # 获取buff类来检查是否有范围效果
        cls = self.world.unit_class(name)
        if cls is None:
            return  # 如果找不到buff类，直接返回

        # 检查是否有范围效果
        buff_radius = getattr(cls, 'buff_radius', 0)
        
        if buff_radius > 0:
            # 有范围效果，对范围内的所有符合条件的单位应用buff
            from ..lib.nofloat import square_of_distance
            from .world_public_method import has_target_type
            
            # 确保目标单位有_buffs属性
            if not hasattr(self, '_buffs'):
                self._buffs = []
            
            # 查找范围内的所有单位
            nearby_units = self.world.get_objects2(
                self.x,
                self.y,
                buff_radius,
                filter=lambda unit: (
                    hasattr(unit, '_buffs') and  # 确保目标有_buffs属性
                    unit.is_vulnerable and  # 只对可受伤的单位生效
                    unit.place is not None and  # 确保单位在地图上
                    unit.hp > 0  # 确保单位还活着
                ),
                skip_cache=True,  # 跳过缓存，确保获取最新的单位位置
            )
            
            # 对每个符合条件的单位应用buff
            applied_count = 0
            for unit in nearby_units:
                if self._apply_single_buff(name, author, unit):
                    applied_count += 1
            
            # 记录范围buff应用的日志（可选）
            if applied_count > 0:
                try:
                    from ..lib.log import debug
                    debug(f"范围buff {name} 被应用到 {applied_count} 个单位，半径: {buff_radius}")
                except:
                    pass  # 如果日志记录失败，忽略错误
        else:
            # 没有范围效果，只对当前单位应用buff（保持原有行为）
            # 确保当前单位有_buffs属性
            if not hasattr(self, '_buffs'):
                self._buffs = []
            
            self._apply_single_buff(name, author, self)
    def apply_damage(self, damage, attacker):
        if not self.is_dead:
            self.hp -= damage
            if self.is_dead:
                self.die(attacker)

    def _notify_guard_units(self, attacker):
        """通知警戒模式的友军单位"""
        # 通知当前区域的友军
        self._notify_units_in_place(self.place, attacker)
        # 通知相邻区域的友军
        for neighbor in self.place.neighbors:
            self._notify_units_in_place(neighbor, attacker)


    def delete(self):
        Entity.delete(self)
        self.set_player(None)
    def increase_xp(self, xp):
        self.xp += xp
        self.xp_reward += xp * self.xp_reward_per_xp // PRECISION

        if (
                self.level < self.max_level
                and self.xp_thresholds  # 确保有阈值定义
                and self.level <= len(self.xp_thresholds)  # 确保当前等级不超过阈值列表长度
                and self.xp >= self.xp_thresholds[max(0, self.level - 1)]
        ):
            self.level += 1
            from ..level_up_stats import apply_level_stat_bonuses
            apply_level_stat_bonuses(self)
            if getattr(self, "level_up_reset_xp", 0):
                self.xp = 0
            self._unlock_level_skills(self.level, notify=True)
            self.notify(f"level_up,{self.type_name},{self.id},{self.level}")
    def claim_rewards(self, target):
        if target.xp_reward:
            # 检查攻击者和目标是否属于同一玩家或盟友，如果是则不分配经验值
            if (self.player is not None and target.player is not None and 
                not self.player.player_is_an_enemy(target.player)):
                return

            allied = self.player.allied if self.player is not None else []
            if self.last_player is not None:
                allied = self.last_player.allied

            # 查找可以获得经验的单位
            # strict_neighbors 在 Round 4 cached_property 优化里改成返回 tuple，
            # ``list + tuple`` 在 Python 里非法。.extend 兼容 tuple 与 list，
            # 未来若再改回 list 也不会回归。hasattr 兜底保留：target.place
            # 在极少数路径上可能没有方格邻居概念（如 zoom target），就只看本格。
            places = [target.place]
            if hasattr(target.place, 'strict_neighbors'):
                places.extend(target.place.strict_neighbors)
            units = [
                o
                for p in places
                for o in p.objects
                if o.player in allied and hasattr(o, 'xp_thresholds') and o.xp_thresholds
            ]

            if units:
                xp = target.xp_reward / len(units)
                for u in units:
                    u.increase_xp(xp)
    def on_disappear(self):
        """当召唤单位时间到期消失时调用"""
        self.notify("disappear")  # 只发送消失通知
        self.delete()  # 直接删除，不调用 die()

    heal_level = 0
    # 治疗/伤害冷却时间跟踪
    heal_next_time = 0
    harm_next_time = 0
    heal_prep_end_time = 0  # 治疗前摇结束时间
    harm_prep_end_time = 0  # 伤害前摇结束时间
    # 生命/法力回复时间跟踪
    hp_regen_next_time = 0
    mana_regen_next_time = 0
    hp_regen_prep_end_time = 0  # 生命回复前摇结束时间
    mana_regen_prep_end_time = 0  # 法力回复前摇结束时间
    
    def heal_nearby_units(self):
        """治疗附近的单位，支持自定义范围和冷却时间"""
        # 检查冷却时间
        current_time = self.world.time
        if current_time < self.heal_next_time:
            return
            
        # 检查前摇时间
        if self.heal_ready > 0:
            if current_time < self.heal_prep_end_time:
                return
            # 如果还没开始前摇，开始前摇
            if self.heal_prep_end_time == 0:
                self.heal_prep_end_time = current_time + self.heal_ready
                return
        
        # 治疗量计算：如果有冷却时间则一次治疗完整量，否则按原始逻辑
        heal_cd = getattr(self, 'heal_cd', 0)
        if heal_cd > 0:
            # 有冷却时间：一次性治疗完整的heal_level
            hp = self.heal_level * PRECISION
        else:
            # 无冷却时间：维持原始的分帧治疗逻辑（每25帧治疗完整量）
            hp = self.heal_level * PRECISION // 25
        

        
        # 使用自定义的治疗范围
        heal_radius = getattr(self, 'heal_radius', 0)
        heal_range = getattr(self, 'heal_range', 0)
        
        # 如果设置了单体射程，使用瞄准模式
        if heal_range > 0:
            # 单体瞄准治疗模式
            self._heal_targeted_unit(hp, heal_range)
        else:
            # 范围治疗模式
            self._heal_area_units(hp, heal_radius)
        
        # 设置下次治疗时间（如果heal_cd为0则不设置冷却）
        if heal_cd > 0:
            self.heal_next_time = current_time + heal_cd
        self.heal_prep_end_time = 0  # 重置前摇时间
        
    def _heal_area_units(self, hp, radius):
        """范围治疗模式"""
        units = self.world.get_objects2(
            self.x,
            self.y,
            radius,
            filter=lambda x: (
                x.hp < x.hp_max and 
                self._can_heal(x)  # 使用heal_target_type检查
            ),
        )
        
        # 去重：确保每个单位只被治疗一次
        unique_units = []
        unit_ids = set()
        for u in units:
            if id(u) not in unit_ids:
                unique_units.append(u)
                unit_ids.add(id(u))
        

        
        for u in unique_units:
            u.hp = min(u.hp_max, u.hp + hp)
            
    def _heal_targeted_unit(self, hp, range_limit):
        """单体瞄准治疗模式"""
        # 查找最近的受伤友军单位
        from ..lib.nofloat import square_of_distance
        
        best_target = None
        best_distance = float('inf')
        
        # 在稍大范围内搜索目标
        search_radius = max(range_limit * 2, 10 * PRECISION)
        units = self.world.get_objects2(
            self.x,
            self.y,
            search_radius,
            filter=lambda x: (
                x.hp < x.hp_max and 
                self._can_heal(x)  # 使用heal_target_type检查
            ),
        )
        
        # 找到射程内最近的受伤单位
        for u in units:
            distance = square_of_distance(self.x, self.y, u.x, u.y)
            max_distance = (range_limit + self.radius + u.radius) ** 2
            
            if distance <= max_distance and distance < best_distance:
                best_target = u
                best_distance = distance
        
        # 治疗目标
        if best_target:
            best_target.hp = min(best_target.hp_max, best_target.hp + hp)
    
    heal_target_type = ()
    def _can_heal(self, other):
        """检查是否可以治疗目标单位"""
        # 基本条件：目标必须是可治疗的友军单位
        if not getattr(other, 'is_healable', True):
            return False
        
        # 治疗不能治疗建筑，建筑需要repair
        if hasattr(other, 'is_a_building') and other.is_a_building:
            return False
        
        # 必须是友军（包括自己）
        if hasattr(other, 'player') and hasattr(self, 'player'):
            if self.player.player_is_an_enemy(other.player):
                return False
        
        # 如果没有heal_target_type定义，默认可以治疗任何友军单位（除了建筑）
        if not self.heal_target_type:
            return True

        from .world_public_method import matches_heal_targets

        return matches_heal_targets(other, self.heal_target_type)
    harm_target_type = ()
    def _can_harm(self, other):
        # 如果没有harm_target_type定义，默认可以伤害任何单位
        if not self.harm_target_type:
            return True

        from .world_public_method import passes_harm_diplomacy_filter

        if not passes_harm_diplomacy_filter(
            self.harm_target_type,
            getattr(self, "player", None),
            getattr(other, "player", None),
        ):
            return False

        # 检查water类型（world.can_harm将water归类为ground，我们需要单独支持）
        if "water" in self.harm_target_type:
            target_airground_type = getattr(other, 'airground_type', 'ground')
            if target_airground_type == 'water':
                return True

        # 使用world.can_harm来检查其他所有类型（building, unit, ground, air, healable, undead, 具体类型名等）
        return self.world.can_harm(self.type_name, other.type_name)
    def harm_nearby_units(self):
        """对周围单位造成伤害，支持自定义范围和冷却时间

        根据harm_target_type确定可以伤害的目标类型:
        - enemy / non_neutral: 只伤害非中立敌对玩家单位
        - neutral: 只伤害中立玩家单位
        - allied: 只伤害盟友
        - building: 只伤害建筑
        - unit: 只伤害单位
        - [unit_type_name]: 只伤害指定类型的单位

        如果没有设置harm_target_type，则伤害所有单位
        
        注意：此方法直接应用伤害，不经过攻击系统的复杂处理
        """
        # 检查冷却时间
        current_time = self.world.time
        if current_time < self.harm_next_time:
            return
            
        # 检查前摇时间
        if self.harm_ready > 0:
            if current_time < self.harm_prep_end_time:
                return
            # 如果还没开始前摇，开始前摇
            if self.harm_prep_end_time == 0:
                self.harm_prep_end_time = current_time + self.harm_ready
                return
        
        # 伤害量计算：如果有冷却时间则一次伤害完整量，否则按原始逻辑
        harm_cd = getattr(self, 'harm_cd', 0)
        if harm_cd > 0:
            # 有冷却时间：一次性造成完整的harm_level伤害
            hp = self.harm_level * PRECISION
        else:
            # 无冷却时间：维持原始的分帧伤害逻辑（每25帧伤害完整量）
            hp = self.harm_level * PRECISION // 25
        
        # 使用自定义的伤害范围
        harm_radius = getattr(self, 'harm_radius', 0)
        harm_range = getattr(self, 'harm_range', 0)
        
        # 如果设置了单体射程，使用瞄准模式
        if harm_range > 0:
            # 单体瞄准伤害模式
            self._harm_targeted_unit(hp, harm_range)
        else:
            # 范围伤害模式
            self._harm_area_units(hp, harm_radius)
        
        # 设置下次伤害时间（如果harm_cd为0则不设置冷却）
        if harm_cd > 0:
            self.harm_next_time = current_time + harm_cd
        self.harm_prep_end_time = 0  # 重置前摇时间
        
    def _harm_area_units(self, hp, radius):
        """范围伤害模式"""
        units = self.world.get_objects2(
            self.x,
            self.y,
            radius,
            filter=lambda x: x.is_vulnerable and self._can_harm(x),
            skip_cache=True,
        )
        
        # 去重：确保每个单位只被伤害一次
        unique_units = []
        unit_ids = set()
        for u in units:
            if id(u) not in unit_ids:
                unique_units.append(u)
                unit_ids.add(id(u))
        
        for u in unique_units:
            # 直接应用伤害，不通过攻击系统
            if u.player is None or u.hp <= 0:
                continue

            # 条约期内拦截敌对AOE伤害
            try:
                if getattr(self.world, 'treaty_until_time', 0) > 0 and self.world.time < self.world.treaty_until_time:
                    if hasattr(self, 'player') and hasattr(u, 'player') and self.player and u.player:
                        if u.player.player_is_an_enemy(self.player):
                            continue
            except Exception:
                pass

            # 记录攻击者用于观察
            if u.player:
                u.player.observe(self)
                u.last_attacker = self

            # 与1.3.8.1一致：直接扣血且不发送受伤/害伤害通知，减少事件与音频
            # 若为编队单位，则此扣血会自动由聚合血量折算为士兵伤亡
            u.hp -= hp

            # 处理死亡
            if u.hp <= 0:
                u.die(self)
                
    def _harm_targeted_unit(self, hp, range_limit):
        """单体瞄准伤害模式"""
        # 查找最近的敌方单位
        from ..lib.nofloat import square_of_distance
        
        best_target = None
        best_distance = float('inf')
        
        # 在稍大范围内搜索目标
        search_radius = max(range_limit * 2, 10 * PRECISION)
        units = self.world.get_objects2(
            self.x,
            self.y,
            search_radius,
            filter=lambda x: x.is_vulnerable and self._can_harm(x),
            skip_cache=True,
        )
        
        # 找到射程内最近的敌方单位
        for u in units:
            distance = square_of_distance(self.x, self.y, u.x, u.y)
            max_distance = (range_limit + self.radius + u.radius) ** 2
            
            if distance <= max_distance and distance < best_distance:
                best_target = u
                best_distance = distance
        
        # 伤害目标
        if best_target:
            # 直接应用伤害，不通过攻击系统
            if best_target.player is None or best_target.hp <= 0:
                return

            # 条约期内拦截敌对单体伤害
            try:
                if getattr(self.world, 'treaty_until_time', 0) > 0 and self.world.time < self.world.treaty_until_time:
                    if hasattr(self, 'player') and hasattr(best_target, 'player') and self.player and best_target.player:
                        if best_target.player.player_is_an_enemy(self.player):
                            return
            except Exception:
                pass

            # 记录攻击者用于观察
            if best_target.player:
                best_target.player.observe(self)
                best_target.last_attacker = self

            if getattr(best_target, "_has_yielded", False):
                return

            # 与1.3.8.1一致：直接扣血且不发送受伤/害伤害通知
            best_target.hp -= hp

            # 处理死亡
            if best_target.hp <= 0:
                best_target.die(self)

    def can_be_captured(self):
        """检查单位是否可以被夺取"""
        return (self.capture_hp_threshold > 0 and
                self.hp > 0 and
                (self.hp * 100 / self.hp_max) <= self.capture_hp_threshold)

