import os

from ..definitions import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL, rules

# 移动数值原语的 Cython 加速器
_mf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import movement_fast as _mf  # type: ignore[no-redef]
        _mf.set_time_interval(VIRTUAL_TIME_INTERVAL)
    except ImportError:
        _mf = None
from ..lib.nofloat import (
    PRECISION,
    int_angle,
    int_cos_1000,
    int_distance,
    int_sin_1000,
    square_of_distance,
    to_int,
)

from ..worldroom import Square, Inside, ZoomTarget
from ..worldentity import Entity

DISTANCE_MARGIN = 175  # millimeters
class CreatureMovement(Entity):
    def can_move_to(self, target_place) -> bool:
        """检查单位是否可以移动到目标区域。

        要求：
        - 单位有速度（speed > 0）
        - 目标区域有效且不同于当前区域
        - 地形允许
        - 出口未被阻挡（或存在可达路径）
        """
        if getattr(self, 'speed', 0) <= 0:
            return False
        if target_place is None or self.place is None:
            return False
        if target_place is self.place:
            return False
        if not self._can_go_terrain(target_place):
            return False
        return self._can_go(target_place)
    def move_to(self, place, x, y, o=None):
        """重写 Entity.move_to 方法以添加速度修正和地形效果

        Args:
            place: 目标区域
            x: 目标x坐标
            y: 目标y坐标
            o: 朝向角度(默认90度)
        """
        # 如果o为None，使用默认值90
        if o is None:
            o = 90
            
        # 调用父类的 move_to 进行基础移动
        super().move_to(place, x, y, o)

        # 应用速度修正
        target = getattr(self, 'action_target', None)
        if target is not None:
            self._actual_speed = self._get_speed_vs(target)
        else:
            self._actual_speed = getattr(self, 'speed', 0)

        # 应用地形速度修正 - 添加防御性检查
        if (hasattr(self, 'speed_on_terrain') and place and
                not isinstance(place, Inside) and  # 添加对Inside类的检查
                hasattr(place, 'type_name')):
            type_name = (
                place.type_name_at(self.x, self.y)
                if hasattr(place, "type_name_at")
                else place.type_name
            )
            if type_name:
                from ..lib.square_terrain_rules import terrain_list_value

                terrain_speed = terrain_list_value(type_name, self.speed_on_terrain)
                if terrain_speed is not None:
                    self._actual_speed = int(terrain_speed)
                    type_name = None
            if type_name and hasattr(place, 'terrain_speed'):
                if hasattr(place, "terrain_speed_at"):
                    terrain_speed = place.terrain_speed_at(self.x, self.y)
                else:
                    terrain_speed = place.terrain_speed
                terrain_type = 0 if getattr(self, 'airground_type', None) == "ground" else 1
                if terrain_type < len(terrain_speed):
                    self._actual_speed = (self._actual_speed * terrain_speed[terrain_type]) // 100

        # 确保最小速度
        if self._actual_speed > 0:
            self._actual_speed = max(self._actual_speed, getattr(self, 'VERY_SLOW', 1))
    # reach (avoiding collisions)
    def _already_walked(self, x, y):
        n = 0
        radius_2 = self.radius * self.radius
        for lw, xw, yw, weight in self.walked:
            if self.place is lw and square_of_distance(x, y, xw, yw) < radius_2:
                n += weight
        return n

    def _future_coords(self, rotation, target_d):
        if _mf is not None:
            return _mf.future_coords(
                self.x, self.y, self.o, self.actual_speed, rotation, target_d
            )
        d = self.actual_speed * VIRTUAL_TIME_INTERVAL // 1000
        if rotation == 0:
            d = min(d, target_d)  # stop before colliding target
        a = self.o + rotation
        x = int(self.x + d * int_cos_1000(a) // 1000)
        y = int(self.y + d * int_sin_1000(a) // 1000)
        return x, y

    def _heuristic_value(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        return abs(rotation) + self._already_walked(x, y) * 200

    def _can_go(self, new_place, ignore_blockers=False, ignore_forests=False):
        # 对空中单位的快速检查
        if self.airground_type != "ground":
            return True

        # 如果是当前位置
        if new_place is self.place:
            return True

        # 使用缓存系统避免重复计算
        if not hasattr(self, '_can_go_cache'):
            self._can_go_cache = {}
            self._can_go_cache_timestamp = self.world.time

        # 清理过期缓存
        current_time = self.world.time
        if current_time - self._can_go_cache_timestamp > 5000:  # 每5秒清理一次
            self._can_go_cache = {}
            self._can_go_cache_timestamp = current_time

        # 创建缓存键
        cache_key = (new_place.id if hasattr(new_place, 'id') else id(new_place),
                     ignore_blockers, ignore_forests)

        # 检查缓存
        if cache_key in self._can_go_cache:
            return self._can_go_cache[cache_key]

        from ..world_build_rules import square_has_construction_scaffold

        if (
            square_has_construction_scaffold(self.place)
            and square_has_construction_scaffold(new_place)
        ):
            self._can_go_cache[cache_key] = False
            return False

        # 实际检查逻辑
        result = False

        # 找到连接当前位置和目标位置的出口
        for e in self.place.exits:
            if e.other_side.place is new_place:
                if ignore_blockers:
                    result = True
                    break

                # 检查是否被阻挡
                if not e.is_blocked(self, ignore_forests=ignore_forests):
                    result = True
                    break
                else:
                    # 通知玩家观察到阻挡物
                    for o in e.blockers:
                        self.player.observe(o)
            else:
                # 检查间接连接的出口（两层出口检查）
                for e2 in e.other_side.place.exits:
                    if e2.other_side.place is new_place:
                        if ignore_blockers or not e2.is_blocked(self, ignore_forests=ignore_forests):
                            result = True
                            break
                if result:
                    break

        # 保存结果到缓存
        self._can_go_cache[cache_key] = result
        return result

    def _can_go_terrain(self, new_place):
        """检查单位是否可以进入目标地形"""
        # 空中单位不受地形限制
        if self.airground_type == "air":
            return True
        
        # 地面单位不能进入纯水路方格（渡口/大桥等 is_ground 方格除外）
        if (self.airground_type == "ground"
                and getattr(new_place, 'is_water', False)
                and not getattr(new_place, 'is_ground', True)):
            return False
            
        # 水面单位不能进入陆地区域
        if self.airground_type == "water" and not getattr(new_place, 'is_water', False):
            return False
            
        return True

    def _mark_the_dead_end(self) -> None:
        self.walked.append((self.place, self.x, self.y, 5))

    def _must_hold(self):
        return (
                not (self.player.smart_units or self.ai_mode == "defensive")
                and self.position_to_hold is not None
                and self.position_to_hold.contains(self.x, self.y)
        )

    def _must_not_go_to(self, x, y):
        return self._must_hold() and not self.position_to_hold.contains(x, y)

    def _try(self, rotation, target_d):
        x, y = self._future_coords(rotation, target_d)
        new_place = self.world.get_place_from_xy(x, y)
        if self._must_not_go_to(x, y):
            return False
        if (new_place is not None and hasattr(new_place, "is_passable_for")
                and not new_place.is_passable_for(self, x, y)):
            return False
        if self._can_go(new_place) and not self.would_collide_if(x, y):
            if abs(rotation) >= 90:
                self._mark_the_dead_end()
            self.move_to(new_place, x, y, self.o + rotation)
            self.unblock()
            return True

    _rotations = None
    _smooth_rotations = None

    def _reach(self, target_d):
        if self._smooth_rotations:  # "smooth rotation" mode
            rotation = self._smooth_rotations.pop(0)
            if self._try(rotation, target_d) or self._try(-rotation, target_d):
                self._smooth_rotations = []
        else:
            if not self._rotations:
                # update memory of dead ends
                self.walked = [x[0:3] + (x[3] - 1,) for x in self.walked if x[3] > 1]
                # "go straight" mode
                if not self.walked and self._try(0, target_d):
                    return
                # enter "rotation mode"
                self._rotations = [
                    (self._heuristic_value(x, target_d), x)
                    for x in (0, 45, -45, 90, -90, 135, -135, 180)
                ]
                self._rotations.sort()
            # "rotation" mode
            for _ in range(min(4, len(self._rotations))):
                _, rotation = self._rotations.pop(0)
                if self._try(rotation, target_d):
                    self._rotations = []
                    return
            if not self._rotations:
                # enter "smooth rotation mode"
                self._smooth_rotations = list(range(1, 180, 1))
                self.walked = []
                self._mark_the_dead_end()
                self.notify("collision")

    # hold
    def deploy(self):
        if isinstance(self.position_to_hold, ZoomTarget):
            self.action_target = self.position_to_hold
        elif self.player.smart_units:
            self.action_target = self.player.get_safest_subsquare(self.place)
        else:
            self.action_target = self.place.x, self.place.y

    def is_in_position(self, target):
        if self.place is target:
            return True
        if isinstance(target, ZoomTarget):
            return target.contains(self.x, self.y)

    def hold(self, target):
        self.position_to_hold = target
        self.deploy()

    # reach
    def _near_enough_to_aim(self, target):
        """判断 target 是否在攻击范围内.

        D-Phase 2: 移除 hot-path getattr.
        - target.airground_type: Entity class default "ground"
        - self.minimal_damage: D-Phase 2 在 Entity 加 class default 0
        - 其余字段 (place/projectile/radius) 已是 class default.
        place 可能为 None (单位 in transit), 用 ``is None`` 检查保留.

        D-Phase 2 §3.1: 整体 cpdef 化 (3.0M calls/5min, 10.8 s tottime).
        cython 版省 frame setup + LOAD_FAST + 字节码 dispatch.
        """
        self._sync_inside_combat_coords(target)
        try:
            if _mf is not None:
                return _mf.near_enough_to_aim(self, target)
            return self._py_near_enough_to_aim(target)
        finally:
            self._restore_inside_combat_coords(target)

    def _py_near_enough_to_aim(self, target):
        """Python fallback for _near_enough_to_aim (与 cython 版语义等价)."""
        # 添加从低地攻击高地的限制
        # 如果攻击者在低地，目标在高地，且攻击者没有投射物能力，则无法攻击
        self_place = self.place
        target_place = target.place
        if (self_place is not None and target_place is not None
                and not self_place.high_ground and target_place.high_ground
                and target.airground_type == "ground"
                and self.mdg_projectile != 1 and self.rdg_projectile != 1):
            return False

        dist2 = square_of_distance(self.x, self.y, target.x, target.y)
        collision = self.radius + target.radius
        DEFAULT_ATTACK_RANGE = 175

        # 获取对目标的伤害值，而不仅是基础伤害
        melee_damage = self._get_melee_damage_vs(target)
        ranged_damage = self._get_ranged_damage_vs(target)
        minimal_damage = self.minimal_damage

        can_use_mdg = False
        # 判断条件修改为检查最终伤害
        if melee_damage > 0 or minimal_damage > 0:
            eff_range = self.get_effective_mdg_range(target)
            max_range = eff_range if eff_range > 0 else DEFAULT_ATTACK_RANGE
            max_r2 = (max_range + collision) ** 2

            # 获取针对目标的最小射程 (基础 + 针对 target 的修正)
            min_range = self.mdg_minimal_range
            if target.type_name in self.mdg_minimal_range_vs:
                min_range += self.mdg_minimal_range_vs[target.type_name]
            else:
                for t in target.expanded_is_a:
                    if t in self.mdg_minimal_range_vs:
                        min_range += self.mdg_minimal_range_vs[t]
                        break

            if min_range > 0:
                min_r2 = (min_range + collision) ** 2
                if min_r2 <= dist2 <= max_r2:
                    can_use_mdg = True
            else:
                if dist2 <= max_r2:
                    can_use_mdg = True

        can_use_rdg = False
        # 判断条件修改为检查最终伤害
        if ranged_damage > 0 or minimal_damage > 0:
            eff_range = self.get_effective_rdg_range(target)
            max_range = eff_range if eff_range > 0 else DEFAULT_ATTACK_RANGE
            max_r2 = (max_range + collision) ** 2

            min_range = self.rdg_minimal_range
            if target.type_name in self.rdg_minimal_range_vs:
                min_range += self.rdg_minimal_range_vs[target.type_name]
            else:
                for t in target.expanded_is_a:
                    if t in self.rdg_minimal_range_vs:
                        min_range += self.rdg_minimal_range_vs[t]
                        break

            if min_range > 0:
                min_r2 = (min_range + collision) ** 2
                if min_r2 <= dist2 <= max_r2:
                    can_use_rdg = True
            else:
                if dist2 <= max_r2:
                    can_use_rdg = True

        return can_use_mdg or can_use_rdg

    def _near_enough(self, target):
        # note: always returns False if the target is a square
        if target.place is self.place:
            d = self.radius + target.radius + DISTANCE_MARGIN
            return square_of_distance(self.x, self.y, target.x, target.y) < d * d

    def _collision_range(self, other):
        if (
                self.collision
                and other.collision
                and other.airground_type == self.airground_type
        ):
            return self.radius + other.radius
        else:
            return 0

    def action_reach_and_stop(self):
        target = self.action_target
        if not self._near_enough(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(
                self.x, self.y, target.x, target.y
            )  # turn toward the goal
            self._reach(d - self._collision_range(target))
        else:
            self.walked = []
            self.target = None

    def action_reach_and_aim(self):
        target = self.action_target
        if not target:
            # 如果没有目标就直接返回，以免后面 target.x, target.y 报错
            return

        # 原本逻辑：还没有到可以攻击/瞄准的距离，继续移动
        if not self._near_enough_to_aim(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y)  # turn toward the goal
            self._reach(d - self._collision_range(target))
        else:
            self.walked = []
            self.aim(target)

    def action_reach_and_capture(self, target):
        """移动到可被夺取建筑处后直接占领（不进行攻击）。

        与 ``action_reach_and_aim`` 的移动逻辑一致，但到位后执行直接占领而非瞄准攻击。
        返回 True 表示已完成占领（调用方应结束当前动作），False 表示仍在靠近中。
        """
        if not target:
            return True
        if not self._near_enough_to_aim(target):
            d = int_distance(self.x, self.y, target.x, target.y)
            self.o = int_angle(self.x, self.y, target.x, target.y)  # turn toward the goal
            self._reach(d - self._collision_range(target))
            return False
        self.walked = []
        self._perform_capture(target)
        return True

    def go_to_xy(self, x, y):
        d = int_distance(self.x, self.y, x, y)
        if d > self.radius:
            self.o = int_angle(self.x, self.y, x, y)  # turn toward the goal
            self._reach(d)
        else:
            return True

    def flee(self):
        sl = [e.other_side.place for e in self.place.exits]
        if self._previous_square:
            sl.insert(0, self._previous_square)
        for s in sl:
            if self.player.balance(s, add=self, mult=100) > self.player.balance(
                    self.place, mult=100
            ):
                self.notify("flee")
                self.take_order(["go", s.id], imperative=True)
                break
    # orders
    # transport
    def stop(self):
        self.action_target = None
        self.position_to_hold = None
        # 重置冲锋状态，但保持冲锋的距离条件限制
        if hasattr(self, 'reset_charge_state'):
            self.reset_charge_state(force=False)
        
        # 停止后切换回默认武器
        if hasattr(self, 'switch_to_default_weapon'):
            self.switch_to_default_weapon()