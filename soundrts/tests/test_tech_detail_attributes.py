"""科技/时代详情：回车后应显示成本、效果、时代加成等完整参数。"""

import sys
import warnings
from types import SimpleNamespace

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.display_interface import DisplayInterface
from soundrts.attributes.effect_formatter import EffectFormatter
from soundrts.attributes.utils import AttributeUtils
from soundrts.definitions import rules


class _Parent:
    def __init__(self):
        self.utils = AttributeUtils(self)

    def _get_stat_tts_name(self, stat):
        return self.utils._get_stat_tts_name(stat)

    def _is_precision_stat(self, stat):
        return self.utils._is_precision_stat(stat)


def _load_rules():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())


def _build_tech_attrs(type_name):
    _load_rules()
    unit_class = rules.unit_class(type_name)
    u = SimpleNamespace(model=unit_class)
    attrs = []
    fmt = EffectFormatter(_Parent())
    display = DisplayInterface(None, None, None, None, None)
    display.populate_tech_attributes(u, attrs, fmt)
    return attrs


def _has_label(attrs, label):
    return any(row[1] == label for row in attrs)


def _effect_items(attrs):
    for _, name, value in attrs:
        if name == mp.EFFECT and isinstance(value, tuple) and value[0] == "EFFECT_ITEMS":
            return value[1]
    return None


def test_hunting_techniques_shows_bonus_effects():
    attrs = _build_tech_attrs("hunting_techniques")
    assert _has_label(attrs, mp.COST)
    assert _has_label(attrs, mp.TIME)
    items = _effect_items(attrs)
    assert items is not None
    assert len(items) >= 4
    assert not any(mp.GATHER_TIME[0] in row[1] for row in attrs)


def test_feudal_age_shows_phase_bonus_and_targets():
    attrs = _build_tech_attrs("feudal_age")
    assert _has_label(attrs, mp.COST)
    assert _has_label(attrs, mp.TIME)
    items = _effect_items(attrs)
    assert items is not None
    assert any(mp.MELEE_DAMAGE_NAME[0] in item for item in items)
    assert not _has_label(attrs, mp.MELEE_DAMAGE_NAME)
    assert _has_label(attrs, mp.PHASE_TARGETS)
    target_row = next(row for row in attrs if row[1] == mp.PHASE_TARGETS)
    assert mp.PHASE_EXCEPT_PREFIX[0] in target_row[2]
    assert mp.PHASE_EXCEPT_SUFFIX[0] in target_row[2]
    assert any(str(part) == "4812" for part in target_row[2])


def test_phase_targets_except_building_phrase():
    _load_rules()
    fmt = EffectFormatter(_Parent())
    text = fmt._format_phase_targets_text(["-building"])
    assert mp.PHASE_EXCEPT_PREFIX[0] in text
    assert mp.PHASE_EXCEPT_SUFFIX[0] in text
    assert "-" not in text


def test_effect_items_use_left_right_navigation_format():
    attrs = _build_tech_attrs("hunting_techniques")
    effect_row = next(row for row in attrs if row[1] == mp.EFFECT)
    assert isinstance(effect_row[2], tuple)
    assert effect_row[2][0] == "EFFECT_ITEMS"
    assert isinstance(effect_row[2][1][0], list)


def test_effect_items_join_name_value_without_inner_commas():
    _load_rules()
    from soundrts.attributes.effect_formatter import EffectFormatter

    fmt = EffectFormatter(_Parent())
    rows = fmt._format_bonus_effect_attribute_rows(["mdg", 1000])
    items = fmt.effect_attribute_rows_to_items(rows)
    item = items[0]
    assert mp.MELEE_DAMAGE_NAME[0] in item
    plus_index = item.index("+")
    assert item[plus_index + 1] != mp.COMMA[0]
    assert " " in item


def test_apply_bonus_effect_item_has_no_duplicate_effect_label():
    attrs = _build_tech_attrs("melee_weapon")
    items = _effect_items(attrs)
    assert items is not None
    assert len(items) == 1
    item = items[0]
    assert mp.EFFECT[0] not in item
    assert mp.APPLY[0] in item
    assert mp.MELEE_DAMAGE_NAME[0] in item
    assert mp.BONUS[0] in item


def test_apply_bonus_multiple_stats_split_into_items():
    attrs = _build_tech_attrs("melee_armor")
    items = _effect_items(attrs)
    assert items is not None
    assert len(items) == 2
    assert all(mp.EFFECT[0] not in item for item in items)


def test_castle_age_shows_requirements_and_next_age():
    attrs = _build_tech_attrs("castle_age")
    assert _has_label(attrs, mp.REQUIREMENTS)
    assert _has_label(attrs, mp.CAN_UPGRADE_TO)
    assert _has_label(attrs, mp.UNITS_AUTO_UPGRADE)


def test_building_shows_belongs_to_age_from_phase_requirement():
    attrs = _build_tech_attrs("barracks")
    assert _has_label(attrs, mp.BELONGS_TO_AGE)
    row = next(r for r in attrs if r[1] == mp.BELONGS_TO_AGE)
    # feudal_age title id from style
    assert row[2]


def test_townhall_has_no_belongs_to_age_without_phase_requirement():
    attrs = _build_tech_attrs("townhall")
    assert not _has_label(attrs, mp.BELONGS_TO_AGE)
