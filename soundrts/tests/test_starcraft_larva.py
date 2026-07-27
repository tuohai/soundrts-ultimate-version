"""Generic unit spawn hosts (StarCraft hatchery/larva) and morph-as-train."""

from pathlib import Path
import types

from soundrts.definitions import Rules
from soundrts.lib.nofloat import to_int
from soundrts.world_build_rules import (
    count_spawned_on_square,
    fill_spawn_host,
    is_unit_spawn_host,
    spawn_host_cap,
    spawns_unit_type,
    spawn_unit_at_host,
)
from soundrts.worldorders.production import (
    ChangeToOrder,
    UpgradeToOrder,
    _spawn_host_inject_time_multiplier,
)


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


def test_starcraft_larva_rules_loaded():
    rules = Rules()
    rules.load(_starcraft_rules_text())
    larva = rules.unit_class("larva")
    hatchery = rules.unit_class("hatchery")
    zergling = rules.unit_class("zergling")
    assert getattr(larva, "morph_as_train", 0) == 1
    assert "zergling" in larva.can_upgrade_to
    assert getattr(hatchery, "spawns_unit", None) == "larva"
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


def test_spawns_unit_type_and_legacy_larva_cap():
    host = types.SimpleNamespace(spawns_unit="egg", larva_cap=2)
    assert spawns_unit_type(host) == "egg"
    assert is_unit_spawn_host(host)
    legacy = types.SimpleNamespace(spawns_unit=None, larva_cap=3)
    assert spawns_unit_type(legacy) == "larva"
    empty = types.SimpleNamespace(spawns_unit=None, larva_cap=0)
    assert spawns_unit_type(empty) is None
    assert not is_unit_spawn_host(empty)


def test_count_and_spawn_use_configured_type():
    player = object()
    place = types.SimpleNamespace(objects=[], find_free_space=lambda *a: (1, 2))
    host = types.SimpleNamespace(
        spawns_unit="drone_egg",
        larva_cap=2,
        player=player,
        place=place,
        x=0,
        y=0,
    )
    egg = types.SimpleNamespace(type_name="drone_egg", player=player, hp=1)
    place.objects.append(egg)
    assert count_spawned_on_square(host) == 1
    assert spawn_host_cap(host) == 2

    created = []

    class _EggCls:
        def __init__(self, p, pl, x, y):
            self.type_name = "drone_egg"
            self.player = p
            self.hp = 1
            self.notify = lambda *_: None
            created.append(self)
            pl.objects.append(self)

    import soundrts.definitions as definitions

    old = definitions.rules.unit_class
    definitions.rules.unit_class = lambda name: _EggCls if name == "drone_egg" else None
    try:
        assert spawn_unit_at_host(host, 1) == 1
        assert len(created) == 1
        assert count_spawned_on_square(host) == 2
        assert spawn_unit_at_host(host, 1) == 0  # at cap
        fill_spawn_host(host)
        assert count_spawned_on_square(host) == 2
    finally:
        definitions.rules.unit_class = old


def test_inject_buff_uses_spawn_host_not_type_name():
    player = object()
    host = types.SimpleNamespace(
        spawns_unit="larva",
        player=player,
        _buff_time_cost_percent=-30,
    )
    other = types.SimpleNamespace(
        type_name="hatchery",
        spawns_unit=None,
        larva_cap=0,
        player=player,
        _buff_time_cost_percent=-50,
    )
    place = types.SimpleNamespace(objects=[other, host])
    unit = types.SimpleNamespace(type_name="larva", player=player, place=place)
    # Uses host that spawns larva, not the hatchery-named building without spawns_unit
    assert _spawn_host_inject_time_multiplier(unit) == 70
