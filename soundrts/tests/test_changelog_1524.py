# -*- coding: utf-8 -*-
"""审计：1.5.2.4 — 星际 1 / 星际 2 模组新原语。

1.5.2.4 发布的内容是：
  * 新增**护盾层**：伤害先扣护盾，溢出才打血；脱战回盾；升级可加护盾上限；
  * 新增**折跃传送门 / 虫道**：建筑把单位瞬间召唤到远处格子里；
  * 新增**建筑燃烧自毁**：血量低于阈值就着火，持续掉血直到爆炸；
  * 星际模组：神族等离子护盾、SC2 单位补齐、单位不互相阻挡、异虫脱战回血；
  * 文档：五种语言的制模文档说明全部新关键字。

这些测试断言五种语言的发行说明都如实记录了上述内容，并且引擎侧与
模组数据侧确实如此。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.2.4 段落里被点名。
_TOPICS = (
    # 护盾层
    "shield_max",
    "shield_start",
    "shield_regen",
    "shield_regen_cd",
    "shield_regen_ready",
    "shield_pierce",
    # 折跃传送门 / 虫道
    "warp_in_types",
    "warp_in_charge",
    "warp_in_recharge",
    "warp_in_needs_field",
    "warp_in_field_radius_m",
    "warp_in_effect",
    "warp_in_skill",
    # 建筑燃烧
    "burn_hp_threshold_pct",
    "burn_damage",
    "burn_interval",
    # 文档与测试
    "modding.rst",
    "test_starcraft_shields.py",
    "test_starcraft_warp_in.py",
    "test_starcraft_building_burn.py",
    # 引擎文件
    "soundrts/world_warp_in.py",
    "soundrts/world_building_burn.py",
    "soundrts/worldorders/warp_in.py",
    "soundrts/combat/damage_effects.py",
    # 模组数据
    "mods/starcraft/rules.txt",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1524(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.2.4\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.2.3\n")
    return rest if next_idx == -1 else rest[:next_idx]


def _modding_section(lang: str) -> str:
    text = _source("doc_src", "src", lang, "mod", "modding.rst")
    marker = "1.5.2.4"
    start = text.index(marker)
    return text[start:]


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------
def test_version_is_at_least_1524():
    """当前 VERSION 必须 >= 1.5.2.4。"""
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 2, 4)


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
    """五种语言的 1.5.2.4 段落都必须点名全部新特性。"""
    for lang in _LANGS:
        section = _section_1524(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_all_modding_guides_document_every_new_keyword_in_all_five_languages():
    """五种语言的制模文档都必须说明全部新关键字。"""
    keywords = (
        "shield_max",
        "shield_regen_cd",
        "shield_regen_ready",
        "shield_pierce",
        "warp_in_types",
        "warp_in_charge",
        "warp_in_recharge",
        "warp_in_needs_field",
        "warp_in_field_radius_m",
        "burn_hp_threshold_pct",
        "burn_damage",
        "burn_interval",
        "collision",
    )
    for lang in _LANGS:
        section = _modding_section(lang)
        for keyword in keywords:
            assert keyword in section, (lang, keyword)


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
    for keyword in (
        "shield_max",
        "shield_start",
        "shield_regen",
        "shield_regen_cd",
        "shield_regen_ready",
        "shield_pierce",
        "warp_in_types",
        "warp_in_charge",
        "warp_in_recharge",
        "warp_in_needs_field",
        "warp_in_field_radius_m",
        "warp_in_effect",
        "warp_in_skill",
        "burn_hp_threshold_pct",
        "burn_damage",
        "burn_interval",
    ):
        assert keyword in known, keyword


def test_the_new_orders_are_registered():
    from soundrts.worldorders import ORDERS_DICT

    assert "warp_in" in ORDERS_DICT
    assert "nydus_in" in ORDERS_DICT


def test_the_new_orders_have_style_entries():
    from soundrts.definitions import style

    for keyword in ("warp_in", "nydus_in"):
        assert style.has(keyword, "index"), keyword
        assert style.has(keyword, "title"), keyword


def test_the_new_tts_ids_exist_in_every_language():
    from soundrts import msgparts as mp

    ids = (
        mp.SHIELD,
        mp.SHIELD_MAX,
        mp.SHIELD_REGEN,
        mp.SHIELD_REGEN_CD,
        mp.SHIELD_REGEN_READY,
        mp.WARP_IN,
        mp.NYDUS,
        mp.BUILDING_BURN,
    )
    flat = [str(x) for group in ids for x in group]
    assert len(set(flat)) == len(flat), "the TTS ids must be unique"
    for lang in ("", "-be", "-cs", "-de", "-es", "-fr", "-it", "-pl", "-pt-BR", "-ru", "-sk", "-vi", "-zh"):
        text = _source("res", f"ui{lang}", "tts.txt")
        for tts_id in flat:
            assert f"\n{tts_id}\t" in f"\n{text}", (lang, tts_id)


# ---------------------------------------------------------------------------
# mod data
# ---------------------------------------------------------------------------
def test_the_starcraft_mod_uses_the_new_keywords():
    text = _source("mods", "starcraft", "rules.txt")
    assert "shield_max" in text
    assert "collision 0" in text
    assert "hp_regen" in text
    assert "warp_in_types" in text
    assert "burn_hp_threshold_pct" in text


def test_the_starcraft_mod_declares_the_sc2_units():
    from soundrts.definitions import Rules

    rules = Rules()
    rules.load(_source("mods", "starcraft", "rules.txt"))
    for name in (
        "orbital_command",
        "mule",
        "reaper",
        "banshee",
        "raven",
        "cyclone",
        "sentry",
        "stalker",
        "immortal",
        "void_ray",
        "baneling",
        "infestor",
        "ravager",
        "viper",
        "brood_lord",
    ):
        assert rules.unit_class(name) is not None, name


def test_the_starcraft_mod_buildings_can_warp_units_in():
    from soundrts.definitions import Rules

    rules = Rules()
    rules.load(_source("mods", "starcraft", "rules.txt"))
    gate = rules.unit_class("warp_gate")
    assert "warp_in" in gate.basic_skills
    nydus = rules.unit_class("nydus")
    assert "nydus_in" in nydus.basic_skills


def test_the_protoss_upgrades_raise_the_shield_pool():
    from soundrts.definitions import Rules

    rules = Rules()
    rules.load(_source("mods", "starcraft", "rules.txt"))
    for name in ("protoss_plasma_shields", "protoss_plasma_shields_2", "protoss_plasma_shields_3"):
        upgrade = rules.unit_class(name)
        assert upgrade is not None, name
        rows = getattr(upgrade, "effect", None) or []
        assert any("shield_max" in row for row in rows), name
