"""测试两块新功能：

1. ``soundrts/definitions.py``：重复的 string-list 属性行改为 **追加**，
   不再互相覆盖。
   起因：Joan of Arc 的 ``rules.txt`` 里大教堂写了三行 ``accept_from``
   （``self`` / ``ally`` / ``neutral``），解析后只剩最后一行的
   ``['neutral']`` —— 前两行被静默冲掉了。

2. ``soundrts/worldplayerbase/triggers.py``：新增计数型触发器条件
   ``(npc_has_items <NPC> <物品> <数量> [方格])``，用于"送齐三件圣物"
   这类收集型目标（旧的 ``npc_has_item`` 只判类型，交 1 件即成立）。

3. ``soundrts/worldunit/world_order.py``：``give`` 动作累计交付件数
   （``received_item_counts``）。

为避免拉起 pygame/locale 等 client-side 重依赖，这里沿用
``test_give_item_to_npc.py`` 的最小化对象注入式测试风格。
"""
from __future__ import annotations

import types
from pathlib import Path

import pytest

# 解开 worldunit 包的循环导入（与现有 neutral 系列测试一致）
import soundrts.worldunit  # noqa: F401

from soundrts.definitions import Rules
from soundrts.worldunit.world_order import CreatureOrders
from soundrts.worldunit.worldcreature import Creature
from soundrts.worldplayerbase.triggers import TriggersMixin


REPO_ROOT = Path(__file__).resolve().parents[2]
JOAN = REPO_ROOT / "mods/aoe2/single/Joan of Arc"


# ---------------------------------------------------------------------------
# 最小化桩对象
# ---------------------------------------------------------------------------


class _StubItem:
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
    """模拟一个能持有物品的单位（giver 或 NPC）。"""

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


def _ally(giver_player, receiver_player):
    if receiver_player not in giver_player.allied:
        giver_player.allied.append(receiver_player)
    if giver_player not in receiver_player.allied:
        receiver_player.allied.append(giver_player)


# ---------------------------------------------------------------------------
# 1. string-list 属性跨行追加（不再覆盖）
# ---------------------------------------------------------------------------


def test_repeated_string_list_lines_append_not_overwrite():
    """重复的 string-list 行必须累加，而不是后者覆盖前者。"""
    rules = Rules()
    rules.read("""
def test_npc
class soldier
receive_items 1
accepted_items relic
accept_from self
accept_from ally
accept_from neutral
""")
    assert rules.get("test_npc", "accept_from") == ["self", "ally", "neutral"]
    assert rules.get("test_npc", "accepted_items") == ["relic"]


def test_repeated_string_list_lines_deduplicate():
    """完全相同的值重复出现不应让列表膨胀（语义是"任一匹配即可"）。"""
    rules = Rules()
    rules.read("""
def test_npc
class soldier
rdg_targets ground air
rdg_targets ground air
""")
    assert rules.get("test_npc", "rdg_targets") == ["ground", "air"]


def test_single_string_list_line_still_works():
    """单行写法不受影响。"""
    rules = Rules()
    rules.read("""
def test_npc
class soldier
accept_from ally
""")
    assert rules.get("test_npc", "accept_from") == ["ally"]


def test_joan_of_arc_rules_keep_all_three_accept_from():
    """Joan of Arc 的两个接收型 NPC 都要保留三行 accept_from。"""
    text = (JOAN / "rules.txt").read_text(encoding="utf-8")
    for name in ("npc_dauphin", "npc_reims_cathedral"):
        assert f"def {name}" in text, name
    # 三行 accept_from 必须都在文件里
    assert text.count("accept_from self") >= 2
    assert text.count("accept_from ally") >= 2
    assert text.count("accept_from neutral") >= 2


def test_string_list_append_does_not_break_vs_pair_lists():
    """``*_vs`` 是"键值对"列表，合并语义与 string-list 不同，保持原样。

    注意：``read()`` 阶段它仍是扁平的 ``[类型, 数值, 类型, 数值, ...]``；
    转换成 dict 发生在 ``interpret_vs_attributes()``（单位类解释阶段）。
    """
    rules = Rules()
    rules.read("""
def test_unit
class soldier
mdg_vs building 150
mdg_vs siege_unit 40
""")
    assert rules.get("test_unit", "mdg_vs") == [
        "building", "150", "siege_unit", "40",
    ]


# ---------------------------------------------------------------------------
# 2. give() 累计交付件数
# ---------------------------------------------------------------------------


def test_give_records_received_item_counts():
    """每次 give 都要把件数累加到 received_item_counts。"""
    p = _StubPlayer()
    giver = _StubUnit(p, type_name="monk", unit_id="g")
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="oldman", unit_id="n1")

    for i in range(3):
        relic = _StubItem("relic", item_id=i)
        giver.inventory.append(relic)
        CreatureOrders.give(giver, relic, npc)

    assert npc.received_item_counts == {"relic": 3}
    # 旧的集合语义不变
    assert npc.received_items == {"relic"}


def test_give_counts_per_item_type():
    """不同类型的物品分别计数。"""
    p = _StubPlayer()
    giver = _StubUnit(p, type_name="monk", unit_id="g")
    npc = _StubUnit(_StubPlayer(neutral=True), type_name="oldman", unit_id="n1")

    for i in range(2):
        relic = _StubItem("relic", item_id=i)
        giver.inventory.append(relic)
        CreatureOrders.give(giver, relic, npc)

    sword = _StubItem("sword", item_id=99)
    giver.inventory.append(sword)
    CreatureOrders.give(giver, sword, npc)

    assert npc.received_item_counts == {"relic": 2, "sword": 1}


# ---------------------------------------------------------------------------
# 3. npc_has_items 计数触发器
# ---------------------------------------------------------------------------


def _deliver(npc, giver, type_name, qty, start_id=0):
    for i in range(qty):
        item = _StubItem(type_name, item_id=start_id + i)
        giver.inventory.append(item)
        CreatureOrders.give(giver, item, npc)


def test_npc_has_items_requires_the_full_count():
    """交 1、2 件都不成立，交够 N 件才成立。"""
    npc_player = _StubPlayer(neutral=True)
    giver_player = _StubPlayer()
    npc = _StubUnit(npc_player, type_name="npc_reims_cathedral", unit_id="n1")
    giver = _StubUnit(giver_player, type_name="monk", unit_id="g")
    world = _StubWorld([npc_player, giver_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "3"]) is False

    _deliver(npc, giver, "relic", 1)
    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "3"]) is False
    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "1"]) is True

    _deliver(npc, giver, "relic", 1, start_id=100)
    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "3"]) is False
    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "2"]) is True

    _deliver(npc, giver, "relic", 1, start_id=200)
    assert t.lang_npc_has_items(["npc_reims_cathedral", "relic", "3"]) is True


def test_npc_has_items_differs_from_npc_has_item():
    """旧触发器交 1 件即成立，新触发器要求计数——两者语义确实不同。"""
    npc_player = _StubPlayer(neutral=True)
    giver_player = _StubPlayer()
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    giver = _StubUnit(giver_player, type_name="monk", unit_id="g")
    world = _StubWorld([npc_player, giver_player])
    t = _make_triggers(world)

    _deliver(npc, giver, "relic", 1)

    assert t.lang_npc_has_item(["oldman", "relic"]) is True
    assert t.lang_npc_has_items(["oldman", "relic", "3"]) is False


def test_npc_has_items_counts_inventory_when_never_given():
    """NPC 开局就带着 relic（没走过 give）也能被计入。"""
    npc_player = _StubPlayer(neutral=True)
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    npc.inventory.append(_StubItem("relic", item_id=1))
    npc.inventory.append(_StubItem("relic", item_id=2))
    world = _StubWorld([npc_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_items(["oldman", "relic", "2"]) is True
    assert t.lang_npc_has_items(["oldman", "relic", "3"]) is False


def test_npc_has_items_does_not_double_count_delivered_items():
    """give 之后物品进了目标库存，计数不得把同一件数两次。"""
    npc_player = _StubPlayer(neutral=True)
    giver_player = _StubPlayer()
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    giver = _StubUnit(giver_player, type_name="monk", unit_id="g")
    world = _StubWorld([npc_player, giver_player])
    t = _make_triggers(world)

    _deliver(npc, giver, "relic", 1)

    assert npc.received_item_counts["relic"] == 1
    assert len(npc.inventory) == 1
    # 一件不能被算成两件
    assert t.lang_npc_has_items(["oldman", "relic", "2"]) is False


def test_npc_has_items_rejects_bad_arguments():
    """参数不足、数量非法、物品/NPC 不匹配都返回 False。"""
    npc_player = _StubPlayer(neutral=True)
    npc = _StubUnit(npc_player, type_name="oldman", unit_id="n1")
    world = _StubWorld([npc_player])
    t = _make_triggers(world)

    assert t.lang_npc_has_items(["oldman"]) is False
    assert t.lang_npc_has_items(["oldman", "relic"]) is False
    assert t.lang_npc_has_items(["oldman", "relic", "0"]) is False
    assert t.lang_npc_has_items(["oldman", "relic", "-1"]) is False
    assert t.lang_npc_has_items(["oldman", "relic", "abc"]) is False
    assert t.lang_npc_has_items(["oldman", "sword", "1"]) is False
    assert t.lang_npc_has_items(["no_such_npc", "relic", "1"]) is False


def test_npc_has_items_respects_square_filter():
    """方格参数用于区分同名 NPC。"""
    npc_player = _StubPlayer(neutral=True)
    giver_player = _StubPlayer()
    a = _StubUnit(npc_player, type_name="oldman", unit_id="a", place="3,4")
    b = _StubUnit(npc_player, type_name="oldman", unit_id="b", place="5,6")
    giver = _StubUnit(giver_player, type_name="monk", unit_id="g")
    world = _StubWorld([npc_player, giver_player])
    world.grid = {"3,4": object(), "5,6": object()}
    t = _make_triggers(world)

    _deliver(a, giver, "relic", 2)

    assert t.lang_npc_has_items(["oldman", "relic", "2", "3,4"]) is True
    assert t.lang_npc_has_items(["oldman", "relic", "2", "5,6"]) is False


# ---------------------------------------------------------------------------
# 4. Joan of Arc 第 4 章使用计数触发器
# ---------------------------------------------------------------------------


def test_ch4_uses_counting_trigger_for_three_relics():
    """第 4 章目标 1 必须要求 3 件圣物，而不是 1 件。"""
    text = (JOAN / "4.txt").read_text(encoding="utf-8")
    assert "(npc_has_items npc_reims_cathedral relic 3 c5)" in text, (
        "ch4 goal 1 must use the counting trigger with 3 relics"
    )
    # 旧的不计数写法不该再出现在目标 1 上
    assert "(npc_has_item npc_reims_cathedral relic c5)" not in text


def test_ch4_still_places_three_relics():
    """地图上仍然放置 3 件圣物（b3 / d3 / e4）。"""
    text = (JOAN / "4.txt").read_text(encoding="utf-8")
    for sq in ("b3", "d3", "e4"):
        assert f"relic {sq}" in text, f"missing relic at {sq}"