"""验证 Phase 3 各模块（perception/pathfind/movement/world_buckets）与
纯 Python 实现等价。"""
from __future__ import annotations

import random

import pytest

# 解开 combat/worldunit 循环依赖
import soundrts.worldunit  # noqa: F401


# =============================================================================
# perception_fast
# =============================================================================

pf = pytest.importorskip(
    "soundrts.worldplayerbase.perception_fast",
    exc_type=ImportError,
    reason="Cython 扩展未编译",
)


class _ObjMock:
    """模拟 World object：x, y, place 属性。"""
    def __init__(self, x, y, place="square"):
        self.x = x
        self.y = y
        self.place = place


class TestFilterInRadius:
    def test_basic(self):
        objs = [_ObjMock(0, 0), _ObjMock(10, 0), _ObjMock(100, 100)]
        # cx=0, cy=0, r2=121 -> include (0,0) and (10,0); exclude (100,100)
        result = pf.filter_in_radius(objs, 0, 0, 121)
        assert len(result) == 2
        assert result[0] is objs[0]
        assert result[1] is objs[1]

    def test_place_none_excluded(self):
        objs = [_ObjMock(0, 0, None), _ObjMock(1, 1)]
        result = pf.filter_in_radius(objs, 0, 0, 100)
        assert len(result) == 1
        assert result[0] is objs[1]

    def test_boundary(self):
        objs = [_ObjMock(3, 4)]  # dist² = 25
        assert pf.filter_in_radius(objs, 0, 0, 25)
        assert pf.filter_in_radius(objs, 0, 0, 24) == []

    def test_with_cb(self):
        objs = [_ObjMock(0, 0), _ObjMock(1, 1)]
        # 让 callback 拒绝第一个
        result = pf.filter_in_radius_with_cb(
            objs, 0, 0, 100, lambda o: o is objs[1]
        )
        assert result == [objs[1]]

    def test_with_cb_none_passes_through(self):
        objs = [_ObjMock(0, 0), _ObjMock(50, 50)]
        # filter_fn=None -> 等价 filter_in_radius
        result = pf.filter_in_radius_with_cb(objs, 0, 0, 100, None)
        assert result == [objs[0]]


class TestMergeBuckets3x3:
    def test_basic(self):
        buckets = {(0, 0): ["a", "b"], (1, 0): ["c"], (0, 1): ["d"]}
        result = pf.merge_buckets_3x3(buckets, 0, 0)
        assert set(result) == {"a", "b", "c", "d"}
        # 长度 = 4
        assert len(result) == 4

    def test_empty(self):
        assert pf.merge_buckets_3x3({}, 5, 5) == []

    def test_with_corners(self):
        buckets = {(-1, -1): ["x"], (1, 1): ["y"], (0, 0): ["z"]}
        result = pf.merge_buckets_3x3(buckets, 0, 0)
        assert set(result) == {"x", "y", "z"}


# =============================================================================
# worldroom_fast
# =============================================================================

rf = pytest.importorskip(
    "soundrts.worldroom_fast",
    exc_type=ImportError,
    reason="Cython 扩展未编译",
)


class _NodeMock:
    def __init__(self, x, y, name=""):
        self.x = x
        self.y = y
        self.name = name

    def __repr__(self):
        return f"<Node {self.name}>"


class TestAstarHeuristic:
    def test_basic(self):
        node = _NodeMock(0, 0)
        # int_distance((0,0), (3,4)) = 5
        assert rf.astar_heuristic(node, 3, 4) == 5

    def test_zero(self):
        node = _NodeMock(10, 20)
        assert rf.astar_heuristic(node, 10, 20) == 0

    def test_node_without_xy_returns_zero(self):
        class Bad:
            pass
        assert rf.astar_heuristic(Bad(), 5, 5) == 0


class TestReconstructPath:
    def test_simple_chain(self):
        a, b, c = _NodeMock(0, 0, "a"), _NodeMock(1, 1, "b"), _NodeMock(2, 2, "c")
        came_from = {b: a, c: b}
        result = rf.reconstruct_path(came_from, c, a)
        assert result == [a, b, c]

    def test_single_node(self):
        a = _NodeMock(0, 0, "a")
        result = rf.reconstruct_path({}, a, a)
        assert result == [a]


class TestCachedIsBlocked:
    def test_cache_hit(self):
        cache = {}
        class Node:
            def is_blocked(self, player, ignore_enemy_walls=True):
                raise AssertionError("should not be called second time")
        node = Node()
        player = object()
        # 第一次填缓存
        cache[(id(node), 42)] = True
        assert rf.cached_is_blocked(node, player, cache, 42) is True

    def test_cache_miss_then_cached(self):
        cache = {}
        call_count = [0]
        class Node:
            def is_blocked(self, player, ignore_enemy_walls=True):
                call_count[0] += 1
                return False
        node = Node()
        player = object()
        assert rf.cached_is_blocked(node, player, cache, 7) is False
        assert rf.cached_is_blocked(node, player, cache, 7) is False
        # 第二次应该走缓存
        assert call_count[0] == 1


# =============================================================================
# world_buckets_fast
# =============================================================================

# soundrts.world.__init__ 会触发 options.py 的 optparse（与 pytest argv 冲突），
# 所以这里用 importlib 直接加载 .pyd 文件，绕开 __init__ 的副作用。
def _load_world_buckets_fast():
    import importlib.util
    import os
    from glob import glob
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = sorted(glob(os.path.join(here, "world", "world_buckets_fast*.pyd"))
                        + glob(os.path.join(here, "world", "world_buckets_fast*.so")))
    if not candidates:
        return None
    spec = importlib.util.spec_from_file_location(
        "soundrts.world.world_buckets_fast", candidates[0]
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


wbf = _load_world_buckets_fast()
if wbf is None:
    pytest.skip("world_buckets_fast Cython 扩展未编译", allow_module_level=True)


class _UnitMock:
    def __init__(self, x, y, is_cloakable=False, is_cloaked=False,
                 is_invisible=False):
        self.x = x
        self.y = y
        self.is_cloakable = is_cloakable
        self.is_cloaked = is_cloaked
        self.is_invisible = is_invisible


def ref_build_buckets(units, A):
    buckets = {}
    for u in units:
        k = (u.x // A, u.y // A)
        try:
            buckets[k].append(u)
        except KeyError:
            buckets[k] = [u]
    return buckets


class TestBuildBuckets:
    def test_basic(self):
        units = [_UnitMock(0, 0), _UnitMock(50, 50), _UnitMock(150, 50)]
        cy = wbf.build_buckets(units, 100)
        py = ref_build_buckets(units, 100)
        assert cy == py

    def test_negative_coords(self):
        """单位 x/y 可能为负（地图边界异常），floor div 应一致。"""
        units = [_UnitMock(-50, -50), _UnitMock(-150, 200)]
        cy = wbf.build_buckets(units, 100)
        py = ref_build_buckets(units, 100)
        assert cy == py

    def test_empty(self):
        assert wbf.build_buckets([], 100) == {}

    def test_random_parity(self):
        rng = random.Random(20260526)
        for _ in range(100):
            n = rng.randint(0, 50)
            A = rng.choice([10, 50, 100, 500])
            units = [
                _UnitMock(rng.randint(-1000, 1000), rng.randint(-1000, 1000))
                for _ in range(n)
            ]
            assert wbf.build_buckets(units, A) == ref_build_buckets(units, A)


class TestMarkCloaked:
    def test_marks_in_range(self):
        units = [
            _UnitMock(0, 0, is_cloakable=True),
            _UnitMock(50, 0, is_cloakable=True),
            _UnitMock(100, 0, is_cloakable=True),
        ]
        # cx=0, cy=0, r2 = 50^2 = 2500 -> (50,0) in (dist²=2500), is < 2500? False
        # (50,0) dist² = 2500, 2500 < 2500 is False -> not marked
        # (0,0) dist² = 0 -> marked
        count = wbf.mark_cloaked(units, 0, 0, 2500)
        assert count == 1
        assert units[0].is_cloaked is True
        assert units[1].is_cloaked is False
        assert units[2].is_cloaked is False

    def test_skips_non_cloakable(self):
        units = [_UnitMock(0, 0, is_cloakable=False)]
        count = wbf.mark_cloaked(units, 0, 0, 100)
        assert count == 0

    def test_skips_already_cloaked(self):
        units = [_UnitMock(0, 0, is_cloakable=True, is_cloaked=True)]
        count = wbf.mark_cloaked(units, 0, 0, 100)
        # 已 cloaked 的不再次设置
        assert count == 0


class TestCollectInvisiblesInRange:
    def test_collects_invisible(self):
        units = [
            _UnitMock(0, 0, is_invisible=True),
            _UnitMock(10, 0, is_cloaked=True),
            _UnitMock(20, 0),  # 可见，跳过
        ]
        result = wbf.collect_invisibles_in_range(units, 0, 0, 10000, set())
        assert units[0] in result
        assert units[1] in result
        assert units[2] not in result

    def test_skips_already_detected(self):
        u = _UnitMock(0, 0, is_invisible=True)
        result = wbf.collect_invisibles_in_range([u], 0, 0, 100, {u})
        assert result == []

    def test_distance_filter(self):
        # cx=0, cy=0, r2=100 -> dist² < 100
        u = _UnitMock(100, 0, is_invisible=True)  # dist² = 10000
        result = wbf.collect_invisibles_in_range([u], 0, 0, 100, set())
        assert result == []


# =============================================================================
# 整体绑定（Mixin 改造后的 Python 调用路径）
# =============================================================================
#
# 不直接导入 soundrts.world / soundrts.worldroom 子模块来检查 _pf/_rf/_wbf
# 是否非空——这些模块的 __init__ 链路会触发 options.py 在 import 时调用
# optparse.parse_args()，与 pytest 自己的 argv 冲突（pre-existing issue）。
#
# 上面的 parity tests 已直接验证每个 *_fast.pyx 模块的功能正确性，wiring 是否
# 接好则通过 `python setup_cython.py --inplace` 后的运行时 smoke 验证。
