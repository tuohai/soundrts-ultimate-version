from .world_public_method import ground_or_air, has_target_type
from ..worldorders import (
    ORDERS_DICT,
    BuildPhaseTwoOrder,
    GoOrder,
    RallyingPointOrder,
    UpgradeToOrder,
    ProducingOrder,
    StartProduceOrder,
)
from ..worldroom import Square, Inside, ZoomTarget
from ..worldresource import Corpse, Deposit
from ..lib.nofloat import PRECISION
from .worldcreature import Creature, BuildingSite, Building
from ..worldweapon import Weapon
from ..worldarmor import Armor

class Unit(Creature):

    drop_loot = 1
    population_cost = 1
    # 统一逻辑：撤退仅在防御模式下评估
    flee_only_in_defensive_mode = True
    corpse_decay = 300 * PRECISION  # 默认尸体消失时间，避免某些单位类型缺少此属性导致错误

    is_cloakable = True
    is_a_gate = True
    is_a_unit = True

    @classmethod
    def interpret(cls, d):
        super().interpret(d)
        for k, f in [
            ("drop_loot", int),
            ("corpse_decay", lambda x: int(float(x[0] if isinstance(x, (list, tuple)) else x) * PRECISION) if x else 300 * PRECISION),
        ]:
            if k in d:
                d[k] = f(d[k])

    def __init__(self, player, place, x, y, o=90):
        # 在调用父类 __init__ 之前初始化武器相关属性
        # 因为父类初始化过程中会调用 update_weapons() 方法
        self._weapons = []  # 当前装备的武器实例列表
        self._weapon_instances = {}  # 所有武器实例的缓存 {weapon_name: weapon_instance}
        self.current_weapon = None  # 当前装备的武器名称
        
        super().__init__(player, place, x, y, o)
        self.player.nb_units_produced += 1
        if self.is_revivable:
            self.altar = self.place
        self.mdg_next_attack_time = 0
        self.mdg_prep_end_time = 0
        self.rdg_next_attack_time = 0
        self.rdg_prep_end_time = 0
        
        # 手动武器切换优先级相关属性
        self.manual_weapon_switch_time = 0  # 最后一次手动切换武器的时间
        self.manual_weapon_switch_weapon = None  # 最后一次手动切换的武器
        self.manual_weapon_switch_duration = 10 * PRECISION  # 手动切换优先级持续时间（10秒）
        
        # 确保有基础的近战/远程伤害属性
        if not hasattr(self, "mdg"):
            self.mdg = 0
        if not hasattr(self, "rdg"):
            self.rdg = 0
        if not hasattr(self, "mdg_range"):
            self.mdg_range = 0
        if not hasattr(self, "rdg_range"):
            self.rdg_range = 0
        if not hasattr(self, "mdg_cd"):
            self.mdg_cd = 0
        if not hasattr(self, "rdg_cd"):
            self.rdg_cd = 0
            
        # 确保有can_use_tech属性
        if not hasattr(self, "can_use_tech"):
            self.can_use_tech = []
        elif isinstance(self.can_use_tech, tuple):
            # 如果can_use_tech是元组，转换为列表方便后续添加
            self.can_use_tech = list(self.can_use_tech)
        
        # 初始化护甲相关属性
        self._armor = None  # 当前装备的护甲实例
        self._armor_instance = None  # 护甲实例
        self._builtin_armor_applied = False  # 内置护甲是否已套用属性

        # 同型模型（背包物品作为武器/盔甲）相关状态
        self._inventory_weapon_items = {}  # {weapon type_name: item} 由背包物品装备的武器
        self._inventory_armor_item = None  # 当前穿戴的盔甲物品（同型模型）
        self._armor_before_item = None  # 穿戴盔甲物品前的原始护甲 type_name
        
        # 确保有基础的近战/远程防御属性
        if not hasattr(self, "mdf"):
            self.mdf = 0
        if not hasattr(self, "rdf"):
            self.rdf = 0
        if not hasattr(self, "mdf_crit_rate"):
            self.mdf_crit_rate = 0
        if not hasattr(self, "rdf_crit_rate"):
            self.rdf_crit_rate = 0
        if not hasattr(self, "mdf_piercing"):
            self.mdf_piercing = 0
        if not hasattr(self, "rdf_piercing"):
            self.rdf_piercing = 0
        
        # 应用单位的武器
        self._apply_weapons()
        
        # 应用单位的护甲
        self._apply_armors()

        # 出厂武器/护甲：同名 class item 转入背包并静默装备
        self._spawn_starting_gear_to_inventory()
        
        # 如果玩家有科技升级，立即应用到武器、护甲和单位上
        if self.player and hasattr(self.player, 'upgrades') and self.player.upgrades:
            # 更新武器属性以反映玩家的科技等级
            self.update_weapons()
            # 更新护甲属性以反映玩家的科技等级
            self.update_armors()

    def _apply_weapons(self):
        """初始化单位的所有武器并装备第一个武器"""
        try:
            if hasattr(self, "weapons") and self.weapons:
                from ..definitions import rules
                
                # 保证weapons是列表
                if isinstance(self.weapons, str):
                    self.weapons = [self.weapons]
                elif not isinstance(self.weapons, list):
                    self.weapons = []
                
                # 为所有武器创建实例并缓存
                for weapon_name in self.weapons:
                    if self._is_item_gear_class(weapon_name, "weapon"):
                        continue
                    # 获取武器定义
                    weapon_class = rules.unit_class(weapon_name)
                    if weapon_class and hasattr(weapon_class, "is_a_weapon"):
                        # 创建武器实例
                        weapon = weapon_class(player=self.player)
                        
                        # 确保武器有一个world引用
                        weapon.world = self.world if hasattr(self, 'world') else None
                        
                        # 如果玩家有升级，应用到武器上
                        if self.player and hasattr(self.player, 'upgrades') and self.player.upgrades:
                            # 确保武器升级到玩家科技等级
                            if hasattr(weapon, "upgrade_to_player_level"):
                                weapon.upgrade_to_player_level()
                        
                        # 缓存武器实例
                        self._weapon_instances[weapon_name] = weapon
                
                # 默认装备第一个内置武器（不播报）
                if (self.weapons and not self.current_weapon
                        and getattr(type(self), "spawn_weapons_equipped", 1)):
                    for weapon_name in self.weapons:
                        if weapon_name in self._weapon_instances:
                            self._equip_weapon_silently(weapon_name)
                            break
                    
        except Exception as e:
            from ..lib.log import warning
            warning(f"Error applying weapons to unit {self.type_name}: {e}")
    
    def _reapply_phase_weapon_bonus(self):
        """在武器属性被 _clear_weapon_attributes + apply_to_unit 重置后，
        把玩家已研究的所有时代（phase）的"武器相关"加成（mdg/rdg/相关
        cd/range/crit 等）再叠加回来。否则带 weapon 的单位每次装备/切换
        武器、或时代研究后的统一刷新都会把 phase 攻防加成无声丢掉。
        """
        try:
            from ..worldphase import Phase
            Phase.apply_pool_weapon_subset_to_unit(self)
        except Exception:
            # 严格不让本辅助函数影响主流程；具体错误会由 Phase 内部 warning 记录
            pass

    def _reapply_phase_armor_bonus(self):
        """在护甲属性被 _clear_armor_attributes + apply_to_unit 重置后，
        把玩家已研究的所有时代（phase）的"护甲相关"加成（mdf/rdf 等）
        再叠加回来。
        """
        try:
            from ..worldphase import Phase
            Phase.apply_pool_armor_subset_to_unit(self)
        except Exception:
            pass

    def _equip_weapon_silently(self, weapon_name):
        """静默装备武器（不播报武器名）
        
        Args:
            weapon_name: 要装备的武器名称
        """
        if not hasattr(self, "weapons") or weapon_name not in self.weapons:
            return False
        
        if weapon_name not in self._weapon_instances:
            return False
        
        # 如果已经是当前武器，不需要切换
        if self.current_weapon == weapon_name:
            return True
        
        # 获取当前武器的主要攻击类型
        current_is_melee = self._is_weapon_primarily_melee(self.current_weapon)
        
        # 获取新武器的主要攻击类型
        new_weapon = self._weapon_instances[weapon_name]
        new_is_melee = self._is_weapon_primarily_melee(weapon_name)
        
        # 保存当前的攻击冷却计时器
        current_next_attack_time = 0
        current_prep_end_time = 0
        
        if current_is_melee:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'mdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'mdg_prep_end_time', 0))
        else:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'rdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'rdg_prep_end_time', 0))
        
        # 清除当前武器的属性
        self._clear_weapon_attributes()
        
        # 设置新武器
        self.current_weapon = weapon_name
        self._weapons = [self._weapon_instances[weapon_name]]
        
        # 应用新武器的属性
        weapon = self._weapon_instances[weapon_name]
        if hasattr(weapon, "apply_to_unit"):
            weapon.apply_to_unit(self)
        else:
            self._apply_weapon_manually(weapon)

        # 重新叠加已激活时代（phase）的武器相关加成（mdg/rdg 等）
        self._reapply_phase_weapon_bonus()
        
        # 将攻击冷却转移到新武器对应的攻击类型
        if new_is_melee:
            self.mdg_next_attack_time = max(self.mdg_next_attack_time, current_next_attack_time)
            self.mdg_prep_end_time = max(self.mdg_prep_end_time, current_prep_end_time)
        else:
            self.rdg_next_attack_time = max(self.rdg_next_attack_time, current_next_attack_time)
            self.rdg_prep_end_time = max(self.rdg_prep_end_time, current_prep_end_time)
        
        # 不播报武器名，只通知属性更新
        self.notify("attributes_changed")
        
        return True

    def switch_weapon(self, weapon_name):
        """切换到指定的武器
        
        Args:
            weapon_name: 要切换到的武器名称
        """
        if not hasattr(self, "weapons") or weapon_name not in self.weapons:
            return False
        
        if weapon_name not in self._weapon_instances:
            return False

        if (
            self.current_weapon
            and not self._can_switch_between_weapons(self.current_weapon, weapon_name)
        ):
            return False
        
        # 如果已经是当前武器，不需要切换
        if self.current_weapon == weapon_name:
            return True
        
        # 获取当前武器的主要攻击类型
        current_is_melee = self._is_weapon_primarily_melee(self.current_weapon)
        
        # 获取新武器的主要攻击类型
        new_weapon = self._weapon_instances[weapon_name]
        new_is_melee = self._is_weapon_primarily_melee(weapon_name)
        
        # 保存当前的攻击冷却计时器
        current_next_attack_time = 0
        current_prep_end_time = 0
        
        if current_is_melee:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'mdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'mdg_prep_end_time', 0))
        else:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'rdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'rdg_prep_end_time', 0))
        
        # 清除当前武器的属性
        self._clear_weapon_attributes()
        
        # 设置新武器
        self.current_weapon = weapon_name
        self._weapons = [self._weapon_instances[weapon_name]]
        
        # 应用新武器的属性
        weapon = self._weapon_instances[weapon_name]
        if hasattr(weapon, "apply_to_unit"):
            weapon.apply_to_unit(self)
        else:
            self._apply_weapon_manually(weapon)

        # 重新叠加已激活时代（phase）的武器相关加成（mdg/rdg 等）
        self._reapply_phase_weapon_bonus()
        
        # 将攻击冷却转移到新武器对应的攻击类型
        if new_is_melee:
            self.mdg_next_attack_time = max(self.mdg_next_attack_time, current_next_attack_time)
            self.mdg_prep_end_time = max(self.mdg_prep_end_time, current_prep_end_time)
        else:
            self.rdg_next_attack_time = max(self.rdg_next_attack_time, current_next_attack_time)
            self.rdg_prep_end_time = max(self.rdg_prep_end_time, current_prep_end_time)
        
        # 设置手动武器切换优先级标记
        self.manual_weapon_switch_time = self.world.time
        self.manual_weapon_switch_weapon = weapon_name
        
        # 通知切换武器
        self.notify(f"weapon_switched,{weapon_name}")
        
        # 通知属性更新（触发客户端刷新属性界面）
        self.notify("attributes_changed")
        
        return True
    
    def _auto_switch_weapon(self, weapon_name):
        """自动切换武器（播放音效但不播报武器名）
        
        Args:
            weapon_name: 要切换到的武器名称
        """
        if not hasattr(self, "weapons") or weapon_name not in self.weapons:
            return False
        
        if weapon_name not in self._weapon_instances:
            return False
        
        # 如果已经是当前武器，不需要切换
        if self.current_weapon == weapon_name:
            return True
        
        # 获取当前武器的主要攻击类型
        current_is_melee = self._is_weapon_primarily_melee(self.current_weapon)
        
        # 获取新武器的主要攻击类型
        new_weapon = self._weapon_instances[weapon_name]
        new_is_melee = self._is_weapon_primarily_melee(weapon_name)
        
        # 保存当前的攻击冷却计时器
        current_next_attack_time = 0
        current_prep_end_time = 0
        
        if current_is_melee:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'mdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'mdg_prep_end_time', 0))
        else:
            current_next_attack_time = max(current_next_attack_time, getattr(self, 'rdg_next_attack_time', 0))
            current_prep_end_time = max(current_prep_end_time, getattr(self, 'rdg_prep_end_time', 0))
        
        # 清除当前武器的属性
        self._clear_weapon_attributes()
        
        # 设置新武器
        self.current_weapon = weapon_name
        self._weapons = [self._weapon_instances[weapon_name]]
        
        # 应用新武器的属性
        weapon = self._weapon_instances[weapon_name]
        if hasattr(weapon, "apply_to_unit"):
            weapon.apply_to_unit(self)
        else:
            self._apply_weapon_manually(weapon)

        # 重新叠加已激活时代（phase）的武器相关加成（mdg/rdg 等）
        self._reapply_phase_weapon_bonus()
        
        # 将攻击冷却转移到新武器对应的攻击类型
        if new_is_melee:
            self.mdg_next_attack_time = max(self.mdg_next_attack_time, current_next_attack_time)
            self.mdg_prep_end_time = max(self.mdg_prep_end_time, current_prep_end_time)
        else:
            self.rdg_next_attack_time = max(self.rdg_next_attack_time, current_next_attack_time)
            self.rdg_prep_end_time = max(self.rdg_prep_end_time, current_prep_end_time)
        
        # 通知自动切换武器（播放音效但不播报武器名）
        self.notify(f"auto_weapon_switched,{weapon_name}")
        
        # 通知属性更新（触发客户端刷新属性界面）
        self.notify("attributes_changed")
        
        return True
    
    def next_weapon(self):
        """切换到下一个武器"""
        if not hasattr(self, "weapons") or len(self.weapons) <= 1:
            return False
        
        current_index = 0
        if self.current_weapon in self.weapons:
            current_index = self.weapons.index(self.current_weapon)
        
        next_index = (current_index + 1) % len(self.weapons)
        return self.switch_weapon(self.weapons[next_index])
    
    def previous_weapon(self):
        """切换到上一个武器"""
        if not hasattr(self, "weapons") or len(self.weapons) <= 1:
            return False
        
        current_index = 0
        if self.current_weapon in self.weapons:
            current_index = self.weapons.index(self.current_weapon)
        
        prev_index = (current_index - 1) % len(self.weapons)
        return self.switch_weapon(self.weapons[prev_index])
    
    def get_available_weapons(self):
        """获取所有可用武器的列表"""
        if not hasattr(self, "weapons"):
            return []
        weapons = self.weapons[:]
        if not self._has_mixed_weapon_gear():
            return weapons
        current_kind = self._weapon_gear_kind(self.current_weapon)
        if current_kind is None:
            return weapons
        return [
            weapon_name
            for weapon_name in weapons
            if self._weapon_gear_kind(weapon_name) == current_kind
        ]
    
    def get_current_weapon_name(self):
        """获取当前武器名称"""
        return self.current_weapon
    
    def _should_respect_manual_weapon_choice(self):
        """检查是否应该尊重玩家的手动武器选择
        
        Returns:
            bool: 如果应该尊重手动选择（阻止自动切换）返回True
        """
        # 如果没有手动切换记录，允许自动切换
        if not hasattr(self, 'manual_weapon_switch_time') or self.manual_weapon_switch_time == 0:
            return False
        
        # 如果没有world引用，允许自动切换
        if not hasattr(self, 'world') or not self.world:
            return False
        
        # 检查当前武器属性是否已初始化
        if not hasattr(self, "current_weapon"):
            return False
        
        # 检查手动切换是否超时
        current_time = self.world.time
        time_since_manual_switch = current_time - self.manual_weapon_switch_time
        
        # 如果超过持续时间，允许自动切换
        if time_since_manual_switch >= self.manual_weapon_switch_duration:
            return False
        
        # 如果当前武器不是手动选择的武器，允许自动切换
        # （这种情况可能发生在手动切换后，武器被其他方式改变）
        if self.current_weapon != self.manual_weapon_switch_weapon:
            return False
        
        # 否则，应该尊重手动选择
        return True
    
    def clear_manual_weapon_priority(self):
        """清除手动武器切换的优先级标记"""
        self.manual_weapon_switch_time = 0
        self.manual_weapon_switch_weapon = None
    
    def switch_to_default_weapon(self):
        """切换回默认武器（weapons列表中的第一个武器）
        
        这个方法用于在目标脱离视野或被消灭后，让单位回到其主职业状态。
        这种切换不会触发手动武器切换的优先级保护。
        
        Returns:
            bool: 如果成功切换返回True，否则返回False
        """
        # 如果禁用了自动武器切换，不执行默认武器切换
        if hasattr(self, '_should_auto_switch_weapon') and not self._should_auto_switch_weapon():
            return True  # 返回True表示不需要切换
        
        # 检查武器系统是否已初始化
        if not hasattr(self, "weapons") or not self.weapons:
            return False
        
        # 检查当前武器属性是否已初始化
        if not hasattr(self, "current_weapon"):
            return False
        
        default_weapon = self.weapons[0]  # 第一个武器是默认武器
        
        # 如果已经是默认武器，不需要切换
        if self.current_weapon == default_weapon:
            return True
        
        # 使用自动切换，播放音效但不播报武器名，也不设置手动优先级
        return self._auto_switch_weapon(default_weapon)
    
    def get_default_weapon(self):
        """获取默认武器名称
        
        Returns:
            str: 默认武器名称，如果没有武器则返回None
        """
        if hasattr(self, "weapons") and self.weapons:
            return self.weapons[0]
        return None
    
    def get_manual_weapon_priority_remaining_time(self):
        """获取手动武器切换优先级的剩余时间（秒）
        
        Returns:
            float: 剩余时间（秒），如果没有优先级则返回0
        """
        # 检查基本属性是否已初始化
        if not hasattr(self, 'manual_weapon_switch_time') or not hasattr(self, 'world'):
            return 0
        
        if not self._should_respect_manual_weapon_choice():
            return 0
        
        current_time = self.world.time
        time_since_manual_switch = current_time - self.manual_weapon_switch_time
        remaining_time = self.manual_weapon_switch_duration - time_since_manual_switch
        
        return max(0, remaining_time / PRECISION)
    
    def debug_weapon_info(self):
        """调试用：输出当前武器信息"""
        from ..lib.log import info
        info(f"=== 单位 {self.type_name}({self.id}) 武器信息 ===")
        info(f"可用武器: {getattr(self, 'weapons', [])}")
        info(f"当前武器: {self.current_weapon}")
        info(f"武器实例缓存: {list(self._weapon_instances.keys())}")
        info(f"当前装备武器: {[w.type_name if hasattr(w, 'type_name') else str(w) for w in self._weapons]}")
        info(f"当前属性 - mdg: {getattr(self, 'mdg', 0)}, rdg: {getattr(self, 'rdg', 0)}")
        info(f"当前属性 - mdg_range: {getattr(self, 'mdg_range', 0)}, rdg_range: {getattr(self, 'rdg_range', 0)}")
        info(f"当前属性 - mdg_cd: {getattr(self, 'mdg_cd', 0)}, rdg_cd: {getattr(self, 'rdg_cd', 0)}")
        
        # 显示手动武器切换状态
        if self._should_respect_manual_weapon_choice():
            remaining_time = self.get_manual_weapon_priority_remaining_time()
            info(f"手动武器切换优先级: 活跃 (剩余 {remaining_time:.1f}秒)")
            info(f"手动选择武器: {self.manual_weapon_switch_weapon}")
        else:
            info(f"手动武器切换优先级: 无")
        
        if self.current_weapon and self.current_weapon in self._weapon_instances:
            weapon = self._weapon_instances[self.current_weapon]
            info(f"武器属性 - mdg: {getattr(weapon, 'mdg', 0)}, rdg: {getattr(weapon, 'rdg', 0)}")
            info(f"武器属性 - mdg_range: {getattr(weapon, 'mdg_range', 0)}, rdg_range: {getattr(weapon, 'rdg_range', 0)}")
        info("==========================================")
        
        # 通知客户端显示调试信息
        priority_info = ""
        if self._should_respect_manual_weapon_choice():
            remaining_time = self.get_manual_weapon_priority_remaining_time()
            priority_info = f", 手动优先级: {remaining_time:.1f}秒"
        
        self.notify(f"debug_info,当前武器: {self.current_weapon}, mdg: {getattr(self, 'mdg', 0)}, rdg: {getattr(self, 'rdg', 0)}{priority_info}")
    
    def _clear_weapon_attributes(self):
        """清除当前武器的属性，恢复到基础值"""
        # 恢复基础攻击属性
        base_class = type(self)
        
        # 恢复基础伤害值
        self.mdg = getattr(base_class, 'mdg', 0)
        self.rdg = getattr(base_class, 'rdg', 0)
        
        # 恢复基础射程
        self.mdg_range = getattr(base_class, 'mdg_range', 0)
        self.rdg_range = getattr(base_class, 'rdg_range', 0)
        
        # 恢复基础最小射程
        self.mdg_minimal_range = getattr(base_class, 'mdg_minimal_range', 0)
        self.rdg_minimal_range = getattr(base_class, 'rdg_minimal_range', 0)
        
        # 恢复基础冷却
        self.mdg_cd = getattr(base_class, 'mdg_cd', 0)
        self.rdg_cd = getattr(base_class, 'rdg_cd', 0)
        
        # 恢复基础暴击属性
        self.mdg_crit = getattr(base_class, 'mdg_crit', 0)
        self.rdg_crit = getattr(base_class, 'rdg_crit', 0)
        self.mdg_crit_rate = getattr(base_class, 'mdg_crit_rate', 0)
        self.rdg_crit_rate = getattr(base_class, 'rdg_crit_rate', 0)
        
        # 恢复基础穿甲属性
        self.mdg_piercing = getattr(base_class, 'mdg_piercing', 0)
        self.rdg_piercing = getattr(base_class, 'rdg_piercing', 0)
        self.mdg_piercing_rate = getattr(base_class, 'mdg_piercing_rate', 0)
        self.rdg_piercing_rate = getattr(base_class, 'rdg_piercing_rate', 0)
        
        # 恢复基础溅射属性
        self.mdg_splash = getattr(base_class, 'mdg_splash', 0)
        self.rdg_splash = getattr(base_class, 'rdg_splash', 0)
        self.mdg_radius = getattr(base_class, 'mdg_radius', 0)
        self.rdg_radius = getattr(base_class, 'rdg_radius', 0)
        
        # 清除bonus属性
        self.mdg_bonus = 0
        self.rdg_bonus = 0
        self.mdg_crit_bonus = 0
        self.rdg_crit_bonus = 0
        self.mdg_piercing_bonus = 0
        self.rdg_piercing_bonus = 0
        
        # 清除vs属性字典
        vs_attributes = [
            "mdg_vs", "rdg_vs", "mdg_crit_vs", "rdg_crit_vs",
            "mdg_crit_rate_vs", "rdg_crit_rate_vs", "mdg_piercing_vs", "rdg_piercing_vs",
            "mdg_piercing_rate_vs", "rdg_piercing_rate_vs", "mdg_cd_vs", "rdg_cd_vs",
            "mdg_range_vs", "rdg_range_vs", "mdg_minimal_range_vs", "rdg_minimal_range_vs",
            "menace_vs", "menace_mult_vs",
        ]
        
        for attr in vs_attributes:
            if hasattr(self, attr):
                setattr(self, attr, dict())
        
        # 恢复基础can_use_tech（移除武器添加的科技）
        base_can_use_tech = getattr(base_class, 'can_use_tech', [])
        if isinstance(base_can_use_tech, tuple):
            self.can_use_tech = list(base_can_use_tech)
        else:
            self.can_use_tech = base_can_use_tech[:]
    
    def _apply_weapon_manually(self, weapon):
        """手动应用武器属性（当武器没有apply_to_unit方法时）"""
        # 应用基础伤害
        if hasattr(weapon, "mdg") and weapon.mdg > 0:
            self.mdg = weapon.mdg
                
        if hasattr(weapon, "rdg") and weapon.rdg > 0:
            self.rdg = weapon.rdg
        
        # 应用武器的bonus属性
        if hasattr(weapon, "mdg_bonus") and weapon.mdg_bonus > 0:
            self.mdg_bonus = weapon.mdg_bonus
            
        if hasattr(weapon, "rdg_bonus") and weapon.rdg_bonus > 0:
            self.rdg_bonus = weapon.rdg_bonus
        
        # 应用暴击属性
        if hasattr(weapon, "mdg_crit"):
            self.mdg_crit = weapon.mdg_crit
            
        if hasattr(weapon, "rdg_crit"):
            self.rdg_crit = weapon.rdg_crit
            
        if hasattr(weapon, "mdg_crit_rate"):
            self.mdg_crit_rate = weapon.mdg_crit_rate
            
        if hasattr(weapon, "rdg_crit_rate"):
            self.rdg_crit_rate = weapon.rdg_crit_rate
        
        # 应用穿甲属性
        if hasattr(weapon, "mdg_piercing"):
            self.mdg_piercing = weapon.mdg_piercing
            
        if hasattr(weapon, "rdg_piercing"):
            self.rdg_piercing = weapon.rdg_piercing
            
        if hasattr(weapon, "mdg_piercing_rate"):
            self.mdg_piercing_rate = weapon.mdg_piercing_rate
            
        if hasattr(weapon, "rdg_piercing_rate"):
            self.rdg_piercing_rate = weapon.rdg_piercing_rate
        
        # 应用武器的冷却时间
        if hasattr(weapon, "mdg_cd"):
            self.mdg_cd = weapon.mdg_cd
            
        if hasattr(weapon, "rdg_cd"):
            self.rdg_cd = weapon.rdg_cd
        
        # 应用武器的射程
        if hasattr(weapon, "mdg_range"):
            self.mdg_range = weapon.mdg_range
            
        if hasattr(weapon, "rdg_range"):
            self.rdg_range = weapon.rdg_range
            
        if hasattr(weapon, "mdg_minimal_range"):
            self.mdg_minimal_range = weapon.mdg_minimal_range
            
        if hasattr(weapon, "rdg_minimal_range"):
            self.rdg_minimal_range = weapon.rdg_minimal_range
        
        # 应用溅射属性
        if hasattr(weapon, "mdg_splash"):
            self.mdg_splash = weapon.mdg_splash
            
        if hasattr(weapon, "rdg_splash"):
            self.rdg_splash = weapon.rdg_splash
            
        if hasattr(weapon, "mdg_radius"):
            self.mdg_radius = weapon.mdg_radius
            
        if hasattr(weapon, "rdg_radius"):
            self.rdg_radius = weapon.rdg_radius
        
        # 应用vs属性字典
        vs_attributes = [
            "mdg_vs", "rdg_vs", "mdg_crit_vs", "rdg_crit_vs",
            "mdg_crit_rate_vs", "rdg_crit_rate_vs", "mdg_piercing_vs", "rdg_piercing_vs",
            "mdg_piercing_rate_vs", "rdg_piercing_rate_vs", "mdg_cd_vs", "rdg_cd_vs",
            "mdg_range_vs", "rdg_range_vs", "mdg_minimal_range_vs", "rdg_minimal_range_vs",
            "menace_vs", "menace_mult_vs",
        ]
        
        for attr in vs_attributes:
            if hasattr(weapon, attr):
                weapon_vs = getattr(weapon, attr)
                if weapon_vs and isinstance(weapon_vs, dict):
                    # 确保单位有该vs属性
                    if not hasattr(self, attr):
                        setattr(self, attr, dict())
                    unit_vs = getattr(self, attr)
                    # 复制武器的vs到单位的vs
                    unit_vs.update(weapon_vs)
            
        # 应用武器的can_use_tech属性
        if hasattr(weapon, "can_use_tech") and weapon.can_use_tech:
            # 确保单位有can_use_tech属性
            if not hasattr(self, "can_use_tech"):
                self.can_use_tech = []
            # 如果can_use_tech是元组，转换为列表
            if isinstance(self.can_use_tech, tuple):
                self.can_use_tech = list(self.can_use_tech)
            # 添加武器的can_use_tech到单位的can_use_tech中
            for tech in weapon.can_use_tech:
                if tech not in self.can_use_tech:
                    self.can_use_tech.append(tech)
        
        # 应用武器的debuffs属性
        if hasattr(weapon, "debuffs") and weapon.debuffs:
            # 确保单位有debuffs属性
            if not hasattr(self, "debuffs"):
                self.debuffs = []
            # 如果debuffs是元组，转换为列表
            if isinstance(self.debuffs, tuple):
                self.debuffs = list(self.debuffs)
            # 添加武器的debuffs到单位的debuffs中（避免重复）
            for debuff in weapon.debuffs:
                if debuff not in self.debuffs:
                    self.debuffs.append(debuff)

    def update_weapons(self):
        """更新单位的武器属性
        在玩家研究科技后调用此方法，重新应用武器属性
        """
        # 检查武器实例是否已初始化
        if not hasattr(self, '_weapon_instances') or not self._weapon_instances:
            return
            
        # 更新所有武器实例的科技等级
        for weapon_name, weapon in self._weapon_instances.items():
            # 调用武器自身的升级方法
            if hasattr(weapon, 'upgrade_to_player_level'):
                weapon.upgrade_to_player_level()
        
        # 重新应用当前装备武器的属性
        if self.current_weapon and self.current_weapon in self._weapon_instances:
            self._clear_weapon_attributes()
            weapon = self._weapon_instances[self.current_weapon]
            if hasattr(weapon, "apply_to_unit"):
                weapon.apply_to_unit(self)
            else:
                self._apply_weapon_manually(weapon)

            # 重新叠加已激活时代（phase）的武器相关加成（mdg/rdg 等），
            # 否则诸如 castle_age 的 phase bonus mdg 2 在每次科技刷新或
            # 武器切换后都会被武器属性覆盖而失效。
            self._reapply_phase_weapon_bonus()

    def die(self, attacker=None):
        if self.player is None:
            return
        self.player.nb_units_lost += 1
        if attacker and hasattr(attacker, 'last_player') and attacker.last_player:
            attacker.last_player.nb_units_killed += 1
        if self.drop_loot:
            for i in self.inventory[:]:
                if i.is_loot:
                    self.drop(i)
        # 修复：确保英雄单位的尸体始终被创建，并且正确设置复活属性
        if self.corpse and not self.is_inside:
            # 为防止多次调用die方法，先检查尸体是否已创建
            if not hasattr(self, '_corpse_created'):
                self._corpse_created = True
                corpse = Corpse(self)

        Creature.die(self, attacker)

    def resurrect(self, corpse):
        if not self.player.check_count_limit(self.type_name):
            return
        p = self.player
        self.player = None
        self.place = None
        self.id = None  # so the unit will be added to world.active_objects
        self.hp = self.hp_max // 3
        self.set_player(p)
        self.move_to(corpse.place, corpse.x, corpse.y)
        # 复活后重置一次性尸体标记，确保后续再次死亡时仍会生成尸体
        if hasattr(self, "_corpse_created"):
            try:
                delattr(self, "_corpse_created")
            except Exception:
                pass
        if self.decay:
            self.time_limit = self.world.time + self.decay
        # 发送复活通知给客户端
        self.notify(f"resurrected,{self.type_name},{self.id}")
        corpse.delete()

    @property
    def basic_skills(self):
        for o in self.orders:
            if isinstance(o, UpgradeToOrder):
                return set()
        return self._basic_skills

    # actions

    def next_square(self, target, avoid=False):
        next_stage = self.next_stage(target, avoid=avoid)
        try:
            return next_stage.other_side.place
        except AttributeError:
            return next_stage

    def next_stage(self, target, avoid=False):
        if self.is_inside:
            return
        if target is None or target.place is None:
            return None
        if not isinstance(target, Square):
            if self.place == target.place:
                return target
            place = target.place
        else:
            if self.place == target:
                return None
            place = target
        if not isinstance(place, Square):
            return None
        if self.airground_type == "water":
            from ..worldplayercomputer_water import water_path_destination

            place = water_path_destination(self, place, self.player)
        nxt, self.distance_to_goal = self.place._shortest_path_to(
            place, self.airground_type, self.player, avoid=avoid
        )
        return nxt

    _destination = None

    def move_on_border(self, e):
        self.move_to(e.place, e.x, e.y)

    def block(self, e):
        if not self.blocked_exit:
            self.blocked_exit = e
            e.add_blocker(self)

    def _is_weapon_primarily_melee(self, weapon_name):
        """判断武器主要是近战还是远程
        
        Args:
            weapon_name: 武器名称
            
        Returns:
            bool: True表示主要是近战武器，False表示主要是远程武器
        """
        if not weapon_name or weapon_name not in self._weapon_instances:
            # 如果没有武器，根据单位基础属性判断
            return getattr(self, 'mdg', 0) > getattr(self, 'rdg', 0)
        
        weapon = self._weapon_instances[weapon_name]
        
        # 获取武器的近战和远程伤害
        weapon_mdg = getattr(weapon, 'mdg', 0)
        weapon_rdg = getattr(weapon, 'rdg', 0)
        
        # 如果只有一种伤害类型，直接判断
        if weapon_mdg > 0 and weapon_rdg == 0:
            return True  # 纯近战武器
        elif weapon_rdg > 0 and weapon_mdg == 0:
            return False  # 纯远程武器
        elif weapon_mdg > 0 and weapon_rdg > 0:
            # 如果两种伤害都有，比较哪种更高
            return weapon_mdg >= weapon_rdg
        else:
            # 如果都没有伤害，根据射程判断（远程武器通常有射程）
            weapon_rdg_range = getattr(weapon, 'rdg_range', 0)
            return weapon_rdg_range == 0  # 没有远程射程则认为是近战

    # 护甲系统相关方法
    def _apply_armors(self):
        """初始化单位的护甲"""
        try:
            if hasattr(self, "armor") and self.armor:
                from ..definitions import rules
                
                # armor应该是字符串，护甲名称
                armor_name = self.armor
                if self._is_item_gear_class(armor_name, "armor"):
                    return
                
                # 获取护甲定义
                armor_class = rules.unit_class(armor_name)
                if armor_class:
                    # 创建护甲实例
                    armor = armor_class(player=self.player)
                    
                    # 确保护甲有一个world引用
                    armor.world = self.world if hasattr(self, 'world') else None
                    
                    # 如果玩家有升级，应用到护甲上
                    if self.player and hasattr(self.player, 'upgrades') and self.player.upgrades:
                        # 确保护甲升级到玩家科技等级
                        if hasattr(armor, "upgrade_to_player_level"):
                            armor.upgrade_to_player_level()
                    
                    # 设置护甲实例
                    self._armor_instance = armor
                    self._armor = armor

                    if getattr(type(self), "spawn_armor_equipped", 1):
                        self._equip_builtin_armor()
                    else:
                        self._builtin_armor_applied = False
                    
        except Exception as e:
            from ..lib.log import warning
            warning(f"Error applying armor to unit {self.type_name}: {e}")

    def _is_builtin_armor_applied(self):
        """内置护甲（class armor）是否已套用属性到单位。"""
        armor_name = getattr(type(self), "armor", None)
        if not armor_name or isinstance(armor_name, (list, tuple)):
            return False
        if self._is_item_gear_class(armor_name, "armor"):
            return False
        return bool(getattr(self, "_builtin_armor_applied", False))

    def _equip_builtin_armor(self):
        """将已创建的内置护甲实例属性套用到单位。"""
        if not self.can_equip_builtin_armor():
            return False
        armor = getattr(self, "_armor_instance", None)
        if armor is None:
            return False
        if getattr(self, "_builtin_armor_applied", False):
            return True
        if hasattr(armor, "apply_to_unit"):
            armor.apply_to_unit(self)
        else:
            self._apply_armor_manually(armor)
        self._reapply_phase_armor_bonus()
        self._builtin_armor_applied = True
        return True

    def get_current_armor_name(self):
        """获取当前护甲名称"""
        return getattr(self, 'armor', None)

    def _clear_armor_attributes(self):
        """清除当前护甲的属性，恢复到基础值"""
        # 恢复基础防御属性
        base_class = type(self)
        
        # 恢复基础防御值
        self.mdf = getattr(base_class, 'mdf', 0)
        self.rdf = getattr(base_class, 'rdf', 0)
        
        # 恢复基础抗性属性
        self.mdf_crit_rate = getattr(base_class, 'mdf_crit_rate', 0)
        self.rdf_crit_rate = getattr(base_class, 'rdf_crit_rate', 0)
        self.mdf_piercing = getattr(base_class, 'mdf_piercing', 0)
        self.rdf_piercing = getattr(base_class, 'rdf_piercing', 0)
        
        # 清除bonus属性
        if hasattr(self, 'mdf_bonus'):
            self.mdf_bonus = 0
        if hasattr(self, 'rdf_bonus'):
            self.rdf_bonus = 0
        if hasattr(self, 'mdf_crit_rate_bonus'):
            self.mdf_crit_rate_bonus = 0
        if hasattr(self, 'rdf_crit_rate_bonus'):
            self.rdf_crit_rate_bonus = 0
        if hasattr(self, 'mdf_piercing_bonus'):
            self.mdf_piercing_bonus = 0
        if hasattr(self, 'rdf_piercing_bonus'):
            self.rdf_piercing_bonus = 0
        
        # 清除vs属性字典（只清除护甲相关的vs属性）
        vs_attributes = [
            "mdf_vs", "rdf_vs", "mdf_crit_rate_vs", "rdf_crit_rate_vs",
            "mdf_piercing_vs", "rdf_piercing_vs"
        ]
        
        for attr in vs_attributes:
            if hasattr(self, attr):
                base_vs = getattr(base_class, attr, {})
                setattr(self, attr, dict(base_vs))

    def _apply_armor_manually(self, armor):
        """手动应用护甲属性（当护甲没有apply_to_unit方法时）"""
        # 应用基础防御
        if hasattr(armor, "mdf") and armor.mdf > 0:
            self.mdf = armor.mdf
                
        if hasattr(armor, "rdf") and armor.rdf > 0:
            self.rdf = armor.rdf
        
        # 应用护甲的bonus属性
        if hasattr(armor, "mdf_bonus") and armor.mdf_bonus > 0:
            if not hasattr(self, "mdf_bonus"):
                self.mdf_bonus = 0
            self.mdf_bonus = armor.mdf_bonus
            
        if hasattr(armor, "rdf_bonus") and armor.rdf_bonus > 0:
            if not hasattr(self, "rdf_bonus"):
                self.rdf_bonus = 0
            self.rdf_bonus = armor.rdf_bonus
        
        # 应用抗性属性
        if hasattr(armor, "mdf_crit_rate"):
            self.mdf_crit_rate = armor.mdf_crit_rate
            
        if hasattr(armor, "rdf_crit_rate"):
            self.rdf_crit_rate = armor.rdf_crit_rate
            
        if hasattr(armor, "mdf_piercing"):
            self.mdf_piercing = armor.mdf_piercing
            
        if hasattr(armor, "rdf_piercing"):
            self.rdf_piercing = armor.rdf_piercing
        
        # 应用vs属性字典
        vs_attributes = [
            "mdf_vs", "rdf_vs", "mdf_crit_rate_vs", "rdf_crit_rate_vs",
            "mdf_piercing_vs", "rdf_piercing_vs"
        ]
        
        for attr in vs_attributes:
            if hasattr(armor, attr):
                armor_vs = getattr(armor, attr)
                if armor_vs and isinstance(armor_vs, dict):
                    # 确保单位有该vs属性
                    if not hasattr(self, attr):
                        setattr(self, attr, dict())
                    unit_vs = getattr(self, attr)
                    # 复制护甲的vs到单位的vs
                    unit_vs.update(armor_vs)
        


    def update_armors(self):
        """更新单位的护甲属性
        在玩家研究科技后调用此方法，重新应用护甲属性
        """
        # 检查护甲实例是否已初始化
        if not hasattr(self, '_armor_instance'):
            return
            
        # 更新护甲实例的科技等级
        if self._armor_instance:
            armor = self._armor_instance
            # 调用护甲自身的升级方法
            if hasattr(armor, 'upgrade_to_player_level'):
                armor.upgrade_to_player_level()
            
            # 重新应用护甲属性
            self._clear_armor_attributes()
            if hasattr(armor, "apply_to_unit"):
                armor.apply_to_unit(self)
            else:
                self._apply_armor_manually(armor)

            # 重新叠加已激活时代（phase）的护甲相关加成（mdf/rdf 等）
            self._reapply_phase_armor_bonus()

    # ==================== 同型模型：背包物品作为武器/盔甲 ====================
    # 一个 rules.txt 类型可以同时是可拾取的 item 且可装备的武器/盔甲。
    # 这些方法把背包里的 item 接入单位既有的武器/护甲系统：装备时套用其数值，
    # 卸下时还原。所有调用都来自服务器端 order，保证确定性与多人同步安全。

    @staticmethod
    def _is_item_gear_class(type_name, gear_kind):
        """rules 中是否存在同名、可装备为武器/护甲的 class item。"""
        if not type_name:
            return False
        from ..definitions import rules
        from ..worlditem import Item

        cls = rules.unit_class(type_name)
        if cls is None or not isinstance(cls, type) or not issubclass(cls, Item):
            return False
        if gear_kind == "weapon":
            return bool(getattr(cls, "equippable_as_weapon", 0))
        if gear_kind == "armor":
            return bool(getattr(cls, "equippable_as_armor", 0))
        return False

    @classmethod
    def _class_weapon_names(cls, unit_cls):
        weapon_names = getattr(unit_cls, "weapons", None) or []
        if isinstance(weapon_names, str):
            weapon_names = [weapon_names]
        return [w for w in weapon_names if w]

    @classmethod
    def _class_has_builtin_weapons(cls, unit_cls):
        return any(
            not cls._is_item_gear_class(w, "weapon")
            for w in cls._class_weapon_names(unit_cls)
        )

    @classmethod
    def _class_has_item_gear_weapons(cls, unit_cls):
        return any(
            cls._is_item_gear_class(w, "weapon")
            for w in cls._class_weapon_names(unit_cls)
        )

    @classmethod
    def _class_has_builtin_armor(cls, unit_cls):
        armor_name = getattr(unit_cls, "armor", None)
        if not armor_name or isinstance(armor_name, (list, tuple)):
            return False
        return not cls._is_item_gear_class(armor_name, "armor")

    @classmethod
    def _class_has_item_gear_armor(cls, unit_cls):
        armor_name = getattr(unit_cls, "armor", None)
        if not armor_name or isinstance(armor_name, (list, tuple)):
            return False
        return cls._is_item_gear_class(armor_name, "armor")

    def _has_mixed_weapon_gear(self):
        unit_cls = type(self)
        return (
            self._class_has_builtin_weapons(unit_cls)
            and self._class_has_item_gear_weapons(unit_cls)
        )

    def _has_mixed_armor_gear(self):
        unit_cls = type(self)
        return (
            self._class_has_builtin_armor(unit_cls)
            and self._class_has_item_gear_armor(unit_cls)
        )

    def _weapon_gear_kind(self, weapon_name):
        """返回 'builtin'、'inventory' 或 None。"""
        if weapon_name in getattr(self, "_inventory_weapon_items", {}):
            return "inventory"
        if weapon_name in getattr(self, "_weapon_instances", {}):
            return "builtin"
        return None

    def _can_switch_between_weapons(self, from_name, to_name):
        if not self._has_mixed_weapon_gear():
            return True
        from_kind = self._weapon_gear_kind(from_name)
        to_kind = self._weapon_gear_kind(to_name)
        if from_kind is None or to_kind is None:
            return True
        return from_kind == to_kind

    def can_equip_item_weapon(self):
        if not self._has_mixed_weapon_gear():
            return True
        return not getattr(type(self), "spawn_weapons_equipped", 1)

    def can_equip_item_armor(self):
        if self._has_mixed_armor_gear() and getattr(type(self), "spawn_armor_equipped", 1):
            return False
        if self._class_has_builtin_armor(type(self)):
            if getattr(type(self), "spawn_armor_equipped", 1):
                return False
            if self._is_builtin_armor_applied():
                return False
        return True

    def can_equip_builtin_armor(self):
        if getattr(self, "_inventory_armor_item", None) is not None:
            return False
        return True

    def _first_restorable_weapon(self):
        weapons = getattr(self, "weapons", None) or []
        if isinstance(weapons, str):
            weapons = [weapons]
        if self._has_mixed_weapon_gear():
            for weapon_name in weapons:
                if (
                    weapon_name in self._weapon_instances
                    and weapon_name not in getattr(self, "_inventory_weapon_items", {})
                ):
                    return weapon_name
        for weapon_name in weapons:
            if weapon_name in self._weapon_instances:
                return weapon_name
        return None

    def _find_gear_item_by_id(self, item_id):
        """按 id 在背包或已装备槽位中查找物品。"""
        for it in getattr(self, "inventory", ()):
            if str(getattr(it, "id", None)) == str(item_id):
                return it
        for it in getattr(self, "_inventory_weapon_items", {}).values():
            if str(getattr(it, "id", None)) == str(item_id):
                return it
        armor = getattr(self, "_inventory_armor_item", None)
        if armor is not None and str(getattr(armor, "id", None)) == str(item_id):
            return armor
        return None

    def _stash_gear_item_on_equip(self, item):
        """装备时从背包移出物品（仍由单位持有）。"""
        inv = getattr(self, "inventory", None)
        if inv is not None and item in inv:
            inv.remove(item)

    def _return_gear_item_on_unequip(self, item):
        """卸下时将物品放回背包；若无空位则掉落在单位脚下。"""
        inv = getattr(self, "inventory", None)
        if inv is None or item in inv:
            return
        if getattr(self, "have_inventory_space", True):
            inv.append(item)
        else:
            item.move_to(self.place, self.x, self.y)

    def _spawn_starting_gear_to_inventory(self):
        """将出厂配置中同名 class item 的武器/护甲放入背包并静默装备。"""
        from ..definitions import rules
        from ..lib.log import warning

        weapon_names = getattr(type(self), "weapons", None) or []
        if isinstance(weapon_names, str):
            weapon_names = [weapon_names]
        for weapon_name in weapon_names:
            if not weapon_name or not self._is_item_gear_class(weapon_name, "weapon"):
                continue
            if not self.have_inventory_space:
                break
            try:
                item_class = rules.unit_class(weapon_name)
                item = item_class(self.place, self.x, self.y)
                item.move_to(None, 0, 0)
                self.inventory.append(item)
                item.equip(self)
                if (
                    getattr(type(self), "spawn_weapons_equipped", 1)
                    and not self._has_mixed_weapon_gear()
                ):
                    self._equip_weapon_item_silently(item)
            except Exception as e:
                warning(
                    f"Error spawning starting weapon item {weapon_name} "
                    f"for unit {self.type_name}: {e}"
                )

        armor_name = getattr(type(self), "armor", None)
        if armor_name and not isinstance(armor_name, (list, tuple)):
            if self._is_item_gear_class(armor_name, "armor") and self.have_inventory_space:
                try:
                    item_class = rules.unit_class(armor_name)
                    item = item_class(self.place, self.x, self.y)
                    item.move_to(None, 0, 0)
                    self.inventory.append(item)
                    item.equip(self)
                    if (
                        getattr(type(self), "spawn_armor_equipped", 1)
                        and not self._has_mixed_armor_gear()
                    ):
                        self._equip_armor_item_silently(item)
                except Exception as e:
                    warning(
                        f"Error spawning starting armor item {armor_name} "
                        f"for unit {self.type_name}: {e}"
                    )

    def _equip_weapon_item_silently(self, item):
        """静默装备背包武器（出厂时使用，不播报）。"""
        if item is None or not getattr(item, "is_weapon_item", False):
            return False
        if not hasattr(self, "weapons") or not self.weapons:
            self.weapons = []
        elif not isinstance(self.weapons, list):
            self.weapons = list(self.weapons)
        else:
            self.weapons = self.weapons[:]

        name = item.type_name
        self._weapon_instances[name] = self._make_weapon_instance_from_item(item)
        if name not in self.weapons:
            self.weapons.append(name)
        self._inventory_weapon_items[name] = item
        self._stash_gear_item_on_equip(item)
        return self._equip_weapon_silently(name)

    def _equip_armor_item_silently(self, item):
        """静默穿戴背包盔甲（出厂时使用，不播报）。"""
        if item is None or not getattr(item, "is_armor_item", False):
            return False
        if self._inventory_armor_item is None:
            self._armor_before_item = getattr(self, "armor", None)

        self._clear_armor_attributes()
        armor = self._make_armor_instance_from_item(item)
        self._armor_instance = armor
        self._armor = armor
        self.armor = item.type_name
        self._inventory_armor_item = item
        self._stash_gear_item_on_equip(item)
        armor.apply_to_unit(self)
        self._reapply_phase_armor_bonus()
        return True

    # 从 item 复制到动态武器实例的标量属性
    _ITEM_WEAPON_ATTRS = (
        "mdg", "rdg", "mdg_range", "rdg_range", "mdg_minimal_range",
        "rdg_minimal_range", "mdg_cd", "rdg_cd", "mdg_crit", "rdg_crit",
        "mdg_crit_rate", "rdg_crit_rate", "mdg_piercing", "rdg_piercing",
        "mdg_piercing_rate", "rdg_piercing_rate",
    )
    # 从 item 复制到动态护甲实例的标量属性
    _ITEM_ARMOR_ATTRS = (
        "mdf", "rdf", "mdf_crit_rate", "rdf_crit_rate", "mdf_piercing", "rdf_piercing",
    )

    def _make_weapon_instance_from_item(self, item):
        """根据背包物品的武器数值，动态创建一个 Weapon 实例。"""
        from ..worldweapon import Weapon

        weapon = Weapon(player=self.player)
        weapon.world = getattr(self, "world", None)
        weapon.type_name = item.type_name
        for attr in self._ITEM_WEAPON_ATTRS:
            if hasattr(item, attr):
                setattr(weapon, attr, getattr(item, attr))
        # 保存原始值以便科技升级计算
        weapon._original_mdg = weapon.mdg
        weapon._original_rdg = weapon.rdg
        weapon._original_mdg_cd = weapon.mdg_cd
        weapon._original_rdg_cd = weapon.rdg_cd
        weapon._original_mdg_range = weapon.mdg_range
        weapon._original_rdg_range = weapon.rdg_range
        if hasattr(item, "can_use_tech") and item.can_use_tech:
            weapon.can_use_tech = (
                list(item.can_use_tech)
                if isinstance(item.can_use_tech, (list, tuple))
                else [item.can_use_tech]
            )
        return weapon

    def _make_armor_instance_from_item(self, item):
        """根据背包物品的护甲数值，动态创建一个 Armor 实例。"""
        from ..worldarmor import Armor

        armor = Armor(player=self.player)
        armor.world = getattr(self, "world", None)
        armor.type_name = item.type_name
        for attr in self._ITEM_ARMOR_ATTRS:
            if hasattr(item, attr):
                setattr(armor, attr, getattr(item, attr))
        if hasattr(item, "can_use_tech") and item.can_use_tech:
            armor.can_use_tech = (
                list(item.can_use_tech)
                if isinstance(item.can_use_tech, (list, tuple))
                else [item.can_use_tech]
            )
        return armor

    def equip_weapon_item(self, item):
        """把背包里的物品作为武器装备到本单位（同型模型）。"""
        if item is None or not getattr(item, "is_weapon_item", False):
            return False
        if not self.can_equip_item_weapon():
            return False
        # 保证 weapons 是实例级列表，避免修改到类属性而影响同类单位
        if not hasattr(self, "weapons") or not self.weapons:
            self.weapons = []
        elif not isinstance(self.weapons, list):
            self.weapons = list(self.weapons)
        else:
            self.weapons = self.weapons[:]

        name = item.type_name
        self._weapon_instances[name] = self._make_weapon_instance_from_item(item)
        if name not in self.weapons:
            self.weapons.append(name)
        self._inventory_weapon_items[name] = item
        self._stash_gear_item_on_equip(item)

        # 装备背包武器（不走 switch_weapon，避免与内置武器互相切换）
        if self.current_weapon == name:
            self._clear_weapon_attributes()
            self._weapons = [self._weapon_instances[name]]
            self._weapon_instances[name].apply_to_unit(self)
            self._reapply_phase_weapon_bonus()
        else:
            self._equip_weapon_silently(name)
        self.notify(f"weapon_equipped,{name}")
        return True

    def unequip_weapon_item(self, item):
        """卸下作为武器装备的背包物品，恢复默认武器/基础属性。"""
        name = getattr(item, "type_name", None)
        if name is None or name not in self._inventory_weapon_items:
            return False
        stored = self._inventory_weapon_items.get(name)
        if stored is not item and getattr(stored, "id", None) != getattr(item, "id", None):
            return False
        del self._inventory_weapon_items[name]
        if isinstance(self.weapons, list) and name in self.weapons:
            self.weapons = [w for w in self.weapons if w != name]
        if name in self._weapon_instances:
            del self._weapon_instances[name]

        if self.current_weapon == name:
            self.current_weapon = None
            self._weapons = []
            self._clear_weapon_attributes()
            # 还原到第一个仍可用的武器（如果有）
            restorable = self._first_restorable_weapon()
            if restorable:
                self._equip_weapon_silently(restorable)
            else:
                self._reapply_phase_weapon_bonus()
        self._return_gear_item_on_unequip(item)
        self.notify(f"weapon_unequipped,{name}")
        return True

    def equip_armor_item(self, item):
        """把背包里的物品作为盔甲穿戴到本单位（同型模型）。"""
        if item is None or not getattr(item, "is_armor_item", False):
            return False
        if not self.can_equip_item_armor():
            return False
        # 记录原始护甲，便于卸下时还原
        if self._inventory_armor_item is None:
            self._armor_before_item = getattr(self, "armor", None)

        self._clear_armor_attributes()
        armor = self._make_armor_instance_from_item(item)
        self._armor_instance = armor
        self._armor = armor
        self.armor = item.type_name
        self._inventory_armor_item = item
        self._stash_gear_item_on_equip(item)
        armor.apply_to_unit(self)
        self._reapply_phase_armor_bonus()
        self.notify(f"armor_equipped,{item.type_name}")
        return True

    def unequip_armor_item(self, item):
        """卸下作为盔甲穿戴的背包物品，恢复原始护甲/基础属性。"""
        if self._inventory_armor_item is None:
            return False
        if (
            self._inventory_armor_item is not item
            and getattr(self._inventory_armor_item, "id", None) != getattr(item, "id", None)
        ):
            return False
        self._inventory_armor_item = None
        self._clear_armor_attributes()
        previous = self._armor_before_item
        self._armor_before_item = None
        self.armor = previous
        self._armor_instance = None
        self._armor = None
        if previous:
            # 还原回单位原本的护甲
            self._apply_armors()
        self._reapply_phase_armor_bonus()
        self._return_gear_item_on_unequip(item)
        self.notify(f"armor_unequipped,{getattr(item, 'type_name', '')}")
        return True

    def use_consumable_item(self, item):
        """使用（消耗）一个普通物品：触发其效果。

        返回 True 表示成功；False 表示失败；str 为失败原因（供 order_impossible 播报）。
        """
        if item is None:
            return False
        used = False
        # 优先使用 use_effect 指向的技能
        use_effect = getattr(item, "use_effect", None)
        if use_effect:
            try:
                from ..definitions import rules
                skill_class = rules.unit_class(use_effect)
                if skill_class is not None:
                    skill = skill_class()
                    if hasattr(skill, "execute_skill"):
                        skill.execute_skill(self, self, self.world)
                        used = True
            except Exception as e:
                from ..lib.log import warning
                warning(f"use_consumable_item: failed to run use_effect {use_effect}: {e}")
        # 技能书：永久学会物品携带的技能（等级要求见物品 learn_level / learn_level_skills
        # 与单位 learn_level_skills，取最高门槛）
        if not used:
            item_skills = getattr(item, "skills", None) or ()
            if item_skills:
                for skill_name in item_skills:
                    ok, reason = self._try_learn_skill(skill_name, item=item)
                    if not ok:
                        return reason
                return True
        # 退化：直接套用物品自身的 buffs
        if not used and getattr(item, "buffs", None):
            for b in item.buffs:
                try:
                    cls = self.world.unit_class(b)
                    if cls is not None:
                        cls(item, self)
                        used = True
                except Exception:
                    pass
        if not used and getattr(item, "resource_rewards", None):
            if any(r > 0 for r in item.resource_rewards):
                item.give_resource_rewards(self.player, self)
                used = True
        return used

    def is_inventory_weapon_item(self, item):
        """该物品当前是否作为武器被本单位装备。"""
        return item in getattr(self, "_inventory_weapon_items", {}).values()

    def is_inventory_armor_item(self, item):
        """该物品当前是否作为盔甲被本单位穿戴。"""
        armor = getattr(self, "_inventory_armor_item", None)
        return armor is not None and (
            armor is item or getattr(armor, "id", None) == getattr(item, "id", None)
        )

    def debug_armor_info(self):
        """调试用：输出当前护甲信息"""
        from ..lib.log import info
        info(f"=== 单位 {self.type_name}({self.id}) 护甲信息 ===")
        info(f"护甲配置: {getattr(self, 'armor', None)}")
        info(f"护甲实例: {self._armor_instance.type_name if self._armor_instance and hasattr(self._armor_instance, 'type_name') else '无'}")
        info(f"当前属性 - mdf: {getattr(self, 'mdf', 0)}, rdf: {getattr(self, 'rdf', 0)}")
        info(f"当前属性 - mdf_crit_rate: {getattr(self, 'mdf_crit_rate', 0)}, rdf_crit_rate: {getattr(self, 'rdf_crit_rate', 0)}")
        info(f"当前属性 - mdf_piercing: {getattr(self, 'mdf_piercing', 0)}, rdf_piercing: {getattr(self, 'rdf_piercing', 0)}")
        
        if self._armor_instance:
            armor = self._armor_instance
            info(f"护甲属性 - mdf: {getattr(armor, 'mdf', 0)}, rdf: {getattr(armor, 'rdf', 0)}")
            info(f"护甲属性 - mdf_crit_rate: {getattr(armor, 'mdf_crit_rate', 0)}, rdf_crit_rate: {getattr(armor, 'rdf_crit_rate', 0)}")
            info(f"护甲属性 - mdf_piercing: {getattr(armor, 'mdf_piercing', 0)}, rdf_piercing: {getattr(armor, 'rdf_piercing', 0)}")
        info("==========================================")
        
        # 通知客户端显示调试信息
        armor_name = getattr(self, 'armor', '无')
        self.notify(f"debug_info,护甲: {armor_name}, mdf: {getattr(self, 'mdf', 0)}, rdf: {getattr(self, 'rdf', 0)}")


