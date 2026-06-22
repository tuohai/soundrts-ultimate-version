# distutils: language = c++
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=False
"""C++ ECS Phase 1: unit scalar SoA + spatial bucket build.

Hybrid ECS: Python ``Unit`` objects stay authoritative. Each tick we snapshot
``x``/``y`` into contiguous C++ vectors and run the bucket inner loop without
per-iteration ``u.x`` attribute reads.

Determinism: integer coordinates, stable slot order, ``//`` uses Python floor
division (``cdivision=False``).
"""

from libcpp.vector cimport vector


cdef class UnitStore:
    """Struct-of-arrays for unit positions. Slot *i* parallels Python ``units[i]``."""

    cdef vector[long long] _x
    cdef vector[long long] _y
    cdef int _size

    cpdef int count(self):
        return self._size

    cpdef void clear(self):
        self._x.clear()
        self._y.clear()
        self._size = 0

    cpdef int add_slot(self, long long x, long long y):
        self._x.push_back(x)
        self._y.push_back(y)
        self._size += 1
        return self._size - 1

    cpdef int remove_slot(self, int slot):
        """Swap-remove *slot*. Return index that moved into *slot*, or -1."""
        cdef int last
        if slot < 0 or slot >= self._size:
            return -1
        last = self._size - 1
        if slot != last:
            self._x[slot] = self._x[last]
            self._y[slot] = self._y[last]
        self._x.pop_back()
        self._y.pop_back()
        self._size -= 1
        if slot != last:
            return slot
        return -1

    cpdef void set_slot(self, int slot, long long x, long long y):
        if 0 <= slot < self._size:
            self._x[slot] = x
            self._y[slot] = y

    cpdef void sync_from_scalars(self, list xs, list ys):
        """Bulk load parallel int lists (single Python boundary crossing)."""
        cdef int n = len(xs)
        cdef int i
        cdef long long xv, yv
        if n != len(ys):
            raise ValueError("xs and ys must have the same length")
        self.clear()
        if n == 0:
            return
        self._x.reserve(n)
        self._y.reserve(n)
        for i in range(n):
            xv = xs[i]
            yv = ys[i]
            self._x.push_back(xv)
            self._y.push_back(yv)
        self._size = n

    cpdef dict build_buckets(self, long long A, objects):
        """Build ``{(gx, gy): [unit, ...]}`` from SoA arrays."""
        cdef dict buckets = {}
        cdef long long gx, gy
        cdef int i, n
        cdef tuple k
        cdef object u, bucket
        n = self._size
        for i in range(n):
            u = objects[i]
            if u is None:
                continue
            gx = self._x[i] // A
            gy = self._y[i] // A
            k = (gx, gy)
            bucket = buckets.get(k)
            if bucket is None:
                buckets[k] = [u]
            else:
                bucket.append(u)
        return buckets
