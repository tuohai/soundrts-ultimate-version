# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: initializedcheck=False
"""Cython 加速的整数三角/距离原语。

提供与 ``soundrts.lib.nofloat`` 同名同签名的函数；``nofloat.py`` 在导入时
若发现本模块可用，会用此处的实现覆盖纯 Python 版本。

关键约束（必须与纯 Python 版本数值结果完全一致，否则 RTS 会 desync）：

* ``int_cos_1000`` / ``int_sin_1000`` 用同一份查表构造算法
  （``int(math.cos/sin(radians(a)) * PRECISION)``）
* ``int_sqrt`` 保留 Python 版本的 floor 修正循环（即使 C ``sqrt`` 在所有平台
  上都精确，仍按相同算法走一遍，万无一失）
* ``int_angle`` 的 acos 查表用同一构造算法
* ``square_of_distance`` 用 ``long long``（int64）避免 1000x1000 地图下
  ``dx*dx + dy*dy`` 超 int32（最坏 2e12）

所有纯数值公开函数为 ``cpdef ... nogil``，既可在持 GIL 的 Python
环境下调用，也可在 ``with nogil:`` 块里被其他 Cython 模块调用（如多线程
全单位扫描）。``to_int`` 涉及 Python ``float()`` / ``isinstance``，无法 nogil。

注意 ``nogil`` 函数体禁止访问 Python 对象、抛 Python 异常；
``int_sqrt`` 的 ``return 0`` 已经替代了原 Python 版的 ``ValueError`` 路径。
"""

cimport cython
from libc.math cimport sqrt as c_sqrt, cos as c_cos, sin as c_sin, acos as c_acos


cdef int _PRECISION = 1000

cdef int _COS_TABLE[360]
cdef int _SIN_TABLE[360]
cdef int _ACOS_TABLE[201]

cdef double _DEG2RAD = 0.017453292519943295  # math.pi / 180


cdef void _init_tables() noexcept:
    """构造与 Python 版本字节一致的查表。"""
    cdef int a
    cdef double rad
    cdef int c
    for a in range(360):
        rad = a * _DEG2RAD
        _COS_TABLE[a] = <int>(c_cos(rad) * _PRECISION)
        _SIN_TABLE[a] = <int>(c_sin(rad) * _PRECISION)
    for c in range(-100, 101):
        _ACOS_TABLE[c + 100] = <int>(c_acos(c / 100.0) / _DEG2RAD)


_init_tables()


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int int_cos_1000(int angle) nogil:
    """angle in degrees; result = cos(angle) * 1000

    Python ``%`` 对负数返回 [0, divisor)，而 C ``%`` 保留符号。本文件全局
    启用了 ``cdivision=True``，因此必须手动 wrap 负数索引，否则会读到
    数组越界（无声 UB）。
    """
    cdef int idx = angle % 360
    if idx < 0:
        idx += 360
    return _COS_TABLE[idx]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef int int_sin_1000(int angle) nogil:
    """angle in degrees; result = sin(angle) * 1000"""
    cdef int idx = angle % 360
    if idx < 0:
        idx += 360
    return _SIN_TABLE[idx]


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long long square_of_distance(long long x1, long long y1,
                                   long long x2, long long y2) nogil:
    cdef long long dx = x2 - x1
    cdef long long dy = y2 - y1
    return dx * dx + dy * dy


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long long int_sqrt(long long x) nogil:
    """与纯 Python 版本字节等价的整数开方。

    Python 版本：r = int(math.sqrt(x))，再 +/- 1 修正。
    C 版本：用 C 的 sqrt + 同样修正循环。在 IEEE 754 平台上，C 与 Python 的
    ``sqrt`` 输出完全一致；修正循环作为安全网保留。
    """
    if x < 0:
        # nogil 不能 raise；调用方从未传入负数（距离平方恒 >= 0），
        # 这里返回 0 防 UB，与原"持 GIL"版本行为兼容（不 raise）。
        return 0
    cdef long long r = <long long>c_sqrt(<double>x)
    while r * r > x:
        r -= 1
    while (r + 1) * (r + 1) < x:
        r += 1
    return r


@cython.boundscheck(False)
@cython.wraparound(False)
cpdef long long int_distance(long long x1, long long y1,
                             long long x2, long long y2) nogil:
    return int_sqrt(square_of_distance(x1, y1, x2, y2))


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.cdivision(False)
cpdef int int_angle(long long x1, long long y1,
                    long long x2, long long y2) nogil:
    """返回与 x 轴的角度（度）。

    数学上 c = (x2-x1) * 100 / d，由 Cauchy-Schwarz |c| <= 100 当 d > 0，
    所以 acos 表索引一定在 [-100, 100] 范围内。defensive clamp 保险。

    ``cdivision(False)`` 让 ``//`` 沿用 Python 的 floor division 语义；
    必须如此，否则 ``-7 // 2`` 在 C 下变 -3（截断），Python 下是 -4（向下取整），
    会导致角度与纯 Python 版本不一致 → RTS desync。
    """
    cdef long long d = int_distance(x1, y1, x2, y2)
    cdef long long c
    cdef int ac
    if d == 0:
        return 0
    c = (x2 - x1) * 100 // d
    if c < -100:
        c = -100
    elif c > 100:
        c = 100
    ac = _ACOS_TABLE[<int>c + 100]
    if y2 - y1 > 0:
        return ac
    return -ac


def to_int(s):
    """convert a string to an integer with PRECISION

    保持与 Python 版本一致的接口（input 必为 str）。
    """
    assert isinstance(s, str)
    return int(float(s) * _PRECISION)
