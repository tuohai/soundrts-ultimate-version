"""验证单位升级/变形为另一种单位后，原单位携带的物品会随之转移。

需求场景：一个单位拿到一个物品，当它升级（upgrade_to / change_to / 时代自动形态升级）
到另一个单位后，物品应当出现在升级后的单位身上，而不是凭空消失。

改动点：
1. ``soundrts/worldunit/world_order.py``：新增 ``CreatureOrders.transfer_inventory_to()``。
2. ``soundrts/worldorders/production.py``：``UpgradeToOrder.complete()`` /
   ``ChangeToOrder.complete()`` 在删除旧单位后把库存转移到新单位。
3. ``soundrts/worldphase.py``：``_instant_morph()`` 同样转移库存。

为避免拉起 pygame/locale 等 client-side 重依赖，这里只针对引擎层做最小化
对象注入式测试（与 test_give_item_to_npc.py 的风格一致）。
"""
from __future__ import annotations

import types

import soundrts.worldunit  # noqa: F401  解开 worldunit 包的循环导入

from soundrts.worldunit.world_order import CreatureOrders


class _StubItem:
    """模拟一件物品的最小接口，记录 equip/unequip/move_to 调用。"""

    def __init__(self, type_name, item_id=1):
        self.type_name = type_name
        self.id = item_id
        self.equipped_on = None
        self.unequipped_from = None
        self.moved_to = None

    def equip(self, host):
        self.equipped_on = host

    def unequip(self, host):
        self.unequipped_from = host

    def move_to(self, place, x, y):
        self.moved_to = (place, x, y)


def _make_unit(inventory=None):
    return types.SimpleNamespace(inventory=list(inventory or []))


def test_transfer_moves_all_items_to_new_unit():
    old = _make_unit()
    new = _make_unit()
    sword = _StubItem("sword", item_id=1)
    potion = _StubItem("health_potion", item_id=2)
    old.inventory.extend([sword, potion])

    CreatureOrders.transfer_inventory_to(old, new)

    # 旧单位库存清空，新单位拿到全部物品
    assert old.inventory == []
    assert sword in new.inventory
    assert potion in new.inventory


def test_transfer_reequips_items_on_new_unit():
    old = _make_unit()
    new = _make_unit()
    sword = _StubItem("sword")
    old.inventory.append(sword)

    CreatureOrders.transfer_inventory_to(old, new)

    # 先从旧单位解除装备，再装备到新单位
    assert sword.unequipped_from is old
    assert sword.equipped_on is new


def test_transfer_with_empty_inventory_is_noop():
    old = _make_unit()
    new = _make_unit()

    CreatureOrders.transfer_inventory_to(old, new)

    assert new.inventory == []


def test_transfer_drops_items_when_target_capacity_is_zero():
    """新单位 inventory_capacity 为 0 时，物品不进入其库存，而是掉落在原地。"""
    old = _make_unit()
    new = _make_unit()
    new.inventory_capacity = 0
    new.place = "square"
    new.x = 3
    new.y = 4
    sword = _StubItem("sword")
    old.inventory.append(sword)

    CreatureOrders.transfer_inventory_to(old, new)

    assert old.inventory == []
    assert sword not in new.inventory
    assert new.inventory == []
    # 物品掉落在新单位所在位置，而不是被销毁
    assert sword.moved_to == ("square", 3, 4)
    # 既然没进入库存，就不会装备到新单位上
    assert sword.equipped_on is None


def test_transfer_respects_partial_capacity():
    """容量有限时，只转移能放下的物品，其余掉落在原地。"""
    old = _make_unit()
    new = _make_unit()
    new.inventory_capacity = 1
    new.place = "square"
    new.x = 0
    new.y = 0
    first = _StubItem("sword", item_id=1)
    second = _StubItem("shield", item_id=2)
    old.inventory.extend([first, second])

    CreatureOrders.transfer_inventory_to(old, new)

    assert len(new.inventory) == 1
    assert first in new.inventory
    assert second not in new.inventory
    assert second.moved_to == ("square", 0, 0)


def test_transfer_skips_target_without_inventory():
    old = _make_unit()
    sword = _StubItem("sword")
    old.inventory.append(sword)
    # 目标没有 inventory 列表（例如不能持有物品的单位）
    new = types.SimpleNamespace()

    CreatureOrders.transfer_inventory_to(old, new)

    # 物品保留在旧单位上，不会丢失
    assert sword in old.inventory


def test_upgrade_to_complete_transfers_inventory(monkeypatch):
    """端到端：UpgradeToOrder.complete() 删除旧单位后转移库存到新单位。"""
    from soundrts.worldorders import production

    created = {}

    class _NewUnit:
        def __init__(self, player, place, x, y):
            self.player = player
            self.place = place
            self.x = x
            self.y = y
            self.hp = 100
            self.hp_max = 100
            self.inventory = []
            self.blocked = None
            self.notifications = []
            created["unit"] = self

        def block(self, exit_):
            self.blocked = exit_

        def notify(self, event, universal=False):
            self.notifications.append(event)

    sword = _StubItem("sword")
    old_unit = types.SimpleNamespace(
        inventory=[sword],
        player="player",
        place="place",
        x=1,
        y=2,
        hp=50,
        hp_max=80,
        blocked_exit=None,
        is_buildable_anywhere=False,
        notifications=[],
        deleted=False,
        world=types.SimpleNamespace(get_next_id=lambda increment=True: 42),
    )
    old_unit.transfer_inventory_to = types.MethodType(
        CreatureOrders.transfer_inventory_to, old_unit
    )

    def _delete():
        old_unit.deleted = True

    old_unit.delete = _delete
    old_unit.notify = lambda event, universal=False: old_unit.notifications.append(event)

    order = production.UpgradeToOrder.__new__(production.UpgradeToOrder)
    order.unit = old_unit
    order.type = _NewUnit
    order.type.is_buildable_anywhere = False

    order.complete()

    new_unit = created["unit"]
    assert old_unit.deleted is True
    assert old_unit.inventory == []
    assert sword in new_unit.inventory
    assert sword.equipped_on is new_unit
