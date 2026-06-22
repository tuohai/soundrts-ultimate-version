"""
动态采集属性处理模块
"""

from .. import msgparts as mp
from ..lib.msgs import format_signed_number, nb2msg_float
from ..clientmedia import voice
from .utils import get_stat_tts_name


class GatherHandler:
    def __init__(self, parent):
        self.parent = parent

    def _add_dynamic_gather_attributes(self, attrs, u, attr_prefix):
        """检测和添加动态采集属性（如gather_time_goldmine, gather_qty_woodcutter等）"""
        try:
            # 遍历单位模型的所有属性
            for attr_name in dir(u.model):
                # 跳过私有属性和方法
                if attr_name.startswith('_') or callable(getattr(u.model, attr_name, None)):
                    continue
                
                # 检查是否匹配目标前缀模式
                if attr_name.startswith(attr_prefix + "_"):
                    attr_value = getattr(u.model, attr_name, 0)
                    
                    if isinstance(attr_value, (int, float)) and attr_value != 0:
                        gather_msg = get_stat_tts_name(attr_name)
                        
                        if attr_prefix == "gather_time":
                            if abs(attr_value) > 1000:
                                time_seconds = round(attr_value / 1000.0, 1)
                            else:
                                time_seconds = round(attr_value, 1)
                            time_text = nb2msg_float(time_seconds) + mp.SECONDS
                            attrs.append(("", gather_msg, time_text))
                            
                        elif attr_prefix == "gather_qty":
                            qty_text = format_signed_number(int(attr_value))
                            attrs.append(("", gather_msg, qty_text))
                            
        except Exception as e:
            print(f"检测动态采集属性时出错: {e}")

    def _check_dynamic_gather_attribute(self, unit, attr_name, display_name):
        """检查并处理动态采集属性的用户查询"""
        try:
            if attr_name.startswith("gather_time_"):
                if hasattr(unit.model, attr_name):
                    attr_value = getattr(unit.model, attr_name, 0)
                    gather_time_msg = get_stat_tts_name(attr_name)
                    if attr_value != 0:
                        if abs(attr_value) > 1000:
                            time_seconds = round(attr_value / 1000.0, 1)
                        else:
                            time_seconds = round(attr_value, 1)
                        voice.item(
                            gather_time_msg + mp.COLON + format_signed_number(time_seconds, as_float=True) + mp.SECONDS
                        )
                        return True
                    voice.item(gather_time_msg + mp.COLON + mp.NO_SUCH_ATTRIBUTE)
                    return True
            
            elif attr_name.startswith("gather_qty_"):
                if hasattr(unit.model, attr_name):
                    attr_value = getattr(unit.model, attr_name, 0)
                    gather_qty_msg = get_stat_tts_name(attr_name)
                    if attr_value != 0:
                        voice.item(gather_qty_msg + mp.COLON + format_signed_number(int(attr_value)))
                        return True
                    voice.item(gather_qty_msg + mp.COLON + mp.NO_SUCH_ATTRIBUTE)
                    return True
                        
            resource_name = self.parent._get_resource_type_name(attr_name)
            if resource_name != attr_name:
                gather_time_attr = f"gather_time_{attr_name}"
                if hasattr(unit.model, gather_time_attr):
                    time_value = getattr(unit.model, gather_time_attr, 0)
                    if time_value != 0:
                        if abs(time_value) > 1000:
                            time_seconds = round(time_value / 1000.0, 1)
                        else:
                            time_seconds = round(time_value, 1)
                        gather_time_msg = get_stat_tts_name(gather_time_attr)
                        voice.item(
                            gather_time_msg + mp.COLON + format_signed_number(time_seconds, as_float=True) + mp.SECONDS
                        )
                        return True
                
                gather_qty_attr = f"gather_qty_{attr_name}"
                if hasattr(unit.model, gather_qty_attr):
                    qty_value = getattr(unit.model, gather_qty_attr, 0)
                    if qty_value != 0:
                        gather_qty_msg = get_stat_tts_name(gather_qty_attr)
                        voice.item(gather_qty_msg + mp.COLON + format_signed_number(int(qty_value)))
                        return True
                        
            return False
            
        except Exception as e:
            print(f"检查动态采集属性时出错: {e}")
            return False
