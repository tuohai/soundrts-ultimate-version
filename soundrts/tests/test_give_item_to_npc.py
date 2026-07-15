"""验证"把物品交给NPC"功能（give 命令 + npc_has_item 触发器条件）。

需求场景：战役里某关的目标是"把某件物品交给某个NPC"才能通关。

涉及改动点：
1. ``soundrts/worldorders/skills.py``：新增 ``GiveOrder``（keyword="give"）。
2. ``soundrts/worldorders/__init__.py``：导出 ``GiveOrder`` → 进入 ``ORDERS_DICT``。
3. ``soundrts/worldunit/world_order.py``：``CreatureOrders.give()`` 完成物品转移，
   并在目标单位上记录 ``received_items``。
4. ``soundrts/worldunit/worldcreature.py`` / ``worldworker.py``：``get_default_order``
   在携带物品右键非敌对单位时返回 "give"。
5. ``soundrts/worldplayerbase/triggers.py``：新增 ``lang_npc_has_item`` 触发器条件。

为避免拉起 pygame/locale 等 client-side 重依赖，这里只针对引擎层做最小化对象
注入式测试（与 test_neutral_passive_creep.py 的风格一致）。
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

# 解开 worldunit 包的循环导入（与现有 neutral 系列测试一致）
import soundrts.worldunit  # noqa: F401

from soundrts.worldorders import ORDERS_DICT
from soundrts.worldorders.skills import GiveOrder
from soundrts.worldunit.world_order import CreatureOrders
from soundrts.worldunit.worldcreature import Creature
from soundrts.worldplayerbase.triggers import TriggersMixin


# ---------------------------------------------------------------------------
# 最小化桩对象
# ---------------------------------------------------------------------------


class _StubItem:
    """模拟一件物品（worlditem.Item）的最小接口（含 is_a 继承判定）。"""

    def __init__(self, type_name, item_id=1, is_a=()):
        self.type_name = type_name
        self.id = item_id
        self.is_a = tuple(is_a)
        self.expanded_is_a = set(is_a)
        self.equipped_on = None
        self.unequipped_from = None
        self.moved_to = None

    def is_a_type(self, type_name):
        return (
            self.type_name == type_name
            or type_name in self.is_a
            or type_name in self.expanded_is_a
        )

    def equip(self, host):
        self.equipped_on = host

    def unequip(self, host):
        self.unequipped_from = host

    def move_to(self, place, x, y):
        self.moved_to = (place, x, y)


class _StubPlayer:
    def __init__(self, neutral=False):
        self.neutral = neutral
        self.units = []
        self.allied = [self]


class _StubUnit:
    """模拟一个能持有物品的单位（giver 或 NPC）。

    直接复用真实的 ``Creature`` 接收判定逻辑（``can_receive_items`` /
    ``relation_to`` / ``accepts_item`` 等），保证测试覆盖到引擎实际代码。

    ``receive_items`` 控制是否接收（默认1=接收，便于多数测试；引擎默认为0）。
    ``accepted_items`` 物品白名单；``accept_from`` 给予者关系白名单；
    ``accept_givers`` 给予者单位类型白名单。
    """

    # 复用真实判定逻辑（property/方法都是描述符，可直接挂到桩类上）
    can_receive_items = Creature.can_receive_items
    relation_to = Creature.relation_to
    _item_in_whitelist = Creature._item_in_whitelist
    _giver_in_whitelist = Creature._giver_in_whitelist
    accepts_item = Creature.accepts_item
    _RELATION_ALIASES = Creature._RELATION_ALIASES

    def __init__(self, player, type_name="unit", unit_id="u1", place="0,0",
                 receive_items=1, accepted_items=(), accept_from=(),
                 accept_givers=(), is_a=()):
        self.player = player
        self.type_name = type_name
        self.id = unit_id
        self.place = place
        self.x = 0
        self.y = 0
        self.inventory = []
        self.notifications = []
        self.receive_items = receive_items
        self.accepted_items = tuple(accepted_items)
        self.accept_from = tuple(accept_from)
        self.accept_givers = tuple(accept_givers)
        self.is_a = tuple(is_a)
        player.units.append(self)

    def is_a_type(self, t):
        return self.type_name == t or t in self.is_a

    def notify(self, event, universal=False):
        self.notifications.append(event)


def _ally(giver_player, receiver_player):
    """把 receiver_player 设为 giver_player 的盟友。"""
    if receiver_player not in giver_player.allied:
        giver_player.allied.append(receiver_player)
    if giver_player not in receiver_player.allied:
        receiver_player.allied.append(giver_player)


class _StubWorld:
    def __init__(self, players):
        self.players = players
        self.ex_players = []
        self.grid = {}
        self.name_to_square = {}
        self.squares = []


def _make_triggers(world):
    t = TriggersMixin.__new__(TriggersMixin)
    t.world = world
    return t


# ---------------------------------------------------------------------------
# 1. GiveOrder 注册 / 基本约束
# ---------------------------------------------------------------------------


def test_give_order_registered_in_orders_dict():
    assert ORDERS_DICT.get("give") is GiveOrder
    assert GiveOrder.keyword == "give"


def test_give_order_is_allowed_only_with_inventory():
    empty = types.SimpleNamespace(inventory=[])
    full = types.SimpleNamespace(inventory=[_StubItem("health_potion")])
    assert GiveOrder.is_allowed(empty) is False
    assert GiveOrder.is_allowed(full) is True


def test_give_order_menu_exposes_keyword_when_allowed():
    full = types.SimpleNamespace(inventory=[_StubItem("health_potion")])
    empty = types.SimpleNamespace(inventory=[])
    assert GiveOrder.menu(full) == ["give"]
    assert GiveOrder.menu(empty) == []


def test_give_order_find_item_selects_by_type_or_first():
    potion = _StubItem("health_potion", item_id=10)
    scroll = _StubItem("scroll", item_id=11)
    order = GiveOrder.__new__(GiveOrder)
    order.unit = types.SimpleNamespace(inventory=[potion, scroll])

    # 无第二参数 → 第一个物品
    order.args = ["target_id"]
    assert order._find_item() is potion

    # 第二参数按 type_name 选择
    order.args = ["target_id", "scroll"]
    assert order._find_item() is scroll

    # 第二参数按物品 id 选择
    order.args = ["target_id", "10"]
    assert order._find_item() is potion


# ---------------------------------------------------------------------------
# 2. CreatureOrders.give() 物品转移
# ---------------------------------------------------------------------------


def test_give_transfers_item_to_target_inventory():
    giver_player = _StubPlayer()
    npc_player = _StubPlayer(neutral=True)
    giver = _StubUnit(giver_player, type_name="hero", unit_id="h1")
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    potion = _StubItem("health_potion")
    giver.inventory.append(potion)

    CreatureOrders.give(giver, potion, npc)

    assert potion not in giver.inventory
    assert potion in npc.inventory
    assert potion.equipped_on is npc
    assert potion.unequipped_from is giver
    # 双方都应有播报
    assert any(n.startswith("give,") for n in giver.notifications)
    assert any(n.startswith("received,") for n in npc.notifications)


def test_give_records_received_items_on_target():
    giver = _StubUnit(_StubPlayer(), unit_id="h1")
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="oldman", unit_id="n1")
    potion = _StubItem("health_potion")
    giver.inventory.append(potion)

    CreatureOrders.give(giver, potion, npc)

    assert "health_potion" in npc.received_items


def test_give_refuses_when_item_not_in_inventory():
    giver = _StubUnit(_StubPlayer(), unit_id="h1")
    npc = _StubUnit(_StubPlayer(neutral=True), unit_id="n1")
    potion = _StubItem("health_potion")  # 不在库存里

    CreatureOrders.give(giver, potion, npc)

    assert "order_impossible" in giver.notifications
    assert potion not in npc.inventory


def test_give_refuses_when_target_has_no_player():
    giver = _StubUnit(_StubPlayer(), unit_id="h1")
    potion = _StubItem("health_potion")
    giver.inventory.append(potion)
    target = types.SimpleNamespace(player=None, inventory=[])

    CreatureOrders.give(giver, potion, target)

    assert "order_impossible" in giver.notifications
    assert potion in giver.inventory


def test_give_refuses_when_target_does_not_receive_items():
    """receive_items=0 的单位不接收物品，交付应被拒绝。"""
    giver = _StubUnit(_StubPlayer(), unit_id="h1")
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="oldman", unit_id="n1",
                    receive_items=0)
    potion = _StubItem("health_potion")
    giver.inventory.append(potion)

    CreatureOrders.give(giver, potion, npc)

    assert "order_impossible" in giver.notifications
    assert potion in giver.inventory          # 物品仍在给予者身上
    assert potion not in npc.inventory
    assert "health_potion" not in getattr(npc, "received_items", set())


def test_give_succeeds_when_target_receives_items():
    """receive_items=1 的单位正常接收物品。"""
    giver = _StubUnit(_StubPlayer(), unit_id="h1")
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="oldman", unit_id="n1",
                    receive_items=1)
    potion = _StubItem("health_potion")
    giver.inventory.append(potion)

    CreatureOrders.give(giver, potion, npc)

    assert potion in npc.inventory
    assert "health_potion" in npc.received_items


def test_give_order_target_is_a_unit_requires_receive_items():
    """GiveOrder 早期校验：目标不接收物品时 _target_is_a_unit 返回 False。"""
    order = GiveOrder.__new__(GiveOrder)
    order.target = _StubUnit(_StubPlayer(neutral=True), unit_id="n1", receive_items=0)
    assert order._target_is_a_unit() is False

    order.target = _StubUnit(_StubPlayer(neutral=True), unit_id="n2", receive_items=1)
    assert order._target_is_a_unit() is True


def test_default_class_receive_items_is_zero():
    """引擎默认：未配置 receive_items 的单位默认不接收物品（0）。"""
    from soundrts.worldunit.worldcreature import Creature
    assert Creature.receive_items == 0


def test_receive_items_registered_as_int_property():
    """receive_items 必须是 int 属性，rules.txt 写 'receive_items 1' 才会被解析为 1。"""
    from soundrts.definitions import Rules
    assert "receive_items" in Rules.int_properties


def test_accept_fields_registered_as_string_list_properties():
    """accepted_items / accept_from 必须是字符串列表属性，才能解析多值白名单。"""
    from soundrts.definitions import Rules
    assert "accepted_items" in Rules.string_list_properties
    assert "accept_from" in Rules.string_list_properties
    assert "accept_givers" in Rules.string_list_properties


def test_default_class_accept_fields_empty():
    """引擎默认：accepted_items / accept_from 为空（即不限物品、不限关系）。"""
    assert Creature.accepted_items == ()
    assert Creature.accept_from == ()
    assert Creature.accept_givers == ()


# ---------------------------------------------------------------------------
# 2b. 精细控制：relation_to / accepted_items（物品白名单）/ accept_from（关系白名单）
# ---------------------------------------------------------------------------


def test_relation_to_self_ally_neutral_enemy():
    """relation_to 正确区分 self / ally / neutral / enemy。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")

    # self：同一玩家
    own = _StubUnit(g_player, unit_id="own")
    assert own.relation_to(giver) == "self"

    # ally：在 giver 的 allied 列表里
    ally_player = _StubPlayer()
    _ally(g_player, ally_player)
    ally_unit = _StubUnit(ally_player, unit_id="a")
    assert ally_unit.relation_to(giver) == "ally"

    # neutral：中立玩家且未结盟
    neutral_unit = _StubUnit(_StubPlayer(neutral=True), unit_id="n")
    assert neutral_unit.relation_to(giver) == "neutral"

    # enemy：非中立、未结盟
    enemy_unit = _StubUnit(_StubPlayer(neutral=False), unit_id="e")
    assert enemy_unit.relation_to(giver) == "enemy"


def test_only_allied_knight_accepts_knight_lance():
    """场景：只有盟友的骑士接收骑士枪，其他物品都不接收，且非盟友不接收。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")

    ally_player = _StubPlayer()
    _ally(g_player, ally_player)
    knight = _StubUnit(ally_player, type_name="knight", unit_id="k",
                       receive_items=1, accepted_items=("knight_lance",),
                       accept_from=("ally",))

    lance = _StubItem("knight_lance")
    potion = _StubItem("health_potion")

    # 盟友骑士接收骑士枪
    assert knight.accepts_item(lance, giver) is True
    # 其他物品一律拒绝
    assert knight.accepts_item(potion, giver) is False

    # 同样配置但属于敌人/中立的骑士，不接收（关系不符）
    enemy_knight = _StubUnit(_StubPlayer(), type_name="knight", unit_id="ek",
                             receive_items=1, accepted_items=("knight_lance",),
                             accept_from=("ally",))
    assert enemy_knight.accepts_item(lance, giver) is False


def test_only_neutral_npc_peasant_accepts_pickaxe():
    """场景：只有中立NPC的农民接收镐头，其他物品都不接收，盟友给则拒绝。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")

    neutral_peasant = _StubUnit(_StubPlayer(neutral=True), type_name="peasant",
                                unit_id="np", receive_items=1,
                                accepted_items=("pickaxe",), accept_from=("neutral",))

    pickaxe = _StubItem("pickaxe")
    sword = _StubItem("sword")

    assert neutral_peasant.accepts_item(pickaxe, giver) is True
    assert neutral_peasant.accepts_item(sword, giver) is False

    # 同配置但属于盟友的农民：关系是 ally，不在 accept_from=neutral 内 → 拒绝
    ally_player = _StubPlayer()
    _ally(g_player, ally_player)
    ally_peasant = _StubUnit(ally_player, type_name="peasant", unit_id="ap",
                             receive_items=1, accepted_items=("pickaxe",),
                             accept_from=("neutral",))
    assert ally_peasant.accepts_item(pickaxe, giver) is False


def test_only_enemy_leader_accepts_secret_letter():
    """场景：只有敌对（非中立）首领接收密信，其他物品都不接收。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")

    enemy_leader = _StubUnit(_StubPlayer(neutral=False), type_name="leader",
                             unit_id="el", receive_items=1,
                             accepted_items=("secret_letter",), accept_from=("enemy",))

    letter = _StubItem("secret_letter")
    gold = _StubItem("gold_coin")

    assert enemy_leader.accepts_item(letter, giver) is True
    assert enemy_leader.accepts_item(gold, giver) is False

    # 中立首领（neutral=True）：关系是 neutral，不在 accept_from=enemy 内 → 拒绝
    neutral_leader = _StubUnit(_StubPlayer(neutral=True), type_name="leader",
                               unit_id="nl", receive_items=1,
                               accepted_items=("secret_letter",), accept_from=("enemy",))
    assert neutral_leader.accepts_item(letter, giver) is False


def test_accepted_items_supports_is_a_inheritance():
    """accepted_items 支持 is_a 继承：accepted_items potion 接收所有药水。"""
    npc = _StubUnit(_StubPlayer(neutral=True), unit_id="n", receive_items=1,
                    accepted_items=("potion",))
    health = _StubItem("health_potion", is_a=("potion",))
    mana = _StubItem("mana_potion", is_a=("potion",))
    sword = _StubItem("sword")

    assert npc.accepts_item(health) is True
    assert npc.accepts_item(mana) is True
    assert npc.accepts_item(sword) is False


def test_empty_whitelists_accept_anything_from_anyone():
    """白名单都为空时：任意物品、任意关系都接收（只要 receive_items=1）。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")
    npc = _StubUnit(_StubPlayer(neutral=True), unit_id="n", receive_items=1)

    assert npc.accepts_item(_StubItem("anything"), giver) is True


def test_give_respects_accept_from_relation():
    """端到端：给予者关系不符时，give 转移被拒绝。"""
    g_player = _StubPlayer()
    giver = _StubUnit(g_player, unit_id="g")
    # 只接收中立关系给予者交来的镐头
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="peasant", unit_id="np",
                    receive_items=1, accepted_items=("pickaxe",), accept_from=("ally",))
    pickaxe = _StubItem("pickaxe")
    giver.inventory.append(pickaxe)

    # giver 与 npc 是 neutral 关系（未结盟），accept_from=ally → 拒绝
    CreatureOrders.give(giver, pickaxe, npc)
    assert "order_impossible" in giver.notifications
    assert pickaxe in giver.inventory
    assert pickaxe not in npc.inventory


def test_accept_givers_restricts_giver_unit_type():
    """accept_givers：只有指定单位类型能交物品，其他单位即使背了物品也拒收。"""
    g_player = _StubPlayer()
    footman = _StubUnit(g_player, type_name="footman", unit_id="f1")
    knight = _StubUnit(g_player, type_name="knight", unit_id="k1")
    leader = _StubUnit(_StubPlayer(), type_name="npc_knight_leader", unit_id="boss",
                       receive_items=1, accepted_items=("secret_letter",),
                       accept_from=("enemy",), accept_givers=("footman",))
    letter = _StubItem("secret_letter")

    footman.inventory.append(letter)
    CreatureOrders.give(footman, letter, leader)
    assert letter not in footman.inventory
    assert letter in leader.inventory

    letter2 = _StubItem("secret_letter")
    knight.inventory.append(letter2)
    CreatureOrders.give(knight, letter2, leader)
    assert "order_impossible" in knight.notifications
    assert letter2 in knight.inventory
    assert letter2 not in leader.inventory


def test_accept_givers_supports_is_a_inheritance():
    """accept_givers knight 时，is_a knight 的单位也可交物品。"""
    g_player = _StubPlayer()
    escort = _StubUnit(g_player, type_name="npc_knight_escort", unit_id="e1",
                       is_a=("knight",))
    leader = _StubUnit(_StubPlayer(), unit_id="boss", receive_items=1,
                       accepted_items=("secret_letter",), accept_givers=("knight",))
    letter = _StubItem("secret_letter")
    escort.inventory.append(letter)

    assert leader.accepts_item(letter, escort) is True
    CreatureOrders.give(escort, letter, leader)
    assert letter in leader.inventory


def test_get_default_order_give_skips_wrong_giver_type():
    """右键默认操作：给予者类型不在 accept_givers 时不出现 give。"""
    g_player = _StubPlayer()
    knight = _StubUnit(g_player, type_name="knight", unit_id="k1")
    knight.player = g_player
    leader = _StubUnit(_StubPlayer(), unit_id="boss", receive_items=1,
                       accepted_items=("secret_letter",), accept_from=("enemy",),
                       accept_givers=("footman",))
    knight.inventory.append(_StubItem("secret_letter"))
    # 桩对象无完整 player.get_object_by_id；直接测 accepts_item 聚合逻辑
    assert not any(leader.accepts_item(it, knight) for it in knight.inventory)
    footman = _StubUnit(g_player, type_name="footman", unit_id="f1")
    footman.inventory.append(_StubItem("secret_letter"))
    assert any(leader.accepts_item(it, footman) for it in footman.inventory)


# ---------------------------------------------------------------------------
# 3. lang_find 触发器条件
# ---------------------------------------------------------------------------


def test_lang_and_requires_all_conditions():
    mark = _StubItem("treasure_opened_mark")
    square = types.SimpleNamespace(objects=[mark], name="1,1")
    world = _StubWorld([])
    world.grid = {"1,1": square, "0,0": types.SimpleNamespace(objects=[], name="0,0")}
    world.squares = [square]
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name
    assert t.lang_and([["find", "b2", "treasure_opened_mark"]]) is True
    assert t.lang_and([["find", "b2", "treasure_opened_mark"], ["not", ["find", "b2", "gold_coin"]]]) is True
    square.objects.append(_StubItem("gold_coin"))
    assert t.lang_and([["find", "b2", "treasure_opened_mark"], ["not", ["find", "b2", "gold_coin"]]]) is False


def test_find_requires_square_before_type():
    """find 须方格在前；反序 (find gold_coin b2) 只在默认方格查类型，会漏掉 b2（第20关 bug）。"""
    a1 = types.SimpleNamespace(objects=[], name="0,0")
    b2 = types.SimpleNamespace(
        objects=[_StubItem("treasure_opened_mark"), _StubItem("gold_coin")],
        name="1,1",
    )
    world = _StubWorld([])
    world.grid = {"0,0": a1, "1,1": b2}
    world.squares = [a1, b2]
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_find(["b2", "gold_coin"]) is True
    assert t.lang_find(["gold_coin", "b2"]) is False

    obj3 = [["find", "b2", "treasure_opened_mark"], ["not", ["find", "b2", "gold_coin"]]]
    assert t.lang_and(obj3) is False

    b2.objects = [o for o in b2.objects if o.type_name != "gold_coin"]
    assert t.lang_and(obj3) is True

    # 错误写法在 b2 仍有金币时也会误判为「地上无金币」
    b2.objects.append(_StubItem("gold_coin"))
    wrong_obj3 = [["find", "b2", "treasure_opened_mark"], ["not", ["find", "gold_coin", "b2"]]]
    assert t.lang_and(wrong_obj3) is True


def test_mystery_treasure_is_consumable_with_use_square():
    item = _StubItem("mystery_treasure")
    item.use_square = "b2"
    item.resource_rewards = [150, 0]
    item.equippable_as_weapon = 0
    item.equippable_as_armor = 0
    item.use_effect = None
    item.skills = ()
    item.buffs = ()
    item.is_weapon_item = False
    item.is_armor_item = False
    from soundrts.worlditem import Item

    assert Item.is_consumable_item.fget(item) is True


def test_use_square_item_skips_resource_rewards_on_pickup():
    from soundrts.worlditem import Item

    stored = []

    class _Player:
        def store(self, resource_type, amount):
            stored.append((resource_type, amount))

        def send_event(self, sender, event):
            pass

    class _Treasure(Item):
        type_name = "mystery_treasure"
        use_square = "b2"
        resource_rewards = [150, 0]

    item = _Treasure.__new__(_Treasure)
    item.resource_rewards = [150, 0]
    item.use_square = "b2"
    picker = types.SimpleNamespace(player=_Player())
    item.on_pickup(picker)
    assert stored == []


def test_use_item_order_requires_use_square():
    from soundrts.worldplayerbase.triggers import TriggersMixin
    from soundrts.worldunit.world_order import CreatureOrders

    treasure = _StubItem("mystery_treasure", item_id=7)
    treasure.use_square = "b2"
    treasure.resource_rewards = [150, 0]
    treasure.is_weapon_item = False
    treasure.is_armor_item = False
    treasure.move_to = lambda *a, **k: None
    treasure.delete = lambda: None
    treasure.unequip = lambda u, **kw: None

    b2 = types.SimpleNamespace(objects=[], name="1,1")
    a1 = types.SimpleNamespace(objects=[], name="0,0")
    world = _StubWorld([])
    world.grid = {"0,0": a1, "1,1": b2}
    world.squares = [a1, b2]
    world.schedule_after = lambda delay, fn: None

    player = TriggersMixin.__new__(TriggersMixin)
    player.world = world
    player.units = []

    unit = types.SimpleNamespace(
        place=a1,
        inventory=[treasure],
        player=player,
        notifications=[],
        world=world,
    )
    player.units = [unit]

    def _find(iid):
        return treasure if str(iid) == "7" else None

    unit._find_inventory_item = _find
    unit.use_consumable_item = lambda item: True
    unit.notify = lambda msg: unit.notifications.append(msg)

    CreatureOrders.use_item_order(unit, 7)
    assert "order_impossible" in unit.notifications

    unit.notifications.clear()
    unit.place = b2
    CreatureOrders.use_item_order(unit, 7)
    assert "order_impossible" not in unit.notifications
    assert treasure not in unit.inventory


def test_add_units_spawns_items_without_count_limit(monkeypatch):
    """add_units 生成 class item 时应走物品分支，不调用 check_count_limit。"""
    from soundrts.worlditem import Item
    from soundrts.worldplayerbase.triggers import TriggersMixin

    created = []

    class _GoldCoin(Item):
        type_name = "gold_coin"

        def __init__(self, place, x, y):
            self.place = place
            self.x = x
            self.y = y
            self.type_name = "gold_coin"
            created.append(self)

    square = types.SimpleNamespace(
        name="1,1",
        x=1000,
        y=1000,
        can_receive=lambda t: True,
        find_and_remove_meadow=lambda cls: (1000, 1000, None),
    )
    world = types.SimpleNamespace(grid={"1,1": square}, squares=[square])
    player = types.SimpleNamespace(world=world, units=[])
    t = TriggersMixin.__new__(TriggersMixin)
    t.world = world
    t.units = []
    t.upgrades = []
    t.send_voice_important = lambda *a, **k: None
    t._default_square_key = lambda: "1,1"
    t._normalize_square_token = TriggersMixin._normalize_square_token.__get__(t, TriggersMixin)
    t.check_count_limit = lambda name: (_ for _ in ()).throw(AssertionError("items must not check count_limit"))

    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.unit_class",
        lambda name: _GoldCoin if name == "gold_coin" else None,
    )
    monkeypatch.setattr(
        "soundrts.worldplayerbase.triggers.rules.get",
        lambda name, key: ["item"] if name == "gold_coin" and key == "class" else None,
    )

    t.lang_add_units(["b2", "3", "gold_coin"])
    assert len(created) == 3


def test_lang_do_runs_all_actions_in_order():
    """do 按顺序执行每个子动作（if 在条件成立时只执行第一个分支）。"""
    world = _StubWorld([])
    t = _make_triggers(world)
    calls = []

    t.lang_cut_scene = lambda args: calls.append("cut_scene")
    t.lang_remove_item = lambda args: calls.append("remove")
    t.lang_objective_complete = lambda args: calls.append("complete")

    t.lang_do([
        ["cut_scene", "7560"],
        ["remove_item", "mana_potion", "c3"],
        ["objective_complete", "1"],
    ])
    assert calls == ["cut_scene", "remove", "complete"]


def test_remove_item_destroys_inventory_on_square():
    """remove_item：从指定方格上的玩家单位库存移除并销毁物品。"""
    potion = _StubItem("mana_potion")
    peasant = _StubUnit(_StubPlayer(), type_name="peasant", unit_id="p1")
    peasant.inventory = [potion]
    peasant.presence = True
    deleted = []

    def _delete():
        deleted.append(potion)

    potion.delete = _delete
    potion.move_to = lambda *a, **k: None
    potion.unequip = lambda host: None

    c3 = types.SimpleNamespace(objects=[peasant], name="2,2")
    a1 = types.SimpleNamespace(objects=[], name="0,0")
    world = _StubWorld([peasant.player])
    world.grid = {"0,0": a1, "2,2": c3}
    world.squares = [a1]
    world.schedule_after = lambda ms, fn: fn()

    t = _make_triggers(world)
    t.units = [peasant]
    peasant.place = c3

    t.lang_remove_item(["mana_potion", "c3"])
    assert potion not in peasant.inventory
    assert deleted == [potion]

    peasant.inventory = [_StubItem("mana_potion")]
    peasant.place = a1
    t.lang_remove_item(["mana_potion", "c3"])
    assert len(peasant.inventory) == 1


def test_has_brought_item_requires_unit_on_square_with_item():
    """has_brought_item：单位在目标格且库存有物品；空手到达或物品在别格均不成立。"""
    potion = _StubItem("mana_potion")
    peasant = _StubUnit(_StubPlayer(), type_name="peasant", unit_id="p1")
    peasant.inventory = [potion]
    peasant.presence = True

    c3 = types.SimpleNamespace(objects=[peasant], name="2,2")
    a1 = types.SimpleNamespace(objects=[], name="0,0")
    world = _StubWorld([peasant.player])
    world.grid = {"0,0": a1, "2,2": c3}
    world.squares = [a1]

    t = _make_triggers(world)
    t.units = [peasant]
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_has_brought_item(["c3", "mana_potion"]) is True

    peasant.inventory = []
    assert t.lang_has_brought_item(["c3", "mana_potion"]) is False

    peasant.inventory = [potion]
    c3.objects = []
    a1.objects = [peasant]
    assert t.lang_has_brought_item(["c3", "mana_potion"]) is False


def test_lang_find_square_must_come_before_type():
    """find 按顺序解析：先更新方格，再在该方格查找类型。"""
    item = _StubItem("mana_potion")
    empty = types.SimpleNamespace(objects=[], name="0,0")
    square = types.SimpleNamespace(objects=[item], name="2,2")
    world = _StubWorld([])
    world.grid = {"0,0": empty, "2,2": square}
    world.squares = [empty]
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_find(["c3", "mana_potion"]) is True
    assert t.lang_find(["mana_potion", "c3"]) is False


# ---------------------------------------------------------------------------
# 4. lang_npc_has_item 触发器条件
# ---------------------------------------------------------------------------


def test_npc_has_item_true_via_received_items():
    npc_player = _StubPlayer(neutral=True)
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    npc.received_items = {"health_potion"}
    world = _StubWorld([npc_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_item(["oldman", "health_potion"]) is True
    # 也可用单位 id 选择
    assert t.lang_npc_has_item(["n1", "health_potion"]) is True


def test_npc_has_item_true_via_live_inventory():
    npc_player = _StubPlayer(neutral=True)
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    npc.inventory.append(_StubItem("health_potion"))
    world = _StubWorld([npc_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_item(["oldman", "health_potion"]) is True


def test_npc_has_item_false_for_wrong_item_or_npc():
    npc_player = _StubPlayer(neutral=True)
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    npc.received_items = {"health_potion"}
    world = _StubWorld([npc_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_item(["oldman", "mana_potion"]) is False
    assert t.lang_npc_has_item(["blacksmith", "health_potion"]) is False
    assert t.lang_npc_has_item(["oldman"]) is False  # 参数不足


def test_npc_has_item_square_disambiguation():
    npc_player = _StubPlayer(neutral=True)
    npc_a = _StubUnit(npc_player, type_name="oldman", unit_id="a", place="3,4")
    npc_b = _StubUnit(npc_player, type_name="oldman", unit_id="b", place="5,6")
    npc_a.received_items = {"health_potion"}
    world = _StubWorld([npc_player])
    # 让 _normalize_square_token 能识别这两个键
    world.grid = {"3,4": object(), "5,6": object()}
    t = _make_triggers(world)

    # 限定到 a 所在方格 → 命中
    assert t.lang_npc_has_item(["oldman", "health_potion", "3,4"]) is True
    # 限定到 b 所在方格（b 没收到物品）→ 不命中
    assert t.lang_npc_has_item(["oldman", "health_potion", "5,6"]) is False


def test_npc_has_item_map_select_index():
    """序号格式：仅第 N 个单位收到物品时成立。"""
    npc_player = _StubPlayer(neutral=True)
    for idx, uid in enumerate(("f1", "f2", "f3"), start=1):
        u = _StubUnit(npc_player, type_name="footman", unit_id=uid)
        u.map_select_square = "1,1"
        u.map_select_type = "footman"
        u.map_select_index = idx
        if idx == 3:
            u.received_items = {"health_potion"}
    world = _StubWorld([npc_player])
    world.grid = {"1,1": object()}
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_npc_has_item(["1,1", "3", "footman", "health_potion"]) is True
    assert t.lang_npc_has_item(["1,1", "1", "footman", "health_potion"]) is False
    assert t.lang_npc_has_item(["1,1", "2", "footman", "health_potion"]) is False


def test_npc_has_item_global_index():
    """全局序号：仅第 N 个刷出单位收到物品时成立（与方格无关）。"""
    npc_player = _StubPlayer(neutral=True)
    for idx, uid in enumerate(("f1", "f2", "f3"), start=1):
        u = _StubUnit(npc_player, type_name="quest_npc", unit_id=uid)
        u.map_select_global_index = idx
        if idx == 3:
            u.received_items = {"short_sword"}
    world = _StubWorld([npc_player])
    world.grid = {"1,1": object(), "5,6": object()}
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_npc_has_item(["3", "quest_npc", "short_sword"]) is True
    assert t.lang_npc_has_item(["1", "quest_npc", "short_sword"]) is False
    assert t.lang_npc_has_item(["2", "quest_npc", "short_sword"]) is False


def test_npc_has_item_map_select_index_survives_move():
    """序号按刷出位置编号，单位移动后仍可识别。"""
    npc_player = _StubPlayer(neutral=True)
    u3 = _StubUnit(npc_player, type_name="footman", unit_id="f3", place="5,6")
    u3.map_select_square = "1,1"
    u3.map_select_type = "footman"
    u3.map_select_index = 3
    u3.received_items = {"health_potion"}
    world = _StubWorld([npc_player])
    world.grid = {"1,1": object(), "5,6": object()}
    t = _make_triggers(world)
    t.check_type = lambda o, name: getattr(o, "type_name", None) == name

    assert t.lang_npc_has_item(["1,1", "3", "footman", "health_potion"]) is True


# ---------------------------------------------------------------------------
# 4. 测试地图配套的 rules.txt 物品/NPC 定义解析
# ---------------------------------------------------------------------------

_RULES_SNIPPET = """
def knight_lance
class item

def pickaxe
class item

def wand
class item

def npc_knight
class soldier
hp_max 200
inventory_capacity 3
receive_items 1
accepted_items knight_lance
accept_from neutral

def npc_peasant
class worker
hp_max 100
inventory_capacity 3
receive_items 1
accepted_items pickaxe
accept_from ally

def npc_mage
class soldier
hp_max 100
inventory_capacity 3
receive_items 1
accepted_items wand
accept_from enemy
"""


def _load_rules_snippet():
    """用独立的 Rules 实例加载片段，避免污染全局 rules 单例。"""
    from soundrts.definitions import Rules
    r = Rules()
    r.load(_RULES_SNIPPET)
    return r


def _rules_or_skip():
    try:
        return _load_rules_snippet()
    except Exception as exc:  # pragma: no cover - 取决于测试环境
        pytest.skip(f"无法在测试环境加载 rules 片段：{exc}")


def test_demo_rules_npc_knight_accepts_neutral_lance():
    r = _rules_or_skip()
    kn = r.unit_class("npc_knight")
    assert kn is not None
    assert int(kn.receive_items) == 1
    assert list(kn.accepted_items) == ["knight_lance"]
    assert list(kn.accept_from) == ["neutral"]


def test_demo_rules_npc_peasant_accepts_ally_pickaxe():
    r = _rules_or_skip()
    pe = r.unit_class("npc_peasant")
    assert pe is not None
    assert int(pe.receive_items) == 1
    assert list(pe.accepted_items) == ["pickaxe"]
    assert list(pe.accept_from) == ["ally"]


def test_demo_rules_npc_mage_accepts_enemy_wand():
    r = _rules_or_skip()
    mg = r.unit_class("npc_mage")
    assert mg is not None
    assert int(mg.receive_items) == 1
    assert list(mg.accepted_items) == ["wand"]
    assert list(mg.accept_from) == ["enemy"]


def test_demo_rules_items_are_item_subclasses():
    from soundrts.worlditem import Item
    r = _rules_or_skip()
    for item_name in ("knight_lance", "pickaxe", "wand"):
        cls = r.unit_class(item_name)
        assert cls is not None, item_name
        assert issubclass(cls, Item), item_name


# ---------------------------------------------------------------------------
# 5. 三张测试地图存在且配置自洽
# ---------------------------------------------------------------------------

# 演示地图在雷诺传战役（The Legend of Raynor）中，按关卡序号命名：
#   15.txt -> 给中立骑士骑士枪   (npc_knight / knight_lance)
#   14.txt -> 给盟友农民镐头     (npc_peasant / pickaxe)
#   16.txt -> 给敌方法师魔杖     (npc_mage / wand)
_CAMPAIGN_DIR = (
    Path(__file__).resolve().parents[2] / "res" / "single" / "The Legend of Raynor"
)

_DEMO_MAPS = {
    "15.txt": ("npc_knight", "knight_lance"),
    "14.txt": ("npc_peasant", "pickaxe"),
    "16.txt": ("npc_mage", "wand"),
}

@pytest.mark.parametrize("fname,expected", list(_DEMO_MAPS.items()))
def test_demo_maps_exist_and_are_consistent(fname, expected):
    npc, item = expected
    path = _CAMPAIGN_DIR / fname
    assert path.exists(), f"缺少测试地图 {fname}"
    text = path.read_text(encoding="utf-8")
    # 地图放置了任务物品
    assert f"{item} a1" in text
    # 放置了对应NPC
    assert f"{npc}" in text
    # 触发器检测该NPC是否收到该物品
    assert f"(npc_has_item {npc} {item})" in text
    # 完成目标
    assert "(objective_complete 1)" in text


def test_allied_peasant_map_sets_alliance():
    """盟友地图必须把玩家与 computer1 设为同盟，否则关系不是 ally。"""
    text = (_CAMPAIGN_DIR / "14.txt").read_text(encoding="utf-8")
    assert "(alliance 1)" in text
    assert "trigger player1 (timer 0) (alliance 1)" in text
    # 单人会剥掉 player1 联盟触发器，须显式绑定 player1+computer1
    assert "trigger computer1 (timer 0) (alliance 1 player1 computer1)" in text


def test_chapter_28_map_select_index_triggers():
    """第28章：演示 killed_target / npc_has_item 的序号选择符。"""
    text = (_CAMPAIGN_DIR / "28.txt").read_text(encoding="utf-8")
    assert "title 4271 3028" in text
    assert "computer_only 0 0 ad30 6 demo_marker_footman" in text
    assert "computer_only 0 0 neutral o15 6 quest_npc" in text
    assert "(killed_target 1 demo_marker_footman enemy)" in text
    assert "(killed_target 2 demo_marker_footman enemy)" in text
    assert "(killed_target 3 demo_marker_footman enemy)" in text
    assert "(cut_scene 7606) (defeat)" in text
    assert "(npc_has_item 3 quest_npc short_sword)" in text
    assert "(objective_complete 1)" in text
    assert "(objective_complete 2)" in text


def test_chapter_23_drop_delivery_triggers():
    """第23章：拾取后须在补给站丢弃 war_supplies 才能完成目标2。"""
    text = (_CAMPAIGN_DIR / "23.txt").read_text(encoding="utf-8")
    assert "war_supplies d1" in text
    assert "(has_item war_supplies) (objective_complete 1)" in text
    assert "(find g7 war_supplies) (do (cut_scene 7573) (remove_ground_item g7 war_supplies) (objective_complete 2))" in text


def test_chapter_22_map_triggers_are_single_line():
    """第22章触发器须单行解析（owner + condition + action）。"""
    text = (_CAMPAIGN_DIR / "22.txt").read_text(encoding="utf-8")
    assert "sealed_treasure g7" in text
    assert "(has_item sealed_treasure) (objective_complete 1)" in text
    assert "(find d4 sealed_treasure) (do (cut_scene 7567)" in text
    assert "(remove_ground_item d4 sealed_treasure)" in text
    assert "(and (find d4 treasure_opened_mark) (not (find d4 gold_coin))) (objective_complete 3)" in text
    for line in text.splitlines():
        if line.strip().startswith("trigger player1"):
            assert line.count("trigger ") == 1
            parts = line.strip().split(" ", 2)
            assert len(parts) >= 3, f"broken trigger line: {line!r}"


def test_chapter_19_cut_scene_before_objective_complete():
    """第19章：交枪须先播 7540 再完成目标2，避免最后一项目标直接 victory 跳过剧情。"""
    text = (_CAMPAIGN_DIR / "19.txt").read_text(encoding="utf-8")
    assert (
        "(npc_has_item npc_wandering_knight knight_lance d4) "
        "(do (cut_scene 7540) (objective_complete 2))"
    ) in text
    assert "(npc_has_item npc_wandering_knight knight_lance) (cut_scene 7540)" not in text


def test_wandering_knight_only_accepts_knight_lance():
    """第19章流浪骑士：accepted_items 白名单仅含骑士枪，拒绝力量之剑等其它物品。"""
    rules_text = (_CAMPAIGN_DIR / "rules.txt").read_text(encoding="utf-8")
    assert "accepted_items knight_lance\naccept_from neutral" in rules_text.replace(
        "\r\n", "\n"
    )
    assert "accepted_items knight_lance power_sword" not in rules_text

    giver = _StubUnit(_StubPlayer(), unit_id="g")
    knight = _StubUnit(
        _StubPlayer(neutral=True),
        type_name="npc_wandering_knight",
        unit_id="wk",
        receive_items=1,
        accepted_items=("knight_lance",),
        accept_from=("neutral",),
    )
    assert knight.accepts_item(_StubItem("knight_lance"), giver) is True
    assert knight.accepts_item(_StubItem("power_sword"), giver) is False
