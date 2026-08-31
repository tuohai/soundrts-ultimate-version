"""属性界面：沿线穿透、弹跳、草场刷羊。"""
import sys
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
sys.argv = ["pytest"]

from soundrts import msgparts as mp
from soundrts.attributes.combat_attributes import (
    append_bounce_attributes,
    append_pierce_line_attributes,
)
from soundrts.attributes.equipment_abilities import EquipmentAbilities
from soundrts.attributes.utils import get_stat_tts_name
from soundrts.lib.nofloat import PRECISION


def _labels(attrs):
    return [name for _key, name, _value in attrs]


def _value(attrs, label):
    for _key, name, value in attrs:
        if name == label:
            return value
    raise AssertionError("missing %r" % (label,))


def test_stat_tts_names_cover_pierce_bounce_spawn():
    assert get_stat_tts_name("rdg_bounce") == list(mp.RDG_BOUNCE)
    assert get_stat_tts_name("rdg_pierce_line") == list(mp.RDG_PIERCE_LINE)
    assert get_stat_tts_name("rdg_pierce_decay") == list(mp.RDG_PIERCE_DECAY)
    assert get_stat_tts_name("spawns_unit") == list(mp.SPAWNS_UNIT)
    assert get_stat_tts_name("claimable") == list(mp.CLAIMABLE)
    assert get_stat_tts_name("storable_resource_types") == list(mp.STORABLE_RESOURCE_TYPES)


def test_scorpion_pierce_shows_yes_width_and_50_percent():
    src = type(
        "Scorpion",
        (),
        {
            "rdg_pierce_line": 1,
            "rdg_pierce_width": PRECISION // 2,
            "rdg_pierce_max": 0,
            "rdg_pierce_decay": 50,
            "mdg_pierce_line": 0,
        },
    )()
    attrs = []
    append_pierce_line_attributes(src, attrs)
    labels = _labels(attrs)
    assert mp.RDG_PIERCE_LINE in labels
    assert mp.RDG_PIERCE_WIDTH in labels
    assert mp.RDG_PIERCE_MAX not in labels
    assert mp.RDG_PIERCE_DECAY in labels
    assert mp.MDG_PIERCE_LINE not in labels
    assert _value(attrs, mp.RDG_PIERCE_LINE) == mp.YES
    assert "%" in _value(attrs, mp.RDG_PIERCE_DECAY)


def test_lurker_pierce_decay_defaults_to_100_percent():
    src = type(
        "Lurker",
        (),
        {
            "rdg_pierce_line": 1,
            "rdg_pierce_width": 0,
            "rdg_pierce_max": 0,
            "rdg_pierce_decay": 0,
        },
    )()
    attrs = []
    append_pierce_line_attributes(src, attrs)
    decay = _value(attrs, mp.RDG_PIERCE_DECAY)
    assert "100" in "".join(str(p) for p in decay) or 100 in decay


def test_no_pierce_when_flag_off():
    attrs = []
    append_pierce_line_attributes(type("X", (), {"rdg_pierce_line": 0})(), attrs)
    assert attrs == []


def test_mutalisk_bounce_shows_hops_range_decay():
    src = type(
        "Mutalisk",
        (),
        {
            "rdg_bounce": 2,
            "rdg_bounce_range": 3 * PRECISION,
            "rdg_bounce_decay": 33,
            "mdg_bounce": 0,
        },
    )()
    attrs = []
    append_bounce_attributes(src, attrs)
    labels = _labels(attrs)
    assert mp.RDG_BOUNCE in labels
    assert mp.RDG_BOUNCE_RANGE in labels
    assert mp.RDG_BOUNCE_DECAY in labels
    assert mp.MDG_BOUNCE not in labels


def test_bounce_uses_attack_range_and_default_decay_when_zero():
    src = type(
        "Hopper",
        (),
        {
            "rdg_bounce": 1,
            "rdg_bounce_range": 0,
            "rdg_bounce_decay": 0,
            "rdg_range": 4 * PRECISION,
        },
    )()
    attrs = []
    append_bounce_attributes(src, attrs)
    assert mp.RDG_BOUNCE_RANGE in _labels(attrs)
    decay = _value(attrs, mp.RDG_BOUNCE_DECAY)
    assert "33" in "".join(str(p) for p in decay) or 33 in decay


def test_no_bounce_when_hops_zero():
    attrs = []
    append_bounce_attributes(type("X", (), {"rdg_bounce": 0})(), attrs)
    assert attrs == []


class _PastureModel:
    spawns_unit = "sheep"
    larva_spawn_time = 112 * PRECISION
    larva_cap = 8
    spawn_player_cap = 30
    spawn_immediate = 1
    storable_resource_types = (2,)
    resource_type = None
    extraction_time = 0
    extraction_qty = 0
    resource_volume_max = 0
    resource_volume_start = 0
    resource_regen = 0
    claimable = 0
    can_herd = 0


class _PastureUnit:
    is_a_building = True
    model = _PastureModel()
    resource_qty = 0


class _SheepModel:
    spawns_unit = None
    larva_cap = 0
    claimable = 1
    can_herd = 0


class _SheepUnit:
    is_a_building = False
    model = _SheepModel()
    claimable = 1


class _HerderModel:
    spawns_unit = None
    larva_cap = 0
    claimable = 0
    can_herd = 1


class _HerderUnit:
    is_a_building = False
    model = _HerderModel()
    can_herd = 1


def _stub_interface():
    return type(
        "StubInterface",
        (),
        {
            "_get_resource_type_name": staticmethod(lambda resource_type: resource_type),
        },
    )()


def test_pasture_shows_spawn_and_storable():
    ea = EquipmentAbilities(_stub_interface())
    spawn_attrs = []
    ea.add_spawn_claim_attributes(_PastureUnit(), spawn_attrs)
    labels = _labels(spawn_attrs)
    assert mp.SPAWNS_UNIT in labels
    assert mp.LARVA_SPAWN_TIME in labels
    assert mp.LARVA_CAP in labels
    assert mp.SPAWN_PLAYER_CAP in labels
    assert mp.SPAWN_IMMEDIATE in labels
    assert _value(spawn_attrs, mp.SPAWN_IMMEDIATE) == mp.YES

    store_attrs = []
    ea.add_building_resource_attributes(_PastureUnit(), store_attrs)
    assert mp.STORABLE_RESOURCE_TYPES in _labels(store_attrs)


def test_sheep_shows_claimable_not_spawn():
    attrs = []
    EquipmentAbilities(_stub_interface()).add_spawn_claim_attributes(_SheepUnit(), attrs)
    labels = _labels(attrs)
    assert mp.CLAIMABLE in labels
    assert mp.SPAWNS_UNIT not in labels
    assert mp.CAN_HERD not in labels


def test_herder_shows_can_herd():
    attrs = []
    EquipmentAbilities(_stub_interface()).add_spawn_claim_attributes(_HerderUnit(), attrs)
    assert mp.CAN_HERD in _labels(attrs)


def test_populate_unit_attributes_wires_new_steps():
    from pathlib import Path

    text = Path("soundrts/attributes/display_interface.py").read_text(encoding="utf-8")
    block = text.split("def populate_unit_attributes", 1)[1].split(
        "def refresh_attributes_for_terrain_if_needed", 1
    )[0]
    assert "add_pierce_line_attributes" in block
    assert "add_bounce_attributes" in block
    assert "add_spawn_claim_attributes" in block
