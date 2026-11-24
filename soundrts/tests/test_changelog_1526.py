# -*- coding: utf-8 -*-
"""审计：1.5.2.6 — 建造建筑被重复计费，黄金被扣成负数。

1.5.2.6 发布的内容是：
  * 修复：建造建筑时资源被扣了两次 —— 建造命令按**折后价**预留并退款，
    ``BuildingSite`` 又按**规则原始价**扣了一次；于是封建时代 10 黄金盖市政厅
    （原始价 12，封建折扣 -2），扣完变成 **-2 黄金**；
  * 修复：预留资源的退款用的是「当前订单价」而不是「当初实付价」，
    价格在预留与退款之间变化时会凭空造出或吞掉资源；
  * 修复：``cancel_building`` 取消在建建筑时退的是原始价而不是实付价。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧确实如此。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.6 段落里被点名。
# 只使用在五种语言里都原样出现的记号（代码名、文件名、数字）。
_TOPICS = (
    # 重复计费与负数黄金
    "-2",
    "10",
    "12",
    "cost 12 16",
    "phase bonus",
    "cost -2 0",
    # 折后价 vs 原始价
    "BuildingSite",
    "paid_cost",
    # 退款用的是实付价
    "reserved_cost",
    "cancel_building",
    # 引擎文件
    "soundrts/worldunit/worldcreature.py",
    "soundrts/worldorders/production.py",
    "soundrts/worldorders/base.py",
    "soundrts/worldorders/immediate.py",
    "soundrts/worldplayerbase/resources.py",
    "soundrts/tests/test_build_cost_not_double_charged.py",
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


def _section_1526(lang: str) -> str:
    return _section(lang, "1.5.2.6", "1.5.2.5")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------
def test_version_is_at_least_1526():
    """当前 VERSION 必须 >= 1.5.2.6。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 6)


def test_all_relnotes_have_1526_before_1525_in_all_five_languages():
    """五种语言都必须有 1.5.2.6 段落，而且排在 1.5.2.5 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.6\n" in src, (lang, "missing 1.5.2.6 header")
        assert src.index("\n1.5.2.6\n") < src.index("\n1.5.2.5\n"), (
            lang,
            "1.5.2.6 must come before 1.5.2.5",
        )


def test_all_relnotes_mention_every_new_topic_in_all_five_languages():
    """五种语言的 1.5.2.6 段落都必须点名全部新特性。"""
    for lang in _LANGS:
        section = _section_1526(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_the_shipped_entries_are_no_longer_in_the_1525_section():
    """1.5.2.5 段落不该再提到 1.5.2.6 的内容。"""
    for lang in _LANGS:
        section = _section(lang, "1.5.2.5", "1.5.2.4")
        for topic in ("test_build_cost_not_double_charged.py", "cancel_building"):
            assert topic not in section, (lang, topic)


# ---------------------------------------------------------------------------
# engine
# ---------------------------------------------------------------------------
def test_the_building_site_charges_the_paid_cost_not_the_raw_cost():
    """``BuildingSite`` 必须按实付金额计费，而不是规则原始价。"""
    import inspect

    from soundrts.worldunit.worldcreature import BuildingSite

    src = inspect.getsource(BuildingSite.__init__)
    assert "paid_cost" in src
    assert "player.pay(paid_cost)" in src
    # 不能再无条件地按原始价扣钱。
    assert "player.pay(building_type.cost)" not in src


def test_the_build_order_passes_its_paid_cost_to_the_site():
    """建造命令必须把实付金额交给建筑工地。"""
    import inspect

    from soundrts.worldorders.production import BuildOrder

    src = inspect.getsource(BuildOrder.execute)
    assert "paid_cost" in src
    assert "paid_cost=paid_cost" in src


def test_the_reservation_records_the_charged_amount():
    """预留资源时必须记下实付金额，退款时原样退回。"""
    import inspect

    from soundrts.worldplayerbase.resources import ResourcesMixin

    reserve = inspect.getsource(ResourcesMixin._reserve_resources)
    assert "reserved_cost" in reserve

    free = inspect.getsource(ResourcesMixin.free_resources)
    assert "reserved_cost" in free


def test_cancel_building_refunds_the_paid_cost():
    """取消在建建筑必须退实付金额。"""
    import inspect

    from soundrts.worldorders.immediate import CancelBuildingOrder

    src = inspect.getsource(CancelBuildingOrder.immediate_action)
    assert "paid_cost" in src
