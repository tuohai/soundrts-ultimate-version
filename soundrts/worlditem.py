from soundrts.worldentity import Entity


class Item(Entity):
    default_order = "pickup"
    skills = ()
    buffs = ()
    # aura_buffs = ()
    # attack_buffs = ()
    is_loot = 0
    
    # 添加is_a机制支持
    is_a = ()  # 直接继承的父类列表
    expanded_is_a = set()  # 展开的继承链，包括间接继承的所有父类
    can_use_tech = ()  # 同型装备物品可使用的科技升级
    
    # 宝藏物品属性
    resource_rewards = ()  # 资源奖励，格式: [resource1_amount, resource2_amount, ...]
    consume_on_pickup = 0  # 拾取时是否消耗物品
    
    # 物品基本属性
    collision = 0  # 物品不阻挡移动
    transport_volume = 1  # 在库存中占据的空间
    hp_max = 1  # 最小生命值，防止某些系统错误
    airground_type = "ground"  # 地面物品
    is_vulnerable = False  # 物品不会受到伤害
    
    # 战斗属性 - 物品本身不参与战斗，默认0；
    # 但同型模型（same-type）允许一个 item 同时是可装备的武器/盔甲：
    # 作者在 rules.txt 里给该 item 写上武器/盔甲数值 + equippable_as_weapon/equippable_as_armor，
    # 装备到背包持有者身上时这些数值会通过单位的武器/护甲系统生效。
    mdg = 0  # 近战伤害
    rdg = 0  # 远程伤害
    mdf = 0  # 近战防御
    rdf = 0  # 远程防御
    mdg_range = 0  # 近战射程
    rdg_range = 0  # 远程射程
    mdg_cd = 0  # 近战冷却时间
    rdg_cd = 0  # 远程冷却时间
    mdg_minimal_range = 0
    rdg_minimal_range = 0
    mdg_crit = 0
    rdg_crit = 0
    mdg_crit_rate = 0
    rdg_crit_rate = 0
    mdg_piercing = 0
    rdg_piercing = 0
    mdg_piercing_rate = 0
    rdg_piercing_rate = 0
    mdf_crit_rate = 0
    rdf_crit_rate = 0
    mdf_piercing = 0
    rdf_piercing = 0

    # 同型模型装备标志：
    #   equippable_as_weapon 1 -> 该物品可作为武器装备（装备时套用其 mdg/rdg/... 到持有者）
    #   equippable_as_armor 1  -> 该物品可作为盔甲穿戴（穿戴时套用其 mdf/rdf/... 到持有者）
    equippable_as_weapon = 0
    equippable_as_armor = 0

    # 可消耗物品的"使用"效果：指向一个技能(skill)的 type_name；
    # 使用时执行该技能效果（如治疗/施法），然后消耗该物品。
    use_effect = None
    # 技能书：learn_level 10 表示使用者需达到 10 级；
    # 或 learn_level_skills 10 skill_a（与单位侧语法相同，可并存，取较高等级）。
    learn_level = 0
    learn_level_skills = ()
    # 限定使用地点（方格别名如 b2）；与 resource_rewards 等配合用于"到某地后背包中使用"。
    use_square = None
    
    # 其他可能需要的属性
    population_cost = 0  # 不消耗人口
    population_provided = 0  # 不提供人口
    speed = 0  # 物品不移动
    sight_range = 0  # 物品没有视野
    
    # 确保物品不会被其他系统误认为是单位
    is_a_unit = False
    is_a_building = False
    
    # 确保物品有类型名称
    type_name = None
    
    @property
    def is_weapon_item(self):
        """同型模型：该物品是否可作为武器装备。"""
        return bool(getattr(self, "equippable_as_weapon", 0))

    @property
    def is_armor_item(self):
        """同型模型：该物品是否可作为盔甲穿戴。"""
        return bool(getattr(self, "equippable_as_armor", 0))

    @property
    def is_consumable_item(self):
        """既非武器也非盔甲、且具备可用效果(use_effect/skills/buffs)的可消耗物品。"""
        if self.is_weapon_item or self.is_armor_item:
            return False
        rewards = getattr(self, "resource_rewards", None) or ()
        return bool(
            getattr(self, "use_effect", None)
            or getattr(self, "skills", None)
            or getattr(self, "buffs", None)
            or (getattr(self, "use_square", None) and any(r > 0 for r in rewards))
        )

    def update_in_inventory(self, owner):
        """
        当物品在库存中时的更新方法
        
        Args:
            owner: 拥有此物品的单位
        """
        # 物品在库存中的基本更新逻辑
        # 对于大多数物品，在库存中不需要特殊的更新逻辑
        # 子类可以重写这个方法来实现特定的更新行为
        pass

    @classmethod
    def interpret(cls, d):
        # 解析基本属性
        for k, f in [
            ("is_loot", int),
            ("consume_on_pickup", int),
            ("collision", int),
            ("transport_volume", int),
            ("hp_max", int),
            ("population_cost", int),
            ("population_provided", int),
            ("speed", int),
            ("sight_range", int),
            ("is_vulnerable", int),
            ("is_a_unit", int),
            ("is_a_building", int),
            ("equippable_as_weapon", int),
            ("equippable_as_armor", int),
            ("learn_level", int),
        ]:
            if k in d:
                d[k] = f(d[k][0] if isinstance(d[k], list) else d[k])
        
        # 解析战斗属性（同型模型：item 可携带武器/盔甲数值）
        for k, f in [
            ("mdg", int),
            ("rdg", int),
            ("mdf", int),
            ("rdf", int),
            ("mdg_range", int),
            ("rdg_range", int),
            ("mdg_cd", int),
            ("rdg_cd", int),
            ("mdg_minimal_range", int),
            ("rdg_minimal_range", int),
            ("mdg_crit", int),
            ("rdg_crit", int),
            ("mdg_crit_rate", int),
            ("rdg_crit_rate", int),
            ("mdg_piercing", int),
            ("rdg_piercing", int),
            ("mdg_piercing_rate", int),
            ("rdg_piercing_rate", int),
            ("mdf_crit_rate", int),
            ("rdf_crit_rate", int),
            ("mdf_piercing", int),
            ("rdf_piercing", int),
        ]:
            if k in d:
                d[k] = f(d[k][0] if isinstance(d[k], list) else d[k])
        
        # 解析字符串属性
        for k in ["airground_type", "type_name", "use_effect", "use_square"]:
            if k in d:
                d[k] = str(d[k][0] if isinstance(d[k], list) else d[k])
        
        # 解析列表属性
        for k in ["skills", "buffs"]:
            if k in d:
                if isinstance(d[k], str):
                    d[k] = d[k].split()
                elif not isinstance(d[k], (list, tuple)):
                    d[k] = [d[k]]
        
        # 解析can_use_tech属性
        if "can_use_tech" in d:
            if isinstance(d["can_use_tech"], str):
                d["can_use_tech"] = d["can_use_tech"].split()
            elif not isinstance(d["can_use_tech"], (list, tuple)):
                d["can_use_tech"] = [d["can_use_tech"]]

        # 解析is_a属性
        if "is_a" in d:
            if isinstance(d["is_a"], str):
                d["is_a"] = d["is_a"].split()
            elif not isinstance(d["is_a"], (list, tuple)):
                d["is_a"] = [d["is_a"]]
        
        # 解析资源奖励
        if "resource_rewards" in d:
            if isinstance(d["resource_rewards"], str):
                # 如果是字符串，按空格分割
                d["resource_rewards"] = [int(x) for x in d["resource_rewards"].split()]
            elif isinstance(d["resource_rewards"], list):
                # 如果是列表，转换为整数
                d["resource_rewards"] = [int(x) for x in d["resource_rewards"]]
            else:
                # 如果是单个值，转换为包含一个元素的列表
                d["resource_rewards"] = [int(d["resource_rewards"])]

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self._buffs = []
        
        # 初始化is_a机制
        self.expanded_is_a = set()
        if hasattr(self, 'is_a') and self.is_a:
            self._expand_is_a(self.is_a)

    def _expand_is_a(self, is_a_list):
        """展开is_a列表，将直接继承的父类和间接继承的父类都添加到expanded_is_a中"""
        if not is_a_list:
            return
            
        for parent_name in is_a_list:
            if parent_name not in self.expanded_is_a:
                self.expanded_is_a.add(parent_name)
                # 递归处理基类的继承
                try:
                    from .definitions import rules
                    parent_class = rules.unit_class(parent_name)
                    if parent_class and hasattr(parent_class, 'is_a'):
                        self._expand_is_a(parent_class.is_a)
                except (AttributeError, KeyError):
                    # 如果没有找到父类定义，或者rules对象还没有初始化，跳过
                    pass

    def is_a_type(self, type_name):
        """检查物品是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果物品属于指定类型返回True，否则返回False
        """
        # 检查直接类型匹配
        if hasattr(self, 'type_name') and self.type_name == type_name:
            return True
        
        # 检查is_a直接继承
        if hasattr(self, 'is_a') and type_name in self.is_a:
            return True
        
        # 检查expanded_is_a间接继承
        if hasattr(self, 'expanded_is_a') and type_name in self.expanded_is_a:
            return True
        
        return False

    @classmethod
    def is_item_type(cls, type_name):
        """检查物品类是否属于指定类型（支持is_a机制）
        
        Args:
            type_name: 要检查的类型名称
            
        Returns:
            bool: 如果物品类属于指定类型返回True，否则返回False
        """
        # 检查直接类型匹配
        if hasattr(cls, 'type_name') and cls.type_name == type_name:
            return True
        
        # 检查is_a直接继承
        if hasattr(cls, 'is_a') and type_name in cls.is_a:
            return True
        
        # 检查expanded_is_a间接继承
        if hasattr(cls, 'expanded_is_a') and type_name in cls.expanded_is_a:
            return True
        
        return False

    def give_resource_rewards(self, player, picker=None):
        """给予资源奖励给玩家"""
        if not self.resource_rewards:
            return
            
        # 处理资源奖励
        for i, reward in enumerate(self.resource_rewards):
            if reward > 0:
                resource_type = f"resource{i + 1}"
                reward_amount = reward * 1000  # 转换为游戏内部单位
                player.store(resource_type, reward_amount)
                # 发送资源奖励通知（与击杀单位奖励使用相同格式）
                # 使用拾取者作为发送者，避免显示unknown
                sender = picker if picker else self
                player.send_event(sender, f"{resource_type}_reward")
    
    def on_pickup(self, picker):
        """物品被拾取时的处理"""
        # 若有 use_square，奖励改在背包中使用（use_item）时发放，拾取时不给
        if self.resource_rewards and not getattr(self, "use_square", None):
            self.give_resource_rewards(picker.player, picker)
        
        # 注意：通知现在由执行拾取的单位发送，不在这里发送
        # 这里可以处理其他逻辑，比如特殊效果等
        
        # 如果设置了拾取时消耗
        if self.consume_on_pickup:
            return True  # 返回True表示物品应该被消耗
        return False  # 返回False表示物品不被消耗

    def on_drop(self, dropper):
        """物品被丢弃时的处理"""
        # 注意：通知现在由执行丢弃的单位发送，不在这里发送
        # 这里可以处理其他逻辑，比如特殊效果等
        
        # 返回 False 表示物品不被消耗（正常丢弃）
        return False

    def equip(self, host):
        # 确保host有can_use_skill属性
        if not hasattr(host, 'can_use_skill'):
            host.can_use_skill = []
        elif host.can_use_skill is None:
            host.can_use_skill = []
        
        # 安全地添加技能（技能书 learn_level / learn_level_skills 仅在使用时学会）
        if hasattr(self, "skills") and self.skills:
            book_gated = bool(getattr(self, "learn_level", 0)) or bool(
                getattr(self, "learn_level_skills", ()) or ()
            )
            if not book_gated:
                for a in self.skills:
                    if a not in host.can_use_skill:
                        host.can_use_skill = list(host.can_use_skill) + [a]
        
        # 确保有_buffs属性
        if not hasattr(self, '_buffs'):
            self._buffs = []
        
        # 安全地添加buff效果
        if hasattr(self, 'buffs') and self.buffs:
            for b in self.buffs:
                try:
                    cls = host.world.unit_class(b)
                    if cls is not None:
                        self._buffs.append(cls(self, host))
                except:
                    pass  # 忽略无效的buff类
    
    def unequip(self, host, *, strip_skills=True):
        # 安全地移除技能（消耗技能书时 strip_skills=False，保留永久学会的技能）
        if strip_skills and hasattr(self, 'skills') and self.skills:
            for a in self.skills:
                if hasattr(host, 'can_use_skill') and a in host.can_use_skill:
                    host.can_use_skill = [x for x in host.can_use_skill if x != a]
        
        # 确保有_buffs属性
        if not hasattr(self, '_buffs'):
            self._buffs = []
        
        # 安全地移除buff效果
        for b in self._buffs:
            try:
                if hasattr(b, 'cancel'):
                    b.cancel()
            except:
                pass  # 忽略错误
        
        # 清空buff列表
        self._buffs = []


