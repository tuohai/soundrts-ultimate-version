"""Warp-in / Nydus (StarCraft 2) regression tests."""

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.worldorders import ORDERS_DICT


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


def test_warp_in_keywords_are_known():
    from soundrts.definitions import rules as global_rules

    known = set(global_rules.key_value_properties) | set(global_rules.int_properties)
    known |= set(global_rules.string_list_properties)
    known |= set(global_rules.string_properties)
    known |= set(global_rules.precision_properties)
    for keyword in (
        "warp_in_types",
        "warp_in_charge",
        "warp_in_recharge",
        "warp_in_needs_field",
        "warp_in_field_radius_m",
        "warp_in_effect",
        "warp_in_skill",
    ):
        assert keyword in known, keyword


def test_warp_in_orders_are_registered():
    assert "warp_in" in ORDERS_DICT
    assert "nydus_in" in ORDERS_DICT
    assert ORDERS_DICT["warp_in"].nb_args == 2
    assert ORDERS_DICT["nydus_in"].nb_args == 2


def test_warp_in_orders_have_style_entries():
    from soundrts.definitions import style

    for keyword in ("warp_in", "nydus_in"):
        assert style.has(keyword, "index"), keyword
        assert style.has(keyword, "title"), keyword


def test_warp_in_types_are_read_from_rules():
    rules = Rules()
    rules.load(
        """
def zealot
class soldier
hp_max 80

def warp_gate
class building
warp_in_types zealot
warp_in_charge 2
warp_in_recharge 45
warp_in_needs_field psi
warp_in_field_radius_m 20
"""
    )
    gate = rules.unit_class("warp_gate")
    assert "zealot" in gate.warp_in_types
    assert gate.warp_in_charge in (2, [2])
    # ``warp_in_recharge`` is a timing field: scaled to milliseconds.
    assert gate.warp_in_recharge in (45 * 1000, [45 * 1000])
    assert gate.warp_in_needs_field in ("psi", ["psi"])
    assert gate.warp_in_field_radius_m in (20 * 1000, [20 * 1000])


def test_warp_in_helpers_read_the_rules():
    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_warp_in import (
        is_warp_in_building,
        warp_in_charge_max,
        warp_in_field_name,
        warp_in_recharge_time,
        warp_in_types,
    )

    rules = Rules()
    rules.load(
        """
def zealot
class soldier
hp_max 80

def warp_gate
class building
warp_in_types zealot dragoon
warp_in_charge 2
warp_in_recharge 45
warp_in_needs_field psi
"""
    )
    gate = rules.unit_class("warp_gate")
    assert is_warp_in_building(gate) is True
    assert warp_in_types(gate) == ["zealot", "dragoon"]
    assert warp_in_charge_max(gate) == 2
    # ``warp_in_recharge`` is a timing field: scaled to milliseconds.
    assert warp_in_recharge_time(gate) == 45 * PRECISION
    assert warp_in_field_name(gate) == "psi"


def test_building_with_warp_in_types_gets_the_order_skill():
    rules = Rules()
    rules.load(
        """
def zealot
class soldier
hp_max 80

def warp_gate
class building
warp_in_types zealot

def nydus
class building
warp_in_types zealot
warp_in_skill nydus_in
"""
    )
    gate = rules.unit_class("warp_gate")
    assert "warp_in" in gate.basic_skills
    nydus = rules.unit_class("nydus")
    assert "nydus_in" in nydus.basic_skills
    assert "warp_in" not in nydus.basic_skills


def test_building_without_warp_in_types_has_no_order_skill():
    rules = Rules()
    rules.load(
        """
def pylon
class building
hp_max 200
"""
    )
    pylon = rules.unit_class("pylon")
    assert "warp_in" not in pylon.basic_skills


def test_warp_in_charge_consumption_and_recharge():
    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_warp_in import (
        warp_in_charges_left,
        warp_in_consume_charge,
        warp_in_is_ready,
        warp_in_recharge_tick,
    )

    class FakeWorld:
        time = 1000

    class Gate:
        warp_in_types = "zealot"
        warp_in_charge = 2
        warp_in_recharge = 45 * PRECISION
        type_name = "warp_gate"
        world = FakeWorld()
        _warp_in_used = 0
        _warp_in_ready_time = 0

    gate = Gate()
    assert warp_in_charges_left(gate) == 2
    assert warp_in_is_ready(gate) is True
    warp_in_consume_charge(gate)
    assert warp_in_charges_left(gate) == 1
    warp_in_consume_charge(gate)
    assert warp_in_charges_left(gate) == 0
    # Out of charges: not ready.
    assert warp_in_is_ready(gate) is False
    # The recharge timer has not elapsed yet.
    warp_in_recharge_tick(gate)
    assert warp_in_charges_left(gate) == 0
    # After the recharge the building is ready again.
    FakeWorld.time = 1000 + 45 * PRECISION
    warp_in_recharge_tick(gate)
    assert warp_in_charges_left(gate) == 2
    assert warp_in_is_ready(gate) is True


def test_starcraft_mod_declares_a_warp_gate_and_a_nydus():
    text = _starcraft_rules_text()
    assert "def warp_gate" in text
    assert "def nydus" in text
    rules = Rules()
    rules.load(text)
    gate = rules.unit_class("warp_gate")
    assert gate is not None
    assert "warp_in" in gate.basic_skills
    nydus = rules.unit_class("nydus")
    assert nydus is not None
    assert "nydus_in" in nydus.basic_skills
