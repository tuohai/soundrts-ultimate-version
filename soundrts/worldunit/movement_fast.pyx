# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的单位移动微原语。

战术层移动旋转探路（``_try``）每 tick 每移动中单位被调用多次，
本模块只抽取确实可加速的数值运算（``_future_coords`` 的三角投影）。

``_can_go`` / ``_reach`` 这类带 Python callback 的逻辑保持在 Python 层，
否则需要重构整个 Mixin 体系（参见 plan 中的"架构约束"）。
"""

cimport cython
# 用 Python import（cpdef 调用开销可忽略），避免对 nofloat_fast 暴露 .pxd
from soundrts.lib.nofloat_fast import int_cos_1000, int_sin_1000


# 与 soundrts.definitions.VIRTUAL_TIME_INTERVAL 对齐（300ms）。
# 若上游常量调整，此处也需同步；为安全起见暴露 set 函数。
cdef long long _TIME_INTERVAL_MS = 300


def set_time_interval(long long ms):
    """允许测试或上游同步 VIRTUAL_TIME_INTERVAL。"""
    global _TIME_INTERVAL_MS
    _TIME_INTERVAL_MS = ms


@cython.cdivision(False)
def future_coords(long long x, long long y, int orientation,
                  long long actual_speed, int rotation,
                  long long target_d):
    """复刻 ``CreatureMovement._future_coords``：

        d = actual_speed * VIRTUAL_TIME_INTERVAL // 1000
        if rotation == 0:
            d = min(d, target_d)
        a = orientation + rotation
        new_x = x + d * int_cos_1000(a) // 1000
        new_y = y + d * int_sin_1000(a) // 1000

    所有 ``//`` 用 Python floor division（``cdivision=False``）。
    返回 (new_x, new_y) 二元组（Python ints，与原版兼容）。
    """
    cdef long long d = actual_speed * _TIME_INTERVAL_MS // 1000
    if rotation == 0 and d > target_d:
        d = target_d
    cdef int a = orientation + rotation
    cdef long long cos_v = int_cos_1000(a)
    cdef long long sin_v = int_sin_1000(a)
    cdef long long new_x = x + d * cos_v // 1000
    cdef long long new_y = y + d * sin_v // 1000
    return int(new_x), int(new_y)


# === D-Phase 2 §3.1: _near_enough_to_aim whole-function cpdef wrap =========
# 3.0M calls / 5min cw1, 10.8 s tottime, 22.4 s cumtime (Python).
# self / target 仍是 Python 对象, 此处仅把函数体 cython 化, 省 frame setup +
# 字节码 dispatch + local var LOAD_FAST. 调 self._get_*_damage_vs / 
# self.get_effective_*_range 仍是 Python method dispatch.

cdef long long _DEFAULT_ATTACK_RANGE = 175


cpdef bint near_enough_to_aim(self, target) except -1:
    """Cython 化的 ``CreatureMovement._near_enough_to_aim``.

    语义与 Python 版完全一致 (见 ``world_movement.py``).

    Args:
        self: Creature 实例 (Python 对象)
        target: 目标实体 (Python 对象)
    Returns:
        bint: 是否在攻击范围内
    """
    cdef object self_place = self.place
    cdef object target_place = target.place

    # 高地限制
    if (self_place is not None and target_place is not None
            and not self_place.high_ground and target_place.high_ground
            and target.airground_type == "ground"
            and self.mdg_projectile != 1 and self.rdg_projectile != 1):
        return False

    cdef long long sx = self.x
    cdef long long sy = self.y
    cdef long long tx = target.x
    cdef long long ty = target.y
    cdef long long dx = sx - tx
    cdef long long dy = sy - ty
    cdef long long dist2 = dx * dx + dy * dy
    cdef long long collision = (<long long>self.radius) + (<long long>target.radius)

    cdef long long melee_damage = self._get_melee_damage_vs(target)
    cdef long long ranged_damage = self._get_ranged_damage_vs(target)
    cdef long long minimal_damage = self.minimal_damage

    cdef long long eff_range, max_range, max_r2, min_range, min_r2
    cdef dict vs_dict
    cdef object expanded_is_a
    cdef object type_name

    # 近战检查
    if melee_damage > 0 or minimal_damage > 0:
        eff_range = self.get_effective_mdg_range(target)
        max_range = eff_range if eff_range > 0 else _DEFAULT_ATTACK_RANGE
        max_r2 = (max_range + collision) * (max_range + collision)

        min_range = self.mdg_minimal_range
        vs_dict = self.mdg_minimal_range_vs
        type_name = target.type_name
        if type_name in vs_dict:
            min_range += vs_dict[type_name]
        else:
            expanded_is_a = target.expanded_is_a
            for t in expanded_is_a:
                if t in vs_dict:
                    min_range += vs_dict[t]
                    break

        if min_range > 0:
            min_r2 = (min_range + collision) * (min_range + collision)
            if min_r2 <= dist2 <= max_r2:
                return True
        else:
            if dist2 <= max_r2:
                return True

    # 远程检查
    if ranged_damage > 0 or minimal_damage > 0:
        eff_range = self.get_effective_rdg_range(target)
        max_range = eff_range if eff_range > 0 else _DEFAULT_ATTACK_RANGE
        max_r2 = (max_range + collision) * (max_range + collision)

        min_range = self.rdg_minimal_range
        vs_dict = self.rdg_minimal_range_vs
        type_name = target.type_name
        if type_name in vs_dict:
            min_range += vs_dict[type_name]
        else:
            expanded_is_a = target.expanded_is_a
            for t in expanded_is_a:
                if t in vs_dict:
                    min_range += vs_dict[t]
                    break

        if min_range > 0:
            min_r2 = (min_range + collision) * (min_range + collision)
            if min_r2 <= dist2 <= max_r2:
                return True
        else:
            if dist2 <= max_r2:
                return True

    return False
