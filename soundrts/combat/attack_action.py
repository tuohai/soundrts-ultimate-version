from ..worldaction import Action, AttackAction, MoveAction, MoveXYAction
from ..lib.nofloat import int_distance as _int_distance, square_of_distance as _square_of_distance
import random

class AttackActionMixin:
    """
    处理攻击动作和序列相关的功能
    """
    def _trigger_attack_start_skill(self, target, skill_name, is_melee):
        if target is None or getattr(self, "_triggering_skill", False):
            return False
        skill_cls = self.world.unit_class(skill_name)
        if skill_cls is None or not getattr(skill_cls, "effect", None):
            return False
        typed_rate = getattr(skill_cls, "mdg_trigger_rate" if is_melee else "rdg_trigger_rate", 0)
        rate = typed_rate if typed_rate > 0 else getattr(skill_cls, "active_trigger_rate", 100)
        if rate <= 0:
            return False
        if rate < 100 and self.world.random.randint(1, 100) > rate:
            return False
        if getattr(skill_cls, "mana_cost", 0) and getattr(self, "mana", 0) < skill_cls.mana_cost:
            return False
        if hasattr(self, "has_cooldown") and self.has_cooldown(skill_cls):
            return False
        skill_target = self if getattr(skill_cls, "effect_target", ()) == ["self"] else target

        def finish_skill():
            if target is None or getattr(target, "player", None) is None or getattr(target, "hp", 0) <= 0:
                return False
            if getattr(self, "player", None) is None or getattr(self, "hp", 0) <= 0:
                return False
            if getattr(skill_cls, "mana_cost", 0) and getattr(self, "mana", 0) < skill_cls.mana_cost:
                return False
            if hasattr(self, "has_cooldown") and self.has_cooldown(skill_cls):
                return False
            try:
                self._triggering_skill = True
                success = bool(skill_cls.execute_skill(self, skill_target, self.world))
            finally:
                self._triggering_skill = False
            if not success:
                return False
            if getattr(skill_cls, "mana_cost", 0):
                self.mana -= skill_cls.mana_cost
            if hasattr(self, "add_cooldown"):
                self.add_cooldown(skill_cls)
            self.notify(f"skill_triggered,{skill_name},{getattr(target, 'id', None)}")
            return True

        ready = getattr(skill_cls, "ready", 0) or 0
        if isinstance(ready, list):
            ready = ready[0] if ready else 0
        try:
            ready = int(ready)
        except (TypeError, ValueError):
            ready = 0
        if ready > 0:
            self.notify(f"skill_ready,{skill_name}")
            self.world.schedule_after(ready, finish_skill)
            return True
        if not finish_skill():
            return False
        return True

    def _trigger_attack_start_skills(self, target, is_melee, replace=False):
        if replace:
            if hasattr(self, "iter_attack_replace_skill_names"):
                names = self.iter_attack_replace_skill_names()
            else:
                names = getattr(self, "attack_replace_skills", ()) or ()
        elif hasattr(self, "iter_attack_trigger_skill_names"):
            names = self.iter_attack_trigger_skill_names()
        else:
            names = getattr(self, "attack_trigger_skills", ()) or ()
        triggered = False
        for skill_name in names:
            if self._trigger_attack_start_skill(target, skill_name, is_melee):
                triggered = True
        return triggered

    def _trigger_attack_start_buff(self, target, buff_name, is_melee, apply_to_target=False):
        if target is None:
            return False
        buff_cls = self.world.unit_class(buff_name)
        if buff_cls is None:
            return False
        rate = getattr(buff_cls, "mdg_trigger_rate" if is_melee else "rdg_trigger_rate", 0)
        if rate <= 0:
            rate = 100
        if rate < 100 and self.world.random.randint(1, 100) > rate:
            return False
        if apply_to_target:
            target.add_buff(buff_name, self)
            self.notify(f"buff_applied,{buff_name},{getattr(target, 'id', None)}")
        else:
            self.add_buff(buff_name, self)
            self.notify(f"buff_triggered,{buff_name},{self.id}")
        return True

    def _trigger_attack_start_buffs(self, target, is_melee, replace=False):
        buff_attr = "attack_replace_buffs" if replace else "attack_trigger_buffs"
        debuff_attr = "attack_replace_debuffs" if replace else "attack_trigger_debuffs"
        triggered = False
        for buff_name in getattr(self, buff_attr, ()) or ():
            if self._trigger_attack_start_buff(target, buff_name, is_melee, apply_to_target=False):
                triggered = True
        for buff_name in getattr(self, debuff_attr, ()) or ():
            if self._trigger_attack_start_buff(target, buff_name, is_melee, apply_to_target=True):
                triggered = True
        return triggered

    
    def _choose_best_weapon_for_target(self, target):
        """根据目标距离和武器属性选择最佳武器
        
        Args:
            target: 攻击目标
            
        Returns:
            str: 最佳武器名称，如果没有合适的武器则返回None
        """
        # 如果单位没有武器系统，直接返回
        if not hasattr(self, 'weapons') or not self.weapons:
            return None
        
        # 如果只有一个武器，直接返回
        if len(self.weapons) == 1:
            return self.weapons[0]
        
        # 计算到目标的距离，用于后续的武器选择
        distance = self._int_distance(self.x, self.y, target.x, target.y)
        collision = self.radius + target.radius
        
        # 检查当前武器是否仍然是最适合的选择
        current_weapon_suitable = False
        if (self.current_weapon and 
            self.current_weapon in self._weapon_instances and
            self._can_weapon_attack_target(self._weapon_instances[self.current_weapon], target)):
            
            current_weapon = self._weapon_instances[self.current_weapon]
            
            # 检查当前武器是否在有效射程内且有伤害
            current_effective = False
            
            # 检查近战攻击
            if getattr(current_weapon, 'mdg', 0) > 0:
                mdg_range = getattr(current_weapon, 'mdg_range', 0) + collision
                mdg_min_range = getattr(current_weapon, 'mdg_minimal_range', 0) + collision
                if mdg_min_range <= distance <= mdg_range:
                    current_effective = True
            
            # 检查远程攻击
            if getattr(current_weapon, 'rdg', 0) > 0:
                rdg_range = getattr(current_weapon, 'rdg_range', 0) + collision  
                rdg_min_range = getattr(current_weapon, 'rdg_minimal_range', 0) + collision
                if rdg_min_range <= distance <= rdg_range:
                    current_effective = True
            
            # 如果当前武器有效，暂时标记为合适，但仍需要与其他武器比较
            current_weapon_suitable = current_effective
        
        # 首先找出所有能够攻击目标的武器
        available_weapons = []
        for weapon_name in self.weapons:
            if weapon_name not in self._weapon_instances:
                continue
                
            weapon = self._weapon_instances[weapon_name]
            if self._can_weapon_attack_target(weapon, target):
                available_weapons.append((weapon_name, weapon))
        
        # 如果没有武器能攻击目标，返回当前武器
        if not available_weapons:
            return self.current_weapon
        
        # 如果只有一个武器能攻击目标，直接返回
        if len(available_weapons) == 1:
            return available_weapons[0][0]
        
        # 基于实际射程的逻辑：近距离用短射程武器，远距离用长射程武器
        weapon_ranges = []
        
        # 计算每个武器的最大射程
        for weapon_name, weapon in available_weapons:
            max_range = 0
            
            # 检查mdg射程
            if getattr(weapon, 'mdg', 0) > 0:
                mdg_range = getattr(weapon, 'mdg_range', 0)
                max_range = max(max_range, mdg_range)
            
            # 检查rdg射程
            if getattr(weapon, 'rdg', 0) > 0:
                rdg_range = getattr(weapon, 'rdg_range', 0)
                max_range = max(max_range, rdg_range)
            
            weapon_ranges.append((weapon_name, weapon, max_range))
        
        # 按射程排序：短射程在前，长射程在后
        weapon_ranges.sort(key=lambda x: x[2])
        
        # 找到射程分界点（使用中位数或最短射程的1.5倍作为阈值）
        if len(weapon_ranges) >= 2:
            shortest_range = weapon_ranges[0][2]
            longest_range = weapon_ranges[-1][2]
            # 使用较短射程的武器射程作为切换阈值
            range_threshold = shortest_range + (shortest_range * 0.5)  # 最短射程的1.5倍
        else:
            range_threshold = weapon_ranges[0][2] if weapon_ranges else 1500
        
        # 根据当前距离选择合适的武器
        if distance <= range_threshold:
            # 近距离：选择射程最短的武器（适合近战）
            return weapon_ranges[0][0]
        else:
            # 远距离：选择射程最长的武器（适合远战）
            return weapon_ranges[-1][0]

    def _evaluate_weapon_for_target(self, weapon, weapon_name, target, distance):
        """评估武器对特定目标的适用性分数
        
        Args:
            weapon: 武器实例
            weapon_name: 武器名称
            target: 攻击目标
            distance: 到目标的距离
            
        Returns:
            int: 适用性分数，分数越高越适合
        """
        score = 0
        
        # 获取武器的近战和远程属性
        weapon_mdg = getattr(weapon, 'mdg', 0)
        weapon_rdg = getattr(weapon, 'rdg', 0)
        weapon_mdg_range = getattr(weapon, 'mdg_range', 0)
        weapon_rdg_range = getattr(weapon, 'rdg_range', 0)
        weapon_mdg_min_range = getattr(weapon, 'mdg_minimal_range', 0)
        weapon_rdg_min_range = getattr(weapon, 'rdg_minimal_range', 0)
        
        # 计算碰撞距离
        collision = self.radius + target.radius
        
        # 获取武器切换策略
        strategy = getattr(self, 'weapon_switch_strategy', 'distance')
        
        # 评估近战攻击的适用性
        if weapon_mdg > 0:
            effective_mdg_range = weapon_mdg_range + collision
            effective_mdg_min_range = weapon_mdg_min_range + collision
            
            # 检查是否在近战攻击范围内
            if effective_mdg_min_range <= distance <= effective_mdg_range:
                melee_score = self._calculate_weapon_score(
                    weapon, weapon_name, target, distance, True, strategy
                )
                score = max(score, melee_score)
        
        # 评估远程攻击的适用性
        if weapon_rdg > 0:
            effective_rdg_range = weapon_rdg_range + collision
            effective_rdg_min_range = weapon_rdg_min_range + collision
            
            # 检查是否在远程攻击范围内
            if effective_rdg_min_range <= distance <= effective_rdg_range:
                ranged_score = self._calculate_weapon_score(
                    weapon, weapon_name, target, distance, False, strategy
                )
                score = max(score, ranged_score)
        
        # 应用武器优先级
        if hasattr(self, 'weapon_priority') and self.weapon_priority:
            if weapon_name in self.weapon_priority:
                priority_index = self.weapon_priority.index(weapon_name)
                # 优先级越高（索引越小），加分越多
                priority_bonus = (len(self.weapon_priority) - priority_index) * 100
                score += priority_bonus
        
        # 如果武器当前正在冷却，减少分数
        now = self.world.time
        if weapon_mdg > 0 and now < getattr(self, 'mdg_next_attack_time', 0):
            score *= 0.5
        if weapon_rdg > 0 and now < getattr(self, 'rdg_next_attack_time', 0):
            score *= 0.5
            
        return score
    
    def _calculate_weapon_score(self, weapon, weapon_name, target, distance, is_melee, strategy):
        """根据策略计算武器分数
        
        Args:
            weapon: 武器实例
            weapon_name: 武器名称
            target: 攻击目标
            distance: 到目标的距离
            is_melee: 是否为近战攻击
            strategy: 武器切换策略
            
        Returns:
            float: 武器分数
        """
        if is_melee:
            base_damage = getattr(weapon, 'mdg', 0)
            weapon_range = getattr(weapon, 'mdg_range', 0)
            weapon_min_range = getattr(weapon, 'mdg_minimal_range', 0)
            vs_damage_dict = getattr(weapon, 'mdg_vs', {})
        else:
            base_damage = getattr(weapon, 'rdg', 0)
            weapon_range = getattr(weapon, 'rdg_range', 0)
            weapon_min_range = getattr(weapon, 'rdg_minimal_range', 0)
            vs_damage_dict = getattr(weapon, 'rdg_vs', {})
        
        # 计算基础分数
        if strategy == "damage":
            # 伤害优先策略：主要基于伤害值
            score = base_damage
            
            # 检查是否有针对目标类型的特殊伤害
            if vs_damage_dict:
                if target.type_name in vs_damage_dict:
                    score += vs_damage_dict[target.type_name]
                elif hasattr(target, 'expanded_is_a'):
                    for t in target.expanded_is_a:
                        if t in vs_damage_dict:
                            score += vs_damage_dict[t]
                            break
            
            # 距离适应性调整（较小的影响）
            collision = self.radius + target.radius
            effective_range = weapon_range + collision
            effective_min_range = weapon_min_range + collision
            if effective_range > 0:
                distance_factor = 1.0 - abs(distance - (effective_min_range + effective_range) / 2) / effective_range
                score *= (0.8 + 0.2 * distance_factor)  # 距离因子影响较小
                
        elif strategy == "range":
            # 射程优先策略：主要基于射程适应性
            collision = self.radius + target.radius
            effective_range = weapon_range + collision
            effective_min_range = weapon_min_range + collision
            
            if effective_range > 0:
                # 基于距离适应性的分数
                optimal_distance = (effective_min_range + effective_range) / 2
                distance_factor = 1.0 - abs(distance - optimal_distance) / effective_range
                score = distance_factor * 1000  # 放大分数以便比较
                
                # 远程武器在较远距离时额外加分
                if not is_melee and distance > effective_range * 0.7:
                    score *= 1.3
                
                # 伤害值作为次要因素
                score += base_damage * 0.1
            else:
                score = base_damage * 0.1
                
        else:  # distance 策略（默认）
            # 距离优先策略：根据距离选择最合适的武器
            collision = self.radius + target.radius
            effective_range = weapon_range + collision
            effective_min_range = weapon_min_range + collision
            
            # 基础分数从伤害值开始
            score = base_damage
            
            if effective_range > 0:
                # 计算距离适应性分数
                if distance <= effective_min_range:
                    # 距离太近，给予较低分数
                    distance_factor = 0.3
                elif distance >= effective_range:
                    # 距离太远，给予较低分数
                    distance_factor = 0.3
                else:
                    # 在有效范围内，距离越接近最佳距离分数越高
                    range_span = effective_range - effective_min_range
                    if range_span > 0:
                        # 对于远程武器，较远距离更优
                        if not is_melee:
                            # 远程武器：距离越远越好（在有效范围内）
                            distance_factor = 0.5 + 0.5 * (distance - effective_min_range) / range_span
                        else:
                            # 近战武器：距离越近越好（在有效范围内）
                            distance_factor = 1.0 - 0.5 * (distance - effective_min_range) / range_span
                    else:
                        distance_factor = 1.0
                
                score *= distance_factor
                
                # 远程武器在较远距离时额外加分
                if not is_melee and distance > effective_range * 0.6:
                    score *= 1.5
                # 近战武器在较近距离时额外加分
                elif is_melee and distance < effective_range * 0.4:
                    score *= 1.3
            
            # 检查是否有针对目标类型的特殊伤害
            if vs_damage_dict:
                if target.type_name in vs_damage_dict:
                    score += vs_damage_dict[target.type_name]
                elif hasattr(target, 'expanded_is_a'):
                    for t in target.expanded_is_a:
                        if t in vs_damage_dict:
                            score += vs_damage_dict[t]
                            break
        
        return score
    
    def _should_auto_switch_weapon(self):
        """检查是否应该启用自动武器切换

        D-Phase 2: auto_weapon_switch 是 Creature class default (False),
        直接属性访问. 875902 calls / 5min.
        """
        return self.auto_weapon_switch

    def _can_charge_attack(self, target, is_melee=True):
        """
        判断是否可以使用冲锋攻击
        
        Args:
            target: 攻击目标
            is_melee: 是否为近战攻击
            
        Returns:
            bool: 是否可以使用冲锋攻击
        """
        now = self.world.time
        
        # 检查冷却时间
        if is_melee:
            if now < self.charge_mdg_next_time:
                return False
            charge_damage = self.charge_mdg
            charge_distance = self.charge_mdg_dist
        else:
            if now < self.charge_rdg_next_time:
                return False
            charge_damage = self.charge_rdg
            charge_distance = self.charge_rdg_dist
        
        # 检查是否有冲锋伤害
        if charge_damage <= 0:
            return False
            
        # 计算与目标的当前距离
        dist = self._int_distance(self.x, self.y, target.x, target.y)
        
        # 检查目标ID是否是上次冲锋的目标
        current_target_id = target.id
        
        # 获取上次冲锋的目标ID（如果存在）
        # 注意：我们需要为近战和远程分别保存相应的上次冲锋目标
        if is_melee:
            last_charge_target_id = getattr(self, 'last_charge_mdg_target_id', None)
            charge_ready_flag = getattr(self, 'charge_mdg_ready', True)
        else:
            last_charge_target_id = getattr(self, 'last_charge_rdg_target_id', None)
            charge_ready_flag = getattr(self, 'charge_rdg_ready', True)
        
        # 如果是同一目标，并且冲锋还未就绪
        if current_target_id == last_charge_target_id and not charge_ready_flag:
            # 检查是否已经拉开了足够的距离（超过冲锋有效距离）
            if dist > charge_distance:
                # 更新冲锋就绪状态，并交由后续距离/伤害校验决定本次是否可冲锋
                # （不再立即 return False，避免在边界场景下白白损失一帧）
                if is_melee:
                    self.charge_mdg_ready = True
                else:
                    self.charge_rdg_ready = True
                charge_ready_flag = True
            else:
                # 距离不够，不能冲锋
                return False

        # 检查是否在冲锋有效距离内（上限）
        if dist > charge_distance:
            return False

        # 检查是否高于冲锋最小触发距离（下限，0 表示不限）
        if is_melee:
            charge_min_distance = getattr(self, 'charge_mdg_min_dist', 0)
        else:
            charge_min_distance = getattr(self, 'charge_rdg_min_dist', 0)
        if charge_min_distance > 0 and dist < charge_min_distance:
            return False

        # 检查是否有针对此目标类型的冲锋伤害
        specific_charge_damage = 0
        if is_melee and target.type_name in self.charge_mdg_vs:
            specific_charge_damage = self.charge_mdg_vs[target.type_name]
        elif not is_melee and target.type_name in self.charge_rdg_vs:
            specific_charge_damage = self.charge_rdg_vs[target.type_name]
            
        # 如果有特定伤害且大于0，可以冲锋
        if specific_charge_damage > 0:
            return True
            
        return True
        
    def _get_charge_damage(self, target, is_melee=True):
        """计算对目标的冲锋伤害（加法公式 + 距离衰减）。

        公式::

            spec_dmg = (mdg + mdg_vs) + (charge_mdg + charge_mdg_vs)

        其中：
        - ``(mdg + mdg_vs)`` 来自 ``_get_melee_damage_vs(target)`` / ``_get_ranged_damage_vs(target)``
        - ``charge_mdg`` 现为加值而非倍率（内部均为 ×1000 精度存储）
        - 例：``mdg 6, charge_mdg 2 → 6000 + 2000 = 8000``（rules 视角 8）

        在 spec 公式之上再叠加距离衰减因子（保留历史平衡设计）::

            dist_factor = 0.5 + (dist / charge_dist) * 0.5  # 0.5 ~ 1.0
            final_dmg = spec_dmg * dist_factor

        距离越远，冲锋伤害越接近 100%；近距离冲锋衰减到 50%。

        Args:
            target: 攻击目标
            is_melee: 是否为近战冲锋
        """
        # 基础伤害（含 mdg_vs / rdg_vs 修正）
        if is_melee:
            base = self._get_melee_damage_vs(target)
            mult = self.charge_mdg + self._get_on_terrain_modifier(
                getattr(self, "charge_mdg_terrain", ())
            )
            vs_dict = self.charge_mdg_vs
            max_dist = self.charge_mdg_dist
        else:
            base = self._get_ranged_damage_vs(target)
            mult = self.charge_rdg + self._get_on_terrain_modifier(
                getattr(self, "charge_rdg_terrain", ())
            )
            vs_dict = self.charge_rdg_vs
            max_dist = self.charge_rdg_dist

        # 冲锋倍率 vs 修正（与 mdg_vs 一样采用"叠加"语义）
        vs_mult = vs_dict.get(target.type_name, 0)
        if vs_mult == 0:
            for t in target.expanded_is_a:
                if t in vs_dict:
                    vs_mult = vs_dict[t]
                    break

        total_mult = mult + vs_mult
        if total_mult <= 0 or base <= 0:
            return 0

        # 加法公式：冲锋伤害 = 自身 mdg/rdg 加值 + charge_mdg/charge_rdg 加值
        spec_damage = base + total_mult

        # 距离衰减因子：dist_factor ∈ [0.5, 1.0]，越远伤害越高
        if max_dist > 0:
            dist = self._int_distance(self.x, self.y, target.x, target.y)
            # 整数运算等价于 spec_damage * (0.5 + (dist/max_dist) * 0.5)
            # = spec_damage * (max_dist + dist) / (2 * max_dist)
            return spec_damage * (max_dist + dist) // (2 * max_dist)

        return spec_damage
        
    def _apply_charge_splash(self, target, is_melee):
        """应用冲锋攻击的溅射伤害
        
        Args:
            target: 攻击目标
            is_melee: 是否为近战冲锋
        """
        # 自伤场景：不触发任何冲锋溅射
        if target is self:
            return
        if target.place is None or target.place.objects is None:
            return
            
        # 获取冲锋溅射属性
        if is_melee:
            # 基础溅射伤害
            splash_damage = getattr(self, 'charge_mdg_splash', 0)
            if splash_damage <= 0:
                return
                
            # 基础溅射半径
            splash_range = getattr(self, 'charge_mdg_radius', 0)
            if splash_range <= 0:
                return
                
            # 检查是否有针对目标类型的近战冲锋溅射半径修正
            if hasattr(target, "type_name") and hasattr(self, 'charge_mdg_radius_vs') and target.type_name in self.charge_mdg_radius_vs:
                splash_range += self.charge_mdg_radius_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_mdg_radius_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_mdg_radius_vs:
                        splash_range += self.charge_mdg_radius_vs[t]
                        break
            
            # 检查是否有针对目标类型的近战冲锋溅射伤害修正
            if hasattr(target, "type_name") and hasattr(self, 'charge_mdg_splash_vs') and target.type_name in self.charge_mdg_splash_vs:
                splash_damage += self.charge_mdg_splash_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_mdg_splash_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_mdg_splash_vs:
                        splash_damage += self.charge_mdg_splash_vs[t]
                        break
                        
            # 获取衰减值
            splash_decay_min = getattr(self, 'charge_mdg_splash_decay_min', 0.5)
            if hasattr(target, "type_name") and hasattr(self, 'charge_mdg_splash_decay_min_vs') and target.type_name in self.charge_mdg_splash_decay_min_vs:
                splash_decay_min += self.charge_mdg_splash_decay_min_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_mdg_splash_decay_min_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_mdg_splash_decay_min_vs:
                        splash_decay_min += self.charge_mdg_splash_decay_min_vs[t]
                        break
        else:
            # 基础溅射伤害
            splash_damage = getattr(self, 'charge_rdg_splash', 0)
            if splash_damage <= 0:
                return
                
            # 基础溅射半径
            splash_range = getattr(self, 'charge_rdg_radius', 0)
            if splash_range <= 0:
                return
                
            # 检查是否有针对目标类型的远程冲锋溅射半径修正
            if hasattr(target, "type_name") and hasattr(self, 'charge_rdg_radius_vs') and target.type_name in self.charge_rdg_radius_vs:
                splash_range += self.charge_rdg_radius_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_rdg_radius_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_rdg_radius_vs:
                        splash_range += self.charge_rdg_radius_vs[t]
                        break
            
            # 检查是否有针对目标类型的远程冲锋溅射伤害修正
            if hasattr(target, "type_name") and hasattr(self, 'charge_rdg_splash_vs') and target.type_name in self.charge_rdg_splash_vs:
                splash_damage += self.charge_rdg_splash_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_rdg_splash_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_rdg_splash_vs:
                        splash_damage += self.charge_rdg_splash_vs[t]
                        break
                        
            # 获取衰减值
            splash_decay_min = getattr(self, 'charge_rdg_splash_decay_min', 0.5)
            if hasattr(target, "type_name") and hasattr(self, 'charge_rdg_splash_decay_min_vs') and target.type_name in self.charge_rdg_splash_decay_min_vs:
                splash_decay_min += self.charge_rdg_splash_decay_min_vs[target.type_name]
            elif hasattr(target, 'expanded_is_a') and hasattr(self, 'charge_rdg_splash_decay_min_vs'):
                # 检查继承类型
                for t in target.expanded_is_a:
                    if t in self.charge_rdg_splash_decay_min_vs:
                        splash_decay_min += self.charge_rdg_splash_decay_min_vs[t]
                        break
        
        # 如果没有有效的溅射半径或伤害，直接返回
        if splash_range <= 0 or splash_damage <= 0:
            return
        
        # 将溅射半径转换为距离平方，用于后续计算
        radius2 = splash_range * splash_range
        
        # 收集范围内目标并计算距离系数
        victims_with_factors = []
        import random
        import math
        
        # 防御性检查：确保 Square 对象有 objects 属性
        if not hasattr(target.place, 'objects') or target.place.objects is None:
            target.place.objects = []
        
        for obj in target.place.objects[:]:
            if obj is self or obj is target:
                continue
                
            # 只对敌方生物单位造成伤害
            from ..worldunit import Creature
            if not self.is_an_enemy(obj) or not isinstance(obj, Creature):
                continue
            
            # 主目标为地面单位时，溅射不影响空中单位
            if getattr(target, 'airground_type', 'ground') == 'ground' and getattr(obj, 'airground_type', 'ground') == 'air':
                continue
                
            # 计算与冲锋目标的距离
            dist2 = self._square_of_distance(target.x, target.y, obj.x, obj.y)
            if dist2 <= radius2:
                # 确保衰减值是浮点数
                decay_min_value = float(splash_decay_min)
                decay_range = 1.0 - decay_min_value
                # 计算距离系数：距离越近，伤害越高
                dist_factor = 1.0 - (math.sqrt(dist2) / splash_range * decay_range)
                victims_with_factors.append((obj, dist_factor))
        
        # 如果没有受影响的目标，直接返回
        if not victims_with_factors:
            return
            
        # 为每个目标生成随机权重，考虑距离因素
        n = len(victims_with_factors)
        rands = []
        for _, factor in victims_with_factors:
            # 距离越近，随机范围越大
            rand_max = 0.5 + (factor * 0.5)  # 0.5 ~ 1.0
            rands.append(self.world.random.random() * rand_max)
            
        sumRand = sum(rands)
        
        # 发送冲锋溅射通知
        self.notify(f"charge_splash,{self.type_name},{self.id}")
        
        if sumRand == 0:
            # 平均分配伤害，但考虑距离衰减
            for (victim, factor), _ in zip(victims_with_factors, rands):
                damage = int(round(splash_damage * factor / n))
                if damage > 0:
                    victim.receive_hit(damage, self, notify=False)
                    victim.notify("charge_splash_hit")
        else:
            # 随机分配伤害，但受距离影响
            distributedSum = 0
            for (victim, factor), rand in zip(victims_with_factors, rands):
                portion = int(round(rand / sumRand * splash_damage * factor))
                distributedSum += portion
                if portion > 0:
                    victim.receive_hit(portion, self, notify=False)
                    victim.notify("charge_splash_hit")
                    
            # 处理剩余伤害
            leftover = splash_damage - distributedSum
            if leftover > 0:
                # 优先补给最近的目标
                closest_victim = max(victims_with_factors, key=lambda x: x[1])[0]
                closest_victim.receive_hit(leftover, self, notify=True)
                
    def _square_of_distance(self, x1, y1, x2, y2):
        """计算两点间距离的平方（委托给 nofloat 的 Cython 加速版本）"""
        return _square_of_distance(x1, y1, x2, y2)
        
    def _set_charge_cooldown(self, is_melee):
        """设置冲锋攻击冷却
        
        Args:
            is_melee: 是否为近战冲锋
        """
        now = self.world.time
        if is_melee:
            cd = self.charge_mdg_cd + self._get_on_terrain_modifier(
                getattr(self, "charge_mdg_cd_on_terrain", ())
            )
            self.charge_mdg_next_time = now + max(0, cd)
            # 标记冲锋不可用，直到拉开足够距离
            self.charge_mdg_ready = False
        else:
            cd = self.charge_rdg_cd + self._get_on_terrain_modifier(
                getattr(self, "charge_rdg_cd_on_terrain", ())
            )
            self.charge_rdg_next_time = now + max(0, cd)
            # 标记冲锋不可用，直到拉开足够距离
            self.charge_rdg_ready = False
    
    def _get_melee_cd_on_terrain(self) -> int:
        return self._get_on_terrain_modifier(getattr(self, "mdg_cd_on_terrain", ()))

    def _get_ranged_cd_on_terrain(self) -> int:
        return self._get_on_terrain_modifier(getattr(self, "rdg_cd_on_terrain", ()))

    def _get_melee_cd_base(self) -> int:
        return max(0, self.mdg_cd + self._get_melee_cd_on_terrain())

    def _get_ranged_cd_base(self) -> int:
        return max(0, self.rdg_cd + self._get_ranged_cd_on_terrain())

    def _apply_melee_cd_on_terrain(self, cd: int) -> int:
        return max(0, cd + self._get_melee_cd_on_terrain())

    def _apply_ranged_cd_on_terrain(self, cd: int) -> int:
        return max(0, cd + self._get_ranged_cd_on_terrain())
    
    def _set_attack_cooldown(self, is_melee, target=None):
        """设置攻击冷却时间

        Args:
            is_melee: 是否为近战攻击
            target: 攻击目标,可选
        """
        now = self.world.time
        if is_melee:
            cd = self._get_melee_cd_vs(target) if target else self._get_melee_cd_base()
            self.mdg_next_attack_time = now + cd
        else:
            cd = self._get_ranged_cd_vs(target) if target else self._get_ranged_cd_base()
            self.rdg_next_attack_time = now + cd

    def aim(self, target):
        """瞄准目标并尝试攻击"""
        # 检查目标是否有效
        if target is None or target.player is None or target.hp <= 0:
            return

        # 检查是否可以从载具内攻击
        if not self._can_attack_from_inside():
            # 不发送攻击通知，直接返回
            return

        # 检查是否允许攻击载具内部目标（直接瞄准乘客时）
        if getattr(target, 'is_inside', False):
            if not self._can_attack_inside_passenger(target):
                return

        # 在每次瞄准时检查并切换到最合适的武器
        if (self._should_auto_switch_weapon() and 
            hasattr(self, 'weapons') and len(self.weapons) > 1 and
            not self._should_respect_manual_weapon_choice()):
            best_weapon = self._choose_best_weapon_for_target(target)
            if best_weapon and best_weapon != self.current_weapon:
                # 自动切换到最佳武器（播放音效但不播报武器名）
                if hasattr(self, '_auto_switch_weapon'):
                    self._auto_switch_weapon(best_weapon)
                elif hasattr(self, '_equip_weapon_silently'):
                    self._equip_weapon_silently(best_weapon)



        # 获取当前时间
        now = self.world.time

        # 获取对目标的近战和远程伤害值
        melee_damage = self._get_melee_damage_vs(target)
        ranged_damage = self._get_ranged_damage_vs(target)

        # 修复：攻击类型判断应该只依赖于该类型的伤害值，不应该被minimal_damage影响
        # minimal_damage只在实际伤害计算时作为最小伤害保证使用
        can_mdg = (melee_damage > 0 or getattr(self, 'mdg_explode', False)) and self.can_attack(target)
        can_rdg = (ranged_damage > 0 or getattr(self, 'rdg_explode', False)) and self.can_attack(target)
        
        # 1.4.0.1 spec：冲锋伤害 = mdg × charge_mdg，因此发动冲锋本质上要求 can_mdg。
        # 若 mdg=0 即使 charge_mdg>0 冲锋伤害也为 0，无意义。
        # 检查是否可以使用近战冲锋攻击（自伤时跳过冲锋；普攻 CD 未过则不发动冲锋，
        # 但不再 return，允许下面的远程冲锋/普攻分支继续尝试）
        if (can_mdg and target is not self
                and now >= self.mdg_next_attack_time
                and self._can_charge_attack(target, is_melee=True)):

            # 计算冲锋伤害
            charge_damage = self._get_charge_damage(target, is_melee=True)
            
            # 发送冲锋攻击通知
            self.notify(f"launch_charge_mdg,{self.type_name},{self.id}")
            
            # 检查冲锋攻击是否会触发自身buff
            for buff_name in self.debuffs:
                # 获取buff类
                buff_cls = self.world.unit_class(buff_name)
                if buff_cls is None:
                    continue
                
                # 使用冲锋攻击触发方式检查是否触发buff
                if hasattr(buff_cls, 'should_trigger_on_charge') and buff_cls.should_trigger_on_charge(self, is_melee=True):
                    # 应用buff效果给自己
                    self.add_buff(buff_name, self)
                    # 添加buff触发通知
                    self.notify(f"buff_triggered,{buff_name},{self.id}")
            
            # 重置冲锋失败标记
            self._charge_failed = False
            
            # 添加冲锋失败事件监听
            def on_charge_failed():
                self._charge_failed = True
            
            # 临时添加通知监听
            old_notify = self.notify
            
            def charge_notify(msg):
                if msg == "charge_failed":
                    on_charge_failed()
                return old_notify(msg)
            
            # 替换通知方法
            self.notify = charge_notify
            
            # 立即应用伤害（显式标记为近战冲锋，避免 receive_hit 内部基于距离误判）
            damage_target = self._resolve_damage_target(target)
            if damage_target is not None:
                damage_target.receive_hit(charge_damage, self, notify=True, is_charge=True, is_melee=True)
            
            # 恢复原始通知方法
            self.notify = old_notify
            
            # 只有在冲锋未被打断时才发送成功通知和应用溅射伤害
            if not getattr(self, '_charge_failed', False):
                self.notify("charge_success")
                # 应用冲锋溅射伤害
                self._apply_charge_splash(target, is_melee=True)
            
            # 保存当前冲锋目标的ID
            self.last_charge_mdg_target_id = target.id
            
            # 设置冲锋冷却和普通攻击冷却
            self._set_charge_cooldown(is_melee=True)
            self._set_attack_cooldown(is_melee=True, target=target)
            return
            
        # 1.4.0.1 spec：远程冲锋同理需要 rdg>0 作为基数
        # 检查是否可以使用远程冲锋攻击（自伤时跳过冲锋；普攻 CD 未过则不发动冲锋，
        # 但不再 return，允许下面的普攻分支继续尝试）
        if (can_rdg and target is not self
                and now >= self.rdg_next_attack_time
                and self._can_charge_attack(target, is_melee=False)):

            # 计算冲锋伤害
            charge_damage = self._get_charge_damage(target, is_melee=False)
            
            # 发送冲锋攻击通知
            self.notify(f"launch_charge_rdg,{self.type_name},{self.id}")
            
            # 检查冲锋攻击是否会触发自身buff
            for buff_name in self.debuffs:
                # 获取buff类
                buff_cls = self.world.unit_class(buff_name)
                if buff_cls is None:
                    continue
                
                # 使用冲锋攻击触发方式检查是否触发buff
                if hasattr(buff_cls, 'should_trigger_on_charge') and buff_cls.should_trigger_on_charge(self, is_melee=False):
                    # 应用buff效果给自己
                    self.add_buff(buff_name, self)
                    # 添加buff触发通知
                    self.notify(f"buff_triggered,{buff_name},{self.id}")
            
            # 重置冲锋失败标记
            self._charge_failed = False
            
            # 添加冲锋失败事件监听
            def on_charge_failed():
                self._charge_failed = True
            
            # 临时添加通知监听
            old_notify = self.notify
            
            def charge_notify(msg):
                if msg == "charge_failed":
                    on_charge_failed()
                return old_notify(msg)
            
            # 替换通知方法
            self.notify = charge_notify
            
            # 立即应用伤害（显式标记为远程冲锋）
            target.receive_hit(charge_damage, self, notify=True, is_charge=True, is_melee=False)
            
            # 恢复原始通知方法
            self.notify = old_notify
            
            # 只有在冲锋未被打断时才发送成功通知和应用溅射伤害
            if not getattr(self, '_charge_failed', False):
                self.notify("charge_success")
                # 应用冲锋溅射伤害
                self._apply_charge_splash(target, is_melee=False)
            
            # 保存当前冲锋目标的ID
            self.last_charge_rdg_target_id = target.id
            
            # 设置冲锋冷却和普通攻击冷却
            self._set_charge_cooldown(is_melee=False)
            self._set_attack_cooldown(is_melee=False, target=target)
            return

        # 优先尝试远程普通攻击
        if can_rdg:
            # 如果还在冷却，直接返回
            if now < self.rdg_next_attack_time:
                return

            # 检查前摇
            if self.rdg_prep_end_time <= 0:  # 如果没有前摇时间，设置新的前摇
                ready = self._get_range_ready_vs(target)
                self.rdg_prep_end_time = now + ready
                if ready > 0:
                    self.notify("rdg_ready")
                return
            elif now < self.rdg_prep_end_time:  # 如果前摇未结束
                return

            # 前摇结束后发起攻击（连发音效由 _schedule_ballistic_hit 按序列播放）
            self._trigger_attack_start_buffs(target, is_melee=False, replace=False)
            self._trigger_attack_start_skills(target, is_melee=False, replace=False)
            replace_triggered = self._trigger_attack_start_buffs(target, is_melee=False, replace=True)
            replace_triggered = self._trigger_attack_start_skills(target, is_melee=False, replace=True) or replace_triggered
            if replace_triggered:
                self.rdg_next_attack_time = now + self._get_ranged_cd_vs(target)
                self.rdg_prep_end_time = 0
                return
            damage_delay = self._calc_rdg_delay(target)
            self._schedule_ballistic_hit(target, damage_delay, is_melee=False)

            # 设置冷却时间并重置前摇时间
            self.rdg_next_attack_time = now + self._get_ranged_cd_vs(target)
            self.rdg_prep_end_time = 0

        # 近战攻击逻辑类似
        if can_mdg:
            if now < self.mdg_next_attack_time:
                return

            if self.mdg_prep_end_time <= 0:
                ready = self._get_melee_ready_vs(target)
                self.mdg_prep_end_time = now + ready
                if ready > 0:
                    self.notify("mdg_ready")
                return
            elif now < self.mdg_prep_end_time:
                return

            self._trigger_attack_start_buffs(target, is_melee=True, replace=False)
            self._trigger_attack_start_skills(target, is_melee=True, replace=False)
            replace_triggered = self._trigger_attack_start_buffs(target, is_melee=True, replace=True)
            replace_triggered = self._trigger_attack_start_skills(target, is_melee=True, replace=True) or replace_triggered
            if replace_triggered:
                self.mdg_next_attack_time = now + self._get_melee_cd_vs(target)
                self.mdg_prep_end_time = 0
                return
            damage_delay = self._calc_mdg_delay(target)
            self._schedule_ballistic_hit(target, damage_delay, is_melee=True)

            self.mdg_next_attack_time = now + self._get_melee_cd_vs(target)
            self.mdg_prep_end_time = 0
            
    def _calc_mdg_delay(self, target) -> int:
        dist_in_grids = self._int_distance(self.x, self.y, target.x, target.y) / 1000
        if dist_in_grids <= 0:
            return 0

        # 计算基础延迟
        base_delay = dist_in_grids * self.mdg_delay

        return int(round(base_delay))

    def _calc_rdg_delay(self, target) -> int:
        # 计算基础距离(转换为实际格子数)
        dist_in_grids = self._int_distance(self.x, self.y, target.x, target.y) / 1000
        if dist_in_grids <= 0:
            return 0

        # 计算基础延迟
        base_delay = dist_in_grids * self.rdg_delay

        return int(round(base_delay))
        
    def _int_distance(self, x1, y1, x2, y2):
        """计算两点之间的距离（委托给模块级 Cython 加速函数）"""
        return _int_distance(x1, y1, x2, y2)
        
    def _get_melee_cd_vs(self, target) -> int:
        """返回对目标的近战冷却时间

        Args:
            target: 目标单位

        Returns:
            int: 冷却时间
        """
        # 先检查直接对单位类型的vs
        cd_vs = self.mdg_cd_vs.get(target.type_name, None)
        if cd_vs is not None:
            return self._apply_melee_cd_on_terrain(self.mdg_cd + cd_vs)

        # 检查对单位继承类型的vs
        for t in target.expanded_is_a:
            if t in self.mdg_cd_vs:
                return self._apply_melee_cd_on_terrain(self.mdg_cd + self.mdg_cd_vs[t])
        
        # 检查对目标护甲类型的vs
        if hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.mdg_cd_vs:
                return self._apply_melee_cd_on_terrain(self.mdg_cd + self.mdg_cd_vs[armor_name])
        
        # 检查对目标护甲继承类型的vs
        if hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.mdg_cd_vs:
                        return self._apply_melee_cd_on_terrain(self.mdg_cd + self.mdg_cd_vs[armor_type])
            # 也检查护甲的直接is_a
            if hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.mdg_cd_vs:
                        return self._apply_melee_cd_on_terrain(self.mdg_cd + self.mdg_cd_vs[armor_type])

        # 否则用基础冷却时间
        return self._get_melee_cd_base()

    def _get_ranged_cd_vs(self, target) -> int:
        """返回对目标的远程冷却时间

        Args:
            target: 目标单位

        Returns:
            int: 冷却时间
        """
        # 先检查直接对单位类型的vs
        cd_vs = self.rdg_cd_vs.get(target.type_name, None)
        if cd_vs is not None:
            return self._apply_ranged_cd_on_terrain(self.rdg_cd + cd_vs)

        # 检查对单位继承类型的vs
        for t in target.expanded_is_a:
            if t in self.rdg_cd_vs:
                return self._apply_ranged_cd_on_terrain(self.rdg_cd + self.rdg_cd_vs[t])
        
        # 检查对目标护甲类型的vs
        if hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.rdg_cd_vs:
                return self._apply_ranged_cd_on_terrain(self.rdg_cd + self.rdg_cd_vs[armor_name])
        
        # 检查对目标护甲继承类型的vs
        if hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.rdg_cd_vs:
                        return self._apply_ranged_cd_on_terrain(self.rdg_cd + self.rdg_cd_vs[armor_type])
            # 也检查护甲的直接is_a
            if hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.rdg_cd_vs:
                        return self._apply_ranged_cd_on_terrain(self.rdg_cd + self.rdg_cd_vs[armor_type])

        # 否则用基础冷却时间
        return self._get_ranged_cd_base()

    def _get_melee_ready_vs(self, target) -> int:
        """返回对目标的近战前摇（攻击预备时间）"""
        # 先检查直接对单位类型的vs
        ready_vs = self.mdg_ready_vs.get(target.type_name, None)
        if ready_vs is not None:
            return self.mdg_ready + ready_vs
        
        # 检查对单位继承类型的vs
        for t in target.expanded_is_a:
            if t in self.mdg_ready_vs:
                return self.mdg_ready + self.mdg_ready_vs[t]
        
        # 检查对目标护甲类型的vs
        if hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.mdg_ready_vs:
                return self.mdg_ready + self.mdg_ready_vs[armor_name]
        
        # 检查对目标护甲继承类型的vs
        if hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.mdg_ready_vs:
                        return self.mdg_ready + self.mdg_ready_vs[armor_type]
            # 也检查护甲的直接is_a
            if hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.mdg_ready_vs:
                        return self.mdg_ready + self.mdg_ready_vs[armor_type]
        
        return self.mdg_ready

    def _get_range_ready_vs(self, target) -> int:
        """返回对目标的远程前摇（攻击预备时间）"""
        # 先检查直接对单位类型的vs
        ready_vs = self.rdg_ready_vs.get(target.type_name, None)
        if ready_vs is not None:
            return self.rdg_ready + ready_vs
        
        # 检查对单位继承类型的vs
        for t in target.expanded_is_a:
            if t in self.rdg_ready_vs:
                return self.rdg_ready + self.rdg_ready_vs[t]
        
        # 检查对目标护甲类型的vs
        if hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.rdg_ready_vs:
                return self.rdg_ready + self.rdg_ready_vs[armor_name]
        
        # 检查对目标护甲继承类型的vs
        if hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.rdg_ready_vs:
                        return self.rdg_ready + self.rdg_ready_vs[armor_type]
            # 也检查护甲的直接is_a
            if hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.rdg_ready_vs:
                        return self.rdg_ready + self.rdg_ready_vs[armor_type]
        
        return self.rdg_ready
        
    def engage_combat(self, target):
        # 示例：可在此处做对战时的额外处理
        pass
        
    def _perform_capture(self, target):
        """直接占领可被夺取的敌方建筑（夺取阈值 100，接触即占领），不进行攻击。

        与攻击触发的夺取效果一致：直接转变阵营并播放占领/被占领音效，
        但全程不造成伤害、不播放攻击动作/音效。
        """
        if getattr(self, "_has_yielded", False):
            return
        if target is None or target.player is None or target.hp <= 0:
            return
        old_player = target.player
        target.set_player(self.player)
        # 被占领方（人类玩家）播放被占领音效
        if old_player is not None and hasattr(old_player, "interface"):
            target.notify("captured_lost")
        # 占领方播放占领成功音效
        self.notify("captured_success")

    def _attack(self, target):
        if getattr(self, "_has_yielded", False):
            return
        # 夺取阈值为 100 的敌方建筑“接触即占领”：AI 直接占领而非攻击。
        # 只创建一个 AttackAction（其 update 会路由到直接占领逻辑），并刷新占领声明，
        # 使本单位在占领途中持续持有声明，其他单位据此避免重复下达占领命令。
        # 不切换武器、不播放攻击音效、不进行冲锋/伤害判定。
        if (
            getattr(target, "capture_hp_threshold", 0) == 100
            and self.is_an_enemy(target)
            and bool(getattr(self, "can_capture", 1))
        ):
            target._capture_claimer_id = self.id
            target._capture_claim_time = self.world.time
            if not isinstance(self.action, AttackAction) or self.action.target != target:
                self.action = AttackAction(self, target)
            return
        # 在决定攻击目标时立即切换到最合适的武器
        if (self._should_auto_switch_weapon() and 
            hasattr(self, 'weapons') and len(self.weapons) > 1 and
            not self._should_respect_manual_weapon_choice()):
            best_weapon = self._choose_best_weapon_for_target(target)
            if best_weapon and best_weapon != self.current_weapon:
                # 自动切换到最佳武器（播放音效但不播报武器名）
                if hasattr(self, '_auto_switch_weapon'):
                    self._auto_switch_weapon(best_weapon)
                elif hasattr(self, '_equip_weapon_silently'):
                    self._equip_weapon_silently(best_weapon)
        
        # 检查对目标的伤害是否为0
        melee_damage = self._get_melee_damage_vs(target)
        ranged_damage = self._get_ranged_damage_vs(target)

        # 获取最小伤害值
        minimal_damage = getattr(self, 'minimal_damage', 0)

        # 如果近战和远程伤害都是0且最小伤害也为0，检查是否是自爆单位
        if melee_damage == 0 and ranged_damage == 0 and minimal_damage == 0:
            # 如果是自爆单位，则允许攻击
            if not (getattr(self, 'mdg_explode', False) or getattr(self, 'rdg_explode', False)):
                return

        # don't notify or attack if already attacking the same target
        # (at the moment, this test is necessary if the target is not a menace, for example a farm)
        if not isinstance(self.action, AttackAction) or self.action.target != target:
            # 如果目标变更，重置冲锋状态
            if hasattr(self, 'reset_charge_state') and (not isinstance(self.action, AttackAction) or 
               (isinstance(self.action, AttackAction) and self.action.target != target)):
                self.reset_charge_state(force=True)
                
            self.action = AttackAction(self, target)
            self.notify("attack")

    def _container_attack_inside_chance(self, container):
        if container is None:
            return 0
        return max(0, min(100, int(getattr(container, "attack_inside_chance", 0))))

    def _get_attack_inside_chance(self, target):
        if target is None:
            return 0
        if getattr(target, "is_inside", False):
            container = getattr(getattr(target, "place", None), "container", None)
            return self._container_attack_inside_chance(container)
        return self._container_attack_inside_chance(target)

    def _combat_target_place(self, target):
        if getattr(target, "is_inside", False):
            container = getattr(getattr(target, "place", None), "container", None)
            if container is not None:
                return container.place
        return getattr(target, "place", None)

    def _sync_inside_combat_coords(self, target):
        if target is None or getattr(target, "_inside_combat_synced", False):
            return
        if not getattr(target, "is_inside", False):
            return
        container = getattr(getattr(target, "place", None), "container", None)
        if container is None:
            return
        target._saved_combat_x = target.x
        target._saved_combat_y = target.y
        target.x = container.x
        target.y = container.y
        target._inside_combat_synced = True

    def _restore_inside_combat_coords(self, target):
        if target is None or not getattr(target, "_inside_combat_synced", False):
            return
        target.x = target._saved_combat_x
        target.y = target._saved_combat_y
        target._inside_combat_synced = False
        del target._saved_combat_x
        del target._saved_combat_y

    def _attackable_passengers(self, container):
        if container is None:
            return []
        inside = getattr(container, "inside", None)
        if inside is None:
            return []
        result = []
        for obj in list(getattr(inside, "objects", [])):
            if obj is None or obj.hp <= 0:
                continue
            if not self.is_an_enemy(obj):
                continue
            result.append(obj)
        return result

    def _attacker_near_container(self, container):
        if container is None:
            return False
        outside = container.place
        if outside is not None and self.place is outside:
            return True
        blocked_exit = getattr(container, "blocked_exit", None)
        if blocked_exit is not None:
            other_place = getattr(getattr(blocked_exit, "other_side", None), "place", None)
            if other_place is not None and self.place is other_place:
                return True
        return False

    def _attacker_can_reach_container_passengers(self, container):
        if self._attacker_near_container(container):
            return True
        return self._near_enough_to_aim(container)

    def _can_attack_inside_passenger(self, target):
        if not getattr(target, "is_inside", False):
            return False
        container = getattr(getattr(target, "place", None), "container", None)
        if container is None:
            return False
        chance = self._container_attack_inside_chance(container)
        if chance <= 0:
            return bool(self.allow_attack_inside)
        if not self._attacker_can_reach_container_passengers(container):
            return False
        return self.is_an_enemy(target)

    def _resolve_inside_attack_target(self, passenger):
        chance = self._get_attack_inside_chance(passenger)
        if chance <= 0:
            return None
        container = passenger.place.container
        if chance >= 100 or self.world.random.randint(1, 100) <= chance:
            return passenger
        return container

    def _resolve_damage_target(self, target):
        if target is None:
            return None
        if getattr(target, "is_inside", False):
            return self._resolve_inside_attack_target(target)
        chance = self._get_attack_inside_chance(target)
        if chance <= 0:
            return target
        passengers = self._attackable_passengers(target)
        if not passengers:
            return target
        if chance >= 100 or self.world.random.randint(1, 100) <= chance:
            return self.world.random.choice(passengers)
        return target

    def _can_attack_from_inside(self):
        """检查单位是否可以从载具内部进行攻击"""
        # 如果不在载具内,允许攻击
        if not self.is_inside:
            return True
            
        # 获取载具对象
        container = self.place.container
        if not container:
            return False
            
        # 检查是否允许所有单位攻击
        attack_types = getattr(container, 'passenger_attack_types', None)
        if attack_types:
            if 'all' in attack_types:
                return True

            # 检查特定单位类型
            return (self.type_name in attack_types or
                    any(t in attack_types for t in getattr(self, 'expanded_is_a', [])))
                    
        return False  # 默认不允许在载具内攻击
        
    def can_attack(self, target):
        """检查是否可以攻击目标"""
        # 防御性检查
        if target is None or target.hp <= 0 or self.hp <= 0:
            return False

        forced = self._player_ordered_attack_on(target)
        if not forced and not self.is_an_enemy(target):
            return False

        # 检查目标是否在视野中（感知或记忆中）或相邻区域
        # 开放式容器内敌人：邻格/射程内可达时跳过视野检查
        inside_passenger = getattr(target, "is_inside", False) and self._can_attack_inside_passenger(target)
        if not forced and not inside_passenger and (
            target not in self.player.perception
            and target not in self.player.memory
            and target.place not in self.place.neighbors
        ):
            return False
            
        # 如果启用了自动武器切换且没有手动武器选择优先级，检查是否有任何武器可以攻击目标
        if (self._should_auto_switch_weapon() and hasattr(self, 'weapons') and 
            len(self.weapons) > 1 and hasattr(self, '_weapon_instances') and
            not self._should_respect_manual_weapon_choice()):
            
            # 检查是否有任何武器可以攻击目标
            for weapon_name in self.weapons:
                if weapon_name in self._weapon_instances:
                    weapon = self._weapon_instances[weapon_name]
                    if self._can_weapon_attack_target(weapon, target):
                        return True
            return False
        else:
            self._sync_inside_combat_coords(target)
            try:
                if self.in_melee_range(target) or self.in_ranged_range(target):
                    return True
            finally:
                self._restore_inside_combat_coords(target)
            return False
    
    def _can_weapon_attack_target(self, weapon, target):
        """检查指定武器是否可以攻击目标
        
        Args:
            weapon: 武器实例
            target: 攻击目标
            
        Returns:
            bool: 是否可以攻击
        """
        # 计算到目标的距离
        distance = self._int_distance(self.x, self.y, target.x, target.y)
        collision = self.radius + target.radius
        
        # 检查近战攻击范围
        weapon_mdg = getattr(weapon, 'mdg', 0)
        if weapon_mdg > 0:
            weapon_mdg_range = getattr(weapon, 'mdg_range', 0)
            weapon_mdg_min_range = getattr(weapon, 'mdg_minimal_range', 0)
            
            effective_mdg_range = weapon_mdg_range + collision
            effective_mdg_min_range = weapon_mdg_min_range + collision
            
            if effective_mdg_min_range <= distance <= effective_mdg_range:
                return True
        
        # 检查远程攻击范围
        weapon_rdg = getattr(weapon, 'rdg', 0)
        if weapon_rdg > 0:
            weapon_rdg_range = getattr(weapon, 'rdg_range', 0)
            weapon_rdg_min_range = getattr(weapon, 'rdg_minimal_range', 0)
            
            effective_rdg_range = weapon_rdg_range + collision
            effective_rdg_min_range = weapon_rdg_min_range + collision
            
            if effective_rdg_min_range <= distance <= effective_rdg_range:
                return True
        
        return False 

    def _can_attack(self, target):
        # 检查目标是否在攻击范围内
        if not self.in_attack_range(target):
            return False

        # 如果目标在容器内
        if target.is_inside:
            if self._can_attack_inside_passenger(target):
                return True
            container = target.place.container
            # 如果容器阻挡了出口
            if hasattr(container, 'blocked_exit'):
                exit = container.blocked_exit
                # 如果攻击者在出口任意一侧都可以攻击
                if (self.place is container.place or  # 攻击者在容器所在区域
                        (exit and self.place is exit.other_side.place)):  # 攻击者在出口另一侧
                    return True

        # 检查目标是否在当前区域或相邻区域
        return (target.place is self.place or
                target.place in self.place.neighbors)