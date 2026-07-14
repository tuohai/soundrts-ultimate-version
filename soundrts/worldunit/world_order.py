
from ..lib.log import warning, debug

from ..worldorders import (
    ORDERS_DICT,
    BuildPhaseTwoOrder,
    GoOrder,
    RallyingPointOrder,
    UpgradeToOrder,
    ProducingOrder,
    StartProduceOrder,
)
from ..worldresource import Corpse, Deposit
from ..worldentity import Entity
from ..worlditem import Item

class CreatureOrders(Entity):
    def take_order(self, o, forget_previous=True, imperative=False, order_id=None):
        imperative_head = (
            self.orders
            and self.orders[0].is_imperative
        )
        # 强制命令进行中时，普通命令自动排队，不得替换队首强制命令（stop 除外）
        if (
            forget_previous
            and not imperative
            and imperative_head
            and o[0] != "stop"
        ):
            forget_previous = False
        # an imperative "go" order on a unit is an "attack" order
        # note: this could be done by the user interface
        if imperative and o[0] == "go":
            target = self.player.get_object_by_id(o[1])
            if getattr(target, "player", None) is not None:
                o[0] = "attack"
        if self.is_inside:
            self.notify("order_impossible")
            return
        cls = ORDERS_DICT.get(o[0])
        if cls is None:
            warning("unknown order: %s", o)
            return
        if not cls.is_allowed(self, *o[1:]):
            self.notify("order_impossible")
            return
        if forget_previous and not cls.never_forget_previous:
            self.cancel_all_orders()
        # 强制命令后只允许一个排队命令：新的普通命令替换已有排队项
        if (
            not imperative
            and imperative_head
            and o[0] != "stop"
            and len(self.orders) >= 2
        ):
            while len(self.orders) > 1:
                self.orders.pop().cancel()
        order = cls(self, o[1:])
        order.id = order_id
        if imperative:
            order.is_imperative = imperative
        order.immediate_action()

    def _target_is_enter_container(self, target):
        return (
            getattr(target, "player", None) is self.player
            and hasattr(target, "have_enough_space")
            and target.have_enough_space(self)
        )

    def _target_needs_imperative_repair(self, target):
        from ..worldunit.worldcreature import BuildingSite

        if self.is_an_enemy(target):
            return False
        if hasattr(self, "can_repair") and not self.can_repair:
            return False
        if (
            isinstance(target, BuildingSite)
            and target.type.__name__ in getattr(self, "can_build", ())
        ) or (
            hasattr(target, "is_repairable")
            and target.is_repairable
            and target.hp < target.hp_max
            and self.can_build
        ):
            return True
        if (
            hasattr(target, "can_be_repaired_by_worker_from_shore")
            and target.can_be_repaired_by_worker_from_shore(self)
            and self.can_build
            and getattr(self, "can_repair_ships", 0)
        ):
            return True
        return False

    def _target_is_herdable_animal(self, target):
        return (
            getattr(type(target), "herdable", 0)
            or getattr(target, "herdable", 0)
        ) and "herd" in self.basic_skills and getattr(target, "hp", 0) > 0

    @staticmethod
    def _unit_can_capture(unit):
        return bool(getattr(unit, "can_capture", 1))

    def _capture_on_contact_default_order(self, target):
        """夺取阈值 100 的敌方单位/建筑：默认命令为移动并占领。"""
        if (
            target is not self
            and getattr(target, "hp", 0) > 0
            and getattr(target, "is_vulnerable", False)
            and getattr(target, "capture_hp_threshold", 0) == 100
            and "attack" in self.basic_skills
            and self._unit_can_capture(self)
            and self.player
            and target.player
            and self.player.player_is_an_enemy(target.player)
        ):
            return "capture"

        return None

    def _imperative_default_order_keyword(self, target_id):
        """Ctrl+退格解析：进入容器 → 修理 → 驱赶动物 → 否则强制攻击。"""
        target = self.player.get_object_by_id(target_id)
        if target is None:
            return None
        if self._target_is_enter_container(target):
            return "enter"
        if self._target_needs_imperative_repair(target):
            return "repair"
        if self._target_is_herdable_animal(target):
            return "herd"
        if (
            target is not self
            and getattr(target, "hp", 0) > 0
            and getattr(target, "is_vulnerable", False)
            and getattr(target, "player", None) is not None
            and "attack" in self.basic_skills
        ):
            return "attack"
        return None

    def resolve_imperative_go_order(self, target_id):
        """与 take_order 中 imperative go → attack 的转换一致。"""
        target = self.player.get_object_by_id(target_id)
        if (
            getattr(target, "player", None) is not None
            and "attack" in self.basic_skills
        ):
            return "attack"
        return "go"

    def get_resolved_default_order(self, target_id, imperative=False):
        """与 take_default_order 一致地解析默认命令（供客户端确认音使用）。"""
        if imperative:
            keyword = self._imperative_default_order_keyword(target_id)
            if keyword:
                return keyword
            order = self.get_default_order(target_id)
            if order == "go":
                return self.resolve_imperative_go_order(target_id)
            return order
        return self.get_default_order(target_id)

    def _take_imperative_default_order(
        self, target_id, forget_previous=True, order_id=None
    ):
        keyword = self._imperative_default_order_keyword(target_id)
        if keyword is None:
            return False
        self.take_order([keyword, target_id], forget_previous, True, order_id)
        return True

    def take_default_order(self, target_id, forget_previous=True, imperative=False, order_id=None
    ):
        if imperative and self._take_imperative_default_order(
            target_id, forget_previous, order_id
        ):
            return
        order = self.get_default_order(target_id)
        if order:
            self.take_order([order, target_id], forget_previous, imperative, order_id)
    def check_if_enough_resources(self, cost, food=0):
        for i, c in enumerate(cost):
            if self.player.resources[i] < c:
                return f"not_enough_resource{i + 1}"
        if (
                not self.orders
                and food > 0
                and self.player.available_food < self.player.used_food + food
        ):
            if self.player.available_food < self.world.food_limit:
                return "not_enough_food"
            else:
                return "population_limit_reached"
    def cancel_all_orders(self, unpay=True):
        while self.orders:
            self.orders.pop().cancel(unpay)
    def must_build(self, order):
        for o in self.orders:
            if o == order:
                return True

    def pickup(self, target):
        # 确保操作的是真实对象而不是记忆版本
        if hasattr(target, 'is_memory') and target.is_memory:
            target = target.initial_model
        
        # 仅允许拾取物品类型
        if not isinstance(target, Item):
            # 非物品目标，标记命令不可行并返回
            self.notify("order_impossible")
            return

        # 调用物品的on_pickup方法处理特殊逻辑
        consume_item = False
        if hasattr(target, 'on_pickup'):
            consume_item = target.on_pickup(self)
        
        # 由执行拾取的单位发送通知，与 drop 方法保持一致
        self.notify(f"pickup,{target.type_name}")
        
        if consume_item:
            # 如果物品应该被消耗（比如宝藏），延迟删除以避免客户端访问问题
            target.move_to(None, 0, 0)
            # 延迟删除，让客户端先处理完事件
            self.world.schedule_after(100, lambda: target.delete())  # 100ms后删除
        else:
            # 普通物品，添加到库存
            target.move_to(None, 0, 0)  # 正确地移除物品，提供x和y坐标
            self.inventory.append(target)
            target.equip(self)
    def _auto_unequip_item_systems(self, item):
        """若该物品当前作为武器/盔甲被装备（同型模型），在移出库存前先卸下，
        以确保单位的攻防属性正确还原。"""
        try:
            if getattr(self, "is_inventory_weapon_item", None) and self.is_inventory_weapon_item(item):
                self.unequip_weapon_item(item)
            if getattr(self, "is_inventory_armor_item", None) and self.is_inventory_armor_item(item):
                self.unequip_armor_item(item)
        except Exception:
            pass

    def drop(self, item):
        # 调用物品的on_drop方法处理特殊逻辑
        if hasattr(item, 'on_drop'):
            item.on_drop(self)
        
        # 同型模型：丢弃前先从武器/护甲系统卸下
        CreatureOrders._auto_unequip_item_systems(self, item)
        
        # 由执行丢弃的单位发送通知，确保客户端能收到
        self.notify(f"drop,{item.type_name}")
        
        # 确保物品在库存中，或先从装备槽卸下
        if hasattr(self, 'inventory') and item in self.inventory:
            item.move_to(self.place, self.x, self.y)
            self.inventory.remove(item)
            item.unequip(self)
        elif getattr(self, "is_inventory_weapon_item", None) and self.is_inventory_weapon_item(item):
            CreatureOrders._auto_unequip_item_systems(self, item)
            if hasattr(self, 'inventory') and item in self.inventory:
                item.move_to(self.place, self.x, self.y)
                self.inventory.remove(item)
                item.unequip(self)
            else:
                item.move_to(self.place, self.x, self.y)
                if hasattr(item, 'unequip'):
                    item.unequip(self)
        elif getattr(self, "is_inventory_armor_item", None) and self.is_inventory_armor_item(item):
            CreatureOrders._auto_unequip_item_systems(self, item)
            if hasattr(self, 'inventory') and item in self.inventory:
                item.move_to(self.place, self.x, self.y)
                self.inventory.remove(item)
                item.unequip(self)
            else:
                item.move_to(self.place, self.x, self.y)
                if hasattr(item, 'unequip'):
                    item.unequip(self)
        else:
            # 如果物品不在库存中，至少将其移动到单位位置
            item.move_to(self.place, self.x, self.y)
            if hasattr(item, 'unequip'):
                item.unequip(self)

    def give(self, item, target):
        """把库存里的物品 item 交给另一个单位 target（含中立/NPC单位）。

        物品会从本单位库存移除并转入目标单位库存。目标单位上会记录
        received_items 集合，供触发器条件 (npc_has_item ...) 检查。
        """
        # 确保操作的是真实对象而不是记忆版本
        if getattr(target, "is_memory", False):
            target = getattr(target, "initial_model", target)

        # 物品必须在本单位库存中
        if not hasattr(self, "inventory") or item not in self.inventory:
            self.notify("order_impossible")
            return

        # 目标必须是一个能持有物品的单位
        if getattr(target, "player", None) is None:
            self.notify("order_impossible")
            return

        # 目标必须接收该物品：receive_items + accepted_items + accept_from
        # + accept_givers，统一由 accepts_item 判定。
        accepts = getattr(target, "accepts_item", None)
        if not callable(accepts) or not accepts(item, self):
            self.notify("order_impossible")
            return

        # 同型模型：转交前先从武器/护甲系统卸下
        CreatureOrders._auto_unequip_item_systems(self, item)

        # 从本单位移除物品（解除装备效果）
        if hasattr(item, "unequip"):
            item.unequip(self)
        self.inventory.remove(item)

        # 通知（双方都播报，便于读屏与音效）
        self.notify(f"give,{item.type_name}")

        # 记录交付，供触发器使用（即使目标无法持有物品也记录）
        received = getattr(target, "received_items", None)
        if received is None:
            received = set()
            try:
                target.received_items = received
            except AttributeError:
                received = None
        if received is not None:
            received.add(item.type_name)

        # 把物品放入目标库存
        if hasattr(target, "inventory") and isinstance(target.inventory, list):
            item.move_to(None, 0, 0)
            target.inventory.append(item)
            if hasattr(item, "equip"):
                item.equip(target)
            target.notify(f"received,{item.type_name}")
        else:
            # 目标无法持有物品时，将物品掉落在目标所在位置
            item.move_to(target.place, target.x, target.y)

    def _find_inventory_item(self, item_id):
        """按 id 在背包或已装备槽位中查找物品。"""
        finder = getattr(self, "_find_gear_item_by_id", None)
        if finder is not None:
            return finder(item_id)
        for it in getattr(self, "inventory", ()):
            if str(getattr(it, "id", None)) == str(item_id):
                return it
        return None

    def equip_weapon_item_order(self, item_id):
        """装备库存中的武器物品（同型模型）。"""
        item = self._find_inventory_item(item_id)
        if item is None or not getattr(item, "is_weapon_item", False):
            self.notify("order_impossible")
            return
        if getattr(self, "equip_weapon_item", None):
            self.equip_weapon_item(item)

    def unequip_weapon_item_order(self, item_id):
        """卸下作为武器装备的库存物品（同型模型）。"""
        item = self._find_inventory_item(item_id)
        if item is None:
            self.notify("order_impossible")
            return
        if getattr(self, "unequip_weapon_item", None):
            self.unequip_weapon_item(item)

    def equip_armor_item_order(self, item_id):
        """穿戴库存中的盔甲物品（同型模型）。"""
        item = self._find_inventory_item(item_id)
        if item is None or not getattr(item, "is_armor_item", False):
            self.notify("order_impossible")
            return
        if getattr(self, "equip_armor_item", None):
            self.equip_armor_item(item)

    def unequip_armor_item_order(self, item_id):
        """脱下作为盔甲穿戴的库存物品（同型模型）。"""
        item = self._find_inventory_item(item_id)
        if item is None:
            self.notify("order_impossible")
            return
        if getattr(self, "unequip_armor_item", None):
            self.unequip_armor_item(item)

    def use_item_order(self, item_id):
        """使用（消耗）库存中的普通物品：触发效果并移出库存。"""
        item = self._find_inventory_item(item_id)
        if item is None:
            self.notify("order_impossible")
            return
        # 武器/盔甲物品不可"使用"消耗（应通过装备/穿戴流程）
        if getattr(item, "is_weapon_item", False) or getattr(item, "is_armor_item", False):
            self.notify("order_impossible")
            return
        use_square = getattr(item, "use_square", None)
        if use_square:
            player = getattr(self, "player", None)
            normalize = getattr(player, "_normalize_square_token", None)
            on_square = getattr(player, "_unit_on_square", None)
            if not callable(normalize) or not callable(on_square):
                self.notify("order_impossible")
                return
            square_key = normalize(use_square)
            if square_key is None or not on_square(self, square_key):
                self.notify("order_impossible")
                return
        used = False
        if getattr(self, "use_consumable_item", None):
            used = self.use_consumable_item(item)
        if isinstance(used, str):
            self.notify(f"order_impossible,{used}")
            return
        if not used:
            # 没有可用效果
            self.notify("order_impossible")
            return
        self.notify(f"use,{item.type_name}")
        keep_skills = bool(getattr(item, "skills", None))
        inv = getattr(self, "inventory", None)
        if inv is not None and item in inv:
            inv.remove(item)
        if hasattr(item, "unequip"):
            item.unequip(self, strip_skills=not keep_skills)
        item.move_to(None, 0, 0)
        if getattr(self, "world", None) is not None:
            self.world.schedule_after(100, lambda: item.delete())

    @staticmethod
    def _inventory_has_space(unit):
        """判断 unit 是否还有库存空间（镜像 have_inventory_space 的逻辑）。

        - 未定义 ``inventory_capacity``（None）：视为不限容量（兼容旧行为）。
        - ``inventory_capacity`` 为 0 或负数：不能持有物品。
        - 否则：当前库存数量 < 容量上限时才有空间。
        """
        cap = getattr(unit, "inventory_capacity", None)
        if cap is None:
            return True
        if isinstance(cap, (list, tuple)):
            cap = cap[0] if cap else 0
        try:
            cap = int(cap)
        except (ValueError, TypeError):
            cap = 0
        if cap <= 0:
            return False
        return len(getattr(unit, "inventory", ())) < cap

    def transfer_inventory_to(self, new_unit):
        """把本单位库存里的所有物品转移到 new_unit。

        用于单位"升级/变形"为另一种单位（删除旧单位、创建新单位）的场景：
        旧单位持有的物品必须随之转移到新单位身上，而不是凭空消失。

        转移时会先解除物品在旧单位上的装备效果（技能/buff），再装备到新单位上，
        以确保技能与 buff 正确绑定到新单位。

        若新单位没有足够的库存空间（例如 ``inventory_capacity 0`` 的单位无法
        持有物品），放不下的物品不会进入新单位库存，而是掉落在新单位所在位置，
        以免物品被静默销毁。
        """
        old_inventory = getattr(self, "inventory", None)
        if not old_inventory and not getattr(self, "_inventory_weapon_items", None) and not getattr(self, "_inventory_armor_item", None):
            return
        # 目标单位必须能够持有物品
        if not (hasattr(new_unit, "inventory") and isinstance(new_unit.inventory, list)):
            return
        # 先把已装备的武器/盔甲卸下（回到背包），再统一转移
        for item in list(getattr(self, "_inventory_weapon_items", {}).values()):
            if getattr(self, "unequip_weapon_item", None):
                try:
                    self.unequip_weapon_item(item)
                except Exception:
                    pass
        armor = getattr(self, "_inventory_armor_item", None)
        if armor is not None and getattr(self, "unequip_armor_item", None):
            try:
                self.unequip_armor_item(armor)
            except Exception:
                pass
        old_inventory = getattr(self, "inventory", None)
        if not old_inventory:
            return
        # 复制一份再遍历，避免在迭代过程中修改列表
        for item in list(old_inventory):
            # 解除物品在旧单位上的装备效果（取消 buff、移除技能）
            if hasattr(item, "unequip"):
                try:
                    item.unequip(self)
                except Exception:
                    pass
            if item in old_inventory:
                old_inventory.remove(item)
            if CreatureOrders._inventory_has_space(new_unit):
                # 放入新单位库存并重新装备
                item.move_to(None, 0, 0)
                new_unit.inventory.append(item)
                if hasattr(item, "equip"):
                    try:
                        item.equip(new_unit)
                    except Exception:
                        pass
            else:
                # 新单位放不下：把物品掉落在新单位所在位置，避免丢失
                item.move_to(
                    getattr(new_unit, "place", None),
                    getattr(new_unit, "x", 0),
                    getattr(new_unit, "y", 0),
                )