"""Rules-driven inventory item production (AoE2 relic gold pattern)."""

from soundrts.definitions import Rules
from soundrts.lib.nofloat import PRECISION
from soundrts.worlditem import Item, apply_inventory_production_rates
from soundrts.worldunit.worldcreature import Creature


_SNIPPET = """
def parameters
nb_of_resource_types 4

def monastery
class building
inventory_capacity 10
receive_items 1
accepted_items relic
accept_from self
accept_givers monk
apply_inventory_production 1

def monk
class soldier
inventory_capacity 1
receive_items 1

def relic
class item
transport_volume 1
inventory_production_rates 0.5 0 0 0
"""


def test_rules_parse_inventory_production_attrs():
    r = Rules()
    r.load(_SNIPPET)
    mon = r.unit_class("monastery")
    assert mon.apply_inventory_production == 1
    assert mon.inventory_capacity == 10
    assert list(mon.accepted_items) == ["relic"]
    assert list(mon.accept_givers) == ["monk"]
    relic = r.unit_class("relic")
    rates = list(relic.inventory_production_rates)
    assert rates == [int(0.5 * PRECISION), 0, 0, 0]


def test_engine_defaults_no_hardcoded_relic_names():
    assert Creature.apply_inventory_production == 0
    assert Item.inventory_production_rates == ()
    assert "apply_inventory_production" in Rules.int_properties
    assert "inventory_production_rates" in Rules.precision_list_properties


def test_apply_rates_only_when_host_flag_set():
    class _Player:
        def __init__(self):
            self.resources = [0, 0, 0, 0]

    class _Item:
        inventory_production_rates = (500, 0, 0, 0)

    class _Host:
        def __init__(self, apply, inventory):
            self.apply_inventory_production = apply
            self.inventory = inventory
            self.player = _Player()

    item = _Item()
    off = _Host(0, [item])
    apply_inventory_production_rates(off)
    assert off.player.resources[0] == 0

    on = _Host(1, [item, item])
    apply_inventory_production_rates(on)
    assert on.player.resources[0] == 1000  # 2 × 500


def test_aoe2_rules_monastery_relic_block():
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "mods" / "aoe2" / "rules.txt"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for needle in (
        "apply_inventory_production 1",
        "inventory_capacity 10",
        "accepted_items relic",
        "accept_givers monk",
        "inventory_production_rates 0.5 0 0 0",
    ):
        assert needle in text, needle
