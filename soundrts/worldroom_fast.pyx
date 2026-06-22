# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的寻路 / 路径重建原语。

设计取舍：``Square.shortest_path_to`` 的 A* 主循环依赖大量 Python callback
（``is_blocked(player, ignore_enemy_walls=True)``、``avoid(v)``）与多态节点
（Square / Exit），整体 Cython 化收益有限。本模块只抽取确实可加速的子操作：

* ``astar_heuristic(node, end_x, end_y)``：替代闭包 ``_heuristic``，
  直接调 Cython 的 ``int_distance``，省一层闭包对象
* ``reconstruct_path(came_from, end, start)``：路径回溯紧循环
* ``add_edge_costs(graph, v, exits)``：为起点/终点动态加边的小工具

``Square`` 类保持不动（17 个 @property，在 cloudpickle 图内）。
"""

cimport cython
# 注意：用 Python import 而非 cimport，避免对 nofloat_fast 暴露 .pxd 的额外维护成本。
# 函数调用经过 Python 边界，但 ``int_distance`` 本身是 cpdef，开销可忽略。
from soundrts.lib.nofloat_fast import int_distance


def astar_heuristic(node, long long end_x, long long end_y):
    """A* 启发式：node 到终点的整数距离。

    与原 ``_heuristic`` 闭包等价：异常时返回 0（兼容缺失 x/y 的退化节点）。
    """
    try:
        return int_distance(node.x, node.y, end_x, end_y)
    except Exception:
        return 0


cpdef list reconstruct_path(dict came_from, end, start):
    """A* 完成后从 ``came_from`` dict 重建路径，从 start 到 end。

    与原版 Python 等价：
        Path = []
        while 1:
            Path.append(end)
            if end == start:
                break
            end = came_from[end]
        Path.reverse()
    """
    cdef list path = []
    cdef int safety = 0  # 防止数据损坏导致无限循环
    cdef int max_iter = 1 << 20  # 100万节点保护上限
    while True:
        path.append(end)
        if end is start or end == start:
            break
        end = came_from[end]
        safety += 1
        if safety > max_iter:
            raise RuntimeError("reconstruct_path: came_from chain too long, possible cycle")
    path.reverse()
    return path


cpdef object cached_is_blocked(node, player, dict block_cache, long long player_id):
    """``is_blocked`` 200ms 缓存的统一查询。

    返回 True/False；缓存键为 ``(id(node), player_id)``，与原版一致。
    """
    cdef tuple lk = (id(node), player_id)
    cdef object blocked = block_cache.get(lk)
    if blocked is not None:
        return blocked
    try:
        blocked = node.is_blocked(player, ignore_enemy_walls=True)
    except Exception:
        blocked = False
    block_cache[lk] = blocked
    return blocked
