"""异虫幼虫：主巢自动产幼虫；幼虫变形消耗目标单位训练成本。"""

from pathlib import Path

from soundrts.definitions import Rules
from soundrts.lib.nofloat import to_int
from soundrts.worldorders.production import ChangeToOrder, UpgradeToOrder


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


class _Larva:
    morph_as_train = 1
    type_name = "larva"
    can_upgrade_to = ["zergling"]
    player = None
    place = None
    orders = []
    cost = (0, 0)
    time_cost = 0
    population_cost = 0


class _Hatchery:
    type_name = "hatchery"
    player = None
    place = None
    x = 0
    y = 0
    hp = 1


def test_starcraft_larva_rules_loaded():
    rules = Rules()
    rules.load(_starcraft_rules_text())
    larva = rules.unit_class("larva")
    hatchery = rules.unit_class("hatchery")
    zergling = rules.unit_class("zergling")
    assert getattr(larva, "morph_as_train", 0) == 1
    assert "zergling" in larva.can_upgrade_to
    assert getattr(hatchery, "larva_cap", 0) == 3
    assert getattr(hatchery, "larva_spawn_time", 0) == to_int("15")
    assert "spawning_pool" in zergling.requirements


def test_larva_morph_uses_target_train_cost():
    import soundrts.definitions as definitions

    definitions.rules.load(_starcraft_rules_text())
    zergling = definitions.rules.unit_class("zergling")
    larva = _Larva()
    order = UpgradeToOrder(larva, ["zergling"])
    assert order.cost == tuple(zergling.cost)
    assert order.time_cost == zergling.time_cost
    assert order.population_cost == zergling.population_cost


def test_larva_morph_as_train_on_change_to():
    import soundrts.definitions as definitions

    definitions.rules.load(_starcraft_rules_text())
    zergling = definitions.rules.unit_class("zergling")
    larva = _Larva()
    larva.can_change_to = ["zergling"]
    order = ChangeToOrder(larva, ["zergling"])
    assert order.cost == tuple(zergling.cost)
    assert order.time_cost == zergling.time_cost
    assert order.population_cost == zergling.population_cost
