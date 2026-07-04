from .damage_calculation import DamageCalculationMixin
from ..lib.nofloat import int_distance as _int_distance


class DamageEffectsMixin(DamageCalculationMixin):
    """
    处理伤害效果相关的功能，如受击处理、自爆、暴击等
    """
    def _int_distance(self, x1, y1, x2, y2):
        """计算两点之间的距离（委托给 nofloat 的 Cython 加速版本）"""
        return _int_distance(x1, y1, x2, y2)

    def _scale_coop_difficulty_damage(self, actual_damage, attacker):
        """按合作战役难度缩放敌方单位打出的伤害（整数运算，确定性安全）。

        仅当攻击者属于敌方（非人类、非中立玩家）且世界设置了难度系数时生效。
        """
        if attacker is None or not actual_damage:
            return actual_damage
        world = getattr(self, "world", None)
        if world is None:
            return actual_damage
        factor = getattr(world, "enemy_damage_factor", 100)
        if factor == 100:
            return actual_damage
        p = getattr(attacker, "player", None)
        if p is None or getattr(p, "is_human", False) or getattr(p, "neutral", False):
            return actual_damage
        return actual_damage * factor // 100

    def _get_reflect_percent(self):
        """累加当前 buff 的 reflect_percent，上限 100。"""
        total = 0
        for b in getattr(self, "_buffs", []):
            pct = getattr(type(b), "reflect_percent", 0)
            if pct:
                total += pct
        return min(total, 100)

    def _skill_trigger_condition_met(self, skill_cls, host):
        condition = getattr(skill_cls, "trigger_condition", "") or ""
        if condition:
            try:
                from ..worldbuff import Buff

                return Buff._evaluate_condition(host, condition)
            except Exception:
                return True
        threshold = getattr(skill_cls, "hp_threshold", 0) or 0
        if threshold > 0:
            hp_max = getattr(host, "hp_max", 0) or 0
            if hp_max <= 0:
                return False
            return (host.hp * 100) // hp_max <= threshold
        return True

    def _skill_trigger_rate(self, skill_cls, trigger_kind, is_melee):
        if trigger_kind == "active":
            typed_rate = getattr(skill_cls, "mdg_trigger_rate" if is_melee else "rdg_trigger_rate", 0)
            return typed_rate if typed_rate > 0 else getattr(skill_cls, "active_trigger_rate", 100)
        return getattr(skill_cls, "passive_trigger_rate", 100)

    def _try_trigger_skill(self, caster, target, skill_name, trigger_kind, is_melee):
        if caster is None or target is None or getattr(caster, "_triggering_skill", False):
            return False
        if getattr(caster, "player", None) is None or getattr(caster, "hp", 0) <= 0:
            return False
        skill_cls = caster.world.unit_class(skill_name)
        if skill_cls is None or not getattr(skill_cls, "effect", None):
            return False
        if not self._skill_trigger_condition_met(skill_cls, caster):
            return False
        rate = self._skill_trigger_rate(skill_cls, trigger_kind, is_melee)
        if rate <= 0:
            return False
        if rate < 100 and caster.world.random.randint(1, 100) > rate:
            return False
        if getattr(skill_cls, "mana_cost", 0) and getattr(caster, "mana", 0) < skill_cls.mana_cost:
            return False
        if hasattr(caster, "has_cooldown") and caster.has_cooldown(skill_cls):
            return False
        skill_target = caster if getattr(skill_cls, "effect_target", ()) == ["self"] else target

        def finish_skill():
            if target is None or getattr(target, "player", None) is None or getattr(target, "hp", 0) <= 0:
                return False
            if getattr(caster, "player", None) is None or getattr(caster, "hp", 0) <= 0:
                return False
            if getattr(skill_cls, "mana_cost", 0) and getattr(caster, "mana", 0) < skill_cls.mana_cost:
                return False
            if hasattr(caster, "has_cooldown") and caster.has_cooldown(skill_cls):
                return False
            try:
                caster._triggering_skill = True
                success = bool(skill_cls.execute_skill(caster, skill_target, caster.world))
            finally:
                caster._triggering_skill = False
            if not success:
                return False
            if getattr(skill_cls, "mana_cost", 0):
                caster.mana -= skill_cls.mana_cost
            if hasattr(caster, "add_cooldown"):
                caster.add_cooldown(skill_cls)
            if hasattr(caster, "notify"):
                caster.notify(f"skill_triggered,{skill_name},{getattr(target, 'id', None)}")
            return True

        ready = getattr(skill_cls, "ready", 0) or 0
        if isinstance(ready, list):
            ready = ready[0] if ready else 0
        try:
            ready = int(ready)
        except (TypeError, ValueError):
            ready = 0
        if ready > 0:
            if hasattr(caster, "notify"):
                caster.notify(f"skill_ready,{skill_name}")
            caster.world.schedule_after(ready, finish_skill)
            return True
        if not finish_skill():
            return False
        return True

    def _trigger_auto_skills_after_hit(self, attacker, is_melee):
        if attacker is None or getattr(attacker, "_is_skill_combat_proxy", False):
            return
        if is_melee is None:
            is_melee = True
        if getattr(attacker, "is_an_enemy", None) and not attacker.is_an_enemy(self):
            return
        for skill_name in (
            attacker.iter_auto_trigger_skill_names()
            if hasattr(attacker, "iter_auto_trigger_skill_names")
            else getattr(attacker, "active_trigger_skills", ()) or ()
        ):
            self._try_trigger_skill(attacker, self, skill_name, "active", is_melee)
        for skill_name in (
            self.iter_passive_trigger_skill_names()
            if hasattr(self, "iter_passive_trigger_skill_names")
            else getattr(self, "passive_trigger_skills", ()) or ()
        ):
            self._try_trigger_skill(self, attacker, skill_name, "passive", is_melee)

    def receive_hit(self, damage, attacker, notify=True, is_crit=False, is_charge=False, is_melee=None, is_reflect=False):
        """处理被命中。

        Args:
            damage: 原始伤害值
            attacker: 攻击者，可为 None（环境伤害）
            notify: 是否发送受伤通知
            is_crit: 是否暴击
            is_charge: 是否冲锋伤害
            is_melee: 明确指定本次攻击为近战(True)或远程(False)。
                      None 时回落到旧的距离/属性推断逻辑（保持向后兼容）。
            is_reflect: 是否为反弹伤害（不再二次反弹）
        """
        # 防御性检查
        # 条约期内：禁止来自敌对单位的直接伤害
        try:
            if attacker is not None and hasattr(self, 'world') and getattr(self.world, 'treaty_until_time', 0) > 0:
                if self.world.time < self.world.treaty_until_time:
                    if hasattr(attacker, 'player') and hasattr(self, 'player') and attacker.player and self.player:
                        if self.player.player_is_an_enemy(attacker.player):
                            # 仅拦截敌对攻击；不处理环境/中立
                            return
        except Exception:
            pass
        if getattr(self, "_has_yielded", False):
            return
        if attacker is not None and getattr(attacker, "_has_yielded", False):
            return
        if self.player is None or self.hp <= 0:
            return

        # 记录攻击者并通知玩家
        if attacker is not None:
            from ..skill_combat import resolve_combat_attacker

            attacker = resolve_combat_attacker(attacker)
            self.player.observe(attacker)
            self.last_attacker = attacker

            # 通知友军单位（仅当攻击者存在时）
            if self.place:
                self._notify_guard_units(attacker)

        # 检查反冲锋机制 (提前检查，在应用伤害之前)
        original_damage = damage
        if attacker is not None and is_charge:
            # 如果攻击者正在冲锋，检查被攻击者是否有反冲锋能力
            now = self.world.time

            # 判断是近战还是远程冲锋：优先使用调用方显式传入的 is_melee，
            # 否则回落到基于当前距离的旧推断（兼容未升级的调用点）。
            if is_melee is None:
                is_melee = attacker.in_melee_range(self) if hasattr(attacker, 'in_melee_range') else True
            
            # 获取反冲锋属性
            if is_melee:
                op_charge = self.op_charge_mdg  # 近战反冲锋倍率
                op_charge_cd = self.op_charge_mdg_cd  # 近战反冲锋冷却时间
                op_charge_dist = self.op_charge_mdg_dist  # 近战反冲锋有效距离
                op_charge_next_time = getattr(self, 'op_charge_mdg_next_time', 0)  # 下次可用时间
                op_charge_ready = getattr(self, 'op_charge_mdg_ready', True)  # 就绪状态
                last_op_charge_target_id = getattr(self, 'last_op_charge_mdg_target_id', None)  # 上次目标
                op_charge_vs = getattr(self, 'op_charge_mdg_vs', {})  # VS特定单位倍率
            else:
                op_charge = self.op_charge_rdg  # 远程反冲锋倍率
                op_charge_cd = self.op_charge_rdg_cd  # 远程反冲锋冷却时间
                op_charge_dist = self.op_charge_rdg_dist  # 远程反冲锋有效距离
                op_charge_next_time = getattr(self, 'op_charge_rdg_next_time', 0)  # 下次可用时间
                op_charge_ready = getattr(self, 'op_charge_rdg_ready', True)  # 就绪状态
                last_op_charge_target_id = getattr(self, 'last_op_charge_rdg_target_id', None)  # 上次目标
                op_charge_vs = getattr(self, 'op_charge_rdg_vs', {})  # VS特定单位倍率
            
            # 校验 op_charge_dist：异常值禁用 op_charge，而不是默认为 0（曾被
            # 当作"不限距离"使用，导致数据写坏反而生效）。
            op_charge_valid = True
            if isinstance(op_charge_dist, list) and op_charge_dist:
                if isinstance(op_charge_dist[0], (int, float)):
                    op_charge_dist = op_charge_dist[0]
                else:
                    op_charge_valid = False
            elif not isinstance(op_charge_dist, (int, float)):
                op_charge_valid = False

            # 校验 op_charge_cd
            if isinstance(op_charge_cd, list) and op_charge_cd:
                if isinstance(op_charge_cd[0], (int, float)):
                    op_charge_cd = op_charge_cd[0]
                else:
                    op_charge_valid = False
            elif not isinstance(op_charge_cd, (int, float)):
                op_charge_valid = False

            # 冷却到期自动恢复 ready 标志（与冲锋系统的距离恢复语义对齐）
            if op_charge_valid and not op_charge_ready and now >= op_charge_next_time:
                op_charge_ready = True
                if is_melee:
                    self.op_charge_mdg_ready = True
                else:
                    self.op_charge_rdg_ready = True

            # "拥有反冲锋机制"的判定：自身设置了反冲锋倍率(op_charge>0)
            # 或者设置了反冲锋有效距离(op_charge_dist>0)。
            # 这样允许配置"只设距离不设倍率"的单位也参与反冲锋（按 spec 公式默认值反伤）。
            has_op_charge_mechanism = (op_charge > 0) or (op_charge_dist > 0)

            # 检查反冲锋条件
            if (op_charge_valid and
                has_op_charge_mechanism and
                op_charge_ready and  # 反冲锋就绪（cooldown 已自动并入此标志）
                attacker.id != last_op_charge_target_id):  # 同一冷却周期内不对同一攻击者重复反冲

                # 计算与攻击者的距离
                dist = self._int_distance(self.x, self.y, attacker.x, attacker.y) if hasattr(self, '_int_distance') else 0

                # 如果在有效距离内（op_charge_dist <= 0 仍保留"不限距离"的设计语义）
                if dist <= op_charge_dist or op_charge_dist <= 0:
                    # 发送反冲锋通知
                    self.notify(f"op_charge,{1 if is_melee else 0},{attacker.id}")

                    # 向攻击者发送冲锋失败通知（aim() 据此跳过 charge_success 与溅射）
                    # 注：历史版本曾在此处强制重置攻击者的冲锋状态，但 aim() 后续会立即
                    # 重写 last_charge_*_target_id 与冲锋冷却，使该重置毫无效果，已移除。
                    attacker.notify("charge_failed")

                    # === 反冲锋伤害计算（加法公式）===
                    # 默认: counter = 对方 mdg(rdg) + 对方 charge_mdg(charge_rdg)
                    # 自身设了反冲锋加值 op_charge: 再 + (op_charge + op_charge_vs)

                    # 攻击者的普攻基础（含 mdg_vs / rdg_vs 对 self 类型的修正）
                    if is_melee:
                        attacker_base = getattr(attacker, 'mdg', 0)
                        attacker_charge_mult = getattr(attacker, 'charge_mdg', 0)
                        atk_vs = getattr(attacker, 'mdg_vs', None) or {}
                        atk_charge_vs = getattr(attacker, 'charge_mdg_vs', None) or {}
                    else:
                        attacker_base = getattr(attacker, 'rdg', 0)
                        attacker_charge_mult = getattr(attacker, 'charge_rdg', 0)
                        atk_vs = getattr(attacker, 'rdg_vs', None) or {}
                        atk_charge_vs = getattr(attacker, 'charge_rdg_vs', None) or {}

                    # 攻击者 mdg/rdg 对 self 类型的 vs 修正
                    if self.type_name in atk_vs:
                        attacker_base += atk_vs[self.type_name]
                    elif hasattr(self, 'expanded_is_a'):
                        for t in self.expanded_is_a:
                            if t in atk_vs:
                                attacker_base += atk_vs[t]
                                break

                    # 攻击者 charge_mdg/charge_rdg 对 self 类型的 vs 修正
                    if self.type_name in atk_charge_vs:
                        attacker_charge_mult += atk_charge_vs[self.type_name]
                    elif hasattr(self, 'expanded_is_a'):
                        for t in self.expanded_is_a:
                            if t in atk_charge_vs:
                                attacker_charge_mult += atk_charge_vs[t]
                                break

                    # 默认反冲锋伤害：对方 mdg/rdg + 对方 charge_mdg/charge_rdg（加法）
                    counter_damage = attacker_base + attacker_charge_mult

                    # 如果自身设了反冲锋加值，再加上 (op_charge + op_charge_vs)
                    if op_charge > 0:
                        # 反冲锋加值 vs（叠加语义）
                        vs_multiplier = 0
                        if attacker.type_name in op_charge_vs:
                            vs_multiplier = op_charge_vs[attacker.type_name]
                        elif hasattr(attacker, 'expanded_is_a'):
                            for t in attacker.expanded_is_a:
                                if t in op_charge_vs:
                                    vs_multiplier = op_charge_vs[t]
                                    break
                        op_charge_total = op_charge + vs_multiplier
                        counter_damage = counter_damage + op_charge_total

                    # 确保最小伤害
                    counter_damage = max(counter_damage, 1)

                    # 对攻击者造成反冲锋伤害（明确传入 is_melee，避免攻击者端再做距离/属性猜测）
                    attacker.receive_hit(counter_damage, self, notify=True, is_crit=False, is_charge=False, is_melee=is_melee)
                    
                    # 检查反冲锋攻击是否会触发自身buff
                    
                    # 首先从当前武器的debuffs中触发
                    debuffs_to_check = []
                    
                    # 优先检查当前武器的debuffs
                    if (hasattr(self, 'current_weapon') and self.current_weapon and 
                        hasattr(self, '_weapon_instances') and self.current_weapon in self._weapon_instances):
                        current_weapon = self._weapon_instances[self.current_weapon]
                        if hasattr(current_weapon, 'debuffs') and current_weapon.debuffs:
                            debuffs_to_check.extend(current_weapon.debuffs)
                    
                    # 然后检查单位自身的debuffs（避免重复）
                    if hasattr(self, 'debuffs') and self.debuffs:
                        for debuff in self.debuffs:
                            if debuff not in debuffs_to_check:
                                debuffs_to_check.append(debuff)

                    for buff_name in debuffs_to_check:
                        # 获取buff类
                        buff_cls = self.world.unit_class(buff_name)
                        if buff_cls is None:
                            continue
                        
                        # 使用反冲锋攻击触发方式检查是否触发buff
                        if hasattr(buff_cls, 'should_trigger_on_op_charge') and buff_cls.should_trigger_on_op_charge(self, is_melee=is_melee):
                            # 应用buff效果给自己
                            self.add_buff(buff_name, self)
                            # 添加buff触发通知
                            self.notify(f"buff_triggered,{buff_name},{self.id}")
                            
                        # 检查是否有对攻击者生效的buff
                        # 优先使用反冲锋触发率，如果没有则依次使用冲锋触发率和普通攻击触发率
                        if is_melee:
                            if hasattr(buff_cls, 'op_charge_mdg_trigger_rate') and buff_cls.op_charge_mdg_trigger_rate > 0:
                                trigger_rate = buff_cls.op_charge_mdg_trigger_rate
                            elif hasattr(buff_cls, 'charge_mdg_trigger_rate') and buff_cls.charge_mdg_trigger_rate > 0:
                                trigger_rate = buff_cls.charge_mdg_trigger_rate
                            else:
                                trigger_rate = buff_cls.mdg_trigger_rate
                        else:
                            if hasattr(buff_cls, 'op_charge_rdg_trigger_rate') and buff_cls.op_charge_rdg_trigger_rate > 0:
                                trigger_rate = buff_cls.op_charge_rdg_trigger_rate
                            elif hasattr(buff_cls, 'charge_rdg_trigger_rate') and buff_cls.charge_rdg_trigger_rate > 0:
                                trigger_rate = buff_cls.charge_rdg_trigger_rate
                            else:
                                trigger_rate = buff_cls.rdg_trigger_rate
                        
                        if trigger_rate > 0 and self.world.random.randint(1, 100) <= trigger_rate:
                            # 应用buff效果给攻击者
                            attacker.add_buff(buff_name, self)
                            # 添加buff触发通知
                            self.notify(f"buff_applied,{buff_name},{attacker.id}")
                    
                    # 更新反冲锋状态
                    if is_melee:
                        self.op_charge_mdg_next_time = now + op_charge_cd
                        self.op_charge_mdg_ready = False
                        self.last_op_charge_mdg_target_id = attacker.id
                    else:
                        self.op_charge_rdg_next_time = now + op_charge_cd
                        self.op_charge_rdg_ready = False
                        self.last_op_charge_rdg_target_id = attacker.id

                    # 修改：反冲锋成功后，将冲锋伤害降为普通攻击伤害
                    # 获取攻击者的普通攻击伤害
                    normal_damage = 0
                    if is_melee and hasattr(attacker, 'mdg'):
                        normal_damage = attacker.mdg
                        
                        # 检查是否有针对当前单位类型的特殊伤害值
                        if hasattr(attacker, 'mdg_vs') and self.type_name in attacker.mdg_vs:
                            normal_damage += attacker.mdg_vs[self.type_name]
                        # 检查扩展类型
                        elif hasattr(attacker, 'mdg_vs') and hasattr(self, 'expanded_is_a'):
                            for t in self.expanded_is_a:
                                if t in attacker.mdg_vs:
                                    normal_damage += attacker.mdg_vs[t]
                                    break
                    elif not is_melee and hasattr(attacker, 'rdg'):
                        normal_damage = attacker.rdg
                        
                        # 检查是否有针对当前单位类型的特殊伤害值
                        if hasattr(attacker, 'rdg_vs') and self.type_name in attacker.rdg_vs:
                            normal_damage += attacker.rdg_vs[self.type_name]
                        # 检查扩展类型
                        elif hasattr(attacker, 'rdg_vs') and hasattr(self, 'expanded_is_a'):
                            for t in self.expanded_is_a:
                                if t in attacker.rdg_vs:
                                    normal_damage += attacker.rdg_vs[t]
                                    break
                    
                    # 将伤害改为普通伤害
                    # 注意：游戏内部的伤害值可能已经是乘以10的值
                    # 在_get_charge_damage方法中，返回 (damage + vs_damage) * 10
                    # 所以这里我们不需要再乘以10
                    damage = normal_damage
                    is_charge = False  # 取消冲锋状态标记

        # 计算实际伤害（harm可绕过防御/最小伤害等计算，保持与旧版一致）
        bypass_calc = getattr(attacker, '_bypass_damage_calc_for_harm', False)
        if bypass_calc:
            actual_damage = damage
        else:
            actual_damage = self._calculate_actual_damage(damage, attacker)

        # 合作战役难度：缩放"敌方（非人类、非中立）单位输出"的伤害。整数运算，
        # 确定性安全；只影响敌人打出的伤害，玩家自身输出不变（与决定版一致）。
        actual_damage = self._scale_coop_difficulty_damage(actual_damage, attacker)

        # 应用伤害
        # 将伤害作用到单位
        self.hp -= actual_damage

        if actual_damage > 0 and attacker is not None and not is_reflect and self.hp > 0:
            self._trigger_auto_skills_after_hit(attacker, is_melee)
        
        # 被动触发Buff (is_passive = True)
        # 检查是否需要触发被动buff (例如HP低于阈值时触发)
        
        # 首先从当前武器的debuffs中触发
        debuffs_to_check = []
        
        # 优先检查当前武器的debuffs
        if (hasattr(self, 'current_weapon') and self.current_weapon and 
            hasattr(self, '_weapon_instances') and self.current_weapon in self._weapon_instances):
            current_weapon = self._weapon_instances[self.current_weapon]
            if hasattr(current_weapon, 'debuffs') and current_weapon.debuffs:
                debuffs_to_check.extend(current_weapon.debuffs)
        
        # 然后检查单位自身的debuffs（避免重复）
        if hasattr(self, 'debuffs') and self.debuffs:
            for debuff in self.debuffs:
                if debuff not in debuffs_to_check:
                    debuffs_to_check.append(debuff)

        for buff_name in debuffs_to_check:
            # 获取buff类
            buff_cls = self.world.unit_class(buff_name)
            if buff_cls is None:
                continue

            # 检查是否是被动型buff并且符合触发条件
            if hasattr(buff_cls, 'should_trigger_on_damage') and buff_cls.should_trigger_on_damage(self):
                # 应用buff效果给自己
                self.add_buff(buff_name, self)
                # 添加buff触发通知
                self.notify(f"buff_triggered,{buff_name},{self.id}")
                
        # 冲锋攻击特殊处理 - 当attacker使用冲锋攻击时，检查和触发buff
        if is_charge and attacker is not None:
            # 首先从攻击者当前武器的debuffs中触发
            debuffs_to_check = []
            
            # 优先检查攻击者当前武器的debuffs
            if (hasattr(attacker, 'current_weapon') and attacker.current_weapon and 
                hasattr(attacker, '_weapon_instances') and attacker.current_weapon in attacker._weapon_instances):
                current_weapon = attacker._weapon_instances[attacker.current_weapon]
                if hasattr(current_weapon, 'debuffs') and current_weapon.debuffs:
                    debuffs_to_check.extend(current_weapon.debuffs)
            
            # 然后检查攻击者自身的debuffs（避免重复）
            if hasattr(attacker, 'debuffs') and attacker.debuffs:
                for debuff in attacker.debuffs:
                    if debuff not in debuffs_to_check:
                        debuffs_to_check.append(debuff)

            # 判断是近战还是远程冲锋：优先复用调用方传入的 is_melee（若 op_charge 分支
            # 进入过会已经被设值），否则回落到距离推断
            if is_melee is None:
                is_melee = attacker.in_melee_range(self) if hasattr(attacker, 'in_melee_range') else True

            # 从攻击者身上获取可用的buff
            for buff_name in debuffs_to_check:
                # 获取buff类
                buff_cls = attacker.world.unit_class(buff_name)
                if buff_cls is None:
                    continue
                
                # 使用冲锋攻击触发方式触发buff
                if hasattr(buff_cls, 'should_trigger_on_charge') and buff_cls.should_trigger_on_charge(attacker, is_melee=is_melee):
                    # 应用buff效果给攻击者
                    attacker.add_buff(buff_name, attacker)
                    # 添加buff触发通知
                    attacker.notify(f"buff_triggered,{buff_name},{attacker.id}")
                    
                # 检查是否有对目标生效的buff
                trigger_rate = buff_cls.charge_mdg_trigger_rate if is_melee else buff_cls.charge_rdg_trigger_rate
                # 如果冲锋触发率为0，则使用普通攻击触发率
                if trigger_rate <= 0:
                    trigger_rate = buff_cls.mdg_trigger_rate if is_melee else buff_cls.rdg_trigger_rate
                
                if trigger_rate > 0 and self.world.random.randint(1, 100) <= trigger_rate:
                    # 应用buff效果给目标
                    self.add_buff(buff_name, attacker)
                    # 添加buff触发通知
                    attacker.notify(f"buff_applied,{buff_name},{self.id}")
                
        # 发送受伤通知（透传 is_melee，避免在通知层再做属性级猜测）
        # 被动 buff/DOT 可能在上方已触发 die() 并清空 player，需再校验。
        if notify and attacker is not None and self.player is not None:
            self._send_hit_notification(attacker, actual_damage, is_crit, is_charge, is_melee=is_melee)

        # 伤害反弹（斗转星移等 buff）
        if (
            not is_reflect
            and attacker is not None
            and actual_damage > 0
            and hasattr(self, "is_an_enemy")
            and self.is_an_enemy(attacker)
        ):
            reflect_percent = self._get_reflect_percent()
            if reflect_percent > 0:
                reflect_damage = actual_damage * reflect_percent // 100
                if reflect_damage > 0:
                    attacker.receive_hit(
                        reflect_damage,
                        self,
                        notify=notify,
                        is_crit=False,
                        is_charge=False,
                        is_melee=is_melee,
                        is_reflect=True,
                    )
            
        # 处理死亡或受伤状态
        if self.hp <= 0 and self.player is not None:
            self.die(attacker)
            return
        else:
            if self.player:
                self.player.on_unit_attacked(self, attacker)

        # 检查是否达到夺取阈值 - 自动转变阵营（仅敌方可夺取，盟友不可互相占领）
        if (self.capture_hp_threshold > 0 and  # 只有当明确设置了大于0的阈值时才可被夺取
                self.hp > 0 and  # 确保目标没有死亡
                (self.hp * 100 / self.hp_max) <= self.capture_hp_threshold and  # 检查血量是否低于阈值
                attacker is not None and attacker.player is not None and self.player is not None and
                attacker.player.player_is_an_enemy(self.player)):

            # 执行自动转变阵营
            old_player = self.player
            self.set_player(attacker.player)

            # 通知双方玩家
            if notify:
                # 对于被占领方播放被占领音效
                if old_player and hasattr(old_player, 'interface'):
                    self.notify("captured_lost")  # 播放被占领音效

                # 对于占领方播放占领成功音效
                if attacker and hasattr(attacker, 'notify'):
                    attacker.notify("captured_success")  # 播放占领成功音效

    def _send_hit_notification(self, attacker, actual_damage, is_crit=False, is_charge=False, is_melee=None):
        """发送受击通知。

        Args:
            is_melee: 显式指定攻击类型；为 None 时回落到旧的属性推断（保留向后兼容，
                     但对双攻击单位 mdg>0 且 rdg>0 会误判为远程）。
        """
        if attacker.is_inside:
            # 如果攻击者在容器内，使用攻击者自己的类型和ID
            attacker_type = attacker.type_name
            attacker_id = attacker.id
        else:
            # 正常情况下使用容器的信息
            attacker_type = attacker.type_name
            attacker_id = attacker.id

        self._raise_subsquare_threat(actual_damage)

        # 判断攻击类型：优先使用调用方显式传入的 is_melee
        if is_melee is None:
            is_melee = not (hasattr(attacker, 'rdg') and attacker.rdg > 0 and
                            hasattr(attacker, 'rdg_range') and attacker.rdg_range > 0)
        attack_type = "mdg" if is_melee else "rdg"

        # 获取伤害等级并添加详细调试日志
        damage_level = getattr(attacker, f'{attack_type}_level', 0)

        # 添加暴击标记到通知中
        crit_flag = "1" if is_crit else "0"
        
        # 添加冲锋标记到通知中
        charge_flag = "1" if is_charge else "0"

        # 发送通知 (添加冲锋标记)
        self.notify(
            f"wounded,{attacker.type_name},{attacker.id},{damage_level},{crit_flag},{charge_flag}"
        )

    def _schedule_ballistic_hit(self, target, damage_delay_ms: int, is_melee=False):
        """调度一次攻击序列"""
        # 获取投射物标记
        is_projectile = (is_melee and self.mdg_projectile) or (not is_melee and self.rdg_projectile)

        # 主动触发Buff (is_active = True)
        # 遍历自身可用的buff，检查是否有主动类型buff可以触发
        
        # 首先从当前武器的debuffs中触发
        debuffs_to_check = []
        
        # 优先检查当前武器的debuffs
        if (hasattr(self, 'current_weapon') and self.current_weapon and 
            hasattr(self, '_weapon_instances') and self.current_weapon in self._weapon_instances):
            current_weapon = self._weapon_instances[self.current_weapon]
            if hasattr(current_weapon, 'debuffs') and current_weapon.debuffs:
                debuffs_to_check.extend(current_weapon.debuffs)
        
        # 然后检查单位自身的debuffs（避免重复）
        if hasattr(self, 'debuffs') and self.debuffs:
            for debuff in self.debuffs:
                if debuff not in debuffs_to_check:
                    debuffs_to_check.append(debuff)

        for buff_name in debuffs_to_check:
            # 获取buff类
            buff_cls = self.world.unit_class(buff_name)
            if buff_cls is None:
                continue

            # 检查是否是主动型buff
            if hasattr(buff_cls, 'should_trigger_on_attack') and buff_cls.should_trigger_on_attack(self, is_melee=True):
                # 应用buff效果给自己
                self.add_buff(buff_name, self)
                # 添加buff触发通知
                self.notify(f"buff_triggered,{buff_name},{self.id}")

        if is_projectile:
            # 计算相对速度并调整延迟
            relative_speed = self._calc_relative_speed(target)
            if relative_speed < 0:  # 目标正在接近
                # 计算距离
                distance = self._int_distance(self.x, self.y, target.x, target.y)
                # 计算预计相遇时间(考虑相对速度)
                meet_time = distance * 1000 // abs(relative_speed) if relative_speed != 0 else damage_delay_ms
                # 取较小值作为新延迟
                damage_delay_ms = min(damage_delay_ms, meet_time)

        # 限制最大和最小延迟
        damage_delay_ms = min(max(damage_delay_ms, 100), 5000)  # 100ms最小延迟,5000ms最大延迟

        # 攻击序列（诸葛弩式连发：一次攻击内多次命中，间隔由 rules 配置）
        if is_melee:
            times = min(self.mdg_seq_times, 6)
            damages = self.mdg_seq_damages
            interval = self.mdg_seq_interval
        else:
            times = min(self.rdg_seq_times, 6)
            damages = self.rdg_seq_damages
            interval = self.rdg_seq_interval

        # 如果没有设置序列,使用单次攻击
        if not damages:
            damages = [self._get_melee_damage_vs(target) if is_melee
                       else self._get_ranged_damage_vs(target)]
            times = 1
            interval = 0
        elif times > 1 and interval <= 0:
            interval = 0.25

        launch_event = "launch_mdg" if is_melee else "launch_rdg"
        launch_notify = f"{launch_event},{self.type_name},{self.id}"
        for i in range(times):
            launch_delay = int(i * interval * 1000)
            if launch_delay <= 0:
                self.notify(launch_notify)
            else:
                self.world.schedule_after(
                    launch_delay,
                    lambda msg=launch_notify: self.notify(msg),
                )

        # 预计算所有伤害值和时间
        sequence = []

        # 计算基础延迟
        base_delay = damage_delay_ms

        # 设置攻击动作时间（按序列）
        for i in range(times):
            damage = damages[i] if i < len(damages) else damages[-1]
            hit_time = self.world.time + base_delay + int(i * interval * 1000)
            sequence.append((hit_time, damage))

        # 按顺序创建攻击事件
        for hit_time, damage in sequence:
            def do_hit():
                # 需要先保存目标的位置信息，以备目标死亡后溅射伤害使用
                target_place = target.place
                target_x = target.x
                target_y = target.y
                target_type_name = target.type_name

                if (target is None or target.player is None or target.hp <= 0 or
                        self.player is None or self.hp <= 0):
                    return

                # 检查攻击范围,但在强制攻击时忽略
                self._sync_inside_combat_coords(target)
                try:
                    if not getattr(self.action, 'is_imperative', False):
                        if is_melee and not self.in_melee_range(target):
                            return
                        elif not is_melee and not self.in_ranged_range(target):
                            return
                finally:
                    self._restore_inside_combat_coords(target)

                # 检查是否是自爆单位（无论是否命中都会触发溅射）
                is_exploding_unit = False

                # 首先检查是否针对该目标类型有特定的自爆设置
                if is_melee and hasattr(self, 'mdg_explode_vs') and self.mdg_explode_vs:
                    # 直接检查目标类型
                    if target.type_name in self.mdg_explode_vs and self.mdg_explode_vs[target.type_name] > 0:
                        is_exploding_unit = True
                    # 检查扩展类型
                    elif hasattr(target, 'expanded_is_a'):
                        for t in target.expanded_is_a:
                            if t in self.mdg_explode_vs and self.mdg_explode_vs[t] > 0:
                                is_exploding_unit = True
                                break
                    # 检查对目标护甲类型的vs
                    elif hasattr(target, 'get_current_armor_name'):
                        armor_name = target.get_current_armor_name()
                        if armor_name and armor_name in self.mdg_explode_vs and self.mdg_explode_vs[armor_name] > 0:
                            is_exploding_unit = True
                    # 检查对目标护甲继承类型的vs
                    elif hasattr(target, '_armor_instance') and target._armor_instance:
                        armor = target._armor_instance
                        if hasattr(armor, 'expanded_is_a'):
                            for armor_type in armor.expanded_is_a:
                                if armor_type in self.mdg_explode_vs and self.mdg_explode_vs[armor_type] > 0:
                                    is_exploding_unit = True
                                    break
                        # 也检查护甲的直接is_a
                        elif hasattr(armor, 'is_a'):
                            for armor_type in armor.is_a:
                                if armor_type in self.mdg_explode_vs and self.mdg_explode_vs[armor_type] > 0:
                                    is_exploding_unit = True
                                    break

                elif not is_melee and hasattr(self, 'rdg_explode_vs') and self.rdg_explode_vs:
                    # 直接检查目标类型
                    if target.type_name in self.rdg_explode_vs and self.rdg_explode_vs[target.type_name] > 0:
                        is_exploding_unit = True
                    # 检查扩展类型
                    elif hasattr(target, 'expanded_is_a'):
                        for t in target.expanded_is_a:
                            if t in self.rdg_explode_vs and self.rdg_explode_vs[t] > 0:
                                is_exploding_unit = True
                                break
                    # 检查对目标护甲类型的vs
                    elif hasattr(target, 'get_current_armor_name'):
                        armor_name = target.get_current_armor_name()
                        if armor_name and armor_name in self.rdg_explode_vs and self.rdg_explode_vs[armor_name] > 0:
                            is_exploding_unit = True
                    # 检查对目标护甲继承类型的vs
                    elif hasattr(target, '_armor_instance') and target._armor_instance:
                        armor = target._armor_instance
                        if hasattr(armor, 'expanded_is_a'):
                            for armor_type in armor.expanded_is_a:
                                if armor_type in self.rdg_explode_vs and self.rdg_explode_vs[armor_type] > 0:
                                    is_exploding_unit = True
                                    break
                        # 也检查护甲的直接is_a
                        elif hasattr(armor, 'is_a'):
                            for armor_type in armor.is_a:
                                if armor_type in self.rdg_explode_vs and self.rdg_explode_vs[armor_type] > 0:
                                    is_exploding_unit = True
                                    break

                # 如果没有特定设置，则检查全局自爆设置
                if not is_exploding_unit:
                    is_exploding_unit = (is_melee and self.mdg_explode) or (not is_melee and self.rdg_explode)

                # 命中判定和伤害处理
                # Bug 修复：原代码 ``self._hit_or_miss(target) or is_exploding_unit`` 与
                # ``is_hit = self._hit_or_miss(target)`` 连续调用两次 _hit_or_miss，
                # 每次都消耗 world.random 状态，且 is_hit 与"是否进入此分支"用了
                # 不同的随机 roll。修复后只 roll 一次，is_hit 反映该 roll 的真实结果，
                # 自爆单位即使 miss 仍会进入此分支（用于触发爆炸伤害逻辑）。
                is_hit = self._hit_or_miss(target)
                if is_hit or is_exploding_unit:

                    # 暴击判定
                    is_crit = False
                    crit_damage = damage

                    # 如果命中，进行暴击和伤害计算
                    if is_hit:
                        # 获取攻击者基础暴击几率
                        base_crit_rate = self.mdg_crit_rate if is_melee else self.rdg_crit_rate

                        # 获取针对特定单位类型的暴击率修正
                        vs_crit_rate = 0
                        if is_melee and hasattr(self, 'mdg_crit_rate_vs'):
                            # 先检查直接对单位类型的vs
                            if target.type_name in self.mdg_crit_rate_vs:
                                vs_crit_rate = self.mdg_crit_rate_vs[target.type_name]
                            # 检查对单位继承类型的vs
                            elif hasattr(target, 'expanded_is_a'):
                                for t in target.expanded_is_a:
                                    if t in self.mdg_crit_rate_vs:
                                        vs_crit_rate = self.mdg_crit_rate_vs[t]
                                        break
                            # 检查对目标护甲类型的vs
                            elif hasattr(target, 'get_current_armor_name'):
                                armor_name = target.get_current_armor_name()
                                if armor_name and armor_name in self.mdg_crit_rate_vs:
                                    vs_crit_rate = self.mdg_crit_rate_vs[armor_name]
                            # 检查对目标护甲继承类型的vs
                            elif hasattr(target, '_armor_instance') and target._armor_instance:
                                armor = target._armor_instance
                                if hasattr(armor, 'expanded_is_a'):
                                    for armor_type in armor.expanded_is_a:
                                        if armor_type in self.mdg_crit_rate_vs:
                                            vs_crit_rate = self.mdg_crit_rate_vs[armor_type]
                                            break
                                # 也检查护甲的直接is_a
                                elif hasattr(armor, 'is_a'):
                                    for armor_type in armor.is_a:
                                        if armor_type in self.mdg_crit_rate_vs:
                                            vs_crit_rate = self.mdg_crit_rate_vs[armor_type]
                                            break
                        elif not is_melee and hasattr(self, 'rdg_crit_rate_vs'):
                            # 先检查直接对单位类型的vs
                            if target.type_name in self.rdg_crit_rate_vs:
                                vs_crit_rate = self.rdg_crit_rate_vs[target.type_name]
                            # 检查对单位继承类型的vs
                            elif hasattr(target, 'expanded_is_a'):
                                for t in target.expanded_is_a:
                                    if t in self.rdg_crit_rate_vs:
                                        vs_crit_rate = self.rdg_crit_rate_vs[t]
                                        break
                            # 检查对目标护甲类型的vs
                            elif hasattr(target, 'get_current_armor_name'):
                                armor_name = target.get_current_armor_name()
                                if armor_name and armor_name in self.rdg_crit_rate_vs:
                                    vs_crit_rate = self.rdg_crit_rate_vs[armor_name]
                            # 检查对目标护甲继承类型的vs
                            elif hasattr(target, '_armor_instance') and target._armor_instance:
                                armor = target._armor_instance
                                if hasattr(armor, 'expanded_is_a'):
                                    for armor_type in armor.expanded_is_a:
                                        if armor_type in self.rdg_crit_rate_vs:
                                            vs_crit_rate = self.rdg_crit_rate_vs[armor_type]
                                            break
                                # 也检查护甲的直接is_a
                                elif hasattr(armor, 'is_a'):
                                    for armor_type in armor.is_a:
                                        if armor_type in self.rdg_crit_rate_vs:
                                            vs_crit_rate = self.rdg_crit_rate_vs[armor_type]
                                            break

                        # 计算最终暴击率 = 基础暴击率 + 针对特定单位暴击率
                        crit_rate = base_crit_rate + vs_crit_rate

                        # 获取目标的抗暴击几率
                        target_crit_resist = 0

                        # 获取目标的基础抗暴击几率
                        base_crit_resist = getattr(target, 'mdf_crit_rate', 0) if is_melee else getattr(target,
                                                                                                        'rdf_crit_rate',
                                                                                                        0)

                        # 获取目标对特定单位类型的抗暴击几率
                        specific_crit_resist = 0
                        if is_melee and hasattr(target, 'mdf_crit_rate_vs'):
                            # 先检查直接对攻击者单位类型的vs
                            if self.type_name in target.mdf_crit_rate_vs:
                                specific_crit_resist = target.mdf_crit_rate_vs[self.type_name]
                            # 检查对攻击者继承类型的vs
                            elif hasattr(self, 'expanded_is_a'):
                                for t in self.expanded_is_a:
                                    if t in target.mdf_crit_rate_vs:
                                        specific_crit_resist = target.mdf_crit_rate_vs[t]
                                        break
                            # 检查对攻击者武器类型的vs
                            elif hasattr(self, 'get_current_weapon_name'):
                                weapon_name = self.get_current_weapon_name()
                                if weapon_name and weapon_name in target.mdf_crit_rate_vs:
                                    specific_crit_resist = target.mdf_crit_rate_vs[weapon_name]
                            # 检查对攻击者武器继承类型的vs
                            elif hasattr(self, '_weapon_instances') and hasattr(self, 'current_weapon'):
                                weapon_name = self.current_weapon
                                if weapon_name and weapon_name in self._weapon_instances:
                                    weapon = self._weapon_instances[weapon_name]
                                    if hasattr(weapon, 'expanded_is_a'):
                                        for weapon_type in weapon.expanded_is_a:
                                            if weapon_type in target.mdf_crit_rate_vs:
                                                specific_crit_resist = target.mdf_crit_rate_vs[weapon_type]
                                                break
                                    # 也检查武器的直接is_a
                                    elif hasattr(weapon, 'is_a'):
                                        for weapon_type in weapon.is_a:
                                            if weapon_type in target.mdf_crit_rate_vs:
                                                specific_crit_resist = target.mdf_crit_rate_vs[weapon_type]
                                                break
                        elif not is_melee and hasattr(target, 'rdf_crit_rate_vs'):
                            # 先检查直接对攻击者单位类型的vs
                            if self.type_name in target.rdf_crit_rate_vs:
                                specific_crit_resist = target.rdf_crit_rate_vs[self.type_name]
                            # 检查对攻击者继承类型的vs
                            elif hasattr(self, 'expanded_is_a'):
                                for t in self.expanded_is_a:
                                    if t in target.rdf_crit_rate_vs:
                                        specific_crit_resist = target.rdf_crit_rate_vs[t]
                                        break
                            # 检查对攻击者武器类型的vs
                            elif hasattr(self, 'get_current_weapon_name'):
                                weapon_name = self.get_current_weapon_name()
                                if weapon_name and weapon_name in target.rdf_crit_rate_vs:
                                    specific_crit_resist = target.rdf_crit_rate_vs[weapon_name]
                            # 检查对攻击者武器继承类型的vs
                            elif hasattr(self, '_weapon_instances') and hasattr(self, 'current_weapon'):
                                weapon_name = self.current_weapon
                                if weapon_name and weapon_name in self._weapon_instances:
                                    weapon = self._weapon_instances[weapon_name]
                                    if hasattr(weapon, 'expanded_is_a'):
                                        for weapon_type in weapon.expanded_is_a:
                                            if weapon_type in target.rdf_crit_rate_vs:
                                                specific_crit_resist = target.rdf_crit_rate_vs[weapon_type]
                                                break
                                    # 也检查武器的直接is_a
                                    elif hasattr(weapon, 'is_a'):
                                        for weapon_type in weapon.is_a:
                                            if weapon_type in target.rdf_crit_rate_vs:
                                                specific_crit_resist = target.rdf_crit_rate_vs[weapon_type]
                                                break

                        # 计算最终的抗暴击几率 = 基础抗暴击几率 + 特定抗暴击几率
                        target_crit_resist = base_crit_resist + specific_crit_resist

                        # 计算最终的暴击几率（攻击者暴击几率减去目标抗暴击几率）
                        final_crit_rate = max(0, crit_rate - target_crit_resist)

                        # 判断是否触发暴击（使用修正后的暴击几率）
                        if final_crit_rate > 0 and self.world.random.randint(1, 100) <= final_crit_rate:
                            # 获取基础暴击倍率
                            base_crit_multiplier = self.mdg_crit if is_melee else self.rdg_crit

                            # 获取针对特定单位类型的暴击倍率
                            vs_crit_multiplier = 0
                            if is_melee and hasattr(self, 'mdg_crit_vs'):
                                # 先检查直接对单位类型的vs
                                if target.type_name in self.mdg_crit_vs:
                                    vs_crit_multiplier = self.mdg_crit_vs[target.type_name]
                                # 检查对单位继承类型的vs
                                elif hasattr(target, 'expanded_is_a'):
                                    for t in target.expanded_is_a:
                                        if t in self.mdg_crit_vs:
                                            vs_crit_multiplier = self.mdg_crit_vs[t]
                                            break
                                # 检查对目标护甲类型的vs
                                elif hasattr(target, 'get_current_armor_name'):
                                    armor_name = target.get_current_armor_name()
                                    if armor_name and armor_name in self.mdg_crit_vs:
                                        vs_crit_multiplier = self.mdg_crit_vs[armor_name]
                                # 检查对目标护甲继承类型的vs
                                elif hasattr(target, '_armor_instance') and target._armor_instance:
                                    armor = target._armor_instance
                                    if hasattr(armor, 'expanded_is_a'):
                                        for armor_type in armor.expanded_is_a:
                                            if armor_type in self.mdg_crit_vs:
                                                vs_crit_multiplier = self.mdg_crit_vs[armor_type]
                                                break
                                    # 也检查护甲的直接is_a
                                    elif hasattr(armor, 'is_a'):
                                        for armor_type in armor.is_a:
                                            if armor_type in self.mdg_crit_vs:
                                                vs_crit_multiplier = self.mdg_crit_vs[armor_type]
                                                break
                            elif not is_melee and hasattr(self, 'rdg_crit_vs'):
                                # 先检查直接对单位类型的vs
                                if target.type_name in self.rdg_crit_vs:
                                    vs_crit_multiplier = self.rdg_crit_vs[target.type_name]
                                # 检查对单位继承类型的vs
                                elif hasattr(target, 'expanded_is_a'):
                                    for t in target.expanded_is_a:
                                        if t in self.rdg_crit_vs:
                                            vs_crit_multiplier = self.rdg_crit_vs[t]
                                            break
                                # 检查对目标护甲类型的vs
                                elif hasattr(target, 'get_current_armor_name'):
                                    armor_name = target.get_current_armor_name()
                                    if armor_name and armor_name in self.rdg_crit_vs:
                                        vs_crit_multiplier = self.rdg_crit_vs[armor_name]
                                # 检查对目标护甲继承类型的vs
                                elif hasattr(target, '_armor_instance') and target._armor_instance:
                                    armor = target._armor_instance
                                    if hasattr(armor, 'expanded_is_a'):
                                        for armor_type in armor.expanded_is_a:
                                            if armor_type in self.rdg_crit_vs:
                                                vs_crit_multiplier = self.rdg_crit_vs[armor_type]
                                                break
                                    # 也检查护甲的直接is_a
                                    elif hasattr(armor, 'is_a'):
                                        for armor_type in armor.is_a:
                                            if armor_type in self.rdg_crit_vs:
                                                vs_crit_multiplier = self.rdg_crit_vs[armor_type]
                                                break

                            # 计算最终暴击倍率 = 基础暴击倍率 + 针对特定单位暴击倍率
                            crit_multiplier = base_crit_multiplier + vs_crit_multiplier

                            # 如果暴击倍率大于0，计算暴击伤害
                            if crit_multiplier > 0:
                                # 将暴击倍率统一处理为实际倍率（除以1000）
                                actual_multiplier = crit_multiplier / 1000
                                crit_damage = int(damage * actual_multiplier)

                                # 调试输出
                                used_multiplier_type = "特定单位类型" if vs_crit_multiplier > 0 else "基础"

                                is_crit = True

                                # 发送暴击通知
                                self.notify(f"critical_hit,{1 if is_melee else 0},{target.type_name}")

                                # 通知游戏系统暴击事件 (用于声音、特效等)
                                self.notify(f"unit_crit,{self.id},{target.id},{crit_damage}")

                    # 处理自爆伤害
                    if is_exploding_unit:
                        # 计算自爆伤害 (自爆伤害为扣除自身血量的百分比)
                        explode_exp_hp_cost = int(self.hp_max * self.exp_hp_cost / 100)

                        # 直接扣除自身血量
                        self.hp -= explode_exp_hp_cost

                        # 发送自爆通知
                        attack_type_str = "近战" if is_melee else "远程"

                        # 检查是否是针对特定单位的自爆
                        explode_vs_info = ""
                        if is_melee and target.type_name in self.mdg_explode_vs:
                            explode_vs_info = f"(针对{target.type_name}的特定自爆)"
                        elif not is_melee and target.type_name in self.rdg_explode_vs:
                            explode_vs_info = f"(针对{target.type_name}的特定自爆)"

                        self.notify(f"explode,{1 if is_melee else 0}")

                        # 播放自爆音效/动画
                        self.notify(f"explode_effect,{self.type_name},{self.id},{target.id}")

                        # 如果血量降至0或以下，安排单位死亡
                        if self.hp <= 0:
                            # 安排在攻击结束后死亡，避免影响当前攻击流程
                            self.world.schedule_after(10, lambda: self.die(None))

                    # 如果命中目标，则应用伤害
                    if is_hit:
                        # 使用最终伤害（可能是暴击伤害）
                        final_damage = crit_damage

                        # 如果是自爆单位，加入额外爆炸伤害系数
                        if is_exploding_unit:
                            # 加入基础爆炸伤害系数
                            if hasattr(self, 'exp_dgf'):
                                final_damage += self.exp_dgf

                            # 检查是否有针对目标类型的额外爆炸伤害系数
                            if hasattr(self, 'exp_dgf_vs') and target.type_name in self.exp_dgf_vs:
                                final_damage += self.exp_dgf_vs[target.type_name]
                            elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'expanded_is_a'):
                                # 检查继承类型
                                for t in target.expanded_is_a:
                                    if t in self.exp_dgf_vs:
                                        final_damage += self.exp_dgf_vs[t]
                                        break
                            # 检查对目标护甲类型的vs
                            elif hasattr(self, 'exp_dgf_vs') and hasattr(target, 'get_current_armor_name'):
                                armor_name = target.get_current_armor_name()
                                if armor_name and armor_name in self.exp_dgf_vs:
                                    final_damage += self.exp_dgf_vs[armor_name]
                            # 检查对目标护甲继承类型的vs
                            elif hasattr(self, 'exp_dgf_vs') and hasattr(target, '_armor_instance') and target._armor_instance:
                                armor = target._armor_instance
                                if hasattr(armor, 'expanded_is_a'):
                                    for armor_type in armor.expanded_is_a:
                                        if armor_type in self.exp_dgf_vs:
                                            final_damage += self.exp_dgf_vs[armor_type]
                                            break
                                # 也检查护甲的直接is_a
                                elif hasattr(armor, 'is_a'):
                                    for armor_type in armor.is_a:
                                        if armor_type in self.exp_dgf_vs:
                                            final_damage += self.exp_dgf_vs[armor_type]
                                            break

                        damage_target = self._resolve_damage_target(target)
                        if damage_target is None:
                            return

                        # 将最终伤害应用到目标（透传 is_melee，避免目标端误判双攻击单位的攻击类型）
                        damage_target.receive_hit(final_damage, self, is_crit=is_crit, is_charge=False, is_melee=is_melee)
                        damage_target.apply_damage_over_time(is_melee=is_melee, base_damage=damage)

                        # 检查是否有对目标生效的buff
                        # 首先从当前武器的debuffs中触发
                        debuffs_to_check = []
                        
                        # 优先检查当前武器的debuffs
                        if (hasattr(self, 'current_weapon') and self.current_weapon and 
                            hasattr(self, '_weapon_instances') and self.current_weapon in self._weapon_instances):
                            current_weapon = self._weapon_instances[self.current_weapon]
                            if hasattr(current_weapon, 'debuffs') and current_weapon.debuffs:
                                debuffs_to_check.extend(current_weapon.debuffs)
                        
                        # 然后检查单位自身的debuffs（避免重复）
                        if hasattr(self, 'debuffs') and self.debuffs:
                            for debuff in self.debuffs:
                                if debuff not in debuffs_to_check:
                                    debuffs_to_check.append(debuff)

                        # 遍历所有可用的debuff，逐一检查触发率
                        for buff_name in debuffs_to_check:
                            # 获取buff类
                            buff_cls = self.world.unit_class(buff_name)
                            if buff_cls is None:
                                continue

                            # 获取buff自身的触发率
                            # 使用buff的触发率，根据攻击类型判断使用近战还是远程触发率
                            if is_melee:
                                trigger_rate = buff_cls.mdg_trigger_rate  # 近战触发率
                            else:
                                trigger_rate = buff_cls.rdg_trigger_rate  # 远程触发率

                            # 如果触发率大于0且随机数在触发率范围内，则应用buff
                            if trigger_rate > 0 and self.world.random.randint(1, 100) <= trigger_rate:
                                # 应用debuff效果给目标
                                target.add_buff(buff_name, self)
                                # 可以添加buff触发通知
                                self.notify(f"buff_triggered,{buff_name},{target.id}")

                    # 创建一个临时的目标对象用于溅射伤害计算（如果原目标已被杀死）
                    class TempTarget:
                        # Round 4: 与 Entity 对齐, is_an_enemy 等热路径直接 LOAD_ATTR
                        player = None

                        def __init__(self, place, x, y, type_name):
                            self.place = place
                            self.x = x
                            self.y = y
                            self.type_name = type_name
                            self.expanded_is_a = []

                    # 对于自爆单位，无论是否命中都触发溅射
                    # 对于非自爆单位，只有命中时才触发溅射
                    if is_exploding_unit or is_hit:
                        # 检查目标是否已死亡
                        if target.hp <= 0 and is_hit:  # 只有真正命中并杀死目标时才使用临时目标
                            # 如果目标已经死亡，使用之前保存的位置信息创建临时目标
                            temp_target = TempTarget(target_place, target_x, target_y, target_type_name)
                            # 使用临时目标进行溅射伤害计算
                            self.splash_aim(temp_target, is_melee=is_melee)
                        else:
                            # 目标未死亡或未命中但是自爆单位，使用原始目标位置进行溅射
                            self.splash_aim(target, is_melee=is_melee)

            # 检查是否需要立即执行
            if (is_melee and self.mdg_delay == 0) or (not is_melee and self.rdg_delay == 0):
                do_hit()
            else:
                # 加入延迟调度
                self.world.schedule_after(hit_time - self.world.time, do_hit)

        # 处理冷却时间
        total_sequence_time = base_delay + int((times - 1) * interval * 1000)
        self.world.schedule_after(total_sequence_time,
                                  lambda: self._set_attack_cooldown(is_melee, target))

# 重命名旧的DamageMixin为DamageMixin (完整功能)
class DamageMixin(DamageEffectsMixin):
    """
    完整的伤害处理Mixin，兼容现有代码
    """
    pass 