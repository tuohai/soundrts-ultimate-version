"""地面物品与狩猎尸体的消失时限。

背景：
  * 动物（鹿/羊/野猪）被杀死后在地上留下可开采的食物尸体
    （``food_carcass`` / ``food_livestock``）。这些尸体以前**永远不会消失**，
    越积越多，地图上全是肉堆。
  * 掉在地上的物品（宝物、金币、生产出来的物品）也一样**永远不会消失**。

新增两个规则关键字（单位：秒；0 = 永不消失，保持旧行为）：

  * ``deposit_decay`` —— 矿床/狩猎尸体生成后多久消失。
  * ``item_decay``    —— 物品掉到地上后多久消失（只在**地上**计时；
    捡进背包就停止计时）。

实现要点：
  * ``Item`` 之前根本没有 ``update`` / ``slow_update``，所以它压根没进
    ``world.active_objects``，世界循环根本不会更新它 —— 这就是地上的物品
    永远不消失的根因。现在补上这两个方法，物品才会被登记进活跃列表。
"""

from __future__ import annotations

import types
from pathlib import Path

from soundrts.lib.nofloat import PRECISION

ROOT = Path(__file__).resolve().parents[2]


def _source(*path_parts):
    return ROOT.joinpath(*path_parts).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 规则关键字
# ---------------------------------------------------------------------------
def test_new_keywords_registered_in_definitions():
    src = _source("soundrts", "definitions.py")
    assert '"deposit_decay"' in src
    assert '"item_decay"' in src


def test_deposit_decay_parsed_as_seconds():
    """``deposit_decay`` 在规则里写秒，加载后是毫秒。"""
    from soundrts.worldresource import Deposit

    d = {"deposit_decay": 120}
    Deposit.interpret(d)
    assert d["deposit_decay"] == 120 * PRECISION


def test_item_decay_parsed_as_seconds():
    """``item_decay`` 在规则里写秒，加载后是毫秒。"""
    from soundrts.worlditem import Item

    d = {"item_decay": 300}
    Item.interpret(d)
    assert d["item_decay"] == 300 * PRECISION


def test_decay_keywords_default_to_never_disappear():
    """没写就是 0 = 永不消失（保持旧行为）。"""
    from soundrts.worlditem import Item
    from soundrts.worldresource import Deposit

    assert Deposit.deposit_decay == 0
    assert Item.item_decay == 0


# ---------------------------------------------------------------------------
# 狩猎尸体（矿床）
# ---------------------------------------------------------------------------
class _FakePlace:
    def __init__(self, world):
        self.world = world
        self.objects = []
        self.x = 0
        self.y = 0
        self.is_inside_place = False
        self.neighbors = []

    def enter(self, o):
        self.objects.append(o)

    def leave(self, o):
        if o in self.objects:
            self.objects.remove(o)

    def add(self, o):
        pass

    def remove(self, o):
        pass

    def would_collide(self, *a):
        return False

    def find_free_space_for(self, *a, **k):
        return 0, 0

    @property
    def subsquares(self):
        return ()


def _make_world(now=0):
    return types.SimpleNamespace(
        time=now,
        map_deposit_capacity=[0, 0, 0, 0],
        unregister_entity=lambda o: None,
    )


def _make_deposit_cls(decay_ms):
    from soundrts.worldresource import Deposit

    class _D(Deposit):
        resource_type = "resource3"
        deposit_decay = decay_ms

    return _D


def test_hunt_carcass_gets_a_time_limit():
    """狩猎尸体生成时就带上消失时限。"""
    cls = _make_deposit_cls(120 * PRECISION)
    world = _make_world(now=5000)
    place = _FakePlace(world)
    deposit = cls(place, "40")
    assert deposit.time_limit == 5000 + 120 * PRECISION


def test_deposit_without_decay_never_expires():
    """没配 ``deposit_decay`` 的矿床不设时限（地图金矿等不受影响）。"""
    cls = _make_deposit_cls(0)
    world = _make_world(now=5000)
    place = _FakePlace(world)
    deposit = cls(place, "40")
    assert deposit.time_limit is None


def test_deposit_slow_update_deletes_it_when_expired():
    """到期后尸体自动消失。"""
    cls = _make_deposit_cls(10 * PRECISION)
    world = _make_world(now=0)
    place = _FakePlace(world)
    deposit = cls(place, "40")
    world.time = 9 * PRECISION
    deposit.slow_update()
    assert deposit.place is place, "还没到期时不能消失"
    world.time = 11 * PRECISION
    deposit.slow_update()
    assert deposit.place is None, "到期后必须消失"


# ---------------------------------------------------------------------------
# 地上的物品
# ---------------------------------------------------------------------------
def _make_item_cls(decay_ms):
    from soundrts.worlditem import Item

    class _I(Item):
        item_decay = decay_ms
        type_name = "test_item"

    return _I


def test_item_has_update_methods():
    """``Item`` 必须有 update / slow_update。

    没有 ``update`` 的话 ``world.register_entity`` 不会把它放进
    ``active_objects``，世界循环压根不会更新它 —— 物品就永远不消失。
    """
    from soundrts.worlditem import Item

    assert hasattr(Item, "update")
    assert hasattr(Item, "slow_update")


def test_item_ground_decay_counts_down_only_on_ground():
    """掉到地上开始计时，捡进背包停止计时。"""
    cls = _make_item_cls(60 * PRECISION)
    world = _make_world(now=1000)
    place = _FakePlace(world)
    item = cls(place, 0, 0)

    item.start_ground_decay()
    assert item._ground_decay_deadline == 1000 + 60 * PRECISION

    item.stop_ground_decay()
    assert item._ground_decay_deadline is None


def test_item_expires_when_deadline_passes():
    """到期后地上的物品自动消失。"""
    cls = _make_item_cls(10 * PRECISION)
    world = _make_world(now=0)
    place = _FakePlace(world)
    item = cls(place, 0, 0)
    item.start_ground_decay()

    world.time = 9 * PRECISION
    item.slow_update()
    assert item.place is place, "还没到期时不能消失"

    world.time = 11 * PRECISION
    item.slow_update()
    assert item.place is None, "到期后必须消失"


def test_item_without_decay_never_expires():
    """没配 ``item_decay`` 的物品不计时（永远留在地上）。"""
    cls = _make_item_cls(0)
    world = _make_world(now=0)
    place = _FakePlace(world)
    item = cls(place, 0, 0)
    item.start_ground_decay()
    world.time = 10 ** 9
    item.slow_update()
    assert item.place is place


def test_drop_starts_ground_decay_and_pickup_stops_it():
    """drop 开始计时，pickup 停止计时。"""
    from soundrts.worldunit.world_order import CreatureOrders

    cls = _make_item_cls(45 * PRECISION)
    world = _make_world(now=0)
    place = _FakePlace(world)
    item = cls(place, 0, 0)

    unit = types.SimpleNamespace(
        inventory=[],
        place=place,
        x=0,
        y=0,
        world=world,
        basic_skills=(),
        orders=[],
        notify=lambda *a, **k: None,
        on_win_fight=lambda: None,
    )
    unit.inventory.append(item)

    CreatureOrders.drop(unit, item)
    assert item._ground_decay_deadline == 45 * PRECISION, "drop 后要开始计时"

    item.stop_ground_decay()
    assert item._ground_decay_deadline is None


def test_pickup_stops_ground_decay():
    """捡进背包后停止计时（物品在背包里不会消失）。"""
    from soundrts.worldunit.world_order import CreatureOrders

    cls = _make_item_cls(45 * PRECISION)
    world = _make_world(now=0)
    place = _FakePlace(world)
    item = cls(place, 0, 0)
    item.start_ground_decay()

    unit = types.SimpleNamespace(
        inventory=[],
        place=place,
        x=0,
        y=0,
        world=world,
        basic_skills=(),
        orders=[],
        notify=lambda *a, **k: None,
        on_win_fight=lambda: None,
    )

    CreatureOrders.pickup(unit, item)
    assert item._ground_decay_deadline is None, "捡进背包后不能继续计时"
    assert item in unit.inventory


# ---------------------------------------------------------------------------
# 各 mod 规则里的实际取值
# ---------------------------------------------------------------------------
def test_aoe2_hunt_carcasses_have_a_decay():
    """狩猎尸体设了时限（它们不是战役目标，只是可采集的肉堆）。"""
    text = _source("mods", "aoe2", "rules.txt")
    for name in ("food_carcass", "food_livestock"):
        block = text.split(f"def {name}", 1)[1].split("\ndef ", 1)[0]
        assert "deposit_decay" in block, f"{name} 必须设置消失时限"


def test_aoe2_relic_never_expires():
    """**帝国 2 的圣物不能有时限** —— 战役里圣物必须一直留在地上，
    否则玩家还没赶到圣物就消失了，战役无法通过。"""
    text = _source("mods", "aoe2", "rules.txt")
    block = text.split("def relic", 1)[1].split("\ndef ", 1)[0]
    assert "item_decay" not in block, "relic 绝不能设置 item_decay"


def test_campaign_items_never_expire():
    """战役会用到的物品（宝物/金币）不能有时限。

    《The Legend of Raynor》第 12 章要求把 ``gold_coin`` 交给商人，
    第 22 章要求地上还剩着 ``gold_coin``；物品到期消失战役就通不过。
    """
    text = _source("res", "rules.txt")
    for name in ("treasure_chest", "gold_pile", "gold_coin"):
        block = text.split(f"def {name}", 1)[1].split("\ndef ", 1)[0]
        assert "item_decay" not in block, f"{name} 不能设置 item_decay"
