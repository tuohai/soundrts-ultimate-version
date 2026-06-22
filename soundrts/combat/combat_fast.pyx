# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的战斗算术原语。

仅抽取纯算术热点：vs 字典查找、射程比较、伤害公式、命中率、溅射衰减。
战斗 Mixin（``damage_calculation``、``hit_miss``、``targeting``、``splash``）
保持纯 Python 类结构（受多继承 + cloudpickle 约束），调用本模块的函数
做内层算术。

所有公开函数都是 ``cpdef`` 或纯 ``def``，避免 ``cdef class`` 干扰 Mixin。

关键约束：
* 整数运算必须与 Python 字节一致（避免 RTS desync）。涉及 ``//`` / ``%`` 的
  函数使用 ``@cython.cdivision(False)``。
* 浮点运算（仅 splash decay）使用 C ``sqrt``，与 Python ``math.sqrt`` 同源。
"""

cimport cython
from libc.math cimport sqrt as c_sqrt

from soundrts.worldunit.world_public_method import matches_attack_targets


# --- vs 字典查找统一原语 -----------------------------------------------------

cpdef object resolve_vs_lookup(dict vs_dict, object type_name,
                               object expanded_is_a):
    """6 个 ``_get_*_vs`` 共有的前两层查找模式：

        1. ``vs_dict[type_name]`` 命中则返回该值
        2. 否则遍历 ``expanded_is_a``，第一个命中返回

    若都未命中返回 ``None``（让调用者继续走 armor/weapon 慢路径）。

    保留语义层级：返回的是 vs 加成值（int），调用者负责 ``base + vs``。
    """
    cdef object v
    if type_name is not None:
        v = vs_dict.get(type_name)
        if v is not None:
            return v
    if expanded_is_a is None:
        return None
    for t in expanded_is_a:
        v = vs_dict.get(t)
        if v is not None:
            return v
    return None


cpdef object resolve_vs_lookup_with_threshold(dict vs_dict, object type_name,
                                              object expanded_is_a,
                                              long long threshold,
                                              long long divisor):
    """与 ``resolve_vs_lookup`` 相同的查找逻辑，但若值 > threshold 则 ``// divisor``。

    用于 ``hit_miss`` 中 dodge 值大于 100 时除以 1000 还原为 0~100 的特殊处理。
    """
    cdef object v = resolve_vs_lookup(vs_dict, type_name, expanded_is_a)
    cdef long long iv
    if v is None:
        return None
    iv = <long long>v
    if iv > threshold:
        return iv // divisor
    return iv


# --- 射程检查 ---------------------------------------------------------------

@cython.cdivision(False)
cpdef bint range_check(long long dist2,
                       long long effective_range,
                       long long min_range,
                       long long collision):
    """判断 ``dist <= eff_range + collision`` 且 ``dist >= min_range + collision``。

    输入是 ``dist2``（已平方）以避免开方。比较都在平方空间完成。
    """
    cdef long long max_range2 = (effective_range + collision) * (effective_range + collision)
    cdef long long min_range2
    if min_range > 0:
        min_range2 = (min_range + collision) * (min_range + collision)
        if dist2 < min_range2:
            return False
    return dist2 <= max_range2


# --- 伤害公式 ---------------------------------------------------------------

cpdef long long apply_piercing(long long base_defense,
                               long long piercing,
                               long long piercing_resistance):
    """穿甲：``max(0, base_defense - max(0, piercing - piercing_resistance))``"""
    cdef long long net_pierce = piercing - piercing_resistance
    if net_pierce < 0:
        net_pierce = 0
    cdef long long reduced = base_defense - net_pierce
    if reduced < 0:
        return 0
    return reduced


cpdef long long calc_actual_damage(long long damage,
                                   long long defense,
                                   long long minimal_damage,
                                   long long forced_damage):
    """``DamageCalculationMixin._calculate_actual_damage`` 的内层算术。

    * actual = max(1, damage - defense)
    * 若 minimal_damage > 0：actual = max(actual, minimal_damage)
    * 若 forced_damage > 0：直接覆盖为 forced_damage

    与原 Python 实现完全一致。
    """
    cdef long long actual = damage - defense
    if actual < 1:
        actual = 1
    if minimal_damage > 0 and actual < minimal_damage:
        actual = minimal_damage
    if forced_damage > 0:
        actual = forced_damage
    return actual


# --- 命中率 -----------------------------------------------------------------

@cython.cdivision(False)
cpdef int calc_hit_chance(long long base_cover,
                          long long specific_cover_bonus,
                          long long terrain_cover_mod,
                          long long base_dodge,
                          long long specific_dodge_bonus,
                          long long terrain_dodge_mod):
    """命中率 = (cover + terrain) - (dodge + terrain)，clamp 到 [0, 100]。

    所有输入都应已转换为 0~100 区间（caller 负责 ``// 1000`` 的还原）。
    """
    cdef long long cover = base_cover + specific_cover_bonus + terrain_cover_mod
    cdef long long dodge = base_dodge + specific_dodge_bonus + terrain_dodge_mod
    cdef long long hit = cover - dodge
    if hit < 0:
        return 0
    if hit > 100:
        return 100
    return <int>hit


@cython.cdivision(False)
cpdef int clamp_0_100(long long x):
    """命中率/闪避率常用 clamp 工具。"""
    if x < 0:
        return 0
    if x > 100:
        return 100
    return <int>x


@cython.cdivision(False)
cpdef long long descale_if_internal(long long value, long long threshold,
                                    long long divisor):
    """若 value > threshold（如 100），返回 value // divisor（如 1000）；否则原样返回。

    用于 hit_miss 中的 dodge 值兼容（rules 文件可能写 50 = 50%，也可能写 50000 = 内部精度）。
    """
    if value > threshold:
        return value // divisor
    return value


# --- 溅射衰减 ---------------------------------------------------------------

cpdef double calc_splash_factor(long long dist2,
                                long long splash_range,
                                double decay_min_value):
    """``1.0 - (sqrt(dist2) / splash_range * (1.0 - decay_min))``

    Python 原版用 ``math.sqrt``。C 的 ``sqrt`` 在 IEEE 754 平台上与 Python
    一致；为保险这里也用 C ``sqrt(double)``。
    """
    if splash_range <= 0:
        return 0.0
    cdef double decay_range = 1.0 - decay_min_value
    cdef double dist = c_sqrt(<double>dist2)
    return 1.0 - (dist / splash_range * decay_range)


# --- 相对速度（attack_action 用到） -----------------------------------------

cpdef long long dot_product_2d(long long ax, long long ay,
                               long long bx, long long by):
    """二维向量点积，用于判断接近/远离。"""
    return ax * bx + ay * by


# --- 距离工具（消除 5 个文件中重复的 _square_of_distance） ------------------

cpdef long long square_of_distance(long long x1, long long y1,
                                   long long x2, long long y2):
    """与 ``nofloat_fast.square_of_distance`` 完全等价，提供给战斗模块。"""
    cdef long long dx = x2 - x1
    cdef long long dy = y2 - y1
    return dx * dx + dy * dy


# === D-Phase 2 §3.4: can_attack_if_in_range whole-function cpdef wrap =====
# targeting.can_attack_if_in_range: 4.3M calls / 5min cw1, 21.8 s tottime.
# 大头在 (1) 200ms cache 命中早返回; (2) damage_vs (已 §3.2 cython); (3) basic
# system 内嵌的 list 'in' 检查. 这里把整个函数 cython 化, self/other 仍是
# Python 对象. weapon_instances 冷路径回调 Python 方法 (大多数单位不进).


cpdef object can_attack_if_in_range(self, other):
    """Cython 化 ``TargetingMixin.can_attack_if_in_range``.

    与 Python 实现 (combat/targeting.py) 完全等价. 保留所有缓存写入语义,
    包括 "is_vulnerable False 分支不写 cache" 的原行为.

    Args:
        self: 攻击者 (Creature 实例, Python 对象)
        other: 目标 (Entity 实例 或 None)
    Returns:
        bool: 是否可以攻击
    """
    cdef object current_time = self.world.time
    cdef object time_bucket = current_time // 200
    cdef dict cache_dict = self._can_attack_cache

    if cache_dict is None or self._can_attack_cache_bucket != time_bucket:
        cache_dict = {}
        self._can_attack_cache = cache_dict
        self._can_attack_cache_bucket = time_bucket

    if other is None:
        return False

    cdef object other_id = other.id
    cdef object cached = cache_dict.get(other_id)
    if cached is not None:
        return cached

    # 廉价校验: place / hp / perception
    if other.place is None or other.hp < 0:
        cache_dict[other_id] = False
        return False
    if other not in self.player.perception:
        cache_dict[other_id] = False
        return False

    # 对目标的伤害值
    cdef long long melee_damage = self._get_melee_damage_vs(other)
    cdef long long ranged_damage = self._get_ranged_damage_vs(other)
    cdef long long minimal_damage = self.minimal_damage
    cdef bint has_attack = (melee_damage > 0 or ranged_damage > 0
                            or minimal_damage > 0)
    cdef bint mdg_explode = self.mdg_explode
    cdef bint rdg_explode = self.rdg_explode

    if not has_attack:
        if mdg_explode or rdg_explode:
            has_attack = True
        else:
            cache_dict[other_id] = False
            return False

    # 目标地面/空中 (复刻 world_public_method.ground_or_air)
    cdef object airground = other.airground_type
    cdef object target_type
    if airground == "water":
        target_type = "ground"
    else:
        target_type = airground

    # 武器/目标兼容性
    cdef bint can_attack_target = False
    cdef object weapons = self.weapons
    cdef object weapon_instances = getattr(self, '_weapon_instances', None)
    cdef object weapon, current_weapon, weapon_name

    if weapons and weapon_instances:
        # weapon_instances 冷路径: 回调 Python 方法
        if (self._should_auto_switch_weapon() and len(weapons) > 1 and
                not self._should_respect_manual_weapon_choice()):
            for weapon_name in weapons:
                if weapon_name not in weapon_instances:
                    continue
                weapon = weapon_instances[weapon_name]
                if self._check_weapon_target_compatibility(weapon, other, target_type):
                    can_attack_target = True
                    break
        else:
            current_weapon = getattr(self, 'current_weapon', None)
            if current_weapon and current_weapon in weapon_instances:
                weapon = weapon_instances[current_weapon]
                can_attack_target = self._check_weapon_target_compatibility(
                    weapon, other, target_type)
    else:
        # 回退基础系统 (大多数单位走这里)
        mdg = self.mdg
        rdg = self.rdg
        has_melee_system = (mdg > 0 or mdg_explode)
        has_ranged_system = (rdg > 0 or rdg_explode)

        if has_melee_system and not has_ranged_system:
            can_attack_target = matches_attack_targets(other, self.mdg_targets, target_type)
        elif has_ranged_system and not has_melee_system:
            can_attack_target = matches_attack_targets(other, self.rdg_targets, target_type)
        elif has_melee_system and has_ranged_system:
            can_melee = matches_attack_targets(other, self.mdg_targets, target_type)
            can_ranged = matches_attack_targets(other, self.rdg_targets, target_type)
            can_attack_target = can_melee or can_ranged

    if not can_attack_target:
        cache_dict[other_id] = False
        return False

    # 目标可被攻击 (NOTE: 此分支不写 cache, 保留原行为)
    if not other.is_vulnerable:
        return False

    # 低地攻击高地限制
    self_place = self.place
    other_place = other.place
    if (self_place is not None and other_place is not None
            and not self_place.high_ground and other_place.high_ground
            and other.airground_type == "ground"
            and self.mdg_projectile != 1 and self.rdg_projectile != 1):
        cache_dict[other_id] = False
        return False

    cache_dict[other_id] = True
    return True


# === D-Phase 2 §3.2: _get_melee/_get_ranged_damage_vs cpdef whole-fn =======
# damage_calculation._get_melee_damage_vs / _get_ranged_damage_vs:
# 6.4M + 6.4M calls / 5min cw1, 合计 ~9.4 s tottime. 大头被 _near_enough_to_aim
# / can_attack_if_in_range 调用. 内层 _vs_lookup 已 cython, 但 frame setup +
# armor 慢路径 + Python method dispatch 仍占主. 此函数把整个 lookup chain
# 一次走完, 调用方一次 cpdef = 省 ~2-3 个 Python frame.

cpdef long long compute_damage_vs(long long base_dg, dict dg_vs, target):
    """统一的 damage_vs 计算: base + adjust(target).

    等价于 damage_calculation._get_melee_damage_vs / _get_ranged_damage_vs
    (Python 实现). target 必须有: type_name, expanded_is_a, armor, _armor_instance
    (Entity class-level defaults 保证存在).

    Args:
        base_dg: self.mdg 或 self.rdg
        dg_vs:   self.mdg_vs 或 self.rdg_vs
        target:  目标实体 (Python 对象)
    Returns:
        long long: base_dg + 最具体的 vs 加成 (无加成时直接返回 base_dg)
    """
    cdef object v
    cdef object type_name = target.type_name
    cdef object expanded_is_a
    cdef object armor_name
    cdef object armor

    # 第一层: target.type_name
    if type_name is not None:
        v = dg_vs.get(type_name)
        if v is not None:
            return base_dg + <long long>v

    # 第二层: target.expanded_is_a
    expanded_is_a = target.expanded_is_a
    if expanded_is_a is not None:
        for t in expanded_is_a:
            v = dg_vs.get(t)
            if v is not None:
                return base_dg + <long long>v

    # 第三层: target.armor (字符串名)
    armor_name = target.armor
    if armor_name:
        v = dg_vs.get(armor_name)
        if v is not None:
            return base_dg + <long long>v

    # 第四层: target._armor_instance (Armor 对象, 含 expanded_is_a / is_a)
    armor = target._armor_instance
    if armor is not None:
        for armor_type in armor.expanded_is_a:
            if armor_type in dg_vs:
                return base_dg + <long long>dg_vs[armor_type]
        for armor_type in armor.is_a:
            if armor_type in dg_vs:
                return base_dg + <long long>dg_vs[armor_type]

    return base_dg
