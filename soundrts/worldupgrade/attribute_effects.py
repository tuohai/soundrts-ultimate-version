"""属性效果处理器模块

包含处理各种属性效果的方法，如：
- 通用属性加成
- 多属性bonus值应用
- 特殊属性处理
"""

import copy
from ..definitions import MAX_NB_OF_RESOURCE_TYPES, Rules
from ..lib.nofloat import PRECISION


class AttributeEffectsMixin:
    """属性效果处理混入类"""

    @classmethod
    def effect_bonus(cls, unit, start_level, *args):
        """通用属性加成处理器
        
        参数：
            unit: 要应用效果的单位
            start_level: 起始等级
            *args: 属性参数，格式为 属性名 值 属性名 值...
        """
        i = 0
        while i < len(args):
            # 获取属性名和值
            stat = args[i]
            
            # 确保i+1在args范围内
            if i + 1 >= len(args):
                i += 1
                continue
                
            value = args[i + 1]
            
            # 处理 can_train 参数，增加或减少建筑物可同时训练的单位数量
            if stat == "can_train":
                # 让处理函数返回已消费到的位置，避免后续的数字被当作属性名处理
                i = cls._handle_can_train_bonus(unit, args, i)
                continue
            
            # 处理storage_bonus（存储奖励）
            if stat == "storage_bonus":
                cls._handle_storage_bonus(unit, value)
                i += 2
                continue
            
            # 处理资源消耗修正
            if stat == "cost":
                cls._handle_cost_bonus(unit, value)
                i += 2
                continue
                
            # 处理人口成本修正
            if stat == "population_cost":
                cls._handle_population_cost_bonus(unit, value)
                i += 2
                continue
                
            # 处理时间成本修正
            if stat == "time_cost":
                cls._handle_time_cost_bonus(unit, value)
                i += 2
                continue
                
            # 处理生产成本修正（与cost类似）
            if stat == "production_cost":
                cls._handle_production_cost_bonus(unit, value)
                i += 2
                continue
                
            # 处理运输相关属性
            if stat.startswith("transport_"):
                # 处理运输相关属性（如transport_volume, transport_capacity等）
                try:
                    current_value = getattr(unit, stat, 0)
                    if isinstance(value, str) and value.endswith('%'):
                        # 百分比增长
                        percent = float(value.rstrip('%')) / 100.0
                        new_value = current_value * (1 + percent)
                        setattr(unit, stat, int(new_value))
                    else:
                        # 直接增量
                        new_value = current_value + int(float(value))
                        setattr(unit, stat, new_value)
                except (ValueError, TypeError) as e:
                    from ..lib.log import warning
                    warning(f"Error in bonus {stat}: {str(e)}")
                i += 2
                continue
                
            # 处理攻击目标类型
            if stat.endswith("_targets"):
                # 处理攻击目标类型（如air_targets, ground_targets等）
                try:
                    if isinstance(value, str):
                        # 字符串格式，可能是空格分隔的多个目标
                        new_targets = value.split()
                        current_targets = getattr(unit, stat, [])
                        if not isinstance(current_targets, list):
                            current_targets = []
                        
                        # 添加新的目标类型（避免重复）
                        for target in new_targets:
                            if target not in current_targets:
                                current_targets.append(target)
                        
                        setattr(unit, stat, current_targets)
                    elif isinstance(value, (list, tuple)):
                        # 列表格式
                        current_targets = getattr(unit, stat, [])
                        if not isinstance(current_targets, list):
                            current_targets = []
                        
                        for target in value:
                            if target not in current_targets:
                                current_targets.append(target)
                        
                        setattr(unit, stat, current_targets)
                except (ValueError, TypeError) as e:
                    from ..lib.log import warning
                    warning(f"Error in bonus {stat}: {str(e)}")
                i += 2
                continue
                
            # 处理gather_time（应用到玩家级别）
            if stat == "gather_time" or stat.startswith("gather_time_"):
                cls._handle_gather_time_bonus(unit, stat, value)
                i += 2
                continue
                
            # 处理gather_qty（应用到玩家级别）
            if stat == "gather_qty" or stat.startswith("gather_qty_"):
                cls._handle_gather_qty_bonus(unit, stat, value)
                i += 2
                continue
                
            # 处理production_time（生产时间，越小越好）
            # 注意：production_time 和 production_qty 由玩家级别的加成在 _update_production_parameters 中统一处理
            # 在 effect_bonus 中不直接修改这些属性，避免重复应用
            if stat == "production_time":
                from ..lib.log import debug
                debug(f"Skipping direct modification of production_time in effect_bonus - will be handled by player-level bonuses")
                i += 2
                continue
                
            # 处理production_qty（生产数量，越大越好）
            # 注意：production_qty 由玩家级别的加成在 _update_production_parameters 中统一处理
            # 在 effect_bonus 中不直接修改这些属性，避免重复应用
            if stat == "production_qty":
                from ..lib.log import debug
                debug(f"Skipping direct modification of production_qty in effect_bonus - will be handled by player-level bonuses")
                i += 2
                continue
                
            # 处理auto_production（自动生产）
            if stat == "auto_production":
                cls._handle_auto_production_bonus(unit, value)
                i += 2
                continue
                
            # 处理auto_cultivate（自动耕种，是auto_production的别名）
            if stat == "auto_cultivate":
                cls._handle_auto_cultivate_bonus(unit, value)
                i += 2
                continue
                
            # 处理manual_production（手动生产）
            if stat == "manual_production":
                cls._handle_manual_production_bonus(unit, value)
                i += 2
                continue
                
            # 处理manual_cultivate（手动耕种，是manual_production的别名）
            if stat == "manual_cultivate":
                cls._handle_manual_cultivate_bonus(unit, value)
                i += 2
                continue
                
            # 处理resource_rewards（单位击杀奖励资源，越大越好）
            if stat == "resource_rewards":
                cls._handle_resource_rewards_bonus(unit, value)
                i += 2
                continue

            # 狩猎尸体食物储量加成（应用到玩家级别）
            if stat == "food_deposit_qty":
                if hasattr(unit, "player") and unit.player:
                    player = unit.player
                    player.food_deposit_qty_bonus = int(
                        getattr(player, "food_deposit_qty_bonus", 0) or 0
                    ) + int(float(value))
                i += 2
                continue
                
            # 处理resource_volume_max（资源容量上限，越大越好）
            if stat == "resource_volume_max":
                cls._handle_resource_volume_max_bonus(unit, value)
                i += 2
                continue
                
            # 处理普通数值属性
            cls._handle_general_attribute_bonus(unit, stat, value)
            i += 2

    @classmethod
    def _baseline_can_train_dict(cls, unit):
        """Rules/effective train batch sizes for a building (or empty for non-trainers)."""
        from ..world_build_rules import _base_can_train, _normalize_train_list, _rules_can_train_dict, _unit_type

        raw = getattr(unit, "can_train", None)
        if isinstance(raw, dict):
            return copy.deepcopy(raw)
        if raw:
            return {name: 1 for name in _normalize_train_list(raw)}
        host_cls = _unit_type(unit)
        if host_cls is None:
            return {}
        names = _normalize_train_list(_base_can_train(unit))
        counts = _rules_can_train_dict(host_cls)
        return {name: max(1, int(counts.get(name, 1))) for name in names}

    @classmethod
    def _handle_can_train_bonus(cls, unit, args, i):
        """处理can_train属性加成，并返回新的参数索引

        语法支持（位于 effect bonus 之后）：
        - can_train <unit> <count> [<unit> <count> ...]
        - can_train <unit> ... <count>    # 最后一个数字应用于前面所有单位
        - can_train <count>               # 对所有已可训练单位统一增量

        返回值：新的索引位置，指向下一个属性键（跳过本次已消费的参数）。
        """
        player = unit.player
        baseline = cls._baseline_can_train_dict(unit)
        if player:
            if not hasattr(player, "_unit_can_train"):
                player._unit_can_train = {}
            unit_id = id(unit)
            if unit_id not in player._unit_can_train:
                player._unit_can_train[unit_id] = copy.deepcopy(baseline)
            can_train_dict = player._unit_can_train[unit_id]
        else:
            can_train_dict = copy.deepcopy(baseline)
        
        try:
            # 起始位置：i 指向 'can_train'
            pos = i + 1
            # 没有更多参数则直接返回下一个位置
            if pos >= len(args):
                return pos

            # 构建可识别的属性名集合，用于判定下一个属性的起始
            recognized_attrs = set()
            try:
                recognized_attrs.update(getattr(Rules, 'precision_properties', set()))
                recognized_attrs.update(getattr(Rules, 'int_properties', set()))
                recognized_attrs.update(getattr(Rules, 'string_properties', set()))
                recognized_attrs.update(getattr(Rules, 'int_list_properties', set()))
                recognized_attrs.update(getattr(Rules, 'precision_list_properties', set()))
                recognized_attrs.update(getattr(Rules, 'string_list_properties', set()))
            except Exception:
                # 若无法获取，保持为空，仅依靠数字模式解析
                recognized_attrs = set()

            def is_attr_token(tok: str) -> bool:
                if not isinstance(tok, str):
                    return False
                if tok in recognized_attrs:
                    return True
                if tok.startswith('gather_time_') or tok.startswith('gather_qty_'):
                    return True
                if tok.startswith('transport_'):
                    return True
                if tok.endswith('_targets'):
                    return True
                # 特殊键
                if tok in {"can_train", "storage_bonus", "cost", "population_cost", "time_cost", "production_cost",
                           "resource_rewards", "resource_volume_max", "auto_production", "auto_cultivate",
                           "manual_production", "manual_cultivate", "production_time", "production_qty"}:
                    return True
                return False

            # 形式1：can_train <count>
            if str(args[pos]).isdigit():
                count_increment = int(args[pos])
                for unit_type in list(can_train_dict.keys()):
                    current_count = can_train_dict[unit_type]
                    can_train_dict[unit_type] = max(1, current_count + count_increment)
                pos += 1
            else:
                # 形式2/3：解析 <unit> <count> 对，或 <unit>... <count>
                while pos < len(args):
                    tok = args[pos]
                    # 如果命中下一个属性名，则停止
                    if is_attr_token(tok):
                        break

                    # 如果后面紧跟数字，则解析成 pair
                    if pos + 1 < len(args) and str(args[pos + 1]).isdigit():
                        unit_type = str(tok)
                        count_val = int(args[pos + 1])
                        can_train_dict[unit_type] = max(1, count_val)
                        pos += 2
                        continue

                    # 否则，尝试查找后续的统一数量：收集连续的单位直到遇到数字或下一个属性
                    units_batch = []
                    while pos < len(args):
                        look = args[pos]
                        if str(look).isdigit() or is_attr_token(look):
                            break
                        units_batch.append(str(look))
                        pos += 1

                    # 如果接下来是数字，则该数字应用到前面收集的单位
                    if pos < len(args) and str(args[pos]).isdigit():
                        batch_count = int(args[pos])
                        for unit_type in units_batch:
                            can_train_dict[unit_type] = max(1, batch_count)
                        pos += 1
                    else:
                        # 没有数量可用，默认数量设为1，并结束
                        for unit_type in units_batch:
                            can_train_dict[unit_type] = max(1, 1)
                        # 不回退 pos；此时 pos 指向下一个属性或末尾
                        break

            # Persist on player; Building.can_train is a read-only @property.
            if player:
                type_name = getattr(unit, "type_name", None)
                if type_name:
                    by_type = player.__dict__.setdefault(
                        "_can_train_overrides_by_type", {}
                    )
                    by_type[type_name] = copy.deepcopy(can_train_dict)

            return pos
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus can_train: {str(e)}")
            # 出错时，至少跳过 'can_train' 与其后一个参数，避免死循环
            return min(len(args), i + 2)

    @classmethod
    def _handle_storage_bonus(cls, unit, value):
        """处理storage_bonus属性"""
        if not hasattr(unit, 'storage_bonus') or not unit.storage_bonus:
            # 如果没有则初始化
            unit.storage_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        
        try:
            # 解析参数值
            bonus_values = []
            if ' ' in str(value):
                # 多个值用空格分隔
                for val in str(value).split():
                    bonus_values.append(int(float(val)))
            else:
                # 单个值
                bonus_values = [int(float(value))]
            
            # 确保长度不超过资源类型数量
            while len(bonus_values) < MAX_NB_OF_RESOURCE_TYPES:
                bonus_values.append(0)
            
            # 更新storage_bonus
            for j, bonus_value in enumerate(bonus_values):
                if j < len(unit.storage_bonus):
                    unit.storage_bonus[j] += bonus_value
            
            # 如果单位是玩家单位，更新玩家的存储奖励
            if hasattr(unit, 'player') and unit.player:
                unit.player._update_storage_bonus()
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus storage_bonus: {str(e)}")

    @classmethod
    def _handle_cost_bonus(cls, unit, value):
        """处理cost属性加成"""
        try:
            # 解析参数值
            cost_values = []
            is_percent = False
            
            # 检查是否是百分比表示
            if str(value).endswith('%'):
                is_percent = True
                val_str = str(value).rstrip('%')
                if ' ' in val_str:
                    # 多个百分比值用空格分隔
                    for val in val_str.split():
                        cost_values.append(float(val) / 100.0)
                else:
                    # 单个百分比值
                    cost_values = [float(val_str) / 100.0]
            else:
                if ' ' in str(value):
                    # 多个值用空格分隔
                    for val in str(value).split():
                        # 乘以PRECISION，确保精度统一
                        cost_values.append(int(float(val) * PRECISION))
                else:
                    # 单个值，乘以PRECISION
                    cost_values = [int(float(value) * PRECISION)]
            
            # 确保长度不超过资源类型数量
            while len(cost_values) < MAX_NB_OF_RESOURCE_TYPES:
                cost_values.append(0)
            
            # 如果单位有cost_bonus属性，添加到现有的加成
            if not hasattr(unit, 'cost_bonus'):
                unit.cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            if not hasattr(unit, 'cost_percent_bonus'):
                unit.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
            
            # 更新cost_bonus或cost_percent_bonus
            for j, cost_value in enumerate(cost_values):
                if j < len(unit.cost_bonus):
                    if is_percent:
                        unit.cost_percent_bonus[j] += cost_value
                    else:
                        unit.cost_bonus[j] += cost_value
                        
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus cost: {str(e)}")

    @classmethod
    def _handle_population_cost_bonus(cls, unit, value):
        """处理population_cost属性加成"""
        try:
            # 检查是否是百分比表示
            is_percent = False
            if str(value).endswith('%'):
                is_percent = True
                val_str = str(value).rstrip('%')
                population_cost_value = float(val_str) / 100.0
            else:
                # 解析参数值，不需要PRECISION转换
                population_cost_value = int(float(value))
            
            # 如果单位有population_cost_bonus属性，添加到现有的加成
            if not hasattr(unit, 'population_cost_bonus'):
                unit.population_cost_bonus = 0
            if not hasattr(unit, 'population_cost_percent_bonus'):
                unit.population_cost_percent_bonus = 0.0
            
            # 更新population_cost_bonus或population_cost_percent_bonus
            if is_percent:
                unit.population_cost_percent_bonus += population_cost_value
            else:
                unit.population_cost_bonus += population_cost_value
                        
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus population_cost: {str(e)}")

    @classmethod
    def _handle_time_cost_bonus(cls, unit, value):
        """处理time_cost属性加成"""
        try:
            # 检查是否是百分比表示
            is_percent = False
            if str(value).endswith('%'):
                is_percent = True
                val_str = str(value).rstrip('%')
                time_cost_value = float(val_str) / 100.0
            else:
                # 解析参数值，不需要PRECISION转换
                time_cost_value = int(float(value))
            
            # 如果单位有time_cost_bonus属性，添加到现有的加成
            if not hasattr(unit, 'time_cost_bonus'):
                unit.time_cost_bonus = 0
            if not hasattr(unit, 'time_cost_percent_bonus'):
                unit.time_cost_percent_bonus = 0.0
            
            # 更新time_cost_bonus或time_cost_percent_bonus
            if is_percent:
                unit.time_cost_percent_bonus += time_cost_value
            else:
                unit.time_cost_bonus += time_cost_value
                        
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus time_cost: {str(e)}")

    @classmethod
    def _handle_production_cost_bonus(cls, unit, value):
        """处理production_cost属性加成"""
        try:
            # 解析参数值
            cost_values = []
            is_percent = False
            
            # 检查是否是百分比表示
            if str(value).endswith('%'):
                is_percent = True
                val_str = str(value).rstrip('%')
                if ' ' in val_str:
                    # 多个百分比值用空格分隔
                    for val in val_str.split():
                        cost_values.append(float(val) / 100.0)
                else:
                    # 单个百分比值
                    cost_values = [float(val_str) / 100.0]
            else:
                if ' ' in str(value):
                    # 多个值用空格分隔
                    for val in str(value).split():
                        # 乘以PRECISION，确保精度统一
                        cost_values.append(int(float(val) * PRECISION))
                else:
                    # 单个值，乘以PRECISION
                    cost_values = [int(float(value) * PRECISION)]
            
            # 确保长度不超过资源类型数量
            while len(cost_values) < MAX_NB_OF_RESOURCE_TYPES:
                cost_values.append(0)
            
            # 如果单位有production_cost_bonus属性，添加到现有的加成
            if not hasattr(unit, 'production_cost_bonus'):
                unit.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
            if not hasattr(unit, 'production_cost_percent_bonus'):
                unit.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
            
            # 更新production_cost_bonus或production_cost_percent_bonus
            for j, cost_value in enumerate(cost_values):
                if j < len(unit.production_cost_bonus):
                    if is_percent:
                        unit.production_cost_percent_bonus[j] += cost_value
                    else:
                        unit.production_cost_bonus[j] += cost_value
                        
        except (ValueError, IndexError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus production_cost: {str(e)}")

    @classmethod
    def _handle_gather_time_bonus(cls, unit, stat, value):
        """处理gather_time属性加成（应用到玩家级别）"""
        from ..lib.log import debug
        debug(f"Processing {stat} with value: {value}")
        if hasattr(unit, "player") and unit.player:
            player = unit.player
            # 初始化玩家的 gather_time_bonus（如果还没有）
            if not hasattr(player, 'gather_time_bonus'):
                player.gather_time_bonus = {}
            
            # 检查是否是特定资源的属性（如 gather_time_wood）
            if stat.startswith("gather_time_") and stat != "gather_time":
                resource_identifier = stat.replace("gather_time_", "")
                
                # 检查是否是百分比格式
                if str(value).endswith('%'):
                    # 百分比格式，直接存储为字符串
                    value_to_store = str(value)
                else:
                    # 普通数值格式
                    value_to_store = int(float(value))
                
                player.gather_time_bonus[resource_identifier] = value_to_store
                
                from ..lib.log import debug
                debug(f"Applied gather_time bonus {value_to_store} to {resource_identifier} for player {player.number}")
            else:
                # 处理通用的 gather_time 属性
                # 解析参数：可能是 "value" 或 "resource_type value" 或 "resource_type1 value1 resource_type2 value2"
                args_str = str(value)
                args_parts = args_str.split()
                
                if len(args_parts) == 1:
                    # 格式: effect bonus gather_time value
                    # 适用于只能采集一种资源的工人或对所有资源类型应用相同值
                    try:
                        # 检查是否是百分比格式
                        if str(args_parts[0]).endswith('%'):
                            # 百分比格式，直接存储为字符串
                            value_to_store = str(args_parts[0])
                        else:
                            # 普通数值格式
                            value_to_store = int(float(args_parts[0]))
                        
                        gather_perms = (
                            (getattr(unit, "can_gather_deposit", None) or [])
                            + (getattr(unit, "can_gather_building", None) or [])
                        )
                        if len(gather_perms) == 1:
                            gather_identifier = gather_perms[0]
                            player.gather_time_bonus[gather_identifier] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_time bonus {value_to_store} to {gather_identifier} for player {player.number}")
                        else:
                            # 对所有可采集类型设置相同的时间增量
                            player.gather_time_bonus["all"] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_time bonus {value_to_store} to all for player {player.number}")
                    except (ValueError, IndexError):
                        pass
                else:
                    # 格式: effect bonus gather_time "resource_type value [resource_type2 value2 ...]"
                    # 或: effect bonus gather_time "all value"
                    j = 0
                    while j < len(args_parts) - 1:
                        resource_identifier = args_parts[j]
                        resource_value = args_parts[j + 1]
                        
                        try:
                            # 检查是否是百分比格式
                            if str(resource_value).endswith('%'):
                                # 百分比格式，直接存储为字符串
                                value_to_store = str(resource_value)
                            else:
                                # 普通数值格式
                                value_to_store = int(float(resource_value))
                            
                            # 直接使用resource_identifier应用到玩家级别
                            player.gather_time_bonus[resource_identifier] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_time bonus {value_to_store} to {resource_identifier} for player {player.number}")
                            
                        except (ValueError, AttributeError):
                            pass
                            
                        j += 2

    @classmethod
    def _handle_gather_qty_bonus(cls, unit, stat, value):
        """处理gather_qty属性加成（应用到玩家级别）"""
        from ..lib.log import debug
        debug(f"Processing {stat} with value: {value}")
        if hasattr(unit, "player") and unit.player:
            player = unit.player
            # 初始化玩家的 gather_qty_bonus（如果还没有）
            if not hasattr(player, 'gather_qty_bonus'):
                player.gather_qty_bonus = {}
            
            # 检查是否是特定资源的属性（如 gather_qty_wood）
            if stat.startswith("gather_qty_") and stat != "gather_qty":
                resource_identifier = stat.replace("gather_qty_", "")
                
                # 检查是否是百分比格式
                if str(value).endswith('%'):
                    # 百分比格式，直接存储为字符串
                    value_to_store = str(value)
                else:
                    # 普通数值格式
                    value_to_store = int(float(value))
                
                player.gather_qty_bonus[resource_identifier] = value_to_store
                
                from ..lib.log import debug
                debug(f"Applied gather_qty bonus {value_to_store} to {resource_identifier} for player {player.number}")
            else:
                # 处理通用的 gather_qty 属性
                # 解析参数：可能是 "value" 或 "resource_type value" 或 "resource_type1 value1 resource_type2 value2"
                args_str = str(value)
                args_parts = args_str.split()
                
                if len(args_parts) == 1:
                    # 格式: effect bonus gather_qty value
                    # 适用于只能采集一种资源的工人或对所有资源类型应用相同值
                    try:
                        # 检查是否是百分比格式
                        if str(args_parts[0]).endswith('%'):
                            # 百分比格式，直接存储为字符串
                            value_to_store = str(args_parts[0])
                        else:
                            # 普通数值格式
                            value_to_store = int(float(args_parts[0]))
                        
                        gather_perms = (
                            (getattr(unit, "can_gather_deposit", None) or [])
                            + (getattr(unit, "can_gather_building", None) or [])
                        )
                        if len(gather_perms) == 1:
                            gather_identifier = gather_perms[0]
                            player.gather_qty_bonus[gather_identifier] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_qty bonus {value_to_store} to {gather_identifier} for player {player.number}")
                        else:
                            # 对所有可采集类型设置相同的数量增量
                            player.gather_qty_bonus["all"] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_qty bonus {value_to_store} to all for player {player.number}")
                    except (ValueError, IndexError):
                        pass
                else:
                    # 格式: effect bonus gather_qty "resource_type value [resource_type2 value2 ...]"
                    # 或: effect bonus gather_qty "all value"
                    j = 0
                    while j < len(args_parts) - 1:
                        resource_identifier = args_parts[j]
                        resource_value = args_parts[j + 1]
                        
                        try:
                            # 检查是否是百分比格式
                            if str(resource_value).endswith('%'):
                                # 百分比格式，直接存储为字符串
                                value_to_store = str(resource_value)
                            else:
                                # 普通数值格式
                                value_to_store = int(float(resource_value))
                            
                            # 直接使用resource_identifier应用到玩家级别
                            player.gather_qty_bonus[resource_identifier] = value_to_store
                            
                            from ..lib.log import debug
                            debug(f"Applied gather_qty bonus {value_to_store} to {resource_identifier} for player {player.number}")
                            
                        except (ValueError, AttributeError):
                            pass
                            
                        j += 2

    @classmethod
    def _handle_auto_production_bonus(cls, unit, value):
        """处理auto_production属性加成"""
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 设置auto_production属性
            unit.auto_production = enabled
            
            # 记录级别信息
            if not hasattr(unit, 'auto_production_level'):
                unit.auto_production_level = 1
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus auto_production: {str(e)}")

    @classmethod
    def _handle_auto_cultivate_bonus(cls, unit, value):
        """处理auto_cultivate属性加成"""
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 同时设置auto_cultivate和auto_production属性
            unit.auto_cultivate = enabled
            unit.auto_production = enabled  # 同时设置auto_production以保持兼容性
            
            # 记录升级信息
            if not hasattr(unit, 'auto_cultivate_level'):
                unit.auto_cultivate_level = 1
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_auto_cultivate: {str(e)}")

    @classmethod
    def _handle_manual_production_bonus(cls, unit, value):
        """处理manual_production属性加成"""
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 设置manual_production属性
            unit.manual_production = enabled
            
            # 记录级别信息
            if not hasattr(unit, 'manual_production_level'):
                unit.manual_production_level = 1
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in bonus manual_production: {str(e)}")

    @classmethod
    def _handle_manual_cultivate_bonus(cls, unit, value):
        """处理manual_cultivate属性加成"""
        try:
            # 转换value为整数
            enabled = int(float(value)) > 0
            
            # 同时设置manual_cultivate和manual_production属性
            unit.manual_cultivate = enabled
            unit.manual_production = enabled  # 同时设置manual_production以保持兼容性
            
            # 记录升级信息
            if not hasattr(unit, 'manual_cultivate_level'):
                unit.manual_cultivate_level = 1
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error in effect_manual_cultivate: {str(e)}")

    @classmethod
    def _handle_resource_rewards_bonus(cls, unit, value):
        """处理resource_rewards属性加成"""
        if hasattr(unit, "resource_rewards"):
            try:
                # 将参数拆分为资源量
                resource_values = value.split()
                if len(resource_values) > 0:
                    # 获取当前奖励值
                    current_rewards = getattr(unit, "resource_rewards", [0, 0])
                    # 确保current_rewards是列表
                    if not isinstance(current_rewards, list):
                        current_rewards = [current_rewards, 0]
                    # 更新每种资源的奖励
                    for j, resource_value in enumerate(resource_values):
                        if j < len(current_rewards):
                            current_rewards[j] += int(float(resource_value))
                    # 设置回单位
                    unit.resource_rewards = current_rewards
            except (ValueError, AttributeError):
                pass

    @classmethod
    def _handle_resource_volume_max_bonus(cls, unit, value):
        """处理resource_volume_max属性加成"""
        if hasattr(unit, "resource_volume_max"):
            try:
                # 检查是否是百分比表示
                is_percent = False
                if str(value).endswith('%'):
                    is_percent = True
                    val_str = str(value).rstrip('%')
                    percent_value = float(val_str) / 100.0
                    
                    # 根据resource_volume_max的类型处理
                    if isinstance(unit.resource_volume_max, list):
                        # 多种资源类型的情况
                        for j in range(len(unit.resource_volume_max)):
                            # 按百分比增加容量
                            bonus_value = int(unit.resource_volume_max[j] * percent_value)
                            unit.resource_volume_max[j] += bonus_value
                    else:
                        # 单一资源类型
                        bonus_value = int(unit.resource_volume_max * percent_value)
                        unit.resource_volume_max += bonus_value
                else:
                    # 非百分比值
                    # 将参数值拆分（如果有多个值）
                    if ' ' in str(value):
                        values = [int(float(v)) for v in str(value).split()]
                        # 如果是list类型的resource_volume_max
                        if isinstance(unit.resource_volume_max, list):
                            for j, val in enumerate(values):
                                if j < len(unit.resource_volume_max):
                                    unit.resource_volume_max[j] += val
                        else:
                            # 单一值，使用第一个
                            unit.resource_volume_max += values[0]
                    else:
                        # 单一值
                        bonus_value = int(float(value))
                        if isinstance(unit.resource_volume_max, list):
                            # 对所有资源类型应用相同的增量
                            for j in range(len(unit.resource_volume_max)):
                                unit.resource_volume_max[j] += bonus_value
                        else:
                            # 单一资源类型
                            unit.resource_volume_max += bonus_value
                
                # 如果单位有qty_max属性，更新它以保持一致
                if hasattr(unit, 'qty_max'):
                    if isinstance(unit.resource_volume_max, list) and isinstance(unit.qty_max, list):
                        for j in range(min(len(unit.qty_max), len(unit.resource_volume_max))):
                            unit.qty_max[j] = unit.resource_volume_max[j]
                    elif isinstance(unit.resource_volume_max, list):
                        unit.qty_max = unit.resource_volume_max[0]
                    else:
                        unit.qty_max = unit.resource_volume_max
                        
                    # 通知资源量更新
                    if hasattr(unit, 'notify'):
                        unit.notify(f"qty_max_update,{unit.qty_max}")
            except (ValueError, IndexError) as e:
                from ..lib.log import warning
                warning(f"Error in bonus resource_volume_max: {str(e)}")

    @classmethod
    def _handle_general_attribute_bonus(cls, unit, stat, value):
        """处理普通数值属性加成"""
        from ..lib.log import debug
        debug(f"Processing general attribute '{stat}' with value: {value}")
        
        # 检查是否是采集相关属性，如果是则不在这里处理
        if stat in ('gather_time', 'gather_qty') or stat.startswith('gather_time_') or stat.startswith('gather_qty_'):
            from ..lib.log import warning
            warning(f"Gather-related attribute '{stat}' should be handled specially, skipping general processing")
            return
        
        current = getattr(unit, stat, 0)
        try:
            # 检查是否是百分比格式，如果是则跳过数值转换
            if isinstance(value, str) and value.endswith('%'):
                # 百分比格式，直接设置
                setattr(unit, stat, value)
            elif stat in cls.integer_stats:  # 必须使用整数的属性
                setattr(unit, stat, current + int(float(value)))
            else:
                value_float = float(value)
                setattr(unit, stat, current + value_float)
        except ValueError:
            try:
                # 如果转换失败，检查是否是百分比格式
                if isinstance(value, str) and value.endswith('%'):
                    # 百分比格式，直接设置
                    setattr(unit, stat, value)
                else:
                    # 尝试使用int
                    setattr(unit, stat, current + int(value))
            except ValueError:
                # 如果仍然失败，记录警告并跳过
                from ..lib.log import warning
                warning(f"Cannot convert value '{value}' for attribute '{stat}' - skipping")

    @classmethod
    def effect_apply_bonus(cls, unit, start_level, *stats):
        """应用多个属性的bonus值
        格式: effect apply_bonus stat1 stat2 stat3 ...
        支持多级升级的bonus值，例如：
        sight_range_bonus 1 1 1  # 三级升级各加1
        rdg_bonus 1 2 6         # 三级升级分别加1,2,6
        """
        # 记录已经处理过的属性
        processed_stats = set()
        
        for stat in stats:
            # 处理目标类型
            if stat.endswith("_targets"):
                targets_bonus = f"{stat}_bonus"
                if hasattr(unit, targets_bonus):
                    targets = getattr(unit, targets_bonus)
                    if isinstance(targets, (list, tuple)):
                        current_targets = getattr(unit, stat, [])
                        for target in targets:
                            if target not in current_targets:
                                current_targets.append(target)
                        setattr(unit, stat, current_targets)
                processed_stats.add(stat)
                continue
                
            # 处理继承关系和资源消耗
            if stat in ("is_a", "cost", "time_cost", "food_cost"):
                bonus_stat = f"{stat}_bonus"
                if hasattr(unit, bonus_stat):
                    bonus_value = getattr(unit, bonus_stat)
                    if stat in ("cost", "time_cost", "food_cost"):
                        # 将成本加成应用到玩家而不是单位
                        cls._apply_cost_bonus_to_player(unit, stat, bonus_value)
                processed_stats.add(stat)
                continue
            
            # 统一处理所有数值属性，包括伤害属性(mdg, rdg)和其他属性
            if stat not in processed_stats:
                cls._apply_attribute_bonus(unit, stat, start_level)
                # 记录已处理的属性
                processed_stats.add(stat)

    @classmethod
    def _apply_cost_bonus_to_player(cls, unit, stat, bonus_value):
        """将成本加成应用到玩家"""
        try:
            if hasattr(unit, 'player') and unit.player:
                player = unit.player
                
                # 根据不同类型的成本初始化不同的属性
                if stat == "cost":
                    # 初始化玩家的成本加成列表（如果还没有）
                    if not hasattr(player, 'cost_bonus'):
                        player.cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
                    bonus_attr = 'cost_bonus'
                    percent_attr = 'cost_percent_bonus'
                elif stat == "time_cost":
                    # 初始化玩家的时间成本加成（如果还没有）
                    if not hasattr(player, 'time_cost_bonus'):
                        player.time_cost_bonus = 0
                    if not hasattr(player, 'time_cost_percent_bonus'):
                        player.time_cost_percent_bonus = 0.0
                    bonus_attr = 'time_cost_bonus'
                    percent_attr = 'time_cost_percent_bonus'
                elif stat == "food_cost":
                    # 初始化玩家的食物成本加成（如果还没有）
                    if not hasattr(player, 'food_cost_bonus'):
                        player.food_cost_bonus = 0
                    if not hasattr(player, 'food_cost_percent_bonus'):
                        player.food_cost_percent_bonus = 0.0
                    bonus_attr = 'food_cost_bonus'
                    percent_attr = 'food_cost_percent_bonus'
                
                # 初始化已应用的成本加成追踪（防止重复应用）
                if not hasattr(player, '_applied_cost_bonuses'):
                    player._applied_cost_bonuses = set()
                
                # 创建一个唯一的标识符，用于跟踪这个特定的加成
                unit_type = getattr(unit, 'type_name', str(type(unit).__name__))
                bonus_id = f"{unit_type}_{stat}_{str(bonus_value)}"
                
                # 检查是否已经应用过这个加成
                if bonus_id not in player._applied_cost_bonuses:
                    # 应用成本加成到玩家
                    if isinstance(bonus_value, (list, tuple)):
                        # 处理列表形式的加成值
                        if stat == "cost":
                            for i, bonus in enumerate(bonus_value):
                                if i < len(player.cost_bonus):
                                    # 处理百分比格式和普通数值
                                    if isinstance(bonus, str) and bonus.endswith('%'):
                                        # 百分比格式，需要特殊处理
                                        # 初始化百分比加成（如果还没有）
                                        if not hasattr(player, 'cost_percent_bonus'):
                                            player.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
                                        
                                        bonus_str = bonus.rstrip('%')
                                        bonus_val = float(bonus_str) / 100.0
                                        if i < len(player.cost_percent_bonus):
                                            player.cost_percent_bonus[i] += bonus_val
                                    else:
                                        # 普通数值格式
                                        bonus_val = int(float(bonus) * PRECISION) if isinstance(bonus, str) else int(bonus * PRECISION)
                                        player.cost_bonus[i] += bonus_val
                        else:
                            # time_cost和food_cost不支持列表形式，只取第一个值
                            bonus = bonus_value[0]
                            if isinstance(bonus, str) and bonus.endswith('%'):
                                # 百分比格式
                                bonus_str = bonus.rstrip('%')
                                bonus_val = float(bonus_str) / 100.0
                                current_val = getattr(player, percent_attr, 0.0)
                                setattr(player, percent_attr, current_val + bonus_val)
                            else:
                                # 普通数值格式
                                bonus_val = int(float(bonus)) if isinstance(bonus, str) else int(bonus)
                                current_val = getattr(player, bonus_attr, 0)
                                setattr(player, bonus_attr, current_val + bonus_val)
                    else:
                        # 单个数值的情况
                        if isinstance(bonus_value, str) and bonus_value.endswith('%'):
                            # 百分比格式
                            if stat == "cost":
                                if not hasattr(player, 'cost_percent_bonus'):
                                    player.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
                                
                                bonus_str = bonus_value.rstrip('%')
                                bonus_val = float(bonus_str) / 100.0
                                if len(player.cost_percent_bonus) > 0:
                                    player.cost_percent_bonus[0] += bonus_val
                            else:
                                # time_cost或food_cost的百分比格式
                                bonus_str = bonus_value.rstrip('%')
                                bonus_val = float(bonus_str) / 100.0
                                current_val = getattr(player, percent_attr, 0.0)
                                setattr(player, percent_attr, current_val + bonus_val)
                        else:
                            # 普通数值格式
                            if stat == "cost":
                                bonus_val = int(float(bonus_value) * PRECISION) if isinstance(bonus_value, str) else int(bonus_value * PRECISION)
                                if len(player.cost_bonus) > 0:
                                    player.cost_bonus[0] += bonus_val
                            else:
                                # time_cost或food_cost的普通数值格式
                                bonus_val = int(float(bonus_value)) if isinstance(bonus_value, str) else int(bonus_value)
                                current_val = getattr(player, bonus_attr, 0)
                                setattr(player, bonus_attr, current_val + bonus_val)
                    
                    # 记录已应用的加成
                    player._applied_cost_bonuses.add(bonus_id)
                    
                    from ..lib.log import debug
                    debug(f"Applied {stat} bonus {bonus_value} to player {player.number}")
                else:
                    from ..lib.log import debug
                    debug(f"{stat} bonus {bonus_id} already applied to player {player.number}, skipping")
            else:
                from ..lib.log import warning
                warning(f"Cannot apply {stat} bonus to {unit}: no player reference")
        except (ValueError, TypeError) as e:
            from ..lib.log import warning
            warning(f"Error processing {stat} bonus for {unit}: {str(e)}")

    @classmethod
    def _apply_attribute_bonus(cls, unit, stat, start_level):
        """应用属性bonus"""
        bonus_stat = f"{stat}_bonus"
        level_stat = f"{stat}_level"
        
        if hasattr(unit, bonus_stat):
            bonus_values = getattr(unit, bonus_stat)
            base_value = getattr(unit, stat, 0)
            
            # 获取或初始化当前级别属性
            if not hasattr(unit, level_stat):
                setattr(unit, level_stat, 0)
            current_level = getattr(unit, level_stat)
            
            # 确保我们只应用当前级别的效果，避免重复应用
            if current_level <= start_level:
                # 如果是多级升级的bonus（列表类型）
                if isinstance(bonus_values, (list, tuple)):
                    # 确保start_level在有效范围内
                    if 0 <= start_level < len(bonus_values):
                        bonus_value = bonus_values[start_level]
                        try:
                            # 处理类型转换
                            base_val = int(float(base_value)) if isinstance(base_value, str) else base_value
                            bonus_val = int(float(bonus_value)) if isinstance(bonus_value, str) else bonus_value
                            new_value = base_val + bonus_val
                            setattr(unit, stat, new_value)
                            # 更新等级属性
                            setattr(unit, level_stat, start_level + 1)
                        except (ValueError, TypeError) as e:
                            from ..lib.log import warning
                            warning(f"Error processing multi-level bonus for {unit}.{stat}: {str(e)}")
                else:
                    # 单级bonus，确保只应用一次
                    if current_level == 0 and start_level == 0:
                        try:
                            # 处理类型转换
                            base_val = int(float(base_value)) if isinstance(base_value, str) else base_value
                            bonus_val = int(float(bonus_values)) if isinstance(bonus_values, str) else bonus_values
                            new_value = base_val + bonus_val
                            setattr(unit, stat, new_value)
                            # 更新等级属性
                            setattr(unit, level_stat, 1)
                        except (ValueError, TypeError) as e:
                            from ..lib.log import warning
                            warning(f"Error processing single-level bonus for {unit}.{stat}: {str(e)}")

    @classmethod
    def _resolve_gather_resource_type(cls, unit, identifier):
        """解析采集资源类型标识符
        
        Args:
            unit: 工人单位对象
            identifier: 可能是resource_type或deposit名称
            
        Returns:
            str: 实际的resource_type，如果无法解析则返回原值
        """
        if not identifier:
            return identifier
            
        # 如果已经是resource开头，直接返回
        if identifier.startswith("resource"):
            return identifier
            
        # 尝试从deposit映射中获取resource_type
        try:
            from ..worldunit import Worker
            deposit_mapping = Worker._get_deposit_resource_type_mapping()
            if identifier in deposit_mapping:
                return deposit_mapping[identifier]
        except Exception:
            pass
            
        # 如果无法解析，返回原值
        return identifier