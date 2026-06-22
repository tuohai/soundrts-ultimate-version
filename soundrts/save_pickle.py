"""Shallow pickle state for game save/load.

cloudpickle 默认遍历完整对象图. 极大世界 (cw1-mm) 里 ``World.g`` 路径图、
``Square.neighbors`` 缓存、战斗 ``last_attacker`` 链等会让递归深度达到数万,
耗尽 C 栈. 这里在 ``__getstate__`` 里去掉可重建索引与瞬时引用, 读档后再恢复.
"""

from __future__ import annotations

WORLD_STRIP_ON_SAVE = (
    "g",
    "grid",
    "region_graph",
    "region_portals",
    "quad_trees",
    "_sights_cache",
    "_sights_cache_bucket",
)

SQUARE_STRIP_ON_SAVE = (
    "spiral",
    "neighbors",
    "strict_neighbors",
    "region",
)

CREATURE_STRIP_ON_SAVE = (
    "last_attacker",
)

PLAYER_CACHE_KEYS = (
    "_buckets",
    "_enemy_units_cache",
    "_enemy_units_cache_time",
    "_cached_enemy_players",
    "_enemy_players_cache_time",
    "_enemy_units_set",
    "_enemy_units_set_time",
    "_perception_set",
    "_perception_set_time",
    "_allied_exploration_cache",
    "_allied_exploration_timestamp",
    "_cached_alliance_ids",
    "_cached_alliance_time",
    "_cached_allied_ids",
    "_cached_allied_time",
    "_cached_enemy_units_hash",
    "_cached_sorted_enemy_units",
    "_last_unit_positions",
    "_last_perception_hash",
    "_last_positions_hash",
    "_last_forced_perception_update",
    "_last_gc_time",
    "_vision_cover_counts",
    "_last_perception_update",
    "_last_memory_cleanup",
    "_nearby_units_cache",
    "_nearby_units_cache_bucket",
    "_memory_scan_cursor",
    "_memory_list",
    "_memory_list_snapshot_time",
    "_cached_allied_vision",
    "_allied_vision_cache_time",
    "_warehouse_cache",
    "_warehouse_candidates_cache",
    "_warehouse_candidates_bucket",
    "_place_distance_cache",
    "_place_distance_cache_bucket",
    "_allied_units_cache",
    "_allied_units_timestamp",
    "_allied_units_count",
    "_allied_military_cache",
    "_allied_military_timestamp",
    "_enemy_menace_cache",
    "_enemy_menace_cache_time",
    "_cached_enemy_units",
    "_cached_enemy_units_time",
    "_balance_cache",
    "_balance_cache_time",
    "_enemy_player_cache",
    "_enemy_player_timestamp",
    "_memory_index",
)


def pop_keys(state: dict, keys) -> None:
    for key in keys:
        state.pop(key, None)


def strip_target_for_pickle(state: dict, attr="target", id_attr="_pickle_target_id") -> None:
    target = state.pop(attr, None)
    if target is None:
        return
    if isinstance(target, tuple):
        state[attr] = target
        return
    tid = getattr(target, "id", None)
    if tid is not None:
        state[id_attr] = tid


def restore_target_after_pickle(obj, id_attr="_pickle_target_id", attr="target") -> None:
    """Restore pickled target id → live object when possible.

    During ``cloudpickle.load``, ``Action``/``Order`` may unpickle before
    ``World.__setstate__`` finishes; ``world.objects`` may not exist yet.
    In that case keep ``_pickle_target_id`` for ``restore_world_pickle_targets``.
    """
    tid = obj.__dict__.get(id_attr)
    existing = obj.__dict__.get(attr, _MISSING)
    if isinstance(existing, tuple):
        return
    unit = obj.__dict__.get("unit")
    world = getattr(unit, "world", None) if unit is not None else None
    objects = getattr(world, "objects", None) if world is not None else None
    if tid is not None and objects is not None:
        obj.__dict__.pop(id_attr, None)
        obj.__dict__[attr] = objects.get(tid)
    elif existing is _MISSING:
        obj.__dict__[attr] = None


_MISSING = object()


def restore_entity_pickle_targets(entity, world) -> None:
    """Fix Action/Order targets after world is fully loaded (incl. old saves)."""
    action = getattr(entity, "action", None)
    if action is not None and hasattr(action, "__dict__"):
        _restore_target_with_world(action, world)
    for order in getattr(entity, "orders", ()) or ():
        if hasattr(order, "__dict__"):
            _restore_target_with_world(order, world)


def _restore_target_with_world(obj, world, id_attr="_pickle_target_id", attr="target") -> None:
    if isinstance(obj.__dict__.get(attr), tuple):
        return
    tid = obj.__dict__.pop(id_attr, None)
    objects = getattr(world, "objects", None)
    if tid is not None and objects is not None:
        obj.__dict__[attr] = objects.get(tid)
    elif tid is None and attr not in obj.__dict__:
        obj.__dict__[attr] = None


def restore_world_pickle_targets(world) -> None:
    for obj in getattr(world, "objects", {}).values():
        restore_entity_pickle_targets(obj, world)


def prepare_memory_for_pickle(memory):
    """Return a copy of *memory* safe for pickle (live game state unchanged)."""
    import copy

    if not memory:
        return memory
    new_memory = set()
    for rem in memory:
        rem_copy = copy.copy(rem)
        initial = getattr(rem_copy, "initial_model", None)
        if initial is not None:
            tid = getattr(initial, "id", None)
            if tid is not None:
                rem_copy._pickle_initial_model_id = tid
            rem_copy.initial_model = None
        new_memory.add(rem_copy)
    return new_memory


def restore_player_memory(player) -> None:
    player._memory_index = {}
    memory = getattr(player, "memory", None)
    if not memory:
        return
    for rem in memory:
        tid = getattr(rem, "_pickle_initial_model_id", None)
        if tid is not None:
            objects = getattr(player.world, "objects", None)
            if objects is not None:
                rem.initial_model = objects.get(tid)
            try:
                del rem._pickle_initial_model_id
            except AttributeError:
                pass
        initial = getattr(rem, "initial_model", None)
        if initial is not None:
            player._memory_index[initial] = rem


def init_player_pickle_caches(player) -> None:
    """Reset recomputable Player caches to post-__init__ defaults."""
    player._buckets = {}
    player._enemy_units_cache = []
    player._enemy_units_cache_time = -1_000_000
    player._cached_enemy_players = []
    player._enemy_players_cache_time = -1_000_000
    player._enemy_units_set = frozenset()
    player._enemy_units_set_time = -1
    player._perception_set = frozenset()
    player._perception_set_time = -1
    player._allied_exploration_cache = {}
    player._allied_exploration_timestamp = 0
    player._cached_alliance_ids = ()
    player._cached_alliance_time = -1_000_000
    player._cached_allied_ids = ()
    player._cached_allied_time = -1_000_000
    player._cached_enemy_units_hash = None
    player._cached_sorted_enemy_units = []
    player._last_unit_positions = {}
    player._last_perception_hash = 0
    player._last_positions_hash = 0
    player._last_forced_perception_update = 0
    player._last_gc_time = 0
    player._vision_cover_counts = {}
    player._last_perception_update = -1_000_000
    player._last_memory_cleanup = 0
    player._nearby_units_cache = {}
    player._nearby_units_cache_bucket = -1
    player._memory_scan_cursor = 0
    player._memory_list = []
    player._memory_list_snapshot_time = -1_000_000
    player._cached_allied_vision = None
    player._allied_vision_cache_time = -1_000_000
    player._warehouse_cache = {}
    player._warehouse_candidates_cache = {}
    player._warehouse_candidates_bucket = -1
    player._place_distance_cache = {}
    player._place_distance_cache_bucket = -1
    player._allied_units_cache = None
    player._allied_units_timestamp = 0
    player._allied_units_count = -1
    player._allied_military_cache = None
    player._allied_military_timestamp = 0
    player._enemy_menace_cache = {}
    player._enemy_menace_cache_time = 0
    player._cached_enemy_units = set()
    player._cached_enemy_units_time = 0
    player._balance_cache = {}
    player._balance_cache_time = {}
    player._enemy_player_cache = {}
    player._enemy_player_timestamp = 0
    player._force_full_update = True


def _normalize_world_players(world) -> None:
    """Drop empty player shells left by client<->player pickle cycles."""
    by_id = {}
    for player in getattr(world, "players", ()):
        pid = getattr(player, "id", None)
        if pid and player.__dict__:
            by_id[pid] = player
    for obj in getattr(world, "objects", {}).values():
        player = getattr(obj, "player", None)
        pid = getattr(player, "id", None)
        if pid and getattr(player, "__dict__", None):
            by_id[pid] = player
    if by_id:
        world.players = sorted(by_id.values(), key=lambda p: int(p.id))


def link_game_clients_after_load(game) -> None:
    world = getattr(game, "world", None)
    if world is None:
        return
    by_id = {p.id: p for p in world.players if getattr(p, "id", None)}
    for client in getattr(game, "players", ()):
        if hasattr(client, "game_session"):
            client.game_session = game
        pid = getattr(client, "_pickle_player_id", None)
        if pid and pid in by_id:
            client.player = by_id[pid]
            client.player.client = client
            try:
                del client._pickle_player_id
            except AttributeError:
                pass
    local = getattr(game, "local_client", None)
    if local is not None and getattr(local, "player", None) is None and by_id:
        # 兜底：本地客户端未写入 _pickle_player_id 时取第一个人类玩家
        for player in by_id.values():
            if getattr(player, "is_human", False):
                local.player = player
                player.client = local
                break


def rebuild_world_after_load(world) -> None:
    if not hasattr(world, "objects") or world.objects is None:
        world.objects = {}
    _normalize_world_players(world)
    world.grid = {}
    for sq in world.squares:
        world.grid[sq.name] = sq
        world.grid[(sq.col, sq.row)] = sq
    world._create_graphs()
    world._sights_cache = {}
    world._sights_cache_bucket = -1
    for key in ("region_graph", "region_portals", "quad_trees"):
        world.__dict__.pop(key, None)
    for player in getattr(world, "players", ()):
        player.world = world
        init_player_pickle_caches(player)
        restore_player_memory(player)
        if hasattr(player, "_init_spatial_index"):
            player._init_spatial_index()
    restore_world_pickle_targets(world)
    ecs = getattr(world, "_ecs", None)
    if ecs is None:
        try:
            from .world.world_ecs import WorldEcs, ecs_enabled

            if ecs_enabled():
                world._ecs = WorldEcs()
                ecs = world._ecs
        except Exception:
            pass
    if ecs is not None:
        try:
            ecs.rebuild_all_players(world.players)
        except Exception:
            pass
