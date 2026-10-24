"""审计：1.5.1.3 — 14 个 AoE2 决定版后期文明 + 5 个新的 mod 规则字段。

1.5.1.3 发布的内容是：
  * ``mods/aoe2/rules.txt`` 里 14 个 DE 后期文明的完整 ``def`` 块；
  * 5 个端到端的新规则字段（``can_fire_on_move`` / ``agro_on_sight`` /
    ``allow_extra_town_center`` / ``relic_loss_immunity`` /
    ``trade_reward_bonus_pct``）；
  * 条约开局提示被 silent flush 吞掉的修复。

这些测试断言五种语言的发布说明都如实记录了上述内容，并核对引擎侧
与 mod 侧确实落地了对应的字段。
"""
from __future__ import annotations

from pathlib import Path

from soundrts.version import VERSION


_LANGS = ("zh", "en", "es", "it", "pt-BR")

# 1.5.1.3 新增的 5 个规则字段。
_NEW_FIELDS = (
    "can_fire_on_move",
    "agro_on_sight",
    "allow_extra_town_center",
    "relic_loss_immunity",
    "trade_reward_bonus_pct",
)


def _source(*path_parts):
    return (
        Path(__file__).resolve().parents[2].joinpath(*path_parts).read_text(encoding="utf-8")
    )


def _section_1513(lang: str) -> str:
    text = _source("doc_src", "src", lang, "relnotes.rst")
    start = text.index("\n1.5.1.3\n")
    rest = text[start:]
    next_idx = rest.find("\n1.5.1.2\n")
    return rest if next_idx == -1 else rest[:next_idx]


def test_version_is_at_least_1513():
    """当前 VERSION 必须 >= 1.5.1.3。

    早期版本把版本号写死成精确值，导致此后每个版本发布都会让这条测试
    失败 —— 那是噪声而不是信号。改成断言「至少」，与
    test_changelog_1510.py 保持一致。
    """
    assert tuple(int(x) for x in VERSION.split(".")) >= (1, 5, 1, 3)


def test_all_relnotes_have_1513_before_1512_in_all_five_languages():
    for lang in _LANGS:
        src = _source("doc_src", "src", lang, "relnotes.rst")
        assert "\n1.5.1.3\n" in src, (lang, "missing 1.5.1.3 header")
        assert src.index("\n1.5.1.3\n") < src.index("\n1.5.1.2\n"), lang


def test_relnotes_1513_document_the_five_new_rule_fields():
    """五种语言的 1.5.1.3 段落都必须列出 5 个新规则字段。"""
    for lang in _LANGS:
        section = _section_1513(lang)
        for field in _NEW_FIELDS:
            assert field in section, (lang, field)
        assert "definitions.py" in section, lang
        assert "mods/aoe2/rules.txt" in section, lang


def test_relnotes_1513_document_the_treaty_voice_flush_fix():
    """条约开局提示被 silent flush 吞掉的修复必须写进发布说明。"""
    for lang in _LANGS:
        section = _section_1513(lang)
        assert "voice.flush" in section, lang


def test_new_rule_fields_are_declared_in_the_engine():
    """5 个新字段必须在 definitions.py 里声明。"""
    text = _source("soundrts", "definitions.py")
    for field in _NEW_FIELDS:
        assert field in text, field


def test_new_rule_fields_are_used_by_the_aoe2_mod():
    """5 个新字段必须在 mods/aoe2/rules.txt 里落地。"""
    text = _source("mods", "aoe2", "rules.txt")
    for field in _NEW_FIELDS:
        assert field in text, field


def test_treaty_voice_flush_replacement_is_in_the_engine():
    """srv_quit 路径必须改用会等待播完的 voice.flush()。"""
    text = _source("soundrts", "clientgame", "game_interface_base.py")
    assert "voice.flush(" in text
