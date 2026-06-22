"""单位类型详情：建筑应显示 rules 中的 can_train / can_research。"""

import sys
import warnings
from types import SimpleNamespace

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.equipment_abilities import EquipmentAbilities
from soundrts.attributes.utils import class_attr_for_detail
from soundrts.definitions import rules


def _load_rules():
    with open("res/rules.txt", encoding="utf-8") as f:
        rules.load(f.read())


def _barracks_temp_unit():
    _load_rules()
    unit_class = rules.unit_class("barracks")

    class TempUnit:
        def __init__(self):
            self.model = unit_class
            self.type_name = "barracks"
            for attr in ("can_train", "can_research", "can_build"):
                value = class_attr_for_detail(unit_class, attr)
                if value:
                    setattr(self, attr, value)

    return TempUnit()


def test_captured_barracks_can_train_per_unit_counts():
    _load_rules()
    unit_class = rules.unit_class("captured_barracks")
    can_train = class_attr_for_detail(unit_class, "can_train")
    assert can_train == {"footman": 5, "archer": 3}


def test_parse_can_train_words_formats():
    from soundrts.definitions import parse_can_train_words

    assert parse_can_train_words(["can_train", "footman", "5", "archer", "3"]) == {
        "footman": 5,
        "archer": 3,
    }
    assert parse_can_train_words(["can_train", "footman", "archer", "knight", "3"]) == {
        "footman": 3,
        "archer": 3,
        "knight": 3,
    }
    assert parse_can_train_words(["can_train", "footman", "archer", "knight"]) == {
        "footman": 1,
        "archer": 1,
        "knight": 1,
    }
    assert parse_can_train_words(["can_train", "footman", "3"]) == {"footman": 3}


def test_class_attr_for_detail_reads_barracks_can_train():
    _load_rules()
    unit_class = rules.unit_class("barracks")
    can_train = class_attr_for_detail(unit_class, "can_train")
    assert can_train == {"footman": 1, "archer": 1, "knight": 1}
    assert not isinstance(can_train, property)


def test_barracks_detail_includes_can_train_items():
    u = _barracks_temp_unit()
    attrs = []
    EquipmentAbilities(SimpleNamespace()).add_training_attributes(u, attrs)
    train_row = next((row for row in attrs if row[1] == mp.CAN_TRAIN), None)
    assert train_row is not None
    assert train_row[2][0] == "CAN_TRAIN_ITEMS"
    assert len(train_row[2][1]) == 3


def test_barracks_detail_includes_can_research_items():
    u = _barracks_temp_unit()
    attrs = []
    ea = EquipmentAbilities(SimpleNamespace())
    ea.add_research_attributes(u, attrs)
    research_row = next((row for row in attrs if row[1] == mp.CAN_RESEARCH), None)
    assert research_row is not None
    assert research_row[2][0] == "CAN_RESEARCH_ITEMS"
    assert len(research_row[2][1]) == 2
