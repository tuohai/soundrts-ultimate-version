"""
World核心模块 - World类的基础定义和核心方法
"""
import copy
import queue
import random
import re
import time
from hashlib import md5
from itertools import chain

from ..definitions import MAX_NB_OF_RESOURCE_TYPES, VIRTUAL_TIME_INTERVAL
from ..lib.log import exception, warning
from ..lib.nofloat import PRECISION, square_of_distance, to_int
from ..worldclient import DummyClient
from ..worldentity import COLLISION_RADIUS
from ..worldroom import Square
from ..lib import collision


class World:
    """游戏世界核心类"""

    # 是否为战役世界（默认否）。
    is_campaign = False
    # 合作战役难度：敌方（非人类、非中立）单位的生命/输出伤害相对标准值的百分比。
    # 100 = 原版强度。由 game.run / SpectatorGame.run 按对局难度写入实例属性；
    # 这里给出类级默认，保证普通对局、读档、测试等路径下读取永远安全。
    enemy_hp_factor = 100
    enemy_damage_factor = 100
    coop_difficulty = ""

    def __init__(self, default_triggers=None, seed=0):
        if default_triggers is None:
            default_triggers = []
        self.default_triggers = default_triggers
        self.seed = seed
        self.id = self.get_next_id()
        self.random = random.Random()
        self.random.seed(int(seed))
        self.time = 0
        self.squares = []
        self.active_objects = []
        self.players = []
        self.ex_players = []
        self.unit_classes = {}
        self.objects = {}
        self.harm_target_types = {}
        self._command_queue = queue.Queue()
        # Hybrid C++ ECS (Phase 1): opt-in via SOUNDRTS_ECS=1
        self._ecs = None
        try:
            from .world_ecs import WorldEcs, ecs_enabled

            if ecs_enabled():
                self._ecs = WorldEcs()
        except Exception:
            self._ecs = None
        # 本局是否锁定联盟（从地图/战役或游戏模式推导）
        self.alliances_locked = False
        # allied_control 热路径: 默认无移交; triggers 修改时置 True 并 bump epoch
        self._allied_control_active = False
        self._allied_control_epoch = 0
        self._allied_control_scanned = False

        # "map" properties
        self.title = []
        self.objective = []
        self.intro = []
        self.cut_scene = []
        self.timer_coefficient = 1
        self.map_music = None  # 添加map_music属性用于存储地图指定的背景音乐
        self.map_battle_music = None  # 添加map_battle_music属性用于存储地图指定的战斗音乐
        self.map_victory_sound = None  # 添加map_victory_sound属性用于存储地图指定的胜利音乐
        self.map_defeat_sound = None  # 添加map_defeat_sound属性用于存储地图指定的失败音乐

        self.map_objects = []
        # 地图矿藏初始储量（内部单位），用于结算开采率
        self.map_deposit_capacity = [0] * MAX_NB_OF_RESOURCE_TYPES

        self.computers_starts = []
        self.players_starts = []
        self.starting_units = []
        self.starting_resources = []  # just for the editor
        self.starting_population = 0  # just for the editor
        self.specific_starts = []  # just for the editor
        # 玩家固定出生点覆盖：{N(1-based): "x,y"(0-based normalized)}
        # 由地图指令 `player_start N <square>` 写入。
        # 解析末尾会用它"锁定" players_starts[N-1] 的所在格，
        # populate_map 时该 slot 会被 pin 给第 N 个 client（按 lobby 顺序）。
        # 详见 _apply_player_start_overrides / populate_map 的注释。
        self.player_start_overrides = {}

        # 标记：地图是否显式定义了初始单位/资源/专属起始
        self.map_defined_starting_units = False
        self.map_defined_starting_resources = False
        self.map_defined_starting_population = False
        self.map_defined_specific_starts = False

        self.square_width = 12  # default value
        self.subcell_precision = 3  # N×N sub-grid for sub-cell terrain (2–20, same as zoom)
        self.nb_lines = 0
        self.nb_columns = 0
        self.nb_rows = (
            0  # deprecated (was incorrectly used for columns instead of lines)
        )
        self.nb_meadows_by_square = 0
        self.nb_building_land_by_square = {}
        self.random_starts = 1  # 添加random_starts属性，默认值为1（启用随机起始位置）

        self.west_east = []
        self.south_north = []

        self.terrain = {}
        self.terrain_speed = {}
        self.terrain_cover = {}
        self.sub_terrain = {}
        self.sub_high_grounds = {}
        self.sub_terrain_speed = {}
        self.sub_terrain_cover = {}
        self.sub_water = {}
        self.sub_ground = {}
        self.sub_no_air = {}
        self.water_squares = set()
        self.no_air_squares = set()
        self.ground_squares = set()

        # 主方格命名支持
        # 映射：别名（地名等） -> 标准方格键 "x,y"
        self.name_to_square = {}
        # 兼容旧版：标准方格键 "x,y" -> 别名（若仅定义一层别名时仍使用）
        self.square_names = {}
        # 分层命名：
        #   - province：每个坐标可归属一个“主区域（省/大区等）”
        #   - city：每个坐标一个“二级区域（市/郡等）”
        #   - district：每个坐标一个“三级区域（区/街道等）”
        self.square_cities = {}
        self.square_provinces = {}
        self.square_districts = {}

        # "squares words"
        self.starting_squares = []
        self.additional_meadows = []
        self.additional_build_sites = []
        self.additional_building_land = []
        self.remove_meadows = []
        from ..worldresource import default_building_land_type

        self.building_land = default_building_land_type()
        self._map_building_land_explicit = False
        self.high_grounds = []

        self.nb_players_min = 1
        self.nb_players_max = 1
        # 添加事件调度列表
        self._scheduled_events = []
        # 条约结束时间（毫秒，0表示无条约）
        self.treaty_until_time = 0

        # Build fields: live providers (psi) + persistent square marks (creep).
        self._build_field_provider_ids = set()
        self._build_field_marked_squares = {}

        # D-Phase 1 T1: 帧级 sight cache.
        # key: (place_id, sight_range) -> frozenset(Square).
        # 同一 (place, sight_range) 在一个 VIRTUAL_TIME_INTERVAL bucket 内复用,
        # 不同 bucket 整体替换 (无需逐 key 清理).
        self._sights_cache: dict = {}
        self._sights_cache_bucket: int = -1

    def schedule_after(self, delay_ms: int, callback):
        """
        调度一个回调函数在指定延迟后执行
        
        Args:
            delay_ms: 延迟执行的毫秒数
            callback: 延迟后要执行的回调函数
        """
        execution_time = self.time + delay_ms
        self._scheduled_events.append((execution_time, callback))

    def __repr__(self):
        return "World(%s)" % self.seed

    def __getstate__(self):
        from ..save_pickle import WORLD_STRIP_ON_SAVE, pop_keys

        odict = self.__dict__.copy()
        del odict["_command_queue"]
        pop_keys(odict, WORLD_STRIP_ON_SAVE)
        return odict

    def __setstate__(self, dict):
        from ..save_pickle import rebuild_world_after_load

        self.__dict__.update(dict)
        self._command_queue = queue.Queue()
        rebuild_world_after_load(self)

    @property
    def turn(self):
        return self.time // VIRTUAL_TIME_INTERVAL

    _next_id = 0  # reset ID for each world to avoid big numbers

    def get_next_id(self, increment=True):
        if increment:
            self._next_id += 1
            return str(self._next_id)
        else:
            return str(self._next_id + 1)

    def register_entity(self, o):
        o.id = self.get_next_id()
        self.objects[o.id] = o
        if hasattr(o, "update"):
            self.active_objects.append(o)
        if self._ecs is not None:
            self._ecs.register(o)

    def unregister_entity(self, o):
        if self._ecs is not None:
            self._ecs.unregister(o)
        if o in self.active_objects:
            self.active_objects.remove(o)

    # Why use a different id for orders: get_next_id() would have worked too,
    # but with higher risks of synchronization errors. This way is probably
    # more sturdy.

    _next_order_id = 0

    def get_next_order_id(self):
        self._next_order_id += 1
        return self._next_order_id

    current_player_number = 0

    def get_next_player_number(self):
        self.current_player_number += 1
        return self.current_player_number

    def get_place_from_xy(self, x, y):
        return self.grid.get((x // self.square_width, y // self.square_width))

    def get_subsquare_id_from_xy(self, x, y):
        return x * 3 // self.square_width, y * 3 // self.square_width

    def _free_memory(self):
        for p in self.players + self.ex_players:
            p.clean()
        for z in self.squares:
            z.clean()
        self.__dict__ = {}

    def _get_objects_values(self):
        # 回退到1.3.8.1的简单同步检查
        yield str(self.random.getstate())

    def get_objects_string(self):
        return "\n".join(self._get_objects_values())

    def get_digest(self):
        d = md5(bytes(self.time))
        for p in self.players:
            d.update(bytes(len(p.units)))
        for z in self.squares:
            d.update(bytes(len(z.objects)))
        for ov in self._get_objects_values():
            d.update(ov.encode())
        return d.hexdigest()

    previous_state = (0, b"")

    def _record_sync_debug_info(self):
        try:
            self.previous_previous_state = self.previous_state
        except AttributeError:
            pass
        self.previous_state = self.time, self.get_objects_string().encode()

    def cpu_intensive_players(self):
        return [p for p in self.players if p.is_cpu_intensive]

    # game status methods
    def current_nb_human_players(self):
        n = 0
        for p in self.players:
            if p.is_human and not getattr(p, '_is_pure_spectator', False):
                n += 1
        return n

    def true_players(self):
        return [p for p in self.players if not p.neutral and not getattr(p, '_is_pure_spectator', False)]

    @property
    def true_playing_players(self):
        return [p for p in self.true_players() if p.is_playing and not getattr(p, '_is_pure_spectator', False)]

    @property
    def match_participating_players(self):
        # 仍在对局中的胜负参与者：真人、邀请的电脑对手等。
        # 地图脚本 NPC（ai_timers）、战役触发器电脑、纯野生动物等
        # broadcasts_defeat_and_quit=False，不计入"还有玩家在打"。
        return [p for p in self.true_playing_players if p.broadcasts_defeat_and_quit]

    @property
    def at_least_two_camps(self):
        participants = self.match_participating_players
        if not participants:
            return False
        first_camp = participants[0].allied_victory
        for player in participants:
            if player not in first_camp:
                return True

    @property
    def population_limit(self):
        return self.global_population_limit

    def update_alliances(self):
        for p in self.players:
            p.update_alliance()

    def stop(self):
        self._must_loop = False

    def queue_command(self, player, order):
        self._command_queue.put((player, order))


# Global constants
GLOBAL_population_LIMIT = 80
PROFILE = False


def check_squares(line, squares):
    for sq in squares[:]:
        # 新格式: "x,y"，允许负号和空格
        if re.match(r"^\s*-?\d+\s*,\s*-?\d+\s*$", sq):
            continue
        # 兼容旧格式 a1：仅警告
        if re.match("^[a-z]+[0-9]+$", sq):
            continue
        map_warning(line, "%s is not a square name" % sq)
        squares.remove(sq)


def start_population_bonus(start):
    """Extra population cap stored on a map start entry (not from buildings)."""
    if not start or not isinstance(start, list):
        return 0
    if len(start) >= 5 and isinstance(start[4], int):
        return start[4]
    if len(start) >= 4 and isinstance(start[3], int):
        return start[3]
    return 0


def convert_and_split_first_numbers(words):
    i = -1
    for i, w in enumerate(words):
        try:
            words[i] = to_int(w)
        except ValueError:
            i -= 1
            break
    return words[:i + 1], words[i + 1:]


class MapError(Exception):
    pass


def map_error(line, msg):
    raise MapError(_formatted_msg(line, msg))


def map_warning(line, msg):
    warning(_formatted_msg(line, msg))


def _formatted_msg(line, msg):
    if line:
        msg += f' (in "{line}")'
    return msg