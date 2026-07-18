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

try:
    from soundrts.world.world_ecs import ecs_enabled as _ecs_enabled_flag
except ImportError:
    def _ecs_enabled_flag():
        return False

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
        # Class default blocked_exit=None — skip observed-square walk for normal units.
        if getattr(unit, "blocked_exit", None) is None:
            return False
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
        # Same place re-queried many times per tick (decide/can_attack).
        # Mutate list in-place — Player.__setattr__ is expensive (69M calls).
        hit = self._known_enemies_hit
        if place is hit[0] and current_time == hit[1]:
            return hit[2]

        # Per-place cache before rebuilding enemy unit lists (was done every miss).
        known_time = self._known_enemies_time.get(place)
        if known_time == current_time:
            result = self._known_enemies[place]
            hit[0] = place
            hit[1] = current_time
            hit[2] = result
            return result

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

        # 每 tick 级集合缓存（舱内单位列表一并缓存，避免 known_enemies
        # 每次对全体敌人扫 is_inside）
        if self._enemy_units_set_time == current_time:
            enemy_units_set = self._enemy_units_set
            enemy_inside = self._enemy_inside_units
        else:
            enemy_units_set = set(self._enemy_units_cache)
            if _fast is not None and hasattr(_fast, "filter_inside_units"):
                enemy_inside = tuple(_fast.filter_inside_units(enemy_units_set))
            else:
                enemy_inside = tuple(
                    u
                    for u in enemy_units_set
                    if (u.place is not None and u.place.is_inside_place)
                )
            self._enemy_units_set = enemy_units_set
            self._enemy_inside_units = enemy_inside
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
        # Open-container passengers (Cython + Python paths).
        for obj in enemy_inside:
            if obj.is_vulnerable and obj not in result:
                container = getattr(getattr(obj, "place", None), "container", None)
                if container_visible_from_place(container, place):
                    result.append(obj)
        self._known_enemies[place] = result
        self._known_enemies_time[place] = current_time
        hit[0] = place
        hit[1] = current_time
        hit[2] = result
        return result

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
        buckets = getattr(self, "_buckets", None)
        if buckets is None:
            buckets = self._buckets = {}

        def _merge():
            if _fast is not None:
                return _fast.merge_buckets_3x3(buckets, grid_x, grid_y)
            result = []
            for dx in (0, 1, -1):
                for dy in (0, 1, -1):
                    k = grid_x + dx, grid_y + dy
                    if k in buckets:
                        result.extend(buckets[k])
            return result

        # 如果需要跳过缓存（用于harm_nearby_units等功能）
        if skip_cache:
            return _merge()

        # 缓存键必须包含玩家 id：每条 computer_only 行是独立 Computer 玩家，
        # 同 Player 子类共享类级缓存；若只用格子坐标，先查询的空电脑会
        # 把「无单位」写入缓存，后查询的有单位电脑会误命中空列表（流星等
        # harm 范围技能因此打不到地图 computer 单位）。
        cache_key = (id(self), grid_x, grid_y)
        cls = self.__class__
        cache = getattr(cls, "_global_neighbors_cache", None)
        if cache is None:
            cache = {}
            cls._global_neighbors_cache = cache
            cls._global_neighbors_timestamp = {}
            cls._last_cleanup_time = self.world.time

        current_time = self.world.time
        if current_time - cls._last_cleanup_time > 30000:
            if len(cache) > 1000:
                recent_keys = sorted(
                    cls._global_neighbors_timestamp.keys(),
                    key=lambda k: cls._global_neighbors_timestamp[k],
                    reverse=True,
                )[:1000]
                new_cache = {}
                new_timestamps = {}
                for k in recent_keys:
                    new_cache[k] = cache[k]
                    new_timestamps[k] = cls._global_neighbors_timestamp[k]
                cache = new_cache
                cls._global_neighbors_cache = new_cache
                cls._global_neighbors_timestamp = new_timestamps
            cls._last_cleanup_time = current_time

        hit = cache.get(cache_key)
        if hit is not None:
            cls._global_neighbors_timestamp[cache_key] = current_time
            return hit

        result = _merge()
        cache[cache_key] = result
        cls._global_neighbors_timestamp[cache_key] = current_time
        return result

    def _clear_neighbors_cache(self):
        """Invalidate neighbor merge cache entries for *this* player only.

        Cache keys are ``(id(player), grid_x, grid_y)``; do not wipe other
        players that share the class-level dict.
        """
        cls = self.__class__
        cache = getattr(cls, "_global_neighbors_cache", None)
        if not cache:
            return
        token = id(self)
        ts = getattr(cls, "_global_neighbors_timestamp", None)
        for key in [k for k in cache if k[0] == token]:
            del cache[key]
            if ts is not None:
                ts.pop(key, None)

    def _invalidate_neighbors_near(self, dirty_cells, player_token=None):
        """Drop neighbor-cache entries affected by dirty bucket cells.

        A query at (gx, gy) reads the 3x3 around that cell. If bucket cell
        (bx, by) changed, every query with |gx-bx|<=1 and |gy-by|<=1 is stale.

        When *dirty_cells* is large, fall back to full clear (selective scan
        used to cost more than the cache itself on chaotic battles).
        Does not touch vision / perception caches.
        """
        if not dirty_cells:
            return
        cls = self.__class__
        cache = getattr(cls, "_global_neighbors_cache", None)
        if not cache:
            return
        # Heuristic: many dirty cells → O(cache) selective scan loses to clear.
        if len(dirty_cells) > 48 or len(cache) <= len(dirty_cells) * 4:
            self._clear_neighbors_cache()
            return

        token = id(self) if player_token is None else player_token
        ts = getattr(cls, "_global_neighbors_timestamp", None)
        dirty = dirty_cells if isinstance(dirty_cells, set) else set(dirty_cells)
        # Queries reading a dirty bucket cell: all (gx,gy) within Chebyshev 1.
        affected = set()
        for bx, by in dirty:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    affected.add((bx + dx, by + dy))
        to_del = []
        for key in cache:
            if key[0] != token:
                continue
            if (key[1], key[2]) in affected:
                to_del.append(key)
        for key in to_del:
            del cache[key]
            if ts is not None:
                ts.pop(key, None)

    def _is_seeing(self, u):
        """1.3.8.1-style: Euclidean sight vs allied observers (no quota / prefilter).

        Temporarily used for playtesting vs the optimized strict/partial+150 path
        (see backup_perception_pre_1381style_20260714/).

        ECS SoA observer APIs are reserved for future *batch* visibility; the
        single-target path stays on warm ``_potential_neighbors`` (neighbor cache).
        """
        if _fast is not None:
            return bool(_fast.is_seeing(self, u))
        return self._py_is_seeing(u)

    def _py_is_seeing(self, u):
        """Python fallback — byte-equivalent to ``perception_fast.is_seeing``."""
        # 如果单位是隐形或隐身的，并且没有被探测，则不可见
        if (u.is_invisible or u.is_cloaked) and u not in self.detected_units:
            return False

        place = u.place
        if place is None:
            return False

        # 墙/门等出口阻挡物：站在出口任一侧或相邻格观察时，应能看到阻挡物本身
        if getattr(u, "blocked_exit", None) is not None and self._exit_blocker_visible(u):
            return True

        x = u.x
        y = u.y
        for avp in self.allied_vision:
            for avu in avp._potential_neighbors(x, y):
                if getattr(avu, "is_inside", False):
                    continue
                sr = avu.sight_range
                if not sr:
                    continue
                dx = avu.x - x
                dy = avu.y - y
                if dx * dx + dy * dy >= sr * sr:
                    continue
                # get_observed_squares() defaults to strict=False（含邻格高度/通行规则）
                if place in avu.get_observed_squares():
                    return True
        return False

    def _is_within_allied_sight_range(self, u):
        """Alias kept for callers/tests; same as 1.3.8.1 ``_is_seeing`` body."""
        return self._is_seeing(u)

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

        # 每180ms切换一个玩家组进行视野更新（9 组 → 单玩家约 1.6s 一轮）
        if current_time - cls._last_global_update_time > 180:
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
            
        # 初始化感知相关集合（new_enemy 由外层 previous_perception 差集计算，避免二次 copy）
        self.perception = set()
        self.observed_squares = set()
        partially_observed_squares = set()
        # 覆盖计数网格（严格观察）：用于O(1)可见性判定与增量处理
        self._vision_cover_counts = {}
        
        # 使用联盟视野缓存机制，减少每tick的计算量
        # (_allied_vision_cache / _allied_vision_timestamp 已在 Player 类体声明)
        current_time = self.world.time
        vision_cache_key = current_time // 500  # 联盟视野拓扑桶（非跨 tick 战斗视野）

        # 创建或使用联盟缓存 - 必须按 allied_vision（实际共享迷雾的玩家），
        # 不能用 self.allied：computer_only 仍同属 "ai" 但不共享迷雾，
        # 若用 allied 作键会把第一个 NPC 的视野错发给其它 NPC。
        # (_cached_allied_ids / _cached_allied_time 已在 Player.__init__ 预初始化)
        if self._cached_allied_time != current_time // 1000:
            self._cached_allied_ids = tuple(
                sorted(ally.id for ally in self.allied_vision)
            )
            self._cached_allied_time = current_time // 1000

        alliance_key = self._cached_allied_ids
        if alliance_key in self.__class__._allied_vision_cache and self.__class__._allied_vision_timestamp.get(alliance_key) == vision_cache_key:
            # 命中缓存：直接引用，本路径不再 mutate 这两个 set
            cached_vision = self.__class__._allied_vision_cache[alliance_key]
            self.observed_squares = cached_vision['observed_squares']
            partially_observed_squares = cached_vision['partially_observed_squares']
            # 覆盖计数：优先复用缓存中的真实计数；旧缓存条目退回全 1。
            # 必须 copy——增量感知会原地 mutate _vision_cover_counts。
            cached_covers = cached_vision.get("cover_counts")
            if cached_covers is not None:
                self._vision_cover_counts = dict(cached_covers)
            else:
                self._vision_cover_counts = {sq: 1 for sq in self.observed_squares}
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
            
            # 保存联盟视野缓存（含 cover_counts，命中时免重建）
            self.__class__._allied_vision_cache[alliance_key] = {
                'observed_squares': self.observed_squares.copy(),
                'partially_observed_squares': partially_observed_squares.copy(),
                'cover_counts': dict(self._vision_cover_counts),
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
        self.partially_observed_squares = partially_observed_squares
        self.observed_before_squares.update(partially_observed_squares)
        self.strictly_observed_before_squares.update(self.observed_squares)

        # 视野方格未变时复用静态感知，跳过昂贵的 bulk 距离检查
        prev_obs = getattr(self, "_prev_obs_squares", None)
        prev_partial = getattr(self, "_prev_partial_squares", None)
        cached_static = getattr(self, "_cached_static_perception", None)
        vision_unchanged = (
            prev_obs is not None
            and prev_partial is not None
            and prev_obs == self.observed_squares
            and prev_partial == partially_observed_squares
            and cached_static is not None
        )
        if vision_unchanged:
            self.perception.update(cached_static)
        else:
            # 严格观察区：静态对象直接可见
            static_objects = set()
            for s in self.observed_squares:
                objs = s.objects
                if objs:
                    for o in objs:
                        if o.player is None:
                            static_objects.add(o)
            if static_objects:
                self.perception.update(static_objects)
                self._memorize_unseen_exit_pairs(static_objects)

            # 部分观察区：与 1.3.8.1 一致——看见的进感知，看不见的进雾战记忆。
            # 昂贵的欧氏可见性检查仍可按配额截断；配额外的静态对象必须直接
            # memorize，否则战云格会只剩出口（出口另有 _memorize_unseen_exit_pairs）
            # 而草地/矿点/树林消失，直到单位到场才重新显示。
            objects_to_check = set()
            for s in partially_observed_squares:
                objs = s.objects
                if objs:
                    for o in objs:
                        if o.player is None:
                            objects_to_check.add(o)

            if objects_to_check:
                _BULK_STATIC_CAP = 100
                visibility_set = objects_to_check
                overflow_to_memory = set()
                if len(objects_to_check) > _BULK_STATIC_CAP:
                    # 先装重要目标，再补其余；避免对整表 sort（曾 ~2 万次/局）
                    capped = []
                    for o in objects_to_check:
                        if isinstance(o, Deposit) or o.is_a_building_land:
                            capped.append(o)
                    if len(capped) > _BULK_STATIC_CAP:
                        capped.sort(key=lambda o: o.id if o.id is not None else 0)
                        capped = capped[:_BULK_STATIC_CAP]
                    elif len(capped) < _BULK_STATIC_CAP:
                        rest = [
                            o
                            for o in objects_to_check
                            if not (isinstance(o, Deposit) or o.is_a_building_land)
                        ]
                        rest.sort(key=lambda o: o.id if o.id is not None else 0)
                        capped.extend(rest[: _BULK_STATIC_CAP - len(capped)])
                    visibility_set = set(capped)
                    overflow_to_memory = objects_to_check - visibility_set
                visible_objects, memory_objects = self._bulk_visibility_check(
                    visibility_set
                )
                self.perception.update(visible_objects)
                static_objects.update(visible_objects)
                # 配额内看不见的 + 配额外未检查的：进雾战记忆（1.3.8.1 语义）。
                # 用 ensure（只补尚未记忆的），避免强制全量感知时每秒对
                # 上百个静态对象做 copy.copy / 刷新 time_stamp。
                to_ensure = set(memory_objects) | overflow_to_memory
                if to_ensure:
                    self._ensure_static_fog_memory(to_ensure)
                self._memorize_unseen_exit_pairs(visible_objects)
                if to_ensure:
                    self._memorize_unseen_exit_pairs(to_ensure)

            self._cached_static_perception = static_objects
            self._prev_obs_squares = set(self.observed_squares)
            self._prev_partial_squares = set(partially_observed_squares)

        # 处理联盟观察到的对象 - 使用联盟视野缓存
        av_cache = self.__class__._allied_vision_cache.get(alliance_key)
        if av_cache is not None and "observed_objects" in av_cache:
            # place 在写入时已过滤；只剔除本桶内被删的对象
            cached_observed = av_cache["observed_objects"]
            if cached_observed:
                self.perception.update(
                    o for o in cached_observed if o.place is not None
                )
        else:
            # 处理观察到的对象
            observed_objects_to_add = set()
            for p in self.allied_vision:
                valid_objects = {
                    o
                    for o, t in p.observed_objects.items()
                    if t >= self.world.time and o.place is not None
                }
                invalid_objects = set(p.observed_objects.keys()) - valid_objects
                for o in invalid_objects:
                    del p.observed_objects[o]
                observed_objects_to_add.update(valid_objects)

            self.perception.update(observed_objects_to_add)

            if av_cache is not None:
                av_cache["observed_objects"] = observed_objects_to_add

        # 添加盟友单位 - 使用联盟缓存优化
        if av_cache is not None and "allied_units" in av_cache:
            # 命中缓存：信任同 vision_cache_key 周期内的列表（存入时已过滤 place）
            self.perception.update(av_cache["allied_units"])
        else:
            allied_units = set()
            for p in self.allied_vision:
                for u in p.units:
                    if u.place is not None:
                        allied_units.add(u)
            self.perception.update(allied_units)

            if av_cache is not None:
                av_cache["allied_units"] = allied_units

        # 处理敌方单位 —— 临时改回 1.3.8.1：每个敌人都跑欧氏 ``_is_seeing``，
        # 不做观察区预筛 / 150 配额（备份见 backup_perception_pre_1381style_20260714/）。
        # ECS=1：批量可见性（按敌军格分组 + SoA 欧氏），语义对齐 ``_is_seeing``。
        # vision_places = 严格∪部分：欧氏前剔除不可能通过 place∈observed 的敌人
        #（出口阻挡物仍在 batch_see 内单独处理，不依赖此集合）。
        enemy_units = set()
        # Cache enemy player list (allied_vision rarely changes mid-second).
        ep_bucket = current_time // 1000
        if (
            self._enemy_players_batch_bucket != ep_bucket
            or self._enemy_players_batch is None
        ):
            self._enemy_players_batch = [
                p for p in self.world.players if p not in self.allied_vision
            ]
            self._enemy_players_batch_bucket = ep_bucket
        enemy_players = self._enemy_players_batch

        ecs = getattr(self.world, "_ecs", None)
        use_batch = (
            ecs is not None
            and _ecs_enabled_flag()
            and hasattr(ecs, "batch_see_enemies")
        )

        vision_places = self.observed_squares | partially_observed_squares

        if use_batch:
            flat = []
            for p in enemy_players:
                flat.extend(p.units)
            enemy_units = ecs.batch_see_enemies(self, flat, A, vision_places)
            for u in flat:
                if u in enemy_units:
                    continue
                pl = u.place
                if pl is not None and pl.is_inside_place and self._open_container_passenger_visible(u):
                    enemy_units.add(u)
        else:
            for p in enemy_players:
                for u in p.units:
                    if self._is_seeing(u):
                        enemy_units.add(u)
                    else:
                        pl = u.place
                        if pl is not None and pl.is_inside_place and self._open_container_passenger_visible(u):
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

    def _record_new_enemy_units(self, previous_perception):
        """Diff perception for UI / alert (was inlined in _update_perception)."""
        new_perception = self.perception - previous_perception
        new_enemy_candidates = []
        for o in new_perception:
            if self.is_an_enemy(o) and not getattr(
                getattr(o, "player", None), "neutral", False
            ):
                p = o.place
                if p is None or not p.is_inside_place:
                    new_enemy_candidates.append(o)
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
        objects = self._expand_unseen_exit_pairs(objects)
        if _fast is not None:
            _fast.bulk_memorize(self, objects)
            return
        self._py_bulk_memorize(objects)

    def _expand_unseen_exit_pairs(self, objects):
        """Seeing/remembering one exit must also fog-remember its other side.

        Exits are paired across squares; incremental leave can keep only one side
        (e.g. a2 south found, a1 north missing). Cheap: only walks the given
        objects, not the whole map.
        """
        if not objects:
            return objects
        observed = self.observed_squares
        perception = self.perception
        index = self._memory_index
        extra = []
        for o in objects:
            # Exit.is_an_exit is a class bool; skip non-exits without getattr.
            if not o.is_an_exit:
                continue
            try:
                other = o.other_side
            except Exception:
                continue
            if other is None:
                continue
            if other in perception or other in index:
                continue
            place = other.place
            if place is not None and place in observed:
                continue
            extra.append(other)
        if not extra:
            return objects
        if isinstance(objects, set):
            out = set(objects)
            out.update(extra)
            return out
        return list(objects) + extra

    def _memorize_unseen_exit_pairs(self, objects):
        """Remember the far side of exits just added to perception."""
        pairs = self._expand_unseen_exit_pairs(objects)
        if pairs is objects:
            return
        # Only the newly expanded far sides (not already in ``objects``).
        if isinstance(objects, set):
            only_pairs = pairs - objects
        else:
            obj_ids = {id(o) for o in objects}
            only_pairs = [o for o in pairs if id(o) not in obj_ids]
        if only_pairs:
            # Bypass expand-again by calling py/fast directly on pairs only.
            if _fast is not None:
                _fast.bulk_memorize(self, only_pairs)
            else:
                self._py_bulk_memorize(only_pairs)

    def _ensure_static_fog_memory(self, objects):
        """把尚未进雾战记忆的静态对象补进记忆；已存在的跳过。

        静态地形（草地/矿/出口等）不按时间过期，强制感知刷新时不必对
        已记忆条目再跑 bulk_memorize（会 copy/刷 time_stamp）。只补缺即可
        同时保证不丢对象和控制性能。
        """
        if not objects:
            return
        index = self._memory_index
        missing = None
        for o in objects:
            if o in index:
                continue
            if getattr(o, "_is_skill_combat_proxy", False):
                continue
            if o.is_invisible or o.is_cloaked:
                continue
            if missing is None:
                missing = []
            missing.append(o)
        if missing:
            self._bulk_memorize(missing)

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
                self._memory_place_index_add(remembrance)

    def _memory_place_index_add(self, remembrance):
        """Track fog memory by square for O(observed) ghost clears."""
        pl = remembrance.place
        if pl is None:
            return
        by_place = getattr(self, "_memory_by_place", None)
        if by_place is None:
            by_place = {}
            self._memory_by_place = by_place
            self._memory_by_place_count = 0
        bag = by_place.get(pl)
        if bag is None:
            bag = set()
            by_place[pl] = bag
        bag.add(remembrance)
        self._memory_by_place_count = getattr(self, "_memory_by_place_count", 0) + 1

    def _memory_place_index_remove(self, remembrance, place):
        by_place = getattr(self, "_memory_by_place", None)
        if not by_place or place is None:
            return
        bag = by_place.get(place)
        if bag is None:
            return
        bag.discard(remembrance)
        if not bag:
            del by_place[place]
        count = getattr(self, "_memory_by_place_count", 0)
        if count > 0:
            self._memory_by_place_count = count - 1

    def _ensure_memory_by_place(self):
        """Rebuild place→memory index when stale (tests / pickle edge cases)."""
        by_place = getattr(self, "_memory_by_place", None)
        count = getattr(self, "_memory_by_place_count", -1)
        memory = self.memory
        if by_place is not None and count == len(memory):
            return by_place
        by_place = {}
        for m in memory:
            pl = m.place
            if pl is None:
                continue
            bag = by_place.get(pl)
            if bag is None:
                bag = set()
                by_place[pl] = bag
            bag.add(m)
        self._memory_by_place = by_place
        self._memory_by_place_count = len(memory)
        return by_place

    def _update_memory(self, previous_perception):
        self.observed_before_squares.update(self.observed_squares)
        
        # 预先获取当前时间，避免重复访问
        current_time = self.world.time
        memory_expires_time = current_time - self.memory_duration
        
        # 优化10：记忆清理频率控制 - 避免每次都检查昂贵的should_be_seeing
        # (_last_memory_cleanup / _memory_scan_cursor / _memory_list /
        #  _memory_list_snapshot_time 已在 Player.__init__ 预初始化)
        should_do_full_cleanup = (current_time - self._last_memory_cleanup) >= 3000

        # 当执行完整清理或内存快照过期时刷新快照
        if should_do_full_cleanup or (current_time - self._memory_list_snapshot_time > 3000):
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
        cleanup_quota = 200 + (total_units // 80)
        display_expired_initial_models = set()

        # 选择扫描集合：完整清理时扫描全部，否则仅扫描批次
        if should_do_full_cleanup:
            iterable_memories = self._memory_list  # 使用快照以获得稳定顺序
        else:
            # 自适应批次：随单位量缩放（收紧以降低 _is_seeing 压力）
            BATCH = 120 + (total_units // 120)
            start = self._memory_scan_cursor
            end = min(start + BATCH, len(self._memory_list))
            iterable_memories = self._memory_list[start:end]
            # 更新游标（环形）
            self._memory_scan_cursor = 0 if end >= len(self._memory_list) else end

        perception = self.perception
        observed = self.observed_squares
        display_duration = getattr(
            self, "display_memory_duration", self.memory_duration
        )

        if _fast is not None and hasattr(_fast, "scan_memories_for_forget"):
            to_forget, display_expired_initial_models = _fast.scan_memories_for_forget(
                iterable_memories,
                perception,
                observed,
                current_time,
                memory_expires_time,
                display_duration,
                should_do_full_cleanup,
                cleanup_quota,
                self._is_seeing,
            )
            units_to_forget = to_forget
        else:
            for m in iterable_memories:
                model = m.initial_model
                if model.place is None:
                    units_to_forget.append(m)
                    continue
                if not model.speed:
                    if model in perception:
                        units_to_forget.append(m)
                    continue
                stamp = m.time_stamp
                display_expired = stamp + display_duration < current_time
                memory_expired = stamp < memory_expires_time
                in_perc = model in perception

                if not in_perc:
                    if memory_expired:
                        units_to_forget.append(m)
                    continue

                if self._is_seeing(model):
                    units_to_forget.append(m)
                    continue
                if display_expired:
                    perception.discard(model)
                    display_expired_initial_models.add(model)
                if memory_expired:
                    units_to_forget.append(m)
                    continue
                if should_do_full_cleanup and cleanup_quota > 0:
                    if m.place in observed:
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
            # 过滤出需要记忆的单位。
            # 静态地形（speed==0）不受 forgotten_initial_models 挡住：同帧若刚
            # 因「已在感知」清掉旧记忆、随后又离开感知，必须立刻重新写入雾战，
            # 否则会出现「只剩出口、草地空白」直到单位到场。
            units_to_memorize = {
                o for o in disappeared_units
                if not (o.is_invisible or o.is_cloaked) and o.place is not None
                and (
                    not getattr(o, "speed", 0)
                    or o not in forgotten_initial_models
                )
                and not (
                    getattr(o, "player", None) is self
                    and getattr(o, "id", None) not in own_unit_ids
                )
            }

            # 批量记忆
            if units_to_memorize:
                self._bulk_memorize(units_to_memorize)

        # 感知更新后再清一遍：己方已站在该格时，雾中幽灵必须立刻消失。
        self._forget_memories_on_observed_squares()

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

        # 空闲时也要定期刷感知；同格接触必须立刻刷，否则 idle AI 会拖到
        # forced 间隔才看见入侵者（1.4.5.2=2s，本分支曾误拉到 5s）。
        time_since_last_forced = current_time - self._last_forced_perception_update
        needs_forced_update = time_since_last_forced >= 1000
        contact_force = False
        if (
            not position_changed
            and not self._force_full_update
            and not self.cheatmode
            and not needs_forced_update
        ):
            contact_force = self._unseen_hostile_on_owned_squares()
            if not contact_force:
                self._lightweight_memory_update()
                return

        # 定期强制或同格接触：作废静态视野缓存并走完整/增量更新
        if needs_forced_update or contact_force:
            if needs_forced_update:
                self._last_forced_perception_update = current_time
            self._cached_static_perception = None
            self._prev_obs_squares = None
            self._prev_partial_squares = None
            
        # 若本帧有单位移动：优先增量。人多时只增量处理按 id 截断的一批，
        # 避免整帧全量（cw1 上全量 _update_perception ~32s tottime）。
        if position_changed and moved_units and not needs_forced_update:
            n_units = len(self.units)
            inc_limit = max(20, min(40, n_units // 2 if n_units else 20))
            if len(moved_units) > inc_limit:
                moved_units = sorted(moved_units, key=lambda u: u.id)[:inc_limit]
            previous_perception = self.perception.copy()
            self._incremental_perception_update(moved_units)
            self._last_unit_positions = current_unit_positions
            self._update_memory(previous_perception)
            self._record_new_enemy_units(previous_perception)
            self._perception_version = getattr(self, '_perception_version', 0) + 1
            return

        # 执行完整的感知更新
        self._force_full_update = False
        self._last_unit_positions = current_unit_positions
        
        # 先保存当前的感知状态（new_enemy + memory 共用这一份，不再内层二次 copy）
        previous_perception = self.perception.copy()
        
        # 更新感知
        self._update_perception()
        
        # 更新记忆 - 优化版本
        self._update_memory(previous_perception)
        self._record_new_enemy_units(previous_perception)
        # 感知版本号：完整更新后递增
        self._perception_version = getattr(self, '_perception_version', 0) + 1

        # 生成供战斗模块复用的“战斗快照”，避免其重复聚合。
        # combat.py 允许快照 ≤2000ms；此前每 1000ms 全量重刷与此不对齐，
        # 30min cw1 上 _refresh_combat_snapshot ~50s tottime。
        if hasattr(self, '_refresh_combat_snapshot'):
            last_call = getattr(self, '_last_snapshot_call_time', 0)
            if current_time - last_call >= 2000:
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

    def _unseen_hostile_on_owned_squares(self):
        """True when a hostile already shares a square with us but is not in perception.

        Idle perception skips must not delay same-square combat (e.g. z5 b3 knight).
        """
        perception = self.perception
        for unit in self.units:
            place = unit.place
            if place is None:
                continue
            if getattr(place, "is_inside_place", False):
                continue
            objs = getattr(place, "objects", None) or ()
            if not objs:
                continue
            for obj in objs:
                if obj is unit or obj.player is None:
                    continue
                if obj in perception:
                    continue
                if not obj.is_vulnerable:
                    continue
                if self.is_an_enemy(obj):
                    return True
        return False

    def _forget_memories_on_observed_squares(self):
        """Clear fog ghosts on squares we are currently observing.

        Re-entering a square must drop stale war-cloud memories there:
        - live unit still here and perceived → memory replaced by perception
        - live unit left / died → ghost is proven wrong
        Cloaked/invisible units keep memory only while still on that square.

        Uses ``_memory_by_place`` so idle ticks scan O(|observed ∩ memory|)
        instead of the full memory set (SESSION 4 semantics unchanged).
        """
        observed = self.observed_squares
        if not observed or not self.memory:
            return
        perception = self.perception
        detected = getattr(self, "detected_units", None)
        by_place = self._ensure_memory_by_place()
        to_forget = []
        for place in observed:
            bag = by_place.get(place)
            if not bag:
                continue
            # Iterate a snapshot: _forget mutates the bag.
            for m in tuple(bag):
                model = m.initial_model
                if model.place is None:
                    to_forget.append(m)
                    continue
                if not model.speed:
                    if model in perception:
                        to_forget.append(m)
                    continue
                if model.place is not place:
                    to_forget.append(m)
                    continue
                if (
                    (model.is_invisible or model.is_cloaked)
                    and detected is not None
                    and model not in detected
                ):
                    continue
                # 正在观察该格：雾中幽灵一律作废（实体由 perception 提供）。
                to_forget.append(m)
        for m in to_forget:
            self._forget(m)

    def _lightweight_memory_update(self):
        """轻量级记忆更新 - 在感知未变化时仅做必要的记忆清理"""
        # 空闲跳过全量感知时也要清当前视野格上的战云幽灵。
        self._forget_memories_on_observed_squares()

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
        stamp = memory.time_stamp
        mem_dur = self.memory_duration
        memory_expired = stamp + mem_dur < current_time
        display_duration = getattr(self, "display_memory_duration", mem_dur)
        display_expired = stamp + display_duration < current_time
        # Common case: still fresh for both timers — skip perception/_is_seeing.
        if not display_expired and not memory_expired:
            return False
        if display_expired and unit in self.perception and not self._is_seeing(unit):
            self.perception.discard(unit)
            if display_expired_initial_models is not None:
                display_expired_initial_models.add(unit)
        return memory_expired

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
        时间桶：2000ms（对齐 combat.py 快照老化阈值；全量按 place 重算语义不变）
        内容：
          - place_enemy_menace: {Square -> menace_sum}
          - enemy_presence_places: [Square]
          - corpse_places: set(Square)
          - friend_places: set(Square)
        """
        current_time = self.world.time
        time_bucket = current_time // 2000
        if getattr(self, '_combat_snapshot_bucket', -1) == time_bucket:
            return

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

        # 敌方单位威胁：必须每桶全量按 place 重算（勿做“只算增量差”）。
        # 旧增量逻辑曾导致交战中 menace 被清空 → AI「刚打过又停手」。
        if _fast is not None and hasattr(_fast, "build_enemy_place_menace"):
            place_enemy_menace, enemy_presence_places = _fast.build_enemy_place_menace(
                perceived, enemy_player_ids
            )
            live_presence = set(enemy_presence_places)
            by_place = self._ensure_memory_by_place()
            if hasattr(_fast, "add_memory_enemy_menace_by_place") and by_place:
                _fast.add_memory_enemy_menace_by_place(
                    place_enemy_menace,
                    enemy_presence_places,
                    live_presence,
                    by_place,
                    enemy_player_ids,
                )
            else:
                _fast.add_memory_enemy_menace(
                    place_enemy_menace,
                    enemy_presence_places,
                    live_presence,
                    mem_set,
                    enemy_player_ids,
                )
        else:
            place_enemy_menace = {}
            enemy_presence_places = []
            for o in perceived:
                p = o.player
                if p is None:
                    continue
                pl = o.place
                # place.is_inside_place：避开 Entity.is_inside property 间接层
                if pl is None or pl.is_inside_place:
                    continue
                if not o.is_vulnerable:
                    continue
                if p.id not in enemy_player_ids:
                    continue
                men = o.menace
                current_sum = place_enemy_menace.get(pl)
                if current_sum is None:
                    place_enemy_menace[pl] = men
                    enemy_presence_places.append(pl)
                else:
                    place_enemy_menace[pl] = current_sum + men

            live_presence = set(enemy_presence_places)
            by_place = self._ensure_memory_by_place()
            if by_place:
                for pl, bag in by_place.items():
                    if pl in live_presence or not bag:
                        continue
                    for rem in bag:
                        o = rem.initial_model
                        p = o.player
                        if p is None:
                            continue
                        if pl.is_inside_place or not o.is_vulnerable:
                            continue
                        if p.id not in enemy_player_ids:
                            continue
                        men = o.menace // 2
                        current_sum = place_enemy_menace.get(pl)
                        if current_sum is None:
                            place_enemy_menace[pl] = men
                            enemy_presence_places.append(pl)
                        else:
                            place_enemy_menace[pl] = current_sum + men
            else:
                for rem in mem_set:
                    o = rem.initial_model
                    p = o.player
                    if p is None:
                        continue
                    pl = o.place
                    if pl is None or pl in live_presence:
                        continue
                    if pl.is_inside_place or not o.is_vulnerable:
                        continue
                    if p.id not in enemy_player_ids:
                        continue
                    men = o.menace // 2
                    current_sum = place_enemy_menace.get(pl)
                    if current_sum is None:
                        place_enemy_menace[pl] = men
                        enemy_presence_places.append(pl)
                    else:
                        place_enemy_menace[pl] = current_sum + men

        # 尸体与友军位置：≥2000ms 才刷新一次，否则复用上次结果
        last_extras_ts = getattr(self, '_snapshot_extras_time', 0)
        if current_time - last_extras_ts >= 2000:
            tmp_corpse = set()
            tmp_friend = set()
            for o in perceived:
                if isinstance(o, Corpse):
                    pl = o.place
                    if isinstance(pl, Square):
                        tmp_corpse.add(pl)
                    continue
                p = o.player
                if p is None:
                    continue
                if p.id in allied_player_ids:
                    pl = o.place
                    if (
                        isinstance(pl, Square)
                        and o.is_vulnerable
                        and not pl.is_inside_place
                    ):
                        tmp_friend.add(pl)
            self._snapshot_corpse_places = tmp_corpse
            self._snapshot_friend_places = tmp_friend
            self._snapshot_extras_time = current_time

        # Reuse frozen snapshots (no per-refresh set() copy).
        corpse_places = getattr(self, '_snapshot_corpse_places', None) or set()
        friend_places = getattr(self, '_snapshot_friend_places', None) or set()

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
            observed_data = unit.get_observed_squares_optimized()
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
                objs = s.objects
                if objs:
                    for o in objs:
                        if o.player is None:
                            static_objects.add(o)
            if static_objects:
                self.perception.update(static_objects)
                self._memorize_unseen_exit_pairs(static_objects)

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

        # 处理失去严格观察的区域：敌方单位可直接摘除；静态对象必须进记忆，
        # 否则雾战里草地/出口等会变成空白（增量优化曾漏掉 memorize）。
        if removed_strict:
            static_to_memorize = []
            for s in removed_strict:
                if s in self.observed_squares:
                    continue
                objs = getattr(s, "objects", None) or ()
                if not objs:
                    continue
                for o in objs:
                    if o.player is None:
                        if o in self.perception:
                            self.perception.discard(o)
                        # 始终写入/刷新记忆：即使 perception 里已丢了（历史空白），
                        # 也要从方格上的静态对象补回雾战内容。
                        static_to_memorize.append(o)
                        continue
                    if o.is_inside:
                        continue
                    # 仅对敌方单位做可见性校验并可能移除；友军/己方单位保持可见，
                    # 以与完整更新路径的“添加盟友单位”逻辑保持一致
                    if (
                        o in self.perception
                        and self.is_an_enemy(o)
                        and not self._is_seeing(o)
                    ):
                        self.perception.discard(o)
            if static_to_memorize:
                self._bulk_memorize(static_to_memorize)
        # 增量改动了观察区/静态感知后，作废全量路径的静态缓存，避免
        # vision_unchanged 跳过「部分观察区 memorize」分支而留下空白战云格。
        if newly_strict or removed_strict:
            self._cached_static_perception = None
            self._prev_obs_squares = None
            self._prev_partial_squares = None
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
            self._memory_place_index_add(remembrance)

    def _forget(self, o):  # o is a memory object
        # 更稳健：使用 discard 避免 KeyError（可能已在其他清理路径中被移除）
        place = o.place
        self.memory.discard(o)
        try:
            del self._memory_index[o.initial_model]
        except KeyError:  # a test requires this to pass
            pass
        self._memory_place_index_remove(o, place)
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