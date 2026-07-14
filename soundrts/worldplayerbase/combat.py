"""玩家战斗、AI和威胁评估模块"""

import os
from typing import Union, List

from ..worldroom import Square
from ..worldexit import Exit
from ..worldresource import Corpse
from ..worldunit import Soldier

# D-Phase 2 (cont.): Cython 加速 player_is_an_enemy (20M calls/5min).
# 失败时静默回退到 Python 实现.
_fast = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import perception_fast as _fast  # type: ignore[no-redef]
    except ImportError:
        _fast = None


class CombatMixin:
    """战斗和威胁评估相关的方法混入类"""

    def _update_enemy_menace_and_presence_and_corpses(self):
        """更新敌人威胁、存在和尸体信息 - 优化版"""
        current_time = self.world.time
        cache_key = current_time // 500  # 每500ms更新一次

        # 检查缓存是否有效
        if self._enemy_menace_cache_time == cache_key:
            cached = self._enemy_menace_cache
            self._enemy_menace = cached.get("enemy_menace", {})
            self._enemy_presence = cached.get("enemy_presence", [])
            self._places_with_corpses = cached.get("places_with_corpses", set())
            self._places_with_friends = cached.get("places_with_friends", set())
            self._cataclysmic_places = cached.get("cataclysmic_places", set())
            return

        # Prefer perception combat snapshot — assign refs, no dict/list copies.
        snapshot = getattr(self, "_combat_snapshot", None)
        if (
            snapshot is None
            or current_time - snapshot.get("timestamp", 0) > 2000
        ):
            refresh = getattr(self, "_refresh_combat_snapshot", None)
            if refresh is not None:
                refresh()
                snapshot = getattr(self, "_combat_snapshot", None)
        if snapshot and current_time - snapshot.get("timestamp", 0) <= 2000:
            enemy_menace = snapshot.get("place_enemy_menace") or {}
            enemy_presence = snapshot.get("enemy_presence_places") or []
            places_with_corpses = snapshot.get("corpse_places") or set()
            places_with_friends = snapshot.get("friend_places") or set()
            cataclysmic_places = set()
            self._enemy_menace = enemy_menace
            self._enemy_presence = enemy_presence
            self._places_with_corpses = places_with_corpses
            self._places_with_friends = places_with_friends
            self._cataclysmic_places = cataclysmic_places
            self._enemy_menace_cache = {
                "enemy_menace": enemy_menace,
                "enemy_presence": enemy_presence,
                "places_with_corpses": places_with_corpses,
                "places_with_friends": places_with_friends,
                "cataclysmic_places": cataclysmic_places,
            }
            self._enemy_menace_cache_time = cache_key
            return

        enemy_menace = {}
        enemy_presence = []
        places_with_corpses = set()
        places_with_friends = set()
        cataclysmic_places = set()

        enemy_players = [p for p in self.world.players if self.player_is_a_hostile_enemy(p)]
        allied_units = self.get_allied_units()
        allied_vulnerable_units = {u for u in allied_units if u.is_vulnerable and not u.is_inside}

        if current_time - getattr(self, "_cached_enemy_units_time", 0) > 200:
            enemy_units = set()
            for p in enemy_players:
                enemy_units.update(p.units)
            self._cached_enemy_units = enemy_units
            self._cached_enemy_units_time = current_time
        else:
            enemy_units = getattr(self, "_cached_enemy_units", set())

        perception_objects = self.perception
        memory_objects = self.memory
        enemy_units_perceived = enemy_units.intersection(perception_objects)
        enemy_units_remembered = enemy_units.intersection(memory_objects)

        # Aggregate without sorting units; sort place presence once for determinism.
        for o in enemy_units_perceived:
            if o.is_inside or not o.is_vulnerable:
                continue
            place = o.place
            if place is None or not isinstance(place, Square):
                continue
            menace = o.menace
            if place in enemy_menace:
                enemy_menace[place] += menace
            else:
                enemy_menace[place] = menace
                enemy_presence.append(place)
            if not getattr(o, "is_melee", True):
                range_threat = menace // 10
                for neighbor in place.neighbors:
                    if neighbor in enemy_menace:
                        enemy_menace[neighbor] += range_threat
                    else:
                        enemy_menace[neighbor] = range_threat

        presence_set = set(enemy_presence)
        for o in enemy_units_remembered:
            if o.is_inside or not o.is_vulnerable:
                continue
            place = o.place
            if place is None or not isinstance(place, Square) or place in presence_set:
                continue
            menace = o.menace // 2
            if place in enemy_menace:
                enemy_menace[place] += menace
            else:
                enemy_menace[place] = menace
                enemy_presence.append(place)
                presence_set.add(place)

        enemy_presence.sort(key=lambda p: p.id)

        for o in perception_objects:
            if isinstance(o, Corpse) and isinstance(o.place, Square):
                places_with_corpses.add(o.place)
        for o in memory_objects:
            if isinstance(o, Corpse) and isinstance(o.place, Square):
                places_with_corpses.add(o.place)

        for u in allied_vulnerable_units:
            place = u.place
            if isinstance(place, Square):
                places_with_friends.add(place)

        for o in perception_objects:
            if o.time_limit and o.harm_level and isinstance(o.place, Square):
                cataclysmic_places.add(o.place)
        for o in memory_objects:
            if o.time_limit and o.harm_level and isinstance(o.place, Square):
                cataclysmic_places.add(o.place)

        self._enemy_menace = enemy_menace
        self._enemy_presence = enemy_presence
        self._places_with_corpses = places_with_corpses
        self._places_with_friends = places_with_friends
        self._cataclysmic_places = cataclysmic_places

        self._enemy_menace_cache = {
            "enemy_menace": enemy_menace,
            "enemy_presence": enemy_presence,
            "places_with_corpses": places_with_corpses,
            "places_with_friends": places_with_friends,
            "cataclysmic_places": cataclysmic_places,
        }
        self._enemy_menace_cache_time = cache_key

    def enemy_menace(self, place):
        try:
            return self._enemy_menace[place]
        except KeyError:
            return 0

    def is_very_dangerous(self, square_or_exit: Union[Square, Exit]) -> bool:
        if square_or_exit is None:
            return False
        # Units leaving a transport/building remember Inside as _previous_square.
        if getattr(square_or_exit, "is_inside_place", False):
            square_or_exit = getattr(square_or_exit, "outside", None)
            if square_or_exit is None:
                return False
        if isinstance(square_or_exit, Square):
            return (
                self.square_is_dangerous(square_or_exit)
                and square_or_exit in self._enemy_presence
            )
        other = getattr(square_or_exit, "other_side", None)
        if other is not None:
            return (
                self.exit_is_dangerous(square_or_exit)
                and other.place in self._enemy_presence
            )
        # Unknown place-like object with exits: treat like a square.
        if hasattr(square_or_exit, "exits"):
            return (
                self.square_is_dangerous(square_or_exit)
                and square_or_exit in self._enemy_presence
            )
        return False

    def square_is_dangerous(self, s: Square) -> bool:
        if s is None:
            return False
        if getattr(s, "is_inside_place", False):
            s = getattr(s, "outside", None)
            if s is None:
                return False
        return s in self._enemy_menace

    def exit_is_dangerous(self, e: Exit) -> bool:
        other = getattr(e, "other_side", None)
        if other is None:
            return False
        place = getattr(other, "place", None)
        return place is not None and place in self._enemy_menace

    def balance(self, *squares, add=None, mult=1):
        # The first square is where the fight will be.
        # TODO: take into account: versus air, ground
        # TODO: take into account: allies (in first square)
        
        # 优化：缓存balance计算结果，减少重复计算
        current_time = self.world.time
        cache_key = (
            tuple(s.id if s is not None else None for s in squares),
            add.id if add else None,
            mult,
            current_time // 200  # 200ms缓存窗口
        )
        
        # (_balance_cache / _balance_cache_time 已在 Player.__init__ 预初始化)
        
        # 检查缓存
        if cache_key in self._balance_cache and current_time - self._balance_cache_time.get(cache_key, 0) < 200:
            return self._balance_cache[cache_key]
        
        # 优化：预先计算squares集合，避免重复的in操作，过滤None值
        squares_set = {s for s in squares if s is not None}
        a = 0
        
        # 优化：直接遍历相关单位，避免检查所有单位
        for u in self.units:
            if u.place in squares_set or u is add:
                a += u.menace
        
        try:
            # 检查第一个square是否有效
            first_square = squares[0] if squares and squares[0] is not None else None
            if first_square is not None:
                result = a * mult // self.enemy_menace(first_square)
            else:
                result = 1000  # 如果没有有效的square，返回默认值
        except (ZeroDivisionError, IndexError):
            result = 1000
        
        # 缓存结果（限制缓存大小）
        if len(self._balance_cache) > 50:
            # 清理旧缓存
            old_keys = [k for k, t in self._balance_cache_time.items() if current_time - t > 1000]
            for k in old_keys:
                if k in self._balance_cache:
                    del self._balance_cache[k]
                del self._balance_cache_time[k]
        
        self._balance_cache[cache_key] = result
        self._balance_cache_time[cache_key] = current_time
        return result

    def player_is_an_enemy(self, p):
        """检查玩家p是否是敌人 - 优化版.

        D-Phase 2 (cont.): 20M calls/5min cw1, 整函数 Cython 化 (省 frame
        setup + bytecode dispatch). _fast 加载失败时走 _py_player_is_an_enemy.
        """
        if _fast is not None:
            return _fast.player_is_an_enemy(self, p)
        return self._py_player_is_an_enemy(p)

    def player_is_a_hostile_enemy(self, p):
        """非盟友且非中立玩家——用于战斗 AI 的目标选择与威胁评估。"""
        if p is None:
            return False
        return self.player_is_an_enemy(p) and not getattr(p, "neutral", False)

    def _py_player_is_an_enemy(self, p):
        """Python fallback (与 perception_fast.player_is_an_enemy 完全等价)."""
        if p is None:
            return False
        current_time = self.world.time
        if current_time - self._enemy_player_timestamp > 5000:
            self._enemy_player_cache.clear()
            self._enemy_player_timestamp = current_time
        if p.id in self._enemy_player_cache:
            return self._enemy_player_cache[p.id]
        result = p not in self.allied
        self._enemy_player_cache[p.id] = result
        return result

    def is_an_enemy(self, o):
        """检查对象o是否属于敌方 - 高度优化版.

        Round 4: Entity / ZoomTarget / TempTarget 都有 player = None class default,
        所以可以直接 o.player. 原 _cached_has_player 缓存机制纯多余, 删除.
        """
        p = o.player
        if p is None:
            return False
        if self.unit_under_allied_control(o):
            return False
        return self.player_is_an_enemy(p)

    def play(self):
        """AI游戏逻辑 - 基础版本，子类可覆盖"""
        pass  # play() is defined for computers