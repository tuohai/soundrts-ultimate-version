"""玩家基础类和初始化模块"""

import copy
import inspect
import re
from typing import Dict, List, Union

from ..worldaction import AttackAction
from .. import msgparts as mp
from ..definitions import MAX_NB_OF_RESOURCE_TYPES, rules, style
from ..lib import group
from ..lib.log import exception, info, warning
from ..lib.square_terrain_rules import squares_same_ground_region
from ..lib.msgs import encode_msg, nb2msg
from ..lib.nofloat import PRECISION, square_of_distance, to_int
from ..worldplayerstats import Stats
from ..worldskill import Skill
from ..worldentity import NotEnoughSpaceError
from ..worldexit import Exit
from ..worldresource import Corpse, Deposit
from ..worldroom import Square, ZoomTarget
from ..worldunit import BuildingSite
from ..worldunit import Soldier
from ..worldunit import Unit
from ..objective_announce import collect_planned_objective_numbers

A = 12 * PRECISION  # bucket side length
VERY_SLOW = int(0.01 * PRECISION)


_UNSET_ALLIANCE = (None, "None", "ai")


def normalize_alliance_id(aid):
    if aid in _UNSET_ALLIANCE:
        return aid
    try:
        return int(aid)
    except (TypeError, ValueError):
        return aid


def alliance_ids_equal(a, b):
    if a in _UNSET_ALLIANCE or b in _UNSET_ALLIANCE:
        return a == b
    return normalize_alliance_id(a) == normalize_alliance_id(b)


def is_wildlife_unit(unit):
    """狩猎/畜牧动物（鹿、羊、野猪等）。"""
    return bool(getattr(unit, "is_huntable", 0) or getattr(unit, "herdable", 0))


def player_is_wildlife_only(player):
    """玩家名下所有存活单位均为野生动物。"""
    units = [u for u in getattr(player, "units", []) if getattr(u, "presence", True)]
    if not units:
        return False
    return all(is_wildlife_unit(u) for u in units)


def computer_start_is_wildlife_only(start):
    """``computer_only`` 槽位是否只会生成狩猎/畜牧动物。"""
    if len(start) < 2:
        return False
    unit_classes = []
    for item in start[1]:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        unit_cls = item[1]
        if unit_cls is None or isinstance(unit_cls, str):
            continue
        unit_classes.append(unit_cls)
    if not unit_classes:
        return False
    return all(
        getattr(unit_cls, "is_huntable", 0) or getattr(unit_cls, "herdable", 0)
        for unit_cls in unit_classes
    )


class Objective:
    def __init__(self, number, description, optional=False):
        self.number = number
        self.description = description
        self.optional = optional

    @staticmethod
    def storage_key(number, optional=False):
        """主要目标与可选目标各自独立编号，存储键不冲突。"""
        return ("secondary", str(number)) if optional else ("primary", str(number))


from .allied_control import allied_control_controller_for, mark_allied_control_changed


class Player:
    """游戏玩家类 - 基础功能和初始化"""
    
    resources: List[int]
    triggers: list
    _buckets: Dict[tuple, list]

    cheatmode = False
    used_population = 0
    population = 0
    observer_if_defeated = False
    has_victory = False
    has_been_defeated = False
    faction = "human_faction"
    memory_duration = 3 * 60 * 1000  # 3 minutes of world time

    # === Round 3: 类级 (跨所有玩家共享) 视野缓存 ===
    # 改为 {player_id -> {cache_key -> data}} 二级结构,
    # 让 _clear_vision_cache 的清理从 O(N_total_keys) 退化为 O(1).
    # 在类体声明保证总是存在, 省掉 hasattr/_global_vision_cache 防御性检查.
    _global_vision_cache: Dict[int, Dict[tuple, bool]] = {}
    _observed_squares_cache: Dict[int, Dict[tuple, tuple]] = {}
    _observed_squares_cache_timestamp: Dict[int, Dict[tuple, int]] = {}
    _last_vision_cleanup = 0
    _vision_cache_hits = 0
    _vision_cache_misses = 0

    # === Round 4: _update_perception 类级 cache ===
    _global_update_cycle = 0
    _last_global_update_time = 0
    _allied_vision_cache: Dict[tuple, dict] = {}
    _allied_vision_timestamp: Dict[tuple, int] = {}

    # === Round 4: _bulk_visibility_check 类级 cache ===
    # 每帧每单位调一次, 原版 5+ 个 hasattr per call.
    _vision_cache_last_cleanup = 0
    _observed_union_cache: Dict[int, set] = {}
    _observed_union_bucket = -1
    _place_covering_units_cache: Dict = {}
    _place_covering_units_bucket = -1
    _place_visible_cache: Dict[int, Dict] = {}
    _place_visible_bucket = -1
    _place_visible_history: Dict[tuple, tuple] = {}

    group = ()
    group_had_enough_mana = False  # used to warn if not enough mana

    AI_type = ""
    is_cpu_intensive = False
    smart_units = False

    groups: Dict[str, List[Unit]] = {}

    def __init__(self, world, client):
        self.stats = Stats(self)
        self._counterattack_places = []
        self.neutral = client.neutral
        self.faction = (
            world.random.choice(rules.factions)
            if client.faction == "random_faction"
            else client.faction
        )
        self.allied = [self]
        if not self.neutral:
            self.number = world.get_next_player_number()
        else:
            self.number = None
        # Round 5: duck-type Player as its own owner so `o.player` works
        # uniformly for both Entity (where player = owner) and Player
        # (where player = self). is_an_enemy(o) at combat.py:308 does a
        # direct `o.player` LOAD_ATTR; Round 4 added the class-level
        # default to Entity / ZoomTarget / TempTarget but missed Player
        # itself, so `Computer.player` blew up on every AI decide().
        self.player = self
        self.perception = set()
        self.memory = set()
        self._memory_index = {}
        # place -> set(memory): speeds observed-square ghost clears
        self._memory_by_place = {}
        self._memory_by_place_count = 0
        self.id = world.get_next_id()
        self.world = world
        self.client = client
        self.ia_start_index = 0
        self.ia_index = 0
        self.objectives = {}
        self._required_objective_numbers = set()
        self._completed_objective_numbers = set()
        self.units = []
        self.budget = []
        self.upgrades = []
        self.forbidden_techs = []
        self.triggers = []  # 初始化 triggers 属性，避免 AttributeError
        # 时代（phase）系统状态
        self.current_phase = None  # 玩家最近研究的 phase 名称
        self._phase_bonus_pool = []  # 已研究 phase 累积的非成本加成参数列表
        self.resources = [0] * MAX_NB_OF_RESOURCE_TYPES  # 初始化 resources 属性，避免 AttributeError
        self.storage_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES  # 初始化 storage_bonus 属性
        self.gathered_resources = [0] * MAX_NB_OF_RESOURCE_TYPES  # 初始化 gathered_resources 属性
        self.observed_before_squares = set()
        self.strictly_observed_before_squares = set()
        self.observed_squares = set()
        self.partially_observed_squares = set()
        self.observed_objects = {}
        # 动态外交状态：单向结盟请求与关系
        self._ally_requests_from = set()  # 收到的结盟请求：对方玩家id集合
        self._alliance_declined_from = set()  # 已拒绝的结盟申请：对方玩家id集合
        self._ally_relations_one_way = set()  # 我单方面视为盟友的玩家id（未对方确认）
        self.detected_units = set()
        self.allied_control = (self,)
        self.allied_control_units_set = set()
        self._known_enemies = {}
        self._known_enemies_time = {}
        # Mutable triple updated in-place to avoid Player.__setattr__ on hot path.
        self._known_enemies_hit = [None, -1, ()]  # place, time, result
        self._enemy_menace = {}
        self._enemy_menace_time = {}
        self._subsquare_threat = {}
        self.new_enemy_units = []  # 初始化新发现的敌方单位列表
        # 空间网格索引；由 World._update_buckets 增量维护（冷启动全量构建）。
        # `_bucket_unit_cells` 为 None 表示尚未建立增量状态。
        self._buckets = {}
        self._bucket_unit_cells = None
        self._bucket_ticks_since_heal = 0
        # known_enemies hot path 用到的缓存; 预初始化避免每次 hasattr 检查
        # (实测: known_enemies 17.9M calls, 原版每次 4-5 个 hasattr/getattr)
        self._enemy_units_cache = []
        self._enemy_units_cache_time = -1_000_000
        self._cached_enemy_players = []
        self._enemy_players_cache_time = -1_000_000
        self._enemy_units_set = frozenset()
        self._enemy_units_set_time = -1
        self._enemy_inside_units = ()
        self._perception_set = frozenset()
        self._perception_set_time = -1

        # === Round 3: 批量预初始化 23 处懒 hasattr 缓存 ===
        # 这些属性分散在 perception.py / base.py / combat.py 各热函数里, 原本
        # 每次访问都做 `if not hasattr(self, '_xxx')` 检查. 集中预初始化后,
        # 调用方可直接读取属性, 省掉 PyObject_HasAttr 慢路径.
        # 时间戳类用 -1_000_000 (远古) 保证首帧触发"过期重建"分支.

        # 修复: perception._update_perception 用了 `(self.id or 0) % 9`,
        # 但 world.get_next_id() 返回 str, "1" % 9 触发字符串格式化, 每帧
        # 每玩家抛 TypeError 被外层 try/except 静默吞掉 (实测 60s game 2109 次).
        # 在此处一次性预算分组, 之后直接 LOAD_ATTR.
        try:
            self._player_group_mod9 = (int(self.id) if self.id else 0) % 9
        except (TypeError, ValueError):
            self._player_group_mod9 = abs(hash(self.id)) % 9

        # Perception 热路径缓存
        self._allied_exploration_cache = {}
        self._allied_exploration_timestamp = 0
        self._cached_alliance_ids = ()
        self._cached_alliance_time = -1_000_000
        self._cached_allied_ids = ()
        self._cached_allied_time = -1_000_000
        self._cached_enemy_units_hash = None
        self._cached_sorted_enemy_units = []
        self._last_unit_positions = {}
        self._last_perception_hash = 0
        self._last_positions_hash = 0
        self._force_full_update = True
        self._last_forced_perception_update = 0
        self._last_gc_time = 0
        self._vision_cover_counts = {}
        self._last_perception_update = -1_000_000  # Round 4
        self._last_memory_cleanup = 0
        # Round 4: _bulk_visibility_check 实例级 cache
        self._nearby_units_cache = {}
        self._nearby_units_cache_bucket = -1
        # 静态视野复用：observed/partial 未变时跳过 bulk
        self._cached_static_perception = None
        self._prev_obs_squares = None
        self._prev_partial_squares = None
        self._memory_scan_cursor = 0
        self._memory_list = []
        self._memory_list_snapshot_time = -1_000_000

        # allied_vision property 缓存
        self._cached_allied_vision = None
        self._allied_vision_cache_time = -1_000_000

        # 经济 / 仓库 缓存 (nearest_warehouse)
        self._warehouse_cache = {}
        self._warehouse_candidates_cache = {}
        self._warehouse_candidates_bucket = -1
        self._place_distance_cache = {}
        self._place_distance_cache_bucket = -1

        # 盟友单位聚合缓存
        self._allied_units_cache = None
        self._allied_units_timestamp = 0
        self._allied_units_count = -1
        self._allied_military_cache = None
        self._allied_military_timestamp = 0

        # Combat 缓存
        self._enemy_menace_cache = {}
        self._enemy_menace_cache_time = 0
        self._cached_enemy_units = set()
        self._cached_enemy_units_time = 0
        self._balance_cache = {}
        self._balance_cache_time = {}
        self._enemy_player_cache = {}
        self._enemy_player_timestamp = 0
        
        # 初始化成本降低相关属性
        self.cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        self.population_cost_bonus = 0
        self.time_cost_bonus = 0
        # 添加百分比成本降低属性
        self.cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        self.population_cost_percent_bonus = 0.0
        self.time_cost_percent_bonus = 0.0
        
        # 时代（phase）专用：训练/建造/研究等全局成本修正，与科技 can_use 判定无关
        self.phase_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        self.phase_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        self.phase_time_cost_bonus = 0
        self.phase_time_cost_percent_bonus = 0.0
        self.phase_population_cost_bonus = 0
        self.phase_population_cost_percent_bonus = 0.0
        
        # 添加生产相关的修正属性
        self.production_cost_bonus = [0] * MAX_NB_OF_RESOURCE_TYPES
        self.production_time_bonus = 0
        self.production_qty_bonus = 0
        self.production_cost_percent_bonus = [0.0] * MAX_NB_OF_RESOURCE_TYPES
        self.production_time_percent_bonus = 0.0
        self.production_qty_percent_bonus = 0.0
        
        # 初始化空间索引
        self._init_spatial_index()
        
        # 确保世界有区域图
        self._ensure_world_regions()

    def __setattr__(self, name, value):
        """确保人口相关字段不为负数。
        
        统一在赋值入口做下限保护，避免在各处加/减操作后出现负数。
        """
        if name in ("population", "used_population"):
            try:
                if value < 0:
                    value = 0
            except Exception:
                pass
        object.__setattr__(self, name, value)

    @property
    def name(self):
        if self.neutral:
            # 给中立玩家一个可播报的"中立 N"名字：
            # N = 在 world.players 中、按出现顺序的 1-based 中立序号。
            # 让 F12 候选、cmd_say_players、ALLIANCE_REQUEST_FROM/ACCEPTED_WITH
            # 等所有 `p.name` 用法都能区分多 creep 阵营。
            idx = 1
            try:
                for p in self.world.players:
                    if p is self:
                        break
                    if getattr(p, "neutral", False):
                        idx += 1
            except Exception:
                idx = 1
            return mp.NEUTRAL + nb2msg(idx)
        if self.is_script_npc:
            # 触发器脚本电脑（ai_timers 等）对外播报统一为 "NPC"，与实体 title、
            # 切换视角一致；避免结盟请求等语音读出内部 login。
            try:
                npc_title = style.get("ai_timers", "title", warn_if_not_found=False)
                if npc_title:
                    return npc_title
            except Exception:
                pass
            return ["NPC"]
        return self.client.name

    @property
    def is_playing(self):
        return not (self.has_victory or self.has_been_defeated)

    def _has_other_playing_humans(self):
        """True if another human is still active in the match."""
        for p in self.world.true_playing_players:
            if p is self:
                continue
            if p.is_human and not getattr(p, "_is_pure_spectator", False):
                return True
        return False

    def _all_required_objectives_done(self):
        required = getattr(self, "_required_objective_numbers", set())
        completed = getattr(self, "_completed_objective_numbers", set())
        return required <= completed

    def _try_mission_victory(self):
        if self.has_victory or not self._all_required_objectives_done():
            return
        from .. import msgparts as mp

        self.send_voice_important(mp.MISSION_COMPLETE)
        self.victory()

    def add(self, unit):
        # 防止观战者获得任何单位
        if hasattr(self, '_is_pure_spectator') and self._is_pure_spectator:
            warning("Attempted to add unit to spectator player, ignoring")
            unit.delete()  # 删除尝试添加给观战者的单位
            return
            
        unit.number = unit.next_free_number()
        self.units.append(unit)
        self.population += unit.population_provided
        # 优先使用单位记录的实际人口消耗（若存在）
        try:
            eff = getattr(unit, 'effective_population_cost', None)
            if eff is None:
                eff = unit.population_cost
            self.used_population += int(eff)
        except Exception:
            self.used_population += unit.population_cost
        unit.upgrade_to_player_level()
        # 中立电脑（`computer_only ... neutral`）的所有 Creature 默认改为
        # guard + counterattack：不主动攻击，被打才反击，符合 RTS creep 习惯。
        # 现有机制：`decide()` (world_ai_decision.py 第 173-185 行) 在 guard
        # 模式下只对 `last_attacker` 反击；`receive_hit` 会自动写
        # `last_attacker`；`_notify_units_in_place` 会唤醒同格/邻格 guard 友军。
        # 必须在 Creature.__init__ 之后覆盖（其 __init__ 写死 ai_mode="offensive"）。
        if self.neutral:
            from ..worldunit.worldcreature import Creature
            if isinstance(unit, Creature):
                unit.ai_mode = "guard"
                unit.counterattack_enabled = True
        # 应用已研究 phase（时代）累积的非成本加成到新加入的单位
        try:
            from ..worldphase import Phase
            Phase.apply_pool_to_unit(unit)
        except Exception as e:
            warning("error applying phase pool to unit %s: %s",
                    getattr(unit, "type_name", unit), str(e))
        # player units must stop attacking the "not hostile anymore" unit
        for u in self.units:
            if u.action_target is unit:
                u.stop()
        # note: updating perception so quickly shouldn't be necessary
        # (now that perception isn't strictly limited to squares)
        # It doesn't take time though.
        for p in self.allied_vision:
            p.perception.add(unit)  # necessary for example for new building sites

    def remove(self, unit):
        self.units.remove(unit)
        self.population -= unit.population_provided
        # 返还与创建时一致的人口消耗
        try:
            eff = getattr(unit, 'effective_population_cost', None)
            if eff is None:
                eff = unit.population_cost
            self.used_population -= int(eff)
        except Exception:
            self.used_population -= unit.population_cost

    @property
    def allied_victory(self):
        return self.allied

    @property
    def allied_vision(self):
        # 优化：缓存allied_vision结果，避免重复计算
        current_time = self.world.time
        cache_interval = 1000  # 1秒缓存
        
        # (_allied_vision_cache_time / _cached_allied_vision 已在 __init__ 预初始化)
        if current_time - self._allied_vision_cache_time > cache_interval:
            # 地图 ``computer_only`` 脚本 NPC（含非中立）在 alliance "ai" 下彼此
            # 结盟是为了互不残杀；但不应共享战争迷雾，否则切到任一 NPC 视角时
            # 能看见其它敌对营地。战役/难度电脑等非 script NPC 仍用完整 allied。
            if self.is_script_npc:
                self._cached_allied_vision = [self]
            else:
                self._cached_allied_vision = self.allied
            self._allied_vision_cache_time = current_time
            
        return self._cached_allied_vision

    def level(self, type_name):
        return self.upgrades.count(type_name)

    def has(self, type_name):
        if type_name in self.upgrades:
            return True
        for u in self.units:
            if u.type_name == type_name or type_name in u.expanded_is_a:
                return True
        return False

    def has_all(self, type_names):
        for t in type_names:
            if not self.has(t):
                return False
        return True

    def get_object_by_id(self, i):
        if isinstance(i, str) and i.startswith("zoom"):
            from ..worldroom import ZoomTarget, parse_zoom_target_id

            parsed = parse_zoom_target_id(i)
            if parsed is None:
                return None
            place_id, x, y, precision = parsed
            o = ZoomTarget(
                self.get_object_by_id(place_id), x, y, id=i, precision=precision
            )
            return o

        # 兼容地图触发器中的坐标与别名：
        # - 支持旧式字母+数字坐标（如 a1, n1 等，转为 0 基 "x,y"）
        # - 支持方括号或无括号的一基坐标（如 "(5,7)" 或 "5,7"，转为 0 基）
        # - 支持通过 square_name 定义的别名（self.world.name_to_square 存储的一基坐标）
        if isinstance(i, str):
            token = i.strip()
            # 优先处理通过 square_name 定义的别名（值为一基坐标字符串）
            try:
                if hasattr(self.world, "name_to_square") and token in self.world.name_to_square:
                    token = self.world.name_to_square[token]
            except Exception:
                pass

            # 去除可选的小括号
            if token.startswith("(") and token.endswith(")"):
                token = token[1:-1].strip()

            # 一基数字坐标："x,y" -> 转 0 基
            if "," in token:
                parts = token.split(",")
                if len(parts) == 2:
                    try:
                        col1 = int(parts[0].strip())
                        row1 = int(parts[1].strip())
                        key0 = f"{col1-1},{row1-1}"
                        if key0 in self.world.grid:
                            return self.world.grid[key0]
                        tup0 = (col1-1, row1-1)
                        if tup0 in self.world.grid:
                            return self.world.grid[tup0]
                    except ValueError:
                        pass

            # 旧式 a1/a12 坐标：按 26 进制字母列转为 0 基
            if re.match(r"^[a-z]+[0-9]+$", token):
                letters = ''.join([c for c in token if c.isalpha()])
                digits = ''.join([c for c in token if c.isdigit()])
                col = 0
                for ch in letters:
                    col = col * 26 + (ord(ch) - ord('a') + 1)
                col -= 1
                try:
                    row = int(digits) - 1
                    key0 = f"{col},{row}"
                    if key0 in self.world.grid:
                        return self.world.grid[key0]
                    tup0 = (col, row)
                    if tup0 in self.world.grid:
                        return self.world.grid[tup0]
                except ValueError:
                    pass

        if i in self.world.grid:
            return self.world.grid[i]
        if i in self.world.objects:
            o = self.world.objects[i]
            if isinstance(o, Square):
                return o
            if o.place and o in self.perception:
                return o
        for o in self.memory:
            if o.id == i:
                return o

    def updated_target(self, target):
        if (
                isinstance(target, (ZoomTarget, Square))  # doesn't change
                or ((target in self.perception or target in self.memory) and target.place)
        ):
            return target
        new_target = self.get_object_by_id(target.id)
        # 如果解析得到的是记忆对象，但其真实对象已被删除，则返回 None，避免后续继续尝试
        try:
            if getattr(new_target, "is_memory", False):
                real = getattr(new_target, "initial_model", None)
                if real is None or (getattr(real, "place", None) is None and not hasattr(real, "find_free_space_for")):
                    return None
            # 兼容性：若目标本身就是实体但已无位置，也视为失效
            if new_target is not None and getattr(new_target, "place", None) is None and not hasattr(new_target, "find_free_space_for"):
                return None
        except Exception:
            pass
        return new_target

    def is_local_human(self):
        return hasattr(self.client, "interface")

    def has_quit(self):
        return self not in self.world.players

    @property
    def is_campaign_npc(self):
        # 战役里所有电脑（含被 (ai ...) 升格的、login 仍是 ai_timers 的）都是无身份的
        # 触发器 NPC：播报归属时统一为 "NPC"，被击败/退出游戏不打扰玩家。
        # 仅凭 AI_type == "timers" 无法覆盖被 (ai easy) 升格的电脑（AI_type 变了
        # 但 login 仍是 ai_timers），故以"战役里的非人类玩家"作为统一判据。
        return getattr(self.world, "is_campaign", False) and not self.is_human

    @property
    def broadcasts_defeat_and_quit(self):
        # 应对局参与者（真人、邀请的电脑对手）才播报被击败/退出；地图脚本 NPC、
        # 狩猎动物、战役触发器电脑等不算"玩家胜负"，静默处理。
        if self.is_campaign_npc:
            return False
        if player_is_wildlife_only(self):
            return False
        if getattr(self, "AI_type", "") == "timers":
            return False
        login = getattr(getattr(self, "client", None), "login", "") or ""
        if login == "ai_timers":
            return False
        return True

    @property
    def is_script_npc(self):
        # "无具体身份的脚本电脑"——播报其*归属/身份*时统一显示为 "NPC"，而不是
        # 读出内部 login（如 "ai_timers"）。两类来源：
        #   1. 战役里的电脑（is_campaign_npc，含被 (ai ...) 升格、AI_type 已不是
        #      "timers" 的）；
        #   2. 任意地图（如 td2）里的 ``computer_only`` / ``computer`` 脚本 AI
        #      ——它们 AI_type=="timers"、login "ai_timers"，并非真人对手。
        # 仅判 is_campaign_npc 会漏掉第 2 种（非战役地图，正是 td2 按 Ctrl+Shift+F4
        # 切视角时读出 "ai_timers" 的 bug）；仅判 AI_type=="timers" 会漏掉第 1 种。
        # 故二者取或。用于"显示身份"的场景（实体 title、切换视角播报）。
        # 被击败/退出是否广播见 broadcasts_defeat_and_quit。
        return self.is_campaign_npc or getattr(self, "AI_type", "") == "timers"

    def quit_game(self):
        self.push("quit")
        # 地图脚本 NPC、战役电脑等不算对局参与者，退出时不播报。
        if self in self.world.true_players() and self.broadcasts_defeat_and_quit:
            self.broadcast_to_others_only(self.name + mp.HAS_JUST_QUIT_GAME)
        for u in self.units[:]:
            u.delete()
        self.world.players.remove(self)
        self.world.ex_players.append(self)
        
        # 立即检查剩余玩家的胜利条件
        # 玩家退出后需要立即检查胜利条件，而不是等到下一个slow_update周期
        self._check_victory_conditions_after_player_change()

    def _check_victory_conditions_after_player_change(self):
        """在玩家状态变化后立即检查胜利条件
        
        这个方法会被在以下情况调用：
        - 玩家退出游戏时
        - 玩家被击败时
        - 其他可能影响胜利条件的玩家状态变化时
        """
        # 避免重复检查的标记
        if hasattr(self.world, '_checking_victory_conditions'):
            return
            
        try:
            self.world._checking_victory_conditions = True
            
            # 为所有剩余的真实玩家检查胜利条件
            for remaining_player in self.world.players[:]:
                if (remaining_player != self and 
                    hasattr(remaining_player, 'run_triggers') and
                    not getattr(remaining_player, '_is_pure_spectator', False)):
                    try:
                        remaining_player.run_triggers()
                    except:
                        # 如果触发器执行出错，继续检查其他玩家
                        pass
        finally:
            # 确保清除标记
            if hasattr(self.world, '_checking_victory_conditions'):
                delattr(self.world, '_checking_victory_conditions')

    def clean(self):
        self.client.player = None
        self.__dict__ = {}

    is_human = False

    def push(self, *args):
        if self.client:
            self.client.push(*args)

    def execute_command(self, data):
        args = data.split()
        cmd = "cmd_" + args[0].lower()
        if hasattr(self, cmd):
            getattr(self, cmd)(args[1:])
        else:
            warning(f"unknown command: '{cmd}' ({data})")

    # ===== 动态联盟：服务器侧命令 =====
    def _resolve_player_by_id(self, pid):
        for p in self.world.players:
            if p.id == pid:
                return p
        return None

    def _alliances_locked_now(self):
        # 若世界标记锁定，或由地图预置为合作战役固定同盟
        return bool(getattr(self.world, 'alliances_locked', False))

    def cmd_diplomacy(self, args):
        if not args:
            return
        action = args[0]
        target_id = args[1] if len(args) > 1 else None
        if self._alliances_locked_now():
            # 提示锁定
            if self.is_local_human():
                self.send_voice_important(mp.ALLIANCES_LOCKED)
            return
        # 针对 accept/decline_or_cancel，允许省略目标，由服务器选择最近的待处理请求
        if action in ('accept', 'decline_or_cancel') and not target_id:
            # 1) 优先选择一个收到的待处理请求
            if self._ally_requests_from:
                try:
                    target_id = next(iter(self._ally_requests_from))
                except Exception:
                    target_id = None
            # 2) 若是撤销/取消操作，且没有收到请求，则尝试查找发出的待处理请求（扫描全局）
            if action == 'decline_or_cancel' and not target_id:
                try:
                    for p in self.world.players:
                        if p is not self and hasattr(p, '_ally_requests_from') and self.id in p._ally_requests_from:
                            target_id = p.id
                            break
                except Exception:
                    pass
            # 3) 若仍无目标，尝试选择同盟中的任意一名盟友用于取消
            if action == 'decline_or_cancel' and not target_id:
                my_aid = getattr(self.client, 'alliance', None)
                if my_aid not in [None, 'None']:
                    for p in self.world.players:
                        if p is not self and getattr(p.client, 'alliance', None) == my_aid:
                            target_id = p.id
                            break
            if not target_id:
                # 无候选
                if self.is_local_human():
                    self.send_voice_important(mp.DIPLOMACY + mp.NO_CANDIDATE)
                return
        if not target_id:
            return
        target = self._resolve_player_by_id(target_id)
        if target is None or target is self:
            return
        if action == 'request':
            # 不允许与中立 (`computer_only ... neutral`) 结盟：中立 creep 被
            # 当成"环境/事件物"，不参与外交。F12 列表里也不会出现，但脚本/旧
            # 协议直接通过 id 走过来时这里再兜底。
            if getattr(target, 'neutral', False):
                if self.is_local_human():
                    self.send_voice_important(mp.DIPLOMACY + mp.NO_CANDIDATE)
                return
            # 已经是盟友？直接短路，不写冷却、不打扰对方。
            # 用 mp.DIPLOMACY + mp.ALLY + target.name 给本人一个简短反馈
            # （"外交，盟友 X"），让用户明白为啥没动作。
            try:
                already_ally = target in getattr(self, 'allied', [])
            except Exception:
                already_ally = False
            if already_ally:
                if self.is_local_human():
                    try:
                        self.send_voice_important(mp.DIPLOMACY + mp.ALLY + target.name)
                    except Exception:
                        self.send_voice_important(mp.DIPLOMACY + mp.ALLY)
                return
            # 频率限制：对同一目标每分钟仅能发送一次结盟申请
            try:
                last_map = getattr(self, '_last_alliance_request_to', None)
            except Exception:
                last_map = None
            if not isinstance(last_map, dict):
                last_map = {}
                self._last_alliance_request_to = last_map
            last = last_map.get(target.id, -10**9)
            if self.world.time - last < 60000:
                if self.is_local_human():
                    try:
                        remaining = max(0, 60000 - (self.world.time - last)) // 1000
                        if remaining > 0:
                            self.send_voice_important(mp.TOO_EARLY + nb2msg(int(remaining)) + mp.SECONDS)
                        else:
                            self.send_voice_important(mp.TOO_EARLY)
                    except Exception:
                        self.send_voice_important(mp.TOO_EARLY)
                return
            last_map[target.id] = self.world.time
            # 发送请求给目标
            target._ally_requests_from.add(self.id)
            try:
                target.send_voice_important(mp.ALLIANCE_REQUEST_FROM + self.name)
            except Exception:
                target.send_voice_important(mp.ALLIANCE_REQUEST_FROM)
        elif action == 'accept':
            # 仅允许对收到的请求进行同意
            if target.id in self._ally_requests_from:
                # 双向确立：对齐 client.alliance 字段为新的同盟编号（采用较小者或新编号）
                # 简化：使用目标的 alliance 值（若为空则继承我的；都为空则新建）
                aid_self = getattr(self.client, 'alliance', None)
                aid_t = getattr(target.client, 'alliance', None)
                affected_before = {aid_self, aid_t}
                # 把 DummyClient 默认的 "ai" 联盟视为"未设"：人和中立 AI 结盟应分配
                # 独立的新 ID，绝不能让人继承 "ai" 而瞬间和地图上所有 AI 同盟。
                _UNSET = (None, 'None', 'ai')
                if aid_self in _UNSET and aid_t in _UNSET:
                    # 分配一个新的同盟编号：选择当前未使用的最小正整数
                    used = {getattr(p.client, 'alliance', None) for p in self.world.players}
                    new_id = 1
                    while new_id in used:
                        new_id += 1
                    self.client.alliance = new_id
                    target.client.alliance = new_id
                elif aid_self in _UNSET:
                    self.client.alliance = aid_t
                elif aid_t in _UNSET:
                    target.client.alliance = aid_self
                else:
                    # 两人已有不同同盟，则将双方合并到较小编号
                    try:
                        nid = min(int(aid_self), int(aid_t))
                    except Exception:
                        nid = aid_self
                    self.client.alliance = nid
                    target.client.alliance = nid
                # 应用更新（选择性刷新，避免全局卡顿）
                affected_after = {getattr(self.client, 'alliance', None), getattr(target.client, 'alliance', None)}
                affected_ids = set(x for x in affected_before | affected_after if x not in [None, 'None'])
                for p in self.world.players:
                    if getattr(p.client, 'alliance', None) in affected_ids or p in (self, target):
                        try:
                            p.update_alliance()
                        except Exception:
                            pass
                # 清理请求
                self._ally_requests_from.discard(target.id)
                target._ally_requests_from.discard(self.id)
                # 语音提示
                # 双方本人（各自听到对方名字）
                self.send_voice_important(mp.ALLIANCE_ACCEPTED_WITH + target.name)
                target.send_voice_important(mp.ALLIANCE_ACCEPTED_WITH + self.name)
                # 其他人：单次播报包含双方名字，并把 target 也排除掉（避免
                # target 二次听到关于自己的播报）。原来的"双 broadcast"会让
                # self/target 都从对方的广播里听到自己的名字，confusing。
                self.broadcast_to_others_only(
                    mp.ALLIANCE_ACCEPTED_WITH + self.name + mp.COMMA + target.name,
                    exclude=target,
                )
            else:
                # 没有待我处理的该目标请求
                if self.is_local_human():
                    self.send_voice_important(mp.DIPLOMACY + mp.NO_CANDIDATE)
        elif action == 'decline_or_cancel':
            # 优先：若存在对方对我的请求 -> 拒绝
            if target.id in self._ally_requests_from:
                self._ally_requests_from.discard(target.id)
                self._alliance_declined_from.add(target.id)
                # 本人与对方
                self.send_voice_important(mp.ALLIANCE_DECLINED_WITH + target.name)
                target.send_voice_important(mp.ALLIANCE_DECLINED_WITH + self.name)
                # 其他人（排除 target，否则 target 会再听一遍"已拒绝结盟 [自己名]"）
                self.broadcast_to_others_only(
                    mp.ALLIANCE_DECLINED_WITH + target.name,
                    exclude=target,
                )
            # 其次：若存在我对对方的请求 -> 撤销
            elif self.id in getattr(target, '_ally_requests_from', set()):
                target._ally_requests_from.discard(self.id)
                # 本人与对方
                try:
                    self.send_voice_important(mp.UNALLY_WITH + target.name)
                    target.send_voice_important(mp.UNALLY_WITH + self.name)
                except Exception:
                    self.send_voice_important(mp.UNALLY_WITH)
                    target.send_voice_important(mp.UNALLY_WITH)
            else:
                # 最后：若目前与对方同盟 -> 取消（单方退出联盟）
                aid_self = getattr(self.client, 'alliance', None)
                aid_t = getattr(target.client, 'alliance', None)
                if aid_self not in [None, 'None'] and aid_self == aid_t:
                    affected_before = {aid_self}
                    self.client.alliance = None
                    # 选择性刷新：当前退盟方 + 原联盟成员
                    for p in self.world.players:
                        if getattr(p.client, 'alliance', None) == aid_self or p is self:
                            try:
                                p.update_alliance()
                            except Exception:
                                pass
                    # 本人与对方
                    self.send_voice_important(mp.UNALLIED_WITH + target.name)
                    target.send_voice_important(mp.UNALLIED_WITH + self.name)
                    # 其他人（排除 target，避免 target 二次听到关于自己的播报）
                    self.broadcast_to_others_only(
                        mp.UNALLIED_WITH + target.name,
                        exclude=target,
                    )
                else:
                    if self.is_local_human():
                        self.send_voice_important(mp.DIPLOMACY + mp.NO_CANDIDATE)

    def send_voice_important(self, msg):
        self.push("voice_important", encode_msg(msg))

    nb_units_produced = 0
    nb_units_lost = 0
    nb_units_killed = 0
    nb_buildings_produced = 0
    nb_buildings_lost = 0
    nb_buildings_killed = 0

    def equivalent(self, tn):
        if rules.get(self.faction, tn):
            return rules.get(self.faction, tn)[0]
        return tn

    def init_alliance(self):
        if player_is_wildlife_only(self):
            self.client.alliance = None
        if self.client.alliance in [None, "None"]:
            return
        for p in self.world.players:
            if p is self or player_is_wildlife_only(p):
                continue
            if alliance_ids_equal(self.client.alliance, p.client.alliance):
                self.allied.append(p)
        # 仅注册轻量联盟管理器（不改变视野机制）
        try:
            from ..world.alliance import AllianceVisionManager
            if not hasattr(self.world, 'alliance_vision_managers'):
                self.world.alliance_vision_managers = {}
            aid = self.client.alliance
            if aid not in self.world.alliance_vision_managers:
                self.world.alliance_vision_managers[aid] = AllianceVisionManager(aid)
            self.world.alliance_vision_managers[aid].add_player(self)
        except Exception:
            pass

    def update_alliance(self):
        if player_is_wildlife_only(self):
            self.client.alliance = None
        if self.client.alliance in [None, "None"]:
            self.allied = [self]
        else:
            self.allied = []
            for p in self.world.players:
                if player_is_wildlife_only(p):
                    continue
                if alliance_ids_equal(self.client.alliance, p.client.alliance):
                    self.allied.append(p)
        # 同步轻量管理器成员（不改变任何视野逻辑）
        try:
            if hasattr(self.world, 'alliance_vision_managers'):
                # 先从不匹配的联盟管理器移除
                for mid, mgr in list(self.world.alliance_vision_managers.items()):
                    if self in getattr(mgr, 'players', []) and mid != self.client.alliance:
                        try:
                            mgr.remove_player(self)
                        except Exception:
                            pass
                # 再添加到当前联盟
                if self.client.alliance not in [None, "None"]:
                    aid = self.client.alliance
                    from ..world.alliance import AllianceVisionManager
                    if aid not in self.world.alliance_vision_managers:
                        self.world.alliance_vision_managers[aid] = AllianceVisionManager(aid)
                    self.world.alliance_vision_managers[aid].add_player(self)
        except Exception:
            pass
        # 清理联盟相关缓存，确保动态变更即时生效
        self._cached_allied_vision = None
        self._allied_vision_cache_time = -1_000_000
        try:
            if hasattr(self, '_clear_allied_vision_cache'):
                self._clear_allied_vision_cache()
            # 立刻使敌友关系判断缓存失效
            if hasattr(self, '_enemy_player_cache'):
                self._enemy_player_cache = {}
                self._enemy_player_timestamp = 0
            # 立刻使关系快照失效
            try:
                if hasattr(self.__class__, '_relation_cache') and self.id in self.__class__._relation_cache:
                    del self.__class__._relation_cache[self.id]
            except Exception:
                pass
            # 强制下一次立刻重建联盟ID缓存
            try:
                self._cached_allied_time = -1
            except Exception:
                pass
        except Exception:
            pass

    def set_ai(self, ai_type):
        pass

    def add_unit(self, type_, place, population_cost=None):
        # 防止观战者获得任何单位
        if hasattr(self, '_is_pure_spectator') and self._is_pure_spectator:
            warning("Attempted to add unit to spectator player via add_unit, ignoring")
            return
            
        x, y, land = place.find_and_remove_meadow(type_)
        x, y = place.find_free_space(type_.airground_type, x, y)
        if x is not None:
            unit = type_(self, place, x, y)
            if population_cost is not None:
                try:
                    base_pop = max(0, int(getattr(unit, "population_cost", 0)))
                    eff = max(0, int(population_cost))
                    unit.effective_population_cost = eff
                    self.used_population += eff - base_pop
                except Exception:
                    pass
            unit.building_land = land
            if hasattr(self, "_assign_map_select_slot"):
                self._assign_map_select_slot(unit, place)
            if getattr(unit, "type_name", None) == "hatchery":
                from ..world_build_rules import fill_hatchery_larva

                fill_hatchery_larva(unit, notify=False)

    @property
    def available_population(self):
        return min(self.population, self.world.population_limit)

    def broadcast_to_others_only(self, msg, exclude=None):
        """向除自己外的玩家播报；可额外排除一个玩家。

        ``exclude`` 用于动态联盟的双方播报：当事 self 和 target 已经分别收到
        过精确包含对方名字的私聊消息，再把 self 视角的 "已建立同盟 target.name"
        广播给所有人时，要把 ``target`` 排除掉——否则 target 会再听一遍
        "已建立同盟 [自己的名字]"，既冗余又像有第三方在喊。
        """
        for p in self.world.players:
            if p is not self and p is not exclude:
                p.send_voice_important(msg)

    def check_type(self, o, t):  # move method to Entity.check_type(t)?
        if isinstance(t, list):
            for _ in t:
                if self.check_type(o, _):
                    return True
        elif inspect.isclass(t):  # Deposit, BuildingSite, Worker, Meadow...
            return isinstance(o, t)
        elif isinstance(t, str):
            return o.type_name == t
        type_name = getattr(t, "type_name", None)
        if type_name is not None:
            return o.type_name == type_name

    @staticmethod
    def effective_count_limit(type_name):
        t = rules.unit_class(type_name)
        if t is None:
            return 0
        if t.count_limit:
            return t.count_limit
        return getattr(t, "global_count_limit", 0) or 0

    def future_count(self, type_name, exclude_order=None):
        result = 0
        for u in self.units:
            if (
                u.type_name == type_name
                or u.type_name == "buildingsite"
                and u.type.type_name == type_name
            ):
                result += 1
            for o in getattr(u, "orders", ()):
                if o is exclude_order:
                    continue
                # don't count the "build" orders because they might concern the same building
                if (
                    o.keyword in ("train", "upgrade_to")
                    and o.type.type_name == type_name
                ):
                    if o.keyword == "train":
                        result += max(1, getattr(o, "train_count", 1))
                    else:
                        result += 1
        return result

    def check_count_limit(self, type_name):
        limit = self.effective_count_limit(type_name)
        if limit == 0:
            return True
        t = rules.unit_class(type_name)
        if t is None:
            info("couldn't check count_limit for %r", type_name)
            return False
        if self.future_count(t.type_name) >= limit:
            return False
        return True

    def nearest_warehouse(self, place, resource_type, include_building_sites=False):
        # 优化：为nearest_warehouse添加缓存，减少重复计算（缓存窗口2秒）
        current_time = self.world.time
        time_bucket = current_time // 2000
        cache_key = (place.id, resource_type, include_building_sites, time_bucket)

        # (_warehouse_cache / _warehouse_candidates_cache /
        #  _warehouse_candidates_bucket 已在 __init__ 预初始化)
        # 命中整体结果缓存
        if cache_key in self._warehouse_cache:
            return self._warehouse_cache[cache_key]

        if self._warehouse_candidates_bucket != time_bucket:
            self._warehouse_candidates_cache.clear()
            self._warehouse_candidates_bucket = time_bucket

        cand_key = (resource_type, include_building_sites)
        candidates = self._warehouse_candidates_cache.get(cand_key)
        if candidates is None:
            candidates = []
            for p in self.allied:
                for u in p.units:
                    # 缓存 BuildingSite 类型检查
                    if not hasattr(u, '_cached_is_building_site'):
                        u._cached_is_building_site = isinstance(u, BuildingSite)
                    try:
                        if (
                            resource_type in u.storable_resource_types
                            or (
                                include_building_sites
                                and u._cached_is_building_site
                                and resource_type in getattr(u.type, 'storable_resource_types', ())
                            )
                        ):
                            candidates.append(u)
                    except Exception:
                        pass
            self._warehouse_candidates_cache[cand_key] = candidates

        if not candidates:
            self._warehouse_cache[cache_key] = None
            return None

        # 直线距离粗筛以限制后续最短路评估数量
        tmp = []
        for u in candidates:
            try:
                dx = place.x - u.place.x
                dy = place.y - u.place.y
                lin_d2 = dx * dx + dy * dy
                tmp.append((lin_d2, u))
            except Exception:
                continue
        if not tmp:
            self._warehouse_cache[cache_key] = None
            return None
        tmp.sort(key=lambda t: (t[0], t[1].id))

        # 按时间桶维护"地点间最短路距离"缓存，避免重复 A*
        # (_place_distance_cache / _place_distance_cache_bucket 已在 __init__ 预初始化)
        if self._place_distance_cache_bucket != time_bucket:
            self._place_distance_cache = {}
            self._place_distance_cache_bucket = time_bucket

        def _dist_between_places(p_from, p_to):
            k = (p_from.id, p_to.id)
            d = self._place_distance_cache.get(k)
            if d is None:
                d = p_from.shortest_path_distance_to(p_to, self)
                self._place_distance_cache[k] = d
            return d

        # 仅对最近的前 N 个做路径距离评估
        TOP_K = 4
        best_dist = float('inf')
        best = None
        for _, u in tmp[:TOP_K]:
            d = _dist_between_places(place, u.place)
            if d == 0:
                best = u
                break
            if d is not None and d < best_dist:
                best_dist = d
                best = u

        result = best

        # 缓存结果（限制缓存大小）
        if len(self._warehouse_cache) > 100:
            old_keys = [k for k in self._warehouse_cache.keys() if k[3] < time_bucket - 5]
            for k in old_keys:
                del self._warehouse_cache[k]

        self._warehouse_cache[cache_key] = result
        return result

    def _is_admin(self):
        return self.world.players.index(self) == 0

    @staticmethod
    def allied_control_controller_for(unit):
        return allied_control_controller_for(unit)

    def unit_under_allied_control(self, unit):
        """该单位是否可由本玩家直接指挥（己方、全盟友或选择性移交）。"""
        if unit.player in self.allied_control:
            return True
        return unit in self.allied_control_units_set

    @property
    def allied_control_units(self):
        result = []
        for p in self.allied_control:
            result.extend(p.units)
        for u in self.allied_control_units_set:
            if getattr(u, "presence", True) and u not in result:
                result.append(u)
        return result

    def _init_spatial_index(self):
        """初始化更高效的空间索引系统"""
        # 初始化四叉树空间索引，而不仅仅是网格桶
        if not hasattr(self.world, 'quad_trees'):
            # 创建空间索引字典，每个玩家一个
            self.world.quad_trees = {}
            
            # 确定世界边界
            world_width = 0
            world_height = 0
            
            for square in self.world.squares:
                # 使用xmax而不是width属性，Square类使用xmin,xmax,ymin,ymax定义边界
                square_width = square.xmax - square.xmin
                world_width = max(world_width, square.xmax)
                world_height = max(world_height, square.ymax)
            
            # 确保有合理的最小边界
            world_width = max(world_width, 1000)
            world_height = max(world_height, 1000)
            
            # 定义边界矩形
            from ..worldroom import QuadTree
            boundary = (0, 0, world_width, world_height)  # (xmin, ymin, xmax, ymax)
            
            # 为每个玩家创建四叉树
            for player in self.world.players:
                self.world.quad_trees[player.id] = QuadTree(boundary)
        
        # 将自己的单位加入四叉树
        if self.id in self.world.quad_trees:
            quad_tree = self.world.quad_trees[self.id]
            for unit in self.units:
                quad_tree.insert(unit)
    
    def _ensure_world_regions(self):
        """确保世界有区域图以支持分层寻路"""
        # 如果世界已经有区域图，则跳过
        if hasattr(self.world, 'region_graph'):
            return
            
        # 创建区域图
        self.world.region_graph = {'ground': {}, 'air': {}}
        self.world.region_portals = {'ground': {}, 'air': {}}
        
        # 创建地形分析器
        terrain_analyzer = self._create_terrain_analyzer()
        
        # 分析地形并创建区域
        regions = terrain_analyzer.analyze()
        
        # 为每个区域分配方格
        for region in regions:
            for square in region.squares:
                square.region = region
            
            # 计算区域的中心点
            center_x = sum(square.x for square in region.squares) / len(region.squares)
            center_y = sum(square.y for square in region.squares) / len(region.squares)
            
            region.center_x = center_x
            region.center_y = center_y
        
        # 建立区域之间的连接（ground）：
        # 仅使用已存在且当前不被森林阻挡的出口，不创建任何新出口，保证决定性
        for s in self.world.squares:
            r1 = getattr(s, 'region', None)
            if r1 is None:
                continue
            if r1 not in self.world.region_graph['ground']:
                self.world.region_graph['ground'][r1] = []
            for e in getattr(s, 'exits', []) or []:
                try:
                    # 跳过当前被森林阻挡的出口，以避免区域层建议进入死路
                    if getattr(e, 'is_blocked_by_forests', False):
                        continue
                    other_place = e.other_side.place
                    r2 = getattr(other_place, 'region', None)
                    if r2 is None or r2 is r1:
                        continue
                    self.world.region_graph['ground'][r1].append(r2)
                    # 记录一个门户代表（同一对区域保留最近一次见到的即可，区域层只做方向指引）
                    self.world.region_portals['ground'][(r1, r2)] = e
                except Exception:
                    continue
    
    def _create_terrain_analyzer(self):
        """创建地形分析器类，用于地形分析和区域划分"""
        class TerrainAnalyzer:
            def __init__(self, world):
                self.world = world
                self.squares = world.squares
                self.visited = set()
                self.regions = []
            
            def analyze(self):
                """分析地图并返回区域列表"""
                # 对每个未访问的方格执行洪水填充，找出连通区域
                for square in self.squares:
                    if square not in self.visited:
                        region = self._flood_fill(square)
                        if region.squares:
                            self.regions.append(region)
                
                return self.regions
            
            def _flood_fill(self, start_square):
                """使用洪水填充算法找出连通区域"""
                class Region:
                    def __init__(self):
                        self.squares = []
                        # 添加区域类型标记
                        self.is_water = False
                        self.is_ground = True
                
                region = Region()
                # 设置区域类型与起始方格一致
                region.is_water = start_square.is_water
                region.is_ground = start_square.is_ground
                
                queue = [start_square]
                self.visited.add(start_square)
                
                while queue:
                    square = queue.pop(0)
                    region.squares.append(square)
                    
                    # 检查相邻方格（浅滩/大桥 is_water+is_ground 与陆地同属地面区域）
                    for neighbor in square.neighbors:
                        if (
                            neighbor not in self.visited
                            and squares_same_ground_region(square, neighbor)
                        ):
                            self.visited.add(neighbor)
                            queue.append(neighbor)
                
                return region
        
        return TerrainAnalyzer(self.world)
    
    def _regions_are_connected(self, region1, region2):
        """检查两个区域是否相邻连通"""
        # 先检查区域类型是否兼容（两个区域都必须是同类型地形）
        # 检查第一个区域的第一个方格和第二个区域的第一个方格
        if region1.squares and region2.squares:
            square1 = region1.squares[0]
            square2 = region2.squares[0]
            if not squares_same_ground_region(square1, square2):
                return False

        # 检查区域1的每个方格是否与区域2的方格相邻
        for square1 in region1.squares:
            for square2 in region2.squares:
                if square2 in square1.neighbors:
                    if squares_same_ground_region(square1, square2):
                        return True
        return False
    
    def _find_region_portal(self, region1, region2):
        """查找两个区域之间已有的出口作为门户（不创建新出口）"""
        for square1 in region1.squares:
            for e in getattr(square1, 'exits', []) or []:
                try:
                    if getattr(e.other_side.place, 'region', None) is region2:
                        return e
                except Exception:
                    continue
        return None

    def get_allied_units(self):
        """获取所有联盟单位的高效缓存方法

        (_allied_units_cache / _allied_units_timestamp / _allied_units_count
        已在 __init__ 预初始化)
        """
        current_time = self.world.time
        
        # 计算当前联盟单位总数用于快速检测变化
        # 这比完全重建单位列表要快得多
        current_count = sum(len(ally.units) for ally in self.allied)
        
        # 如果时间超过250ms或单位数量发生变化，则刷新缓存
        if (current_time - self._allied_units_timestamp > 250 or 
            current_count != self._allied_units_count):
                
            # 重建缓存
            allied_units = set()
            for ally in self.allied:
                allied_units.update(ally.units)
                
            # 更新缓存和时间戳
            self._allied_units_cache = allied_units
            self._allied_units_timestamp = current_time
            self._allied_units_count = current_count
            
        return self._allied_units_cache
    
    def get_allied_military_units(self):
        """获取所有联盟军事单位的高效缓存方法

        (_allied_military_cache / _allied_military_timestamp 已在 __init__ 预初始化)
        """
        current_time = self.world.time
        
        # 每500ms刷新一次军事单位缓存
        if current_time - self._allied_military_timestamp > 500:
            # 首先获取所有联盟单位
            all_units = self.get_allied_units()
            
            # 过滤出军事单位 (士兵类型且可移动)
            from ..worldunit import Soldier
            military_units = {u for u in all_units if isinstance(u, Soldier) and u.speed > 0}
            
            # 更新缓存和时间戳
            self._allied_military_cache = military_units
            self._allied_military_timestamp = current_time
            
        return self._allied_military_cache

    def init_position(self, parsed_start):
        """初始化玩家位置和状态"""
        units, self.upgrades, self.forbidden_techs, resources, triggers, population_bonus = parsed_start

        # 若起始 upgrades 中包含 phase（时代），则把其 phase bonus 注入到玩家加成池
        # 以及（若设置）记录 current_phase。这样起始时代下生产的单位也能获得对应加成。
        try:
            from ..worldphase import Phase, is_a_phase
            self._phase_bonus_pool = []
            for upgrade_name in self.upgrades:
                cls = rules.unit_class(upgrade_name)
                if cls is not None and isinstance(cls, type) and issubclass(cls, Phase):
                    bonus_args = list(getattr(cls, "phase_bonus", ()) or ())
                    targets = list(getattr(cls, "phase_targets", ()) or ())
                    if bonus_args:
                        Phase._apply_phase_bonus_to_player(self, bonus_args)
                        self._phase_bonus_pool.append((bonus_args, targets))
                    self.current_phase = cls.type_name

            # 若地图未显式提供任何起始 phase，则自动选用"起源时代"——即 rules
            # 中定义的、其 requirements 不包含任何其他 phase 名的那个 phase。
            # 这样地图开局，市政厅之类带 can_advance <phase> 的建筑就能立即
            # 通过 current_age_status 显示"当前时代：XX"，匹配 AoE 玩家直觉。
            # 注意：仅把该时代名写入 player.upgrades 和 current_phase；
            # 不应用 phase_bonus（"起源时代"通常没有 bonus；若设置了也不应用，
            # 以避免与未来 phase 累积重复，保持"未推进时代 = 基线"语义）。
            if self.current_phase is None:
                all_phase_names = []
                try:
                    for cname, ccls in getattr(rules, "classes", {}).items():
                        if is_a_phase(ccls):
                            all_phase_names.append(cname)
                except Exception:
                    all_phase_names = []
                if all_phase_names:
                    phase_name_set = set(all_phase_names)
                    root_phases = []
                    for pname in all_phase_names:
                        pcls = rules.unit_class(pname)
                        reqs = list(getattr(pcls, "requirements", ()) or ())
                        if not any(r in phase_name_set for r in reqs):
                            root_phases.append(pname)
                    if root_phases:
                        if len(root_phases) > 1:
                            info(
                                "multiple root phases found (%s); using first: %s",
                                ", ".join(root_phases), root_phases[0],
                            )
                        chosen = root_phases[0]
                        if chosen not in self.upgrades:
                            self.upgrades.append(chosen)
                        self.current_phase = chosen
        except Exception as e:
            warning("error initializing phase state from starting upgrades: %s", str(e))

        self.resources = resources
        self._starting_resources = list(resources)
        for index, qty in enumerate(self.resources):
            self.stats.add("gathered", index, qty)

        # 设置触发器，分别处理timer 0触发器
        self.triggers = triggers
        planned_primary, planned_secondary = collect_planned_objective_numbers(
            self.triggers
        )
        self._planned_primary_objective_numbers = planned_primary
        self._planned_secondary_objective_numbers = planned_secondary
        
        # 分别处理timer 0触发器：立即执行联盟和保护相关的，延迟执行添加单位的
        for t in self.triggers[:]:
            condition, action = t
            if (len(condition) >= 2 and condition[0] == "timer" and 
                float(condition[1]) == 0.0):
                action_str = str(action)
                # 立即执行联盟和保护相关的触发器
                if "alliance" in action_str or "protect" in action_str:
                    if self.my_eval(condition):
                        self.my_eval(action)
                        self.triggers.remove(t)
                        self._eventually_reschedule(t)
                # 延迟执行添加单位的触发器，改为在正常游戏循环中执行（确保客户端完全初始化）
                elif "add_units" in action_str:
                    condition[1] = 0.0  # 即使是0，也会延迟到下一个游戏更新周期
        
        # 观战者不应该获得任何单位
        if not (hasattr(self, '_is_pure_spectator') and self._is_pure_spectator):
            # 如果 place 为 None，使用本玩家起始格（players_starts 中对应的 sq）作为落点；
            # 为兼容默认起始（从规则来）情况。
            default_place = None
            # 尝试找到该玩家对应的起始格（若存在）
            try:
                # self.number 从1开始分配
                start_index = (self.number - 1) if self.number is not None else 0
                if 0 <= start_index < len(self.world.players_starts):
                    start_entry = self.world.players_starts[start_index]
                    # start_entry[1] 是 units 列表，包含若干 (sq, cls, n) 或 [None, "-x", None]
                    # 找到第一个具备方格的条目，作为默认 sq
                    for item in start_entry[1]:
                        if isinstance(item, (list, tuple)) and len(item) >= 1 and item[0]:
                            default_place = self.world.grid.get(item[0])
                            if default_place:
                                break
                # 若还没有，退化为地图上的第一个方格
                if default_place is None and self.world.squares:
                    default_place = self.world.squares[0]
            except Exception:
                # 如果任何异常，忽略并不设置默认落点
                pass

            for place, n, type_ in units:
                # 默认起始（规则定义）时 place 可能为 None
                actual_place = place
                if actual_place is None:
                    actual_place = default_place
                    if actual_place is None:
                        # 再兜底：随机一个可用方格
                        if hasattr(self.world, 'squares') and self.world.squares:
                            actual_place = self.world.random.choice(self.world.squares)
                for _ in range(n):
                    self.add_unit(type_, actual_place)

        if population_bonus:
            self.population += population_bonus

        self._apply_starting_upgrades()

    def _apply_starting_upgrades(self):
        """Apply ``starting_units`` / rules upgrades after initial units exist."""
        from ..worldphase import is_a_phase
        from ..worldupgrade import is_an_upgrade

        seen = set()
        for upgrade_name in self.upgrades:
            if upgrade_name in seen:
                continue
            seen.add(upgrade_name)
            cls = rules.unit_class(upgrade_name)
            if cls is None or not is_an_upgrade(cls):
                continue
            if is_a_phase(cls):
                continue
            try:
                cls.upgrade_player(self)
            except Exception as e:
                warning(
                    "error applying starting upgrade %s: %s",
                    upgrade_name,
                    str(e),
                )

    # 这些方法将在其他模块中实现，这里添加占位符以避免导入错误
    def play(self):
        """AI游戏逻辑 - 在combat.py中实现"""
        pass

    # slow_update 和 update 方法将在主 Player 类中实现

    def __getstate__(self):
        from ..save_pickle import (
            PLAYER_CACHE_KEYS,
            pop_keys,
            prepare_memory_for_pickle,
        )

        state = self.__dict__.copy()
        memory = state.get("memory")
        if memory is not None:
            state["memory"] = prepare_memory_for_pickle(memory)
        pop_keys(state, PLAYER_CACHE_KEYS)
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        # Player 常在 World 之前完成 unpickle; 缓存与 memory 由
        # World.__setstate__ -> rebuild_world_after_load 统一恢复.