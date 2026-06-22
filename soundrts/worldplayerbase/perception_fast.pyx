# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的感知 / 邻居过滤热点。

主要服务对象：``world/world_objects.py::get_objects2`` 的距离过滤循环
（被 ``heal_nearby_units`` / ``harm_nearby_units`` / 范围技能等高频调用）。

不改 ``PerceptionMixin`` 类结构（避免触碰大量动态属性与多 Mixin）。
仅抽取"对象列表 + 距离/place 过滤 + 可选 filter callback"的紧循环。
"""

cimport cython
import copy as _copy_mod


cpdef list filter_in_radius(objects, long long cx, long long cy,
                            long long radius2):
    """从 ``objects`` 中筛出 ``o.place is not None`` 且
    ``(o.x - cx)^2 + (o.y - cy)^2 <= radius2`` 的对象。

    输入是任意可迭代（dict_values / list / tuple / set 都行）。
    返回 Python list，调用方可继续应用 Python filter callback。
    """
    cdef list result = []
    cdef long long dx, dy
    for o in objects:
        if o.place is None:
            continue
        dx = o.x - cx
        dy = o.y - cy
        if dx * dx + dy * dy <= radius2:
            result.append(o)
    return result


cpdef list filter_in_radius_with_cb(objects, long long cx, long long cy,
                                    long long radius2, filter_fn):
    """同 ``filter_in_radius``，外加 Python filter callback。

    callback 在距离检查之后调用（早出剪枝），减少 callback 调用次数。
    若 ``filter_fn`` 为 None，等价于 ``filter_in_radius``。
    """
    cdef list result = []
    cdef long long dx, dy
    if filter_fn is None:
        return filter_in_radius(objects, cx, cy, radius2)
    for o in objects:
        if o.place is None:
            continue
        dx = o.x - cx
        dy = o.y - cy
        if dx * dx + dy * dy > radius2:
            continue
        if filter_fn(o):
            result.append(o)
    return result


cpdef list filter_visible_vulnerable_enemies(objects, perceived_set,
                                             enemy_units_set):
    """D-Phase 1 T2: ``known_enemies`` 内层热点 (22M calls / 5min cw1).

    等价于 ``perception.py:known_enemies`` line 85-94:
        for obj in place.objects:
            if obj in perceived_set and obj in enemy_units_set and obj.is_vulnerable:
                op = obj.place
                if op is None or not op.is_inside_place:
                    result.append(obj)

    Cython 化只省 frame setup + 字节码 dispatch (set in 仍是 PyObject 操作);
    实测每次 ~0.5us → ~0.3us. 累计 22M × 0.2us = ~4s real.
    """
    cdef list result = []
    for obj in objects:
        if obj not in perceived_set:
            continue
        if obj not in enemy_units_set:
            continue
        if not obj.is_vulnerable:
            continue
        op = obj.place
        if op is None or not op.is_inside_place:
            result.append(obj)
    return result


# === D-Phase 2 (continued): player_is_an_enemy whole-fn cpdef ============
# combat.player_is_an_enemy: 20.2M calls / 5min cw1, 6.8 s tottime.
# 函数体短小 (5-line dict cache + set membership), 但 frame setup +
# bytecode dispatch overhead 占主. 把整函数 Cython 化, self/p 仍是 Python
# 对象, 节省 ~150-250 ns/call × 20M = 3-5 s.
#
# 语义保留: 与 worldplayerbase/combat.py:277 byte-exact:
#   1. p is None -> False (无副作用)
#   2. 缓存 5 秒过期 -> clear + 更新时间戳
#   3. p.id 命中缓存 -> 直接返回缓存值
#   4. 计算 p not in self.allied -> 写缓存 -> 返回
#
# 注: 不能用 cdef bint 返回值因为缓存写入的是 Python bool. 用 object 保留语义.

cpdef object player_is_an_enemy(self, p):
    """Cython 化 ``CombatMixin.player_is_an_enemy``.

    与 Python 实现 (worldplayerbase/combat.py:277) 完全等价. 缓存语义不变.

    Args:
        self: Player 实例 (Python 对象)
        p:    候选玩家 (Player 实例 或 None)
    Returns:
        bool: p 是否敌对 (None 返回 False)
    """
    if p is None:
        return False
    cdef object current_time = self.world.time
    cdef dict cache = self._enemy_player_cache
    cdef object timestamp = self._enemy_player_timestamp
    if current_time - timestamp > 5000:
        cache.clear()
        self._enemy_player_timestamp = current_time
    cdef object pid = p.id
    cdef object cached = cache.get(pid)
    if cached is not None:
        return cached
    cdef bint result = p not in self.allied
    cache[pid] = result
    return result


# === D-Phase 2 (cont.): bulk_memorize whole-fn cpdef =====================
# perception._bulk_memorize: 22.6k calls / 5min cw1, 14.8 s tottime
# (0.66 ms/call avg). 内层 for-loop 遍历 objects (typical ~100 entries/call,
# 累计 ~2.3M iterations), 每 iter 做: 2 attribute (is_invisible/is_cloaked) +
# dict membership + 二选一更新/copy. Cython 化省 Python frame setup + 字节
# 码 dispatch, copy.copy 本身仍调 CPython C 实现, 无法再加速.
#
# 语义保留: 与 perception.py:1112 byte-exact, 包括 invisible/cloaked 跳过
# 顺序与 memory/_memory_index 双向写入语义.

cpdef bulk_memorize(self, objects):
    """Cython 化 ``PerceptionMixin._bulk_memorize``.

    Args:
        self: Player 实例 (Python 对象)
        objects: 可迭代对象集合 (通常是 self.perception set)
    """
    cdef object current_time = self.world.time
    cdef dict memory_index = self._memory_index
    cdef object memory_set = self.memory
    cdef object _copy = _copy_mod.copy
    cdef object obj, remembrance, existing
    for obj in objects:
        if getattr(obj, "_is_skill_combat_proxy", False):
            continue
        if obj.is_invisible or obj.is_cloaked:
            continue
        existing = memory_index.get(obj)
        if existing is not None:
            existing.time_stamp = current_time
        else:
            remembrance = _copy(obj)
            remembrance.time_stamp = current_time
            remembrance.initial_model = obj
            memory_set.add(remembrance)
            memory_index[obj] = remembrance


cpdef list merge_buckets_3x3(dict buckets, long long grid_x, long long grid_y):
    """合并 ``buckets[(gx+dx, gy+dy)] for dx in {-1,0,1} for dy in {-1,0,1}``。

    替代 ``PerceptionMixin._potential_neighbors`` 内的 3x3 网格 list extend。
    保持与原版完全一致的对象顺序（dx=0,1,-1 × dy=0,1,-1 同样的扫描顺序）。

    实现说明：
    - ``bucket`` 不能 ``cdef list``，因为 ``dict.get`` 可能返回 None，
      给 typed list 赋 None 会在 C 层 SEGV。
    - 9 个 offset 用 C 数组而非 Python tuple，避免 cdef int 迭代 PyTuple 的
      Cython 代码生成 bug。
    """
    cdef list result = []
    # dx/dy 顺序必须与原 _potential_neighbors 一致以保 determinism：
    # for dx in (0, 1, -1) for dy in (0, 1, -1)
    cdef int[9] dxs
    cdef int[9] dys
    dxs[0] = 0;  dys[0] = 0
    dxs[1] = 0;  dys[1] = 1
    dxs[2] = 0;  dys[2] = -1
    dxs[3] = 1;  dys[3] = 0
    dxs[4] = 1;  dys[4] = 1
    dxs[5] = 1;  dys[5] = -1
    dxs[6] = -1; dys[6] = 0
    dxs[7] = -1; dys[7] = 1
    dxs[8] = -1; dys[8] = -1
    cdef int i
    for i in range(9):
        key = (grid_x + dxs[i], grid_y + dys[i])
        bucket = buckets.get(key)
        if bucket is not None:
            result.extend(bucket)
    return result


# === D-Phase 2 (cont.): bulk_visibility_check whole-fn cpdef =================
# perception._bulk_visibility_check: ~3.7k calls / 90s cw1, ~4.8 s tottime.
# 250 行含 6 层 cache + place 大循环; Cython 化省 frame setup + 字节码 dispatch.
# Python fallback: perception._py_bulk_visibility_check (byte-exact 参考).

cpdef tuple bulk_visibility_check(self, objects):
    """Cython 化 ``PerceptionMixin._bulk_visibility_check``.

    返回 (visible_objects set, invisible_objects set).
    """
    cdef object visible_objects = set()
    cdef object invisible_objects = set()
    cdef object current_time = self.world.time
    cdef long long time_bucket = current_time // 250
    cdef object cls = self.__class__
    cdef object player_cache
    cdef dict objects_by_place = {}
    cdef object obj, place
    cdef object union_cache, observed_places_union, observed_places
    cdef object pvc_root, place_visible_cache
    cdef object place_objects, cache_key, cache_key_nearby
    cdef object all_nearby_units, avp, nearby_units
    cdef object covering_units, unit, observed_squares
    cdef bint place_visible_for_any
    cdef object history_key, cov_ids, prev, prev_bucket, prev_sig, prev_visible
    cdef object remaining_to_check
    cdef object ivc, ivc_key, ivc_entry, last_bucket, last_visible
    cdef object x, y, units_to_check, sight_range, radius2
    cdef long long dx, dy, dist2
    cdef int checked
    cdef bint is_visible
    cdef object observed_key

    if self.id not in cls._global_vision_cache:
        cls._global_vision_cache[self.id] = {}
    player_cache = cls._global_vision_cache[self.id]

    for obj in objects:
        place = obj.place
        if place not in objects_by_place:
            objects_by_place[place] = []
        objects_by_place[place].append(obj)

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

    if cls._place_covering_units_bucket != time_bucket:
        cls._place_covering_units_cache = {}
        cls._place_covering_units_bucket = time_bucket

    if cls._place_visible_bucket != time_bucket:
        cls._place_visible_cache = {}
        cls._place_visible_bucket = time_bucket
    pvc_root = cls._place_visible_cache
    if self.id not in pvc_root:
        pvc_root[self.id] = {}
    place_visible_cache = pvc_root[self.id]

    for place, place_objects in objects_by_place.items():
        if place not in observed_places:
            invisible_objects.update(place_objects)
            for obj in place_objects:
                cache_key = (obj.id, time_bucket)
                player_cache[cache_key] = False
            continue

        if self._nearby_units_cache_bucket != time_bucket:
            self._nearby_units_cache = {}
            self._nearby_units_cache_bucket = time_bucket
        cache_key_nearby = place.id
        all_nearby_units = self._nearby_units_cache.get(cache_key_nearby)
        if all_nearby_units is None:
            all_nearby_units = set()
            for avp in self.allied_vision:
                x, y = place.x, place.y
                nearby_units = avp._potential_neighbors(x, y)
                all_nearby_units.update(nearby_units)
            self._nearby_units_cache[cache_key_nearby] = all_nearby_units

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
                    if len(covering_units) >= 3:
                        break
            cls._place_covering_units_cache[place] = covering_units

        place_visible_for_any = len(covering_units) > 0

        history_key = (self.id, place.id)
        if covering_units:
            cov_ids = tuple(sorted([u.id for u in covering_units])[:3])
        else:
            cov_ids = ()
        prev = cls._place_visible_history.get(history_key)
        if not place_visible_for_any and prev:
            prev_bucket, prev_sig, prev_visible = prev
            if prev_visible and (time_bucket - prev_bucket) <= 3 and prev_sig == cov_ids:
                place_visible_for_any = True

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
            place_objects = remaining_to_check
        cls._place_visible_history[history_key] = (time_bucket, cov_ids, place_visible_for_any)

        for obj in place_objects:
            cache_key = (obj.id, time_bucket)

            if cache_key in player_cache:
                cls._vision_cache_hits += 1
                if player_cache[cache_key]:
                    visible_objects.add(obj)
                else:
                    invisible_objects.add(obj)
                continue

            cls._vision_cache_misses += 1

            if (getattr(obj, 'is_invisible', False) or getattr(obj, 'is_cloaked', False)) and obj not in self.detected_units:
                if not hasattr(cls, '_invis_visibility_cache'):
                    cls._invis_visibility_cache = {}
                    cls._invis_visibility_bucket = time_bucket
                ivc = cls._invis_visibility_cache
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

            if self.is_an_enemy(obj) and place not in self.observed_squares:
                player_cache[cache_key] = False
                invisible_objects.add(obj)
                continue

            x, y = obj.x, obj.y
            is_visible = False

            if not hasattr(cls, '_sight_range_squares'):
                cls._sight_range_squares = {}

            units_to_check = covering_units if covering_units else all_nearby_units
            checked = 0
            for unit in units_to_check:
                sight_range = unit.sight_range
                if sight_range not in cls._sight_range_squares:
                    cls._sight_range_squares[sight_range] = sight_range * sight_range
                radius2 = cls._sight_range_squares[sight_range]

                dx = unit.x - x
                dy = unit.y - y
                dist2 = dx * dx + dy * dy

                if dist2 < radius2 / 4:
                    is_visible = True
                    break

                if dist2 < radius2:
                    observed_key = (unit.id, time_bucket)
                    observed_squares = getattr(unit, '_cached_observed_squares', None)
                    if observed_squares is None or getattr(unit, '_cached_observed_time', 0) != time_bucket:
                        observed_squares = set(unit.get_observed_squares())
                        unit._cached_observed_squares = observed_squares
                        unit._cached_observed_time = time_bucket
                    if place in observed_squares:
                        is_visible = True
                        break
                checked += 1
                if checked >= 4:
                    break

            player_cache[cache_key] = is_visible
            if getattr(obj, 'is_invisible', False) or getattr(obj, 'is_cloaked', False):
                if not hasattr(cls, '_invis_visibility_cache'):
                    cls._invis_visibility_cache = {}
                    cls._invis_visibility_bucket = time_bucket
                ivc = cls._invis_visibility_cache
                ivc_key = (self.id, getattr(place, 'id', id(place)), getattr(obj, 'id', id(obj)))
                ivc[ivc_key] = (time_bucket, is_visible)
            if is_visible:
                visible_objects.add(obj)
            else:
                invisible_objects.add(obj)

    return visible_objects, invisible_objects
