# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的世界级每 tick 全单位扫描。

服务对象：``WorldGameMixin._update_buckets`` / ``_update_cloaking`` /
``_update_detection``。这三个函数每 tick × 所有 active players × 所有 units
被调用，是 RTS 主循环的稳定开销。

设计：函数全部 cpdef，输入是 Python 序列（``p.units``、邻居列表等），
内部用 ``long long`` 做距离比较，避免 PyLong 中间对象。

注意：``//`` 全部用 Python floor division（``cdivision=False``），保证 ``u.x``
出现负数时与原版一致。

多线程 PoC：``mark_cloaked_parallel`` 是 ``mark_cloaked`` 的 OpenMP 并行版本。
*只在候选规模足够大（默认 >= 64 单位）时才比单线程快*；
小规模下线程启停的开销会吃掉收益。详见函数 docstring。
"""

cimport cython
from cython.parallel cimport prange
from cpython.array cimport array as cpy_array
import array as py_array


@cython.cdivision(False)
cpdef dict build_buckets(units, long long A):
    """``WorldGameMixin._update_buckets`` 的内层：

        for u in units:
            k = (u.x // A, u.y // A)
            buckets.setdefault(k, []).append(u)

    返回新构造的 dict。

    ``bucket`` 不能 ``cdef list``——``dict.get`` 可能返回 None，赋给
    typed list 会触发 C 层 SEGV。保留 Python object 类型即可。
    """
    cdef dict buckets = {}
    cdef long long gx, gy
    cdef tuple k
    for u in units:
        gx = u.x // A
        gy = u.y // A
        k = (gx, gy)
        bucket = buckets.get(k)  # 保持 Python object 类型
        if bucket is None:
            buckets[k] = [u]
        else:
            bucket.append(u)
    return buckets


cpdef int mark_cloaked(candidates, long long cx, long long cy,
                       long long radius2) except -1:
    """``_update_cloaking`` 的内层：

        for vu in candidates:
            if not vu.is_cloakable or vu.is_cloaked:
                continue
            if (vu.x - cx)^2 + (vu.y - cy)^2 < radius2:
                vu.is_cloaked = True

    返回标记数量（供调试/统计；调用方可忽略）。
    """
    cdef long long dx, dy
    cdef int count = 0
    for vu in candidates:
        if not vu.is_cloakable:
            continue
        if vu.is_cloaked:
            continue
        dx = vu.x - cx
        dy = vu.y - cy
        if dx * dx + dy * dy < radius2:
            vu.is_cloaked = True
            count += 1
    return count


# ===================================================================
# 重要：mark_cloaked_parallel 的实测结论（保留作为教学 / 未来参考）
# ===================================================================
# 在 16 核 Windows + Cython 3.0.12 + MSVC /openmp 下实测：
#
#       n     serial(ms)   par-auto(ms)   par-2(ms)   par-4(ms)   speedup
#      16      0.0005          0.0059        0.0031     0.0034     0.16x
#      64      0.0028          0.0128        0.0075     0.0080     0.37x
#     512      0.0164          0.0770        0.0467     0.0491     0.35x
#    2048      0.0679          0.2972        0.1841     0.1902     0.37x
#    8192      0.2697          1.2886        0.8220     0.7844     0.34x
#
# 结论：**在所有规模下并行版都比单线程慢 0.16x ~ 0.37x**。
#
# 原因：
# 1. 单线程版本直接在 Python 对象列表上迭代，零拷贝。
# 2. 并行版必须先把 (x, y, eligible) 复制到 typed C 数组（O(n) 开销），
#    再用 nogil + prange 算 hit_mask（O(n) 计算），最后再 O(n) 写回。
# 3. 真正的并行计算量太少（每个候选只是 dx*dx + dy*dy < r² 一次比较），
#    O(n) 复制开销 + 线程启停成本 >>  并行带来的计算收益。
#
# 要让并行真正有意义，必须满足以下任一条件：
# (a) 数据本身已经在 C 数组里（需要重构 RTS 数据模型，工作量巨大）
# (b) 每个元素的计算量大得多（如完整 A* / 多次 sqrt / 复杂判定）
#
# 因此 `_update_cloaking` 应继续使用单线程 `mark_cloaked`。
# `mark_cloaked_parallel` 保留作为：
#   * 未来重构 SoA 数据模型后的接入点
#   * 多线程 PoC 教学样本
#   * `nogil` + `prange` + `typed memoryview` 的最小可运行示例
# ===================================================================
# 经验阈值：实测下不存在"启用并行更快"的拐点，保留 64 仅作为占位常量。
DEF _PARALLEL_THRESHOLD = 64


cpdef int mark_cloaked_parallel(candidates, long long cx, long long cy,
                                long long radius2,
                                int num_threads=0) except -1:
    """``mark_cloaked`` 的 OpenMP 并行版本（PoC，**实测不快**）。

    与单线程版本**数值上完全等价**——所有命中的单位 ``is_cloaked`` 都会被
    设为 True，未命中的不变。``is_cloaked = True`` 是幂等写，多核同时命中
    同一目标不会产生 race condition。

    实现：三阶段，分离 Python-object 访问与数值计算：

    1. **GIL Phase**：遍历 candidates 一次，把 (x, y, eligible_flag) 抽到
       typed C 数组（``signed char`` / ``long long``）。
    2. **nogil + prange Phase**：纯 C 数组上的并行距离比较，写入 hit_mask。
       这是唯一真正多核并发的部分。
    3. **GIL Phase**：根据 hit_mask 把 ``is_cloaked = True`` 写回 Python 对象。

    Args:
        num_threads: 0 = OpenMP 自动（一般 = CPU 核数）；> 0 = 指定线程数。

    Returns:
        命中并标记的单位数量。

    实测警告（见文件顶部表格）：
        在所有规模下本函数都**比单线程 mark_cloaked 慢**，因为数据复制
        开销超过并行收益。除非未来重构数据模型让坐标已经在 C 数组里，
        否则**不应**调用此函数；保留它仅作为 PoC 教学 + 未来扩展接入点。
    """
    cdef int n = len(candidates)
    cdef int i
    cdef int count = 0
    cdef long long dx, dy

    if n == 0:
        return 0

    cdef cpy_array xs = py_array.array("q", [0] * n)
    cdef cpy_array ys = py_array.array("q", [0] * n)
    cdef cpy_array eligible = py_array.array("b", [0] * n)
    cdef cpy_array hit = py_array.array("b", [0] * n)

    cdef long long[:] xs_view = xs
    cdef long long[:] ys_view = ys
    cdef signed char[:] eligible_view = eligible
    cdef signed char[:] hit_view = hit

    # Phase 1: 抽数据（持 GIL）
    for i in range(n):
        vu = candidates[i]
        if vu.is_cloakable and not vu.is_cloaked:
            xs_view[i] = vu.x
            ys_view[i] = vu.y
            eligible_view[i] = 1
        # else: eligible_view[i] 保持 0，并行循环会跳过

    # Phase 2: 并行扫描（nogil + OpenMP prange）
    # Cython 限制：num_threads 不能用变量传给 prange，所以分两个分支。
    if num_threads > 0:
        with nogil:
            for i in prange(n, schedule="static", num_threads=num_threads):
                if eligible_view[i]:
                    dx = xs_view[i] - cx
                    dy = ys_view[i] - cy
                    if dx * dx + dy * dy < radius2:
                        hit_view[i] = 1
    else:
        with nogil:
            for i in prange(n, schedule="static"):
                if eligible_view[i]:
                    dx = xs_view[i] - cx
                    dy = ys_view[i] - cy
                    if dx * dx + dy * dy < radius2:
                        hit_view[i] = 1

    # Phase 3: 写回（持 GIL）
    for i in range(n):
        if hit_view[i]:
            candidates[i].is_cloaked = True
            count += 1
    return count


def get_parallel_threshold() -> int:
    """返回并行版的经验启用阈值（candidate 数）。

    调用方可据此选择 ``mark_cloaked`` 还是 ``mark_cloaked_parallel``。
    """
    return _PARALLEL_THRESHOLD


cpdef list collect_invisibles_in_range(candidates, long long cx, long long cy,
                                       long long radius2, set already_detected):
    """``_update_detection`` 的内层：

        for iu in candidates:
            if not (iu.is_invisible or iu.is_cloaked):
                continue
            if iu in already_detected:
                continue
            if (iu.x - cx)^2 + (iu.y - cy)^2 < radius2:
                result.append(iu)

    返回 list，让调用方接着做 ``share_detection`` / ``allied_vision`` 广播。
    """
    cdef list result = []
    cdef long long dx, dy
    for iu in candidates:
        if not (iu.is_invisible or iu.is_cloaked):
            continue
        if iu in already_detected:
            continue
        dx = iu.x - cx
        dy = iu.y - cy
        if dx * dx + dy * dy < radius2:
            result.append(iu)
    return result
