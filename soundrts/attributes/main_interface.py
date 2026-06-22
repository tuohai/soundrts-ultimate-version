"""
属性界面主类
"""

import math
import os
from .. import msgparts as mp
from ..lib.bindings import Bindings
from ..lib.nofloat import PRECISION
from ..clientmedia import voice
from .. import parameters
from ..lib.msgs import nb2msg, nb2msg_float
from ..definitions import style

from .bonus_handler import BonusHandler
from .vs_handler import VsHandler
from .gather_handler import GatherHandler
from .resource_utils import ResourceUtils
from .main_display import MainDisplay
from .resource_display import ResourceDisplay
from .production_calc import ProductionCalculator
from .weapon_detail import WeaponDetail
from .armor_detail import ArmorDetail
from .unit_detail import UnitDetail
from .item_detail import ItemDetail
from .effect_formatter import EffectFormatter
from .key_bindings import KeyBindings
from .inventory_screen import InventoryScreen
from .equipment_screen import EquipmentScreen
from .utils import AttributeUtils


class AttributesInterface:
    def __init__(self, interface):
        self.interface = interface
        # 属性界面相关变量初始化
        self._in_attributes_screen = False
        # 背包界面相关变量
        self._in_inventory_screen = False
        self._inventory_screen_unit_id = None
        self._inventory_item_index = 0
        self._inventory_confirm_drop = False
        # 装备栏界面相关变量
        self._in_equipment_screen = False
        self._equipment_screen_unit_id = None
        self._equipment_item_index = 0
        self._equipment_confirm_drop = False
        self._attributes_screen_unit = None
        self._attributes_screen_attrs = []
        self._current_attribute_index = -1
        self._original_bindings = None
        # 子项导航相关变量（用于可训练单位等复杂属性）
        self._current_sub_item_index = 0
        self._current_attribute_sub_items = []
        # 用于支持详细属性界面的返回功能
        self._in_detail_attributes_screen = False
        self._saved_attributes_state = None

        # 初始化各个功能模块
        self.bonus_handler = BonusHandler(self)
        self.vs_handler = VsHandler(self)
        self.gather_handler = GatherHandler(self)
        self.resource_utils = ResourceUtils(self)
        self.main_display = MainDisplay(self)
        self.resource_display = ResourceDisplay(self)
        self.production_calc = ProductionCalculator(self)
        self.weapon_detail = WeaponDetail(self)
        self.armor_detail = ArmorDetail(self)
        self.unit_detail = UnitDetail(self)
        self.item_detail = ItemDetail(self)
        self.effect_formatter = EffectFormatter(self)
        self.key_bindings = KeyBindings(self)
        self.inventory_screen = InventoryScreen(self)
        self.equipment_screen = EquipmentScreen(self)
        self.utils = AttributeUtils(self)

    def cmd_unit_inventory_screen(self):
        """打开当前单位的背包界面"""
        return self.inventory_screen.cmd_unit_inventory_screen()

    def cmd_unit_equipment_screen(self):
        """打开当前单位的装备栏界面"""
        return self.equipment_screen.cmd_unit_equipment_screen()

    def cmd_unit_attributes_screen(self):
        """打开单位或建筑的属性界面，显示单位的全部信息"""
        return self.main_display.cmd_unit_attributes_screen()

    def _display_current_attribute(self, show_attribute_name=True):
        """显示当前选中的属性"""
        return self.main_display._display_current_attribute(show_attribute_name)

    def cmd__exit_attributes_screen(self):
        """退出属性界面或从详细属性界面返回"""
        return self.key_bindings.cmd__exit_attributes_screen()

    def _process_keyboard_event(self, e):
        """处理键盘事件"""
        if self.equipment_screen._process_keyboard_event(e):
            return True
        if self.inventory_screen._process_keyboard_event(e):
            return True
        return self.key_bindings._process_keyboard_event(e)

    def cmd__inventory_prev(self):
        return self.inventory_screen.cmd__inventory_prev()

    def cmd__inventory_next(self):
        return self.inventory_screen.cmd__inventory_next()

    def cmd__inventory_intro(self):
        return self.inventory_screen.cmd__inventory_intro()

    def cmd__inventory_use(self):
        return self.inventory_screen.cmd__inventory_use()

    def cmd__inventory_unequip(self):
        return self.inventory_screen.cmd__inventory_unequip()

    def cmd__inventory_drop_confirm(self):
        return self.inventory_screen.cmd__inventory_drop_confirm()

    def cmd__inventory_drop_now(self):
        return self.inventory_screen.cmd__inventory_drop_now()

    def cmd__inventory_drop_execute(self):
        return self.inventory_screen.cmd__inventory_drop_execute()

    def cmd__inventory_escape(self):
        return self.inventory_screen.cmd__inventory_escape()

    def cmd__equipment_prev(self):
        return self.equipment_screen.cmd__equipment_prev()

    def cmd__equipment_next(self):
        return self.equipment_screen.cmd__equipment_next()

    def cmd__equipment_intro(self):
        return self.equipment_screen.cmd__equipment_intro()

    def cmd__equipment_use(self):
        return self.equipment_screen.cmd__equipment_use()

    def cmd__equipment_unequip(self):
        return self.equipment_screen.cmd__equipment_unequip()

    def cmd__equipment_drop_confirm(self):
        return self.equipment_screen.cmd__equipment_drop_confirm()

    def cmd__equipment_drop_now(self):
        return self.equipment_screen.cmd__equipment_drop_now()

    def cmd__equipment_drop_execute(self):
        return self.equipment_screen.cmd__equipment_drop_execute()

    def cmd__equipment_escape(self):
        return self.equipment_screen.cmd__equipment_escape()

    # 将各种cmd方法委托给相应的模块
    def cmd_attributes_attr(self, attr_name):
        """响应自定义属性热键"""
        return self.key_bindings.cmd_attributes_attr(attr_name)

    def cmd__attribute_not_available(self, name):
        """显示属性不可用的消息"""
        return self.key_bindings.cmd__attribute_not_available(name)

    def cmd__attribute_check_dynamic(self, attr_name, display_name):
        """动态检查并显示属性值"""
        return self.key_bindings.cmd__attribute_check_dynamic(attr_name, display_name)

    def cmd__attribute_jump(self, index):
        """跳转到指定属性"""
        return self.key_bindings.cmd__attribute_jump(index)

    def cmd__attribute_prev(self):
        """移动到上一个属性（循环）"""
        return self.key_bindings.cmd__attribute_prev()

    def cmd__attribute_next(self):
        """移动到下一个属性（循环）"""
        return self.key_bindings.cmd__attribute_next()

    def cmd__attribute_sub_prev(self):
        """在当前属性的子项中向前导航"""
        return self.key_bindings.cmd__attribute_sub_prev()

    def cmd__attribute_sub_next(self):
        """在当前属性的子项中向后导航"""
        return self.key_bindings.cmd__attribute_sub_next()

    def cmd__attribute_sub_detail(self):
        """打开当前选中项的详细属性界面"""
        return self.key_bindings.cmd__attribute_sub_detail()

    # 代理方法以便各模块能访问主类的方法
    def _should_show_bonus(self, u, bonus_attr):
        """检查是否应该显示某个bonus属性"""
        return self.bonus_handler._should_show_bonus(u, bonus_attr)

    def _add_bonus_attribute(self, attrs, u, base_attr, display_key, display_msg, precision_divide=False, divide_by_1000=False):
        """抽象的bonus属性处理函数"""
        return self.bonus_handler._add_bonus_attribute(attrs, u, base_attr, display_key, display_msg, precision_divide, divide_by_1000)

    def _add_vs_attribute(self, attrs, vs_dict, attr_name, precision_divide=False, divide_by_1000=False):
        """处理vs属性的显示"""
        return self.vs_handler._add_vs_attribute(attrs, vs_dict, attr_name, precision_divide, divide_by_1000)

    def _add_dynamic_gather_attributes(self, attrs, u, attr_prefix):
        """检测和添加动态采集属性"""
        return self.gather_handler._add_dynamic_gather_attributes(attrs, u, attr_prefix)

    def _check_dynamic_gather_attribute(self, unit, attr_name, display_name):
        """检查并处理动态采集属性的用户查询"""
        return self.gather_handler._check_dynamic_gather_attribute(unit, attr_name, display_name)

    def _get_resource_type_name(self, resource_type):
        """动态获取资源类型的本地化名称"""
        return self.resource_utils._get_resource_type_name(resource_type)

    def _show_resource_attributes(self, resource):
        """显示资源属性界面"""
        return self.resource_display._show_resource_attributes(resource)

    def _calculate_modified_production_time(self, unit):
        """计算经过科技修正后的生产时间"""
        return self.production_calc._calculate_modified_production_time(unit)

    def _calculate_modified_production_qty(self, unit):
        """计算经过科技修正后的生产数量"""
        return self.production_calc._calculate_modified_production_qty(unit)

    def _format_effect_description(self, effect_def):
        """格式化效果描述为可读的文本"""
        return self.effect_formatter._format_effect_description(effect_def)

    def _get_stat_tts_name(self, stat):
        """将属性名转换为 TTS 消息 ID 列表。"""
        return self.utils._get_stat_tts_name(stat)

    def _is_precision_stat(self, stat):
        """判断属性是否需要除以PRECISION来显示正确数值"""
        return self.utils._is_precision_stat(stat)
    
    def _calculate_modified_production_time(self, unit):
        """计算经过科技修正后的生产时间"""
        if not hasattr(unit.model, "production_time") or unit.model.production_time is None:
            return None
            
        # 首先尝试从单位类获取基础值（与StartProduceOrder保持一致）
        unit_class = type(unit)
        base_time = getattr(unit_class, "production_time", 0)
        
        # 如果单位类没有production_time属性，则从model获取
        if base_time <= 0:
            base_time = unit.model.production_time
        
        if base_time <= 0:
            return None
            
        modified_time = base_time
        
        # 应用玩家的科技加成
        if hasattr(unit, 'player') and unit.player:
            player = unit.player
            
            # 应用固定值修正
            if hasattr(player, 'production_time_bonus'):
                modified_time += player.production_time_bonus
            
            # 应用百分比修正
            if hasattr(player, 'production_time_percent_bonus') and player.production_time_percent_bonus != 0:
                # 正确的百分比计算：-50% 意味着时间变为原来的 50%
                final_multiplier = 1.0 + player.production_time_percent_bonus
                modified_time = int(modified_time * final_multiplier)
        
        # 确保生产时间不为负
        modified_time = max(1, modified_time)
        
        return modified_time

    def _calculate_modified_production_qty(self, unit):
        """计算经过科技修正后的生产数量"""
        if not hasattr(unit.model, "production_qty") or unit.model.production_qty is None:
            return None
            
        # 首先尝试从单位类获取基础值（与StartProduceOrder保持一致）
        unit_class = type(unit)
        base_qty = getattr(unit_class, "production_qty", 0)
        
        # 如果单位类没有production_qty属性，则从model获取
        if base_qty <= 0:
            base_qty = unit.model.production_qty
        
        if base_qty <= 0:
            return None
            
        modified_qty = base_qty
        
        # 应用玩家的科技加成
        if hasattr(unit, 'player') and unit.player:
            player = unit.player
            
            # 应用固定值修正
            if hasattr(player, 'production_qty_bonus'):
                modified_qty += player.production_qty_bonus
            
            # 应用百分比修正
            if hasattr(player, 'production_qty_percent_bonus') and player.production_qty_percent_bonus != 0:
                # 正确的百分比计算：+50% 意味着数量变为原来的 150%
                final_multiplier = 1.0 + player.production_qty_percent_bonus
                modified_qty = int(modified_qty * final_multiplier)
        
        # 确保产量不为负
        modified_qty = max(0, modified_qty)
        
        return modified_qty