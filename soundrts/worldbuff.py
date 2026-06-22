# TODO: buff name in unit status
# TODO: buff noise while active
# TODO: use world.time instead? (no update of time_left all the time)
from soundrts.definitions import VIRTUAL_TIME_INTERVAL
from soundrts.lib.log import warning
from soundrts.lib.nofloat import PRECISION, to_int
# 移除随机数模块导入，使用世界同步随机数

ALLOWED_STATS = """
hp hp_max hp_regen mana mana_max mana_regen
speed mdg rdg mdg_ready rdg_ready mdg_cd rdg_cd mdg_cover rdg_cover mdg_dodge rdg_dodge mdf rdf mdg_range rdg_range mdg_minimal_range rdg_minimal_range mdg_splash rdg_splash mdg_splash_decay_min rdg_splash_decay_min
mdg_radius rdg_radius minimal_mdg minimal_rdg harm_level harm_range harm_ready harm_cd harm_radius heal_level heal_cd heal_radius heal_range heal_ready buff_radius
time_cost population_cost production_time production_qty
""".split()

# 生产类属性用百分比累加到 host._buff_<stat>_percent，由 ProductionOrder 读取。
_PRODUCTION_BUFF_STATS = frozenset(
    {"time_cost", "population_cost", "production_time", "production_qty"}
)

# 注意：属性的精度处理现在使用definitions._precision_properties来判断

# The following stats would require specific code:
# - food_cost (used food should be updated by the player)
# - damage_level (the damage would need to be updated with the damage bonus)
# - revival_time (temporary buffs are removed after death)


class Buff:
    is_a = ()  # silence warning
    expanded_is_a = ()  # silence warning

    duration = 0
    stack = 0
    temporary = 0
    negative = 0
    stat = ""  # 可以是单个属性字符串或多个属性的列表
    percentage = 0  # 可以是单个值或多个值的列表
    v = 0  # 可以是单个值或多个值的列表
    dv = 0  # 可以是单个值或多个值的列表
    dt = to_int("1")
    target_type = ()
    drain_to = ()
    buff_radius = 0  # 新增：buff半径，默认0表示没有范围效果
    mdg_trigger_rate = 0  # 近战触发率，默认0
    rdg_trigger_rate = 0  # 远程触发率，默认0%
    is_active = False     # 主动触发，当发起攻击时触发，例如给自己增加一层防御之类的
    is_passive = False    # 被动触发，当遭受攻击时触发，例如hp低于30%触发霸体
    hp_threshold = 0      # HP阈值百分比，用于被动触发条件，默认0表示无条件触发
    trigger_condition = ""  # 触发条件表达式，例如 "hp < 30" 或 "mdg < 30"
    passive_trigger_rate = 100  # 被动触发率，默认100%，表示满足条件时100%触发
    # 冲锋攻击触发属性
    charge_mdg_trigger_rate = 0  # 近战冲锋触发率，默认0%
    charge_rdg_trigger_rate = 0  # 远程冲锋触发率，默认0%
    is_charge_active = False     # 是否在冲锋攻击时主动触发
    # 反冲锋攻击触发属性
    op_charge_mdg_trigger_rate = 0  # 近战反冲锋触发率，默认0%
    op_charge_rdg_trigger_rate = 0  # 远程反冲锋触发率，默认0%
    is_op_charge_active = False     # 是否在反冲锋攻击时主动触发
    reflect_percent = 0  # 反弹所受伤害的比例（0-100）

    @classmethod
    def interpret(cls, d):
        # 处理多属性stat
        if "stat" in d:
            if isinstance(d["stat"], list):
                # 如果已经是列表，直接使用
                d["stat"] = [str(s) for s in d["stat"]]
            else:
                # 如果是单个值，转换为字符串
                d["stat"] = str(d["stat"])
        
        # 处理其他单值参数
        for k, f in [
            ("duration", to_int),
            ("stack", int),
            ("temporary", int),
            ("negative", int),
            ("dt", to_int),
            ("buff_radius", to_int),  # 新增：处理buff_radius参数
        ]:
            if k in d:
                d[k] = f(d[k][0]) if isinstance(d[k], list) else f(d[k])
        
        # 处理可能为多值的参数（percentage, v, dv）
        for k, f in [
            ("percentage", int),
            ("v", to_int),
            ("dv", to_int),
        ]:
            if k in d:
                if isinstance(d[k], list):
                    # 如果是列表，转换每个元素
                    d[k] = [f(x) for x in d[k]]
                else:
                    # 如果是单个值，转换为对应类型
                    d[k] = f(d[k])
        
        # 特殊处理各种触发率属性，它们可能是整数或列表
        for k, f in [
            ("mdg_trigger_rate", int),
            ("rdg_trigger_rate", int),
            ("passive_trigger_rate", int),
            # 冲锋攻击触发率属性
            ("charge_mdg_trigger_rate", int),
            ("charge_rdg_trigger_rate", int),
            # 反冲锋攻击触发率属性
            ("op_charge_mdg_trigger_rate", int),
            ("op_charge_rdg_trigger_rate", int),
            ("reflect_percent", int),
        ]:
            if k in d:
                # 检查是否已经是整数值
                if isinstance(d[k], int):
                    continue
                # 如果是列表则取第一个值
                if isinstance(d[k], list) and len(d[k]) > 0:
                    d[k] = f(d[k][0])
                else:
                    # 默认值
                    d[k] = 100 if k == "passive_trigger_rate" else 0
        
        # 验证触发率是否在有效范围内（0-100）
        for k in ["mdg_trigger_rate", "rdg_trigger_rate", "passive_trigger_rate", 
                  "charge_mdg_trigger_rate", "charge_rdg_trigger_rate",
                  "op_charge_mdg_trigger_rate", "op_charge_rdg_trigger_rate",
                  "reflect_percent"]:
            if k in d and (d[k] < 0 or d[k] > 100):
                warning(f"{k} 必须在 0-100 之间，使用适当的默认值")
                d[k] = 100 if k == "passive_trigger_rate" else 0
        
        # 验证buff_radius是否为非负值
        if "buff_radius" in d and d["buff_radius"] < 0:
            warning("buff_radius 必须为非负值，使用 0 作为默认值")
            d["buff_radius"] = 0
        
        # 处理新增的参数
        for k, f in [
            ("is_active", bool),
            ("is_passive", bool),
            ("hp_threshold", int),
            ("is_charge_active", bool),
            ("is_op_charge_active", bool),  # 新增反冲锋攻击主动触发属性
        ]:
            if k in d:
                # 如果是列表则取第一个值
                if isinstance(d[k], list) and len(d[k]) > 0:
                    if k in ["is_active", "is_passive", "is_charge_active", "is_op_charge_active"]:
                        # 对于布尔值，转换"0"或"false"为False，其他为True
                        value = d[k][0].lower()
                        d[k] = value not in ["0", "false"]
                    else:
                        d[k] = f(d[k][0])
                else:
                    # 如果不是列表，直接使用值
                    d[k] = d[k]

        # 处理触发条件
        if "trigger_condition" in d:
            if isinstance(d["trigger_condition"], list) and len(d["trigger_condition"]) > 0:
                # 如果是列表，拼接所有元素
                d["trigger_condition"] = " ".join(str(x) for x in d["trigger_condition"])
            # 否则直接使用值
                    
        # 验证HP阈值是否在有效范围内（0-100）
        if "hp_threshold" in d and (d["hp_threshold"] < 0 or d["hp_threshold"] > 100):
            warning("hp_threshold 必须在 0-100 之间，使用 0 作为默认值")
            d["hp_threshold"] = 0
            
        if "dt" in d and d["dt"] < to_int(".1"):
            warning("dt is too small: using .1 instead")
            d["dt"] = to_int(".1")
        
        # 验证stat属性
        if "stat" in d:
            stats_to_check = d["stat"] if isinstance(d["stat"], list) else [d["stat"]]
            for stat in stats_to_check:
                if stat not in ALLOWED_STATS:
                    warning('the "%s" stat might not work well with buffs', stat)
        
        if "drain_to" in d:
            n = len(d["drain_to"])
            d["drain_to"] = [x for x in d["drain_to"] if x in ["hp", "mana"]]
            if len(d["drain_to"]) != n:
                warning(
                    'drain_to can only contain "hp" and/or "mana", in priority order'
                )

    def _normalize_multi_values(self):
        """标准化多值属性，确保它们与stat的数量匹配"""
        # 获取stat列表
        if isinstance(self.stat, list):
            self.stats = self.stat
        else:
            self.stats = [self.stat]
        
        stat_count = len(self.stats)
        
        # 标准化percentage
        if isinstance(self.percentage, list):
            if len(self.percentage) < stat_count:
                # 如果值不够，用最后一个值填充
                last_val = self.percentage[-1] if self.percentage else 0
                self.percentage.extend([last_val] * (stat_count - len(self.percentage)))
            elif len(self.percentage) > stat_count:
                # 如果值太多，截断
                self.percentage = self.percentage[:stat_count]
        else:
            # 如果是单个值，复制给所有属性
            self.percentage = [self.percentage] * stat_count
        
        # 标准化v
        if isinstance(self.v, list):
            if len(self.v) < stat_count:
                last_val = self.v[-1] if self.v else 0
                self.v.extend([last_val] * (stat_count - len(self.v)))
            elif len(self.v) > stat_count:
                self.v = self.v[:stat_count]
        else:
            self.v = [self.v] * stat_count
        
        # 标准化dv
        if isinstance(self.dv, list):
            if len(self.dv) < stat_count:
                last_val = self.dv[-1] if self.dv else 0
                self.dv.extend([last_val] * (stat_count - len(self.dv)))
            elif len(self.dv) > stat_count:
                self.dv = self.dv[:stat_count]
        else:
            self.dv = [self.dv] * stat_count

    def __init__(self, author, host):
        self.author = author
        self._time_left = self.duration
        
        # 标准化多值属性
        self._normalize_multi_values()
        
        if any(self.dv):
            self._t = 0
        if self.temporary:
            self._variations = [0] * len(self.stats)
        
        # 为每个属性应用初始变化
        for i, stat in enumerate(self.stats):
            if stat in _PRODUCTION_BUFF_STATS:
                pct = self.percentage[i] if isinstance(self.percentage, list) else self.percentage
                flat = self.v[i] if isinstance(self.v, list) else self.v
                delta = int(pct) + int(flat)
                attr = f"_buff_{stat}_percent"
                setattr(host, attr, getattr(host, attr, 0) + delta)
                if self.temporary:
                    self._variations[i] = delta
                continue
            variation = getattr(host, stat) * self.percentage[i] // 100 + self.v[i]
            self._apply_variation(host, variation, i)
        
        # 通知消息
        if author.cls.__name__ == "Item":
            # 为多属性构建通知消息
            stat_msgs = []
            for i, stat in enumerate(self.stats):
                if self.temporary:
                    var = self._variations[i]  # 临时buff使用实际变化值
                    # 根据实际的_variations存储方式分类处理
                    from .definitions import _precision_properties
                    
                    # 这些precision属性在_variations中存储显示值，直接使用
                    display_value_stats = {"hp", "hp_max", "mana", "mana_max", "mdg", "rdg", "mdf", "rdf"}
                    
                    if stat in display_value_stats:
                        display_value = var  # 直接显示
                    elif stat in _precision_properties:
                        display_value = var / PRECISION  # 除以1000显示
                    else:
                        display_value = var  # 直接显示
                else:
                    var = self.v[i]  # 非临时buff使用原始配置值
                    # 对于非临时buff，所有属性都需要除以PRECISION得到显示值
                    # 因为self.v[i]都是经过to_int()处理的（乘以了PRECISION）
                    display_value = var // PRECISION
                stat_msgs.append(f"{stat} {'+'if display_value > 0 else ''}{str(display_value)}")
            host.notify(
                "buff,add,%s,%s" % (self.type_name, " ".join(stat_msgs))
            )
        else:
            host.notify("buff,add,%s," % self.type_name)

    @property
    def type_name(self):
        return self.__class__.__name__

    def renew(self):
        self._time_left = self.duration

    def _apply_variation(self, host, v, stat_index=0):
        """应用属性变化
        
        Args:
            host: 目标单位
            v: 变化值
            stat_index: 属性索引（用于多属性buff）
        """
        stat = self.stats[stat_index]
        if stat in _PRODUCTION_BUFF_STATS:
            attr = f"_buff_{stat}_percent"
            current = getattr(host, attr, 0)
            setattr(host, attr, current + int(v))
            if self.temporary:
                self._variations[stat_index] += int(v)
            return
        initial_value = getattr(host, stat)
        
        # 使用官方的precision_properties来判断哪些属性需要精度处理
        from .definitions import _precision_properties
        if stat not in _precision_properties:
            # 不在precision_properties中的属性（如heal_level）需要除以PRECISION
            v = v // PRECISION
        # 在precision_properties中的属性不除以PRECISION，让游戏引擎内部处理
        
        if self.negative:
            v *= -1
        if v < 0 and stat == "hp":
            host.apply_damage(-v, self.author)
        else:
            setattr(host, stat, getattr(host, stat) + v)
        if stat not in ["hp_regen", "mana_regen"] and getattr(host, stat) < 0:
            setattr(host, stat, 0)
        elif stat in ["hp", "mana"] and getattr(host, stat) > getattr(
            host, stat + "_max"
        ):
            setattr(host, stat, getattr(host, stat + "_max"))
        
        variation = getattr(host, stat) - initial_value
        
        # drain_to只在第一个属性上生效，避免重复消耗
        if stat_index == 0:
            for drain_stat in self.drain_to:
                stat_current = getattr(self.author, drain_stat)
                stat_max = getattr(self.author, drain_stat + "_max")
                if stat_current < stat_max:
                    setattr(self.author, drain_stat, min(stat_current - variation, stat_max))
                    break
        
        if self.temporary:
            self._variations[stat_index] += variation

    def should_stop(self):
        return self._time_left <= 0

    def update(self, host):
        self._time_left -= VIRTUAL_TIME_INTERVAL
        if any(self.dv):
            self._t += VIRTUAL_TIME_INTERVAL
            while self._t >= self.dt:
                # 为每个属性应用dv变化
                for i, dv_val in enumerate(self.dv):
                    if dv_val != 0:
                        self._apply_variation(host, dv_val, i)
                self._t -= self.dt

    def stop(self, host):
        if self.temporary:
            # 移除每个属性的临时变化
            for i, stat in enumerate(self.stats):
                variation = self._variations[i]
                if stat in _PRODUCTION_BUFF_STATS:
                    attr = f"_buff_{stat}_percent"
                    setattr(host, attr, getattr(host, attr, 0) - variation)
                    continue
                # 对于直接数值属性，_variations已经是正确的内部值，直接使用
                setattr(host, stat, getattr(host, stat) - variation)
            host.notify("buff,del,%s" % self.type_name)

    @classmethod
    def should_trigger_on_attack(cls, unit_or_random, is_melee=True):
        """判断是否应该在发起攻击时触发
        
        Args:
            unit_or_random: 单位对象（用于获取world.random）或随机数生成器
            is_melee: 是否为近战攻击，用于判断使用哪种触发率
            
        Returns:
            bool: 是否应该触发buff
        """
        # 如果不是主动buff，直接返回False
        if not cls.is_active:
            return False
            
        # 根据攻击类型选择对应的触发率
        if is_melee:
            trigger_rate = cls.mdg_trigger_rate
        else:
            trigger_rate = cls.rdg_trigger_rate
            
        # 如果触发率为0或100，直接返回结果
        if trigger_rate <= 0:
            return False
        if trigger_rate >= 100:
            return True
            
        # 获取随机数生成器
        if hasattr(unit_or_random, 'world'):
            rng = unit_or_random.world.random
        else:
            rng = unit_or_random  # 假设直接传递了随机数生成器
            
        # 否则根据概率判断是否触发
        return rng.randint(1, 100) <= trigger_rate

    @classmethod
    def should_trigger_on_charge(cls, unit_or_random, is_melee=True):
        """判断是否应该在冲锋攻击时触发
        
        Args:
            unit_or_random: 单位对象（用于获取world.random）或随机数生成器
            is_melee: 是否为近战冲锋攻击，用于判断使用哪种触发率
            
        Returns:
            bool: 是否应该触发buff
        """
        # 如果不是冲锋主动buff，查看是否是普通主动buff，普通攻击buff也能被冲锋触发
        if not cls.is_charge_active and not cls.is_active:
            return False
            
        # 优先使用冲锋触发率，如果没有设置则使用普通攻击触发率
        if is_melee:
            trigger_rate = cls.charge_mdg_trigger_rate if cls.charge_mdg_trigger_rate > 0 else cls.mdg_trigger_rate
        else:
            trigger_rate = cls.charge_rdg_trigger_rate if cls.charge_rdg_trigger_rate > 0 else cls.rdg_trigger_rate
            
        # 如果触发率为0或100，直接返回结果
        if trigger_rate <= 0:
            return False
        if trigger_rate >= 100:
            return True
            
        # 获取随机数生成器
        if hasattr(unit_or_random, 'world'):
            rng = unit_or_random.world.random
        else:
            rng = unit_or_random  # 假设直接传递了随机数生成器
            
        # 否则根据概率判断是否触发
        return rng.randint(1, 100) <= trigger_rate

    @classmethod
    def should_trigger_on_op_charge(cls, unit_or_random, is_melee=True):
        """判断是否应该在反冲锋攻击时触发
        
        Args:
            unit_or_random: 单位对象（用于获取world.random）或随机数生成器
            is_melee: 是否为近战反冲锋攻击，用于判断使用哪种触发率
            
        Returns:
            bool: 是否应该触发buff
        """
        # 如果不是反冲锋主动buff，则查看是否是冲锋主动buff或普通主动buff
        if not cls.is_op_charge_active and not cls.is_charge_active and not cls.is_active:
            return False
            
        # 优先使用反冲锋触发率，如果没有设置则使用冲锋触发率，再没有则使用普通攻击触发率
        if is_melee:
            if cls.op_charge_mdg_trigger_rate > 0:
                trigger_rate = cls.op_charge_mdg_trigger_rate
            elif cls.charge_mdg_trigger_rate > 0:
                trigger_rate = cls.charge_mdg_trigger_rate
            else:
                trigger_rate = cls.mdg_trigger_rate
        else:
            if cls.op_charge_rdg_trigger_rate > 0:
                trigger_rate = cls.op_charge_rdg_trigger_rate
            elif cls.charge_rdg_trigger_rate > 0:
                trigger_rate = cls.charge_rdg_trigger_rate
            else:
                trigger_rate = cls.rdg_trigger_rate
            
        # 如果触发率为0或100，直接返回结果
        if trigger_rate <= 0:
            return False
        if trigger_rate >= 100:
            return True
            
        # 获取随机数生成器
        if hasattr(unit_or_random, 'world'):
            rng = unit_or_random.world.random
        else:
            rng = unit_or_random  # 假设直接传递了随机数生成器
            
        # 否则根据概率判断是否触发
        return rng.randint(1, 100) <= trigger_rate

    @classmethod
    def _evaluate_condition(cls, host, condition):
        """解析并评估触发条件"""
        if not condition:
            return True
            
        # 分离属性、操作符和值
        parts = condition.split()
        if len(parts) != 3:
            warning(f"无效的触发条件格式: '{condition}'，应为 'attribute operator value'")
            return True
            
        attr, operator, value = parts
        
        # 检查属性是否有效
        if attr not in ALLOWED_STATS:
            warning(f"触发条件中的属性 '{attr}' 不在允许的属性列表中")
            return True
            
        # 获取属性值
        try:
            attr_value = getattr(host, attr)
            # 如果属性是百分比形式，转换为百分比值
            if attr in ["hp", "mana"] and hasattr(host, f"{attr}_max") and getattr(host, f"{attr}_max") > 0:
                attr_value = (attr_value * 100) // getattr(host, f"{attr}_max")
        except AttributeError:
            warning(f"单位没有属性 '{attr}'")
            return True
            
        # 转换值
        try:
            value = int(value)
        except ValueError:
            warning(f"触发条件中的值 '{value}' 无法转换为整数")
            return True
            
        # 评估条件
        if operator == "<":
            return attr_value < value
        elif operator == "<=":
            return attr_value <= value
        elif operator == ">":
            return attr_value > value
        elif operator == ">=":
            return attr_value >= value
        elif operator == "==":
            return attr_value == value
        elif operator == "!=":
            return attr_value != value
        else:
            warning(f"触发条件中的操作符 '{operator}' 无效，应为 '<', '<=', '>', '>=', '==' 或 '!='")
            return True

    @classmethod
    def should_trigger_on_damage(cls, host):
        """判断是否应该在受到伤害时触发"""
        if not cls.is_passive:
            return False
            
        # 首先检查trigger_condition
        conditions_met = True
        if cls.trigger_condition:
            conditions_met = cls._evaluate_condition(host, cls.trigger_condition)
        elif cls.hp_threshold > 0:  # 向后兼容：如果设置了HP阈值
            hp_percentage = (host.hp * 100) // host.hp_max
            conditions_met = hp_percentage <= cls.hp_threshold
            
        # 如果条件不满足，直接返回False
        if not conditions_met:
            return False
            
        # 如果满足条件，根据被动触发率决定是否触发
        if cls.passive_trigger_rate <= 0:
            return False
        if cls.passive_trigger_rate >= 100:
            return True
            
        # 根据概率判断是否触发
        return host.world.random.randint(1, 100) <= cls.passive_trigger_rate

