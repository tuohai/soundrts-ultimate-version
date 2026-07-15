# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的 AI 决策内层热点 (D-Phase 1).

抽取 ``world_ai_decision.py`` 里**纯计算**部分:
* ``bfs_squares_in_sight`` — sight_range BFS, 输入 Python Square, 返回 set
* ``compute_decide_interval`` — ai_mode/speed/状态 → interval int

不动 Creature mixin 架构, 不依赖 cdef class.
单位 hot path 上层 (self.xxx) 仍走 Python, 这里只省 frame setup + 内层 loop
的字节码 dispatch. 配合 caller 端的帧级 cache, 实测 -3-4%.
"""

cimport cython


# === AI mode → int 映射 (避免 Python str hash) ============================
# caller 端导出 AI_MODE_* 常量, 在 hot path 上比较 int 比比 str 快 ~5x.
AI_MODE_OFFENSIVE = 0
AI_MODE_CHASE = 1
AI_MODE_DEFENSIVE = 2
AI_MODE_GUARD = 3
AI_MODE_OTHER = 4


cpdef int compute_decide_interval(int ai_mode_id, int speed,
                                  bint has_attacker, bint has_orders,
                                  bint truly_idle=False):
    """根据 ai_mode / speed / 攻击状态 / 命令状态返回 decide 间隔 (毫秒).

    ``truly_idle``: 无订单、无攻击者、非 auto_explore — 再拉开间隔以少进 decide 主体。
    """
    cdef int interval
    if ai_mode_id == AI_MODE_OFFENSIVE or ai_mode_id == AI_MODE_CHASE:
        # Was 100; 150 cuts decide volume ~33% with acceptable AI latency.
        interval = 150
    elif ai_mode_id == AI_MODE_DEFENSIVE:
        interval = 200
    else:
        interval = 400

    if speed <= 0:
        interval += 300

    if has_attacker:
        if interval > 80:
            interval = 80

    if has_orders:
        # max(80, interval - 70)
        interval -= 70
        if interval < 80:
            interval = 80
    elif truly_idle:
        # No orders / attacker / auto_explore: engagement still driven by
        # contact_force perception + next decide; 600ms keeps same-square
        # response within~1 tick of contact under normal load.
        if interval < 600:
            interval = 600

    return interval


cpdef set bfs_squares_in_sight(object start_place, int sight_range):
    """BFS 展开视野: 从 ``start_place`` 出发, 最远走 ``sight_range`` 步.

    输入 ``start_place``: 任意有 ``.neighbors`` (返回可迭代 Square) 的对象.
    输出 ``set`` of Square — 包含 ``start_place`` 自身和所有 ≤ sight_range
    步内可达的 neighbors.

    等价于 ``world_ai_decision.py:_get_squares_in_sight`` 的语义.
    """
    cdef set squares = {start_place}

    if sight_range <= 1:
        return squares

    # sight_range == 2: 只加直接邻居
    if sight_range <= 2:
        for p in start_place.neighbors:
            squares.add(p)
        return squares

    # sight_range > 2: 多步 BFS
    cdef set visited = {start_place}
    cdef list queue = [(start_place, 0)]
    cdef int distance
    cdef int qi = 0
    cdef int qlen = 1
    cdef object current_place, neighbor

    while qi < qlen:
        current_place, distance = queue[qi]
        qi += 1

        if distance >= sight_range:
            continue

        for neighbor in current_place.neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                squares.add(neighbor)
                queue.append((neighbor, distance + 1))
                qlen += 1

    return squares
