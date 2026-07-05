

def _terrain_modifier_from_list(terrain_type, terrain_list):
    from ..lib.square_terrain_rules import terrain_list_value

    value = terrain_list_value(terrain_type, terrain_list)
    if value is None:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0


class HitMissMixin:
    """
    处理命中与闪避相关的功能
    """
    def _get_dodge_on_terrain(self, is_melee=True) -> int:
        """获取当前地形上的闪避修正（0~100）"""
        terrain_type = self.place.type_name if self.place else None
        if not terrain_type:
            return 0

        if is_melee and hasattr(self, 'mdg_dodge_on_terrain') and self.mdg_dodge_on_terrain:
            return _terrain_modifier_from_list(terrain_type, self.mdg_dodge_on_terrain)
        elif not is_melee and hasattr(self, 'rdg_dodge_on_terrain') and self.rdg_dodge_on_terrain:
            return _terrain_modifier_from_list(terrain_type, self.rdg_dodge_on_terrain)
        return 0

    def _get_melee_cover_vs(self, target) -> int:
        """返回对目标的近战命中修正（0~100）"""
        # 获取基础命中率
        base_cover = self.mdg_cover // 1000 if self.mdg_cover else 100  # 默认100%命中

        # 获取对特定目标的命中修正
        specific_cover = 0

        # 先检查直接对单位类型的vs
        if target.type_name in self.mdg_cover_vs:
            specific_cover = self.mdg_cover_vs[target.type_name] // 1000  # vs值需要除以1000还原为0~100
        # 检查对单位继承类型的vs
        elif hasattr(target, 'expanded_is_a'):
            for t in target.expanded_is_a:
                if t in self.mdg_cover_vs:
                    specific_cover = self.mdg_cover_vs[t] // 1000  # vs值需要除以1000还原为0~100
                    break
        
        # 如果还没有找到，检查对目标护甲类型的vs
        if specific_cover == 0 and hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.mdg_cover_vs:
                specific_cover = self.mdg_cover_vs[armor_name] // 1000
        
        # 检查对目标护甲继承类型的vs
        if specific_cover == 0 and hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.mdg_cover_vs:
                        specific_cover = self.mdg_cover_vs[armor_type] // 1000
                        break
            # 也检查护甲的直接is_a
            if specific_cover == 0 and hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.mdg_cover_vs:
                        specific_cover = self.mdg_cover_vs[armor_type] // 1000
                        break

        # 返回基础命中率加上特定目标命中修正
        final_cover = base_cover + specific_cover

        # 限制在0-100范围内
        return max(0, min(100, final_cover))

    def _get_ranged_cover_vs(self, target) -> int:
        """返回对目标的远程命中修正（0~100）"""
        # 获取基础命中率
        base_cover = self.rdg_cover // 1000 if self.rdg_cover else 100  # 默认100%命中

        # 获取对特定目标的命中修正
        specific_cover = 0

        # 先检查直接对单位类型的vs
        if target.type_name in self.rdg_cover_vs:
            specific_cover = self.rdg_cover_vs[target.type_name] // 1000  # vs值需要除以1000还原为0~100
        # 检查对单位继承类型的vs
        elif hasattr(target, 'expanded_is_a'):
            for t in target.expanded_is_a:
                if t in self.rdg_cover_vs:
                    specific_cover = self.rdg_cover_vs[t] // 1000  # vs值需要除以1000还原为0~100
                    break
        
        # 如果还没有找到，检查对目标护甲类型的vs
        if specific_cover == 0 and hasattr(target, 'get_current_armor_name'):
            armor_name = target.get_current_armor_name()
            if armor_name and armor_name in self.rdg_cover_vs:
                specific_cover = self.rdg_cover_vs[armor_name] // 1000
        
        # 检查对目标护甲继承类型的vs
        if specific_cover == 0 and hasattr(target, '_armor_instance') and target._armor_instance:
            armor = target._armor_instance
            if hasattr(armor, 'expanded_is_a'):
                for armor_type in armor.expanded_is_a:
                    if armor_type in self.rdg_cover_vs:
                        specific_cover = self.rdg_cover_vs[armor_type] // 1000
                        break
            # 也检查护甲的直接is_a
            if specific_cover == 0 and hasattr(armor, 'is_a'):
                for armor_type in armor.is_a:
                    if armor_type in self.rdg_cover_vs:
                        specific_cover = self.rdg_cover_vs[armor_type] // 1000
                        break

        # 返回基础命中率加上特定目标命中修正
        final_cover = base_cover + specific_cover

        # 限制在0-100范围内
        return max(0, min(100, final_cover))

    def _get_dodge_vs(self, attacker, is_melee=True) -> int:
        """
        当对方来攻击我时，我的闪避率是多少？(0~100)
        """
        if is_melee:
            # 先检查直接对攻击者单位类型的vs
            if hasattr(self, 'mdg_dodge_vs') and hasattr(attacker, 'type_name') and attacker.type_name in self.mdg_dodge_vs:
                dodge_value = self.mdg_dodge_vs[attacker.type_name]
                # 如果值大于100，假定它是内部值(需要除以1000)
                if dodge_value > 100:
                    dodge_value = dodge_value // 1000
                return dodge_value

            # 检查对攻击者继承类型的vs
            if hasattr(self, 'mdg_dodge_vs') and hasattr(attacker, 'expanded_is_a'):
                for t in attacker.expanded_is_a:
                    if t in self.mdg_dodge_vs:
                        dodge_value = self.mdg_dodge_vs[t]
                        # 如果值大于100，假定它是内部值(需要除以1000)
                        if dodge_value > 100:
                            dodge_value = dodge_value // 1000
                        return dodge_value
            
            # 检查对攻击者武器类型的vs
            if hasattr(self, 'mdg_dodge_vs') and hasattr(attacker, 'get_current_weapon_name'):
                weapon_name = attacker.get_current_weapon_name()
                if weapon_name and weapon_name in self.mdg_dodge_vs:
                    dodge_value = self.mdg_dodge_vs[weapon_name]
                    if dodge_value > 100:
                        dodge_value = dodge_value // 1000
                    return dodge_value
            
            # 检查对攻击者武器继承类型的vs
            if hasattr(self, 'mdg_dodge_vs') and hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
                weapon_name = attacker.current_weapon
                if weapon_name and weapon_name in attacker._weapon_instances:
                    weapon = attacker._weapon_instances[weapon_name]
                    if hasattr(weapon, 'expanded_is_a'):
                        for weapon_type in weapon.expanded_is_a:
                            if weapon_type in self.mdg_dodge_vs:
                                dodge_value = self.mdg_dodge_vs[weapon_type]
                                if dodge_value > 100:
                                    dodge_value = dodge_value // 1000
                                return dodge_value
                    # 也检查武器的直接is_a
                    if hasattr(weapon, 'is_a'):
                        for weapon_type in weapon.is_a:
                            if weapon_type in self.mdg_dodge_vs:
                                dodge_value = self.mdg_dodge_vs[weapon_type]
                                if dodge_value > 100:
                                    dodge_value = dodge_value // 1000
                                return dodge_value

            # 默认值需要除以1000还原
            base_dodge = self.mdg_dodge // 1000 if hasattr(self, 'mdg_dodge') and self.mdg_dodge else 0
            return base_dodge
        else:
            # 先检查直接对攻击者单位类型的vs
            if hasattr(self, 'rdg_dodge_vs') and hasattr(attacker, 'type_name') and attacker.type_name in self.rdg_dodge_vs:
                dodge_value = self.rdg_dodge_vs[attacker.type_name]
                # 如果值大于100，假定它是内部值(需要除以1000)
                if dodge_value > 100:
                    dodge_value = dodge_value // 1000
                return dodge_value

            # 检查对攻击者继承类型的vs
            if hasattr(self, 'rdg_dodge_vs') and hasattr(attacker, 'expanded_is_a'):
                for t in attacker.expanded_is_a:
                    if t in self.rdg_dodge_vs:
                        dodge_value = self.rdg_dodge_vs[t]
                        # 如果值大于100，假定它是内部值(需要除以1000)
                        if dodge_value > 100:
                            dodge_value = dodge_value // 1000
                        return dodge_value
            
            # 检查对攻击者武器类型的vs
            if hasattr(self, 'rdg_dodge_vs') and hasattr(attacker, 'get_current_weapon_name'):
                weapon_name = attacker.get_current_weapon_name()
                if weapon_name and weapon_name in self.rdg_dodge_vs:
                    dodge_value = self.rdg_dodge_vs[weapon_name]
                    if dodge_value > 100:
                        dodge_value = dodge_value // 1000
                    return dodge_value
            
            # 检查对攻击者武器继承类型的vs
            if hasattr(self, 'rdg_dodge_vs') and hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
                weapon_name = attacker.current_weapon
                if weapon_name and weapon_name in attacker._weapon_instances:
                    weapon = attacker._weapon_instances[weapon_name]
                    if hasattr(weapon, 'expanded_is_a'):
                        for weapon_type in weapon.expanded_is_a:
                            if weapon_type in self.rdg_dodge_vs:
                                dodge_value = self.rdg_dodge_vs[weapon_type]
                                if dodge_value > 100:
                                    dodge_value = dodge_value // 1000
                                return dodge_value
                    # 也检查武器的直接is_a
                    if hasattr(weapon, 'is_a'):
                        for weapon_type in weapon.is_a:
                            if weapon_type in self.rdg_dodge_vs:
                                dodge_value = self.rdg_dodge_vs[weapon_type]
                                if dodge_value > 100:
                                    dodge_value = dodge_value // 1000
                                return dodge_value

            # 默认值需要除以1000还原
            base_dodge = self.rdg_dodge // 1000 if hasattr(self, 'rdg_dodge') and self.rdg_dodge else 0
            return base_dodge

    def _hit_or_miss(self, target):
        """命中判定

        返回值:
            bool: True表示命中，False表示未命中
        """
        # 预先判断是否为近战还是远程攻击
        is_melee = not (hasattr(self, 'rdg_range') and self.rdg_range > 0 and self.in_ranged_range(target))

        # 获取攻击者的基础命中修正（现在已包含基础命中+特定命中）
        cover = self._get_melee_cover_vs(target) if is_melee else self._get_ranged_cover_vs(target)

        # 应用地形修正 - 修改为将地形修正加到命中值，而不是替换
        terrain_type = None
        if target.place:
            if hasattr(target.place, "type_name_at"):
                terrain_type = target.place.type_name_at(target.x, target.y)
            else:
                terrain_type = target.place.type_name
        if terrain_type:
            terrain_modifier = 0

            if is_melee and hasattr(self, 'mdg_cover_on_terrain') and self.mdg_cover_on_terrain:
                terrain_modifier = _terrain_modifier_from_list(
                    terrain_type, self.mdg_cover_on_terrain
                )
            elif not is_melee and hasattr(self, 'rdg_cover_on_terrain') and self.rdg_cover_on_terrain:
                terrain_modifier = _terrain_modifier_from_list(
                    terrain_type, self.rdg_cover_on_terrain
                )

            # 将地形修正直接加到命中率上，而不是做百分比调整
            cover = cover + terrain_modifier

        # 获取目标在地形上的闪避修正
        target_dodge_on_terrain = target._get_dodge_on_terrain(is_melee)

        # 获取目标对攻击者的特定闪避修正
        target_dodge_vs = 0
        if is_melee and hasattr(target, 'mdg_dodge_vs'):
            if self.type_name in target.mdg_dodge_vs:
                target_dodge_vs = target.mdg_dodge_vs[self.type_name]
            elif hasattr(self, 'expanded_is_a'):
                for t in self.expanded_is_a:
                    if t in target.mdg_dodge_vs:
                        target_dodge_vs = target.mdg_dodge_vs[t]
                        break

            # 如果值大于100，假定它是内部值(需要除以1000)
            if target_dodge_vs > 100:
                target_dodge_vs = target_dodge_vs // 1000
        elif not is_melee and hasattr(target, 'rdg_dodge_vs'):
            if self.type_name in target.rdg_dodge_vs:
                target_dodge_vs = target.rdg_dodge_vs[self.type_name]
            elif hasattr(self, 'expanded_is_a'):
                for t in self.expanded_is_a:
                    if t in target.rdg_dodge_vs:
                        target_dodge_vs = target.rdg_dodge_vs[t]
                        break

            # 如果值大于100，假定它是内部值(需要除以1000)
            if target_dodge_vs > 100:
                target_dodge_vs = target_dodge_vs // 1000

        # 获取目标的基础闪避值
        base_dodge = target.mdg_dodge // 1000 if is_melee else target.rdg_dodge // 1000

        # 修改：计算最终闪避值为基础闪避 + 特定闪避 + 地形闪避
        total_dodge = base_dodge + target_dodge_vs + target_dodge_on_terrain

        # 计算最终命中率
        hit_chance = cover - total_dodge
        hit_chance = max(min(hit_chance, 100), 0)  # 限制在0-100范围内

        # 投掷随机数判定是否命中
        roll = self.world.random.randint(1, 100)
        result = roll <= hit_chance

        # 通知逻辑
        if result:
            return True  # 命中
        elif roll <= cover:
            # 命中修正范围内但被闪避，发送闪避通知
            target.notify(f"dodge,{self.type_name},{1 if is_melee else 0}")
        else:
            # 完全落空，发送未命中通知
            target.notify(f"missed,{self.type_name},{1 if is_melee else 0}")
        return False

    def chance_to_hit(self, target):
        """计算基础命中率(0~100)"""
        # 获取是否为近战攻击
        is_melee = self.in_melee_range(target)

        # 1. 获取基础命中率
        if is_melee:
            base_chance = self._get_melee_cover_vs(target)
        else:
            base_chance = self._get_ranged_cover_vs(target)

        # 2. 应用地形修正
        terrain_type = None
        if target.place:
            if hasattr(target.place, "type_name_at"):
                terrain_type = target.place.type_name_at(target.x, target.y)
            else:
                terrain_type = target.place.type_name
        if terrain_type:
            if is_melee and self.mdg_cover_on_terrain:
                terrain_modifier = _terrain_modifier_from_list(
                    terrain_type, self.mdg_cover_on_terrain
                )
                if terrain_modifier:
                    base_chance = base_chance * terrain_modifier // 100
            elif not is_melee and self.rdg_cover_on_terrain:
                terrain_modifier = _terrain_modifier_from_list(
                    terrain_type, self.rdg_cover_on_terrain
                )
                if terrain_modifier:
                    base_chance = base_chance * terrain_modifier // 100

        # 3. 处理高地修正
        attacker_high = (
            self.place.high_ground_at(self.x, self.y)
            if self.place is not None and hasattr(self.place, "high_ground_at")
            else getattr(self.place, "high_ground", False)
        )
        target_high = (
            target.place.high_ground_at(target.x, target.y)
            if target.place is not None and hasattr(target.place, "high_ground_at")
            else getattr(target.place, "high_ground", False)
        )
        high_ground = (
                not attacker_high
                and target_high
                and target.airground_type == "ground"
                and self.height < target.height
        )

        if high_ground:
            is_projectile = (is_melee and hasattr(self, 'mdg_projectile') and self.mdg_projectile) or \
                            (not is_melee and hasattr(self, 'rdg_projectile') and self.rdg_projectile)
            if is_projectile:
                base_chance //= 2  # 投射物攻击打高地命中率减半

        # 4. 处理地形掩护修正
        if not is_melee and target.place is not None:
            if hasattr(target.place, "terrain_cover_at"):
                terrain_cover = target.place.terrain_cover_at(target.x, target.y)
            else:
                terrain_cover = target.place.terrain_cover
            terrain_cover = terrain_cover[
                0 if target.airground_type != "air" else 1
            ]
            base_chance = base_chance * (100 - terrain_cover) // 100

        return base_chance

    def has_hit(self, target) -> bool:
        """
        判定是否命中：
          1) 攻击方 'chance_to_hit' 得到基础命中率 (0~100)
          2) 目标 'dodge' 得到闪避率 (0~100)
          3) 最终命中率 = 命中率 * (100 - dodge) / 100
          4) 随机掷 1~100 <= 最终命中率 => 命中，否则 Miss
        """
        return self._hit_or_miss(target) 