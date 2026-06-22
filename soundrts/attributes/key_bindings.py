"""
按键绑定和导航模块
"""

import os
from .. import msgparts as mp
from ..lib.bindings import Bindings
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from ..clientmedia import voice
from ..definitions import style
from .utils import NAVIGABLE_ITEM_TYPES


class KeyBindings:
    def __init__(self, parent):
        self.parent = parent

    def _setup_attributes_screen_bindings(self):
        """设置属性界面的按键绑定"""
        # 创建新的绑定对象
        new_bindings = Bindings()
        
        # 创建绑定字符串
        bindings_str = ""
        
        # 尝试从自定义文件加载用户定义的属性界面热键绑定
        user_bindings_path = os.path.join("res", "ui", "attributes_bindings.txt")
        if os.path.exists(user_bindings_path):
            try:
                with open(user_bindings_path, "r", encoding="utf-8") as f:
                    user_bindings = f.read()
                # 使用用户定义的绑定，但强制覆盖LEFT/RIGHT键
                bindings_str = user_bindings
                # 移除用户文件中的LEFT/RIGHT绑定
                lines = bindings_str.split('\n')
                filtered_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    if not (line_stripped.startswith('LEFT:') or line_stripped.startswith('RIGHT:')):
                        filtered_lines.append(line)
                bindings_str = '\n'.join(filtered_lines)
                # 添加我们自己的LEFT/RIGHT绑定和回车键绑定
                bindings_str += "\nLEFT: _attribute_sub_prev\n"
                bindings_str += "RIGHT: _attribute_sub_next\n"
                bindings_str += "RETURN: _attribute_sub_detail\n"
                bindings_str += "KP_ENTER: _attribute_sub_detail\n"
            except Exception as e:
                # 加载失败时使用默认绑定
                bindings_str = self._setup_default_attributes_bindings()
        else:
            # 如果没有自定义文件，则使用默认绑定
            bindings_str = self._setup_default_attributes_bindings()
            
        # 加载绑定
        try:
            # 只在第一次进入属性界面时保存原始绑定
            if not self.parent._in_attributes_screen:
                self.parent._original_bindings = self.parent._bindings
            
            # 创建新的绑定对象并加载绑定字符串
            self.parent._bindings = Bindings()
            self.parent._bindings.load(bindings_str, self.parent)
        except Exception as e:
            # 出错时还原回原始绑定
            if self.parent._original_bindings:
                self.parent._bindings = self.parent._original_bindings
                self.parent._original_bindings = None

    def _setup_default_attributes_bindings(self):
        """设置默认的属性界面绑定"""
        bindings_str = ""
        
        # 创建属性键到索引的映射
        attr_key_to_index = {}
        
        # 为每个属性的首字母设置跳转绑定
        for i, (key, name, _) in enumerate(self.parent._attributes_screen_attrs):
            # 记录每个键对应的索引
            if key:  # 只为有键的属性添加跳转绑定
                attr_key_to_index[key] = i
                
                # 添加小写字母绑定
                bindings_str += f"{key}: _attribute_jump {i}\n"
                # 添加大写字母绑定
                bindings_str += f"{key.upper()}: _attribute_jump {i}\n"
        
        # 定义常用属性键及其属性信息
        common_attrs = {
            'm': ('mdg', ['近战伤害']),
            'r': ('rdg', ['远程伤害']),
            'e': ('rdg_range', ['远程射程']),
            'g': ('can_gather_deposit', ['可开采矿床']),
            'c': ('can_repair', ['修理能力']),
            't': ('gather_time', ['采集时间']),
            'q': ('gather_qty', ['采集数量']),
            'k': ('armor', ['护甲']),
            'p': ('production_type', ['生产类型']),
            "cost": mp.COST_NAME,
            "time_cost": mp.TIME_COST_NAME,
            "population_cost": mp.POPULATION_COST_NAME,
            "population_provided": mp.POPULATION_PROVIDED,
            "heal_level": mp.HEAL_LEVEL,
            "production_time": mp.PRODUCTION_TIME_NAME,
            "production_qty": mp.PRODUCTION_QUANTITY_NAME,
            "requires_deposit": mp.REQUIRES_DEPOSIT,
        }
        
        # 获取当前单位
        unit = self.parent._attributes_screen_unit
        
        # 为不在属性列表中但常用的属性键添加特殊处理
        for key, (attr_name, display_name) in common_attrs.items():
            if key not in attr_key_to_index:
                # 检查单位的model是否有这个属性
                if hasattr(unit.model, attr_name):
                    attr_value = getattr(unit.model, attr_name, 0)
                    # 如果属性值大于0，说明单位有这个属性，但可能在界面逻辑中没有被包含
                    if attr_value > 0:
                        # 添加特殊处理，在下次按下该键时检测这个属性
                        bindings_str += f"{key}: _attribute_check_dynamic {attr_name} {display_name[0]}\n"
                        bindings_str += f"{key.upper()}: _attribute_check_dynamic {attr_name} {display_name[0]}\n"
                    else:
                        # 如果属性值为0，说明单位没有这个属性
                        bindings_str += f"{key}: _attribute_not_available {display_name[0]}\n"
                        bindings_str += f"{key.upper()}: _attribute_not_available {display_name[0]}\n"
                else:
                    # 单位完全没有这个属性
                    bindings_str += f"{key}: _attribute_not_available {display_name[0]}\n"
                    bindings_str += f"{key.upper()}: _attribute_not_available {display_name[0]}\n"
        
        # 动态检测单位的gather属性并添加快捷键绑定
        dynamic_bindings = self._get_dynamic_gather_bindings(unit, attr_key_to_index)
        bindings_str += dynamic_bindings
        
        # 添加ESC键退出
        bindings_str += "ESCAPE: _exit_attributes_screen\n"
        
        # 添加上下键导航
        bindings_str += "UP: _attribute_prev\n"
        bindings_str += "DOWN: _attribute_next\n"
        
        # 添加左右键导航子项
        bindings_str += "LEFT: _attribute_sub_prev\n"
        bindings_str += "RIGHT: _attribute_sub_next\n"
        
        # 添加回车键打开子项详细属性
        bindings_str += "RETURN: _attribute_sub_detail\n"
        bindings_str += "KP_ENTER: _attribute_sub_detail\n"
        
        return bindings_str

    def _get_dynamic_gather_bindings(self, unit, attr_key_to_index):
        """获取动态采集属性的键盘绑定"""
        dynamic_bindings = ""
        
        try:
            # 收集所有gather_time和gather_qty属性
            gather_attrs = []
            
            # 遍历单位模型的所有属性
            for attr_name in dir(unit.model):
                # 跳过私有属性和方法
                if attr_name.startswith('_') or callable(getattr(unit.model, attr_name, None)):
                    continue
                
                # 检查是否是gather相关属性
                if attr_name.startswith("gather_time_") or attr_name.startswith("gather_qty_"):
                    attr_value = getattr(unit.model, attr_name, 0)
                    if isinstance(attr_value, (int, float)) and attr_value != 0:
                        gather_attrs.append(attr_name)
            
            # 为找到的gather属性添加绑定（限制数量避免键盘冲突）
            added_count = 0
            max_dynamic_bindings = 5  # 最多添加5个动态绑定
            
            for attr_name in gather_attrs:
                if added_count >= max_dynamic_bindings:
                    break
                
                # 提取资源类型名称
                if attr_name.startswith("gather_time_"):
                    resource_type = attr_name[12:]
                elif attr_name.startswith("gather_qty_"):
                    resource_type = attr_name[11:]
                else:
                    continue
                
                # 获取资源类型的友好名称
                resource_name = self.parent._get_resource_type_name(resource_type)
                
                # 尝试找一个没有被使用的数字键（1-9）
                for num in range(1, 10):
                    key = str(num)
                    if key not in attr_key_to_index:
                        # 添加绑定
                        dynamic_bindings += f"{key}: _attribute_check_dynamic {attr_name} {resource_name}\n"
                        attr_key_to_index[key] = -1  # 标记为已使用
                        added_count += 1
                        break
            
        except Exception as e:
            print(f"生成动态采集绑定时出错: {e}")
        
        return dynamic_bindings

    def cmd_attributes_attr(self, attr_name):
        """响应自定义属性热键，找到并显示指定名称的属性"""
        if not self.parent._in_attributes_screen or not self.parent._attributes_screen_unit:
            return
        
        # 处理可能的情况：属性名可以是msgparts中的常量名，也可以是单字符快捷键
        if len(attr_name) == 1:
            # 单字符快捷键情况，检查是否对应属性界面绑定表中的某个热键
            for i, (key, name, value) in enumerate(self.parent._attributes_screen_attrs):
                if key and key.lower() == attr_name.lower():
                    self.parent._current_attribute_index = i
                    voice.item(name + mp.COLON + value)
                    return
        
        # 特殊属性名称映射表，将常量名映射到模型属性名
        special_attr_map = {
            'HP': 'hp',
            'MANA': 'mana',
            'MELEE_DAMAGE': 'mdg',
            'RANGE_DAMAGE': 'rdg',
            'MELEE_DEFENSE': 'melee_armor',
            'RANGE_DEFENSE': 'range_armor',
            'MDG_RANGE': 'mdg_range',
            'RANGED_RANGE': 'rdg_range',
            'MDG_CD': 'mcd',
            'RDG_CD': 'rcd',
            'SPEED': 'speed',
            'MDG_DODGE': 'dodge',
            'RDG_DODGE': 'dodge',
            'MDG_READY': 'mready',
            'RDG_READY': 'rready',
            'MDG_COVER': 'mcover',
            'RDG_COVER': 'rcover',
            'MDG_VS': 'mdg_vs',
            'RDG_VS': 'rdg_vs',
            'STATS': 'stats',
            'TECHNIC_STATS': 'technic_stats',
            'CAN_GATHER': 'can_gather_deposit',
            'GATHER_TIME': 'gather_time',
            'GATHER_QTY': 'gather_qty',
            'CAN_REPAIR': 'can_repair',
        }
        
        # 尝试查找属性常量
        attr_msg_id = None
        
        # 检查是否为已知特殊属性名称
        model_attr_name = special_attr_map.get(attr_name, attr_name.lower())
        
        try:
            # 先尝试直接从mp模块获取属性名常量
            attr_msg_id = getattr(mp, attr_name, None)
        except (AttributeError, TypeError):
            print(f"在msgparts中未找到属性常量: {attr_name}")
            pass
        
        # 在属性列表中查找匹配的属性
        found = False
        
        # 如果找到了消息ID，在属性列表中查找
        if attr_msg_id:
            for i, (_, name, value) in enumerate(self.parent._attributes_screen_attrs):
                # 检查属性名称是否匹配
                if name == attr_msg_id:
                    # 跳转到这个属性
                    self.parent._current_attribute_index = i
                    voice.item(name + mp.COLON + value)
                    found = True
                    break
        
        # 如果没有找到匹配的属性，但是单位模型中存在该属性
        if not found:
            unit = self.parent._attributes_screen_unit
            
            # 尝试从模型中获取属性值
            if hasattr(unit.model, model_attr_name):
                try:
                    attr_value = getattr(unit.model, model_attr_name, 0)
                    # 如果是数值类型的属性
                    if isinstance(attr_value, (int, float)):
                        if attr_value > 0:
                            # 格式化数值
                            try:
                                from ...lib.nofloat import PRECISION
                                value = int(attr_value/PRECISION) if attr_value >= PRECISION else attr_value
                            except:
                                value = attr_value
                            voice.item([attr_name, ":", str(value)])
                            found = True
                    # 如果是字符串或列表类型
                    elif attr_value:
                        voice.item([attr_name, ":", str(attr_value)])
                        found = True
                except Exception as e:
                    pass
            
        # 如果仍然没有找到匹配属性，播放提示音
        if not found:
            voice.item(mp.BEEP)

    def cmd__attribute_not_available(self, name):
        """显示属性不可用的消息"""
        # 根据名称获取对应的消息ID
        msg_id = None
        if name == "近战伤害":
            msg_id = mp.MELEE_DAMAGE
        elif name == "远程伤害":
            msg_id = mp.RANGE_DAMAGE
        elif name == "近战射程":
            msg_id = mp.MDG_RANGE
        elif name == "远程射程":
            msg_id = mp.RANGED_RANGE
        else:
            msg_id = [name]
            
        voice.item(msg_id + mp.COLON + mp.NO_SUCH_ATTRIBUTE)

    def cmd__attribute_check_dynamic(self, attr_name, display_name):
        """动态检查并显示属性值"""
        unit = self.parent._attributes_screen_unit
        if not hasattr(unit.model, attr_name):
            voice.item([display_name] + mp.COLON + mp.NO_SUCH_ATTRIBUTE)
            return
            
        attr_value = getattr(unit.model, attr_name, 0)
        if attr_value <= 0:
            voice.item([display_name] + mp.COLON + mp.NO_SUCH_ATTRIBUTE)
            return
            
        # 处理不同类型的属性
        if attr_name == "rdg":  # 远程伤害
            value = int(attr_value/PRECISION)
            text = nb2msg(value)
            display_name_msg = mp.RANGE_DAMAGE
            voice.item(display_name_msg + mp.COLON + text)
        # 更多属性类型的处理...
        else:
            # 检查是否是动态采集属性
            if self.parent._check_dynamic_gather_attribute(unit, attr_name, display_name):
                return
                
            # 尝试根据属性名找到对应的消息ID
            display_name_msg = [display_name]
            voice.item(display_name_msg + mp.COLON + [str(attr_value)])

    def cmd__attribute_jump(self, index):
        """跳转到指定属性"""
        index = int(index)
        if 0 <= index < len(self.parent._attributes_screen_attrs):
            self.parent._current_attribute_index = index
            # 重置子项索引
            self.parent._current_sub_item_index = 0
            self.parent.main_display._display_current_attribute()

    def cmd__attribute_prev(self):
        """移动到上一个属性（循环）"""
        if len(self.parent._attributes_screen_attrs) == 0:
            return
            
        if self.parent._current_attribute_index > 0:
            self.parent._current_attribute_index -= 1
        else:
            # 如果当前是第一个属性，则循环到最后一个属性
            self.parent._current_attribute_index = len(self.parent._attributes_screen_attrs) - 1
            
        # 重置子项索引
        self.parent._current_sub_item_index = 0
        self.parent.main_display._display_current_attribute()
            
    def cmd__attribute_next(self):
        """移动到下一个属性（循环）"""
        if len(self.parent._attributes_screen_attrs) == 0:
            return
            
        if self.parent._current_attribute_index < len(self.parent._attributes_screen_attrs) - 1:
            self.parent._current_attribute_index += 1
        else:
            # 如果当前是最后一个属性，则循环到第一个属性
            self.parent._current_attribute_index = 0
            
        # 重置子项索引
        self.parent._current_sub_item_index = 0
        self.parent.main_display._display_current_attribute()
    
    def cmd__attribute_sub_prev(self):
        """在当前属性的子项中向前导航（仅对可导航属性有效）"""
        if len(self.parent._current_attribute_sub_items) <= 1:
            # 如果没有子项或只有一个子项，播放提示音
            voice.item(mp.BEEP)
            return
            
        if self.parent._current_sub_item_index > 0:
            self.parent._current_sub_item_index -= 1
        else:
            # 循环到最后一个子项
            self.parent._current_sub_item_index = len(self.parent._current_attribute_sub_items) - 1
            
        # 子项导航时不显示属性名
        self.parent.main_display._display_current_attribute(show_attribute_name=False)
    
    def cmd__attribute_sub_next(self):
        """在当前属性的子项中向后导航（仅对可导航属性有效）"""
        if len(self.parent._current_attribute_sub_items) <= 1:
            # 如果没有子项或只有一个子项，播放提示音
            voice.item(mp.BEEP)
            return
            
        if self.parent._current_sub_item_index < len(self.parent._current_attribute_sub_items) - 1:
            self.parent._current_sub_item_index += 1
        else:
            # 循环到第一个子项
            self.parent._current_sub_item_index = 0
            
        # 子项导航时不显示属性名
        self.parent.main_display._display_current_attribute(show_attribute_name=False)
    
    def cmd__attribute_sub_detail(self):
        """打开当前选中的可训练单位/可升级单位/可研究科技/护甲的详细属性界面"""
        # 检查是否在属性界面
        if not self.parent._in_attributes_screen:
            voice.item(mp.BEEP)
            return
            
        # 检查当前是否在可导航属性上
        if (self.parent._current_attribute_index < 0 or 
            self.parent._current_attribute_index >= len(self.parent._attributes_screen_attrs)):
            voice.item(mp.BEEP)
            return
            
        _, attr_name, attr_value = self.parent._attributes_screen_attrs[self.parent._current_attribute_index]
        current_unit = self.parent._attributes_screen_unit
        
        # 检查是否是护甲属性（单个项目，非列表）
        if attr_name == mp.CURRENT_ARMOR:
            # 处理护甲详情查看
            if not hasattr(current_unit, "armor") or not current_unit.armor:
                voice.item(mp.BEEP)
                return
            
            # 显示护甲详情
            self.parent.armor_detail._show_armor_detail(current_unit, current_unit.armor)
            return
        
        # 检查是否是当前武器属性（单个项目，非列表）
        if attr_name == mp.CURRENT_WEAPON:
            # 处理当前武器详情查看
            if not hasattr(current_unit, "weapons") or not current_unit.weapons:
                voice.item(mp.BEEP)
                return
            
            # 获取当前武器
            current_weapon = None
            if hasattr(current_unit, 'current_weapon') and current_unit.current_weapon:
                current_weapon = current_unit.current_weapon
            elif hasattr(current_unit.model, 'current_weapon') and current_unit.model.current_weapon:
                current_weapon = current_unit.model.current_weapon
            else:
                # 如果没有current_weapon或者为None，使用第一个武器
                current_weapon = current_unit.weapons[0]
            
            if current_weapon:
                # 显示武器详情
                self.parent.weapon_detail._show_weapon_detail(current_unit, current_weapon)
                return
            else:
                voice.item(mp.BEEP)
                return
            
        # 检查当前属性是否有子项
        if len(self.parent._current_attribute_sub_items) == 0:
            voice.item(mp.BEEP)
            return
            
        # 确认这是可导航的属性（可训练单位、可建造建筑、可升级单位、可研究科技、可推进时代、可使用技能、可采集资源、可用武器或库存物品）
        if not (isinstance(attr_value, tuple) and len(attr_value) == 2 and
                attr_value[0] in NAVIGABLE_ITEM_TYPES):
            voice.item(mp.BEEP)
            return
        
        item_type = attr_value[0]
        current_unit = self.parent._attributes_screen_unit
        
        # 根据不同类型处理
        if item_type == "CAN_TRAIN_ITEMS":
            # 处理可训练单位
            if not hasattr(current_unit, "can_train") or not current_unit.can_train:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（可训练单位类型）
            train_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(train_items):
                voice.item(mp.BEEP)
                return
                
            # 从 can_train 中获取单位类型名称
            unit_types = []
            if isinstance(current_unit.can_train, dict):
                unit_types = list(current_unit.can_train.keys())
            else:
                unit_types = list(current_unit.can_train)
                
            if self.parent._current_sub_item_index >= len(unit_types):
                voice.item(mp.BEEP)
                return
                
            selected_unit_type = unit_types[self.parent._current_sub_item_index]
            
        elif item_type == "CAN_BUILD_ITEMS":
            # 处理可建造建筑
            if not hasattr(current_unit, "can_build") or not current_unit.can_build:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（可建造建筑类型）
            build_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(build_items):
                voice.item(mp.BEEP)
                return
                
            # 从 can_build 中获取建筑类型名称
            building_types = []
            if isinstance(current_unit.can_build, dict):
                building_types = list(current_unit.can_build.keys())
            else:
                building_types = list(current_unit.can_build)
                
            if self.parent._current_sub_item_index >= len(building_types):
                voice.item(mp.BEEP)
                return
                
            selected_unit_type = building_types[self.parent._current_sub_item_index]
            
        elif item_type == "CAN_UPGRADE_TO_ITEMS":
            # 处理可升级单位
            if not hasattr(current_unit, "can_upgrade_to") or not current_unit.can_upgrade_to:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（可升级单位类型）
            upgrade_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(upgrade_items):
                voice.item(mp.BEEP)
                return
                
            # 从 can_upgrade_to 中获取单位类型名称
            upgrade_types = list(current_unit.can_upgrade_to)
            if self.parent._current_sub_item_index >= len(upgrade_types):
                voice.item(mp.BEEP)
                return
                
            selected_unit_type = upgrade_types[self.parent._current_sub_item_index]
            
        elif item_type == "CAN_RESEARCH_ITEMS":
            # 处理可研究科技
            if not hasattr(current_unit, "can_research") or not current_unit.can_research:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（可研究科技类型）
            research_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(research_items):
                voice.item(mp.BEEP)
                return
                
            # 从 can_research 中获取科技类型名称；
            # 与显示侧保持一致，剔除已迁移到 can_advance 的 phase 类型，
            # 避免索引与实际显示列表错位。
            try:
                from ..worldphase import is_a_phase
                from ..definitions import rules as _rules
            except Exception:
                is_a_phase = None
                _rules = None
            research_types = []
            for t in current_unit.can_research:
                if is_a_phase is not None and _rules is not None:
                    try:
                        if is_a_phase(_rules.unit_class(t)):
                            continue
                    except Exception:
                        pass
                research_types.append(t)
            if self.parent._current_sub_item_index >= len(research_types):
                voice.item(mp.BEEP)
                return
                
            selected_unit_type = research_types[self.parent._current_sub_item_index]
            
        elif item_type == "CAN_ADVANCE_ITEMS":
            # 处理可推进时代
            if not hasattr(current_unit, "can_advance") or not current_unit.can_advance:
                voice.item(mp.BEEP)
                return

            advance_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(advance_items):
                voice.item(mp.BEEP)
                return

            # 与显示侧（add_advance_attributes）保持一致：剔除非 phase
            # 类型，避免索引与实际显示列表错位。
            try:
                from ..worldphase import is_a_phase
                from ..definitions import rules as _rules
            except Exception:
                is_a_phase = None
                _rules = None
            advance_types = []
            for t in current_unit.can_advance:
                if is_a_phase is not None and _rules is not None:
                    try:
                        if not is_a_phase(_rules.unit_class(t)):
                            continue
                    except Exception:
                        pass
                advance_types.append(t)
            if self.parent._current_sub_item_index >= len(advance_types):
                voice.item(mp.BEEP)
                return

            selected_unit_type = advance_types[self.parent._current_sub_item_index]

        elif item_type == "CAN_USE_TECH_ITEMS":
            if not hasattr(current_unit, "can_use_tech") or not current_unit.can_use_tech:
                voice.item(mp.BEEP)
                return

            tech_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(tech_items):
                voice.item(mp.BEEP)
                return

            tech_types = list(current_unit.can_use_tech)
            if self.parent._current_sub_item_index >= len(tech_types):
                voice.item(mp.BEEP)
                return

            selected_unit_type = tech_types[self.parent._current_sub_item_index]

        elif item_type == "CAN_USE_SKILL_ITEMS":
            # 处理可使用技能
            # 从已学会技能列表中获取类型名称
            if hasattr(current_unit, "iter_manual_skill_names"):
                skill_types = list(current_unit.iter_manual_skill_names())
            else:
                skill_types = list(getattr(current_unit, "can_use_skill", ()) or ())
            if not skill_types:
                voice.item(mp.BEEP)
                return
            skill_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(skill_items):
                voice.item(mp.BEEP)
                return
            if self.parent._current_sub_item_index >= len(skill_types):
                voice.item(mp.BEEP)
                return
                
            selected_unit_type = skill_types[self.parent._current_sub_item_index]
            
        elif item_type in ("CAN_GATHER_ITEMS", "CAN_GATHER_DEPOSIT_ITEMS", "CAN_GATHER_BUILDING_ITEMS"):
            from .utils import gather_type_names
            type_names = gather_type_names(current_unit)
            if not type_names:
                voice.item(mp.BEEP)
                return
            gather_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(gather_items):
                voice.item(mp.BEEP)
                return
            if self.parent._current_sub_item_index >= len(type_names):
                voice.item(mp.BEEP)
                return
            selected_type = type_names[self.parent._current_sub_item_index]
            self.parent.resource_display._show_enhanced_resource_gather_detail(
                current_unit, selected_type
            )
            return
        
        elif item_type == "AVAILABLE_WEAPONS_ITEMS":
            # 处理可用武器
            if not hasattr(current_unit, "weapons") or not current_unit.weapons:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（可用武器类型）
            weapon_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(weapon_items):
                voice.item(mp.BEEP)
                return
                
            # 从 weapons 中获取武器类型名称
            weapon_types = list(current_unit.weapons)
            if self.parent._current_sub_item_index >= len(weapon_types):
                voice.item(mp.BEEP)
                return
                
            selected_weapon_type = weapon_types[self.parent._current_sub_item_index]
            
            # 显示武器详情
            self.parent.weapon_detail._show_weapon_detail(current_unit, selected_weapon_type)
            return
        
        elif item_type == "INVENTORY_ITEMS":
            # 处理库存物品
            if not hasattr(current_unit, "inventory") or not current_unit.inventory:
                voice.item(mp.BEEP)
                return
                
            # 获取当前选中的子项（库存物品）
            inventory_items = attr_value[1]
            if self.parent._current_sub_item_index >= len(inventory_items):
                voice.item(mp.BEEP)
                return
                
            # 从 inventory 中获取物品类型名称
            if self.parent._current_sub_item_index >= len(current_unit.inventory):
                voice.item(mp.BEEP)
                return
                
            selected_item = current_unit.inventory[self.parent._current_sub_item_index]
            
            # 显示物品详情
            self.parent.item_detail._show_item_detail(selected_item.type_name)
            return

        elif item_type in ("VS_ITEMS", "EFFECT_ITEMS"):
            voice.item(mp.BEEP)
            return
        
        self.parent.unit_detail._show_unit_detail(selected_unit_type)

    def cmd__exit_attributes_screen(self):
        """退出属性界面或从详细属性界面返回"""
        if not self.parent._in_attributes_screen:
            return
            
        # 如果在详细属性界面，返回到原始属性界面
        if self.parent._in_detail_attributes_screen and self.parent._saved_attributes_state:
            # 恢复原始状态
            self.parent._attributes_screen_unit = self.parent._saved_attributes_state['unit']
            self.parent._attributes_screen_attrs = self.parent._saved_attributes_state['attrs']
            self.parent._current_attribute_index = self.parent._saved_attributes_state['index']
            self.parent._current_sub_item_index = self.parent._saved_attributes_state['sub_index']
            self.parent._current_attribute_sub_items = self.parent._saved_attributes_state['sub_items']
            
            # 清理详细属性界面状态
            self.parent._in_detail_attributes_screen = False
            self.parent._saved_attributes_state = None
            
            # 播放返回音并显示当前属性
            voice.item(mp.BEEP)
            self.parent.main_display._display_current_attribute()
            
            # 重新设置键盘绑定以确保正确的按键处理
            self._setup_attributes_screen_bindings()
        else:
            # 完全退出属性界面
            self.parent._in_attributes_screen = False
            voice.item(mp.EXITING_ATTRIBUTES_SCREEN)
            
            # 重置状态变量
            self.parent._current_sub_item_index = 0
            self.parent._current_attribute_sub_items = []
            self.parent._in_detail_attributes_screen = False
            self.parent._saved_attributes_state = None
            
            # 恢复原始按键绑定
            if self.parent._original_bindings is not None:
                from ..clientgame.interface_modes import restore_active_bindings
                restore_active_bindings(self.parent.interface)
                self.parent._original_bindings = None

    def _process_keyboard_event(self, e):
        # 如果处于属性界面模式，优先处理属性界面的按键
        if self.parent._in_attributes_screen:
            try:
                result = self.parent._bindings.process_keydown_event(e)
                if result:
                    return True  # 按键被处理
            except Exception as err:
                from ..lib.log import debug
                debug(f"属性界面按键处理错误: {err}")
                return False
        return False  # 按键未被处理