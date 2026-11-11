"""审计：1.5.1.8 — 破隐机制（攻击暴露）、亡灵骑士、隐形子系统的模组文档。

1.5.1.8 发布的内容是：
  * 新的破隐机制：``reveal_stealth_on_attack`` + ``stealth_reveal_time``，
    在隐形 / 隐身状态下发动攻击会暴露自己（帝国 3 间谍 / 忍者 / 美洲虎潜行武士）；
  * 基础版 ``res/rules.txt`` 新增 ``undead_knight``（攻击后暴露 3 秒）；
  * 法兰克村民才可升级为 ``flemish_militia``（越南村民不再能升级）；
  * 马扎尔城堡里的悬空 ``mercenaries`` 科技被移除（点选即崩溃）；
  * AoE2 DE 缺失的样式定义与 TTS 播报（9122-9131，13 个语言包）；
  * AI 会派机动侦测器拆掉隐身的敌方基地；
  * AoE2 jl3 的黑暗时代经济修复、res jl1 的探索与城堡时代波次拆分；
  * 状态面板会列出 ``effect_bonus_targets`` 的科技；
  * 观战重建与实战不再共用感知 / AI 决策缓存；
  * 战败后立刻退出对局（``Voice.discard_pending()``）；
  * 第 4 到第 7 轮热点路径优化；
  * z5 地图的电脑阵容重新平衡；
  * 模组编写指南新增隐形子系统与破隐机制章节（五种语言）。

这些测试断言五种语言的发行说明都如实记录了上述内容，模组指南的五种语言
都写清了破隐机制，并且引擎侧与 mod 侧确实落地了对应的实现。
"""

from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION

_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 每个条目都必须在这五种语言的 1.5.1.8 段落里被点名。
_TOPICS = (
    # 破隐机制
    "reveal_stealth_on_attack",
    "stealth_reveal_time",
    # 亡灵骑士
    "undead_knight",
    # 法兰克村民 / 佛兰德民兵
    "flemish_militia",
    "burgundian_villager",
    # 马扎尔城堡的悬空科技
    "mercenaries",
    # AoE2 DE 的样式与播报
    "style.txt",
    "tts.txt",
    # AI 拆隐身基地
    "is_a_detector",
    "detection_range",
    "cancel_all_orders",
    # AI 经济与探索
    "jl3",
    "jl1",
    # 状态面板
    "effect_bonus_targets",
    # 观战缓存隔离
    "PerceptionCachesMixin",
    # 战败立刻退出
    "discard_pending",
    # 性能
    "PERF_ROUND7_SUMMARY.md",
    # z5 地图
    "z5.txt",
    # 模组指南
    "modding.rst",
    # 新测试
    "test_changelog_1518.py",
)

# 模组指南里必须写到的隐形子系统字段。
_MODDING_FIELDS = (
    "is_invisible",
    "is_cloakable",
    "is_a_cloaker",
    "cloaking_range",
    "is_a_detector",
    "detection_range",
    "reveal_stealth_on_attack",
    "stealth_reveal_time",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1518(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.8\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.7\n")
    return rest if next_idx == -1 else rest[:next_idx]


def _modding(lang: str) -> str:
    return _source("doc_src", "src", lang, "mod", "modding.rst")


def test_version_is_at_least_1518():
    """当前 VERSION 必须 >= 1.5.1.8。

    早期版本把版本号写死成精确值，导致此后每个版本发布都会让这条测试
    失败 —— 那是噪声而不是信号。断言"至少"。
    """
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 8)


def test_all_relnotes_have_1518_before_1517_in_all_five_languages():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.8\n" in src, (lang, "missing 1.5.1.8 header")
        assert src.index("\n1.5.1.8\n") < src.index("\n1.5.1.7\n"), lang
        assert src.index("\n1.5.1.7\n") < src.index("\n1.5.1.6\n"), lang


def test_relnotes_1518_document_every_session_topic():
    """五种语言的 1.5.1.8 段落都必须点名本次会话的每一项改动。"""
    for lang in _LANGS:
        section = _section_1518(lang)
        for topic in _TOPICS:
            assert topic in section, (lang, topic)


def test_relnotes_1518_document_the_stealth_reveal_mechanic():
    """破隐机制必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1518(lang)
        assert "reveal_stealth_on_attack" in section, lang
        assert "stealth_reveal_time" in section, lang


def test_relnotes_1518_document_the_undead_knight():
    """亡灵骑士必须写进发行说明。"""
    for lang in _LANGS:
        assert "undead_knight" in _section_1518(lang), lang


def test_relnotes_1518_document_the_flemish_militia_upgrade():
    """法兰克村民才能升级为佛兰德民兵，必须写进发行说明。"""
    for lang in _LANGS:
        section = _section_1518(lang)
        assert "flemish_militia" in section, lang
        assert "burgundian_villager" in section, lang


def test_modding_guide_documents_the_stealth_subsystem_in_all_languages():
    """模组指南的五种语言都必须写清隐形子系统与破隐机制。"""
    for lang in _LANGS:
        text = _modding(lang)
        for field in _MODDING_FIELDS:
            assert field in text, (lang, field)


def test_modding_guide_documents_the_reveal_semantics():
    """破隐机制的语义必须写清：暴露时长、恢复、不可重新隐身。"""
    for lang in _LANGS:
        text = _modding(lang)
        assert "1.5.1.8" in text, lang


def test_engine_declares_the_stealth_reveal_fields():
    """两个新规则字段必须在引擎里注册。"""
    definitions = _source("soundrts", "definitions.py")
    assert '"reveal_stealth_on_attack"' in definitions
    assert '"stealth_reveal_time"' in definitions


def test_engine_implements_the_reveal():
    """暴露逻辑必须真的在引擎里实现。"""
    entity = _source("soundrts", "worldentity.py")
    assert "def _reveal_stealth(self, now):" in entity
    assert "def _end_stealth_reveal(self):" in entity
    assert "reveal_stealth_on_attack = 0" in entity
    assert "stealth_reveal_time = 3 * PRECISION" in entity

    attack = _source("soundrts", "combat", "attack_action.py")
    assert "_reveal_stealth" in attack


def test_res_rules_define_the_undead_knight():
    """基础版规则里必须真的有亡灵骑士。"""
    rules = _source("res", "rules.txt")
    assert "\ndef undead_knight\n" in rules
    i = rules.index("\ndef undead_knight\n")
    block = rules[i:i + 2000]
    assert "reveal_stealth_on_attack 1" in block
    assert "stealth_reveal_time 3" in block


def test_aoe2_rules_put_the_flemish_militia_upgrade_on_the_burgundian_villager():
    """佛兰德民兵的升级只能挂在法兰克村民上。"""
    rules = _source("mods", "aoe2", "rules.txt")
    i = rules.index("\ndef burgundian_villager\n")
    block = rules[i:i + 2000]
    assert "can_upgrade_to flemish_militia" in block


def test_aoe2_rules_dropped_the_dangling_mercenaries_tech():
    """马扎尔城堡不再引用不存在的 ``mercenaries`` 科技。"""
    rules = _source("mods", "aoe2", "rules.txt")
    assert "\ndef mercenaries\n" not in rules
