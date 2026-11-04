"""审计：1.5.1.7 — 帝国 2 DE 对齐（官方简介、独有单位、队伍奖励、9 个独有建筑与光环）。

1.5.1.7 发布的内容是：
  * 42 个文明的简介改用 DE 官方原文（13 个语言包），并新增官方 DE 参考数据
    流水线（``_de_strings/`` 与 ``_de_trees/`` 随仓库提交）；
  * 补齐简介承诺却未定义的 DE 独有单位与独有科技，并删除参考表里的杜撰项；
  * ``can_use_tech`` 改为可累加的字符串列表属性；
  * Citadels 的效果行与攻城象的 ``train_time`` 修复（``train_time`` 注册为
    规则属性）；
  * 七个 DE 队伍奖励真正生效（``team_repair_cost_pct`` 等）；
  * ``can_train`` 效果不再泄漏目标名、研究解锁的单位会并入宿主建筑、
    贸易奖励百分比不再被放大 250 倍；
  * 中文科技名对齐 DE 字符串表、独有单位图标与 Monaspa 单位类别修正；
  * 磨坊科技对已建农田生效；
  * 新增西西里 Donjon；
  * 补齐 9 个缺失的 DE 独有 / 地区建筑，并新增数据驱动的建筑光环引擎
    （``soundrts/world_aura.py``）；
  * 装甲象升级线接线；
  * 过滤效果行的目标列表成为它唯一的授权依据。

这些测试断言五种语言的发行说明都如实记录了上述内容，并核对引擎侧与
mod 侧确实落地了对应的实现。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.1.7 段落里被点名。
_TOPICS = (
    # 官方简介
    "_de_civ_data",
    "_de_strings",
    "_de_trees",
    "_gen_civ_intros.py",
    "_verify_de_civs.py",
    "tts.txt",
    # 独有单位与独有科技
    "houfnice",
    "missionary",
    "fereters",
    "boiling_oil",
    "citadels",
    "recurve_bow",
    "can_use_tech",
    # Citadels 与 train_time
    "train_time",
    "rdg_vs",
    # 队伍奖励
    "team_repair_cost_pct",
    "team_military_building_pop",
    "team_free_stone_buildings",
    "team_start_free_llama",
    "team_relic_food",
    "team_relic_visible",
    "team_train_speed_pct",
    # can_train 与订单
    "can_train",
    "research_cost_tech_discount",
    "trade_reward_bonus_pct",
    # 磨坊科技
    "farm",
    "resource_volume_max",
    # Donjon
    "donjon",
    # 9 个独有建筑与光环
    "krepost",
    "caravanserai",
    "folwark",
    "mule_cart",
    "fortified_church",
    "settlement",
    "world_aura.py",
    "aura_radius",
    "aura_heal_level",
    "aura_speed_bonus_pct",
    "aura_target_types",
    # 装甲象
    "armored_elephant",
    "line_upgrade",
    # 目标列表即授权
    "effect_bonus_targets",
    "expanded_is_a",
    # 新测试
    "test_aoe2_team_bonuses_alignment.py",
    "test_aoe2_unique_buildings_alignment.py",
    "test_aoe2_sicilians_donjon.py",
    "test_effect_bonus_self_authorize.py",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1517(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.7\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.6\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1517():
    """当前 VERSION 必须 >= 1.5.1.7。

    早期版本把版本号写死成精确值，导致此后每个版本发布都会让这条测试
    失败 —— 那是噪声而不是信号。断言"至少"，与 test_changelog_1516.py 一致。
    """
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 7)


def test_all_relnotes_have_1517_before_1516_in_all_five_languages():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.7\n" in src, (lang, "missing 1.5.1.7 header")
        assert src.index("\n1.5.1.7\n") < src.index("\n1.5.1.6\n"), lang
        assert src.index("\n1.5.1.6\n") < src.index("\n1.5.1.5\n"), lang


def test_relnotes_1517_document_every_session_topic():
    """五种语言的 1.5.1.7 段落都必须点名本次会话的每一项改动。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1517_document_the_official_civ_intros():
    """官方 DE 简介与参考数据流水线必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        assert "_de_strings" in section, lang
        assert "_de_trees" in section, lang
        assert "_gen_civ_intros.py" in section, lang


def test_relnotes_1517_document_the_unique_units_and_technologies():
    """新增的独有单位 / 独有科技与删除的杜撰项必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        for name in ("houfnice", "missionary", "fereters", "citadels"):
            assert name in section, (lang, name)
        assert "boiling_oil" in section, lang


def test_relnotes_1517_document_the_team_bonuses():
    """七个 DE 队伍奖励必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        for name in (
            "team_repair_cost_pct",
            "team_military_building_pop",
            "team_free_stone_buildings",
            "team_start_free_llama",
            "team_relic_food",
            "team_relic_visible",
            "team_train_speed_pct",
        ):
            assert name in section, (lang, name)


def test_relnotes_1517_document_the_unique_buildings_and_the_aura():
    """9 个独有建筑与数据驱动的光环引擎必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        for name in (
            "krepost",
            "caravanserai",
            "folwark",
            "mule_cart",
            "fortified_church",
            "settlement",
        ):
            assert name in section, (lang, name)
        assert "world_aura.py" in section, lang
        assert "aura_radius" in section, lang


def test_relnotes_1517_document_the_sicilian_donjon():
    """西西里 Donjon 必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        assert "donjon" in section, lang


def test_relnotes_1517_document_the_self_authorizing_effect_rows():
    """过滤效果行的目标列表即授权，必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1517(lang)
        assert "effect_bonus_targets" in section, lang
        assert "expanded_is_a" in section, lang


def test_engine_has_the_de_team_bonus_fields():
    """七个队伍奖励字段必须在引擎里声明、解析并提供。"""
    definitions = _source("soundrts", "definitions.py")
    for name in (
        "team_repair_cost_pct",
        "team_start_free_llama",
        "team_relic_food",
        "team_relic_visible",
    ):
        assert f'"{name}"' in definitions, name
    for name in (
        "team_military_building_pop",
        "team_free_stone_buildings",
        "team_train_speed_pct",
    ):
        assert f'words[0] == "{name}"' in definitions, name

    bonuses = _source("soundrts", "world_civ_bonuses.py")
    for func in (
        "def team_repair_cost_pct(",
        "def team_military_building_pop(",
        "def team_free_stone_buildings(",
        "def team_start_free_llama(",
        "def team_relic_food(",
        "def team_relic_visible(",
        "def team_train_speed_pct(",
    ):
        assert func in bonuses, func


def test_engine_has_the_aura_module_and_the_aura_rule_fields():
    """光环引擎与五个 ``aura_*`` 规则字段必须存在。"""
    aura = _source("soundrts", "world_aura.py")
    assert "def apply_building_aura(" in aura
    assert "def apply_speed_aura(" in aura

    definitions = _source("soundrts", "definitions.py")
    for name in (
        "aura_radius",
        "aura_heal_level",
        "aura_heal_cd",
        "aura_speed_bonus_pct",
        "aura_target_types",
    ):
        assert f'"{name}"' in definitions, name


def test_engine_registers_train_time_and_can_use_tech_as_additive():
    """``train_time`` 必须是规则属性，``can_use_tech`` 必须可累加。"""
    definitions = _source("soundrts", "definitions.py")
    assert '"train_time"' in definitions
    assert "can_use_tech" in definitions

    creature = _source("soundrts", "worldunit", "worldcreature.py")
    assert "train_time = 0" in creature


def test_engine_has_the_self_authorizing_effect_row_helpers():
    """目标列表即授权的判定辅助函数必须在引擎里存在。"""
    parse = _source("soundrts", "worldupgrade", "effect_bonus_parse.py")
    assert "def unit_matches_tech_targets(" in parse
    assert "def type_matches_tech_targets(" in parse

    base = _source("soundrts", "worldupgrade", "base.py")
    assert "def _unit_authorised(cls, unit):" in base

    orders = _source("soundrts", "worldorders", "base.py")
    assert "def _applicable_techs_for_type(" in orders


def test_aoe2_rules_have_the_unique_buildings_and_the_aura_rows():
    """``mods/aoe2/rules.txt`` 里必须真的有 9 个独有建筑与光环字段。"""
    rules = _source("mods", "aoe2", "rules.txt")
    for name in (
        "krepost",
        "caravanserai",
        "persian_caravanserai",
        "hindustani_caravanserai",
        "folwark",
        "polish_folwark",
        "mule_cart",
        "armenian_mule_cart",
        "georgian_mule_cart",
        "fortified_church",
        "armenian_fortified_church",
        "georgian_fortified_church",
        "settlement",
        "incan_settlement",
        "donjon",
        "houfnice",
        "missionary",
    ):
        assert f"def {name}\n" in rules, name
    assert "aura_radius 8" in rules
    assert "aura_target_types trade_cart" in rules


def test_aoe2_rules_dropped_the_fan_invented_technologies():
    """AoE2 DE 里并不存在的科技必须已经删掉。"""
    rules = _source("mods", "aoe2", "rules.txt")
    for bogus in (
        "boiling_oil",
        "mahouts",
        "atikulu",
        "obsidian_arrows",
        "el_dorado",
        "frontier_defense",
        "fogarasi_mercenaries",
    ):
        assert f"\ndef {bogus}\n" not in rules, bogus


def test_aoe2_rules_wire_the_armored_elephant_line_upgrade():
    """装甲象的精锐形态必须带 ``line_upgrade``。"""
    rules = _source("mods", "aoe2", "rules.txt")
    i = rules.index("\ndef elite_armored_elephant\n")
    block = rules[i:i + 2000]
    assert "line_upgrade 1" in block
    assert "no_auto_upgrade 1" in block
