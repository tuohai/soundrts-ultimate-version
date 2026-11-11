# -*- coding: utf-8 -*-
"""破隐机制在属性界面里的显示。

属性界面（``attributes/display_interface.py`` → ``populate_unit_attributes``）
必须把隐形 / 破隐子系统的字段念出来：

* ``cloaking_range``（隐身范围）—— 只有 ``is_a_cloaker`` 的单位；
* ``detection_range``（侦测范围）—— 只有 ``is_a_detector`` 的单位；
* ``reveal_stealth_on_attack``（攻击暴露）—— 破隐开关；
* ``stealth_reveal_time``（暴露时间）—— 暴露持续秒数，0 = 永久暴露。

这些字段以前根本念不出来：``basic_attributes.py`` 引用了从未定义的
``mp.CLOAKING_RANGE`` / ``mp.DETECTION_RANGE``，异常又被 ``populate_unit_attributes``
的 ``try/except`` 吞掉，于是隐身范围 / 侦测范围两行永远不会出现。

本模块锁定：

* ``msgparts.py`` 里这五个常量存在且 id 唯一；
* 13 个界面语言的 ``tts.txt`` 都有这五个 id 的译文；
* 属性列表真的生成了这些行（值正确、单位正确）；
* 普通单位（既不隐形也不破隐）不会被念一堆破隐字段。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from soundrts import msgparts as mp
from soundrts.attributes.basic_attributes import BasicAttributes
from soundrts.lib.nofloat import PRECISION

ROOT = Path(__file__).resolve().parents[2]

LOCALES = (
    "ui",
    "ui-be",
    "ui-cs",
    "ui-de",
    "ui-es",
    "ui-fr",
    "ui-it",
    "ui-pl",
    "ui-pt-BR",
    "ui-ru",
    "ui-sk",
    "ui-vi",
    "ui-zh",
)

STEALTH_IDS = (
    mp.CLOAKING_RANGE[0],
    mp.DETECTION_RANGE[0],
    mp.REVEAL_STEALTH_ON_ATTACK[0],
    mp.STEALTH_REVEAL_TIME[0],
    mp.STEALTH_REVEAL_FOREVER[0],
)


# ---------------------------------------------------------------------------
# 1. msgparts 常量
# ---------------------------------------------------------------------------

def test_msgparts_defines_the_stealth_constants():
    """这五个常量以前根本没定义，属性界面因此静默失败。"""
    assert mp.CLOAKING_RANGE == [5869]
    assert mp.DETECTION_RANGE == [5870]
    assert mp.REVEAL_STEALTH_ON_ATTACK == [5871]
    assert mp.STEALTH_REVEAL_TIME == [5872]
    assert mp.STEALTH_REVEAL_FOREVER == [5873]


def test_stealth_tts_ids_are_unique():
    """id 冲突会让播报串到别的条目上。"""
    assert len(set(STEALTH_IDS)) == len(STEALTH_IDS)


# ---------------------------------------------------------------------------
# 2. 13 个语言包都有译文
# ---------------------------------------------------------------------------

def _read_tts(path: Path) -> dict[int, str]:
    table: dict[int, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        head = re.match(r"^(\d+)\s+(.*)$", line)
        if head:
            table[int(head.group(1))] = head.group(2).strip()
    return table


@pytest.mark.parametrize("locale", LOCALES)
def test_every_locale_translates_the_stealth_strings(locale):
    """没有译文的 id 在该语言下是哑的。"""
    path = ROOT / "res" / locale / "tts.txt"
    assert path.exists(), "%s missing" % locale
    table = _read_tts(path)
    for tid in STEALTH_IDS:
        assert tid in table, "%s: missing tts id %d" % (locale, tid)
        assert table[tid], "%s: empty tts id %d" % (locale, tid)


def test_the_english_strings_name_the_fields():
    table = _read_tts(ROOT / "res" / "ui" / "tts.txt")
    assert table[mp.CLOAKING_RANGE[0]] == "cloaking range"
    assert table[mp.DETECTION_RANGE[0]] == "detection range"
    assert table[mp.REVEAL_STEALTH_ON_ATTACK[0]] == "reveals on attack"
    assert table[mp.STEALTH_REVEAL_TIME[0]] == "reveal duration"
    assert table[mp.STEALTH_REVEAL_FOREVER[0]] == "stays revealed forever"


def test_the_chinese_strings_name_the_fields():
    table = _read_tts(ROOT / "res" / "ui-zh" / "tts.txt")
    assert table[mp.CLOAKING_RANGE[0]] == "隐身范围"
    assert table[mp.DETECTION_RANGE[0]] == "侦测范围"
    assert table[mp.REVEAL_STEALTH_ON_ATTACK[0]] == "攻击暴露"
    assert table[mp.STEALTH_REVEAL_TIME[0]] == "暴露时间"
    assert table[mp.STEALTH_REVEAL_FOREVER[0]] == "永久暴露"


# ---------------------------------------------------------------------------
# 3. 属性列表真的生成了这些行
# ---------------------------------------------------------------------------

class _FakeModel:
    """一个「单位类型」：属性界面读的是 ``u.model``。"""

    def __init__(self, **kw):
        self.is_invisible = 0
        self.is_cloaked = 0
        self.is_cloakable = 0
        self.is_a_cloaker = 0
        self.is_a_detector = 0
        self.cloaking_range = 6 * PRECISION
        self.detection_range = 85 * PRECISION // 10
        self.reveal_stealth_on_attack = 0
        self.stealth_reveal_time = 3 * PRECISION
        for k, v in kw.items():
            setattr(self, k, v)


class _FakeUnit:
    """属性界面的 ``u``：只有 ``model``（详情界面的 TempUnit 也是这样）。"""

    def __init__(self, model):
        self.model = model


def _attrs(model):
    ba = BasicAttributes(main_interface=None)
    attrs = []
    ba.add_sight_attributes(_FakeUnit(model), attrs)
    ba.add_stealth_attributes(_FakeUnit(model), attrs)
    return attrs


def _rows(attrs):
    """(名字, 值) 列表，方便断言。"""
    return [(row[1], row[2]) for row in attrs]


def _row(attrs, name):
    """按 msgparts 名字取那一行的值（名字是 id 列表）。"""
    for row_name, value in _rows(attrs):
        if row_name == name:
            return value
    raise AssertionError("attribute %r not generated" % (name,))


def test_cloaking_range_row_is_generated():
    """以前这里是 ``mp.CLOAKING_RANGE`` → AttributeError → 整段被吞掉。"""
    attrs = _attrs(_FakeModel(is_a_cloaker=1))
    names = [r[0] for r in _rows(attrs)]
    assert mp.CLOAKING_RANGE in names
    assert _row(attrs, mp.CLOAKING_RANGE) is not None


def test_cloaking_range_value_is_in_squares():
    from soundrts.lib.msgs import nb2msg_float

    attrs = _attrs(_FakeModel(is_a_cloaker=1, cloaking_range=6 * PRECISION))
    value = _row(attrs, mp.CLOAKING_RANGE)
    assert value == nb2msg_float(6)


def test_detection_range_row_is_generated():
    from soundrts.lib.msgs import nb2msg_float

    attrs = _attrs(_FakeModel(is_a_detector=1, detection_range=8500))
    value = _row(attrs, mp.DETECTION_RANGE)
    assert value == nb2msg_float(8.5)


def test_ranges_are_hidden_for_plain_units():
    """普通单位不该被念隐身 / 侦测范围。"""
    attrs = _attrs(_FakeModel())
    names = [r[0] for r in _rows(attrs)]
    assert mp.CLOAKING_RANGE not in names
    assert mp.DETECTION_RANGE not in names


def test_reveal_on_attack_is_announced_yes():
    attrs = _attrs(_FakeModel(is_invisible=1, reveal_stealth_on_attack=1))
    value = _row(attrs, mp.REVEAL_STEALTH_ON_ATTACK)
    assert value == mp.YES


def test_reveal_on_attack_is_announced_no_for_plain_invisible_units():
    """隐形但不会破隐的单位要明确说「否」。"""
    attrs = _attrs(_FakeModel(is_invisible=1, reveal_stealth_on_attack=0))
    value = _row(attrs, mp.REVEAL_STEALTH_ON_ATTACK)
    assert value == mp.NO


def test_reveal_duration_is_shown_in_seconds():
    attrs = _attrs(
        _FakeModel(is_invisible=1, reveal_stealth_on_attack=1,
                   stealth_reveal_time=5 * PRECISION)
    )
    value = _row(attrs, mp.STEALTH_REVEAL_TIME)
    # 值 = 秒数 + 「秒」
    assert list(mp.SECONDS)[0] in value


def test_zero_reveal_duration_means_forever():
    attrs = _attrs(
        _FakeModel(is_invisible=1, reveal_stealth_on_attack=1,
                   stealth_reveal_time=0)
    )
    value = _row(attrs, mp.STEALTH_REVEAL_TIME)
    assert value == mp.STEALTH_REVEAL_FOREVER


def test_plain_units_get_no_stealth_rows_at_all():
    """既不隐形也不破隐的单位不念破隐字段。"""
    attrs = _attrs(_FakeModel())
    names = [r[0] for r in _rows(attrs)]
    assert mp.REVEAL_STEALTH_ON_ATTACK not in names
    assert mp.STEALTH_REVEAL_TIME not in names


# ---------------------------------------------------------------------------
# 4. 属性界面管线注册了这一步
# ---------------------------------------------------------------------------

def test_the_display_interface_pipeline_runs_the_stealth_step():
    """管线里必须有这一步，否则主界面永远看不到破隐字段。"""
    source = (
        ROOT / "soundrts" / "attributes" / "display_interface.py"
    ).read_text(encoding="utf-8")
    assert "self.basic_attributes.add_stealth_attributes" in source


# ---------------------------------------------------------------------------
# 5. 端到端：真实规则单位 → 属性界面
# ---------------------------------------------------------------------------

def _populate(model):
    """走完整的属性界面管线（和主界面 / 详情界面同一条路）。"""
    from soundrts.attributes.basic_attributes import BasicAttributes
    from soundrts.attributes.build_rules_attributes import BuildRulesAttributes
    from soundrts.attributes.combat_attributes import CombatAttributes
    from soundrts.attributes.display_interface import DisplayInterface
    from soundrts.attributes.equipment_abilities import EquipmentAbilities

    di = DisplayInterface(
        None,
        BasicAttributes(None),
        BuildRulesAttributes(None),
        EquipmentAbilities(None),
        CombatAttributes(None),
    )
    attrs = []
    di.populate_unit_attributes(_FakeUnit(model), attrs)
    return attrs


def test_the_real_undead_knight_shows_the_reveal_fields():
    """基础版的亡灵骑士（攻击即破隐）必须在属性界面里念出来。"""
    from soundrts import config
    from soundrts.lib.resource import res

    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    try:
        from soundrts.definitions import rules

        cls = rules.unit_class("undead_knight")
        assert cls is not None
        attrs = _populate(cls)
        names = [row[1] for row in attrs]
        assert mp.REVEAL_STEALTH_ON_ATTACK in names
        assert mp.STEALTH_REVEAL_TIME in names
        assert _row(attrs, mp.REVEAL_STEALTH_ON_ATTACK) == mp.YES
        # 3 秒 → 秒数 + 「秒」
        assert list(mp.SECONDS)[0] in _row(attrs, mp.STEALTH_REVEAL_TIME)
    finally:
        config.mods = old
        res.set_mods(old or "")
        if old:
            res.load_rules_and_ai()


def test_a_plain_unit_shows_no_reveal_rows_end_to_end():
    """普通单位不能被念一堆破隐字段。"""
    from soundrts import config
    from soundrts.lib.resource import res

    old = getattr(config, "mods", "")
    config.mods = ""
    res.set_mods("")
    res.load_rules_and_ai()
    try:
        from soundrts.definitions import rules

        cls = rules.unit_class("peasant")
        if cls is None:
            pytest.skip("no peasant in the base rules")
        attrs = _populate(cls)
        names = [row[1] for row in attrs]
        assert mp.REVEAL_STEALTH_ON_ATTACK not in names
        assert mp.STEALTH_REVEAL_TIME not in names
    finally:
        config.mods = old
        res.set_mods(old or "")
        if old:
            res.load_rules_and_ai()
