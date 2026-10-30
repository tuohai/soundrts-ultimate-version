"""审计：1.5.1.6 — 帝国 2 文明外壳标题、科技效果引擎、罗马对标 DE 与新文明独有单位。

1.5.1.6 发布的内容是：
  * ``mods/aoe2/ui/style.txt`` 补齐 142 个缺失的文明建筑 / 单位外壳样式
    定义（此前骡马（罗马）兵营按 W 键不播报，就是因为外壳没有样式定义）；
  * 科技效果引擎的两处修复：带 ``effect_bonus_targets`` 过滤器的成本效果
    不再泄漏到所有单位；多行 ``effect`` 的每一行都会生效；
  * 新增 ``team_share_train`` 规则字段（意大利盟友可训练佣兵）；
  * 修复种族 ``build_speed_pct`` 从未生效；
  * 罗马整棵科技树对标 AoE2 DE（Return of Rome），新增 ``centurion`` /
    ``elite_centurion`` 与两个独有科技 ``ballistas`` / ``comitatenses``；
  * 科尼克取代并不存在的"壁垒"、印度斯坦获得古拉姆、印加卡玛尤克与投石手
    对标 DE、意大利佣兵数值修正、德龙进入《Return of Rome》船坞、
    萨拉森建筑槽位指向真实基类；
  * 新增四个回归测试模块。

这些测试断言五种语言的发布说明都如实记录了上述内容，并核对引擎侧与
mod 侧确实落地了对应的实现。
"""
from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.1.6 段落里被点名。
_TOPICS = (
    # 文明外壳样式
    "style.txt",
    "roman_barracks",
    "142",
    # 测试状态泄漏
    "_isolate_resource_mods",
    "try/finally",
    # 带过滤器的成本效果
    "effect_bonus_targets",
    "worldupgrade/base.py",
    # 多行科技效果
    "kill_resource_vs",
    "time_cost",
    # team_share_train
    "team_share_train",
    "team_share_train_entries",
    "world_build_rules.effective_can_train",
    # build_speed_pct
    "build_speed_pct",
    "player.build_speed_pct",
    "worldplayerbase/base.py",
    # 罗马
    "legionary",
    "centurion",
    "elite_centurion",
    "ballistas",
    "comitatenses",
    "long_swordsman",
    # 科尼克
    "konnik",
    "bulwark",
    # 古拉姆
    "ghulam",
    # 印加
    "kamayuk",
    "slinger",
    # 佣兵
    "condottiero",
    # 德龙
    "dromon",
    # 萨拉森
    "aoe_barracks",
    "barracks",
    # 新测试
    "test_aoe2_civ_unique_units_alignment.py",
    "test_aoe2_romans_alignment.py",
    "test_aoe2_tech_effect_engine.py",
    "test_aoe2_civ_building_shell_titles.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1516(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.6\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.5\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1516():
    """当前 VERSION 必须 >= 1.5.1.6。

    早期版本把版本号写死成精确值，导致此后每个版本发布都会让这条测试
    失败 —— 那是噪声而不是信号。断言"至少"，与 test_changelog_1515.py 一致。
    """
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 6)


def test_all_relnotes_have_1516_before_1515_in_all_five_languages():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.6\n" in src, (lang, "missing 1.5.1.6 header")
        assert src.index("\n1.5.1.6\n") < src.index("\n1.5.1.5\n"), lang
        assert src.index("\n1.5.1.5\n") < src.index("\n1.5.1.4\n"), lang


def test_relnotes_1516_document_every_session_topic():
    """五种语言的 1.5.1.6 段落都必须点名本次会话的每一项改动。"""
    for lang in _LANGS:
        section = _section_1516(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1516_document_the_civ_shell_style_fix():
    """文明外壳缺样式定义导致建筑没有标题 / 热键，必须写进发布说明。"""
    for lang in _LANGS:
        section = _section_1516(lang)
        assert "style.txt" in section, lang
        assert "test_aoe2_civ_building_shell_titles.py" in section, lang


def test_relnotes_1516_document_the_tech_effect_engine_fixes():
    """带过滤器的成本效果泄漏与多行效果只生效第一行，必须写进发布说明。"""
    for lang in _LANGS:
        section = _section_1516(lang)
        assert "effect_bonus_targets" in section, lang
        assert "worldupgrade/base.py" in section, lang
        assert "worldupgrade/cost_effects.py" in section, lang
        assert "worldorders/base.py" in section, lang


def test_relnotes_1516_document_the_roman_alignment():
    """罗马对标 DE 必须写进发布说明。"""
    for lang in _LANGS:
        section = _section_1516(lang)
        assert "centurion" in section, lang
        assert "elite_centurion" in section, lang
        assert "legionary" in section, lang
        assert "ballistas" in section, lang
        assert "comitatenses" in section, lang
        assert "long_swordsman" in section, lang
        assert "mods/aoe2/rules.txt" in section, lang


def test_relnotes_1516_document_the_new_unique_units():
    """新加入 / 修正的文明独有单位必须写进发布说明。"""
    for lang in _LANGS:
        section = _section_1516(lang)
        for unit in ("konnik", "ghulam", "kamayuk", "slinger", "condottiero", "dromon"):
            assert unit in section, (lang, unit)


def test_engine_has_team_share_train_rule_field():
    """``team_share_train`` 必须在引擎里声明、读取并提供。"""
    definitions = _source("soundrts", "definitions.py")
    assert 'words[0] == "team_share_train"' in definitions
    assert '"team_share_train"' in definitions

    bonuses = _source("soundrts", "world_civ_bonuses.py")
    assert "def team_share_train_entries(player):" in bonuses
    assert '"team_share_train"' in bonuses

    build_rules = _source("soundrts", "world_build_rules.py")
    assert "team_share_train" in build_rules
    assert "effective_can_train" in build_rules


def test_engine_applies_the_race_build_speed_bonus():
    """``build_speed_pct`` 必须被读取并存进玩家。"""
    base = _source("soundrts", "worldplayerbase", "base.py")
    assert "def _race_build_speed_pct(faction):" in base
    assert "self.build_speed_pct = _race_build_speed_pct(self.faction)" in base


def test_engine_keeps_filtered_cost_effects_separate():
    """带过滤器的成本效果必须单独存放，不能写成玩家级加成。"""
    base = _source("soundrts", "worldupgrade", "base.py")
    assert "filtered_cost_effects" in base
    assert "effect_targets" in base


def test_engine_applies_every_row_of_a_multi_row_effect():
    """多行科技效果的去重键必须带上行号。"""
    base = _source("soundrts", "worldupgrade", "base.py")
    assert 'f"{cls.type_name}:{level}:{row_index}"' in base


def test_aoe2_rules_have_the_roman_tree():
    """``mods/aoe2/rules.txt`` 里必须真的有罗马科技树与两个独有科技。"""
    rules = _source("mods", "aoe2", "rules.txt")
    assert "def roman_barracks" in rules
    assert "def roman_castle" in rules
    assert "def ballistas" in rules
    assert "def comitatenses" in rules
    assert "def centurion" in rules
    assert "def elite_centurion" in rules
    assert "def legionary" in rules


def test_aoe2_rules_dropped_the_nonexistent_bulwark():
    """AoE2 里并不存在的"壁垒"必须已经删掉。"""
    rules = _source("mods", "aoe2", "rules.txt")
    assert "\ndef bulwark\n" not in rules
    assert "\ndef elite_bulwark\n" not in rules
    assert "\ndef konnik\n" in rules
    assert "\ndef elite_konnik\n" in rules


def test_aoe2_rules_saracen_slots_point_at_real_base_classes():
    """萨拉森的建筑槽位必须指向真实存在的基类。"""
    rules = _source("mods", "aoe2", "rules.txt")
    for bogus in (
        "barracks aoe_barracks",
        "archery_range aoe_archery",
        "stables aoe_stables",
        "blacksmith aoe_blacksmith",
        "university aoe_university",
        "workshop aoe_workshop",
        "shipyard aoe_dock",
        "monastery aoe_monastery",
    ):
        assert bogus not in rules, bogus
