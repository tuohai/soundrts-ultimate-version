"""生产完成时资源入库（无 is_create 落地堆）。"""

import types

from soundrts.worldunit.world_status_update import CreatureStatusUpdate


class _StubPlayer:
    def __init__(self):
        self.resources = [0, 0, 0]
        self.storage_bonus = [0, 0, 0]
        self.world = types.SimpleNamespace(players=[self])
        self.stored = []

    def store(self, resource_type, qty):
        self.stored.append((resource_type, qty))
        if resource_type == "resource1":
            self.resources[0] += qty

    def send_event(self, unit, event):
        pass


def _make_building(**overrides):
    player = _StubPlayer()
    building = types.SimpleNamespace(
        player=player,
        production_type="resource1",
        production_qty=200,
        is_gather=0,
        production_item=None,
        current_production_mode="manual",
        manual_production=0,
        is_producing=True,
        production_progress=0,
        orders=[],
        _previous_completeness=None,
        type_name="gold_house",
        debug_log=lambda *args, **kwargs: None,
        notify=lambda *args, **kwargs: None,
    )
    for key, value in overrides.items():
        setattr(building, key, value)
    building._normalize_production_item_name = (
        CreatureStatusUpdate._normalize_production_item_name
    )
    return building


def test_complete_production_manual_mode_stores_to_stockpile():
    building = _make_building(current_production_mode="manual", manual_production=1)
    CreatureStatusUpdate.complete_production(building)
    assert building.player.stored == [("resource1", 200000)]
    assert building.player.resources[0] == 200000
    assert building.is_producing is False


def test_complete_production_auto_mode_stores_to_stockpile():
    building = _make_building(
        current_production_mode="auto",
        manual_production=1,
        check_if_enough_resources=lambda *args, **kwargs: "not_enough",
    )
    CreatureStatusUpdate.complete_production(building)
    assert building.player.stored == [("resource1", 200000)]
    assert building.player.resources[0] == 200000


def test_complete_production_is_gather_adds_to_building_storage():
    building = _make_building(
        is_gather=1,
        resource_volume_max=50,
        resource_qty=10,
        resource_type="resource3",
        production_type="resource3",
        production_qty=5,
    )
    CreatureStatusUpdate.complete_production(building)
    assert building.resource_qty == 15
    assert building.player.stored == []


def test_complete_production_item_spawns_items_not_stockpile():
    building = _make_building(
        production_item="gold_pile",
        production_type=None,
        production_qty=2,
    )
    spawned = []

    def _fake_spawn(item_type_name, count):
        spawned.append((item_type_name, count))
        return count

    building._spawn_production_items = _fake_spawn
    CreatureStatusUpdate.complete_production(building)
    assert spawned == [("gold_pile", 2)]
    assert building.player.stored == []


def test_gold_house_rules_use_production_type_not_item():
    from pathlib import Path

    text = Path("res/rules.txt").read_text(encoding="utf-8")
    block = text.split("def gold_house")[1].split("\ndef ")[0]
    assert "auto_production 1" in block
    assert "manual_production 1" in block
    assert "production_type resource1" in block
    assert "production_qty 200" in block
    assert "production_item" not in block
    assert "is_create" not in block
    assert "is_gather" not in block


def test_gold_house_class_supports_manual_and_auto_produce():
    from pathlib import Path

    from soundrts.definitions import Rules, _get_base_classes

    rules = Rules()
    rules.load(Path("res/rules.txt").read_text(encoding="utf-8"), base_classes=_get_base_classes())
    gold_house = rules.unit_class("gold_house")
    assert gold_house.auto_production == 1
    assert gold_house.manual_production == 1
    assert gold_house.is_gather == 0
