"""可左右导航子项：内容内空格分隔，逗号仅用于 (n/m) 计数。"""

import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.utils import (
    gather_type_names,
    normalize_nav_item,
    NAVIGABLE_ITEM_TYPES,
)
from soundrts.attributes.vs_handler import VsHandler


class _Parent:
    pass


def test_normalize_nav_item_replaces_commas_with_spaces():
    item = [4783, mp.COMMA[0], "+", mp.COMMA[0], 1000001]
    normalized = normalize_nav_item(item)
    assert mp.COMMA[0] not in normalized
    assert normalized == [4783, " ", "+", " ", 1000001]


def test_vs_item_uses_spaces_not_commas():
    vs = VsHandler(_Parent())
    item = vs._build_vs_item(["light_cavalry"], [12])
    assert mp.COMMA[0] not in item
    assert mp.VERSUS[0] in item
    assert " " in item
    assert 12 in item


class _GatherModel:
    def __init__(self, deposits, buildings):
        self.can_gather_deposit = deposits
        self.can_gather_building = buildings


def test_gather_type_names_merges_all_into_one():
    unit = _GatherModel(["all"], ["all"])
    assert gather_type_names(unit) == ["all"]


def test_gather_type_names_merges_deposits_and_buildings():
    unit = _GatherModel(["goldmine", "wood"], ["farm"])
    assert gather_type_names(unit) == ["goldmine", "wood", "farm"]


def test_gather_type_names_deduplicates_shared_types():
    unit = _GatherModel(["goldmine"], ["goldmine", "farm"])
    assert gather_type_names(unit) == ["goldmine", "farm"]


def test_navigable_item_types_include_common_lists():
    for name in (
        "CAN_TRAIN_ITEMS",
        "CAN_BUILD_ITEMS",
        "CAN_RESEARCH_ITEMS",
        "CAN_GATHER_ITEMS",
        "CAN_USE_TECH_ITEMS",
        "VS_ITEMS",
        "EFFECT_ITEMS",
    ):
        assert name in NAVIGABLE_ITEM_TYPES
