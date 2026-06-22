"""验证 ``soundrts.worldplayerbase.perception_fast.player_is_an_enemy``
（Cython）与 Python 参考实现一致.

D-Phase 2 (cont.): 20.2M calls / 5min cw1 大乱斗, 把整函数 Cython 化的
parity 测试. 缓存语义 (5 秒过期, p.id 字典, p not in allied) byte-exact.
"""
from __future__ import annotations

import pytest


pf = pytest.importorskip(
    "soundrts.worldplayerbase.perception_fast",
    exc_type=ImportError,
    reason="Cython 扩展未编译；运行 `python setup_cython.py --inplace`",
)


# --- 测试 stub: 模拟 Player 行为, 不引入完整 game stack -------------------

class _StubWorld:
    def __init__(self, time=0):
        self.time = time


class _StubPlayer:
    def __init__(self, pid):
        self.id = pid


class _StubSelf:
    """模拟 CombatMixin 拥有的 fields. 仅 player_is_an_enemy 用到的部分."""

    def __init__(self, allied=(), time=0):
        self.world = _StubWorld(time=time)
        self.allied = list(allied)
        self._enemy_player_cache = {}
        self._enemy_player_timestamp = 0


def _py_player_is_an_enemy(self, p):
    """Python 参考实现 (copy from combat.py:_py_player_is_an_enemy)."""
    if p is None:
        return False
    current_time = self.world.time
    if current_time - self._enemy_player_timestamp > 5000:
        self._enemy_player_cache.clear()
        self._enemy_player_timestamp = current_time
    if p.id in self._enemy_player_cache:
        return self._enemy_player_cache[p.id]
    result = p not in self.allied
    self._enemy_player_cache[p.id] = result
    return result


def _both(allied, time, p, cache_after=None):
    """跑 Cython 和 Python 同一输入, 比较 result + cache 状态."""
    s_py = _StubSelf(allied=allied, time=time)
    s_cy = _StubSelf(allied=allied, time=time)
    r_py = _py_player_is_an_enemy(s_py, p)
    r_cy = pf.player_is_an_enemy(s_cy, p)
    assert r_py == r_cy, f"result mismatch: py={r_py!r} cy={r_cy!r}"
    assert s_py._enemy_player_cache == s_cy._enemy_player_cache, (
        f"cache mismatch: py={s_py._enemy_player_cache} cy={s_cy._enemy_player_cache}")
    assert s_py._enemy_player_timestamp == s_cy._enemy_player_timestamp, (
        f"timestamp mismatch: py={s_py._enemy_player_timestamp} "
        f"cy={s_cy._enemy_player_timestamp}")
    return r_cy


def test_none_returns_false():
    s = _StubSelf(allied=[], time=1234)
    assert pf.player_is_an_enemy(s, None) is False
    # 缓存与时间戳不变
    assert s._enemy_player_cache == {}
    assert s._enemy_player_timestamp == 0


def test_allied_returns_false():
    ally = _StubPlayer("p1")
    s = _StubSelf(allied=[ally], time=1000)
    assert pf.player_is_an_enemy(s, ally) is False
    assert s._enemy_player_cache == {"p1": False}


def test_non_allied_returns_true():
    enemy = _StubPlayer("p2")
    s = _StubSelf(allied=[], time=1000)
    assert pf.player_is_an_enemy(s, enemy) is True
    assert s._enemy_player_cache == {"p2": True}


def test_cache_hit():
    enemy = _StubPlayer("p3")
    s = _StubSelf(allied=[], time=1000)
    pf.player_is_an_enemy(s, enemy)  # 写缓存
    # 二次调用应命中缓存 (allied 不变, 即使 allied 变了也忽略)
    s.allied = [enemy]  # 模拟 allied 变更但缓存未过期
    assert pf.player_is_an_enemy(s, enemy) is True  # 用缓存值, 与 Python 一致


def test_cache_expiry_5s():
    enemy = _StubPlayer("p4")
    s = _StubSelf(allied=[], time=0)
    pf.player_is_an_enemy(s, enemy)  # 写缓存
    assert s._enemy_player_cache == {"p4": True}
    # 推进 5001 ms, 超出 5000 ms 窗口
    s.world.time = 5001
    s.allied = [enemy]  # 重要: 触发重新计算后, allied 变了
    assert pf.player_is_an_enemy(s, enemy) is False  # 重算: 现在是盟友
    assert s._enemy_player_cache == {"p4": False}
    assert s._enemy_player_timestamp == 5001


def test_cache_not_expired_just_at_5000ms():
    """边界: 恰好 5000 ms 不应清缓存 (> 5000, 严格大于)."""
    enemy = _StubPlayer("p5")
    s = _StubSelf(allied=[], time=0)
    pf.player_is_an_enemy(s, enemy)
    s.world.time = 5000  # exactly 5000
    s.allied = [enemy]  # 变更 allied
    assert pf.player_is_an_enemy(s, enemy) is True  # 仍走缓存
    assert s._enemy_player_cache == {"p5": True}


def test_parity_with_python_basic():
    # 一组覆盖性场景
    allied_a = _StubPlayer("a")
    allied_b = _StubPlayer("b")
    enemy_x = _StubPlayer("x")
    enemy_y = _StubPlayer("y")

    _both([allied_a], 0, allied_a)        # 盟友
    _both([allied_a, allied_b], 0, enemy_x)  # 敌方
    _both([], 0, None)                    # None
    _both([], 5001, enemy_y)              # 触发清缓存路径


def test_id_collision_safe():
    """两个不同 Player 对象 id 字段相同 → 缓存按 id 共享 (与 Python 一致)."""
    p1 = _StubPlayer("same")
    p2 = _StubPlayer("same")
    s = _StubSelf(allied=[p1], time=0)
    # p1 是盟友 (cached as False)
    assert pf.player_is_an_enemy(s, p1) is False
    # p2 是 unrelated object 但 id 相同, 走缓存 → 也返回 False
    assert pf.player_is_an_enemy(s, p2) is False


def test_repeated_calls_keep_cache():
    enemy = _StubPlayer("repeat")
    s = _StubSelf(allied=[], time=100)
    for _ in range(50):
        assert pf.player_is_an_enemy(s, enemy) is True
    # 50 次调用后, 缓存只有 1 个 key
    assert s._enemy_player_cache == {"repeat": True}
    # 时间戳没动 (没触发清缓存路径)
    assert s._enemy_player_timestamp == 0
