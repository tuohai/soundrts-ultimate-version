"""Burning buildings (StarCraft) regression tests."""

from pathlib import Path

from soundrts.definitions import Rules


def _starcraft_rules_text():
    return Path("mods/starcraft/rules.txt").read_text(encoding="utf-8")


class _FakeBuilding:
    """Minimal stand-in for a building that can burn.

    ``hp_max`` / ``hp`` / ``burn_damage`` are on the PRECISION HP scale
    (the engine stores HP multiplied by 1000).
    """

    is_a_building = True
    hp_max = 100 * 1000
    hp = 100 * 1000
    burn_hp_threshold_pct = 33
    burn_damage = 5 * 1000
    burn_interval = 1000  # milliseconds
    _is_burning = False
    _burn_next_time = 0

    def notify(self, *_args, **_kwargs):
        pass

    def die(self, *_args, **_kwargs):
        self.hp = 0


def test_burn_keywords_are_known():
    from soundrts.definitions import rules as global_rules

    # ``burn_hp_threshold_pct`` is a raw percentage.
    assert "burn_hp_threshold_pct" in global_rules.int_properties
    # ``burn_damage`` follows the HP scale and ``burn_interval`` the
    # timing scale: both are PRECISION-scaled.
    assert "burn_damage" in global_rules.precision_properties
    assert "burn_interval" in global_rules.precision_properties


def test_burn_helpers_read_the_rules():
    from soundrts.lib.nofloat import PRECISION
    from soundrts.world_building_burn import (
        burn_damage,
        burn_interval,
        burn_threshold_pct,
        can_burn,
    )

    rules = Rules()
    rules.load(
        """
def barracks
class building
hp_max 600
burn_hp_threshold_pct 33
burn_damage 5
burn_interval 1
"""
    )
    barracks = rules.unit_class("barracks")
    assert burn_threshold_pct(barracks) == 33
    assert burn_damage(barracks) == 5 * PRECISION
    assert burn_interval(barracks) == 1 * PRECISION
    assert can_burn(barracks) is True


def test_building_without_burn_rules_does_not_burn():
    from soundrts.world_building_burn import can_burn, should_start_burning

    rules = Rules()
    rules.load(
        """
def pylon
class building
hp_max 200
"""
    )
    pylon = rules.unit_class("pylon")
    assert can_burn(pylon) is False
    assert should_start_burning(pylon) is False


def test_building_below_the_threshold_starts_burning():
    from soundrts.world_building_burn import (
        is_burning,
        should_start_burning,
        start_burning,
    )

    building = _FakeBuilding()
    assert should_start_burning(building) is False
    building.hp = 30 * 1000  # 30% of 100 -> below the 33% threshold
    assert should_start_burning(building) is True
    start_burning(building)
    assert is_burning(building) is True
    # Once burning, it does not restart.
    assert should_start_burning(building) is False


def test_burn_tick_removes_hp():
    from soundrts.world_building_burn import burn_tick, start_burning

    building = _FakeBuilding()
    building.hp = 30 * 1000
    start_burning(building)
    assert burn_tick(building, 1000) is True
    assert building.hp == 25 * 1000


def test_burn_tick_respects_the_interval():
    from soundrts.world_building_burn import burn_tick, start_burning

    building = _FakeBuilding()
    building.hp = 30 * 1000
    start_burning(building)
    assert burn_tick(building, 1000) is True
    assert building.hp == 25 * 1000
    # Too soon for the next tick.
    assert burn_tick(building, 1500) is False
    assert building.hp == 25 * 1000
    # After the interval.
    assert burn_tick(building, 2000) is True
    assert building.hp == 20 * 1000


def test_burning_building_dies_when_its_hp_runs_out():
    from soundrts.world_building_burn import burn_tick, start_burning

    building = _FakeBuilding()
    building.hp = 5 * 1000
    start_burning(building)
    burn_tick(building, 1000)
    assert building.hp == 0


def test_starcraft_mod_buildings_burn():
    rules = Rules()
    rules.load(_starcraft_rules_text())
    for name in ("barracks", "factory", "pylon", "hatchery"):
        building = rules.unit_class(name)
        assert building is not None, name
        assert int(getattr(building, "burn_damage", 0) or 0) > 0, name
        assert int(getattr(building, "burn_hp_threshold_pct", 0) or 0) == 33, name
