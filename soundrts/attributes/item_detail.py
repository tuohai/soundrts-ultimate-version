"""
物品详情显示模块
"""

from .. import msgparts as mp
from ..lib.msgs import nb2msg
from ..clientmedia import voice
from ..definitions import style


class ItemDetail:
    def __init__(self, parent):
        self.parent = parent

    def _show_item_detail(self, item_type_name):
        """显示指定物品类型的详细属性界面"""
        try:
            # 导入 rules
            from ..definitions import rules
            
            # 获取物品类型定义
            item_class = rules.unit_class(item_type_name)
            
            # 如果找不到物品类型定义，显示基本信息
            if item_class is None:
                voice.item(mp.NO_SUCH_ATTRIBUTE)
                return
            
            # 保存当前状态，以便返回
            self.parent._saved_attributes_state = {
                'unit': self.parent._attributes_screen_unit,
                'attrs': self.parent._attributes_screen_attrs,
                'index': self.parent._current_attribute_index,
                'sub_index': self.parent._current_sub_item_index,
                'sub_items': self.parent._current_attribute_sub_items
            }
            
            # 切换到详细界面
            self.parent._in_detail_attributes_screen = True
            
            # 构建物品属性列表
            attrs = []
            
            # 显示物品名称
            item_title = style.get(item_type_name, "title")
            if item_title:
                if isinstance(item_title, list):
                    title_text = item_title
                else:
                    title_text = [str(item_title)]
            else:
                title_text = [item_type_name]
            
            attrs.append(("", mp.ITEM_NAME, title_text))

            intro = style.get(item_type_name, "intro")
            if intro:
                if isinstance(intro, list):
                    attrs.append(("?", mp.INTRO, intro))
                else:
                    attrs.append(("?", mp.INTRO, [str(intro)]))
            
            # 创建临时物品实例来获取property属性的值
            try:
                temp_item = item_class()
            except:
                temp_item = None
            
            # 显示物品类型 (is_a)
            if hasattr(item_class, "is_a") and item_class.is_a:
                is_a_text = []
                if isinstance(item_class.is_a, (list, tuple)):
                    for item_type in item_class.is_a:
                        type_title = style.get(item_type, "title")
                        if type_title:
                            if isinstance(type_title, list):
                                is_a_text.extend(type_title)
                            else:
                                is_a_text.append(str(type_title))
                        else:
                            is_a_text.append(str(item_type))
                        is_a_text.extend(mp.COMMA)
                    # 移除最后一个逗号
                    if is_a_text and is_a_text[-1] in mp.COMMA:
                        is_a_text = is_a_text[:-1]
                else:
                    # 单个类型
                    type_title = style.get(item_class.is_a, "title")
                    if type_title:
                        if isinstance(type_title, list):
                            is_a_text.extend(type_title)
                        else:
                            is_a_text.append(str(type_title))
                    else:
                        is_a_text.append(str(item_class.is_a))
                
                if is_a_text:
                    attrs.append(("i", mp.IS_A, is_a_text))
            
            # 显示物品职业 (class)
            if hasattr(item_class, "class"):
                item_classes = getattr(item_class, "class")
                if item_classes:
                    class_text = []
                    if isinstance(item_classes, list):
                        for class_type in item_classes:
                            class_title = style.get(class_type, "title")
                            if class_title:
                                if isinstance(class_title, list):
                                    class_text.extend(class_title)
                                else:
                                    class_text.append(str(class_title))
                            else:
                                class_text.append(str(class_type))
                            class_text.extend(mp.COMMA)
                        # 移除最后一个逗号
                        if class_text and class_text[-1] in mp.COMMA:
                            class_text = class_text[:-1]
                    else:
                        # 单个职业
                        class_title = style.get(item_classes, "title")
                        if class_title:
                            if isinstance(class_title, list):
                                class_text.extend(class_title)
                            else:
                                class_text.append(str(class_title))
                        else:
                            class_text.append(str(item_classes))
                    
                    if class_text:
                        attrs.append(("c", mp.CLASS, class_text))
            
            # 显示物品属性
            # 拾取时是否消耗
            if hasattr(item_class, "consume_on_pickup") and item_class.consume_on_pickup:
                consume_text = mp.YES if item_class.consume_on_pickup else mp.NO
                attrs.append(("", mp.CONSUME_ON_PICKUP, consume_text))
            
            # 运输体积
            if hasattr(item_class, "transport_volume") and item_class.transport_volume > 0:
                volume_text = nb2msg(item_class.transport_volume)
                attrs.append(("", mp.TRANSPORT_VOLUME, volume_text))
            
            # 是否为战利品
            if hasattr(item_class, "is_loot") and item_class.is_loot:
                loot_text = mp.YES if item_class.is_loot else mp.NO
                attrs.append(("", mp.IS_LOOT, loot_text))
            
            # 资源奖励
            if hasattr(item_class, "resource_rewards") and item_class.resource_rewards:
                rewards_text = []
                for i, reward in enumerate(item_class.resource_rewards):
                    if reward > 0:
                        rewards_text.extend(nb2msg(reward))
                        # 使用通用的资源名称
                        resource_name = f"resource{i + 1}"
                        resource_title = style.get(resource_name, "title")
                        if resource_title:
                            if isinstance(resource_title, list):
                                rewards_text.extend(resource_title)
                            else:
                                rewards_text.append(str(resource_title))
                        rewards_text.extend(mp.COMMA)
                if rewards_text:
                    rewards_text = rewards_text[:-1]  # 移除最后一个逗号
                    attrs.append(("", mp.RESOURCE_REWARDS, rewards_text))
            
            # 技能
            if hasattr(item_class, "skills") and item_class.skills:
                skills_text = []
                for skill in item_class.skills:
                    skill_title = style.get(skill, "title")
                    if skill_title:
                        if isinstance(skill_title, list):
                            skills_text.extend(skill_title)
                        else:
                            skills_text.append(str(skill_title))
                    else:
                        skills_text.append(str(skill))
                    skills_text.extend(mp.COMMA)
                if skills_text:
                    skills_text = skills_text[:-1]  # 移除最后一个逗号
                    attrs.append(("", mp.SKILLS, skills_text))
            
            # Buff效果
            if hasattr(item_class, "buffs") and item_class.buffs:
                buffs_text = []
                for buff in item_class.buffs:
                    buff_title = style.get(buff, "title")
                    if buff_title:
                        if isinstance(buff_title, list):
                            buffs_text.extend(buff_title)
                        else:
                            buffs_text.append(str(buff_title))
                    else:
                        buffs_text.append(str(buff))
                    buffs_text.extend(mp.COMMA)
                if buffs_text:
                    buffs_text = buffs_text[:-1]  # 移除最后一个逗号
                    attrs.append(("", mp.BUFFS, buffs_text))
            
            # 创建临时物品对象用于显示
            class SimpleItem:
                def __init__(self):
                    self.type_name = item_type_name
                
                @property
                def title(self):
                    return title_text
                
                @property
                def hp_status(self):
                    return ["无生命值"]
                
                @property
                def mana_status(self):
                    return ["无魔法值"]
                
                @property
                def upgrades_status(self):
                    return []
            
            # 设置新的属性界面
            self.parent._attributes_screen_unit = SimpleItem()
            self.parent._attributes_screen_attrs = attrs
            self.parent._current_attribute_index = 0
            self.parent._current_sub_item_index = 0
            self.parent._current_attribute_sub_items = []
            
            # 播放物品名称
            if len(attrs) > 1:
                voice.item(title_text + ["的属性"])
            else:
                voice.item(title_text + ["没有可用属性"])
            
            # 显示第一个属性
            if len(attrs) > 1:
                self.parent.main_display._display_current_attribute()
            
        except Exception as e:
            # 错误处理
            voice.item(["显示物品详情时出错"] + [str(e)])