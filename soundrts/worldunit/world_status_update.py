from ..worldorders import ORDERS_DICT, BuildPhaseTwoOrder, GoOrder, RallyingPointOrder, UpgradeToOrder, ProducingOrder, StartProduceOrder, AutoProduceOrder, AutoCultivateOrder
from ..lib.nofloat import PRECISION, int_angle, int_cos_1000, int_distance, int_sin_1000, square_of_distance, to_int
from ..worldaction import Action, AttackAction, MoveAction, MoveXYAction
from .world_public_method import *
from ..worldentity import Entity
from ..world_siege_pack import tick_siege_pack

class CreatureStatusUpdate(Entity):
    _cached_inventory_hash = -1
    _cached_sorted_inventory = ()
    _cached_buffs_hash = -1
    _cached_sorted_buffs = ()

    def update(self):
        """更新单位状态"""
        self.x = int(self.x)
        self.y = int(self.y)
        '在每帧更新时检查并应用持续伤害'
        super().update()
        now = self.world.time
        if now < self.mdg_dot_end_time and self.mdg_dot_damage > 0:
            self.receive_hit(self.mdg_dot_damage, None, notify=False)
        if now < self.rdg_dot_end_time and self.rdg_dot_damage > 0:
            self.receive_hit(self.rdg_dot_damage, None, notify=False)

    def _update_cooldowns(self):
        for t, c in list(self._cooldowns.items()):
            if self.world.time >= c:
                del self._cooldowns[t]
                self.notify('cooldown_end,%s' % t.type_name)

    def regenerate(self):
        """生命和法力回复，支持自定义冷却时间和前摇"""
        current_time = self.world.time
        if self.hp_regen and self.hp < self.hp_max:
            if current_time >= self.hp_regen_next_time:
                hp_regen_ready = getattr(self, 'hp_regen_ready', 0)
                if hp_regen_ready > 0:
                    if current_time < self.hp_regen_prep_end_time:
                        return
                    if self.hp_regen_prep_end_time == 0:
                        self.hp_regen_prep_end_time = current_time + hp_regen_ready
                        return
                hp_regen_cd = getattr(self, 'hp_regen_cd', 0)
                if hp_regen_cd > 0:
                    regen_amount = self.hp_regen
                else:
                    regen_amount = self.hp_regen
                self.hp = min(self.hp_max, self.hp + regen_amount)
                if hp_regen_cd > 0:
                    self.hp_regen_next_time = current_time + hp_regen_cd
                self.hp_regen_prep_end_time = 0
        if self.mana_regen and self.mana < self.mana_max:
            if current_time >= self.mana_regen_next_time:
                mana_regen_ready = getattr(self, 'mana_regen_ready', 0)
                if mana_regen_ready > 0:
                    if current_time < self.mana_regen_prep_end_time:
                        return
                    if self.mana_regen_prep_end_time == 0:
                        self.mana_regen_prep_end_time = current_time + mana_regen_ready
                        return
                mana_regen_cd = getattr(self, 'mana_regen_cd', 0)
                if mana_regen_cd > 0:
                    regen_amount = self.mana_regen
                else:
                    regen_amount = self.mana_regen
                self.mana = min(self.mana_max, self.mana + regen_amount)
                if mana_regen_cd > 0:
                    self.mana_regen_next_time = current_time + mana_regen_cd
                self.mana_regen_prep_end_time = 0

    def slow_update(self):
        self.regenerate()
        if hasattr(self, 'resource_type') and self.resource_type and hasattr(self, 'resource_regen') and self.resource_regen and hasattr(self, 'resource_qty') and hasattr(self, 'resource_volume_max'):
            if getattr(self, 'is_a_building', False) and self.resource_volume_max > 0 and (self.resource_qty < self.resource_volume_max):
                self.resource_qty = min(self.resource_qty + self.resource_regen, self.resource_volume_max)
                self.notify(f'qty_update,{self.resource_qty}')
        if getattr(self, 'is_producing', False):
            self.update_production()
        elif not getattr(self, 'is_producing', False) and getattr(self, 'is_gather', 0) == 1:
            production_mode = getattr(self, 'current_production_mode', None)
            is_auto_manual_both = False
            if getattr(self, 'auto_production', 0) == 1 and getattr(self, 'manual_production', 0) == 1 or (getattr(self, 'auto_cultivate', 0) == 1 and getattr(self, 'manual_cultivate', 0) == 1):
                is_auto_manual_both = True
                pass
            if production_mode == 'auto':
                user_manually_stopped = getattr(self, '_user_manually_stopped', False)
                if user_manually_stopped:
                    pass
                    return
                from ..world_extractor import depleted_production_qty_of, effective_resource_volume_max, is_extractor_source_depleted
                if is_extractor_source_depleted(self) and depleted_production_qty_of(self) <= 0:
                    pass
                    return
                resource_is_full = False
                vol_max = effective_resource_volume_max(self)
                if vol_max > 0 and hasattr(self, 'resource_qty') and (self.resource_qty >= vol_max):
                    resource_is_full = True
                    pass
                if not resource_is_full:
                    resource_depleted = vol_max > 0 and hasattr(self, 'resource_qty') and (self.resource_qty == 0)
                    should_restart = False
                    if getattr(self, 'auto_cultivate', 0) == 1:
                        should_restart = resource_depleted
                        if should_restart:
                            pass
                        else:
                            pass
                    elif getattr(self, 'auto_production', 0) == 1:
                        should_restart = resource_depleted or not is_auto_manual_both
                    if should_restart:
                        temp_order = StartProduceOrder(self, [])
                        production_cost = temp_order._calculate_production_cost()
                        result = self.check_if_enough_resources(production_cost, 0)
                        if result is None:
                            if getattr(self, 'auto_production', 0) == 1:
                                pass
                                temp_order = AutoProduceOrder(self, [])
                                temp_order.immediate_action()
                            elif getattr(self, 'auto_cultivate', 0) == 1:
                                pass
                                temp_order = AutoCultivateOrder(self, [])
                                temp_order.immediate_action()
                        else:
                            pass
                            if hasattr(self, 'notify'):
                                self.notify(f'auto_production_blocked,{result}')
            elif production_mode is None:
                pass
        if self.time_limit is not None and self.place.world.time >= self.time_limit:
            self.on_disappear()

    def update_production(self):
        """更新资源生产进度"""
        if not hasattr(self, 'is_producing') or not self.is_producing:
            pass
            return
        if getattr(self, 'production_time', 0) <= 0:
            pass
            return
        progress_per_second = 1
        old_progress = self.production_progress
        self.production_progress += progress_per_second
        progress_percent = int(self.production_progress * 100 / self.production_time)
        pass
        self._notify_production_completeness()
        if self.production_progress >= self.production_time:
            pass
            self.complete_production()

    def _notify_production_completeness(self):
        """通知生产进度，与ProductionOrder._notify_completeness逻辑一致"""
        if getattr(self, 'production_time', 0) == 0:
            return
        c = int(self.production_progress * 10 / self.production_time)
        if c > 10:
            c = 10
        if not hasattr(self, '_previous_completeness'):
            self._previous_completeness = None
        if c != self._previous_completeness:
            pass
            self.notify('completeness,%s' % c)
            self._previous_completeness = c

    @staticmethod
    def _normalize_production_item_name(raw):
        if isinstance(raw, (list, tuple)):
            return raw[0] if raw else None
        return raw

    def _spawn_production_items(self, item_type_name, count):
        """在建筑旁生成可拾取物品。"""
        from ..worlditem import Item
        item_cls = self.world.unit_class(item_type_name)
        if item_cls is None or not issubclass(item_cls, Item):
            pass
            return 0
        place = self.place
        spawned = 0
        for i in range(max(1, int(count))):
            offset_x = (i % 3 - 1) * 100 + 1000
            offset_y = i // 3 * 100
            item_cls(place, self.x + offset_x, self.y + offset_y)
            spawned += 1
        return spawned

    def complete_production(self):
        """完成资源生产"""
        from ..worldorders import ProducingOrder, StartProduceOrder
        if not self.player:
            pass
            return
        production_item = self._normalize_production_item_name(getattr(self, 'production_item', None))
        if production_item:
            item_count = max(1, int(getattr(self, 'production_qty', 1) or 1))
            spawned = self._spawn_production_items(production_item, item_count)
            pass
            self.notify(f'produced_item,{production_item},{spawned}')
        else:
            resource_type = getattr(self, 'production_type', None)
            if resource_type is None:
                resource_type = 'resource1'
            production_qty = getattr(self, 'production_qty', 0)
            if getattr(self, 'is_an_extractor', 0):
                from ..world_extractor import apply_extractor_production
                production_qty = apply_extractor_production(self, production_qty)
            production_qty *= 1000
            pass
            if production_qty > 0 and getattr(self, 'is_gather', 0) == 1:
                if hasattr(self, 'resource_volume_max') and self.resource_volume_max > 0:
                    if not hasattr(self, 'resource_qty'):
                        self.resource_qty = 0
                    if not hasattr(self, 'resource_type') or self.resource_type is None:
                        self.resource_type = resource_type
                    from ..world_extractor import effective_resource_volume_max
                    vol_max = effective_resource_volume_max(self)
                    add_qty = production_qty // 1000
                    self.resource_qty = min(self.resource_qty + add_qty, vol_max)
                    pass
                    self.notify(f'qty_update,{self.resource_qty}')
                    self.notify('gathered_produced_%s,%s' % (resource_type.replace('resource', ''), production_qty))
                else:
                    pass
                    before_resources = self.player.resources[:]
                    self.player.store(resource_type, production_qty)
                    after_resources = self.player.resources[:]
                    pass
                    self.notify('produced_%s,%s' % (resource_type.replace('resource', ''), production_qty))
            elif production_qty > 0:
                before_resources = self.player.resources[:]
                self.player.store(resource_type, production_qty)
                after_resources = self.player.resources[:]
                pass
                self.notify('produced_%s,%s' % (resource_type.replace('resource', ''), production_qty))
            elif getattr(self, 'is_an_extractor', 0):
                pass
        for player in self.player.world.players:
            if player is self.player:
                player.send_event(self, 'resource_complete')
        production_mode = getattr(self, 'current_production_mode', None)
        if production_mode == 'manual':
            self.is_producing = False
            self.production_progress = 0
            self._previous_completeness = None
            for i, order in enumerate(self.orders[:]):
                if isinstance(order, ProducingOrder):
                    self.orders.pop(i)
                    break
            pass
        elif production_mode == 'auto' or (production_mode is None and getattr(self, 'manual_production', 0) != 1):
            is_gather_mode = getattr(self, 'is_gather', 0) == 1
            resource_is_full = False
            if is_gather_mode:
                from ..world_extractor import depleted_production_qty_of, effective_resource_volume_max, is_extractor_source_depleted
                vol_max = effective_resource_volume_max(self)
                if vol_max > 0 and hasattr(self, 'resource_qty') and (self.resource_qty >= vol_max):
                    resource_is_full = True
                    is_auto_manual_both = False
                    if getattr(self, 'auto_production', 0) == 1 and getattr(self, 'manual_production', 0) == 1 or (getattr(self, 'auto_cultivate', 0) == 1 and getattr(self, 'manual_cultivate', 0) == 1):
                        is_auto_manual_both = True
                        pass
                    pass
                    self.is_producing = False
                    self.production_progress = 0
                    self._previous_completeness = None
                    for i, order in enumerate(self.orders[:]):
                        if isinstance(order, ProducingOrder):
                            self.orders.pop(i)
                            break
                    return
                if is_extractor_source_depleted(self) and depleted_production_qty_of(self) <= 0:
                    self.is_producing = False
                    self.production_progress = 0
                    self._previous_completeness = None
                    for i, order in enumerate(self.orders[:]):
                        if isinstance(order, ProducingOrder):
                            self.orders.pop(i)
                            break
                    pass
                    return
            temp_order = StartProduceOrder(self, [])
            production_cost = temp_order._calculate_production_cost()
            result = self.check_if_enough_resources(production_cost, 0)
            if result is None:
                self.player.pay(production_cost)
                self.production_progress = 0
                self._previous_completeness = None
                pass
                has_producing_order = False
                for order in self.orders:
                    if isinstance(order, ProducingOrder):
                        has_producing_order = True
                        break
                if not has_producing_order:
                    producing_order = ProducingOrder(self, [])
                    self.orders.insert(0, producing_order)
                self.notify('order_ok')
            else:
                self.is_producing = False
                self.production_progress = 0
                self._previous_completeness = None
                pass
                for i, order in enumerate(self.orders[:]):
                    if isinstance(order, ProducingOrder):
                        self.orders.pop(i)
                        break
                self.notify(result)
        else:
            self.is_producing = False
            self.production_progress = 0
            self._previous_completeness = None
            for i, order in enumerate(self.orders[:]):
                if isinstance(order, ProducingOrder):
                    self.orders.pop(i)
                    break
            pass

    def apply_damage_over_time(self, is_melee: bool, base_damage: int):
        """应用持续伤害效果"""
        now = self.world.time
        if is_melee and self.mdg_status_duration > 0:
            self.mdg_dot_end_time = now + int(self.mdg_status_duration * 1000)
            self.mdg_dot_damage = base_damage // 4
        elif not is_melee and self.rdg_status_duration > 0:
            self.rdg_dot_end_time = now + int(self.rdg_status_duration * 1000)
            self.rdg_dot_damage = base_damage // 4

    def update(self):
        if self.player is None:
            return
        inventory = self.inventory
        if inventory:
            inventory_hash = hash(tuple((i.id for i in inventory)))
            if self._cached_inventory_hash != inventory_hash:
                self._cached_sorted_inventory = sorted(inventory, key=lambda i: i.id)
                self._cached_inventory_hash = inventory_hash
            for i in self._cached_sorted_inventory:
                update_inv = getattr(i, 'update_in_inventory', None)
                if update_inv is not None:
                    update_inv(self)
        buffs = self._buffs
        if buffs:
            buffs_hash = hash(tuple((b.type_name for b in buffs)))
            if self._cached_buffs_hash != buffs_hash:
                self._cached_sorted_buffs = sorted(buffs, key=lambda b: b.type_name)
                self._cached_buffs_hash = buffs_hash
            for b in self._cached_sorted_buffs:
                if b.should_stop():
                    b.stop(self)
                    self._buffs.remove(b)
                else:
                    b.update(self)
                    if self.is_dead:
                        return
        if self._cooldowns:
            self._update_cooldowns()
        self.is_moving = False
        if self.packable or self.unpack_time or self.pack_time:
            tick_siege_pack(self)
        if self.heal_level:
            self.heal_nearby_units()
        if self.harm_level:
            self.harm_nearby_units()
        if self.inside:
            self.inside.update()
        if self.player is None:
            return
        if self.claimable or self.herdable:
            owner = self.player
            if owner is not None and getattr(owner, 'neutral', False):
                self._try_auto_claim()
            elif owner is not None:
                self._try_steal_owned_herdable()
            if self.player is None:
                return
        if self.herdable and self._herd_leader is not None:
            self._maintain_herd_follow()
        if self.action:
            self.action.update()
        if self.player is None:
            return
        if self.has_imperative_orders():
            self._execute_orders()
        else:
            if self.world.time >= self._next_decide_time or self.last_attacker is not None:
                self.decide()
            if not self._is_attacking() and self.orders:
                self._execute_orders()

    def has_imperative_orders(self):
        return self.orders and self.orders[0].is_imperative

    def _execute_orders(self):
        queue = self.orders
        while queue and (queue[0].is_complete or queue[0].is_impossible):
            queue.pop(0)
        if not queue:
            return
        queue[0].update()

    def _is_attacking(self):
        return isinstance(self.action, AttackAction)

    def _claim_range_ok(self, obj, claim_range):
        place = self.place
        if claim_range > 0:
            from ..lib.nofloat import square_of_distance
            reach = claim_range
            try:
                reach += int(getattr(self, 'radius', 0) or 0)
            except (TypeError, ValueError):
                pass
            try:
                reach += int(getattr(obj, 'radius', 0) or 0)
            except (TypeError, ValueError):
                pass
            return square_of_distance(self.x, self.y, obj.x, obj.y) <= reach * reach
        return getattr(obj, 'place', None) is place

    def _claim_range_value(self):
        claim_range = getattr(self, 'claim_range', None)
        if claim_range is None:
            claim_range = getattr(type(self), 'claim_range', 0)
        try:
            return int(claim_range[0] if isinstance(claim_range, list) else claim_range)
        except (TypeError, ValueError):
            return 0

    def _iter_claim_candidates(self, claim_range):
        place = self.place
        if place is None:
            return
        seen = set()
        for obj in list(getattr(place, 'objects', ()) or ()):
            if obj is self or id(obj) in seen:
                continue
            seen.add(id(obj))
            yield obj
        if claim_range > 0:
            for nb in getattr(place, 'neighbors', ()) or ():
                for obj in list(getattr(nb, 'objects', ()) or ()):
                    if obj is self or id(obj) in seen:
                        continue
                    seen.add(id(obj))
                    yield obj

    def _finish_herd_claim(self, claimer):
        p = getattr(claimer, 'player', None)
        self.set_player(p)
        self.flee_on_hit = 0
        skills = getattr(claimer, 'basic_skills', None) or getattr(claimer, '_basic_skills', ()) or ()
        if 'herd' in skills and getattr(type(self), 'herdable', 0):
            from ..worldorders.movement import _attach_herd
            _attach_herd(self, claimer)
        animal_type = getattr(self, 'type_name', None) or getattr(type(self), 'type_name', None) or getattr(type(self), '__name__', '')
        try:
            claimer.notify(f'claim_ok,{animal_type}')
        except Exception:
            pass
        return True

    def _try_auto_claim(self):
        """Neutral ``claimable`` animals join a non-neutral player on proximity (AoE2 sheep)."""
        raw = getattr(self, 'claimable', None)
        if raw is None:
            raw = getattr(type(self), 'claimable', 0)
        if raw not in (1, '1', True) and (not (isinstance(raw, list) and raw and (str(raw[0]) in ('1', 'true', 'True')))):
            return False
        owner = self.player
        if owner is None or not getattr(owner, 'neutral', False):
            return False
        if self.place is None or getattr(self, 'hp', 0) <= 0:
            return False
        claim_range = self._claim_range_value()
        for obj in self._iter_claim_candidates(claim_range):
            if getattr(obj, 'hp', 0) <= 0:
                continue
            if getattr(obj, 'inside', None) is not None:
                continue
            p = getattr(obj, 'player', None)
            if p is None or p is owner or getattr(p, 'neutral', False):
                continue
            if not self._claim_range_ok(obj, claim_range):
                continue
            return self._finish_herd_claim(obj)
        return False

    def _player_in_group(self, player, owner):
        if player is owner:
            return True
        for ally in getattr(owner, 'allied', None) or ():
            if ally is player:
                return True
        return False

    def _owner_guard_nearby(self, owner, claim_range):
        """True if a living non-building unit allied to ``owner`` stands by the animal."""
        for obj in self._iter_claim_candidates(claim_range):
            if getattr(obj, 'hp', 0) <= 0:
                continue
            if getattr(obj, 'is_a_building', False):
                continue
            if getattr(obj, 'inside', None) is not None:
                continue
            if getattr(obj, 'herdable', 0) or getattr(obj, 'claimable', 0):
                continue
            p = getattr(obj, 'player', None)
            if p is None or not self._player_in_group(p, owner):
                continue
            if not self._claim_range_ok(obj, claim_range):
                continue
            return True
        return False

    def _try_steal_owned_herdable(self):
        """Steal enemy-owned herdables. Race flags decide guarded / protected flocks."""
        from ..world_civ_bonuses import herdable_steal_ignore_guards, herdable_steal_protected
        if not (getattr(type(self), 'claimable', 0) or getattr(type(self), 'herdable', 0)):
            return False
        owner = self.player
        if owner is None or getattr(owner, 'neutral', False):
            return False
        if self.place is None or getattr(self, 'hp', 0) <= 0:
            return False
        claim_range = self._claim_range_value()
        guarded = self._owner_guard_nearby(owner, claim_range)
        protected = bool(herdable_steal_protected(owner))
        for obj in self._iter_claim_candidates(claim_range):
            if getattr(obj, 'hp', 0) <= 0:
                continue
            if getattr(obj, 'inside', None) is not None:
                continue
            if getattr(obj, 'is_a_building', False):
                continue
            p = getattr(obj, 'player', None)
            if p is None or p is owner or getattr(p, 'neutral', False):
                continue
            if self._player_in_group(owner, p):
                continue
            if not self._claim_range_ok(obj, claim_range):
                continue
            if guarded and (protected or not herdable_steal_ignore_guards(p)):
                continue
            return self._finish_herd_claim(obj)
        return False
    pass

    def _raise_subsquare_threat(self, delta):
        player = self.player
        if player is None:
            return
        subsquare = self.world.get_subsquare_id_from_xy(self.x, self.y)
        for p in player.allied_vision:
            if p in player.allied:
                p.raise_threat(subsquare, delta)

    def _apply_single_buff(self, name, author, target):
        """对单个目标应用buff的内部方法"""
        cls = self.world.unit_class(name)
        if cls is None:
            return False
        if not hasattr(cls, 'target_type') or cls.target_type is None:
            return False
        from .world_public_method import has_target_type
        if has_target_type(target, cls.target_type):
            if cls.stack:
                n = cls.stack
                for b in target._buffs:
                    if isinstance(b, cls):
                        b.renew()
                        n -= 1
                        if n == 0:
                            return True
            else:
                for b in target._buffs:
                    if isinstance(b, cls):
                        return True
            target._buffs.append(cls(author, target))
            return True
        return False

    def add_buff(self, name, author):
        """给单位或范围内的单位添加buff"""
        cls = self.world.unit_class(name)
        if cls is None:
            return
        buff_radius = getattr(cls, 'buff_radius', 0)
        if buff_radius > 0:
            from ..lib.nofloat import square_of_distance
            from .world_public_method import has_target_type
            if not hasattr(self, '_buffs'):
                self._buffs = []
            nearby_units = self.world.get_objects2(self.x, self.y, buff_radius, filter=lambda unit: hasattr(unit, '_buffs') and unit.is_vulnerable and (unit.place is not None) and (unit.hp > 0), skip_cache=True)
            applied_count = 0
            for unit in nearby_units:
                if self._apply_single_buff(name, author, unit):
                    applied_count += 1
            if applied_count > 0:
                try:
                    from ..lib.log import debug
                    debug(f'范围buff {name} 被应用到 {applied_count} 个单位，半径: {buff_radius}')
                except:
                    pass
        else:
            if not hasattr(self, '_buffs'):
                self._buffs = []
            self._apply_single_buff(name, author, self)

    def apply_damage(self, damage, attacker):
        if not self.is_dead:
            self.hp -= damage
            if self.is_dead:
                self.die(attacker)

    def _notify_guard_units(self, attacker):
        """通知警戒模式的友军单位"""
        self._notify_units_in_place(self.place, attacker)
        for neighbor in self.place.neighbors:
            self._notify_units_in_place(neighbor, attacker)

    def delete(self):
        Entity.delete(self)
        self.set_player(None)

    def increase_xp(self, xp):
        self.xp += xp
        self.xp_reward += xp * self.xp_reward_per_xp // PRECISION
        if self.level < self.max_level and self.xp_thresholds and (self.level <= len(self.xp_thresholds)) and (self.xp >= self.xp_thresholds[max(0, self.level - 1)]):
            self.level += 1
            from ..level_up_stats import apply_level_stat_bonuses
            apply_level_stat_bonuses(self)
            if getattr(self, 'level_up_reset_xp', 0):
                self.xp = 0
            self._unlock_level_skills(self.level, notify=True)
            self.notify(f'level_up,{self.type_name},{self.id},{self.level}')

    def claim_rewards(self, target):
        if target.xp_reward:
            if self.player is not None and target.player is not None and (not self.player.player_is_an_enemy(target.player)):
                return
            allied = self.player.allied if self.player is not None else []
            if self.last_player is not None:
                allied = self.last_player.allied
            places = [target.place]
            if hasattr(target.place, 'strict_neighbors'):
                places.extend(target.place.strict_neighbors)
            units = [o for p in places for o in p.objects if o.player in allied and hasattr(o, 'xp_thresholds') and o.xp_thresholds]
            if units:
                xp = target.xp_reward / len(units)
                for u in units:
                    u.increase_xp(xp)

    def on_disappear(self):
        """当召唤单位时间到期消失时调用"""
        if getattr(self, '_disappeared', False):
            return
        self._disappeared = True
        from ..worldplayerstats import uncount_expired_unit_produced
        uncount_expired_unit_produced(self)
        self.notify('disappear')
        self.delete()
    heal_level = 0
    heal_garrisoned = 0
    heal_next_time = 0
    harm_next_time = 0
    heal_prep_end_time = 0
    harm_prep_end_time = 0
    hp_regen_next_time = 0
    mana_regen_next_time = 0
    hp_regen_prep_end_time = 0
    mana_regen_prep_end_time = 0

    def heal_nearby_units(self):
        """治疗：附近范围 / 单体瞄准 / 仅载具内（``heal_garrisoned 1``）。"""
        current_time = self.world.time
        if current_time < self.heal_next_time:
            return
        if self.heal_ready > 0:
            if current_time < self.heal_prep_end_time:
                return
            if self.heal_prep_end_time == 0:
                self.heal_prep_end_time = current_time + self.heal_ready
                return
        heal_cd = getattr(self, 'heal_cd', 0)
        if heal_cd > 0:
            hp = self.heal_level * PRECISION
        else:
            hp = self.heal_level * PRECISION // 25
        heal_radius = getattr(self, 'heal_radius', 0)
        heal_range = getattr(self, 'heal_range', 0)
        if int(getattr(self, 'heal_garrisoned', 0) or 0):
            self._heal_garrisoned_units(hp)
        elif heal_range > 0:
            self._heal_targeted_unit(hp, heal_range)
        else:
            self._heal_area_units(hp, heal_radius)
        if heal_cd > 0:
            self.heal_next_time = current_time + heal_cd
        self.heal_prep_end_time = 0

    def _heal_garrisoned_units(self, hp):
        """Only heal units currently inside this unit's transport/shelter."""
        inside = getattr(self, 'inside', None)
        objects = getattr(inside, 'objects', None) if inside is not None else None
        if not objects:
            return
        for u in list(objects):
            if getattr(u, 'hp', 0) <= 0:
                continue
            if u.hp >= getattr(u, 'hp_max', 0):
                continue
            if not self._can_heal(u):
                continue
            u.hp = min(u.hp_max, u.hp + hp)

    def _heal_area_units(self, hp, radius):
        """范围治疗模式"""
        units = self.world.get_objects2(self.x, self.y, radius, filter=lambda x: x.hp < x.hp_max and self._can_heal(x))
        unique_units = []
        unit_ids = set()
        for u in units:
            if id(u) not in unit_ids:
                unique_units.append(u)
                unit_ids.add(id(u))
        for u in unique_units:
            u.hp = min(u.hp_max, u.hp + hp)

    def _heal_targeted_unit(self, hp, range_limit):
        """单体瞄准治疗模式"""
        from ..lib.nofloat import square_of_distance
        best_target = None
        best_distance = float('inf')
        search_radius = max(range_limit * 2, 10 * PRECISION)
        units = self.world.get_objects2(self.x, self.y, search_radius, filter=lambda x: x.hp < x.hp_max and self._can_heal(x))
        for u in units:
            distance = square_of_distance(self.x, self.y, u.x, u.y)
            max_distance = (range_limit + self.radius + u.radius) ** 2
            if distance <= max_distance and distance < best_distance:
                best_target = u
                best_distance = distance
        if best_target:
            best_target.hp = min(best_target.hp_max, best_target.hp + hp)
    heal_target_type = ()

    def _can_heal(self, other):
        """检查是否可以治疗目标单位"""
        if not getattr(other, 'is_healable', True):
            return False
        if hasattr(other, 'is_a_building') and other.is_a_building:
            return False
        if hasattr(other, 'player') and hasattr(self, 'player'):
            if self.player.player_is_an_enemy(other.player):
                return False
        if not self.heal_target_type:
            return True
        from .world_public_method import matches_heal_targets
        return matches_heal_targets(other, self.heal_target_type)
    harm_target_type = ()

    def _can_harm(self, other):
        if not self.harm_target_type:
            return True
        from .world_public_method import passes_harm_diplomacy_filter
        if not passes_harm_diplomacy_filter(self.harm_target_type, getattr(self, 'player', None), getattr(other, 'player', None)):
            return False
        if 'water' in self.harm_target_type:
            target_airground_type = getattr(other, 'airground_type', 'ground')
            if target_airground_type == 'water':
                return True
        return self.world.can_harm(self.type_name, other.type_name)

    def harm_nearby_units(self):
        """对周围单位造成伤害，支持自定义范围和冷却时间

        根据harm_target_type确定可以伤害的目标类型:
        - enemy / non_neutral: 只伤害非中立敌对玩家单位
        - neutral: 只伤害中立玩家单位
        - allied: 只伤害盟友
        - building: 只伤害建筑
        - unit: 只伤害单位
        - [unit_type_name]: 只伤害指定类型的单位

        如果没有设置harm_target_type，则伤害所有单位
        
        注意：此方法直接应用伤害，不经过攻击系统的复杂处理
        """
        current_time = self.world.time
        if current_time < self.harm_next_time:
            return
        if self.harm_ready > 0:
            if current_time < self.harm_prep_end_time:
                return
            if self.harm_prep_end_time == 0:
                self.harm_prep_end_time = current_time + self.harm_ready
                return
        harm_cd = getattr(self, 'harm_cd', 0)
        if harm_cd > 0:
            hp = self.harm_level * PRECISION
        else:
            hp = self.harm_level * PRECISION // 25
        harm_radius = getattr(self, 'harm_radius', 0)
        harm_range = getattr(self, 'harm_range', 0)
        if harm_range > 0:
            self._harm_targeted_unit(hp, harm_range)
        else:
            self._harm_area_units(hp, harm_radius)
        if harm_cd > 0:
            self.harm_next_time = current_time + harm_cd
        self.harm_prep_end_time = 0

    def _harm_area_units(self, hp, radius):
        """范围伤害模式"""
        units = self.world.get_objects2(self.x, self.y, radius, filter=lambda x: x.is_vulnerable and self._can_harm(x), skip_cache=True)
        unique_units = []
        unit_ids = set()
        for u in units:
            if id(u) not in unit_ids:
                unique_units.append(u)
                unit_ids.add(id(u))
        for u in unique_units:
            if u.player is None or u.hp <= 0:
                continue
            try:
                if getattr(self.world, 'treaty_until_time', 0) > 0 and self.world.time < self.world.treaty_until_time:
                    if hasattr(self, 'player') and hasattr(u, 'player') and self.player and u.player:
                        if u.player.player_is_an_enemy(self.player):
                            from ...worldplayerbase.base import is_wildlife_unit
                            if is_wildlife_unit(u) or is_wildlife_unit(self):
                                pass
                            else:
                                continue
            except Exception:
                pass
            if u.player:
                u.player.observe(self)
                u.last_attacker = self
            u.hp -= hp
            if u.hp <= 0:
                u.die(self)

    def _harm_targeted_unit(self, hp, range_limit):
        """单体瞄准伤害模式"""
        from ..lib.nofloat import square_of_distance
        best_target = None
        best_distance = float('inf')
        search_radius = max(range_limit * 2, 10 * PRECISION)
        units = self.world.get_objects2(self.x, self.y, search_radius, filter=lambda x: x.is_vulnerable and self._can_harm(x), skip_cache=True)
        for u in units:
            distance = square_of_distance(self.x, self.y, u.x, u.y)
            max_distance = (range_limit + self.radius + u.radius) ** 2
            if distance <= max_distance and distance < best_distance:
                best_target = u
                best_distance = distance
        if best_target:
            if best_target.player is None or best_target.hp <= 0:
                return
            try:
                if getattr(self.world, 'treaty_until_time', 0) > 0 and self.world.time < self.world.treaty_until_time:
                    if hasattr(self, 'player') and hasattr(best_target, 'player') and self.player and best_target.player:
                        if best_target.player.player_is_an_enemy(self.player):
                            from ...worldplayerbase.base import is_wildlife_unit
                            if is_wildlife_unit(best_target) or is_wildlife_unit(self):
                                pass
                            else:
                                return
            except Exception:
                pass
            if best_target.player:
                best_target.player.observe(self)
                best_target.last_attacker = self
            if getattr(best_target, '_has_yielded', False):
                return
            best_target.hp -= hp
            if best_target.hp <= 0:
                best_target.die(self)

    def can_be_captured(self):
        """检查单位是否可以被夺取"""
        return self.capture_hp_threshold > 0 and self.hp > 0 and (self.hp * 100 / self.hp_max <= self.capture_hp_threshold)