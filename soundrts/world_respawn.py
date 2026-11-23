# -*- coding: utf-8 -*-
"""敌军刷新（respawn）—— RPG 式的「怪物重生」。

**这是什么**

地图上的一批敌军单位（或者建筑）被玩家打死之后，过一段时间会在
**它倒下的那个格子**重新冒出来一个全新的、满血的同类单位 —— 就像
RPG 里的怪物刷新点。用来做「无限刷兵的怪盗剑士」这类地图。

**怎么配置**

1. 规则里给单位 / 建筑写 ``respawn_time <秒>``::

       def footman
           respawn_time 30

   ``0``（默认）表示永不刷新。

2. 地图的 ``computer_only`` 行可以**逐类型覆盖**规则里的值::

       computer_only 0 0 b3 20 footman 20 archer respawn footman 10 archer 60

   这里的 ``respawn <类型> <秒>`` 会覆盖该槽位里对应类型的刷新时间，
   写 ``respawn <类型> 0`` 则表示这个类型不刷新。

**规则**

* 可刷新的单位**不参与失败判定**：把 b3 的守军全杀了，敌人也不会
  宣布失败 —— 它会等着刷新出来继续打。判定逻辑见
  ``soundrts/worldplayerbase/triggers.py`` 里的 ``no_unit_left`` 与
  ``no_building_left``。
* 刷新出来的是**全新的**单位：满血、无buff、属于原主人、站在死者
  原来的格子上。等级 / 经验**不保留**（RPG 里的怪物也是重新生成）。
* 原格子被占满（玩家站在那儿）时刷新会**推迟**到下一次 tick，
  不会凭空叠单位。
* 玩家自己的单位也能用这个机制（模组作者的自由度），但只有写了
  ``respawn_time`` 的类型才会刷新。

实现要点
--------

世界维护一个待刷新队列 ``world._respawn_queue``：每条记录是
``(到期时间, 玩家, 单位类型, 方格)``。``tick_respawns`` 每秒跑一次
（挂在 ``world.update()`` 的 slow-update 段落），把到期的记录取出来，
在原格子生成新单位。

单位死亡时（``Creature.die``）调用 ``schedule_respawn``，把记录排进
队列。死亡单位自己的 ``delete()`` 照常执行 —— 刷新出来的是一个
**新对象**，不是把旧对象复活。
"""

from __future__ import annotations

from .lib.log import warning

__all__ = [
    "schedule_respawn",
    "tick_respawns",
    "respawn_time_for",
    "player_has_respawnable_units",
    "clear_respawn_queue",
    "group_respawn_seconds_for",
    "schedule_group_respawn",
    "schedule_group_respawn_if_wiped_out",
    "player_has_pending_group_respawn",
    "tick_group_respawns",
    "restore_group_roster",
]


def _queue(world):
    """取出（必要时创建）世界的刷新队列。"""
    q = getattr(world, "_respawn_queue", None)
    if q is None:
        q = []
        world._respawn_queue = q
    return q


def respawn_time_for(unit, type_name=None):
    """取某个单位类型的刷新时限（毫秒）。0 = 永不刷新。

    优先级：
      1. 单位实例上的地图级覆盖（``_respawn_time_override``）；
      2. 单位实例上的 ``respawn_time``（少见，但模组可以运行时改）；
      3. 类型（类）上的 ``respawn_time`` —— 规则里写的那个。
    """
    override = getattr(unit, "_respawn_time_override", None)
    if override is not None:
        return int(override)
    instance_value = getattr(unit, "respawn_time", None)
    if instance_value is not None:
        return int(instance_value or 0)
    if type_name:
        # 按名字查类（地图级覆盖也可能按名字给）。
        try:
            from .definitions import rules

            unit_cls = rules.unit_class(type_name)
        except Exception:
            unit_cls = None
        if unit_cls is not None:
            return int(getattr(unit_cls, "respawn_time", 0) or 0)
    return int(getattr(type(unit), "respawn_time", 0) or 0)


def schedule_respawn(unit, attacker=None):
    """单位死亡时调用：排一次刷新。

    返回排入队列的到期时间（毫秒），没有刷新则返回 ``None``。
    """
    world = getattr(unit, "world", None)
    if world is None:
        return None
    place = getattr(unit, "place", None)
    if place is None:
        return None
    player = getattr(unit, "player", None)
    if player is None:
        return None
    # 势力整体刷新（``respawn_group``）与逐单位刷新互斥：整体刷新的槽位
    # 里，单位死了不该各自回来 —— 整个势力被打光后整队回来才是设计意图。
    if getattr(player, "_respawn_group_armed", False):
        return None
    delay = respawn_time_for(unit)
    if delay <= 0:
        return None

    now = getattr(world, "time", 0)
    deadline = now + delay
    queue = _queue(world)
    # 记录： (到期时间, 玩家, 类型名, 方格, 地图级覆盖毫秒或 None)
    #
    # 存**类型名**而不是类对象 —— 规则里的单位类型是运行时动态建出来的
    # （``type(name, (base,), d)``），把类塞进存档会让 cloudpickle 把它
    # 整个按值序列化，存档体积暴涨。名字则只是一个字符串。
    type_name = getattr(unit, "type_name", None) or getattr(type(unit), "type_name", None)
    if not type_name:
        return None
    # 覆盖值要跟着走 —— 刷新出来的新单位也得用同一个时限。
    override = getattr(unit, "_respawn_time_override", None)
    queue.append((deadline, player, type_name, place, override))
    # 队列按到期时间排序；同一时刻的按入队顺序（append 保持稳定）。
    queue.sort(key=lambda item: item[0])
    return deadline


def tick_respawns(world):
    """每秒调用一次：把到期的刷新做掉。

    格子放不下（玩家站在那儿）时**不丢弃**记录 —— 推到下一个 tick
    再试，这样玩家一走开怪物就出来了。
    """
    if world is None:
        return
    queue = getattr(world, "_respawn_queue", None)
    if not queue:
        return
    now = getattr(world, "time", 0)
    remaining = []
    for record in queue:
        deadline, player, type_name, place = record[:4]
        override = record[4] if len(record) >= 5 else None
        if deadline > now:
            remaining.append(record)
            continue
        # 到期了 —— 尝试在原格子生成。
        if place is None or getattr(place, "world", None) is not world:
            # 方格没了（地图被换掉？）—— 放弃这一条。
            continue
        try:
            if not _spawn_respawned_unit(world, player, type_name, place, override):
                # 格子满了 —— 稍后再试。
                remaining.append(record)
        except Exception:
            warning("couldn't respawn %s", type_name)
            remaining.append(record)
    world._respawn_queue = remaining


def _spawn_respawned_unit(world, player, type_name, place, override=None):
    """在 ``place`` 上生成一个 ``type_name`` 类型的单位。成功返回 True。

    格子满了（没有空位）返回 False，调用方会把记录推到下一 tick。

    位置交给 ``Player.add_unit`` 处理 —— 它会先
    ``find_and_remove_meadow`` 再 ``find_free_space``，跟正常出生、
    跟建筑出兵走的是同一条路径。
    """
    if player is None or not type_name:
        return False
    # 主人已经被击败 / 退出了，就别再刷了。
    if getattr(player, "has_been_defeated", False):
        return True
    if not getattr(player, "is_playing", True):
        return True
    # 按名字找类型 —— 队列里存的是名字（见 ``schedule_respawn``）。
    unit_cls = None
    try:
        from .definitions import rules

        unit_cls = rules.unit_class(type_name)
    except Exception:
        unit_cls = None
    if unit_cls is None:
        return True
    try:
        if not place.have_enough_square_space(unit_cls, player=player):
            return False
    except Exception:
        return False
    before = len(getattr(player, "units", ()) or ())
    try:
        player.add_unit(unit_cls, place, respawn_time_override=override)
    except Exception:
        warning("couldn't respawn %s", type_name)
        return False
    # ``add_unit`` 在格子放不下时会静默返回 —— 用单位数判断有没有真刷出来。
    after = len(getattr(player, "units", ()) or ())
    if after <= before:
        return False
    return True


def player_has_respawnable_units(player):
    """这个玩家还有「会回来的」单位吗？

    用来判断失败条件：会回来的单位即使全死了，敌人也不算输 ——
    它还会刷新 / 复活出来。

    两种「会回来」都算：
      1. **本模块的刷新队列**（``respawn_time``）—— 已经排进队列等刷新；
      2. **现有的英雄复活**（``is_revivable``）—— 地上有一具尸体正在等
         ``revival_time`` 到期复活。详见 ``soundrts/worldresource.py``
         的 ``Corpse``。

    3. 玩家手上还活着一个 ``respawn_time > 0`` 的类型。
    """
    if player is None:
        return False
    world = getattr(player, "world", None)
    if world is None:
        return False
    # 已经在排队等刷新的 —— 一定不能算输。
    for record in getattr(world, "_respawn_queue", ()) or ():
        owner = record[1] if len(record) >= 2 else None
        if owner is player:
            return True
    # 玩家手上还活着一个可刷新的单位 —— 也不能算输。
    for unit in getattr(player, "units", ()) or ():
        try:
            if respawn_time_for(unit) > 0:
                return True
        except Exception:
            continue
    # 地上有等着复活的尸体（现有英雄系统）—— 也不能算输。
    if _has_pending_corpse_revival(player, world):
        return True
    return False


def _has_pending_corpse_revival(player, world):
    """这个玩家还有等着复活的尸体吗？

    现有英雄系统（``is_revivable`` + ``revival_time``）在单位死亡后留下
    一具 ``Corpse``，到期把同一个单位复活回来。**那具尸体还在，就说明
    玩家并没有输** —— 之前这里没检查，导致「只有一个可复活单位」的
    电脑在被清空后会被判负，而它的单位马上就要复活了。

    尸体不属于 ``player.units``（它是 ``world.objects`` 里的独立实体），
    所以要从 ``Corpse.unit.player`` 反查主人。
    """
    try:
        from .worldresource import Corpse
    except Exception:
        return False
    objects = getattr(world, "objects", None)
    if not objects:
        return False
    for obj in list(objects.values()):
        if not isinstance(obj, Corpse):
            continue
        unit = getattr(obj, "unit", None)
        if unit is None:
            continue
        if getattr(unit, "player", None) is not player:
            continue
        if not getattr(unit, "is_revivable", 0):
            continue
        # 尸体还在等 —— 等它的是否已被清掉（主人退出了）？
        if getattr(player, "has_been_defeated", False):
            continue
        return True
    return False


def clear_respawn_queue(world):
    """清空刷新队列（读档 / 重开时用）。"""
    if world is None:
        return
    world._respawn_queue = []
    world._respawn_group_queue = []


# ---------------------------------------------------------------------------
# 势力整体刷新（``respawn_group``）
# ---------------------------------------------------------------------------
# 「势力整体刷新」是逐单位刷新的加强版：地图在 ``computer_only`` 行里写
# ``respawn_group <秒>``，表示**这个势力被全歼之后**，过这么多秒，
# 它的原始阵容（单位 + 建筑，含原来的数量与格子）原样回来。
#
# 与逐单位 ``respawn <类型> <秒>`` 互斥：逐单位刷新意味着单位各回各的，
# 势力永远不会真的被消灭；整体刷新意味着势力作为一个整体被打掉、
# 过一段时间再作为一个整体回来。
#
# 实现：势力被全歼的那一刻（``Creature.die`` 里发现这已经是最后一个
# 活着的单位）排一次队列；到期时按 ``player._respawn_roster`` 重建阵容。

def group_respawn_seconds_for(player):
    """这个玩家配置的势力整体刷新时限（毫秒）。0 = 没配置。"""
    if player is None:
        return 0
    try:
        return int(getattr(player, "_respawn_group_seconds", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _living_combat_units(player):
    """玩家还活着的单位（不含已在刷新队列里等着的）。"""
    units = getattr(player, "units", None) or []
    return [u for u in units if getattr(u, "place", None) is not None]


def schedule_group_respawn(player, world=None):
    """势力被全歼时调用：排一次「整队回来」。

    返回到期时间（毫秒）；没配置整体刷新时返回 ``None``。
    """
    delay = group_respawn_seconds_for(player)
    if delay <= 0:
        return None
    if world is None:
        world = getattr(player, "world", None)
    if world is None:
        return None
    # 已经在队列里了 —— 不要重复排。
    for deadline, owner in _group_queue(world):
        if owner is player:
            return deadline
    now = getattr(world, "time", 0)
    deadline = now + delay
    queue = _group_queue(world)
    queue.append((deadline, player))
    queue.sort(key=lambda item: item[0])
    return deadline


def schedule_group_respawn_if_wiped_out(unit):
    """单位死掉时调用：这个单位是不是本势力的最后一个？

    是的话 —— 整个势力被打光了 —— 排一次整队复活的队列。

    必须在 ``Creature.die()`` 里、``delete()`` **之前**调用：那时单位还
    在玩家的名册里，才能数清楚还剩几个。

    触发点刻意**不在** ``Player.remove()`` 里：那个方法也会在归属转移
    （认领一只羊、夺回建筑）时被调用，那时势力并没有被打光。
    """
    player = getattr(unit, "player", None)
    if player is None:
        return None
    if not getattr(player, "_respawn_group_armed", False):
        return None
    if getattr(player, "has_been_defeated", False):
        return None
    # 队列里已经有一支在等着了 —— 不要重复排。
    world = getattr(unit, "world", None)
    if world is None:
        world = getattr(player, "world", None)
    if world is None:
        return None
    for _deadline, owner in _group_queue(world):
        if owner is player:
            return None
    # 还有活着的单位 —— 还没被全歼。
    for other in getattr(player, "units", ()) or ():
        if other is unit:
            continue
        if getattr(other, "place", None) is not None:
            return None
    return schedule_group_respawn(player, world)


def _group_queue(world):
    """取出（必要时创建）世界的势力整体刷新队列。"""
    q = getattr(world, "_respawn_group_queue", None)
    if q is None:
        q = []
        world._respawn_group_queue = q
    return q


def player_has_pending_group_respawn(player, world=None):
    """这个玩家有一支整队正在等着回来吗？

    等待期间它**不算输** —— 势力马上就会回来。
    """
    if player is None:
        return False
    if world is None:
        world = getattr(player, "world", None)
    if world is None:
        return False
    for _deadline, owner in _group_queue(world):
        if owner is player:
            return True
    return False


def tick_group_respawns(world):
    """每秒调用一次：把到期的势力整体刷新做掉。

    格子放不下（玩家站在那儿）时**不丢弃**记录 —— 推到下一个 tick
    再试。
    """
    if world is None:
        return
    queue = _group_queue(world)
    if not queue:
        return
    now = getattr(world, "time", 0)
    remaining = []
    for deadline, player in queue:
        if deadline > now:
            remaining.append((deadline, player))
            continue
        try:
            if not restore_group_roster(world, player):
                # 格子满了 —— 稍后再试。
                remaining.append((deadline, player))
        except Exception:
            warning("couldn't respawn the %s garrison", player)
            remaining.append((deadline, player))
    world._respawn_group_queue = remaining


def restore_group_roster(world, player):
    """按原始阵容重建这个势力的部队。成功返回 True。

    原始阵容记在 ``player._respawn_roster`` 里：``(方格, 类型名, 数量)``。
    只恢复**还缺的那些** —— 已经站着的单位不动（避免每次重试都叠一份）。
    """
    if world is None or player is None:
        return False
    roster = getattr(player, "_respawn_roster", None) or []
    if not roster:
        return False
    # 主人已经被击败 / 退出了，就别再刷了。
    if getattr(player, "has_been_defeated", False):
        return True
    if not getattr(player, "is_playing", True):
        return True

    from .definitions import rules

    # 现在这个势力实际还站着什么：(类型名, 格子) -> 数量
    standing = {}
    for unit in _living_combat_units(player):
        key = (getattr(unit, "type_name", None), getattr(unit, "place", None))
        standing[key] = standing.get(key, 0) + 1

    complete = True
    for place, type_name, count in roster:
        if not place or not type_name or count <= 0:
            continue
        have = standing.get((type_name, place), 0)
        missing = count - have
        if missing <= 0:
            continue
        unit_cls = rules.unit_class(type_name)
        if unit_cls is None:
            continue
        for _ in range(missing):
            try:
                if not place.have_enough_square_space(unit_cls, player=player):
                    # 格子满了 —— 这次不算成功，下个 tick 再试。
                    complete = False
                    continue
            except Exception:
                complete = False
                continue
            before = len(getattr(player, "units", ()) or ())
            try:
                player.add_unit(unit_cls, place)
            except Exception:
                warning("couldn't respawn %s", type_name)
                complete = False
                continue
            after = len(getattr(player, "units", ()) or ())
            if after <= before:
                # ``add_unit`` 在格子放不下时会静默返回。
                complete = False
                continue
            key = (type_name, place)
            standing[key] = standing.get(key, 0) + 1
    return complete
