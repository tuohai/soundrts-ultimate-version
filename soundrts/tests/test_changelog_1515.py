"""审计：1.5.1.5 增补 — 中立持有者不触发胜利倒计时 + 任务目标动态进度。

1.5.1.5 发布的内容（本次会话增补的部分）：
  * ``soundrts/world_inventory_victory.py`` 新增 ``_holder_can_win``，
    中立 creep / 战役 NPC 持有的胜利物品不再被当成"胜利方"——修复了
    圣女贞德德战役第四章把三件圣物交给兰斯大教堂后误报
    "中立 1 的胜利倒计时已开始，还剩 16 分 40 秒"的 bug；
  * 任务目标支持动态进度（F9 / HUD 显示 ``0/3`` → ``1/3`` → ``3/3``），
    实现在 ``soundrts/worldplayerbase/triggers.py`` 的 ``objective_progress``
    与 ``soundrts/objective_announce.py`` 的 ``objective_progress_parts``；
  * ``mods/aoe2/single/Joan of Arc/4.txt`` 的 ``register_objective 1 2 3 4``
    修正为 ``register_objective 1 2``（3、4 是不存在的目标）。

这些测试断言五种语言的发布说明与地图制作文档都如实记录了上述内容，
并核对引擎侧与地图侧确实落地了对应的实现。
"""
from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1515(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.5\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.4\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1515():
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 5)


def test_all_relnotes_have_1515_before_1514_in_all_five_languages():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.5\n" in src, (lang, "missing 1.5.1.5 header")
        assert src.index("\n1.5.1.5\n") < src.index("\n1.5.1.4\n"), lang


def test_relnotes_1515_documents_neutral_holder_victory_fix():
    for lang in _LANGS:
        s = _section_1515(lang)
        assert "_holder_can_win" in s, lang
        assert "world_inventory_victory.py" in s, lang
        assert "controlling_team" in s, lang
        assert "test_inventory_victory.py" in s, lang


def test_relnotes_1515_documents_objective_progress_feature():
    for lang in _LANGS:
        s = _section_1515(lang)
        assert "objective_progress" in s, lang
        assert "objective_progress_parts" in s, lang
        assert "npc_has_items" in s, lang
        assert "has_brought_item" in s, lang
        assert "Objective.progress" in s, lang
        assert "test_objective_progress.py" in s, lang


def test_relnotes_1515_documents_joan_chapter4_objective_fix():
    for lang in _LANGS:
        s = _section_1515(lang)
        assert "register_objective 1 2" in s, lang
        assert "Joan of Arc/4.txt" in s, lang


def test_mapmaking_docs_document_objective_progress():
    for lang in _LANGS:
        doc = _source("doc_src", "src", lang, "mod", "mapmaking.rst")
        assert "objective_progress" in doc, lang
        assert "npc_has_items" in doc, lang
        assert "has_brought_item" in doc, lang
        assert "1.5.1.5" in doc, lang


def test_engine_has_holder_can_win_guard():
    src = _source("soundrts", "world_inventory_victory.py")
    assert "def _holder_can_win(holder, world):" in src
    assert "controlling_team" in src
    block = src.split("def _holder_can_win(holder, world):")[1].split("\ndef ")[0]
    assert 'getattr(holder, "neutral", False)' in block
    assert 'getattr(holder, "is_campaign_npc", False)' in block


def test_engine_has_objective_progress_resolver():
    triggers = _source("soundrts", "worldplayerbase", "triggers.py")
    assert "def objective_progress(self, number, optional=False):" in triggers
    assert "def _counting_progress(self, condition):" in triggers
    assert '"npc_has_items"' in triggers
    assert '"has_item"' in triggers
    assert '"has_brought_item"' in triggers

    announce = _source("soundrts", "objective_announce.py")
    assert "def objective_progress_parts(player, objective):" in announce

    base = _source("soundrts", "worldplayerbase", "base.py")
    assert "self.progress = None" in base


def test_joan_chapter4_registers_only_existing_objectives():
    map_text = _source("mods", "aoe2", "single", "Joan of Arc", "4.txt")
    assert "register_objective 1 2 3 4" not in map_text
    assert "register_objective 1 2" in map_text
    assert "square_name 8888 " not in map_text
    assert "square_name 8886 " in map_text
