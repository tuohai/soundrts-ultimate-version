# -*- coding: utf-8 -*-
"""审计：1.5.2.3 — 5 档难度、story 语义档、remove_unit、19 章难度差异。

1.5.2.3 发布的内容是：
  * 新增 ``(difficulty ...)`` 触发器条件：关卡内容可以按难度分支；
  * 新增 ``story`` **语义档**：覆盖 easy + standard 两档（决定版「标准档礼物」）；
  * 新增 ``(remove_unit <方格> <类型> [数量])`` 触发器动作；
  * 单人战役难度恢复为 5 档（简单/标准/中等/困难/极难，极难保留）；
  * 三个 AoE2 战役共 19 章按决定版原版逐章落实难度差异；
  * 修复：触发器发放的科技真正作用到已有单位；
  * 文档：五种语言的制图文档说明 ``(difficulty ...)`` 与 ``(remove_unit ...)``。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧与
战役数据侧确实如此。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.3 段落里被点名。
_TOPICS = (
    # 触发器条件与语义档
    "(difficulty ",
    "story",
    "remove_unit",
    # 五档难度
    "easy",
    "standard",
    "moderate",
    "hard",
    "extreme",
    # 三个战役
    "El Cid",
    "Joan of Arc",
    "William Wallace",
    "mods/aoe2/single/El Cid/",
    "mods/aoe2/single/Joan of Arc/",
    "mods/aoe2/single/William Wallace/",
    # 文档与测试
    "mapmaking.rst",
    "test_campaign_difficulty_tiers.py",
    "test_difficulty_trigger.py",
    "test_changelog_1523.py",
    # 引擎文件
    "soundrts/worldplayerbase/triggers.py",
    "soundrts/coop_difficulty.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1523(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.2.3\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.2.2\n")
    return rest if next_idx == -1 else rest[:next_idx]


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------
def test_version_is_at_least_1523():
    """当前 VERSION 必须 >= 1.5.2.3。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 3)


def test_the_version_file_says_1523():
    src = _source("soundrts", "version.py")
    assert 'VERSION = "1.5.2.3"' in src


# ---------------------------------------------------------------------------
# release notes
# ---------------------------------------------------------------------------
def test_all_relnotes_have_1523_before_1522_in_all_five_languages():
    """五种语言都必须有 1.5.2.3 段落，而且排在 1.5.2.2 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.3\n" in src, (lang, "missing 1.5.2.3 header")
        assert src.index("\n1.5.2.3\n") < src.index("\n1.5.2.2\n"), lang
        assert src.index("\n1.5.2.2\n") < src.index("\n1.5.2.1\n"), lang


def test_relnotes_1523_document_every_session_topic():
    """五种语言的 1.5.2.3 段落都必须点名本次发布的每一项改动。"""
    for lang in _LANGS:
        section = _section_1523(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1523_mention_the_nineteen_chapters():
    """发行说明必须说明「19 章」都落实了难度差异。"""
    for lang in _LANGS:
        section = _section_1523(lang)
        assert "19" in section, lang


# ---------------------------------------------------------------------------
# the engine
# ---------------------------------------------------------------------------
def test_the_engine_has_five_difficulty_tiers():
    """单人战役难度必须仍是 5 档，极难保留。"""
    from soundrts.coop_difficulty import (
        EASY,
        EXTREME,
        HARD,
        LEVELS,
        MODERATE,
        STANDARD,
        normalize_single_player_level,
    )

    assert LEVELS == (EASY, STANDARD, MODERATE, HARD, EXTREME)
    for level in LEVELS:
        assert normalize_single_player_level(level) == level


def test_the_engine_has_the_story_semantic_tier():
    """``story`` = easy + standard。"""
    from soundrts.coop_difficulty import (
        EASY,
        STANDARD,
        STORY,
        STORY_TIERS,
        compare_level,
        is_story_tier,
    )

    assert STORY == "story"
    assert STORY_TIERS == (EASY, STANDARD)
    assert is_story_tier(EASY) is True
    assert is_story_tier(STANDARD) is True
    for tier in ("moderate", "hard", "extreme"):
        assert is_story_tier(tier) is False
    # ``story`` 没有次序，大小比较永远为假。
    for op in ("<", "<=", ">", ">="):
        assert compare_level("extreme", op, "story") is False


def test_the_engine_has_the_remove_unit_trigger_action():
    """``(remove_unit <方格> <类型> [数量])`` 必须真的存在并删除对象。"""
    from soundrts.worldplayerbase.triggers import TriggersMixin

    assert hasattr(TriggersMixin, "lang_remove_unit")
    src = Path(TriggersMixin.lang_remove_unit.__code__.co_filename)
    text = src.read_text(encoding="utf-8")
    assert "o.delete()" in text


def test_the_campaign_menu_offers_five_tiers():
    """单人战役菜单必须遍历 5 档，不再用 3 档的决定版列表。"""
    src = _source("soundrts", "campaign.py")
    assert "LEVELS" in src
    assert "SINGLE_PLAYER_LEVELS" not in src
    assert "normalize_single_player_level" in src


def test_trigger_granted_techs_reach_the_existing_units():
    """触发器发放的科技必须真正作用到玩家已有的单位上。"""
    src = _source("soundrts", "worldplayerbase", "triggers.py")
    assert "_grant_upgrade_by_trigger" in src
    block_start = src.index("def _grant_upgrade_by_trigger")
    block = src[block_start : block_start + 2000]
    assert "upgrade_player" in block, (
        "the granted tech must be applied to the units the player already "
        "owns, not just recorded in player.upgrades"
    )


# ---------------------------------------------------------------------------
# the campaign data
# ---------------------------------------------------------------------------
def test_all_nineteen_chapters_exist():
    """三个战役共 19 章：El Cid 6 + Joan of Arc 6 + William Wallace 7。"""
    root = Path(__file__).resolve().parents[2]
    counts = {
        "El Cid": 6,
        "Joan of Arc": 6,
        "William Wallace": 7,
    }
    total = 0
    for name, count in counts.items():
        camp = root / "mods" / "aoe2" / "single" / name
        assert camp.is_dir(), name
        for n in range(1, count + 1):
            assert (camp / f"{n}.txt").is_file(), f"{name}/{n}.txt"
        total += count
    assert total == 19


def test_every_chapter_with_a_documented_difference_uses_a_difficulty_trigger():
    """有差异的章节必须真的用到难度触发器。"""
    root = Path(__file__).resolve().parents[2]
    # 决定版记为「无差异」的章节不得分支。
    no_difference = (
        ("El Cid", "2.txt"),
        ("El Cid", "5.txt"),
        ("Joan of Arc", "4.txt"),
        ("William Wallace", "1.txt"),
        ("William Wallace", "2.txt"),
        ("William Wallace", "3.txt"),
        ("William Wallace", "5.txt"),
        ("William Wallace", "6.txt"),
        ("William Wallace", "7.txt"),
    )
    for name, chapter in no_difference:
        text = (root / "mods" / "aoe2" / "single" / name / chapter).read_text(
            encoding="utf-8"
        )
        statements = [
            line.split(";", 1)[0]
            for line in text.splitlines()
        ]
        joined = "\n".join(statements)
        assert "(difficulty " not in joined, (
            f"{name}/{chapter} has no difficulty differences in the DE "
            "original -- it must not branch on the difficulty"
        )

    # 有差异的章节必须用到难度触发器。
    with_difference = (
        ("El Cid", "1.txt"),
        ("El Cid", "3.txt"),
        ("El Cid", "4.txt"),
        ("El Cid", "6.txt"),
        ("Joan of Arc", "1.txt"),
        ("Joan of Arc", "2.txt"),
        ("Joan of Arc", "3.txt"),
        ("Joan of Arc", "5.txt"),
        ("Joan of Arc", "6.txt"),
        ("William Wallace", "4.txt"),
    )
    for name, chapter in with_difference:
        text = (root / "mods" / "aoe2" / "single" / name / chapter).read_text(
            encoding="utf-8"
        )
        assert "(difficulty " in text, f"{name}/{chapter}"


def test_the_tier_test_file_exists():
    """本次发布新增的测试必须真的存在。"""
    root = Path(__file__).resolve().parents[2]
    for name in (
        "test_campaign_difficulty_tiers.py",
        "test_difficulty_trigger.py",
    ):
        assert (root / "soundrts" / "tests" / name).exists(), name


# ---------------------------------------------------------------------------
# the documentation
# ---------------------------------------------------------------------------
def test_the_mapmaking_docs_document_difficulty_and_remove_unit():
    """五种语言的制图文档都必须讲清楚 ``(difficulty ...)`` 与 ``(remove_unit ...)``。"""
    for lang in _LANGS:
        mapmaking = _source("doc_src", "src", lang, "mod", "mapmaking.rst")
        assert "difficulty" in mapmaking, lang
        assert "remove_unit" in mapmaking, lang
        assert "story" in mapmaking, lang
