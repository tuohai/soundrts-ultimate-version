# from soundrts import version
import os

DEBUG_MODE = False  # version.IS_DEV_VERSION


SHAPE = (
    (0, 0),
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    #            (1, 1), (-1, -1), (1, -1), (-1, 1),
)


# --- Cython 加速绑定 ---------------------------------------------------
# CollisionMatrix 必须保持纯 Python 类（在 World pickle 图内，不能改 cdef class），
# 但内部计算可委托给 cpdef 函数。
_cy = None
if os.environ.get("SOUNDRTS_NO_CYTHON", "").strip() not in ("1", "true", "True"):
    try:
        from . import collision_fast as _cy  # type: ignore[no-redef]
    except ImportError:
        _cy = None

CYTHON_ACCELERATED = _cy is not None

##        BIG_SHAPE = (
##                    (0, 0),
##                    (1, 0), (-1, 0), (0, 1), (0, -1),
####                        (1, 1), (-1, -1), (1, -1), (-1, 1),
##                    (2, 0), (-2, 0), (0, 2), (0, -2),
####                        (2, 2), (-2, -2), (2, -2), (-2, 2),
##                    (3, 0), (-3, 0), (0, 3), (0, -3),
####                        (3, 3), (-3, -3), (3, -3), (-3, 3),
####                        (4, 0), (-4, 0), (0, 4), (0, -4),
####                        (4, 4), (-4, -4), (4, -4), (-4, 4),
##                 )


class CollisionMatrix:
    """碰撞矩阵：保持纯 Python 类以兼容 cloudpickle（在 World 存档对象图内）。

    若 ``collision_fast`` 可用，热点方法委托到 cpdef 函数；否则走纯 Python
    fallback。Pickle 行为不变（实例只持有原生 Python 数据：set + int）。
    """

    def __init__(self, xmax, res):
        if DEBUG_MODE:
            assert isinstance(xmax, int)
            assert isinstance(res, int)
        self._set = set()
        self.xmax = xmax
        self.res = res
        self.amax = self.xmax // self.res

    ##    def _key(self, x, y): # tuple variant
    ##        return x // self.res, y // self.res

    def _key(self, x, y):
        if _cy is not None:
            return _cy.compute_key(x, y, self.res, self.amax)
        return x // self.res + self.amax * (y // self.res)

    ##    def _xy(self, k): # tuple variant
    ##        return (k[0] * self.res, k[1] * self.res)

    def _xy(self, k):
        if _cy is not None:
            return _cy.xy_from_key(k, self.res, self.amax)
        b = k // self.amax
        a = k % self.amax
        return a * self.res, b * self.res

    def xy_set(self):
        return [self._xy(k) for k in self._set]

    ##    def _shape(self, x, y): # tuple variant
    ##        ka, kb = self._key(x, y)
    ##        return set(((ka + a, kb + b) for (a, b) in SHAPE))

    def _shape(self, x, y):
        if DEBUG_MODE:
            assert isinstance(x, int)
            assert isinstance(y, int)
            assert x >= 0
            assert x <= self.xmax
        if _cy is not None:
            return _cy.compute_shape(x, y, self.res, self.amax)
        k = x // self.res + self.amax * (y // self.res)
        return {k + a + self.amax * b for (a, b) in SHAPE}

    def would_collide(self, x, y):
        if _cy is not None:
            return _cy.would_collide_fn(self._set, x, y, self.res, self.amax)
        return self._set.intersection(self._shape(x, y))

    def add(self, x, y):
        if DEBUG_MODE:
            assert not self.would_collide(x, y)
        if _cy is not None:
            _cy.add_fn(self._set, x, y, self.res, self.amax)
        else:
            self._set.update(self._shape(x, y))

    def remove(self, x, y):
        if DEBUG_MODE:
            assert self._shape(x, y).issubset(self._set)
        if _cy is not None:
            _cy.remove_fn(self._set, x, y, self.res, self.amax)
        else:
            self._set.difference_update(self._shape(x, y))


if __name__ == "__main__":
    m = CollisionMatrix(200, 2)
    #    assert m._key(0, 0) == 0
    print(m._key(50, 0))
    print(m._key(0, 50))
    for x, y in (
        (0, 0),
        (50, 0),
        (0, 50),
        (20, 56),
    ):
        k = m._key(x, y)
        print((x, y), k, m._xy(k))
        assert m._xy(k) == (x, y)
    for x, y in ((20, 57),):
        k = m._key(x, y)
        print((x, y), k, m._xy(k))
        assert m._xy(k) != (x, y)

    class O:
        collision = 1
        x = 6
        y = 6

    o = O()
    print(m._shape(o.x, o.y))
    assert len(m._shape(o.x, o.y)) in (5, 9)
    if m.would_collide(o.x, o.y):
        print("error")
    m.add(o.x, o.y)
    print(m.xy_set())
    #    m.add(o.x, o.y)
    if not m.would_collide(o.x, o.y):
        print("error")
    m.remove(o.x, o.y)
    if m.would_collide(o.x, o.y):
        print("error")
##    m.remove(o.x, o.y)
##    if m.would_collide(o.x, o.y):
##        print "error"
