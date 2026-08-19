from .base import BasicOrder


def _target_has_gatherable_resource(target):
    """True if workers can still extract from this deposit/building."""
    if target is None:
        return False
    if getattr(target, "is_an_extractor", 0):
        from ..world_extractor import extractor_can_still_yield

        return extractor_can_still_yield(target)
    if hasattr(target, "resource_qty"):
        return target.resource_qty > 0
    return True


class GatherOrder(BasicOrder):

    keyword = "gather"
    nb_args = 1

    storage = None
    
    @property
    def title(self):
        from ..definitions import style
        return style.get(self.keyword, "title") or [102]
    
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        """检查单位是否可以使用gather命令"""
        # 首先检查基本技能
        if cls.keyword not in unit.basic_skills:
            return False
        
        from ..worldunit.worldworker import Worker
        return Worker.has_gather_permissions(unit)
    
    def __init__(self, unit, args):
        super().__init__(unit, args)
        self.delay = 0  # 初始化delay属性
        self.mode = None  # 初始化mode属性

    def on_queued(self):
        from ..worldresource import Deposit

        self.target = self.player.get_object_by_id(self.args[0])
        if not (isinstance(self.target, Deposit) or
                (hasattr(self.target, "is_a_building") and
                 self.target.is_a_building and 
                 hasattr(self.target, "resource_type") and 
                 self.target.resource_type)):
            self.mark_as_impossible()
            return
            
        # 检查资源是否耗尽（气矿萃取建筑看气泉储量，不是建筑缓冲仓）
        if not _target_has_gatherable_resource(self.target):
            self.mark_as_impossible()
            return
            
        from ..worldunit.worldworker import Worker
        if not Worker.has_gather_permissions(self.unit):
            self.mark_as_impossible()
            self.unit.notify("cannot_gather_any_resource_type")
            return
        if not self.unit._can_gather_target(self.target):
            from ..worldorders.base import _terrain_impassable_reason

            place = Worker._gather_target_place(self.target)
            reason = _terrain_impassable_reason(self.unit, place) if place else None
            self.mark_as_impossible()
            if reason:
                self.unit.notify(f"order_impossible,{reason}")
            else:
                self.unit.notify("cannot_gather_this_resource_type")
            return
                
        self.unit.notify("order_ok")
        self.mode = None

    def _store_cargo(self):
        # 检查cargo是否有效
        if self.unit.cargo is None:
            self.mode = "go_gather"
            return
            
        # 确保cargo是一个有效的元组，包含资源类型和数量
        if not isinstance(self.unit.cargo, tuple) or len(self.unit.cargo) != 2:
            self.unit.cargo = None
            self.mode = "go_gather"
            return
            
        # 确保资源类型和数量都不是None
        resource_type, qty = self.unit.cargo
        if resource_type is None or qty is None:
            self.unit.cargo = None
            self.mode = "go_gather"
            return
            
        # 直接存储资源，无需进行转换
        # 因为资源在提取时已经是内部单位(1000)，存储时应该保持一致
        self.player.store(resource_type, qty)
        self.unit.cargo = None

    def _extract_cargo(self):
        # 使用工人的gather_qty属性并考虑Deposit的extraction_qty
        # gather_qty方法返回的是基础单位数量，需要乘以1000转换为游戏内部资源单位
        from ..lib.nofloat import PRECISION

        gather_qty = self.unit.get_gather_qty(self.target.resource_type, self.target) * PRECISION
        
        # 提取资源并获取返回值
        extracted_qty = self.target.extract_resource(gather_qty)
        
        # 检查返回值，如果为0表示资源已耗尽
        if extracted_qty == 0:
            # 资源已耗尽，将目标设为None以触发资源耗尽逻辑
            self.target = None
            # 清空工人的货物
            self.unit.cargo = None
            return
            
        # 资源正常提取，设置工人的货物
        self.unit.cargo = (self.target.resource_type, extracted_qty)
        try:
            self.unit.notify("gather,%s" % self.target.resource_type)
        except Exception:
            pass

    def _cargo_amount(self):
        if self.unit.cargo is None:
            return 0
        if not isinstance(self.unit.cargo, tuple) or len(self.unit.cargo) != 2:
            return 0
        return int(self.unit.cargo[1] or 0)

    def _continuous_carry_cap_internal(self):
        from ..lib.nofloat import PRECISION

        cap = self.unit.get_carry_capacity(self.target.resource_type, self.target)
        return max(PRECISION, int(cap) * PRECISION)

    def _add_to_cargo(self, resource_type, amount_internal):
        if amount_internal <= 0:
            return
        if self.unit.cargo is None:
            self.unit.cargo = (resource_type, amount_internal)
        else:
            cur_type, cur_qty = self.unit.cargo
            if cur_type != resource_type:
                # 换资源类型：先视为应送回；此处覆盖
                self.unit.cargo = (resource_type, amount_internal)
            else:
                self.unit.cargo = (resource_type, int(cur_qty) + amount_internal)

    def _continuous_gather_tick(self):
        """AoE2-style: accumulate at gather_rate until carry_capacity, then return."""
        from ..lib.nofloat import PRECISION

        if self.target is None:
            if self._cargo_amount() > 0:
                self.mode = "bring_back"
                self.storage = None
            else:
                self.mark_as_complete()
            return
        if not _target_has_gatherable_resource(self.target):
            if self._cargo_amount() > 0:
                self.mode = "bring_back"
                self.storage = None
            else:
                self.mark_as_complete()
                self.unit.deploy()
            return
        if not self.unit._near_enough(self.target):
            self.mode = "go_gather"
            self.unit.stop()
            self._cont_last_t = None
            return

        now = self.unit.place.world.time
        if getattr(self, "_cont_last_t", None) is None:
            self._cont_last_t = now
            self._cont_accum = getattr(self, "_cont_accum", 0.0) or 0.0
            return

        dt = (now - self._cont_last_t) / 1000.0
        self._cont_last_t = now
        if dt <= 0:
            return

        rate = float(self.unit.get_gather_rate(self.target.resource_type, self.target))
        # AI gather_time percent: lower percent → faster (same as trip mode)
        player = getattr(self.unit, "player", None)
        pct = getattr(player, "ai_gather_time_percent", 100) if player else 100
        if pct and pct != 100:
            if pct <= 0:
                rate *= 10.0
            else:
                rate *= 100.0 / float(pct)

        self._cont_accum = float(getattr(self, "_cont_accum", 0.0) or 0.0)
        self._cont_accum += rate * PRECISION * dt

        cap = self._continuous_carry_cap_internal()
        current = self._cargo_amount()
        room = cap - current
        if room <= 0:
            self.mode = "bring_back"
            self.storage = None
            self._cont_last_t = None
            return

        take = int(self._cont_accum)
        if take < 1:
            return
        take = min(take, room)
        extracted = self.target.extract_resource(take)
        self._cont_accum -= extracted
        if extracted <= 0:
            if self._cargo_amount() > 0:
                self.mode = "bring_back"
                self.storage = None
            else:
                self.target = None
                self.mark_as_complete()
            self._cont_last_t = None
            return

        had = current
        self._add_to_cargo(self.target.resource_type, extracted)
        if had == 0:
            try:
                self.unit.notify("gather,%s" % self.target.resource_type)
            except Exception:
                pass

        # AoE2 Paper Money: lumberjacks generate gold while chopping wood
        self._apply_gather_byproduct(dt, extracted)

        if self._cargo_amount() >= cap:
            self.mode = "bring_back"
            self.storage = None
            self._cont_last_t = None
            return

        # Deposit may have died mid-tick after extract
        if self.target is None or not _target_has_gatherable_resource(self.target):
            if self._cargo_amount() > 0:
                self.mode = "bring_back"
                self.storage = None
            self._cont_last_t = None

    def _apply_gather_byproduct(self, dt, gathered=0):
        """While gathering, grant byproduct resources (e.g. Paper Money gold/s on wood)."""
        from ..lib.nofloat import PRECISION
        from ..worldmarket import (
            resource_or_type_key,
            unpack_gather_byproduct_entry,
        )

        byproduct = getattr(self.unit, "gather_byproduct", None)
        if not isinstance(byproduct, dict) or not byproduct or (dt <= 0 and not gathered):
            return
        player = getattr(self.unit, "player", None)
        if player is None or self.target is None:
            return
        entry = None
        for tok in (
            getattr(self.target, "type_name", None),
            getattr(self.target, "resource_type", None),
        ):
            if not tok:
                continue
            if tok in byproduct:
                entry = byproduct[tok]
                break
            key = resource_or_type_key(tok)
            if key and key in byproduct:
                entry = byproduct[key]
                break
        if entry is None:
            return
        rate_f, product, mode = unpack_gather_byproduct_entry(entry)
        if rate_f <= 0:
            return
        acc = float(getattr(self, "_byproduct_accum", 0.0) or 0.0)
        if mode == "per_food":
            acc += rate_f * (float(gathered) / float(PRECISION or 1))
        else:
            acc += rate_f * dt
        whole = int(acc)
        if whole >= 1:
            player.store(product, whole * PRECISION)
            acc -= whole
        self._byproduct_accum = acc

    def _handle_water_unit_transport(self):
        """处理水上单位的资源运输：先移动到最佳岸边位置，然后将资源运输到相邻陆地的仓库"""
        if self.unit.cargo is None:
            self.mode = "go_gather"
            return
            
        # 首先尝试寻找水上仓库（如果有的话）
        water_storage = self._find_water_storage()
        if water_storage is not None:
            self.storage = water_storage
            # 使用标准的陆地单位存储逻辑
            if self.unit._near_enough(self.storage):
                self.mode = "store"
                self.storage.notify("store,%s" % self.unit.cargo[0])
                self.delay = self.unit.place.world.time + 1000  # 1 second
                self.unit.stop()
            elif self.unit.is_idle:
                self.unit.start_moving_to(self.storage)
                if self.unit.is_idle:
                    self.storage = None
            return
            
        # 不使用就近原则，而是寻找最佳岸边位置
        if not hasattr(self, 'shore_target'):
            self.shore_target = None
            
        if self.shore_target is None:
            self.shore_target = self._find_best_shore_for_storage()
            if self.shore_target is None:
                # 没有找到合适的岸边位置，任务失败
                self.unit.cargo = None
                self.mark_as_impossible()
                return
                
        # 移动到最佳岸边位置
        if not self.unit._near_enough(self.shore_target):
            if self.unit.is_idle:
                self.unit.start_moving_to(self.shore_target)
        else:
            # 到达最佳岸边位置，处理资源存储
            self.shore_target = None
            # 现在在最佳岸边位置，寻找相邻陆地的仓库
            land_storage = self._find_adjacent_land_storage()
            if land_storage is not None:
                self._store_cargo_to_land_storage(land_storage)
            else:
                # 没有找到合适的仓库，任务失败
                self.unit.cargo = None
                self.mark_as_impossible()

    def _find_adjacent_land_storage(self):
        """寻找相邻陆地方格上的仓库"""
        if self.unit.cargo is None:
            return None
            
        resource_type = self.unit.cargo[0]
        current_place = self.unit.place
        
        # 收集相邻陆地方格上的仓库
        land_storages = []
        
        for neighbor in current_place.strict_neighbors:
            # 检查是否是陆地方格
            if (not getattr(neighbor, 'is_water', True) and 
                getattr(neighbor, 'is_ground', False)):
                
                # 在该陆地方格中寻找仓库
                for obj in neighbor.objects:
                    if self._is_suitable_land_storage(obj, resource_type):
                        # 计算距离（使用简单的直线距离）
                        from ..lib.nofloat import int_distance
                        distance = int_distance(self.unit.x, self.unit.y, obj.x, obj.y)
                        land_storages.append((distance, obj))
        
        # 返回最近的仓库
        if land_storages:
            land_storages.sort()
            return land_storages[0][1]
            
        return None

    def _store_cargo_to_land_storage(self, storage):
        """直接将货物存储到陆地仓库"""
        if self.unit.cargo is None:
            self.mode = "go_gather"
            return
            
        # 获取资源类型用于通知
        resource_type = self.unit.cargo[0]
        
        # 存储资源
        self._store_cargo()
        
        # 通知资源已存储（音效在仓库位置播放）
        storage.notify("store,%s" % resource_type)
        
        # 返回采集模式
        self.mode = "go_gather"


    def _is_near_shore(self):
        """检查当前位置是否靠近岸边"""
        current_place = self.unit.place
        if not getattr(current_place, 'is_water', False):
            return False
            
        # 检查相邻方格是否有陆地
        for neighbor in current_place.strict_neighbors:
            if (not getattr(neighbor, 'is_water', True) and 
                getattr(neighbor, 'is_ground', False)):
                return True
        return False

    def _find_best_shore_for_storage(self):
        """寻找能够访问到陆地仓库的最佳岸边位置"""
        if self.unit.cargo is None:
            return None
            
        resource_type = self.unit.cargo[0]
        current_place = self.unit.place
        
        # 首先寻找所有可能的陆地仓库
        all_land_storages = []
        for p in self.player.allied:
            for u in p.units:
                if self._is_suitable_land_storage(u, resource_type):
                    all_land_storages.append(u)
        
        if not all_land_storages:
            # 没有找到陆地仓库，返回None表示失败
            return None
        
        # 寻找能够访问到这些仓库的岸边位置
        shore_candidates = []
        
        # 遍历所有陆地仓库，寻找它们附近的岸边位置
        for storage in all_land_storages:
            storage_place = storage.place
            
            # 检查仓库周围的方格，寻找相邻的水域
            for neighbor in storage_place.strict_neighbors:
                if getattr(neighbor, 'is_water', False):
                    # 这是仓库相邻的水域位置
                    # 检查水上单位是否可以到达这个位置
                    water_distance = neighbor.shortest_path_distance_to(current_place, self.player, "water")
                    if water_distance is not None:
                        from ..worldroom import ZoomTarget
                        shore_point = ZoomTarget(neighbor, neighbor.x, neighbor.y)
                        shore_candidates.append((water_distance, shore_point, storage))
        
        # 如果没有找到直接相邻的岸边位置，扩大搜索范围
        if not shore_candidates:
            # 搜索所有水域位置，寻找能够到达陆地仓库的位置
            all_water_places = []
            for place in self.unit.world.squares:
                if getattr(place, 'is_water', False):
                    # 检查这个水域位置是否可以从当前位置到达
                    water_distance = place.shortest_path_distance_to(current_place, self.player, "water")
                    if water_distance is not None:
                        all_water_places.append((water_distance, place))
            
            # 对所有水域位置按距离排序
            all_water_places.sort(key=lambda x: x[0])
            
            # 检查每个水域位置，看是否能够访问到陆地仓库
            for water_distance, water_place in all_water_places:
                for neighbor in water_place.strict_neighbors:
                    if (not getattr(neighbor, 'is_water', True) and 
                        getattr(neighbor, 'is_ground', False)):
                        # 这是一个陆地方格，检查是否有仓库
                        for obj in neighbor.objects:
                            if obj in all_land_storages:
                                from ..worldroom import ZoomTarget
                                shore_point = ZoomTarget(water_place, water_place.x, water_place.y)
                                shore_candidates.append((water_distance, shore_point, obj))
                                break
                        # 如果已经找到了一些候选位置，可以停止搜索以提高性能
                        if len(shore_candidates) >= 5:
                            break
                if len(shore_candidates) >= 5:
                    break
        
        # 选择最近的能够访问仓库的岸边位置
        if shore_candidates:
            shore_candidates.sort(key=lambda x: x[0])  # 按距离排序
            return shore_candidates[0][1]  # 返回岸边点
            
        # 如果仍然没有找到合适的岸边位置，返回None表示失败
        return None

    def _find_water_storage(self):
        """寻找水上的仓库（如果有的话）"""
        resource_type = self.unit.cargo[0]
        
        for p in self.player.allied:
            for u in p.units:
                # 检查是否是水上建筑物且能存储该类型资源
                if (getattr(u, 'airground_type', None) == "water" and
                    hasattr(u, 'storable_resource_types') and
                    resource_type in u.storable_resource_types):
                    
                    # 检查是否可达
                    distance = self.unit.place.shortest_path_distance_to(u.place, self.player, "water")
                    if distance is not None:
                        return u
        return None


    def _is_suitable_land_storage(self, unit, resource_type):
        """检查单位是否是合适的陆地仓库"""
        # 基本检查：必须能存储该类型资源
        if resource_type not in getattr(unit, 'storable_resource_types', []):
            return False
            
        # 必须是陆地或空中单位（不是水上单位）
        if getattr(unit, 'airground_type', 'ground') == "water":
            return False
            
        # 不能在建筑物内部
        if getattr(unit, 'is_inside', False):
            return False
            
        # 必须是建筑物或者具有存储能力的单位
        if not (getattr(unit, 'is_a_building', False) or 
                hasattr(unit, 'storable_resource_types')):
            return False
            
        # 检查是否在陆地上
        unit_place = getattr(unit, 'place', None)
        if unit_place is None:
            return False
            
        # 确保仓库在陆地方格中
        if getattr(unit_place, 'is_water', False):
            return False
            
        return True

    def execute(self):
        if self.mode is None:
            if self.unit.cargo is not None:  # cargo from previous orders
                self.mode = "bring_back"
            else:
                self.mode = "go_gather"
        self.update_target()
        if self.mode == "bring_back":
            # 首先检查cargo是否为None，如果为None则切换到go_gather模式
            if self.unit.cargo is None:
                self.mode = "go_gather"
                return
                
            # 特殊处理水上单位：需要跨地形运输资源
            if getattr(self.unit, 'airground_type', None) == "water":
                self._handle_water_unit_transport()
                return
                
            if self.storage is None:
                self.storage = self.player.nearest_warehouse(
                    self.unit.place, self.unit.cargo[0]
                )
                if self.storage is None:
                    # 没有可存储该资源的建筑（市政厅/伐木场等）时不能入库；
                    # 保留货物，稍后仓库建成后再送回。
                    if not getattr(self, "_notified_no_warehouse", False):
                        self._notified_no_warehouse = True
                        self.unit.notify("order_impossible")
                    self.unit.stop()
                    return
                self._notified_no_warehouse = False
                self.unit.start_moving_to(self.storage)
            elif self.unit._near_enough(self.storage):
                self.mode = "store"
                self.storage.notify("store,%s" % self.unit.cargo[0])
                self.delay = self.unit.place.world.time + 1000  # 1 second
                self.unit.stop()
            elif self.unit.is_idle:
                self.unit.start_moving_to(self.storage)
                if self.unit.is_idle:
                    self.storage = None  # find a new storage
        elif self.mode == "store":
            if self.unit.place.world.time > self.delay:
                self._store_cargo()
                self.mode = "go_gather"
        elif self.mode == "go_gather":
            if self.target is None:  # resource exhausted
                self.mark_as_complete()
                self.unit.deploy()
            elif not _target_has_gatherable_resource(self.target):
                self.mark_as_complete()
                self.unit.deploy()
            elif self.unit._near_enough(self.target):
                from ..world_extractor import gather_slot_available

                # StarCraft gas: only gather_slots workers extract at once; extras wait.
                if not gather_slot_available(self.target, self.unit):
                    self.unit.stop()
                    return
                continuous = False
                try:
                    continuous = bool(self.unit.uses_continuous_gather())
                except Exception:
                    continuous = False
                self.mode = "gather"
                self.unit.stop()
                if continuous:
                    self._cont_last_t = self.unit.place.world.time
                    self._cont_accum = float(getattr(self, "_cont_accum", 0.0) or 0.0)
                    self.delay = 0
                else:
                    # 使用工人的gather_time属性并考虑Deposit的extraction_time
                    # gather_time方法返回的是秒，需要乘以1000转换为毫秒
                    gather_time = self.unit.get_gather_time(self.target.resource_type, self.target) * 1000
                    self.delay = self.unit.place.world.time + gather_time
            elif self.unit.is_idle:
                self.move_to_or_fail(self.target)
        elif self.mode == "gather":
            continuous = False
            try:
                continuous = bool(self.unit.uses_continuous_gather())
            except Exception:
                continuous = False
            if continuous:
                self._continuous_gather_tick()
            elif self.target is None:  # resource exhausted
                self.mark_as_complete()
            elif not _target_has_gatherable_resource(self.target):
                self.mark_as_complete()
            elif not self.unit._near_enough(self.target):
                self.mode = "go_gather"
                self.unit.stop()
            elif self.unit.place.world.time > self.delay:
                self._extract_cargo()
                self.mode = "bring_back"
                self.storage = None