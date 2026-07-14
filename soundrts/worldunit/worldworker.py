from .worldbase import Unit
from ..worldresource import Deposit
from .worldcreature import BuildingSite
from ..worldorders import RallyingPointOrder, GoOrder

class Worker(Unit):

    ai_mode = "defensive"
    auto_gather = True
    auto_repair = True
    # 工人只在防御模式下才会根据AI自动撤退
    flee_only_in_defensive_mode = True
    can_switch_ai_mode = True
    can_repair = 1  # 0表示不允许修理，1表示允许修理
    can_herd = 0  # 0表示不允许驱赶，1表示允许（须在 rules.txt 显式开启）
    can_repair_ships = 0  # 0表示不允许修理船只，1表示允许
    build_mode = "assisted"  # assisted | place_and_leave | sacrifice
    _basic_skills = {"go", "attack", "herd", "gather", "repair", "block", "join_group", "pickup", "drop"}
    is_teleportable = True
    cargo = None  # gathered resource
    stat_type = "unit"
    # 可开采目标：矿床与建筑分开配置
    can_gather_deposit = None
    can_gather_building = None
    can_gather = None  # 已废弃，interpret 时迁移到上述两项
    # 资源采集时间和数量
    gather_time = {}  # 采集各类资源的时间
    gather_qty = {}   # 采集各类资源的数量

    def __init__(self, player, place, x, y, o=90):
        """初始化工人单位，确保ai_mode为defensive"""
        super().__init__(player, place, x, y, o)
        # 工人默认采用防御模式；若 rules.txt 为该单位定义了合法的 ai_mode，
        # 则尊重该配置（_resolve_default_ai_mode 已校验取值）。
        self.ai_mode = self._resolve_default_ai_mode("defensive")
        
        for attr in ("can_gather_deposit", "can_gather_building", "can_gather"):
            value = getattr(self, attr, None)
            if value is None:
                setattr(self, attr, None)
            else:
                setattr(self, attr, list(value))
        
        # 确保每个工人实例都有独立的gather_time属性
        if not hasattr(self, 'gather_time'):
            self.gather_time = {}
        else:
            # 创建类级别gather_time的副本，确保实例独立
            if isinstance(self.gather_time, dict):
                self.gather_time = dict(self.gather_time)
            else:
                self.gather_time = self.gather_time
        
        # 确保每个工人实例都有独立的gather_qty属性
        if not hasattr(self, 'gather_qty'):
            self.gather_qty = {}
        else:
            # 创建类级别gather_qty的副本，确保实例独立
            if isinstance(self.gather_qty, dict):
                self.gather_qty = dict(self.gather_qty)
            else:
                self.gather_qty = self.gather_qty

    @property
    def basic_skills(self):
        """动态返回基本技能，根据can_repair参数决定是否包含repair技能"""
        # 首先检查父类的条件（如是否在升级中）
        for o in self.orders:
            if hasattr(o, '__class__') and o.__class__.__name__ == 'UpgradeToOrder':
                return set()
        
        # 创建基本技能集合
        skills = set(self._basic_skills)
        
        # 如果can_repair为0，则移除repair技能
        if not getattr(self, 'can_repair', 0):
            skills.discard('repair')
        if not getattr(self, 'can_herd', 0):
            skills.discard('herd')

        return skills

    def take_default_order(self, target_id, forget_previous=True, imperative=False, order_id=None):
        super().take_default_order(
            target_id, forget_previous, imperative, order_id
        )

    def decide(self):
        # Computer AI workers almost never fight; Unit.decide → _choose_enemy was
        # ~15s / 10min for workers that mostly return at _cached_has_attack=False.
        player = self.player
        if not player.is_human:
            if (
                self.last_attacker is None
                and not self.mdg
                and not self.rdg
                and self.ai_mode != "defensive"
            ):
                return
            Unit.decide(self)
            return
        Unit.decide(self)
        if self.orders and self.orders[0].keyword != "gather":
            return
        if self.auto_repair and self.can_repair:  # 检查can_repair参数
            # 检查同一区域内的可修理单位
            for p in player.allied:
                for u in p.units:
                    if (
                        u.place is self.place
                        and u.is_repairable
                        and u.hp < u.hp_max
                        and not isinstance(u, BuildingSite)
                        and self.check_if_enough_resources(u.repair_cost) is None
                    ):
                        self.take_order(["repair", u.id])
                        return
            
            # 检查靠岸的船只（在相邻水域中的水上单位）
            if self.is_near_water and self.can_repair_ships:
                for p in player.allied:
                    for u in p.units:
                        if u.can_be_repaired_by_worker_from_shore(self):
                            if self.check_if_enough_resources(u.repair_cost) is None:
                                self.take_order(["repair", u.id])
                                return
        if self.orders:
            return
        if self.auto_gather:
            # 确保在自动收集前感知系统是最新的（避免游戏开始时的无效命令）
            if hasattr(player, 'force_perception_update'):
                player.force_perception_update()
            
            local_warehouses_resource_types = set()
            for w in self.place.objects:
                if w.player in player.allied:
                    local_warehouses_resource_types.update(w.storable_resource_types)
            if local_warehouses_resource_types:
                # 筛选可采集的资源
                deposits = []
                for o in self.place.objects:
                    # 检查是否是可采集的资源点或可采集的建筑物
                    if ((isinstance(o, Deposit) or
                         (hasattr(o, "is_a_building") and o.is_a_building and 
                          hasattr(o, "resource_type") and o.resource_type and 
                          hasattr(o, "resource_qty") and o.resource_qty > 0)) and 
                        o.resource_type in local_warehouses_resource_types):
                        
                        # 修改：使用新的采集权限检查逻辑
                        if not self._can_gather_target(o):
                            continue
                        deposits.append(o)
                        
                if deposits:
                    if (
                        self.cargo
                        and self.cargo[0] not in local_warehouses_resource_types
                    ):
                        self.cargo = None
                    o = self.world.random.choice(deposits)
                    self.take_order(["gather", o.id])

    def get_gather_time(self, resource_type, target=None):
        """获取采集指定目标的时间，支持严格区分deposit和resource
        
        Args:
            resource_type: 资源类型
            target: 目标对象（Deposit、Resource或建筑物），用于精确查找采集时间
            
        Returns:
            int: 最终的采集时间（以秒为单位）
        """
        # 确保gather_time是字典
        if not hasattr(self, 'gather_time'):
            self.gather_time = {}
        
        # 计算基础采集时间
        base_time = None
        
        # 首先检查是否只能开采一种目标且 gather_time 是简单值
        if self._single_gather_permission():
            if isinstance(self.gather_time, (int, float)):
                base_time = int(self.gather_time)
            elif isinstance(self.gather_time, str):
                try:
                    base_time = int(float(self.gather_time))
                except (ValueError, TypeError):
                    pass
            elif isinstance(self.gather_time, list) and self.gather_time:
                try:
                    base_time = int(float(self.gather_time[0]))
                except (ValueError, TypeError, IndexError):
                    pass
        
        # 如果还没有找到时间值，尝试根据目标对象的具体类型查找
        if base_time is None and target is not None:
            target_key = None
            if isinstance(target, Deposit):
                target_key = getattr(target, 'type_name', None)
                if target_key and isinstance(self.gather_time, dict) and target_key in self.gather_time:
                    time_value = self.gather_time[target_key]
                    if isinstance(time_value, list) and time_value:
                        base_time = int(time_value[0])
                    else:
                        base_time = int(time_value)
            elif hasattr(target, "is_a_building") and target.is_a_building:
                # 对于建筑物，使用resource_type
                target_key = resource_type
                if target_key and isinstance(self.gather_time, dict) and target_key in self.gather_time:
                    time_value = self.gather_time[target_key]
                    if isinstance(time_value, list) and time_value:
                        base_time = int(time_value[0])
                    else:
                        base_time = int(time_value)
        
        # 如果还没有找到时间值，使用原有的通用逻辑
        if base_time is None:
            if isinstance(self.gather_time, list):
                # 如果gather_time是列表，转换为字典
                gather_time_dict = {}
                for i in range(0, len(self.gather_time), 2):
                    if i + 1 < len(self.gather_time):
                        try:
                            key = self.gather_time[i]
                            value = int(self.gather_time[i + 1])
                            gather_time_dict[key] = value
                        except (ValueError, IndexError):
                            pass
                self.gather_time = gather_time_dict
                
            # 检查是否有定义特定资源类型的时间
            if isinstance(self.gather_time, dict) and resource_type in self.gather_time:
                time_value = self.gather_time[resource_type]
                # 确保返回整数，如果time_value是列表，取第一个元素并转换为整数
                if isinstance(time_value, list) and time_value:
                    base_time = int(time_value[0])
                else:
                    base_time = int(time_value)
            
            # 检查是否有定义 gather_time_resource# 格式的采集时间
            if base_time is None:
                attr_name = f"gather_time_{resource_type}"
                if hasattr(self, attr_name):
                    time_value = getattr(self, attr_name)
                    # 确保返回整数，如果time_value是列表，取第一个元素并转换为整数
                    if isinstance(time_value, list) and time_value:
                        base_time = int(time_value[0])
                    else:
                        base_time = int(time_value)
            
            # 检查是否有定义 gather_time_deposit名称 格式的采集时间（如 gather_time_wood）
            if base_time is None and target is not None:
                if isinstance(target, Deposit):
                    deposit_type = getattr(target, 'type_name', None)
                    if deposit_type:
                        attr_name = f"gather_time_{deposit_type}"
                        if hasattr(self, attr_name):
                            time_value = getattr(self, attr_name)
                            # 确保返回整数，如果time_value是列表，取第一个元素并转换为整数
                            if isinstance(time_value, list) and time_value:
                                base_time = int(time_value[0])
                            else:
                                base_time = int(time_value)
            
            # 检查是否有定义统一采集时间
            if base_time is None and isinstance(self.gather_time, dict) and "all" in self.gather_time:
                time_value = self.gather_time["all"]
                # 确保返回整数，如果time_value是列表，取第一个元素并转换为整数
                if isinstance(time_value, list) and time_value:
                    base_time = int(time_value[0])
                else:
                    base_time = int(time_value)
            
            # 如果gather_time直接是一个整数（对应简化定义：gather_time 1）
            if base_time is None:
                if isinstance(self.gather_time, int):
                    base_time = self.gather_time
                elif isinstance(self.gather_time, (str, float)):
                    try:
                        # 尝试将字符串或浮点数转换为整数
                        base_time = int(float(self.gather_time))
                    except (ValueError, TypeError):
                        pass
        
        # 如果仍然没有找到时间值，使用默认值
        if base_time is None:
            base_time = 0
        
        # 考虑 target 的 extraction_time 影响
        if target is not None and hasattr(target, 'extraction_time') and target.extraction_time is not None:
            # 确保extraction_time是整数值
            extraction_time = target.extraction_time
            if isinstance(extraction_time, list) and extraction_time:
                # 如果是列表，取第一个元素作为提取时间
                try:
                    extraction_time = int(extraction_time[0])
                except (ValueError, TypeError):
                    extraction_time = 0
            elif not isinstance(extraction_time, (int, float)):
                try:
                    # 尝试将其他类型转换为整数
                    extraction_time = int(float(extraction_time))
                except (ValueError, TypeError):
                    extraction_time = 0
            
            # 应用资源点的时间修正（可以是负数，表示减少采集时间）
            base_time = base_time + extraction_time
        
        # 应用 gather_time_bonus 效果
        final_time = base_time
        if hasattr(self.player, 'gather_time_bonus') and self.player.gather_time_bonus:
            # 检查是否有资源特定的bonus
            if isinstance(self.player.gather_time_bonus, dict):
                # 支持资源特定的bonus: gather_time_bonus = {"wood": -7, "gold": -5}
                if resource_type in self.player.gather_time_bonus:
                    bonus_value = self.player.gather_time_bonus[resource_type]
                    if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                        # 处理百分比bonus
                        percent_value = float(bonus_value[:-1])
                        final_time = base_time * (1 + percent_value / 100)
                    else:
                        # 处理固定值bonus
                        final_time = base_time + int(bonus_value)
                # 检查是否有目标特定的bonus（如deposit名称）
                elif target is not None:
                    if isinstance(target, Deposit):
                        deposit_type = getattr(target, 'type_name', None)
                        if deposit_type and deposit_type in self.player.gather_time_bonus:
                            bonus_value = self.player.gather_time_bonus[deposit_type]
                            if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                                # 处理百分比bonus
                                percent_value = float(bonus_value[:-1])
                                final_time = base_time * (1 + percent_value / 100)
                            else:
                                # 处理固定值bonus
                                final_time = base_time + int(bonus_value)
                # 检查是否有通用bonus
                elif "all" in self.player.gather_time_bonus:
                    bonus_value = self.player.gather_time_bonus["all"]
                    if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                        # 处理百分比bonus
                        percent_value = float(bonus_value[:-1])
                        final_time = base_time * (1 + percent_value / 100)
                    else:
                        # 处理固定值bonus
                        final_time = base_time + int(bonus_value)
            else:
                # 处理简单的通用bonus值
                bonus_value = self.player.gather_time_bonus
                if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                    # 处理百分比bonus
                    percent_value = float(bonus_value[:-1])
                    final_time = base_time * (1 + percent_value / 100)
                else:
                    # 处理固定值bonus
                    final_time = base_time + int(bonus_value)
        
        # 确保至少需要0.1秒
        return max(0.1, final_time)

    def get_gather_qty(self, resource_type, target=None):
        """获取采集指定目标的数量，支持严格区分deposit和resource
        
        Args:
            resource_type: 资源类型
            target: 目标对象（Deposit、Resource或建筑物），用于精确查找采集数量
            
        Returns:
            int: 最终的采集数量
        """
        # 确保gather_qty是字典
        if not hasattr(self, 'gather_qty'):
            self.gather_qty = {}
        
        # 计算基础采集数量
        base_qty = None
        
        # 首先检查是否只能开采一种目标且 gather_qty 是简单值
        if self._single_gather_permission():
            if isinstance(self.gather_qty, (int, float)):
                base_qty = int(self.gather_qty)
            elif isinstance(self.gather_qty, str):
                try:
                    base_qty = int(float(self.gather_qty))
                except (ValueError, TypeError):
                    pass
            elif isinstance(self.gather_qty, list) and self.gather_qty:
                try:
                    base_qty = int(float(self.gather_qty[0]))
                except (ValueError, TypeError, IndexError):
                    pass
        
        # 如果还没有找到数量值，尝试根据目标对象的具体类型查找
        if base_qty is None and target is not None:
            target_key = None
            if isinstance(target, Deposit):
                # 对于Deposit，只使用deposit的type_name，不回退到resource_type
                target_key = getattr(target, 'type_name', None)
                if target_key and isinstance(self.gather_qty, dict) and target_key in self.gather_qty:
                    qty_value = self.gather_qty[target_key]
                    if isinstance(qty_value, list) and qty_value:
                        base_qty = int(qty_value[0])
                    else:
                        base_qty = int(qty_value)
            elif hasattr(target, "is_a_building") and target.is_a_building:
                # 对于建筑物，使用resource_type
                target_key = resource_type
                if target_key and isinstance(self.gather_qty, dict) and target_key in self.gather_qty:
                    qty_value = self.gather_qty[target_key]
                    if isinstance(qty_value, list) and qty_value:
                        base_qty = int(qty_value[0])
                    else:
                        base_qty = int(qty_value)
        
        # 如果还没有找到数量值，使用原有的通用逻辑
        if base_qty is None:
            if isinstance(self.gather_qty, list):
                # 如果gather_qty是列表，转换为字典
                gather_qty_dict = {}
                for i in range(0, len(self.gather_qty), 2):
                    if i + 1 < len(self.gather_qty):
                        try:
                            key = self.gather_qty[i]
                            value = int(self.gather_qty[i + 1])
                            gather_qty_dict[key] = value
                        except (ValueError, IndexError):
                            pass
                self.gather_qty = gather_qty_dict
                
            # 检查是否有定义特定资源类型的采集量
            if isinstance(self.gather_qty, dict) and resource_type in self.gather_qty:
                qty_value = self.gather_qty[resource_type]
                # 确保返回整数，如果qty_value是列表，取第一个元素并转换为整数
                if isinstance(qty_value, list) and qty_value:
                    base_qty = int(qty_value[0])
                else:
                    base_qty = int(qty_value)
            
            # 检查是否有定义 gather_qty_resource# 格式的采集量
            if base_qty is None:
                attr_name = f"gather_qty_{resource_type}"
                if hasattr(self, attr_name):
                    qty_value = getattr(self, attr_name)
                    # 确保返回整数，如果qty_value是列表，取第一个元素并转换为整数
                    if isinstance(qty_value, list) and qty_value:
                        base_qty = int(qty_value[0])
                    else:
                        base_qty = int(qty_value)
            
            # 检查是否有定义 gather_qty_deposit名称 格式的采集量（如 gather_qty_wood）
            if base_qty is None and target is not None:
                if isinstance(target, Deposit):
                    deposit_type = getattr(target, 'type_name', None)
                    if deposit_type:
                        attr_name = f"gather_qty_{deposit_type}"
                        if hasattr(self, attr_name):
                            qty_value = getattr(self, attr_name)
                            # 确保返回整数，如果qty_value是列表，取第一个元素并转换为整数
                            if isinstance(qty_value, list) and qty_value:
                                base_qty = int(qty_value[0])
                            else:
                                base_qty = int(qty_value)
            
            # 检查是否有定义统一采集量
            if base_qty is None and isinstance(self.gather_qty, dict) and "all" in self.gather_qty:
                qty_value = self.gather_qty["all"]
                # 确保返回整数，如果qty_value是列表，取第一个元素并转换为整数
                if isinstance(qty_value, list) and qty_value:
                    base_qty = int(qty_value[0])
                else:
                    base_qty = int(qty_value)
            
            # 如果gather_qty直接是一个整数
            if base_qty is None:
                if isinstance(self.gather_qty, int):
                    base_qty = self.gather_qty
                elif isinstance(self.gather_qty, (str, float)):
                    try:
                        # 尝试将字符串或浮点数转换为整数
                        base_qty = int(float(self.gather_qty))
                    except (ValueError, TypeError):
                        pass
        
        # 如果仍然没有找到数量值，使用默认值
        if base_qty is None:
            base_qty = 0
        
        # 考虑 target 的 extraction_qty 影响
        if target is not None and hasattr(target, 'extraction_qty') and target.extraction_qty is not None:
            # 确保extraction_qty是整数值
            extraction_qty = target.extraction_qty
            if isinstance(extraction_qty, list) and extraction_qty:
                # 如果是列表，取第一个元素作为提取数量
                try:
                    extraction_qty = int(extraction_qty[0])
                except (ValueError, TypeError):
                    extraction_qty = 0
            elif not isinstance(extraction_qty, (int, float)):
                try:
                    # 尝试将其他类型转换为整数
                    extraction_qty = int(float(extraction_qty))
                except (ValueError, TypeError):
                    extraction_qty = 0
            
            # 应用资源点的数量修正（应该是正数，增加采集量）
            base_qty = base_qty + extraction_qty
        
        # 应用 gather_qty_bonus 效果
        final_qty = base_qty
        if hasattr(self.player, 'gather_qty_bonus') and self.player.gather_qty_bonus:
            # 检查是否有资源特定的bonus
            if isinstance(self.player.gather_qty_bonus, dict):
                # 支持资源特定的bonus: gather_qty_bonus = {"wood": 2, "gold": 1}
                if resource_type in self.player.gather_qty_bonus:
                    bonus_value = self.player.gather_qty_bonus[resource_type]
                    if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                        # 处理百分比bonus
                        percent_value = float(bonus_value[:-1])
                        final_qty = base_qty * (1 + percent_value / 100)
                    else:
                        # 处理固定值bonus
                        final_qty = base_qty + int(bonus_value)
                # 检查是否有目标特定的bonus（如deposit名称）
                elif target is not None:
                    if isinstance(target, Deposit):
                        deposit_type = getattr(target, 'type_name', None)
                        if deposit_type and deposit_type in self.player.gather_qty_bonus:
                            bonus_value = self.player.gather_qty_bonus[deposit_type]
                            if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                                # 处理百分比bonus
                                percent_value = float(bonus_value[:-1])
                                final_qty = base_qty * (1 + percent_value / 100)
                            else:
                                # 处理固定值bonus
                                final_qty = base_qty + int(bonus_value)
                # 检查是否有通用bonus
                elif "all" in self.player.gather_qty_bonus:
                    bonus_value = self.player.gather_qty_bonus["all"]
                    if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                        # 处理百分比bonus
                        percent_value = float(bonus_value[:-1])
                        final_qty = base_qty * (1 + percent_value / 100)
                    else:
                        # 处理固定值bonus
                        final_qty = base_qty + int(bonus_value)
            else:
                # 处理简单的通用bonus值
                bonus_value = self.player.gather_qty_bonus
                if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                    # 处理百分比bonus
                    percent_value = float(bonus_value[:-1])
                    final_qty = base_qty * (1 + percent_value / 100)
                else:
                    # 处理固定值bonus
                    final_qty = base_qty + int(bonus_value)
        
        # 确保至少采集1个单位的资源
        return max(1, int(final_qty))

    @classmethod
    def interpret(cls, d):
        """处理Worker属性解析"""
        # 处理父类属性
        Unit.interpret(d)
        
        # 处理can_repair参数
        if "can_repair" in d:
            value = d["can_repair"]
            if isinstance(value, list):
                d["can_repair"] = int(value[0]) if value else 0
            else:
                d["can_repair"] = int(value)
        
        # 处理can_repair_ships参数 - 不要直接修改基类，而是设置到字典中
        # 这样每个工人类型都会有自己的can_repair_ships属性
        if "can_repair_ships" in d:
            # 将属性设置到字典中，而不是直接修改基类
            value = d["can_repair_ships"]
            if isinstance(value, list):
                d["can_repair_ships"] = int(value[0]) if value else 0
            else:
                d["can_repair_ships"] = int(value)
        
        # 可开采矿床 / 建筑（兼容旧版 can_gather）
        for key in ("can_gather_deposit", "can_gather_building"):
            if key in d:
                d[key] = cls._parse_gather_permission_list(d[key])
        if "can_gather" in d and "can_gather_deposit" not in d and "can_gather_building" not in d:
            legacy = cls._parse_gather_permission_list(d["can_gather"])
            dep, bld = cls._split_legacy_can_gather(legacy)
            d["can_gather_deposit"] = dep
            d["can_gather_building"] = bld
        d.pop("can_gather", None)
        
        # 解析资源采集时间
        gather_time = {}
        
        # 处理 gather_time resource1 10 resource2 15 格式
        if "gather_time" in d and isinstance(d["gather_time"], list) and len(d["gather_time"]) > 1:
            i = 0
            while i < len(d["gather_time"]) - 1:
                if d["gather_time"][i] == "all":
                    try:
                        gather_time["all"] = int(float(d["gather_time"][i + 1]))  # 转换为毫秒
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
                elif d["gather_time"][i].startswith("resource"):
                    try:
                        resource_type = d["gather_time"][i]
                        gather_time[resource_type] = int(float(d["gather_time"][i + 1]))  # 转换为毫秒
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
                else:
                    # 处理deposit名称，如 goldmine、wood等
                    try:
                        deposit_name = d["gather_time"][i]
                        gather_time[deposit_name] = int(float(d["gather_time"][i + 1]))  # 转换为毫秒
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
        
        # 处理 gather_time 10 格式（只有一个数值，适用于只能开采一种资源的工人）
        elif "gather_time" in d and (isinstance(d["gather_time"], str) or isinstance(d["gather_time"], int)):
            try:
                value = d["gather_time"] if isinstance(d["gather_time"], int) else d["gather_time"].strip()
                gather_time = int(float(value))  # 转换为毫秒
            except ValueError:
                pass
                
        # 处理 gather_time_resource# 和 gather_time_wood 等格式
        for key in d:
            if key.startswith("gather_time_") and key != "gather_time":
                try:
                    resource_type = key.replace("gather_time_", "")
                    value = d[key]
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0]
                    d[key] = int(float(value))  # 转换为毫秒
                except (ValueError, IndexError):
                    pass
        
        # 将gather_time设置到字典中
        if gather_time:
            d["gather_time"] = gather_time
        
        # 解析资源采集数量
        gather_qty = {}
        
        # 处理 gather_qty resource1 2 resource2 3 格式
        if "gather_qty" in d and isinstance(d["gather_qty"], list) and len(d["gather_qty"]) > 1:
            i = 0
            while i < len(d["gather_qty"]) - 1:
                if d["gather_qty"][i] == "all":
                    try:
                        gather_qty["all"] = int(d["gather_qty"][i + 1])
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
                elif d["gather_qty"][i].startswith("resource"):
                    try:
                        resource_type = d["gather_qty"][i]
                        gather_qty[resource_type] = int(d["gather_qty"][i + 1])
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
                else:
                    # 处理deposit名称，如 goldmine、wood等
                    try:
                        deposit_name = d["gather_qty"][i]
                        gather_qty[deposit_name] = int(d["gather_qty"][i + 1])
                        i += 2
                    except (ValueError, IndexError):
                        i += 1
        
        # 处理 gather_qty 2 格式（只有一个数值，适用于只能开采一种资源的工人）
        elif "gather_qty" in d and (isinstance(d["gather_qty"], str) or isinstance(d["gather_qty"], int)):
            try:
                value = d["gather_qty"] if isinstance(d["gather_qty"], int) else d["gather_qty"].strip()
                gather_qty = int(value)
            except ValueError:
                pass
                
        # 处理 gather_qty_resource# 和 gather_qty_wood 等格式
        for key in d:
            if key.startswith("gather_qty_") and key != "gather_qty":
                try:
                    resource_type = key.replace("gather_qty_", "")
                    value = d[key]
                    if isinstance(value, list) and len(value) > 0:
                        value = value[0]
                    d[key] = int(value)
                except (ValueError, IndexError):
                    pass
        
        # 将gather_qty设置到字典中
        if gather_qty:
            d["gather_qty"] = gather_qty 

    def get_default_order(self, target_id):
        from ..worlditem import Item
        
        target = self.player.get_object_by_id(target_id)
        if not target:
            return
        elif getattr(target, "is_an_exit", False):
            return "block"
        elif getattr(target, "player", None) is self.player and self.have_enough_space(
                target
        ):
            return "load"
        elif getattr(target, "player", None) is self.player and target.have_enough_space(self):
            return "enter"
        # 检查是否是物品
        elif isinstance(target, Item) and self.have_inventory_space:
            return "pickup"

        elif (
            getattr(target, "herdable", 0)
            and "herd" in self.basic_skills
            and getattr(target, "hp", 0) > 0
        ):
            return "herd"

        elif (
            getattr(target, "is_huntable", 0)
            and "attack" in self.basic_skills
            and getattr(target, "hp", 0) > 0
        ):
            return "attack"

        capture_order = self._capture_on_contact_default_order(target)
        if capture_order:
            return capture_order

        # 修改：检查目标是否是可开采的建筑物（具有resource_type属性）
        elif "gather" in self.basic_skills and (
            isinstance(target, Deposit) or
            (hasattr(target, "is_a_building") and target.is_a_building and
             hasattr(target, "resource_type") and target.resource_type)
        ):
            # 添加：检查目标是否是敌方建筑物，如果是敌方建筑则不开采
            if hasattr(target, "player") and target.player and self.is_an_enemy(target):
                return "go"  # 敌方可开采建筑，默认使用"go"命令而非"gather"
                
            # 检查工人是否可以采集此目标
            if not self._can_gather_target(target):
                return "go"
                
            # 检查资源是否耗尽
            if hasattr(target, "resource_qty") and target.resource_qty <= 0:
                return "go"  # 资源已耗尽，返回go命令
            return "gather"
        elif (
                isinstance(target, BuildingSite)
                and target.type.__name__ in self.can_build
                or hasattr(target, "is_repairable")
                and target.is_repairable
                and target.hp < target.hp_max
                and self.can_build
                and self.can_repair  # 检查can_repair参数
        ) and not self.is_an_enemy(target):
            return "repair"
        # 检查靠岸的船只是否可以修理
        elif (hasattr(target, "can_be_repaired_by_worker_from_shore") and 
              target.can_be_repaired_by_worker_from_shore(self) and
              self.can_build and
              self.can_repair and  # 检查can_repair参数
              self.can_repair_ships and
              not self.is_an_enemy(target)):
            return "repair"
        # 携带物品时，右键能接收所携带物品的单位（含NPC/中立单位）= 交给该单位
        elif (
            getattr(target, "player", None) is not None
            and target is not self
            and not getattr(target, "is_a_building", False)
            and getattr(self, "inventory", None)
            and callable(getattr(target, "accepts_item", None))
            and any(target.accepts_item(it, self) for it in self.inventory)
        ):
            return "give"
        elif RallyingPointOrder.is_allowed(self):
            return "rallying_point"
        elif GoOrder.is_allowed(self):
            return "go" 

    @staticmethod
    def _get_deposit_resource_type_mapping():
        """从rules系统动态获取deposit名称到resource_type的映射表"""
        from ..definitions import rules
        mapping = {}
        
        try:
            # 遍历所有定义的对象名称
            for obj_name in rules.classnames():
                # 检查对象是否为deposit类
                if rules.get(obj_name, "class") == ["deposit"]:
                    # 获取其resource_type
                    resource_type = rules.get(obj_name, "resource_type")
                    if resource_type:
                        mapping[obj_name] = resource_type
        except Exception as e:
            # 如果动态获取失败，使用基本的硬编码映射作为后备
            from ..lib.log import warning
            warning(f"Failed to get deposit mapping from rules: {e}")
            mapping = {
                'goldmine': 'resource1',
                'wood': 'resource2',
                'orchard': 'resource3',
            }
        
        return mapping
    
    @staticmethod
    def _parse_gather_permission_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return list(value)
        return value.split()

    @staticmethod
    def _rules_dict_for_interpret():
        rules_dict = getattr(Worker, "_interp_rules_dict", None)
        if rules_dict is not None:
            return rules_dict
        from ..definitions import rules
        return getattr(rules, "_dict", {})

    @staticmethod
    def _rules_entry(name, key, default=None):
        entry = Worker._rules_dict_for_interpret().get(name) or {}
        value = entry.get(key, default)
        if isinstance(value, list) and len(value) == 1 and key != "is_a":
            return value[0]
        return value

    @staticmethod
    def _legacy_gather_entry_kind(name):
        """推断旧版 can_gather 条目的目标类型（interpret 阶段尚无 unit_class）。"""
        obj_class = Worker._rules_entry(name, "class")
        if obj_class == "deposit" or obj_class == ["deposit"]:
            return "deposit"
        if obj_class == "building" or obj_class == ["building"]:
            return "building"
        if obj_class == "item" or obj_class == ["item"]:
            return None
        is_a = Worker._rules_entry(name, "is_a") or []
        if isinstance(is_a, str):
            is_a = is_a.split()
        elif not isinstance(is_a, (list, tuple)):
            is_a = []
        if any("building" in str(tag) for tag in is_a):
            return "building"
        if Worker._rules_entry(name, "is_gather"):
            return "building"
        if Worker._rules_entry(name, "resource_volume_max") or Worker._rules_entry(
            name, "auto_production"
        ):
            return "building"
        return "deposit"

    @staticmethod
    def _split_legacy_can_gather(names):
        """将旧版 can_gather 拆分为矿床名与建筑名，忽略 resource# 条目。"""
        if not names:
            return [], []
        if "all" in names:
            return ["all"], ["all"]
        deposits = []
        buildings = []
        for name in names:
            if name.startswith("resource"):
                continue
            kind = Worker._legacy_gather_entry_kind(name)
            if kind == "deposit":
                deposits.append(name)
            elif kind == "building":
                buildings.append(name)
        return deposits, buildings

    @staticmethod
    def has_gather_permissions(unit):
        if getattr(unit, "can_gather_deposit", None):
            return True
        if getattr(unit, "can_gather_building", None):
            return True
        return bool(getattr(unit, "can_gather", None))

    def _single_gather_permission(self):
        perms = (self.can_gather_deposit or []) + (self.can_gather_building or [])
        return len(perms) == 1

    @staticmethod
    def _gather_target_place(target):
        if hasattr(target, "place") and target.place is not None:
            return target.place
        if hasattr(target, "strict_neighbors"):
            return target
        return None

    @staticmethod
    def _gather_terrain_ok_for_unit(unit, target):
        """采集是否合法取决于目标所在方格（如 goldmines a3 中 a3 是否为水路）。"""
        from ..worldorders.base import (
            _is_impassable_land_for_water_unit,
            _is_impassable_water_for_ground_unit,
        )

        place = Worker._gather_target_place(target)
        if place is None:
            return False
        if _is_impassable_land_for_water_unit(unit, place):
            return False
        if _is_impassable_water_for_ground_unit(unit, place):
            return False
        return True

    def _can_gather_target(self, target):
        """检查工人是否可以采集矿床或可采集建筑。"""
        deposits = self.can_gather_deposit or []
        buildings = self.can_gather_building or []
        if not deposits and not buildings:
            return False

        allowed = False
        if isinstance(target, Deposit):
            if "all" in deposits:
                allowed = True
            else:
                deposit_type = getattr(target, "type_name", None)
                allowed = bool(deposit_type and deposit_type in deposits)
        elif hasattr(target, "is_a_building") and target.is_a_building:
            if not getattr(target, "resource_type", None):
                return False
            if "all" in buildings:
                allowed = True
            else:
                building_type = getattr(target, "type_name", None)
                allowed = bool(building_type and building_type in buildings)

        if not allowed:
            return False
        return Worker._gather_terrain_ok_for_unit(self, target)