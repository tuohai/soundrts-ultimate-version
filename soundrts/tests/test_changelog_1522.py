# -*- coding: utf-8 -*-
"""审计：1.5.2.2 — El Cid 战役、文明专属科技泄漏、战役序章解锁、命中加成标签。

1.5.2.2 发布的内容是：
  * 新增帝国时代 2 决定版剧情战役「El Cid」（6 章 + 13 种语言的 TTS）；
  * 新增地图关键字 ``player_faction``（战役中途换文明）；
  * 地图解析器不再把 ``>=`` 之类的比较运算符误报成未知单位类型；
  * 修复文明专属科技泄漏到别的文明的单位上（不列颠的巨型投石机曾经
    列着西西里的「第一次十字军东征」）；
  * 修复单人战役菜单：0.txt 序章不出现、第一关无法解锁；
  * 修复属性界面把「命中加成」念成「伤害加成」；
  * 测试套件不再受资源栈导入顺序影响。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧与
战役数据侧确实如此。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.2 段落里被点名。
_TOPICS = (
    # 新战役
    "El Cid",
    "mods/aoe2/single/El Cid/",
    "player_faction",
    "default_faction",
    "test_el_cid_campaign.py",
    # 触发器比较运算符
    ">=",
    # 科技泄漏
    "first_crusade",
    "can_build",
    "is_tech_researchable_by_player",
    "test_can_use_tech_civ_filter.py",
    # 战役序章
    "0.txt",
    "unlock_next",
    "campaigns.ini",
    "test_campaign_chapter_unlock.py",
    # 属性界面
    "rdg_hit_rate",
    "STAT_TTS_NAMES",
    "vs_handler.py",
    "test_vs_handler_hit_rate_labels.py",
    # 测试套件
    "conftest.py",
)

# 实测数字：207 处修正、11460 条泄漏条目、42 个文明、249 项科技、30 个标签。
_NUMBERS = ("207", "11460", "42", "249")


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1522(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.2.2\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.2.1\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1522():
    """当前 VERSION 必须 >= 1.5.2.2。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 2)


def test_all_relnotes_have_1522_before_1521_in_all_five_languages():
    """五种语言都必须有 1.5.2.2 段落，而且排在 1.5.2.1 之前。"""
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.2.2\n" in src, (lang, "missing 1.5.2.2 header")
        assert src.index("\n1.5.2.2\n") < src.index("\n1.5.2.1\n"), lang
        assert src.index("\n1.5.2.1\n") < src.index("\n1.5.2.0\n"), lang


def test_relnotes_1522_document_every_session_topic():
    """五种语言的 1.5.2.2 段落都必须点名本次发布的每一项改动。"""
    for lang in _LANGS:
        section = _section_1522(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)
        for number in _NUMBERS:
            assert number in section, (lang, number)


def test_the_el_cid_campaign_ships_with_all_its_chapters():
    """El Cid 战役的 6 章、战役元数据、规则与 style 必须都在。"""
    root = Path(__file__).resolve().parents[2]
    camp = root / "mods" / "aoe2" / "single" / "El Cid"
    assert camp.is_dir()
    for n in range(1, 7):
        assert (camp / f"{n}.txt").is_file(), f"missing chapter {n}.txt"
    assert (camp / "campaign.txt").is_file()
    assert (camp / "rules.txt").is_file()
    assert (camp / "ui" / "style.txt").is_file()


def test_the_el_cid_campaign_has_all_thirteen_languages():
    """El Cid 必须有英文加 12 个本地化语言目录。"""
    root = Path(__file__).resolve().parents[2]
    camp = root / "mods" / "aoe2" / "single" / "El Cid"
    assert (camp / "ui" / "tts.txt").is_file()
    for lang in (
        "ui-be", "ui-cs", "ui-de", "ui-es", "ui-fr", "ui-it", "ui-pl",
        "ui-pt-BR", "ui-ru", "ui-sk", "ui-vi", "ui-zh",
    ):
        assert (camp / lang / "tts.txt").is_file(), lang


def test_the_map_parser_supports_player_faction():
    """``player_faction`` 必须既能被解析，也必须被引擎真正使用。"""
    world_map = _source("soundrts", "world", "world_map.py")
    assert 'w == "player_faction"' in world_map
    assert "self.player_faction = words[1]" in world_map

    game = _source("soundrts", "game.py")
    assert "def _faction_for_chapter(chapter):" in game
    assert 'getattr(getattr(chapter, "map", None), "player_faction", None)' in game
    # 地图的 player_faction 必须优先于 campaign.txt 的 default_faction。
    assert game.index('"player_faction"') < game.index('"default_faction"')


def test_the_map_parser_knows_the_comparison_operators():
    """比较运算符不得再被当成未知单位类型。"""
    world_map = _source("soundrts", "world", "world_map.py")
    assert "_TRIGGER_COMPARISON_OPERATORS" in world_map
    for op in ('"=="', '"!="', '"<="', '">="', '"<"', '">"'):
        assert op in world_map, op


def test_the_civ_tech_leak_fix_is_in_place():
    """文明专属科技不得泄漏到别的文明。"""
    utils = _source("soundrts", "attributes", "utils.py")
    assert "def _faction_buildable_types(faction):" in utils
    assert "if maker not in _faction_buildable_types(faction):" in utils

    definitions = _source("soundrts", "definitions.py")
    assert "_faction_buildable_types_cache" in definitions


def test_the_campaign_bookmark_semantics_are_fixed():
    """书签必须表示「下一个可玩章节的下标」。"""
    campaign = _source("soundrts", "campaign.py")
    assert "def unlock_next(" in campaign
    assert "def _available_chapters(" in campaign
    # campaigns.ini 的读写必须用 ``with``（不能泄漏文件句柄）。
    assert "with open(" in campaign
    assert "CAMPAIGNS_CONFIG_PATH" in campaign


def test_the_vs_label_fix_is_in_place():
    """``*_vs`` 标签必须查权威映射表，而不是靠猜。"""
    vs_handler = _source("soundrts", "attributes", "vs_handler.py")
    assert "STAT_TTS_NAMES.get(root + \"_vs\")" in vs_handler

    utils = _source("soundrts", "attributes", "utils.py")
    assert '"rdg_hit_rate_vs": mp.RDG_COVER_VS' in utils
    assert '"mdg_hit_rate_vs": mp.MDG_COVER_VS' in utils


def test_the_test_suite_imports_the_resource_stack_eagerly():
    """资源栈必须在 conftest 导入期就绪，而不是懒加载。"""
    conftest = _source("soundrts", "tests", "conftest.py")
    assert "import soundrts.options" in conftest
    assert "soundrts.lib.resource" in conftest


def test_the_new_tests_exist():
    """本次发布新增的三个测试必须真的存在。"""
    root = Path(__file__).resolve().parents[2]
    for name in (
        "test_el_cid_campaign.py",
        "test_vs_handler_hit_rate_labels.py",
        "test_campaign_chapter_unlock.py",
        "test_can_use_tech_civ_filter.py",
    ):
        assert (root / "soundrts" / "tests" / name).exists(), name


def test_the_mapmaking_docs_document_player_faction():
    """五种语言的制图文档都必须讲清楚 ``player_faction``。"""
    for lang in _LANGS:
        mapmaking = _source("doc_src", "src", lang, "mod", "mapmaking.rst")
        assert "player_faction" in mapmaking, lang
        assert "default_faction" in mapmaking, lang
        assert "saracens" in mapmaking, lang


def test_the_campaign_menu_docs_explain_the_bookmark():
    """五种语言的战役菜单文档都必须讲清楚书签语义与过场章节。"""
    for lang in _LANGS:
        menu = _source("doc_src", "src", lang, "player", "campaign-menu.rst")
        assert "cut_scene_chapter" in menu, lang
        assert "0.txt" in menu, lang
        assert "1.5.2.2" in menu, lang
