# -*- coding: utf-8 -*-
"""审计：1.5.2.5 — 狩猎尸体与地上物品的消失时限 + 牲口死亡的统计与播报。

1.5.2.5 发布的内容是：
  * 新增 ``deposit_decay``：动物尸体（鹿 / 羊 / 野猪）留地一段时间后消失；
  * 新增 ``item_decay``：掉在地上的物品一段时间后消失，捡进背包即停止计时；
  * 修复 ``Item`` 类缺少 ``update`` / ``slow_update`` —— 地上的物品以前根本
    不会被登记进 ``active_objects``，所以永远不会被世界循环更新；
  * 修复：归属自己的羊被播报成「阵亡」、杀掉一只羊被算成「消灭了敌人」；
  * 帝国 2 的 ``relic`` 与战役物品（``gold_coin`` / ``treasure_chest`` /
    ``gold_pile`` ）故意**没有**时限，否则战役通不过。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧与
模组数据侧确实如此。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.5 段落里被点名。
_TOPICS = (
    # 狩猎尸体与地上物品的时限
    "deposit_decay",
    "item_decay",
    "class deposit",
    "class item",
    # 地上的物品以前根本不会被更新
    "slow_update",
    "active_objects",
    # 战役物品不得有时限
    "relic",
    "gold_coin",
    "treasure_chest",
    "gold_pile",
    # 引擎与模组文件
    "soundrts/worldresource.py",
    "soundrts/worlditem.py",
    "soundrts/worldunit/world_order.py",
    "soundrts/worldunit/world_status_update.py",
    "mods/aoe2/rules.txt",
    "res/rules.txt",
    "soundrts/tests/test_ground_item_decay.py",
    # 牲口死亡的统计与播报
    "test_livestock_kill_stats.py",
    "test_livestock_death_announcement.py",
    "soundrts/clientgameentity/events.py",
    "soundrts/clientgame/game_unit_control.py",
    "soundrts/worldunit/worldcreature.py",
    # 敌人刷新（RPG 式怪物复活）
    "respawn_time",
    "respawn",
    "computer_only",
    "is_revivable",
    "revival_time",
    "soundrts/world_respawn.py",
    "soundrts/world/world_map.py",
    "soundrts/world/world_core.py",
    "soundrts/world/world_objects.py",
    "soundrts/world/world_game.py",
    "soundrts/worldplayerbase/base.py",
    "soundrts/worldplayerbase/triggers.py",
    "res/multi/z5.txt",
    "test_respawn.py",
    "test_respawn_end_to_end.py",
    # 势力整体刷新
    "respawn_group",
    "test_respawn_group.py",
    "test_z5_group_respawn.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section(lang: str, version: str, next_version: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n%s\n" % version)
    rest = text[start:]
    next_idx = rest.find("\n%s\n" % next_version)
    return rest if next_idx == -1 else rest[:next_idx]


def _section_1525(lang: str) -> str:
    return _section(lang, "1.5.2.5", "1.5.2.4")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------
def test_version_is_at_least_1525():
    """当前 VERSION 必须 >= 1.5.2.5。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 5)


def test_all_relnotes_have_1525_before_1524_in_all_five_languages():
    """五种语言都必须有 1.5.2.5 段落，而且排在 1.5.2.4 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.5\n" in src, (lang, "missing 1.5.2.5 header")
        assert src.index("\n1.5.2.5\n") < src.index("\n1.5.2.4\n"), (
            lang,
            "1.5.2.5 must come before 1.5.2.4",
        )


def test_all_relnotes_have_1524_before_1523_in_all_five_languages():
    """五种语言都必须有 1.5.2.4 段落，而且排在 1.5.2.3 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.4\n" in src, (lang, "missing 1.5.2.4 header")
        assert src.index("\n1.5.2.4\n") < src.index("\n1.5.2.3\n"), (
            lang,
            "1.5.2.4 must come before 1.5.2.3",
        )


def test_all_relnotes_mention_every_new_topic_in_all_five_languages():
    """五种语言的 1.5.2.5 段落都必须点名全部新特性。"""
    for lang in _LANGS:
        section = _section_1525(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_the_shipped_entries_are_no_longer_in_the_1524_section():
    """1.5.2.4 段落不该再提到 1.5.2.5 的内容（护盾层才是 1.5.2.4 的开头）。"""
    for lang in _LANGS:
        section = _section(lang, "1.5.2.4", "1.5.2.3")
        for topic in ("deposit_decay", "item_decay", "test_ground_item_decay.py"):
            assert topic not in section, (lang, topic)


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------
def test_the_new_rules_keywords_are_known_to_the_parser():
    from soundrts.definitions import rules as global_rules

    known = (
        set(global_rules.key_value_properties)
        | set(global_rules.int_properties)
        | set(global_rules.string_list_properties)
        | set(global_rules.string_properties)
        | set(global_rules.precision_properties)
    )
    for keyword in ("deposit_decay", "item_decay"):
        assert keyword in known, keyword


def test_deposit_and_item_decay_default_to_never_expiring():
    """两个关键字的默认值必须是 0 —— 也就是「永不消失」，保持向后兼容。"""
    from soundrts.worlditem import Item
    from soundrts.worldresource import Deposit

    assert Deposit.deposit_decay == 0
    assert Item.item_decay == 0


def test_item_is_registered_as_an_active_object():
    """Item 必须有 update / slow_update，否则掉在地上的物品不会被登记。"""
    from soundrts.worlditem import Item

    assert callable(getattr(Item, "update", None))
    assert callable(getattr(Item, "slow_update", None))


# ---------------------------------------------------------------------------
# mod data
# ---------------------------------------------------------------------------
def test_the_aoe2_mod_caresses_decay_but_the_relic_does_not():
    """帝国 2 的狩猎尸体会过期，但圣物绝不能过期。"""
    from soundrts.definitions import Rules

    rules = Rules()
    rules.load(_source("mods", "aoe2", "rules.txt"))
    for name in ("food_carcass", "food_livestock"):
        cls = rules.unit_class(name)
        assert cls is not None, name
        assert cls.deposit_decay > 0, name
    relic = rules.unit_class("relic")
    assert relic is not None
    assert not relic.item_decay, "the AoE2 relic must never expire"


def test_the_campaign_items_have_no_decay():
    """战役必需物品（金币、宝箱、金堆）不得设置时限。"""
    rules_text = _source("res", "rules.txt")
    for name in ("treasure_chest", "gold_pile", "gold_coin"):
        assert name in rules_text, name
    for line in rules_text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("treasure_chest ", "gold_pile ", "gold_coin ")):
            assert "item_decay" not in stripped, stripped


# ---------------------------------------------------------------------------
# 敌人刷新（RPG 式怪物复活）
# ---------------------------------------------------------------------------
def test_respawn_time_is_known_to_the_parser():
    """``respawn_time`` 必须是引擎认识的规则关键字。"""
    from soundrts.definitions import rules as global_rules

    known = (
        set(global_rules.key_value_properties)
        | set(global_rules.int_properties)
        | set(global_rules.string_list_properties)
        | set(global_rules.string_properties)
        | set(global_rules.precision_properties)
    )
    assert "respawn_time" in known


def test_respawn_time_defaults_to_never_respawning():
    """默认必须是 0（永不刷新），保持向后兼容。"""
    from soundrts.worldunit.worldcreature import Creature

    assert Creature.respawn_time == 0


def test_the_zombie_planet_map_configures_respawns():
    """z5 地图的 b3 守军必须配置了刷新时间。

    z5 用的是**整队复活**（``respawn_group``）：守军被打光之后整队回来。
    """
    map_text = _source("res", "multi", "z5.txt")
    assert "respawn" in map_text, "z5.txt must configure respawn timers"
    assert "respawn_group 60" in map_text, (
        "z5.txt must configure the b3 garrison's group respawn"
    )
