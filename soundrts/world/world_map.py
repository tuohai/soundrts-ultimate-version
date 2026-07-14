"""
World地图管理模块 - 地图解析、构建、保存和相关功能
"""
import re
import string
from ..definitions import rules, get_ai_names
from ..lib.defs import preprocess
from ..lib.log import warning
from ..lib.nofloat import PRECISION, int_distance, to_int
from ..lib.resource import res
from ..worldentity import COLLISION_RADIUS
from ..worldexit import passage
from ..worldorders import ORDERS_DICT
from ..worldplayerbase import Player
from ..worldresource import create_building_land
from ..worldroom import Square
from ..lib import collision
from ..lib.map_tokens import expand_deposit_plurals
from ..lib.subcell_terrain import (
    DEFAULT_SUBCELL_PRECISION,
    MAX_SUBCELL_PRECISION,
    MIN_SUBCELL_PRECISION,
    parse_location_token,
    format_subcell_suffix,
)

class WorldMapMixin:
    """World地图管理混入类"""

    starting_population = 0
    map_defined_starting_population = False

    # --- 新增: 坐标标准化工具 ---
    def _normalize_square_token(self, token):
        """将坐标标准化为"x,y"字符串。

        规则:
        - 已是 x,y 或 (x,y) -> 解析为整数后返回 "x,y"
        - 旧式 a1/a12/a... -> 转换为 0 基的 "x,y"，其中列按 26 进位字母序转换
        - 否则原样返回
        """
        if not isinstance(token, str):
            return token
        t = token.strip()
        # 去掉包裹的小括号
        if t.startswith("(") and t.endswith(")"):
            t = t[1:-1].strip()
        # x,y -> 解析为1基坐标并转换为内部使用的0基字符串
        if "," in t:
            parts = t.split(",")
            if len(parts) == 2:
                try:
                    col_1based = int(parts[0].strip())
                    row_1based = int(parts[1].strip())
                    # 转换为0基
                    col_0based = col_1based - 1
                    row_0based = row_1based - 1
                    return f"{col_0based},{row_0based}"
                except ValueError:
                    return token
        # 旧式 a1/a12/a... -> 转换为 x,y（排除 rules 里已定义的单位名，如 dragon2、raynor7）
        if re.match(r"^[a-z]+[0-9]+$", t) and rules.unit_class(t) is None:
            letters = ''.join([c for c in t if c.isalpha()])
            digits = ''.join([c for c in t if c.isdigit()])
            # 将字母部分按 26 进制转换（a->1, b->2 ... aa->27），再统一转为 0 基
            col = 0
            for ch in letters:
                col = col * 26 + (ord(ch) - ord('a') + 1)
            col -= 1
            try:
                row = int(digits) - 1
            except ValueError:
                return token
            return f"{col},{row}"
        return token

    def _normalize_square_list(self, tokens):
        out = []
        for t in tokens:
            if isinstance(t, str) and rules.unit_class(t) is not None:
                out.append(t)
            else:
                out.append(self._normalize_square_token(t))
        return out

    def _parse_terrain_location_tokens(self, tokens, line, command):
        """Parse square or square/sub_x,sub_y tokens for terrain commands."""
        from .world_core import check_squares, map_warning

        result = []
        for tok in tokens:
            alias = self.name_to_square.get(tok, tok)
            try:
                raw_square, subcell = parse_location_token(alias)
                square_key = self._normalize_square_token(raw_square)
            except ValueError as exc:
                map_warning(line, "%s: %s" % (command, exc))
                continue
            if subcell is None:
                check_squares(line, [square_key])
            result.append((square_key, subcell))
        return result

    def _apply_subcell_overlays(self):
        precision = getattr(self, "subcell_precision", DEFAULT_SUBCELL_PRECISION)

        def _valid_cell(cell):
            if cell[0] >= precision or cell[1] >= precision:
                warning(
                    "sub-cell (%d,%d) out of range for subcell_precision %d"
                    % (cell[0] + 1, cell[1] + 1, precision)
                )
                return False
            return True

        for square_key, cells in self.sub_high_grounds.items():
            square = self.grid.get(square_key)
            if square is None:
                continue
            for cell in cells:
                if _valid_cell(cell):
                    square.subcells.set_high_ground(cell[0], cell[1], True)
        for (square_key, cell), t in self.sub_terrain.items():
            square = self.grid.get(square_key)
            if square is not None and _valid_cell(cell):
                from ..lib.square_terrain_rules import (
                    apply_terrain_map_flags,
                    resolve_terrain_cover,
                    resolve_terrain_speed,
                )

                square.subcells.set_type_name(cell[0], cell[1], t)
                apply_terrain_map_flags(square, t, cell[0], cell[1])
                square.subcells.set_terrain_speed(
                    cell[0],
                    cell[1],
                    resolve_terrain_speed(t, self.sub_terrain_speed.get((square_key, cell))),
                )
                square.subcells.set_terrain_cover(
                    cell[0],
                    cell[1],
                    resolve_terrain_cover(t, self.sub_terrain_cover.get((square_key, cell))),
                )
        for (square_key, cell), t in self.sub_terrain_speed.items():
            if (square_key, cell) in self.sub_terrain:
                continue
            square = self.grid.get(square_key)
            if square is not None and _valid_cell(cell):
                square.subcells.set_terrain_speed(cell[0], cell[1], t)
        for (square_key, cell), t in self.sub_terrain_cover.items():
            if (square_key, cell) in self.sub_terrain:
                continue
            square = self.grid.get(square_key)
            if square is not None and _valid_cell(cell):
                square.subcells.set_terrain_cover(cell[0], cell[1], t)
        for square_key, cells in self.sub_water.items():
            square = self.grid.get(square_key)
            if square is None:
                continue
            for cell in cells:
                if _valid_cell(cell):
                    square.subcells.set_is_water(cell[0], cell[1], True)
        for square_key, cells in self.sub_ground.items():
            square = self.grid.get(square_key)
            if square is None:
                continue
            for cell in cells:
                if _valid_cell(cell):
                    square.subcells.set_is_ground(cell[0], cell[1], True)
        for square_key, cells in self.sub_no_air.items():
            square = self.grid.get(square_key)
            if square is None:
                continue
            for cell in cells:
                if _valid_cell(cell):
                    square.subcells.set_is_air(cell[0], cell[1], False)

    def _queue_dynamic_terrain_spawns(self):
        """Queue objects implied by dynamic ``terrain`` via ``square_terrain``."""
        from ..lib.square_terrain_rules import (
            terrain_deposit_spawn_qty,
            terrain_is_dynamic,
            terrain_map_object_spawns,
            terrain_object_spawn_kind,
        )

        self.terrain_building_land = []
        self.terrain_map_units = []
        for square_key, terrain_name in self.terrain.items():
            if not terrain_is_dynamic(terrain_name):
                continue
            for obj_type, count in terrain_map_object_spawns(terrain_name).items():
                kind = terrain_object_spawn_kind(obj_type)
                if kind == "building_land":
                    for _ in range(count):
                        self.terrain_building_land.append((square_key, obj_type))
                elif kind == "deposit":
                    qty = terrain_deposit_spawn_qty(obj_type)
                    for _ in range(count):
                        self.map_objects.append([square_key, obj_type, qty])
                elif kind == "unit":
                    self.terrain_map_units.append((square_key, obj_type, count))

    def _ensure_map_terrain_player(self):
        player = getattr(self, "_map_terrain_player", None)
        if player is not None and player in getattr(self, "players", []):
            return player
        from ..worldclient import DummyClient

        client = DummyClient(neutral=True, alliance=None)
        client.create_player(self)
        self._map_terrain_player = client.player
        return self._map_terrain_player

    def _spawn_terrain_map_units(self):
        units = getattr(self, "terrain_map_units", None) or []
        if not units:
            return
        player = self._ensure_map_terrain_player()
        for square_key, obj_type, count in units:
            if square_key not in self.grid:
                continue
            entity_class = rules.unit_class(obj_type)
            if entity_class is None:
                continue
            square = self.grid[square_key]
            for _ in range(count):
                player.add_unit(entity_class, square)

    def _create_squares_and_grid(self):
        from ..lib.square_terrain_rules import (
            apply_terrain_map_flags,
            resolve_terrain_cover,
            resolve_terrain_speed,
            terrain_is_dynamic,
        )

        self.grid = {}
        for col in range(self.nb_columns):
            for row in range(self.nb_lines):
                square = Square(self, col, row, self.square_width)
                # 名称键直接用 "x,y" 字符串
                self.grid[square.name] = square
                # 同时保留 (col,row) 作为索引
                self.grid[(col, row)] = square
                square.high_ground = square.name in self.high_grounds
                terrain_name = self.terrain.get(square.name)
                if terrain_name:
                    apply_terrain_map_flags(square, terrain_name)
                    if not terrain_is_dynamic(terrain_name):
                        square.type_name = terrain_name
                        square.fixed_terrain = True
                square.terrain_speed = resolve_terrain_speed(
                    terrain_name,
                    self.terrain_speed.get(square.name),
                )
                square.terrain_cover = resolve_terrain_cover(
                    terrain_name,
                    self.terrain_cover.get(square.name),
                )
                if square.name in self.water_squares:
                    square.is_water = True
                    square.is_ground = square.name in self.ground_squares
                if square.name in self.no_air_squares:
                    square.is_air = False
        self._apply_subcell_overlays()
        xmax = self.nb_columns * self.square_width
        res = COLLISION_RADIUS * 2 // 3
        self.collision = {
            "ground": collision.CollisionMatrix(xmax, res),
            "air": collision.CollisionMatrix(xmax, res),
        }
        self.collision["water"] = self.collision["ground"]

    @staticmethod
    def _nb_by_square_land_type(keyword):
        from ..worldresource import nb_by_square_land_type

        return nb_by_square_land_type(keyword)

    def _sync_map_building_land_default(self):
        """Infer ``world.building_land`` from map keywords when the map omits ``building_land``."""
        if getattr(self, "_map_building_land_explicit", False):
            return
        nb = getattr(self, "nb_building_land_by_square", None) or {}
        if len(nb) == 1:
            self.building_land = next(iter(nb.keys()))

    def _building_land_placements(self):
        placements = []
        default_type = getattr(self, "building_land", "meadow")
        nb_by_square = getattr(self, "nb_building_land_by_square", {})
        for square in sorted([x for x in list(self.grid.keys()) if isinstance(x, str)]):
            placements.extend([(square, default_type)] * self.nb_meadows_by_square)
            for land_type, count in nb_by_square.items():
                placements.extend([(square, land_type)] * count)
        placements.extend((square, "meadow") for square in self.additional_meadows)
        placements.extend(
            (square, "build_site") for square in self.additional_build_sites
        )
        placements.extend(getattr(self, "terrain_building_land", []))
        placements.extend(getattr(self, "additional_building_land", []))
        counts = {}
        for square, land_type in placements:
            counts[(square, land_type)] = counts.get((square, land_type), 0) + 1
        for square in self.remove_meadows:
            key = (square, "meadow")
            if key in counts:
                counts[key] -= 1
                if counts[key] <= 0:
                    del counts[key]
        result = []
        for (square, land_type), count in counts.items():
            result.extend([(square, land_type)] * count)
        return result

    def _meadows(self):
        return [square for square, land_type in self._building_land_placements() if land_type == "meadow"]

    def _deposit_spawn_totals(self):
        totals = {}
        for z, cls, _n in self.map_objects:
            if z not in self.grid:
                continue
            if rules.get(cls, "class") == ["item"]:
                continue
            totals[(z, cls)] = totals.get((z, cls), 0) + 1
        return totals

    def _create_resources(self):
        deposit_totals = self._deposit_spawn_totals()
        deposit_index = {}
        for z, cls, n in self.map_objects:
            # 检查坐标有效性
            if z not in self.grid:
                warning(f"{z} is not a valid coordinate")
                continue
                
            # 获取实体类型的类定义
            try:
                entity_class = rules.unit_class(cls)
                if not entity_class:
                    warning(f"unknown entity type: {cls}")
                    continue
                
                # 检查是否可以放置地面实体
                if self.grid[z].can_receive("ground"):  # avoids using the spiral
                    # 判断是物品还是资源
                    if rules.get(cls, "class") == ["item"]:
                        # 根据数量参数创建多个物品实例
                        quantity = n if n is not None else 1
                        for i in range(quantity):
                            # 为了避免物品完全重叠，稍微偏移位置
                            offset_x = (i % 3 - 1) * 100  # -100, 0, 100毫米偏移
                            offset_y = (i // 3 - 1) * 100 
                            
                            # 创建物品实例，稍微偏移位置
                            item = entity_class(self.grid[z], 
                                               self.grid[z].x + offset_x, 
                                               self.grid[z].y + offset_y)
                            # 物品不需要建筑用地
                    else:
                        square = self.grid[z]
                        key = (z, cls)
                        total = deposit_totals.get(key, 1)
                        idx = deposit_index.get(key, 0)
                        deposit_index[key] = idx + 1
                        if total > 1 and self.time == 0:
                            x, y = square.deposit_arrange_xy(idx, total)
                            resource = entity_class.__new__(entity_class)
                            resource.collision = 0
                            resource.__init__(
                                square, n if n is not None else 0, x, y
                            )
                        else:
                            x, y = square.find_free_space(
                                "ground", square.x, square.y
                            )
                            if x is None:
                                warning(f"no space for {cls} on {z}")
                                continue
                            resource = entity_class(
                                square, n if n is not None else 0, x, y
                            )

                        # 设置建筑用地
                        resource.building_land = create_building_land(self.grid[z])
                        resource.building_land.delete()
            except Exception as e:
                warning(f"couldn't create entity {cls}: {e}")
                continue

        for z, land_type in self._building_land_placements():
            create_building_land(self.grid[z], type_name=land_type)

    def _arrange_resources_symmetrically(self):
        xc = self.nb_columns * 10 // 2
        yc = self.nb_lines * 10 // 2
        for z in self.squares:
            z.arrange_resources_symmetrically(xc, yc)

    def _create_we_passage(self, i, exit_type):
        is_a_portal = False
        # i 和 j 都是 "x,y" 字符串
        cx, cy = [int(x) for x in i.split(',')]
        col = cx + 1
        if col == self.nb_columns:
            col = 0
            is_a_portal = True
        j = f"{col},{cy}"
        if j not in self.grid:
            from .world_core import map_warning
            map_warning("", f"couldn't create a west-east passage from {i} to {j}")
        else:
            passage(
                (self.grid[i].east_side(), self.grid[j].west_side(), is_a_portal),
                exit_type,
            )

    def _create_sn_passage(self, i, exit_type):
        is_a_portal = False
        cx, cy = [int(x) for x in i.split(',')]
        line = cy + 1
        if line == self.nb_lines:
            line = 0
            is_a_portal = True
        j = f"{cx},{line}"
        if j not in self.grid:
            from .world_core import map_warning
            map_warning("", f"couldn't create a south-north passage from {i} to {j}")
        else:
            passage(
                (self.grid[i].north_side(), self.grid[j].south_side(), is_a_portal),
                exit_type,
            )

    def _create_passages(self):
        for t, squares in self.west_east:
            for i in squares:
                self._create_we_passage(i, t)
        for t, squares in self.south_north:
            for i in squares:
                self._create_sn_passage(i, t)

    def _build_map(self):
        self._queue_dynamic_terrain_spawns()
        self._create_squares_and_grid()
        self._create_resources()
        self._spawn_terrain_map_units()
        self._arrange_resources_symmetrically()
        self._create_passages()
        self._create_graphs()
        self._update_all_auto_terrain()

    def _update_all_auto_terrain(self):
        for s in self.squares:
            if not getattr(s, "fixed_terrain", False):
                s.update_terrain()

    def _strip_population_from_items(self, items):
        population = 0
        filtered = []
        i = 0
        while i < len(items):
            token = items[i]
            if (
                token == "population"
                and i + 1 < len(items)
                and re.match("^[0-9]+$", str(items[i + 1]))
            ):
                population = int(items[i + 1])
                i += 2
            else:
                filtered.append(token)
                i += 1
        return filtered, population

    def _add_start_to(self, starts, resources, items, sq=None, neutral=None, population=0):
        items, from_items = self._strip_population_from_items(list(items))
        if from_items:
            population = from_items

        def is_a_square(x):
            if not isinstance(x, str):
                return False
            x = x.strip()
            # 新格式: x,y（允许空格）
            if re.match(r"^\s*-?\d+\s*,\s*-?\d+\s*$", x):
                return True
            # 兼容旧格式: a1/a12
            return (
                len(x) >= 2
                and x[0] in string.ascii_letters
                and x[1:].isdigit()
            )

        start = []
        multiplicator = 1
        for x in items:
            if is_a_square(x):
                sq = x
                multiplicator = 1
            elif x[0] == "-":
                start.append([None, x, None])
            elif re.match("[0-9]+$", x):
                multiplicator = int(x)
            else:
                start.append((sq, rules.unit_class(x), multiplicator))
                multiplicator = 1
        
        # 添加neutral / population 信息到 start 数据中
        start_data = [resources, start, []]
        if neutral is not None:
            start_data.append(neutral)
        if population:
            start_data.append(population)
        starts.append(start_data)

    def _add_start(self, w, words):
        if w == "player":
            n = "players_starts"
        else:
            n = "computers_starts"
        from .world_core import convert_and_split_first_numbers
        resources, units = convert_and_split_first_numbers(words[1:])
        if len(resources) != self.nb_res:
            warning("the map have %s resources while the rules have %s resources",
                 len(resources), self.nb_res)
        
        # 检查是否为computer_only并且指定了neutral标志
        # 默认 = False（敌对 AI），等价于显式 `non_neutral`。
        # 这与 doc_src/src/en/mapmaking.rst 第 223 行
        # "This AI will be hostile to any other player or AI."
        # 的文档承诺一致；要变中立 creep 必须显式写 `neutral`。
        neutral = False
        if w in ["computer_only", "computer"]:
            # 检查units中是否有"neutral"或"non_neutral"标志
            if "non_neutral" in units:
                neutral = False
                units = [u for u in units if u != "non_neutral"]
            elif "neutral" in units:
                neutral = True
                units = [u for u in units if u != "neutral"]
        units, population = self._strip_population_from_items(units)

        start_info = [resources, units]
        if w in ["computer_only", "computer"]:
            start_info.append(neutral)  # 添加neutral标志
        
        # ``_add_start_to`` 的签名是 ``(starts, resources, items, sq=None,
        # neutral=None, population=0)``——第 4 个位置参数是 ``sq``，不是 ``neutral``。
        # 历史上这里把 ``neutral`` 当第 4 个位置参数传，结果落到了 ``sq``
        # 上，``neutral`` 永远是 ``None``——``start_data`` 永远只有 3 项，
        # ``world_objects.populate_map`` 的 ``len >= 4`` 检查永远失败，
        # 于是所有 ``computer_only ...`` 行（包括 ``non_neutral`` 标记）
        # 在引擎眼里都成了中立电脑。修复：用关键字传 ``neutral=``。
        # 影响范围：``res/multi/td2/map.txt`` 里那两条 ``non_neutral``
        # corner-base 现在会真正成为非中立 AI，匹配该地图的触发器设计
        # （`trigger computer1 (alliance 1)` 等）。战役地图全都没写
        # ``non_neutral``，行为完全不变。
        self._add_start_to(
            getattr(self, n),
            start_info[0],
            start_info[1],
            neutral=neutral if len(start_info) > 2 else None,
            population=population,
        )

    def _apply_player_start_overrides(self, starting_resources):
        """把 ``player_start N <sq>`` 的指令落到 ``players_starts[N-1]`` 上。

        必须在 ``starting_squares`` 已展开到 ``players_starts`` 之后调用。

        策略：
        - 如果 ``players_starts`` 不足 N 项，按需用全局 ``starting_units``/
          ``starting_resources`` 在 override 格创建新 slot 补齐——等价于
          "把 <sq> 当作隐式的 starting_square 追加进来"。
        - 否则就地把 ``players_starts[N-1]`` 里所有 ``(sq, cls, mult)``
          单位条目的格子改写成 override 格。资源、触发器、neutral 标记保留，
          因此 ``trigger playerN ...`` 这类已经按位置挂上的触发器不会丢。
        - ``populate_map`` 看到 ``player_start_overrides`` 非空时，
          会把这些 slot pin 给对应 client，绕过 random_starts 的洗牌。
        """
        if not self.player_start_overrides:
            return
        for n_idx in sorted(self.player_start_overrides):
            override = self.player_start_overrides[n_idx]
            if isinstance(override, dict):
                # 完整式：player_start N <resources...> <square> <units...>
                # 像 `player` 行那样重建整个 slot（资源 + 单位 + 出生格），
                # 然后 pin 给第 N 个 client。
                resources = override.get("resources") or []
                items = override.get("items") or []
                # 主出生格 = items 里第一个方格，用于补齐中间缺失的 slot。
                pad_sq = None
                for t in items:
                    if isinstance(t, str) and re.match(r"^-?\d+\s*,\s*-?\d+$", t):
                        pad_sq = t
                        break
                while len(self.players_starts) < n_idx:
                    self._add_start_to(
                        self.players_starts,
                        starting_resources,
                        self.starting_units,
                        pad_sq,
                        population=self.starting_population,
                    )
                # 复用 _add_start_to 的解析语义构建完整 slot。
                built_list = []
                self._add_start_to(built_list, resources, items)
                built = built_list[0]
                existing = self.players_starts[n_idx - 1]
                # 触发器此刻还没挂上（在 _parse_map 末尾才 _add_trigger），
                # 但仍保留已有 slot 的触发器列表引用以防万一。
                triggers = (
                    existing[2]
                    if isinstance(existing, list) and len(existing) >= 3
                    else []
                )
                self.players_starts[n_idx - 1] = [built[0], built[1], triggers]
                if len(built) >= 4 and isinstance(built[3], bool):
                    self.players_starts[n_idx - 1].append(built[3])
                from .world_core import start_population_bonus
                pop = start_population_bonus(built)
                if pop:
                    self.players_starts[n_idx - 1].append(pop)
                continue
            sq = override
            # 补齐到长度 == n_idx 的 slot 数量
            while len(self.players_starts) < n_idx:
                self._add_start_to(
                    self.players_starts,
                    starting_resources,
                    self.starting_units,
                    sq,
                    population=self.starting_population,
                )
            slot = self.players_starts[n_idx - 1]
            # slot 结构：[resources, units, triggers, (neutral)]
            if len(slot) >= 2 and isinstance(slot[1], list):
                rewritten = []
                for item in slot[1]:
                    if isinstance(item, tuple) and len(item) == 3:
                        rewritten.append((sq, item[1], item[2]))
                    else:
                        # 例如 [None, "-tech", None] 这种禁用条目原样保留
                        rewritten.append(item)
                slot[1] = rewritten

    def _list_to_tree(self, words):
        # 预处理：标记和保留引号内的文本
        i = 0
        while i < len(words):
            word = words[i]
            # 确保word是字符串
            if isinstance(word, str):
                if word.startswith('"') and not word.endswith('"'):
                    # 开始一个引号字符串，但不在同一个单词结束
                    j = i + 1
                    # 寻找结束引号
                    while j < len(words) and isinstance(words[j], str) and not words[j].endswith('"'):
                        j += 1
                    
                    if j < len(words) and isinstance(words[j], str):  # 找到了结束引号
                        # 合并引号内的所有单词
                        merged = ' '.join(words[i:j+1])
                        words[i:j+1] = [merged]  # 替换为合并后的字符串
            i += 1
            
        # 现在像以前一样构建树结构
        cache = [[]]
        for w in words:
            if w == "(":
                cache.append([])
            elif w == ")":
                cache[-2].append(cache.pop())
            else:
                cache[-1].append(w)
        return cache[0]

    def _add_trigger(self, words):
        owners, condition, action = self._list_to_tree(words)
        if isinstance(owners, str):
            owners = [owners]
        for o in owners:
            if o == "computers":
                for s in self.computers_starts:
                    s[2].append([condition, action])
            elif o == "players":
                for s in self.players_starts:
                    s[2].append([condition, action])
            elif o == "all":
                for s in self.computers_starts + self.players_starts:
                    s[2].append([condition, action])
            elif o.startswith("computer") and o != "computers":
                match = re.match(r"^computer(\d+)$", o)
                if match:
                    try:
                        self.computers_starts[int(match.group(1)) - 1][2].append(
                            [condition, action]
                        )
                    except IndexError:
                        from .world_core import map_warning
                        map_warning("trigger " + " ".join(words), "%s is unknown" % o)
                else:
                    from .world_core import map_warning
                    map_warning("trigger " + " ".join(words), "%s is unknown" % o)
            elif o.startswith("player") and o != "players":
                match = re.match(r"^player(\d+)$", o)
                if match:
                    try:
                        self.players_starts[int(match.group(1)) - 1][2].append(
                            [condition, action]
                        )
                    except IndexError:
                        from .world_core import map_warning
                        map_warning("trigger " + " ".join(words), "%s is unknown" % o)
                else:
                    from .world_core import map_warning
                    map_warning("trigger " + " ".join(words), "%s is unknown" % o)
            else:
                from .world_core import map_warning
                map_warning("trigger " + " ".join(words), "%s is unknown" % o)

    def random_choice_repl(self, matchobj):
        return self.random.choice(matchobj.group(1).split("\n#end_choice\n"))

    def _parse_map(self, map_definition):
        from .world_core import check_squares, map_error, map_warning
        
        triggers = []
        starting_resources = [0 for _ in range(self.nb_res)]

        squares_words = [
            "starting_squares",
            "additional_meadows",
            "additional_build_sites",
            "remove_meadows",
        ]

        s = map_definition  # "universal newlines"
        s = preprocess(s)
        s = s.replace("(", " ( ")
        s = s.replace(")", " ) ")
        s = re.sub(r"\s*\n\s*", r"\n", s)  # strip lines
        s = re.sub(
            r"(?ms)^#random_choice\n(.*?)\n#end_random_choice$",
            self.random_choice_repl,
            s,
        )
        s = expand_deposit_plurals(s)
        s = re.sub(r"(south_north|west_east)_paths", r"\1 path", s)
        s = re.sub(r"(south_north|west_east)_bridges", r"\1 bridge", s)
        
        # 预处理触发器，保存引号内的文本
        quoted_texts = {}
        quoted_index = 0
        
        def replace_quoted(match):
            nonlocal quoted_index
            text_id = f"__QUOTED_TEXT_{quoted_index}__"
            quoted_texts[text_id] = match.group(0)
            quoted_index += 1
            return text_id
        
        # 保存所有引号内的文本
        s = re.sub(r'"[^"]*"', replace_quoted, s)
        
        for line in s.split("\n"):  # TODO: error msg
            words = line.strip().split()
            if not words:
                continue  # empty line
            w = words[0]
            if w[0:1] == ";":
                continue  # comment
                
            # 还原引号内的文本
            restored_words = []
            for word in words:
                if word in quoted_texts:
                    restored_words.append(quoted_texts[word])
                else:
                    restored_words.append(word)
            
            # 处理restored_words列表
            for i, _w in enumerate(restored_words[1:], 1):
                if w in ["south_north", "west_east", "terrain", "speed", "cover",
                         "high_grounds", "water", "ground", "no_air"]:
                    continue  # TODO: check that the exit type_name is defined in style
                for _w in _w.split(","):
                    if _w and _w[0] == "-":
                        _w = _w[1:]
                    # 如果是引号括起来的字符串，直接跳过验证
                    if _w.startswith('"') and _w.endswith('"'):
                        continue
                    # 检查是否是临时替换的引号文本ID
                    if _w in quoted_texts:
                        continue
                    # 允许数字坐标格式 x,y 或 (x,y)
                    if re.match(r"^\(?\s*\d+\s*,\s*\d+\s*\)?$", _w):
                        continue
                    if (
                            # 允许a-z+数字、纯数字、以及开头是字母或中文的Unicode字符串 
                            re.match("^([a-z]+[0-9]+|[0-9]+(.[0-9]*)?|.[0-9]+|[a-zA-Z\u4e00-\u9fff].*)$", _w)
                            is None
                            and not hasattr(Player, "lang_" + _w)
                            and _w not in rules.classnames()
                            and _w not in get_ai_names()
                            and _w not in ["(", ")", "all", "players", "computers", "="]
                            and _w not in ORDERS_DICT
                    ):
                        # 如果包含中文字符，则不触发警告
                        if any('\u4e00' <= c <= '\u9fff' for c in _w):
                            continue
                        else:
                            map_warning(line, "unknown: %s" % _w)
                            
            # 还原原始命令行用于后续处理，但保持引号内文本完整
            words = restored_words
            
            if w in ["title", "objective", "intro", "cut_scene"]:
                # 支持等号格式：title = ID 或 title = 文本内容
                if len(words) >= 2 and words[1] == "=":
                    # 跳过等号，只使用后面的参数
                    params = words[2:]
                else:
                    # 保持原有格式：title ID
                    params = words[1:]
                
                # 检查是否使用双引号格式
                if params and params[0].startswith('"') and params[-1].endswith('"'):
                    # 双引号格式，作为一个整体处理并去掉引号
                    content = " ".join(params)
                    content = content.strip('"')  # 去掉首尾引号
                    setattr(self, w, [content])
                # 检查是否包含中文字符
                elif params and any('\u4e00' <= c <= '\u9fff' for c in " ".join(params)):
                    # 包含中文字符，作为一个整体处理
                    content = " ".join(params)
                    setattr(self, w, [content])
                else:
                    # 按原来的方式处理，尝试转换为整数（用于ID引用）
                    try:
                        setattr(self, w, [int(x) for x in params])
                    except ValueError:
                        # 如果无法转换为整数，则保留为字符串列表
                        setattr(self, w, params)
            elif w in [
                "square_width",
                "subcell_precision",
                "nb_rows",
                "nb_columns",
                "nb_lines",
                "nb_players_min",
                "nb_players_max",
                "scenario",
                "nb_meadows_by_square",
                "global_population_limit",
                "timer_coefficient",
                "random_starts",
                "merge_default_triggers",
                "random_map",
            ]:
                try:
                    setattr(self, w, int(words[1]))
                    if w == "subcell_precision":
                        if self.subcell_precision < MIN_SUBCELL_PRECISION:
                            map_error(
                                line,
                                "subcell_precision must be >= %d"
                                % MIN_SUBCELL_PRECISION,
                            )
                        elif self.subcell_precision > MAX_SUBCELL_PRECISION:
                            map_error(
                                line,
                                "subcell_precision must be <= %d"
                                % MAX_SUBCELL_PRECISION,
                            )
                    if w == "nb_rows":
                        self.nb_columns = self.nb_rows
                        warning("nb_rows is deprecated, use nb_columns instead")
                except:
                    map_error(line, "%s must be an integer" % w)
            elif (land_type := self._nb_by_square_land_type(w)) is not None:
                from ..worldresource import (
                    building_land_types,
                    normalize_building_land_type_name,
                )

                try:
                    count = int(words[1])
                except (IndexError, ValueError):
                    map_error(line, "%s requires an integer count" % w)
                land_type = normalize_building_land_type_name(land_type)
                if land_type not in building_land_types():
                    map_error(
                        line,
                        "unknown building_land type %r for %s (known: %s)"
                        % (
                            land_type,
                            w,
                            ", ".join(sorted(building_land_types())),
                        ),
                    )
                else:
                    self.nb_building_land_by_square[land_type] = count
            elif w == "victory_mode":
                mode = words[1].lower() if len(words) >= 2 else "conquest"
                setattr(self, w, mode)
            elif w == "building_land":
                from ..worldresource import building_land_types

                land_type = words[1].lower() if len(words) >= 2 else None
                if land_type is None:
                    from ..worldresource import default_building_land_type

                    land_type = default_building_land_type()
                if land_type not in building_land_types():
                    map_error(
                        line,
                        "building_land must be one of: %s"
                        % ", ".join(sorted(building_land_types())),
                    )
                else:
                    self.building_land = land_type
                    self._map_building_land_explicit = True
            elif w == "additional_building_land":
                from ..worldresource import building_land_types

                if len(words) < 3:
                    map_error(line, "additional_building_land requires a type and squares")
                land_type = words[1].lower()
                if land_type not in building_land_types():
                    map_error(
                        line,
                        "unknown building_land type: %s" % land_type,
                    )
                replaced = [
                    self.name_to_square.get(tok, tok) for tok in words[2:]
                ]
                squares = self._normalize_square_list(replaced)
                check_squares(line, squares)
                self.additional_building_land.extend(
                    (square, land_type) for square in squares
                )
            elif w in ["south_north", "west_east"]:
                # 支持别名
                replaced = []
                for tok in words[2:]:
                    replaced.append(self.name_to_square.get(tok, tok))
                squares = self._normalize_square_list(replaced)
                check_squares(line, squares)
                getattr(self, w).append((words[1], squares))
            elif w in squares_words:
                # 支持别名
                replaced = []
                for tok in words[1:]:
                    replaced.append(self.name_to_square.get(tok, tok))
                squares = self._normalize_square_list(replaced)
                check_squares(line, squares)
                getattr(self, w).extend(squares)
            elif w == "high_grounds":
                locations = self._parse_terrain_location_tokens(words[1:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.high_grounds.append(square_key)
                    else:
                        self.sub_high_grounds.setdefault(square_key, set()).add(subcell)
            elif w == "square_name":
                # 支持：
                # 1) 多对：square_name 别名1 x1,y1 别名2 x2,y2 ...
                # 2) 一个别名后跟多个坐标：square_name 别名 x1,y1 x2,y2 ...
                # 说明：
                #   - 别名→多个坐标：按“主区域”（province）处理
                #   - 别名→单个坐标：按“二级区域”（city）处理
                # 如需第三级区域，请使用 square_name3
                if len(words) < 3:
                    map_warning(line, "square_name requires alias and coordinate")
                else:
                    i = 1
                    coord_re = r"^\s*\d+\s*,\s*\d+\s*$"
                    while i < len(words):
                        alias = words[i]
                        i += 1
                        if i >= len(words):
                            map_warning(line, f"square_name '{alias}' is missing a coordinate")
                            break
                        # 消费一个或多个坐标，先收集再决定主/子层
                        coords = []
                        while i < len(words):
                            std_1based = words[i].strip()
                            if std_1based.startswith("(") and std_1based.endswith(")"):
                                std_1based = std_1based[1:-1].strip()
                            if re.match(coord_re, std_1based):
                                coords.append(std_1based)
                                i += 1
                            else:
                                break
                        if not coords:
                            map_warning(line, f"square_name invalid coordinate after alias '{alias}'")
                            continue
                        # 记录一个别名的代表坐标（用于后续别名替换）
                        if alias not in self.name_to_square:
                            self.name_to_square[alias] = coords[0]
                        for std_1based in coords:
                            try:
                                x_str, y_str = [t.strip() for t in std_1based.split(',')]
                                col0 = int(x_str) - 1
                                row0 = int(y_str) - 1
                                key = f"{col0},{row0}"
                                # 判定主/子层：
                                if len(coords) >= 2:
                                    # 多坐标：主区域优先，不覆盖已存在主区域
                                    if key not in self.square_provinces:
                                        self.square_provinces[key] = alias
                                    else:
                                        # 若已存在主区域，则作为二级区域名
                                        self.square_cities.setdefault(key, alias)
                                        self.square_names[key] = alias
                                else:
                                    # 单坐标：若尚无二级区域，则作为二级；否则作为第三级
                                    if key not in self.square_cities:
                                        self.square_cities[key] = alias
                                        self.square_names[key] = alias
                                    else:
                                        # 将其放入第三级，不覆盖已有二级
                                        if not hasattr(self, 'square_districts'):
                                            self.square_districts = {}
                                        self.square_districts[key] = alias
                                        # 兼容：square_names 以更细级为准
                                        self.square_names[key] = alias
                            except Exception:
                                pass
            elif w in ["starting_resources"]:
                # 地图显式定义了起始资源
                self.starting_resources = " ".join(words[1:])  # just for the editor
                starting_resources = []
                for c in words[1:]:
                    try:
                        starting_resources.append(to_int(c))
                    except:
                        map_error(line, "expected an integer but found %s" % c)
                # 标记为地图显式定义
                self.map_defined_starting_resources = True
            elif rules.get(w, "class") == ["deposit"]:
                # 支持别名
                replaced = []
                for tok in words[2:]:
                    replaced.append(self.name_to_square.get(tok, tok))
                for sq in self._normalize_square_list(replaced):  # TODO: error msg (squares)
                    self.map_objects.append([sq, w, words[1]])
            elif rules.get(w, "class") == ["item"]:
                # 支持在地图中放置物品
                # 格式1: 物品类型 数量 坐标1 坐标2 ...
                # 格式2: 物品类型 坐标1 坐标2 ... (数量默认为1)
                
                if len(words) < 2:
                    map_warning(line, "物品定义需要至少一个坐标")
                    continue
                
                # 检查第二个参数是否是数字（数量）
                try:
                    quantity = int(words[1])
                    # 如果成功转换为整数，说明有数量参数
                    squares = words[2:]
                except (ValueError, IndexError):
                    # 如果转换失败，说明没有数量参数，默认数量为1
                    quantity = 1
                    squares = words[1:]
                
                # 处理坐标列表
                # 支持别名
                replaced = []
                for tok in squares:
                    replaced.append(self.name_to_square.get(tok, tok))
                for sq in self._normalize_square_list(replaced):  # TODO: error msg (squares)
                    self.map_objects.append([sq, w, quantity])
            elif w in ["starting_units"]:
                getattr(self, w).extend(words[1:])  # TODO: error msg (types)
                # 标记为地图显式定义
                self.map_defined_starting_units = True
            elif w == "starting_population":
                if len(words) < 2:
                    map_warning(line, "starting_population needs an integer")
                else:
                    try:
                        self.starting_population = int(words[1])
                    except ValueError:
                        map_error(line, "expected an integer but found %s" % words[1])
                    self.map_defined_starting_population = True
            elif w == "player_start":
                # 语法（两种）：
                #   1) player_start <N> <square>
                #      只把"第 N 个加入的人/AI"固定到 <square> 出生，
                #      保留该 slot 已有的资源 / 单位列表，只换格子。
                #   2) player_start <N> <resources...> <square> <units...>
                #      像 `player` 行那样为"第 N 个玩家"定义完整的资源 +
                #      出生格 + 单位，并把该 slot pin 给第 N 个 client。
                #      例：player_start 1 5 10 a1 townhall peasant
                #          等价于把 `player 5 10 a1 townhall peasant`
                #          固定成"第 1 个玩家"的开局。
                # N：1-based 玩家序号，与 `trigger playerN` 一致。
                # square：可以是 "a1"/"1,1"/别名/已注册的 square_name。
                # 语义：被钉的玩家不论 random_starts 是否启用都不随机；
                #       其它没指定的玩家仍按 random_starts 的现行规则分配。
                # 实际位置写入 self.player_start_overrides，落地在
                # _apply_player_start_overrides() 与 populate_map()。
                if len(words) < 3:
                    map_warning(line, "player_start needs <player_index> <square>")
                else:
                    try:
                        n_idx = int(words[1])
                    except ValueError:
                        map_warning(line, "player_start: invalid index %r" % words[1])
                        continue
                    if n_idx < 1:
                        map_warning(line, "player_start: index must be >= 1 (got %d)" % n_idx)
                        continue
                    # 把 words[2:] 当作 `player` 行那样预处理：先替换别名、
                    # 归一化坐标（a1 -> "x,y"），再用
                    # convert_and_split_first_numbers 把开头的资源数字与其余
                    # （square + units）切开。
                    from .world_core import convert_and_split_first_numbers
                    replaced = [self.name_to_square.get(tok, tok) for tok in words[2:]]
                    norm = self._normalize_square_list(replaced)
                    resources, items = convert_and_split_first_numbers(list(norm))

                    def _is_square_tok(tok):
                        return isinstance(tok, str) and re.match(
                            r"^-?\d+\s*,\s*-?\d+$", tok
                        ) is not None

                    if not resources and len(items) == 1:
                        # 简单式：player_start N <square>——只换格子，
                        # 保留该 slot 已写好的资源 / 单位列表。
                        sq = items[0]
                        check_squares(line, [sq])
                        prev = self.player_start_overrides.get(n_idx)
                        if isinstance(prev, str) and prev != sq:
                            map_warning(
                                line,
                                "player_start %d redefined (was %s, now %s)"
                                % (n_idx, prev, sq),
                            )
                        self.player_start_overrides[n_idx] = sq
                    else:
                        # 完整式：resources + square + units。
                        squares_in_items = [t for t in items if _is_square_tok(t)]
                        if not squares_in_items:
                            map_warning(
                                line,
                                "player_start: missing <square> in %r"
                                % " ".join(words[2:]),
                            )
                            continue
                        check_squares(line, squares_in_items)
                        if n_idx in self.player_start_overrides:
                            map_warning(line, "player_start %d redefined" % n_idx)
                        self.player_start_overrides[n_idx] = {
                            "resources": resources,
                            "items": items,
                        }
            elif w in ["player", "computer_only", "computer"]:
                # 规范化坐标后再记录/处理（避免起始位置中的数字坐标无法识别）
                # 支持别名：将别名替换为标准方格键
                replaced = []
                for tok in words[1:]:
                    if tok in self.name_to_square:
                        replaced.append(self.name_to_square[tok])
                    else:
                        replaced.append(tok)
                norm_words = [words[0]] + self._normalize_square_list(replaced)
                self.specific_starts.append(" ".join(norm_words))  # just for the editor
                # 标记为地图显式定义
                self.map_defined_specific_starts = True
                self._add_start(w, norm_words)
            elif w == "trigger":
                triggers.append(words[1:])
            elif w == "terrain":
                t = words[1]
                locations = self._parse_terrain_location_tokens(words[2:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.terrain[square_key] = t
                    else:
                        self.sub_terrain[(square_key, subcell)] = t
            elif w == "map_music":
                # 解析地图音乐设置
                if len(words) >= 2:
                    self.map_music = words[1]
            elif w == "map_battle_music":
                # 解析地图战斗音乐设置
                if len(words) >= 2:
                    self.map_battle_music = words[1]
            elif w == "map_victory_sound":
                # 解析地图胜利音乐设置
                if len(words) >= 2:
                    self.map_victory_sound = words[1]
            elif w == "map_defeat_sound":
                # 解析地图失败音乐设置
                if len(words) >= 2:
                    self.map_defeat_sound = words[1]
            elif w == "speed":
                t = tuple(int(float(x) * 100) for x in words[1:3])
                locations = self._parse_terrain_location_tokens(words[3:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.terrain_speed[square_key] = t
                    else:
                        self.sub_terrain_speed[(square_key, subcell)] = t
            elif w == "cover":
                t = tuple(int(float(x) * 100) for x in words[1:3])
                locations = self._parse_terrain_location_tokens(words[3:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.terrain_cover[square_key] = t
                    else:
                        self.sub_terrain_cover[(square_key, subcell)] = t
            elif w == "water":
                locations = self._parse_terrain_location_tokens(words[1:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.water_squares.add(square_key)
                    else:
                        self.sub_water.setdefault(square_key, set()).add(subcell)
            elif w == "ground":
                locations = self._parse_terrain_location_tokens(words[1:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.ground_squares.add(square_key)
                    else:
                        self.sub_ground.setdefault(square_key, set()).add(subcell)
            elif w == "no_air":
                locations = self._parse_terrain_location_tokens(words[1:], line, w)
                for square_key, subcell in locations:
                    if subcell is None:
                        self.no_air_squares.add(square_key)
                    else:
                        self.sub_no_air.setdefault(square_key, set()).add(subcell)
            elif w == "square_name3":
                # 第三级区域（district）：别名后接一系列单坐标
                if len(words) < 3:
                    map_warning(line, "square_name3 requires alias and coordinate")
                else:
                    i = 1
                    coord_re = r"^\s*\d+\s*,\s*\d+\s*$"
                    while i < len(words):
                        alias = words[i]
                        i += 1
                        if i >= len(words):
                            map_warning(line, f"square_name3 '{alias}' is missing a coordinate")
                            break
                        mapped_any = False
                        while i < len(words):
                            std_1based = words[i].strip()
                            if std_1based.startswith("(") and std_1based.endswith(")"):
                                std_1based = std_1based[1:-1].strip()
                            if re.match(coord_re, std_1based):
                                # 三级区域仅接受单个坐标；但为便利也允许多个坐标，都按三级名赋值
                                try:
                                    x_str, y_str = [t.strip() for t in std_1based.split(',')]
                                    col0 = int(x_str) - 1
                                    row0 = int(y_str) - 1
                                    key = f"{col0},{row0}"
                                    self.square_districts[key] = alias
                                except Exception:
                                    pass
                                i += 1
                                mapped_any = True
                            else:
                                break
                        if not mapped_any:
                            map_warning(line, f"square_name3 invalid coordinate after alias '{alias}'")
            else:
                map_warning(line, "unknown command: %s" % w)
        # build self.players_starts
        for sq in self.starting_squares:
            self._add_start_to(
                self.players_starts,
                starting_resources,
                self.starting_units,
                sq,
                population=self.starting_population,
            )
        # 应用 `player_start N <sq>` 覆盖：必须在 starting_squares 展开之后
        # 进行，使得"玩家 N"的 slot 一定带着指定的格子。
        self._apply_player_start_overrides(starting_resources)
        if self.nb_players_min > self.nb_players_max:
            map_error("", "nb_players_min > nb_players_max")
        if len(self.players_starts) < self.nb_players_max:
            map_error("", "not enough starting places for nb_players_max")
        # 2 multiplayer map types: with or without standard triggers
        # TODO: select in a menu: User Map Settings, melee, free for all, etc
        if not triggers and self.default_triggers:
            triggers = self.default_triggers
        elif triggers and getattr(self, "merge_default_triggers", 0) and self.default_triggers:
            triggers = list(triggers) + list(self.default_triggers)
        
        # 处理触发器列表，确保引号内的文本不被分割
        for i, t in enumerate(triggers):
            # 预处理每个触发器中可能的引号文本
            j = 0
            while j < len(t):
                if isinstance(t[j], str) and t[j].startswith('"') and not t[j].endswith('"'):
                    # 找到未闭合的引号
                    start = j
                    j += 1
                    while j < len(t) and not (isinstance(t[j], str) and t[j].endswith('"')):
                        j += 1
                    
                    if j < len(t):  # 找到了结束引号
                        # 合并引号内的内容
                        merged = ' '.join(t[start:j+1])
                        t[start:j+1] = [merged]
                        j = start + 1
                    else:
                        j += 1
                else:
                    j += 1
            
            # 用处理后的触发器数据调用_add_trigger
            self._add_trigger(t)

        self._sync_map_building_land_default()

    def load_and_build_map(self, map):
        res.set_map(map)
        res.load_rules_and_ai()  # TODO: remove this line when tests don't require it

        self._parse_map(map.definition)

        self.square_width = int(self.square_width * PRECISION)
        self._build_map()

    def save_map(self, filename):
        def _sorted(squares):
            def _key(n):
                # n 为 "x,y"
                try:
                    x, y = [int(v) for v in n.split(',')]
                    return (x, y)
                except Exception:
                    return (0, 0)
            return sorted(squares, key=_key)

        def res():
            return sorted(
                {
                    (o.type_name, o.qty // PRECISION)
                    for s in set(self.grid.values())
                    for o in s.objects
                    if getattr(o, "resource_type", None) is not None
                },
                key=lambda x: (x[0], -x[1]),
            )
        
        def items():
            """获取地图上的所有物品"""
            return [
                (s.name, o.type_name)
                for s in set(self.grid.values())
                for o in s.objects
                if rules.get(o.type_name, "class") == ["item"]
            ]

        with open(filename, "w") as f:
            f.write("title %s\n" % " ".join(map(str, self.title)))
            f.write("objective %s\n" % " ".join(map(str, self.objective)))
            f.write("\n")
            f.write("square_width %s\n" % (self.square_width // PRECISION))
            f.write("nb_columns %s\n" % self.nb_columns)
            f.write("nb_lines %s\n" % self.nb_lines)
            f.write("\n")
            f.write("nb_players_min %s\n" % self.nb_players_min)
            f.write("nb_players_max %s\n" % self.nb_players_max)
            f.write("starting_squares %s\n" % " ".join(_sorted(self.starting_squares)))
            f.write("starting_units %s\n" % " ".join(self.starting_units))
            f.write("starting_resources %s\n" % self.starting_resources)
            if self.starting_population:
                f.write("starting_population %s\n" % self.starting_population)
            f.write("global_population_limit %s\n" % self.global_population_limit)
            # 保存地图音乐设置
            if self.map_music:
                f.write("map_music %s\n" % self.map_music)
            # 保存地图战斗音乐设置
            if self.map_battle_music:
                f.write("map_battle_music %s\n" % self.map_battle_music)
            if self.map_victory_sound:
                f.write("map_victory_sound %s\n" % self.map_victory_sound)
            if self.map_defeat_sound:
                f.write("map_defeat_sound %s\n" % self.map_defeat_sound)
            for line in self.specific_starts:
                f.write(line + "\n")
            f.write("\n")
            for t, q in res():
                squares = _sorted(
                    s.name
                    for s in set(self.grid.values())
                    for o in s.objects
                    if o.type_name == t and o.qty // PRECISION == q
                )
                f.write("{} {} {}\n".format(t, q, " ".join(squares)))
            # 保存物品信息
            f.write("\n; 物品位置\n")
            item_types = {}
            for square_name, item_type in items():
                if item_type not in item_types:
                    item_types[item_type] = []
                item_types[item_type].append(square_name)
            
            for item_type, squares in sorted(item_types.items()):
                f.write("{} 1 {}\n".format(item_type, " ".join(_sorted(squares))))
            
            f.write("\nnb_meadows_by_square 0\n")
            for n in sorted(
                    {s.nb_meadows for s in list(self.grid.values()) if s.nb_meadows}
            ):
                squares = _sorted(
                    [s.name for s in set(self.grid.values()) if s.nb_meadows == n]
                )
                if n == 1:
                    f.write("; 1 meadow\n")
                else:
                    f.write("; %s meadows\n" % n)
                for _ in range(n):
                    f.write("additional_meadows %s\n" % " ".join(squares))
            f.write("\n")
            if getattr(self, "subcell_precision", DEFAULT_SUBCELL_PRECISION) != DEFAULT_SUBCELL_PRECISION:
                f.write("subcell_precision %s\n" % self.subcell_precision)
            for t in sorted(
                    {s.type_name for s in list(self.grid.values()) if s.type_name}
            ):
                squares = _sorted(
                    [s.name for s in set(self.grid.values()) if s.type_name == t]
                )
                f.write("terrain {} {}\n".format(t, " ".join(squares)))
            squares = _sorted([s.name for s in set(self.grid.values()) if s.high_ground])
            f.write("high_grounds %s\n" % " ".join(squares))
            squares = _sorted([s.name for s in set(self.grid.values()) if s.is_water])
            f.write("water %s\n" % " ".join(squares))
            squares = _sorted(
                [s.name for s in set(self.grid.values()) if s.is_ground and s.is_water]
            )
            f.write("ground %s\n" % " ".join(squares))
            squares = _sorted([s.name for s in set(self.grid.values()) if not s.is_air])
            f.write("no_air %s\n" % " ".join(squares))
            for t in sorted(
                    {
                        s.terrain_cover
                        for s in list(self.grid.values())
                        if s.terrain_cover != (0, 0)
                    }
            ):
                squares = _sorted(
                    [s.name for s in set(self.grid.values()) if s.terrain_cover == t]
                )
                f.write(
                    "cover {} {}\n".format(
                        " ".join([str(x / 100.0) for x in t]), " ".join(squares)
                    )
                )
            for t in sorted(
                    {
                        s.terrain_speed
                        for s in list(self.grid.values())
                        if s.terrain_speed != (100, 100)
                    }
            ):
                squares = _sorted(
                    [s.name for s in set(self.grid.values()) if s.terrain_speed == t]
                )
                f.write(
                    "speed {} {}\n".format(
                        " ".join([str(x / 100.0) for x in t]), " ".join(squares)
                    )
                )
            for s in sorted(
                    [x for x in set(self.grid.values()) if getattr(x, "subcells", None) and x.subcells.has_any()],
                    key=lambda sq: sq.name,
            ):
                sc = s.subcells
                for (cx, cy), t in sc.iter_type_names():
                    f.write(
                        "terrain {} {}{}\n".format(
                            t, s.name, format_subcell_suffix(cx, cy)
                        )
                    )
                for (cx, cy), value in sc.iter_high_ground():
                    if value:
                        f.write(
                            "high_grounds {}{}\n".format(
                                s.name, format_subcell_suffix(cx, cy)
                            )
                        )
                for (cx, cy), value in sc.iter_is_water():
                    if value:
                        f.write(
                            "water {}{}\n".format(
                                s.name, format_subcell_suffix(cx, cy)
                            )
                        )
                for (cx, cy), value in sc.iter_is_ground():
                    f.write(
                        "ground {}{}\n".format(
                            s.name, format_subcell_suffix(cx, cy)
                        )
                    )
                for (cx, cy), value in sc.iter_is_air():
                    if not value:
                        f.write(
                            "no_air {}{}\n".format(
                                s.name, format_subcell_suffix(cx, cy)
                            )
                        )
                for (cx, cy), t in sc.iter_terrain_covers():
                    f.write(
                        "cover {} {}{}\n".format(
                            " ".join([str(x / 100.0) for x in t]),
                            s.name,
                            format_subcell_suffix(cx, cy),
                        )
                    )
                for (cx, cy), t in sc.iter_terrain_speeds():
                    f.write(
                        "speed {} {}{}\n".format(
                            " ".join([str(x / 100.0) for x in t]),
                            s.name,
                            format_subcell_suffix(cx, cy),
                        )
                    )
            f.write("\n")
            we = dict()
            sn = dict()
            for s in set(self.grid.values()):
                for e in s.exits:
                    o = e.other_side.place
                    delta = o.col - s.col, o.row - s.row
                    if delta == (1, 0):
                        if e.type_name not in we:
                            we[e.type_name] = []
                        we[e.type_name].append(s.name)
                    elif delta == (0, 1):
                        if e.type_name not in sn:
                            sn[e.type_name] = []
                        sn[e.type_name].append(s.name)
            for tn in we:
                f.write("west_east {} {}\n".format(tn, " ".join(_sorted(we[tn]))))
            for tn in sn:
                f.write("south_north {} {}\n".format(tn, " ".join(_sorted(sn[tn]))))