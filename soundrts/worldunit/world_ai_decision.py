import os

from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)
from ..worldentity import Entity

# D-Phase 1: 内层 Cython 加速器 (失败时自动 fallback 到 Python).
_fast = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import world_ai_decision_fast as _fast  # type: ignore[no-redef]
    except ImportError:
        _fast = None

# VIRTUAL_TIME_INTERVAL 用于 sight cache bucket; world.time 是毫秒,
# 一个 tick = VIRTUAL_TIME_INTERVAL ms, sight 在一个 tick 内不会变.
from ..definitions import VIRTUAL_TIME_INTERVAL as _VTI

# D-Phase 1 T4: ai_mode 字符串 → int 映射. 在模块顶层 build dict,
# decide() 每帧每单位查一次 (1.1M calls/5min), dict.get 比字符串比较省 ~3-5x.
# 注: 与 world_ai_decision_fast.pyx 里的 AI_MODE_* 常量必须一致.
if _fast is not None:
    _AI_MODE_MAP = {
        "offensive": _fast.AI_MODE_OFFENSIVE,
        "chase": _fast.AI_MODE_CHASE,
        "defensive": _fast.AI_MODE_DEFENSIVE,
        "guard": _fast.AI_MODE_GUARD,
    }
    _AI_MODE_OTHER = _fast.AI_MODE_OTHER
else:
    _AI_MODE_MAP = {"offensive": 0, "chase": 1, "defensive": 2, "guard": 3}
    _AI_MODE_OTHER = 4
class CreatureAIDecision(Entity):
    # Round 4: class-level defaults 避免 decide 每帧 hasattr 检查.
    # decide 被每帧每单位调 (1.10M calls/5min); 每个 None sentinel 用 LOAD_ATTR
    # 一次即可判断是否计算过, 比 hasattr 慢路径快 3-4x.
    _last_decide_time = 0
    _cached_has_attack = None
    _cached_counterattack_enabled = None
    # D-Phase 2: counterattack_enabled class default = False, 替代 hot path
    # 上 getattr(self, 'counterattack_enabled', False). decide 调 1M+ /5min.
    counterattack_enabled = False
    # last_attacker class default = None, 替代 hasattr fallback.
    last_attacker = None

    def _is_neutral_target(self, other):
        p = getattr(other, "player", None)
        return p is not None and getattr(p, "neutral", False)

    def _flee_from_attacker(self):
        """受击后向远离攻击者的相邻方格逃跑（鹿、羊等狩猎动物）。"""
        if self.speed <= 0 or self.place is None:
            return False
        attacker = self.last_attacker
        if attacker is None or attacker.place is None:
            return False
        possible_squares = [s for s in self.place.exits if s.other_side]
        if not possible_squares:
            return False
        ax, ay = attacker.x, attacker.y
        best = max(
            possible_squares,
            key=lambda s: square_of_distance(
                s.other_side.place.x, s.other_side.place.y, ax, ay
            ),
        )
        self._herd_leader = None
        self.notify("flee")
        self.take_order(["go", best.other_side.place.id], imperative=True)
        return True

    @staticmethod
    def _is_wildlife_unit(unit=None):
        """狩猎动物或可驱赶牲畜（帝国时代式野生动物）。"""
        if unit is None:
            unit = CreatureAIDecision
        return bool(
            getattr(unit, "is_huntable", 0) or getattr(unit, "herdable", 0)
        )

    def _wildlife_wander(self):
        """野生动物在出生点附近随机徘徊（帝国时代式行为）。"""
        if not CreatureAIDecision._is_wildlife_unit(type(self)):
            return False
        if self.speed <= 0 or self.place is None or self.orders:
            return False
        if getattr(self, "_herd_leader", None) is not None:
            return False
        if self.last_attacker is not None:
            return False

        origin = getattr(self, "_wander_origin", None)
        if origin is None:
            self._wander_origin = (self.place, self.x, self.y)
            origin = self._wander_origin
        origin_place, ox, oy = origin
        wander_range = getattr(type(self), "wander_range", 0) or 12000
        max_dist_sq = wander_range * wander_range

        dist_sq = square_of_distance(self.x, self.y, ox, oy)
        if dist_sq > max_dist_sq:
            if origin_place is not None:
                self.take_order(["go", origin_place.id], imperative=True)
                return True
            return False

        if self.world.random.randint(0, 99) >= 12:
            return False

        possible_squares = [s for s in self.place.exits if s.other_side]
        if not possible_squares:
            return False

        valid = []
        for s in possible_squares:
            dest = s.other_side.place
            if square_of_distance(dest.x, dest.y, ox, oy) <= max_dist_sq:
                valid.append(s)
        if not valid:
            return False

        chosen = self.world.random.choice(valid)
        self.take_order(["go", chosen.other_side.place.id], imperative=True)
        return True

    def _maintain_herd_follow(self):
        """可驱赶动物持续跟随牧民（直接移动，不依赖中立玩家的视野解析）。"""
        leader = getattr(self, "_herd_leader", None)
        if leader is None:
            return
        if getattr(leader, "place", None) is None or getattr(leader, "hp", 0) <= 0:
            self._herd_leader = None
            self._herd_follow_place = None
            return
        herd_player = getattr(self, "_herd_player", None)
        leader_player = getattr(leader, "player", None)
        if (
            herd_player is not None
            and leader_player is not None
            and leader_player is not herd_player
            and leader_player not in getattr(herd_player, "allied", ())
        ):
            self._herd_leader = None
            self._herd_follow_place = None
            return
        if self.place is None or self.speed <= 0:
            return
        max_leash = getattr(type(self), "herd_leash_range", 0)
        if max_leash > 0:
            dist = int_distance(self.x, self.y, leader.x, leader.y)
            if dist > max_leash:
                self._herd_leader = None
                self._herd_follow_place = None
                return
        leader_place = leader.place
        prev_place = getattr(self, "_herd_follow_place", None)
        if self.place is leader_place:
            self._herd_follow_place = leader_place
            if (
                self._near_enough(leader)
                and not getattr(leader, "action_target", None)
            ):
                if self.action_target is not None:
                    self.stop()
                return
            following_leader = (
                self.action_target is not None
                and getattr(self.action_target, "id", None) == getattr(leader, "id", None)
            )
            if self.is_idle or not following_leader:
                self.cancel_all_orders()
                self.start_moving_to(leader, avoid=False)
            return
        if prev_place is not leader_place or self.is_idle:
            self._herd_follow_place = leader_place
            self.cancel_all_orders()
            self.start_moving_to(leader, avoid=False)

    @staticmethod
    def _same_unit_target(a, b):
        if a is None or b is None:
            return False
        return getattr(a, "id", None) == getattr(b, "id", None)

    def _player_ordered_attack_on(self, other):
        """玩家是否对该单位下达了强制攻击命令（imperative go/attack）。"""
        if not self.orders:
            return False
        order = self.orders[0]
        if not getattr(order, "is_imperative", False):
            return False
        if not CreatureAIDecision._same_unit_target(
            getattr(order, "target", None), other
        ):
            return False
        return getattr(order, "keyword", None) in ("attack", "go")
    # D-Phase 2 §4.3: decision_cache 现在用 (id, bucket) tuple key 替代
    # f"decision_{id}_{bucket}" 字符串 (decide 调 1.1M 次, f-string format
    # 每次 ~1us = ~1s 浪费). 同时 _decision_cache_bucket 用 sentinel 跟踪
    # 当前 bucket, bucket 变化时整体 clear, 防止 dict 无限增长.
    _decision_cache = {}
    _decision_cache_bucket = -1

    def decide(self):
        """优化的单位AI决策逻辑"""
        if getattr(self, "_has_yielded", False):
            return
        if getattr(type(self), "herdable", 0):
            leader = getattr(self, "_herd_leader", None)
            if (
                leader is not None
                and getattr(leader, "place", None) is not None
                and getattr(leader, "hp", 0) > 0
            ):
                return
        # 动态降频：根据单位状态/AI模式调整决策频率，减少重负载路径调用
        current_time = self.world.time
        last = self._last_decide_time

        # D-Phase 1 T4: interval 计算抽到 Cython (1.1M calls/5min).
        # 行为与原版完全一致 (参考: AI_MODE_*; offensive/chase=100, defensive=150,
        # 其他=400; speed<=0 加 300; last_attacker → min(interval, 80);
        # orders → max(80, interval-70)).
        ai_mode_id = _AI_MODE_MAP.get(self.ai_mode, _AI_MODE_OTHER)
        if _fast is not None:
            interval = _fast.compute_decide_interval(
                ai_mode_id,
                self.speed,
                self.last_attacker is not None,
                bool(self.orders),
            )
        else:
            if ai_mode_id == 0 or ai_mode_id == 1:  # offensive / chase
                interval = 100
            elif ai_mode_id == 2:  # defensive
                interval = 150
            else:
                interval = 400
            if self.speed <= 0:
                interval += 300
            if self.last_attacker is not None and interval > 80:
                interval = 80
            if self.orders:
                interval -= 70
                if interval < 80:
                    interval = 80

        if current_time - last < interval:
            return
        self._last_decide_time = current_time

        if getattr(type(self), "flee_on_hit", 0) and self.last_attacker is not None:
            if self._flee_from_attacker():
                return

        if self._wildlife_wander():
            return

        # 如果在载具内，选择载具位置的敌人
        if self.is_inside:
            # 获取容器的实际位置（确保是Square对象而不是Inside对象）
            container_place = self.place.container.place
            # 如果容器也在另一个容器内，需要找到最终的Square位置
            while hasattr(container_place, 'container') and hasattr(container_place, 'outside'):
                container_place = container_place.outside
            self._choose_enemy(container_place)
            return

        # 单位在过场 (in transit) 时 self.place 为 None (见 world_movement.py
        # 与 worldbase.resurrect). 后续目标选择 / balance / 逃跑逻辑全部假定
        # self.place 是合法 Square; place 为 None 时直接跳过本帧决策, 否则
        # known_enemies(None) 会在 place.objects 处抛 AttributeError.
        if self.place is None:
            return

        # 默认/持续自动探索：若该单位（按 rules.txt 配置 auto_explore，或玩家
        # 手动开启）启用了自动探索，且当前空闲且可移动，则下达 auto_explore
        # 标准命令。该命令会持续驱动探索；一旦发现敌人，下方战斗逻辑会在
        # 后续帧自动接管（attack 命令 forget_previous 覆盖 auto_explore）。
        # auto_explore 默认 False（类属性），绝大多数单位此处只是一次假值判断。
        if self.auto_explore and self.speed > 0 and not self.orders:
            self.take_order(["auto_explore"])
            return

        # 决策缓存: 100ms bucketed cache, 同 bucket 内复用同一单位决策.
        # D-Phase 2 §4.3: tuple key 替代 f-string (1.1M calls/5min)
        # + bucket 变化时 clear, 防止 dict 跨 1000+ bucket 累积.
        decision_bucket = current_time // 100
        cls = self.__class__
        if cls._decision_cache_bucket != decision_bucket:
            cls._decision_cache = {}
            cls._decision_cache_bucket = decision_bucket
        decision_cache = cls._decision_cache
        cache_key = (self.id, decision_bucket)
        if cache_key in decision_cache:
            # 恢复上一次的决策
            decision = decision_cache[cache_key]

            # 如果是攻击决策，应用之前的攻击目标
            if decision.get('action') == 'attack' and decision.get('target'):
                target = decision['target']
                # 确保目标仍然有效；中立单位仅在有强制攻击命令时才继续。
                # 额外校验目标仍是敌人：可被夺取的建筑一旦被占领即转为友方，
                # 此时必须停止攻击，避免对自己人下达无效的攻击/占领命令。
                if (target.place is not None and target.hp > 0
                        and self.is_an_enemy(target)
                        and (not self._is_neutral_target(target)
                             or self._player_ordered_attack_on(target))):
                    self._attack(target)
                return

            # 如果是逃跑决策且时间未过期，继续逃跑
            elif decision.get('action') == 'flee' and current_time - decision.get('time', 0) < 3000:
                # 避免重复逃跑计算，直接执行上次的逃跑命令
                if decision.get('escape_square'):
                    self.take_order(["go", decision['escape_square'].id], imperative=True)
                    return

        # 仅防御模式下的撤退判断：其他模式不撤退
        if (self.ai_mode == "defensive"
                and self.speed > 0  # 可以移动的单位
                and not self._must_hold()  # 不是被命令固定位置
                and self.player.balance(self.place, self._previous_square, mult=10) < 5):  # 战力不平衡

            # 计算逃跑
            possible_squares = [s for s in self.place.exits if s.other_side]

            # 找到威胁最小的安全区域
            if possible_squares:
                safest_square = min(
                    possible_squares,
                    key=lambda s: self.player.enemy_menace(s.other_side.place)
                )

                # 缓存逃跑决策
                decision_cache[cache_key] = {
                    'action': 'flee',
                    'time': current_time,
                    'escape_square': safest_square.other_side.place
                }

                # 执行逃跑
                self.notify("flee")
                self.take_order(["go", safest_square.other_side.place.id], imperative=True)
                return

        # 优化：缓存攻击能力检查，避免重复属性访问
        # (_cached_has_attack class default None; None 表示首次计算)
        if self._cached_has_attack is None:
            self._cached_has_attack = (self.mdg > 0) or (self.rdg > 0)

        if not self._cached_has_attack:
            return

        # 站岗模式处理：不主动攻击，但遭受攻击时反击
        # D-Phase 2: counterattack_enabled 现是 class default = False, 直接读取.
        if self.ai_mode == "guard":
            if (self.last_attacker is not None and self.last_attacker.place is not None and
                self.counterattack_enabled):
                # 站岗模式下，如果遭受攻击且反击开关开启，才进行反击
                # 缓存反击决策
                decision_cache[cache_key] = {
                    'action': 'attack',
                    'target': self.last_attacker
                }

                # 攻击
                self._attack(self.last_attacker)
            return  # 站岗模式不主动攻击，只有遭受攻击时才反击

        # 追击模式处理：主动追击视野内的敌人到射程内攻击
        if self.ai_mode == "chase":
            # 获取视野范围内的所有区域
            squares_in_sight = self._get_squares_in_sight()
            
            # 在视野范围内寻找最近的敌人
            closest_enemy = None
            closest_distance = float('inf')
            
            for square in squares_in_sight:
                # 获取该区域的敌人
                enemies = self.player.known_enemies(square)
                if not enemies:
                    # 如果 known_enemies 没返回敌人, 直接检查区域内对象.
                    # Round 4: square.objects (_Space.objects=()), obj.player/
                    # is_vulnerable/is_inside/hp 都在 Entity 基类有 default,
                    # 全部 hasattr 永远 True; 删除 _cached_ai_attrs 机制.
                    for obj in square.objects:
                        if (obj.player and obj.is_vulnerable and not obj.is_inside
                                and obj.hp > 0
                                and self.is_an_enemy(obj)
                                and not self._is_neutral_target(obj)):
                            enemies = [obj]
                            break
                
                # 计算与每个敌人的距离
                for enemy in enemies:
                    if self.can_attack(enemy):
                        # 计算距离（使用平方距离避免开方运算）
                        dist_squared = (self.x - enemy.x) ** 2 + (self.y - enemy.y) ** 2
                        if dist_squared < closest_distance:
                            closest_distance = dist_squared
                            closest_enemy = enemy
            
            # 如果找到了敌人
            if closest_enemy:
                # 如果敌人在当前区域且可以攻击，直接攻击
                if closest_enemy.place is self.place and self.in_attack_range(closest_enemy):
                    self._attack(closest_enemy)
                    return
                
                # 如果敌人在相邻区域，移动到敌人所在区域
                # Round 4: speed/take_order 永远存在 (Entity.speed=0; 方法)
                if closest_enemy.place in self.place.neighbors:
                    if self.speed > 0:
                        # 使用take_order来执行移动命令
                        self.take_order(["go", closest_enemy.place.id], forget_previous=True)
                        return

                # 如果敌人在更远的区域，移动到最近的相邻区域
                elif self.speed > 0:
                    # 找到通往敌人区域的最短路径
                    target_place = closest_enemy.place
                    self.take_order(["go", target_place.id], forget_previous=True)
                    return
            
            # 如果没有找到敌人，使用原来的逻辑作为后备
            # 优先攻击当前位置的敌人
            # Round 4: self.action 永远存在 (Creature.__init__ self.action = None);
            # action 对象有 target 属性 (worldaction 类).
            if self._choose_enemy(self.place):
                last_target = self.action.target if (self.action is not None
                                                     and hasattr(self.action, 'target')) else None

                # 缓存攻击决策
                if last_target:
                    decision_cache[cache_key] = {
                        'action': 'attack',
                        'target': last_target
                    }
                return

            # 如果当前区域没有敌人，主动追击相邻区域的敌人
            threatening_neighbors = [
                place for place in self.place.neighbors
                if self.player.enemy_menace(place) > 0
            ]

            if threatening_neighbors:
                # 选择威胁最大的相邻区域
                target_place = max(
                    threatening_neighbors,
                    key=lambda p: self.player.enemy_menace(p)
                )

                # 使用take_order来执行移动命令
                if self.speed > 0:
                    self.take_order(["go", target_place.id], forget_previous=True)
                    return
            return

        # 防御模式处理：根据威胁值决定是攻击还是逃跑
        if self.ai_mode == "defensive":
            # 计算当前区域的威胁平衡
            threat_balance = self.player.balance(self.place, self._previous_square, mult=1)
            
            # 如果威胁值低于己方（threat_balance > 0），攻击敌人
            if threat_balance > 0:
                if self._choose_enemy(self.place):
                    last_target = self.action.target if (self.action is not None
                                                         and hasattr(self.action, 'target')) else None

                    # 缓存攻击决策
                    if last_target:
                        decision_cache[cache_key] = {
                            'action': 'attack',
                            'target': last_target
                        }
                    return
            # 如果威胁值高于己方（threat_balance <= 0），逃跑逻辑已经在上面处理了
            return

        # 进攻模式处理：主动攻击敌人
        if self.ai_mode == "offensive" or self.player.smart_units:
            # 尝试选择当前位置的敌人
            if self._choose_enemy(self.place):
                last_target = self.action.target if (self.action is not None
                                                     and hasattr(self.action, 'target')) else None

                # 缓存攻击决策
                if last_target:
                    decision_cache[cache_key] = {
                        'action': 'attack',
                        'target': last_target
                    }
                return

            # 如果当前区域没有敌人，检查是否应该追击敌人
            # 进攻模式需要检查反击开关 (D-Phase 2: class default 替代 getattr)
            if self.counterattack_enabled:
                threatening_neighbors = [
                    place for place in self.place.neighbors
                    if self.player.enemy_menace(place) > 0
                ]

                if threatening_neighbors:
                    # 选择威胁最大的相邻区域
                    target_place = max(
                        threatening_neighbors,
                        key=lambda p: self.player.enemy_menace(p)
                    )

                    # 移动到目标区域
                    if self.can_move_to(target_place):
                        # 使用已有的 go 命令移动
                        self.take_order(["go", target_place.id], forget_previous=True)
                        return
    def _get_squares_in_sight(self):
        """获取单位视野范围内的所有区域.

        D-Phase 1 T1: 帧级 cache + Cython 化 BFS.
        - bucket = world.time // VIRTUAL_TIME_INTERVAL, 同 bucket 内复用结果
        - cache miss 时调 _fast.bfs_squares_in_sight (Cython, fallback Python)
        - sight_range 不变 + place 不变 + 同帧 → 同结果, 安全
        """
        place = self.place
        sight_range = self.sight_range

        # 同 unit 在同帧重复调 _get_squares_in_sight 的场景: cache hit
        world = place.world
        bucket = world.time // _VTI
        cache = world._sights_cache
        if world._sights_cache_bucket != bucket:
            cache.clear()
            world._sights_cache_bucket = bucket
        key = (id(place), sight_range)
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Cython 加速版 (与 Python 版本语义等价)
        if _fast is not None:
            result = _fast.bfs_squares_in_sight(place, sight_range)
        else:
            result = self._py_bfs_squares_in_sight(place, sight_range)

        cache[key] = result
        return result

    @staticmethod
    def _py_bfs_squares_in_sight(start_place, sight_range):
        """Python fallback for D-Phase 1 T1 BFS — 与 cython 版语义一致."""
        squares = {start_place}
        if sight_range <= 1:
            return squares
        if sight_range <= 2:
            for p in start_place.neighbors:
                squares.add(p)
            return squares
        visited = {start_place}
        queue = [(start_place, 0)]
        qi = 0
        qlen = 1
        while qi < qlen:
            current_place, distance = queue[qi]
            qi += 1
            if distance >= sight_range:
                continue
            for neighbor in current_place.neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    squares.add(neighbor)
                    queue.append((neighbor, distance + 1))
                    qlen += 1
        return squares
    def in_attack_range(self, target):
        """检查目标是否在攻击射程内"""
        if target is None:
            return False

        # 添加从低地攻击高地的限制
        # 如果攻击者在低地，目标在高地，且攻击者没有投射物能力，则无法攻击
        if (hasattr(self, 'place') and hasattr(target, 'place') and
                self.place is not None and target.place is not None):
            attacker_high = (
                self.place.high_ground_at(self.x, self.y)
                if hasattr(self.place, "high_ground_at")
                else self.place.high_ground
            )
            target_high = (
                target.place.high_ground_at(target.x, target.y)
                if hasattr(target.place, "high_ground_at")
                else target.place.high_ground
            )
            if (not attacker_high and target_high and
                target.airground_type == "ground" and
                not ((hasattr(self, 'mdg_projectile') and self.mdg_projectile == 1) or
                     (hasattr(self, 'rdg_projectile') and self.rdg_projectile == 1))):
                return False

        dist2 = square_of_distance(self.x, self.y, target.x, target.y)
        collision = self.radius + target.radius

        # 如果是近战单位（射程为0），只要在同一个区域就视为在攻击范围内
        if (self.mdg_range == 0 and self.mdg > 0) or (self.rdg_range == 0 and self.rdg > 0):
            return target.place is self.place

        if self.mdg_range > 0:
            max_range2 = (self.mdg_range + collision) ** 2
            if dist2 <= max_range2:
                return True

        if self.rdg_range > 0:
            max_range2 = (self.rdg_range + collision) ** 2
            if dist2 <= max_range2:
                return True

        return False
    # D-Phase 1 T3: 删除上面的 def can_attack(target) 死代码 — Python 后定义
    # 的同名方法覆盖前者, line 394-432 早就不会被调用 (game 一直在跑下面这个).
    # 只保留 line 434 这个 "without moving to another square" 版本.
    def can_attack(self, other):  # without moving to another square
        if not self.is_an_enemy(other):
            return False
        # 进攻/防御/追击等 AI 不主动攻击中立者；仅强制攻击命令例外
        if self._is_neutral_target(other) and not self._player_ordered_attack_on(other):
            return False
        # 条约期内禁止攻击敌对单位
        try:
            if getattr(self.world, "treaty_until_time", 0) > 0 and self.world.time < self.world.treaty_until_time:
                if hasattr(other, 'player') and other.player is not None and self.player.player_is_an_enemy(other.player):
                    return False
        except Exception:
            pass
        if not self.can_attack_if_in_range(other):
            return False
        # D-Phase 1 T3: damage 本地变量缓存. mdg_range / rdg_range 一般固定;
        # 3.6M calls/5min, 原版每次 self._get_melee/ranged_damage_vs 调用都
        # 走 method dispatch + dict lookup, 本地变量后 hot path 上 LOAD_FAST 即可.
        mdg_range = self.mdg_range
        rdg_range = self.rdg_range
        is_same_place = other.place is self.place
        # 如果是近战单位（射程为0）且在同一区域，允许攻击
        if is_same_place and (mdg_range == 0 or rdg_range == 0):
            minimal = getattr(self, 'minimal_damage', 0)
            if mdg_range == 0:
                if self._get_melee_damage_vs(other) > 0 or minimal > 0:
                    return True
            if rdg_range == 0:
                if self._get_ranged_damage_vs(other) > 0 or minimal > 0:
                    return True
        if self.speed and is_same_place:
            return True
        return self._near_enough_to_aim(other)

    def immediate_order_toggle_ai_mode(self):
        """切换 AI 模式的顺序：offensive -> defensive -> guard -> chase -> offensive"""
        modes = ["offensive", "defensive", "guard", "chase"]
        current_index = modes.index(self.ai_mode)
        next_index = (current_index + 1) % len(modes)
        self.ai_mode = modes[next_index]
        self.notify("order_ok")
    def immediate_order_toggle_counterattack(self):
        """处理反击开关命令"""
        # 切换反击状态
        self.counterattack_enabled = not self.counterattack_enabled

        # 发送状态变更通知
        if self.counterattack_enabled:
            self.notify("counterattack_enabled")
        else:
            self.notify("counterattack_disabled")

        # 发送命令完成通知
        self.notify("order_ok")