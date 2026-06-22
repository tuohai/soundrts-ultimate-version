"""
主属性界面显示模块 - 重构版本
协调各个子模块的显示功能
"""

from .basic_attributes import BasicAttributes
from .build_rules_attributes import BuildRulesAttributes
from .equipment_abilities import EquipmentAbilities
from .combat_attributes import CombatAttributes
from .display_interface import DisplayInterface


class MainDisplay:
    def __init__(self, main_interface):
        self.main_interface = main_interface
        
        # 初始化各个子模块，传递main_interface引用
        self.basic_attributes = BasicAttributes(main_interface)
        self.build_rules_attributes = BuildRulesAttributes(main_interface)
        self.equipment_abilities = EquipmentAbilities(main_interface)
        self.combat_attributes = CombatAttributes(main_interface)
        # DisplayInterface需要访问其他子模块，所以传递它们的引用
        self.display_interface = DisplayInterface(main_interface, 
                                                 self.basic_attributes,
                                                 self.build_rules_attributes,
                                                 self.equipment_abilities, 
                                                 self.combat_attributes)

    def cmd_unit_attributes_screen(self):
        """委托给display_interface模块处理"""
        return self.display_interface.cmd_unit_attributes_screen()
    
    def _display_current_attribute(self, show_attribute_name=True):
        """委托给display_interface模块处理"""
        return self.display_interface._display_current_attribute(show_attribute_name)
    
    def _build_unit_attributes(self, u, attrs=None, is_detail_view=False):
        """委托给display_interface模块处理"""
        return self.display_interface._build_unit_attributes(u, attrs, is_detail_view)