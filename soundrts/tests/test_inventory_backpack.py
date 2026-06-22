"""背包同型物品：装备武器/盔甲、使用消耗品、新命令注册与客户端绑定。"""
from __future__ import annotations

from pathlib import Path

import pytest

import soundrts.worldunit  # noqa: F401

from soundrts.worlditem import Item
from soundrts.worldorders import ORDERS_DICT
from soundrts.worldorders.immediate import (
    EquipArmorOrder,
    EquipBuiltinArmorOrder,
    EquipWeaponOrder,
    UnequipArmorOrder,
    UnequipWeaponOrder,
    UseItemOrder,
)


def _source(*parts):
    return (Path(__file__).resolve().parents[1] / Path(*parts)).read_text(encoding="utf-8")


def test_item_same_type_weapon_armor_flags():
    assert hasattr(Item, "equippable_as_weapon")
    assert hasattr(Item, "equippable_as_armor")
    assert hasattr(Item, "can_use_tech")
    assert "can_use_tech" in _source("worlditem.py")

    class _Sword:
        type_name = "sword"
        equippable_as_weapon = 1
        equippable_as_armor = 0

        @property
        def is_weapon_item(self):
            return bool(self.equippable_as_weapon)

        @property
        def is_armor_item(self):
            return bool(self.equippable_as_armor)

    item = _Sword()
    assert item.is_weapon_item is True
    assert item.is_armor_item is False


def test_inventory_orders_registered():
    for kw in (
        "equip_weapon", "unequip_weapon", "equip_armor", "unequip_armor",
        "equip_builtin_armor", "use_item",
    ):
        assert kw in ORDERS_DICT
    assert ORDERS_DICT["equip_weapon"] is EquipWeaponOrder
    assert ORDERS_DICT["equip_builtin_armor"] is EquipBuiltinArmorOrder
    assert ORDERS_DICT["use_item"] is UseItemOrder


def test_client_inventory_screen_wiring():
    src = _source("attributes", "inventory_screen.py")
    assert "cmd_unit_inventory_screen" in src
    assert "_inventory_use" in src
    assert "_inventory_intro" in src
    bindings = _source("..", "res", "ui", "global_bindings.txt")
    assert "SHIFT V: toggle_gear_screen" in bindings
    legacy = _source("..", "res", "ui", "legacy_bindings.txt")
    assert "SHIFT V: toggle_gear_screen" in legacy


def test_client_equipment_screen_wiring():
    src = _source("attributes", "equipment_screen.py")
    assert "cmd_unit_equipment_screen" in src
    assert "_equipment_use" in src
    assert "_equipment_unequip" in src
    assert "builtin_weapon" in src
    assert "CANNOT_EQUIP_ITEM_WITH_BUILTIN" in src
    assert "CANNOT_SWITCH_MIXED_GEAR" in src
    assert "nb2msg" in src
    assert "_current_weapon_name" in src
    bindings = _source("..", "res", "ui", "global_bindings.txt")
    assert "CTRL V: unit_equipment_screen" not in bindings
    assert "F3: toggle_gear_screen" in bindings
    main = _source("attributes", "main_interface.py")
    assert "cmd_unit_equipment_screen" in main
    assert "EquipmentScreen" in main


def test_equipment_screen_display_uses_nb2msg():
    """序号应使用 nb2msg，避免 tts.txt 将 \"1\" 读成 \"你在\"。"""
    src = _source("attributes", "equipment_screen.py")
    assert "nb2msg(idx + 1)" in src
    assert "nb2msg(len(entries))" in src
    assert '[str(idx + 1), "共", str(len(entries))]' not in src
    inv = _source("attributes", "inventory_screen.py")
    assert "nb2msg(idx + 1)" in inv
    assert "nb2msg(len(items))" in inv


def test_equipment_screen_skips_item_gear_as_builtin():
    """class item 出厂装备只出现在背包条目，不与内置武器/护甲重复。"""
    src = _source("attributes", "equipment_screen.py")
    assert "_is_item_gear_type" in src
    assert '_is_item_gear_type(weapon_name, "weapon")' in src
    assert '_is_item_gear_type(armor, "armor")' in src


def test_equipment_screen_builtin_weapon_equipped_uses_current_weapon():
    """内置武器是否已装备应直接看 current_weapon，出厂未装备时不应误判。"""
    src = _source("attributes", "equipment_screen.py")
    assert 'getattr(model, "current_weapon", None) == data' in src
    assert "switch_to_weapon" in src
    assert "equip_builtin_armor" in src


def test_equipment_screen_blocks_builtin_drop():
    """传统内置武器/护甲不可丢弃；背包物品及已装备物品可直接丢弃。"""
    src = _source("attributes", "equipment_screen.py")
    assert "_can_drop_entry" in src
    assert "CANNOT_DROP_BUILTIN_GEAR" in src
    assert "builtin_weapon" in src
    assert "builtin_armor" in src
    assert "data not in inv" not in src
    assert src.index("_can_drop_entry") < src.index("DROPPED_ITEM")
    drop_src = _source("worldorders", "skills.py")
    assert "_find_gear_item_by_id" in drop_src
    assert "_inventory_weapon_items" in drop_src


def test_intro_in_item_weapon_armor_detail():
    for name in ("item_detail.py", "weapon_detail.py", "armor_detail.py"):
        assert 'style.get(' in _source("attributes", name)
        assert "intro" in _source("attributes", name)


class _WeaponItem:
    type_name = "sword"
    id = 42

    @property
    def is_weapon_item(self):
        return True

    @property
    def is_armor_item(self):
        return False


class _StubUnit:
    def __init__(self):
        self.inventory = [_WeaponItem()]
        self.notified = []
        self.equipped = None

    def notify(self, msg):
        self.notified.append(msg)

    def equip_weapon_item(self, item):
        self.equipped = item
        return True


def test_equip_weapon_order_allowed():
    unit = _StubUnit()
    assert EquipWeaponOrder.is_allowed(unit, 42) is True
    assert EquipWeaponOrder.is_allowed(unit, 99) is False
    assert UseItemOrder.is_allowed(unit, 42) is False


def test_drop_order_accepts_navigated_square():
    """菜单丢弃需 1 个地图目标（当前导航格），以便先走到目标格再丢弃。"""
    from soundrts.worldorders.skills import DropOrder

    assert DropOrder.nb_args == 1


def test_drop_order_parse_item_and_place_args():
    import types

    from soundrts.worldorders.skills import DropOrder

    a1 = types.SimpleNamespace(id="0,0")
    c1 = types.SimpleNamespace(id="2,0")
    item = types.SimpleNamespace(id=42, type_name="sword")
    player = types.SimpleNamespace(
        get_object_by_id=lambda i: c1 if str(i) == "2,0" else None,
    )
    unit = types.SimpleNamespace(
        inventory=[item],
        _inventory_weapon_items={},
        _inventory_armor_item=None,
        player=player,
        place=a1,
        notifications=[],
    )
    unit.notify = lambda msg: unit.notifications.append(msg)

    order = DropOrder(unit, ["42", "2,0"])
    order.on_queued()
    assert order.is_impossible is False
    assert order.item is item
    assert order.drop_place is c1

    order = DropOrder(unit, ["42"])
    order.on_queued()
    assert order.item is item
    assert order.drop_place is None

    order = DropOrder(unit, ["2,0"])
    order.on_queued()
    assert order.item is item
    assert order.drop_place is c1


def test_drop_order_moves_before_drop():
    import types

    from soundrts.worldorders.skills import DropOrder

    a1 = types.SimpleNamespace(id="0,0")
    c1 = types.SimpleNamespace(id="2,0")
    item = types.SimpleNamespace(id=42, type_name="sword")
    player = types.SimpleNamespace(
        get_object_by_id=lambda i: c1 if str(i) == "2,0" else None,
    )
    moves = []
    drops = []
    unit = types.SimpleNamespace(
        inventory=[item],
        _inventory_weapon_items={},
        _inventory_armor_item=None,
        player=player,
        place=a1,
        drop=lambda i: drops.append(i),
        notifications=[],
    )
    unit.notify = lambda msg: unit.notifications.append(msg)

    order = DropOrder(unit, ["42", "2,0"])
    order.on_queued()
    order.move_to_or_fail = lambda place: moves.append(place)
    order.execute()
    assert moves == [c1]
    assert drops == []

    unit.place = c1
    order.execute()
    assert order.is_complete is True
    assert drops == [item]


def test_drop_order_drops_on_meadow_in_target_square():
    """单位站在目标格的草地上时应能丢弃，而非一直尝试移动。"""
    import types

    from soundrts.worldorders.skills import DropOrder

    a1 = types.SimpleNamespace(id="0,0")
    c1 = types.SimpleNamespace(id="2,0")
    meadow_c1 = types.SimpleNamespace(id="meadow-c1", place=c1, type_name="meadow")
    item = types.SimpleNamespace(id=42, type_name="sword")
    player = types.SimpleNamespace(
        get_object_by_id=lambda i: c1 if str(i) == "2,0" else None,
    )
    drops = []
    unit = types.SimpleNamespace(
        inventory=[item],
        _inventory_weapon_items={},
        _inventory_armor_item=None,
        player=player,
        place=meadow_c1,
        drop=lambda i: drops.append(i),
        notifications=[],
    )
    unit.notify = lambda msg: unit.notifications.append(msg)

    order = DropOrder(unit, ["42", "2,0"])
    order.on_queued()
    order.execute()
    assert order.is_complete is True
    assert drops == [item]


def test_send_inventory_order_appends_navigated_place():
    src = _source("clientgame", "game_unit_control.py")
    assert "_entity_map_square" in src
    assert "unit_square is not nav_square" in src
    assert 'if order == "drop":' in src


def test_drop_order_finds_equipped_gear():
    from soundrts.worldorders.skills import DropOrder

    class _Sword:
        type_name = "sword"
        id = 42

    unit = type("Unit", (), {})()
    unit.inventory = []
    unit._inventory_weapon_items = {"sword": _Sword()}
    unit._inventory_armor_item = None

    assert DropOrder.is_allowed(unit) is True
    assert DropOrder._find_item(unit, 42) is unit._inventory_weapon_items["sword"]
    assert DropOrder._find_item(unit, 99) is None


def test_starting_gear_spawn_wiring():
    src = _source("worldunit", "worldbase.py")
    assert "_spawn_starting_gear_to_inventory" in src
    assert "_equip_weapon_item_silently" in src
    assert "_is_item_gear_class" in src
    assert "_has_mixed_weapon_gear" in src
    assert "can_equip_item_weapon" in src
    assert "_can_switch_between_weapons" in src
    assert "equippable_as_weapon" in src
    assert "spawn_weapons_equipped" in src
    assert "spawn_armor_equipped" in src
    assert "_equip_builtin_armor" in src


def test_spawn_starting_gear_puts_sword_in_inventory(monkeypatch):
    import types

    import soundrts.worldunit  # noqa: F401
    from soundrts.worlditem import Item
    from soundrts.worldunit.worldbase import Unit

    class _SwordItem(Item):
        type_name = "sword"
        equippable_as_weapon = 1
        equippable_as_armor = 0
        mdg = 3500
        mdg_bonus = 2500
        mdg_cd = 1500
        mdg_range = 1000
        transport_volume = 1

        def __init__(self, place, x, y):
            self.id = 101
            self.place = place
            self.x = x
            self.y = y

        def move_to(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y

        def equip(self, host):
            pass

    class _Footman(Unit):
        type_name = "test_footman"
        weapons = ["sword"]
        armor = "footman_armor"
        inventory_capacity = 2
        spawn_weapons_equipped = 1

    unit = _Footman.__new__(_Footman)
    unit.inventory = []
    unit.weapons = ["sword"]
    unit.armor = "footman_armor"
    unit._weapon_instances = {}
    unit._inventory_weapon_items = {}
    unit._inventory_armor_item = None
    unit._armor_before_item = None
    unit.current_weapon = None
    unit._weapons = []
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())
    unit.x = 0
    unit.y = 0
    unit.player = None
    unit.type_name = "test_footman"
    unit.mdf = 0
    unit.rdf = 0
    unit.mdf_crit_rate = 0
    unit.rdf_crit_rate = 0
    unit.mdf_piercing = 0
    unit.rdf_piercing = 0

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: _SwordItem if name == "sword" else None,
    )

    unit._spawn_starting_gear_to_inventory()

    assert len(unit.inventory) == 0
    assert unit.current_weapon == "sword"
    assert unit._inventory_weapon_items.get("sword").id == 101
    assert unit.is_inventory_weapon_item(unit._inventory_weapon_items["sword"]) is True


def test_spawn_weapons_equipped_zero_keeps_item_in_inventory(monkeypatch):
    import types

    from soundrts.worlditem import Item
    from soundrts.worldunit.worldbase import Unit

    class _SwordItem(Item):
        type_name = "sword"
        equippable_as_weapon = 1
        equippable_as_armor = 0
        transport_volume = 1

        def __init__(self, place, x, y):
            self.id = 101
            self.place = place
            self.x = x
            self.y = y

        def move_to(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y

        def equip(self, host):
            pass

    class _Footman(Unit):
        type_name = "test_footman"
        weapons = ["sword"]
        inventory_capacity = 2
        spawn_weapons_equipped = 0

    unit = _Footman.__new__(_Footman)
    unit.inventory = []
    unit.weapons = ["sword"]
    unit._weapon_instances = {}
    unit._inventory_weapon_items = {}
    unit.current_weapon = None
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())
    unit.x = 0
    unit.y = 0
    unit.player = None
    unit.type_name = "test_footman"

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: _SwordItem if name == "sword" else None,
    )

    unit._spawn_starting_gear_to_inventory()

    assert len(unit.inventory) == 1
    assert unit.inventory[0].id == 101
    assert unit.current_weapon is None
    assert not unit._inventory_weapon_items


def test_spawn_armor_equipped_zero_and_equip_builtin_armor(monkeypatch):
    import types

    from soundrts.worldarmor import Armor
    from soundrts.worldunit.worldbase import Unit

    class _LightArmor(Armor):
        type_name = "light_armor"
        mdf = 500

        def apply_to_unit(self, unit):
            unit.mdf = self.mdf

    class _Knight(Unit):
        type_name = "test_knight"
        armor = "light_armor"
        spawn_armor_equipped = 0

    unit = _Knight.__new__(_Knight)
    unit.inventory = []
    unit._armor = None
    unit._armor_instance = None
    unit._builtin_armor_applied = False
    unit._inventory_armor_item = None
    unit.mdf = 0
    unit.rdf = 0
    unit.mdf_crit_rate = 0
    unit.rdf_crit_rate = 0
    unit.mdf_piercing = 0
    unit.rdf_piercing = 0
    unit.player = None
    unit.type_name = "test_knight"
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: _LightArmor if name == "light_armor" else None,
    )
    monkeypatch.setattr(
        Unit,
        "_is_item_gear_class",
        staticmethod(lambda type_name, gear_kind: False),
    )

    unit._apply_armors()

    assert unit._armor_instance is not None
    assert unit._builtin_armor_applied is False
    assert unit.mdf == 0
    assert EquipBuiltinArmorOrder.is_allowed(unit) is True

    assert unit._equip_builtin_armor() is True
    assert unit._builtin_armor_applied is True
    assert unit.mdf == 500


def test_use_item_order_rejects_weapon():
    unit = _StubUnit()
    assert UseItemOrder.is_allowed(unit, 42) is False


def test_gear_sound_event_handlers_wired():
    """卸下武器/装备盔甲/卸下盔甲的客户端音效处理器已接入。"""
    src = _source("clientgameentity", "events.py")
    for name in (
        "on_weapon_unequipped",
        "on_armor_equipped",
        "on_armor_unequipped",
        "_play_type_sound",
    ):
        assert name in src
    worldbase = _source("worldunit", "worldbase.py")
    assert 'self.notify(f"weapon_unequipped,{name}")' in worldbase
    assert 'self.notify(f"armor_equipped,{item.type_name}")' in worldbase
    assert 'self.notify(f"armor_unequipped,{getattr(item, \'type_name\', \'\')}")' in worldbase


def test_mixed_weapon_gear_spawn_prefers_builtin(monkeypatch):
    """混合内置+item 武器且 spawn_weapons_equipped=1 时，内置优先装备，item 留在背包。"""
    import types

    from soundrts.worlditem import Item
    from soundrts.worldunit.worldbase import Unit
    from soundrts.worldweapon import Weapon

    class _Bow(Weapon):
        type_name = "bow"
        rdg = 2500
        rdg_range = 4000

    class _SwordItem(Item):
        type_name = "sword"
        equippable_as_weapon = 1
        equippable_as_armor = 0
        transport_volume = 1

        def __init__(self, place, x, y):
            self.id = 101
            self.place = place
            self.x = x
            self.y = y

        def move_to(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y

        def equip(self, host):
            pass

    class _Archer(Unit):
        type_name = "test_archer"
        weapons = ["bow", "sword"]
        inventory_capacity = 3
        spawn_weapons_equipped = 1

    unit = _Archer.__new__(_Archer)
    unit.inventory = []
    unit.weapons = ["bow", "sword"]
    unit._weapon_instances = {}
    unit._inventory_weapon_items = {}
    unit._inventory_armor_item = None
    unit.current_weapon = None
    unit._weapons = []
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())
    unit.x = 0
    unit.y = 0
    unit.player = None
    unit.type_name = "test_archer"

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: {"bow": _Bow, "sword": _SwordItem}.get(name),
    )

    unit._apply_weapons()
    unit._spawn_starting_gear_to_inventory()

    assert unit.current_weapon == "bow"
    assert not unit._inventory_weapon_items
    assert len(unit.inventory) == 1
    assert unit.inventory[0].type_name == "sword"
    assert unit.can_equip_item_weapon() is False


def test_mixed_weapon_gear_blocks_cross_switch(monkeypatch):
    import types

    from soundrts.worlditem import Item
    from soundrts.worldunit.worldbase import Unit
    from soundrts.worldweapon import Weapon

    class _Bow(Weapon):
        type_name = "bow"
        rdg = 2500
        rdg_range = 4000

        def apply_to_unit(self, u):
            u.rdg = self.rdg

    class _SwordItem(Item):
        type_name = "sword"
        equippable_as_weapon = 1
        equippable_as_armor = 0
        transport_volume = 1
        mdg = 3500
        mdg_range = 1000

        def __init__(self, place, x, y):
            self.id = 101
            self.place = place
            self.x = x
            self.y = y

        def move_to(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y

        def equip(self, host):
            pass

    class _Archer(Unit):
        type_name = "test_archer"
        weapons = ["bow", "sword"]
        inventory_capacity = 3
        spawn_weapons_equipped = 0

    unit = _Archer.__new__(_Archer)
    unit.inventory = []
    unit.weapons = ["bow", "sword"]
    unit._weapon_instances = {}
    unit._inventory_weapon_items = {}
    unit.current_weapon = None
    unit._weapons = []
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())
    unit.x = 0
    unit.y = 0
    unit.player = None
    unit.type_name = "test_archer"
    unit.world = types.SimpleNamespace(time=0)
    unit.notify = lambda *args, **kwargs: None
    unit._clear_weapon_attributes = lambda: None
    unit._reapply_phase_weapon_bonus = lambda: None
    unit.equip_weapon_item = Unit.equip_weapon_item.__get__(unit, Unit)
    unit.switch_weapon = Unit.switch_weapon.__get__(unit, Unit)
    unit._make_weapon_instance_from_item = Unit._make_weapon_instance_from_item.__get__(unit, Unit)

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: {"bow": _Bow, "sword": _SwordItem}.get(name),
    )

    unit._apply_weapons()
    unit._spawn_starting_gear_to_inventory()
    sword = unit.inventory[0]

    assert unit.can_equip_item_weapon() is True
    assert unit.equip_weapon_item(sword) is True
    assert unit.current_weapon == "sword"
    assert unit.switch_weapon("bow") is False
    assert unit.current_weapon == "sword"
    assert unit.get_available_weapons() == ["sword"]


def test_builtin_armor_blocks_item_armor_equip(monkeypatch):
    import types

    from soundrts.worldarmor import Armor
    from soundrts.worlditem import Item
    from soundrts.worldunit.worldbase import Unit

    class _LightArmor(Armor):
        type_name = "light_armor"
        mdf = 500

        def apply_to_unit(self, unit):
            unit.mdf = self.mdf

    class _ItemArmor(Item):
        type_name = "footman_armor"
        equippable_as_weapon = 0
        equippable_as_armor = 1
        transport_volume = 1
        mdf = 300

        def __init__(self, place, x, y):
            self.id = 202
            self.place = place
            self.x = x
            self.y = y

        def move_to(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y

        def equip(self, host):
            pass

    class _Knight(Unit):
        type_name = "test_knight"
        armor = "light_armor"
        spawn_armor_equipped = 1

    unit = _Knight.__new__(_Knight)
    unit.inventory = [_ItemArmor(None, 0, 0)]
    unit._armor = None
    unit._armor_instance = None
    unit._builtin_armor_applied = False
    unit._inventory_armor_item = None
    unit.mdf = 0
    unit.rdf = 0
    unit.mdf_crit_rate = 0
    unit.rdf_crit_rate = 0
    unit.mdf_piercing = 0
    unit.rdf_piercing = 0
    unit.player = None
    unit.type_name = "test_knight"
    unit.place = types.SimpleNamespace(world=types.SimpleNamespace())
    unit.notify = lambda *args, **kwargs: None
    unit._clear_armor_attributes = lambda: None
    unit._reapply_phase_armor_bonus = lambda: None
    unit._make_armor_instance_from_item = Unit._make_armor_instance_from_item.__get__(unit, Unit)

    from soundrts.definitions import rules

    monkeypatch.setattr(
        rules,
        "unit_class",
        lambda name: {"light_armor": _LightArmor, "footman_armor": _ItemArmor}.get(name),
    )
    monkeypatch.setattr(
        Unit,
        "_is_item_gear_class",
        staticmethod(lambda type_name, gear_kind: type_name == "footman_armor"),
    )

    unit._apply_armors()

    assert unit._is_builtin_armor_applied() is True
    assert unit.can_equip_item_armor() is False
    assert unit.equip_armor_item(unit.inventory[0]) is False


def test_equipped_gear_removed_from_inventory():
    """已装备的武器/盔甲不在背包中，卸下后回到背包。"""
    import types

    from soundrts.worldunit.worldbase import Unit

    class _Sword:
        type_name = "sword"
        id = 101

        @property
        def is_weapon_item(self):
            return True

    class _Armor:
        type_name = "footman_armor"
        id = 202

        @property
        def is_armor_item(self):
            return True

    unit = Unit.__new__(Unit)
    sword = _Sword()
    armor = _Armor()
    unit.inventory = [sword, armor]
    unit.weapons = []
    unit._weapon_instances = {}
    unit._inventory_weapon_items = {}
    unit._inventory_armor_item = None
    unit._armor_before_item = None
    unit.current_weapon = None
    unit._weapons = []
    unit.place = types.SimpleNamespace()
    unit.x = 0
    unit.y = 0
    unit.player = None
    unit.mdf = 0
    unit.rdf = 0
    unit.mdf_crit_rate = 0
    unit.rdf_crit_rate = 0
    unit.mdf_piercing = 0
    unit.rdf_piercing = 0
    unit.inventory_capacity = 10
    unit.notify = lambda *args, **kwargs: None

    unit.equip_weapon_item = Unit.equip_weapon_item.__get__(unit, Unit)
    unit.equip_armor_item = Unit.equip_armor_item.__get__(unit, Unit)
    unit.unequip_weapon_item = Unit.unequip_weapon_item.__get__(unit, Unit)
    unit.unequip_armor_item = Unit.unequip_armor_item.__get__(unit, Unit)
    unit._make_weapon_instance_from_item = lambda item: types.SimpleNamespace(
        type_name=item.type_name,
        apply_to_unit=lambda u: None,
    )
    unit._make_armor_instance_from_item = lambda item: types.SimpleNamespace(
        type_name=item.type_name,
        apply_to_unit=lambda u: None,
    )
    unit.switch_weapon = lambda name: setattr(unit, "current_weapon", name)
    unit._clear_weapon_attributes = lambda: None
    unit._clear_armor_attributes = lambda: None
    unit._reapply_phase_weapon_bonus = lambda: None
    unit._reapply_phase_armor_bonus = lambda: None

    unit.equip_weapon_item(sword)
    assert sword not in unit.inventory
    assert "sword" in unit._inventory_weapon_items

    unit.equip_armor_item(armor)
    assert armor not in unit.inventory
    assert unit._inventory_armor_item is armor

    unit.unequip_weapon_item(sword)
    assert sword in unit.inventory

    unit.unequip_armor_item(armor)
    assert armor in unit.inventory
