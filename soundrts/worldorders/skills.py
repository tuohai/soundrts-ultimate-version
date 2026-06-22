from ..definitions import VIRTUAL_TIME_INTERVAL, rules
from ..lib.nofloat import square_of_distance
from .base import ComplexOrder, Order
from ..worlditem import Item


class UseOrder(ComplexOrder):
    _previous_completeness = None
    is_imperative = True
    unit_menu_attribute = "can_use"
    keyword = "use"
    burst_target_type = "unit"
    harm_target_target_type = "unit"
    push_target_type = "unit"

    def __init__(self, unit, args):
        super().__init__(unit, args)
        self.cast_time = 0
        self.is_casting = False
        self.ready_end_time = 0


    def _notify_casting_progress(self):
        if self.type.time_cost == 0:
            return
            
        if self.cast_time < 0:
            t = 0
        else:
            t = self.cast_time
            
        # 计算完成度(0-10)
        c = int((self.type.time_cost - t) * 10 / self.type.time_cost)
        if c != self._previous_completeness:
            self.unit.notify("completeness,%s" % c)
            # 添加施法音效
            self.unit.notify("casting")
            self._previous_completeness = c

    def _ready_duration(self):
        ready = getattr(self.type, "ready", 0)
        if isinstance(ready, list):
            ready = ready[0] if ready else 0
        try:
            return int(ready)
        except (TypeError, ValueError):
            return 0

    @property
    def nb_args(self):
        if self.type.effect_target == ["ask"]:
            return 1
        return 0

    def _group_has_enough_mana(self, mana):
        if self.unit.player.group_had_enough_mana:
            return True
        # assertion: the order is recent (so player.group is relevant)
        # assertion: every unit in the group is concerned by the order
        for u in self.unit.player.group:
            if u.mana > mana:
                self.unit.player.group_had_enough_mana = True
                return True
        return False

    def _effect_range_to_target(self):
        effect_range = self.type.effect_range
        if hasattr(self.unit, "radius") and hasattr(self.target, "radius"):
            return effect_range + self.unit.radius + self.target.radius
        return effect_range

    @property
    def _target_type(self):
        # 安全地获取effect类型
        if hasattr(self.type, 'effect') and self.type.effect:
            if isinstance(self.type.effect, (list, tuple)):
                effect_type = self.type.effect[0]
            else:
                effect_type = self.type.effect
            return getattr(self, "%s_target_type" % effect_type, "square")
        return "square"

    @classmethod
    def _is_almost_allowed(cls, unit, type_name):
        if type_name in getattr(unit, cls.unit_menu_attribute):
            allowed = True
        elif hasattr(unit, "iter_manual_skill_names"):
            allowed = type_name in set(unit.iter_manual_skill_names())
        else:
            allowed = (
                hasattr(unit, "can_use_skill") and type_name in unit.can_use_skill
            )
        if not allowed:
            return False
        return (
            unit.player is not None
            and type_name not in unit.player.forbidden_techs
            and (not unit.orders or unit.orders[-1].can_be_followed)
            and cls.additional_condition(unit, type_name)
            and unit.player.check_count_limit(type_name)
        )

    @classmethod
    def menu(cls, unit, strict=False):
        is_allowed = cls.is_allowed if strict else cls._is_almost_allowed
        m = []
        # 添加can_use中的技能
        for t in getattr(unit, cls.unit_menu_attribute):
            if is_allowed(unit, t):
                m.append(cls.keyword + " " + t)
        # 已学会、可手动释放的技能（含 auto_trigger 与纯手动）
        if hasattr(unit, "iter_manual_skill_names"):
            skill_iter = unit.iter_manual_skill_names()
        elif hasattr(unit, "can_use_skill"):
            skill_iter = unit.can_use_skill
        else:
            skill_iter = ()
        for t in skill_iter:
            if t not in getattr(unit, cls.unit_menu_attribute) and is_allowed(unit, t):
                m.append(cls.keyword + " " + t)
        return m

    def on_queued(self):
        # 检查目标
        if self.type.effect_target == ["ask"]:
            if self.args:
                self.target = self.player.get_object_by_id(self.args[0])
            else:
                self.target = None
            if self.target is None:
                self.mark_as_impossible()
                return
            if self._target_type == "square":
                # make sure that the target is a square
                if not hasattr(self.target, "x"):
                    self.mark_as_impossible()
                    return
        elif self.type.effect_target == ["random"]:
            self.target = self.world.random.choice(self.player.world.squares)
        elif self.type.effect_target == ["self"]:
            self.target = self.unit
            
        # 检查资源消耗
        if any(self.type.cost):
            result = self.unit.check_if_enough_resources(self.type.cost)
            if result is not None:
                self.mark_as_impossible(result)
                return
                
        # 检查法力消耗
        if self.unit.mana < self.type.mana_cost:
            if self._group_has_enough_mana(self.type.mana_cost):
                self.mark_as_complete()  # ignore silently
            else:
                self.mark_as_impossible("not_enough_mana")
            return
                
        # 如果有资源消耗，先扣除资源
        if any(self.type.cost):
            self.player.pay(self.type.cost)
            
        # 如果有施法时间，初始化计时器
        if self.type.time_cost:
            self.cast_time = self.type.time_cost
            self.is_casting = True
            
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        if self.target is None:  # target has disappeared
            if any(self.type.cost):  # 如果目标消失，返还资源
                self.player.unpay(self.type.cost)
            self.mark_as_impossible()
            return
            
        # 检查是否正在施法
        if self.type.time_cost and self.is_casting:
            if self.cast_time > 0:
                self.cast_time -= VIRTUAL_TIME_INTERVAL
                self._notify_casting_progress()
                return  # 继续施法
            self.is_casting = False  # 施法完成
            
        # 使用技能类的is_cast_necessary方法检查是否需要释放
        try:
            if hasattr(self.type, 'is_cast_necessary') and not self.type.is_cast_necessary(self.unit, self.target):
                # 如果技能不需要释放，返还资源
                if any(self.type.cost):
                    self.player.unpay(self.type.cost)
                self.mark_as_complete()
                return
        except Exception:
            # 如果检查方法出错，继续执行技能
            pass
            
        # 检查施法距离
        effect_range = self._effect_range_to_target()
        if (
            square_of_distance(self.target.x, self.target.y, self.unit.x, self.unit.y)
            > effect_range * effect_range
        ):
            self.move_to_or_fail(self.target)  # move closer
            return
            
        self.unit.stop()
        
        # 检查法力值
        if self.unit.mana < self.type.mana_cost:
            if any(self.type.cost):
                self.player.unpay(self.type.cost)
            self.mark_as_impossible("not_enough_mana")
            return

        if hasattr(self.type, "validate_summon_target"):
            ok, reason = self.type.validate_summon_target(self.unit, self.target)
            if not ok:
                if any(self.type.cost):
                    self.player.unpay(self.type.cost)
                self.mark_as_impossible(reason or "cannot_build_here")
                return

        if self.unit.has_cooldown(self.type):
            self.mark_as_impossible("cooldown")
            return

        ready = self._ready_duration()
        if ready > 0:
            if self.ready_end_time <= 0:
                self.ready_end_time = self.world.time + ready
                self.unit.notify("skill_ready,%s" % self.type.type_name)
                return
            if self.world.time < self.ready_end_time:
                return

        # 执行技能效果 - 使用通用技能系统
        try:
            if hasattr(self.type, 'execute_skill'):
                success = self.type.execute_skill(self.unit, self.target, self.world)
                if not success:
                    # 技能执行失败时返还资源
                    if any(self.type.cost):
                        self.player.unpay(self.type.cost)
                    self.mark_as_impossible()
                    return
            else:
                # 技能类没有execute_skill方法，可能是旧的定义方式
                # 这种情况下我们默认技能执行成功
                pass
        except Exception as e:
            # 技能执行失败时返还资源
            if any(self.type.cost):
                self.player.unpay(self.type.cost)
            self.mark_as_impossible()
            return
            
        # 扣除法力值
        self.unit.mana -= self.type.mana_cost
        self.unit.add_cooldown(self.type)
        if hasattr(self.player, "record_skill_used"):
            self.player.record_skill_used(
                self.type.type_name, caster=self.unit, target=self.target
            )
        # 通知技能完成
        self.ready_end_time = 0
        self.unit.notify(
            "use_complete,%s" % self.type.type_name,
            universal=self.type.universal_notification,
        )
        
        # 应用技能属性效果
        if hasattr(self.unit, 'apply_skill_effect'):
            if self.type.effect_target == ["ask"] and self.target:
                self.unit.apply_skill_effect(self.type.type_name, self.target)
            elif self.type.effect_target == ["self"]:
                self.unit.apply_skill_effect(self.type.type_name)
            elif hasattr(self, "_target_effect_units"):
                # 如果技能有目标效果单位列表，对每个单位应用效果
                for target_unit in self._target_effect_units():
                    self.unit.apply_skill_effect(self.type.type_name, target_unit)
        
        self.mark_as_complete()



    @staticmethod
    def additional_condition(unused_unit, type_name):
        # 通用技能系统：检查技能是否可以使用
        e = rules.get(type_name, "effect")
        if not e:
            return False
            
        # 如果是字符串形式的effect（如rules.txt中定义的）
        if isinstance(e, str):
            effect_parts = e.split()
            if effect_parts and effect_parts[0] in {"bonus", "apply_bonus"}:
                return False  # 这些是upgrade效果，不是技能
        # 如果是列表形式的effect
        elif isinstance(e, (list, tuple)) and e:
            if e[0] in {"bonus", "apply_bonus"}:
                return False  # 这些是upgrade效果，不是技能
                
        return True  # 其他所有有effect的都认为是有效技能



class PickupOrder(Order):

    keyword = "pickup"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return unit.have_inventory_space

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if self.target is None:
            self.mark_as_impossible()
            return
        # 仅允许拾取物品类型
        if not isinstance(self.target, Item):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        # 仅允许拾取物品类型
        if self.target is None or not isinstance(self.target, Item) or not self.unit.have_inventory_space:
            self.mark_as_impossible()
        # 检查目标物品是否还有有效的位置
        elif (not hasattr(self.target, 'place') or 
              self.target.place is None or
              not hasattr(self.target.place, 'place')):
            # 物品位置无效，可能已被删除或移动到无效位置，直接尝试拾取
            self.mark_as_complete()
            self.unit.pickup(self.target)
        elif self.unit.place != self.target.place:
            self.move_to_or_fail(self.target.place)
        else:
            self.mark_as_complete()
            self.unit.pickup(self.target)

class DropOrder(Order):

    keyword = "drop"
    nb_args = 1

    @classmethod
    def _find_item(cls, unit, item_id):
        finder = getattr(unit, "_find_gear_item_by_id", None)
        if finder is not None:
            return finder(item_id)
        for item in getattr(unit, "inventory", ()):
            if str(getattr(item, "id", None)) == str(item_id):
                return item
        for item in getattr(unit, "_inventory_weapon_items", {}).values():
            if str(getattr(item, "id", None)) == str(item_id):
                return item
        armor = getattr(unit, "_inventory_armor_item", None)
        if armor is not None and str(getattr(armor, "id", None)) == str(item_id):
            return armor
        return None

    @classmethod
    def _has_droppable_item(cls, unit):
        if getattr(unit, "inventory", None):
            return True
        if getattr(unit, "_inventory_weapon_items", None):
            return True
        return getattr(unit, "_inventory_armor_item", None) is not None

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return hasattr(unit, "inventory") and cls._has_droppable_item(unit)

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    @classmethod
    def _first_inventory_item(cls, unit):
        inventory = getattr(unit, "inventory", None)
        if inventory:
            return inventory[0]
        return None

    def _resolve_place(self, place_id):
        from ..worldroom import Square

        obj = self.player.get_object_by_id(place_id)
        if obj is None or isinstance(obj, Item):
            return None
        if isinstance(obj, Square):
            return obj
        if hasattr(obj, "other_side"):
            return obj.other_side.place
        if getattr(obj, "player", None) is None and getattr(obj, "id", None) is not None:
            return obj
        return None

    def _unit_at_drop_place(self, target_place):
        """单位站在草地上时 place 是 Meadow，目标格是 Square，不能直接用 is 比较。"""
        if target_place is None:
            return True
        unit_place = self.unit.place
        if unit_place is target_place:
            return True
        if getattr(unit_place, "place", None) is target_place:
            return True
        return False

    def on_queued(self):
        self.item = None
        self.drop_place = None

        if len(self.args) >= 2 and self.args[0] and self.args[1]:
            self.item = self._find_item(self.unit, self.args[0])
            self.drop_place = self._resolve_place(self.args[1])
            if self.item is None or self.drop_place is None:
                self.mark_as_impossible()
                return
        elif self.args and self.args[0]:
            arg = self.args[0]
            item = self._find_item(self.unit, arg)
            if item is not None:
                self.item = item
            else:
                self.drop_place = self._resolve_place(arg)
                if self.drop_place is None:
                    self.mark_as_impossible()
                    return
                self.item = self._first_inventory_item(self.unit)
                if self.item is None:
                    self.mark_as_impossible()
                    return
        else:
            self.item = self._first_inventory_item(self.unit)
            if self.item is None:
                self.mark_as_impossible()
                return

        self.unit.notify("order_ok")

    def execute(self):
        item = getattr(self, "item", None)
        drop_place = getattr(self, "drop_place", None)
        if item is None:
            self.mark_as_impossible()
            return
        if self._find_item(self.unit, getattr(item, "id", None)) is not item:
            self.mark_as_impossible()
            return
        target_place = drop_place if drop_place is not None else self.unit.place
        if not self._unit_at_drop_place(target_place):
            self.move_to_or_fail(target_place)
        else:
            self.mark_as_complete()
            self.unit.drop(item)


class GiveOrder(Order):
    """把携带的物品交给另一个单位（包括中立/NPC单位）。

    用法：
        give <目标单位id>            把库存里的第一个物品交给目标
        give <目标单位id> <物品>     把指定物品（按物品id或type_name）交给目标

    主要用于战役/地图目标，例如"把某物品交给某NPC才能通关"。
    配合触发器条件 (npc_has_item <NPC> <物品>) 使用。
    """

    keyword = "give"
    nb_args = 1

    @classmethod
    def is_allowed(cls, unit, *unused_args):
        return hasattr(unit, "inventory") and len(unit.inventory) > 0

    @classmethod
    def menu(cls, unit, strict=False):
        if cls.is_allowed(unit):
            return [cls.keyword]
        else:
            return []

    def _target_accepts(self, item):
        target = getattr(self, "target", None)
        accepts = getattr(target, "accepts_item", None)
        return callable(accepts) and accepts(item, self.unit)

    def _find_item(self):
        inventory = getattr(self.unit, "inventory", [])
        if not inventory:
            return None
        # 可选的第二个参数指定要交出的具体物品（按id或type_name）
        if len(self.args) >= 2 and self.args[1]:
            sel = self.args[1]
            for item in inventory:
                if str(item.id) == str(sel) or getattr(item, "type_name", None) == sel:
                    return item
            return None  # 显式指定的物品不在库存中
        # 未显式指定：优先选择目标"愿意接收"的第一件物品
        if getattr(self, "target", None) is not None:
            for item in inventory:
                if self._target_accepts(item):
                    return item
        return inventory[0]

    def _target_is_a_unit(self):
        # 目标必须是一个单位（拥有 player 属性），且不能是物品本身，
        # 并且该单位必须允许接收物品（receive_items 总开关）
        return (
            self.target is not None
            and not isinstance(self.target, Item)
            and getattr(self.target, "player", None) is not None
            and getattr(self.target, "can_receive_items", False)
        )

    def on_queued(self):
        self.target = self.player.get_object_by_id(self.args[0])
        if not self._target_is_a_unit():
            self.mark_as_impossible()
            return
        self.item = self._find_item()
        # 物品必须存在，且目标愿意接收（物品白名单 + 给予者关系白名单）
        if self.item is None or not self._target_accepts(self.item):
            self.mark_as_impossible()
            return
        self.unit.notify("order_ok")

    def execute(self):
        self.update_target()
        item = getattr(self, "item", None)
        if (
            not self._target_is_a_unit()
            or item is None
            or item not in getattr(self.unit, "inventory", [])
            or not self._target_accepts(item)
        ):
            self.mark_as_impossible()
        elif self.unit.place != self.target.place:
            self.move_to_or_fail(self.target.place)
        else:
            self.mark_as_complete()
            self.unit.give(item, self.target)