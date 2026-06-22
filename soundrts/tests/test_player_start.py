"""验证 ``player_start <N> <square>`` 指令把第 N 个玩家固定到指定格出生。

涉及的改动点：

1. ``soundrts/world/world_core.py``
   - ``World.__init__`` 新增 ``self.player_start_overrides = {}``。
2. ``soundrts/world/world_map.py``
   - ``_parse_map`` 新增 ``elif w == "player_start":`` 分支。
   - ``_apply_player_start_overrides``：解析末尾把 override 落到
     ``players_starts[N-1]``，必要时补齐 slot。
3. ``soundrts/world/world_objects.py``
   - ``populate_map``：override 非空时 pinned client 走 fixed slot，
     unpinned 在剩余池里按 random_starts 继续随机/顺序。

测试结构：
- 逻辑级：复刻 override 应用 + populate 分配，避免拉真 World 构造。
- 模块级：用 ``_try_import_world_map`` + ``WorldMapMixin.__new__`` 调 ``_parse_map``。
- 源码契约：world_core / world_map / world_objects 关键片段存在。
"""
from __future__ import annotations

import re
import sys
import warnings
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _source(rel_parts):
    return (REPO_ROOT.joinpath(*rel_parts)).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# world_map import 兜底（与 test_neutral_diplomacy 同套路）
# ---------------------------------------------------------------------------


def _try_import_world_map():
    saved_argv = sys.argv
    try:
        sys.argv = [saved_argv[0]] if saved_argv else ["pytest"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from soundrts.world import world_map  # noqa: WPS433
            return world_map
    except (SystemExit, Exception):
        return None
    finally:
        sys.argv = saved_argv


_WM = _try_import_world_map()


def _make_parse_stub():
    """造一个能跑 ``_parse_map`` 的最小化 mixin 实例。

    ``_parse_map`` 里有未知 token 警告路径会读 ``Player`` / ``rules`` /
    ``get_ai_names`` / ``ORDERS_DICT``。我们只测 player_start 相关，
    所以 token 都用 ``starting_squares`` / ``nb_players_*`` / ``player_start``
    这种 parser 直接识别的关键字，能避开那些反射。
    """
    if _WM is None:
        return None
    m = _WM.WorldMapMixin.__new__(_WM.WorldMapMixin)
    # _parse_map 用到的所有可写字段（与 world_core.__init__ 对齐）
    m.computers_starts = []
    m.players_starts = []
    m.starting_units = []
    m.starting_resources = []
    m.specific_starts = []
    m.player_start_overrides = {}
    m.starting_squares = []
    m.additional_meadows = []
    m.remove_meadows = []
    m.high_grounds = []
    m.nb_players_min = 1
    m.nb_players_max = 1
    m.nb_columns = 8
    m.nb_lines = 8
    m.nb_rows = 0
    m.square_width = 12
    m.nb_meadows_by_square = 0
    m.random_starts = 1
    m.west_east = []
    m.south_north = []
    m.terrain = {}
    m.terrain_speed = {}
    m.terrain_cover = {}
    m.sub_terrain = {}
    m.sub_high_grounds = {}
    m.sub_terrain_speed = {}
    m.sub_terrain_cover = {}
    m.sub_water = {}
    m.sub_ground = {}
    m.sub_no_air = {}
    m.subcell_precision = 3
    m.water_squares = set()
    m.no_air_squares = set()
    m.ground_squares = set()
    m.name_to_square = {}
    m.square_names = {}
    m.square_cities = {}
    m.square_provinces = {}
    m.square_districts = {}
    m.map_objects = []
    m.map_music = None
    m.map_battle_music = None
    m.map_victory_sound = None
    m.map_defeat_sound = None
    m.map_defined_starting_units = False
    m.map_defined_starting_resources = False
    m.map_defined_specific_starts = False
    m.map_defined_starting_population = False
    m.starting_population = 0
    m.nb_res = 2
    m.default_triggers = []

    class _R:
        def choice(self, xs):
            return xs[0]
    m.random = _R()
    return m


# ---------------------------------------------------------------------------
# 解析：player_start_overrides 写入正确
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_single_writes_override():
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 1
starting_squares a1
player_start 1 b1
""")
    assert m.player_start_overrides == {1: "1,0"}


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_multi_writes_all_overrides():
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 2
nb_players_max 3
starting_squares a1 c1 e1
player_start 1 a1
player_start 2 c1
player_start 3 e1
""")
    assert m.player_start_overrides == {1: "0,0", 2: "2,0", 3: "4,0"}


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_accepts_xy_form_and_alias():
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 1
square_name home 3,4
starting_squares a1
player_start 1 home
""")
    # "3,4" 是 1-based 坐标，归一为 0-based "2,3"
    assert m.player_start_overrides == {1: "2,3"}


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_bad_index_is_warning_not_crash():
    m = _make_parse_stub()
    # 'zero' 不是合法 int、0 < 1，两条都该被吃掉不抛
    m._parse_map("""
nb_players_min 1
nb_players_max 1
starting_squares a1
player_start zero a1
player_start 0 a1
""")
    assert m.player_start_overrides == {}


# ---------------------------------------------------------------------------
# 应用：override 让 players_starts[N-1] 的单位改写到指定格
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_override_rewrites_existing_slot_units():
    """starting_squares 已经建出 3 个 slot，override 把第 1 个的单位移到 b1。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 2
nb_players_max 3
starting_squares a1 c1 e1
starting_units townhall 5 peasant
player_start 1 b1
""")
    assert len(m.players_starts) == 3
    # slot 0 的单位应全部坐落在 "1,0"（b1 归一化结果）
    slot0_units = m.players_starts[0][1]
    assert slot0_units, "slot 0 unit list should not be empty"
    for sq, _cls, _mult in slot0_units:
        assert sq == "1,0"
    # slot 1/2 保持原样（c1=2,0；e1=4,0）
    for sq, _, _ in m.players_starts[1][1]:
        assert sq == "2,0"
    for sq, _, _ in m.players_starts[2][1]:
        assert sq == "4,0"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_override_pads_missing_slots():
    """nb_players_max=4 但只有 2 个 starting_squares + override 给 3/4：自动补齐。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 2
nb_players_max 4
starting_squares a1 c1
starting_units townhall
player_start 3 e1
player_start 4 g1
""")
    assert len(m.players_starts) == 4
    # 补出来的两个 slot 应在 e1/g1
    for sq, _, _ in m.players_starts[2][1]:
        assert sq == "4,0"
    for sq, _, _ in m.players_starts[3][1]:
        assert sq == "6,0"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_override_keeps_resources_and_triggers():
    """``player`` 行已经写好的资源 + 单位，override 只换格子，不动其它字段。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 1
player 100 1000 a1 5 peasant
player_start 1 d1
""")
    slot = m.players_starts[0]
    # 资源未变（注意 convert_and_split_first_numbers 会乘 PRECISION=1000，
    # 这里我们只关心"override 不动资源"，所以验证 player 行原值×1000 即可）
    assert slot[0] == [100 * 1000, 1000 * 1000]
    # 单位位置变到 d1 = "3,0"
    for sq, _, _ in slot[1]:
        assert sq == "3,0"


# ---------------------------------------------------------------------------
# 完整式：player_start N <resources...> <square> <units...>
# ---------------------------------------------------------------------------


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_full_form_builds_slot():
    """player_start 1 5 10 a1 townhall peasant 等价于把 `player` 行钉成玩家 1。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 2
starting_squares a1 c1
player_start 1 5 10 a1 townhall peasant
""")
    # override 以 dict 形式记录，仍带键 1（populate_map 据此 pin）
    assert isinstance(m.player_start_overrides[1], dict)
    slot0 = m.players_starts[0]
    # 资源被 to_int 乘以 PRECISION=1000
    assert slot0[0] == [5 * 1000, 10 * 1000]
    # 两个单位都坐落在 a1 = "0,0"
    assert len(slot0[1]) == 2
    for sq, _cls, _mult in slot0[1]:
        assert sq == "0,0"


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_full_form_respects_multiplicators():
    """单位列表里的数字是倍率：player_start 1 5 10 a1 townhall 5 peasant。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 1
player_start 1 5 10 a1 townhall 5 peasant
""")
    slot0 = m.players_starts[0]
    mults = {cls.__name__: mult for _sq, cls, mult in slot0[1]}
    assert mults.get("townhall") == 1
    assert mults.get("peasant") == 5


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_full_form_pads_missing_slots():
    """只有 1 个 starting_square，full-form 钉到玩家 3：自动补齐到 3 个 slot。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 1
nb_players_max 3
starting_squares a1
player_start 3 7 7 e1 townhall
""")
    assert len(m.players_starts) == 3
    # 第 3 个 slot 用 full-form 的资源/单位/格子
    slot2 = m.players_starts[2]
    assert slot2[0] == [7 * 1000, 7 * 1000]
    for sq, _cls, _mult in slot2[1]:
        assert sq == "4,0"  # e1


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_full_form_keeps_simple_form_backcompat():
    """简单式仍然写字符串值，完整式写 dict——两者可同图共存。"""
    m = _make_parse_stub()
    m._parse_map("""
nb_players_min 2
nb_players_max 2
starting_squares a1 c1
starting_units townhall
player_start 1 b1
player_start 2 9 9 d1 townhall peasant
""")
    assert m.player_start_overrides[1] == "1,0"
    assert isinstance(m.player_start_overrides[2], dict)
    # 简单式只换格子，保留全局 starting_units
    for sq, _cls, _mult in m.players_starts[0][1]:
        assert sq == "1,0"
    # 完整式用自带资源/单位
    assert m.players_starts[1][0] == [9 * 1000, 9 * 1000]
    for sq, _cls, _mult in m.players_starts[1][1]:
        assert sq == "3,0"  # d1


@pytest.mark.skipif(_WM is None, reason="world_map could not be imported")
def test_player_start_full_form_missing_square_warns():
    """完整式但没给方格（纯资源/单位）：警告并忽略，不写 override、不崩。"""
    m = _make_parse_stub()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m._parse_map("""
nb_players_min 1
nb_players_max 1
starting_squares a1
player_start 1 5 10 townhall peasant
""")
    assert 1 not in m.player_start_overrides


# ---------------------------------------------------------------------------
# populate_map 的混合分配逻辑（逻辑级复刻）
# ---------------------------------------------------------------------------


class _StubRandom:
    """让 sample 行为确定：永远按下标顺序取前 k 个。"""

    def sample(self, seq, k):
        return list(seq)[:k]


class _StubWorld:
    """只暴露 populate_map 用到的 attribute。"""

    def __init__(self, slots, overrides, random_starts=1):
        self.players_starts = slots
        self.player_start_overrides = overrides
        self.random_starts = random_starts
        self.random = _StubRandom()


def _populate_assignment(world, n_clients):
    """复刻 populate_map 里 players_starts 那段的赋值逻辑。"""
    overrides = world.player_start_overrides or {}
    slots = world.players_starts
    if n_clients > len(slots):
        return (slots * ((n_clients // len(slots)) + 1))[:n_clients]
    if overrides:
        pinned_client_idxs = {N - 1 for N in overrides if N - 1 < n_clients}
        pinned_slot_idxs = {N - 1 for N in overrides if N - 1 < len(slots)}
        remaining = [i for i in range(len(slots)) if i not in pinned_slot_idxs]
        unpinned_clients = [i for i in range(n_clients) if i not in pinned_client_idxs]
        k = min(len(remaining), len(unpinned_clients))
        chosen = world.random.sample(remaining, k) if world.random_starts else remaining[:k]
        out = [None] * n_clients
        for i in pinned_client_idxs:
            out[i] = slots[i]
        for ci, si in zip(unpinned_clients, chosen):
            out[ci] = slots[si]
        return out
    if world.random_starts and n_clients <= len(slots):
        return world.random.sample(slots, n_clients)
    return slots[:n_clients]


def test_populate_no_overrides_keeps_existing_behaviour():
    """没有 override 时，逻辑与历史一致：random.sample 或 [:n]。"""
    slots = ["A", "B", "C"]
    world = _StubWorld(slots, overrides={}, random_starts=1)
    out = _populate_assignment(world, 3)
    assert out == ["A", "B", "C"]  # stub sample 顺序取


def test_populate_all_pinned():
    """全员锁定：每个 client 拿自己 1-based 序号对应的 slot。"""
    slots = ["A", "B", "C"]
    world = _StubWorld(slots, overrides={1: "x", 2: "y", 3: "z"}, random_starts=1)
    out = _populate_assignment(world, 3)
    assert out == ["A", "B", "C"]


def test_populate_partial_pinned_locks_then_fills_rest():
    """只锁 player 1：client 0 拿 slot 0；其余 client 在剩余 slot 池里走原规则。"""
    slots = ["A", "B", "C"]
    world = _StubWorld(slots, overrides={1: "x"}, random_starts=1)
    out = _populate_assignment(world, 3)
    assert out[0] == "A"  # pinned
    # client 1/2 由 stub.sample 取 [B, C] 的前 2 个
    assert out[1] == "B"
    assert out[2] == "C"


def test_populate_pinned_slot_reserved_even_if_no_client():
    """锁了 player 3 但只有 2 个 client：slot 2 仍被保留，不会被 client 1 抢走。"""
    slots = ["A", "B", "C"]
    world = _StubWorld(slots, overrides={3: "x"}, random_starts=1)
    out = _populate_assignment(world, 2)
    # client 0/1 应该拿 A、B（slot 2 因为是 pinned 给"player 3" 不参与分配）
    assert "C" not in out
    assert set(out) == {"A", "B"}


def test_populate_pinned_overrides_random_starts():
    """random_starts=1 时也得把 pinned client 钉死。"""
    slots = ["A", "B", "C", "D"]
    world = _StubWorld(slots, overrides={2: "x"}, random_starts=1)
    out = _populate_assignment(world, 3)
    # client 1 必定是 slot 1
    assert out[1] == "B"


# ---------------------------------------------------------------------------
# 源码契约（一次性把"接线没掉"锁住）
# ---------------------------------------------------------------------------


def test_world_core_initializes_player_start_overrides():
    src = _source(["soundrts", "world", "world_core.py"])
    assert "self.player_start_overrides = {}" in src


def test_world_map_has_player_start_branch():
    src = _source(["soundrts", "world", "world_map.py"])
    assert 'elif w == "player_start":' in src
    assert "self.player_start_overrides" in src
    assert "_apply_player_start_overrides" in src


def test_world_map_apply_helper_exists():
    src = _source(["soundrts", "world", "world_map.py"])
    assert "def _apply_player_start_overrides(self" in src
    # 在 _parse_map 末尾、starting_squares 展开之后调用
    parse_end = src.index("# build self.players_starts")
    apply_call = src.index("self._apply_player_start_overrides(", parse_end)
    validation = src.index('"not enough starting places for nb_players_max"', apply_call)
    # 顺序保证：展开 -> apply -> 校验
    assert parse_end < apply_call < validation


def test_world_objects_populate_map_handles_overrides():
    src = _source(["soundrts", "world", "world_objects.py"])
    assert "player_start_overrides" in src
    # 关键变量都在
    assert "pinned_client_idxs" in src
    assert "pinned_slot_idxs" in src
    assert "remaining_slot_idxs" in src
