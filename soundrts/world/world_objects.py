"""
World对象管理模块 - 对象查询、单位类管理和实体相关功能
"""
import os
import re
from ..lib.nofloat import to_int
from ..definitions import rules, get_ai_names, _raw_class_attr
from ..lib.nofloat import square_of_distance, int_distance
from ..worldunit import Building, Effect, Soldier, Unit, Worker, ground_or_air, has_target_type, matches_attack_targets
from ..worldresource import Deposit
from ..worldupgrade import Upgrade, is_an_upgrade
from ..worldskill import Skill
from ..worldbuff import Buff
from ..worlditem import Item
from ..worldorders import ORDERS_DICT
from ..worldplayerbase import A, Player

# 感知热点的 Cython 加速器；不可用时回退到纯 Python 列表推导
_pf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from ..worldplayerbase import perception_fast as _pf  # type: ignore[no-redef]
    except ImportError:
        _pf = None


class WorldObjectsMixin:
    """World对象管理混入类"""

    def get_objects(self, x, y, radius, filter=lambda x: True):
        radius_2 = radius * radius
        return [
            o
            for z in self.squares
            for o in z.objects
            if filter(o) and square_of_distance(x, y, o.x, o.y) <= radius_2
        ]

    def get_objects2(self, x, y, radius, filter=lambda x: True, players=None, skip_cache=False):
        if not players:
            players = self.players
        radius_2 = radius * radius
        # 热路径：Cython 加速距离过滤 + 可选 filter callback
        if _pf is not None:
            result = []
            for p in players:
                survivors = _pf.filter_in_radius_with_cb(
                    p._potential_neighbors(x, y, skip_cache=skip_cache),
                    x, y, radius_2, filter,
                )
                result.extend(survivors)
            return result
        return [
            o
            for p in players
            for o in p._potential_neighbors(x, y, skip_cache=skip_cache)
            if o.place is not None
               and filter(o)
               and square_of_distance(x, y, o.x, o.y) <= radius_2
        ]

    def can_harm(self, unit_type_name, other_type_name):
        try:
            return self.harm_target_types[(unit_type_name, other_type_name)]
        except:
            unit = rules.unit_class(unit_type_name)
            other = rules.unit_class(other_type_name)
            if other is None:
                result = False
            elif unit is None or not getattr(unit, "harm_target_type", None):
                result = True
            else:
                result = has_target_type(other, unit.harm_target_type)
            self.harm_target_types[(unit_type_name, other_type_name)] = result
            return result

    # Unit class management methods
    
    unit_base_classes = {
        "worker": Worker,
        "soldier": Soldier,
        "building": Building,
        "effect": Effect,
        "deposit": Deposit,
        "upgrade": Upgrade,
        "skill": Skill,
        "buff": Buff,
        "item": Item,
    }

    def unit_class(self, s):
        """Get a custom unit class from its name.
        
        Example: unit_class("peasant") to get the peasant class

        At the moment, unit_classes contains also: upgrades, abilities...
        """
        try:
            return rules.classes[s]
        except KeyError:
            return

    def _get_classnames(self, condition):
        result = []
        for c in rules.classnames():
            uc = self.unit_class(c)
            if uc is not None and condition(uc):
                result.append(c)
        return result

    def get_makers(self, t):
        def can_make(uc, t):
            rules_train = _raw_class_attr(uc, "_rules_can_train", None)
            if rules_train and t in rules_train:
                return True
            for a in ("can_build", "can_train", "can_upgrade_to", "can_research", "can_advance"):
                if t in _raw_class_attr(uc, a, ()):
                    return True
            for ability in _raw_class_attr(uc, "can_use", ()):
                effect = rules.get(ability, "effect")
                if effect and "summon" in effect[:1] and t in effect:
                    return True
            if getattr(uc, "morph_as_train", 0):
                if t in _raw_class_attr(uc, "can_change_to", ()):
                    return True

        if t.__class__ != str:
            t = t.__name__
        return self._get_classnames(lambda uc: can_make(uc, t))

    def get_units(self):
        return self._get_classnames(lambda uc: issubclass(uc.cls, Unit))

    def get_soldiers(self):
        return self._get_classnames(lambda uc: issubclass(uc.cls, Soldier))

    def get_deposits(self, resource_index):
        return self._get_classnames(
            lambda uc: issubclass(uc.cls, Deposit)
            and rules.parse_resource_type(uc.resource_type) == resource_index
        )

    @property
    def nb_res(self):
        return rules.get("parameters", "nb_of_resource_types", 2)

    # Graph methods for pathfinding
    
    def _ground_graph(self):
        g = {}
        for z in self.squares:
            for e in z.exits:
                g[e] = {}
                for f in z.exits:
                    if f is not e:
                        g[e][f] = int_distance(e.x, e.y, f.x, f.y)
                
                # 地面单位可以通过的条件：
                # 1. 两个方格都不是水区域（传统陆地连接）
                # 2. 或者两个方格都同时是is_water和is_ground（big_bridge等）
                target_square = e.other_side.place
                current_can_ground = not z.is_water or z.is_ground
                target_can_ground = not target_square.is_water or target_square.is_ground
                
                if current_can_ground and target_can_ground:
                    g[e][e.other_side] = 0
        return g

    def _air_graph(self):
        g = {}
        for z in self.squares:
            g[z] = {}
            if not z.is_air:
                continue
            # This is not perfect. Some diagonals will be missing.
            if [z2 for z2 in z.strict_neighbors if not z2.is_air]:
                n = z.strict_neighbors
            else:
                n = z.neighbors
            for z2 in n:
                if not z2.is_air:
                    continue
                g[z][z2] = int_distance(z.x, z.y, z2.x, z2.y)
        return g

    def _water_graph(self):
        g = {}
        for z in self.squares:
            g[z] = {}
            if not z.is_water:
                continue
            # This is not perfect. Some diagonals will be missing.
            if [z2 for z2 in z.strict_neighbors if not z2.is_water]:
                n = z.strict_neighbors
            else:
                n = z.neighbors
            for z2 in n:
                if not z2.is_water:
                    continue
                g[z][z2] = int_distance(z.x, z.y, z2.x, z2.y)
        return g

    def _create_graphs(self):
        self.g = {}
        self.g["ground"] = self._ground_graph()
        self.g["air"] = self._air_graph()
        self.g["water"] = self._water_graph()

    # Population and game management
    
    global_population_limit = 80  # Default value

    def populate_map(self, clients, random_starts=True, equivalents=False):
        # 确保有足够的起始位置
        overrides = getattr(self, "player_start_overrides", None) or {}
        if len(clients) > len(self.players_starts):
            # 如果客户端数量超过起始位置数量，使用非随机模式并重复使用起始位置
            from ..lib.log import warning
            warning("Not enough starting positions for all clients. Using non-random placement.")
            players_starts = (self.players_starts * ((len(clients) // len(self.players_starts)) + 1))[:len(clients)]
        elif overrides:
            # 混合分配：被 `player_start N <sq>` 锁定的 client（i = N-1）拿走
            # players_starts[i] 这个固定 slot；其余 client 在剩下的 slot 池里
            # 按 random_starts 的现行规则继续洗或顺序取。
            # 即使锁定的 N 超过 len(clients)，对应 slot 也会被"保留"
            # （不会被其他人抢走），保持地图作者的预期：那个格子是给"第 N 名"的。
            pinned_client_idxs = {N - 1 for N in overrides if N - 1 < len(clients)}
            pinned_slot_idxs = {N - 1 for N in overrides if N - 1 < len(self.players_starts)}
            remaining_slot_idxs = [
                i for i in range(len(self.players_starts)) if i not in pinned_slot_idxs
            ]
            unpinned_client_idxs = [
                i for i in range(len(clients)) if i not in pinned_client_idxs
            ]
            n_to_pick = min(len(remaining_slot_idxs), len(unpinned_client_idxs))
            if self.random_starts:
                chosen = self.random.sample(remaining_slot_idxs, n_to_pick)
            else:
                chosen = remaining_slot_idxs[:n_to_pick]
            players_starts = [None] * len(clients)
            for i in pinned_client_idxs:
                players_starts[i] = self.players_starts[i]
            for client_idx, slot_idx in zip(unpinned_client_idxs, chosen):
                players_starts[client_idx] = self.players_starts[slot_idx]
            # 兜底：理论上 n_to_pick 已经够，但万一 slot 不够（比如有人写
            # nb_players_max > 实际 slot 数）也不至于让某个 client 拿 None。
            for i in range(len(clients)):
                if players_starts[i] is None:
                    from ..lib.log import warning
                    warning(
                        "populate_map: client %d has no spawn slot; "
                        "fallback to players_starts[0]" % i
                    )
                    players_starts[i] = self.players_starts[0] if self.players_starts else None
        elif self.random_starts and len(clients) <= len(self.players_starts):
            players_starts = self.random.sample(self.players_starts, len(clients))
        else:
            players_starts = self.players_starts[:len(clients)]
        for client in clients:
            client.create_player(self)
        for computer_start in self.computers_starts:
            # 检查是否指定了neutral标志
            # 默认 False = 敌对，与 world_map.py 的解析默认保持一致。
            # 注：当前 _add_start 总会写第 4 位，所以这条 fallback 几乎只是兜底；
            # 仍同步改成 False，避免哪天另一条路径漏写后悄悄变成中立。
            neutral = False
            if len(computer_start) >= 4:
                neutral = computer_start[3]
            from ..worldclient import DummyClient
            from ..worldplayerbase.base import computer_start_is_wildlife_only

            # 狩猎动物独占一个 computer_only 槽位：不加入 alliance "ai"，
            # 在引擎里不与任何其它电脑结盟。
            alliance = (
                None
                if computer_start_is_wildlife_only(computer_start)
                else "ai"
            )
            DummyClient(neutral=neutral, alliance=alliance).create_player(self)
        
        # 初始化所有玩家的联盟（在所有玩家创建后）
        for player in self.players:
            player.init_alliance()
        
        from itertools import chain
        starts = list(chain(players_starts, self.computers_starts))

        # 按阵营构造默认起始（只对缺少玩家起始单位/资源的情况进行回退）
        # 规则侧格式：
        #   def <faction>
        #   class faction
        #   starting_units ...
        #   starting_resources ...
        def _build_default_start_for_faction(faction_name, square_name=None):
            # 读取规则中该阵营的 starting_resources 与 starting_units
            # resources 是数字列表；units 是扁平字符串列表
            res_from_rules = rules.get(faction_name, "starting_resources")
            units_from_rules = rules.get(faction_name, "starting_units")

            # 规范化资源长度
            resources = []
            if res_from_rules:
                try:
                    resources = [to_int(c) for c in res_from_rules]
                except Exception:
                    resources = []
            resources = rules.normalized_cost_or_resources(resources or [])

            # units 列表解析为与 _add_start_to 相同的格式：[(sq, unit_cls, multiplicator)]
            # 如果提供 square_name，则将单位放在该起始格
            # 若未提供，尝试回退到地图的第一个 starting_square；再不行选任一格
            if not square_name:
                if self.starting_squares:
                    square_name = self.starting_squares[0]
                else:
                    # 选用任意一个方格名（grid 的键中含有 "x,y" 字符串）
                    for key in self.grid.keys():
                        if isinstance(key, str) and "," in key:
                            square_name = key
                            break
            start_units = []
            multiplicator = 1
            if units_from_rules:
                for token in units_from_rules:
                    if isinstance(token, str) and token.startswith("-"):
                        start_units.append([None, token, None])
                    elif isinstance(token, str) and re.match("^[0-9]+$", token):
                        multiplicator = int(token)
                    else:
                        unit_cls = rules.unit_class(token)
                        if unit_cls is not None:
                            start_units.append((square_name, unit_cls, multiplicator))
                        multiplicator = 1

            # 触发器为空
            return [resources, start_units, []]

        # 针对每个“玩家”（不包括地图定义的 computer_only）进行逐个回退：
        # 条件：
        # - 地图未显式定义 starting_units（全局），并且该玩家的起始单位列表为空，则用阵营默认 starting_units
        # - 地图未显式定义 starting_resources（全局），则用阵营默认 starting_resources
        # 这样即使地图定义了 computer_only，也不会阻止玩家使用阵营默认开局。
        for idx, player in enumerate(self.players):
            if idx >= len(players_starts):
                # 后续的是计算机阵营（来自 computers_starts 的 DummyClient），不改动
                continue
            # 获取该玩家当前的起始定义
            current_start = starts[idx]
            current_resources = current_start[0] if len(current_start) >= 1 else []
            current_units = current_start[1] if len(current_start) >= 2 else []

            # 确定该玩家的首选起始落点
            square_for_player = None
            # 若已有单位条目中带有坐标，沿用该坐标
            for item in current_units:
                if isinstance(item, (list, tuple)) and item and item[0]:
                    square_for_player = item[0]
                    break
            # 否则回退到 starting_squares 的第 idx 个
            if not square_for_player and idx < len(self.starting_squares):
                square_for_player = self.starting_squares[idx]

            # 如需回退则构造默认起始
            need_units_default = (not self.map_defined_starting_units) and (len(current_units) == 0)
            # 仅当地图未显式定义全局起始资源，且该玩家条目本身未提供资源时，才回退到规则默认
            need_resources_default = (not self.map_defined_starting_resources) and (len(current_resources) == 0)

            if need_units_default or need_resources_default:
                default_start = _build_default_start_for_faction(player.faction, square_for_player)
                # 组装新的起始：
                # 资源：若需回退则替换；否则保留地图值
                new_resources = default_start[0] if need_resources_default else current_resources
                # 单位：若需回退则替换；否则保留地图值
                new_units = default_start[1] if need_units_default else current_units
                # 触发器保持不变
                new_triggers = current_start[2] if len(current_start) >= 3 else []
                starts[idx] = [new_resources, new_units, new_triggers]

        for player, start in zip(self.players, starts):
            parsed_start = self.parse_start(start, player.faction, equivalents)
            player.init_position(parsed_start)
        
        # 在单位创建后再次确保联盟正确设置
        self.update_alliances()

    def parse_start(self, start, faction, must_apply_equivalent_type):
        from .world_core import start_population_bonus

        resources = rules.normalized_cost_or_resources(start[0])
        units, upgrades, forbidden_techs = self.parse_assets(start, faction, must_apply_equivalent_type)
        triggers = start[2]
        population_bonus = start_population_bonus(start)
        return units, upgrades, forbidden_techs, resources, triggers, population_bonus

    def parse_assets(self, start, faction, must_apply_equivalent_type):
        units = []
        upgrades = []
        forbidden_techs = []
        for place, type_, n in start[1]:
            if must_apply_equivalent_type:
                type_ = rules.equivalent_type(type_, faction)
            if isinstance(type_, str) and type_[0:1] == "-":
                forbidden_techs.append(type_[1:])
            elif is_an_upgrade(type_):
                upgrades.append(
                    type_.type_name
                )  # type_.upgrade_player(self) would require the units already there
            elif not type_:
                from ..lib.log import warning
                warning("couldn't create an initial unit")
            else:
                place = self.grid[place]
                units.append((place, n, type_))
        return units, upgrades, forbidden_techs