"""
资源类型名称处理工具模块
"""

from ..definitions import style


class ResourceUtils:
    def __init__(self, parent):
        self.parent = parent

    def _get_resource_type_name(self, resource_type):
        """动态获取资源类型的本地化名称（从rules和style中获取）"""
        try:
            # 首先尝试从style定义中获取资源类型的名称
            if hasattr(self.parent, 'interface') and hasattr(self.parent.interface, 'world'):
                # 如果world有resource_types_map，优先使用
                world = self.parent.interface.world
                if hasattr(world, 'resource_types_map') and resource_type in world.resource_types_map:
                    return world.resource_types_map[resource_type].get("name", resource_type)
            
            # 尝试从style定义中获取title
            resource_title = style.get(resource_type, "title")
            if resource_title:
                if isinstance(resource_title, list):
                    return " ".join(str(x) for x in resource_title)
                else:
                    return str(resource_title)
            
            # 尝试从rules中获取类型定义
            try:
                from ..definitions import rules
                # 尝试获取单位类定义
                unit_class = rules.unit_class(resource_type)
                if unit_class:
                    # 从style中获取该类型的title
                    type_title = style.get(resource_type, "title")
                    if type_title:
                        if isinstance(type_title, list):
                            return " ".join(str(x) for x in type_title)
                        else:
                            return str(type_title)
            except Exception:
                pass
            
            # 如果是标准的resource1, resource2格式，尝试从style获取对应的resource定义
            if resource_type.startswith("resource"):
                try:
                    resource_title = style.get(resource_type, "title")
                    if resource_title:
                        if isinstance(resource_title, list):
                            return " ".join(str(x) for x in resource_title)
                        else:
                            return str(resource_title)
                    
                    # 如果没有找到，尝试获取资源编号并生成默认名称
                    resource_num = int(resource_type.replace("resource", ""))
                    return f"资源{resource_num}"
                except ValueError:
                    pass
            
            # 如果是deposit类型，尝试从style获取对应的deposit定义
            if resource_type.startswith("deposit"):
                try:
                    deposit_title = style.get(resource_type, "title")
                    if deposit_title:
                        if isinstance(deposit_title, list):
                            return " ".join(str(x) for x in deposit_title)
                        else:
                            return str(deposit_title)
                    
                    # 如果没有找到，尝试获取矿床编号并生成默认名称
                    deposit_num = int(resource_type.replace("deposit", ""))
                    return f"矿床{deposit_num}"
                except ValueError:
                    pass
            
            # 尝试处理复合类型（如wood_deposit, gold_mine等）
            # 首先检查是否有下划线分隔的复合类型
            if "_" in resource_type:
                parts = resource_type.split("_")
                if len(parts) == 2:
                    base_type, suffix = parts
                    
                    # 尝试从style获取基础类型的名称
                    base_title = style.get(base_type, "title")
                    if base_title:
                        if isinstance(base_title, list):
                            base_name = " ".join(str(x) for x in base_title)
                        else:
                            base_name = str(base_title)
                        
                        # 根据后缀添加适当的描述
                        if suffix in ["deposit", "mine"]:
                            return base_name + "矿床"
                        elif suffix == "well":
                            return base_name + "井"
                        elif suffix == "mill":
                            return base_name + "厂"
                        elif suffix == "farm":
                            return base_name + "农场"
                        else:
                            return base_name + "_" + suffix
            
            # 尝试处理以特定后缀结尾的类型
            if resource_type.endswith("mine"):
                base_type = resource_type[:-4]  # 去掉"mine"
                base_title = style.get(base_type, "title")
                if base_title:
                    if isinstance(base_title, list):
                        base_name = " ".join(str(x) for x in base_title)
                    else:
                        base_name = str(base_title)
                    return base_name + "矿"
                else:
                    return resource_type + "矿"
            
            if resource_type.endswith("well"):
                base_type = resource_type[:-4]  # 去掉"well"
                base_title = style.get(base_type, "title")
                if base_title:
                    if isinstance(base_title, list):
                        base_name = " ".join(str(x) for x in base_title)
                    else:
                        base_name = str(base_title)
                    return base_name + "井"
                else:
                    return resource_type + "井"
            
            if resource_type.endswith("mill"):
                base_type = resource_type[:-4]  # 去掉"mill"
                base_title = style.get(base_type, "title")
                if base_title:
                    if isinstance(base_title, list):
                        base_name = " ".join(str(x) for x in base_title)
                    else:
                        base_name = str(base_title)
                    return base_name + "厂"
                else:
                    return resource_type + "厂"
            
            # 如果都没有找到，返回原始类型名称
            return resource_type
            
        except Exception:
            # 如果出现任何错误，返回原始资源类型名称
            return resource_type