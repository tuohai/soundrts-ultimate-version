"""基础功能模块 - 工具函数、SquareView类和EntityView基础部分"""

import math
import random
import time

import pygame
from ..definitions import rules  
from .. import config, parameters
from .. import msgparts as mp
from ..animation import noise
from ..clientgamenews import must_be_said
from ..clientgameorder import get_orders_list, substitute_args
from ..clientmedia import sounds, voice
from ..definitions import style
from ..open_container import inside_unit_visible_from_place
from ..lib.log import exception, warning
from ..lib.msgs import nb2msg
from ..lib.nofloat import PRECISION
from ..lib.sound import distance, psounds, angle
from ..worldunit import BuildingSite
from itertools import chain

# 最小步行音效间隔（秒）
FOOTSTEP_LIMIT = 0.1

# 添加flatten函数用于处理可能嵌套的列表
def flatten(lst):
    """将嵌套列表展平为一维列表 - 使用迭代方式避免pickle问题"""
    def _flatten_iter(item):
        """内部生成器函数用于展平嵌套列表"""
        if isinstance(item, list):
            for subitem in item:
                yield from _flatten_iter(subitem)
        else:
            yield item
    
    return list(_flatten_iter(lst))

def direction_to_msgpart(o):
    o = round(o / 45) * 45
    while o >= 360:
        o -= 360
    while o < 0:
        o += 360
    if o == 0:
        return mp.EAST
    elif o == 45:
        return mp.NORTHEAST
    elif o == 90:
        return mp.NORTH
    elif o == 135:
        return mp.NORTHWEST
    elif o == 180:
        return mp.WEST
    elif o == 225:
        return mp.SOUTHWEST
    elif o == 270:
        return mp.SOUTH
    elif o == 315:
        return mp.SOUTHEAST

def compute_title(type_name):
    """计算实体的标题
    
    - 支持常规格式：title 123
    - 支持等号格式：title = 123（等号作为分隔符，在解析时已被移除）
    - 保留原始类型：支持数字和字符串混合的标题
    """
    t = style.get(type_name, "title")
    if t is None:
        return []
    
    # 返回处理后的列表，保留所有元素的类型
    # 等号在definitions.py的read方法中已经被移除，不需要再处理
    return t

def _order_title_msg(order, interface, nb=1):
    if order.is_deferred:
        result = style.get("messages", "production_deferred")
    else:
        result = []
    
    # 研究时代（phase）类型时，使用"升级到"风格的标题，更符合直觉
    is_phase_research = False
    if order.keyword == "research" and getattr(order, "type", None) is not None:
        try:
            from ..worldphase import is_a_phase
            if is_a_phase(order.type):
                is_phase_research = True
        except Exception:
            is_phase_research = False

    # 获取命令标题 - 优先使用order对象的title属性
    if hasattr(order, 'title') and callable(getattr(order, 'title', None)):
        # 如果order有title属性且是方法，调用它
        result += order.title
    elif hasattr(order, 'title') and not callable(getattr(order, 'title', None)):
        # 如果order有title属性但不是方法，直接使用
        result += order.title
    elif is_phase_research:
        # 研究时代时，借用 upgrade_to 的标题（"升级到 $1"）
        result += style.get("upgrade_to", "title")
    else:
        # 否则使用默认的style.get逻辑
        result += style.get(order.keyword, "title")
    
    # 如果命令有类型参数
    if order.type is not None:
        t = style.get(order.type.type_name, "title")
        
        # 处理训练命令的数量显示
        if order.keyword == "train":
            try:
                # 优先使用train_count属性（多个相同单位同时训练），如果没有则使用nb参数（队列中的相同单位数量）
                train_count = getattr(order, "train_count", 1)
                if nb > 1:
                    # 如果队列中有多个相同类型的单位
                    display_count = train_count * nb
                    t = nb2msg(display_count) + t
                elif train_count > 1:
                    # 如果是一次性训练多个单位
                    t = nb2msg(train_count) + t
            except (AttributeError, TypeError):
                # 如果处理出错，退回到使用nb参数
                if nb > 1:
                    t = nb2msg(nb) + t
        
        result = substitute_args(result, [t])
    
    # 处理目标显示
    if hasattr(order, "targets"):  # patrol
        for t in getattr(order, "targets"):
            # 这里需要引用完整的EntityView，因为需要title属性
            from . import EntityView
            result += EntityView(interface, t).title + mp.COMMA
    elif order.target is not None:
        if order.keyword == "build_phase_two":
            result += style.get(order.target.type.type_name, "title")
        else:
            # 这里需要引用完整的EntityView，因为需要title属性
            from . import EntityView
            result += EntityView(interface, order.target).title
    
    return mp.COMMA + result

class SquareView:
    def __init__(self, interface, model):
        self.interface = interface
        self.model = model

    def __getattr__(self, name):
        # 防御性处理：反序列化时，pickle 会先调用 getattr(inst, "__setstate__", None)，
        # 此时实例的 __dict__ 还没有恢复 model 属性。若直接 self.model.xxx，会触发
        # __getattr__("model") -> self.model -> __getattr__("model") 的无限递归。
        # 因此对 model 本身以及 dunder 名字直接抛 AttributeError，让上层走默认分支。
        if name == "model" or (name.startswith("__") and name.endswith("__")):
            raise AttributeError(name)
        model = self.__dict__.get("model")
        if model is None:
            raise AttributeError(name)
        v = getattr(model, name)
        if name in ["x", "y"]:
            v /= 1000.0
        return v

    def __getstate__(self):
        return self.__dict__.copy()

    def __setstate__(self, state):
        self.__dict__.update(state)

    @property
    def fow(self):
        return self.model not in self.interface.scouted_squares

class EntityViewBase:
    """EntityView的基础部分"""
    
    next_step = None
    # 添加类变量用来处理喊杀声的音效与冷却
    _last_shout_time = 0  # 上次喊杀时间
    _shout_cooldown = 10000  # 喊杀冷却时间(10秒)
    _min_units_for_shout = 5  # 触发喊杀的最小单位数
    _units_per_volume = 5  # 每5个单位增加1音量
    _base_volume = 1  # 基础音量
    _max_volume_increase = 5  # 最大音量增加值
    # 添加类变量用于攻击音效冷却
    _last_attack_sound_time = 0  # 上次攻击音效时间
    _attack_sound_cooldown = 8000  # 攻击音效冷却时间(1秒)

    def __init__(self, interface, model):
        self.interface = interface
        self.model = model
        self.footstep_random = (
            random.random() * 0.2
        )  # to avoid strange synchronicity of footsteps when several units are walking

    def __getattr__(self, name):
        if name == "model":
            return
        # 如果 model 为 None，返回安全的默认值
        if self.model is None:
            if name == "type_name":
                return "unknown"
            elif name in ["x", "y"]:
                return 0.0
            elif name in ("qty", "hp", "hp_max", "mana", "mana_max"):
                return 0
            elif name.startswith("on_"):
                # 对于事件处理方法，如果不存在则抛出 AttributeError
                # 这样 hasattr 就能正确返回 False
                raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
            else:
                return None
        v = getattr(self.model, name)
        if name in ["x", "y"]:
            v /= 1000.0
        elif name in ("qty", "hp", "hp_max", "mana", "mana_max"):
            v = int(v / PRECISION)
        return v

    def __getstate__(self):
        # 创建状态字典的副本，确保安全的序列化
        state = self.__dict__.copy()
        
        # 删除不可序列化的属性
        unsafe_attrs = ["_noise", "_buff_noises"]
        for attr in unsafe_attrs:
            state.pop(attr, None)
            
        return state

    def __setstate__(self, state):
        # 恢复对象状态
        self.__dict__.update(state)
        # 重新初始化可能丢失的属性
        if not hasattr(self, '_noise'):
            self._noise = None
        if not hasattr(self, '_buff_noises'):
            self._buff_noises = None

    @property
    def fow(self):
        return self.is_memory

    @property
    def footstep_interval(self):
        try:
            s = self.model.actual_speed
        except:
            s = self.model.speed
        try:
            return 1000.0 / s / 2 + self.footstep_random
        except ZeroDivisionError:
            return 1000.0 * 999

    @property
    def when_moving_through(self):
        return style.get(self.model.type_name, "when_moving_through")

    @property
    def is_an_exit(self):
        if getattr(self.model, "is_an_exit", False):
            return True
        type_name = getattr(self.model, "type_name", None)
        if type_name in ("wooden_bridge", "buildingsite"):
            return False
        if getattr(self.model, "is_a_building", False) or getattr(
            self.model, "is_a_building_land", False
        ):
            return False
        return style.has(type_name, "when_moving_through")

    def is_in(self, place):
        if getattr(self, "is_inside", False):
            return inside_unit_visible_from_place(self, place)
        # For the interface, a blocker is also on the other side of the exit.
        return (
            self.place is place
            or getattr(self, "blocked_exit", None)
            and self.blocked_exit.other_side.place is place
        )

    def is_a_useful_target(self):
        # (useful for a worker)
        # resource deposits, building lands, damaged repairable units or buildings, blockable exits
        # and now: buildings with resources that can be gathered
        return (
            self.qty > 0
            or self.is_a_building_land
            or self.is_repairable
            and self.hp < self.hp_max
            or self.is_an_exit
            or (hasattr(self, "is_a_building") and self.is_a_building 
                and hasattr(self, "resource_type") and self.resource_type
                and hasattr(self, "resource_qty") and self.resource_qty > 0)
        )

    def shape(self):
        shape = style.get(self.type_name, "shape", warn_if_not_found=False)
        if shape:
            return shape[0]

    def color(self):
        color = style.get(self.type_name, "color", warn_if_not_found=False)
        try:
            return pygame.Color(color[0])
        except:
            try:
                # 使用字符串的哈希值转为颜色
                if self.short_title and len(self.short_title) > 0:
                    # 获取第一个元素
                    first_element = self.short_title[0]
                    # 如果是字符串，使用哈希值
                    if isinstance(first_element, str):
                        hash_value = hash(first_element) % 256
                        return (
                            255,
                            (hash_value * hash_value) % 256,
                            hash_value % 256,
                        )
                    # 如果是数字，直接使用
                    elif isinstance(first_element, int):
                        return (
                            255,
                            (first_element * first_element) % 256,
                            first_element % 256,
                        )
                return (255, 255, 255)
            except:
                return (255, 255, 255)

    def corrected_color(self):
        if self.model in self.interface.memory:
            return tuple([x // 2 for x in self.color()])
        else:
            return self.color()

    def stop(self):
        if self._noise:
            self._noise.stop()
        if getattr(self, "_buff_noises", None):
            for buff_noise in self._buff_noises.values():
                buff_noise.stop()
            self._buff_noises.clear()