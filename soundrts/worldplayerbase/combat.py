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
        # 初始化数据结构
        enemy_menace = {}
        enemy_presence = []
        places_with_corpses = set()
        places_with_friends = set()
        cataclysmic_places = set()
        
        # 使用缓存机制减少计算
        current_time = self.world.time
        cache_key = current_time // 500  # 每500ms更新一次
        
        # 初始化缓存
        # (_enemy_menace_cache / _enemy_menace_cache_time 已在 Player.__init__ 预初始化)
        
        # 检查缓存是否有效
        if self._enemy_menace_cache_time == cache_key:
            # 使用缓存数据
            self._enemy_menace = self._enemy_menace_cache.get('enemy_menace', {})
            self._enemy_presence = self._enemy_menace_cache.get('enemy_presence', [])
            self._places_with_corpses = self._enemy_menace_cache.get('places_with_corpses', set())
            self._places_with_friends = self._enemy_menace_cache.get('places_with_friends', set())
            self._cataclysmic_places = self._enemy_menace_cache.get('cataclysmic_places', set())
            return
            
        # 首先尝试复用 perception 生成的战斗快照（放宽至1000ms内有效）
        snapshot = getattr(self, '_combat_snapshot', None)
        if snapshot:
            snap_ts = snapshot.get('timestamp', 0)
            if self.world.time - snap_ts <= 2000:
                enemy_menace = dict(snapshot.get('place_enemy_menace', {}))
                enemy_presence = list(snapshot.get('enemy_presence_places', []))
                places_with_corpses = set(snapshot.get('corpse_places', set()))
                places_with_friends = set(snapshot.get('friend_places', set()))
                cataclysmic_places = set()  # 暂不在快照中构建
                # 保存结果并更新缓存后返回
                self._enemy_menace = enemy_menace
                self._enemy_presence = enemy_presence
                self._places_with_corpses = places_with_corpses
                self._places_with_friends = places_with_friends
                self._cataclysmic_places = cataclysmic_places
                self._enemy_menace_cache = {
                    'enemy_menace': enemy_menace,
                    'enemy_presence': enemy_presence,
                    'places_with_corpses': places_with_corpses,
                    'places_with_friends': places_with_friends,
                    'cataclysmic_places': cataclysmic_places
                }
                self._enemy_menace_cache_time = cache_key
                return

        # 敌方单位集合的短期缓存（200ms窗口），减少集合构建与交集成本
        # (_cached_enemy_units / _cached_enemy_units_time 已在 Player.__init__ 预初始化)

        # 使用优化的玩家关系判断
        enemy_players = [p for p in self.world.players if self.player_is_a_hostile_enemy(p)]

        # 使用已有的联盟单位缓存
        allied_units = self.get_allied_units()
        allied_vulnerable_units = {u for u in allied_units if u.is_vulnerable and not u.is_inside}

        # 创建敌人单位集合 - 200ms短期缓存，避免每帧重建
        if current_time - getattr(self, '_cached_enemy_units_time', 0) > 200:
            enemy_units = set()
            for p in enemy_players:
                enemy_units.update(p.units)
            self._cached_enemy_units = enemy_units
            self._cached_enemy_units_time = current_time
        else:
            enemy_units = getattr(self, '_cached_enemy_units', set())
        
        # 预处理感知中的对象 - 一次分类处理
        perception_objects = set(self.perception)
        memory_objects = set(self.memory)
        
        # 分类感知对象 - 按ID排序确保顺序一致
        enemy_units_perceived = enemy_units.intersection(perception_objects)
        enemy_units_remembered = enemy_units.intersection(memory_objects)
        
        # 优化：缓存类型检查，减少isinstance调用
        corpses_perceived = set()
        corpses_remembered = set()
        
        for o in perception_objects:
            if not hasattr(o, '_cached_is_corpse'):
                o._cached_is_corpse = isinstance(o, Corpse)
            if o._cached_is_corpse:
                corpses_perceived.add(o)
                
        for o in memory_objects:
            if not hasattr(o, '_cached_is_corpse'):
                o._cached_is_corpse = isinstance(o, Corpse)
            if o._cached_is_corpse:
                corpses_remembered.add(o)
        
        # 先处理感知中的敌方单位 - 按ID排序确保顺序一致
        sorted_enemy_perceived = sorted(enemy_units_perceived, key=lambda o: o.id)
        for o in sorted_enemy_perceived:
            if o.is_inside or not o.is_vulnerable:
                continue
                
            place = o.place
            # 优化：缓存Square类型检查
            if not hasattr(place, '_cached_is_square'):
                place._cached_is_square = isinstance(place, Square)
            if not place._cached_is_square:
                continue
                
            # 计算威胁
            menace = o.menace
            if place in enemy_menace:
                enemy_menace[place] += menace
            else:
                enemy_menace[place] = menace
                enemy_presence.append(place)
                
            # 处理远程单位
            # 优化：缓存is_melee属性检查
            if not hasattr(o, '_cached_is_melee'):
                o._cached_is_melee = getattr(o, 'is_melee', True)
            
            if not o._cached_is_melee:
                range_threat = menace // 10
                for neighbor in place.neighbors:
                    if neighbor in enemy_menace:
                        enemy_menace[neighbor] += range_threat
                    else:
                        enemy_menace[neighbor] = range_threat
        
        # 处理记忆中的敌方单位
        for o in enemy_units_remembered:
            if o.is_inside or not o.is_vulnerable:
                continue
                
            place = o.place
            # 优化：复用已有的Square类型检查缓存
            if not hasattr(place, '_cached_is_square'):
                place._cached_is_square = isinstance(place, Square)
            if not place._cached_is_square or place in enemy_presence:
                continue
                
            # 记忆中的单位威胁降低50%
            menace = o.menace // 2
            if place in enemy_menace:
                enemy_menace[place] += menace
            else:
                enemy_menace[place] = menace
                enemy_presence.append(place)
        
        # 处理尸体
        all_corpses = corpses_perceived.union(corpses_remembered)
        for o in all_corpses:
            place = o.place
            if isinstance(place, Square):
                places_with_corpses.add(place)
        
        # 处理友方单位
        for u in allied_vulnerable_units:
            place = u.place
            if isinstance(place, Square):
                places_with_friends.add(place)
        
        # 处理灾难性区域
        for o in perception_objects.union(memory_objects):
            if o.time_limit and o.harm_level:
                if isinstance(o.place, Square):
                    cataclysmic_places.add(o.place)
        
        # 保存结果
        self._enemy_menace = enemy_menace
        self._enemy_presence = enemy_presence
        self._places_with_corpses = places_with_corpses
        self._places_with_friends = places_with_friends
        self._cataclysmic_places = cataclysmic_places
        
        # 更新缓存
        self._enemy_menace_cache = {
            'enemy_menace': enemy_menace,
            'enemy_presence': enemy_presence,
            'places_with_corpses': places_with_corpses,
            'places_with_friends': places_with_friends,
            'cataclysmic_places': cataclysmic_places
        }
        self._enemy_menace_cache_time = cache_key

    def enemy_menace(self, place):
        try:
            return self._enemy_menace[place]
        except KeyError:
            return 0

    def is_very_dangerous(self, square_or_exit: Union[Square, Exit]) -> bool:
        if isinstance(square_or_exit, Square):
            return (
                self.square_is_dangerous(square_or_exit)
                and square_or_exit in self._enemy_presence
            )
        else:
            return (
                square_or_exit.other_side is not None
                and self.exit_is_dangerous(square_or_exit)
                and square_or_exit.other_side.place in self._enemy_presence
            )

    def square_is_dangerous(self, s: Square) -> bool:
        return s in self._enemy_menace

    def exit_is_dangerous(self, e: Exit) -> bool:
        return e.other_side.place in self._enemy_menace

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