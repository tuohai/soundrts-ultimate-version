# distutils: language = c++
# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=False
"""C++ ECS: unit scalar SoA + spatial bucket build + Euclidean observer filter.

Hybrid ECS: Python ``Unit`` objects stay authoritative. Each tick we snapshot
``x``/``y``/``sight_range``/``is_inside`` into contiguous C++ vectors and run
hot loops without per-iteration attribute reads.

Determinism: integer coordinates, stable slot order, ``//`` uses Python floor
division (``cdivision=False``).

Flag bits (``_flags``):
  bit0 = is_inside (skip as observer, same as ``_is_seeing``)
"""

from libcpp.vector cimport vector

cdef unsigned char FLAG_INSIDE = 1


cdef class UnitStore:
    """Struct-of-arrays for unit scalars. Slot *i* parallels Python ``units[i]``."""

    cdef vector[long long] _x
    cdef vector[long long] _y
    cdef vector[long long] _sight
    cdef vector[unsigned char] _flags
    cdef int _size

    cpdef int count(self):
        return self._size

    cpdef void clear(self):
        self._x.clear()
        self._y.clear()
        self._sight.clear()
        self._flags.clear()
        self._size = 0

    cpdef int add_slot(self, long long x, long long y,
                       long long sight=0, unsigned char flags=0):
        self._x.push_back(x)
        self._y.push_back(y)
        self._sight.push_back(sight)
        self._flags.push_back(flags)
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
            self._sight[slot] = self._sight[last]
            self._flags[slot] = self._flags[last]
        self._x.pop_back()
        self._y.pop_back()
        self._sight.pop_back()
        self._flags.pop_back()
        self._size -= 1
        if slot != last:
            return slot
        return -1

    cpdef void set_slot(self, int slot, long long x, long long y,
                        long long sight=0, unsigned char flags=0):
        if 0 <= slot < self._size:
            self._x[slot] = x
            self._y[slot] = y
            self._sight[slot] = sight
            self._flags[slot] = flags

    cpdef void sync_slots_from_units(self, objects):
        """In-place refresh of existing slots from Python units (no clear/rebuild).

        Slot *i* must already parallel ``objects[i]``. Used on the hot tick path
        so ECS keeps SoA sight/position without reallocating vectors every frame.
        """
        cdef int i, n
        cdef object u, sr
        cdef long long xv, yv, sv
        cdef unsigned char fv
        n = self._size
        if len(objects) != n:
            raise ValueError("objects length must match store size")
        for i in range(n):
            u = objects[i]
            xv = u.x
            yv = u.y
            sr = getattr(u, "sight_range", 0)
            sv = <long long>sr if sr else 0
            fv = FLAG_INSIDE if getattr(u, "is_inside", False) else 0
            self._x[i] = xv
            self._y[i] = yv
            self._sight[i] = sv
            self._flags[i] = fv

    cpdef void sync_from_scalars(self, list xs, list ys,
                                 list sights=None, list flags=None):
        """Bulk load parallel int lists (single Python boundary crossing)."""
        cdef int n = len(xs)
        cdef int i
        cdef long long xv, yv, sv
        cdef unsigned char fv
        cdef bint have_sight = sights is not None
        cdef bint have_flags = flags is not None
        if n != len(ys):
            raise ValueError("xs and ys must have the same length")
        if have_sight and n != len(sights):
            raise ValueError("xs and sights must have the same length")
        if have_flags and n != len(flags):
            raise ValueError("xs and flags must have the same length")
        self.clear()
        if n == 0:
            return
        self._x.reserve(n)
        self._y.reserve(n)
        self._sight.reserve(n)
        self._flags.reserve(n)
        for i in range(n):
            xv = xs[i]
            yv = ys[i]
            sv = <long long>sights[i] if have_sight else 0
            fv = <unsigned char>flags[i] if have_flags else 0
            self._x.push_back(xv)
            self._y.push_back(yv)
            self._sight.push_back(sv)
            self._flags.push_back(fv)
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

    cpdef list filter_candidates_euclidean(self, candidates, dict id_to_slot,
                                           long long tx, long long ty):
        """Euclidean + inside filter over a small candidate list (e.g. 3×3 halo).

        Looks up SoA scalars via ``id_to_slot[unit.id]``; falls back to Python
        attrs if the slot is missing. Prefer this over ``observers_seeing_point``
        when ``player._buckets`` neighbor cache is warm.
        """
        cdef list result = []
        cdef object u, slot_obj, sr
        cdef int slot
        cdef long long dx, dy, sv, sr2
        for u in candidates:
            if u is None:
                continue
            slot_obj = id_to_slot.get(getattr(u, "id", None))
            if slot_obj is None:
                if getattr(u, "is_inside", False):
                    continue
                sr = getattr(u, "sight_range", 0)
                if not sr:
                    continue
                dx = u.x - tx
                dy = u.y - ty
                sv = <long long>sr
                if dx * dx + dy * dy >= sv * sv:
                    continue
                result.append(u)
                continue
            slot = slot_obj
            if slot < 0 or slot >= self._size:
                continue
            if self._flags[slot] & FLAG_INSIDE:
                continue
            sv = self._sight[slot]
            if sv == 0:
                continue
            dx = self._x[slot] - tx
            dy = self._y[slot] - ty
            sr2 = sv * sv
            if dx * dx + dy * dy >= sr2:
                continue
            result.append(u)
        return result

    cpdef list mark_enemies_seen_by_observers(self, dict id_to_slot,
                                              list observers, list enemies,
                                              dict observed_cache=None):
        """Mark enemies seen by any observer in *observers* (1.3.8.1 geometry).

        ``observed_cache`` (optional ``{id(unit): set}``) shares tick topology
        across overlapping 3×3 cell queries in one ``batch_see_enemies`` call.
        """
        cdef list result = []
        cdef object seen = set()
        cdef object avu, enemy, place, observed, slot_obj, sr, opt, data
        cdef object oid
        cdef int slot
        cdef int n_enemies
        cdef long long ox, oy, sr2, dx, dy, ex, ey, sv
        cdef bint have_soa
        cdef bint have_cache = observed_cache is not None

        if not observers or not enemies:
            return result

        n_enemies = len(enemies)
        for avu in observers:
            if avu is None:
                continue
            if n_enemies > 0 and len(result) >= n_enemies:
                break
            slot_obj = id_to_slot.get(getattr(avu, "id", None))
            have_soa = slot_obj is not None
            if have_soa:
                slot = slot_obj
                if slot < 0 or slot >= self._size:
                    continue
                if self._flags[slot] & FLAG_INSIDE:
                    continue
                sv = self._sight[slot]
                if sv == 0:
                    continue
                ox = self._x[slot]
                oy = self._y[slot]
                sr2 = sv * sv
            else:
                if getattr(avu, "is_inside", False):
                    continue
                sr = getattr(avu, "sight_range", 0)
                if not sr:
                    continue
                ox = avu.x
                oy = avu.y
                sv = <long long>sr
                sr2 = sv * sv
            oid = id(avu)
            observed = observed_cache.get(oid) if have_cache else None
            if observed is None:
                opt = getattr(avu, "get_observed_squares_optimized", None)
                if opt is not None:
                    data = opt()
                    observed = data["all"] if data is not None else None
                if observed is None:
                    observed = set(avu.get_observed_squares())
                if have_cache:
                    observed_cache[oid] = observed
            for enemy in enemies:
                if enemy is None or id(enemy) in seen:
                    continue
                place = enemy.place
                if place is None:
                    continue
                ex = enemy.x
                ey = enemy.y
                dx = ox - ex
                dy = oy - ey
                if dx * dx + dy * dy >= sr2:
                    continue
                if place in observed:
                    seen.add(id(enemy))
                    result.append(enemy)
                    if len(result) >= n_enemies:
                        break
        return result

    cpdef list observers_seeing_point(self, objects, long long tx, long long ty,
                                      long long A):
        """Observers that could see ``(tx, ty)`` (1.3.8.1 ``_is_seeing`` geometry).

        Matches ``_potential_neighbors`` + Euclidean sight + skip ``is_inside``:
        - bucket Chebyshev distance ≤ 1 (same 3×3 halo as neighbor merge)
        - ``dx² + dy² < sight²`` (strict less-than, same as ``_is_seeing``)
        - skip observers with FLAG_INSIDE / zero sight

        Returns Python units in **stable slot order** (sufficient for boolean
        visibility; neighbor-list consumers should keep ``_potential_neighbors``).
        """
        cdef list result = []
        cdef int i, n
        cdef long long gx, gy, ogx, ogy, dx, dy, sr, sr2
        cdef long long cell_dx, cell_dy
        cdef object u
        n = self._size
        if n == 0:
            return result
        gx = tx // A
        gy = ty // A
        for i in range(n):
            if self._flags[i] & FLAG_INSIDE:
                continue
            sr = self._sight[i]
            if sr == 0:
                continue
            ogx = self._x[i] // A
            ogy = self._y[i] // A
            cell_dx = ogx - gx
            cell_dy = ogy - gy
            if cell_dx < 0:
                cell_dx = -cell_dx
            if cell_dy < 0:
                cell_dy = -cell_dy
            if cell_dx > 1 or cell_dy > 1:
                continue
            dx = self._x[i] - tx
            dy = self._y[i] - ty
            sr2 = sr * sr
            if dx * dx + dy * dy >= sr2:
                continue
            u = objects[i]
            if u is not None:
                result.append(u)
        return result
