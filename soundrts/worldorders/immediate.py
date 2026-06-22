from .base import Order


class ImmediateOrder(Order):

    never_forget_previous = True

    def immediate_action(self):
        cmd = "immediate_order_" + self.keyword
        getattr(self.unit, cmd)(*self.args)

class ToggleCounterattackOrder(ImmediateOrder):
    """切换反击模式的命令"""
    keyword = "toggle_counterattack"
    nb_args = 0
    population_cost = 0  # 确保不检查食物消耗
# 确保命令被注册到字典中

    @classmethod
    def menu(cls, unit, strict=False):
        # 如果是建筑物，直接返回空列表，不显示任何命令
        if hasattr(unit, "is_a_building") and unit.is_a_building:
            return []
            
        # 对于非建筑物单位，保持原有逻辑
        if cls.is_allowed(unit):
            if unit.counterattack_enabled:
                return ["disable_counterattack"]
            else:
                return ["enable_counterattack"]
        return []




class EnableCounterattack(ToggleCounterattackOrder):
    keyword = "enable_counterattack"
    
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return hasattr(unit, "counterattack_enabled") and not unit.counterattack_enabled

    def immediate_action(self):
        self.unit.counterattack_enabled = True
        self.unit.notify("order_ok")


class DisableCounterattack(ToggleCounterattackOrder):
    keyword = "disable_counterattack"
    
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return hasattr(unit, "counterattack_enabled") and unit.counterattack_enabled

    def immediate_action(self):
        self.unit.counterattack_enabled = False
        self.unit.notify("order_ok")

class AttackKeyOrder(ImmediateOrder):
    """攻击键命令"""
    keyword = "attack_key"
    nb_args = 0
    population_cost = 0

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查单位是否可以攻击
        return hasattr(unit, 'damage') and unit.damage > 0

    def immediate_action(self):
        # 执行攻击命令
        if self.unit.target is not None:
            self.unit.take_order(["attack", self.unit.target.id])
        self.unit.notify("order_ok")


class SwitchWeaponOrder(ImmediateOrder):
    """切换武器命令"""
    keyword = "switch_weapon"
    nb_args = 0
    population_cost = 0

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查单位是否有多个武器可以切换
        return (hasattr(unit, 'weapons') and 
                hasattr(unit, 'get_available_weapons') and
                len(unit.get_available_weapons()) > 1)

    def immediate_action(self):
        # 切换到下一个武器
        if not self.unit.next_weapon():
            self.unit.notify("order_impossible")


class SwitchToWeaponOrder(ImmediateOrder):
    """切换到指定武器命令"""
    keyword = "switch_to_weapon"
    nb_args = 1
    population_cost = 0

    @classmethod
    def is_allowed(cls, unit, weapon_name=None):
        # 检查单位是否有指定的武器
        if not (hasattr(unit, 'weapons') and hasattr(unit, 'get_available_weapons')):
            return False

        available_weapons = unit.get_available_weapons()
        if weapon_name is None or weapon_name not in available_weapons:
            return False
        current_weapon = getattr(unit, "current_weapon", None)
        if current_weapon and not unit._can_switch_between_weapons(current_weapon, weapon_name):
            return False
        if len(available_weapons) > 1:
            return True
        # 出厂未装备时仅有一把内置武器，允许装备
        return current_weapon != weapon_name

    def immediate_action(self):
        weapon_name = self.args[0] if self.args else None
        if not (weapon_name and self.unit.switch_weapon(weapon_name)):
            self.unit.notify("order_impossible")


class ToggleAutoWeaponSwitchOrder(ImmediateOrder):
    """切换自动武器切换功能的命令"""
    keyword = "toggle_auto_weapon_switch"
    nb_args = 0
    population_cost = 0

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 检查单位是否有多个武器
        return (hasattr(unit, 'weapons') and unit.weapons and len(unit.weapons) > 1)

    def immediate_action(self):
        # 切换自动武器切换状态
        if hasattr(self.unit, 'auto_weapon_switch'):
            self.unit.auto_weapon_switch = not self.unit.auto_weapon_switch
            # 通知状态改变
            if self.unit.auto_weapon_switch:
                self.unit.notify("auto_weapon_switch_enabled")
            else:
                self.unit.notify("auto_weapon_switch_disabled")
        else:
            self.unit.notify("order_impossible")


class EnableAutoWeaponSwitchOrder(ToggleAutoWeaponSwitchOrder):
    """启用自动武器切换命令"""
    keyword = "enable_auto_weapon_switch"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 只有当前自动武器切换关闭时才允许启用
        return (super().is_allowed(unit) and 
                hasattr(unit, 'auto_weapon_switch') and 
                not unit.auto_weapon_switch)

    def immediate_action(self):
        self.unit.auto_weapon_switch = True
        self.unit.notify("auto_weapon_switch_enabled")


class DisableAutoWeaponSwitchOrder(ToggleAutoWeaponSwitchOrder):
    """禁用自动武器切换命令"""
    keyword = "disable_auto_weapon_switch"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 只有当前自动武器切换开启时才允许禁用
        return (super().is_allowed(unit) and 
                hasattr(unit, 'auto_weapon_switch') and 
                unit.auto_weapon_switch)

    def immediate_action(self):
        self.unit.auto_weapon_switch = False
        self.unit.notify("auto_weapon_switch_disabled")


class StopOrder(ImmediateOrder):

    keyword = "stop"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return not unit.is_idle or unit.orders

    def immediate_action(self):
        # 检查是否正在生产资源，如果是则停止生产并返还资源
        if getattr(self.unit, "is_producing", False):
            # 添加调试日志
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log(f"执行通用停止命令，同时停止生产，当前进度: {self.unit.production_progress}/{self.unit.production_time}")
            
            # 只有在生产未完成时才返还资源
            if getattr(self.unit, "production_progress", 0) < getattr(self.unit, "production_time", 0):
                # 需要从production模块导入StopProduceOrder
                from .production import StopProduceOrder
                # 使用StopProduceOrder中相同的方法计算修正后的生产成本
                # 创建临时StopProduceOrder对象来使用其_calculate_production_cost方法
                temp_order = StopProduceOrder(self.unit, [])
                production_cost = temp_order._calculate_production_cost()
                
                # 记录返还前的资源量
                if hasattr(self.unit, "debug_log"):
                    before_resources = self.player.resources[:]
                    self.unit.debug_log(f"返还资源前: {before_resources}, 返还金额: {production_cost}")
                
                # 返还资源
                self.player.unpay(production_cost)
                
                # 记录返还后的资源量
                if hasattr(self.unit, "debug_log"):
                    after_resources = self.player.resources[:]
                    self.unit.debug_log(f"返还资源后: {after_resources}")
            else:
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"生产已完成，无需返还资源")
            
            # 重置生产状态
            self.unit.is_producing = False
            self.unit.production_progress = 0
            if hasattr(self.unit, "_previous_completeness"):
                self.unit._previous_completeness = None
            
            # 重要：重置生产模式，防止自动重启
            if hasattr(self.unit, "current_production_mode"):
                old_mode = getattr(self.unit, "current_production_mode", None)
                self.unit.current_production_mode = None
                if hasattr(self.unit, "debug_log"):
                    self.unit.debug_log(f"重置生产模式: {old_mode} -> None，防止自动重启")
            
            # 设置用户手动停止标志，防止自动重启逻辑再次启动生产
            self.unit._user_manually_stopped = True
            if hasattr(self.unit, "debug_log"):
                self.unit.debug_log("设置用户手动停止标志，防止自动重启")
            
            # 移除ProducingOrder或PlowingOrder
            for i, order in enumerate(self.unit.orders[:]):
                if (hasattr(order, "keyword") and 
                    (order.keyword == "producing" or order.keyword == "plowing")):
                    self.unit.orders.pop(i)
                    break
        
        # 在取消命令前，标记所有BuildOrder为不需返还资源
        # 因为BuildOrder.resources_reserved字段已经跟踪了资源状态
        for order in self.unit.orders[:]:
            if hasattr(order, 'resources_reserved') and order.resources_reserved:
                # 当命令已经预留了资源，我们需要确保资源正确返还一次
                # 在cancel_all_orders中会处理返还逻辑
                pass
                
        # 然后正常取消所有命令
        self.unit.cancel_all_orders()
        self.unit.stop()
        
        # 停止后切换回默认武器
        if hasattr(self.unit, 'switch_to_default_weapon'):
            self.unit.switch_to_default_weapon()
        
        self.unit.notify("order_ok")


class ImmediateCancelOrder(ImmediateOrder):
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.orders and unit.orders[-1].cancel_order == cls.keyword

    def immediate_action(self):
        self.unit.orders.pop().cancel()


class CancelTrainingOrder(ImmediateCancelOrder):

    keyword = "cancel_training"


class CancelUpgradingOrder(ImmediateCancelOrder):

    keyword = "cancel_upgrading"


class CancelChangingOrder(ImmediateCancelOrder):

    keyword = "cancel_changing"


class CancelBuildingOrder(ImmediateOrder):

    keyword = "cancel_building"

    def immediate_action(self):
        self.unit.player.unpay(self.unit.type.cost)
        self.unit.die()


class EnableAutoGather(ImmediateOrder):

    keyword = "enable_auto_gather"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 首先检查基本条件
        if not (hasattr(unit, "auto_gather") and not unit.auto_gather):
            return False
        
        from ..worldunit.worldworker import Worker
        return Worker.has_gather_permissions(unit)

    def immediate_action(self):
        self.unit.auto_gather = True
        self.unit.notify("order_ok")


class DisableAutoGather(ImmediateOrder):

    keyword = "disable_auto_gather"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 首先检查基本条件
        if not (hasattr(unit, "auto_gather") and unit.auto_gather):
            return False
        
        from ..worldunit.worldworker import Worker
        return Worker.has_gather_permissions(unit)

    def immediate_action(self):
        self.unit.auto_gather = False
        self.unit.notify("order_ok")


class EnableAutoRepair(ImmediateOrder):

    keyword = "enable_auto_repair"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 首先检查基本条件
        if not (hasattr(unit, "auto_repair") and not unit.auto_repair):
            return False
        
        # 检查can_repair参数
        if hasattr(unit, "can_repair"):
            # 如果can_repair为0，则不允许auto_repair命令
            if not getattr(unit, "can_repair", 0):
                return False
        
        return True

    def immediate_action(self):
        self.unit.auto_repair = True
        self.unit.notify("order_ok")


class DisableAutoRepair(ImmediateOrder):

    keyword = "disable_auto_repair"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 首先检查基本条件
        if not (hasattr(unit, "auto_repair") and unit.auto_repair):
            return False
        
        # 检查can_repair参数
        if hasattr(unit, "can_repair"):
            # 如果can_repair为0，则不允许auto_repair命令
            if not getattr(unit, "can_repair", 0):
                return False
        
        return True

    def immediate_action(self):
        self.unit.auto_repair = False
        self.unit.notify("order_ok")


class EnableAutoExplore(ImmediateOrder):

    keyword = "enable_auto_explore"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 仅人类玩家、且该单位类型在 rules.txt 里开放了自动探索选项
        # （can_auto_explore 1）、可移动、当前未开启自动探索时可启用。
        if not unit.player.is_human:
            return False
        if not getattr(unit, "can_auto_explore", False):
            return False
        if getattr(unit, "auto_explore", False):
            return False
        return getattr(unit, "speed", 0) > 0

    def immediate_action(self):
        self.unit.auto_explore = True
        self.unit.notify("order_ok")


class DisableAutoExplore(ImmediateOrder):

    keyword = "disable_auto_explore"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 人类玩家、且当前正处于自动探索状态时可禁用。
        # 注意：即使未配置 can_auto_explore，只要当前 auto_explore 为开
        # （例如作者用 auto_explore 1 设了开局默认开启），也允许关闭，
        # 避免出现"开着却关不掉"的死角。
        if not unit.player.is_human:
            return False
        return bool(getattr(unit, "auto_explore", False))

    def immediate_action(self):
        self.unit.auto_explore = False
        # 立即停止正在进行的自动探索命令（其余命令保持不变）
        if self.unit.orders and getattr(self.unit.orders[0], "keyword", None) == "auto_explore":
            self.unit.cancel_all_orders()
        self.unit.notify("order_ok")


class ModeOffensive(ImmediateOrder):
    keyword = "mode_offensive"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and (unit.ai_mode == "chase")

    def immediate_action(self):
        self.unit.ai_mode = "offensive"
        self.unit.notify("order_ok")


class ModeDefensive(ImmediateOrder):
    keyword = "mode_defensive"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and (unit.ai_mode == "offensive")

    def immediate_action(self):
        self.unit.ai_mode = "defensive"
        self.unit.notify("order_ok")

class ModeGuard(ImmediateOrder):
    keyword = "mode_guard"

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and (unit.ai_mode == "defensive")
        
    def immediate_action(self):
        self.unit.ai_mode = "guard"
        self.unit.notify("order_ok")

class ModeChase(ImmediateOrder):
    keyword = "mode_chase"
    
    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode and (unit.ai_mode == "guard")
        
    def immediate_action(self):
        self.unit.ai_mode = "chase"
        self.unit.notify("order_ok")

class ModeToggle(ImmediateOrder):
    """切换 AI 模式的命令"""
    keyword = "toggle_ai_mode"
    nb_args = 0
    population_cost = 0

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            next_mode = {
                "offensive": "defensive",
                "defensive": "guard",
                "guard": "chase",
                "chase": "offensive"
            }[unit.ai_mode]
            return [f"mode_{next_mode}"]
        return []

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.can_switch_ai_mode

    def immediate_action(self):
        next_mode = {
            "offensive": "defensive",
            "defensive": "guard",
            "guard": "chase",
            "chase": "offensive"
        }[self.unit.ai_mode]
        self.unit.ai_mode = next_mode
        self.unit.notify("order_ok")

class RallyingPointOrder(ImmediateOrder):

    keyword = "rallying_point"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        # 需要从production模块导入TrainOrder
        from .production import TrainOrder
        return TrainOrder.menu(unit)

    def immediate_action(self):
        self.unit.rallying_point = self.args[0]
        self.unit.notify("order_ok")


class JoinGroupOrder(ImmediateOrder):

    keyword = "join_group"
    nb_args = 1

    def immediate_action(self):
        group_name = self.args[0]
        if group_name not in self.player.groups:
            self.player.groups[group_name] = []
        if self.unit.group != self.player.groups[group_name]:
            self.unit.group = self.player.groups[group_name]
            self.unit.group.append(self.unit)
            self.unit.notify("order_ok")


# ==================== 同型模型：背包物品装备/使用命令 ====================
# 这些命令以背包物品的 id 作为参数，由背包界面下发到服务器执行，
# 通过 order/command 管道保证确定性与多人同步安全。它们不出现在普通
# 命令菜单里（menu 返回空），仅供背包界面调用。


class _InventoryItemOrder(ImmediateOrder):
    """以库存物品 id 为参数的背包命令基类。"""

    nb_args = 1
    population_cost = 0

    @classmethod
    def menu(cls, unit, strict=False):
        # 背包命令不进入普通命令菜单
        return []

    @classmethod
    def _find_item(cls, unit, item_id):
        finder = getattr(unit, "_find_gear_item_by_id", None)
        if finder is not None:
            return finder(item_id)
        for it in getattr(unit, "inventory", ()):
            if str(getattr(it, "id", None)) == str(item_id):
                return it
        return None


class EquipWeaponOrder(_InventoryItemOrder):
    keyword = "equip_weapon"

    @classmethod
    def is_allowed(cls, unit, item_id=None, *unused_args):
        item = cls._find_item(unit, item_id)
        if item is None or not getattr(item, "is_weapon_item", False):
            return False
        checker = getattr(unit, "can_equip_item_weapon", None)
        return checker() if checker else True

    def immediate_action(self):
        self.unit.equip_weapon_item_order(self.args[0])


class UnequipWeaponOrder(_InventoryItemOrder):
    keyword = "unequip_weapon"

    @classmethod
    def is_allowed(cls, unit, item_id=None, *unused_args):
        item = cls._find_item(unit, item_id)
        if item is None:
            return False
        return bool(getattr(unit, "is_inventory_weapon_item", None)) and unit.is_inventory_weapon_item(item)

    def immediate_action(self):
        self.unit.unequip_weapon_item_order(self.args[0])


class EquipArmorOrder(_InventoryItemOrder):
    keyword = "equip_armor"

    @classmethod
    def is_allowed(cls, unit, item_id=None, *unused_args):
        item = cls._find_item(unit, item_id)
        if item is None or not getattr(item, "is_armor_item", False):
            return False
        checker = getattr(unit, "can_equip_item_armor", None)
        return checker() if checker else True

    def immediate_action(self):
        self.unit.equip_armor_item_order(self.args[0])


class EquipBuiltinArmorOrder(ImmediateOrder):
    """穿上出厂时未自动装备的内置护甲（class armor）。"""
    keyword = "equip_builtin_armor"
    nb_args = 0
    population_cost = 0

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        if not getattr(unit, "_is_builtin_armor_applied", None):
            return False
        if unit._is_item_gear_class(getattr(type(unit), "armor", None), "armor"):
            return False
        return (
            getattr(unit, "_armor_instance", None) is not None
            and not unit._is_builtin_armor_applied()
            and bool(getattr(unit, "can_equip_builtin_armor", None))
            and unit.can_equip_builtin_armor()
        )

    def immediate_action(self):
        if not getattr(self.unit, "_equip_builtin_armor", lambda: False)():
            self.unit.notify("order_impossible")


class UnequipArmorOrder(_InventoryItemOrder):
    keyword = "unequip_armor"

    @classmethod
    def is_allowed(cls, unit, item_id=None, *unused_args):
        item = cls._find_item(unit, item_id)
        if item is None:
            return False
        return bool(getattr(unit, "is_inventory_armor_item", None)) and unit.is_inventory_armor_item(item)

    def immediate_action(self):
        self.unit.unequip_armor_item_order(self.args[0])


class UseItemOrder(_InventoryItemOrder):
    keyword = "use_item"

    @classmethod
    def is_allowed(cls, unit, item_id=None, *unused_args):
        item = cls._find_item(unit, item_id)
        if item is None:
            return False
        # 武器/盔甲物品不可被"使用消耗"
        return not (getattr(item, "is_weapon_item", False) or getattr(item, "is_armor_item", False))

    def immediate_action(self):
        self.unit.use_item_order(self.args[0])