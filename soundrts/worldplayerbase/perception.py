"""玩家视野、感知和记忆系统模块"""

import copy
import os
from typing import Union, List

from ..lib.log import warning
from ..worldroom import Square
from ..worldexit import Exit
from ..worldresource import Corpse, Deposit
from ..open_container import (
    container_visible_from_place,
    exit_blocker_visible_from_observed_squares,
    is_open_container,
)
from .base import A

# D-Phase 1 T2: known_enemies 内层 Cython 化 (失败 fallback 到 Python).
_fast = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import perception_fast as _fast  # type: ignore[no-redef]
    except ImportError:
        _fast = None

# 算法优化模式：专注于减少计算量而非加速单次计算


class PerceptionMixin:
    """视野、感知和记忆相关的方法混入类"""

    def _open_container_passenger_visible(self, unit):
        if not getattr(unit, "is_inside", False):
            return False
        container = getattr(getattr(unit, "place", None), "container", None)
        if not is_open_container(container):
            return False
        observed = self.observed_squares
        for sq in observed:
            if container_visible_from_place(container, sq):
                return True
        return False

    def _exit_blocker_visible(self, unit):
        return exit_blocker_visible_from_observed_squares(unit, self.observed_squares)

    def raise_threat(self, subsquare, delta):
        try:
            self._subsquare_threat[subsquare] += delta
        except:
            self._subsquare_threat[subsquare] = delta

    def _get_threat(self, subsquare):
        try:
            return self._subsquare_threat[subsquare]
        except:
            return 0

    def get_safest_subsquare(self, place):
        x = place.x * 3 // self.world.square_width
        y = place.y * 3 // self.world.square_width
        candidates = list((x + dx, y + dy) for dx in (0, 1, -1) for dy in (0, 1, -1))
        sub = sorted(candidates, key=self._get_threat)[0]
        return (
            sub[0] * self.world.square_width // 3 + self.world.square_width // 6,
            sub[1] * self.world.square_width // 3 + self.world.square_width // 6,
        )

    def known_enemies(self, place):
        """获取指定位置的已知敌人 - 优化版: 直接属性访问, 无 hasattr/getattr.

        所有缓存属性 (_known_enemies, _known_enemies_time, _enemy_units_cache,
        _enemy_units_cache_time, _cached_enemy_players, _enemy_players_cache_time,
        _enemy_units_set, _enemy_units_set_time, _perception_set,
        _perception_set_time) 已在 Player.__init__ 预初始化.
        place.objects / obj.place.is_inside_place 由 class-level 默认值兜底.

        实测: 此函数 17.9M calls / 5min cw1 大乱斗, 原版每次 4-5 个 hasattr/getattr
        是 cProfile 中 hasattr 4.74 亿次的主要贡献者之一.
        """
        # 过场单位 / 已删除位置可能传入 place=None; 此时无 objects 可枚举,
        # 直接返回空列表, 避免 place.objects 抛 AttributeError.
        if place is None:
            return []

        current_time = self.world.time
        if current_time - self._enemy_units_cache_time > 250:
            if current_time - self._enemy_players_cache_time > 1000:
                self._cached_enemy_players = [
                    p for p in self.world.players if self.player_is_a_hostile_enemy(p)
                ]
                self._enemy_players_cache_time = current_time
            cache = []
            for e in self._cached_enemy_players:
                cache.extend(e.units)
            self._enemy_units_cache = cache
            self._enemy_units_cache_time = current_time

        # 本帧未计算则重建
        known_time = self._known_enemies_time.get(place)
        if known_time != current_time:
            # 每 tick 级集合缓存
            if self._enemy_units_set_time == current_time:
                enemy_units_set = self._enemy_units_set
            else:
                enemy_units_set = set(self._enemy_units_cache)
                self._enemy_units_set = enemy_units_set
                self._enemy_units_set_time = current_time

            if self._perception_set_time == current_time:
                perceived_set = self._perception_set
            else:
                perceived_set = set(self.perception)
                self._perception_set = perceived_set
                self._perception_set_time = current_time

            # D-Phase 1 T2: 内层 Cython 化 (22M calls / 5min).
            if _fast is not None:
                result = _fast.filter_visible_vulnerable_enemies(
                    place.objects, perceived_set, enemy_units_set
                )
            else:
                result = []
                for obj in place.objects:
                    if (
                        obj in perceived_set
                        and obj in enemy_units_set
                        and obj.is_vulnerable
                    ):
                        op = obj.place
                        if op is None or not op.is_inside_place:
                            result.append(obj)
                for obj in enemy_units_set:
                    if (
                        obj.is_vulnerable
                        and getattr(obj, "is_inside", False)
                        and obj not in result
                    ):
                        container = getattr(getattr(obj, "place", None), "container", None)
                        if container_visible_from_place(container, place):
                            result.append(obj)
            self._known_enemies[place] = result
            self._known_enemies_time[place] = current_time
        # D-Phase 2 §4.x: cache-hit 路径不再重新 filter (单位在同帧内不移动,
        # cached list 在同帧内有效; 下游 can_attack_if_in_range 已检查
        # place is None / hp < 0 兜底, 移除无用的 list 重建 = 19M calls × ~5
        # element listcomp 节省).
        return self._known_enemies[place]

    def allied_vision_has_explored(self, square):
        """检查联盟是否已经探索过某个方格(优化版)

        缓存属性 _allied_exploration_cache / _allied_exploration_timestamp
        已在 Player.__init__ 预初始化, 此处无需 hasattr 检查.
        """
        current_time = self.world.time
        if current_time - self._allied_exploration_timestamp > 1000:
            self._allied_exploration_cache.clear()
            self._allied_exploration_timestamp = current_time
            
        # 检查缓存
        if square in self._allied_exploration_cache:
            return self._allied_exploration_cache[square]
            
        # 计算结果
        result = any(square in ally.strictly_observed_before_squares for ally in self.allied)
        
        # 存入缓存
        self._allied_exploration_cache[square] = result
        return result

    def _potential_neighbors(self, x, y, skip_cache=False):
        # 将坐标转为网格坐标
        grid_x = x // A
        grid_y = y // A
        
        # 如果需要跳过缓存（用于harm_nearby_units等功能）
        if skip_cache:
            # 直接计算结果，不使用缓存
            result = []
            for dx in [0, 1, -1]:
                for dy in [0, 1, -1]:
                    k = grid_x + dx, grid_y + dy
                    if k in self._buckets:
                        result.extend(self._buckets[k])
            return result
        
        # 缓存键必须包含玩家 id：每条 computer_only 行是独立 Computer 玩家，
        # 同 Player 子类共享类级缓存；若只用格子坐标，先查询的空电脑会
        # 把「无单位」写入缓存，后查询的有单位电脑会误命中空列表（流星等
        # harm 范围技能因此打不到地图 computer 单位）。
        cache_key = (id(self), grid_x, grid_y)
        
        # 使用类变量而不是实例变量存储缓存，提高共享效率
        if not hasattr(self.__class__, '_global_neighbors_cache'):
            self.__class__._global_neighbors_cache = {}
            self.__class__._global_neighbors_timestamp = {}
            self.__class__._last_cleanup_time = self.world.time
            
        # 定期清理缓存（每30秒游戏时间）
        current_time = self.world.time
        if current_time - self.__class__._last_cleanup_time > 30000:
            # 仅保留最近使用的1000个缓存项
            if len(self.__class__._global_neighbors_cache) > 1000:
                # 根据时间戳排序，保留最近的1000
                recent_keys = sorted(self.__class__._global_neighbors_timestamp.keys(), 
                                    key=lambda k: self.__class__._global_neighbors_timestamp[k],
                                    reverse=True)[:1000]
                
                # 创建新缓存，只包含最近的项
                new_cache = {}
                new_timestamps = {}
                for k in recent_keys:
                    new_cache[k] = self.__class__._global_neighbors_cache[k]
                    new_timestamps[k] = self.__class__._global_neighbors_timestamp[k]
                
                # 替换旧缓存
                self.__class__._global_neighbors_cache = new_cache
                self.__class__._global_neighbors_timestamp = new_timestamps
            
            self.__class__._last_cleanup_time = current_time
        
        # 检查是否有缓存
        if cache_key in self.__class__._global_neighbors_cache:
            # 更新时间戳
            self.__class__._global_neighbors_timestamp[cache_key] = current_time
            return self.__class__._global_neighbors_cache[cache_key]
        
        # 如果没有缓存，则计算邻居
        # 优化：预先分配空间以减少内存分配
        result = []
        result_capacity = 0
        
        # 估计需要的容量
        for dx in [0, 1, -1]:
            for dy in [0, 1, -1]:
                k = grid_x + dx, grid_y + dy
                if k in self._buckets:
                    result_capacity += len(self._buckets[k])
        
        # 一次性分配空间
        if result_capacity > 0:
            result = [None] * result_capacity
            idx = 0
            
            # 填充结果
            for dx in [0, 1, -1]:
                for dy in [0, 1, -1]:
                    k = grid_x + dx, grid_y + dy
                    if k in self._buckets:
                        bucket = self._buckets[k]
                        bucket_len = len(bucket)
                        for i in range(bucket_len):
                            result[idx] = bucket[i]
                            idx += 1
            
            # 如果预估不准确，截断结果
            if idx < result_capacity:
                result = result[:idx]
        
        # 存储结果到缓存
        self.__class__._global_neighbors_cache[cache_key] = result
        self.__class__._global_neighbors_timestamp[cache_key] = current_time
        
        return result

    def _clear_neighbors_cache(self):
        """清除邻居缓存"""
        if hasattr(self.__class__, '_global_neighbors_cache'):
            # 仅清除与当前玩家相关的缓存项
            # 这比完全清空缓存更高效
            current_grid_keys = set()
            for unit in self.units:
                grid_x = unit.x // A
                grid_y = unit.y // A
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        current_grid_keys.add((grid_x + dx, grid_y + dy))
            
            # 从缓存中移除这些键（仅当前玩家）
            player_id = id(self)
            for gx, gy in current_grid_keys:
                k = (player_id, gx, gy)
                if k in self.__class__._global_neighbors_cache:
                    del self.__class__._global_neighbors_cache[k]
                    if k in self.__class__._global_neighbors_timestamp:
                        del self.__class__._global_neighbors_timestamp[k]

    def _is_seeing(self, u):
        # 如果单位是隐形或隐身的，并且没有被探测，则不可见
        if (u.is_invisible or u.is_cloaked) and u not in self.detected_units:
            return False
        
        # 覆盖计数网格：若该格子被任意友军严格观察覆盖，则O(1)返回
        # (_vision_cover_counts 已在 Player.__init__ 预初始化)
        if self._vision_cover_counts.get(u.place, 0) > 0:
            return True

        # 超快路径：已在合并后的严格观察区内则可见（避免后续一切开销）
        if u.place in self.observed_squares:
            return True

        # 墙/门等出口阻挡物：站在出口任一侧或相邻格观察时，应能看到阻挡物本身
        if self._exit_blocker_visible(u):
            return True
        
        # 如果是敌方单位，且不在观察区域中，则不可见
        if self.is_an_enemy(u) and u.place not in self.observed_squares:
            return False
        
        # 提取目标单位的位置
        x = u.x
        y = u.y
        place = u.place
        
        # 使用更高效的全局缓存系统 - 双层 dict {player_id -> {key -> bool}}
        # (Round 3: 类级 dict 已在 Player 类体声明, 总是存在)
        current_time = self.world.time
        
        # 优化缓存键结构 - 更快速的缓存查找
        # 使用固定间隔的时间戳分段，减少缓存失效频率
        time_bucket = current_time // 250  # 250ms更新一次缓存
        
        # 使用双层字典结构，第一层是玩家ID，第二层是单位ID和时间的组合
        if self.id not in self.__class__._global_vision_cache:
            self.__class__._global_vision_cache[self.id] = {}
        
        player_cache = self.__class__._global_vision_cache[self.id]
        cache_key = (u.id, time_bucket)
        
        # 查看缓存
        if cache_key in player_cache:
            self.__class__._vision_cache_hits += 1
            return player_cache[cache_key]
        
        self.__class__._vision_cache_misses += 1
        
        # 缓存管理 - 仅当缓存命中率较低时才清理
        cache_total = self.__class__._vision_cache_hits + self.__class__._vision_cache_misses
        if cache_total > 10000 and self.__class__._vision_cache_hits / cache_total < 0.5:
            # 缓存效率低，进行清理 (_last_vision_cleanup 已在类体初始化)
            if current_time - self.__class__._last_vision_cleanup > 5000:
                self.__class__._last_vision_cleanup = current_time
                self.__class__._global_vision_cache.clear()
                self.__class__._vision_cache_hits = 0
                self.__class__._vision_cache_misses = 0
                player_cache = self.__class__._global_vision_cache[self.id] = {}
        
        # 优化8：缓存联盟观察区域，避免重复any()生成器计算
        # 预计算并缓存联盟ID列表，避免每次调用都重新排序
        # (_cached_alliance_ids / _cached_alliance_time 已在 Player.__init__ 预初始化)
        if self._cached_alliance_time != current_time // 1000:
            self._cached_alliance_ids = tuple(sorted(avp.id for avp in self.allied_vision))
            self._cached_alliance_time = current_time // 1000
        
        # 创建联盟观察区域的缓存键
        alliance_cache_key = (self._cached_alliance_ids, time_bucket)
        
        # 初始化联盟观察区域缓存
        if not hasattr(self.__class__, '_alliance_observed_cache'):
            self.__class__._alliance_observed_cache = {}
            
        # 检查缓存中是否有合并的观察区域
        if alliance_cache_key in self.__class__._alliance_observed_cache:
            merged_observed_squares = self.__class__._alliance_observed_cache[alliance_cache_key]
        else:
            # 合并所有盟友的观察区域到一个集合中，避免重复any()调用
            merged_observed_squares = set()
            for avp in self.allied_vision:
                merged_observed_squares.update(avp.observed_squares)
                
            # 缓存结果，但限制缓存大小避免内存问题
            if len(self.__class__._alliance_observed_cache) > 50:
                # 清理一半旧缓存
                items = list(self.__class__._alliance_observed_cache.items())
                self.__class__._alliance_observed_cache = dict(items[25:])
                
            self.__class__._alliance_observed_cache[alliance_cache_key] = merged_observed_squares
        
        # 快速预检查 - 使用预合并的集合，避免any()生成器
        in_observed_area = place in merged_observed_squares
        
        if not in_observed_area:
            player_cache[cache_key] = False
            return False
        
        # 关键优化：如果位置已在联盟严格观察区内，则必然可见
        player_cache[cache_key] = True
        return True
        
        # 优化9：缓存对象属性检查，避免重复hasattr调用
        # 为单位缓存airground_type属性的存在性
        if not hasattr(u, '_cached_has_airground_type'):
            u._cached_has_airground_type = hasattr(u, 'airground_type')
            
        # 空中单位特殊处理 - 如果在同一格子中，则空中单位一定能看到地面单位，地面单位也一定能看到空中单位
        if u._cached_has_airground_type and u.place:
            for avp in self.allied_vision:
                for avu in avp.units:
                    if not avu.is_inside and avu.place == u.place:
                        # 同一方格内互相可见
                        player_cache[cache_key] = True
                        return True
        
        # 使用缓存存储视野距离的平方值 - 避免重复计算
        if not hasattr(self.__class__, '_sight_range_squares'):
            self.__class__._sight_range_squares = {}
        
        # 计算结果
        result = False
        
        # 使用空间索引加速邻居单位查找
        nearby_units_map = {}  # 用于去重，避免重复检查同一单位
        
        # 优化11：联盟级别的空间索引缓存，避免重复_potential_neighbors调用
        # 复用之前缓存的联盟ID列表
        alliance_spatial_key = (self._cached_alliance_ids, x // A, y // A, time_bucket)
        
        # 初始化联盟空间索引缓存
        if not hasattr(self.__class__, '_alliance_spatial_cache'):
            self.__class__._alliance_spatial_cache = {}
            
        # 检查是否有缓存的联盟单位
        if alliance_spatial_key in self.__class__._alliance_spatial_cache:
            nearby_allied_units = self.__class__._alliance_spatial_cache[alliance_spatial_key]
        else:
            # 合并所有盟友的附近单位，避免重复计算
            nearby_allied_units = []
            processed_unit_ids = set()
            
            for avp in self.allied_vision:
                # 获取可能在视野范围内的友方单位
                nearby_units = avp._potential_neighbors(x, y)
                
                for avu in nearby_units:
                    # 避免重复添加同一单位
                    if avu.id not in processed_unit_ids:
                        nearby_allied_units.append(avu)
                        processed_unit_ids.add(avu.id)
            
            # 缓存结果，但限制缓存大小
            if len(self.__class__._alliance_spatial_cache) > 200:
                # 清理一半旧缓存
                items = list(self.__class__._alliance_spatial_cache.items())
                self.__class__._alliance_spatial_cache = dict(items[100:])
                
            self.__class__._alliance_spatial_cache[alliance_spatial_key] = nearby_allied_units
        
        # 算法优化：减少视野检查频率，而非加速单次计算
        # 策略1：空间分区预筛选 - 只检查相邻区域的单位
        if nearby_allied_units:
            # 将目标位置量化到网格
            grid_x = x // (A * 2)  # 使用更大的网格减少计算
            grid_y = y // (A * 2)
            
            # 快速预筛选：优先检查距离最近的单位
            min_distance_unit = None
            min_distance = float('inf')
            
            # 第一轮：快速距离预筛选，找到最近的几个单位
            close_units = []
            for avu in nearby_allied_units:
                # 使用曼哈顿距离进行快速预筛选（比欧几里得距离快）
                manhattan_dist = abs(avu.x - x) + abs(avu.y - y)
                if manhattan_dist < avu.sight_range * 1.5:  # 粗筛选
                    close_units.append((avu, manhattan_dist))
            
            # 按距离排序，优先检查最近的单位
            close_units.sort(key=lambda item: item[1])
            
            # 第二轮：对预筛选的单位进行精确检查
            for avu, _ in close_units[:5]:  # 最多检查5个最近的单位
                # 获取或计算视野范围的平方
                sight_range = avu.sight_range
                if sight_range not in self.__class__._sight_range_squares:
                    self.__class__._sight_range_squares[sight_range] = sight_range * sight_range
                
                radius2 = self.__class__._sight_range_squares[sight_range]
                
                # 精确距离计算
                dx = avu.x - x
                dy = avu.y - y
                dist2 = dx * dx + dy * dy
                
                # 对于距离非常近的单位直接判定为可见
                if dist2 < radius2 / 4:
                    result = True
                    break
                
                # 检查是否在视野范围内
                if dist2 < radius2:
                    # 缓存单位的观察区域检查结果
                    observed_squares = getattr(avu, '_cached_observed_squares', None)
                    
                    # 如果缓存不存在或者已过期，重新计算
                    if observed_squares is None or getattr(avu, '_cached_observed_time', 0) != time_bucket:
                        observed_squares = set(avu.get_observed_squares())
                        avu._cached_observed_squares = observed_squares
                        avu._cached_observed_time = time_bucket
                    
                    if place in observed_squares:
                        result = True
                        break
                
                if result:
                    break
        
        # 保存结果到缓存
        player_cache[cache_key] = result
        
        return result

    def _clear_vision_cache(self):
        """清除视野缓存 - O(1) 版本.

        Round 3 重构: ``_observed_squares_cache`` / ``_global_vision_cache``
        改为 ``{player_id -> {key -> data}}`` 二级 dict, 当前玩家清理只需
        ``pop(self.id, None)``, 从原本 O(N_total_keys) 退化为 O(1).

        类级 dict 已在 Player 类体声明, 永远存在, 无需 hasattr 检查.
        """
        cls = self.__class__
        pid = self.id

        # 该玩家的视野/观察缓存——O(1) 一次性弹出
        cls._global_vision_cache.pop(pid, None)
        cls._observed_squares_cache.pop(pid, None)
        cls._observed_squares_cache_timestamp.pop(pid, None)

        # 重置缓存命中率计数器
        cls._vision_cache_hits = 0
        cls._vision_cache_misses = 0

        # 清除单位上的观察区域缓存
        # 注: Round 4 把 _cached_observed_squares / _cached_observed_time 升级
        # 为 Creature 类级 default (None / 0), 所以 hasattr 总为 True 而 delattr
        # 会抛 AttributeError (无法删 class 属性). 改为重置实例值, 让下次访问
        # 的 "is None / != time_bucket" 触发重建.
        for u in self.units:
            d = u.__dict__
            if '_cached_observed_squares' in d:
                d['_cached_observed_squares'] = None
                d['_cached_observed_time'] = 0

        # 清除联盟视野缓存
        self._clear_allied_vision_cache()

    def _clear_allied_vision_cache(self):
        """清除与该玩家相关的联盟视野缓存"""
        if hasattr(self.__class__, '_allied_vision_cache'):
            # 找出包含此玩家的所有联盟
            player_alliances = []
            for alliance_key in list(self.__class__._allied_vision_cache.keys()):
                if self.id in alliance_key:
                    player_alliances.append(alliance_key)
            
            # 批量删除这些联盟的缓存
            for alliance_key in player_alliances:
                if alliance_key in self.__class__._allied_vision_cache:
                    del self.__class__._allied_vision_cache[alliance_key]
                if alliance_key in self.__class__._allied_vision_timestamp:
                    del self.__class__._allied_vision_timestamp[alliance_key]
        
        # 清除本地的联盟视野探索缓存
        if hasattr(self, '_allied_exploration_cache'):
            self._allied_exploration_cache.clear()

    def _team_has_lost(self):
        for p in self.allied_vision:
            if not p.has_been_defeated:
                return False
        return True

    def _update_perception(self):
        """更新玩家的感知.

        Round 4: 所有 class-level cache (_global_update_cycle, _last_global_update_time,
        _allied_vision_cache, _allied_vision_timestamp) 已在 Player 类体声明;
        instance _last_perception_update / _last_unit_positions 在 __init__ 预初始化.
        """
        # 算法优化：分帧更新策略 - 减少高频无用计算
        cls = self.__class__
        current_time = self.world.time

        # 每140ms切换一个玩家组进行视野更新，并将分组数从7提高到9
        if current_time - cls._last_global_update_time > 140:
            cls._global_update_cycle = (cls._global_update_cycle + 1) % 9
            cls._last_global_update_time = current_time

        # 根据玩家ID分组，不同组在不同时间更新
        # (修复: world.get_next_id() 返回 str, 原 `(self.id or 0) % 9` 触发
        #  字符串格式化 TypeError 每帧抛+捕获. _player_group_mod9 已在
        #  Player.__init__ 预算)
        should_update_this_frame = (cls._global_update_cycle == self._player_group_mod9)

        # 策略2：移动单位优先更新，静止单位降低更新频率
        if not should_update_this_frame:
            # 检查是否有单位移动或重要事件
            has_moving_units = False
            last_unit_positions = self._last_unit_positions
            for unit in self.units:
                last_pos = last_unit_positions.get(unit.id, (unit.x, unit.y))
                if (unit.x, unit.y) != last_pos:
                    has_moving_units = True
                    break

            # 如果没有移动单位且不是该玩家的更新帧，跳过更新
            if not has_moving_units:
                if current_time - self._last_perception_update < 500:  # 500ms内不重复更新
                    return
        
        # 记录本次更新时间
        self._last_perception_update = current_time
        
        # 策略3：单位位置变化检测
        # (_last_unit_positions 已在 Player.__init__ 预初始化)
        for unit in self.units:
            self._last_unit_positions[unit.id] = (unit.x, unit.y)
        
        # 如果在开启作弊模式或团队已失败的情况下，直接观察整个地图
        if self.cheatmode or self._team_has_lost():
            self.observed_squares = set(self.world.squares)
            self.observed_before_squares.update(self.world.squares)
            self.strictly_observed_before_squares.update(self.world.squares)
            self.perception = set()
            # D-Phase 2: _Space.objects class default = (), 直接访问.
            for s in self.world.squares:
                objs = s.objects
                if objs:
                    self.perception.update(objs)
            return
            
        # 初始化感知相关集合
        previous_perception = self.perception.copy()  # 保存之前的感知状态，用于检测新的敌方单位
        self.perception = set()
        self.observed_squares = set()
        partially_observed_squares = set()
        # 覆盖计数网格（严格观察）：用于O(1)可见性判定与增量处理
        self._vision_cover_counts = {}
        
        # 使用联盟视野缓存机制，减少每tick的计算量
        # (_allied_vision_cache / _allied_vision_timestamp 已在 Player 类体声明)
        current_time = self.world.time
        vision_cache_key = current_time // 250  # 每250毫秒更新一次视野缓存

        # 创建或使用联盟缓存 - 复用已有的联盟ID缓存
        # (_cached_allied_ids / _cached_allied_time 已在 Player.__init__ 预初始化)
        if self._cached_allied_time != current_time // 1000:
            self._cached_allied_ids = tuple(sorted(ally.id for ally in self.allied))
            self._cached_allied_time = current_time // 1000

        alliance_key = self._cached_allied_ids
        if alliance_key in self.__class__._allied_vision_cache and self.__class__._allied_vision_timestamp.get(alliance_key) == vision_cache_key:
            # 使用缓存数据
            cached_vision = self.__class__._allied_vision_cache[alliance_key]
            self.observed_squares = cached_vision['observed_squares'].copy()
            partially_observed_squares = cached_vision['partially_observed_squares'].copy()
        else:
            # 优化: 预计算相同特性单位组
            unit_vision_groups = {}
            
            # 收集所有盟友单位的视野 - 优化的数据收集
            for p in self.allied_vision:
                for u in p.units:
                    # 缓存单位的视野特性
                    vision_key = (
                        u.is_inside,
                        u.sight_range < self.world.square_width,
                        u.height,
                        u.place,
                    )
                    
                    if vision_key not in unit_vision_groups:
                        unit_vision_groups[vision_key] = []
                    unit_vision_groups[vision_key].append(u)
            
            # 批量处理每个视野特性组
            # 使用缓存减少重复计算
            
            # 处理每个视野特性组
            for vision_key, units in unit_vision_groups.items():
                # 跳过在建筑物内部的单位
                if vision_key[0]:  # is_inside
                    continue
                    
                sample_unit = units[0]
                
                # 缓存键
                unit_cache_key = (sample_unit.sight_range, sample_unit.id, vision_cache_key)

                # Round 3: 二级 dict {player_id -> {unit_cache_key -> ...}}
                # 类级 dict 已在 Player 类体声明, 总是存在.
                player_obs_cache = self.__class__._observed_squares_cache.get(self.id)
                cached_entry = player_obs_cache.get(unit_cache_key) if player_obs_cache is not None else None

                # 检查缓存
                if cached_entry is not None:
                    strict_squares, all_squares = cached_entry
                    # 严格观察：更新集合与覆盖计数
                    for sq in strict_squares:
                        self.observed_squares.add(sq)
                        self._vision_cover_counts[sq] = self._vision_cover_counts.get(sq, 0) + 1
                    # 部分观察：直接并入集合
                    partially_observed_squares.update(all_squares)
                    continue

                # 如果没有缓存，则计算并存储
                observed_data = sample_unit.get_observed_squares_optimized()
                strict_squares = observed_data['strict']
                all_squares = observed_data['all']

                # 更新当前状态
                for sq in strict_squares:
                    self.observed_squares.add(sq)
                    self._vision_cover_counts[sq] = self._vision_cover_counts.get(sq, 0) + 1
                partially_observed_squares.update(all_squares)

                # 存储到缓存 (按玩家分片)
                if player_obs_cache is None:
                    player_obs_cache = {}
                    self.__class__._observed_squares_cache[self.id] = player_obs_cache
                    self.__class__._observed_squares_cache_timestamp[self.id] = {}
                player_obs_cache[unit_cache_key] = (strict_squares, all_squares)
                self.__class__._observed_squares_cache_timestamp[self.id][unit_cache_key] = current_time
                
            # 从部分可见方格中移除完全可见的方格
            partially_observed_squares -= self.observed_squares
            
            # 保存联盟视野缓存
            self.__class__._allied_vision_cache[alliance_key] = {
                'observed_squares': self.observed_squares.copy(),
                'partially_observed_squares': partially_observed_squares.copy()
            }
            self.__class__._allied_vision_timestamp[alliance_key] = vision_cache_key
                    
            # 定期清理缓存 - 每60秒游戏时间或缓存大小超过20个联盟
            if (
                len(self.__class__._allied_vision_cache) > 20 or 
                not hasattr(self.__class__, '_last_vision_cache_cleanup') or 
                current_time - getattr(self.__class__, '_last_vision_cache_cleanup', 0) > 60000
            ):
                self.__class__._last_vision_cache_cleanup = current_time
                # 保留最近的10个记录
                if len(self.__class__._allied_vision_cache) > 10:
                    recent_alliances = sorted(
                        self.__class__._allied_vision_timestamp.items(), 
                        key=lambda x: x[1], 
                        reverse=True
                    )[:10]
                    
                    # 创建新缓存
                    new_cache = {}
                    new_timestamps = {}
                    for alliance, timestamp in recent_alliances:
                        new_cache[alliance] = self.__class__._allied_vision_cache[alliance]
                        new_timestamps[alliance] = timestamp
                        
                    # 替换旧缓存
                    self.__class__._allied_vision_cache = new_cache
                    self.__class__._allied_vision_timestamp = new_timestamps
        
        # 更新历史观察记录
        self.observed_before_squares.update(partially_observed_squares)
        self.strictly_observed_before_squares.update(self.observed_squares)
        
        # 优化：使用集合操作批量添加静态对象
        static_objects = set()
        for s in self.observed_squares:
            objs = getattr(s, 'objects', None)
            if objs:
                static_objects.update([o for o in objs if o.player is None])
        self.perception.update(static_objects)
        
        # 创建部分可见区域中的静态对象映射，仅检查一次每个对象
        objects_to_check = set()
        for s in partially_observed_squares:
            objs = getattr(s, 'objects', None)
            if objs:
                objects_to_check.update([o for o in objs if o.player is None])
        
        # 批量检查可见性 - 使用批处理接口，显著降低函数调用开销
        if objects_to_check:
            visible_objects, memory_objects = self._bulk_visibility_check(objects_to_check)
            self.perception.update(visible_objects)
            if memory_objects:
                self._bulk_memorize(memory_objects)
            
        # 处理联盟观察到的对象 - 使用联盟视野缓存
        if alliance_key in self.__class__._allied_vision_cache and 'observed_objects' in self.__class__._allied_vision_cache[alliance_key]:
            cached_observed = {
                o for o in self.__class__._allied_vision_cache[alliance_key]['observed_objects']
                if getattr(o, "place", None) is not None
            }
            self.perception.update(cached_observed)
        else:
            # 处理观察到的对象 - 使用字典推导优化
            observed_objects_to_add = set()
            for p in self.allied_vision:
                # 过滤出有效的观察对象
                valid_objects = {o for o, t in p.observed_objects.items() 
                               if t >= self.world.time and o.place is not None}
                
                # 移除过期和无效对象
                invalid_objects = set(p.observed_objects.keys()) - valid_objects
                for o in invalid_objects:
                    del p.observed_objects[o]
                    
                observed_objects_to_add.update(valid_objects)
            
            self.perception.update(observed_objects_to_add)
            
            # 更新缓存
            if alliance_key in self.__class__._allied_vision_cache:
                self.__class__._allied_vision_cache[alliance_key]['observed_objects'] = observed_objects_to_add
        
        # 添加盟友单位 - 使用联盟缓存优化
        if alliance_key in self.__class__._allied_vision_cache and 'allied_units' in self.__class__._allied_vision_cache[alliance_key]:
            # 使用缓存的联盟单位
            allied_units = self.__class__._allied_vision_cache[alliance_key]['allied_units']
            # 检查缓存的单位是否仍然存在
            allied_units = {u for u in allied_units if u.place is not None}
            self.perception.update(allied_units)
        else:
            # 重新收集盟友单位
            allied_units = set()
            for p in self.allied_vision:
                allied_units.update(p.units)
            self.perception.update(allied_units)
            
            # 更新缓存
            if alliance_key in self.__class__._allied_vision_cache:
                self.__class__._allied_vision_cache[alliance_key]['allied_units'] = allied_units
        
        # 处理敌方单位 - 使用集合操作优化，但保持顺序确定性
        enemy_units = set()
        enemy_players = set(self.world.players) - set(self.allied_vision)
        
        all_enemy_units = set()
        for p in enemy_players:
            all_enemy_units.update(p.units)
        
        # 优化：缓存敌方单位排序结果，避免每次_update_perception都重新排序
        enemy_units_hash = hash(frozenset(u.id for u in all_enemy_units))
        
        # (_cached_enemy_units_hash / _cached_sorted_enemy_units 已在 Player.__init__ 预初始化)
        if self._cached_enemy_units_hash != enemy_units_hash:
            self._cached_sorted_enemy_units = sorted(all_enemy_units, key=lambda u: u.id)
            self._cached_enemy_units_hash = enemy_units_hash
        
        # 优化：批量检查敌方单位可见性，减少_is_seeing调用次数
        sorted_enemy_units = self._cached_sorted_enemy_units
        
        # 预先筛选在观察区域内的敌方单位，避免对不在视野内的单位调用昂贵的_is_seeing
        enemy_units_in_sight = []
        observed_squares_set = self.observed_squares  # 缓存集合引用
        
        for u in sorted_enemy_units:
            # 快速预检查：观察区内，或出口阻挡物从观察区可见
            if u.place in observed_squares_set or self._exit_blocker_visible(u):
                enemy_units_in_sight.append(u)
        
        # 批量检查可见性（限制每帧昂贵检查次数，避免极端场景爆发）
        checks_left = 200
        for u in enemy_units_in_sight:
            if checks_left <= 0:
                break
            if self._is_seeing(u):
                enemy_units.add(u)
            checks_left -= 1

        for u in sorted_enemy_units:
            if getattr(u, "is_inside", False) and self._open_container_passenger_visible(u):
                enemy_units.add(u)

        self.perception.update(enemy_units)
        
        # 移除位于建筑内部的单位 - 使用集合推导，按ID排序确保顺序
        # Round 4: Entity.place 默认 None, _Space.is_inside_place 默认 False;
        # 改用 obj.place is not None and obj.place.is_inside_place 替代嵌套 getattr.
        self_units = self.units
        inside_units = set()
        for o in self.perception:
            p = o.place
            if p is not None and p.is_inside_place and o not in self_units:
                if self._open_container_passenger_visible(o):
                    continue
                inside_units.add(o)
        self.perception -= inside_units

        # 检测新出现的敌方单位 - 按ID排序确保顺序一致
        if hasattr(self, 'new_enemy_units'):
            # 使用集合操作找出新的敌方单位
            new_perception = self.perception - previous_perception
            # 优化：只对新出现的单位进行排序，通常数量很少
            new_enemy_candidates = []
            for o in new_perception:
                # 中立电脑的单位（被动 creep）不计入"新敌人"提示链路。
                # 与 game_navigation.update_fog_of_war 的过滤规则保持一致。
                if self.is_an_enemy(o) and not getattr(
                    getattr(o, "player", None), "neutral", False
                ):
                    p = o.place
                    if p is None or not p.is_inside_place:
                        new_enemy_candidates.append(o)
            
            # 对少量新单位排序比对全部单位排序更高效
            if new_enemy_candidates:
                self.new_enemy_units = sorted(new_enemy_candidates, key=lambda o: o.id)
            else:
                self.new_enemy_units = []

    def _should_be_seeing(self, m):
        # 直接使用已优化的_is_seeing函数，利用其缓存机制
        return self._is_seeing(m)

    def _bulk_visibility_check(self, objects):
        """批量检查对象可见性，减少重复计算

        返回: (可见对象集合, 不可见对象集合)

        D-Phase 2 (cont.): 整函数 Cython 化 (见 perception_fast.bulk_visibility_check).
        """
        if _fast is not None:
            return _fast.bulk_visibility_check(self, objects)
        return self._py_bulk_visibility_check(objects)

    def _py_bulk_visibility_check(self, objects):
        """Python fallback (与 perception_fast.bulk_visibility_check 完全等价)."""
        # 预先分配结果集
        visible_objects = set()
        invisible_objects = set()
        
        # 获取当前时间戳 - 仅计算一次
        current_time = self.world.time
        time_bucket = current_time // 250  # 与_is_seeing函数保持一致
        
        # 确保有缓存结构
        # Round 4: 所有类级 cache 已在 Player 类体声明, 删除冗余 hasattr.
        cls = self.__class__

        # 获取或创建玩家缓存
        if self.id not in cls._global_vision_cache:
            cls._global_vision_cache[self.id] = {}
        player_cache = cls._global_vision_cache[self.id]

        # 按位置分组 - 相同位置的对象可以一次性检查
        objects_by_place = {}
        for obj in objects:
            place = obj.place
            if place not in objects_by_place:
                objects_by_place[place] = []
            objects_by_place[place].append(obj)

        # 批量预检查 - 快速排除不在任何盟友观察区域内的位置
        # 玩家+时间桶级缓存：避免同一桶内重复合并
        if cls._observed_union_bucket != time_bucket:
            cls._observed_union_cache = {}
            cls._observed_union_bucket = time_bucket
        union_cache = cls._observed_union_cache
        if self.id not in union_cache:
            observed_places_union = set()
            for avp in self.allied_vision:
                observed_places_union.update(avp.observed_squares)
            union_cache[self.id] = observed_places_union
        else:
            observed_places_union = union_cache[self.id]
        observed_places = observed_places_union

        # 初始化位置→覆盖该位置的观察者缓存（时间桶级）
        if cls._place_covering_units_bucket != time_bucket:
            cls._place_covering_units_cache = {}
            cls._place_covering_units_bucket = time_bucket

        # 本时间桶方格可见性布尔缓存 (循环外 init 一次, 不在每个 place 重复 init)
        if cls._place_visible_bucket != time_bucket:
            cls._place_visible_cache = {}
            cls._place_visible_bucket = time_bucket
        pvc_root = cls._place_visible_cache
        if self.id not in pvc_root:
            pvc_root[self.id] = {}
        place_visible_cache = pvc_root[self.id]

        # 针对每个位置批量处理
        for place, place_objects in objects_by_place.items():
            # 如果位置不在观察区域，所有对象都不可见
            if place not in observed_places:
                invisible_objects.update(place_objects)
                
                # 更新缓存
                for obj in place_objects:
                    cache_key = (obj.id, time_bucket)
                    player_cache[cache_key] = False
                continue
                
            # 收集所有可能的观察者单位（按位置与时间桶缓存）
            # Round 4: _nearby_units_cache* 已在 Player.__init__ 预初始化
            if self._nearby_units_cache_bucket != time_bucket:
                self._nearby_units_cache = {}
                self._nearby_units_cache_bucket = time_bucket
            cache_key_nearby = place.id
            all_nearby_units = self._nearby_units_cache.get(cache_key_nearby)
            if all_nearby_units is None:
                all_nearby_units = set()
                for avp in self.allied_vision:
                    # 使用空间索引快速找到附近单位
                    x, y = place.x, place.y
                    nearby_units = avp._potential_neighbors(x, y)
                    all_nearby_units.update(nearby_units)
                self._nearby_units_cache[cache_key_nearby] = all_nearby_units

            # 位置级快速可见性缓存：记录覆盖该 place 的少量观察者，便于该位置多个对象复用
            # Round 4: _cached_observed_squares/_cached_observed_time 在 Creature 类有 default
            covering_units = cls._place_covering_units_cache.get(place)
            if covering_units is None:
                covering_units = []
                for unit in all_nearby_units:
                    observed_squares = unit._cached_observed_squares
                    if observed_squares is None or unit._cached_observed_time != time_bucket:
                        observed_squares = set(unit.get_observed_squares())
                        unit._cached_observed_squares = observed_squares
                        unit._cached_observed_time = time_bucket
                    if place in observed_squares:
                        covering_units.append(unit)
                        # 只保留少量观察者用于早退，加速同一位置的多对象检查
                        if len(covering_units) >= 3:
                            break
                cls._place_covering_units_cache[place] = covering_units

            place_visible_for_any = len(covering_units) > 0

            # 跨桶稳定复用：若上一桶也可见且观察者签名一致，则对非隐形对象直接视为可见
            # (_place_visible_history 已在 Player 类体声明)
            history_key = (self.id, place.id)
            # 观察者签名：取最多3个最小ID，确保稳定
            if covering_units:
                cov_ids = tuple(sorted(u.id for u in covering_units)[:3])
            else:
                cov_ids = ()
            prev = cls._place_visible_history.get(history_key)
            if not place_visible_for_any and prev:
                prev_bucket, prev_sig, prev_visible = prev
                # 放宽为近3个桶内、覆盖者签名一致且上一判定为可见
                if prev_visible and (time_bucket - prev_bucket) <= 3 and prev_sig == cov_ids:
                    place_visible_for_any = True

            # 若位置对任一观察者可见：
            # 先批量处理“非隐身/隐形”的对象，直接判为可见并写入缓存，避免逐个距离检查
            # (Entity.is_invisible/is_cloaked = False 是 class default)
            if place_visible_for_any:
                place_visible_cache[place] = True
                remaining_to_check = []
                for obj in place_objects:
                    cache_key = (obj.id, time_bucket)
                    if not obj.is_invisible and not obj.is_cloaked:
                        player_cache[cache_key] = True
                        visible_objects.add(obj)
                    else:
                        remaining_to_check.append(obj)
                # 后续仅对隐身/隐形对象做细查
                place_objects = remaining_to_check
            # 写入可见性历史
            cls._place_visible_history[history_key] = (time_bucket, cov_ids, place_visible_for_any)

            # 对每个位置上的剩余对象进行检查
            for obj in place_objects:
                cache_key = (obj.id, time_bucket)
                
                # 检查缓存
                if cache_key in player_cache:
                    self.__class__._vision_cache_hits += 1
                    if player_cache[cache_key]:
                        visible_objects.add(obj)
                    else:
                        invisible_objects.add(obj)
                    continue
                    
                self.__class__._vision_cache_misses += 1
                
                # 对象本身隐身/隐形且未被探测（附加：细查结果缓存）
                if (getattr(obj, 'is_invisible', False) or getattr(obj, 'is_cloaked', False)) and obj not in self.detected_units:
                    # 隐形细查结果缓存（按玩家+方格+对象+时间桶）
                    # 允许跨2个桶的稳定复用
                    if not hasattr(self.__class__, '_invis_visibility_cache'):
                        self.__class__._invis_visibility_cache = {}
                        self.__class__._invis_visibility_bucket = time_bucket
                    ivc = self.__class__._invis_visibility_cache
                    ivc_key = (self.id, getattr(place, 'id', id(place)), getattr(obj, 'id', id(obj)))
                    ivc_entry = ivc.get(ivc_key)
                    if ivc_entry:
                        last_bucket, last_visible = ivc_entry
                        if time_bucket - last_bucket <= 2:
                            player_cache[cache_key] = last_visible
                            if last_visible:
                                visible_objects.add(obj)
                            else:
                                invisible_objects.add(obj)
                            continue
                    player_cache[cache_key] = False
                    invisible_objects.add(obj)
                    continue
                
                # 敌人单位但不在观察区域
                if self.is_an_enemy(obj) and place not in self.observed_squares:
                    player_cache[cache_key] = False
                    invisible_objects.add(obj)
                    continue
                
                # 获取对象坐标
                x, y = obj.x, obj.y
                
                # 检查视野
                is_visible = False
                
                # 获取缓存的距离平方计算
                if not hasattr(self.__class__, '_sight_range_squares'):
                    self.__class__._sight_range_squares = {}
                    
                # 遍历可能的观察者（优先检查覆盖该位置的观察者，快速早退）
                units_to_check = covering_units if covering_units else all_nearby_units
                checked = 0
                for unit in units_to_check:
                    # 获取视野范围
                    sight_range = unit.sight_range
                    if sight_range not in self.__class__._sight_range_squares:
                        self.__class__._sight_range_squares[sight_range] = sight_range * sight_range
                    radius2 = self.__class__._sight_range_squares[sight_range]
                    
                    # 计算距离平方
                    dx = unit.x - x
                    dy = unit.y - y
                    dist2 = dx * dx + dy * dy
                    
                    # 快速检查距离
                    if dist2 < radius2 / 4:  # 非常接近
                        is_visible = True
                        break
                        
                    # 详细检查
                    if dist2 < radius2:
                        # 检查单位是否可以观察到这个位置
                        observed_key = (unit.id, time_bucket)
                        observed_squares = getattr(unit, '_cached_observed_squares', None)
                        
                        # 如果缓存不存在或已过期，重新计算
                        if observed_squares is None or getattr(unit, '_cached_observed_time', 0) != time_bucket:
                            observed_squares = set(unit.get_observed_squares())
                            unit._cached_observed_squares = observed_squares
                            unit._cached_observed_time = time_bucket
                            
                        if place in observed_squares:
                            is_visible = True
                            break
                    checked += 1
                    # 限制每对象最大检查数量，进一步早退
                    if checked >= 4:
                        break
                
                # 记录结果
                player_cache[cache_key] = is_visible
                # 将隐形对象的细查结果写入缓存便于复用
                if getattr(obj, 'is_invisible', False) or getattr(obj, 'is_cloaked', False):
                    if not hasattr(self.__class__, '_invis_visibility_cache'):
                        self.__class__._invis_visibility_cache = {}
                        self.__class__._invis_visibility_bucket = time_bucket
                    ivc = self.__class__._invis_visibility_cache
                    ivc_key = (self.id, getattr(place, 'id', id(place)), getattr(obj, 'id', id(obj)))
                    ivc[ivc_key] = (time_bucket, is_visible)
                if is_visible:
                    visible_objects.add(obj)
                else:
                    invisible_objects.add(obj)
                    
        return visible_objects, invisible_objects

    def _bulk_memorize(self, objects):
        """批量记忆多个对象，避免重复函数调用开销.

        D-Phase 2 (cont.): 22.6k calls/5min cw1, 14.8 s tottime. 整函数 Cython
        化省 frame setup + bytecode dispatch. 失败时 fallback 到 Python.
        """
        if _fast is not None:
            _fast.bulk_memorize(self, objects)
            return
        self._py_bulk_memorize(objects)

    def _py_bulk_memorize(self, objects):
        """Python fallback (与 perception_fast.bulk_memorize 完全等价)."""
        current_time = self.world.time
        for obj in objects:
            if getattr(obj, "_is_skill_combat_proxy", False):
                continue
            if obj.is_invisible or obj.is_cloaked:
                continue
            if obj in self._memory_index:
                remembrance = self._memory_index[obj]
                remembrance.time_stamp = current_time
                if hasattr(obj, "hp"):
                    remembrance.hp = obj.hp
            else:
                remembrance = copy.copy(obj)
                remembrance.time_stamp = current_time
                remembrance.initial_model = obj
                self.memory.add(remembrance)
                self._memory_index[obj] = remembrance

    def _update_memory(self, previous_perception):
        self.observed_before_squares.update(self.observed_squares)
        
        # 预先获取当前时间，避免重复访问
        current_time = self.world.time
        memory_expires_time = current_time - self.memory_duration
        
        # 优化10：记忆清理频率控制 - 避免每次都检查昂贵的should_be_seeing
        # (_last_memory_cleanup / _memory_scan_cursor / _memory_list /
        #  _memory_list_snapshot_time 已在 Player.__init__ 预初始化)
        should_do_full_cleanup = (current_time - self._last_memory_cleanup) >= 2000

        # 当执行完整清理或内存快照过期时刷新快照
        if should_do_full_cleanup or (current_time - self._memory_list_snapshot_time > 2000):
            # 重新拍摄快照，避免每帧从 set 迭代
            self._memory_list = list(self.memory)
            self._memory_list_snapshot_time = current_time
            # 避免游标越界
            if self._memory_scan_cursor >= len(self._memory_list):
                self._memory_scan_cursor = 0
        
        # 处理需要遗忘的记忆（自适应批次：随单位量缩放）
        units_to_forget = []
        # 分帧配额：限制每次完整清理中昂贵判断的数量，避免爆发
        total_units = len(self.world.units) if hasattr(self.world, 'units') else 0
        cleanup_quota = 300 + (total_units // 50)
        display_expired_initial_models = set()

        # 选择扫描集合：完整清理时扫描全部，否则仅扫描批次
        if should_do_full_cleanup:
            iterable_memories = self._memory_list  # 使用快照以获得稳定顺序
        else:
            # 自适应批次：随单位量缩放
            BATCH = 250 + (total_units // 80)
            start = self._memory_scan_cursor
            end = min(start + BATCH, len(self._memory_list))
            iterable_memories = self._memory_list[start:end]
            # 更新游标（环形）
            self._memory_scan_cursor = 0 if end >= len(self._memory_list) else end

        for m in iterable_memories:
            # 基本忘记条件（总是检查，成本低）
            expired_memory = self._expire_memory_if_stale(
                m, current_time, display_expired_initial_models
            )
            visible_model_in_perception = (
                m.initial_model in self.perception and self._is_seeing(m.initial_model)
            )
            basic_forget_conditions = (
                expired_memory
                or visible_model_in_perception
                or m.initial_model.place is None
            )
            
            if basic_forget_conditions:
                units_to_forget.append(m)
            elif should_do_full_cleanup and cleanup_quota > 0:
                # 使用观察区集合做快速判定，替代昂贵的可见性函数
                if m.place in self.observed_squares:
                    units_to_forget.append(m)
                cleanup_quota -= 1
        
        if should_do_full_cleanup:
            self._last_memory_cleanup = current_time
                
        # 批量遗忘单位
        for m in units_to_forget:
            self._forget(m)
        forgotten_initial_models = {
            m.initial_model for m in units_to_forget
        }.union(display_expired_initial_models)
            
        # 记忆"刚刚离开感知"的单位。
        # 注意：绝不能用 ``len(perception) 是否变化`` 来判断是否有单位消失。
        # 当一个单位在同一帧里离开一个方格、同时另一个方格（对象数量相同）进入
        # 感知时，集合大小不变（旧对象出、新对象进各 N 个），但确实有对象消失。
        # 旧的 ``perception_size_change > 0`` 门控会在这种"等量交换"时跳过记忆，
        # 导致刚离开的方格对象既不在感知、也不在记忆里，于是客户端雾战中出现
        # 几秒钟的空白，直到下一次完整感知更新才被重新补进记忆。
        # 直接用集合差集判断消失单位（开销很低），保证每帧都正确记忆。
        disappeared_units = previous_perception - self.perception
        if disappeared_units:
            own_unit_ids = {u.id for u in self.units}
            # 过滤出需要记忆的单位
            units_to_memorize = {
                o for o in disappeared_units
                if not (o.is_invisible or o.is_cloaked) and o.place is not None
                and o not in forgotten_initial_models
                and not (
                    getattr(o, "player", None) is self
                    and getattr(o, "id", None) not in own_unit_ids
                )
            }

            # 批量记忆
            if units_to_memorize:
                self._bulk_memorize(units_to_memorize)

    def _update_perception_and_memory(self):
        # 优化12：增量感知更新系统 - 只更新真正发生变化的部分
        # (_last_unit_positions / _last_perception_hash / _force_full_update /
        #  _last_positions_hash 已在 Player.__init__ 预初始化)

        # 检查是否有单位移动或状态变化
        current_unit_positions = {}
        position_changed = False
        moved_units = []
        
        # 优化：快速检查己方单位位置变化，使用hash比较
        current_positions_hash = 0
        for unit in self.units:
            if unit.place:
                # 使用简化的位置hash，减少tuple创建开销
                pos_hash = hash((unit.x, unit.y, unit.place.id))
                current_positions_hash += pos_hash
                current_unit_positions[unit.id] = pos_hash
                # 记录移动的单位（用于增量更新）
                if self._last_unit_positions.get(unit.id) not in (None, pos_hash):
                    moved_units.append(unit)
        
        # 比较hash值来快速检测变化
        if current_positions_hash != self._last_positions_hash:
            position_changed = True
            self._last_positions_hash = current_positions_hash
        
        # 增加一个机制：定期强制刷新感知，避免缓存导致的视野问题
        # (_last_forced_perception_update 已在 Player.__init__ 预初始化)
        current_time = self.world.time

        # 每2秒强制刷新一次感知，确保建筑物视野等不会被缓存遗漏
        time_since_last_forced = current_time - self._last_forced_perception_update
        needs_forced_update = time_since_last_forced >= 2000  # 2秒
        
        # 如果单位位置没有变化，且不是强制更新，且不是作弊模式，且不需要定期强制更新，则跳过感知更新
        if not position_changed and not self._force_full_update and not self.cheatmode and not needs_forced_update:
            # 仍然需要轻量级记忆更新
            self._lightweight_memory_update()
            return
            
        # 如果是定期强制更新，记录时间
        if needs_forced_update:
            self._last_forced_perception_update = current_time
            
        # 若本帧仅少量单位移动，执行增量更新以避免整帧重算
        # 阈值可调整：在大地图上通常只有极少数单位同时移动
        if position_changed and moved_units and len(moved_units) <= 5:
            previous_perception = self.perception.copy()
            self._incremental_perception_update(moved_units)
            self._last_unit_positions = current_unit_positions
            # 增量路径也需要更新记忆（基于变化前的感知）
            self._update_memory(previous_perception)
            # 感知版本号：每次增量更新后递增，供其他系统做去抖/早退
            self._perception_version = getattr(self, '_perception_version', 0) + 1
            return

        # 执行完整的感知更新
        self._force_full_update = False
        self._last_unit_positions = current_unit_positions
        
        # 先保存当前的感知状态
        previous_perception = self.perception.copy()
        
        # 更新感知
        self._update_perception()
        
        # 更新记忆 - 优化版本
        self._update_memory(previous_perception)
        # 感知版本号：完整更新后递增
        self._perception_version = getattr(self, '_perception_version', 0) + 1

        # 生成供战斗模块复用的“战斗快照”，避免其重复聚合
        if hasattr(self, '_refresh_combat_snapshot'):
            # 每 ≥1500ms 且在感知/记忆变化或强制更新时才刷新快照
            last_call = getattr(self, '_last_snapshot_call_time', 0)
            last_per_size = getattr(self, '_last_snapshot_perception_size', -1)
            last_mem_size = getattr(self, '_last_snapshot_memory_size', -1)
            should_snapshot = (
                current_time - last_call >= 1500 and (
                    last_per_size != len(self.perception) or
                    last_mem_size != len(self.memory) or
                    needs_forced_update or
                    position_changed
                )
            )
            if should_snapshot:
                self._refresh_combat_snapshot()
                self._last_snapshot_call_time = current_time
                self._last_snapshot_perception_size = len(self.perception)
                self._last_snapshot_memory_size = len(self.memory)
        
        # 内存管理 - 定期释放Python GC不会立即回收的内存
        # (_last_gc_time 已在 Player.__init__ 预初始化)
        current_time = self.world.time
        if current_time - self._last_gc_time > 60000:  # 每60秒游戏时间进行一次
            self._last_gc_time = current_time
            
            # 清除无用的大型缓存，减少内存占用
            self._clear_vision_cache()
            
            # 重置增量更新系统，强制下次完整更新
            self._force_full_update = True
            
            # 如果程序有内存压力，可以在这里调用gc.collect()

    def _lightweight_memory_update(self):
        """轻量级记忆更新 - 在感知未变化时仅做必要的记忆清理"""
        current_time = self.world.time
        
        # 简化的记忆过期检查
        if hasattr(self, '_last_memory_cleanup'):
            time_since_cleanup = current_time - self._last_memory_cleanup
            if time_since_cleanup < 5000:  # 5秒内不需要记忆清理
                return
                
        # 只做基本的记忆过期清理
        units_to_forget = []
        for m in self.memory:
            # 只检查明确过期的条件，跳过昂贵的should_be_seeing检查
            if (m.initial_model.place is None or
                self._expire_memory_if_stale(m, current_time)):
                units_to_forget.append(m)
        
        # 批量遗忘
        for m in units_to_forget:
            self._forget(m)
            
        self._last_memory_cleanup = current_time

    def _expire_memory_if_stale(
        self, memory, current_time, display_expired_initial_models=None
    ):
        """Return True when an old moving-unit memory must be forgotten.

        In shared-vision games a remembered enemy can remain in ``perception``
        through an alliance cache even after it is no longer actually visible.
        When the sighting reaches the display limit, drop that stale perception
        entry too; genuinely visible units are kept. AI can still keep a longer
        internal memory for decisions.
        """
        unit = memory.initial_model
        if not unit.speed:
            return False
        display_duration = getattr(self, "display_memory_duration", self.memory_duration)
        display_expired = memory.time_stamp + display_duration < current_time
        if display_expired and unit in self.perception and not self._is_seeing(unit):
            self.perception.discard(unit)
            if display_expired_initial_models is not None:
                display_expired_initial_models.add(unit)
        return memory.time_stamp + self.memory_duration < current_time

    def _memory_visible_for_display(self, memory, current_time):
        unit = memory.initial_model
        if not unit.speed:
            return True
        display_duration = getattr(self, "display_memory_duration", self.memory_duration)
        return memory.time_stamp + display_duration >= current_time

    def memory_for_display(self):
        current_time = self.world.time
        return {
            memory for memory in self.memory
            if self._memory_visible_for_display(memory, current_time)
        }

    def _refresh_combat_snapshot(self):
        """构建战斗快照，供战斗模块直接读取，减少重复聚合成本。
        时间桶：250ms
        内容：
          - place_enemy_menace: {Square -> menace_sum}
          - enemy_presence_places: [Square]
          - corpse_places: set(Square)
          - friend_places: set(Square)
        """
        current_time = self.world.time
        time_bucket = current_time // 250
        if getattr(self, '_combat_snapshot_bucket', -1) == time_bucket:
            return

        place_enemy_menace = {}
        enemy_presence_places = []
        corpse_places = set()
        friend_places = set()

        # 准备集合引用，减少属性访问
        perceived = self.perception
        mem_set = self.memory

        # 预先构建敌我玩家ID集合，加速归类判断（按玩家+节流缓存）
        if not hasattr(self.__class__, '_relation_cache'):
            self.__class__._relation_cache = {}
        rel_key = self.id
        rel_entry = self.__class__._relation_cache.get(rel_key)
        if not rel_entry or current_time - rel_entry['ts'] > 1000:
            try:
                enemy_ids = {p.id for p in self.world.players if self.player_is_a_hostile_enemy(p)}
                allied_ids = {p.id for p in self.allied}
            except Exception:
                enemy_ids = set()
                allied_ids = set()
            self.__class__._relation_cache[rel_key] = {'ts': current_time, 'enemy': enemy_ids, 'allied': allied_ids}
            enemy_player_ids = enemy_ids
            allied_player_ids = allied_ids
        else:
            enemy_player_ids = rel_entry['enemy']
            allied_player_ids = rel_entry['allied']

        # 敌方单位（感知 + 记忆）聚合威胁（增量：与上次快照对比差异）
        last_perceived = getattr(self, '_last_snapshot_perceived', None)
        last_memory = getattr(self, '_last_snapshot_memory', None)
        # 初次或无快照：走全量
        if last_perceived is None or last_memory is None:
            iter_perceived = perceived
            iter_memory = mem_set
            added_perceived = set()
            removed_perceived = set()
            added_memory = set()
            removed_memory = set()
        else:
            added_perceived = perceived - last_perceived
            removed_perceived = last_perceived - perceived
            added_memory = mem_set - last_memory
            removed_memory = last_memory - mem_set
            # 仅增量处理：新出现与刚消失的单位需要调整聚合
            iter_perceived = added_perceived
            iter_memory = added_memory

        # D-Phase 2: 移除热路径 getattr.
        # o.player/o.place/o.menace 都在 Entity 类有 class-level default
        # (None/None/0); o.is_inside 是 Entity @property; 直接访问.
        # 唯一保留 getattr 的是 is_vulnerable: Entity 默认 False, 但本函数旧
        # 默认 True (对没有 is_vulnerable 字段的对象当成可攻击); 由于 Entity
        # 已加 class default, 现在 o.is_vulnerable 永远存在 → 行为是
        # "Entity default False (e.g. Resource/Item/Memory) 视为不可攻击",
        # 这与"对没有该字段的对象视为可攻击"语义不同. 检查后实测 perception
        # 内有效目标 (Creature) 都正确 override 为 True; Resource/Item/Corpse
        # 等本就不应进入威胁聚合, 跳过它们更符合 menace 计算的意图.

        # 全量或增量地加和来自感知的敌人
        for o in iter_perceived:
            p = o.player
            if p is None:
                continue
            if o.is_inside or not o.is_vulnerable:
                continue
            if p.id not in enemy_player_ids:
                continue
            pl = o.place
            if pl is None:
                continue
            men = o.menace
            current_sum = place_enemy_menace.get(pl)
            if current_sum is None:
                place_enemy_menace[pl] = men
                enemy_presence_places.append(pl)
            else:
                place_enemy_menace[pl] = current_sum + men

        # 记忆中的敌人给予折扣威胁 (memory 对象有 initial_model)
        for rem in iter_memory:
            o = rem.initial_model if hasattr(rem, 'initial_model') else rem
            p = o.player
            if p is None:
                continue
            if o.is_inside or not o.is_vulnerable:
                continue
            if p.id not in enemy_player_ids:
                continue
            pl = o.place
            if pl is None or pl in enemy_presence_places:
                continue
            men = o.menace // 2
            current_sum = place_enemy_menace.get(pl)
            if current_sum is None:
                place_enemy_menace[pl] = men
                enemy_presence_places.append(pl)
            else:
                place_enemy_menace[pl] = current_sum + men

        # 处理消失的单位：从聚合中减去它们贡献（仅在存在上次快照时）
        if last_perceived is not None and last_memory is not None:
            for o in removed_perceived:
                p = o.player
                if p is None or p.id not in enemy_player_ids:
                    continue
                if o.is_inside or not o.is_vulnerable:
                    continue
                pl = o.place
                if pl is None:
                    continue
                men = o.menace
                if pl in place_enemy_menace:
                    place_enemy_menace[pl] -= men
                    if place_enemy_menace[pl] <= 0:
                        del place_enemy_menace[pl]
                        if pl in enemy_presence_places:
                            try:
                                enemy_presence_places.remove(pl)
                            except ValueError:
                                pass
            for rem in removed_memory:
                o = rem.initial_model if hasattr(rem, 'initial_model') else rem
                p = o.player
                if p is None or p.id not in enemy_player_ids:
                    continue
                if o.is_inside or not o.is_vulnerable:
                    continue
                pl = o.place
                if pl is None:
                    continue
                men = o.menace // 2
                if pl in place_enemy_menace:
                    place_enemy_menace[pl] -= men
                    if place_enemy_menace[pl] <= 0:
                        del place_enemy_menace[pl]
                        if pl in enemy_presence_places:
                            try:
                                enemy_presence_places.remove(pl)
                            except ValueError:
                                pass

        # 尸体与友军位置：≥2000ms 才刷新一次，否则复用上次结果
        last_extras_ts = getattr(self, '_snapshot_extras_time', 0)
        if current_time - last_extras_ts >= 2000:
            tmp_corpse = set()
            tmp_friend = set()
            for o in perceived:
                # 尸体位置
                if isinstance(o, Corpse):
                    pl = o.place
                    if isinstance(pl, Square):
                        tmp_corpse.add(pl)
                    continue
                # 友军位置 - D-Phase 2 直接属性访问
                p = o.player
                if p is None:
                    continue
                if p.id in allied_player_ids:
                    if isinstance(o.place, Square) and o.is_vulnerable and not o.is_inside:
                        tmp_friend.add(o.place)
            self._snapshot_corpse_places = tmp_corpse
            self._snapshot_friend_places = tmp_friend
            self._snapshot_extras_time = current_time

        corpse_places = set(getattr(self, '_snapshot_corpse_places', set()))
        friend_places = set(getattr(self, '_snapshot_friend_places', set()))

        # 写入快照
        self._combat_snapshot = {
            'place_enemy_menace': place_enemy_menace,
            'enemy_presence_places': enemy_presence_places,
            'corpse_places': corpse_places,
            'friend_places': friend_places,
            'bucket': time_bucket,
            'timestamp': current_time,
        }
        self._combat_snapshot_bucket = time_bucket
        # 保存用于下次增量的快照集合引用（浅拷贝为set，避免后续被修改）
        try:
            self._last_snapshot_perceived = set(perceived)
            self._last_snapshot_memory = set(mem_set)
        except Exception:
            self._last_snapshot_perceived = None
            self._last_snapshot_memory = None



    def _incremental_perception_update(self, moved_units):
        """增量更新：仅根据少量移动单位更新覆盖网格与感知。
        目标：在不整帧重算的情况下，让 AI 使用到同步且足够准确的视野。
        """
        # (_vision_cover_counts 已在 Player.__init__ 预初始化;
        #  observed_squares 已在 Player.__init__ (base.py) 预初始化为 set())
        # 防御性 None 检查保留, 极端情况下 _update_perception 可能尚未运行.
        if self._vision_cover_counts is None:
            self._vision_cover_counts = {}
        if self.observed_squares is None:
            self.observed_squares = set()

        current_time = self.world.time
        time_bucket = current_time // 250

        # 需要追踪新增/移除的严格观察方格
        newly_strict = set()
        removed_strict = set()

        # 出于确定性考虑，按单位 id 排序处理
        for unit in sorted(moved_units, key=lambda u: u.id):
            if unit.is_inside or not unit.place:
                continue

            # 读取上次覆盖（若有）
            last_strict = getattr(unit, '_last_coverage_strict', None)

            # 读取或计算本帧覆盖
            observed_data = unit.get_observed_squares_optimized() if hasattr(unit, 'get_observed_squares_optimized') else {
                'strict': set(unit.get_observed_squares()),
                'all': set(unit.get_observed_squares())
            }
            strict_now = set(observed_data['strict'])

            # 计算差分
            if last_strict is None:
                inc = strict_now
                dec = set()
            else:
                inc = strict_now - last_strict
                dec = last_strict - strict_now

            # 写入单位级快照
            unit._last_coverage_strict = strict_now
            unit._cached_observed_squares = strict_now
            unit._cached_observed_time = time_bucket

            # 应用到全局覆盖计数与玩家观察集合
            for sq in inc:
                self._vision_cover_counts[sq] = self._vision_cover_counts.get(sq, 0) + 1
                if self._vision_cover_counts[sq] > 0:
                    self.observed_squares.add(sq)
            for sq in dec:
                if sq in self._vision_cover_counts:
                    self._vision_cover_counts[sq] -= 1
                    if self._vision_cover_counts[sq] <= 0:
                        del self._vision_cover_counts[sq]
                        if sq in self.observed_squares:
                            self.observed_squares.remove(sq)

            newly_strict.update(inc)
            removed_strict.update(dec)

        # 更新历史观察
        if newly_strict:
            self.strictly_observed_before_squares.update(newly_strict)

        # 静态对象批量处理：仅处理新进入严格观察的方格
        if newly_strict:
            static_objects = set()
            for s in newly_strict:
                objs = getattr(s, 'objects', None)
                if objs:
                    static_objects.update([o for o in objs if o.player is None])
            if static_objects:
                self.perception.update(static_objects)

        # 敌方单位：仅检查新进入严格观察的方格，避免全量扫描
        if newly_strict:
            for s in newly_strict:
                objs = getattr(s, 'objects', None)
                if not objs:
                    continue
                for o in objs:
                    if o.player is None:
                        continue
                    if o.is_inside:
                        continue
                    if (o.is_invisible or o.is_cloaked) and o not in getattr(self, 'detected_units', set()):
                        continue
                    if self.is_an_enemy(o):
                        if self._is_seeing(o):
                            self.perception.add(o)

        # 处理失去严格观察的区域：移除不再可见的对象，避免感知集“漏删”
        if removed_strict:
            for s in removed_strict:
                if s not in self.observed_squares:
                    objs = list(getattr(s, 'objects', ()))
                    if not objs:
                        continue
                    for o in objs:
                        if o.player is None and o in self.perception:
                            self.perception.discard(o)
                    for o in objs:
                        if o.player is None:
                            continue
                        # 仅对敌方单位做可见性校验并可能移除；友军/己方单位保持可见，
                        # 以与完整更新路径的“添加盟友单位”逻辑保持一致
                        if o in self.perception and self.is_an_enemy(o) and not self._is_seeing(o):
                            self.perception.discard(o)
        # 确保移动的友军单位始终在感知集中（与完整更新路径保持一致行为）
        # 这是必要的，因为增量移除步骤可能会把不在严格观察区内的友军从感知中移除，
        # 而完整更新会无条件把盟友单位加入感知。
        for unit in moved_units:
            if getattr(unit, 'player', None) is not None and unit.place is not None and not getattr(unit, 'is_inside', False):
                self.perception.add(unit)
        # 结束时不直接在此处递增版本（由调用者控制），避免重复递增
    def force_perception_update(self):
        """强制在下次更新时刷新感知系统"""
        self._force_perception_update = True

    def observe(self, o):
        # for example: a catapult firing from an unknown place
        # doesn't work for invisible units (hints are given in Starcraft though)
        if getattr(o, "_is_skill_combat_proxy", False):
            from ..skill_combat import resolve_combat_attacker

            o = resolve_combat_attacker(o)
        if o.is_invisible or o.is_cloaked:
            return  # don't observe dark archers
        self.observed_objects[o] = self.world.time + 3000

    def _memorize(self, o):
        # 优化：缓存当前时间，避免重复访问
        # (_memory_index 已在 Player.__init__ (base.py:77) 初始化)
        current_time = self.world.time

        if o in self._memory_index:
            # 简单更新时间戳，避免不必要的操作
            self._memory_index[o].time_stamp = current_time
        else:
            # 优化：减少copy开销，创建轻量级记忆对象
            remembrance = copy.copy(o)
            remembrance.time_stamp = current_time
            remembrance.initial_model = o
            self.memory.add(remembrance)
            self._memory_index[o] = remembrance

    def _forget(self, o):  # o is a memory object
        # 更稳健：使用 discard 避免 KeyError（可能已在其他清理路径中被移除）
        self.memory.discard(o)
        try:
            del self._memory_index[o.initial_model]
        except KeyError:  # a test requires this to pass
            pass
        o.place = None  # make sure this object is not reused

    def remembers(self, actual_object):
        for remembrance in self.memory:
            if remembrance.initial_model is actual_object:
                return True

    def send_event(self, o, e):
        """发送事件给客户端"""
        if self.is_local_human():
            self.client.push("event", copy.copy(o), e)

    @property
    def unknown_starting_squares(self) -> List[Square]:
        starting_squares = [self.world.grid[n] for n in self.world.starting_squares]
        result = [
            s
            for s in starting_squares
            if s not in self.strictly_observed_before_squares
        ]
        return self.world.random.sample(result, len(result))

    @property
    def unknown_squares(self) -> List[Square]:
        result = [
            p
            for p in self.world.squares
            if p not in self.strictly_observed_before_squares
        ]
        return self.world.random.sample(result, len(result))

    @property
    def squares_to_watch(self) -> List[Square]:
        squares = set()  # desync risk
        for m in self.memory:  # desync risk
            # Round 4: m.place 默认 None; _Space.is_inside_place 默认 False
            p = m.place
            if p is not None and p.is_inside_place:
                continue
            if self.is_an_enemy(m):
                squares.add(p)
                for e in getattr(m.place, "exits", []):
                    if e.other_side is not None:
                        squares.add(e.other_side.place)
            elif isinstance(m, Deposit):
                squares.add(m.place)
        result = sorted(squares, key=lambda s: s.name)  # avoid desync
        return self.world.random.sample(result, len(result))