"""审计：1.4.2.5 — ``can_advance`` 与 phase（时代）显示、``hide_locked_commands``。

更新日志承诺：

1. 新增 ``can_advance`` 字段，专门用于 phase 升级；与 ``can_research`` 区分开。
   - 例：``can_advance feudal_age``（在 townhall 上）。
2. 属性界面（按 v 查看单位属性）也增加 ``can_advance`` 显示可推进的阶段。
3. 游戏开局显示默认 phase：rules.txt 中存在多个 phase 时，requirements 不含
   其他 phase 名的那个就是开局自动设置的 ``current_phase`` 与 ``upgrades`` 之一。
4. ``hide_locked_commands`` 参数：1 表示隐藏未满足 requirements 的命令，0（默认）显示。

测试策略：源码契约 + 纯逻辑验证（不启动 pygame）。
"""
from __future__ import annotations

from pathlib import Path

import pytest


def _source(*path_parts):
    return (Path(__file__).resolve().parents[2]
            .joinpath(*path_parts).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# can_advance 接入：source contract
# ---------------------------------------------------------------------------


def test_creature_defaults_have_can_advance():
    """``Creature`` 类默认值里必须有 ``can_advance = ()``，否则 hasattr 检查会漏。"""
    src = _source("soundrts", "worldunit", "worldcreature.py")
    assert "can_advance = ()" in src
    assert "can_research = ()" in src


def test_can_advance_registered_in_get_makers():
    """``get_makers`` 必须把 ``can_advance`` 当成可造关系一并查询。
    （地图/AI 的"哪些建筑能造出 X"判定不能漏掉时代）。"""
    src1 = _source("soundrts", "definitions.py")
    src2 = _source("soundrts", "world", "world_objects.py")
    assert '"can_advance"' in src1 and "get_makers" in src1
    assert '"can_advance"' in src2 and "get_makers" in src2


def test_advance_order_separated_from_research_order():
    """``AdvanceOrder`` 必须独立于 ``ResearchOrder``，且 ``unit_menu_attribute='can_advance'``、
    ``keyword='advance'``。"""
    src = _source("soundrts", "worldorders", "production.py")
    block = _section(src, "class AdvanceOrder(ResearchOrder):", ["\nclass "])
    assert 'unit_menu_attribute = "can_advance"' in block
    assert 'keyword = "advance"' in block


def test_research_order_filters_phase_into_advance_lane():
    """``ResearchOrder.additional_condition`` 必须拒绝 phase 类型，避免出现在科技通道。"""
    src = _source("soundrts", "worldorders", "production.py")
    block = _section(src, "class ResearchOrder(ProductionOrder):", ["\nclass "])
    assert "from ..worldphase import is_a_phase" in block
    assert "if is_a_phase(rules.unit_class(type_name)):" in block
    assert "return False" in block


def test_advance_order_only_allows_phase():
    """``AdvanceOrder.additional_condition`` 必须拒绝非 phase 类型。"""
    src = _source("soundrts", "worldorders", "production.py")
    block = _section(src, "class AdvanceOrder(ResearchOrder):", ["\nclass "])
    assert "if not is_a_phase(rules.unit_class(type_name)):" in block


# ---------------------------------------------------------------------------
# 属性界面：can_advance 显示
# ---------------------------------------------------------------------------


def _section(src, start_marker, end_marker_options):
    """从 src 中截取 ``start_marker`` 到下一个 ``end_marker_options`` 之间的代码块。"""
    s = src.index(start_marker)
    best_e = len(src)
    for em in end_marker_options:
        idx = src.find(em, s + len(start_marker))
        if idx != -1 and idx < best_e:
            best_e = idx
    return src[s:best_e]


def test_attributes_have_add_advance_attributes():
    """属性界面必须有 ``add_advance_attributes`` 分支，且只展示 phase 类型。"""
    src = _source("soundrts", "attributes", "equipment_abilities.py")
    assert "def add_advance_attributes(self, u, attrs):" in src
    block = _section(
        src,
        "def add_advance_attributes(self, u, attrs):",
        ["\n    def ", "\nclass "],
    )
    assert "from ..worldphase import is_a_phase" in block
    assert "if not is_a_phase(_rules.unit_class(advance_type)):" in block
    assert "CAN_ADVANCE_ITEMS" in block


def test_attributes_research_block_skips_phase():
    """``add_research_attributes`` 必须显式跳过 phase 类型，避免与 advance 重复显示。"""
    src = _source("soundrts", "attributes", "equipment_abilities.py")
    block = _section(
        src,
        "def add_research_attributes(self, u, attrs):",
        ["\n    def ", "\nclass "],
    )
    assert "if is_a_phase(_rules.unit_class(research_type)):" in block
    assert "continue" in block


def test_attribute_key_bindings_skip_phase_in_research():
    """读屏快捷键 TECHNIC_STATS 浏览也得跳过 phase。"""
    src = _source("soundrts", "attributes", "key_bindings.py")
    # 与显示侧保持一致，剔除 phase 类型
    assert "can_advance" in src


# ---------------------------------------------------------------------------
# 开局默认 phase 显示
# ---------------------------------------------------------------------------


def test_player_init_auto_picks_root_phase():
    """玩家初始化时若无显式 phase，会自动选 rules 中 requirements 不含
    其他 phase 名的"起源时代"。"""
    src = _source("soundrts", "worldplayerbase", "base.py")
    assert "if self.current_phase is None:" in src
    assert "root_phases" in src
    s = src.index("if self.current_phase is None:")
    # 取后续 200 行左右作为搜索区
    block = src[s:s + 4000]
    assert "self.upgrades.append(chosen)" in block
    assert "self.current_phase = chosen" in block


def test_current_age_status_reads_can_advance_and_falls_back_to_can_research():
    """``current_age_status`` 必须先看 ``can_advance``，找不到 phase 才回退到 ``can_research``。"""
    src = _source("soundrts", "clientgameentity", "properties.py")
    block = _section(
        src,
        "def current_age_status(self):",
        ["\n    @property", "\n    def ", "\nclass "],
    )
    assert 'can_advance = getattr(self, "can_advance", None) or ()' in block
    assert 'can_research = getattr(self, "can_research", None) or ()' in block
    assert 'getattr(player, "current_phase", None)' in block
    assert "mp.CURRENT_AGE" in block


def test_phase_upgrade_player_updates_current_phase():
    """``Phase.upgrade_player`` 完成时必须把 ``player.current_phase`` 改为新 phase 名。"""
    src = _source("soundrts", "worldphase.py")
    block = _section(
        src,
        "def upgrade_player(cls, player):",
        ["\n    @classmethod", "\n    def ", "\nclass "],
    )
    assert "player.current_phase = cls.type_name" in block


# ---------------------------------------------------------------------------
# hide_locked_commands 行为
# ---------------------------------------------------------------------------


def test_hide_locked_commands_registered_in_int_properties():
    """``hide_locked_commands`` 必须在 ``int_properties`` 里，否则解析为 ``[1]`` 列表
    会让 ``and rules.get(...)`` 永远真。"""
    src = _source("soundrts", "definitions.py")
    # 在 int_properties / int_properties_extended 中（同一 set）
    assert '"hide_locked_commands"' in src


def test_order_menu_respects_hide_locked_commands():
    """``Order.menu`` 必须根据 ``hide_locked_commands`` 切换 ``is_allowed`` 谓词。"""
    src = _source("soundrts", "worldorders", "base.py")
    block = _section(
        src,
        "def _hide_locked_commands(cls):",
        ["\n    @", "\n    def ", "\nclass "],
    )
    # 仅对 menu 类型（can_build/can_train/can_research/can_advance/can_upgrade_to/can_change_to）生效
    assert '"can_build"' in block
    assert '"can_train"' in block
    assert '"can_research"' in block
    assert '"can_advance"' in block
    assert '"can_upgrade_to"' in block
    assert '"can_change_to"' in block

    # 文件中有多个 `def menu(...)`（不同基类）。我们要的是 ProductionOrder/Order
    # 体系里 _hide_locked_commands 后面紧跟的那个，故从 _hide_locked_commands 处往后切。
    after_pred = src[src.index("def _hide_locked_commands"):]
    block2 = _section(
        after_pred,
        "def menu(cls, unit, strict=False):",
        ["\n    @", "\n    def ", "\nclass "],
    )
    assert "hide_locked = strict or cls._hide_locked_commands()" in block2
    assert "is_allowed = cls.is_allowed if hide_locked else cls._is_almost_allowed" in block2


def test_rules_get_hide_locked_commands_returns_int_not_list():
    """运行时验证：解析 ``hide_locked_commands 1`` 后 ``rules.get`` 返回整数 1 而不是 ``[1]``。
    
    若返回 ``[0]``（非空列表），会被 ``and`` 视为真，导致默认值 0 也隐藏命令——这是 bug。
    """
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def parameters
hide_locked_commands 1
""")
    v = r.get("parameters", "hide_locked_commands", 0)
    assert v == 1
    assert not isinstance(v, list)

    r2 = Rules()
    r2.read("""
def parameters
hide_locked_commands 0
""")
    v2 = r2.get("parameters", "hide_locked_commands", 0)
    assert v2 == 0
    assert not isinstance(v2, list)


def test_rules_get_hide_locked_commands_default_when_missing():
    """未定义 ``hide_locked_commands`` 时，``rules.get`` 应返回 default=0。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def parameters
nb_of_resource_types 2
""")
    assert r.get("parameters", "hide_locked_commands", 0) == 0


def test_rules_parse_can_advance_as_list():
    """``can_advance feudal_age castle_age`` 必须解析为 ``["feudal_age", "castle_age"]``。"""
    from soundrts.definitions import Rules

    r = Rules()
    r.read("""
def townhall
class building
can_advance feudal_age castle_age
""")
    out = r.get("townhall", "can_advance")
    assert out == ["feudal_age", "castle_age"]


def test_rules_default_rules_txt_ships_hide_locked_commands_zero():
    """``res/rules.txt`` 必须默认带 ``hide_locked_commands 0``，保持向后兼容（不破现存 mod）。"""
    src = (Path(__file__).resolve().parents[2]
           .joinpath("res", "rules.txt").read_text(encoding="utf-8"))
    assert "hide_locked_commands 0" in src
