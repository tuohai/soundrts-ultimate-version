import os
import random

from ..lib.nofloat import int_distance as _int_distance, to_int
from ..worldaction import MoveAction

# 战斗算术热点的 Cython 加速器；不可用时回退纯 Python
_cf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import combat_fast as _cf  # type: ignore[no-redef]
    except ImportError:
        _cf = None


def _resolve_vs(vs_dict, type_name, expanded_is_a):
    """resolve_vs_lookup 的纯 Python fallback，签名与 _cf.resolve_vs_lookup 一致。"""
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


# 单一入口，根据 _cf 可用性自动切换实现
_vs_lookup = _cf.resolve_vs_lookup if _cf is not None else _resolve_vs


class DamageCalculationMixin:
    """
    处理基础伤害计算相关的功能
    """
    def _get_attacker_terrain_type(self):
        """返回攻击者当前所在格的地形类型名。"""
        place = self.place
        if not place:
            return None
        if hasattr(place, "type_name_at"):
            return place.type_name_at(self.x, self.y)
        return getattr(place, "type_name", None)

    def _get_on_terrain_modifier(self, terrain_list) -> int:
        """从 [地形, 修正, 地形, 修正, ...] 列表读取当前地形修正值。"""
        if not terrain_list:
            return 0
        terrain_type = self._get_attacker_terrain_type()
        if not terrain_type:
            return 0
        try:
            idx = terrain_list.index(terrain_type)
            if idx + 1 < len(terrain_list):
                return to_int(terrain_list[idx + 1])
        except (ValueError, IndexError, TypeError):
            pass
        return 0

    def _get_melee_damage_vs(self, target) -> int:
        """返回对 target 的近战基础伤害（含 vs 修正）.

        D-Phase 2 §3.2: 整个函数走 ``combat_fast.compute_damage_vs`` (cpdef),
        含 4 层 lookup (type_name / expanded_is_a / armor name / armor instance).
        Fallback 是 Python 等价实现 (见 ``_py_get_melee_damage_vs``).

        D-Phase 2: armor / _armor_instance 已上提到 Entity class default = None,
        直接属性访问替代 getattr (12.88M calls / 5min).
        """
        if _cf is not None:
            damage = _cf.compute_damage_vs(self.mdg, self.mdg_vs, target)
        else:
            damage = self._py_get_melee_damage_vs(target)
        terrain_mod = self._get_on_terrain_modifier(getattr(self, "mdg_on_terrain", ()))
        return max(0, damage + terrain_mod)

    def _py_get_melee_damage_vs(self, target) -> int:
        """Python fallback for _get_melee_damage_vs."""
        v = _vs_lookup(self.mdg_vs, target.type_name, target.expanded_is_a)
        if v is not None:
            return self.mdg + v

        mdg_vs = self.mdg_vs
        armor_name = target.armor
        if armor_name and armor_name in mdg_vs:
            return self.mdg + mdg_vs[armor_name]

        armor = target._armor_instance
        if armor is not None:
            for armor_type in armor.expanded_is_a:
                if armor_type in mdg_vs:
                    return self.mdg + mdg_vs[armor_type]
            for armor_type in armor.is_a:
                if armor_type in mdg_vs:
                    return self.mdg + mdg_vs[armor_type]

        return self.mdg

    def _get_ranged_damage_vs(self, target) -> int:
        """返回对 target 的远程基础伤害（含 vs 修正）.

        D-Phase 2 §3.2: 整个函数走 ``combat_fast.compute_damage_vs`` (cpdef).
        """
        if _cf is not None:
            damage = _cf.compute_damage_vs(self.rdg, self.rdg_vs, target)
        else:
            damage = self._py_get_ranged_damage_vs(target)
        terrain_mod = self._get_on_terrain_modifier(getattr(self, "rdg_on_terrain", ()))
        return max(0, damage + terrain_mod)

    def _py_get_ranged_damage_vs(self, target) -> int:
        """Python fallback for _get_ranged_damage_vs."""
        v = _vs_lookup(self.rdg_vs, target.type_name, target.expanded_is_a)
        if v is not None:
            return self.rdg + v

        rdg_vs = self.rdg_vs
        armor_name = target.armor
        if armor_name and armor_name in rdg_vs:
            return self.rdg + rdg_vs[armor_name]

        armor = target._armor_instance
        if armor is not None:
            for armor_type in armor.expanded_is_a:
                if armor_type in rdg_vs:
                    return self.rdg + rdg_vs[armor_type]
            for armor_type in armor.is_a:
                if armor_type in rdg_vs:
                    return self.rdg + rdg_vs[armor_type]

        return self.rdg

    def _get_vs_damage_bonus(self, target) -> int:
        """Return the best mdg_vs / rdg_vs bonus against target (expanded_is_a aware)."""
        bonus = 0
        for vs_dict in (self.mdg_vs, self.rdg_vs):
            v = _vs_lookup(vs_dict, target.type_name, target.expanded_is_a)
            if v is not None and v > bonus:
                bonus = v
        return bonus

    def _get_melee_defense_vs(self, attacker) -> int:
        """返回基于 mdf / mdf_vs 的近战防御值"""
        d = self.mdf_vs
        v = _vs_lookup(d, attacker.type_name, attacker.expanded_is_a)
        if v is not None:
            return self.mdf + v

        # 检查对攻击者武器类型的vs
        if hasattr(attacker, 'get_current_weapon_name'):
            weapon_name = attacker.get_current_weapon_name()
            if weapon_name and weapon_name in d:
                return self.mdf + d[weapon_name]

        # 检查对攻击者武器继承类型的vs
        if hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
            weapon_name = attacker.current_weapon
            if weapon_name and weapon_name in attacker._weapon_instances:
                weapon = attacker._weapon_instances[weapon_name]
                if hasattr(weapon, 'expanded_is_a'):
                    for weapon_type in weapon.expanded_is_a:
                        if weapon_type in d:
                            return self.mdf + d[weapon_type]
                # 也检查武器的直接is_a
                if hasattr(weapon, 'is_a'):
                    for weapon_type in weapon.is_a:
                        if weapon_type in d:
                            return self.mdf + d[weapon_type]

        return self.mdf

    def _get_ranged_defense_vs(self, attacker) -> int:
        """返回基于 rdf / rdf_vs 的远程防御值"""
        d = self.rdf_vs
        v = _vs_lookup(d, attacker.type_name, attacker.expanded_is_a)
        if v is not None:
            return self.rdf + v

        # 检查对攻击者武器类型的vs
        if hasattr(attacker, 'get_current_weapon_name'):
            weapon_name = attacker.get_current_weapon_name()
            if weapon_name and weapon_name in d:
                return self.rdf + d[weapon_name]

        # 检查对攻击者武器继承类型的vs
        if hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
            weapon_name = attacker.current_weapon
            if weapon_name and weapon_name in attacker._weapon_instances:
                weapon = attacker._weapon_instances[weapon_name]
                if hasattr(weapon, 'expanded_is_a'):
                    for weapon_type in weapon.expanded_is_a:
                        if weapon_type in d:
                            return self.rdf + d[weapon_type]
                # 也检查武器的直接is_a
                if hasattr(weapon, 'is_a'):
                    for weapon_type in weapon.is_a:
                        if weapon_type in d:
                            return self.rdf + d[weapon_type]

        return self.rdf
        
    def _get_total_melee_defense_vs(self, attacker) -> int:
        """获取总的近战防御值（考虑穿甲）"""
        base_defense = self._get_melee_defense_vs(attacker)  # 获取基础mdf

        # 检查攻击者是否有穿甲属性
        if hasattr(attacker, 'mdg_piercing') and attacker.mdg_piercing > 0:
            # 获取对特定单位/武器的近战抗穿甲值
            specific_piercing_resistance = 0
            if hasattr(self, 'mdf_piercing_vs'):
                # 检查对攻击者单位类型的抗穿甲
                if attacker.type_name in self.mdf_piercing_vs:
                    specific_piercing_resistance = self.mdf_piercing_vs[attacker.type_name]
                # 检查攻击者的扩展类型
                elif hasattr(attacker, 'expanded_is_a'):
                    for t in attacker.expanded_is_a:
                        if t in self.mdf_piercing_vs:
                            specific_piercing_resistance = self.mdf_piercing_vs[t]
                            break
                
                # 检查对攻击者武器类型的抗穿甲
                if specific_piercing_resistance == 0 and hasattr(attacker, 'get_current_weapon_name'):
                    weapon_name = attacker.get_current_weapon_name()
                    if weapon_name and weapon_name in self.mdf_piercing_vs:
                        specific_piercing_resistance = self.mdf_piercing_vs[weapon_name]
                
                # 检查对攻击者武器继承类型的抗穿甲
                if specific_piercing_resistance == 0 and hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
                    weapon_name = attacker.current_weapon
                    if weapon_name and weapon_name in attacker._weapon_instances:
                        weapon = attacker._weapon_instances[weapon_name]
                        if hasattr(weapon, 'expanded_is_a'):
                            for weapon_type in weapon.expanded_is_a:
                                if weapon_type in self.mdf_piercing_vs:
                                    specific_piercing_resistance = self.mdf_piercing_vs[weapon_type]
                                    break
                        # 也检查武器的直接is_a
                        if specific_piercing_resistance == 0 and hasattr(weapon, 'is_a'):
                            for weapon_type in weapon.is_a:
                                if weapon_type in self.mdf_piercing_vs:
                                    specific_piercing_resistance = self.mdf_piercing_vs[weapon_type]
                                    break

            # 穿甲效果：减少目标防御值，应用抗穿甲
            if _cf is not None:
                return _cf.apply_piercing(base_defense, attacker.mdg_piercing, specific_piercing_resistance)
            return max(0, base_defense - max(0, attacker.mdg_piercing - specific_piercing_resistance))

        return base_defense  # 如果没有穿甲效果，返回原始防御值

    def _get_total_ranged_defense_vs(self, attacker) -> int:
        """获取总的远程防御值（考虑穿甲）"""
        base_defense = self._get_ranged_defense_vs(attacker)  # 获取基础rdf

        # 检查攻击者是否有穿甲属性
        if hasattr(attacker, 'rdg_piercing') and attacker.rdg_piercing > 0:
            # 获取对特定单位/武器的远程抗穿甲值
            specific_piercing_resistance = 0
            if hasattr(self, 'rdf_piercing_vs'):
                # 检查对攻击者单位类型的抗穿甲
                if attacker.type_name in self.rdf_piercing_vs:
                    specific_piercing_resistance = self.rdf_piercing_vs[attacker.type_name]
                # 检查攻击者的扩展类型
                elif hasattr(attacker, 'expanded_is_a'):
                    for t in attacker.expanded_is_a:
                        if t in self.rdf_piercing_vs:
                            specific_piercing_resistance = self.rdf_piercing_vs[t]
                            break
                
                # 检查对攻击者武器类型的抗穿甲
                if specific_piercing_resistance == 0 and hasattr(attacker, 'get_current_weapon_name'):
                    weapon_name = attacker.get_current_weapon_name()
                    if weapon_name and weapon_name in self.rdf_piercing_vs:
                        specific_piercing_resistance = self.rdf_piercing_vs[weapon_name]
                
                # 检查对攻击者武器继承类型的抗穿甲
                if specific_piercing_resistance == 0 and hasattr(attacker, '_weapon_instances') and hasattr(attacker, 'current_weapon'):
                    weapon_name = attacker.current_weapon
                    if weapon_name and weapon_name in attacker._weapon_instances:
                        weapon = attacker._weapon_instances[weapon_name]
                        if hasattr(weapon, 'expanded_is_a'):
                            for weapon_type in weapon.expanded_is_a:
                                if weapon_type in self.rdf_piercing_vs:
                                    specific_piercing_resistance = self.rdf_piercing_vs[weapon_type]
                                    break
                        # 也检查武器的直接is_a
                        if specific_piercing_resistance == 0 and hasattr(weapon, 'is_a'):
                            for weapon_type in weapon.is_a:
                                if weapon_type in self.rdf_piercing_vs:
                                    specific_piercing_resistance = self.rdf_piercing_vs[weapon_type]
                                    break

            # 穿甲效果：减少目标防御值，应用抗穿甲
            if _cf is not None:
                return _cf.apply_piercing(base_defense, attacker.rdg_piercing, specific_piercing_resistance)
            return max(0, base_defense - max(0, attacker.rdg_piercing - specific_piercing_resistance))

        return base_defense  # 如果没有穿甲效果，返回原始防御值
        
    def _calculate_actual_damage(self, damage, attacker):
        """计算实际伤害，考虑防御值和特殊属性"""
        # 如果攻击者为None，直接返回原始伤害
        if attacker is None:
            return damage

        # 确定攻击类型
        is_melee = not (hasattr(attacker, 'rdg_range') and attacker.rdg_range > 0)

        # 获取防御值
        defense = self._get_total_melee_defense_vs(attacker) if is_melee else self._get_total_ranged_defense_vs(attacker)

        minimal_damage = getattr(attacker, 'minimal_damage', 0)
        forced_damage = getattr(attacker, 'forced_damage', 0)

        # 算术外包给 combat_fast.calc_actual_damage（含 max/clamp/forced 覆盖）
        if _cf is not None:
            return _cf.calc_actual_damage(damage, defense, minimal_damage, forced_damage)

        # 纯 Python fallback
        actual_damage = max(1, damage - defense)
        if minimal_damage > 0:
            actual_damage = max(actual_damage, minimal_damage)
        if forced_damage > 0:
            actual_damage = forced_damage
        return actual_damage
    
    def _get_speed_vs(self, target):
        """获取单位对特定目标的移动速度"""
        # 如果没有指定目标，返回基础速度
        if target is None:
            return self.speed

        # 初始化为基础速度
        final_speed = self.speed

        # 添加地形移动速度修正(如果有)
        terrain_type = self.place.type_name if self.place else None
        if terrain_type and hasattr(self, 'speed_on_terrain'):
            try:
                idx = self.speed_on_terrain.index(terrain_type)
                if idx + 1 < len(self.speed_on_terrain):
                    final_speed += int(self.speed_on_terrain[idx + 1])
            except (ValueError, IndexError):
                pass

        # 检查是否有针对这个目标类型的特定速度
        if hasattr(target, 'type_name') and target.type_name in self.speed_vs:
            # 修改：加上基础速度，而不是替换
            final_speed += self.speed_vs[target.type_name]
            return final_speed

        # 检查扩展类型
        if hasattr(target, 'expanded_is_a'):
            for t in target.expanded_is_a:
                if t in self.speed_vs:
                    # 修改：加上基础速度，而不是替换
                    final_speed += self.speed_vs[t]
                    return final_speed

        # 返回最终计算的速度
        return final_speed
        
    def _int_distance(self, x1, y1, x2, y2):
        """计算两点之间的距离（委托给模块级 Cython 加速函数）"""
        return _int_distance(x1, y1, x2, y2)

        
    def _calc_relative_speed(self, target) -> int:
        """计算目标与攻击者的相对速度(使用内部单位)

        Returns:
            int: > 0 表示正在远离
                 < 0 表示正在接近
                 = 0 表示相对静止
        """
        # 如果目标没有移动行为，返回0
        if not isinstance(target.action, MoveAction):
            return 0

        # 获取双方位置
        ax, ay = self.x, self.y
        tx, ty = target.x, target.y

        # 获取目标的移动目的地
        dest = target.action.target
        if not dest or not hasattr(dest, 'x') or not hasattr(dest, 'y'):
            return 0

        # 计算目标移动向量
        move_x = dest.x - tx
        move_y = dest.y - ty

        # 计算目标相对攻击者的位移向量
        relative_x = tx - ax
        relative_y = ty - ay

        # 使用点积判断接近/远离
        dot_product = (move_x * relative_x + move_y * relative_y)
        dist2 = relative_x * relative_x + relative_y * relative_y

        if dist2 == 0:
            return 0

        # 获取目标实际速度
        actual_speed = target.actual_speed if hasattr(target, 'actual_speed') else target.speed

        # 返回相对速度(负值表示接近)
        return (dot_product * actual_speed) // self._int_distance(0, 0, relative_x, relative_y) 