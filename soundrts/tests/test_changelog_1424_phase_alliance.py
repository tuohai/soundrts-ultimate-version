"""审计：1.4.2.4 — ``class phase`` 系统 + 结盟请求独立冷却。

更新日志承诺：

class phase（时代升级）相关：
1. ``phase_targets soldier``：可以是 ``building`` / ``unit`` / 具体单位名（如 ``footman knight``）
   - 空 targets = 所有单位都受益
   - ``-`` 前缀排除（如 ``phase_targets -building``）；可与正向项混用
2. ``phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5``：升级时代后的加成
3. ``units_auto_upgrade 0`` / ``1``：1 表示自动把单位升级到下一个时代的形态

完善了动态结盟：
- 每一个结盟请求的冷却时间变成独立的（按目标 id 维护），而不是公共冷却。
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Phase 类与默认值
# ---------------------------------------------------------------------------


def test_phase_class_exists_with_defaults():
    """``Phase`` 类必须存在，且 ``phase_targets`` / ``units_auto_upgrade`` 默认值与日志一致。"""
    from soundrts.worldphase import Phase, is_a_phase
    assert Phase.phase_bonus == ()
    assert Phase.phase_targets == ()
    assert Phase.units_auto_upgrade == 0
    assert Phase.can_upgrade_to == ()
    assert callable(is_a_phase)


def test_is_a_phase_distinguishes_phase_from_upgrade():
    """``is_a_phase`` 必须仅认 Phase 子类，不认普通 Upgrade。"""
    from soundrts.worldphase import Phase, is_a_phase
    from soundrts.worldupgrade import Upgrade

    class _MyPhase(Phase):
        type_name = "feudal_age"

    class _MyUpgrade(Upgrade):
        type_name = "blacksmith"

    assert is_a_phase(_MyPhase)
    assert not is_a_phase(_MyUpgrade)
    # 普通对象 / None 不能误判
    assert not is_a_phase(object)
    assert not is_a_phase(None)


# ---------------------------------------------------------------------------
# _unit_matches_targets：phase_targets 匹配规则
# ---------------------------------------------------------------------------


def test_unit_matches_targets_empty_means_all():
    """空 phase_targets 列表 = 命中所有单位。"""
    from soundrts.worldphase import Phase

    class _U:
        type_name = "footman"
        expanded_is_a = ()
        cls = None
    assert Phase._unit_matches_targets(_U(), []) is True
    assert Phase._unit_matches_targets(_U(), ()) is True


def test_unit_matches_targets_exact_type_name():
    from soundrts.worldphase import Phase

    class _U:
        type_name = "footman"
        expanded_is_a = ()
        cls = None
    assert Phase._unit_matches_targets(_U(), ["footman"]) is True
    assert Phase._unit_matches_targets(_U(), ["knight"]) is False


def test_unit_matches_targets_expanded_is_a():
    """phase_targets 写父类型名，单位的 expanded_is_a 包含父类型名 → 命中。"""
    from soundrts.worldphase import Phase

    class _U:
        type_name = "footman"
        expanded_is_a = ("footman", "infantry", "human_unit")
        cls = None
    assert Phase._unit_matches_targets(_U(), ["infantry"]) is True
    assert Phase._unit_matches_targets(_U(), ["human_unit"]) is True
    assert Phase._unit_matches_targets(_U(), ["air_unit"]) is False


def test_unit_matches_targets_class_category():
    """phase_targets 写 ``soldier`` / ``worker`` / ``building`` 等基类名 → 命中。

    单位.cls 是 SoundRTS 在 ``Rules.load`` 中赋值的基类（Soldier/Worker/Building/...）。
    ``__name__`` 取自类对象本身，所以直接用 ``type(name, ...)`` 动态造类来确保
    ``Soldier.__name__ == "Soldier"``（普通 ``class _Soldier`` 的 ``__name__`` 是 ``_Soldier``）。
    """
    from soundrts.worldphase import Phase

    Soldier = type("Soldier", (), {})  # __name__ = "Soldier"

    class _U:
        type_name = "footman"
        expanded_is_a = ()
        cls = Soldier
    assert Phase._unit_matches_targets(_U(), ["soldier"]) is True
    # 大小写不敏感
    assert Phase._unit_matches_targets(_U(), ["Soldier"]) is True
    assert Phase._unit_matches_targets(_U(), ["worker"]) is False


def test_unit_matches_targets_multi_target_any_match():
    """phase_targets 列出多个名字，任一命中即返回 True。"""
    from soundrts.worldphase import Phase

    class _U:
        type_name = "footman"
        expanded_is_a = ()
        cls = None
    assert Phase._unit_matches_targets(_U(), ["knight", "footman", "archer"]) is True


def test_unit_matches_targets_handles_unexpected_attrs():
    """如果 unit 缺关键字段，函数必须不抛异常，返回 False（保守）。"""
    from soundrts.worldphase import Phase

    class _U:
        pass  # 没有 type_name / expanded_is_a / cls
    out = Phase._unit_matches_targets(_U(), ["footman"])
    assert out in (False, None)  # 不抛异常即可


def test_unit_matches_targets_exclude_building():
    """``phase_targets -building`` = 除建筑外的所有单位。"""
    from soundrts.worldphase import Phase

    Building = type("Building", (), {})
    Soldier = type("Soldier", (), {})

    class _Townhall:
        type_name = "townhall"
        expanded_is_a = ()
        cls = Building

    class _Footman:
        type_name = "footman"
        expanded_is_a = ()
        cls = Soldier

    targets = ["-building"]
    assert Phase._unit_matches_targets(_Footman(), targets) is True
    assert Phase._unit_matches_targets(_Townhall(), targets) is False


def test_unit_matches_targets_exclude_multiple():
    """多个排除项：命中任一排除项即不匹配。"""
    from soundrts.worldphase import Phase

    Building = type("Building", (), {})
    Effect = type("Effect", (), {})
    Soldier = type("Soldier", (), {})

    class _Townhall:
        type_name = "townhall"
        expanded_is_a = ()
        cls = Building

    class _Explosion:
        type_name = "explosion"
        expanded_is_a = ()
        cls = Effect

    class _Footman:
        type_name = "footman"
        expanded_is_a = ()
        cls = Soldier

    targets = ["-building", "-effect"]
    assert Phase._unit_matches_targets(_Footman(), targets) is True
    assert Phase._unit_matches_targets(_Townhall(), targets) is False
    assert Phase._unit_matches_targets(_Explosion(), targets) is False


def test_unit_matches_targets_include_and_exclude():
    """正向项与排除项可混用：``soldier -footman``。"""
    from soundrts.worldphase import Phase

    Soldier = type("Soldier", (), {})

    class _Footman:
        type_name = "footman"
        expanded_is_a = ()
        cls = Soldier

    class _Knight:
        type_name = "knight"
        expanded_is_a = ()
        cls = Soldier

    class _Peasant:
        type_name = "peasant"
        expanded_is_a = ()
        cls = None

    targets = ["soldier", "-footman"]
    assert Phase._unit_matches_targets(_Knight(), targets) is True
    assert Phase._unit_matches_targets(_Footman(), targets) is False
    assert Phase._unit_matches_targets(_Peasant(), targets) is False


def test_rules_parses_phase_targets_exclude_syntax():
    """``phase_targets -building`` → ``['-building']``。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def feudal_age
class phase
cost 10 5
time_cost 60
phase_targets -building
""")
    out = r.get("feudal_age", "phase_targets")
    assert out == ["-building"]


# ---------------------------------------------------------------------------
# phase_bonus 解析（与日志的"phase bonus a v b v ..."一致）
# ---------------------------------------------------------------------------


def test_rules_parses_phase_bonus_flat_list():
    """``phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5`` 必须被解析为扁平的
    [stat, val, stat, val, ...] 列表，其中 cost 多值用空格 join。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def feudal_age
class phase
cost 10 5
time_cost 60
phase bonus mdg 1 hp_max 5 cost -2 0 time_cost -5
""")
    pb = r.get("feudal_age", "phase_bonus")
    # 必须能取到 mdg / hp_max / cost / time_cost 这些 key
    flat_keys = [pb[i] for i in range(0, len(pb), 2)]
    assert "mdg" in flat_keys
    assert "hp_max" in flat_keys
    assert "cost" in flat_keys
    assert "time_cost" in flat_keys


def test_rules_parses_phase_targets_as_list():
    """``phase_targets footman knight`` → ``['footman', 'knight']``。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def feudal_age
class phase
cost 10 5
time_cost 60
phase_targets footman knight
""")
    out = r.get("feudal_age", "phase_targets")
    assert out == ["footman", "knight"]


def test_rules_parses_units_auto_upgrade_as_int():
    """``units_auto_upgrade 1`` 是 int_properties，返回 int。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def feudal_age
class phase
cost 10 5
time_cost 60
units_auto_upgrade 1
""")
    out = r.get("feudal_age", "units_auto_upgrade")
    assert out == 1
    assert not isinstance(out, list)


# ---------------------------------------------------------------------------
# upgrade_player：成本类项目走玩家级，非成本走单位级
# ---------------------------------------------------------------------------


def test_upgrade_player_warns_only_for_positive_phase_targets_with_cost(
    monkeypatch,
):
    """仅排除型 phase_targets（如 ``-building``）配全局 cost 是合法写法，不应警告；
    正向 phase_targets 与 cost 混用时才警告，且每个 phase 名只警告一次。"""
    from soundrts import worldphase
    from soundrts.worldphase import Phase

    worldphase._PHASE_COST_TARGET_WARNED.clear()
    warnings = []

    def _capture(msg, *args):
        warnings.append(msg % args if args else msg)

    monkeypatch.setattr(worldphase, "warning", _capture)

    class _FeudalStyle(Phase):
        type_name = "test_feudal_style"
        phase_bonus = ("mdg", 1, "cost", "-2 0", "time_cost", -5)
        phase_targets = ("-building",)

    player = type("P", (), {"upgrades": [], "units": []})()
    _FeudalStyle.upgrade_player(player)
    assert warnings == []

    class _SoldierOnly(Phase):
        type_name = "test_soldier_only"
        phase_bonus = ("cost", "-2 0", "mdg", 1)
        phase_targets = ("soldier",)

    _SoldierOnly.upgrade_player(player)
    assert len(warnings) == 1
    assert "cost" in warnings[0]

    _SoldierOnly.upgrade_player(player)
    assert len(warnings) == 1


def test_filter_out_cost_args_drops_only_cost_keys():
    """``_filter_out_cost_args`` 必须只剥离 cost/production_cost/time_cost/
    population_cost/production_time/production_qty，其他属性保留。"""
    from soundrts.worldphase import Phase

    args = ["mdg", 1, "cost", "-2 0", "hp_max", 5, "time_cost", -5,
            "population_cost", -1, "production_qty", 10]
    out = Phase._filter_out_cost_args(args)
    assert out == ["mdg", 1, "hp_max", 5]


def test_filter_args_by_stats_allowed_and_denied():
    """``_filter_args_by_stats`` 必须支持 allowed_stats / denied_stats 过滤。"""
    from soundrts.worldphase import Phase

    args = ["mdg", 1, "rdg", 2, "hp_max", 5, "mdf", 3]
    out = Phase._filter_args_by_stats(args, allowed_stats={"mdg", "rdg"})
    assert out == ["mdg", 1, "rdg", 2]
    out2 = Phase._filter_args_by_stats(args, denied_stats={"mdg", "rdg"})
    assert out2 == ["hp_max", 5, "mdf", 3]


def test_weapon_and_armor_cleared_stats_listed():
    """WEAPON_CLEARED_STATS / ARMOR_CLEARED_STATS 必须包含装备会重置的字段，
    否则戴武器/护甲后 phase bonus 会被清回 base 而无声丢失。"""
    from soundrts.worldphase import WEAPON_CLEARED_STATS, ARMOR_CLEARED_STATS
    # 武器：mdg/rdg、对应 _range、_cd、crit、piercing、splash
    for s in ("mdg", "rdg", "mdg_range", "rdg_range", "mdg_cd", "rdg_cd",
              "mdg_crit", "rdg_crit", "mdg_piercing", "rdg_piercing",
              "mdg_splash", "rdg_splash"):
        assert s in WEAPON_CLEARED_STATS, f"missing {s} in WEAPON_CLEARED_STATS"
    # 护甲：mdf/rdf、_crit_rate、_piercing
    for s in ("mdf", "rdf", "mdf_crit_rate", "rdf_crit_rate",
              "mdf_piercing", "rdf_piercing"):
        assert s in ARMOR_CLEARED_STATS, f"missing {s} in ARMOR_CLEARED_STATS"


# ---------------------------------------------------------------------------
# units_auto_upgrade：与目标形态 requirements 中含本时代名挂钩
# ---------------------------------------------------------------------------


def test_auto_upgrade_units_requires_phase_in_target_requirements():
    """``_auto_upgrade_units`` 必须仅对"目标形态 requirements 包含本时代名"的
    单位执行变形，避免误升手动建造的形态链。"""
    src = _source("soundrts", "worldphase.py")
    s = src.index("def _auto_upgrade_units(cls, player):")
    block = src[s:s + 3500]
    assert "if phase_name in requirements:" in block
    assert "_instant_morph" in block


def test_instant_morph_preserves_hp_ratio():
    """瞬时变形必须按比例保留 hp（不送满血特权）。"""
    src = _source("soundrts", "worldphase.py")
    s = src.index("def _instant_morph(unit, target_cls):")
    block = src[s:s + 3000]
    assert "hp_ratio" in block
    assert "max(0.0, min(1.0," in block
    assert "int(new_unit.hp_max * hp_ratio)" in block


# ---------------------------------------------------------------------------
# phase 加成池 + 武器/护甲刷新链
# ---------------------------------------------------------------------------


def test_apply_pool_to_unit_excludes_weapon_armor_cleared():
    """``apply_pool_to_unit`` 必须把 WEAPON/ARMOR 会重置的字段过滤掉，
    交给 ``apply_pool_weapon_subset_to_unit`` / ``apply_pool_armor_subset_to_unit`` 处理。"""
    src = _source("soundrts", "worldphase.py")
    s = src.index("def apply_pool_to_unit(cls, unit):")
    block = src[s:s + 2000]
    assert "WEAPON_CLEARED_STATS | ARMOR_CLEARED_STATS" in block
    assert "denied_stats=denied" in block


def test_pool_entry_supports_legacy_and_tuple_format():
    """``_iter_pool_entries`` 必须同时兼容 老 list 格式 与 新 (bonus_args, targets) 元组。"""
    src = _source("soundrts", "worldphase.py")
    s = src.index("def _iter_pool_entries(cls, unit):")
    block = src[s:s + 2000]
    assert "isinstance(entry, tuple) and len(entry) == 2" in block
    assert "bonus_args, targets = entry" in block
    assert "bonus_args, targets = entry, ()" in block


# ---------------------------------------------------------------------------
# 1.4.2.4：每目标独立的结盟请求冷却
# ---------------------------------------------------------------------------


def test_alliance_request_cooldown_is_per_target_dict():
    """``cmd_diplomacy 'request'`` 必须用 ``_last_alliance_request_to[target.id]``
    作为冷却 key，而不是单个标量字段。"""
    src = _source("soundrts", "worldplayerbase", "base.py")
    s = src.index("if action == 'request':")
    block = src[s:s + 3000]
    assert "_last_alliance_request_to" in block
    assert "last_map.get(target.id," in block
    assert "last_map[target.id] = self.world.time" in block


def test_alliance_request_cooldown_is_60_seconds():
    """日志声明：每分钟仅能发送一次结盟申请 — 60s = 60000ms。"""
    src = _source("soundrts", "worldplayerbase", "base.py")
    s = src.index("if action == 'request':")
    block = src[s:s + 3000]
    assert "60000" in block  # 1 minute in ms


def test_alliance_request_skips_if_already_ally():
    """已经是盟友时，``request`` 必须短路：不打扰对方、不写冷却。"""
    src = _source("soundrts", "worldplayerbase", "base.py")
    s = src.index("if action == 'request':")
    block = src[s:s + 3000]
    assert "already_ally" in block
    # 短路返回前没有调用 last_map[target.id] = ...
    short_circuit_idx = block.index("if already_ally:")
    write_idx = block.find("last_map[target.id] = self.world.time")
    assert write_idx == -1 or write_idx > short_circuit_idx


# ---------------------------------------------------------------------------
# 行为级测试：直接模拟 cmd_diplomacy 中冷却部分的逻辑
# ---------------------------------------------------------------------------


def test_per_target_cooldown_independence_logic():
    """复刻 cmd_diplomacy 'request' 中的冷却算法，验证不同 target 互不影响。"""
    last_map = {}
    NOW0 = 0
    COOL = 60000  # 1 分钟

    def try_request(self_world_time, target_id):
        """返回 True 表示允许发送，False 表示被冷却拦下。"""
        last = last_map.get(target_id, -10**9)
        if self_world_time - last < COOL:
            return False
        last_map[target_id] = self_world_time
        return True

    # 在 t=0 给 target=10 发请求，允许
    assert try_request(0, 10) is True
    # t=1000ms 给 target=10 再发，被冷却
    assert try_request(1000, 10) is False
    # 同 t=1000ms 给 target=20 发，不受 target=10 影响 — 独立冷却的核心
    assert try_request(1000, 20) is True
    # t=61000ms 给 target=10 发，刚刚过 60s，允许
    assert try_request(61000, 10) is True
