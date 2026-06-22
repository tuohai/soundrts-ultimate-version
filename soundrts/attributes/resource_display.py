"""
资源属性显示模块
"""

from .. import msgparts as mp
from ..lib.msgs import nb2msg, nb2msg_float
from ..clientmedia import voice
from ..definitions import style
from ..clientgameentity.properties import carcass_short_title


class ResourceDisplay:
    def __init__(self, parent):
        self.parent = parent

    def _show_resource_attributes(self, resource):
        """显示矿床（Deposit）的属性界面"""
        try:
            from ..worldresource import Deposit
            
            # 构建资源属性列表
            attrs = []
            
            # 基本信息
            # 资源类型
            resource_type = getattr(resource, 'resource_type', None)
            if resource_type:
                resource_type_name = self.parent._get_resource_type_name(resource_type)
                attrs.append(("", mp.RESOURCE_TYPE, [resource_type_name]))
            
            # 资源名称（狩猎尸体带来源动物时显示「鹿的尸体」）
            if hasattr(resource, 'type_name') and resource.type_name:
                carcass_title = carcass_short_title(resource)
                if carcass_title:
                    attrs.append(("", mp.RESOURCE_NAME, list(carcass_title)))
            
            # 当前资源数量
            if hasattr(resource, 'qty') and resource.qty is not None:
                qty_text = nb2msg(resource.qty)
                attrs.append(("", mp.CURRENT_QUANTITY, qty_text))
            
            # 最大资源数量
            if hasattr(resource, 'qty_max') and resource.qty_max is not None:
                qty_max_text = nb2msg(resource.qty_max)
                attrs.append(("", mp.MAX_QUANTITY, qty_max_text))
            
            # 开采时间
            if hasattr(resource, 'extraction_time') and resource.extraction_time is not None:
                extraction_time = resource.extraction_time
                if isinstance(extraction_time, list) and extraction_time:
                    extraction_time = extraction_time[0]
                
                if extraction_time > 0:
                    # 智能转换时间单位
                    if extraction_time > 1000:
                        time_seconds = round(extraction_time / 1000.0, 1)
                    else:
                        time_seconds = round(extraction_time, 1)
                    time_text = nb2msg_float(time_seconds) + mp.SECONDS
                    attrs.append(("", mp.EXTRACTION_TIME, time_text))
            
            # 开采数量
            if hasattr(resource, 'extraction_qty') and resource.extraction_qty is not None:
                extraction_qty = resource.extraction_qty
                if isinstance(extraction_qty, list) and extraction_qty:
                    extraction_qty = extraction_qty[0]
                
                if extraction_qty > 0:
                    qty_text = nb2msg(extraction_qty)
                    attrs.append(("", mp.EXTRACTION_QTY, qty_text))
            
            # 资源再生时间（只对 Deposit 有效）
            if isinstance(resource, Deposit) and hasattr(resource, 'resource_regen') and resource.resource_regen:
                regen_time = resource.resource_regen
                if regen_time > 0:
                    # 智能转换时间单位
                    if regen_time > 1000:
                        regen_seconds = round(regen_time / 1000.0, 1)
                    else:
                        regen_seconds = round(regen_time, 1)
                    regen_text = nb2msg_float(regen_seconds) + mp.SECONDS
                    attrs.append(("", mp.RESOURCE_REGEN, regen_text))
            
            # 最大资源容量
            if hasattr(resource, 'resource_volume_max') and resource.resource_volume_max is not None:
                volume_max_text = nb2msg(resource.resource_volume_max)
                attrs.append(("", mp.RESOURCE_VOLUME_MAX, volume_max_text))
            
            # 初始资源容量
            if hasattr(resource, 'resource_volume_start') and resource.resource_volume_start is not None:
                volume_start_text = nb2msg(resource.resource_volume_start)
                attrs.append(("", mp.RESOURCE_VOLUME_START, volume_start_text))
            
            # 矿床类型（对于 Deposit）
            if isinstance(resource, Deposit):
                attrs.append(("", mp.DEPOSIT_TYPE, ["矿床"]))
            else:
                attrs.append(("", mp.DEPOSIT_TYPE, mp.RESOURCE_POINT))
            
            # 保存属性列表以供界面使用
            self.parent._attributes_screen_attrs = attrs
            
            # 显示标题和提示
            resource_display_name = getattr(resource, 'type_name', '资源')
            if hasattr(resource, 'type_name') and resource.type_name:
                resource_title = style.get(resource.type_name, "title")
                if resource_title:
                    if isinstance(resource_title, list):
                        resource_display_name = " ".join(str(x) for x in resource_title)
                    else:
                        resource_display_name = str(resource_title)
            
            voice.item([resource_display_name] + mp.ATTRIBUTES + mp.PRESS_LETTER_FOR_INFO + mp.COMMA + mp.PRESS_ESC_TO_EXIT)
            
            # 显示第一个属性开始
            if attrs:
                self.parent._current_attribute_index = 0
                self.parent._current_sub_item_index = 0
                self.parent.main_display._display_current_attribute()
            else:
                voice.item(mp.NO_ATTRIBUTES)
                self.parent._current_attribute_index = -1
            
            # 进入属性界面模式
            self.parent._in_attributes_screen = True
            
            # 保存原始按键绑定
            self.parent._original_bindings = self.parent._bindings
            
            # 创建新的按键绑定用于属性界面
            self.parent.key_bindings._setup_attributes_screen_bindings()
            
        except Exception as e:
            # 出错时恢复原始状态
            voice.item(mp.BEEP)
            print(f"Error showing resource attributes: {e}")

    def _show_enhanced_resource_gather_detail(self, current_unit, resource_type):
        """显示增强的资源采集详情，包括class、resource_type、extraction_time、extraction_qty、resource_regen等信息"""
        try:
            # 获取资源类型的友好名称
            resource_name = self.parent._get_resource_type_name(resource_type)
            
            # 构建资源详情属性列表
            attrs = []
            
            # 1. 基本信息
            # 资源名称
            attrs.append(("", mp.RESOURCE_NAME, [resource_name]))
            
            # 2. 尝试从rules系统获取资源类型的详细信息
            try:
                from ..definitions import rules, style
                
                # 检查是否是矿床类型
                resource_class = rules.unit_class(resource_type)
                if resource_class:
                    # 显示class信息（矿床或资源）
                    if hasattr(resource_class, 'class'):
                        class_info = getattr(resource_class, 'class')
                        if class_info:
                            if isinstance(class_info, list):
                                class_name = class_info[0] if class_info else resource_type
                            else:
                                class_name = class_info
                            
                            # 转换class名称为中文
                            if class_name == "deposit":
                                attrs.append(("", mp.CATEGORY, ["矿床"]))
                            elif class_name == "resource":
                                attrs.append(("", mp.CATEGORY, mp.RESOURCE_POINT))
                            else:
                                attrs.append(("", mp.CATEGORY, [class_name]))
                    
                    # 显示resource_type（出产的资源类型）
                    if hasattr(resource_class, 'resource_type') and resource_class.resource_type:
                        produced_resource_name = self.parent._get_resource_type_name(resource_class.resource_type)
                        attrs.append(("", mp.RESOURCE_TYPE, [produced_resource_name]))
                    
                    # 显示extraction_time（开采时间）
                    if hasattr(resource_class, 'extraction_time') and resource_class.extraction_time is not None:
                        extraction_time = resource_class.extraction_time
                        if isinstance(extraction_time, list) and extraction_time:
                            extraction_time = extraction_time[0]
                        
                        if extraction_time != 0:  # 显示所有非零值，包括负数
                            # 智能转换时间单位
                            if abs(extraction_time) > 1000:
                                time_seconds = round(extraction_time / 1000.0, 1)
                            else:
                                time_seconds = round(extraction_time, 1)
                            time_text = nb2msg_float(time_seconds) + mp.SECONDS
                            attrs.append(("", mp.EXTRACTION_TIME, time_text))
                    
                    # 显示extraction_qty（开采数量）
                    if hasattr(resource_class, 'extraction_qty') and resource_class.extraction_qty is not None:
                        extraction_qty = resource_class.extraction_qty
                        if isinstance(extraction_qty, list) and extraction_qty:
                            extraction_qty = extraction_qty[0]
                        
                        if extraction_qty != 0:  # 显示所有非零值，包括负数
                            qty_text = nb2msg(extraction_qty)
                            attrs.append(("", mp.EXTRACTION_QTY, qty_text))
                    
                    # 显示resource_regen（资源再生时间）
                    if hasattr(resource_class, 'resource_regen') and resource_class.resource_regen:
                        regen_time = resource_class.resource_regen
                        if regen_time > 0:
                            # 智能转换时间单位
                            if regen_time > 1000:
                                regen_seconds = round(regen_time / 1000.0, 1)
                            else:
                                regen_seconds = round(regen_time, 1)
                            regen_text = nb2msg_float(regen_seconds) + mp.SECONDS
                            attrs.append(("", mp.RESOURCE_REGEN, regen_text))
                    
                    # 显示resource_volume_max（最大资源容量）
                    if hasattr(resource_class, 'resource_volume_max') and resource_class.resource_volume_max is not None:
                        if resource_class.resource_volume_max > 0:
                            volume_max_text = nb2msg(resource_class.resource_volume_max)
                            attrs.append(("", mp.RESOURCE_VOLUME_MAX, volume_max_text))
                    
                    # 显示resource_volume_start（初始资源容量）
                    if hasattr(resource_class, 'resource_volume_start') and resource_class.resource_volume_start is not None:
                        if resource_class.resource_volume_start > 0:
                            volume_start_text = nb2msg(resource_class.resource_volume_start)
                            attrs.append(("", mp.RESOURCE_VOLUME_START, volume_start_text))
                    
                    # 显示其他属性
                    if hasattr(resource_class, 'hp_max') and resource_class.hp_max > 0:
                        from ..lib.nofloat import PRECISION
                        hp_text = nb2msg_float(resource_class.hp_max / PRECISION)
                        attrs.append(("", mp.HP, hp_text))
                    
                    if hasattr(resource_class, 'is_a') and resource_class.is_a:
                        is_a_text = []
                        if isinstance(resource_class.is_a, list):
                            for unit_type in resource_class.is_a:
                                type_title = style.get(unit_type, "title")
                                if type_title:
                                    if isinstance(type_title, list):
                                        is_a_text.extend(type_title)
                                    else:
                                        is_a_text.append(str(type_title))
                                    is_a_text.extend(mp.COMMA)
                            # 移除最后一个逗号
                            if is_a_text and is_a_text[-1] in mp.COMMA:
                                is_a_text = is_a_text[:-1]
                        else:
                            type_title = style.get(resource_class.is_a, "title")
                            if type_title:
                                if isinstance(type_title, list):
                                    is_a_text.extend(type_title)
                                else:
                                    is_a_text.append(str(type_title))
                            else:
                                is_a_text.append(str(resource_class.is_a))
                        
                        if is_a_text:
                            attrs.append(("", mp.IS_A, is_a_text))
                            
            except Exception as e:
                # 如果不是rules中定义的类型，忽略错误
                pass
            
            # 3. 显示当前单位对这个资源类型的采集信息
            # 这里需要检查采集时间和数量等信息...
            
            # 保存当前状态，以便返回
            self.parent._saved_attributes_state = {
                'unit': self.parent._attributes_screen_unit,
                'attrs': self.parent._attributes_screen_attrs,
                'index': self.parent._current_attribute_index,
                'sub_index': self.parent._current_sub_item_index,
                'sub_items': self.parent._current_attribute_sub_items
            }
            
            # 设置详细属性界面标志
            self.parent._in_detail_attributes_screen = True
            
            # 更新属性界面
            self.parent._attributes_screen_attrs = attrs
            
            # 显示资源采集详情
            voice.item([resource_name] + ["详细信息"])
            
            # 显示第一个属性
            if attrs:
                self.parent._current_attribute_index = 0
                self.parent._current_sub_item_index = 0
                self.parent._current_attribute_sub_items = []
                self.parent.main_display._display_current_attribute()
            else:
                voice.item(mp.NO_ATTRIBUTES)
                
        except Exception as e:
            # 出错时恢复原始状态
            voice.item(mp.BEEP)
            print(f"Error showing enhanced resource gather detail: {e}")