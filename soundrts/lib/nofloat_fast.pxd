# cython: language_level=3
"""nofloat_fast 的 C 级签名声明。

其他 .pyx 模块用 ``from soundrts.lib.nofloat_fast cimport int_distance``
即可在 ``with nogil:`` / ``cdef ... nogil`` 块里直接调用这些函数（无 GIL）。
"""

cpdef int int_cos_1000(int angle) nogil
cpdef int int_sin_1000(int angle) nogil
cpdef long long square_of_distance(long long x1, long long y1,
                                   long long x2, long long y2) nogil
cpdef long long int_sqrt(long long x) nogil
cpdef long long int_distance(long long x1, long long y1,
                             long long x2, long long y2) nogil
cpdef int int_angle(long long x1, long long y1,
                    long long x2, long long y2) nogil
