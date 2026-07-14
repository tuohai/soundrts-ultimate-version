"""
Bonus属性处理模块
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from .terrain_effective import ATTR_ON_TERRAIN, ATTR_TERRAIN_VS, effective_stat_value


class BonusHandler:
    def __init__(self, parent):
        self.parent = parent

    def _should_show_bonus(self, u, bonus_attr):
        """
        检查是否应该显示某个bonus属性
        
        显示条件：
        1. 必须定义了有effect apply_bonus的科技
        2. 研究科技之前（一旦科技研究完成就不会显示）
        
        参数:
        - u: 单位对象
        - bonus_attr: bonus属性名（如"mdg_bonus", "rdg_bonus"等）
        
        返回:
        - True: 应该显示bonus
        - False: 不应该显示bonus
        """
        # 如果单位没有玩家，不显示bonus
        if not hasattr(u, 'player') or not u.player:
            return False
        
        # 获取基础属性名（去掉_bonus后缀）
        base_attr = bonus_attr.replace("_bonus", "")
        
        try:
            from ..definitions import rules
            
            # 遍历所有科技定义
            for tech_name in rules.classnames():
                tech_class = rules.unit_class(tech_name)
                if not tech_class:
                    continue
                
                # 检查科技是否有effect属性
                if not hasattr(tech_class, 'effect'):
                    continue
                
                effect = tech_class.effect
                if not effect:
                    continue
                
                # 处理多个effects的情况
                effects_to_check = []
                if isinstance(effect, list) and effect and isinstance(effect[0], list):
                    effects_to_check = effect
                else:
                    effects_to_check = [effect]
                
                # 检查每个effect
                for current_effect in effects_to_check:
                    if isinstance(current_effect, str):
                        effect_parts = current_effect.split()
                    else:
                        effect_parts = list(current_effect)
                    
                    # 检查是否为apply_bonus效果，并且影响到当前属性
                    if (len(effect_parts) >= 2 and 
                        effect_parts[0] == "apply_bonus" and 
                        base_attr in effect_parts[1:]):
                        
                        # 检查玩家是否已经研究了该科技
                        if tech_name in u.player.upgrades:
                            # 科技已研究，不显示bonus
                            return False
                        else:
                            # 科技未研究，但有相关的apply_bonus效果，显示bonus
                            return True
            
            # 没有找到相关的apply_bonus科技，不显示bonus
            return False
            
        except Exception as e:
            # 如果出现错误，默认不显示bonus
            print(f"检查bonus显示条件时出错: {e}")
            return False

    def _add_bonus_attribute(self, attrs, u, base_attr, display_key, display_msg, precision_divide=False, divide_by_1000=False):
        """
        抽象的bonus属性处理函数
        
        参数:
        - attrs: 属性列表
        - u: 单位对象
        - base_attr: 基础属性名 (如 "mdg", "mdf")
        - display_key: 显示按键 (如 "m", "d")
        - display_msg: 显示消息常量 (如 mp.MELEE_DAMAGE)
        - precision_divide: 是否需要除以PRECISION进行精度转换
        - divide_by_1000: 是否需要除以1000（如暴击倍率）
        """
        # 处理基础属性 - 先检查单位本身，再检查model
        base_value = 0
        
        # 优先检查单位对象本身的属性
        if hasattr(u, base_attr):
            base_value = getattr(u, base_attr, 0)
        # 如果单位本身没有，再检查model
        elif hasattr(u.model, base_attr):
            base_value = getattr(u.model, base_attr, 0)

        # 当前格地形 *_vs / 单位 *_on_terrain：计入 mdg 等显示值
        if base_value and (
            base_attr in ATTR_TERRAIN_VS or base_attr in ATTR_ON_TERRAIN
        ):
            base_value = effective_stat_value(u, base_attr, base_value)
            
        if base_value > 0:
            if precision_divide:
                text = nb2msg_float(base_value / PRECISION)
            elif divide_by_1000:
                text = nb2msg_float(base_value / 1000)
            else:
                text = nb2msg_float(base_value)
            attrs.append((display_key, display_msg, text))
        
        # 处理bonus属性 - 先检查单位本身，再检查model
        bonus_attr = base_attr + "_bonus"
        bonus_value = 0
        
        # 优先检查单位对象本身的bonus属性
        if hasattr(u, bonus_attr):
            bonus_value = getattr(u, bonus_attr, 0)
        # 如果单位本身没有，再检查model
        elif hasattr(u.model, bonus_attr):
            bonus_value = getattr(u.model, bonus_attr, 0)
            
        if bonus_value > 0:
            # 检查是否应该显示bonus
            if self._should_show_bonus(u, bonus_attr):
                if precision_divide:
                    bonus_text = nb2msg_float(bonus_value / PRECISION)
                elif divide_by_1000:
                    bonus_text = nb2msg_float(bonus_value / 1000)
                else:
                    bonus_text = nb2msg_float(bonus_value)
                
                # 创建bonus显示消息
                bonus_display_msg = display_msg + [" "] + mp.BONUS
                attrs.append(("", bonus_display_msg, bonus_text))
        
        # 处理vs属性（对特定单位类型的加成）- 先检查单位本身，再检查model
        vs_attr = base_attr + "_vs"
        vs_dict = {}
        
        # 优先检查单位对象本身的vs属性
        if hasattr(u, vs_attr):
            vs_dict = getattr(u, vs_attr, {})
        # 如果单位本身没有，再检查model
        elif hasattr(u.model, vs_attr):
            vs_dict = getattr(u.model, vs_attr, {})
            
        if vs_dict:
            self.parent._add_vs_attribute(attrs, vs_dict, base_attr, precision_divide, divide_by_1000)
        
        # 处理bonus vs属性（bonus对特定单位类型的加成）- 先检查单位本身，再检查model
        bonus_vs_attr = base_attr + "_bonus_vs"
        bonus_vs_dict = {}
        
        # 优先检查单位对象本身的bonus vs属性
        if hasattr(u, bonus_vs_attr):
            bonus_vs_dict = getattr(u, bonus_vs_attr, {})
        # 如果单位本身没有，再检查model
        elif hasattr(u.model, bonus_vs_attr):
            bonus_vs_dict = getattr(u.model, bonus_vs_attr, {})
            
        if bonus_vs_dict:
            # 检查是否应该显示bonus vs属性
            if self._should_show_bonus(u, bonus_attr):
                self.parent._add_vs_attribute(attrs, bonus_vs_dict, base_attr + "_bonus", precision_divide, divide_by_1000)