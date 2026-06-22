"""生产物品的建筑不应显示默认 production_type（如黄金）。"""
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.equipment_abilities import EquipmentAbilities
from soundrts.lib.nofloat import PRECISION


class _GoldMintModel:
    production_type = "resource1"
    production_item = "gold_coin"
    production_time = 60
    production_qty = 1
    production_cost = (0, 0)
    is_gather = 0
    auto_production = 1
    manual_production = 1


class _GoldMintUnit:
    is_a_building = True
    model = _GoldMintModel()


def _stub_interface():
    return type(
        "StubInterface",
        (),
        {
            "_get_resource_type_name": staticmethod(lambda resource_type: resource_type),
            "_calculate_modified_production_time": staticmethod(lambda unit: 60),
            "_calculate_modified_production_qty": staticmethod(lambda unit: 1),
            "_add_dynamic_gather_attributes": staticmethod(lambda *args: None),
        },
    )()


def _attr_labels(attrs):
    return [name for _key, name, _value in attrs]


def test_item_production_building_shows_item_not_resource_type():
    attrs = []
    EquipmentAbilities(_stub_interface()).add_production_attributes(
        _GoldMintUnit(), attrs
    )
    labels = _attr_labels(attrs)
    assert mp.PRODUCTION_ITEM in labels
    assert mp.PRODUCTION_TYPE not in labels
    assert mp.PRODUCTION_TIME_NAME in labels
    assert mp.PRODUCTION_QUANTITY_NAME in labels
    assert mp.AUTO_PRODUCTION in labels
    assert mp.MANUAL_PRODUCTION in labels
