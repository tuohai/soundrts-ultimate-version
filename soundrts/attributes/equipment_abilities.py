"""
装备和能力显示模块
处理武器、护甲、库存、技能、科技等相关属性
"""

from .. import msgparts as mp
from ..lib.nofloat import PRECISION
from ..lib.msgs import nb2msg, nb2msg_float
from ..definitions import style


class EquipmentAbilities:
    def __init__(self, main_interface):
        self.main_interface = main_interface
    
    def add_weapon_attributes(self, u, attrs):
        """添加武器相关属性"""
        # 武器信息显示
        if hasattr(u, 'weapons') and u.weapons:
            weapon_info = []
            
            # 显示当前装备的武器
            # 尝试多种方式获取当前武器
            current_weapon = None
            if hasattr(u, 'current_weapon'):
                current_weapon = u.current_weapon
            elif hasattr(u.model, 'current_weapon'):
                current_weapon = u.model.current_weapon
            
            # 如果没有current_weapon或者为None，使用第一个武器
            if not current_weapon and u.weapons:
                current_weapon = u.weapons[0]
            
            if current_weapon:
                weapon_title = style.get(current_weapon, "title")
                if weapon_title:
                    if isinstance(weapon_title, list):
                        weapon_info.extend(weapon_title)
                    else:
                        weapon_info.append(str(weapon_title))
                else:
                    weapon_info.append(current_weapon)
                
                # 如果有多个武器，显示可切换提示
                if len(u.weapons) > 1:
                    weapon_info.extend(mp.COMMA)
                    weapon_info.extend(mp.SWITCHABLE)
            
            if weapon_info:
                attrs.append(("w", mp.CURRENT_WEAPON, weapon_info))
            
            # 如果有多个武器，显示所有可用武器，并支持导航
            if len(u.weapons) > 1:
                weapon_items = []
                for weapon_name in u.weapons:
                    weapon_title = style.get(weapon_name, "title")
                    if weapon_title:
                        if isinstance(weapon_title, list):
                            weapon_items.append(weapon_title)
                        else:
                            weapon_items.append([str(weapon_title)])
                    else:
                        weapon_items.append([weapon_name])
                
                if weapon_items:
                    # 保存为特殊格式，用 "AVAILABLE_WEAPONS_ITEMS" 标记这是可导航的项目列表
                    attrs.append(("", mp.AVAILABLE_WEAPONS, ("AVAILABLE_WEAPONS_ITEMS", weapon_items)))
    
    def add_armor_attributes(self, u, attrs):
        """添加护甲相关属性"""
        # 护甲信息显示
        if hasattr(u, 'armor') and u.armor:
            armor_info = []
            
            # 显示当前装备的护甲
            current_armor = u.armor
            if current_armor:
                armor_title = style.get(current_armor, "title")
                if armor_title:
                    if isinstance(armor_title, list):
                        armor_info.extend(armor_title)
                    else:
                        armor_info.append(str(armor_title))
                else:
                    armor_info.append(current_armor)
            
            if armor_info:
                attrs.append(("k", mp.CURRENT_ARMOR, armor_info))
    
    def add_inventory_attributes(self, u, attrs):
        """添加库存相关属性"""
        # 库存显示
        if hasattr(u, 'inventory') and u.inventory:
            inventory_items = []
            for item in u.inventory:
                item_title = style.get(item.type_name, "title")
                if item_title:
                    if isinstance(item_title, list):
                        inventory_items.append(item_title)
                    else:
                        inventory_items.append([str(item_title)])
                else:
                    inventory_items.append([item.type_name])
            
            if inventory_items:
                # 保存为特殊格式，用 "INVENTORY_ITEMS" 标记这是可导航的项目列表
                attrs.append(("v", mp.INVENTORY, ("INVENTORY_ITEMS", inventory_items)))
        
        # 库存容量
        if hasattr(u.model, "inventory_capacity") and u.model.inventory_capacity > 0:
            inventory_capacity_text = nb2msg(u.model.inventory_capacity)
            attrs.append(("", mp.INVENTORY_CAPACITY, inventory_capacity_text))
    
    def add_status_attributes(self, u, attrs):
        """添加特殊状态属性"""
        # 特殊状态
        status_text = []
        if getattr(u, "is_invisible", 0) or getattr(u, "is_cloaked", 0):
            status_text.extend(mp.INVISIBLE)
        if getattr(u, "is_a_detector", 0):
            status_text.extend(mp.DETECTOR)
        if getattr(u, "is_a_cloaker", 0):
            status_text.extend(mp.CLOAKER)
        
        if status_text:
            attrs.append(("t", mp.STATS, status_text))
    
    def add_unit_type_attributes(self, u, attrs):
        """添加单位类型相关属性"""
        # 单位类型
        if hasattr(u.model, "is_a") and u.model.is_a:
            is_a_text = []
            if isinstance(u.model.is_a, list):
                for unit_type in u.model.is_a:
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
                # 单个类型
                type_title = style.get(u.model.is_a, "title")
                if type_title:
                    if isinstance(type_title, list):
                        is_a_text.extend(type_title)
                    else:
                        is_a_text.append(str(type_title))
                else:
                    is_a_text.append(str(u.model.is_a))
            
            if is_a_text:
                attrs.append(("i", mp.IS_A, is_a_text))
    
    def add_class_attributes(self, u, attrs):
        """添加单位职业相关属性"""
        # 单位职业
        try:
            from ..definitions import rules
            unit_type_name = getattr(u, 'type_name', None) or getattr(u.model, 'type_name', None)
            if unit_type_name:
                unit_class_obj = rules.unit_class(unit_type_name)
                if unit_class_obj and hasattr(unit_class_obj, "class"):
                    unit_classes = getattr(unit_class_obj, "class")
                    if unit_classes:
                        class_text = []
                        if isinstance(unit_classes, list):
                            for class_type in unit_classes:
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
                            class_title = style.get(unit_classes, "title")
                            if class_title:
                                if isinstance(class_title, list):
                                    class_text.extend(class_title)
                                else:
                                    class_text.append(str(class_title))
                            else:
                                class_text.append(str(unit_classes))
                        
                        if class_text:
                            attrs.append(("c", mp.CLASS, class_text))
        except Exception as e:
            pass
    
    def add_training_attributes(self, u, attrs):
        """添加训练相关属性"""
        # 可训练单位 - 直接从单位对象访问（原始代码方式）
        if hasattr(u, "can_train") and u.can_train:
            train_items = []
            if isinstance(u.can_train, dict):
                # 新格式：字典形式，包含训练数量
                for unit_type, count in u.can_train.items():
                    unit_title = style.get(unit_type, "title")
                    if unit_title:
                        if isinstance(unit_title, list):
                            if count > 1:
                                # 如果数量大于1，显示数量
                                train_items.append(unit_title + ["×" + str(count)])
                            else:
                                # 数量为1时只显示单位名称
                                train_items.append(unit_title)
                        else:
                            if count > 1:
                                train_items.append([str(unit_title)] + ["×" + str(count)])
                            else:
                                train_items.append([str(unit_title)])
                    else:
                        if count > 1:
                            train_items.append([unit_type] + ["×" + str(count)])
                        else:
                            train_items.append([unit_type])
            else:
                # 旧格式：列表形式，默认数量为1
                for unit_type in u.can_train:
                    unit_title = style.get(unit_type, "title")
                    if unit_title:
                        if isinstance(unit_title, list):
                            train_items.append(unit_title)
                        else:
                            train_items.append([str(unit_title)])
                    else:
                        train_items.append([unit_type])
            
            if train_items:
                # 保存为特殊格式，用 "CAN_TRAIN_ITEMS" 标记这是可导航的项目列表
                attrs.append(("o", mp.CAN_TRAIN, ("CAN_TRAIN_ITEMS", train_items)))
    
    def add_building_attributes(self, u, attrs):
        """添加建造相关属性"""
        # 可建造建筑 - 直接从单位对象访问（原始代码方式）
        if hasattr(u, "can_build") and u.can_build:
            build_items = []
            if isinstance(u.can_build, dict):
                # 新格式：字典形式，包含建造数量
                for building_type, count in u.can_build.items():
                    building_title = style.get(building_type, "title")
                    if building_title:
                        if isinstance(building_title, list):
                            if count > 1:
                                # 如果数量大于1，显示数量
                                build_items.append(building_title + ["×" + str(count)])
                            else:
                                # 数量为1时只显示建筑名称
                                build_items.append(building_title)
                        else:
                            if count > 1:
                                build_items.append([str(building_title)] + ["×" + str(count)])
                            else:
                                build_items.append([str(building_title)])
                    else:
                        if count > 1:
                            build_items.append([building_type] + ["×" + str(count)])
                        else:
                            build_items.append([building_type])
            else:
                # 旧格式：列表形式，默认数量为1
                for building_type in u.can_build:
                    building_title = style.get(building_type, "title")
                    if building_title:
                        if isinstance(building_title, list):
                            build_items.append(building_title)
                        else:
                            build_items.append([str(building_title)])
                    else:
                        build_items.append([building_type])
            
            if build_items:
                # 保存为特殊格式，用 "CAN_BUILD_ITEMS" 标记这是可导航的项目列表
                attrs.append(("b", mp.CAN_BUILD, ("CAN_BUILD_ITEMS", build_items)))
    
    def add_upgrade_attributes(self, u, attrs):
        """添加升级相关属性"""
        # 可升级到 - 直接从单位对象访问（原始代码方式）
        if hasattr(u, "can_upgrade_to") and u.can_upgrade_to:
            upgrade_items = []
            for upgrade_type in u.can_upgrade_to:
                upgrade_title = style.get(upgrade_type, "title")
                if upgrade_title:
                    if isinstance(upgrade_title, list):
                        upgrade_items.append(upgrade_title)
                    else:
                        upgrade_items.append([str(upgrade_title)])
                else:
                    upgrade_items.append([upgrade_type])
            
            if upgrade_items:
                # 保存为特殊格式，用 "CAN_UPGRADE_TO_ITEMS" 标记这是可导航的项目列表
                attrs.append(("", mp.CAN_UPGRADE_TO, ("CAN_UPGRADE_TO_ITEMS", upgrade_items)))
        
        # 单位升级状态
        if hasattr(u, "upgrades") and u.upgrades:
            upgrades_list = []
            for upgrade_name in u.upgrades:
                upgrade_title = style.get(upgrade_name, "title")
                if upgrade_title:
                    if isinstance(upgrade_title, list):
                        upgrades_list.extend(upgrade_title)
                    else:
                        upgrades_list.append(str(upgrade_title))
                else:
                    upgrades_list.append(str(upgrade_name))
                upgrades_list.extend(mp.COMMA)
            
            if upgrades_list:
                upgrades_list = upgrades_list[:-1]  # 移除最后一个逗号
                attrs.append(("u", mp.TECHNIC_STATS, upgrades_list))
    
    def add_research_attributes(self, u, attrs):
        """添加研究相关属性

        注意：此处只显示普通科技。phase（时代）已经迁移到独立的
        ``can_advance`` 字段；为了兼容老地图把 phase 误写在 ``can_research``
        中的情况，这里也会显式跳过 phase 类型，避免与 ``add_advance_attributes``
        重复展示。
        """
        if not (hasattr(u, "can_research") and u.can_research):
            return

        try:
            from ..worldphase import is_a_phase
            from ..definitions import rules as _rules
        except Exception:
            is_a_phase = None
            _rules = None

        research_items = []
        for research_type in u.can_research:
            if is_a_phase is not None and _rules is not None:
                try:
                    if is_a_phase(_rules.unit_class(research_type)):
                        continue
                except Exception:
                    pass
            research_title = style.get(research_type, "title")
            if research_title:
                if isinstance(research_title, list):
                    research_items.append(research_title)
                else:
                    research_items.append([str(research_title)])
            else:
                research_items.append([research_type])

        if research_items:
            attrs.append(("", mp.CAN_RESEARCH, ("CAN_RESEARCH_ITEMS", research_items)))

    def add_advance_attributes(self, u, attrs):
        """添加可推进时代相关属性

        与 ``add_research_attributes`` 分离显示，让 UI 与读屏体验中"科技"
        与"时代"两类升级泾渭分明：从 ``can_advance`` 收集条目，并附带
        type 标记 ``CAN_ADVANCE_ITEMS``，由 key_bindings 中的导航分支处理。
        """
        if not (hasattr(u, "can_advance") and u.can_advance):
            return

        try:
            from ..worldphase import is_a_phase
            from ..definitions import rules as _rules
        except Exception:
            is_a_phase = None
            _rules = None

        advance_items = []
        for advance_type in u.can_advance:
            # 仅展示真正的 phase 项；非 phase 跳过，避免与科技混淆。
            if is_a_phase is not None and _rules is not None:
                try:
                    if not is_a_phase(_rules.unit_class(advance_type)):
                        continue
                except Exception:
                    pass
            advance_title = style.get(advance_type, "title")
            if advance_title:
                if isinstance(advance_title, list):
                    advance_items.append(advance_title)
                else:
                    advance_items.append([str(advance_title)])
            else:
                advance_items.append([advance_type])

        if advance_items:
            attrs.append(("", mp.CAN_ADVANCE, ("CAN_ADVANCE_ITEMS", advance_items)))
    
    def add_tech_skill_attributes(self, u, attrs):
        """添加科技和技能相关属性"""
        # 可使用的技术 - 直接从单位对象访问（原始代码方式）
        if hasattr(u, "can_use_tech") and u.can_use_tech:
            tech_items = []
            for tech_type in u.can_use_tech:
                tech_title = style.get(tech_type, "title")
                if tech_title:
                    if isinstance(tech_title, list):
                        tech_items.append(tech_title)
                    else:
                        tech_items.append([str(tech_title)])
                else:
                    tech_items.append([tech_type])
            
            if tech_items:
                attrs.append(("", mp.CAN_USE_TECH, ("CAN_USE_TECH_ITEMS", tech_items)))
        
        # 可使用的技能（手动 + 已学会的自动触发技能，统一列表）
        skill_names = (
            list(u.iter_manual_skill_names())
            if hasattr(u, "iter_manual_skill_names")
            else list(getattr(u, "can_use_skill", ()) or ())
        )
        if skill_names:
            skill_items = []
            for skill_type in skill_names:
                skill_title = style.get(skill_type, "title")
                if skill_title:
                    if isinstance(skill_title, list):
                        skill_items.append(skill_title)
                    else:
                        skill_items.append([str(skill_title)])
                else:
                    skill_items.append([skill_type])
            
            if skill_items:
                attrs.append(("", mp.CAN_USE_SKILL, ("CAN_USE_SKILL_ITEMS", skill_items)))
    
    def add_gather_attributes(self, u, attrs):
        """添加采集相关属性（矿床与可采集建筑合并为一条可导航列表）"""
        from .utils import gather_type_names

        type_names = gather_type_names(u)
        if type_names:
            gather_items = []
            for type_name in type_names:
                if type_name == "all":
                    gather_items.append(["all"])
                    continue
                type_title = style.get(type_name, "title")
                if type_title:
                    if isinstance(type_title, list):
                        gather_items.append(type_title)
                    else:
                        gather_items.append([str(type_title)])
                else:
                    gather_items.append([type_name])
            if gather_items:
                attrs.append(("", mp.CAN_GATHER, ("CAN_GATHER_ITEMS", gather_items)))
        
        # 动态采集属性
        self.main_interface._add_dynamic_gather_attributes(attrs, u, "gather_time")
        
        # 动态采集数量属性
        self.main_interface._add_dynamic_gather_attributes(attrs, u, "gather_qty")

    @staticmethod
    def _scalar_time_text(time_val):
        if time_val is None:
            return None
        if isinstance(time_val, (list, tuple)) and time_val:
            time_val = time_val[0]
        if not time_val or time_val <= 0:
            return None
        if time_val > 1000:
            time_seconds = round(time_val / 1000.0, 1)
        else:
            time_seconds = round(time_val, 1)
        return nb2msg_float(time_seconds) + mp.SECONDS

    def _format_production_cost_text(self, production_cost):
        if not production_cost:
            return None
        cost_text = []
        for i, cost_value in enumerate(production_cost):
            if cost_value > 0:
                cost_text.extend(nb2msg(int(cost_value / PRECISION)))
                resource_title = style.get(f"resource{i + 1}", "title")
                if resource_title:
                    if isinstance(resource_title, list):
                        cost_text.extend(resource_title)
                    else:
                        cost_text.append(str(resource_title))
                cost_text.extend(mp.COMMA)
        if not cost_text:
            return None
        return cost_text[:-len(mp.COMMA)]

    def add_building_resource_attributes(self, u, attrs):
        """添加可采集建筑（农庄等）的资源储量与开采参数。"""
        if not getattr(u, "is_a_building", False):
            return
        model = u.model

        resource_type = getattr(model, "resource_type", None)
        if resource_type:
            resource_type_name = self.main_interface._get_resource_type_name(
                resource_type
            )
            attrs.append(("", mp.RESOURCE_TYPE, [resource_type_name]))

        time_text = self._scalar_time_text(getattr(model, "extraction_time", None))
        if time_text:
            attrs.append(("", mp.EXTRACTION_TIME, time_text))

        extraction_qty = getattr(model, "extraction_qty", None)
        if isinstance(extraction_qty, (list, tuple)) and extraction_qty:
            extraction_qty = extraction_qty[0]
        if extraction_qty is not None and extraction_qty > 0:
            attrs.append(("", mp.EXTRACTION_QTY, nb2msg(extraction_qty)))

        volume_max = getattr(model, "resource_volume_max", None)
        if volume_max is not None and volume_max > 0:
            attrs.append(("", mp.RESOURCE_VOLUME_MAX, nb2msg(volume_max)))

        volume_start = getattr(model, "resource_volume_start", None)
        if volume_start is not None and volume_start > 0:
            attrs.append(("", mp.RESOURCE_VOLUME_START, nb2msg(volume_start)))

        resource_qty = getattr(u, "resource_qty", None)
        if resource_qty is not None and resource_qty > 0:
            attrs.append(("", mp.CURRENT_QUANTITY, nb2msg(resource_qty)))

        regen_text = self._scalar_time_text(getattr(model, "resource_regen", None))
        if regen_text:
            attrs.append(("", mp.RESOURCE_REGEN, regen_text))

    def add_production_attributes(self, u, attrs):
        """添加生产相关属性（资源入库 / 建筑储量 / 生产物品）"""
        model = u.model
        production_time = getattr(model, "production_time", 0) or 0
        has_production_time = production_time > 0
        production_type = getattr(model, "production_type", None)
        production_item = getattr(model, "production_item", None)
        if isinstance(production_item, (list, tuple)):
            production_item = production_item[0] if production_item else None

        is_gather = bool(getattr(model, "is_gather", 0))
        has_item_production = bool(production_item) and has_production_time
        # production_item 与 production_type 二选一；Building 默认 production_type 须忽略
        has_stockpile_production = (
            bool(production_type)
            and has_production_time
            and not is_gather
            and not production_item
        )
        has_gather_production = (
            not production_item
            and is_gather
            and bool(
                production_type
                or getattr(model, "production_qty", 0)
                or getattr(model, "auto_cultivate", 0)
                or getattr(model, "manual_cultivate", 0)
            )
        )

        if production_type and not production_item and (
            has_stockpile_production or has_gather_production
        ):
            production_type_name = self.main_interface._get_resource_type_name(
                production_type
            )
            attrs.append(("", mp.PRODUCTION_TYPE, [production_type_name]))

        if has_item_production:
            item_title = style.get(production_item, "title")
            if item_title:
                if isinstance(item_title, list):
                    item_name = item_title
                else:
                    item_name = [str(item_title)]
            else:
                item_name = [production_item]
            attrs.append(("", mp.PRODUCTION_ITEM, item_name))

        show_production = (
            has_item_production or has_stockpile_production or has_gather_production
        )
        if show_production:
            if has_production_time:
                modified_production_time = (
                    self.main_interface._calculate_modified_production_time(u)
                )
                time_text = self._scalar_time_text(modified_production_time)
                if time_text:
                    attrs.append(("", mp.PRODUCTION_TIME_NAME, time_text))

            modified_production_qty = (
                self.main_interface._calculate_modified_production_qty(u)
            )
            if modified_production_qty is not None and modified_production_qty > 0:
                attrs.append((
                    "",
                    mp.PRODUCTION_QUANTITY_NAME,
                    nb2msg(modified_production_qty),
                ))

            production_cost = getattr(model, "production_cost", None)
            if production_cost:
                cost_text = self._format_production_cost_text(production_cost)
                if cost_text:
                    attrs.append(("", mp.COST, cost_text))

            if is_gather:
                attrs.append((
                    "",
                    mp.AUTO_CULTIVATE,
                    mp.YES if getattr(model, "auto_cultivate", 0) else mp.NO,
                ))
                attrs.append((
                    "",
                    mp.MANUAL_CULTIVATE,
                    mp.YES if getattr(model, "manual_cultivate", 0) else mp.NO,
                ))
            else:
                attrs.append((
                    "",
                    mp.AUTO_PRODUCTION,
                    mp.YES if getattr(model, "auto_production", 0) else mp.NO,
                ))
                attrs.append((
                    "",
                    mp.MANUAL_PRODUCTION,
                    mp.YES if getattr(model, "manual_production", 0) else mp.NO,
                ))