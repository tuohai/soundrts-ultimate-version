"""
World游戏逻辑模块 - 游戏更新循环、事件处理和游戏流程控制
"""
import copy
import os
import time
from ..lib import chronometer as chrono
from ..lib.log import exception
from ..lib.nofloat import square_of_distance
from ..worldplayerbase import A

# 世界级每 tick 全单位扫描的 Cython 加速器
_wbf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import world_buckets_fast as _wbf  # type: ignore[no-redef]
    except ImportError:
        _wbf = None

from .world_ecs import ecs_enabled as _ecs_enabled


class WorldGameMixin:
    """World游戏逻辑混入类"""

    # Periodic full bucket rebuild to heal rare incremental drift (units removed
    # without going through normal death paths, etc.). Does not touch perception
    # idle / contact_force / decide timing — only spatial index correctness.
    _BUCKET_HEAL_TICKS = 120

    def _rebuild_player_buckets(self, p, A):
        """Full rebuild of one player's spatial buckets (cold start / heal)."""
        if _wbf is not None:
            p._buckets = _wbf.build_buckets(p.units, A)
        else:
            buckets = {}
            for u in p.units:
                k = (u.x // A, u.y // A)
                try:
                    buckets[k].append(u)
                except KeyError:
                    buckets[k] = [u]
            p._buckets = buckets
        # id(u) keys: Creature instances are hashable, but keep this robust for
        # stubs / unusual unit types.
        p._bucket_unit_cells = {
            id(u): ((u.x // A, u.y // A), u) for u in p.units
        }
        p._bucket_ticks_since_heal = 0

    def _incremental_player_buckets(self, p, A):
        """Move units between bucket cells. Returns dirty cell set, or None for full invalidate."""
        prev = getattr(p, "_bucket_unit_cells", None)
        buckets = getattr(p, "_buckets", None)
        ticks = getattr(p, "_bucket_ticks_since_heal", 0) + 1
        p._bucket_ticks_since_heal = ticks
        if (
            prev is None
            or not isinstance(buckets, dict)
            or ticks >= self._BUCKET_HEAL_TICKS
        ):
            self._rebuild_player_buckets(p, A)
            return None  # caller must full-clear this player's neighbor entries

        dirty = set()
        live_ids = {id(u) for u in p.units}

        for uid in tuple(prev.keys()):
            if uid in live_ids:
                continue
            old_k, u = prev.pop(uid)
            bl = buckets.get(old_k)
            if bl is not None:
                try:
                    bl.remove(u)
                except ValueError:
                    pass
                if not bl:
                    buckets.pop(old_k, None)
            dirty.add(old_k)

        for u in p.units:
            k = (u.x // A, u.y // A)
            uid = id(u)
            entry = prev.get(uid)
            if entry is None:
                bl = buckets.get(k)
                if bl is None:
                    buckets[k] = [u]
                else:
                    bl.append(u)
                prev[uid] = (k, u)
                dirty.add(k)
            else:
                old_k, _stored = entry
                if old_k != k:
                    bl = buckets.get(old_k)
                    if bl is not None:
                        try:
                            bl.remove(u)
                        except ValueError:
                            pass
                        if not bl:
                            buckets.pop(old_k, None)
                    bl = buckets.get(k)
                    if bl is None:
                        buckets[k] = [u]
                    else:
                        bl.append(u)
                    prev[uid] = (k, u)
                    dirty.add(old_k)
                    dirty.add(k)
                else:
                    # Same cell; refresh stored ref in case object was replaced.
                    prev[uid] = (k, u)

        return dirty

    def _update_buckets(self):
        """Maintain per-player spatial buckets.

        Safety constraints (SESSION_PERF_AND_FIXES_REPORT.md):
        - Still clear vision cache every tick (do not reuse stale vision).
        - Do not touch perception idle / contact_force / decide intervals.
        - Neighbor merge cache: keep across ticks when nothing moved; selective
          invalidate near dirty cells; large dirty → full clear.

        ECS (default-on when extension built; ``SOUNDRTS_ECS=0`` to disable):
        same incremental ``_buckets`` as the default path; SoA scalars sync each
        tick for ``batch_see_enemies``.
        """
        ecs = getattr(self, "_ecs", None) if _ecs_enabled() else None

        for p in self.players:
            dirty = self._incremental_player_buckets(p, A)
            if ecs is not None:
                # Batch visibility needs fresh SoA every tick; heal → full rebuild.
                ecs.sync_player(p, force_rebuild=(dirty is None))
            if dirty is None:
                clear_nb = getattr(p, "_clear_neighbors_cache", None)
                if clear_nb is not None:
                    clear_nb()
            elif dirty:
                inv = getattr(p, "_invalidate_neighbors_near", None)
                if inv is not None:
                    inv(dirty)
            # else: units stationary → keep neighbor merge cache warm

            # Vision cache still every tick — required for perception correctness
            # (reusing it across ticks previously caused delayed engagement).
            clear_vis = getattr(p, "_clear_vision_cache", None)
            if clear_vis is not None:
                clear_vis()

    def _update_cloaking(self):
        for p in self.players:
            for u in p.units:
                if u.is_cloakable:
                    u.is_cloaked = False
        for p in self.players:
            for u in p.units:
                if u.is_a_cloaker:
                    radius2 = u.cloaking_range * u.cloaking_range
                    for vp in p.allied:
                        # 强制跳过缓存以确保隐身装置能获取到最新的可隐身单位信息
                        candidates = vp._potential_neighbors(u.x, u.y, skip_cache=True)
                        if _wbf is not None:
                            _wbf.mark_cloaked(candidates, u.x, u.y, radius2)
                        else:
                            for vu in candidates:
                                if not vu.is_cloakable or vu.is_cloaked:
                                    continue
                                if square_of_distance(vu.x, vu.y, u.x, u.y) < radius2:
                                    vu.is_cloaked = True
                                    continue

    def _update_detection(self):
        for p in self.players:
            p.detected_units = set()
        for p in self.players:
            for u in p.units:
                if u.is_a_detector:
                    radius2 = u.detection_range * u.detection_range
                    for e in self.players:
                        if e in p.allied:
                            continue
                        # 强制跳过缓存以确保探测器能获取到最新的隐形单位信息
                        candidates = e._potential_neighbors(u.x, u.y, skip_cache=True)
                        if _wbf is not None:
                            detected = _wbf.collect_invisibles_in_range(
                                candidates, u.x, u.y, radius2, p.detected_units
                            )
                            for iu in detected:
                                # 优先通过联盟管理器共享探测，保持现有感知机制不变
                                mgr = getattr(p, 'alliance_vision_manager', None)
                                if mgr is not None:
                                    try:
                                        mgr.share_detection(iu)
                                    except Exception:
                                        pass
                                else:
                                    for a in p.allied_vision:
                                        a.detected_units.add(iu)
                        else:
                            for iu in candidates:
                                if not (iu.is_invisible or iu.is_cloaked):
                                    continue
                                if iu in p.detected_units:
                                    continue
                                if square_of_distance(iu.x, iu.y, u.x, u.y) < radius2:
                                    mgr = getattr(p, 'alliance_vision_manager', None)
                                    if mgr is not None:
                                        try:
                                            mgr.share_detection(iu)
                                        except Exception:
                                            pass
                                    else:
                                        for a in p.allied_vision:
                                            a.detected_units.add(iu)
                                    continue

    def _update_terrain(self):
        # 优先更新脏方格，周期性再做一次全量兜底
        dirty = getattr(self, '_dirty_terrain_squares', None)
        if dirty:
            for s in list(dirty):
                if not getattr(s, "fixed_terrain", False):
                    s.update_terrain()
            dirty.clear()
        # 每2秒全量校验一次，防止遗漏
        if not hasattr(self, '_last_full_terrain_update'):
            self._last_full_terrain_update = 0
        if self.time - self._last_full_terrain_update >= 2000:
            for s in self.squares:
                if not getattr(s, "fixed_terrain", False):
                    s.update_terrain()
            self._last_full_terrain_update = self.time

    _previous_slow_update = 0

    def update(self):
        chrono.start("update")
        
        # 处理调度事件
        remaining_events = []
        current_time = self.time
        for exec_time, callback in self._scheduled_events:
            if current_time >= exec_time:
                try:
                    callback()
                except:
                    exception("调度事件执行出错")
            else:
                remaining_events.append((exec_time, callback))
        self._scheduled_events = remaining_events

        # normal updates（恢复固定顺序）
        self._update_terrain()
        self._update_buckets()
        self._update_cloaking()
        self._update_detection()
        
        # 决定性配额：按玩家 id 稳定顺序分帧更新，避免不同步
        players_snapshot = sorted(self.players, key=lambda _p: _p.id)
        n_players = len(players_snapshot)
        if n_players:
            # 在 player_cycle_ticks 个游戏 tick 内覆盖全部玩家
            from ..definitions import VIRTUAL_TIME_INTERVAL as _VT
            player_cycle_ticks = 1
            quota = max(1, (n_players + player_cycle_ticks - 1) // player_cycle_ticks)
            phase = ((self.time // _VT) % player_cycle_ticks) * quota
            for k in range(min(quota, n_players)):
                p = players_snapshot[(phase + k) % n_players]
                if p in self.players:
                    try:
                        p.update()
                    except:
                        exception("")
                    
        # 决定性配额：按对象 id 稳定顺序分帧更新
        objects_snapshot = self._active_objects_snapshot()
        n_objects = len(objects_snapshot)
        if n_objects:
            from ..definitions import VIRTUAL_TIME_INTERVAL as _VT
            object_cycle_ticks = 1
            quota_o = max(1, (n_objects + object_cycle_ticks - 1) // object_cycle_ticks)
            phase_o = ((self.time // _VT) % object_cycle_ticks) * quota_o
            for k in range(min(quota_o, n_objects)):
                o = objects_snapshot[(phase_o + k) % n_objects]
                if o.place is not None:
                    try:
                        o.update()
                    except:
                        exception("")

        # slow updates (called every second) - 稳定顺序
        if self.time >= self._previous_slow_update + 1000:
            try:
                from ..world_build_rules import tick_build_fields

                tick_build_fields(self)
                from ..world_build_rules import tick_hatchery_larva

                tick_hatchery_larva(self)
            except Exception:
                exception("")
            for o in self._active_objects_snapshot():
                if o.place is not None:
                    try:
                        o.slow_update()
                    except:
                        exception("")
            for p in sorted(self.players[:], key=lambda _p: _p.id):
                if p in self.players:
                    try:
                        p.slow_update()
                    except:
                        exception("")
            self._previous_slow_update += 1000

        # 优化：感知清理 - 只在必要时执行，减少每帧开销
        if not hasattr(self, '_last_perception_cleanup'):
            self._last_perception_cleanup = 0
            
        # 每5秒进行一次感知清理，而不是每帧都清理
        if self.time - self._last_perception_cleanup >= 5000:
            # 从perception中移除已删除的对象
            # 确保处理顺序确定性：按玩家ID排序
            sorted_players = sorted(self.players, key=lambda p: p.id)
            for p in sorted_players:
                units_to_remove = []
                for o in p.perception:
                    if o.place is None:
                        units_to_remove.append(o)
                for o in units_to_remove:
                    p.perception.remove(o)
            self._last_perception_cleanup = self.time

        chrono.stop("update")
        self._record_sync_debug_info()

        # 指示此时间的更新已结束
        from ..definitions import VIRTUAL_TIME_INTERVAL
        self.time += VIRTUAL_TIME_INTERVAL
        for p in self.players[:]:
            try:
                def _copy(l):
                    try:
                        return l.copy()
                    except AttributeError:
                        return set(l)

                collision_debug = None
                if p.is_local_human():  # 避免不必要的复制
                    if p.cheatmode:
                        observed_before_squares = self.squares
                    else:
                        observed_before_squares = p.observed_before_squares
                    p.push(
                        "voila",
                        self.time,
                        _copy(p.memory_for_display()),
                        _copy(p.perception),
                        p.observed_squares,
                        observed_before_squares,
                        collision_debug,
                    )
            except:
                exception("")

        # 如果没有胜负参与者仍在游戏中（忽略脚本 NPC 等），结束游戏
        if not self.match_participating_players:
            for p in self.players:
                p.quit_game()

    def _loop(self):
        self._must_loop = True
        while self._must_loop:
            if not self._command_queue.empty():
                player, order = self._command_queue.get()
                try:
                    if player is None:
                        order()
                    else:
                        player.execute_command(order)
                except:
                    exception("")
            else:
                time.sleep(0.001)

    def loop(self):
        from .world_core import PROFILE
        if PROFILE:
            import cProfile

            cProfile.runctx("self._loop()", globals(), locals(), "world_profile.tmp")
            # 额外输出文本报告，便于查看
            try:
                import pstats
                with open("world_profile.txt", "w", encoding="utf-8") as _txt:
                    _p = pstats.Stats("world_profile.tmp", stream=_txt)
                    _p.strip_dirs()
                    _p.sort_stats("time", "cumulative").print_stats(30)
                    _p.print_callers(30)
                    _p.print_callees(20)
                    _p.sort_stats("cumulative").print_stats(50)
                    _p.print_callers(100)
                    _p.print_callees(100)
            except Exception:
                pass
        else:
            self._loop()
        self._free_memory()