from typing import List

from . import msgparts as mp
from .definitions import style, rules
from .lib.log import warning
from .lib.msgs import nb2msg, nb2msg_float
from .lib.nofloat import PRECISION
from .worldorders import ORDERS_DICT
from .worldorders.base import ComplexOrder


def nb2msg_f(n):
    # the TTS cannot guess how to say "1 ration" ("une ration")
    # (note: many other cases are not correctly done)
    if n == 1:
        return mp.ONE_F
    return nb2msg(n)


def _is_phase_type(type_or_name):
    """判定一个单位类型（类或名字）是否属于时代（phase）类型。

    用于在 UI 标题/状态中区分"研究时代"与普通的"研究科技"。
    任何异常都安全降级为 False，避免影响主流程。
    """
    try:
        from .worldphase import is_a_phase
        if isinstance(type_or_name, str):
            cls = rules.unit_class(type_or_name)
        else:
            cls = type_or_name
        return is_a_phase(cls)
    except Exception:
        return False


class OrderTypeView:  # future order

    type = None
    requirements: List[str] = []

    def __init__(self, order, unit):
        self.unit = unit
        o = order.split()
        self.cls = ORDERS_DICT[o[0]]
        if len(o) > 1:
            self.type = o[1]
            self.requirements = rules.unit_class(self.type).requirements

        # 创建命令对象以便获取类型和成本信息
        order_obj = self.cls(unit, [self.type])

        # 初始化训练数量
        self.train_count = 1
        
        # 如果是训练命令，处理训练数量
        if self.cls.keyword == "train" and hasattr(unit, "can_train"):
            if isinstance(unit.can_train, dict):
                # 尝试使用self.type作为键
                if self.type in unit.can_train:
                    self.train_count = unit.can_train[self.type]
                # 如果失败，尝试使用单位类名作为键
                elif hasattr(order_obj, "type") and hasattr(order_obj.type, "__name__"):
                    unit_class_name = order_obj.type.__name__
                    if unit_class_name in unit.can_train:
                        self.train_count = unit.can_train[unit_class_name]

        # 在确定训练数量后生成标题和快捷键
        self.title = self._get_title()
        self.shortcut = self._get_shortcut()
        self.index = _ord_index(self.cls.keyword)

        self.comment = style.get(self.cls.keyword, "comment", False)
        if self.comment is None:
            self.comment = []
        
        # 处理成本计算，特别是训练多个单位的情况
        if self.cls.keyword == "train" and self.train_count > 1:
            # 获取基础单位成本（不应用修正）
            base_unit_cost = order_obj.type.cost
            
            # 计算多个单位的总基础成本
            base_total_cost = [c * self.train_count for c in base_unit_cost]
            
            # 创建一个用于应用修正的成本列表
            modified_cost = list(base_total_cost)
            
            # 应用玩家的成本修正（只应用一次）
            if hasattr(unit.player, 'cost_bonus'):
                for i, bonus in enumerate(unit.player.cost_bonus):
                    if i < len(modified_cost):
                        modified_cost[i] += bonus  # 只加一次
            
            # 应用玩家的百分比成本修正
            if hasattr(unit.player, 'cost_percent_bonus'):
                for i, percent_bonus in enumerate(unit.player.cost_percent_bonus):
                    if i < len(modified_cost) and percent_bonus != 0:
                        bonus_amount = int(modified_cost[i] * percent_bonus)
                        modified_cost[i] += bonus_amount

            ComplexOrder._merge_phase_resource_cost(unit.player, modified_cost)
            
            # 确保所有成本不为负
            for i in range(len(modified_cost)):
                modified_cost[i] = max(0, modified_cost[i])
            
            self.cost = tuple(modified_cost)
            self.single_cost = order_obj.cost  # 保留单个单位的成本，可能会在某些地方使用
            
            # 处理食物成本计算逻辑
            # 先获取未经修正的基础单位食物成本
            base_unit_population_cost = order_obj.type.population_cost
            
            # 计算总基础食物成本
            base_total_population_cost = base_unit_population_cost * self.train_count
            
            # 应用玩家的食物成本修正（只应用一次）
            modified_population_cost = base_total_population_cost
            if hasattr(unit.player, 'population_cost_bonus'):
                modified_population_cost += unit.player.population_cost_bonus
                
            # 应用百分比修正
            if hasattr(unit.player, 'population_cost_percent_bonus') and unit.player.population_cost_percent_bonus != 0:
                bonus_amount = int(modified_population_cost * unit.player.population_cost_percent_bonus)
                modified_population_cost += bonus_amount

            modified_population_cost = ComplexOrder._merge_phase_scalar_cost(
                unit.player,
                modified_population_cost,
                "phase_population_cost_bonus",
                "phase_population_cost_percent_bonus",
            )
                
            # 确保食物成本不为负
            modified_population_cost = max(0, modified_population_cost)
            
            self.single_population_cost = order_obj.population_cost
            self.population_cost = modified_population_cost
        else:
            # 非训练命令或单个单位训练，使用标准逻辑
            self.single_cost = order_obj.cost
            self.single_population_cost = order_obj.population_cost
            self.cost = self.single_cost
            self.population_cost = self.single_population_cost
            
        self.nb_args = order_obj.nb_args

    @property
    def target_shouldnt_collide(self):
        return (
            self.cls.keyword == "use"
            and self.cls(self.unit, [self.type]).type.effect_range > 12 * PRECISION
        )

    def __eq__(self, other):
        return self.cls.keyword == other.cls.keyword and self.type == other.type

    def _get_title(self):
        # 对于GatherOrder，我们需要特殊处理，因为它的title依赖于target
        # 在菜单生成阶段，我们无法确定target，所以保持原有逻辑
        # 实际的title会在命令执行时通过_order_title_msg函数正确处理
        # 研究时代（phase）类型的科技时，使用"升级到"风格的标题，更符合直觉
        if self.cls.keyword == "research" and self.type and _is_phase_type(self.type):
            t = style.get("upgrade_to", "title")
        else:
            t = style.get(self.cls.keyword, "title")
        
        if t is None:
            t = []
            warning("%s.title is None", self.cls.keyword)
        if self.type:
            t2 = style.get(self.type, "title")
            if t2 is None:
                warning("%s.title is None", self.type)
            else:
                # 如果是训练命令且训练数量大于1，在单位名称前添加数量
                # 获取train_count
                train_count = getattr(self, "train_count", 1)
                if self.cls.keyword == "train" and train_count > 1:
                    t2 = nb2msg(train_count) + t2
                t = substitute_args(t, [t2])
        return t

    def _get_shortcut(self):
        s = style.get(self.cls.keyword, "shortcut", False)
        if s:
            return str(s[0])
        if self.type:
            s = style.get(self.type, "shortcut", False)
            if s:
                return str(s[0])

    def _get_requirements_msg(self):
        and_index = 0
        msg = []
        missing = [r for r in self.requirements if not self.unit.player.has(r)]
        for t in missing:
            and_index = len(msg)
            msg += style.get(t, "title")
        if not missing:
            # 检查是否是生产或耕种命令，如果是，显示其资源成本
            if self.cls.keyword in ["auto_produce", "manual_produce", "start_automatic_cultivate", "start_manual_cultivate"]:
                # 获取建筑的生产成本（从规则定义获取）
                unit_type_name = getattr(self.unit, 'type_name', None)
                production_cost = (0, 0)
                
                if unit_type_name:
                    # 从规则定义中获取生产成本
                    try:
                        production_cost = getattr(rules.unit_class(unit_type_name), 'production_cost', (0, 0))
                    except:
                        production_cost = (0, 0)
                
                if production_cost and any(production_cost):
                    # 在客户端菜单显示时，直接使用基础成本，不需要计算修正
                    modified_cost = production_cost
                    
                    # 显示修正后的成本
                    for i, c in enumerate(modified_cost):
                        if c > 0:
                            and_index = len(msg)
                            # 资源成本显示为整数，除以PRECISION获得实际值
                            resource_amount = int(c / PRECISION)
                            if resource_amount > 0:
                                # 获取资源类型的标题
                                resource_title = style.get("parameters", f"resource{i+1}_title")
                                if resource_title:
                                    msg += nb2msg(resource_amount) + resource_title
            else:
                # 原有的成本显示逻辑（用于训练、升级等其他命令）
                if self.cost:
                    for i, c in enumerate(self.cost):
                        if c:
                            and_index = len(msg)
                        # 资源成本显示为整数
                            resource_amount = int(c / PRECISION)
                        # 获取资源类型的标题
                            resource_title = style.get("parameters", f"resource{i+1}_title")
                            msg += nb2msg(resource_amount) + resource_title
            if self.population_cost:
                and_index = len(msg)
                msg += nb2msg_f(self.population_cost) + style.get("parameters", "population_title")
        # add "and" if there are at least 2 requirements
        if and_index > 0:
            msg[and_index:and_index] = style.get("parameters", "and")
        if msg:
            msg[0:0] = style.get("parameters", "requires")
        return msg

    @property
    def full_comment(self):
        return self.comment + self._get_requirements_msg()

    @property
    def encode(self):
        result = self.cls.keyword
        if self.type:
            result += " " + self.type
        return result


def _ord_index(keyword):
    try:
        return float(style.get(keyword, "index", False)[0])
    except ValueError:
        warning("%s.index should be a number or nothing (check style.txt)", keyword)
    except IndexError:
        pass
    return 9999  # end of the list


def _has_ord_index(keyword):
    return style.has(keyword, "index")


_orders_list = ()


def update_orders_list():
    global _orders_list
    # this sorted list of order classes is used when generating the menu
    _orders_list = sorted(
        [_x for _x in list(ORDERS_DICT.values()) if _has_ord_index(_x.keyword)],
        key=lambda x: _ord_index(x.keyword),
    )


def get_orders_list():
    return _orders_list


def substitute_args(t, args):
    if t is not None:
        while "$1" in t:
            i = t.index("$1")
            del t[i]
            t[i:i] = args[0]
        return t
