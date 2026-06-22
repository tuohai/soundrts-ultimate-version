"""农庄等可采集建筑的属性界面应显示资源储量与耕种参数。"""
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.equipment_abilities import EquipmentAbilities
from soundrts.lib.nofloat import PRECISION


class _FarmModel:
    resource_type = "resource3"
    extraction_time = 10
    extraction_qty = 1
    resource_volume_max = 50
    resource_volume_start = 25
    production_type = "resource3"
    production_cost = (0, 50 * PRECISION)
    production_qty = 50
    production_time = 0
    is_gather = 1
    auto_cultivate = 1
    manual_cultivate = 0


class _FarmUnit:
    is_a_building = True
    model = _FarmModel()
    resource_qty = 25


def _stub_interface():
    return type(
        "StubInterface",
        (),
        {
            "_get_resource_type_name": staticmethod(lambda resource_type: resource_type),
            "_calculate_modified_production_time": staticmethod(lambda unit: None),
            "_calculate_modified_production_qty": staticmethod(lambda unit: 50),
            "_add_dynamic_gather_attributes": staticmethod(lambda *args: None),
        },
    )()


def _attr_labels(attrs):
    return [name for _key, name, _value in attrs]


def test_farm_shows_building_resource_attributes():
    attrs = []
    EquipmentAbilities(_stub_interface()).add_building_resource_attributes(
        _FarmUnit(), attrs
    )
    labels = _attr_labels(attrs)
    assert mp.RESOURCE_TYPE in labels
    assert mp.EXTRACTION_TIME in labels
    assert mp.EXTRACTION_QTY in labels
    assert mp.RESOURCE_VOLUME_MAX in labels
    assert mp.RESOURCE_VOLUME_START in labels
    assert mp.CURRENT_QUANTITY in labels


def test_farm_shows_cultivate_production_without_production_time():
    attrs = []
    EquipmentAbilities(_stub_interface()).add_production_attributes(_FarmUnit(), attrs)
    labels = _attr_labels(attrs)
    assert mp.PRODUCTION_TYPE in labels
    assert mp.PRODUCTION_QUANTITY_NAME in labels
    assert mp.COST in labels
    assert mp.AUTO_CULTIVATE in labels
    assert mp.MANUAL_CULTIVATE in labels
    assert mp.PRODUCTION_TIME_NAME not in labels
