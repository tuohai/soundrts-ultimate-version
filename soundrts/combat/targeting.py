import os

from ..lib.nofloat import PRECISION, int_distance, square_of_distance
from ..worldunit.world_public_method import ground_or_air, matches_attack_targets
from ..worldaction import AttackAction

_cf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import combat_fast as _cf  # type: ignore[no-redef]
    except ImportError:
        _cf = None


def _resolve_vs_py(vs_dict, type_name, expanded_is_a):
    if vs_dict is None:
        return None
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


_vs_lookup = _cf.resolve_vs_lookup if _cf is not None else _resolve_vs_py
_range_check = _cf.range_check if _cf is not None else None


def _range_check_py(dist2, eff_range, min_range, collision):
    max_range2 = (eff_range + collision) ** 2
    if min_range > 0:
        min_range2 = (min_range + collision) ** 2
        if dist2 < min_range2:
            return False
    return dist2 <= max_range2


if _range_check is None:
    _range_check = _range_check_py


# 夺取阈值为 100 的敌方建筑“接触即占领”：单位只要打中一下即可夺取。
# 为避免多个单位同时对同一建筑下达占领命令（占领成功后建筑转为友方，
# 其余命令立刻变成无效命令），由第一个决定占领的单位“声明”该建筑，
# 其他单位在声明有效期内不再下达占领命令。声明者每次决策都会刷新声明，
# 因此只要它仍在占领途中声明就不会过期；一旦它死亡/停止，声明在超时后失效，
# 其他单位可以接手。
_CAPTURE_CLAIM_TIMEOUT = 1000  # ms


def _is_capture_on_contact(target):
    """敌方建筑夺取阈值为 100：接触即夺取，AI 应直接占领而非反复攻击。"""
    return getattr(target, "capture_hp_threshold", 0) == 100


class TargetingMixin:
    """
    处理目标选择和攻击范围相关的功能
    """
    def _capture_claimed_by_other(self, target):
        """该可占领建筑是否已被其他存活单位声明占领（声明仍在有效期内）。"""
        claimer_id = getattr(target, "_capture_claimer_id", None)
        if claimer_id is None or claimer_id == self.id:
            return False
        claim_time = getattr(target, "_capture_claim_time", 0)
        return (self.world.time - claim_time) <= _CAPTURE_CLAIM_TIMEOUT

    def _claim_capture(self, target):
        """声明由本单位负责占领该建筑，并刷新声明时间。"""
        target._capture_claimer_id = self.id
        target._capture_claim_time = self.world.time

    def menace_versus(self, observer):
        """Threat of ``self`` when ``observer`` is choosing targets.

        Lookup order on this unit's rules:
        1. ``menace_vs`` vs observer type / is_a (absolute)
        2. ``menace_mult_vs`` vs observer → auto multi-dim base × weight
        3. else ``self.menace`` (absolute menace / menace_mult / auto score)
        """
        obs_type = getattr(observer, "type_name", None)
        obs_isa = getattr(observer, "expanded_is_a", None)
        vs = getattr(self, "menace_vs", None)
        if vs:
            v = _vs_lookup(vs, obs_type, obs_isa)
            if v is not None:
                return v
        mult_vs = getattr(self, "menace_mult_vs", None)
        if mult_vs:
            m = _vs_lookup(mult_vs, obs_type, obs_isa)
            if m is not None:
                if hasattr(self, "_auto_combat_menace_base"):
                    base = self._auto_combat_menace_base()
                else:
                    mdg = getattr(self, "mdg", 0) or 0
                    rdg = getattr(self, "rdg", 0) or 0
                    base = mdg if mdg > rdg else rdg
                    if not base:
                        tc = getattr(self, "transport_capacity", 0) or 0
                        if tc:
                            base = tc * PRECISION * 2
                if not base:
                    return 0
                return base * m // PRECISION
        return self.menace

    def _choose_enemy(self, place):
        # 1.3.8.1-style: sort by menace (rules may override auto damage threat).
        # Same-square object scan: idle perception throttle must not leave an
        # empty known_enemies list while hostiles share the square.
        known = self.player.known_enemies(place)
        if not known:
            for place in place.strict_neighbors:
                known = self.player.known_enemies(place)
                if known:
                    break
        if not known and place is self.place:
            local = []
            for obj in place.objects:
                if (
                    obj.player is not None
                    and obj.is_vulnerable
                    and not obj.is_inside
                    and obj.hp > 0
                    and self.is_an_enemy(obj)
                    and not self._is_neutral_target(obj)
                ):
                    local.append(obj)
            known = local
        reachable_enemies = [x for x in known if self.can_attack(x)]
        if reachable_enemies:
            player = self.player
            smart = getattr(player, "smart_units", False)
            if smart:
                skill = max(0, min(100, getattr(player, "counter_skill", 100)))
            else:
                skill = 0

            def _enemy_sort_key(enemy):
                dist2 = square_of_distance(self.x, self.y, enemy.x, enemy.y)
                threat = enemy.menace_versus(self) if hasattr(
                    enemy, "menace_versus"
                ) else enemy.menace
                if skill > 0:
                    score = (
                        self._get_vs_damage_bonus(enemy) * skill
                        + threat * (100 - skill)
                    )
                    return (-score, dist2, enemy.id)
                return (-threat, dist2, enemy.id)

            reachable_enemies.sort(key=_enemy_sort_key)
            # 按优先级遍历：对“接触即占领”的敌方建筑，若已有其他单位在占领中
            # 则跳过（避免无效命令），改打下一个目标；否则声明占领并直接占领。
            for enemy in reachable_enemies:
                if _is_capture_on_contact(enemy) and bool(getattr(self, "can_capture", 1)):
                    if self._capture_claimed_by_other(enemy):
                        continue
                    self._claim_capture(enemy)
                self._attack(enemy)
                return True

    def _get_height_bonus_range(self, is_melee=True):
        """计算基于高度和投射物类型的额外射程加成

        Args:
            is_melee: 是否为近战攻击

        Returns:
            int: 额外射程加成(内部单位:毫米)

        Round 4: self.height (CreatureAttributes property)、self.place.high_ground/height
        在所有 _Space/Creature 类都有, hasattr 永远 True; 直接访问.
        place 可能为 None (单位 in transit), 用 if place is None 替代.
        """
        place = self.place
        if place is None:
            return 0

        # 获取相应的投射物标志
        projectile_flag = self.mdg_projectile if is_melee else self.rdg_projectile
        if not projectile_flag:
            return 0

        # 计算与当前位置的高度差
        height_diff = self.height - place.height
        if height_diff <= 0:
            return 0

        # 每1级高度差增加1格射程（与1.3.8.1一致，PRECISION=1000 毫米）
        return (height_diff // 1) * 1000  # 转换为内部单位(毫米)

    def get_effective_mdg_range(self, target):
        """获取对特定目标的有效近战射程.

        Round 4: mdg_range / mdg_range_vs / expanded_is_a / _armor_instance
        都在 Creature/Armor 类有 class-level default, hasattr 永远 True.
        get_current_armor_name 是方法, 永远存在.
        原 elif 链中 ``hasattr(target, 'expanded_is_a')`` 永远 True →
        后续 armor 分支永远不达 (原行为, 保留 dead-code 注释).
        """
        # 如果射程为0，返回一个足够小的射程
        if self.mdg_range == 0:
            return 1

        # 获取基础射程
        base_range = self.mdg_range

        # 检查是否有针对特定目标的射程
        if self.mdg_range_vs:
            # 直接检查目标类型
            if target.type_name in self.mdg_range_vs:
                base_range += self.mdg_range_vs[target.type_name]
            else:
                # expanded_is_a 永远存在 (Creature 默认 ()).
                # 原代码后续还有 armor_name / armor.expanded_is_a / armor.is_a
                # fallback 链, 但因为本 elif 永远命中, 那些分支永远不达, 删除.
                for t in target.expanded_is_a:
                    if t in self.mdg_range_vs:
                        base_range += self.mdg_range_vs[t]
                        break

        # 使用现有的高度加成方法
        height_bonus = self._get_height_bonus_range(is_melee=True)
        if height_bonus > 0:
            base_range += height_bonus

        return base_range

    def get_effective_rdg_range(self, target):
        """获取对特定目标的有效远程射程.

        Round 4: 同 ``get_effective_mdg_range``, 全部 hasattr 永远 True.
        """
        # 如果射程为0，返回一个足够小的射程
        if self.rdg_range == 0:
            return 1

        # 获取基础射程
        base_range = self.rdg_range

        # 检查是否有针对特定目标的射程
        if self.rdg_range_vs:
            # 直接检查目标类型
            if target.type_name in self.rdg_range_vs:
                base_range += self.rdg_range_vs[target.type_name]
            else:
                # expanded_is_a 永远存在; armor fallback 永远不达 (见 mdg 同函数注释)
                for t in target.expanded_is_a:
                    if t in self.rdg_range_vs:
                        base_range += self.rdg_range_vs[t]
                        break

        # 使用现有的高度加成方法
        height_bonus = self._get_height_bonus_range(is_melee=False)
        if height_bonus > 0:
            base_range += height_bonus

        return base_range

    def in_melee_range(self, target) -> bool:
        """判断目标是否在近战范围内。

        热路径：``square_of_distance`` 与 ``range_check`` 都走 Cython；
        最小射程 vs 字典查找走 ``_vs_lookup``（前两层 type_name + expanded_is_a）。
        armor 层保留 Python（与原版等价，仅在前两层都 miss 时进入）。

        Round 4: target.expanded_is_a 永远存在 (Creature 默认 ()); armor 层
        ``get_current_armor_name`` 是方法、``_armor_instance`` 在 worldbase
        __init__ 中初始化, hasattr 永远 True. Armor 类的 expanded_is_a/is_a
        也有 class-level default. 全部删除 hasattr.
        """
        dist2 = square_of_distance(self.x, self.y, target.x, target.y)
        effective_range = self.get_effective_mdg_range(target)
        collision = self.radius + target.radius

        # 最小射程 vs 修正（前两层 Cython 加速）
        min_range = self.mdg_minimal_range
        v = _vs_lookup(self.mdg_minimal_range_vs, target.type_name,
                       target.expanded_is_a)
        if v is not None:
            min_range += v
        else:
            # armor 慢路径（与原版完全等价，仅在前两层都 miss 时进入）
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.mdg_minimal_range_vs:
                min_range += self.mdg_minimal_range_vs[armor_name]
            else:
                armor = target._armor_instance
                if armor is not None:
                    for armor_type in armor.expanded_is_a:
                        if armor_type in self.mdg_minimal_range_vs:
                            min_range += self.mdg_minimal_range_vs[armor_type]
                            break
                    else:
                        for armor_type in armor.is_a:
                            if armor_type in self.mdg_minimal_range_vs:
                                min_range += self.mdg_minimal_range_vs[armor_type]
                                break

        return _range_check(dist2, effective_range, min_range, collision)

    def in_ranged_range(self, target) -> bool:
        """判断目标是否在远程范围内.

        Round 4: 同 in_melee_range 的优化.
        """
        effective_range = self.get_effective_rdg_range(target)
        if effective_range <= 0:
            return False

        dist2 = square_of_distance(self.x, self.y, target.x, target.y)
        collision = self.radius + target.radius

        min_range = self.rdg_minimal_range
        v = _vs_lookup(self.rdg_minimal_range_vs, target.type_name,
                       target.expanded_is_a)
        if v is not None:
            min_range += v
        else:
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.rdg_minimal_range_vs:
                min_range += self.rdg_minimal_range_vs[armor_name]
            else:
                armor = target._armor_instance
                if armor is not None:
                    for armor_type in armor.expanded_is_a:
                        if armor_type in self.rdg_minimal_range_vs:
                            min_range += self.rdg_minimal_range_vs[armor_type]
                            break
                    else:
                        for armor_type in armor.is_a:
                            if armor_type in self.rdg_minimal_range_vs:
                                min_range += self.rdg_minimal_range_vs[armor_type]
                                break

        return _range_check(dist2, effective_range, min_range, collision)


    # D-Phase 2: class-level defaults for can_attack_if_in_range hot path.
    # 替代每帧 getattr(self, '_can_attack_cache', None) + getattr(_bucket, -1).
    # 旧版本 4.3M calls/5min, 41M getattr 调用. 现 cache 走 LOAD_ATTR 直命中.
    _can_attack_cache = None
    _can_attack_cache_bucket = -1

    def can_attack_if_in_range(self, other):
        """检查是否可以攻击目标（假设目标在攻击范围内）.

        D-Phase 2 §3.4: 整个函数走 ``combat_fast.can_attack_if_in_range``
        (cpdef). 4.3M calls / 5min cw1, Python 版 21.8 s tottime. 内含 200ms
        bucketed cache + damage_vs (已 §3.2 cython) + basic system 兼容性.
        Fallback 是 Python 等价实现 (见 _py_can_attack_if_in_range).
        """
        if _cf is not None:
            return _cf.can_attack_if_in_range(self, other)
        return self._py_can_attack_if_in_range(other)

    def _py_can_attack_if_in_range(self, other):
        """Python fallback for can_attack_if_in_range.

        D-Phase 2 重构: 移除 hot-path 上所有 getattr/hasattr.
        - `_can_attack_cache` / `_can_attack_cache_bucket`: 类级 default,
          直接 LOAD_ATTR.
        - `other.id` / `other.place` / `other.hp`: Entity class-level
          defaults (id=None, place=None, hp=0).
        - `other.is_vulnerable` / `other.airground_type`: Entity defaults.
        - `other.is_a_building` / `other.is_a_unit` / `other.type_name`:
          D-Phase 2 在 Entity 加 class default (False/False/None).
        - `self.minimal_damage` / `self.mdg` / `self.rdg` / `self.mdg_explode`
          / `self.rdg_explode` / `self.mdg_targets` / `self.rdg_targets`
          / `self.mdg_projectile` / `self.rdg_projectile` / `self.weapons`:
          Creature/Entity class-level defaults 全部存在.
        - `self.world`: 在 Entity.__init__ 设置, hot path 上必存在.
        """
        # 200ms 级别结果缓存（同窗口同目标复用）
        current_time = self.world.time
        time_bucket = current_time // 200
        cache_dict = self._can_attack_cache
        if cache_dict is None or self._can_attack_cache_bucket != time_bucket:
            cache_dict = {}
            self._can_attack_cache = cache_dict
            self._can_attack_cache_bucket = time_bucket

        # other 可能为 None (调用方语义保留)
        if other is None:
            return False
        other_id = other.id
        cached = cache_dict.get(other_id)
        if cached is not None:
            return cached

        # 廉价校验
        if other.place is None or other.hp < 0:
            cache_dict[other_id] = False
            return False
        if other not in self.player.perception:
            cache_dict[other_id] = False
            return False

        # 对目标的伤害值
        melee_damage = self._get_melee_damage_vs(other)
        ranged_damage = self._get_ranged_damage_vs(other)
        minimal_damage = self.minimal_damage

        has_attack = (melee_damage > 0 or ranged_damage > 0 or minimal_damage > 0)
        if not has_attack:
            if self.mdg_explode or self.rdg_explode:
                has_attack = True
            else:
                cache_dict[other_id] = False
                return False

        # 目标地面/空中
        target_type = ground_or_air(other.airground_type)

        # 武器/目标兼容性
        can_attack_target = False
        weapons = self.weapons
        weapon_instances = getattr(self, '_weapon_instances', None)
        if weapons and weapon_instances:
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
                    can_attack_target = self._check_weapon_target_compatibility(weapon, other, target_type)
        else:
            # 回退基础系统
            mdg = self.mdg
            rdg = self.rdg
            mdg_explode = self.mdg_explode
            rdg_explode = self.rdg_explode
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

        # 目标可被攻击 (注意此分支不写 cache, 保留原行为)
        if not other.is_vulnerable:
            return False

        # 低地攻击高地限制 (self.place/other.place 在 hot path 上必非 None,
        # 但仍保留 None 安全检查作为防御性回退)
        self_place = self.place
        other_place = other.place
        attacker_high = (
            self_place.high_ground_at(self.x, self.y)
            if self_place is not None and hasattr(self_place, "high_ground_at")
            else getattr(self_place, "high_ground", False)
        )
        target_high = (
            other_place.high_ground_at(other.x, other.y)
            if other_place is not None and hasattr(other_place, "high_ground_at")
            else getattr(other_place, "high_ground", False)
        )
        if (self_place is not None and other_place is not None
                and not attacker_high and target_high
                and other.airground_type == "ground"
                and self.mdg_projectile != 1 and self.rdg_projectile != 1):
            cache_dict[other_id] = False
            return False

        cache_dict[other_id] = True
        return True

    def _check_weapon_target_compatibility(self, weapon, target, target_type):
        """检查武器是否能攻击指定类型的目标
        
        Args:
            weapon: 武器实例
            target: 目标单位
            target_type: 目标的地面/空中类型 ("ground" 或 "air")
            
        Returns:
            bool: 武器是否能攻击该类型的目标
        """
        # 检查近战攻击目标兼容性
        weapon_mdg = getattr(weapon, 'mdg', 0)
        if weapon_mdg > 0:
            weapon_mdg_targets = getattr(weapon, 'mdg_targets', ['ground'])
            if matches_attack_targets(target, weapon_mdg_targets, target_type):
                return True
        
        # 检查远程攻击目标兼容性
        weapon_rdg = getattr(weapon, 'rdg', 0)
        if weapon_rdg > 0:
            weapon_rdg_targets = getattr(weapon, 'rdg_targets', ['ground'])
            if matches_attack_targets(target, weapon_rdg_targets, target_type):
                return True
        
        return False

    def counterattack(self, place):
        """在反击开启时才执行反击"""
        # 检查反击开关状态
        if not hasattr(self, 'counterattack_enabled') or not self.counterattack_enabled:
            return

        # 整合旧版本的所有条件检查
        if not (self.speed
                and self.menace
                and self.ai_mode == "offensive"
                and not self.orders
                and self.action.__class__ != AttackAction
                and self._can_go(place)):  # 使用 _can_go 而不是 can_go
            return

        # 执行反击移动
        self.take_order(["go", place.id])
        self.take_order(
            ["go", f"zoom-{self.place.id}-{self.x}-{self.y}"],
            forget_previous=False
        )