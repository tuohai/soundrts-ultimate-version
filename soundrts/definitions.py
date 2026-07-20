import copy

import re
from typing import Set

from .lib.defs import preprocess
from .lib.log import info, warning, debug
from .lib.nofloat import PRECISION, to_int
from .level_up_stats import LEVEL_UP_STAT_ATTRS

VIRTUAL_TIME_INTERVAL = 300  # milliseconds
MAX_NB_OF_RESOURCE_TYPES = 10


def _get_base_classes():
    from .worldskill import Skill
    from .worldresource import Deposit
    from .worldresource import BuildingLand
    from .worldunit import Unit
    from .worldweapon import Weapon
    from .worldarmor import Armor
    from .worldunit import Soldier
    from .worldunit import Building
    from .worldunit import Effect
    from .worldupgrade import Upgrade
    from .worldphase import Phase
    from .worldbuff import Buff
    from .worldunit import Worker
    from .worlditem import Item
    from .worldterrain import TerrainRules

    return {
        "worker": Worker,
        "soldier": Soldier,
        "building": Building,
        "effect": Effect,
        "deposit": Deposit,
        "building_land": BuildingLand,
        "resource": Deposit,  # 已废弃：class resource 等同 deposit
        "upgrade": Upgrade,
        "phase": Phase,  # 时代（age）类——作用于玩家所有单位
        "skill": Skill,  # 将 ability 改为 skill
        "buff": Buff,  # 添加buff类
        "weapon": Weapon,
        "armor": Armor,  # 添加护甲类
        "item": Item,  # 添加物品类
        "terrain": TerrainRules,
    }


def _update_old_definitions(d, name):
    if "sight_range" in d and d["sight_range"] == 1 * PRECISION:
        d["sight_range"] = 12 * PRECISION
        d["bonus_height"] = 1
        info(
            "in %s: replacing sight_range 1 with sight_range 12 and bonus_height 1",
            name,
        )
    if "special_range" in d:
        del d["special_range"]
        d["range"] = 12 * PRECISION
        d["minimal_range"] = 4 * PRECISION
        d["is_ballistic"] = 1
        info(
            "in %s: replacing special_range 1 with range 12, minimal_range 4 and is_ballistic 1",
            name,
        )
    return d


def parse_can_train_words(words) -> dict:
    """Parse ``can_train`` tokens (``words[0]`` must be ``can_train``).

    Supported formats:
    1. ``can_train unit count [unit count ...]`` — per-unit batch size
    2. ``can_train unit ... unit count`` — one count for every listed unit
    3. ``can_train unit ...`` — default batch size 1
    """
    # Format 1: alternating unit/count pairs consume the whole line.
    pair_result = {}
    index = 1
    while index < len(words):
        if (
            index + 1 < len(words)
            and not words[index].isdigit()
            and words[index + 1].isdigit()
        ):
            pair_result[words[index]] = int(words[index + 1])
            index += 2
        else:
            pair_result = None
            break
    if pair_result:
        return pair_result

    # Format 2: trailing unified count for all preceding unit names.
    if len(words) > 2 and words[-1].isdigit():
        count = int(words[-1])
        result = {}
        for token in words[1:-1]:
            if not token.isdigit():
                result[token] = count
        return result

    # Format 3: unit names only, default to 1.
    result = {}
    for token in words[1:]:
        if not token.isdigit():
            result[token] = 1
    return result


class _Definitions:
    int_properties: Set[str] = set()
    precision_properties: Set[str] = set()
    int_list_properties: Set[str] = set()
    precision_list_properties: Set[str] = set()
    string_properties: Set[str] = set()

    def __init__(self):
        self._dict = {}
        # 缓存 (obj, attr) -> value，降低频繁查询与递归成本
        self._get_cache = {}

    def read(self, s):
        # 定义内容将发生变化，清空缓存
        if hasattr(self, "_get_cache"):
            self._get_cache.clear()
        s = preprocess(s)
        d = self._dict
        name = "(the name is missing)"
        for line in s.split("\n"):
            try:
                # 处理引号内的字符串，将其视为单个单词
                processed_words = []
                in_quotes = False
                current_quoted_string = ""
                
                # 先处理每一行，识别引号中的内容为单个单词
                i = 0
                words = line.split()
                while i < len(words):
                    word = words[i]
                    
                    # 检查是否包含引号
                    if not in_quotes and (word.startswith('"') or word.startswith("'")):
                        # 引号开始
                        in_quotes = True
                        quote_char = word[0]
                        
                        # 如果单词也以同类引号结尾且长度>1（避免单独一个引号）
                        if len(word) > 1 and word.endswith(quote_char):
                            # 去掉前后引号
                            processed_words.append(word[1:-1])
                            in_quotes = False
                        else:
                            # 引号没有在同一个单词中闭合
                            current_quoted_string = word[1:]  # 移除开始引号
                    elif in_quotes:
                        # 正在引号内
                        if word.endswith(quote_char):
                            # 引号结束
                            current_quoted_string += " " + word[:-1]  # 添加空格和当前单词（移除结束引号）
                            processed_words.append(current_quoted_string)
                            current_quoted_string = ""
                            in_quotes = False
                        else:
                            # 继续引号内的内容
                            current_quoted_string += " " + word
                    else:
                        # 普通单词
                        processed_words.append(word)
                    
                    i += 1
                
                # 如果引号未闭合，发出警告并添加已解析的部分
                if in_quotes:
                    warning(f"未闭合的引号: {line}")
                    if current_quoted_string:
                        processed_words.append(current_quoted_string)
                
                # 使用处理后的单词列表
                words = processed_words
                
                if not words:
                    continue
                if words[0] == "clear":
                    d.clear()
                elif words[0] == "def":
                    name = words[1]
                    if name not in d:
                        d[name] = {}
                # 特殊处理is_a属性，保持括号内的内容完整
                elif words[0] == "is_a":
                    # 重新构建is_a值，以保持原始格式
                    is_a_value = []
                    i = 1
                    while i < len(words):
                        current_word = words[i]
                        # 检查是否有未闭合的括号
                        if '(' in current_word and ')' not in current_word:
                            # 收集括号内容直到找到闭合括号
                            complete_term = current_word
                            j = i + 1
                            while j < len(words) and ')' not in words[j]:
                                complete_term += ' ' + words[j]
                                j += 1
                            if j < len(words):  # 找到了闭合括号
                                complete_term += ' ' + words[j]
                                is_a_value.append(complete_term)
                                i = j + 1
                            else:  # 没有找到闭合括号
                                is_a_value.append(current_word)
                                i += 1
                        else:
                            is_a_value.append(current_word)
                            i += 1
                    
                    if words[0] in d[name]:
                        d[name][words[0]].extend(is_a_value)
                    else:
                        d[name][words[0]] = is_a_value
                # 添加对 damage_seq 的特殊处理
                elif words[0] == "damage_seq":
                    # 解析攻击序列
                    seq_str = " ".join(words[1:])
                    match = re.search(r'(mdg|rdg)\s+(\d+)', seq_str)
                    if match:
                        damage_type = match.group(1)
                        # 检查基础伤害是否已定义
                        if damage_type not in d[name]:
                            warning(f"Base {damage_type} damage not defined for {name}")
                            continue
                            
                        requested_times = int(match.group(2))
                        base_prec = d[name][damage_type]
                        interval_match = re.search(r'\(interval\s+([\d\.]+)\)', seq_str)
                        interval = float(interval_match.group(1)) if interval_match else 0.0
                        damages = None
                        times = requested_times

                        # 解析伤害序列；省略 (damage ...) 时均分基础伤害（诸葛弩式连发）
                        damage_match = re.search(r'\(damage\s+([0-9\s]+)\)', seq_str)
                        if damage_match:
                            raw_damages = [int(x) for x in damage_match.group(1).split()]
                            actual_times = len(raw_damages)

                            if actual_times > requested_times:
                                warning(f"Got {actual_times} damage values but only {requested_times} attacks requested - will truncate damage sequence")
                                raw_damages = raw_damages[:requested_times]
                                actual_times = requested_times
                            elif actual_times < requested_times:
                                warning(f"Requested {requested_times} attacks but got only {actual_times} damage values - will use actual damage sequence length")

                            base_damage = base_prec // PRECISION
                            if sum(raw_damages) == base_damage:
                                damages = [x * PRECISION for x in raw_damages]
                                times = actual_times
                            else:
                                warning(f"Total sequence damage {sum(raw_damages)} does not match base damage {base_damage}")
                        else:
                            per_shot = base_prec // requested_times
                            remainder = base_prec % requested_times
                            damages = [
                                per_shot + (1 if i < remainder else 0)
                                for i in range(requested_times)
                            ]

                        if damages and sum(damages) == base_prec:
                            d[name][words[0]] = seq_str
                            d[name][f"{damage_type}_seq_times"] = times
                            d[name][f"{damage_type}_seq_damages"] = damages
                            d[name][f"{damage_type}_seq_interval"] = interval
                elif words[0] == "square_terrain":
                    from .lib.square_terrain_rules import parse_square_terrain_entries

                    entries = parse_square_terrain_entries(words[1:])
                    existing = d[name].get("square_terrain", [])
                    if not isinstance(existing, list):
                        existing = []
                    d[name]["square_terrain"] = existing + entries
                elif words[0] in self.string_properties:
                    d[name][words[0]] = words[1]
                elif words[0] in self.int_properties:
                    d[name][words[0]] = int(words[1])
                elif (
                    words[0] == "speed"
                    and d[name].get("class") == ["terrain"]
                    and len(words) >= 3
                ):
                    # terrain speed is ground/air pair, not unit movement speed
                    d[name][words[0]] = words[1:]
                elif words[0] in self.precision_properties:
                    if words[0] == "effect_range" and len(words) >= 2:
                        if words[1] == "square":
                            words[1] = "6"
                            info(
                                "effect_range of %s will be 6 (instead of 'square')",
                                name,
                            )
                        elif words[1] == "nearby":
                            words[1] = "12"
                            info(
                                "effect_range of %s will be 12 (instead of 'nearby')",
                                name,
                            )
                        elif words[1] == "anywhere":
                            words[1] = "2147483"  # sys.maxint / 1000 (32 bits)
                    if len(words) >= 2 and words[1] == "inf":
                        words[1] = "2147483"  # sys.maxint / 1000 (32 bits)
                    
                    # 支持百分比格式
                    if len(words) >= 2 and str(words[1]).endswith('%'):
                        # 保留百分比格式，不转换
                        d[name][words[0]] = words[1]
                    else:
                        d[name][words[0]] = to_int(words[1])
                elif words[0] in self.int_list_properties:
                    d[name][words[0]] = [int(x) for x in words[1:]]
                elif words[0] in self.precision_list_properties:
                    d[name][words[0]] = [to_int(x) for x in words[1:]]
                else:
                    # 特殊处理带等号的属性，如 title = value
                    if len(words) > 1 and words[1] == "=":
                        # 如果第二个词是等号，则跳过等号
                        d[name][words[0]] = words[2:]
                    elif (words[0] == "effect" and words[1] == "bonus"):
                        # 处理多个属性-值对
                        processed_words = [words[0], words[1]]  # 保留 "effect bonus"
                        
                        # 从第三个词开始,每两个词为一组(属性和值)
                        for i in range(2, len(words), 2):
                            if i + 1 >= len(words):  # 确保有值
                                break

                            stat = words[i]
                            # can_train accepts variable tokens (unit/count pairs); do not pair-parse.
                            if stat == "can_train":
                                processed_words.append(stat)
                                processed_words.extend(words[i + 1 :])
                                break

                            value = words[i + 1]
                            
                            # 特殊处理time_cost属性，支持百分比
                            if stat == "time_cost" and str(value).endswith('%'):
                                # 保持百分比格式，不转换
                                processed_words.extend([stat, value])
                                continue
                            
                            # 如果是精确属性,转换为整数
                            if stat in self.precision_properties:
                                try:
                                    value = to_int(value)
                                except ValueError:
                                    warning(f"Invalid value for {stat}: {value}")
                                    continue
                                    
                            processed_words.extend([stat, value])
                        
                        # 合并多个effect bonus，而不是覆盖
                        if words[0] in d[name]:
                            # 已经存在effect属性，检查是否为列表
                            if isinstance(d[name][words[0]], list):
                                # 检查第一个元素是否是"bonus"
                                if d[name][words[0]] and d[name][words[0]][0] == "bonus":
                                    # 这是已有的一个effect bonus定义
                                    # 现在我们要添加一个新的effect bonus定义，而不是合并
                                    # 将单个effect bonus列表转换为多个effect列表
                                    d[name][words[0]] = [d[name][words[0]], processed_words[1:]]
                                else:
                                    # 已经是多个effect的列表，简单添加新的effect
                                    d[name][words[0]].append(processed_words[1:])
                            else:
                                # 不是列表，需要转换为包含多个效果的列表
                                d[name][words[0]] = [d[name][words[0]], processed_words[1:]]
                        else:
                            # 第一次添加effect
                            d[name][words[0]] = processed_words[1:]  # 存储处理后的结果
                    elif (words[0] == "phase" and len(words) >= 2
                          and words[1] == "bonus"):
                        # 特殊处理 phase bonus（时代加成），与 effect bonus 对齐：
                        #   phase bonus stat1 val1 stat2 val2 ...
                        # 其中 cost / production_cost 等列表型属性
                        # 可以连续给多个数值（按资源类型）：cost -5 -3 -2
                        # time_cost、population_cost 等为单值，可与 cost 混写在同一行
                        # 内部存储键为 "phase_bonus"（Python 标识符不能含空格）
                        list_attrs = set(self.precision_list_properties)
                        known_attrs = (
                            set(self.precision_properties)
                            | set(self.int_properties)
                            | set(self.string_properties)
                            | set(self.string_list_properties)
                            | set(self.int_list_properties)
                            | list_attrs
                        )

                        def _is_numeric_token(tok):
                            t = str(tok)
                            if t.endswith('%'):
                                t = t[:-1]
                            try:
                                float(t)
                                return True
                            except (ValueError, TypeError):
                                return False

                        parsed = []
                        i = 2  # 跳过 "phase" 和 "bonus"
                        while i < len(words):
                            stat = words[i]
                            i += 1
                            if i >= len(words):
                                break
                            if stat in list_attrs:
                                # 收集连续的数字 token，直到遇到下一个已知属性名或结尾
                                values = []
                                while (
                                    i < len(words)
                                    and _is_numeric_token(words[i])
                                    and words[i] not in known_attrs
                                ):
                                    values.append(words[i])
                                    i += 1
                                if not values:
                                    warning(
                                        "phase bonus %s in %s: no value provided",
                                        stat, name,
                                    )
                                    continue
                                parsed.extend([stat, " ".join(values)])
                            else:
                                value = words[i]
                                i += 1
                                if (
                                    stat in self.precision_properties
                                    and not (isinstance(value, str)
                                             and value.endswith('%'))
                                ):
                                    try:
                                        value = to_int(value)
                                    except (ValueError, TypeError):
                                        warning(
                                            "phase bonus %s in %s: invalid value '%s'",
                                            stat, name, value,
                                        )
                                        continue
                                parsed.extend([stat, value])

                        # 多次声明合并，而不是覆盖
                        if "phase_bonus" in d[name] and isinstance(
                            d[name]["phase_bonus"], list
                        ):
                            d[name]["phase_bonus"].extend(parsed)
                        else:
                            d[name]["phase_bonus"] = parsed
                    elif words[0] == "can_train":
                        d[name][words[0]] = parse_can_train_words(words)
                    elif (
                        getattr(self, "key_value_properties", None)
                        and words[0] in self.key_value_properties
                    ):
                        d[name][words[0]] = self.parse_property(words[0], words[1:])
                    # 特殊处理gather相关属性，支持百分比格式
                    elif (words[0] == "gather_time" or words[0] == "gather_qty" or 
                          words[0].startswith("gather_time_") or words[0].startswith("gather_qty_")):
                        # 处理gather属性的不同格式
                        if len(words) == 2:
                            # 简单格式：gather_time 3 或 gather_time 50%
                            value = words[1]
                            if str(value).endswith('%'):
                                # 保留百分比格式
                                d[name][words[0]] = value
                            else:
                                # 转换为整数
                                try:
                                    d[name][words[0]] = int(value)
                                except ValueError:
                                    warning(f"Invalid value for {words[0]}: {value}")
                                    d[name][words[0]] = 0
                        elif len(words) == 3:
                            # 资源特定格式：gather_time goldmine 3 或 gather_time goldmine 50%
                            resource_type = words[1]
                            value = words[2]
                            combined_key = f"{words[0]}_{resource_type}"
                            if str(value).endswith('%'):
                                # 保留百分比格式
                                d[name][combined_key] = value
                            else:
                                # 转换为整数
                                try:
                                    d[name][combined_key] = int(value)
                                except ValueError:
                                    warning(f"Invalid value for {combined_key}: {value}")
                                    d[name][combined_key] = 0
                        else:
                            # 其他格式，保持原样
                            d[name][words[0]] = words[1:]
                    else:
                        d[name][words[0]] = words[1:]
            except:
                warning("error in line: %s", line)

    def apply_inheritance(self, expanded_is_a=False):
        # 应用继承前后都清理一次缓存，确保一致性
        if hasattr(self, "_get_cache"):
            self._get_cache.clear()
        d = self._dict
        modified = True
        n = 0
        while modified:
            modified = False
            n += 1
            # for every object
            for ko, o in list(d.items()):
                if "is_a" in o:
                    # init "expanded_is_a" (first pass)
                    if expanded_is_a and "expanded_is_a" not in o:
                        o["expanded_is_a"] = o["is_a"][:]
                        modified = True
                    # for every parent
                    for p_info in o["is_a"]:
                        # 解析父类信息，可能包含括号内的属性指定
                        parent_info = self._parse_parent_info(p_info)
                        p = parent_info["parent"]
                        include_attrs = parent_info.get("include", set())
                        exclude_attrs = parent_info.get("exclude", set())
                        is_exclude_mode = parent_info.get("is_exclude_mode", False)

                        if p in d:
                            # 首先确保继承class属性，无论是否使用选择性继承
                            if "class" in d[p] and "class" not in o:
                                o["class"] = d[p]["class"]
                                modified = True
                                
                            # for every attribute
                            for k, v in list(d[p].items()):
                                if expanded_is_a and k == "expanded_is_a":
                                    # add parents from "expanded_is_a" of parent
                                    # (if not yet in the object's "expanded_is_a")
                                    for is_a in v:
                                        if is_a not in o[k]:
                                            o[k] += [is_a]
                                            modified = True
                                # 处理增强继承语法
                                elif k not in o and k != "is_a" and k != "class":  # 排除class，因为已经在上面处理过了
                                    if is_exclude_mode:
                                        # 排除模式: 如果属性不在排除列表中，则继承
                                        if k not in exclude_attrs:
                                            o[k] = v
                                            modified = True
                                    else:
                                        # 包含模式: 如果包含列表为空或属性在包含列表中，则继承
                                        if not include_attrs or k in include_attrs:
                                            o[k] = v
                                            modified = True
                        else:
                            warning("error in %s.is_a: %s doesn't exist", ko, p)
        if hasattr(self, "_get_cache"):
            self._get_cache.clear()

    @staticmethod
    def _classify_bracket_attrs(attrs):
        """将括号内的属性标记分为包含/排除两组。

        支持：
        - ``attr1 attr2`` — 仅继承列出的属性
        - ``apart attr1`` / ``-attr1`` — 排除继承（不继承列出的属性）
        - ``-attr1 -attr2`` — 多个排除项
        """
        if not attrs:
            return set(), set(), False
        if attrs[0] == "apart":
            return set(), set(attrs[1:]), True
        minus_attrs = [a[1:] for a in attrs if a.startswith("-") and len(a) > 1]
        plain_attrs = [a for a in attrs if not a.startswith("-")]
        if minus_attrs and not plain_attrs:
            return set(), set(minus_attrs), True
        if plain_attrs:
            return set(plain_attrs), set(), False
        return set(), set(), False

    def _parse_parent_info(self, parent_str):
        """解析父类信息，支持括号内的属性指定
        
        格式:
        parent_name - 继承所有属性
        parent_name(attr1 attr2) - 仅继承指定属性
        parent_name(apart attr1 attr2) - 继承除了指定属性外的所有属性
        parent_name(-attr1 -attr2) - 排除继承（与 apart 等价）
        """
        result = {"parent": parent_str, "include": set(), "exclude": set(), "is_exclude_mode": False}
        
        # 检查是否有括号
        open_bracket = parent_str.find('(')
        if open_bracket == -1:
            return result
        
        close_bracket = parent_str.rfind(')')
        if close_bracket == -1:
            warning(f"Unclosed parenthesis in is_a definition: {parent_str}")
            # 在找不到闭合括号的情况下，假设括号一直到字符串结尾
            close_bracket = len(parent_str)
            # 返回基本父类名称作为parent字段
            parent_name = parent_str[:open_bracket].strip()
            return {"parent": parent_name, "include": set(), "exclude": set(), "is_exclude_mode": False}
        
        # 解析父类名称和括号内容
        parent_name = parent_str[:open_bracket].strip()
        bracket_content = parent_str[open_bracket+1:close_bracket].strip()
        
        result["parent"] = parent_name
        
        if not bracket_content:
            return result
        
        include_attrs, exclude_attrs, is_exclude_mode = self._classify_bracket_attrs(
            bracket_content.split()
        )
        result["include"] = include_attrs
        result["exclude"] = exclude_attrs
        result["is_exclude_mode"] = is_exclude_mode
        
        return result

    def _val(self, obj, attr):
        d = self._dict
        if obj not in d:
            return
        o = d[obj]
        if attr not in o:
            if "is_a" in o:
                for p in o["is_a"]:
                    if p in d and self._val(p, attr) is not None:
                        return self._val(p, attr)
            return
        return o[attr]

    def get(self, obj, attr, default=None):
        # 先查缓存
        cache_key = (obj, attr)
        if hasattr(self, "_get_cache") and cache_key in self._get_cache:
            v_cached = self._get_cache[cache_key]
            if isinstance(v_cached, list):
                return v_cached[:]
            if v_cached is None and default is not None:
                return default
            return v_cached

        v = self._val(obj, attr)
        if v is None and attr[-8:-1] == "_level_":
            v = self._val(obj, attr[:-8])
        # 写入缓存（注意list需要复制返回以免外部修改影响缓存）
        if hasattr(self, "_get_cache"):
            self._get_cache[cache_key] = v
        if isinstance(v, list):
            return v[:]
        if v is None and default is not None:
            return default
        return v

    def get_dict(self, obj):
        return self._dict[obj]

    def classnames(self):
        return list(self._dict.keys())

    def copy(self, other):
        self.__dict__ = other.__dict__


_precision_properties = {
    "mdg",
    "mdg_per_level",
    "rdg_per_level",
    "mdf_per_level",
    "rdf_per_level",
    "rdg",
    "menace",
    "menace_mult",
    "menace_armor_weight",
    "menace_dodge_weight",
    "menace_range_weight",
    "menace_speed_weight",
    "menace_hp_ref",
    "exp_dgf",
        "exp_hp_cost",
    "mdg_crit",
    "rdg_crit",
    "charge_mdg",
    "charge_rdg",
    "charge_mdg_dist",
    "charge_rdg_dist",
    "charge_mdg_min_dist",
    "charge_rdg_min_dist",
    "op_charge_mdg",
    "op_charge_rdg",
    "op_charge_mdg_dist",
    "op_charge_rdg_dist",
    "mdf",
    "rdf",
    "mdg_cd",
    "rdg_cd",
    "cooldown",
    "ready",
    "charge_mdg_cd",
    "charge_rdg_cd",
    "op_charge_mdg_cd",
    "op_charge_rdg_cd",
    "mdg_ready",
    "rdg_ready",
    "heal_cd",
    "harm_cd",
    "heal_ready",
    "harm_ready",
    "hp_regen_cd",
    "hp_regen_ready",
    "mana_regen_cd", 
    "mana_regen_ready",
    "mdg_range",
    "rdg_range",
    "heal_radius",
    "harm_radius",
    "heal_range",
    "harm_range",
    "mdg_minimal_range",
    "rdg_minimal_range",
    "mdg_status_duration",
    "rdg_status_duration",
    "mdg_cover",
    "rdg_cover",
    "mdg_dodge",
    "rdg_dodge",
    "minimal_damage",
    "mdg_minimal_damage",
    "rdg_minimal_damage",
    "forced_damage",
    "mdg_radius",
    "rdg_radius",
    "charge_mdg_radius",
    "charge_rdg_radius",
    "mdg_splash",
    "rdg_splash",
    "mdg_splash_decay_min",
    "rdg_splash_decay_min",
    "charge_mdg_splash",
    "charge_rdg_splash",
    "charge_mdg_splash_decay_min",
    "charge_rdg_splash_decay_min",
        "mdg_delay",
        "rdg_delay",
    "decay",
    "corpse_decay",
    "qty",
    "hp_start",
    "hp_max",
    "hp_max_per_level",
    "mana_cost",
    "mana_max",
    "mana_start",
    "time_cost",
    "change_time",     # 单位变形所需时间
    "larva_spawn_time",  # 主巢幼虫生成间隔（秒）
    "hp_regen",
    "hp_regen_per_level",
    "mana_regen",
    "speed",
    "effect_range",
    "effect_radius",
    "sight_range",
    "build_field_radius",
    "build_field_radius_m",
    "addon_offset_x",
    "cloaking_range",
    "detection_range",
    "xp_reward_per_xp",
    "revival_time",
    "revival_time_per_level",
}

_precision_properties_extended = _precision_properties.union(
    s + "_bonus" for s in _precision_properties
)

for _level_up_attr in LEVEL_UP_STAT_ATTRS:
    _level_up_per_level = f"{_level_up_attr}_per_level"
    if _level_up_attr in _precision_properties:
        _precision_properties.add(_level_up_per_level)
        _precision_properties_extended.add(_level_up_per_level)

assert "mdf" in _precision_properties_extended
assert "rdf" in _precision_properties_extended
assert "mdf_bonus" in _precision_properties_extended
assert "rdf_bonus" in _precision_properties_extended


def _raw_class_attr(cls, name, default=()):
    """Read rules class attr; skip @property descriptors inherited from Building."""
    for base in getattr(cls, "__mro__", (cls,)):
        if name in base.__dict__:
            val = base.__dict__[name]
            if isinstance(val, property):
                continue
            return val if val else default
    return default


class Rules(_Definitions):

    # 键值对属性集合
    key_value_properties = {
        "load_bonus",          # 每装载一名单位 → 容器属性加成
        "passenger_bonus",     # 进入容器后 → 乘客属性加成
    }

    string_properties = {
        "airground_type",
        "resource_type",  # 将resource_type从int_properties移到string_properties
        "production_type",  # 生产的资源类型
        "production_item",  # 生产的物品类型（落地供拾取）
        "armor",  # 护甲名称
        "ai_mode",  # 单位开局的默认AI模式：offensive/defensive/guard/chase
        "campaign_carryover_id",  # 跨章存档键名（默认 def 名）
        "food_deposit",  # 狩猎动物死亡后生成的食物矿床类型名
        "provides_build_field",  # 提供建造场：psi、creep 等
        "requires_build_field",  # 需要建造场；0 表示豁免
        "build_mode",  # 工人施工模式：assisted / place_and_leave / sacrifice
        "ground_form",  # 飞行建筑落地后的地面形态（如 flying_barracks → barracks）
        "requires_deposit",  # 必须建在指定矿床类型上（如气矿 geyser）
        "summon_requires_build_field",  # 召唤技能：目标格需有指定建造场（如 creep）
        "bridge_terrain",  # 建成后将该格变为指定桥梁地形（如 big_bridge）
    }

    # vs属性集合
    vs_properties = {
        "mdg",
        "rdg",
        "mdf",
        "rdf",
        "mdg_range",
        "rdg_range",
        "mdg_cd",
        "rdg_cd",
        "mdg_cover",
        "rdg_cover",
        "mdg_dodge",
        "rdg_dodge",
    }

    def parse_unit_definition(self, type_name, attrs):
        """解析单位定义，支持灵活的继承机制
        支持以下格式:
        1. is_a footman(mdg rdf) - 继承指定的属性
        2. is_a footman(apart hp_max) / is_a footman(-hp_max) - 排除继承
        3. is_a footman knight archer - 同时继承多个单位的所有属性
        4. is_a footman(mdg rdf) knight(hp_max) archer(-rdg_range) - 混合继承
        """
        definition = {}
        
        # 处理所有非is_a属性
        for key, value in attrs:
            if key != "is_a":
                definition[key] = self.parse_property(key, value)
                
        # 处理is_a继承
        for key, value in attrs:
            if key == "is_a":
                if isinstance(value, (list, tuple)):
                    parents = list(value)
                else:
                    parents = value.split()
                for p_info in parents:
                    parent_info = self._parse_parent_info(p_info)
                    source_name = parent_info["parent"]
                    included_attrs = parent_info.get("include", set())
                    excluded_attrs = parent_info.get("exclude", set())
                    is_exclude_mode = parent_info.get("is_exclude_mode", False)

                    source_def = self.get(source_name)
                    if source_def:
                        if "class" in source_def and "class" not in definition:
                            definition["class"] = copy.deepcopy(source_def["class"])

                        for attr, val in source_def.items():
                            if attr.startswith('_') or attr in ('type_name', 'is_a', 'class'):
                                continue
                            if is_exclude_mode:
                                if attr in excluded_attrs:
                                    continue
                            elif included_attrs and attr not in included_attrs:
                                continue
                            if attr not in definition:
                                definition[attr] = copy.deepcopy(val)
                    else:
                        warning(f"Unknown unit type for inheritance: {source_name}")
                
        return definition

    def parse_upgrade_definition(self, type_name, attrs):
        """解析升级定义，支持继承机制"""
        definition = {"type_name": type_name, "expanded_is_a": set()}
        
        # 处理常规属性
        for key, value in attrs:
            if key != "is_a":
                definition[key] = self.parse_property(key, value)
                
        # 处理is_a继承
        for key, value in attrs:
            if key == "is_a":
                source_upgrades = value.split()
                definition["is_a"] = source_upgrades
                
                # 展开并记录所有继承关系
                for source_name in source_upgrades:
                    if source_name not in definition["expanded_is_a"]:
                        definition["expanded_is_a"].add(source_name)
                        source_def = self.get(source_name)
                        if source_def:
                            # 特殊处理class属性，确保无论什么情况下都继承
                            if "class" in source_def and "class" not in definition:
                                definition["class"] = copy.deepcopy(source_def["class"])
                                
                            # 继承基类的expanded_is_a
                            if hasattr(source_def, "expanded_is_a"):
                                definition["expanded_is_a"].update(source_def.expanded_is_a)
                            # 继承其他属性
                            for attr, val in source_def.items():
                                if (not attr.startswith('_') and 
                                    attr not in ('type_name', 'is_a', 'expanded_is_a', 'class')):
                                    if attr not in definition:
                                        definition[attr] = copy.deepcopy(val)
                        else:
                            warning(f"Unknown upgrade type for inheritance: {source_name}")
                            
        return definition

    def parse_skill_definition(self, type_name, attrs):
        """解析技能定义，支持继承机制"""
        definition = {"type_name": type_name, "expanded_is_a": set()}
    
        # 处理常规属性
        for key, value in attrs:
            if key != "is_a":
                definition[key] = self.parse_property(key, value)
                
    # 处理is_a继承
        for key, value in attrs:
            if key == "is_a":
                source_skills = value.split()
                definition["is_a"] = source_skills
            
            # 展开并记录所有继承关系
                for source_name in source_skills:
                    if source_name not in definition["expanded_is_a"]:
                        definition["expanded_is_a"].add(source_name)
                        source_def = self.get(source_name)
                        if source_def:
                            # 特殊处理class属性，确保无论什么情况下都继承
                            if "class" in source_def and "class" not in definition:
                                definition["class"] = copy.deepcopy(source_def["class"])
                                
                        # 继承基类的expanded_is_a
                            if hasattr(source_def, "expanded_is_a"):
                                definition["expanded_is_a"].update(source_def.expanded_is_a)
                        # 继承其他属性
                            for attr, val in source_def.items():
                                if (not attr.startswith('_') and 
                                    attr not in ('type_name', 'is_a', 'expanded_is_a', 'class')):
                                    if attr not in definition:
                                        definition[attr] = copy.deepcopy(val)
                        else:
                            warning(f"Unknown skill type for inheritance: {source_name}")
                            
        return definition

    def parse_item_definition(self, type_name, attrs):
        """解析物品定义，支持继承机制"""
        definition = {"type_name": type_name, "expanded_is_a": set()}
        
        # 处理常规属性
        for key, value in attrs:
            if key != "is_a":
                definition[key] = self.parse_property(key, value)
                
        # 处理is_a继承
        for key, value in attrs:
            if key == "is_a":
                source_items = value.split()
                definition["is_a"] = source_items
                
                # 展开并记录所有继承关系
                for source_name in source_items:
                    if source_name not in definition["expanded_is_a"]:
                        definition["expanded_is_a"].add(source_name)
                        source_def = self.get(source_name)
                        if source_def:
                            # 特殊处理class属性，确保无论什么情况下都继承
                            if "class" in source_def and "class" not in definition:
                                definition["class"] = copy.deepcopy(source_def["class"])
                                
                            # 继承基类的expanded_is_a
                            if hasattr(source_def, "expanded_is_a"):
                                definition["expanded_is_a"].update(source_def.expanded_is_a)
                            # 继承其他属性
                            for attr, val in source_def.items():
                                if (not attr.startswith('_') and 
                                    attr not in ('type_name', 'is_a', 'expanded_is_a', 'class')):
                                    if attr not in definition:
                                        definition[attr] = copy.deepcopy(val)
                        else:
                            warning(f"Unknown item type for inheritance: {source_name}")
                            
        return definition

    def parse_definition(self, type_name, attrs):
        """根据类型选择合适的解析方法"""
        if type_name.startswith("summon_"):  # 对于召唤类技能
            return self.parse_skill_definition(type_name, attrs)
        elif any(attr[0] == "class" and attr[1] == "upgrade" for attr in attrs):
            return self.parse_upgrade_definition(type_name, attrs)
        elif any(attr[0] == "class" and attr[1] == "item" for attr in attrs):
            return self.parse_item_definition(type_name, attrs)
        else:
            return self.parse_unit_definition(type_name, attrs)


    def parse_property(self, key, value):
        """解析单个属性"""
        # 处理键值对属性
        if key in self.key_value_properties:
            result = {}
            if isinstance(value, str):
                items = value.split()
            else:
                items = value
            i = 0
            while i < len(items):
                if i + 1 >= len(items):
                    break
                try:
                    result[items[i]] = self.parse_item(items[i+1])
                except Exception as e:
                    warning(f"解析键值对属性失败: {e}")
                i += 2
            return result
        # 处理精度属性（支持百分比格式）
        elif key in self.precision_properties:
            if isinstance(value, int):
                return value
            elif isinstance(value, list) and value:
                try:
                    return self.parse_precision_value(value[0])
                except (ValueError, TypeError):
                    warning(f"无法将 {value[0]} 转换为精度值，使用默认值")
                    return 0
            else:
                try:
                    return self.parse_precision_value(value)
                except (ValueError, TypeError):
                    warning(f"无法将 {value} 转换为精度值，使用默认值")
                    return 0
        # 处理整数属性
        elif key in self.int_properties:
            if isinstance(value, int):
                return value
            elif isinstance(value, list) and value:
                try:
                    return int(value[0])
                except (ValueError, TypeError):
                    warning(f"无法将 {value[0]} 转换为整数，使用默认值")
                    return 0
            else:
                try:
                    return int(value)
                except (ValueError, TypeError):
                    warning(f"无法将 {value} 转换为整数，使用默认值")
                    return 0
        # 处理字符串属性
        elif key in self.string_properties:
            return str(value)
        # 处理整数列表属性
        elif key in self.int_list_properties:
            if isinstance(value, list):
                result = []
                for item in value:
                    try:
                        result.append(int(item))
                    except (ValueError, TypeError):
                        result.append(0)
                return result
            else:
                try:
                    return [int(x) for x in value.split()]
                except (ValueError, TypeError, AttributeError):
                    warning(f"无法解析 {value} 为整数列表，使用空列表")
                    return []
        # 处理字符串列表属性
        elif key in self.string_list_properties:
            if isinstance(value, list):
                return [str(x) for x in value]
            else:
                return value.split()
        # 默认返回原值
        else:
            return value
    
    def parse_precision_value(self, value):
        """解析精度值，支持普通数值和百分比格式"""
        if isinstance(value, str):
            # 处理百分比格式
            if value.endswith('%'):
                # 对于百分比格式，我们直接保留字符串格式
                # 让后续处理逻辑来决定如何处理
                return value
            else:
                # 普通数值格式，使用to_int转换
                from .lib.nofloat import to_int
                return to_int(value)
        else:
            # 如果已经是数值，直接返回
            return value

    def parse_item(self, value):
        """解析单个配置项的值"""
        try:
            # 尝试转换为整数
            return int(value)
        except (ValueError, TypeError):
            # 如果无法转换为整数，则返回原始值
            return value

    def parse_upgrade_effect(self, effect_str):
        """解析升级效果
        effect_str 格式: "bonus stat1 value1 [stat2 value2 ...]"
        """
        try:
            parts = effect_str.split()
            if len(parts) < 3 or len(parts) % 2 != 1:
                raise ValueError(f"Invalid effect format: {effect_str}")
            
            effect_type = parts[0]
            
            # 验证所有属性-值对
            for i in range(1, len(parts), 2):
                if i + 1 >= len(parts):
                    raise ValueError(f"Missing value for attribute: {parts[i]}")
                    
                stat = parts[i]
                value = parts[i + 1]
                
                # 验证属性是否合法
                if not (stat in self.precision_properties or 
                       stat in self.string_list_properties or 
                       stat in self.int_properties or
                       stat.startswith("transport_")):
                    raise ValueError(f"Unknown attribute: {stat}")
                
                # 处理特殊值
                if stat == "effect_range" and value in ("square", "nearby", "anywhere"):
                    continue
                
                if value == "inf":
                    continue
                    
                # 根据属性类型验证值
                try:
                    if stat in self.precision_properties:
                        to_int(value)
                    elif stat in self.int_properties:
                        int(value)
                except ValueError:
                    raise ValueError(f"Invalid value for {stat}: {value}")
            
            return parts
            
        except Exception as e:
            warning(f"Error parsing upgrade effect: {str(e)}")
            raise

    def load_rules(self, filename):
        """加载规则文件"""
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(';'):
                    continue
                    
                if line.startswith('def '):
                    self._parse_definition(line[4:])

    int_properties = {
        "nb_of_resource_types",  # only in parameters
        "collision",
        "corpse",
        "population_cost",
        "population_provided",
        "harm_level",
        "heal_level",

        "is_repairable",
        "is_healable",
        "is_vulnerable",
        "is_undead",
        "is_a_building_land",
        "is_buildable_anywhere",
        "bonus_height",
        "transport_capacity",
        "transport_volume",
        "inventory_capacity",  # 添加inventory_capacity
        "is_invisible",
        "is_cloakable",
        "is_a_detector",
        "is_a_cloaker",
        "universal_notification",
        "presence",
        "provides_survival",
        "is_teleportable",
        "is_a_gate",
        "is_buildable_on_exits_only",
        "is_buildable_near_water_only",
        "is_buildable_on_water_only",
        "self_constructs",
        "build_sacrifices_worker",
        "build_field_persists",
        "build_field_spreads",
        "build_field_spread_squares",
        "requires_build_field_on_square",
        "summon_requires_marked_field",
        "morph_as_train",  # can_upgrade_to / can_change_to 均按目标单位训练成本/时间计费
        "larva_cap",  # 主巢：该格最多同时存在的幼虫数
        "loses_power_without_field",
        "is_addon",
        "addon_max",
        "addon_train_multiplier",  # 反应堆等：训练数量倍率（2=双产）
        "can_repair_ships",  # 是否允许修理船只，1允许，0不允许
        "count_limit",
        "global_count_limit",
        "is_revivable",
        "campaign_carryover",  # 1 = 单人战役跨章保存（见 campaign_carryover_stats / inventory）
        "campaign_carryover_stats",  # 1 = 跨章保存等级与经验（默认随 campaign_carryover 开启）
        "campaign_carryover_inventory",  # 1 = 跨章保存背包（默认随 campaign_carryover 开启）
        "xp_reward",
        "xp",
        "production_time",
        "production_qty",
        "level",
        "max_level",  # 英雄等级上限；与 xp_threshold_growth 配合，加载时展开为 xp_thresholds
        "level_up_heal_full",  # 1 = 升级后生命/法力回满（默认 0：仅加上限增量）
        "level_up_reset_xp",  # 1 = 升级后当前经验清零（默认 0：保留累计经验）
        "allow_attack_inside", # 允许攻击载具内部目标
        "attack_inside_chance",  # 容器：外部攻击命中内部乘客的几率（0-100）
        "capture_hp_threshold",  # 可被夺取的血量阈值(百分比,0表示不可夺取)
        "yield_on_defeat",       # 战败投降(不死亡)，用于比武收服剧情
        "reflect_percent",  # buff：反弹所受伤害比例（0-100）
        "mdg_projectile",  # 近战攻击是否为投射物
        "rdg_projectile",  # 远程攻击是否为投射物
        "extraction_time",  # 资源开采时间
        "extraction_qty",   # 资源开采量
        "auto_production",   # 建筑物是否可以生产资源
        "manual_production",   # 建筑物是否可以生产资源
        "auto_cultivate",   # 建筑物是否可以生产资源
        "manual_cultivate",   # 建筑物是否可以生产资源
        "is_gather",
        "is_dynamic",
        "is_high_ground",
        "is_water",
        "is_ground",
        "is_air",
        "height",
        "blocks_path",
        "resource_volume_max",
        "resource_volume_start",
        "resource_regen",
        "mdg_piercing",
        "rdg_piercing",
        "mdg_crit_rate", # 近战触发率，百分比（0-100）
        "rdg_crit_rate", # 远程触发率，百分比（0-100）
        "mdf_piercing",
        "rdf_piercing",
        "mdg_piercing_rate",
        "rdg_piercing_rate",
        "mdf_crit_rate",
        "rdf_crit_rate",
        "is_loot",
        "can_repair",  # 是否允许修理，1允许，0不允许
        "can_capture",  # 是否对夺取阈值100的目标使用占领命令，1允许，0不允许
        "can_herd",  # 是否允许驱赶牲畜，1允许，0不允许
        "receive_items",  # 是否接收其他单位交给的物品（1接收/0不接收，默认0）
        "auto_gather",  # 是否自动采集资源
        "auto_repair",  # 是否自动修理建筑物
        "auto_explore",  # 开局是否自动探索（可移动单位）
        "can_auto_explore",  # 命令菜单里是否提供"启用/禁用自动探索"选项
        "can_switch_ai_mode",  # 是否可以切换AI模式
        "spawn_weapons_equipped",  # 出厂时是否自动装备武器（1装备/0不装备）
        "spawn_armor_equipped",  # 出厂时是否自动装备护甲（1装备/0不装备）
        "auto_weapon_switch",  # 是否启用自动武器切换
        "drop_loot",  # 是否掉落物品
        "mdg_explode",  # 近战攻击是否自爆
        "rdg_explode",  # 远程攻击是否自爆
        "consume_on_pickup",  # 拾取时是否消耗物品
        "units_auto_upgrade",  # phase（时代）研究完成后是否自动把所有单位形态升级到 can_upgrade_to 目标
        "hide_locked_commands",  # 未满足 requirements 时是否隐藏建造/训练/研究/升级命令
        "achievements_enabled",  # 1=启用成就/卡牌/军衔（默认）；0=模组关闭整套系统
        "achievements_per_faction",  # 1=按阵营独立存档/军衔/军械库（多分支模组如 CrazyMod）
        "no_number",  # 1=同类型仅1个时不报序号，2个及以上才报（默认0=始终报序号）
        "is_huntable",  # 可被村民狩猎的动物（右键默认攻击）
        "food_deposit_qty",  # 死亡后留下的食物尸体储量
        "flee_on_hit",  # 受击后逃跑（鹿、羊等）
        "herdable",  # 可被村民驱赶跟随（羊）
        "herd_leash_range",  # 驱赶跟随的最大距离（毫米）
        "wander_range",  # 野生动物徘徊的最大半径（毫米）
    
    }
    precision_properties = _precision_properties_extended
    int_list_properties = {
        "resource_rewards",  # 物品/单位击杀奖励，[资源1数量, 资源2数量]
        "xp_thresholds",
    }
    precision_list_properties = {"cost", "storage_bonus", "production_cost"}
    
    # 字符串列表属性
    string_list_properties = {
        "storable_resource_types",  # 添加这个新的属性集合
        "mdg_targets",
        "rdg_targets",
        "mdg_cover_on_terrain",
        "rdg_cover_on_terrain",
        "mdg_dodge_on_terrain",
        "rdg_dodge_on_terrain",
        "mdg_on_terrain",
        "rdg_on_terrain",
        "mdg_cd_on_terrain",
        "rdg_cd_on_terrain",
        "charge_mdg_terrain",
        "charge_rdg_terrain",
        "charge_mdg_cd_on_terrain",
        "charge_rdg_cd_on_terrain",
        "passenger_attack_types",  # 容器内可攻击的单位类型列表
        "can_gather",          # 已废弃，见 can_gather_deposit / can_gather_building
        "can_gather_deposit",  # 可开采的矿床（deposit）类型列表
        "can_gather_building", # 可开采的建筑类型列表（如 farm）
        "can_change_to",       # 单位可以变形为的单位类型列表
        "addon_host_types",    # 附属建筑可依附的主建筑类型
        "can_have_addon",      # 主建筑可挂载的附属建筑类型
        "addon_grants_train",  # 附件为任意宿主增加的 train 列表
        "addon_grants_train_barracks",
        "addon_grants_train_factory",
        "addon_grants_train_starport",
        "addon_grants_research",  # 附件为宿主增加的研究项
        "accepted_items",      # NPC可接受的物品类型列表（type_name，支持is_a；空=接收任意）
        "accept_from",         # 仅接收来自这些关系的给予者：self/ally/neutral/enemy（空=不限）
        "accept_givers",       # 仅接收这些单位类型交来的物品（type_name，支持is_a；空=不限）
        "passable_units",      # 地形允许通行的单位类型（type_name，支持 is_a 继承链）
        "speed_vs",
        "cover_vs",
        "dodge_vs",
        "mdg_vs",
        "rdg_vs",
        "mdg_cd_vs",
        "rdg_cd_vs",
        "menace_vs",
        "menace_mult_vs",
    }

    def parse_resource_list(self, resource_list):
        """解析资源类型列表"""
        if not resource_list:
            return []
            
        result = []
        for resource in resource_list:
            index = self.parse_resource_type(resource)
            if index is not None:
                result.append(index)
                
        return result

    def get_property(self, classname, property_name, default=None):
        """重写get_property方法来处理资源类型列表"""
        value = super().get_property(classname, property_name, default)
        
        if property_name == "storable_resource_types" and value:
            return self.parse_resource_list(value)
            
        return value

    def parse_resource_type(self, resource_str):
        """
        将resource1、resource2等格式解析为对应的资源索引
        返回资源类型的索引(0-based)
        """
        if not resource_str:
            return None
            
        # 如果是数字,保持向后兼容
        if isinstance(resource_str, int) or resource_str.isdigit():
            return int(resource_str)
            
        # 解析resource{n}格式
        if resource_str.startswith('resource'):
            try:
                return int(resource_str[8:]) - 1  # resource1 -> 0
            except ValueError:
                return None
                
        return None


    def normalized_cost_or_resources(self, lst):
        lst = lst[:]
        n = self.get("parameters", "nb_of_resource_types", 2)
        while len(lst) < n:
            lst += [0]
        while len	(lst) > n:
            del lst[-1]
        return lst

    _DOC_ONLY_PROPERTIES = frozenset({"name", "desc", "description"})
    _PARSE_ONLY_PROPERTIES = frozenset({"max_level", "xp_threshold_growth"})
    _RULES_ONLY_PROPERTIES = frozenset({"square_terrain"})

    def _expand_xp_thresholds_for_all_units(self):
        from .xp_threshold_growth import expand_xp_thresholds_in_definition

        for name, defn in self._dict.items():
            if defn.get("class", [None])[0] in _get_base_classes():
                expand_xp_thresholds_in_definition(defn, name)

    def interpret(self, d, base, name):
        if hasattr(base, "interpret"):
            base.interpret(d)
        if hasattr(base, "mdg_seq_times"):
            d.setdefault("mdg_seq_times", 1)
            d.setdefault("mdg_seq_damages", [])
            d.setdefault("mdg_seq_interval", 0)
        if hasattr(base, "rdg_seq_times"):
            d.setdefault("rdg_seq_times", 1)
            d.setdefault("rdg_seq_damages", [])
            d.setdefault("rdg_seq_interval", 0)
        if "cost" not in d and hasattr(base, "cost"):
            d["cost"] = [0] * self.get("parameters", "nb_of_resource_types", 2)
        d = _update_old_definitions(d, name)
        for k, v in list(d.items()):
            if k == "class":
                continue
            if k in self._PARSE_ONLY_PROPERTIES:
                del d[k]
                continue
            if k in self._RULES_ONLY_PROPERTIES:
                continue
            if k in self._DOC_ONLY_PROPERTIES:
                continue
            if (
                not hasattr(base, k)
                and not (k.endswith("_bonus") and hasattr(base, k[:-6]))
                and not (k.startswith("gather_time_") or k.startswith("gather_qty_"))
                and not (k.endswith("_per_level") and k[:-10] in LEVEL_UP_STAT_ATTRS)
            ) or callable(getattr(base, k, None)):
                del d[k]
                warning(
                    "in %s: %s doesn't have any attribute called '%s'", name, base, k,
                )
            elif k == "cost":
                d[k] = self.normalized_cost_or_resources(v)

    def load(self, *strings, base_classes=None):
        if base_classes is None:
            base_classes = _get_base_classes()
        self._dict = {}
        if hasattr(self, "_get_cache"):
            self._get_cache.clear()
        if hasattr(self, "_makers_cache"):
            self._makers_cache.clear()
        try:
            from .lib.square_terrain_rules import clear_terrain_lookup_caches

            clear_terrain_lookup_caches()
        except ImportError:
            pass
        for s in strings:
            s = re.sub(r"^[ \t]*class +race\b", "class faction", s, flags=re.M)
            self.read(s)
        self.apply_inheritance(expanded_is_a=True)
        self._expand_xp_thresholds_for_all_units()
        from .worldunit.worldworker import Worker
        previous_interp_rules = getattr(Worker, "_interp_rules_dict", None)
        Worker._interp_rules_dict = self._dict
        d = {}
        try:
            for k, v in self._dict.items():
                cls = v.get("class", [None])[0]
                if cls == "terrain":
                    from .worldterrain import TerrainRules

                    self.interpret(v, TerrainRules, k)
                    continue
                if cls in base_classes:
                    base = base_classes[cls]
                    self.interpret(v, base, k)
                    # can_train 解析为 dict 时会遮蔽 Building.can_train @property
                    if isinstance(v.get("can_train"), dict):
                        v["_rules_can_train"] = v.pop("can_train")
                    d[k] = type(k, (base,), v)
                    d[k].type_name = k
                    d[k].cls = base
        finally:
            if previous_interp_rules is None:
                if hasattr(Worker, "_interp_rules_dict"):
                    delattr(Worker, "_interp_rules_dict")
            else:
                Worker._interp_rules_dict = previous_interp_rules
        self.classes = d

    def classnames(self):
        result = _Definitions.classnames(self)
        result.remove("parameters")
        return result

    @property
    def factions(self):
        return [c for c in self.classnames() if self.get(c, "class") == ["faction"]]

    def unit_class(self, s):
        """Get a custom unit class from its name.

        Example: unit_class("peasant") to get the peasant class

        At the moment, unit_classes contains also: upgrades, skills...
        """
        try:
            return self.classes[s]
        except KeyError:
            return

    def equivalent_type(self, t, faction):
        tn = getattr(t, "type_name", "")
        if rules.get(faction, tn):
            return self.unit_class(rules.get(faction, tn)[0])
        return t

    def _get_classnames(self, condition):
        result = []
        for c in self.classnames():
            uc = self.unit_class(c)
            if uc is not None and condition(uc):
                result.append(c)
        return result

    def class_rules_attr(self, cls, name, default=()):
        return _raw_class_attr(cls, name, default)

    def class_can_train(self, cls):
        raw = _raw_class_attr(cls, "_rules_can_train", None)
        if raw:
            return raw
        return _raw_class_attr(cls, "can_train", ())

    def get_makers(self, t):
        def can_make(uc, t):
            rules_train = _raw_class_attr(uc, "_rules_can_train", None)
            if rules_train and t in rules_train:
                return True
            for a in ("can_build", "can_train", "can_upgrade_to", "can_research", "can_advance"):
                if t in _raw_class_attr(uc, a, ()):
                    return True
            for skill in _raw_class_attr(uc, "can_use", ()):
                effect = self.get(skill, "effect")
                if effect and "summon" in effect[:1] and t in effect:
                    return True
            if getattr(uc, "morph_as_train", 0):
                if t in _raw_class_attr(uc, "can_change_to", ()):
                    return True

        if t.__class__ != str:
            t = t.__name__
        cache = getattr(self, "_makers_cache", None)
        if cache is None:
            cache = {}
            self._makers_cache = cache
        cached = cache.get(t)
        if cached is not None:
            return cached
        result = self._get_classnames(lambda uc: can_make(uc, t))
        cache[t] = result
        return result


def parse_noise(st):
    if st:
        if st[0] == "if_me":
            return "if_me", parse_noise(st[1]), parse_noise(st[2])
        ambient = st[0] == "ambient"
        if ambient:
            st = st[1:]
        t = st[0]
        if t == "loop":
            try:
                v = float(st[2])
            except IndexError:
                v = 1
            return "loop", st[1], v, ambient
        if t == "repeat":
            return "repeat", float(st[1]), st[2:], ambient
    return ()


class Style(_Definitions):
    @staticmethod
    def _attr_aliases(attr):
        aliases = []
        if "mdg" in attr or "rdg" in attr:
            aliases.append(attr.replace("mdg", "matk").replace("rdg", "ratk"))
        if "matk" in attr or "ratk" in attr:
            aliases.append(attr.replace("matk", "mdg").replace("ratk", "rdg"))
        return [a for a in aliases if a != attr]

    def __init__(self):
        self._style_warnings = []
        # 默认音乐设置
        self._menu_music = None
        self._game_music = None

    def load(self, *strings):
        self._dict = {}
        for s in strings:
            self.read(s)
        for d in self._dict.values():
            for k, v in d.items():
                if v and v[0] == "if_me":
                    if "else" in v:
                        i = v.index("else")
                        v = "if_me", v[1:i], v[i + 1:]
                    else:
                        v = "if_me", v[1:], []
                if k.startswith("noise"):
                    try:
                        v = parse_noise(v)
                    except:
                        warning("problem with noise: %s", " ".join(d[k]))
                d[k] = v
        
        # 处理增强继承语法
        self._process_enhanced_inheritance()
        
        # 加载背景音乐设置
        self._load_music_settings()
        
    def _load_music_settings(self):
        """从style.txt中加载背景音乐设置"""
        from soundrts.lib import sound
        
        # 从style.txt中读取各种菜单音乐和游戏内背景音乐
        menu_music_path = self.get("parameters", "menu_music", warn_if_not_found=False)
        game_music_path = self.get("parameters", "game_music", warn_if_not_found=False)
        campaign_music_path = self.get("parameters", "campaign_music", warn_if_not_found=False)
        game_creation_music_path = self.get("parameters", "game_creation_music", warn_if_not_found=False)
        server_lobby_music_path = self.get("parameters", "server_lobby_music", warn_if_not_found=False)
        battle_music_path = self.get("parameters", "battle_music", warn_if_not_found=False)
        victory_sound_path = self.get("parameters", "victory_sound", warn_if_not_found=False)
        defeat_sound_path = self.get("parameters", "defeat_sound", warn_if_not_found=False)
        
        # 设置音乐路径
        if menu_music_path:
            resolved_path = self._resolve_music_path(menu_music_path)
            if resolved_path:
                sound.set_menu_music(resolved_path)
            
        if game_music_path:
            resolved_path = self._resolve_music_path(game_music_path)
            if resolved_path:
                sound.set_game_music(resolved_path)
                
        if campaign_music_path:
            resolved_path = self._resolve_music_path(campaign_music_path)
            if resolved_path:
                sound.set_campaign_music(resolved_path)
                
        if game_creation_music_path:
            resolved_path = self._resolve_music_path(game_creation_music_path)
            if resolved_path:
                sound.set_game_creation_music(resolved_path)
                
        if server_lobby_music_path:
            resolved_path = self._resolve_music_path(server_lobby_music_path)
            if resolved_path:
                sound.set_server_lobby_music(resolved_path)
                
        if battle_music_path:
            resolved_path = self._resolve_music_path(battle_music_path)
            if resolved_path:
                sound.set_battle_music(resolved_path)
                
        if victory_sound_path:
            resolved_path = self._resolve_music_path(victory_sound_path)
            if resolved_path:
                sound.set_victory_sound(resolved_path)
                
        if defeat_sound_path:
            resolved_path = self._resolve_music_path(defeat_sound_path)
            if resolved_path:
                sound.set_defeat_sound(resolved_path)
                
        # 加载阵营专属音乐设置
        self._load_faction_music_settings()

    def _load_faction_music_settings(self):
        """从style.txt中加载阵营专属音乐设置"""
        from soundrts.lib import sound
        from .lib.log import debug
        
        # 查找以_music结尾的参数，这些是阵营专属音乐
        faction_music_settings = {}
        faction_battle_music_settings = {}
        
        # 遍历parameters中的所有设置
        if "parameters" in self._dict:
            for key, value in self._dict["parameters"].items():
                # 检查是否是阵营专属音乐设置（以_music结尾）
                if key.endswith("_music") and key not in [
                    "menu_music", "game_music", "campaign_music", 
                    "game_creation_music", "server_lobby_music", "battle_music"
                ]:
                    # 提取阵营ID和音乐类型
                    if key.endswith("_battle_music"):
                        # 阵营专属战斗音乐 (例如: china_battle_music)
                        faction_id = key[:-13]  # 移除"_battle_music"
                        music_type = "battle"
                    else:
                        # 普通阵营专属音乐 (例如: china_music)
                        faction_id = key[:-6]  # 移除"_music"
                        music_type = "normal"
                    
                    # 获取音乐ID或路径
                    if isinstance(value, list) and value:
                        music_id = value[0]
                    else:
                        music_id = value
                    
                    # 检查音乐文件是否存在
                    resolved_path = self._resolve_music_path(music_id)
                    if resolved_path:
                        # 将阵营ID和音乐路径存储到相应字典中
                        if music_type == "battle":
                            faction_battle_music_settings[key] = resolved_path
                            debug(f"找到阵营 {faction_id} 的专属战斗音乐: {resolved_path}")
                        else:
                            faction_music_settings[faction_id] = resolved_path
                            debug(f"找到阵营 {faction_id} 的专属背景音乐: {resolved_path}")
                    else:
                        if music_type == "battle":
                            debug(f"阵营 {faction_id} 的专属战斗音乐文件未找到: {music_id}")
                        else:
                            debug(f"阵营 {faction_id} 的专属背景音乐文件未找到: {music_id}")
        
        # 将阵营音乐设置存储到样式对象中，以便稍后使用
        self.faction_music_settings = faction_music_settings
        self.faction_battle_music_settings = faction_battle_music_settings

    def _resolve_music_path(self, music_path_setting):
        """解析音乐文件路径
        
        如果提供的是相对路径，将其转换为绝对路径
        支持从mod文件夹中加载音乐
        
        Args:
            music_path_setting: 从style.txt中读取的音乐路径设置
            
        Returns:
            str: 解析后的音乐文件绝对路径，如果找不到则返回None
        """
        from soundrts.lib.sound import MUSIC_FORMATS
        import os
        
        if not music_path_setting:
            return None
            
        # 如果有多个路径，只使用第一个
        if isinstance(music_path_setting, list) and music_path_setting:
            music_path = music_path_setting[0]
        else:
            music_path = music_path_setting
            
        # 检查是否为绝对路径
        if os.path.isabs(music_path) and os.path.exists(music_path):
            return music_path
            
        # 如果未指定扩展名，自动添加.mp3后缀
        base_path = music_path
        if not music_path.lower().endswith('.mp3'):
            full_path = base_path + '.mp3'
            # 先检查相对于当前目录的路径
            if os.path.exists(full_path):
                return full_path
            # 检查ui/music目录
            ui_music_path = os.path.join('ui', 'music', full_path)
            if os.path.exists(ui_music_path):
                return ui_music_path
        else:
            # 已指定扩展名，直接查找
            if os.path.exists(music_path):
                return music_path
            # 检查ui/music目录
            ui_music_path = os.path.join('ui', 'music', music_path)
            if os.path.exists(ui_music_path):
                return ui_music_path
            
        # 这里不再尝试导入res，而是返回一个用于延迟解析的字符串
        # 音乐加载器将尝试在不同路径查找该文件
        return music_path

    def _process_enhanced_inheritance(self):
        """处理增强的继承语法，包括多重继承和属性选择性继承"""
        for ko, o in list(self._dict.items()):
            if "is_a" in o:
                # 将字符串形式的is_a转换为列表形式，以支持多重继承
                if isinstance(o["is_a"], str):
                    # 分割多个父类（空格分隔）
                    parents = []
                    parts = o["is_a"].split()
                    i = 0
                    while i < len(parts):
                        # 如果下一个部分是以"("开头的括号，需要合并到当前父类
                        if i + 1 < len(parts) and "(" in parts[i] and ")" not in parts[i]:
                            # 查找闭合括号
                            j = i + 1
                            parent_str = parts[i]
                            while j < len(parts) and ")" not in parts[j]:
                                parent_str += " " + parts[j]
                                j += 1
                            if j < len(parts):
                                parent_str += " " + parts[j]
                                parents.append(parent_str)
                                i = j + 1
                            else:
                                # 没有找到闭合括号，作为单独的父类
                                parents.append(parts[i])
                                i += 1
                        elif "(" in parts[i] and ")" in parts[i]:
                            # 括号在同一个部分内
                            parents.append(parts[i])
                            i += 1
                        else:
                            # 普通父类名称
                            parents.append(parts[i])
                            i += 1
                    o["is_a"] = parents
        
        # 应用继承
        self.apply_inheritance()

    def get(self, obj, attr, warn_if_not_found=True):
        result = _Definitions.get(self, obj, attr)
        if result is None:
            for alias in self._attr_aliases(attr):
                result = _Definitions.get(self, obj, alias)
                if result is not None:
                    break
        if result is None:
            result = []  # the caller might expect a list
            if warn_if_not_found:
                # 忽略已经被新系统替代的属性
                deprecated_attrs = {
                    'missed',  # 已被 dodge 系统替代
                }
                
                if attr not in deprecated_attrs:
                    # 仅在调试模式下输出缺失样式项的告警
                    should_warn = True
                    try:
                        from . import config
                        should_warn = bool(getattr(config, "debug_mode", 0))
                    except Exception:
                        # 如果无法读取配置，维持默认行为（非调试模式下不告警）
                        should_warn = False

                    if should_warn and (obj, attr) not in self._style_warnings:
                        self._style_warnings.append((obj, attr))
                        warning("no value found for %s.%s (check style.txt)", obj, attr)
        return result

    def has(self, obj, attr):
        if _Definitions.get(self, obj, attr) is not None:
            return True
        return any(_Definitions.get(self, obj, alias) is not None for alias in self._attr_aliases(attr))


# AI (probably completely separate)


# ---------------------------------------------------------------------------
# AI script loader
# ---------------------------------------------------------------------------
#
# ``ai.txt`` is loaded as a layered concatenation: base ``res/ai.txt``, then
# each enabled mod's ``ai.txt``, then the optional per-campaign and per-map
# ``ai.txt`` (see ``resource.py:load_rules_and_ai`` / ``text(append=True)``).
# Names defined later replace earlier ones with the same name.
#
# The two top-level directives understood by this loader are:
#
# * ``def <name>``: starts a new AI script. Subsequent non-directive lines
#   become its body until the next ``def`` (or ``clear``, or end-of-file).
# * ``clear``: wipes every AI script accumulated so far. This mirrors
#   ``Rules.load``'s ``clear`` directive and lets a mod *replace* the base
#   list (e.g. crazyMod's faction-specific AIs) instead of being forced to
#   coexist with the base ``easy``/``aggressive`` defs. Without ``clear``
#   the mod's defs are simply appended on top of the base list.
#
# Lines before any ``def`` (and that are not directives) are reported with a
# warning, just like before — this catches the common mistake of forgetting
# to write ``def <name>`` at the top of a new section.


def _read_ai_to_dict(s, d, order=None):
    s = preprocess(s)
    name = None
    had_clear = False
    new_defs = []
    for line in s.split("\n"):
        words = line.split()
        if not words:
            continue
        if words[0] == "clear":
            d.clear()
            if order is not None:
                order.clear()
            name = None
            had_clear = True
        elif words[0] == "def":
            name = words[1]
            d[name] = []
            new_defs.append(name)
            if order is not None and name not in order:
                order.append(name)
        elif name is not None:
            d[name] += [line]
        else:
            warning("'def <AI_name>' is missing (check ai.txt)")
    return had_clear, new_defs


_ai = {}
_ai_load_order = []
_ai_mod_contributed = False
_ai_mod_menu_order = []


# ---------------------------------------------------------------------------
# Difficulty levels
# ---------------------------------------------------------------------------
#
# The five built-in computer difficulties. Each one is just an AI script that
# the player can (re)write in ``ai.txt`` with ``def <name>``:
#
#   beginner     (初级 / Beginner)     — was the legacy ``easy`` AI
#   intermediate (中级 / Intermediate) — was the legacy ``aggressive`` AI
#   advanced     (高级 / Advanced)
#   expert       (专家 / Expert)
#   nightmare    (噩梦 / Nightmare)
#
# ``AI_DIFFICULTIES`` keeps the menu / server order in one place.
AI_DIFFICULTIES = ["beginner", "intermediate", "advanced", "expert", "nightmare"]

# When the requested difficulty has no ``def`` in the loaded ``ai.txt`` files,
# ``get_ai`` walks down this list until it finds one that exists. This keeps
# old mods (that only define ``easy`` / ``aggressive``) working with the new
# difficulty buttons, and lets a player ship just a couple of difficulties.
_AI_FALLBACKS = {
    "beginner": ["beginner", "easy"],
    "intermediate": ["intermediate", "aggressive", "beginner", "easy"],
    "advanced": ["advanced", "intermediate", "aggressive", "beginner", "easy"],
    "expert": [
        "expert", "advanced", "intermediate", "aggressive", "beginner", "easy"
    ],
    "nightmare": [
        "nightmare", "expert", "advanced", "intermediate", "aggressive",
        "beginner", "easy",
    ],
    # legacy names map onto the new ones
    "easy": ["easy", "beginner"],
    "aggressive": ["aggressive", "intermediate"],
}

# Script-only AIs (map triggers, legacy cheat AI, …) — never offered in invite menus.
_AI_MENU_HIDDEN = frozenset({"timers", "ai2"})

# Standard invite-tier ids. Mods may also ship custom names (``tang_easy``, …).
_MENU_TIER_ORDER = list(AI_DIFFICULTIES) + ["easy", "aggressive"]

_AI_PLAYER_LABELS = {
    "beginner": "BEGINNER_COMPUTER",
    "intermediate": "INTERMEDIATE_COMPUTER",
    "advanced": "ADVANCED_COMPUTER",
    "expert": "EXPERT_COMPUTER",
    "nightmare": "NIGHTMARE_COMPUTER",
    "easy": "QUIET_COMPUTER",
    "aggressive": "AGGRESSIVE_COMPUTER",
}


def _defs_in_layer(s):
    """``def`` names declared in one ai.txt layer, in source order."""
    s = preprocess(s)
    names = []
    for line in s.split("\n"):
        words = line.split()
        if not words:
            continue
        if words[0] == "clear":
            names = []
        elif words[0] == "def":
            name = words[1]
            if name not in names:
                names.append(name)
    return names


def load_ai(*strings):
    global _ai, _ai_load_order, _ai_mod_contributed, _ai_mod_menu_order
    _ai = {}
    _ai_load_order = []
    _ai_mod_contributed = False
    _ai_mod_menu_order = []
    for index, s in enumerate(strings):
        if not s or not s.strip():
            continue
        _read_ai_to_dict(s, _ai, _ai_load_order)
        if index == 0:
            continue
        _ai_mod_contributed = True
        for name in _defs_in_layer(s):
            if name not in _ai_mod_menu_order:
                _ai_mod_menu_order.append(name)


# One-shot directives in ai.txt (applied at game start, not in the script loop).
AI_ONE_SHOT_COMMANDS = frozenset({
    "starting_resources",
    "starting_units",
    "starting_population",
    "defeat_score",
    "train_time",
    "research_time",
    "build_time",
    "gather_time",
    "unit_hp",
})

# Post-game bonus for defeating this AI difficulty (overridable per ``def`` in ai.txt).
DEFAULT_AI_DEFEAT_SCORE = {
    "beginner": 10,
    "easy": 10,
    "intermediate": 20,
    "aggressive": 20,
    "advanced": 40,
    "expert": 80,
    "nightmare": 200,
}


def filter_ai_executable_plan(lines):
    """Drop start-only lines from the runtime AI script loop."""
    filtered = []
    for line in lines:
        words = line.split()
        if words and words[0] in AI_ONE_SHOT_COMMANDS:
            continue
        filtered.append(line)
    return filtered


def _parse_ai_percent_directive(words, name, default=100):
    """Parse ``name <pct>`` from ai.txt; ``pct`` is a positive integer percent."""
    if len(words) >= 2 and re.match("^[0-9]+$", words[1]):
        return max(0, int(words[1]))
    warning("%s: expected a non-negative integer percent (in ai.txt)", name)
    return default


def parse_ai_start_settings(name):
    """Return start settings from the resolved AI script.

    Returns
    -------
    resource_bonus
        Amounts **added** to the map/faction start (same length as rules
        resource types), or ``None``.
    unit_tokens
        Flat tokens like map ``starting_units`` (counts before type names).
    population_bonus
        Added to ``player.population`` after units spawn.
    train_time_percent
        Percent of normal training duration (100 = normal, 50 = half time).
    research_time_percent
        Percent of normal research/advance duration (100 = normal).
    build_time_percent
        Percent of normal building-construction duration (100 = normal).
    gather_time_percent
        Percent of normal resource-gathering duration (100 = normal, 50 = twice as fast).
    unit_hp_percent
        Percent of normal unit HP (100 = normal, 120 = +20%).
    """
    lines = get_ai(name)
    resource_bonus = None
    unit_tokens = []
    population_bonus = 0
    train_time_percent = 100
    research_time_percent = 100
    build_time_percent = 100
    gather_time_percent = 100
    unit_hp_percent = 100
    for line in lines:
        words = line.split()
        if not words:
            continue
        if words[0] == "starting_resources":
            raw = []
            for w in words[1:]:
                if re.match("^[0-9]+$", w):
                    raw.append(to_int(w))
                else:
                    warning("starting_resources: expected a number (in ai.txt), got '%s'", w)
            if raw:
                resource_bonus = rules.normalized_cost_or_resources(raw)
        elif words[0] == "starting_units":
            unit_tokens = words[1:]
        elif words[0] == "starting_population":
            if len(words) >= 2 and re.match("^[0-9]+$", words[1]):
                population_bonus = int(words[1])
            else:
                warning("starting_population: expected an integer (in ai.txt)")
        elif words[0] == "train_time":
            train_time_percent = _parse_ai_percent_directive(words, "train_time")
        elif words[0] == "research_time":
            research_time_percent = _parse_ai_percent_directive(words, "research_time")
        elif words[0] == "build_time":
            build_time_percent = _parse_ai_percent_directive(words, "build_time")
        elif words[0] == "gather_time":
            gather_time_percent = _parse_ai_percent_directive(words, "gather_time")
        elif words[0] == "unit_hp":
            unit_hp_percent = _parse_ai_percent_directive(words, "unit_hp")
    return (
        resource_bonus,
        unit_tokens,
        population_bonus,
        train_time_percent,
        research_time_percent,
        build_time_percent,
        gather_time_percent,
        unit_hp_percent,
    )


def get_ai_defeat_score(name):
    """Bonus points for defeating a computer of difficulty ``name``.

    Reads optional ``defeat_score <n>`` from the resolved ai.txt script (same
    fallback chain as ``get_ai``). Falls back to ``DEFAULT_AI_DEFEAT_SCORE``
    for built-in tiers; custom ``def`` names without the directive score 0.
    """
    for line in get_ai(name):
        words = line.split()
        if not words or words[0] != "defeat_score":
            continue
        if len(words) >= 2 and re.match("^[0-9]+$", words[1]):
            return max(0, int(words[1]))
        warning("defeat_score: expected a non-negative integer (in ai.txt), got '%s'", words[1] if len(words) >= 2 else "")
        break
    return DEFAULT_AI_DEFEAT_SCORE.get(name, 0)


def get_ai(name):
    for candidate in _AI_FALLBACKS.get(name, [name]):
        if candidate in _ai:
            return _ai[candidate]
    # last resort: any loaded difficulty (keeps the AI from crashing if the
    # author forgot to define the requested level and gave no fallback either)
    for candidate in AI_DIFFICULTIES + ["easy", "aggressive"]:
        if candidate in _ai:
            return _ai[candidate]
    return []


def get_ai_names():
    return list(_ai.keys())


def _tier_mapped_in_rules(tier):
    for faction in rules.factions:
        val = rules.get(faction, tier)
        if val and val[0] in _ai:
            return True
    return False


def get_menu_ai_difficulties():
    """Return AI type names to show in single/multiplayer invite menus.

    No mod ``ai.txt``: the five standard tiers.
    With a mod: tiers declared in ``rules.txt`` (``beginner tang_empire_easy``,
    ``easy tang_empire_easy``, …) whose script ``def`` exists in ``ai.txt``.
    ``beginner`` … ``nightmare`` → 初级 … 噩梦; legacy ``easy`` / ``aggressive``
    → 防御型 / 攻击型 (old mods).
    """
    if not _ai_mod_contributed:
        return list(AI_DIFFICULTIES)
    tiers = [tier for tier in _MENU_TIER_ORDER if _tier_mapped_in_rules(tier)]
    if "beginner" in tiers and "easy" in tiers:
        tiers.remove("easy")
    if "intermediate" in tiers and "aggressive" in tiers:
        tiers.remove("aggressive")
    if tiers:
        return tiers
    return [tier for tier in AI_DIFFICULTIES if tier in _ai]


def ai_player_label(ai_type):
    """Human-facing label for an AI type (without the INVITE prefix)."""
    from . import msgparts as mp

    attr = _AI_PLAYER_LABELS.get(ai_type)
    if attr is not None:
        return list(getattr(mp, attr))
    title = style.get(ai_type, "title", warn_if_not_found=False)
    if title:
        return list(title)
    return [ai_type.replace("_", " ")]


def ai_invite_label(ai_type):
    from . import msgparts as mp

    return list(mp.INVITE) + ai_player_label(ai_type)


# define two convenient variables

rules = Rules()
for _level_up_attr in LEVEL_UP_STAT_ATTRS:
    if _level_up_attr in rules.int_properties:
        rules.int_properties.add(f"{_level_up_attr}_per_level")
style = Style()
