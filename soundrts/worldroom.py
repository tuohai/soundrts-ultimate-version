import os
from functools import cached_property

from .definitions import rules, style
from .lib.log import warning
from .lib.msgs import nb2msg
from . import msgparts as mp
from .lib.nofloat import int_angle, int_cos_1000, int_distance, int_sin_1000
from .lib.priodict import priorityDictionary
from heapq import heappush, heappop
from .worldentity import COLLISION_RADIUS
from .worldexit import passage
from .worldresource import Deposit, BuildingLand, create_building_land
from .lib.subcell_terrain import SubCellOverlay
from .lib.square_terrain_rules import (
    object_affects_square_terrain,
    resolve_square_type_name,
    terrain_blocks_path,
)

# A* 内层 Cython 加速器；不可用时回退到 Python 实现
_rf = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import worldroom_fast as _rf  # type: ignore[no-redef]
    except ImportError:
        _rf = None

SPACE_LIMIT = 144


def square_spiral(x, y, step=COLLISION_RADIUS * 25 // 10):
    yield x, y
    sign = 1
    delta = 1
    while delta < 25:
        for _ in range(delta):
            x += sign * step
            yield x, y
        for _ in range(delta):
            y += sign * step
            yield x, y
        delta += 1
        sign *= -1


_cache = {}
_cache_time = None


def cache(f):
    def decorated_f(*args, **kargs):
        global _cache, _cache_time
        # 将缓存时间粒度放宽到3000ms，减少同一时间段内重复寻路
        current_bucket = args[0].world.time // 3000
        if _cache_time != current_bucket:
            _cache = {}
            _cache_time = current_bucket
        # 热路径几乎都是纯 positional；避免每次 sorted(kargs.items())
        if kargs:
            k = (args, tuple(sorted(kargs.items())))
        else:
            k = args
        if k not in _cache:
            _cache[k] = f(*args, **kargs)
        return _cache[k]

    return decorated_f


class _Space:
    high_ground = False
    # class-level 默认值: 让 getattr(place, 'objects', ()) / getattr(place, 'is_inside_place', False)
    # 这类反射调用在热路径上 (perception.known_enemies 17.9M calls) 能直接命中类属性,
    # 避免 PyObject_HasAttr 慢路径. 实例化后会被 __init__ 覆盖为各自的实例属性.
    objects = ()
    is_inside_place = False
    # A* 图节点含 Square 与 Exit；仅 Exit 有 is_blocked。用 is_an_exit 替代
    # hasattr(v, 'is_blocked')，避免千万级 HasAttr 慢路径。
    is_an_exit = False

    def __init__(self):
        self.objects = []

    def enter(self, o):
        self.objects.append(o)
        if o.id is None:
            self.world.register_entity(o)

    def leave(self, o):
        self.objects.remove(o)


class Square(_Space):

    transport_capacity = 0
    type_name = ""
    fixed_terrain = False
    terrain_speed = (100, 100)
    terrain_cover = (0, 0)
    is_ground = True
    is_water = False
    is_air = True

    def __init__(self, world, col, row, width):
        super().__init__()
        self.col = col
        self.row = row
        # 使用平面网格坐标作为名称，例如 "3,5"
        self.name = f"{col},{row}"
        self.id = world.get_next_id()
        self.world = world
        world.squares.append(self)
        world.objects[self.id] = self
        self.place = world
        # 标题：优先使用第三级名称，其次二级；若均无则为坐标（1基）
        std = f"{col},{row}"
        # 组合标题：若有第三级（district）则只播第三级；否则播第二级（city）；否则 fallback；最后加坐标
        city = getattr(world, 'square_cities', {}).get(std)
        district = getattr(world, 'square_districts', {}).get(std)
        fallback = getattr(world, 'square_names', {}).get(std)
        coord = nb2msg(col + 1) + mp.COMMA + nb2msg(row + 1)
        if district:
            self.title = [district] + mp.COMMA + coord
        elif city:
            # 二级区域名仅在跨入时由前缀播报；标题内不再重复二级
            self.title = coord
        elif fallback:
            self.title = [fallback] + mp.COMMA + coord
        else:
            self.title = coord
        self.exits = []
        self.xmin = col * width
        self.ymin = row * width
        self.xmax = self.xmin + width
        self.ymax = self.ymin + width
        self.x = (self.xmax + self.xmin) // 2
        self.y = (self.ymax + self.ymin) // 2
        # 标记：该 place 为外部区域（非 Inside）
        self.is_inside_place = False
        self.subcells = SubCellOverlay()

    def __repr__(self):
        return "<'%s'>" % self.name

    def high_ground_at(self, x, y):
        return self.subcells.high_ground_at(self, x, y)

    def type_name_at(self, x, y):
        return self.subcells.type_name_at(self, x, y)

    def terrain_speed_at(self, x, y):
        return self.subcells.terrain_speed_at(self, x, y)

    def terrain_cover_at(self, x, y):
        return self.subcells.terrain_cover_at(self, x, y)

    def is_water_at(self, x, y):
        return self.subcells.is_water_at(self, x, y)

    def is_ground_at(self, x, y):
        return self.subcells.is_ground_at(self, x, y)

    def is_air_at(self, x, y):
        return self.subcells.is_air_at(self, x, y)

    def is_passable_for(self, unit, x, y):
        """Whether *unit* may stand at world coords (*x*, *y*) in this square."""
        terrain_name = ""
        if hasattr(self, "type_name_at"):
            terrain_name = self.type_name_at(x, y) or ""
        elif getattr(self, "fixed_terrain", False):
            terrain_name = getattr(self, "type_name", "") or ""

        if terrain_name:
            from .lib.square_terrain_rules import (
                terrain_allows_unit,
                terrain_has_passable_units,
            )

            if terrain_has_passable_units(terrain_name):
                return terrain_allows_unit(terrain_name, unit)

        ag = getattr(unit, "airground_type", "ground")
        if ag == "air":
            return self.is_air_at(x, y)
        if ag == "water":
            return self.is_water_at(x, y)
        if self.is_water_at(x, y) and not self.is_ground_at(x, y):
            return False
        return self.is_ground_at(x, y)

    @property
    def height(self):
        if self.high_ground:
            return 1
        else:
            return 0

    # Round 4 优化: neighbors / strict_neighbors 从 @property + try/except 改为
    # functools.cached_property. cached_property 是 *non-data* descriptor:
    # 首次访问时计算并 *直接写入 instance __dict__*; 后续访问跳过 descriptor
    # 协议, 走普通 LOAD_ATTR (~30-50ns vs property 的 ~200ns).
    #
    # round 4 profile 中 worldroom.neighbors 是 30.3M calls / 6.96s,
    # 移到 cached_property 后预期单 call 降到 ~50ns, 节省 ~5s.

    @cached_property
    def strict_neighbors(self):
        grid_get = self.world.grid.get
        c = self.col
        r = self.row
        result = []
        for dc, dr in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            s = grid_get((c + dc, r + dr))
            if s is not None:
                result.append(s)
        return tuple(result)

    @cached_property
    def neighbors(self):
        grid_get = self.world.grid.get
        c = self.col
        r = self.row
        result = []
        for dc, dr in (
            (0, 1), (0, -1), (1, 0), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1),
        ):
            s = grid_get((c + dc, r + dr))
            if s is not None:
                result.append(s)
        return tuple(result)

    @property
    def building_land(self):
        for o in self.objects:
            if o.is_a_building_land:
                return o

    @property
    def exit(self):
        for o in self.exits:
            if o.is_an_exit and not o.is_blocked():
                return o

    @property
    def subsquares(self):
        k = (self.xmax - self.xmin) // 3
        for dx in [0, 1, -1]:
            for dy in [0, 1, -1]:
                yield ZoomTarget(self, self.x + dx * k, self.y + dy * k)

    @property
    def any_land(self):
        """返回任何适合建造的陆地，优先建筑用地，否则返回第一个陆地对象"""
        # 优先返回建筑用地
        building_land = self.building_land
        if building_land:
            return building_land
        
        # 如果没有建筑用地，返回任何陆地对象
        for o in self.objects:
            if (hasattr(o, 'is_a_building_land') and o.is_a_building_land):
                return o
        
        return None

    @property 
    def is_near_water(self):
        """检查该方格是否靠近水域"""
        # 如果自己就是水域，返回False（水域本身不算"靠近"水域）
        if self.is_water:
            return False
            
        # 检查相邻方格是否有水域
        for neighbor in self.strict_neighbors:
            if getattr(neighbor, 'is_water', False):
                return True
        
        return False

    def update_water_status(self):
        """根据地形类型和名称更新水域状态"""
        # 检查方格名称或类型名称中是否包含水域关键词
        water_keywords = ['water', 'sea', 'ocean', 'lake', 'river', 'pond', '水', '海', '湖', '河']
        
        # 检查type_name
        if hasattr(self, 'type_name') and self.type_name:
            type_name_lower = self.type_name.lower()
            if any(keyword in type_name_lower for keyword in water_keywords):
                self.is_water = True
                self.is_ground = False
                return
        
        # 检查方格对象中是否有水域地形
        for obj in self.objects:
            if hasattr(obj, 'type_name'):
                obj_type_lower = obj.type_name.lower()
                if any(keyword in obj_type_lower for keyword in water_keywords):
                    self.is_water = True
                    self.is_ground = False
                    return
        
        # 如果明确设置了is_water属性，使用该设置
        if hasattr(self, '_is_water_set'):
            self.is_water = self._is_water_set
            if self.is_water:
                self.is_ground = False

    def set_water_terrain(self, is_water=True):
        """手动设置方格的水域状态"""
        self._is_water_set = is_water
        self.is_water = is_water
        if is_water:
            self.is_ground = False
        else:
            self.is_ground = True


    def __getstate__(self):
        from .save_pickle import SQUARE_STRIP_ON_SAVE, pop_keys

        d = self.__dict__.copy()
        pop_keys(d, SQUARE_STRIP_ON_SAVE)
        return d

    def is_near(self, square):  # FIXME: not used (remove?)
        try:
            return (abs(self.col - square.col), abs(self.row - square.row)) in (
                (0, 1),
                (1, 0),
                (1, 1),
            )
        except AttributeError:  # not a square
            return False

    def clean(self):
        for o in self.objects:
            o.clean()
        self.__dict__ = {}

    def contains(self, x, y):
        return self.xmin <= x < self.xmax and self.ymin <= y < self.ymax

    def shortest_path_to(
        self, dest, player=None, plane="ground", places=False, avoid=False
    ):
        if places:
            return self._shortest_path_to(dest, plane, player, places=True, avoid=avoid)
        else:
            return self._shortest_path_to(dest, plane, player, avoid=avoid)[0]

    def shortest_path_distance_to(self, dest, player=None, plane="ground", avoid=False):
        return self._shortest_path_to(dest, plane, player, avoid=avoid)[1]

    @cache
    def _shortest_path_to(self, dest, plane, player, places=False, avoid=False):
        """Returns the next exit to the shortest path from self to dest
        and the distance of the shortest path from self to dest."""
        # 区域层优先（若有），失败再用局部A*
        region_res = self._region_path_to(dest, plane, player, places=places, avoid=avoid)
        if region_res is not None:
            return region_res
        # TODO: remove the duplicate exits in the graph
        if avoid:
            avoid_fn = player.is_very_dangerous
        else:
            avoid_fn = None
        if dest is self:
            return [self] if places else (None, 0)

        # 邻格快路径：直接出口连通时跳过整图 A*（常见近距移动）
        if plane == "ground" and not places:
            for e in self.exits:
                other = e.other_side
                if other is None:
                    continue
                if other.place is not dest:
                    continue
                if player is not None:
                    try:
                        if e.is_blocked(player, ignore_enemy_walls=True):
                            continue
                    except Exception:
                        pass
                    try:
                        if other.is_blocked(player, ignore_enemy_walls=True):
                            continue
                    except Exception:
                        pass
                if avoid_fn is not None and (avoid_fn(e) or avoid_fn(other)):
                    continue
                dist = int_distance(self.x, self.y, e.x, e.y) + int_distance(
                    other.x, other.y, dest.x, dest.y
                )
                return e, dist

        ##        if not dest.exits: # small optimization
        ##            return None, None # no path exists

        # add start and end to the graph
        G = self.world.g[plane]
        water_shore_temps = []
        if plane == "ground":
            for v in (self, dest):
                G[v] = {}
                for e in v.exits:
                    G[v][e] = G[e][v] = int_distance(v.x, v.y, e.x, e.y)
        elif plane == "water":
            for v in (self, dest):
                if getattr(v, "is_water", False):
                    continue
                water_shore_temps.append(v)
                G[v] = {}
                for n in v.strict_neighbors:
                    if not getattr(n, "is_water", False):
                        continue
                    edge = int_distance(v.x, v.y, n.x, n.y)
                    G[v][n] = edge
                    if n not in G:
                        G[n] = {}
                    G[n][v] = edge
        start = self
        end = dest

        # A* 使用 heapq，减少 priodict 的开销；保持跨机器确定性。
        # 启发式与 is_blocked 缓存查询走 Cython（如可用）以省闭包/属性查找开销。
        # Round 4: end/start/w 都是 Entity 子类, x/y/id 在基类有, 直接访问.
        end_x = end.x
        end_y = end.y
        if _rf is not None:
            _h = lambda n: _rf.astar_heuristic(n, end_x, end_y)
        else:
            def _h(n):
                try:
                    return int_distance(n.x, n.y, end_x, end_y)
                except Exception:
                    return 0

        g_score = {start: 0}
        came_from = {}
        open_heap = []  # (f, tie_breaker, node)
        heappush(open_heap, (_h(start), int(start.id), start))
        closed = set()

        # 本次寻路的局部阻挡缓存，避免对同一出口重复判断
        local_block_cache = {}
        player_id = int(player.id) if player else 0

        while open_heap:
            _, _, v = heappop(open_heap)
            if v in closed:
                continue
            # D-Phase 1 T5: pop 时的 is_blocked 也走 cached_is_blocked.
            # 同一 A* 调用内 v 可能多次入堆 (从不同方向), cache 复用首次结果.
            # 配合下面 neighbors 检查共用一份 local_block_cache, 命中率显著提升.
            # 仅 Exit 有 is_blocked；用 is_an_exit 替代 hasattr (千万级调用)。
            if player and v.is_an_exit:
                if _rf is not None:
                    v_blocked = _rf.cached_is_blocked(v, player, local_block_cache, player_id)
                else:
                    lk = (id(v), player_id)
                    v_blocked = local_block_cache.get(lk)
                    if v_blocked is None:
                        try:
                            v_blocked = v.is_blocked(player, ignore_enemy_walls=True)
                        except Exception:
                            v_blocked = False
                        local_block_cache[lk] = v_blocked
            else:
                v_blocked = False
            if v_blocked or (avoid_fn is not None and avoid_fn(v)):
                closed.add(v)
                continue
            if v is end:
                break
            closed.add(v)

            neighbors = G.get(v, {})
            g_v = g_score.get(v, 0)
            for w, edge_cost in neighbors.items():
                # 使用局部阻挡缓存（Cython 加速时走 cached_is_blocked）
                if player and w.is_an_exit:
                    if _rf is not None:
                        blocked = _rf.cached_is_blocked(w, player, local_block_cache, player_id)
                    else:
                        lk = (id(w), player_id)
                        blocked = local_block_cache.get(lk)
                        if blocked is None:
                            try:
                                blocked = w.is_blocked(player, ignore_enemy_walls=True)
                            except Exception:
                                blocked = False
                            local_block_cache[lk] = blocked
                else:
                    blocked = False
                if blocked or (avoid_fn is not None and avoid_fn(w)):
                    continue

                tentative_g = g_v + edge_cost
                if tentative_g < g_score.get(w, 1 << 60):
                    came_from[w] = v
                    g_score[w] = tentative_g
                    f = tentative_g + _h(w)
                    heappush(open_heap, (f, int(w.id), w))

        # restore the graph
        if plane == "ground":
            for v in (start, end):
                del G[v]
                for e in v.exits:
                    del G[e][v]
        elif plane == "water":
            for v in water_shore_temps:
                for n in list(G.get(v, {})):
                    if v in G.get(n, {}):
                        del G[n][v]
                G[v] = {}

        # exploit the results
        if end not in came_from:
            # no path exists
            return [] if places else (None, float("inf"))
        # 路径重建（Cython 加速）
        if _rf is not None:
            Path = _rf.reconstruct_path(came_from, end, start)
        else:
            Path = []
            while 1:
                Path.append(end)
                if end == start:
                    break
                end = came_from[end]
            Path.reverse()
        if places:
            result = []
            for e in Path:
                if hasattr(e, "other_side"):
                    result.append(e.place)
                elif hasattr(e, "strict_neighbors"):
                    result.append(e)
            return result
        else:
            return Path[1], g_score[dest]

    def find_nearest_meadow(self, unit):
        return self.find_meadow_near_xy(unit.x, unit.y)

    def find_meadow_near_xy(self, x, y):
        def _d(o):
            # o.id to make sure that the result is the same on any computer
            return int_distance(o.x, o.y, x, y), o.id

        meadows = sorted(
            [
                o
                for o in self.objects
                if isinstance(o, BuildingLand) and not getattr(o, "is_an_exit", False)
            ],
            key=_d,
        )
        if meadows:
            return meadows[0]

    def find_and_remove_meadow(self, item_type):
        if item_type.is_buildable_anywhere:
            return self.x, self.y, None
        for o in self.objects:
            if isinstance(o, BuildingLand) and not getattr(o, "is_an_exit", False):
                x, y = o.x, o.y
                o.delete()
                return x, y, o
        return self.x, self.y, None

    def contains_enemy(self, player):
        for o in self.objects:
            if player.is_an_enemy(o):
                return True
        return False

    def north_side(self):
        return self, self.x, self.ymax - 1, -90

    def south_side(self):
        return self, self.x, self.ymin, 90

    def east_side(self):
        return self, self.xmax - 1, self.y, 180

    def west_side(self):
        return self, self.xmin, self.y, 0

    def _shift(self, xc, yc):
        # shift angle to have central symmetry and map balance
        # (distance from the townhall to the resources)
        return int_angle(xc, yc, self.col * 10 + 5, self.row * 10 + 5)

    def arrange_resources_symmetrically(self, xc, yc):
        things = [o for o in self.objects if isinstance(o, (Deposit, BuildingLand))]
        square_width = self.xmax - self.xmin
        nb = len(things)
        shift = self._shift(xc, yc)
        for i, o in enumerate(things):
            x = self.x
            y = self.y
            if nb > 1:
                a = 360 * i // nb + shift
                # it is possible to add a constant to this angle and keep
                # the symmetry
                x += square_width * 35 // 100 * int_cos_1000(a) // 1000
                y += square_width * 35 // 100 * int_sin_1000(a) // 1000
            o.move_to(o.place, x, y)

    def can_receive(self, airground_type, player=None):
        if player is not None:
            f = player.is_an_enemy
        else:
            f = lambda x: False
        return (
            len(
                [
                    u
                    for u in self.objects
                    if u.collision and u.airground_type == airground_type and not f(u)
                ]
            )
            < SPACE_LIMIT
        )

    def find_free_space(self, airground_type, x, y):
        # assertion: object has collision
        if self.contains(x, y) and not self.world.collision[
            airground_type
        ].would_collide(x, y):
            return x, y
        if self.world.time == 0 and (x, y) == (self.x, self.y):
            if not hasattr(self, "spiral"):
                self.spiral = {}
                self.spiral["ground"] = square_spiral(x, y)
                self.spiral["air"] = square_spiral(x, y)
                self.spiral["water"] = square_spiral(x, y)
            spiral = self.spiral[
                airground_type
            ]  # reuse spiral (don't retry used places: much faster!)
        else:
            spiral = square_spiral(x, y)
        for x, y in spiral:
            if self.contains(x, y) and not self.world.collision[
                airground_type
            ].would_collide(x, y):
                return x, y
        return None, None

    def find_free_space_for(self, o, x, y):
        o.free_space()
        x, y = self.find_free_space(o.airground_type, x, y)
        o.occupy_space()
        return x, y

    def add(self, o):
        self.world.collision[o.airground_type].add(o.x, o.y)
        try:
            if object_affects_square_terrain(o):
                if not hasattr(self.world, '_dirty_terrain_squares'):
                    self.world._dirty_terrain_squares = set()
                self.world._dirty_terrain_squares.add(self)
                for s in self.strict_neighbors:
                    self.world._dirty_terrain_squares.add(s)
        except Exception:
            pass

    def remove(self, o):
        self.world.collision[o.airground_type].remove(o.x, o.y)
        try:
            if object_affects_square_terrain(o):
                if not hasattr(self.world, '_dirty_terrain_squares'):
                    self.world._dirty_terrain_squares = set()
                self.world._dirty_terrain_squares.add(self)
                for s in self.strict_neighbors:
                    self.world._dirty_terrain_squares.add(s)
        except Exception:
            pass

    def would_collide(self, o, x, y):
        space = self.world.collision[o.airground_type]
        space.remove(o.x, o.y)
        result = space.would_collide(x, y)
        space.add(o.x, o.y)
        return result

    def ensure_path(self, other, exit_type="path"):
        for e in self.exits:
            if e.other_side.place is other:
                if e.type_name != exit_type:
                    e.delete()
                else:
                    return
                break
        if other not in [e.other_side.place for e in self.exits]:
            x = (self.x + other.x) // 2
            y = (self.y + other.y) // 2
            passage(((self, x, y, 0), (other, x, y, 0), False), exit_type)
            self.world._create_graphs()

    def ensure_nopath(self, other):
        for e in self.exits:
            if other == e.other_side.place:
                e.delete()

    def ensure_free_path(self, other):
        for e in self.exits:
            if other == e.other_side.place:
                e.is_blocked_by_forests = False

    def ensure_blocked_path(self, other):
        for e in self.exits:
            if other == e.other_side.place:
                e.is_blocked_by_forests = True

    def toggle_path(self, dc, dr):
        other = self.world.grid.get((self.col + dc, self.row + dr))
        if not other:  # border
            return
        if other in [e.other_side.place for e in self.exits]:
            self.ensure_nopath(other)
        else:
            self.ensure_path(other)
            return True

    def ensure_meadows(self, n):
        for o in self.objects[:]:
            if n >= self.nb_meadows:
                break
            if o.is_a_building_land and not getattr(o, "is_an_exit", False):
                o.delete()
        for _ in range(n - self.nb_meadows):
            create_building_land(self)
        self.arrange_resources_symmetrically(self.x, self.y)

    def deposit_arrange_xy(self, index, total):
        x, y = self.x, self.y
        if total <= 1:
            return x, y
        world = self.world
        xc = world.nb_columns * 10 // 2
        yc = world.nb_lines * 10 // 2
        shift = self._shift(xc, yc)
        square_width = self.xmax - self.xmin
        angle = 360 * index // total + shift
        x += square_width * 35 // 100 * int_cos_1000(angle) // 1000
        y += square_width * 35 // 100 * int_sin_1000(angle) // 1000
        return x, y

    def ensure_resources(self, t, n, q):
        for o in self.objects[:]:
            if o.type_name == t:
                o.delete()
        if n <= 0:
            return
        entity_class = rules.unit_class(t)
        if entity_class is None:
            return
        if n > 1:
            for i in range(n):
                x, y = self.deposit_arrange_xy(i, n)
                obj = entity_class.__new__(entity_class)
                obj.collision = 0
                obj.__init__(self, q, x, y)
            self.arrange_resources_symmetrically(self.x, self.y)
        else:
            x, y = self.find_free_space("ground", self.x, self.y)
            if x is not None:
                entity_class(self, q, x, y)

    @property
    def nb_meadows(self):
        return len(
            [
                o
                for o in self.objects
                if o.is_a_building_land
                and not getattr(o, "is_an_exit", False)
                or o.building_land
                and not getattr(o, "qty", 0)
            ]
        )

    def update_terrain(self):
        if getattr(self, "fixed_terrain", False):
            return
        self.type_name = resolve_square_type_name(self)
        if terrain_blocks_path(self.type_name):
            for s in self.strict_neighbors:
                if terrain_blocks_path(s.type_name):
                    self.ensure_blocked_path(s)
                else:
                    self.ensure_free_path(s)
        else:
            for s in self.strict_neighbors:
                self.ensure_free_path(s)

    # 区域图/HPA*：若存在区域图，则先在区域层寻路以确定下一个区域
    # 返回 (最佳出口, 估计距离)；若 places=True 或无可用区域路由则返回 None
    def _region_path_to(self, dest, plane, player, places=False, avoid=False):
        if places:
            return None
        try:
            rg_all = getattr(self.world, 'region_graph', None)
            if not rg_all:
                return None
            rg = rg_all.get('ground' if plane == 'ground' else plane, {})
            start_region = getattr(self, 'region', None)
            dest_region = getattr(dest, 'region', None)
            if start_region is None or dest_region is None or start_region is dest_region:
                return None

            # 区域层A*（g=边数或门户距离，h=区域中心曼哈顿距离）
            from heapq import heappush, heappop

            def h(r):
                try:
                    dx = (getattr(r, 'center_x', self.x) - getattr(dest_region, 'center_x', dest.x))
                    dy = (getattr(r, 'center_y', self.y) - getattr(dest_region, 'center_y', dest.y))
                    return abs(dx) + abs(dy)
                except Exception:
                    return 0

            openq = []
            heappush(openq, (h(start_region), 0, id(start_region), start_region, None))
            came = {}
            cost = {start_region: 0}
            visited_ids = set()

            # 读取门户映射用于边权估计
            portals_all = getattr(self.world, 'region_portals', {})
            portals = portals_all.get('ground' if plane == 'ground' else plane, {})

            # 避敌函数：用玩家的危险评估函数作为过滤（如果请求avoid=True）
            is_dangerous = None
            if avoid and player is not None and hasattr(player, 'is_very_dangerous'):
                is_dangerous = player.is_very_dangerous

            while openq:
                _, g, rid, cur, prev = heappop(openq)
                if rid in visited_ids:
                    continue
                visited_ids.add(rid)
                came[cur] = prev
                if cur is dest_region:
                    break

                neighbors = rg.get(cur, []) or []
                for nb in neighbors:
                    # 边过滤：若门户当前因森林或敌方墙等导致不可通行，则跳过
                    e = portals.get((cur, nb))
                    if e is None:
                        continue
                    try:
                        # 区域层检查使用忽略敌方墙（和局部一致），但保留森林阻挡
                        if e.is_blocked(player, ignore_enemy_walls=True, ignore_forests=False):
                            continue
                        # 避敌：若出口另一侧方格被标记为危险则尽量避开
                        if is_dangerous is not None:
                            try:
                                if is_dangerous(e.other_side.place):
                                    continue
                            except Exception:
                                pass
                    except Exception:
                        continue

                    # 使用门户两端的欧氏近似距离作边权（更贴近真实路径长度）
                    try:
                        edge_w = int_distance(e.x, e.y, e.other_side.x, e.other_side.y)
                    except Exception:
                        edge_w = 1
                    ng = g + max(1, edge_w)
                    if nb not in cost or ng < cost[nb]:
                        cost[nb] = ng
                        heappush(openq, (ng + h(nb), ng, id(nb), nb, cur))

            if dest_region not in came:
                return None
            # 重建区域路径并取下一区域
            r = dest_region
            path_regions = []
            while r is not None:
                path_regions.append(r)
                r = came.get(r)
            path_regions.reverse()
            if len(path_regions) < 2:
                return None
            next_region = path_regions[1]

            # 找到通往下一区域的、当前不被阻挡的最佳出口
            best_exit = None
            best_d = None
            for e in self.exits:
                try:
                    # 保持与局部A*一致：忽略敌方墙阻挡，但保留森林阻挡
                    if e.is_blocked(player, ignore_enemy_walls=True, ignore_forests=False):
                        continue
                    other_place = e.other_side.place
                    if getattr(other_place, 'region', None) is next_region:
                        d = int_distance(self.x, self.y, other_place.x, other_place.y)
                        if best_d is None or d < best_d:
                            best_d = d
                            best_exit = e
                except Exception:
                    continue
            if best_exit is None:
                return None
            approx = int_distance(self.x, self.y, dest.x, dest.y)
            return best_exit, approx
        except Exception:
            return None


class Inside(_Space):
    container = None
    neighbors = []
    is_ground = True
    place = None
    id = None

    def __init__(self, container):
        super().__init__()
        self.container = container
        # 标记：该 place 为内部区域
        self.is_inside_place = True

    @property
    def title(self):
        return style.get(self.container.type_name, "title")

    @property
    def high_ground(self):
        if self.container.airground_type == "air":
            return True
        return self.container.place.high_ground

    @property
    def height(self):
        return self.container.height

    @property
    def world(self):
        return self.container.world

    @property
    def outside(self):
        return self.container.place

    @property
    def type_name(self):
        outside = self.outside
        if outside is None:
            return ""
        return getattr(outside, "type_name", "")

    def type_name_at(self, x, y):
        outside = self.outside
        if outside is None:
            return ""
        if hasattr(outside, "type_name_at"):
            return outside.type_name_at(x, y)
        return getattr(outside, "type_name", "")

    @property
    def terrain_cover(self):
        outside = self.outside
        if outside is None:
            return (0, 0)
        return getattr(outside, "terrain_cover", (0, 0))

    def terrain_cover_at(self, x, y):
        outside = self.outside
        if outside is None:
            return (0, 0)
        if hasattr(outside, "terrain_cover_at"):
            return outside.terrain_cover_at(x, y)
        return getattr(outside, "terrain_cover", (0, 0))

    def high_ground_at(self, x, y):
        outside = self.outside
        if outside is None:
            return self.high_ground
        if hasattr(outside, "high_ground_at"):
            return outside.high_ground_at(x, y)
        return getattr(outside, "high_ground", False)

    def have_enough_space(self, new_object):
        capacity = self.container.transport_capacity
        for o in self.objects:
            capacity -= o.transport_volume
        return capacity >= new_object.transport_volume

    def find_free_space_for(self, o, x, y):
        return x, y

    def add(self, o):
        return

    def remove(self, o):
        return

    def update(self):
        for o in self.objects:
            o.x = self.container.x
            o.y = self.container.y
            o.update()


def format_zoom_target_id(place_id, x, y, precision=3):
    base = "zoom-{}-{}-{}".format(place_id, int(x), int(y))
    if precision != 3:
        return "{}-p{}".format(base, int(precision))
    return base


def parse_zoom_target_id(zoom_id):
    """Parse zoom target id → (place_id, x, y, precision)."""
    if not isinstance(zoom_id, str) or not zoom_id.startswith("zoom"):
        return None
    parts = zoom_id.split("-")
    if len(parts) < 4 or parts[0] != "zoom":
        return None
    precision = 3
    if len(parts) >= 5 and parts[4].startswith("p"):
        precision = int(parts[4][1:])
    return parts[1], int(parts[2]), int(parts[3]), precision


def zoom_cell_contains(place, precision, center_x, center_y, x, y):
    """Same zoom sub-cell as center at client F8 precision."""
    if place is None or precision <= 0:
        return False
    xmin = place.xmin
    ymin = place.ymin
    xmax = place.xmax
    ymax = place.ymax
    sub_w = (xmax - xmin) / precision
    sub_h = (ymax - ymin) / precision
    if sub_w <= 0 or sub_h <= 0:
        return int(center_x) == int(x) and int(center_y) == int(y)

    def _cell(px, py):
        ix = int((px - xmin) // sub_w)
        iy = int((py - ymin) // sub_h)
        ix = min(max(ix, 0), precision - 1)
        iy = min(max(iy, 0), precision - 1)
        return ix, iy

    return _cell(center_x, center_y) == _cell(x, y)


class ZoomTarget:

    collision = 0
    radius = 0
    # Round 4: 与 Entity 对齐, 让 is_an_enemy / o.player 等热路径直接 LOAD_ATTR
    player = None

    def __init__(self, place, x, y, id=None, precision=3):
        self.place = place
        self.x = x
        self.y = y
        self.id = id
        self.precision = precision
        self.title = self.place.title  # TODO: full zoom title

    def title_msg(self):
        """TTS：方格名 + 缩放子格坐标（与 F8 缩放模式一致，1 基）。"""
        from .lib.subcell_terrain import subcell_index

        precision = getattr(self, "precision", 3) or 3
        cx, cy = subcell_index(self.place, self.x, self.y, precision)
        return (
            (getattr(self.place, "title", []) or [])
            + mp.COMMA
            + nb2msg(cx + 1)
            + mp.DOT
            + nb2msg(cy + 1)
        )

    def __eq__(self, other):
        if isinstance(other, ZoomTarget):
            return self.x, self.y == other.x, other.y

    def __ne__(self, other):
        return not self.__eq__(other)

    @property
    def building_land(self):
        for o in self.place.objects:
            if o.is_a_building_land and self.contains(o.x, o.y):
                return o

    @property
    def exit(self):
        for o in self.place.exits:
            if not o.is_blocked() and self.contains(o.x, o.y):
                return o

    @property
    def any_land(self):
        for o in self.place.objects:
            if getattr(o, "is_buildable_anywhere", False) and self.contains(o.x, o.y):
                return
        return self

    def contains(self, x, y):
        precision = getattr(self, "precision", 3) or 3
        if zoom_cell_contains(self.place, precision, self.x, self.y, x, y):
            return True
        # Legacy 3×3 fallback for old zoom ids without precision suffix.
        subsquare = self.place.world.get_subsquare_id_from_xy
        return subsquare(self.x, self.y) == subsquare(x, y)


class QuadTree:
    """四叉树实现,用于空间划分和快速区域查询"""
    
    def __init__(self, boundary, max_objects=4, max_depth=6):
        self.boundary = boundary  # (xmin, ymin, xmax, ymax)
        self.max_objects = max_objects
        self.max_depth = max_depth
        self.objects = []
        self.divided = False
        self.nw = None
        self.ne = None
        self.sw = None
        self.se = None
        self.depth = 0
        
    def subdivide(self):
        """将节点分为四个子节点"""
        xmin, ymin, xmax, ymax = self.boundary
        xmid = (xmin + xmax) // 2
        ymid = (ymin + ymax) // 2
        
        # 创建四个子节点
        self.nw = QuadTree((xmin, ymid, xmid, ymax), self.max_objects, self.max_depth)
        self.ne = QuadTree((xmid, ymid, xmax, ymax), self.max_objects, self.max_depth)
        self.sw = QuadTree((xmin, ymin, xmid, ymid), self.max_objects, self.max_depth)
        self.se = QuadTree((xmid, ymin, xmax, ymid), self.max_objects, self.max_depth)
        
        # 设置子节点深度
        for child in (self.nw, self.ne, self.sw, self.se):
            child.depth = self.depth + 1
            
        self.divided = True
        
    def insert(self, obj):
        """插入对象到四叉树"""
        # 如果对象不在边界内,返回False
        if not self._in_boundary(obj):
            return False
            
        # 如果没有达到对象数量限制且未划分
        if len(self.objects) < self.max_objects and not self.divided:
            self.objects.append(obj)
            return True
            
        # 如果需要划分且未达到最大深度
        if not self.divided and self.depth < self.max_depth:
            self.subdivide()
            
            # 重新分配现有对象
            objects = self.objects
            self.objects = []
            for existing_obj in objects:
                self._insert_to_children(existing_obj)
                
        # 尝试插入到子节点
        if self.divided:
            return self._insert_to_children(obj)
            
        # 如果已达到最大深度,添加到当前节点
        self.objects.append(obj)
        return True
        
    def _insert_to_children(self, obj):
        """将对象插入到合适的子节点"""
        if self.nw.insert(obj): return True
        if self.ne.insert(obj): return True
        if self.sw.insert(obj): return True
        if self.se.insert(obj): return True
        return False
        
    def _in_boundary(self, obj):
        """检查对象是否在边界内"""
        xmin, ymin, xmax, ymax = self.boundary
        return (xmin <= obj.x < xmax and 
                ymin <= obj.y < ymax)
                
    def query_range(self, range_boundary):
        """查询指定范围内的所有对象"""
        found_objects = []
        
        # 如果查询范围与当前节点边界不相交,返回空列表
        if not self._intersects_boundary(range_boundary):
            return found_objects
            
        # 添加当前节点中的对象(如果在查询范围内)
        for obj in self.objects:
            if self._object_in_range(obj, range_boundary):
                found_objects.append(obj)
                
        # 如果已划分,递归查询子节点
        if self.divided:
            found_objects.extend(self.nw.query_range(range_boundary))
            found_objects.extend(self.ne.query_range(range_boundary))
            found_objects.extend(self.sw.query_range(range_boundary))
            found_objects.extend(self.se.query_range(range_boundary))
            
        return found_objects
        
    def _intersects_boundary(self, range_boundary):
        """检查两个边界是否相交"""
        xmin1, ymin1, xmax1, ymax1 = self.boundary
        xmin2, ymin2, xmax2, ymax2 = range_boundary
        return not (xmax1 < xmin2 or xmax2 < xmin1 or
                   ymax1 < ymin2 or ymax2 < ymin1)
                   
    def _object_in_range(self, obj, range_boundary):
        """检查对象是否在指定范围内"""
        xmin, ymin, xmax, ymax = range_boundary
        return (xmin <= obj.x < xmax and 
                ymin <= obj.y < ymax)
