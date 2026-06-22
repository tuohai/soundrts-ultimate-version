# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: initializedcheck=False
"""Cython 加速的碰撞矩阵原语。

策略：``CollisionMatrix`` 类保持纯 Python 实现以兼容 cloudpickle
（``World.collision`` 在存档对象图内）；仅把热点方法 ``would_collide`` /
``add`` / ``remove`` / ``_shape`` / ``_key`` 的内部计算委托给这里的
cpdef 函数。

数学上必须与 Python 版本字节一致：

* ``_key(x, y) = x // res + amax * (y // res)``
* ``_shape(x, y) = { key + a + amax * b for (a, b) in SHAPE }``
* ``SHAPE = ((0,0), (1,0), (-1,0), (0,1), (0,-1))``（十字 5 格）

注意：``//`` 在此处使用 Python floor division（``cdivision=False``）以保证
负数情况下与 Python 一致。实际使用中 x/y 均非负，但 defensive。
"""

cimport cython


cdef long long _SHAPE_DX[5]
cdef long long _SHAPE_DY[5]


cdef void _init_shape() noexcept:
    """与 collision.SHAPE 完全一致的十字 5 格偏移。"""
    cdef int i
    cdef tuple shape = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
    for i in range(5):
        _SHAPE_DX[i] = shape[i][0]
        _SHAPE_DY[i] = shape[i][1]


_init_shape()


@cython.cdivision(False)
cpdef long long compute_key(long long x, long long y,
                            long long res, long long amax):
    """``x // res + amax * (y // res)``，与 Python 版本一致的 floor div。"""
    return x // res + amax * (y // res)


@cython.cdivision(False)
cpdef tuple xy_from_key(long long k, long long res, long long amax):
    cdef long long b = k // amax
    cdef long long a = k % amax
    return a * res, b * res


@cython.cdivision(False)
cpdef set compute_shape(long long x, long long y,
                        long long res, long long amax):
    """返回十字 5 格 key 的 Python set。

    与原版 ``{ key + a + amax * b for (a, b) in SHAPE }`` 数学等价：
    设 key = compute_key(x, y)，则每个 shape 偏移 (dx, dy)（注意 collision.py
    的 SHAPE 偏移是格子数，不是像素），加到 key 上 = ``key + dx + amax * dy``。
    """
    cdef long long key = x // res + amax * (y // res)
    cdef int i
    cdef set result = set()
    for i in range(5):
        result.add(key + _SHAPE_DX[i] + amax * _SHAPE_DY[i])
    return result


@cython.cdivision(False)
cpdef set would_collide_fn(set _set, long long x, long long y,
                           long long res, long long amax):
    """返回 _set ∩ shape(x, y)。"""
    return _set.intersection(compute_shape(x, y, res, amax))


@cython.cdivision(False)
cpdef add_fn(set _set, long long x, long long y,
             long long res, long long amax):
    """_set |= shape(x, y)，就地修改。"""
    _set.update(compute_shape(x, y, res, amax))


@cython.cdivision(False)
cpdef remove_fn(set _set, long long x, long long y,
                long long res, long long amax):
    """_set -= shape(x, y)，就地修改。"""
    _set.difference_update(compute_shape(x, y, res, amax))
